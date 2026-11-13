"""Parltrack : activités des députés européens (point `parltrack-activites`, fichier
`ep_mep_activities.json.zst`, ODbL 1.0 ; cahier 3.4 ; décision Q37 du 13/11/2026).

Un objet par député européen (`mep_id`, identifiant du portail du PE), avec une liste par type
d'activité : `CRE` (intervention en séance), `REPORT`, `REPORT-SHADOW`, `COMPARL`,
`COMPARL-SHADOW` (rapports et avis, comme rapporteur ou rapporteur fictif), `MOTION`, `IMOTION`
(propositions de résolution), `WQ`, `OQ`, `MINT` (questions), `WEXP` (explications de vote, avec
leur texte), `WDECL` (déclarations écrites), `PRUNACT`. Une ligne de `activite_pt` par activité.

**Date** (piège du cahier 3.4) : 548 598 activités portent la date de republication du
22/11/2016 (`date-type: datePublished`). Pour celles-là, la date est relue dans l'adresse
(`CRE-8-2017-02-15`) ou la référence (`P8_CRE-REV(2017)02-15`) ; à défaut, seule l'année de la
référence (`A7-0342/2011`) est gardée (`annee`), et la date reste vide, avec sa raison. La date
publiée est gardée telle quelle (`date_publiee`).
"""
import io
import re

import orjson
import pyarrow as pa

NOM = "parltrack_activites"
VERSION = 1
TYPES = ("activites_parltrack",)
S = pa.string()
TABLES = {"activite_pt": pa.schema([
    ("mep", S), ("type", S), ("rang", pa.int32()), ("date", S), ("annee", S), ("date_raison", S),
    ("date_publiee", S), ("titre", S), ("reference", S), ("dossiers", S), ("commission", S),
    ("terme", S), ("texte", S)])}
REPUBLICATION = "2016-11-22T19:07"
_JOUR = re.compile(r"(?:CRE-\d+-|\()?((?:19|20)\d{2})[-)](\d{2})-(\d{2})")
_ANNEE = re.compile(r"/((?:19|20)\d{2})\b|\(((?:19|20)\d{2})\)")
LOT = 50_000


def date_reelle(x: dict) -> tuple[str | None, str | None, str | None]:
    """(date, année, raison) : la date publiée, sauf la date de republication du 22/11/2016."""
    d = str(x.get("date") or "")
    if d and not (x.get("date-type") == "datePublished" and d.startswith(REPUBLICATION)):
        return d[:10], d[:4], None
    for champ in (x.get("url") or "", x.get("reference") or ""):
        m = _JOUR.search(champ)
        if m:
            a, mo, j = m.groups()
            return f"{a}-{mo}-{j}", a, "date relue dans l'adresse ou la référence (date publiée : republication du 22/11/2016)"
    m = _ANNEE.search(x.get("reference") or "")
    if m:
        a = m.group(1) or m.group(2)
        return None, a, "date inconnue : seule l'année de la référence est sûre (date publiée : republication du 22/11/2016)"
    return None, None, "date inconnue (date publiée : republication du 22/11/2016)"


def _objets(octets):
    import zstandard
    flux = io.TextIOWrapper(zstandard.ZstdDecompressor().stream_reader(io.BytesIO(octets)), encoding="utf-8")
    for ligne in flux:
        ligne = ligne.strip().lstrip("[,").rstrip("]").strip()
        if ligne:
            yield orjson.loads(ligne)


def lire(m):
    lot = []
    for o in _objets(m.octets):
        mep = str(o.get("mep_id"))
        for type_, liste in o.items():
            if not isinstance(liste, list):
                continue
            for k, x in enumerate(liste):
                if not isinstance(x, dict):
                    continue
                d, a, raison = date_reelle(x)
                dos = x.get("dossiers")
                lot.append({"mep": mep, "type": type_, "rang": k, "date": d, "annee": a, "date_raison": raison,
                            "date_publiee": x.get("date"), "titre": (x.get("title") or "").strip() or None,
                            "reference": x.get("reference"),
                            "dossiers": ", ".join(dos) if isinstance(dos, list) else (str(dos) if dos else None),
                            "commission": x.get("committee"), "terme": str(x.get("term") or "") or None,
                            "texte": x.get("text"), "prov_url": x.get("url")})
                if len(lot) >= LOT:
                    yield {"activite_pt": lot}
                    lot = []
    if lot:
        yield {"activite_pt": lot}


EXPORT = {"activite_pt": {"type": "activite_parltrack", "cle": ["mep", "type", "rang"],
                          "ids": {"acteur": "mep"}, "date": "date"}}
