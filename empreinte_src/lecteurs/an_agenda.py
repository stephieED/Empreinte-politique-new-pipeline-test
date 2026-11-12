"""Agenda de l'Assemblée (cahier 3.1.7) : réunions et points d'ordre du jour.

Les présences (`participants`) ne sont **pas lues** : elles restent dans l'entrepôt, comme à la
source, et ne deviennent jamais des faits (règle 3 ; décision du 06/11/2026).
"""
import orjson
import pyarrow as pa

from ..lecture import liste, val

NOM = "an_agenda"
VERSION = 1
TYPES = ("agenda",)
TABLES = {
    "reunion": pa.schema([
        ("uid", pa.string()), ("type_reunion", pa.string()), ("debut", pa.string()),
        ("fin", pa.string()), ("date_seance", pa.string()), ("etat", pa.string()),
        ("organe", pa.string()), ("lieu", pa.string()), ("session", pa.string()),
        ("compte_rendu", pa.string()), ("num_seance_jo", pa.string()), ("quantieme", pa.string()),
    ]),
    "point_odj": pa.schema([
        ("reunion", pa.string()), ("uid", pa.string()), ("rang", pa.int32()),
        ("objet", pa.string()), ("type_point", pa.string()), ("nature_travaux", pa.string()),
        ("etat", pa.string()), ("procedure", pa.string()), ("dossiers", pa.list_(pa.string())),
        ("textes_associes", pa.list_(pa.string())),
    ]),
}


def lire(m):
    """Un fichier par réunion (XVe → XVIIe), ou toutes les réunions dans un seul fichier
    (archive de la XIVe : `{"reunions": {"reunion": [...]}}`)."""
    doc = orjson.loads(m.octets)
    if "reunion" in doc:
        return _reunion(doc["reunion"])
    if isinstance(doc.get("reunions"), dict):
        out = {"reunion": [], "point_odj": []}
        for r in liste(doc["reunions"].get("reunion")):
            for t, ls in _reunion(r).items():
                out[t] += ls
        return out
    raise ValueError(f"pas d'objet « reunion » : clés {sorted(doc)[:5]}")


def _reunion(r):
    uid = r["uid"]
    ident = r.get("identifiants") or {}
    cdv = r.get("cycleDeVie") or {}
    reunion = {
        "uid": uid, "type_reunion": r.get("@xsi:type"),
        "debut": val(r.get("timeStampDebut")), "fin": val(r.get("timeStampFin")),
        "date_seance": val(ident.get("DateSeance")), "etat": val(cdv.get("etat")),
        "organe": val(r.get("organeReuniRef")),
        "lieu": val((r.get("lieu") or {}).get("lieuRef")),
        "session": val(r.get("sessionRef")), "compte_rendu": val(r.get("compteRenduRef")),
        "num_seance_jo": val(ident.get("numSeanceJO")), "quantieme": val(ident.get("quantieme")),
        "prov_url": None,
    }
    points = []
    odj = r.get("ODJ") or {}
    for k, p in enumerate(liste((odj.get("pointsODJ") or {}).get("pointODJ"))):
        dossiers = [val(d) for d in liste((p.get("dossiersLegislatifsRefs") or {}).get("dossierRef"))]
        textes = [val(t.get("refTexteAssocie") if isinstance(t, dict) else t)
                  for t in liste((p.get("textesAssocies") or {}).get("texteAssocie"))]
        points.append({
            "reunion": uid, "uid": val(p.get("uid")), "rang": k,
            "objet": val(p.get("objet")), "type_point": val(p.get("typePointODJ")),
            "nature_travaux": val(p.get("natureTravauxODJ")),
            "etat": val((p.get("cycleDeVie") or {}).get("etat")),
            "procedure": val(p.get("procedure")),
            "dossiers": [d for d in dossiers if d], "textes_associes": [t for t in textes if t],
        })
    return {"reunion": [reunion], "point_odj": points}

EXPORT = {
    "reunion": {"type": "reunion", "cle": ["uid"],
                "ids": {"reunion": "uid", "organe": "organe", "compte_rendu": "compte_rendu"},
                "date": "date_seance"},
    "point_odj": {"type": "point_odj", "cle": ["reunion", "rang"],
                  "ids": {"reunion": "reunion", "autre": "uid"}, "date": None},
}
