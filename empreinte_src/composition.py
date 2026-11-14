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
  du poids téléchargé par fiche, commande, section 5) ;
- **une source en panne se voit** (doc. 2, 2.8, C5 ; commande, scénario 2) : une section dite
  `complet` dont un point d'accès n'a pas pu être relevé cette nuit passe en `panne`, avec la date
  du premier échec ; ses données restent celles du dernier relevé complet, et la publication
  continue. Le composeur n'a rien à faire : l'Ecrivain reçoit la liste des pannes.
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
    """Une fiche en cours d'écriture, ouverte par `Ecrivain.fiche`. Son identifiant est
    `<type_fiche>/<adresse>` et ses fichiers vont dans le dossier `<type_fiche>s/<adresse>`. Elle
    garde ses sections écrites, la couverture de chacune et les licences de ses faits jusqu'à
    `fermer`."""
    def __init__(self, ecr: "Ecrivain", type_fiche: str, adresse: str, titre: str):
        self.ecr, self.type, self.adresse, self.titre = ecr, type_fiche, adresse, titre
        self.id = f"{type_fiche}/{adresse}"
        self.dossier = f"{type_fiche}s/{adresse}"
        self.sections: dict[str, dict] = {}
        self.licences: set[str] = set()
        self.couverture: list[dict] = []
        self._entete: dict = {}

    def entete(self, donnees: dict):
        """Ajoute `donnees` à l'en-tête de la fiche (`fiche.json.gz`), écrit à la fermeture ; une
        clé déjà donnée est remplacée. Ne rend rien."""
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
        couverture = self.ecr.marquer_panne(couverture)
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
        """Écrit l'en-tête `fiche.json.gz` (titre, date de génération, données d'en-tête, sections
        avec leurs poids, couverture, licences) et ajoute la fiche à la liste de l'écrivain
        (`fiches`), avec le poids de l'en-tête et de chaque section. Ne rend rien."""
        contenu = {"contrat": CONTRAT, "fiche": self.id, "type": self.type, "titre": self.titre,
                   "genere_le": self.ecr.genere_le, **self._entete,
                   "sections": self.sections, "couverture": self.couverture,
                   "licences": sorted(self.licences)}
        info = self.ecr.ecrire(f"{self.dossier}/fiche.json.gz", contenu)
        self.ecr.fiches.append({"fiche": self.id, "type": self.type, "adresse": self.adresse,
                                "titre": self.titre, "entete": info,
                                "sections": {k: {"brut": v["brut"], "gz": v["gz"], "lignes": v["lignes"]}
                                             for k, v in self.sections.items()}})


def _schema_faits():
    import pyarrow as pa
    return pa.schema([("fiche", pa.string()), ("section", pa.string()), ("type_fait", pa.string())]
                     + [(f"id_{k}", pa.string()) for k in IDS]
                     + [("valeur", pa.string()), ("date", pa.string()), ("source_url", pa.string())])


class Ecrivain:
    """Écrit les fichiers servis et inscrit chaque fait publié.

    Avec `chemin_faits`, les faits publiés sont écrits **au fil de l'eau** dans ce Parquet, par lots
    de `lot_faits` lignes : la mémoire ne garde qu'un lot (≈ 2 millions de faits sur le périmètre
    complet). Sans lui, ils restent dans `faits` (tests) jusqu'à `ecrire_faits_publies`."""

    def __init__(self, dossier: str, id_publication: str, pannes: dict[str, str] | None = None,
                 chemin_faits: str | None = None, lot_faits: int = 50_000,
                 releves_reussis: dict[str, str | None] | None = None):
        self.racine = os.path.join(dossier, "donnees", id_publication)
        self.id_publication = id_publication
        os.makedirs(self.racine, exist_ok=True)
        self.genere_le = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
        self.fichiers: dict[str, dict] = {}
        self.fiches: list[dict] = []
        # adresses citées par des articles publiés → fiche (composeur `adresses`, issue #86)
        self.adresses_citees: list[dict] = []
        self.faits: list[dict] = []          # lot en cours (tout, sans `chemin_faits`)
        self.nb_faits = 0
        self.chemin_faits, self.lot_faits, self._writer = chemin_faits, lot_faits, None
        self._ouvertes: list[Fiche] = []
        # {point d'accès en panne cette nuit: date du premier échec depuis le dernier relevé réussi}
        self.pannes = dict(pannes or {})
        # {point d'accès en panne: date du dernier relevé complet réussi, ou None s'il n'y en a
        # jamais eu} ; un point absent : inconnu (issue #33).
        self.reussis = dict(releves_reussis or {})

    def marquer_panne(self, couverture: dict | None) -> dict | None:
        """Une couverture « complet » dont une source est en panne devient « panne », datée."""
        if not couverture or couverture.get("statut") not in ("complet", "partiel") or not self.pannes:
            return couverture
        touches = sorted(set(couverture.get("points_acces") or []) & set(self.pannes))
        if not touches:
            return couverture
        depuis = min((self.pannes[p] for p in touches if self.pannes[p]), default=None)
        # Un point qui n'a jamais été relevé avec succès n'a pas de « dernier relevé complet » : ses
        # données manquent, la section ne doit pas laisser croire qu'elle les montre (issue #33).
        jamais = [p for p in touches if p in self.reussis and not self.reussis[p]]
        autres = [p for p in touches if p not in jamais]
        dates = [self.reussis[p] for p in autres if self.reussis.get(p)]
        suites = []
        if jamais:
            suites.append("aucun relevé n'a encore abouti pour " + ", ".join(jamais) + " : "
                          + ("ses" if len(jamais) == 1 else "leurs") + " données manquent ici")
        if autres:
            suites.append((f"pour {', '.join(autres)}, " if jamais else "")
                          + "données du dernier relevé complet"
                          + (f", du {min(dates)[:10]}" if len(dates) == len(autres) else ""))
        c = dict(couverture)
        c.update({"statut": "panne", "statut_sans_panne": c["statut"], "points_en_panne": touches,
                  "panne_depuis": depuis,
                  "dernier_releve_reussi": {p: (self.reussis[p] or None) for p in touches if p in self.reussis},
                  "detail": (c.get("detail") or "") + (" " if c.get("detail") else "")
                  + f"Source en panne{' depuis le ' + depuis[:10] if depuis else ''} ("
                  + ", ".join(touches) + ") : " + " ; ".join(suites) + "."})
        return c

    def citer(self, adresse: str, lien: str | None, decision: str | None, raison: str | None = None):
        """Inscrit une adresse citée par un article publié et la fiche où elle mène (`lien`,
        `<type>/<adresse>`), ou `None` et sa `raison` ; servie dans le catalogue (issue #86)."""
        self.adresses_citees.append({"adresse": adresse, "lien": lien, "decision": decision,
                                     "raison": raison})

    def fiche(self, type_fiche: str, adresse: str, titre: str) -> Fiche:
        """Ouvre et rend une nouvelle `Fiche` ; elle sera fermée par `clore`."""
        f = Fiche(self, type_fiche, adresse, titre)
        self._ouvertes.append(f)
        return f

    def ecrire(self, chemin: str, contenu) -> dict:
        """Écrit `contenu` en JSON compact, compressé en gzip (octets reproductibles), au chemin
        `chemin` sous le dossier de la publication. Rend `{"brut", "gz", "sha256"}` (tailles avant
        et après compression, empreinte du fichier compressé) et le garde pour le manifeste."""
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
        """Inscrit la ligne affichée `ligne` comme fait publié de la section `section` de `fiche` :
        type, identifiants (`ids`, `{clé de l'export: colonne}`), valeur (la ligne en JSON), date
        (colonne `date`) et source (colonne `source`). Avec `chemin_faits`, le lot est écrit dès
        qu'il atteint `lot_faits` lignes. Ne rend rien."""
        r = {"fiche": fiche.id, "section": section, "type_fait": type_fait}
        for k in IDS:
            col = ids.get(k)
            r[f"id_{k}"] = None if col is None or ligne.get(col) is None else str(ligne.get(col))
        r["valeur"] = _json(ligne).decode()
        r["date"] = None if not date or ligne.get(date) is None else str(ligne.get(date))
        r["source_url"] = ligne.get(source) if source else None
        self.faits.append(r)
        self.nb_faits += 1
        if self.chemin_faits and len(self.faits) >= self.lot_faits:
            self._vider_faits()

    def _vider_faits(self):
        import pyarrow as pa
        import pyarrow.parquet as pq
        if self._writer is None:
            os.makedirs(os.path.dirname(self.chemin_faits) or ".", exist_ok=True)
            self._writer = pq.ParquetWriter(self.chemin_faits, _schema_faits(), compression="zstd")
        if self.faits:
            self._writer.write_table(pa.Table.from_pylist(self.faits, schema=_schema_faits()))
        self.faits = []

    def clore(self) -> dict:
        """Ferme les fiches encore ouvertes, écrit le catalogue des fiches (`catalogue.json.gz`) et
        le manifeste de la publication (`manifeste.json` : chaque fichier avec ses poids et son
        empreinte, chaque fiche). Rend le manifeste."""
        for f in self._ouvertes:
            f.fermer()
        catalogue = {"contrat": CONTRAT, "publication": self.id_publication,
                     "genere_le": self.genere_le,
                     "fiches": [{k: f[k] for k in ("fiche", "type", "adresse", "titre")}
                                for f in self.fiches]}
        if self.adresses_citees:
            # Une cible qui n'est pas une fiche publiée cette nuit n'est jamais servie comme lien.
            publiees = {f["fiche"] for f in self.fiches}
            lignes = []
            for a in sorted(self.adresses_citees, key=lambda a: a["adresse"] or ""):
                lien, raison = a["lien"], a["raison"]
                if lien is not None and lien not in publiees:
                    lien, raison = None, f"la fiche {a['lien']} n'est pas publiée"
                lignes.append([a["adresse"], lien, raison, a["decision"]])
            catalogue["adresses_citees"] = {"colonnes": ["adresse", "lien", "raison", "decision"],
                                            "lignes": lignes}
        self.ecrire("catalogue.json.gz", catalogue)
        manifeste = {"contrat": CONTRAT, "publication": self.id_publication,
                     "genere_le": self.genere_le,
                     "fichiers": dict(sorted(self.fichiers.items())), "fiches": self.fiches}
        with open(os.path.join(self.racine, "manifeste.json"), "w") as f:
            json.dump(manifeste, f, ensure_ascii=False, indent=1)
        return manifeste

    def ecrire_faits_publies(self, chemin_parquet: str | None = None) -> int:
        """Achève le fichier des faits publiés et rend leur nombre. Écrit au fil de l'eau : vide le
        dernier lot et ferme le fichier. Sinon : écrit tous les faits gardés à `chemin_parquet`."""
        import pyarrow as pa
        import pyarrow.parquet as pq
        if self.chemin_faits:
            if chemin_parquet and os.path.abspath(chemin_parquet) != os.path.abspath(self.chemin_faits):
                raise ValueError("faits publiés déjà écrits dans " + self.chemin_faits)
            self._vider_faits()
            self._writer.close()
            self._writer = None
            return self.nb_faits
        pq.write_table(pa.Table.from_pylist(self.faits, schema=_schema_faits()), chemin_parquet,
                       compression="zstd")
        return len(self.faits)


def composeurs() -> list:
    """Rend les modules du paquet `composeurs` (sauf ceux dont le nom commence par `_`) qui
    déclarent `NOM`, `VERSION` et `composer`, triés par `NOM`."""
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
