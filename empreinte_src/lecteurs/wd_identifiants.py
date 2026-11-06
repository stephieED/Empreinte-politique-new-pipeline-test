"""Wikidata : identifiants parlementaires d'une personne (cahier 3.10).

Une ligne par (élément Wikidata, identifiant) tel que publié. Wikidata écrit l'identifiant de
l'Assemblée sans le préfixe `PA` (P4123), et l'identifiant du Sénat (P1808) comme un chemin
d'adresse (`senateur/melenchon_jean_luc86039k`) dont la fin est le matricule en minuscules :
on garde la valeur publiée et l'on rend en plus la forme normalisée."""
import re
import urllib.parse

import orjson
import pyarrow as pa

from ..lecture import pa_id

NOM = "wd_identifiants"
VERSION = 1
TYPES = ("identifiants_wikidata",)
TABLES = {
    "identifiant_externe": pa.schema([
        ("element", pa.string()), ("propriete", pa.string()), ("valeur_publiee", pa.string()),
        ("identifiant", pa.string()), ("naissance", pa.string()), ("article_frwiki", pa.string()),
    ]),
}
MATRICULE = re.compile(r"(\d{5}[a-z])$")


def lire(m):
    d = orjson.loads(m.octets)
    vus, out = set(), []
    for b in d["results"]["bindings"]:
        el = b["item"]["value"].rsplit("/", 1)[-1]
        naissance = (b.get("naissance") or {}).get("value")
        naissance = naissance[:10] if naissance and not naissance.startswith("-") else None
        art = (b.get("article") or {}).get("value")
        titre = urllib.parse.unquote(art.rsplit("/wiki/", 1)[-1]).replace("_", " ") if art else None
        for prop, cle in (("P4123", "an"), ("P1808", "senat"), ("P1045", "sycomore")):
            v = (b.get(cle) or {}).get("value")
            if not v or (el, prop, v, titre) in vus:
                continue
            vus.add((el, prop, v, titre))
            if prop == "P4123":
                ident = pa_id(v)
            elif prop == "P1808":
                mm = MATRICULE.search(v)
                ident = mm.group(1).upper() if mm else None
            else:
                ident = v
            out.append({"element": el, "propriete": prop, "valeur_publiee": v, "identifiant": ident,
                        "naissance": naissance, "article_frwiki": titre,
                        "prov_url": f"https://www.wikidata.org/wiki/{el}"})
    return {"identifiant_externe": out}


EXPORT = {
    "identifiant_externe": {"type": "identifiant_wikidata",
                            "cle": ["element", "propriete", "valeur_publiee", "article_frwiki"],
                            "ids": {"autre": "element"}, "date": None},
}
