"""Composeur « candidat » (cahier 4.2) sur de petites tables Z3 écrites à la main.

Quatre candidats : Alice Martin (députée en XVIe puis XVIIe : toute son activité est dans le
périmètre, XIVe à XVIIe), Éric Zemmour (aucun identifiant parlementaire), Jean Ancien (député de la
XIIIe seulement, avant le périmètre) et Rémi Retiré (candidature retirée : pas de fiche)."""
import gzip
import json
import os

import pyarrow as pa
import pytest

from empreinte_src.composeurs import candidat as composeur
from empreinte_src.composition import Ecrivain
from empreinte_src.controles import Controles
from empreinte_src.liaison import Contexte

STATUTS = {"complet", "partiel", "trou_source", "borne_historique", "non_collecte", "panne", "en_cours",
           "relu_aucun", "non_relu", "hors_perimetre"}
AU = "2026-11-06"
CR = "https://www.assemblee-nationale.fr/dyn/17/comptes-rendus/seance/"
SC = "https://www.assemblee-nationale.fr/dyn/17/scrutins/"


def _cand(per, nom, adresse, acteur=None, statut="declaree", ratt="wikidata", connu=True):
    return {"per": per, "nom": nom, "statut": statut, "date_declaration": "2026-01-10",
            "article_frwiki": nom, "element_wikidata": "Q1" if acteur else None, "acteur": acteur,
            "matricule_senat": None, "adresse": adresse, "publie": statut == "declaree",
            "rattachement": ratt, "raison_rattachement": None, "raison_adresse": None,
            "raison_non_publie": None, "n_homonymes": 0, "statut_source": statut,
            "date_declaration_texte": "10/01/2026", "date_declaration_raison": None,
            "date_declaration_phrase": None, "sycomore": None,
            "acteur_connu_an": connu if acteur else None, "matricule_connu_senat": None,
            "references": [], "revision": 1, "source_url": "https://fr.wikipedia.org/wiki/Liste",
            "article_url": f"https://fr.wikipedia.org/wiki/{nom.replace(' ', '_')}",
            "element_url": None, "personne_source": nom}


def _ident(per, nom, prenom, acteur=None, src="an"):
    return {"per": per, "nom": nom, "prenom": prenom, "naissance": "1975-10-18" if acteur else None,
            "lieu_naissance": "Calais (Pas-de-Calais)" if acteur else None,
            "profession": "Reporter" if acteur else None, "civilite": "Mme" if acteur else None,
            "deces": None, "nom_usage_wikipedia": f"{prenom} {nom}", "source_nom": src,
            "source_prenom": src, "source_naissance": "an" if acteur else None,
            "source_lieu_naissance": "an" if acteur else None,
            "source_profession": "an" if acteur else None,
            "raison_naissance": None if acteur else "non connue de nos sources",
            "raison_lieu_naissance": None, "raison_profession": None, "naissance_concordance": "une_source",
            "source_url": None, "source_url_wikipedia": None, "source_url_wikidata": None,
            "acteur": acteur, "matricule_senat": None, "acteur_present_an": bool(acteur),
            "matricule_present_senat": False}


def _car(per, debut, fin, leg, lien, groupe=None, sigle=None, inst="assemblee", gouv=None, mandat="PM1",
         acteur="PA1"):
    return {"per": per, "institution": inst, "debut": debut, "fin": fin, "libelle": "Députée",
            "legislature": leg, "gouvernement": gouv, "groupe": groupe, "groupe_sigle": sigle,
            "groupe_libelle": "Écologiste et Social" if sigle else None,
            "groupe_statut": "groupe" if groupe else "non_etabli", "siege": None, "siege_date": None,
            "raison_siege": None, "lien": lien, "source": "an", "etat": "en_fonction", "qualite": None,
            "mandat": mandat, "acteur": acteur, "circonscription": None, "cause_fin": None,
            "fin_raison": None, "source_url": f"https://www.assemblee-nationale.fr/dyn/deputes/{acteur}"}


def _couvcar(per, statuts):
    return [{"per": per, "institution": i, "depuis": None, "lignes": 0, "statut": s, "detail": f"{i} : {s}"}
            for i, s in statuts.items()]


def _texte(acteur, dossier, document, role, date, publiable=True, etape="examen_commission", gouv=None,
           titre="Logement des étudiants"):
    return {"acteur": acteur, "dossier": dossier, "document": document, "role": role,
            "qualite_rapporteur": None, "nature": "proposition_de_loi", "nature_code": document[:4],
            "sous_nature_code": None, "date_depot": date, "date_role": date, "date_retrait": None,
            "rang": 1, "chambre": "AN", "etape_atteinte": etape, "rang_etape": 2, "date_etape": date,
            "sort": "non_connu", "raison_sort": None, "par_49_3": False, "adopte_par_49_3": False,
            "matiere": "PO420120", "matiere_statut": "assemblee",
            "matiere_libelle": "Commission des affaires sociales", "gouvernement": gouv,
            "publiable": publiable,
            "raison_non_publiable": None if publiable else "pas_encore_examine_en_commission",
            "titre": titre, "acte": None, "source_url": f"https://www.assemblee-nationale.fr/{document}"}


def _am(uid, acteur, date, famille, sort="rejete", commission="PO420120"):
    return {"acteur": acteur, "amendement": uid, "type_auteur": "Depute", "date_depot": date, "sort": sort,
            "famille_sort": famille, "etat_code": "DI", "etat": None, "sous_etat": None, "sort_source": None,
            "commission": commission, "commission_libelle": "Commission des affaires sociales",
            "commission_source": "organe_examen", "raison_commission": None, "dossier": "DL1",
            "raison_dossier": None, "document": "PIONANR5L17B0001", "examen": "EX1", "numero_long": uid[-1],
            "organe_examen": commission, "type_organe_examen": "COMPER", "sous_amendement": False,
            "amendement_parent": None, "nb_copies": 1, "alias": [], "copies_divergentes": False,
            "nb_cosignataires_liste": 0, "groupe_auteur_source": None, "groupe_au_depot": "POG",
            "banc_au_depot": "non_declaree", "raison_banc": None, "organe_rapporteur": None,
            "article_designation": "Article 1", "mission": None, "date_sort": None, "sans_texte": False,
            "document_uri": None, "source_url": None, "raison_source_url": "adresse_non_publiee_dans_les_donnees"}


def _vote(scrutin, date, position, nature="ensemble", dossier="DL1", par_49_3=False, periode="PA1/2024-12-14"):
    return {"acteur": "PA1", "scrutin": scrutin, "dossier": dossier, "date": date, "position": position,
            "nature": nature, "derniere_lecture": nature == "ensemble", "matiere": "PO420120",
            "matiere_statut": "assemblee", "matiere_libelle": "Commission des affaires sociales",
            "origine": "proposition", "raison_origine": None, "type_texte": "PION", "sort_final": "adopte",
            "par_49_3": par_49_3, "groupe": "POG", "groupe_scrutin": "POG", "raison_groupe": None,
            "periode": periode, "banc": "non_declaree", "gouvernement": "GB", "raison_periode": None,
            "cause_non_votant": None, "par_delegation": False, "mise_au_point": None,
            "mise_au_point_dysfonctionnement": None, "lecture": "premiere", "numero": 1, "solennel": False,
            "dossiers": None, "titre_dossier": "Logement des étudiants", "intitule": f"l'ensemble ({scrutin})",
            "mandat": "PM2", "num_place": "505", "source_url": SC + scrutin}


def _parole(ids, date, extrait, preside=False, sujet="Logement des étudiants", qualite="depute"):
    return {"acteur": "PA1", "compte_rendu": "CR1", "id_syceron": ids, "date": date, "qualite": qualite,
            "qualite_source": "deduite", "raison_qualite": None, "preside": preside, "interruption": False,
            "sujet": sujet, "statut_sujet": "etabli", "creneau": None, "type_sujet": "texte",
            "dossier": "DL1", "lien_dossier": "lie", "extrait": extrait, "extrait_tronque": False,
            "longueur": len(extrait), "periode": "PA1/2024-12-14", "gouvernement_a_la_date": None,
            "seance": "S1", "ordre_absolu_seance": int(ids), "source_url": f"{CR}CR1#{ids}"}


TABLES = {
    "legislature": [{"numero": 13, "organe": "PO13", "debut": "2007-06-20", "fin": "2012-06-19",
                     "en_cours": False, "mode_fin": "fin_de_legislature", "source_url": None},
                    {"numero": 14, "organe": "PO14", "debut": "2012-06-20", "fin": "2017-06-20",
                     "en_cours": False, "mode_fin": "fin_de_legislature", "source_url": None},
                    {"numero": 15, "organe": "PO15", "debut": "2017-06-21", "fin": "2022-06-21",
                     "en_cours": False, "mode_fin": "fin_de_legislature", "source_url": None},
                    {"numero": 16, "organe": "PO16", "debut": "2022-06-22", "fin": "2024-06-09",
                     "en_cours": False, "mode_fin": "dissolution", "source_url": None},
                    {"numero": 17, "organe": "PO17", "debut": "2024-07-01", "fin": None, "en_cours": True,
                     "mode_fin": "en_cours", "source_url": None}],
    "gouvernement": [{"organe": "GA", "nom": "Alpha", "adresse": "alpha", "debut": "2022-05-17",
                      "fin": "2024-01-09", "en_cours": False, "rang": 1, "source_url": None},
                     {"organe": "GB", "nom": "Beta", "adresse": "beta", "debut": "2024-12-14",
                      "fin": None, "en_cours": True, "rang": 2, "source_url": None}],
    # Alpha ne traverse ici que la XIIIe (avant le périmètre) : pas de fiche.
    "gouvernement_legislature": [{"gouvernement": "GA", "legislature": 13, "debut": "2022-06-22",
                                  "fin": "2024-01-09"},
                                 {"gouvernement": "GB", "legislature": 17, "debut": "2024-12-14", "fin": None}],
    "groupe": [{"organe": "POG", "legislature": 17, "sigle": "ECOS", "libelle": "Écologiste et Social",
                "debut": "2024-07-19", "fin": None, "position_declaree": "non_declaree"}],
    "candidat": [_cand("per:000001", "Alice Martin", "alice-martin", "PA1"),
                 _cand("per:000002", "Éric Zemmour", "eric-zemmour", ratt="sans_identifiant_parlementaire"),
                 _cand("per:000003", "Jean Ancien", "jean-ancien", "PA3"),
                 _cand("per:000004", "Rémi Retiré", "remi-retire", "PA4", statut="retiree")],
    "personne_identite": [_ident("per:000001", "Martin", "Alice", "PA1"),
                          _ident("per:000002", "Zemmour", "Éric", None, src="wikipedia"),
                          _ident("per:000003", "Ancien", "Jean", "PA3"),
                          _ident("per:000004", "Retiré", "Rémi", "PA4")],
    "carriere": [_car("per:000001", "2022-06-22", "2024-06-09", 16, "legislature/16"),
                 _car("per:000001", "2024-07-08", "2024-07-18", 17, "legislature/17", mandat="PM2"),
                 _car("per:000001", "2024-07-19", None, 17, "legislature/17", "POG", "ECOS", mandat="PM2"),
                 _car("per:000003", "2007-06-20", "2012-06-19", 13, None, mandat="PM3", acteur="PA3")],
    "couverture_carriere": (
        _couvcar("per:000001", {"assemblee": "complet", "assemblee_avant_2002": "hors_source",
                                "gouvernement": "relu_aucun", "senat": "aucun_identifiant",
                                "parlement_europeen": "non_collecte", "local": "non_collecte"})
        + _couvcar("per:000002", {"assemblee": "aucun_identifiant", "assemblee_avant_2002": "hors_source",
                                  "gouvernement": "aucun_identifiant", "senat": "aucun_identifiant",
                                  "parlement_europeen": "non_collecte", "local": "non_collecte"})
        + _couvcar("per:000003", {"assemblee": "complet", "assemblee_avant_2002": "hors_source",
                                  "gouvernement": "relu_aucun", "senat": "aucun_identifiant",
                                  "parlement_europeen": "non_collecte", "local": "non_collecte"})),
    "fonction_personne": [
        {"per": "per:000001", "famille": "commission", "organe": "PO420120",
         "libelle": "Commission des affaires sociales", "qualite": "Secrétaire", "debut": "2022-07-01",
         "fin": None, "duree_jours": 1590, "raison_duree": None, "duree_organe_jours": 1590, "en_cours": True,
         "duree_calculee_au": AU, "qualite_distinctive": True, "libelle_famille": "Commissions",
         "rang_famille": 3, "type_organe": "COMPER", "chambre": "an", "legislature": 17,
         "nb_periodes_fusionnees": 2, "plus_long_trou_fusionne_jours": 2, "nb_mandats_source": 2,
         "mandats": ["PM10", "PM11"], "acteur": "PA1", "source_url": None}],
    "fonction_periode": [
        {"per": "per:000001", "chambre": "an", "type_organe": "COMPER", "organe": "PO420120",
         "libelle": "Commission des affaires sociales", "legislature": 17, "qualite": "Secrétaire",
         "mandat": m, "debut": d, "fin": fi, "acteur": "PA1", "source_url": None,
         "ouverte_dans_le_mandat_en_cours": fi is None, "famille": "commission",
         "libelle_famille": "Commissions", "rang_famille": 3}
        for m, d, fi in (("PM10", "2022-07-01", "2024-06-09"), ("PM11", "2024-06-12", None))],
    "texte_porte": [
        _texte("PA1", "DL1", "PIONANR5L17B0001", "auteur", "2025-01-15", titre="Logement des étudiants"),
        _texte("PA1", "DL2", "PIONANR5L17B0002", "cosignataire", "2025-02-01", publiable=False, etape="depot"),
        _texte("PA1", "DL0", "PIONANR5L13B0009", "cosignataire", "2011-11-03", titre="Ancien texte"),
        _texte("PA1", "DL3", "PRJLANR5L17B0003", "initiative_gouvernementale", "2025-03-01", gouv="GB",
               titre="Projet de loi de finances"),
        _texte("PA1", "DL4", "PRJLANR5L16B0004", "initiative_gouvernementale", "2024-07-20", gouv="GA",
               titre="Projet ancien gouvernement")],
    "amendement_canonique": [_am("AM1", "PA1", "2025-01-20", "discute"),
                             _am("AM2", "PA1", "2025-01-21", "irrecevable_40", "irrecevable"),
                             _am("AM3", "PA1", "2026-02-02", "irrecevable_45", "irrecevable"),
                             _am("AM9", "PA9", "2025-03-03", "discute", "adopte")],
    "amendement_auteur": [
        {"acteur": "PA1", "amendement": a, "role": "auteur", "rang": 1, "cite_plusieurs_fois": False,
         "type_auteur": "Depute", "date_depot": d, "sort": "rejete", "famille_sort": "discute",
         "commission": "PO420120", "dossier": "DL1", "document": "PIONANR5L17B0001"}
        for a, d in (("AM1", "2025-01-20"), ("AM2", "2025-01-21"), ("AM3", "2026-02-02"))]
        + [{"acteur": "PA1", "amendement": "AM9", "role": "cosignataire", "rang": 2, "cite_plusieurs_fois": False,
            "type_auteur": "Depute", "date_depot": "2025-03-03", "sort": "adopte", "famille_sort": "discute",
            "commission": "PO420120", "dossier": "DL1", "document": "PIONANR5L17B0001"}],
    "an_amendements__amendement": [
        {"uid": "AM1", "expose_sommaire": "<p>Cet amendement vise &#x00E0; garantir la pr&#x00E9;sence "
                                          "d&#x2019;un logement pour chaque &#x00E9;tudiant boursier.</p>",
         "dispositif": "<p>Texte</p>", "prov_point": "an-amendements-l17", "licence": "etalab-2.0"},
        {"uid": "AM2", "expose_sommaire": None, "dispositif": None, "prov_point": "an-amendements-l17",
         "licence": "etalab-2.0"},
        {"uid": "AM3", "expose_sommaire": "<p>Rattrapage des bourses.</p>", "dispositif": None,
         "prov_point": "an-amendements-l17", "licence": "etalab-2.0"}],
    "vote_personne": [_vote("VT1", "2025-01-30", "pour"), _vote("VT2", "2025-06-10", "contre", dossier="DL3",
                                                                  par_49_3=True),
                      _vote("VT3", "2025-10-01", "pour", nature="motion_censure", dossier=None)],
    "periode_position": [
        {"acteur": "PA1", "periode": "PA1/2022-06-22", "debut": "2022-06-22", "fin": "2024-01-09",
         "banc": "opposition", "gouvernement": "GA", "legislature": 16, "raison_gouvernement": None,
         "raisons_banc": [], "mandats": ["PM1"]},
        {"acteur": "PA1", "periode": "PA1/2024-12-14", "debut": "2024-12-14", "fin": None,
         "banc": "non_declaree", "gouvernement": "GB", "legislature": 17, "raison_gouvernement": None,
         "raisons_banc": ["position_non_declaree_par_le_groupe"], "mandats": ["PM2"]}],
    "divergence": [
        {"acteur": "PA1", "scrutin": "VT1", "date": "2025-01-30", "position": "pour", "position_groupe": "contre",
         "groupe": "POG", "diverge": True, "dossier": "DL1", "sigle": "ECOS", "groupe_scrutin": "POG",
         "groupe_scrutin_different": False, "groupe_divise": True, "groupe_pour": 3, "groupe_contre": 30,
         "groupe_abstentions": 0, "groupe_non_votants": 0, "groupe_membres": 38, "matiere": "PO420120",
         "matiere_libelle": "Commission des affaires sociales", "sort_final": "adopte", "origine": "proposition",
         "titre_dossier": "Logement des étudiants", "periode": "PA1/2024-12-14", "source_url": SC + "VT1"}],
    "an_scrutins__decompte_groupe": [
        {"scrutin": "VT1", "organe": "POG", "position_majoritaire": "contre", "pour": 3, "contre": 30,
         "abstentions": 0, "non_votants": 0, "nombre_membres": 38},
        # Q30 : « contre » publié pour 19 pour, 7 contre : position du groupe non établie.
        {"scrutin": "VT2", "organe": "POG", "position_majoritaire": "contre", "pour": 19, "contre": 7,
         "abstentions": 7, "non_votants": 0, "nombre_membres": 38}],
    "parole_personne": [
        _parole("101", "2025-01-30", "Le logement des étudiants est une urgence nationale."),
        _parole("102", "2025-01-30", "La parole est à Mme la ministre.", preside=True),
        _parole("103", "2026-03-04", "Nous voterons ce texte sur la présence médicale.", sujet=None)],
    "question_personne": [
        {"acteur": "PA1", "question": "QANR5L17QE1", "type": "ecrite", "type_code": "QE", "date": "2025-02-04",
         "date_nature": "question_publiee_au_jo", "ministere": "PO9", "ministere_libelle": "Logement",
         "ministere_abrege": None, "ministere_attributaire": "PO9", "ministere_attributaire_libelle": "Logement",
         "rubrique": "logement", "tete_analyse": "Résidences universitaires", "analyses": ["Manque de places"],
         "date_reponse": None, "cloture": None, "date_cloture": None, "groupe_source": None,
         "legislature": "17", "numero": "1", "source_url": None,
         "raison_source_url": "adresse_non_publiee_dans_les_donnees"}],
}


def _composer(tmp_path, tables=TABLES, **remplace):
    os.makedirs(tmp_path / "z2", exist_ok=True)
    ctx = Contexte(str(tmp_path / "z2"), str(tmp_path / "z3"), date_reference=AU)
    for nom, lignes in {**tables, **remplace}.items():
        if lignes is not None:
            ctx.con.register(nom, pa.Table.from_pylist(lignes))
    ecr = Ecrivain(str(tmp_path / "site"), "essai")
    composeur.composer(ctx, ecr)
    man = ecr.clore()
    return ecr, man, os.path.join(str(tmp_path / "site"), "donnees", "essai")


def _lire(racine, chemin):
    with gzip.open(os.path.join(racine, chemin)) as f:
        return json.load(f)


def _rows(d):
    return [dict(zip(d["colonnes"], l)) for l in d["lignes"]]


@pytest.fixture(scope="module")
def sortie(tmp_path_factory):
    return _composer(tmp_path_factory.mktemp("cand"))


def test_une_fiche_par_candidat_publie_et_controles(sortie):
    ecr, man, racine = sortie
    assert [f["fiche"] for f in man["fiches"]] == ["candidat/alice-martin", "candidat/eric-zemmour",
                                                    "candidat/jean-ancien"]          # retiré : pas de fiche
    c = Controles(racine)
    c.c2_liens({f["fiche"] for f in man["fiches"]} | {"legislature/16", "legislature/17", "gouvernement/beta"})
    c.c4_interdits()
    assert c.bilan()["publication_autorisee"], c.bilan()


def test_entete_identite_groupe_et_liens_publies(sortie):
    _, _, racine = sortie
    f = _lire(racine, "candidats/alice-martin/fiche.json.gz")
    assert f["titre"] == "Alice Martin"
    assert f["personne"]["profession"] == {"valeur": "Reporter", "source": "an",
                                           "source_point": "an-amo30-l17", "raison": None}
    g = f["groupe_actuel"]
    # Sans lignée publiée pour ce groupe : pas de lien, la raison est écrite.
    assert g["sigle"] == "ECOS" and g["lien"] is None and g["raison_lien"] == "groupe sans lignée publiée"
    car = _rows(f["en_bref"]["carriere"])
    # XIVe à XVIIe publiées : chaque période renvoie à sa législature.
    assert [l["lien"] for l in car] == ["legislature/16", "legislature/17", "legislature/17"]
    per = _rows(f["periodes"])
    assert [p["lien"] for p in per] == [None, "gouvernement/beta"]
    inst = {i["institution"]: i["statut"] for i in f["en_bref"]["institutions"]}
    assert inst["assemblee_avant_2002"] == "borne_historique"
    assert inst["parlement_europeen"] == inst["local"] == "non_collecte"
    for c in f["en_bref"]["compteurs"]:
        assert c["au"] == AU


def test_groupe_actuel_renvoie_a_sa_lignee(tmp_path):
    """Le groupe actuel d'un député renvoie à la fiche de sa lignée (R-LIGNEE), seule cible publiée."""
    lignee = [{"lignee": "lig:000016", "adresse": "ecologiste-et-social", "publiee": True}]
    maillon = [{"lignee": "lig:000016", "maillon": "grp:17:POG", "organes": ["POG"], "affiche": True}]
    _, man, racine = _composer(tmp_path, lignee=lignee, lignee_maillon=maillon)
    g = _lire(racine, "candidats/alice-martin/fiche.json.gz")["groupe_actuel"]
    assert g["lien"] == "lignee/ecologiste-et-social" and g["raison_lien"] is None
    c = Controles(racine)
    c.c2_liens({f["fiche"] for f in man["fiches"]} | {"legislature/16", "legislature/17", "gouvernement/beta"})
    assert not c.bilan()["publication_autorisee"]          # la lignée n'est pas composée ici
    c = Controles(racine)
    c.c2_liens({f["fiche"] for f in man["fiches"]} | {"legislature/16", "legislature/17", "gouvernement/beta",
                                                       "lignee/ecologiste-et-social"})
    assert c.bilan()["publication_autorisee"]


def test_chaque_section_a_sa_couverture(sortie):
    _, man, racine = sortie
    for fi in man["fiches"]:
        for nom in fi["sections"]:
            d = _lire(racine, f"candidats/{fi['adresse']}/{nom}.json.gz")
            c = d["couverture"]
            assert c["statut"] in STATUTS, (nom, c)
            assert c["points_acces"], (nom, c)
            assert "detail" in c
            if not d["lignes"]:
                assert c["statut"] in ("complet", "relu_aucun", "non_collecte", "hors_perimetre"), (nom, c)


def test_sans_identifiant_parlementaire(sortie):
    _, man, racine = sortie
    f = _lire(racine, "candidats/eric-zemmour/fiche.json.gz")
    assert f["perimetre_activite"]["raison"] == "aucun_identifiant_parlementaire"
    assert all(c["statut"] == "hors_perimetre" for c in f["couverture"])
    act = [c for c in f["en_bref"]["compteurs"] if c["perimetre"] == "XIVe à la XVIIe législature"]
    assert act and all(c["valeur"] is None for c in act)          # jamais 0
    fi = next(x for x in man["fiches"] if x["adresse"] == "eric-zemmour")
    assert set(fi["sections"]) == {"fonctions", "fonctions-periodes", "proposes", "amendements", "votes",
                                   "votes-motions", "divergences", "paroles", "questions"}
    assert f["filtres"]["mot"]["tranches"] == []


def test_activite_anterieure_hors_perimetre_sans_zero(sortie):
    _, _, racine = sortie
    f = _lire(racine, "candidats/jean-ancien/fiche.json.gz")
    assert f["perimetre_activite"]["statut"] == "hors_perimetre"
    assert f["perimetre_activite"]["jours_dans_le_perimetre"] == 0
    assert f["perimetre_activite"]["depuis"] == "2012-06-20"
    comptes = {(c["institution"], c["famille"]): c["valeur"] for c in f["en_bref"]["compteurs"]}
    assert comptes[("assemblee", "positions_textes")] is None
    assert comptes[("assemblee", "prises_de_parole")] is None
    assert comptes[("assemblee", "mandats")] == 1
    assert comptes[("parlement_europeen", "mandats")] is None


def test_textes_portes_publiables_xviie_et_initiative_gouvernementale(sortie):
    _, _, racine = sortie
    d = _lire(racine, "candidats/alice-martin/proposes.json.gz")
    t = _rows(d)
    assert [(x["dossier"], x["role"]) for x in t] == [("DL4", "initiative_gouvernementale"),
                                                       ("DL1", "auteur"),
                                                       ("DL3", "initiative_gouvernementale")]
    assert {x["dossier"]: x["lien"] for x in t} == {"DL4": None, "DL1": None, "DL3": "gouvernement/beta"}
    sel = d["couverture"]["selection"]
    assert sel["anterieurs_au_perimetre"] == 1 and sel["ecartes"] == {"pas_encore_examine_en_commission": 1}


def test_amendements_irrecevables_et_signatures_a_part_exposes_separes(sortie):
    _, _, racine = sortie
    d = _lire(racine, "candidats/alice-martin/amendements.json.gz")
    agr = {x["annee"]: x for x in _rows(d)}
    assert agr["2025"]["nb_amendements"] == 1 and agr["2025"]["nb_irrecevables_40"] == 1
    assert agr["2025"]["nb_signatures_cosignataire"] == 1
    assert agr["2026"]["nb_amendements"] == 0 and agr["2026"]["nb_irrecevables_45"] == 1
    assert not any("adopt" in c for c in d["colonnes"])                  # aucun taux, aucun compte d'adoptés
    liste = _rows(_lire(racine, "candidats/alice-martin/amendements-2025.json.gz"))
    assert "expose" not in liste[0]
    am1 = next(x for x in liste if x["amendement"] == "AM1")
    ex = _rows(_lire(racine, "candidats/alice-martin/" + am1["expose_fichier"]))[am1["expose_ligne"]]
    assert ex["expose"] == ("Cet amendement vise à garantir la présence d’un logement pour chaque "
                            "étudiant boursier.")
    am2 = next(x for x in liste if x["amendement"] == "AM2")
    assert am2["expose_fichier"] is None and am2["raison_sans_expose"] == "ni exposé ni dispositif publiés"
    f = _lire(racine, "candidats/alice-martin/fiche.json.gz")
    comptes = {c["famille"]: c["valeur"] for c in f["en_bref"]["compteurs"]}
    assert comptes["amendements_auteur_principal"] == 1 and comptes["signatures_cosignataire"] == 1


def test_votes_une_position_par_texte_motions_a_part_49_3_jamais_position(sortie):
    _, _, racine = sortie
    v = _rows(_lire(racine, "candidats/alice-martin/votes.json.gz"))
    assert [x["scrutin"] for x in v] == ["VT1", "VT2"]
    assert {x["position"] for x in v} <= {"pour", "contre", "abstention", "non_votant"}
    assert next(x for x in v if x["scrutin"] == "VT2")["dossier_par_49_3"] is True
    m = _rows(_lire(racine, "candidats/alice-martin/votes-motions.json.gz"))
    assert [x["scrutin"] for x in m] == ["VT3"]


def test_divergences_bande_sans_total_et_q30(sortie):
    _, _, racine = sortie
    d = _lire(racine, "candidats/alice-martin/divergences.json.gz")
    rows = _rows(d)
    assert len(rows) == 1 and rows[0]["diverge"] is True
    txt = json.dumps(d, ensure_ascii=False)
    assert "nb_divergences" not in txt and "total_divergences" not in txt
    c = d["couverture"]
    assert c["numerateur"] == 1 and c["denominateur"] == 2
    assert c["ecartes"] == [{"raison": "position_publiee_contredite_par_le_decompte", "positions": 1}]
    assert "Q30" in c["detail"]


def test_paroles_index_presidence_et_extraits_par_semestre(sortie):
    _, man, racine = sortie
    d = _lire(racine, "candidats/alice-martin/paroles.json.gz")
    rows = _rows(d)
    assert "extrait" not in d["colonnes"]
    assert [r["preside"] for r in rows] == [False, True, False]
    assert d["par_qualite"] == {"depute": 2, "presidence_de_seance": 1}
    r = rows[2]
    ex = _rows(_lire(racine, "candidats/alice-martin/" + r["fichier"]))[r["ligne"]]
    assert r["fichier"] == "paroles-textes-2026-s1.json.gz" and ex["source_url"].endswith("#103")
    suj = {s[0]: s for s in d["sujets"]["lignes"]}
    assert suj[r["sujet_id"]][2] == "Intitulé non publié"
    f = _lire(racine, "candidats/alice-martin/fiche.json.gz")
    comptes = {c["famille"]: c["valeur"] for c in f["en_bref"]["compteurs"]}
    assert comptes["prises_de_parole"] == 2 and comptes["presidence_de_seance"] == 1


def test_filtre_par_mot_tranches_et_renvois(sortie):
    _, _, racine = sortie
    f = _lire(racine, "candidats/alice-martin/fiche.json.gz")
    assert "lo" in f["filtres"]["mot"]["tranches"] and "pr" in f["filtres"]["mot"]["tranches"]
    tr = _lire(racine, "candidats/alice-martin/mots/lo.json.gz")
    ren = {m: r for m, r in tr["lignes"]}
    fichiers = {tr["fichiers"][i]: rs for i, rs in ren["logement"]}
    assert fichiers["proposes.json.gz"] == [1]                         # titre du texte DL1
    assert any(k.startswith("exposes-2025") for k in fichiers)        # exposé de AM1
    assert any(k.startswith("paroles-textes-2025-s1") for k in fichiers)
    assert "questions.json.gz" in fichiers and "votes.json.gz" in fichiers
    # « présence » est un mot indexé (valeur), jamais une clé : C4 ne le prend pas pour un taux.
    pr = {m for m, _ in _lire(racine, "candidats/alice-martin/mots/pr.json.gz")["lignes"]}
    assert "presence" in pr


def test_tables_absentes_couverture_le_dit(tmp_path):
    tables = {k: v for k, v in TABLES.items() if k in ("candidat", "personne_identite", "legislature",
                                                       "gouvernement", "gouvernement_legislature")}
    _, man, racine = _composer(tmp_path, tables)
    f = _lire(racine, "candidats/alice-martin/fiche.json.gz")
    st = {c["section"]: c["statut"] for c in f["couverture"]}
    assert st["votes"] == st["paroles"] == st["divergences"] == "non_relu"


def test_depute_de_la_xive_seulement_paroles_hors_perimetre(tmp_path):
    """Un député de la XIVe seulement : votes, amendements, textes et questions sont dans le
    périmètre (XIVe à XVIIe) ; les prises de parole ne sont lues qu'à partir de la XVe : « hors
    périmètre », sans compte (pas même 0), et la limite le dit."""
    car = [x for x in TABLES["carriere"] if x["per"] != "per:000003"] + [
        _car("per:000003", "2012-06-20", "2017-06-20", 14, "legislature/14", mandat="PM3", acteur="PA3")]
    _, _, racine = _composer(tmp_path, carriere=car)
    f = _lire(racine, "candidats/jean-ancien/fiche.json.gz")
    assert f["perimetre_activite"]["statut"] == "complet"
    comptes = {(c["institution"], c["famille"]): c for c in f["en_bref"]["compteurs"]}
    assert comptes[("assemblee", "positions_textes")]["valeur"] == 0        # vrai zéro : lu
    assert comptes[("assemblee", "prises_de_parole")]["valeur"] is None     # pas lu : jamais 0
    assert comptes[("assemblee", "prises_de_parole")]["perimetre"] == "XVe à la XVIIe législature"
    p = _lire(racine, "candidats/jean-ancien/paroles.json.gz")["couverture"]
    assert p["statut"] == "hors_perimetre" and p["raison"] == "activite_anterieure_au_perimetre"
    assert "paroles" in {l["famille"] for l in f["limites"]}


def test_activite_en_partie_avant_le_perimetre_partiel(tmp_path):
    """Un député de la XIIIe puis de la XIVe : son activité est lue depuis le 20/06/2012 (`partiel`),
    ses comptes portent sur cette partie et peuvent valoir zéro."""
    car = [x for x in TABLES["carriere"] if x["per"] != "per:000003"] + [
        _car("per:000003", "2007-06-20", "2012-06-19", 13, None, mandat="PM3", acteur="PA3"),
        _car("per:000003", "2012-06-20", "2017-06-20", 14, "legislature/14", mandat="PM4", acteur="PA3")]
    _, _, racine = _composer(tmp_path, carriere=car)
    f = _lire(racine, "candidats/jean-ancien/fiche.json.gz")
    assert f["perimetre_activite"]["statut"] == "partiel"
    assert f["perimetre_activite"]["jours_dans_le_perimetre"] > 0
    comptes = {(c["institution"], c["famille"]): c for c in f["en_bref"]["compteurs"]}
    assert comptes[("assemblee", "positions_textes")]["valeur"] == 0
    assert _lire(racine, "candidats/jean-ancien/votes.json.gz")["couverture"]["statut"] == "partiel"
