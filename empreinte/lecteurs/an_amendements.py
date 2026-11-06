"""Amendements de l'Assemblée (cahier 3.1.3) : amendements et signatures.

Un membre de l'archive = un amendement (`json/{dossier}/{document visé}/{uid}.json`). Le
lecteur restitue ce que dit le fichier, sans règle :

- les **copies** `B`/`BTC` d'un même amendement (même `examenRef`, même `numeroLong`, deux uid :
  346 paires dans l'archive XVIIe du 03/11/2026) sont lues **toutes les deux**, chacune sous son
  uid ; le dédoublonnage est la règle R-AMENDEMENT (tranche suivante). `chronotag` et `chemin`
  sont gardés pour elle ;
- le dossier `json/incorrect_data/` (170 amendements) : le chemin ne donne pas de dossier,
  `dossier_chemin` vaut alors `None` ; le document visé reste lu dans `texteLegislatifRef` ;
- les amendements irrecevables n'ont ni exposé ni dispositif : `None`, jamais une chaîne vide ;
- les amendements « effacés » n'ont ni auteur, ni corps, ni date : `None` partout, aucune
  signature ;
- la **liste complète** des cosignataires est gardée, dans l'ordre de la source, doublons
  compris (une liste XVIIe cite deux fois le même député : deux lignes, deux rangs) ;
- le sort est restitué **tel que publié** (`sort`, et le couple état / sous-état) : le sort
  retenu est la règle R-SORT-AMENDEMENT ;
- exposé, dispositif, cartouche et libellé des signataires sont gardés **tels que publiés**
  (HTML avec ses entités) ; le dispositif des amendements de crédits (PLF, PLFR), qui est une
  structure et non un texte, est gardé en JSON dans `dispositif_credits`.

Adresse publique : la source ne donne qu'une adresse relative (`documentURI`, `/base/{uid}?format=pdf`,
gardée telle quelle) sans dire sur quel hôte elle se résout ; aucune adresse de page n'est
vérifiable depuis les données, donc `prov_url` reste vide (à établir, voir la fiche du lecteur).
"""
import re

import orjson
import pyarrow as pa

from ..lecture import liste, pa_id, val

NOM = "an_amendements"
VERSION = 1
TYPES = ("amendements",)
TABLES = {
    "amendement": pa.schema([
        ("uid", pa.string()), ("legislature", pa.string()), ("chronotag", pa.string()),
        ("numero_long", pa.string()), ("numero_ordre_depot", pa.string()),
        ("numero_rect", pa.string()), ("prefixe_organe_examen", pa.string()),
        ("examen", pa.string()), ("organe_examen", pa.string()), ("document", pa.string()),
        ("amendement_parent", pa.string()),
        ("article_titre", pa.string()), ("article_designation", pa.string()),
        ("article_designation_courte", pa.string()), ("division_type", pa.string()),
        ("division_rattachee", pa.string()), ("avant_a_apres", pa.string()),
        ("article_additionnel", pa.string()), ("chapitre_additionnel", pa.string()),
        ("url_division", pa.string()), ("alinea", pa.string()),
        ("mission", pa.string()), ("mission_ref", pa.string()),
        ("type_auteur", pa.string()), ("auteur", pa.string()), ("groupe_auteur", pa.string()),
        ("gouvernement", pa.string()), ("organe_rapporteur", pa.string()),
        ("nb_cosignataires", pa.int32()), ("signataires_libelle", pa.string()),
        ("suffixe", pa.string()),
        ("date_depot", pa.string()), ("date_publication", pa.string()),
        ("date_sort", pa.string()), ("soumis_article_40", pa.string()),
        ("etat_code", pa.string()), ("etat", pa.string()),
        ("sous_etat_code", pa.string()), ("sous_etat", pa.string()), ("sort", pa.string()),
        ("seance_discussion", pa.string()),
        ("discussion_identique", pa.string()), ("discussion_identique_position", pa.string()),
        ("discussion_commune", pa.string()), ("discussion_commune_position", pa.string()),
        ("article_99", pa.string()), ("accord_gouvernement_hors_delai", pa.string()),
        ("loi_reference", pa.string()),
        ("cartouche", pa.string()), ("expose_sommaire", pa.string()),
        ("dispositif", pa.string()), ("dispositif_credits", pa.string()),
        ("annexe_expose", pa.string()), ("avant_appel", pa.string()),
        ("document_uri", pa.string()), ("chemin", pa.string()), ("dossier_chemin", pa.string()),
    ]),
    # Lignes compactes : 3,5 millions de signatures en XVIIe.
    "signature": pa.schema([
        ("amendement", pa.string()), ("acteur", pa.string()), ("role", pa.string()),
        ("rang", pa.int32()),
    ]),
}

# Grammaire de l'examen : EXANR5L17 + organe d'examen (PO…) + texte + …
_ORGANE_EXAMEN = re.compile(r"^EXANR\d+L\d+(PO\d+)")


def _d(x) -> dict:
    """Un sous-objet, ou {} quand il manque ou qu'il est écrit vide."""
    x = val(x)
    return x if isinstance(x, dict) else {}


def _s(x):
    """Une valeur simple en texte ; None pour le vide (jamais "" ni 0)."""
    x = val(x)
    if x is None or isinstance(x, (dict, list)):
        return None
    x = str(x)
    return x if x.strip() else None


def _json(x):
    x = val(x)
    return orjson.dumps(x).decode() if x else None


def _s_ou_json(x):
    """Valeur simple en texte, ou structure gardée en JSON (forme non mesurée en XVIIe)."""
    return _json(x) if isinstance(val(x), (dict, list)) else _s(x)


def _dossier_du_chemin(chemin: str):
    morceaux = (chemin or "").split("/")
    if len(morceaux) >= 3 and morceaux[1].startswith("DLR"):
        return morceaux[1]
    return None             # json/incorrect_data/… : l'archive ne range pas l'amendement


def lire(m):
    a = orjson.loads(m.octets)["amendement"]
    uid = a["uid"]
    ident = _d(a.get("identification"))
    sig = _d(a.get("signataires"))
    aut = _d(sig.get("auteur"))
    pft = _d(a.get("pointeurFragmentTexte"))
    div = _d(pft.get("division"))
    mission = _d(pft.get("missionVisee"))
    standard = _d(pft.get("amendementStandard"))
    corps = _d(a.get("corps"))
    contenu = _d(corps.get("contenuAuteur"))
    cdv = _d(a.get("cycleDeVie"))
    traite = _d(cdv.get("etatDesTraitements"))
    etat, sous_etat = _d(traite.get("etat")), _d(traite.get("sousEtat"))
    ident_disc, commune = _d(a.get("discussionIdentique")), _d(a.get("discussionCommune"))
    rep = liste(_d(a.get("representations")).get("representation"))
    uris = [_s(_d(r.get("contenu")).get("documentURI")) for r in rep if isinstance(r, dict)]
    examen = _s(a.get("examenRef"))
    o = _ORGANE_EXAMEN.match(examen or "")
    credits = contenu.get("dispositifAmdtCreditPLF") or contenu.get("dispositifAmdtCreditPLFR")

    auteur = pa_id(aut.get("acteurRef"))
    cosig = [pa_id(x) for x in liste(_d(sig.get("cosignataires")).get("acteurRef"))]
    cosig = [x for x in cosig if x]

    amendement = {
        "uid": uid, "legislature": _s(a.get("legislature")), "chronotag": _s(a.get("chronotag")),
        "numero_long": _s(ident.get("numeroLong")),
        "numero_ordre_depot": _s(ident.get("numeroOrdreDepot")),
        "numero_rect": _s(ident.get("numeroRect")),
        "prefixe_organe_examen": _s(ident.get("prefixeOrganeExamen")),
        "examen": examen, "organe_examen": o.group(1) if o else None,
        "document": _s(a.get("texteLegislatifRef")),
        "amendement_parent": _s(a.get("amendementParentRef")),
        "article_titre": _s(div.get("titre")),
        "article_designation": _s(div.get("articleDesignation")),
        "article_designation_courte": _s(div.get("articleDesignationCourte")),
        "division_type": _s(div.get("type")),
        "division_rattachee": _s(div.get("divisionRattachee")),
        "avant_a_apres": _s(div.get("avant_A_Apres")),
        "article_additionnel": _s(div.get("articleAdditionnel")),
        "chapitre_additionnel": _s(div.get("chapitreAdditionnel")),
        "url_division": _s(div.get("urlDivisionTexteVise")),
        "alinea": _s_ou_json(standard.get("alinea")),
        "mission": _s(mission.get("libelleMission")), "mission_ref": _s(mission.get("missionRef")),
        "type_auteur": _s(aut.get("typeAuteur")), "auteur": auteur,
        "groupe_auteur": _s(aut.get("groupePolitiqueRef")),
        "gouvernement": _s(aut.get("gouvernementRef")),
        "organe_rapporteur": _s(aut.get("auteurRapporteurOrganeRef")),
        "nb_cosignataires": len(cosig),
        "signataires_libelle": _s(sig.get("libelle")), "suffixe": _s(sig.get("suffixe")),
        "date_depot": _s(cdv.get("dateDepot")), "date_publication": _s(cdv.get("datePublication")),
        "date_sort": _s(cdv.get("dateSort")), "soumis_article_40": _s(cdv.get("soumisArticle40")),
        "etat_code": _s(etat.get("code")), "etat": _s(etat.get("libelle")),
        "sous_etat_code": _s(sous_etat.get("code")), "sous_etat": _s(sous_etat.get("libelle")),
        "sort": _s(cdv.get("sort")),
        "seance_discussion": _s(a.get("seanceDiscussionRef")),
        "discussion_identique": _s(ident_disc.get("idDiscussion")),
        "discussion_identique_position": _s(ident_disc.get("typePosition")),
        "discussion_commune": _s(commune.get("idDiscussion")),
        "discussion_commune_position": _s(commune.get("typePosition")),
        "article_99": _s(a.get("article99")),
        "accord_gouvernement_hors_delai": _s(a.get("accordGouvernementDepotHorsDelai")),
        "loi_reference": _s_ou_json(a.get("loiReference")),
        "cartouche": _s_ou_json(corps.get("cartoucheInformatif")),
        "expose_sommaire": _s(contenu.get("exposeSommaire")),
        "dispositif": _s(contenu.get("dispositif")),
        "dispositif_credits": _json(credits),
        "annexe_expose": _s_ou_json(contenu.get("annexeExposeSommaire")),
        "avant_appel": _s_ou_json(contenu.get("avantAppel")),
        "document_uri": next((u for u in uris if u), None),
        "chemin": m.chemin, "dossier_chemin": _dossier_du_chemin(m.chemin),
        "prov_url": None,
    }
    signatures = []
    if auteur:
        signatures.append({"amendement": uid, "acteur": auteur, "role": "auteur", "rang": 0})
    for k, x in enumerate(cosig, start=1):
        signatures.append({"amendement": uid, "acteur": x, "role": "cosignataire", "rang": k})
    return {"amendement": [amendement], "signature": signatures}


EXPORT = {
    "amendement": {"type": "amendement", "cle": ["uid"],
                   "ids": {"amendement": "uid", "acteur": "auteur", "organe": "organe_examen",
                           "document": "document", "reunion": "seance_discussion"},
                   "date": "date_depot"},
    # Clé (amendement, rang) et non (amendement, acteur) : une liste de la source cite deux fois
    # le même cosignataire, les deux lignes sont gardées.
    "signature": {"type": "signature", "cle": ["amendement", "rang"],
                  "ids": {"amendement": "amendement", "acteur": "acteur"}, "date": None},
}
