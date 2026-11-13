"""Relevé du point `pe-eurodeputes` : les candidats anciens ou actuels députés européens, dans le
portail du Parlement européen (`data.europarl.europa.eu/api/v2/`, CC BY 4.0 ; décision Q3 du
13/11/2026).

Le portail ne dit pas qui est candidat ; Wikidata déclare l'identifiant de député européen d'une
personne (P1186). Le relevé est donc fait de trois sortes de membres, tous gardés à l'octet :

1. `wikidata-p1186` : la réponse de Wikidata à la question « quel identifiant européen (P1186),
   et quelle date de naissance (P569), pour chacun des éléments de la liste des candidats ? »
   (décisions `candidature`, tous statuts : les données d'un candidat retiré restent, cahier
   4.1). Rien n'est rapproché par le nom. La date de naissance sert au rattachement des mandats
   locaux (décision Q34) pour les candidats que la grande requête Wikidata ne couvre pas ;
2. `mep-<id>` : la fiche de chaque député européen ainsi déclaré (`meps/<id>`), avec ses
   mandats, ses groupes et ses fonctions datés ;
3. `org-<id>` : chaque groupe politique européen cité par ces fiches (`corporate-bodies/<id>`),
   pour son nom ;
4. `interventions-<id>-<rang>` : les interventions en séance de chaque député européen déclaré
   (`speeches?person-id=<id>`, par pages de 500, jusqu'à la réponse vide 204 ; décision Q37).

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
    """Adresse de la requête SPARQL : identifiant européen (P1186) et date de naissance (P569) des
    éléments, résultat trié."""
    q = ("SELECT ?item ?pe ?naissance WHERE { VALUES ?item { " + " ".join(f"wd:{e}" for e in elements)
         + " } OPTIONAL { ?item wdt:P1186 ?pe . } OPTIONAL { ?item wdt:P569 ?naissance . } }"
         + " ORDER BY ?item ?pe ?naissance")
    return f"{SPARQL}?format=json&query={urllib.parse.quote(q)}"


def identifiants_pe(octets: bytes) -> dict[str, list[str]]:
    """{élément: [identifiants européens]} lus dans la réponse SPARQL."""
    out: dict[str, list[str]] = {}
    for b in orjson.loads(octets)["results"]["bindings"]:
        if "pe" not in b:
            continue
        el = b["item"]["value"].rsplit("/", 1)[-1]
        if b["pe"]["value"] not in out.get(el, []):
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


def _obtenir_brut_poli(transport, url, dernier, pause_s, releve):
    """GET direct (un 204 de fin de pagination n'est pas une panne), au rythme du portail."""
    attente = pause_s - (time.monotonic() - dernier[0])
    if attente > 0:
        time.sleep(attente)
    code, octets = _obtenir_brut(transport, url)
    dernier[0] = time.monotonic()
    releve["octets_recus"] += len(octets)
    return code, octets


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
            # Interventions en séance (Q37) : pages de 500 jusqu'à la réponse vide (204).
            for rang in range(0, 40):
                code, o = _obtenir_brut_poli(transport, f"{PORTAIL}speeches?person-id={i}&limit=500&offset={rang * 500}&{FORMAT}",
                                             dernier, pause_s, r)
                requetes.append({"url": "speeches", "http": code})
                if code in (204, 404) or not o:
                    break
                if code != 200:
                    raise RuntimeError(f"interventions {i} : HTTP {code}")
                membres.append(_membre(f"interventions-{i}-{rang}", f"speeches/{i}-{rang}.json", o))
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


# -- Votes en séance plénière (lot 2 : portail du PE depuis juillet 2019) ----------------------

def _obtenir_brut(transport, url: str, essais: int = 3, pauses=(5, 30)) -> tuple[int, bytes]:
    """GET direct, sans le transport des archives : un 404 ou un 204 est une réponse (une séance
    sans décision, un lundi), pas une panne à réessayer pendant dix minutes. Seuls une erreur
    réseau ou un 5xx sont réessayés."""
    import requests
    dernier = None
    for k in range(essais):
        if k:
            time.sleep(pauses[min(k - 1, len(pauses) - 1)])
        try:
            r = transport.session.get(url, timeout=getattr(transport, "delai_s", 60))
        except requests.RequestException as e:
            dernier = f"{type(e).__name__}: {e}"
            continue
        if r.status_code >= 500:
            dernier = f"HTTP {r.status_code}"
            continue
        return r.status_code, r.content
    raise RuntimeError(f"{url} : {dernier}")


def seances_a_relire(seances: list[str], deja: set[str], depuis: str, aujourd_hui: str,
                     fenetre_jours: int) -> list[str]:
    """Séances plénières (`MTG-PL-AAAA-MM-JJ`) à relire : passées, depuis `depuis`, et absentes
    de l'entrepôt ou récentes (le portail complète ses décisions dans les jours qui suivent)."""
    import datetime as _dt
    borne = (_dt.date.fromisoformat(aujourd_hui) - _dt.timedelta(days=fenetre_jours)).isoformat()
    out = []
    for s in sorted(set(seances)):
        d = s[len("MTG-PL-"):][:10]
        if not (depuis <= d <= aujourd_hui):
            continue
        if f"decisions-{s}" not in deja or d >= borne:
            out.append(s)
    return out


def relever_votes(entrepot, transport, pa_cfg: dict, params: dict, pause_s: float = 2.1,
                  aujourd_hui: str | None = None, horloge=time.monotonic) -> dict:
    """Point `pe-votes` : la liste des séances plénières de chaque année depuis `depuis`
    (`seances-<année>`), puis les décisions de chaque séance (`decisions-<séance>`), gardées à
    l'octet, une réponse vide (404 ou 204 : séance sans décision) comprise. Une séance déjà rangée
    n'est relue que si elle date de moins de `fenetre_jours` jours. Au-delà de `budget_s`, le relevé
    s'arrête proprement (`complet` faux) et reprend la nuit suivante. Rangé sans retrait."""
    import datetime as _dt
    from .collecte import releve_vide
    r = releve_vide(entrepot, pa_cfg)
    depuis = str(pa_cfg.get("depuis", "2019-07-02"))
    fenetre = int(pa_cfg.get("fenetre_jours", 60))
    budget = float(pa_cfg.get("budget_s", 2400))
    aujourd_hui = aujourd_hui or _dt.datetime.now(_dt.timezone.utc).date().isoformat()
    debut = horloge()
    etat = {"requetes": 0, "erreur": None, "interrompu": False, "seances": 0, "vides": 0}
    dernier = [None]

    def obtenir(url):
        if dernier[0] is not None:
            attente = pause_s - (horloge() - dernier[0])
            if attente > 0:
                time.sleep(attente)
        code, octets = _obtenir_brut(transport, url)
        dernier[0] = horloge()
        etat["requetes"] += 1
        r["octets_recus"] += len(octets)
        return code, octets

    def membres():
        try:
            seances = []
            for an in range(int(depuis[:4]), int(aujourd_hui[:4]) + 1):
                code, o = obtenir(f"{PORTAIL}meetings?year={an}&limit=500&{FORMAT}")
                if code not in (200, 204):
                    raise RuntimeError(f"séances {an} : HTTP {code}")
                yield _membre(f"seances-{an}", f"meetings/{an}.json", o)
                d = orjson.loads(o).get("data") if o else []
                seances += [x["activity_id"] for x in (d or []) if str(x.get("activity_id", "")).startswith("MTG-PL-")]
            deja = set(entrepot.presents(pa_cfg["id"]))
            for s in seances_a_relire(seances, deja, depuis, aujourd_hui, fenetre):
                if horloge() - debut > budget:
                    etat["interrompu"] = True
                    return
                code, o = obtenir(f"{PORTAIL}meetings/{s}/decisions?{FORMAT}")
                if code not in (200, 204, 404):
                    raise RuntimeError(f"{s} : HTTP {code}")
                etat["seances"] += 1
                etat["vides"] += 0 if o else 1
                yield _membre(f"decisions-{s}", f"meetings/{s}/decisions.json", o if code == 200 else b"")
        except Exception as e:  # ce qui est déjà reçu est rangé ; le relevé est en échec
            etat["erreur"] = f"{type(e).__name__}: {e}"

    try:
        bilan = entrepot.versionner(pa_cfg, r["releve_id"], membres(), complet=True, delta=True)
        r.update(nb_membres=bilan.membres, nb_nouvelles_versions=bilan.nouvelles,
                 nb_inchanges=bilan.inchanges, nb_retraits=0, nb_reapparitions=bilan.reapparitions,
                 nb_doublons=bilan.doublons, exemples=bilan.exemples)
        msg = (f"{etat['seances']} séances relues ({etat['vides']} sans décision), "
               f"{etat['requetes']} requêtes")
        if etat["erreur"]:
            r.update(issue="echec", complet=False, message=f"{etat['erreur']} ; {msg}")
        elif etat["interrompu"]:
            r.update(issue="nouveau", complet=False, statut_http=200,
                     message=f"budget de {int(budget)} s atteint, suite la nuit prochaine ; {msg}")
        else:
            r.update(issue="nouveau", complet=True, statut_http=200, message=msg)
    except Exception as e:
        r.update(issue="echec", complet=False,
                 message=f"{type(e).__name__}: {e}\n{traceback.format_exc(limit=3)}")
    finally:
        r["requetes"] = etat["requetes"]
        r["fin"] = maintenant()
    return r
