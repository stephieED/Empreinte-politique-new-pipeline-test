"""Parlement européen : les candidats députés européens, d'après le portail du PE (point
`pe-eurodeputes`, `empreinte_src/collecte_pe.py` ; CC BY 4.0 ; décision Q3 du 13/11/2026).

Trois sortes de membres :

- `wikidata-p1186` : réponse SPARQL, une ligne par (élément Wikidata, identifiant européen) →
  table `identifiant_pe`, et par (élément, date de naissance) → `naissance_wikidata` ;
- `mep-<id>` : fiche d'un député européen (`meps/<id>`) → `eurodepute` (identité telle que
  publiée) et `appartenance_pe` (une ligne par appartenance datée : mandat de député européen
  `MEMBER_PARLIAMENT` dans `org/ep-<n>`, groupe politique, commission, délégation, parti
  national…, avec le rôle). Le portail publie `data` en liste d'un élément, parfois en objet
  (cahier 3.3) : les deux sont lus ;
- `org-<id>` : un groupe politique européen (`corporate-bodies/<id>`) → `groupe_pe` (sigle, nom
  français, période de l'organe).

Les dates sont gardées telles que publiées (`AAAA-MM-JJ`). Rien n'est déduit ici : le choix des
périodes de la frise est celui de R-CARRIERE.
"""
import orjson
import pyarrow as pa

NOM = "pe_eurodeputes"
VERSION = 3
TYPES = ("eurodeputes_pe",)
S = pa.string()
TABLES = {
    "identifiant_pe": pa.schema([("element", S), ("identifiant", S)]),
    "naissance_wikidata": pa.schema([("element", S), ("naissance", S)]),
    "intervention_pe": pa.schema([
        ("personne", S), ("intervention", S), ("date", S), ("heure", S), ("debat", S), ("compte_rendu", S),
        ("point", S)]),
    "eurodepute": pa.schema([
        ("personne", S), ("libelle", S), ("prenom", S), ("nom", S), ("naissance", S),
        ("lieu_naissance", S), ("nationalite", S), ("genre", S)]),
    "appartenance_pe": pa.schema([
        ("personne", S), ("appartenance", S), ("organisation", S), ("classification", S),
        ("role", S), ("debut", S), ("fin", S), ("represente", S)]),
    "groupe_pe": pa.schema([
        ("organisation", S), ("sigle", S), ("libelle", S), ("libelle_court", S),
        ("version_de", S), ("debut", S), ("fin", S), ("classification", S)]),
}
URL_PERSONNE = "https://www.europarl.europa.eu/meps/fr/"


def _donnees(octets) -> list[dict]:
    d = orjson.loads(octets).get("data")
    return [x for x in (d if isinstance(d, list) else [d]) if isinstance(x, dict)]


def _suffixe(v):
    return v.rsplit("/", 1)[-1] if isinstance(v, str) else None


def lire(m):
    out = {t: [] for t in TABLES}
    if m.uid == "wikidata-p1186":
        vus = set()
        for b in orjson.loads(m.octets)["results"]["bindings"]:
            el = b["item"]["value"].rsplit("/", 1)[-1]
            url = f"https://www.wikidata.org/wiki/{el}"
            if "pe" in b and (el, "pe", b["pe"]["value"]) not in vus:
                vus.add((el, "pe", b["pe"]["value"]))
                out["identifiant_pe"].append({"element": el, "identifiant": b["pe"]["value"], "prov_url": url})
            n = (b.get("naissance") or {}).get("value")
            # Une date « -… » (avant notre ère) ou partielle n'est pas une date de naissance utile.
            if n and not n.startswith("-") and (el, "n", n[:10]) not in vus:
                vus.add((el, "n", n[:10]))
                out["naissance_wikidata"].append({"element": el, "naissance": n[:10], "prov_url": url})
    elif m.uid.startswith("mep-"):
        for p in _donnees(m.octets):
            pid = str(p.get("identifier") or _suffixe(p.get("id")))
            url = URL_PERSONNE + pid
            out["eurodepute"].append({
                "personne": pid, "libelle": p.get("label"), "prenom": p.get("givenName"),
                "nom": p.get("familyName"), "naissance": p.get("bday"),
                "lieu_naissance": p.get("placeOfBirth"), "nationalite": _suffixe(p.get("citizenship")),
                "genre": _suffixe(p.get("hasGender")), "prov_url": url})
            for h in p.get("hasMembership") or []:
                periode = h.get("memberDuring") or {}
                rep = h.get("represents") or []
                out["appartenance_pe"].append({
                    "personne": pid, "appartenance": h.get("identifier") or _suffixe(h.get("id")),
                    "organisation": h.get("organization"),
                    "classification": _suffixe(h.get("membershipClassification")),
                    "role": _suffixe(h.get("role")), "debut": periode.get("startDate"),
                    "fin": periode.get("endDate"),
                    "represente": _suffixe(rep[0]) if rep else None, "prov_url": url})
    elif m.uid.startswith("interventions-"):
        pid = m.uid.split("-")[1]
        for x in _donnees(m.octets):
            cr = x.get("recorded_in_a_realization_of") or []
            cr = cr[0].get("id") if cr and isinstance(cr[0], dict) else (cr[0] if cr else None)
            lab = x.get("activity_label")
            out["intervention_pe"].append({
                "personne": pid, "intervention": x.get("activity_id"), "date": x.get("activity_date"),
                "heure": x.get("activity_start_date"),
                "debat": (lab.get("fr") or lab.get("en")) if isinstance(lab, dict) else lab,
                "compte_rendu": _suffixe(cr) if cr else None,
                "point": _suffixe((x.get("inverse_consists_of") or [None])[0]),
                "prov_url": ("https://www.europarl.europa.eu/doceo/document/" + _suffixe(cr) + "_FR.html")
                            if cr else None})
    elif m.uid.startswith("org-"):
        for o in _donnees(m.octets):
            t = o.get("temporal") or {}
            out["groupe_pe"].append({
                "organisation": o.get("id"), "sigle": o.get("label"),
                "libelle": (o.get("prefLabel") or {}).get("fr"),
                "libelle_court": (o.get("altLabel") or {}).get("fr"),
                "version_de": o.get("isVersionOf"), "debut": t.get("startDate"), "fin": t.get("endDate"),
                "classification": _suffixe(o.get("classification")), "prov_url": None})
    return out


EXPORT = {
    "intervention_pe": {"type": "intervention_pe", "cle": ["personne", "intervention"],
                        "ids": {"acteur": "personne", "compte_rendu": "compte_rendu"}, "date": "date"},
    "naissance_wikidata": {"type": "naissance_wikidata", "cle": ["element", "naissance"],
                           "ids": {"autre": "element"}, "date": None},
    "identifiant_pe": {"type": "identifiant_pe_wikidata", "cle": ["element", "identifiant"],
                       "ids": {"autre": "element"}, "date": None},
    "eurodepute": {"type": "eurodepute", "cle": ["personne"], "ids": {"acteur": "personne"},
                   "date": None},
    "appartenance_pe": {"type": "appartenance_pe", "cle": ["personne", "appartenance"],
                        "ids": {"acteur": "personne", "organe": "organisation", "mandat": "appartenance"},
                        "date": "debut"},
    "groupe_pe": {"type": "groupe_pe", "cle": ["organisation"], "ids": {"organe": "organisation"},
                  "date": None},
}
