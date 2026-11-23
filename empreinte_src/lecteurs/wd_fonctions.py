"""Wikidata : les fonctions (P39) déclarées pour les éléments de la liste des candidats (point
`wd-fonctions-candidats`, `empreinte_src/collecte_wd_fonctions.py` ; décision Q52 du 23/11/2026).

Une ligne par déclaration P39 et par combinaison de qualificatifs, telle que publiée :
l'élément, l'identifiant de la déclaration (`Q…$…`, stable tant que la déclaration existe), le
poste (élément et libellé français), le début (P580), la fin (P582), le ressort (P1001) et
l'objet (P642) par leurs libellés. Les dates sont ramenées à `AAAA-MM-JJ` ; une date avant notre
ère, ou une valeur inconnue (nœud anonyme), devient `None`. Rien n'est classé ici : la règle
R-MANDAT-LOCAL dit quelles fonctions sont locales.
"""
import orjson
import pyarrow as pa

NOM = "wd_fonctions"
VERSION = 1
TYPES = ("fonctions_wikidata",)
S = pa.string()
TABLES = {"fonction_wikidata": pa.schema([
    ("element", S), ("declaration", S), ("poste", S), ("poste_libelle", S), ("debut", S),
    ("fin", S), ("juridiction", S), ("objet", S)])}


def _val(b, cle):
    return (b.get(cle) or {}).get("value")


def _date(v):
    if not v or v.startswith("-") or v.startswith("http") or len(v) < 10:
        return None
    return v[:10]


def _apres(v, sep):
    return v.rsplit(sep, 1)[-1] if v else None


def lire(m):
    d = orjson.loads(m.octets)
    vus, out = set(), []
    for b in d["results"]["bindings"]:
        el = _apres(_val(b, "item"), "/")
        st = _apres(_val(b, "st"), "/statement/")
        ligne = {"element": el, "declaration": st, "poste": _apres(_val(b, "pos"), "/"),
                 "poste_libelle": _val(b, "posLabel"), "debut": _date(_val(b, "debut")),
                 "fin": _date(_val(b, "fin")), "juridiction": _val(b, "jurLabel"),
                 "objet": _val(b, "ofLabel")}
        cle = tuple(ligne.values())
        if cle in vus or not el or not st:
            continue
        vus.add(cle)
        out.append({**ligne, "prov_url": f"https://www.wikidata.org/wiki/{el}#P39"})
    return {"fonction_wikidata": out}


EXPORT = {
    "fonction_wikidata": {"type": "fonction_wikidata",
                          "cle": ["declaration", "debut", "fin", "juridiction", "objet"],
                          "ids": {"autre": "element"}, "date": "debut"},
}
