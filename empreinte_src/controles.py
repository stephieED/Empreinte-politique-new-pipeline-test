"""Étape E6 — Contrôler (doc. 2, 2.8).

Contrôles **bloquants** : si l'un d'eux trouve une anomalie, la publication est refusée (la
tâche `ecrire` écrit alors l'acquis, et rien d'autre). Chaque anomalie a une **empreinte**
(contrôle + objets concernés) ; une décision `levee_controle` dont le champ `empreinte` est
égal à celle de l'anomalie la lève, pour cette anomalie seulement : si l'anomalie change, la
levée ne vaut plus (doc. 3, J16).

Contrôles réalisés dans cette tranche : C1 (pertes non expliquées), C2 (liens pendants), C4
(données interdites), C5 (lecture incomplète présentée comme complète), C6 (effondrement).
C3 et C7 restent à faire (voir le journal de l'étape 2).
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import re

import duckdb

# Clés et motifs interdits dans un fichier servi (cahier, partie 2 et 2.1).
CLES_INTERDITES = re.compile(
    r"(taux_?de_?presence|presence|participation_individuelle|score|classement|rang_personne|"
    r"cohesion|nb_divergences|total_divergences|taux_adoption|part_appliquant|indice_)", re.I)
VALEURS_49_3_INTERDITES = {"49.3", "49-3", "art.49.3"}     # jamais une position de vote


def _empreinte(controle: str, objets) -> str:
    h = hashlib.sha256((controle + "|" + "|".join(sorted(map(str, objets)))).encode()).hexdigest()
    return f"{controle}:{h[:16]}"


class Controles:
    def __init__(self, racine_publication: str, levees: list[dict] | None = None):
        self.racine = racine_publication
        self.levees = {l.get("empreinte"): l for l in (levees or []) if l.get("empreinte")}
        self.anomalies: list[dict] = []

    def _signaler(self, controle, titre, objets, bloquant=True, detail=None):
        e = _empreinte(controle, objets)
        levee = self.levees.get(e)
        self.anomalies.append({"controle": controle, "titre": titre, "empreinte": e,
                               "bloquant": bloquant and levee is None,
                               "levee_par": (levee or {}).get("fichier"),
                               "nb_objets": len(objets), "exemples": sorted(map(str, objets))[:10],
                               "detail": detail})

    # -- lecture des fichiers servis -----------------------------------------------------
    def _fichiers(self):
        for racine, _, noms in os.walk(self.racine):
            for n in noms:
                if n.endswith(".json.gz"):
                    p = os.path.join(racine, n)
                    with gzip.open(p) as f:
                        yield os.path.relpath(p, self.racine), json.load(f)

    # -- C2 : liens pendants -------------------------------------------------------------
    def c2_liens(self, fiches_publiees: set[str]):
        pendants = []
        for chemin, contenu in self._fichiers():
            for cible in _liens(contenu):
                if cible not in fiches_publiees:
                    pendants.append(f"{chemin} -> {cible}")
        if pendants:
            self._signaler("C2", "Liens vers une fiche absente", pendants)

    # -- C4 : données interdites -----------------------------------------------------------
    def c4_interdits(self):
        trouves = []
        for chemin, contenu in self._fichiers():
            for cle in _cles(contenu):
                if CLES_INTERDITES.search(cle):
                    trouves.append(f"{chemin}: clé « {cle} »")
            if contenu.get("section") and "colonnes" in contenu:
                cols = contenu["colonnes"]
                if "position" in cols:
                    i = cols.index("position")
                    for l in contenu["lignes"]:
                        if str(l[i]).lower() in VALEURS_49_3_INTERDITES:
                            trouves.append(f"{chemin}: 49.3 présenté comme une position de vote")
                for c in cols:
                    if c.startswith("ratio") or c.startswith("taux"):
                        trouves.append(f"{chemin}: ratio servi tout fait (« {c} »)")
        if trouves:
            self._signaler("C4", "Données interdites dans les fichiers servis", trouves)

    # -- C5 : lecture incomplète présentée comme complète --------------------------------
    def c5_couverture(self, releves: list[dict]):
        """Une section dite complète pour une source dont le dernier relevé a échoué."""
        en_panne = {r["point_acces"] for r in releves if r.get("issue") in ("echec", "suspect")}
        fautives = []
        for chemin, contenu in self._fichiers():
            c = contenu.get("couverture") or {}
            # Une section porte un dictionnaire ; l'en-tête d'une fiche, la liste de ses sections.
            for x in (c if isinstance(c, list) else [c]):
                if (isinstance(x, dict) and x.get("statut") == "complet"
                        and set(x.get("points_acces") or []) & en_panne):
                    fautives.append(f"{chemin} ({x.get('section', 'section')})")
        if fautives:
            self._signaler("C5", "Section dite complète alors qu'une de ses sources est en panne", fautives)

    # -- C1 et C6 : comparaison avec la publication précédente ----------------------------
    def c1_c6_comparer(self, faits_avant: str | None, faits_apres: str,
                       uids_changes_a_la_source: set[str] | None = None, seuil_effondrement=0.2):
        if not faits_avant or not os.path.exists(faits_avant):
            return
        con = duckdb.connect()
        perdus = con.execute(f"""
            SELECT a.fiche, a.section, a.type_fait, a.valeur FROM read_parquet('{faits_avant}') a
            ANTI JOIN read_parquet('{faits_apres}') b
              ON a.fiche = b.fiche AND a.section = b.section AND a.valeur = b.valeur""").fetchall()
        # Un fait qui disparaît parce que sa source a changé ou l'a retiré est expliqué : sa
        # valeur cite l'identifiant d'un fichier source modifié ou retiré cette nuit.
        non_expliques = [p for p in perdus
                         if not (uids_changes_a_la_source and _touche(p[3], uids_changes_a_la_source))]
        if non_expliques:
            self._signaler("C1", "Faits publiés perdus sans explication",
                           [f"{p[0]} / {p[1]} / {p[2]}: {p[3][:120]}" for p in non_expliques])
        # C6 : une section qui tombe à zéro ou baisse fortement d'un coup.
        avant = dict(((f, s), n) for f, s, n in con.execute(
            f"SELECT fiche, section, count(*) FROM read_parquet('{faits_avant}') GROUP BY 1, 2").fetchall())
        apres = dict(((f, s), n) for f, s, n in con.execute(
            f"SELECT fiche, section, count(*) FROM read_parquet('{faits_apres}') GROUP BY 1, 2").fetchall())
        chutes = [f"{f}/{s}: {n} → {apres.get((f, s), 0)}" for (f, s), n in avant.items()
                  if n >= 10 and apres.get((f, s), 0) < n * (1 - seuil_effondrement)]
        if chutes:
            self._signaler("C6", "Effondrement d'une section", chutes)
        con.close()

    def bilan(self) -> dict:
        bloquantes = [a for a in self.anomalies if a["bloquant"]]
        return {"publication_autorisee": not bloquantes, "anomalies": self.anomalies,
                "bloquantes": [a["empreinte"] for a in bloquantes]}


def _touche(valeur_json: str, uids: set[str]) -> bool:
    return any(u in valeur_json for u in uids)


def _cles(obj, prefixe=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from _cles(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _cles(v)
    if isinstance(obj, dict) and isinstance(obj.get("colonnes"), list):
        yield from obj["colonnes"]


def _liens(obj):
    """Les liens vers d'autres fiches s'écrivent {"lien": "legislature/17"} dans les fichiers servis."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "lien" and isinstance(v, str):
                yield v
            else:
                yield from _liens(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _liens(v)
    if isinstance(obj, dict) and isinstance(obj.get("colonnes"), list) and "lien" in obj["colonnes"]:
        i = obj["colonnes"].index("lien")
        for l in obj.get("lignes", []):
            if isinstance(l[i], str):
                yield l[i]
