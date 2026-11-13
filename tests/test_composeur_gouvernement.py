"""Composeur « gouvernement » (cahier 4.4) sur de petites tables Z3 écrites à la main.

Quatre gouvernements : Alpha (XIIIe seulement, avant le périmètre : pas de fiche), Beta (XVIe puis XVIIe), Gamma (XVIIe,
clos), Delta II (XVIIe, en cours, seul couvert en partie par le Journal officiel). Les législatures
sont celles de la source (XIVe à XVIIe) : Beta est entier dans le périmètre (dossiers depuis la XIVe,
comptes rendus depuis la XVe)."""
import gzip
import json
import os

import pyarrow as pa
import pytest

from empreinte_src.composeurs import gouvernement as composeur
from empreinte_src.composition import Ecrivain
from empreinte_src.controles import Controles
from empreinte_src.liaison import Contexte

STATUTS = {"complet", "partiel", "trou_source", "borne_historique", "non_collecte", "panne", "en_cours",
           "relu_aucun", "non_relu", "hors_perimetre"}
AU = "2026-11-06"
URL_CR = "https://www.assemblee-nationale.fr/dyn/17/comptes-rendus/seance/"


def _mg(gouv, acteur, portefeuille, ministere, debut, fin=None, qualite="Ministre", tutelle=None,
        statut="sans_objet", pm=False, preseance=30, mandat=None, raison=None):
    return {"gouvernement": gouv, "acteur": acteur, "portefeuille": portefeuille, "qualite": qualite,
            "ministere": ministere, "ministere_tutelle": tutelle, "tutelle_statut": statut,
            "raison_tutelle": raison, "debut": debut, "fin": fin, "premier_ministre": pm,
            "preseance": preseance, "mandat": mandat or f"PM{acteur}{ministere}", "source_url": None}


def _parole(gouv, acteur, cr, ids, date, sujet, type_sujet="texte", dossier=None, inter=False):
    return {"gouvernement": gouv, "acteur": acteur, "compte_rendu": cr, "id_syceron": ids, "date": date,
            "sujet": sujet, "dossier": dossier, "statut_sujet": "etabli" if sujet else "intitule_non_publie",
            "type_sujet": type_sujet, "qualite_source": "compte_rendu", "qualite_ecrite_libelle": "ministre",
            "interruption": inter, "source_url": f"{URL_CR}{cr}#{ids}"}


def _acte(uid, date, gouv, dans, ministere="Ministère de la culture", nature="ARRETE", nomin=False,
          loi=False):
    return {"acte": uid, "id_jorf": uid, "date_publication": date, "nature": nature, "numero": None,
            "nor": f"NOR{uid}", "titre": f"Arrêté {uid}", "ministere_libelle": ministere,
            "ministere_statut": "non_etabli" if ministere else "non_precise", "ministere_normalise": None,
            "mesure_nominative": nomin, "cite_une_loi": loi, "nb_lois_citees": int(loi),
            "est_rectificatif": False, "rectificatif_de": None, "num_jo": "0233",
            "source_url": f"https://www.legifrance.gouv.fr/jorf/id/{uid}", "gouvernement": gouv,
            "dans_periode_couverte": dans}


TABLES = {
    "legislature": [
        {"numero": 14, "organe": "PO644420", "debut": "2012-06-20", "fin": "2017-06-20", "en_cours": False},
        {"numero": 15, "organe": "PO717460", "debut": "2017-06-21", "fin": "2022-06-21", "en_cours": False},
        {"numero": 16, "organe": "PO800538", "debut": "2022-06-22", "fin": "2024-06-09", "en_cours": False},
        {"numero": 17, "organe": "PO838901", "debut": "2024-07-18", "fin": None, "en_cours": True}],
    "gouvernement": [
        {"organe": "PO1", "nom": "Alpha", "adresse": "alpha", "debut": "2022-05-17", "fin": "2024-01-09",
         "en_cours": False, "rang": 1, "source_url": None},
        {"organe": "PO2", "nom": "Beta", "adresse": "beta", "debut": "2024-01-10", "fin": "2024-09-05",
         "en_cours": False, "rang": 2, "source_url": None},
        {"organe": "PO3", "nom": "Gamma", "adresse": "gamma", "debut": "2024-09-06", "fin": "2024-12-13",
         "en_cours": False, "rang": 3, "source_url": None},
        {"organe": "PO4", "nom": "Delta II", "adresse": "delta-ii", "debut": "2025-10-11", "fin": None,
         "en_cours": True, "rang": 4, "source_url": None}],
    "gouvernement_legislature": [
        {"gouvernement": "PO1", "legislature": 13, "debut": "2022-06-22", "fin": "2024-01-09"},
        {"gouvernement": "PO2", "legislature": 16, "debut": "2024-01-10", "fin": "2024-06-09"},
        {"gouvernement": "PO2", "legislature": 17, "debut": "2024-07-01", "fin": "2024-09-05"},
        {"gouvernement": "PO3", "legislature": 17, "debut": "2024-09-06", "fin": "2024-12-13"},
        {"gouvernement": "PO4", "legislature": 17, "debut": "2025-10-11", "fin": None}],
    "membre_gouvernement": [
        _mg("PO2", "PA1", "Premier ministre", "M21", "2024-01-10", "2024-09-05", "Premier ministre", pm=True,
            preseance=1),
        _mg("PO2", "PA2", "Ministère de la culture", "M22", "2024-01-12", "2024-09-05"),
        # Gamma : le Premier ministre seul, puis ses ministres dix jours plus tard.
        _mg("PO3", "PA10", "Premier ministre", "M31", "2024-09-06", "2024-12-13", "Premier ministre",
            pm=True, preseance=1),
        _mg("PO3", "PA12", "Ministère de l'intérieur", "M33", "2024-09-21", "2024-12-13", preseance=10),
        _mg("PO3", "PA11", "Ministère de la culture", "M32", "2024-09-21", "2024-12-13"),
        _mg("PO3", "PA13", "Ministère délégué auprès du ministre de l'intérieur", "M34", "2024-09-21",
            "2024-12-13", "Ministre délégué", tutelle="M33", statut="etabli", preseance=40),
        _mg("PO3", "PA14", "Secrétariat d'État auprès des ministres", "M35", "2024-09-21", "2024-12-13",
            "Secrétaire d'État", statut="non_etabli", preseance=50, raison="le libellé désigne plusieurs ministres"),
        _mg("PO3", "PA15", "Ministère délégué auprès du Premier ministre", "M36", "2024-09-21", "2024-12-13",
            "Ministre délégué", tutelle="M31", statut="etabli", preseance=40),
        # Delta II : remaniement, la culture change d'organe sans changer de libellé.
        _mg("PO4", "PA20", "Premier ministre", "M41", "2025-10-11", None, "Premier ministre", pm=True,
            preseance=1),
        _mg("PO4", "PA21", "Ministère de la culture", "M42", "2025-10-13", "2026-02-26"),
        _mg("PO4", "PA22", "Ministère de la culture", "M43", "2026-02-27", None),
        _mg("PO4", "PA23", "Ministère des armées", "M44", "2025-10-13", None)],
    "mandat_ouvert_organe_clos": [{"mandat": "PM15999", "organe": "PO3"}],
    "vague": [
        {"gouvernement": "PO3", "vague": 1, "debut": "2024-09-06", "fin": "2024-09-06", "nb_nominations": 1,
         "nb_personnes": 1, "nb_arrivees": 1, "nb_departs": 0, "nb_changements": 0, "nature": "formation"},
        {"gouvernement": "PO3", "vague": 2, "debut": "2024-09-21", "fin": "2024-09-21", "nb_nominations": 5,
         "nb_personnes": 5, "nb_arrivees": 5, "nb_departs": 0, "nb_changements": 0, "nature": "formation"}],
    "groupe": [
        {"organe": "PO900", "legislature": 17, "sigle": "EPR", "libelle": "Ensemble pour la République",
         "debut": "2024-07-18", "fin": None, "position_declaree": "non_declaree"},
        {"organe": "PO901", "legislature": 17, "sigle": "AD", "libelle": "À Droite", "debut": "2024-07-18",
         "fin": "2024-09-11", "position_declaree": "non_declaree"},
        {"organe": "PO800", "legislature": 16, "sigle": "REN", "libelle": "Renaissance", "debut": "2022-06-28",
         "fin": "2024-06-09", "position_declaree": "majoritaire"}],
    "projet_gouvernement": [
        {"gouvernement": "PO3", "dossier": "DL1", "document": "PRJLANR5L17B0001", "titre_dossier": "Projet A",
         "date_depot": "2024-10-01", "chambre_depot": "AN", "procedure_libelle": "Projet de loi ordinaire",
         "source_url": "https://www.assemblee-nationale.fr/dyn/17/dossiers/a"},
        {"gouvernement": "PO3", "dossier": "DL2", "document": "PRJLSNR5S1", "titre_dossier": "Projet B",
         "date_depot": "2024-11-01", "chambre_depot": "SN", "procedure_libelle": "Projet de loi ordinaire",
         "source_url": "https://www.assemblee-nationale.fr/dyn/17/dossiers/b"}],
    "matiere": [
        {"dossier": "DL1", "statut": "assemblee", "libelle": "Commission des finances", "commission": "PO59048"},
        {"dossier": "DL2", "statut": "senat_seulement", "libelle": "Saisi au Sénat seulement",
         "commission": None}],
    "etat_dossier": [
        {"dossier": "DL1", "legislature": 17, "sort": "promulgue", "date_sort": "2024-12-01",
         "raison_sort": None, "par_49_3": True, "adopte_par_49_3": True, "nb_engagements_49_3": 1,
         "numero_loi": "2024-1", "date_promulgation": "2024-12-01", "url_loi": None,
         "etape_atteinte": "promulgue"},
        {"dossier": "DL2", "legislature": 17, "sort": "non_connu", "date_sort": None,
         "raison_sort": "aucune_decision_en_seance", "par_49_3": False, "adopte_par_49_3": False,
         "nb_engagements_49_3": 0, "numero_loi": None, "date_promulgation": None, "url_loi": None,
         "etape_atteinte": "depot"}],
    "engagement_49_3": [
        {"gouvernement": "PO3", "acte": "L17-VD1", "date": "2024-11-20", "etape": "AN1", "declaration": "DECL1",
         "dossier": "DL1", "titre_dossier": "Projet A", "procedure_code": "1",
         "procedure_libelle": "Projet de loi ordinaire", "source_url": "https://exemple.invalid/a"},
        {"gouvernement": "PO3", "acte": "L17-VD1", "date": "2024-11-20", "etape": "AN21", "declaration": "DECL1",
         "dossier": "DL49", "titre_dossier": "Engagement de la responsabilité…", "procedure_code": "13",
         "procedure_libelle": "Engagement de la responsabilité gouvernementale",
         "source_url": "https://exemple.invalid/49"}],
    "parole_gouvernement": [
        _parole("PO3", "PA11", "CR1", "10", "2024-10-01", "Projet A", dossier="DL1"),
        _parole("PO3", "PA12", "CR1", "11", "2024-10-01", "Projet A", dossier="DL1", inter=True),
        _parole("PO3", "PA11", "CR2", "20", "2024-10-02", "Question sur le patrimoine", "question"),
        _parole("PO3", "PA13", "CR3", "30", "2024-12-02", None, "hors_point")],
    "an_comptes_rendus__intervention": [
        {"compte_rendu": "CR1", "id_syceron": "10", "texte": "Mesdames, messieurs " + "x" * 400,
         "licence": "etalab-2.0", "prov_point": "an-syceron-l17"},
        {"compte_rendu": "CR1", "id_syceron": "11", "texte": "Très bien !", "licence": "etalab-2.0",
         "prov_point": "an-syceron-l17"},
        {"compte_rendu": "CR2", "id_syceron": "20", "texte": "Le patrimoine\n  est  protégé.",
         "licence": "etalab-2.0", "prov_point": "an-syceron-l17"},
        {"compte_rendu": "CR3", "id_syceron": "30", "texte": "Bref.", "licence": "etalab-2.0",
         "prov_point": "an-syceron-l17"}],
    "an_acteurs__identite_source": [
        {"uid": f"PA{n}", "prenom": p, "nom": nm, "nom_alpha": nm, "prov_point": "an-amo30-l17"}
        for n, p, nm in [(1, "Gabriel", "Attal"), (2, "Rachida", "Dati"), (10, "Michel", "Barnier"),
                         (11, "Rachida", "Dati"), (12, "Bruno", "Retailleau"), (13, "Nicolas", "Daragon"),
                         (14, "Ana", "Zed"), (15, "Maud", "Bregeon"), (20, "Sébastien", "Lecornu"),
                         (21, "Rachida", "Dati"), (22, "Catherine", "Pégard"), (23, "Catherine", "Vautrin")]],
    "an_acteurs__mandat": [{"prov_point": "an-amo30-l17", "licence": "etalab-2.0"}],
    "an_dossiers__dossier": [{"prov_point": "an-dossiers-l17", "licence": "etalab-2.0"}],
    "jo_actes__acte_reglementaire": [{"prov_point": "jo-livraisons", "licence": "etalab-2.0"}],
    "couverture_jo": [{"premiere_publication": "2026-10-06", "derniere_publication": "2026-11-06"}],
    "couverture_jo_gouvernement": [
        {"gouvernement": "PO2", "couvert_du": None, "couvert_au": None, "statut": "non_collecte"},
        {"gouvernement": "PO3", "couvert_du": None, "couvert_au": None, "statut": "non_collecte"},
        {"gouvernement": "PO4", "couvert_du": "2026-10-06", "couvert_au": "2026-11-06", "statut": "partiel"}],
    "acte_rattache": [
        _acte("J1", "2026-10-06", "PO4", True, loi=True),
        _acte("J2", "2026-10-07", "PO4", True, nature="DECRET", nomin=True),
        _acte("J3", "2026-11-02", "PO4", True, ministere=None, nature="LOI"),
        _acte("J4", "2025-12-01", "PO4", False),              # redélivré : hors période couverte
        _acte("J5", "2024-10-01", "PO3", False)],
    "acte_loi_citee": [
        {"acte": "J1", "numero_loi": "2021-1754", "type_loi": "loi", "loi_jorf": "JORFTEXT1",
         "loi_identifiee_par": "lien_jo", "loi_source_url": "https://www.legifrance.gouv.fr/jorf/id/JORFTEXT1",
         "rang": 1},
        {"acte": "J5", "numero_loi": "2000-1", "type_loi": "loi", "loi_jorf": None, "loi_identifiee_par": None,
         "loi_source_url": None, "rang": 1}],
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
    return _composer(tmp_path_factory.mktemp("gouv"))


def test_une_fiche_par_gouvernement_de_la_xviie_et_liens_publies(sortie):
    ecr, man, racine = sortie
    assert [f["fiche"] for f in man["fiches"]] == ["gouvernement/beta", "gouvernement/gamma",
                                                    "gouvernement/delta-ii"]
    beta = _lire(racine, "gouvernements/beta/fiche.json.gz")
    assert beta["titre"] == "Gouvernement Beta"
    frise = beta["en_bref"]["frise"]
    assert "lien" not in frise["precedent"] and frise["precedent"]["nom"] == "Alpha"   # pas de fiche
    assert frise["suivant"]["lien"] == "gouvernement/gamma"
    legs = beta["en_bref"]["legislatures"]
    assert [l.get("lien") for l in legs] == ["legislature/16", "legislature/17"]   # XIVe à XVIIe publiées
    delta = _lire(racine, "gouvernements/delta-ii/fiche.json.gz")
    assert delta["en_bref"]["frise"]["suivant"] is None
    assert delta["gouvernement"]["en_cours"] and delta["gouvernement"]["duree_au"] == AU
    assert delta["gouvernement"]["duree_jours"] == 392
    # C2 et C4 passent : liens seulement vers des fiches publiées, aucune donnée interdite.
    c = Controles(racine)
    c.c2_liens({f["fiche"] for f in man["fiches"]} | {"legislature/16", "legislature/17"})
    c.c4_interdits()
    assert c.bilan()["publication_autorisee"], c.bilan()


def test_chaque_section_a_sa_couverture(sortie):
    ecr, man, racine = sortie
    for fi in man["fiches"]:
        for nom in fi["sections"]:
            d = _lire(racine, f"gouvernements/{fi['fiche'].split('/')[1]}/{nom}.json.gz")
            c = d["couverture"]
            assert c["statut"] in STATUTS, (nom, c)
            assert c["points_acces"] is not None and "detail" in c
            # une liste vide n'est servie que complète, relue sans rien, ou dite non collectée
            if not d["lignes"]:
                assert c["statut"] in ("complet", "relu_aucun", "non_collecte"), (nom, c)
    fiche = _lire(racine, "gouvernements/gamma/fiche.json.gz")
    assert {c["section"] for c in fiche["couverture"]} >= {"composition", "paroles", "deposes",
                                                          "procedure-49-3", "actes", "budgets"}
    assert fiche["licences"] == ["etalab-2.0"]


def test_composition_ordre_protocolaire_et_tutelles(sortie):
    _, _, racine = sortie
    d = _lire(racine, "gouvernements/gamma/composition.json.gz")
    rows = _rows(d)
    assert [(r["nom"], r["rattachement"]) for r in rows] == [
        ("Michel Barnier", "titulaire"),             # Premier ministre en tête
        ("Maud Bregeon", "rattache"),                # délégué auprès du Premier ministre
        ("Bruno Retailleau", "titulaire"),           # préséance 10
        ("Nicolas Daragon", "rattache"),             # délégué rattaché à l'intérieur
        ("Rachida Dati", "titulaire"),               # préséance 30
        ("Ana Zed", "non_etabli")]                   # rattachement non établi, à part
    zed = rows[-1]
    assert zed["ministere_groupe"] is None and zed["raison_tutelle"]
    assert rows[3]["ministere_tutelle_libelle"] == "Ministère de l'intérieur"
    assert "ordre" in d
    entete = _lire(racine, "gouvernements/gamma/fiche.json.gz")["en_bref"]["composition"]
    assert entete["nb_membres"] == 6
    # Minimum lu après la formation (Premier ministre seul du 06 au 20/09, puis ses ministres) :
    # 6, pas 1 (décision du 07/11/2026).
    assert entete["effectif_minimal"] == {"valeur": 6, "periodes": [{"du": "2024-09-21", "au": "2024-12-13"}]}
    assert entete["effectif_maximal"]["valeur"] == 6
    assert entete["nb_vagues"] == 2 and entete["remaniements"] == 0 and entete["remaniements_definition"]
    assert [v["nature"] for v in entete["vagues"]] == ["formation", "formation"]
    assert entete["tutelle"] == {"etablie": 2, "a_rattacher": 3}
    limites = _lire(racine, "gouvernements/gamma/fiche.json.gz")["limites"]
    assert any(l["famille"] == "composition" and l["mandats"] == ["PM15999"] for l in limites)


def test_composition_ministere_recree_reste_un_groupe(sortie):
    _, _, racine = sortie
    rows = _rows(_lire(racine, "gouvernements/delta-ii/composition.json.gz"))
    assert [r["nom"] for r in rows] == ["Sébastien Lecornu", "Rachida Dati", "Catherine Pégard",
                                        "Catherine Vautrin"]
    assert rows[1]["ministere_groupe_libelle"] == rows[2]["ministere_groupe_libelle"]
    assert rows[1]["ministere_groupe"] != rows[2]["ministere_groupe"]


def test_majorite_non_declaree_jamais_deduite(sortie):
    _, _, racine = sortie
    gamma = _lire(racine, "gouvernements/gamma/fiche.json.gz")
    m = gamma["en_bref"]["majorite"]
    assert m["statut"] == "non_declaree" and m["libelle"] == "non déclarée"
    assert [g["sigle"] for g in m["groupes"]] == ["AD", "EPR"]       # alphabétique, accents ignorés
    assert m["nb_groupes_declarant"] == 0
    assert any(l["famille"] == "majorite" and l["statut"] == "relu_aucun" for l in gamma["limites"])
    beta = _lire(racine, "gouvernements/beta/fiche.json.gz")["en_bref"]["majorite"]
    assert beta["positions_declarees"] == {"majoritaire": ["REN"]}  # la source le déclare (XVIe)


def test_deposes_et_49_3_fait_de_procedure(sortie):
    _, _, racine = sortie
    rows = _rows(_lire(racine, "gouvernements/gamma/deposes.json.gz"))
    assert [r["dossier"] for r in rows] == ["DL1", "DL2"]
    assert rows[0]["par_49_3"] is True and rows[0]["matiere"] == "Commission des finances"
    assert rows[1]["matiere"] == "Saisi au Sénat seulement" and rows[1]["ministere_porteur"] is None
    b = _lire(racine, "gouvernements/gamma/fiche.json.gz")["en_bref"]
    assert {k: b["projets_de_loi"][k] for k in ("deposes", "adoptes", "promulgues", "au")} == \
        {"deposes": 2, "adoptes": 1, "promulgues": 1, "au": AU}
    assert b["procedure_49_3"]["nb_engagements"] == 1 and b["procedure_49_3"]["nb_textes"] == 1
    e = _lire(racine, "gouvernements/gamma/procedure-49-3.json.gz")
    assert "position" not in e["colonnes"] and len(e["lignes"]) == 2


def test_zero_hors_couverture_complete_reste_null(sortie):
    _, _, racine = sortie
    b = _lire(racine, "gouvernements/beta/fiche.json.gz")["en_bref"]
    # Beta commence en XVIe, dans le périmètre : ses zéros sont de vrais zéros.
    assert b["paroles"]["nb_prises_de_parole"] == 0 and b["paroles"]["couverture"] == "complet"
    assert b["projets_de_loi"]["deposes"] == 0 and b["projets_de_loi"]["couverture"] == "complet"
    # Delta II, entièrement en XVIIe : 0 projet est un vrai zéro.
    d = _lire(racine, "gouvernements/delta-ii/fiche.json.gz")["en_bref"]
    assert d["projets_de_loi"]["deposes"] == 0 and d["projets_de_loi"]["couverture"] == "complet"


def test_paroles_index_leger_et_extraits_a_part(sortie):
    ecr, _, racine = sortie
    d = _lire(racine, "gouvernements/gamma/paroles.json.gz")
    idx = _rows(d)
    assert "extrait" not in d["colonnes"]
    assert [r["sujet_libelle"] for r in idx] == ["Projet A", "Question sur le patrimoine",
                                                 "Intitulé non publié"]
    assert idx[0]["nb_membres_intervenus"] == 2 and idx[0]["membres"] == ["PA11", "PA12"]
    assert idx[0]["dont_interruptions"] == 1 and idx[0]["nb_seances"] == 1
    assert d["personnes"]["PA11"] == "Rachida Dati"
    ex = _rows(_lire(racine, f"gouvernements/gamma/{idx[0]['fichiers_extraits'][0]}"))
    long_ = [x for x in ex if x["id_syceron"] == "10"][0]
    assert len(long_["extrait"]) == composeur.LONGUEUR_EXTRAIT and long_["extrait_tronque"]
    assert [x for x in ex if x["id_syceron"] == "20"][0]["extrait"] == "Le patrimoine est protégé."
    assert all(x["source_url"].startswith(URL_CR) for x in ex)
    b = _lire(racine, "gouvernements/gamma/fiche.json.gz")["en_bref"]["paroles"]
    assert (b["nb_membres_intervenus"], b["nb_membres"], b["nb_sujets"]) == (3, 6, 3)
    faits = [f for f in ecr.faits if f["fiche"] == "gouvernement/gamma" and f["type_fait"] == "parole_extrait"]
    assert len(faits) == 4 and {f["id_compte_rendu"] for f in faits} == {"CR1", "CR2", "CR3"}


def test_paroles_extraits_decoupes_en_paquets(tmp_path, monkeypatch):
    monkeypatch.setattr(composeur, "PAQUET_EXTRAITS", 50)
    _, man, racine = _composer(tmp_path)
    gamma = [f for f in man["fiches"] if f["fiche"] == "gouvernement/gamma"][0]
    paquets = sorted(k for k in gamma["sections"] if k.startswith("paroles-textes-"))
    assert len(paquets) == 4
    idx = _rows(_lire(racine, "gouvernements/gamma/paroles.json.gz"))
    assert idx[0]["fichiers_extraits"] == ["paroles-textes-001.json.gz", "paroles-textes-002.json.gz"]


def test_actes_seule_la_periode_couverte_compte(sortie):
    ecr, man, racine = sortie
    b = _lire(racine, "gouvernements/delta-ii/fiche.json.gz")["en_bref"]["actes"]
    assert b["nb_actes"] == 3                       # J4, redélivré hors période, ne compte pas
    assert b["nb_mesures_nominatives"] == 1 and b["nb_titre_cite_une_loi"] == 1
    assert b["periode_couverte"] == {"du": "2026-10-06", "au": "2026-11-06"} and b["etendue"] == "partiel"
    a = _lire(racine, "gouvernements/delta-ii/actes.json.gz")
    assert a["couverture"]["statut"] == "non_collecte" and a["couverture"]["etendue"] == "partiel"
    assert (a["couverture"]["numerateur"], a["couverture"]["denominateur"]) == (32, 392)
    assert not any("part" in c or "taux" in c for c in a["colonnes"])
    assert [m["mois"] for m in a["mois"]] == ["2026-10", "2026-11"]
    octobre = _rows(_lire(racine, "gouvernements/delta-ii/actes-2026-10.json.gz"))
    assert [r["acte"] for r in octobre] == ["J1"] and octobre[0]["lois_citees"] == ["2021-1754"]
    nomin = _rows(_lire(racine, "gouvernements/delta-ii/actes-nominatives-2026-10.json.gz"))
    assert [r["acte"] for r in nomin] == ["J2"]
    lois = _rows(_lire(racine, "gouvernements/delta-ii/actes-lois.json.gz"))
    assert [(l["numero_loi"], l["nb_actes"]) for l in lois] == [("2021-1754", 1)]
    # aucune personne dans les actes
    assert not any(c in ("acteur", "signataires") for c in a["colonnes"])


def test_actes_non_collectes_aucun_compte(sortie):
    _, man, racine = sortie
    b = _lire(racine, "gouvernements/gamma/fiche.json.gz")["en_bref"]["actes"]
    assert b["nb_actes"] is None and b["nb_titre_cite_une_loi"] is None
    assert b["couverture"] == "non_collecte"
    gamma = [f for f in man["fiches"] if f["fiche"] == "gouvernement/gamma"][0]
    assert not any(k.startswith("actes-20") for k in gamma["sections"])
    assert _lire(racine, "gouvernements/gamma/actes.json.gz")["lignes"] == []


def test_budgets_vides_non_collectes(sortie):
    _, _, racine = sortie
    d = _lire(racine, "gouvernements/delta-ii/budgets.json.gz")
    assert d["lignes"] == [] and d["couverture"]["statut"] == "non_collecte"


def test_tables_absentes_couverture_le_dit(tmp_path):
    _, man, racine = _composer(tmp_path, parole_gouvernement=None, couverture_jo_gouvernement=None,
                               acte_rattache=None, vague=None)
    fiche = _lire(racine, "gouvernements/gamma/fiche.json.gz")
    assert fiche["en_bref"]["paroles"]["nb_prises_de_parole"] is None
    assert fiche["en_bref"]["actes"]["nb_actes"] is None
    assert fiche["en_bref"]["composition"]["nb_vagues"] is None
    p = _lire(racine, "gouvernements/gamma/paroles.json.gz")
    assert p["couverture"]["statut"] == "en_cours"


def test_avant_le_perimetre_aucun_zero(tmp_path, monkeypatch):
    """Un gouvernement qui commence avant le début des comptes rendus lus (cahier 4.1 : XVe) et reste
    en fonction après : ses paroles sont lues en partie (`partiel`), et un zéro n'est pas servi.
    Simulé en faisant commencer les paroles à la XVIIe."""
    monkeypatch.setattr(composeur, "PAROLES_DEPUIS", 17)
    _, _, racine = _composer(tmp_path)
    b = _lire(racine, "gouvernements/beta/fiche.json.gz")["en_bref"]
    assert b["paroles"]["nb_prises_de_parole"] is None and b["paroles"]["couverture"] == "partiel"
    g = _lire(racine, "gouvernements/gamma/fiche.json.gz")["en_bref"]
    assert g["paroles"]["couverture"] == "complet"
