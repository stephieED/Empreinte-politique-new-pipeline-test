"""Parltrack : votes nominatifs du Parlement européen (point `parltrack-votes`, fichier
`ep_votes.json.zst`, ODbL 1.0 ; cahier 3.4 ; décision Q3 du 13/11/2026 : Parltrack pour les votes
antérieurs au 02/07/2019).

Le membre est le fichier compressé tel que reçu (zstandard), lu en flux : un tableau JSON, un
scrutin par ligne (`[{…}` puis `,{…}`, `]` seul à la fin ; mesures du 04/11/2026). Pour chaque
scrutin : `vote_pt` (identifiant Parltrack, date et heure, intitulé, document, adresse du
procès-verbal) et `position_pt` (une ligne par position publiée, `+` → `favor`, `-` →
`against`, `0` → `abstention`, avec la **liste** des députés européens, `mepid`, qui est
l'identifiant du portail du Parlement européen). Mêmes noms que le lecteur `pe_votes`, pour que
R-VOTE-PE lise les deux sources de la même façon.

Pièges connus (cahier 3.4) : un identifiant de scrutin entier ou texte (`7754`,
`"2017-12-12 00:00:00-1."`) : gardé en texte, préfixé `pt-` ; des scrutins sans `votes` (92) ni
`doc` ; la position d'un député est rangée sous son groupe : les groupes sont aplatis.
"""
import io
import re

import orjson
import pyarrow as pa

NOM = "parltrack_votes"
VERSION = 1
TYPES = ("votes_parltrack",)
S, I = pa.string(), pa.int32()
TABLES = {
    "vote_pt": pa.schema([
        ("vote", S), ("voteid", S), ("date", S), ("heure", S), ("libelle", S), ("document_ref", S),
        ("objet", S), ("procedures", S), ("pour", I), ("contre", I), ("abstention", I),
        ("nominatif", pa.bool_())]),
    "position_pt": pa.schema([("vote", S), ("position", S), ("personnes", pa.list_(S))]),
}
POSITIONS = {"+": "favor", "-": "against", "0": "abstention"}
LOT = 5_000


def _objets(octets):
    import zstandard
    flux = io.TextIOWrapper(zstandard.ZstdDecompressor().stream_reader(io.BytesIO(octets)), encoding="utf-8")
    for ligne in flux:
        ligne = ligne.strip().lstrip("[,").rstrip("]").strip()
        if ligne:
            yield orjson.loads(ligne)


def lire(m):
    lot = {t: [] for t in TABLES}
    for o in _objets(m.octets):
        vid = str(o.get("voteid"))
        vote = f"pt-{vid}"
        titre = (o.get("title") or "").strip() or None
        morceaux = [p.strip() for p in re.split(r"\s[-–—]\s", titre or "")]
        votes = o.get("votes") or {}
        ts = str(o.get("ts") or "")
        url = o.get("url")
        ep = o.get("epref")
        lot["vote_pt"].append({
            "vote": vote, "voteid": vid, "date": ts[:10] or None, "heure": ts or None, "libelle": titre,
            "document_ref": o.get("doc"), "objet": morceaux[-1] if titre else None,
            "procedures": ", ".join(ep) if isinstance(ep, list) else ep,
            "pour": (votes.get("+") or {}).get("total"), "contre": (votes.get("-") or {}).get("total"),
            "abstention": (votes.get("0") or {}).get("total"), "nominatif": bool(votes),
            "prov_url": url})
        for signe, position in POSITIONS.items():
            groupes = (votes.get(signe) or {}).get("groups") or {}
            personnes = [str(p["mepid"]) for membres in groupes.values() for p in membres
                         if isinstance(p, dict) and p.get("mepid") is not None]
            if personnes:
                lot["position_pt"].append({"vote": vote, "position": position, "personnes": personnes,
                                           "prov_url": url})
        if len(lot["vote_pt"]) >= LOT:
            yield lot
            lot = {t: [] for t in TABLES}
    if lot["vote_pt"]:
        yield lot


EXPORT = {
    "vote_pt": {"type": "vote_parltrack", "cle": ["vote"], "ids": {"scrutin": "vote"}, "date": "date"},
    "position_pt": {"type": "position_parltrack_liste", "cle": ["vote", "position"],
                    "ids": {"scrutin": "vote"}, "date": None},
}
