"""Parlement européen : décisions des séances plénières depuis juillet 2019 (point `pe-votes`,
`empreinte_src/collecte_pe.py` ; portail du PE, CC BY 4.0 ; décisions Q3 et Q33 du 13/11/2026).

Membres :

- `seances-<année>` : la liste des séances plénières de l'année → `seance_pe` ;
- `decisions-<séance>` : les décisions de la séance (`meetings/<séance>/decisions`), vide pour une
  séance sans décision (404 ou 204, un lundi) → `vote_pe` (une ligne par décision : libellé,
  méthode, résultat, décomptes publiés) et `position_pe` (une ligne par décision et par position
  publiée : `favor`, `against`, `abstention`, et les corrections d'intention `intended_…`, avec
  la **liste** des députés européens, `person/<id>` sans son préfixe).

Les listes restent des listes : une ligne par député européen et par vote ferait 15 à 20 millions
de lignes, dont la fiche n'utilise que celles de quelques candidats (R-VOTE-PE). Le libellé est
gardé tel que publié, en français ; la nature du vote (ensemble d'un texte, partie) est établie
par la règle, pas ici.
"""
import re

import orjson
import pyarrow as pa

NOM = "pe_votes"
VERSION = 2
TYPES = ("votes_pe",)
S, I = pa.string(), pa.int32()
TABLES = {
    "seance_pe": pa.schema([("seance", S), ("date", S), ("libelle", S)]),
    "vote_pe": pa.schema([
        ("vote", S), ("numero", S), ("seance", S), ("date", S), ("heure", S), ("type", S),
        ("libelle", S), ("document_ref", S), ("objet", S), ("rubrique", S), ("reference", S),
        ("methode", S), ("resultat", S), ("pour", I), ("contre", I), ("abstention", I),
        ("presents", I), ("nominatif", pa.bool_()), ("document_vote", S), ("proces_verbal", S),
        ("ordre", S)]),
    "position_pe": pa.schema([("vote", S), ("position", S), ("personnes", pa.list_(S))]),
}
URI = "https://data.europarl.europa.eu/"


def _fr(v):
    if isinstance(v, dict):
        return v.get("fr") or v.get("en")
    return v


def _suffixe(v):
    return v.rsplit("/", 1)[-1] if isinstance(v, str) else None


def _premier(v):
    if isinstance(v, list):
        return v[0] if v else None
    return v


def _entier(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _donnees(octets):
    if not octets:
        return []
    d = orjson.loads(octets).get("data")
    return [x for x in (d if isinstance(d, list) else [d]) if isinstance(x, dict)]


def lire(m):
    out = {t: [] for t in TABLES}
    if m.uid.startswith("seances-"):
        for x in _donnees(m.octets):
            out["seance_pe"].append({"seance": x.get("activity_id"), "date": x.get("activity_date"),
                                     "libelle": _fr(x.get("activity_label")),
                                     "prov_url": URI + str(x.get("id"))})
        return out
    if not m.uid.startswith("decisions-"):
        return out
    seance = m.uid[len("decisions-"):]
    for x in _donnees(m.octets):
        vote = x.get("activity_id") or _suffixe(x.get("id"))
        libelle = (_fr(x.get("activity_label")) or "").strip() or None
        # Le libellé sépare ses parties par un tiret court ou long (« A9-0200/2023 – … – Am 287 »).
        morceaux = [p.strip() for p in re.split(r"\s[-–—]\s", libelle or "")]
        listes = {k[len("had_voter_"):]: [_suffixe(p) for p in v]
                  for k, v in x.items() if k.startswith("had_voter_") and isinstance(v, list)}
        out["vote_pe"].append({
            "vote": vote, "numero": x.get("notation_votingId"), "seance": seance,
            "date": x.get("activity_date"), "heure": x.get("activity_start_date"),
            "type": x.get("type"), "libelle": libelle,
            "document_ref": morceaux[0] if len(morceaux) > 1 else None,
            "objet": morceaux[-1] if libelle else None,
            "rubrique": (_fr(x.get("headingLabel")) or "").strip() or None,
            "reference": (_fr(x.get("referenceText")) or "").strip() or None,
            "methode": _suffixe(x.get("decision_method")), "resultat": _suffixe(x.get("decision_outcome")),
            "pour": _entier(x.get("number_of_votes_favor")), "contre": _entier(x.get("number_of_votes_against")),
            "abstention": _entier(x.get("number_of_votes_abstention")),
            "presents": _entier(x.get("number_of_attendees")),
            "nominatif": any(listes.get(k) for k in ("favor", "against", "abstention")),
            "document_vote": _premier(x.get("decided_on_a_realization_of")),
            "proces_verbal": _premier(x.get("recorded_in_a_realization_of")),
            "ordre": x.get("activity_order"), "prov_url": URI + str(x.get("id"))})
        for position, personnes in sorted(listes.items()):
            out["position_pe"].append({"vote": vote, "position": position, "personnes": personnes,
                                       "prov_url": URI + str(x.get("id"))})
    return out


EXPORT = {
    "seance_pe": {"type": "seance_pe", "cle": ["seance"], "ids": {"reunion": "seance"}, "date": "date"},
    "vote_pe": {"type": "vote_pe", "cle": ["vote"], "ids": {"scrutin": "vote", "reunion": "seance"},
                "date": "date"},
    "position_pe": {"type": "position_pe_liste", "cle": ["vote", "position"], "ids": {"scrutin": "vote"},
                    "date": None},
}
