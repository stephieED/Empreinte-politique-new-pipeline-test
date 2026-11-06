"""Étape E3 — Lire (doc. 2, 2.5) : les versions de Z1 deviennent des faits (Z2).

Un **lecteur** transforme les octets exacts d'une version de membre en lignes de faits. Il
déclare :

    NOM = "an_scrutins"                 # nom stable
    VERSION = 1                         # à augmenter à chaque correction ou champ ajouté
    TYPES = ("scrutins",)               # types de points d'accès lus (config/points_acces.yaml)
    TABLES = {"scrutin": SCHEMA, ...}   # tables produites et leurs colonnes propres (pyarrow)

    def lire(m: MembreLu) -> dict[str, list[dict]]:
        ...                             # rend {table: [lignes]} ; une erreur lève une exception

Le cadre ajoute à chaque ligne les colonnes de provenance (doc. 1, 1.4) :
`prov_source`, `prov_point`, `prov_uid`, `prov_version`, `prov_empreinte`, `prov_vu_du`,
`prov_vu_jusqu_au`, `prov_etat`, `lecteur`, `licence`. Une ligne peut fournir `prov_url` (adresse
publique du fait) ; le cadre la garde.

Z2 garde les faits de **toutes** les versions conservées, avec leurs dates de validité dans
l'entrepôt (`prov_vu_du`, `prov_vu_jusqu_au`, `prov_etat`) : l'état courant est celui des versions dont le
membre est encore présent, et l'historique reste interrogeable. Le cache est indexé par
(empreinte, lecteur, version du lecteur) : une version déjà lue n'est pas relue ; un lecteur
dont la version change relit toutes les versions conservées.
"""
from __future__ import annotations

import importlib
import os
import pkgutil
import traceback
from dataclasses import dataclass

import pyarrow as pa
import pyarrow.parquet as pq

from .entrepot import Entrepot

COLONNES_PROVENANCE = [
    ("prov_source", pa.string()), ("prov_point", pa.string()), ("prov_uid", pa.string()),
    ("prov_version", pa.int32()), ("prov_empreinte", pa.string()), ("prov_url", pa.string()),
    ("prov_vu_du", pa.int32()), ("prov_vu_jusqu_au", pa.int32()), ("prov_etat", pa.string()),
    ("lecteur", pa.string()), ("licence", pa.string()),
]


@dataclass
class MembreLu:
    point_acces: str
    source: str
    type: str
    uid: str
    chemin: str
    version: int
    empreinte: str
    octets: bytes
    licence: str | None


# -- aides pour les pièges communs des archives (cahier 3.1) --------------------------------

def liste(x) -> list:
    """« Un objet seul est un dictionnaire, plusieurs sont une liste » ; None -> []."""
    if x is None or est_nil(x):
        return []
    return x if isinstance(x, list) else [x]


def est_nil(x) -> bool:
    """Le vide de l'Assemblée s'écrit parfois {"@xsi:nil": "true"}."""
    return isinstance(x, dict) and x.get("@xsi:nil") in ("true", True)


def val(x):
    """Valeur simple : None pour le vide écrit à la manière de l'Assemblée."""
    if x is None or est_nil(x):
        return None
    if isinstance(x, dict) and "#text" in x:
        return x["#text"]
    return x


def pa_id(x) -> str | None:
    """Identifiant de personne de l'Assemblée avec son préfixe `PA` (rétabli s'il manque)."""
    x = val(x)
    if x is None:
        return None
    x = str(x).strip()
    if not x:
        return None
    return x if x.startswith("PA") else f"PA{x}"


# -- registre des lecteurs -------------------------------------------------------------------

def lecteurs() -> list:
    """Tous les modules de `empreinte/lecteurs/` qui déclarent NOM, VERSION, TYPES, TABLES, lire."""
    from . import lecteurs as paquet
    out = []
    for info in pkgutil.iter_modules(paquet.__path__):
        if info.name.startswith("_"):
            continue
        mod = importlib.import_module(f"{paquet.__name__}.{info.name}")
        if all(hasattr(mod, a) for a in ("NOM", "VERSION", "TYPES", "TABLES", "lire")):
            out.append(mod)
    return sorted(out, key=lambda m: m.NOM)


def schema_complet(schema_propre: pa.Schema) -> pa.Schema:
    noms = set(schema_propre.names)
    return pa.schema(list(schema_propre) + [pa.field(n, t) for n, t in COLONNES_PROVENANCE
                                            if n not in noms])


# -- exécution -------------------------------------------------------------------------------

class Lecture:
    def __init__(self, entrepot: Entrepot, dossier_z2: str, config: dict):
        self.e = entrepot
        self.dossier = dossier_z2
        os.makedirs(dossier_z2, exist_ok=True)
        self.licences = {p["id"]: p.get("licence") for p in config["points_acces"]}
        self.bilan: list[dict] = []

    def _chemin(self, lecteur, table):
        return os.path.join(self.dossier, f"{lecteur.NOM}__{table}.parquet")

    def _cache(self, lecteur) -> set:
        """Versions (point, uid, version) déjà lues par cette version du lecteur."""
        p = os.path.join(self.dossier, f"{lecteur.NOM}__versions.parquet")
        if not os.path.exists(p):
            return set()
        return {(r["p"], r["u"], r["n"]) for r in pq.read_table(p).to_pylist()
                if r["lecteur_version"] == lecteur.VERSION}

    def executer(self, mod, points: list[str] | None = None, limite: int | None = None) -> dict:
        """Lit les versions conservées des types du lecteur qui ne sont pas déjà lues par cette
        version du lecteur. Mémoire bornée : les lignes sont écrites lot par lot, et les
        jointures sont faites par DuckDB."""
        import duckdb
        versions = [r for r in self.e._index if r["type"] in mod.TYPES
                    and (not points or r["point_acces"] in points)]
        if limite:
            versions = versions[:limite]
        deja = self._cache(mod)
        cle = lambda r: (r["point_acces"], r["uid"], r["version"])
        a_lire = [r for r in versions if cle(r) not in deja]
        tmp = {t: self._chemin(mod, t) + ".tmp" for t in mod.TABLES}
        schemas = {t: schema_complet(mod.TABLES[t]) for t in mod.TABLES}
        ecrivains = {t: pq.ParquetWriter(tmp[t], schemas[t], compression="zstd") for t in mod.TABLES}
        try:
            # 2. Lecture des versions nouvelles, lot par lot.
            illisibles, exemples = 0, []
            par_empreinte: dict[str, list] = {}
            for r in a_lire:
                par_empreinte.setdefault(r["empreinte"], []).append(r)
            sortie = {t: [] for t in mod.TABLES}
            nb_sortie = 0

            def vider():
                for t, rows in sortie.items():
                    if rows:
                        ecrivains[t].write_table(pa.Table.from_pylist(rows, schema=schemas[t]))
                        rows.clear()

            octets_tampon = 0
            for emp, octets in self.e.parcourir(par_empreinte):
                octets_tampon += len(octets) * len(par_empreinte[emp])
                for r in par_empreinte[emp]:
                    m = MembreLu(r["point_acces"], r["source"], r["type"], r["uid"], r["chemin"],
                                 r["version"], r["empreinte"], octets,
                                 self.licences.get(r["point_acces"]))
                    try:
                        res = mod.lire(m)
                    except Exception as e:
                        illisibles += 1
                        if len(exemples) < 5:
                            exemples.append(f"{r['uid']}: {type(e).__name__}: {e} | "
                                            + " / ".join(traceback.format_exc(limit=3).splitlines()[-3:]))
                        continue
                    for t, rows in res.items():
                        for x in rows:
                            x.setdefault("prov_url", None)
                            x.update(prov_source=r["source"], prov_point=r["point_acces"],
                                     prov_uid=r["uid"], prov_version=r["version"],
                                     prov_empreinte=r["empreinte"],
                                     lecteur=f"{mod.NOM}@{mod.VERSION}", licence=m.licence,
                                     prov_vu_du=None, prov_vu_jusqu_au=None, prov_etat=None)
                        sortie[t].extend(rows)
                        nb_sortie += len(rows)
                    # On vide le tampon au-delà de 100 000 lignes ou de 64 Mo d'octets lus
                    # (des textes longs, comme les questions, pèsent plus que leur nombre).
                    if nb_sortie >= 100_000 or octets_tampon >= 64 << 20:
                        vider()
                        nb_sortie, octets_tampon = 0, 0
            vider()
        finally:
            for w in ecrivains.values():
                w.close()
        # 3. Validité de chaque ligne = celle de sa version dans l'entrepôt (jointure DuckDB).
        v = pa.Table.from_pylist([{"p": r["point_acces"], "u": r["uid"], "n": r["version"],
                                   "du": r["vu_du"], "au": r["vu_jusqu_au"], "et": r["etat"]}
                                  for r in versions],
                                 schema=pa.schema([("p", pa.string()), ("u", pa.string()),
                                                   ("n", pa.int32()), ("du", pa.int32()),
                                                   ("au", pa.int32()), ("et", pa.string())]))
        con = duckdb.connect()
        from .memoire import regler_duckdb
        regler_duckdb(con)
        con.register("v", v)
        con.register("r", pa.Table.from_pylist([{"p": x["point_acces"], "u": x["uid"], "n": x["version"]}
                                                for x in a_lire],
                                               schema=pa.schema([("p", pa.string()), ("u", pa.string()),
                                                                 ("n", pa.int32())])))
        lignes = {}
        for t in mod.TABLES:
            cols = ", ".join(f'x."{c}"' if c not in ("prov_vu_du", "prov_vu_jusqu_au", "prov_etat")
                             else {"prov_vu_du": "v.du AS prov_vu_du", "prov_vu_jusqu_au": "v.au AS prov_vu_jusqu_au",
                                   "prov_etat": "v.et AS prov_etat"}[c] for c in schemas[t].names)
            final = self._chemin(mod, t)
            sources = f"SELECT * FROM read_parquet('{tmp[t]}')"
            if deja and os.path.exists(final):
                # Lignes déjà lues, sauf celles des versions relues.
                sources += f""" UNION ALL BY NAME SELECT * FROM read_parquet('{final}') o
                    WHERE NOT EXISTS (SELECT 1 FROM r WHERE r.p = o.prov_point
                                      AND r.u = o.prov_uid AND r.n = o.prov_version)"""
            con.execute(f"""COPY (SELECT {cols} FROM ({sources}) x
                            JOIN v ON v.p = x.prov_point AND v.u = x.prov_uid AND v.n = x.prov_version)
                            TO '{final}.new' (FORMAT parquet, COMPRESSION zstd, ROW_GROUP_SIZE 20000)""")
            os.replace(final + ".new", final)
            os.unlink(tmp[t])
            lignes[t] = pq.ParquetFile(final).metadata.num_rows
        con.close()
        lues = sorted(deja | {cle(r) for r in a_lire})
        pq.write_table(pa.Table.from_pylist([{"p": p_, "u": u, "n": n, "lecteur_version": mod.VERSION}
                                             for (p_, u, n) in lues]),
                       os.path.join(self.dossier, f"{mod.NOM}__versions.parquet"))
        b = {"lecteur": f"{mod.NOM}@{mod.VERSION}", "versions": len(versions),
             "lues": len(a_lire), "illisibles": illisibles, "exemples_illisibles": exemples,
             "lignes": lignes}
        self.bilan.append(b)
        return b

    def _lire_table(self, mod, t) -> list[dict]:
        p = self._chemin(mod, t)
        return pq.read_table(p).to_pylist() if os.path.exists(p) else []
