"""Composeur « lignee » (cahier 4.3 ; doc. 1, 1.7.2) sur de petites tables, à la forme exacte des
sorties des règles : deux lignées, l'une sur la XVIe (deux organes successifs) et la XVIIe, l'autre
sur la XVIIe seule."""
import gzip
import json
import os

import pyarrow as pa
import pytest

from empreinte_src.composeurs import lignee as composeur
from empreinte_src.composition import Ecrivain, composeurs
from empreinte_src.controles import Controles
from empreinte_src.liaison import Contexte, regles

AU = "2026-11-06"
AMO = {"prov_point": "an-amo30-l17", "licence": "etalab-2.0"}


def _ident(uid, prenom, nom):
    return {"uid": uid, "prenom": prenom, "nom": nom, "nom_alpha": nom, **AMO}


def _parole(acteur, ids, date, extrait, sujet="Logement", preside=False):
    return {"acteur": acteur, "compte_rendu": "CRSANR5L17S2025O1N001", "id_syceron": ids, "date": date,
            "ordre_absolu_seance": int(ids), "type_sujet": "texte", "sujet": sujet, "dossier": "DL1",
            "preside": preside, "statut_sujet": "etabli", "extrait": extrait, "extrait_tronque": False,
            "qualite": "depute", "source_url": "https://www.assemblee-nationale.fr/dyn/17/comptes-rendus/x#" + ids}


def _dg(scrutin, organe, pos, pour, contre, abst, membres=10):
    return {"scrutin": scrutin, "organe": organe, "position_majoritaire": pos, "pour": pour, "contre": contre,
            "abstentions": abst, "non_votants": 0, "nombre_membres": membres}


def _scr(scrutin, numero, date, nature="ensemble"):
    return {"scrutin": scrutin, "numero": numero, "date": date, "titre": f"l'ensemble du texte {numero}",
            "nature": nature, "lecture": "1", "sort": "adopte", "legislature": 17,
            "source_url": f"https://www.assemblee-nationale.fr/dyn/17/scrutins/{numero}"}


TABLES = {
    "lignee": [
        {"lignee": "lig:000001", "adresse": "socialistes", "nom": "Socialistes et apparentés", "sigle": "SOC",
         "debut": "2022-06-28", "fin": None, "en_cours": True, "premiere_legislature": 16,
         "debut_affiche": "2022-06-28", "publiee": True, "maillon_racine": "grp:16:PO16A", "regle": "R-LIGNEE@1"},
        {"lignee": "lig:000002", "adresse": "rassemblement", "nom": "Rassemblement", "sigle": "RN",
         "debut": "2024-07-18", "fin": None, "en_cours": True, "premiere_legislature": 17,
         "debut_affiche": "2024-07-18", "publiee": True, "maillon_racine": "grp:17:PO17R", "regle": "R-LIGNEE@1"},
        {"lignee": "lig:000003", "adresse": "ancien", "nom": "Ancien", "sigle": "A", "debut": "2007-06-26",
         "fin": "2012-06-19", "en_cours": False, "premiere_legislature": 13, "debut_affiche": None,
         "publiee": False, "maillon_racine": "grp:13:PO13A", "regle": "R-LIGNEE@1"}],
    "lignee_maillon": [
        {"lignee": "lig:000001", "maillon": "grp:16:PO16A", "legislature": 16, "rang_dans_lignee": 1,
         "affiche": True, "debut": "2022-06-28", "fin": "2024-06-09", "sigle": "SOC-A",
         "libelle": "Socialistes et apparentés", "position_maillon": "divergente", "organes": ["PO16A", "PO16B"],
         "sigles": ["SOC", "SOC-A"], "libelles": ["Socialistes (NUPES)", "Socialistes et apparentés"],
         "nb_organes": 2},
        {"lignee": "lig:000001", "maillon": "grp:17:PO17S", "legislature": 17, "rang_dans_lignee": 2,
         "affiche": True, "debut": "2024-07-18", "fin": None, "sigle": "SOC", "libelle": "Socialistes et apparentés",
         "position_maillon": "non_declaree", "organes": ["PO17S"], "sigles": ["SOC"],
         "libelles": ["Socialistes et apparentés"], "nb_organes": 1},
        {"lignee": "lig:000002", "maillon": "grp:17:PO17R", "legislature": 17, "rang_dans_lignee": 1,
         "affiche": True, "debut": "2024-07-18", "fin": None, "sigle": "RN", "libelle": "Rassemblement",
         "position_maillon": "non_declaree", "organes": ["PO17R"], "sigles": ["RN"], "libelles": ["Rassemblement"],
         "nb_organes": 1},
        {"lignee": "lig:000003", "maillon": "grp:13:PO13A", "legislature": 13, "rang_dans_lignee": 1,
         "affiche": False, "debut": "2007-06-26", "fin": "2012-06-19", "sigle": "A", "libelle": "Ancien",
         "position_maillon": "non_declaree", "organes": ["PO13A"], "sigles": ["A"], "libelles": ["Ancien"],
         "nb_organes": 1}],
    "maillon": [
        {"maillon": m, "organe": o, "rang": r, "sigle": s, "libelle": s, "fin_maillon": fin,
         "position_declaree": p, "source_url": None}
        for m, o, r, s, fin, p in (("grp:16:PO16A", "PO16A", 1, "SOC", "2024-06-09", "opposition"),
                                   ("grp:16:PO16A", "PO16B", 2, "SOC-A", "2024-06-09", "minoritaire"),
                                   ("grp:17:PO17S", "PO17S", 1, "SOC", None, "non_declaree"),
                                   ("grp:17:PO17R", "PO17R", 1, "RN", None, "non_declaree"),
                                   ("grp:15:PO15N", "PO15N", 1, "NG", "2022-06-21", "opposition"),
                                   ("grp:13:PO13A", "PO13A", 1, "A", "2012-06-19", "non_declaree"))],
    "filiation": [
        {"maillon_avant": "grp:16:PO16A", "maillon_apres": "grp:17:PO17S", "legislature_avant": 16,
         "legislature_apres": 17, "reelus": 3, "anciens_deputes": 3, "communs": 3, "verdict": "suite",
         "raison": "decision", "decision": "filiation/soc17.yaml"},
        # Le premier maillon de la lignée socialiste : la comparaison la plus proche dit pourquoi
        # la lignée commence là.
        {"maillon_avant": "grp:15:PO15N", "maillon_apres": "grp:16:PO16A", "legislature_avant": 15,
         "legislature_apres": 16, "reelus": 20, "anciens_deputes": 4, "communs": 2, "verdict": "pas_suite",
         "raison": "moins_de_5_communs", "decision": None}],
    "appartenance": [
        # P1 : XVIe (deux organes successifs) puis XVIIe ; P2 : XVIe seulement ; P3 : nouveau en XVIIe,
        # parti le 2025-03-31 ; P4 : candidat, XVIIe ; P9 : RN.
        {"acteur": "PA1", "groupe": "PO16A", "debut": "2022-06-28", "fin": "2023-10-18"},
        {"acteur": "PA1", "groupe": "PO16B", "debut": "2023-10-19", "fin": "2024-06-09"},
        {"acteur": "PA1", "groupe": "PO17S", "debut": "2024-07-18", "fin": None},
        {"acteur": "PA2", "groupe": "PO16A", "debut": "2022-06-28", "fin": "2024-06-09"},
        {"acteur": "PA3", "groupe": "PO17S", "debut": "2024-07-18", "fin": "2025-03-31"},
        {"acteur": "PA4", "groupe": "PO17S", "debut": "2024-07-18", "fin": None},
        {"acteur": "PA9", "groupe": "PO17R", "debut": "2024-07-18", "fin": None}],
    "effectif_groupe": [
        {"groupe": g, "date": d, "effectif": n}
        for g, d, n in (("PO16A", "2022-06-28", 2), ("PO16A", "2022-06-29", 2), ("PO16A", "2023-10-18", 2),
                        ("PO16B", "2023-10-19", 1), ("PO16B", "2024-06-09", 1),
                        ("PO17S", "2024-07-18", 3), ("PO17S", "2025-03-31", 3), ("PO17S", "2025-04-01", 2),
                        ("PO17S", AU, 2), ("PO17R", "2024-07-18", 1), ("PO17R", AU, 1))],
    "legislature": [{"numero": 16, "debut": "2022-06-22", "fin": "2024-06-09"},
                    {"numero": 17, "debut": "2024-07-18", "fin": None}],
    "candidat": [{"acteur": "PA4", "adresse": "dora-candidate", "publie": True},
                 {"acteur": "PA2", "adresse": None, "publie": False}],
    "an_acteurs__identite_source": [_ident("PA1", "Alice", "Martin"), _ident("PA2", "Bruno", "Abel"),
                                    _ident("PA3", "Chloé", "Zola"), _ident("PA4", "Dora", "Candidate"),
                                    _ident("PA9", "Yves", "Roux")],
    "an_dossiers__dossier": [{"uid": "DL1", "titre": "Logement des étudiants", **AMO}],
    "parole_personne": [
        _parole("PA1", "1", "2025-01-30", "Le logement des étudiants est une urgence nationale."),
        _parole("PA3", "2", "2025-01-30", "Je soutiens cette proposition."),
        _parole("PA3", "3", "2025-06-10", "Parole après son départ du groupe : pas au groupe."),
        _parole("PA4", "4", "2025-06-10", "La séance est ouverte.", preside=True),
        _parole("PA9", "5", "2025-01-30", "Parole d'un autre groupe.")],
    "texte_porte": [
        {"acteur": a, "dossier": d, "document": doc, "titre": None, "role": role, "qualite_rapporteur": None,
         "nature": "Proposition de loi", "nature_code": "PION", "date_role": None, "date_depot": dd,
         "etape_atteinte": "examen_commission", "sort": None, "par_49_3": False, "adopte_par_49_3": False,
         "matiere": "PO420120", "matiere_statut": "assemblee", "matiere_libelle": "Affaires sociales",
         "publiable": pub, "source_url": None}
        for a, d, doc, role, dd, pub in (("PA1", "DL1", "PIONANR5L17B0001", "auteur", "2025-01-15", True),
                                         ("PA4", "DL1", "PIONANR5L17B0001", "cosignataire", "2025-01-15", True),
                                         ("PA3", "DL2", "PIONANR5L17B0002", "auteur", "2025-05-01", True),
                                         ("PA1", "DL3", "PIONANR5L17B0003", "auteur", "2025-02-01", False))],
    "amendement_canonique": [
        {"acteur": a, "amendement": u, "numero_long": u, "date_depot": d, "sort": "rejete", "famille_sort": fs,
         "commission": "PO420120", "commission_libelle": "Affaires sociales", "dossier": "DL1",
         "document": "PIONANR5L17B0001", "article_designation": "Article 1", "source_url": None}
        for a, u, d, fs in (("PA1", "AM1", "2025-01-20", "discute"), ("PA3", "AM2", "2025-01-21", "irrecevable_40"),
                            ("PA3", "AM3", "2025-05-02", "discute"),     # après son départ : pas au groupe
                            ("PA9", "AM9", "2025-03-03", "discute"))],
    "amendement_auteur": [
        {"acteur": "PA4", "amendement": "AM9", "role": "cosignataire", "date_depot": "2025-03-03",
         "commission": "PO420120"},
        {"acteur": "PA4", "amendement": "AM1", "role": "cosignataire", "date_depot": "2025-01-20",
         "commission": "PO420120"}],          # cosigne l'amendement d'un membre : déjà compté
    "scrutin_classe": [_scr("VT1", 1, "2025-01-30"), _scr("VT2", 2, "2025-06-10"),
                       _scr("VT3", 3, "2025-07-01", "amendement")],
    "derniere_lecture": [{"scrutin": "VT1", "dossier": "DL1"}],
    "lien_scrutin_dossier": [{"scrutin": "VT1", "dossier": "DL1"}],
    "an_scrutins__decompte_groupe": [
        _dg("VT1", "PO17S", "pour", 2, 0, 0), _dg("VT1", "PO17R", "pour", 1, 0, 0),
        # Q30 : « contre » publié pour 19 pour, 7 contre : non établie.
        _dg("VT2", "PO17S", "contre", 19, 7, 7), _dg("VT2", "PO17R", "contre", 0, 1, 0),
        _dg("VT3", "PO17S", "pour", 1, 0, 1), _dg("VT3", "PO17R", "contre", 0, 1, 0)],
    "groupe": [{"organe": "PO17S", "sigle": "SOC"}, {"organe": "PO17R", "sigle": "RN"}],
    "hemicycle": [{"legislature": 17, "siege": "100", "groupe": "PO17S"},
                  {"legislature": 17, "siege": "300", "groupe": "PO17S"},
                  {"legislature": 17, "siege": "500", "groupe": "PO17R"}],
}


def _composer(tmp_path, tables=TABLES):
    os.makedirs(tmp_path / "z2", exist_ok=True)
    ctx = Contexte(str(tmp_path / "z2"), str(tmp_path / "z3"), date_reference=AU)
    for nom, lignes in tables.items():
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
    return _composer(tmp_path_factory.mktemp("lig"))


def test_contrat_et_dependances():
    assert composeur in composeurs() and composeur.NOM == "lignee"
    assert set(composeur.DEPEND) <= {r.NOM for r in regles()}


def test_une_fiche_par_lignee_publiee_et_controles(sortie):
    ecr, man, racine = sortie
    assert [f["fiche"] for f in man["fiches"]] == ["lignee/rassemblement", "lignee/socialistes"]
    c = Controles(racine)
    c.c2_liens({f["fiche"] for f in man["fiches"]} | {"legislature/16", "legislature/17", "candidat/dora-candidate"})
    c.c4_interdits()
    assert c.bilan()["publication_autorisee"], c.bilan()


def test_entete_frise_et_filiations(sortie):
    _, _, racine = sortie
    f = _lire(racine, "lignees/socialistes/fiche.json.gz")
    assert f["lignee"]["noms_successifs"] == ["Socialistes (NUPES)", "Socialistes et apparentés"]
    m = _rows(f["maillons"])
    assert [x["legislature"] for x in m] == [16, 17]
    assert m[0]["organes"] == ["PO16A", "PO16B"] and m[0]["positions_organes"] == ["opposition", "minoritaire"]
    assert m[0]["position_maillon"] == "divergente"
    # Maillon clos : effectif à sa fin ; en cours : à la date de référence. Membres : personnes distinctes.
    assert (m[0]["effectif"], m[0]["effectif_au"], m[0]["membres"]) == (1, "2024-06-09", 2)
    assert (m[1]["effectif"], m[1]["effectif_au"], m[1]["membres"]) == (2, AU, 3)
    assert m[0]["lien"] == "legislature/16" and m[1]["lien"] == "legislature/17"     # XIVe à XVIIe publiées
    fil = _rows(f["filiations"])
    assert [(x["maillon"], x["verdict"]) for x in fil] == [("grp:16:PO16A", "pas_suite"), ("grp:17:PO17S", "suite")]
    assert (fil[1]["reelus"], fil[1]["anciens_deputes"], fil[1]["communs"]) == (3, 3, 3)
    assert {c["section"] for c in f["couverture"]} >= {"membres", "effectifs", "paroles", "votes-16", "avec-qui-16",
                                                       "votes-17", "avec-qui-17"}


def test_membres_provenance_et_candidat(sortie):
    _, _, racine = sortie
    mb = {(x["acteur"], x["legislature"]): x for x in _rows(_lire(racine, "lignees/socialistes/membres.json.gz"))}
    assert mb[("PA1", 16)]["provenance"] == "au_depart"
    # Deux organes successifs : une seule période.
    assert mb[("PA1", 16)]["periodes"] == [["2022-06-28", "2024-06-09"]]
    assert mb[("PA1", 16)]["reste_au_maillon_suivant"] is True
    assert mb[("PA2", 16)]["reste_au_maillon_suivant"] is False
    assert (mb[("PA1", 17)]["provenance"], mb[("PA3", 17)]["provenance"]) == ("deja_la", "nouveau")
    assert mb[("PA1", 17)]["reste_au_maillon_suivant"] is None        # pas de maillon suivant
    assert mb[("PA4", 17)]["lien"] == "candidat/dora-candidate" and mb[("PA4", 17)]["candidat"]
    assert mb[("PA2", 16)]["lien"] is None                             # non publié : pas de lien
    assert mb[("PA3", 17)]["depart"] == "2025-03-31"


def test_effectifs_aux_seuls_changements(sortie):
    _, _, racine = sortie
    e = [(x["maillon"], x["date"], x["effectif"]) for x in _rows(_lire(racine, "lignees/socialistes/effectifs.json.gz"))]
    assert e == [("grp:16:PO16A", "2022-06-28", 2), ("grp:16:PO16A", "2023-10-19", 1),
                 ("grp:16:PO16A", "2024-06-09", 1),
                 ("grp:17:PO17S", "2024-07-18", 3), ("grp:17:PO17S", "2025-04-01", 2), ("grp:17:PO17S", AU, 2)]


def test_paroles_pendant_l_appartenance_et_index_non_compte_deux_fois(sortie):
    ecr, man, racine = sortie
    p = _lire(racine, "lignees/socialistes/paroles.json.gz")
    lignes = _rows(p)
    assert [x["id_syceron"] for x in lignes] == ["1", "2", "4"]      # « 3 » : après le départ de PA3
    suj = _rows(p["sujets"])
    assert (suj[0]["prises_de_parole"], suj[0]["orateurs_distincts"]) == (2, 2)   # présidence à part
    assert {x["acteur"]: x["paragraphes_de_presidence"] for x in _rows(p["orateurs"])}["PA4"] == 1
    # XVIe et XVIIe : dans le périmètre des paroles (XVe à XVIIe), aucun maillon hors périmètre.
    assert p["couverture"]["maillons_hors_perimetre"] == []
    assert p["maillons"] == ["grp:16:PO16A", "grp:17:PO17S"]
    sections = {x["section"] for x in ecr.faits if x["fiche"] == "lignee/socialistes"}
    assert "paroles" not in sections and any(s.startswith("paroles-textes-") for s in sections)
    textes = [x for x in ecr.faits if x["fiche"] == "lignee/socialistes" and x["section"].startswith("paroles-textes")]
    assert len(textes) == 3


def test_textes_et_amendements_pendant_l_appartenance(sortie):
    _, _, racine = sortie
    t = _lire(racine, "lignees/socialistes/proposes.json.gz")
    assert sorted((x["dossier"], x["acteur"]) for x in _rows(t)) == [("DL1", "PA1"), ("DL1", "PA4")]
    agr = [dict(zip(t["agregats"]["colonnes"], x)) for x in t["agregats"]["lignes"]]
    assert sum(a["dossiers_distincts"] for a in agr) == 2                 # DL1 compté une fois par rôle
    a = _rows(_lire(racine, "lignees/socialistes/amendements.json.gz"))
    assert len(a) == 1
    assert (a[0]["nb_amendements"], a[0]["nb_irrecevables_40"], a[0]["nb_signatures_cosignataire"]) == (1, 1, 1)
    liste = _rows(_lire(racine, "lignees/socialistes/amendements-2025.json.gz"))
    assert [x["amendement"] for x in liste] == ["AM1", "AM2"]


def test_votes_decompte_publie_et_q30(sortie):
    _, _, racine = sortie
    v = {x["scrutin"]: x for x in _rows(_lire(racine, "lignees/socialistes/votes-17.json.gz"))}
    assert (v["VT1"]["position_groupe"], v["VT1"]["partage"], v["VT1"]["derniere_lecture"]) == ("pour", "une_seule_voix", True)
    assert v["VT2"]["position_groupe"] is None
    assert v["VT2"]["raison_position_non_etablie"] == "position_publiee_contredite_par_le_decompte"
    assert v["VT2"]["partage"] == "pour_et_contre" and v["VT3"]["partage"] == "position_et_abstention"
    assert v["VT1"]["titre_dossier"] == "Logement des étudiants"


def test_avec_qui_decomptes_sans_part_ordre_hemicycle(sortie):
    _, _, racine = sortie
    d = _lire(racine, "lignees/socialistes/avec-qui-17.json.gz")
    r = {x["nature"]: x for x in _rows(d)}
    # VT2 : position socialiste non établie → hors comparaison.
    assert (r["ensemble"]["scrutins_compares"], r["ensemble"]["scrutins_coincidents"]) == (1, 1)
    assert (r["amendement"]["scrutins_compares"], r["amendement"]["scrutins_coincidents"]) == (1, 0)
    assert r["ensemble"]["lien"] == "lignee/rassemblement" and r["ensemble"]["place_mediane"] == 500
    assert not any(c.startswith(("part", "ratio", "taux")) for c in d["colonnes"])


def test_lignee_close_avant_la_xviie(tmp_path):
    """Une lignée close avant la XVIIe (XVIe seule) : son activité est dans le périmètre (XIVe à
    XVIIe) ; votes et « avec qui » de sa législature, comptés à la fin du maillon ; groupes rangés
    par sigle (l'hémicycle d'une législature close n'est pas publié)."""
    t = {k: v for k, v in TABLES.items()}
    t["lignee"] = [dict(TABLES["lignee"][0], fin="2024-06-09", en_cours=False)]
    t["lignee_maillon"] = [TABLES["lignee_maillon"][0]]
    ecr, man, racine = _composer(tmp_path, t)
    f = _lire(racine, "lignees/socialistes/fiche.json.gz")
    assert set(f["sections"]) == {"effectifs", "membres", "paroles", "proposes", "amendements", "votes-16",
                                  "avec-qui-16"}
    for nom in ("paroles", "proposes", "amendements"):
        c = _lire(racine, f"lignees/socialistes/{nom}.json.gz")["couverture"]
        assert c["statut"] == "complet" and not c.get("maillons_hors_perimetre"), nom
    aq = _lire(racine, "lignees/socialistes/avec-qui-16.json.gz")
    assert aq["au"] == "2024-06-09" and aq["ordre"].startswith("alphabétique")


def test_paroles_avant_le_perimetre_aucun_zero(tmp_path, monkeypatch):
    """Un maillon d'une législature sans paroles lues (XIVe, cahier 4.1) : « hors périmètre », sans
    compte. Simulé en faisant commencer les paroles à la XVIIe."""
    monkeypatch.setattr(composeur, "LEGISLATURES_PAROLES", (17,))
    t = {k: v for k, v in TABLES.items()}
    t["lignee"] = [dict(TABLES["lignee"][0], fin="2024-06-09", en_cours=False)]
    t["lignee_maillon"] = [TABLES["lignee_maillon"][0]]
    ecr, man, racine = _composer(tmp_path, t)
    c = _lire(racine, "lignees/socialistes/paroles.json.gz")["couverture"]
    assert c["statut"] == "hors_perimetre" and c["maillons_hors_perimetre"][0]["raison"] == "paroles_avant_la_xve"
    assert not any(x["section"].startswith("paroles-textes") for x in ecr.faits)
