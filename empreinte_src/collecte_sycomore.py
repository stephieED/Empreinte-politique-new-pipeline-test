"""Relevé du point `sycomore-fiches` : les mandats de député antérieurs à 2002 des candidats
(cahier 3.11 et 4.2 ; décision Q36 du 13/11/2026 : « Oui, les faits seulement »).

Sycomore (`www2.assemblee-nationale.fr/sycomore/fiche?num_dept=<id>`) est « tous droits
réservés » : seuls des **faits** peuvent en être repris (cahier 2.2 ; doc. 1, 1.7.4). Le relevé
ne garde donc **pas la page** : il en extrait les faits au moment du relevé (nom, et pour chaque
mandat : chambre, régime, législature, dates, département, groupe) et range ces faits en JSON,
avec l'adresse de la fiche et la version de l'extracteur. Conséquence assumée : une erreur
d'extraction ne se corrige qu'en relevant de nouveau la fiche (correction P2 impossible ici,
faute de droit de garder la page).

Membres :

1. `wikidata-p1045` : la réponse de Wikidata (CC0) à « quel identifiant Sycomore (P1045) pour
   chacun des éléments de la liste des candidats ? », gardée à l'octet ;
2. `sycomore-<id>` : les faits d'une fiche (JSON écrit par le relevé).

Une requête toutes les 2,1 s. Pas de `robots.txt` sur www2.assemblee-nationale.fr (404, mesuré
le 13/11/2026). Une fiche en échec fait échouer le relevé (rien n'est rangé, la panne se voit).
Rangé sans retrait (un candidat qui sort de la liste garde ses données).
"""
from __future__ import annotations

import html
import re
import time
import traceback
import urllib.parse

import orjson

from .collecte_pe import SPARQL, elements_de_la_liste
from .depaquetage import _membre
from .entrepot import maintenant

FICHE = "https://www2.assemblee-nationale.fr/sycomore/fiche?num_dept="
EXTRACTEUR = "sycomore@1"
MOIS = {m: i for i, m in enumerate(
    ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre",
     "octobre", "novembre", "décembre"], 1)}
_DATE = re.compile(r"(\d{1,2})(?:er)?\s+(" + "|".join(MOIS) + r")\s+(\d{4})", re.I)


def requete_p1045(elements: list[str]) -> str:
    q = ("SELECT ?item ?sycomore WHERE { VALUES ?item { " + " ".join(f"wd:{e}" for e in elements)
         + " } ?item wdt:P1045 ?sycomore . } ORDER BY ?item ?sycomore")
    return f"{SPARQL}?format=json&query={urllib.parse.quote(q)}"


def date_iso(texte: str) -> str | None:
    m = _DATE.search(texte or "")
    if not m:
        return None
    j, mois, a = m.groups()
    return f"{a}-{MOIS[mois.lower()]:02d}-{int(j):02d}"


def _texte(fragment: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def faits_sycomore(page: str, num: str) -> dict:
    """Les faits d'une fiche : nom (`h1`) et mandats (chaque `dl` qui suit un `h2` « Mandats à
    l'Assemblée… » ou « Mandats au Sénat… »). Rien d'autre de la page n'est gardé."""
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", page, re.S)
    out = {"num_dept": num, "url": FICHE + num, "extracteur": EXTRACTEUR,
           "nom": _texte(h1.group(1)) if h1 else None, "mandats": []}
    sections = list(re.finditer(r"<h2[^>]*>(.*?)</h2>", page, re.S))
    for k, s in enumerate(sections):
        titre = _texte(s.group(1)).lower()
        chambre = ("assemblee" if "assemblée" in titre or "chambre des députés" in titre
                   else "senat" if "sénat" in titre or "pairs" in titre else None)
        if not chambre:
            continue
        fin = sections[k + 1].start() if k + 1 < len(sections) else len(page)
        for dl in re.finditer(r"<dl[^>]*>(.*?)</dl>", page[s.end():fin], re.S):
            paires = re.findall(r"<dt[^>]*>(.*?)</dt>\s*<dd[^>]*>(.*?)</dd>", dl.group(1), re.S)
            d = {_texte(a).lower(): _texte(b) for a, b in paires}
            mandat = d.get("mandat") or ""
            morceaux = re.split(r"\bau\b", mandat, maxsplit=1, flags=re.I)
            out["mandats"].append({
                "chambre": chambre, "regime": d.get("régime politique"),
                "legislature": d.get("législature"), "mandat": mandat or None,
                "debut": date_iso(morceaux[0]), "fin": date_iso(morceaux[1]) if len(morceaux) > 1 else None,
                "departement": d.get("département"), "groupe": d.get("groupe")})
    return out


def relever_sycomore(entrepot, transport, pa_cfg: dict, params: dict, dossier_decisions: str | None = None,
                     pause_s: float = 2.1) -> dict:
    from .collecte import releve_vide
    from .collecte_pe import _obtenir_brut
    r = releve_vide(entrepot, pa_cfg)
    membres, n = [], 0
    dernier = [None]

    def obtenir(url, poli=True):
        if poli and dernier[0] is not None:
            attente = pause_s - (time.monotonic() - dernier[0])
            if attente > 0:
                time.sleep(attente)
        code, octets = _obtenir_brut(transport, url)
        if poli:
            dernier[0] = time.monotonic()
        r["octets_recus"] += len(octets)
        if code != 200:
            raise RuntimeError(f"{url} : HTTP {code}")
        return octets

    try:
        dossier = dossier_decisions or pa_cfg.get("decisions") or "decisions"
        elements = elements_de_la_liste(dossier)
        if not elements:
            raise RuntimeError(f"aucun élément Wikidata dans les décisions `candidature` de {dossier}")
        o = obtenir(requete_p1045(elements), poli=False)
        membres.append(_membre("wikidata-p1045", "wikidata-p1045.json", o))
        ids = sorted({b["sycomore"]["value"] for b in orjson.loads(o)["results"]["bindings"]},
                     key=lambda x: (len(x), x))
        for i in ids:
            page = obtenir(FICHE + i).decode("utf-8", errors="replace")
            faits = faits_sycomore(page, i)
            if not faits["nom"]:
                raise RuntimeError(f"fiche Sycomore {i} : nom introuvable (page changée ?)")
            membres.append(_membre(f"sycomore-{i}", f"sycomore/{i}.json",
                                   orjson.dumps(faits, option=orjson.OPT_SORT_KEYS | orjson.OPT_INDENT_2)))
            n += 1
        bilan = entrepot.versionner(pa_cfg, r["releve_id"], membres, complet=True, delta=True)
        r.update(issue="nouveau", complet=True, statut_http=200, nb_membres=bilan.membres,
                 nb_nouvelles_versions=bilan.nouvelles, nb_inchanges=bilan.inchanges, nb_retraits=0,
                 nb_reapparitions=bilan.reapparitions, nb_doublons=bilan.doublons, exemples=bilan.exemples,
                 message=f"{len(elements)} éléments, {n} fiches Sycomore (faits seulement)")
    except Exception as e:
        r.update(issue="echec", complet=False,
                 message=f"{type(e).__name__}: {e}\n{traceback.format_exc(limit=3)}")
    finally:
        r["fin"] = maintenant()
    return r
