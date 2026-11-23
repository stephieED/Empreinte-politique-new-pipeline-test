"""Relevé du point `wd-fonctions-candidats` : les fonctions (P39) que Wikidata déclare pour les
éléments de la liste des candidats (décision Q52 du 23/11/2026 : « Ajouter Wikidata P39
maintenant » ; les mandats locaux passés, que le Répertoire national des élus ne publie pas).

Un seul membre, `wikidata-p39` : la réponse de Wikidata (CC0) à « quelles déclarations P39,
avec leur début (P580), leur fin (P582), leur ressort (P1001) et leur objet (P642), pour chacun
des éléments de la liste ? », libellés en français. La réponse est gardée sous sa forme
canonique (clés triées, lignes sans doublon : exception à P2 décidée pour Wikidata, Q40), pour
qu'une nuit sans changement ne fasse pas de version nouvelle. Toutes les fonctions sont gardées ;
c'est la règle R-MANDAT-LOCAL qui retient les fonctions locales.

Un échec (HTTP autre que 200, réponse illisible) fait échouer le relevé : rien n'est rangé, la
panne se voit, et la nuit suivante réessaie. Rangé sans retrait (un candidat qui sort de la liste
garde ses données).
"""
from __future__ import annotations

import traceback
import urllib.parse

import orjson

from .collecte_pe import SPARQL, elements_de_la_liste
from .depaquetage import _membre, canoniser_json
from .entrepot import maintenant


def requete_p39(elements: list[str]) -> str:
    """L'adresse de la requête SPARQL pour les éléments `elements` (triée, donc stable)."""
    q = ("SELECT ?item ?st ?pos ?posLabel ?debut ?fin ?jurLabel ?ofLabel WHERE { VALUES ?item { "
         + " ".join(f"wd:{e}" for e in elements)
         + " } ?item p:P39 ?st . ?st ps:P39 ?pos . "
           "OPTIONAL { ?st pq:P580 ?debut . } OPTIONAL { ?st pq:P582 ?fin . } "
           "OPTIONAL { ?st pq:P1001 ?jur . } OPTIONAL { ?st pq:P642 ?of . } "
           "SERVICE wikibase:label { bd:serviceParam wikibase:language \"fr,en\". } } "
           "ORDER BY ?item ?st ?debut ?fin ?jurLabel ?ofLabel")
    return f"{SPARQL}?format=json&query={urllib.parse.quote(q)}"


def relever_fonctions(entrepot, transport, pa_cfg: dict, params: dict,
                      dossier_decisions: str | None = None) -> dict:
    from .collecte import releve_vide
    from .collecte_pe import _obtenir_brut
    r = releve_vide(entrepot, pa_cfg)
    try:
        dossier = dossier_decisions or pa_cfg.get("references") or "references"
        elements = elements_de_la_liste(dossier)
        if not elements:
            raise RuntimeError(f"aucun élément Wikidata dans les décisions `candidature` de {dossier}")
        code, octets = _obtenir_brut(transport, requete_p39(elements))
        r["octets_recus"] += len(octets)
        if code != 200:
            raise RuntimeError(f"Wikidata : HTTP {code}")
        n = len(orjson.loads(octets)["results"]["bindings"])          # réponse lisible, sinon échec
        m = canoniser_json(_membre("wikidata-p39", "wikidata-p39.json", octets))
        bilan = entrepot.versionner(pa_cfg, r["releve_id"], [m], complet=True, delta=True)
        r.update(issue="nouveau", complet=True, statut_http=200, nb_membres=bilan.membres,
                 nb_nouvelles_versions=bilan.nouvelles, nb_inchanges=bilan.inchanges, nb_retraits=0,
                 nb_reapparitions=bilan.reapparitions, nb_doublons=bilan.doublons, exemples=bilan.exemples,
                 message=f"{len(elements)} éléments, {n} lignes P39")
    except Exception as e:
        r.update(issue="echec", complet=False,
                 message=f"{type(e).__name__}: {e}\n{traceback.format_exc(limit=3)}")
    finally:
        r["fin"] = maintenant()
    return r
