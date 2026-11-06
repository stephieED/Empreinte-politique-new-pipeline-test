"""Règles du groupe C — paroles et ordre du jour : R-ORATEUR, R-SUJET, R-QUALITE,
R-ORDRE-DU-JOUR, R-PAROLES-GOUVERNEMENT.

Deux jeux :
- `reel` : cinq comptes rendus réels (`syceron_l17_extrait.zip`), les orateurs utiles dans AMO30
  (`amo30_l17_orateurs_extrait.zip`), l'agenda de leurs séances (`agenda_l17_seances_extrait.zip`),
  et trois dossiers recopiés en petite table (fiche `extraits/regles_c.md`) ;
- `petit` : de petites tables écrites ici pour les cas que l'extrait ne couvre pas (qualité
  déduite, rapporteur, `PA0` nommé, civilité contredite…).

`membre_gouvernement` (R-COMPOSITION, groupe A) est remplacée dans ces tests par une règle de
substitution tirée des mandats GOUVERNEMENT : seules les colonnes du contrat (gouvernement,
acteur, debut, fin) sont lues par le groupe C.
"""
import os
import types

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from empreinte_src.depaquetage import depaqueter
from empreinte_src.entrepot import Entrepot
from empreinte_src.lecture import COLONNES_PROVENANCE, Lecture
from empreinte_src.lecteurs import an_acteurs, an_agenda, an_comptes_rendus, an_dossiers
from empreinte_src.liaison import Contexte, ordonner, relier
from empreinte_src.regles import (r_gouvernements, r_legislatures, r_orateur, r_ordre_du_jour,
                              r_paroles_gouvernement, r_qualite, r_sujet)

EXTRAITS = os.path.join(os.path.dirname(__file__), "extraits")
SOURCES = [
    ({"id": "an-syceron-l17", "type": "comptes_rendus"}, "syceron_l17_extrait.zip", an_comptes_rendus),
    ({"id": "an-amo30-l17", "type": "acteurs_organes"}, "amo30_l17_orateurs_extrait.zip", an_acteurs),
    ({"id": "an-agenda-l17", "type": "agenda"}, "agenda_l17_seances_extrait.zip", an_agenda),
]
GROUPE_C = [r_orateur, r_sujet, r_qualite, r_ordre_du_jour, r_paroles_gouvernement]


def _composition(ctx):
    ctx.ecrire("membre_gouvernement", """
        SELECT m.organe AS gouvernement, m.acteur, min(m.date_debut) AS debut,
               max(least(coalesce(m.date_fin, g.fin, '9999-12-31'), coalesce(g.fin, '9999-12-31'))) AS fin
        FROM an_acteurs__mandat m JOIN gouvernement g ON g.organe = m.organe
        WHERE m.type_organe = 'GOUVERNEMENT' GROUP BY 1, 2""")
    return {}


COMPOSITION = types.SimpleNamespace(NOM="R-COMPOSITION", VERSION=0, DEPEND=("R-GOUVERNEMENTS",),
                                    SORTIES=("membre_gouvernement",), appliquer=_composition)


def _matiere(ctx):
    ctx.ecrire("matiere", """SELECT 'DLR5L17N50169' AS dossier, 'PO59051' AS commission,
        'assemblee' AS statut, 'Commission des lois' AS libelle""")
    return {}


MATIERE = types.SimpleNamespace(NOM="R-MATIERE", VERSION=0, DEPEND=(), SORTIES=("matiere",),
                                appliquer=_matiere)


def ecrire_table(z2, mod, table, lignes):
    """Petite table de faits au schéma du lecteur, avec ses colonnes de provenance."""
    schema = mod.TABLES[table]
    for nom, t in COLONNES_PROVENANCE:
        if nom not in schema.names:
            schema = schema.append(pa.field(nom, t))
    rows = []
    for k, r in enumerate(lignes):
        r = {n: r.get(n) for n in schema.names} | {
            "prov_point": "test", "prov_uid": f"{table}-{k}", "prov_version": 1,
            "prov_etat": "present", "prov_url": r.get("prov_url")}
        rows.append(r)
    pq.write_table(pa.Table.from_pylist(rows, schema=schema),
                   os.path.join(z2, f"{mod.NOM}__{table}.parquet"))


def appliquer(z2, z3, extra=()):
    ctx = Contexte(str(z2), str(z3))
    bilan = relier(ctx, ordonner([r_legislatures, r_gouvernements, COMPOSITION, *extra, *GROUPE_C]))
    return ctx, {b["regle"].split("@")[0]: b for b in bilan}


def _un(ctx, sql):
    r = ctx.con.execute(sql).fetchall()
    assert len(r) == 1, (sql, r)
    return r[0]


# --------------------------------------------------------------------------- jeu réel

DOSSIERS = [  # 17_Dossiers_Legislatifs.json.zip du 04/11/2026, recopiés champ par champ
    {"uid": "DLR5L17N50169", "legislature": "17",
     "titre": "Proposition de loi visant à sortir la France du piège du narcotrafic"},
    {"uid": "DLR5L17N51078", "legislature": "17",
     "titre": "Proposition de loi organique fixant le statut du procureur national anti-stupéfiants"},
    {"uid": "DLR5L17N54629", "legislature": "17", "titre": "Projet de loi de finances pour 2027"},
]
ACTES = [
    {"dossier": "DLR5L17N51078", "uid": "L17-VD223923S49416", "code": "AN1-DEBATS-SEANCE",
     "reunion": "RUANR5L17S2025IDS29213", "odj": "RUANR5L17S2025IDS29213PT49416", "rapporteurs": []},
    {"dossier": "DLR5L17N50169", "uid": "L17-VD223922S49415", "code": "AN1-DEBATS-SEANCE",
     "reunion": "RUANR5L17S2025IDS29213", "odj": "RUANR5L17S2025IDS29213PT49415", "rapporteurs": []},
    {"dossier": "DLR5L17N54629", "uid": "L17-VD233824S53446", "code": "AN1-DEBATS-SEANCE",
     "reunion": "RUANR5L17S2027IDS30975", "odj": "RUANR5L17S2027IDS30975PT53446", "rapporteurs": []},
]


@pytest.fixture(scope="module")
def reel(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("c")
    e = Entrepot(str(tmp / "e"))
    for pa_, zip_, _ in SOURCES:
        pa_ = {**pa_, "source": "an", "format": "zip", "url": "http://exemple.invalid/x.zip"}
        e.versionner(pa_, f"R{e.generation}", depaqueter(os.path.join(EXTRAITS, zip_), "zip"), complet=True)
    e.clore("test")
    cfg = {"points_acces": [{"id": p["id"], "licence": "etalab-2.0"} for p, _, _ in SOURCES]}
    lecture = Lecture(Entrepot(str(tmp / "e")), str(tmp / "z2"), cfg)
    for _, _, mod in SOURCES:
        b = lecture.executer(mod)
        assert b["illisibles"] == 0
    ecrire_table(tmp / "z2", an_dossiers, "dossier", DOSSIERS)
    ecrire_table(tmp / "z2", an_dossiers, "acte", ACTES)
    ctx, bilan = appliquer(tmp / "z2", tmp / "z3")
    return ctx, bilan, tmp


def _attr(ctx, cr, ids):
    return _un(ctx, f"""SELECT acteur, raison_non_attribuee, preside, orateur_source, nom_affiche
                        FROM intervention_attribuee WHERE compte_rendu = '{cr}' AND id_syceron = '{ids}'""")


def test_une_ligne_par_paragraphe_et_couverture(reel):
    ctx, bilan, _ = reel
    assert bilan["R-ORATEUR"]["lignes"] == {"intervention_attribuee": 1109}
    assert bilan["R-SUJET"]["lignes"] == {"sujet_intervention": 1109}
    n, d = bilan["R-ORATEUR"]["couverture"]["paragraphe_attribue"]
    assert 0 < n < d
    assert _un(ctx, "SELECT count(DISTINCT regle) FROM intervention_attribuee") == (1,)
    # Chaque fait garde son adresse publique (ancre du paragraphe).
    assert _un(ctx, """SELECT count(*) FROM intervention_attribuee
                       WHERE source_url <> 'https://www.assemblee-nationale.fr/dyn/17/comptes-rendus/seance/'
                                         || compte_rendu || '#' || id_syceron""") == (0,)


def test_nom_affiche_qui_ne_correspond_pas_a_l_identifiant(reel):
    ctx, _, _ = reel
    # « Mme Alice Rufo, ministre déléguée » publiée sous l'identifiant de François Ruffin.
    assert _attr(ctx, "CRSANR5L17S2026O1N177", "4042860") == (
        None, "nom_discordant", False, "PA722142", "Mme Alice Rufo")


def test_identifiant_de_repli_negatif_et_inconnu(reel):
    ctx, _, _ = reel
    rows = ctx.x("""SELECT nom_affiche, raison_non_attribuee FROM intervention_attribuee
                    WHERE orateur_source = 'PA793214'""")
    assert rows and all(r == "identifiant_de_repli" for _, r in rows)
    assert {n for n, _ in rows} >= {"Mme Olga Douin", "M. Daniel Goldberg"}
    assert _un(ctx, """SELECT count(*), count(acteur), min(raison_non_attribuee), max(raison_non_attribuee)
                       FROM intervention_attribuee WHERE orateur_source LIKE 'PA-%'""") == (
        13, 0, "identifiant_negatif", "identifiant_negatif")
    # Identifiant absent du référentiel (cet acteur n'est pas dans l'extrait AMO).
    assert _attr(ctx, "CRSANR5L17S2026O1N105", "3984042")[:2] == (None, "identifiant_inconnu")


def test_collectif_plusieurs_orateurs_interpellation(reel):
    ctx, _, _ = reel
    assert _un(ctx, """SELECT DISTINCT raison_non_attribuee FROM intervention_attribuee
                       WHERE nom_affiche = 'Un député du groupe SOC'""") == ("orateur_collectif",)
    # PA0 sur un paragraphe à plusieurs orateurs.
    assert _attr(ctx, "CRSANR5L17S2026O1N120", "3994515")[:4] == (None, "plusieurs_orateurs", False, "PA0")
    # Orateur nommé sans identifiant d'acteur (exclamation depuis les bancs).
    assert _attr(ctx, "CRSANR5L17S2026O1N105", "3984146")[:2] == (None, "interpellation")
    assert _un(ctx, """SELECT count(*) FROM intervention_attribuee
                       WHERE raison_non_attribuee = 'sans_orateur' AND nom_affiche IS NOT NULL""") == (0,)


def test_presidence_reconnue_aussi_par_le_libelle(reel):
    ctx, _, _ = reel
    # « Mme la présidente » sans roledebat : présidence quand même, attribuée à la vice-présidente.
    assert _un(ctx, """SELECT i.roledebat FROM an_comptes_rendus__intervention i
                       WHERE id_syceron = '4042280'""") == (None,)
    assert _attr(ctx, "CRSANR5L17S2026O1N177", "4042280")[:3] == ("PA721908", None, True)
    assert _un(ctx, """SELECT count(*) FROM intervention_attribuee a JOIN an_comptes_rendus__intervention i
                       USING (compte_rendu, id_syceron)
                       WHERE i.roledebat IS NULL AND a.preside""")[0] > 0
    # Présider n'est pas intervenir : la qualité est « président de séance », jamais un débat
    # du gouvernement.
    assert _un(ctx, """SELECT DISTINCT qualite, qualite_source FROM qualite_orateur
                       WHERE compte_rendu = 'CRSANR5L17S2026O1N177' AND acteur = 'PA721908'""") == (
        "president_de_seance", "compte_rendu")


def test_sujet_sous_le_creneau(reel):
    ctx, _, _ = reel
    s = _un(ctx, """SELECT sujet, statut, type_sujet, creneau, lien_dossier FROM sujet_intervention
                    WHERE compte_rendu = 'CRSANR5L17S2026O1N177' AND id_syceron = '4042280'""")
    assert s[:3] == ("Prix de l’énergie", "etabli", "question")
    assert s[3].lower().startswith("questions au gouvernement") and s[4] == "sans_objet"
    # « Questions au gouvernement » seul n'est pas un sujet.
    assert _un(ctx, """SELECT count(*) FROM sujet_intervention
                       WHERE lower(sujet) LIKE 'questions au gouvernement%'""") == (0,)
    assert _un(ctx, """SELECT sujet, statut FROM sujet_intervention
                       WHERE compte_rendu = 'CRSANR5L17S2026O1N177' AND id_syceron = '4042278'""") == (
        None, "creneau_seul")
    # Hors de tout point (ouverture de séance) ; ordre du jour de la prochaine séance.
    assert _un(ctx, """SELECT DISTINCT statut FROM sujet_intervention WHERE type_sujet = 'hors_point'""") == (
        "intitule_non_publie",)
    assert _un(ctx, """SELECT DISTINCT sujet, statut FROM sujet_intervention WHERE code_point = 'FIN_SEAN_1_2'""") == (
        None, "procedure")


def test_sujet_relie_au_dossier_parmi_ceux_de_la_seance(reel):
    ctx, _, _ = reel
    # Deux dossiers discutés dans la séance : le titre départage.
    assert _un(ctx, """SELECT DISTINCT sujet, dossier, lien_dossier, route FROM sujet_intervention
                       WHERE compte_rendu = 'CRSANR5L17S2025O1N139' AND type_sujet = 'texte'""") == (
        "Sortir la France du piège du narcotrafic", "DLR5L17N50169", "lie", "titre_contenu")
    # Loi de finances : code de point propre (APPEL_PLF_1_20).
    assert _un(ctx, """SELECT DISTINCT sujet, dossier, code_point, type_sujet FROM sujet_intervention
                       WHERE compte_rendu = 'CRSANR5L17S2027O1N051' AND type_sujet = 'loi_de_finances'""") == (
        "Projet de loi de finances pour 2027", "DLR5L17N54629", "APPEL_PLF_1_20", "loi_de_finances")
    # « Hommage à … » : aucun dossier de la séance ne lui correspond.
    assert _un(ctx, """SELECT DISTINCT lien_dossier FROM sujet_intervention
                       WHERE sujet LIKE 'Hommage%'""") == ("non_lie",)


def test_qualite_ecrite_ou_deduite(reel):
    ctx, _, _ = reel
    # Ministre délégué : qualité écrite par le compte rendu.
    assert ctx.x("""SELECT DISTINCT qualite, qualite_source FROM qualite_orateur
                    WHERE acteur = 'PA870010'""") == [("membre_du_gouvernement", "compte_rendu")]
    # Député sans qualité écrite : déduite du mandat à la date.
    assert ctx.x("""SELECT DISTINCT qualite, qualite_source, qualite_ecrite FROM qualite_orateur
                    WHERE acteur = 'PA718850'""") == [("depute", "deduite", None)]
    # Qualité composée : classée membre du gouvernement.
    assert _un(ctx, """SELECT DISTINCT qualite FROM qualite_orateur WHERE acteur = 'PA795990'
                       AND qualite_ecrite_libelle LIKE 'ministre déléguée, porte-parole%'""") == (
        "membre_du_gouvernement",)


def test_paroles_du_gouvernement(reel):
    ctx, bilan, _ = reel
    # Lecornu II pour le 24/03/2026, Bayrou pour le 20/03/2025.
    assert ctx.x("""SELECT gouvernement, acteur, count(*) > 0 FROM parole_gouvernement
                    GROUP BY 1, 2 ORDER BY 1, 2""") == [
        ("PO855052", "PA2538", True), ("PO873634", "PA795990", True), ("PO873634", "PA870010", True)]
    assert _un(ctx, """SELECT count(*) FROM parole_gouvernement WHERE id_syceron = '4042860'""") == (0,)
    assert _un(ctx, """SELECT DISTINCT sujet FROM parole_gouvernement WHERE acteur = 'PA2538'""") == (
        "Sortir la France du piège du narcotrafic",)
    assert bilan["R-PAROLES-GOUVERNEMENT"]["couverture"]["qualite_ecrite_par_le_compte_rendu"][0] > 0


def test_ordre_du_jour_seances_publiques_de_l_assemblee(reel):
    ctx, bilan, _ = reel
    reunions = {r for (r,) in ctx.x("SELECT DISTINCT reunion FROM ordre_du_jour")}
    assert reunions == {"RUANR5L17S2026IDS30399", "RUANR5L17S2025IDS29213",
                        "RUANR5L17S2026IDS30144", "RUANR5L17S2025IDS28653"}   # ni Sénat ni commission
    assert _un(ctx, """SELECT DISTINCT statut_seance FROM ordre_du_jour
                       WHERE reunion = 'RUANR5L17S2025IDS28653'""") == ("supprimee",)
    assert ctx.x("""SELECT rang, statut_point, dossier, lien_dossier FROM ordre_du_jour
                    WHERE reunion = 'RUANR5L17S2025IDS29213' AND rang IN (0, 3, 7) ORDER BY rang""") == [
        (0, "supprime", None, "non_lie"), (3, "confirme", "DLR5L17N50169", "lie"),
        (7, "confirme", "DLR5L17N51078", "lie")]
    assert _un(ctx, """SELECT date, source_url FROM ordre_du_jour
                       WHERE reunion = 'RUANR5L17S2026IDS30399' AND rang = 0""") == (
        "2026-03-24", "https://www.assemblee-nationale.fr/dyn/17/comptes-rendus/seance/CRSANR5L17S2026O1N177")
    # Sans `matiere`, la commission reste vide, et le dit.
    assert _un(ctx, "SELECT DISTINCT matiere_statut FROM ordre_du_jour") == ("matiere_absente",)
    assert "commission_connue" not in bilan["R-ORDRE-DU-JOUR"]["couverture"]


def test_ordre_du_jour_lit_la_matiere_si_elle_existe(reel):
    _, _, tmp = reel
    ctx, bilan = appliquer(tmp / "z2", tmp / "z3m", extra=(MATIERE,))
    assert _un(ctx, """SELECT commission, matiere_statut FROM ordre_du_jour
                       WHERE dossier = 'DLR5L17N50169'""") == ("PO59051", "assemblee")
    assert _un(ctx, """SELECT commission FROM ordre_du_jour WHERE dossier = 'DLR5L17N51078'""") == (None,)
    assert bilan["R-ORDRE-DU-JOUR"]["couverture"]["commission_connue"] == [1, 2]


# --------------------------------------------------------------------------- petit jeu écrit

def _p(niv, ids, code, titre):
    return {"niv": niv, "nivpoint": str(niv), "id_syceron": ids, "code_grammaire": code,
            "valeur_ptsodj": "1", "titre": titre}


QAG = [_p(1, "P1", "TITRE_TEXTE_DISCUSSION", "Questions au gouvernement"),
       _p(2, "P2", "QG_1_1", "Prix de l’énergie")]
EAU = [_p(1, "P3", "TITRE_TEXTE_DISCUSSION", "Protection de l’eau potable (suite)"),
       _p(2, "P4", "DISC_GENERALE_1", "Discussion générale")]
PLF = [_p(1, "P5", "APPEL_PLF_1_20", "Projet de loi de finances pour 2027"),
       _p(2, "P6", "APPEL_PLF_1_30", "Première partie (suite)")]
SANS_TITRE = [_p(1, "P7", "TITRE_TEXTE_DISCUSSION", None)]


def _par(ids, orateur, nom, points, qualite=None, code="PAROLE_GENERIQUE", roledebat=None, orateurs=None):
    if orateurs is None:
        orateurs = [{"id": orateur, "nom": nom, "qualite": qualite}] if (orateur or nom) else []
    return {"compte_rendu": "CRT1", "seance": "RUT1", "date": "2026-03-24", "id_syceron": ids,
            "orateur": orateur, "orateur_nom": nom, "qualite": qualite, "orateurs": orateurs,
            "roledebat": roledebat, "code_grammaire": code, "points": points,
            "prov_url": f"https://www.assemblee-nationale.fr/dyn/17/comptes-rendus/seance/CRT1#{ids}"}


PARAGRAPHES = [
    _par("1", "PA2", "Mme Claire Martin", QAG),                       # ministre, qualité non écrite
    _par("2", "PA1", "M. Jean Durand", QAG),                          # député
    _par("3", "PA3", "M. Paul Vermorel-Marques (DR)", EAU),           # nom AMO plus court
    _par("4", "PA4", "M. Luc Bernard", EAU),                          # rapporteur du dossier
    _par("5", "PA5", "M. Hugo Petit", EAU),                           # ni député ni ministre
    _par("6", "PA6", "Mme Anne Roux", QAG, qualite="ministre"),       # « ministre » mais hors fonction
    _par("7", "PA1", "Mme la ministre", QAG),                         # libellé de civilité contraire
    _par("8", "PA0", "M. Jean Durand", EAU, code="INTERRUPTION_1_10"),
    _par("9", None, "M. Jean Durand", EAU, code="INTERRUPTION_1_10"),
    _par("10", "PA7", "Mme la présidente", EAU),                       # présidence sans roledebat
    _par("11", "PA1", "M. Jean Durand", PLF),
    _par("12", "PA1", "M. Jean Durand", []),
    _par("13", "PA1", "M. Jean Durand", SANS_TITRE),
    _par("14", "PA9999", "M. Inconnu Total", EAU),
    _par("15", "PA1", "M. Jean-Marc Cantais", EAU, qualite="policier, lanceur d’alerte"),
    _par("16", "PA4", "M. le rapporteur", EAU),                        # libellé de fonction, civilité juste
    _par("17", None, None, EAU, code="ADOP_ADT"),
    _par("18", "PA1", "Un député du groupe RN", EAU, code="INTERRUPTION_1_10"),
    _par("19", "PA1", "MM. Jean Durand et Luc Bernard", EAU, code="INTERRUPTION_1_10"),
    _par("20", "PA8", "M. Marc Faure", EAU),                          # ministre et député à la date
]
IDENTITES = [("PA1", "M.", "Jean", "Durand"), ("PA2", "Mme", "Claire", "Martin"),
             ("PA3", "M.", "Paul", "Vermorel"), ("PA4", "M.", "Luc", "Bernard"),
             ("PA5", "M.", "Hugo", "Petit"), ("PA6", "Mme", "Anne", "Roux"),
             ("PA7", "Mme", "Eva", "Leroy"), ("PA8", "M.", "Marc", "Faure")]


def _mandat(acteur, type_organe, organe, debut, fin=None):
    return {"uid": f"PM-{acteur}-{organe}", "acteur": acteur, "type_organe": type_organe,
            "organe": organe, "date_debut": debut, "date_fin": fin}


@pytest.fixture(scope="module")
def petit(tmp_path_factory):
    z2 = tmp_path_factory.mktemp("p") / "z2"
    z2.mkdir()
    ecrire_table(z2, an_comptes_rendus, "intervention", PARAGRAPHES)
    ecrire_table(z2, an_acteurs, "identite_source",
                 [{"uid": u, "civilite": c, "prenom": p, "nom": n} for u, c, p, n in IDENTITES])
    ecrire_table(z2, an_acteurs, "organe", [
        {"uid": "PO838901", "type_organe": "ASSEMBLEE", "legislature": "17", "date_debut": "2024-07-01"},
        {"uid": "POG", "type_organe": "GOUVERNEMENT", "libelle_abrege": "ESSAI", "date_debut": "2025-10-11"}])
    ecrire_table(z2, an_acteurs, "mandat", [
        _mandat("PA1", "ASSEMBLEE", "PO838901", "2024-07-18"),
        _mandat("PA3", "ASSEMBLEE", "PO838901", "2024-07-18"),
        _mandat("PA4", "ASSEMBLEE", "PO838901", "2024-07-18"),
        _mandat("PA7", "ASSEMBLEE", "PO838901", "2024-07-18"),
        _mandat("PA2", "GOUVERNEMENT", "POG", "2025-10-12"),
        _mandat("PA8", "GOUVERNEMENT", "POG", "2025-10-12"),
        _mandat("PA8", "ASSEMBLEE", "PO838901", "2024-07-18"),
        _mandat("PA6", "GOUVERNEMENT", "POG", "2025-10-12", "2026-02-01")])
    ecrire_table(z2, an_dossiers, "dossier", [
        {"uid": "DLRT1", "titre": "Protéger l'eau potable"},
        {"uid": "DLRT2", "titre": "Projet de loi de finances pour 2027"},
        {"uid": "DLRT3", "titre": "Améliorer la protection des personnes ciblées par la criminalité"}])
    ecrire_table(z2, an_dossiers, "acte", [
        {"dossier": "DLRT1", "uid": "A1", "reunion": "RUT1", "rapporteurs": ["PA4"]},
        {"dossier": "DLRT2", "uid": "A2", "reunion": "RUT1", "rapporteurs": []},
        {"dossier": "DLRT3", "uid": "A3", "reunion": "RUT1", "rapporteurs": []}])
    ecrire_table(z2, an_agenda, "reunion", [])
    ecrire_table(z2, an_agenda, "point_odj", [])
    ctx, bilan = appliquer(z2, z2.parent / "z3")
    return ctx, bilan


def _ligne(ctx, ids):
    return _un(ctx, f"""SELECT a.acteur, a.raison_non_attribuee, a.preside, q.qualite, q.qualite_source,
                               s.sujet, s.statut, s.dossier
                        FROM intervention_attribuee a
                        LEFT JOIN qualite_orateur q USING (compte_rendu, id_syceron)
                        LEFT JOIN sujet_intervention s USING (compte_rendu, id_syceron)
                        WHERE a.id_syceron = '{ids}'""")


def test_petit_attribution(petit):
    ctx, _ = petit
    raisons = dict(ctx.x("SELECT id_syceron, raison_non_attribuee FROM intervention_attribuee"))
    assert raisons == {
        "1": None, "2": None, "3": None, "4": None, "5": None, "6": None,
        "7": "nom_discordant", "8": "identifiant_nul", "9": "interpellation", "10": None,
        "11": None, "12": None, "13": None, "14": "identifiant_inconnu",
        "15": "personne_hors_assemblee", "16": None, "17": "sans_orateur",
        "18": "orateur_collectif", "19": "plusieurs_orateurs", "20": None}
    assert _ligne(ctx, "10")[:3] == ("PA7", None, True)
    assert _un(ctx, "SELECT interruption FROM intervention_attribuee WHERE id_syceron = '8'") == (True,)


def test_petit_qualite_deduite_et_non_etablie(petit):
    ctx, bilan = petit
    assert _ligne(ctx, "1")[3:5] == ("membre_du_gouvernement", "deduite")
    assert _ligne(ctx, "2")[3:5] == ("depute", "deduite")
    assert _ligne(ctx, "4")[3:5] == ("rapporteur", "deduite")      # rapporteur du dossier du sujet
    assert _ligne(ctx, "5")[3:5] == (None, None)
    assert _un(ctx, "SELECT raison_non_etablie FROM qualite_orateur WHERE id_syceron = '5'") == (
        "qualite_non_etablie",)
    assert _ligne(ctx, "6")[3:5] == ("membre_du_gouvernement", "compte_rendu")
    # Ministre et député à la fois à la date (ministres démissionnaires élus en juillet 2024) :
    # rien n'est déduit.
    assert _un(ctx, """SELECT qualite, raison_non_etablie, gouvernement_a_la_date FROM qualite_orateur
                       WHERE id_syceron = '20'""") == (None, "gouvernement_et_assemblee_a_la_date", "POG")
    n, d = bilan["R-QUALITE"]["couverture"]["qualite_etablie"]
    assert n == d - 2


def test_petit_paroles_du_gouvernement(petit):
    ctx, bilan = petit
    # La ministre en fonction (qualité déduite) ; pas la « ministre » sortie le 01/02/2026.
    assert ctx.x("""SELECT gouvernement, acteur, id_syceron, qualite_source, sujet
                    FROM parole_gouvernement""") == [("POG", "PA2", "1", "deduite", "Prix de l’énergie")]
    assert bilan["R-PAROLES-GOUVERNEMENT"]["couverture"]["qualite_gouvernementale_retenue"] == [1, 2]


def test_petit_sujets(petit):
    ctx, _ = petit
    assert _ligne(ctx, "3")[5:] == ("Protection de l’eau potable", "etabli", "DLRT1")   # « (suite) » ôté
    assert _un(ctx, "SELECT route FROM sujet_intervention WHERE id_syceron = '3'") == ("mots_communs",)
    assert _ligne(ctx, "11")[5:] == ("Projet de loi de finances pour 2027", "etabli", "DLRT2")
    assert _ligne(ctx, "12")[5:] == (None, "intitule_non_publie", None)
    assert _ligne(ctx, "13")[5:] == (None, "intitule_non_publie", None)
