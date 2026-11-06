"""Étape E5 — Composer (doc. 2, 2.7) : les fichiers servis des fiches (doc. 1, 1.7).

Un **composeur** est un module de `empreinte_src/composeurs/` qui déclare :

    NOM = "legislature"            # type de fiche
    VERSION = 1
    DEPEND = ("R-LEGISLATURES", …) # règles dont il lit les sorties

    def composer(ctx, ecr):        # ctx : le Contexte des règles ; ecr : l'Ecrivain ci-dessous
        f = ecr.fiche("legislature", "17", titre="XVIIe législature")
        f.entete({...})                                     # fiche.json : chargé tout de suite
        f.section("textes", lignes, type_fait="texte_legislature",
                  ids={"dossier": "dossier"}, date="date_depot", source="source_url",
                  couverture={...})                         # textes.json.gz : à la demande

Ce que le cadre garantit :
- chaque fichier est écrit en JSON compact, **pré-compressé** (`.json.gz`, doc. 1, 1.7.1) ;
- les listes sont écrites en colonnes (`{"colonnes": [...], "lignes": [[...]]}`) ;
- chaque section a sa **couverture** et chaque fiche ses licences (union de celles de ses faits) ;
- chaque ligne affichée devient un **fait publié** de l'export « fiche par fiche »
  (commande de réalisation, section 7) : fiche, section, type, identifiants, valeur, date, source ;
- le manifeste dit, pour chaque fichier, son empreinte et ses poids brut et compressé (mesure
  du poids téléchargé par fiche, commande, section 5).
"""
from __future__ import annotations

import datetime as dt
import gzip
import hashlib
import json
import os

CONTRAT = "1.0"
IDS = ["acteur", "organe", "mandat", "scrutin", "amendement", "dossier", "document",
       "reunion", "compte_rendu", "question", "acte", "autre"]


def _json(obj) -> bytes:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), default=str).encode()


class Fiche:
    def __init__(self, ecr: "Ecrivain", type_fiche: str, adresse: str, titre: str):
        self.ecr, self.type, self.adresse, self.titre = ecr, type_fiche, adresse, titre
        self.id = f"{type_fiche}/{adresse}"
        self.dossier = f"{type_fiche}s/{adresse}"
        self.sections: dict[str, dict] = {}
        self.licences: set[str] = set()
        self.couverture: list[dict] = []
        self._entete: dict = {}

    def entete(self, donnees: dict):
        self._entete.update(donnees)

    def section(self, nom: str, lignes: list[dict], type_fait: str, ids: dict | None = None,
                date: str | None = None, source: str | None = "source_url",
                licence: str | None = "licence", couverture: dict | None = None,
                colonnes: list[str] | None = None, extra: dict | None = None):
        """Écrit `<nom>.json.gz` et inscrit ses lignes comme faits publiés.
        `ids` : {clé d'identifiant de l'export: colonne de la ligne}. Avec `type_fait=None`, la
        section est un **index** de faits inscrits par une autre section de la fiche (par exemple
        l'index léger des prises de parole, dont chaque ligne renvoie à son extrait) : ses lignes
        ne sont pas inscrites une seconde fois."""
        colonnes = colonnes or sorted({k for l in lignes for k in l})
        contenu = {"contrat": CONTRAT, "fiche": self.id, "section": nom,
                   "colonnes": colonnes, "lignes": [[l.get(c) for c in colonnes] for l in lignes],
                   "couverture": couverture or {}, **(extra or {})}
        info = self.ecr.ecrire(f"{self.dossier}/{nom}.json.gz", contenu)
        self.sections[nom] = {"fichier": f"{nom}.json.gz", "lignes": len(lignes), **info}
        if couverture:
            self.couverture.append({"section": nom, **couverture})
        for l in lignes:
            if licence and l.get(licence):
                self.licences.add(l[licence])
            if type_fait is not None:
                self.ecr.fait_publie(self, nom, type_fait, l, ids or {}, date, source)
        return info

    def fermer(self):
        contenu = {"contrat": CONTRAT, "fiche": self.id, "type": self.type, "titre": self.titre,
                   "genere_le": self.ecr.genere_le, **self._entete,
                   "sections": self.sections, "couverture": self.couverture,
                   "licences": sorted(self.licences)}
        info = self.ecr.ecrire(f"{self.dossier}/fiche.json.gz", contenu)
        self.ecr.fiches.append({"fiche": self.id, "type": self.type, "adresse": self.adresse,
                                "titre": self.titre, "entete": info,
                                "sections": {k: {"brut": v["brut"], "gz": v["gz"]}
                                             for k, v in self.sections.items()}})


class Ecrivain:
    def __init__(self, dossier: str, id_publication: str):
        self.racine = os.path.join(dossier, "donnees", id_publication)
        self.id_publication = id_publication
        os.makedirs(self.racine, exist_ok=True)
        self.genere_le = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
        self.fichiers: dict[str, dict] = {}
        self.fiches: list[dict] = []
        self.faits: list[dict] = []
        self._ouvertes: list[Fiche] = []

    def fiche(self, type_fiche: str, adresse: str, titre: str) -> Fiche:
        f = Fiche(self, type_fiche, adresse, titre)
        self._ouvertes.append(f)
        return f

    def ecrire(self, chemin: str, contenu) -> dict:
        brut = _json(contenu)
        gz = gzip.compress(brut, compresslevel=9, mtime=0)      # mtime=0 : octets reproductibles
        p = os.path.join(self.racine, chemin)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as f:
            f.write(gz)
        info = {"brut": len(brut), "gz": len(gz), "sha256": hashlib.sha256(gz).hexdigest()}
        self.fichiers[chemin] = info
        return info

    def fait_publie(self, fiche: Fiche, section, type_fait, ligne, ids, date, source):
        r = {"fiche": fiche.id, "section": section, "type_fait": type_fait}
        for k in IDS:
            col = ids.get(k)
            r[f"id_{k}"] = None if col is None or ligne.get(col) is None else str(ligne.get(col))
        r["valeur"] = _json(ligne).decode()
        r["date"] = None if not date or ligne.get(date) is None else str(ligne.get(date))
        r["source_url"] = ligne.get(source) if source else None
        self.faits.append(r)

    def clore(self) -> dict:
        for f in self._ouvertes:
            f.fermer()
        catalogue = {"contrat": CONTRAT, "publication": self.id_publication,
                     "genere_le": self.genere_le,
                     "fiches": [{k: f[k] for k in ("fiche", "type", "adresse", "titre")}
                                for f in self.fiches]}
        self.ecrire("catalogue.json.gz", catalogue)
        manifeste = {"contrat": CONTRAT, "publication": self.id_publication,
                     "genere_le": self.genere_le,
                     "fichiers": dict(sorted(self.fichiers.items())), "fiches": self.fiches}
        with open(os.path.join(self.racine, "manifeste.json"), "w") as f:
            json.dump(manifeste, f, ensure_ascii=False, indent=1)
        return manifeste

    def ecrire_faits_publies(self, chemin_parquet: str) -> int:
        import pyarrow as pa
        import pyarrow.parquet as pq
        schema = pa.schema([("fiche", pa.string()), ("section", pa.string()),
                            ("type_fait", pa.string())]
                           + [(f"id_{k}", pa.string()) for k in IDS]
                           + [("valeur", pa.string()), ("date", pa.string()),
                              ("source_url", pa.string())])
        pq.write_table(pa.Table.from_pylist(self.faits, schema=schema), chemin_parquet,
                       compression="zstd")
        return len(self.faits)


def composeurs() -> list:
    import importlib
    import pkgutil
    from . import composeurs as paquet
    out = []
    for info in pkgutil.iter_modules(paquet.__path__):
        if info.name.startswith("_"):
            continue
        m = importlib.import_module(f"{paquet.__name__}.{info.name}")
        if all(hasattr(m, a) for a in ("NOM", "VERSION", "composer")):
            out.append(m)
    return sorted(out, key=lambda m: m.NOM)
