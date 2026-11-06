"""Étape E4 — Relier et dériver (doc. 2, 2.6) : les faits lus (Z2) deviennent le graphe relié (Z3).

Une **règle** est un module de `empreinte_src/regles/` qui déclare :

    NOM = "R-COMPOSITION"           # nom publié sur la page de méthodologie (doc. 1, 1.6)
    VERSION = 1                     # à augmenter à chaque changement de comportement
    DEPEND = ("R-GOUVERNEMENTS",)   # règles dont elle lit les sorties
    DEPEND_FACULTATIF = ("R-MATIERE",)   # lues si elles existent (ctx.existe), facultatif
    SORTIES = ("membre_gouvernement",)
    DESCRIPTION = "…"               # le texte publié sur la page de méthodologie

    def appliquer(ctx) -> dict:     # écrit ses sorties avec ctx.ecrire ; rend sa couverture
        ctx.ecrire("membre_gouvernement", "SELECT … FROM an_acteurs__mandat …")
        return {"rattachement_etabli": (n, d)}     # chiffres de couverture : (numérateur, dénominateur)

Dans le SQL d'une règle :
- `<lecteur>__<table>` est l'**état courant** d'une table de faits (dernière version de chaque
  fichier source, encore présent à la source) ;
- `<lecteur>__<table>__hist` donne toutes les versions conservées ;
- chaque sortie d'une règle déjà appliquée est une vue du même nom ;
- `decision_<type>` donne les décisions de la propriétaire de ce type (dossier `decisions/`).

Tout est recalculé à chaque mise à jour (doc. 3, J6). Chaque ligne de sortie porte la colonne
`regle` (`R-COMPOSITION@1`). Une règle qui ne conclut pas écrit « non établi » et sa raison,
jamais une devinette.
"""
from __future__ import annotations

import glob
import importlib
import os
import pkgutil
import time

import duckdb
import yaml

from .memoire import regler_duckdb


def regles() -> list:
    from . import regles as paquet
    mods = []
    for info in pkgutil.iter_modules(paquet.__path__):
        if info.name.startswith("_"):
            continue
        m = importlib.import_module(f"{paquet.__name__}.{info.name}")
        if all(hasattr(m, a) for a in ("NOM", "VERSION", "DEPEND", "SORTIES", "appliquer")):
            mods.append(m)
    return ordonner(mods)


def ordonner(mods) -> list:
    """Ordre topologique selon DEPEND ; une dépendance inconnue ou circulaire est une erreur."""
    par_nom = {m.NOM: m for m in mods}
    ordre, en_cours, fait = [], set(), set()

    def visiter(m):
        if m.NOM in fait:
            return
        if m.NOM in en_cours:
            raise ValueError(f"dépendance circulaire autour de {m.NOM}")
        en_cours.add(m.NOM)
        for d in m.DEPEND:
            if d not in par_nom:
                raise ValueError(f"{m.NOM} dépend de {d}, règle inconnue")
            visiter(par_nom[d])
        # Dépendance facultative : appliquée avant si elle existe, sans erreur sinon.
        for d in getattr(m, "DEPEND_FACULTATIF", ()):
            if d in par_nom:
                visiter(par_nom[d])
        en_cours.discard(m.NOM)
        fait.add(m.NOM)
        ordre.append(m)

    for m in sorted(mods, key=lambda m: m.NOM):
        visiter(m)
    return ordre


class Contexte:
    def __init__(self, dossier_z2: str, dossier_z3: str, dossier_decisions: str | None = None,
                 generation: int | None = None, date_reference: str | None = None,
                 registre=None):
        self.z2, self.z3 = dossier_z2, dossier_z3
        # Registre des identités (ZI, correction P1) : R-IDENTITE y lit les attributions
        # acquises et y ajoute les nouvelles. None : une règle qui en a besoin le dit.
        self.registre = registre
        os.makedirs(dossier_z3, exist_ok=True)
        self.generation = generation
        self.date_reference = date_reference      # « aujourd'hui » pour les comptes datés
        self.con = duckdb.connect()
        regler_duckdb(self.con)
        self.regle_courante = None
        self.sorties: dict[str, str] = {}
        for p in sorted(glob.glob(os.path.join(dossier_z2, "*.parquet"))):
            nom = os.path.basename(p)[:-len(".parquet")]
            if nom.endswith("__versions"):
                continue
            self.x(f"CREATE VIEW {nom}__hist AS SELECT * FROM read_parquet('{p}')")
            # État courant : dernière version de chaque fichier source, encore présent.
            self.x(f"""CREATE VIEW {nom} AS SELECT x.* FROM read_parquet('{p}') x
                SEMI JOIN (SELECT prov_point AS p, prov_uid AS u, max(prov_version) AS n
                           FROM read_parquet('{p}') GROUP BY 1, 2) d
                  ON x.prov_point = d.p AND x.prov_uid = d.u AND x.prov_version = d.n
                WHERE x.prov_etat = 'present'""")
        self._charger_decisions(dossier_decisions)

    def _charger_decisions(self, dossier):
        import pyarrow as pa
        par_type: dict[str, list] = {}
        if dossier and os.path.isdir(dossier):
            for p in sorted(glob.glob(os.path.join(dossier, "**", "*.yaml"), recursive=True)):
                with open(p) as f:
                    d = yaml.safe_load(f) or {}
                # Un fichier porte une décision, ou plusieurs du même type sous `decisions:`
                # (une table de 152 libellés de ministère tient ainsi dans un seul fichier).
                lot = d.pop("decisions", None)
                elements = [{**d, **x} for x in lot] if isinstance(lot, list) else [d]
                for k, x in enumerate(elements):
                    x["fichier"] = os.path.relpath(p, dossier) + (f"#{k}" if lot else "")
                    par_type.setdefault(x.get("type", "inconnu"), []).append(
                        {c: (v if isinstance(v, (str, int, float, bool)) or v is None else str(v))
                         for c, v in x.items()})
        self.decisions = par_type
        for t, rows in par_type.items():
            self.con.register(f"decision_{t}", pa.Table.from_pylist(rows))

    def existe(self, nom: str) -> bool:
        return bool(self.con.execute(
            "SELECT count(*) FROM duckdb_views() WHERE view_name = ?", [nom]).fetchall()[0][0])

    def ecrire(self, nom: str, sql: str):
        """Écrit une sortie de la règle courante dans Z3 et en fait une vue."""
        r = self.regle_courante
        p = os.path.join(self.z3, f"{nom}.parquet")
        self.x(f"COPY (SELECT *, '{r.NOM}@{r.VERSION}' AS regle FROM ({sql})) "
                         f"TO '{p}' (FORMAT parquet, COMPRESSION zstd, ROW_GROUP_SIZE 20000)")
        self.x(f"CREATE OR REPLACE VIEW {nom} AS SELECT * FROM read_parquet('{p}')")
        self.sorties[nom] = p

    def un(self, sql: str, params=None):
        return self.con.execute(sql, params or []).fetchall()[0][0]

    def x(self, sql: str, params=None):
        """Exécute un ordre et lit son résultat jusqu'au bout (DuckDB l'exige avant l'ordre suivant)."""
        return self.con.execute(sql, params or []).fetchall()


def relier(ctx: Contexte, mods=None) -> list[dict]:
    """Applique toutes les règles dans l'ordre de leurs dépendances. Rend le bilan."""
    bilan = []
    for m in mods or regles():
        ctx.regle_courante = m
        debut = time.monotonic()
        couverture = m.appliquer(ctx) or {}
        manquantes = [s for s in m.SORTIES if s not in ctx.sorties]
        if manquantes:
            raise RuntimeError(f"{m.NOM} n'a pas écrit {manquantes}")
        bilan.append({"regle": f"{m.NOM}@{m.VERSION}", "duree_s": round(time.monotonic() - debut, 2),
                      "lignes": {s: ctx.un(f"SELECT count(*) FROM {s}") for s in m.SORTIES},
                      "couverture": {k: list(v) for k, v in couverture.items()},
                      "description": getattr(m, "DESCRIPTION", "")})
    return bilan
