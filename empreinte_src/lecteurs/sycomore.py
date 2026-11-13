"""Sycomore : mandats de député des candidats, tels qu'extraits au relevé (point
`sycomore-fiches`, `empreinte_src/collecte_sycomore.py` ; cahier 3.11 ; décision Q36 du
13/11/2026). Des **faits** seulement (la page, sous droits, n'est pas gardée).

Membres : `wikidata-p1045` (réponse SPARQL : élément → identifiant Sycomore) →
`identifiant_sycomore` ; `sycomore-<id>` (faits JSON écrits par le relevé) → `mandat_sycomore`,
une ligne par mandat (chambre `assemblee` ou `senat`, régime, législature, début, fin,
département, groupe, tels que la fiche les écrit ; dates converties au relevé).
"""
import orjson
import pyarrow as pa

NOM = "sycomore"
VERSION = 1
TYPES = ("fiches_sycomore",)
S = pa.string()
TABLES = {
    "identifiant_sycomore": pa.schema([("element", S), ("identifiant", S)]),
    "mandat_sycomore": pa.schema([
        ("identifiant", S), ("nom", S), ("rang", pa.int32()), ("chambre", S), ("regime", S),
        ("legislature", S), ("mandat", S), ("debut", S), ("fin", S), ("departement", S), ("groupe", S),
        ("extracteur", S)]),
}


def lire(m):
    out = {t: [] for t in TABLES}
    d = orjson.loads(m.octets)
    if m.uid == "wikidata-p1045":
        for b in d["results"]["bindings"]:
            el = b["item"]["value"].rsplit("/", 1)[-1]
            out["identifiant_sycomore"].append({"element": el, "identifiant": b["sycomore"]["value"],
                                                "prov_url": f"https://www.wikidata.org/wiki/{el}"})
    elif m.uid.startswith("sycomore-"):
        for k, x in enumerate(d.get("mandats") or []):
            out["mandat_sycomore"].append({"identifiant": d["num_dept"], "nom": d.get("nom"), "rang": k, **{
                c: x.get(c) for c in ("chambre", "regime", "legislature", "mandat", "debut", "fin",
                                      "departement", "groupe")}, "extracteur": d.get("extracteur"),
                                           "prov_url": d.get("url")})
    return out


EXPORT = {
    "identifiant_sycomore": {"type": "identifiant_sycomore_wikidata", "cle": ["element", "identifiant"],
                             "ids": {"autre": "element"}, "date": None},
    "mandat_sycomore": {"type": "mandat_sycomore", "cle": ["identifiant", "chambre", "debut"],
                        "ids": {"acteur": "identifiant"}, "date": "debut"},
}
