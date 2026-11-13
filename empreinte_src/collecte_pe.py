"""Relevé du point `pe-eurodeputes` : les candidats anciens ou actuels députés européens, dans le
portail du Parlement européen (`data.europarl.europa.eu/api/v2/`, CC BY 4.0 ; décision Q3 du
13/11/2026).

Le portail ne dit pas qui est candidat ; Wikidata déclare l'identifiant de député européen d'une
personne (P1186). Le relevé est donc fait de trois sortes de membres, tous gardés à l'octet :

1. `wikidata-p1186` : la réponse de Wikidata à la question « quel identifiant européen pour
   chacun des éléments de la liste des candidats ? » (décisions `candidature`, tous statuts :
   les données d'un candidat retiré restent, cahier 4.1). Rien n'est rapproché par le nom ;
2. `mep-<id>` : la fiche de chaque député européen ainsi déclaré (`meps/<id>`), avec ses
   mandats, ses groupes et ses fonctions datés ;
3. `org-<id>` : chaque groupe politique européen cité par ces fiches (`corporate-bodies/<id>`),
   pour son nom.

Le portail ne publie ni `ETag` ni `Last-Modified` (mesuré le 04/11/2026) : chaque nuit relit tout,
et l'entrepôt ne garde une version nouvelle que si les octets changent. Une requête toutes les
2,1 s (`Crawl-delay: 2` du `robots.txt` du portail). Une seule réponse en échec fait échouer le
relevé entier : rien n'est rangé, la panne se voit, les données du relevé précédent restent. Un
député européen qui sort de la liste n'est jamais « retiré » : le relevé est rangé sans retrait
(ses données restent, cahier 4.1).
"""
from __future__ import annotations

import glob
import os
import time
import traceback
import urllib.parse

import orjson
import yaml

from .depaquetage import _membre
from .entrepot import maintenant

PORTAIL = "https://data.europarl.europa.eu/api/v2/"
SPARQL = "https://query.wikidata.org/sparql"
FORMAT = "format=application%2Fld%2Bjson"
CLASSE_GROUPE = "def/ep-entities/EU_POLITICAL_GROUP"


def elements_de_la_liste(dossier_decisions: str) -> list[str]:
    """Les éléments Wikidata de toutes les décisions `candidature`, tous statuts, triés."""
    qs = set()
    for p in glob.glob(os.path.join(dossier_decisions, "candidature", "*.yaml")):
        with open(p) as f:
            d = yaml.safe_load(f) or {}
        for e in d.get("decisions") or []:
            q = (e.get("wikidata") or "").strip()
            if q.startswith("Q") and q[1:].isdigit():
                qs.add(q)
    return sorted(qs, key=lambda q: int(q[1:]))


def requete_p1186(elements: list[str]) -> str:
    """Adresse de la requête SPARQL : identifiant européen (P1186) des éléments, résultat trié."""
    q = ("SELECT ?item ?pe WHERE { VALUES ?item { " + " ".join(f"wd:{e}" for e in elements)
         + " } ?item wdt:P1186 ?pe . } ORDER BY ?item ?pe")
    return f"{SPARQL}?format=json&query={urllib.parse.quote(q)}"


def identifiants_pe(octets: bytes) -> dict[str, list[str]]:
    """{élément: [identifiants européens]} lus dans la réponse SPARQL."""
    out: dict[str, list[str]] = {}
    for b in orjson.loads(octets)["results"]["bindings"]:
        el = b["item"]["value"].rsplit("/", 1)[-1]
        out.setdefault(el, []).append(b["pe"]["value"])
    return out


def groupes_cites(octets: bytes) -> list[str]:
    """Identifiants des groupes politiques européens cités par une fiche `meps/<id>`."""
    d = orjson.loads(octets).get("data")
    personnes = d if isinstance(d, list) else [d]
    out = set()
    for p in personnes:
        for h in (p or {}).get("hasMembership") or []:
            if h.get("membershipClassification") == CLASSE_GROUPE and str(h.get("organization", "")).startswith("org/"):
                out.add(h["organization"].split("/", 1)[1])
    return sorted(out, key=lambda x: (len(x), x))


def relever_eurodeputes(entrepot, transport, pa_cfg: dict, params: dict,
                        dossier_decisions: str | None = None, pause_s: float = 2.1) -> dict:
    from .collecte import releve_vide
    r = releve_vide(entrepot, pa_cfg)
    r["url"] = pa_cfg.get("url", PORTAIL)
    membres, requetes = [], []
    dernier = [0.0]

    def obtenir(url: str, portail: bool) -> bytes:
        if portail:
            attente = pause_s - (time.monotonic() - dernier[0])
            if attente > 0:
                time.sleep(attente)
        rep = transport.telecharger(url)
        if portail:
            dernier[0] = time.monotonic()
        requetes.append({"url": url, "http": rep.statut_http, "issue": rep.issue})
        r["octets_recus"] += rep.octets_recus
        try:
            if rep.issue != "nouveau":
                raise RuntimeError(f"{url} : {rep.issue} ({rep.message})")
            with open(rep.chemin, "rb") as f:
                return f.read()
        finally:
            if rep.chemin and os.path.exists(rep.chemin):
                os.unlink(rep.chemin)

    try:
        dossier = dossier_decisions or pa_cfg.get("decisions") or "decisions"
        elements = elements_de_la_liste(dossier)
        if not elements:
            raise RuntimeError(f"aucun élément Wikidata dans les décisions `candidature` de {dossier}")
        o = obtenir(requete_p1186(elements), portail=False)
        membres.append(_membre("wikidata-p1186", "wikidata-p1186.json", o))
        ids = sorted({i for v in identifiants_pe(o).values() for i in v}, key=lambda x: (len(x), x))
        groupes = set()
        for i in ids:
            o = obtenir(f"{PORTAIL}meps/{i}?{FORMAT}", portail=True)
            membres.append(_membre(f"mep-{i}", f"meps/{i}.json", o))
            groupes.update(groupes_cites(o))
        for g in sorted(groupes, key=lambda x: (len(x), x)):
            o = obtenir(f"{PORTAIL}corporate-bodies/{g}?{FORMAT}&language=fr", portail=True)
            membres.append(_membre(f"org-{g}", f"corporate-bodies/{g}.json", o))
        # Rangé sans retrait (delta) : un député européen qui sort de la liste garde ses données.
        bilan = entrepot.versionner(pa_cfg, r["releve_id"], membres, complet=True, delta=True)
        r.update(issue="nouveau", complet=True, statut_http=200, nb_membres=bilan.membres,
                 nb_nouvelles_versions=bilan.nouvelles, nb_inchanges=bilan.inchanges,
                 nb_retraits=0, nb_reapparitions=bilan.reapparitions, nb_doublons=bilan.doublons,
                 exemples=bilan.exemples,
                 message=f"{len(elements)} éléments, {len(ids)} députés européens, {len(groupes)} groupes")
    except Exception as e:  # un point d'accès qui casse n'arrête pas les autres
        r.update(issue="echec", complet=False,
                 message=f"{type(e).__name__}: {e}\n{traceback.format_exc(limit=3)}")
    finally:
        r["requetes"] = len(requetes)
        r["fin"] = maintenant()
    return r
