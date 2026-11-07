"""Règles du groupe E2 — activité d'une personne : R-TEXTE-PORTE, R-AMENDEMENT, R-PERIODE,
R-VOTE-PERSONNE, R-DIVERGENCE, R-PAROLE-PERSONNE, R-QUESTION-PERSONNE.

Deux jeux :
- `reel` : extraits réels lus par le vrai cadre (`Entrepot` + `Lecture`) — comptes rendus,
  acteurs (François Ruffin, une vice-présidente…), agenda, amendements, questions, dossiers
  (`an_dossiers_l17_extrait.zip`, `e2_dossiers_l17_extrait.zip`), scrutins
  (`e2_scrutins_l17_extrait.zip` : deux dernières lectures du 21/07/2026 et une motion de
  censure ; fiche `extraits/e2_activite.md`), complétés de quelques organes, mandats et actes
  réels recopiés champ par champ (faits lus de la XVIIe, collecte du 06/11/2026) ;
- petites tables écrites ici pour les cas que les extraits ne couvrent pas.

`membre_gouvernement` (R-COMPOSITION, groupe A) est remplacée par une règle de substitution tirée
des mandats GOUVERNEMENT : R-QUALITE n'en lit que les colonnes du contrat."""
import os
import types

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from empreinte_src.depaquetage import depaqueter
from empreinte_src.entrepot import Entrepot
from empreinte_src.lecture import COLONNES_PROVENANCE, Lecture
from empreinte_src.lecteurs import (an_acteurs, an_agenda, an_amendements, an_comptes_rendus,
                                    an_dossiers, an_questions, an_scrutins)
from empreinte_src.liaison import Contexte, ordonner, relier
from empreinte_src.regles import (r_49_3, r_amendement, r_appartenance, r_depot_gouvernement,
                                  r_derniere_lecture, r_deputes, r_divergence, r_etape,
                                  r_gouvernements, r_legislatures, r_lien_scrutin_dossier, r_lois,
                                  r_matiere, r_nature_scrutin, r_orateur, r_origine,
                                  r_parole_personne, r_periode, r_qualite, r_question_personne,
                                  r_sort_final, r_sujet, r_texte_porte, r_vote_personne)

EXTRAITS = os.path.join(os.path.dirname(__file__), "extraits")
SOURCES = [
    ({"id": "an-syceron-l17", "type": "comptes_rendus"}, "syceron_l17_extrait.zip"),
    ({"id": "an-amo30-l17", "type": "acteurs_organes"}, "amo30_l17_orateurs_extrait.zip"),
    ({"id": "an-agenda-l17", "type": "agenda"}, "agenda_l17_seances_extrait.zip"),
    ({"id": "an-scrutins-l17", "type": "scrutins"}, "e2_scrutins_l17_extrait.zip"),
    ({"id": "an-dossiers-l17", "type": "dossiers"}, "an_dossiers_l17_extrait.zip"),
    ({"id": "an-dossiers-l17-e2", "type": "dossiers"}, "e2_dossiers_l17_extrait.zip"),
    ({"id": "an-amendements-l17", "type": "amendements"}, "amendements_l17_extrait.zip"),
    ({"id": "an-qe-l17", "type": "questions_ecrites"}, "questions_ecrites_l17_extrait.zip"),
    ({"id": "an-qg-l17", "type": "questions_gouvernement"}, "questions_gouvernement_l17_extrait.zip"),
    ({"id": "an-qosd-l17", "type": "questions_orales"}, "questions_orales_l17_extrait.zip"),
]
LECTEURS = [an_comptes_rendus, an_acteurs, an_agenda, an_scrutins, an_dossiers, an_amendements,
            an_questions]
AMONT = [r_legislatures, r_gouvernements, r_appartenance, r_deputes, r_nature_scrutin,
         r_lien_scrutin_dossier, r_origine, r_derniere_lecture, r_matiere, r_etape, r_49_3, r_lois,
         r_sort_final, r_depot_gouvernement, r_orateur, r_sujet, r_qualite]
GROUPE_E2 = [r_texte_porte, r_amendement, r_periode, r_vote_personne, r_divergence,
             r_parole_personne, r_question_personne]

# Organes réels absents de l'extrait AMO (AMO30 XVIIe, collecte du 06/11/2026).
ORGANES = [
    {"uid": "PO845439", "type_organe": "GP", "legislature": "17", "sigle": "ECOS",
     "libelle": "Écologiste et Social", "libelle_abrege": "EcoS", "date_debut": "2024-07-18"},
    {"uid": "PO845407", "type_organe": "GP", "legislature": "17", "sigle": "EPR",
     "libelle": "Ensemble pour la République", "libelle_abrege": "EPR", "date_debut": "2024-07-18"},
    {"uid": "PO840056", "type_organe": "GP", "legislature": "17", "sigle": "NI",
     "libelle": "Non inscrit", "date_debut": "2024-07-08"},
    {"uid": "PO847639", "type_organe": "GOUVERNEMENT", "libelle_abrege": "BARNIER",
     "date_debut": "2024-09-06", "date_fin": "2024-12-13"},
    {"uid": "PO873418", "type_organe": "GOUVERNEMENT", "libelle_abrege": "LECORNU",
     "date_debut": "2025-09-10", "date_fin": "2025-10-10"},
    {"uid": "PO59047", "type_organe": "COMPER", "libelle": "Commission des affaires étrangères"},
    {"uid": "PO419604", "type_organe": "COMPER",
     "libelle": "Commission des affaires culturelles et de l'éducation"},
    {"uid": "PO419610", "type_organe": "COMPER", "libelle": "Commission des affaires économiques"},
    {"uid": "PO420120", "type_organe": "COMPER", "libelle": "Commission des affaires sociales"},
    {"uid": "PO59051", "type_organe": "COMPER", "libelle": "Commission des lois constitutionnelles, "
     "de la législation et de l'administration générale de la République"},
    {"uid": "PO883517", "type_organe": "CNPS", "libelle": "Commission spéciale chargée d’examiner "
     "le projet de loi relatif à la protection des enfants"},
]
# Mandats réels d'une députée absente de l'extrait AMO (elle vote « pour » le 21/07/2026 quand son
# groupe s'abstient).
MANDATS = [
    {"uid": "PM843563", "acteur": "PA842013", "organe": "PO838901", "type_organe": "ASSEMBLEE",
     "legislature": "17", "qualite": "membre", "date_debut": "2024-07-07",
     "date_prise_fonction": "2024-07-08", "cause_mandat": "élections générales",
     "circonscription": "PO839975"},
    {"uid": "PM843564", "acteur": "PA842013", "organe": "PO840056", "type_organe": "GP",
     "legislature": "17", "qualite": "Député non-inscrit", "date_debut": "2024-07-08",
     "date_fin": "2024-07-18"},
    {"uid": "PM846038", "acteur": "PA842013", "organe": "PO845439", "type_organe": "GP",
     "legislature": "17", "qualite": "Membre du", "date_debut": "2024-07-19"},
]
# Saisines au fond réelles des deux dossiers votés le 21/07/2026, et leurs dossiers.
ACTES = [
    {"dossier": "DLR5L17N54372", "uid": "L17-VD232177CFS", "type_acte": "SaisieComFond_Type",
     "code": "AN1-COM-FOND-SAISIE", "date": "2026-05-27T00:00:00.000+02:00", "organe": "PO883517"},
    {"dossier": "DLR5L17N53187", "uid": "L17-VD228800CFS", "type_acte": "SaisieComFond_Type",
     "code": "AN1-COM-FOND-SAISIE", "date": "2025-11-18T00:00:00.000+01:00", "organe": "PO419604"},
]
DOSSIERS = [
    {"uid": "DLR5L17N54372", "legislature": "17", "procedure_code": "1",
     "titre": "Projet de loi relatif à la protection des enfants"},
    {"uid": "DLR5L17N53187", "legislature": "17", "procedure_code": "2",
     "titre": "Protéger les mineurs des risques auxquels les expose l’utilisation des réseaux sociaux"},
]
RUFFIN = "PA722142"


def _composition(ctx):
    ctx.ecrire("membre_gouvernement", """
        SELECT m.organe AS gouvernement, m.acteur, min(m.date_debut) AS debut,
               max(least(coalesce(m.date_fin, g.fin, '9999-12-31'), coalesce(g.fin, '9999-12-31'))) AS fin
        FROM an_acteurs__mandat m JOIN gouvernement g ON g.organe = m.organe
        WHERE m.type_organe = 'GOUVERNEMENT' GROUP BY 1, 2""")
    return {}


COMPOSITION = types.SimpleNamespace(NOM="R-COMPOSITION", VERSION=0, DEPEND=("R-GOUVERNEMENTS",),
                                    SORTIES=("membre_gouvernement",), appliquer=_composition)


def _schema(mod, table):
    schema = mod.TABLES[table]
    for nom, t in COLONNES_PROVENANCE:
        if nom not in schema.names:
            schema = schema.append(pa.field(nom, t))
    return schema


def ajouter(z2, mod, table, lignes):
    """Ajoute de petites lignes (schéma du lecteur, provenance « test ») à une table de faits,
    créée vide au besoin."""
    p = os.path.join(z2, f"{mod.NOM}__{table}.parquet")
    schema = _schema(mod, table)
    base = pq.read_table(p).to_pylist() if os.path.exists(p) else []
    if base:
        schema = pq.read_schema(p)
    schema = pa.schema([f.with_nullable(True) for f in schema])
    listes = {f.name for f in schema if pa.types.is_list(f.type)}
    rows = list(base)
    for k, r in enumerate(lignes):
        x = {n: ([] if n in listes else None) for n in schema.names}
        x.update({"prov_point": "test", "prov_uid": f"{table}-test-{k}", "prov_version": 1,
                  "prov_etat": "present"})
        x.update(r)
        rows.append({n: x.get(n) for n in schema.names})
    pq.write_table(pa.Table.from_pylist(rows, schema=schema), p)


def tables_vides(z2):
    """Toutes les tables de faits lues par les règles, vides si aucun extrait ne les remplit."""
    for mod in LECTEURS:
        for t in mod.TABLES:
            if not os.path.exists(os.path.join(z2, f"{mod.NOM}__{t}.parquet")):
                ajouter(z2, mod, t, [])


def relier_e2(z2, z3, regles=(), date_reference="2026-11-06"):
    ctx = Contexte(str(z2), str(z3), date_reference=date_reference)
    bilan = relier(ctx, ordonner([COMPOSITION, *AMONT, *GROUPE_E2, *regles]))
    return ctx, {b["regle"].split("@")[0]: b for b in bilan}


def lignes(ctx, sql):
    r = ctx.con.execute(sql)
    cols = [d[0] for d in r.description]
    return [dict(zip(cols, x)) for x in r.fetchall()]


def une(ctx, sql):
    r = lignes(ctx, sql)
    assert len(r) == 1, (sql, r)
    return r[0]


@pytest.fixture(scope="module")
def reel(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("e2")
    e = Entrepot(str(tmp / "e"))
    for pa_, zip_ in SOURCES:
        pa_ = {**pa_, "source": "an", "format": "zip", "url": "http://exemple.invalid/x.zip"}
        e.versionner(pa_, f"R{e.generation}", depaqueter(os.path.join(EXTRAITS, zip_), "zip"), complet=True)
    e.clore("test")
    cfg = {"points_acces": [{"id": p["id"], "licence": "etalab-2.0"} for p, _ in SOURCES]}
    lecture = Lecture(Entrepot(str(tmp / "e")), str(tmp / "z2"), cfg)
    for mod in LECTEURS:
        assert lecture.executer(mod)["illisibles"] == 0
    z2 = tmp / "z2"
    ajouter(z2, an_acteurs, "organe", ORGANES)
    ajouter(z2, an_acteurs, "mandat", MANDATS)
    ajouter(z2, an_dossiers, "acte", ACTES)
    ajouter(z2, an_dossiers, "dossier", DOSSIERS)
    tables_vides(z2)
    ctx, bilan = relier_e2(z2, tmp / "z3")
    return ctx, bilan


# --------------------------------------------------------------------------- jeu réel : textes portés

def test_texte_porte_reel_auteur_rapporteur_et_initiative_gouvernementale(reel):
    ctx, _ = reel
    # Ruffin, auteur et rapporteur de la résolution européenne sur l'accord UE-Mercosur, adoptée.
    r = {x["role"]: x for x in lignes(ctx, f"SELECT * FROM texte_porte WHERE acteur = '{RUFFIN}'")}
    assert set(r) == {"auteur", "rapporteur"}
    a = r["auteur"]
    assert (a["dossier"], a["document"], a["nature"], a["date_depot"]) == (
        "DLR5L17N52728", "PNREANR5L17B1785", "proposition_de_resolution", "2025-09-15")
    assert (a["etape_atteinte"], a["sort"], a["publiable"], a["matiere"]) == ("adopte", "adopte", True, "PO59047")
    assert (r["rapporteur"]["qualite_rapporteur"], r["rapporteur"]["date_role"]) == ("rapporteur", "2025-10-22")
    assert ctx.un("""SELECT count(*) FROM texte_porte WHERE dossier = 'DLR5L17N52728'
                     AND role = 'cosignataire'""") == 105
    # Projet de loi : initiative gouvernementale, jamais « auteur » ; gouvernement du dépôt.
    p = une(ctx, """SELECT * FROM texte_porte WHERE document = 'PRJLANR5L17B2155'
                    AND role <> 'rapporteur'""")
    assert (p["role"], p["nature"], p["gouvernement"], p["sort"]) == (
        "initiative_gouvernementale", "projet_de_loi", "PO873634", "promulgue")
    assert ctx.un("SELECT count(*) FROM texte_porte WHERE nature = 'projet_de_loi' AND role = 'auteur'") == 0


def test_texte_porte_reel_cosignature_retiree_non_publiable(reel):
    ctx, _ = reel
    r = une(ctx, "SELECT * FROM texte_porte WHERE document = 'PNREANR5L17B0643' AND date_retrait IS NOT NULL")
    assert (r["role"], r["publiable"], r["raison_non_publiable"]) == ("cosignataire", False, "cosignature_retiree")


# --------------------------------------------------------------------------- jeu réel : amendements

def test_amendements_reel_copies_sorts_et_signatures(reel):
    ctx, b = reel
    c = b["R-AMENDEMENT"]["couverture"]
    assert c["amendements_distincts_sur_uid"] == [12, 13] and c["copies_divergentes"] == [0, 1]
    # Paire B/BTC : la copie du texte examiné (BTC) est retenue, l'autre est un alias.
    p = une(ctx, "SELECT * FROM amendement_canonique WHERE amendement LIKE '%2202P0D1N000011'")
    assert p["amendement"] == "AMANR5L17PO838901BTC2202P0D1N000011"
    assert p["alias"] == ["AMANR5L17PO838901B2202P0D1N000011"] and p["nb_copies"] == 2
    assert (p["dossier"], p["raison_dossier"]) == (None, "document_vise_absent_des_dossiers")
    # Adresse publique : la page /dyn/17/amendements/<uid> redirige vers celle de l'amendement.
    assert p["source_url"] == "https://www.assemblee-nationale.fr/dyn/17/amendements/AMANR5L17PO838901BTC2202P0D1N000011"
    assert p["raison_source_url"] is None
    s = {x["amendement"][9:]: (x["sort"], x["famille_sort"], x["acteur"], x["type_auteur"])
         for x in lignes(ctx, "SELECT * FROM amendement_canonique")}
    assert s["PO838901B1906P1D2N000001"][:3] == ("efface", "efface", None)
    assert s["PO838901BTC2468P0D1N000300"] == ("adopte", "discute", None, "Gouvernement")
    assert s["PO838901BTC1245P0D1N000038"][:2] == ("irrecevable", "irrecevable_autre")    # doublon
    assert s["PO838901B0622P0D1N000312"][:2] == ("en_traitement", "en_cours")             # sous-état « R »
    assert s["PO838901B1851P0D1N000018"][:2] == ("retire_avant_publication", "retire")
    # Commission : l'organe d'examen quand c'est une commission.
    r = une(ctx, "SELECT * FROM amendement_canonique WHERE amendement = 'AMANR5L17PO419610B1906P2D1N000024'")
    assert (r["commission"], r["commission_source"]) == ("PO419610", "organe_examen")
    # Cosignataire cité deux fois : une seule signature ; l'amendement compte une fois.
    sig = lignes(ctx, """SELECT * FROM amendement_auteur
                         WHERE amendement = 'AMANR5L17PO419610B1906P2D1N000024' AND acteur = 'PA795482'""")
    assert len(sig) == 1 and sig[0]["cite_plusieurs_fois"] and sig[0]["role"] == "cosignataire"
    assert ctx.un("""SELECT count(*) FROM amendement_auteur WHERE role = 'auteur'""") == ctx.un(
        "SELECT count(*) FROM amendement_canonique WHERE acteur IS NOT NULL")
    # Aucun taux : aucune colonne de ratio.
    cols = [x[0] for x in ctx.x("DESCRIBE amendement_canonique")]
    assert not [c for c in cols if "taux" in c or "ratio" in c or "part_" in c]


def test_amendement_banc_au_depot_non_declare(reel):
    ctx, _ = reel
    r = une(ctx, "SELECT * FROM amendement_canonique WHERE amendement = 'AMANR5L17PO838901B3210P2D1N001096'")
    assert (r["banc_au_depot"], r["type_auteur"]) == ("non_declaree", "Rapporteur")


# --------------------------------------------------------------------------- jeu réel : votes

def test_vote_une_position_par_texte_en_derniere_lecture(reel):
    ctx, b = reel
    v = {x["scrutin"]: x for x in lignes(ctx, f"SELECT * FROM vote_personne WHERE acteur = '{RUFFIN}'")}
    assert set(v) == {"VTANR5L17V8430", "VTANR5L17V8431", "VTANR5L17V5154"}
    p = v["VTANR5L17V8430"]                                  # projet de loi « protection des enfants »
    assert (p["dossier"], p["position"], p["nature"], p["derniere_lecture"], p["origine"]) == (
        "DLR5L17N54372", "abstention", "ensemble", True, "projet")
    assert (p["matiere"], p["groupe"], p["groupe_scrutin"], p["gouvernement"], p["banc"]) == (
        "PO883517", "PO845439", "PO845439", "PO873634", "non_declaree")
    assert p["periode"] == "PA722142/2025-10-11" and p["par_delegation"] is True
    assert (v["VTANR5L17V8431"]["origine"], v["VTANR5L17V8431"]["matiere"]) == ("proposition", "PO419604")
    # Motion de censure : à part, jamais une position sur un texte ; elle porte sur deux dossiers.
    m = v["VTANR5L17V5154"]
    assert (m["nature"], m["derniere_lecture"], m["position"], m["dossier"]) == (
        "motion_censure", False, "pour", None)
    assert m["dossiers"] == ["DLR5L17N52428", "DLR5L17N53597"]
    # Non-votant nommé (présidence de séance) : position servie avec sa cause.
    n = une(ctx, "SELECT * FROM vote_personne WHERE acteur = 'PA721908' AND scrutin = 'VTANR5L17V8431'")
    assert (n["position"], n["cause_non_votant"]) == ("non_votant", "PAN")
    # Mise au point servie à part, sans remplacer le vote enregistré.
    mp = une(ctx, "SELECT * FROM vote_personne WHERE acteur = 'PA335054' AND scrutin = 'VTANR5L17V8431'")
    assert (mp["position"], mp["mise_au_point"]) == ("pour", "abstention")
    assert b["R-VOTE-PERSONNE"]["couverture"]["position_nommee_en_derniere_lecture"] == [987, 987]


def test_49_3_jamais_une_position(reel):
    ctx, _ = reel
    assert ctx.un("SELECT count(*) FROM vote_personne WHERE scrutin IN (SELECT acte FROM engagement_49_3)") == 0
    assert ctx.un("SELECT count(*) FROM vote_personne WHERE nature NOT IN ('ensemble', 'motion_censure')") == 0


# --------------------------------------------------------------------------- jeu réel : divergence

def test_divergence_reelle_cinq_conditions(reel):
    ctx, b = reel
    d = {(x["acteur"], x["scrutin"]): x for x in lignes(ctx, "SELECT * FROM divergence")}
    # 21/07/2026, projet « protection des enfants » : le groupe EcoS s'abstient (33), PA842013 vote pour.
    x = d[("PA842013", "VTANR5L17V8430")]
    assert (x["position"], x["position_groupe"], x["diverge"], x["groupe_divise"]) == ("pour", "abstention", True, True)
    assert (x["groupe_pour"], x["groupe_abstentions"], x["sigle"]) == (3, 33, "ECOS")
    assert d[(RUFFIN, "VTANR5L17V8430")]["diverge"] is False
    # 21/07/2026, réseaux sociaux : « contre » publié pour un groupe à 19 pour, 7 contre, 7 abstentions
    # (les listes nominatives le confirment) : position du groupe non établie, aucune ligne.
    assert (RUFFIN, "VTANR5L17V8431") not in d
    assert ctx.un("""SELECT position_majoritaire FROM an_scrutins__decompte_groupe
                     WHERE scrutin = 'VTANR5L17V8431' AND organe = 'PO845439'""") == "contre"
    # Non-votant (présidence) et motion de censure : jamais comparés.
    assert ("PA721908", "VTANR5L17V8430") not in d
    assert "VTANR5L17V5154" not in {k[1] for k in d}
    c = b["R-DIVERGENCE"]["couverture"]
    assert c["dont_position_publiee_contredite_par_le_decompte"][0] == 1
    assert c["exclues_position_personne_non_votant"][0] == 3


def test_divergence_aucun_total(reel):
    ctx, b = reel
    cols = [x[0] for x in ctx.x("DESCRIBE divergence")]
    assert not [c for c in cols if c.startswith(("nb_", "total", "nombre_divergences", "taux"))]
    assert not [k for k in b["R-DIVERGENCE"]["couverture"] if "diverge" in k and "comparables" not in k]


# --------------------------------------------------------------------------- jeu réel : périodes

def test_periode_reelle_change_avec_le_gouvernement(reel):
    ctx, _ = reel
    p = lignes(ctx, f"""SELECT * FROM periode_position WHERE acteur = '{RUFFIN}' AND legislature = 17
                        ORDER BY debut""")
    assert [(x["debut"], x["fin"], x["gouvernement"]) for x in p] == [
        ("2024-07-08", "2024-09-05", None),            # Attal : absent de l'extrait d'organes
        ("2024-09-06", "2024-12-13", "PO847639"), ("2024-12-14", "2025-09-09", "PO855052"),
        ("2025-09-10", "2025-10-10", "PO873418"), ("2025-10-11", None, "PO873634")]
    assert {x["banc"] for x in p} == {"non_declaree"}
    # Non-inscrit (8-18/07/2024) puis EcoS : banc non déclaré des deux côtés, pas de coupure.
    assert "sans_groupe" in p[0]["raisons_banc"]


# --------------------------------------------------------------------------- jeu réel : paroles, questions

def test_paroles_reelles(reel):
    ctx, _ = reel
    # « Mme Alice Rufo, ministre déléguée » sous l'identifiant de Ruffin : jamais servi à Ruffin.
    assert ctx.un(f"SELECT count(*) FROM parole_personne WHERE acteur = '{RUFFIN}'") == 0
    assert ctx.un("SELECT count(*) FROM parole_personne WHERE id_syceron = '4042860'") == 0
    # Présidence de séance : gardée, marquée.
    assert ctx.un("SELECT bool_and(preside) FROM parole_personne WHERE acteur = 'PA721908'") is True
    r = une(ctx, """SELECT * FROM parole_personne
                    WHERE compte_rendu = 'CRSANR5L17S2025O1N139' AND id_syceron = '3673703'""")
    assert (r["acteur"], r["qualite"], r["qualite_source"], r["dossier"]) == (
        "PA2538", "membre_du_gouvernement", "compte_rendu", "DLR5L17N50169")
    assert r["sujet"] == "Sortir la France du piège du narcotrafic"
    assert (len(r["extrait"]), r["extrait_tronque"], r["longueur"]) == (300, True, 1041)
    assert r["source_url"] == ("https://www.assemblee-nationale.fr/dyn/17/comptes-rendus/seance/"
                               "CRSANR5L17S2025O1N139#3673703")


def test_questions_reelles(reel):
    ctx, b = reel
    q = {x["question"]: x for x in lignes(ctx, "SELECT * FROM question_personne")}
    g = q["QANR5L17QG390"]
    assert (g["type"], g["date"], g["date_nature"], g["date_reponse"]) == (
        "au_gouvernement", "2025-02-12", "seance_de_la_reponse", "2025-02-12")
    assert (q["QANR5L17QOSD680"]["type"], q["QANR5L17QOSD680"]["date_reponse"]) == ("orale_sans_debat", None)
    e = q["QANR5L17QE2225"]                                   # quatre ministères attributaires
    assert (e["type"], e["ministere"], e["ministere_attributaire"]) == ("ecrite", "PO847668", "PO873685")
    assert all(x["source_url"] == f"https://www.assemblee-nationale.fr/dyn/17/questions/{u}"
               and x["raison_source_url"] is None for u, x in q.items())
    assert b["R-QUESTION-PERSONNE"]["couverture"]["adresse_publique_verifiable"] == [6, 6]


# --------------------------------------------------------------------------- petites tables

def _petit(tmp_path, tables=None):
    """Z2 de petites tables : {(lecteur, table): lignes} ; le reste vide."""
    z2 = tmp_path / "z2"
    os.makedirs(z2)
    base = {(an_acteurs, "organe"): [
        {"uid": "PO838901", "type_organe": "ASSEMBLEE", "legislature": "17", "date_debut": "2024-07-01"},
        {"uid": "PO847639", "type_organe": "GOUVERNEMENT", "libelle_abrege": "BARNIER",
         "date_debut": "2024-09-06", "date_fin": "2024-12-13"},
        {"uid": "PO855052", "type_organe": "GOUVERNEMENT", "libelle_abrege": "BAYROU",
         "date_debut": "2024-12-14", "date_fin": "2025-09-09"}]}
    for (mod, t), l in {**base, **(tables or {})}.items():
        ajouter(z2, mod, t, l)
    tables_vides(z2)
    return relier_e2(z2, tmp_path / "z3")


SORTS_COUPLES = [
    ("DI", "Discuté", "Adopté", "adopte", "discute"),
    ("DI", "Discuté", "Retiré", "retire", "retire"),
    ("RT", "Retiré", "Retiré après publication", "retire", "retire"),
    ("RT", "Retiré", "R", "retire", "retire"),
    ("IR", "Irrecevable 40", "Gage", "irrecevable", "irrecevable_40"),
    ("IRRAIF", "Irrecevable", "Autre irrecevabilité 40", "irrecevable", "irrecevable_40"),
    ("IRR45", "Irrecevable", "Entonnoir (45)", "irrecevable", "irrecevable_45"),
    ("IRRHC", "Irrecevable", "Hors champ", "irrecevable", "irrecevable_autre"),
    ("AC", "A discuter", None, "a_discuter", "en_cours"),
    ("XX", "Inconnu", None, "non_etabli", "non_etablie"),
]


@pytest.mark.parametrize("etat_code,etat,sous_etat,sort,famille", SORTS_COUPLES)
def test_sort_normalise_par_la_table(tmp_path, etat_code, etat, sous_etat, sort, famille):
    am = {"uid": "AMANR5L17PO59051B0001P0D1N000001", "examen": "EXANR5L17PO59051B0001P0D1",
          "numero_long": "1", "auteur": "PA1", "type_auteur": "Député", "date_depot": "2025-01-10",
          "etat_code": etat_code, "etat": etat, "sous_etat": sous_etat, "organe_examen": "PO59051",
          "document": "PIONANR5L17B0001"}
    ctx, b = _petit(tmp_path, {(an_amendements, "amendement"): [am]})
    r = une(ctx, "SELECT * FROM amendement_canonique")
    assert (r["sort"], r["famille_sort"]) == (sort, famille)
    assert b["R-AMENDEMENT"]["couverture"]["sort_etabli"] == [int(sort != "non_etabli"), 1]


def test_copies_divergentes_signalees_et_commission_du_dossier(tmp_path):
    """Deux copies B/BTC dont les cosignataires diffèrent : la copie de l'examen fait foi, la
    divergence est signalée. En séance, la commission est la matière du dossier visé."""
    base = {"examen": "EXANR5L17PO838901BTC0002P0D1", "numero_long": "7", "auteur": "PA1",
            "type_auteur": "Député", "date_depot": "2025-01-10", "etat_code": "DI", "etat": "Discuté",
            "sous_etat": "Rejeté", "organe_examen": "PO838901"}
    am = [{**base, "uid": "AMANR5L17PO838901B0002P0D1N000007", "chronotag": "2",
           "document": "PIONANR5L17B0002"},
          {**base, "uid": "AMANR5L17PO838901BTC0002P0D1N000007", "chronotag": "1",
           "document": "PIONANR5L17BTC0002"}]
    sig = [{"amendement": am[0]["uid"], "acteur": "PA1", "role": "auteur", "rang": 0},
           {"amendement": am[0]["uid"], "acteur": "PA2", "role": "cosignataire", "rang": 1},
           {"amendement": am[1]["uid"], "acteur": "PA1", "role": "auteur", "rang": 0}]
    doc = [{"uid": "PIONANR5L17BTC0002", "dossier": "DLR5L17N1", "profondeur": 0}]
    saisine = [{"dossier": "DLR5L17N1", "uid": "L17-S1", "type_acte": "SaisieComFond_Type",
                "code": "AN1-COM-FOND-SAISIE", "date": "2025-01-05T00:00:00.000+01:00", "organe": "PO59051"}]
    org = [{"uid": "PO59051", "type_organe": "COMPER", "libelle": "Commission des lois"},
           {"uid": "PO838901", "type_organe": "ASSEMBLEE", "legislature": "17", "date_debut": "2024-07-01"}]
    ctx, b = _petit(tmp_path, {(an_amendements, "amendement"): am, (an_amendements, "signature"): sig,
                                 (an_dossiers, "document"): doc, (an_dossiers, "acte"): saisine,
                                 (an_dossiers, "dossier"): [{"uid": "DLR5L17N1", "legislature": "17"}],
                                 (an_acteurs, "organe"): org})
    r = une(ctx, "SELECT * FROM amendement_canonique")
    assert r["amendement"] == "AMANR5L17PO838901BTC0002P0D1N000007"     # pas la plus récente
    assert r["copies_divergentes"] is True and r["alias"] == ["AMANR5L17PO838901B0002P0D1N000007"]
    assert (r["commission"], r["commission_source"], r["dossier"]) == ("PO59051", "matiere_du_dossier", "DLR5L17N1")
    assert [x["acteur"] for x in lignes(ctx, "SELECT acteur FROM amendement_auteur")] == ["PA1"]
    assert b["R-AMENDEMENT"]["couverture"]["copies_divergentes"] == [1, 1]


def _acte(dossier, uid, type_acte, code, date, **k):
    return {"dossier": dossier, "uid": uid, "type_acte": type_acte, "code": code,
            "date": f"{date}T00:00:00.000+01:00", **k}


def test_texte_porte_publiable_seulement_apres_examen_en_commission(tmp_path):
    """La saisine (code « COM ») est posée le jour du dépôt : elle ne prouve pas l'examen. Un
    rapport déposé, si."""
    doc = [{"uid": "PIONANR5L17B0010", "dossier": "DA", "profondeur": 0, "date_depot": "2025-01-10",
            "auteurs_acteurs": ["PA1"], "auteurs_qualites": ["auteur"]},
           # Une personne citée deux fois parmi les auteurs (71 documents du Sénat en XVIIe) : une ligne.
           {"uid": "PIONANR5L17B0011", "dossier": "DB", "profondeur": 0, "date_depot": "2025-01-10",
            "auteurs_acteurs": ["PA1", "PA1"], "auteurs_qualites": ["auteur", "auteur"]},
           {"uid": "PRJLANR5L17B0012", "dossier": "DC", "profondeur": 0, "date_depot": "2025-01-10",
            "auteurs_acteurs": ["PA9", "PA8"], "auteurs_qualites": ["auteur", "auteur"]}]
    actes = [_acte("DA", "L17-A1", "DepotInitiative_Type", "AN1-DEPOT", "2025-01-10", texte_associe="PIONANR5L17B0010"),
             _acte("DA", "L17-A2", "SaisieComFond_Type", "AN1-COM-FOND-SAISIE", "2025-01-10", organe="PO59051"),
             _acte("DB", "L17-B1", "DepotInitiative_Type", "AN1-DEPOT", "2025-01-10", texte_associe="PIONANR5L17B0011"),
             _acte("DB", "L17-B2", "DepotRapport_Type", "AN1-COM-FOND-RAPPORT", "2025-02-01"),
             _acte("DB", "L17-B3", "NominRapporteurs_Type", "AN1-COM-FOND-NOMIN", "2025-01-20",
                   rapporteurs=["PA2"], rapporteurs_types=["rapporteur"]),
             _acte("DC", "L17-C1", "DepotInitiative_Type", "AN1-DEPOT", "2025-01-10", texte_associe="PRJLANR5L17B0012")]
    dos = [{"uid": d, "legislature": "17", "procedure_code": "2"} for d in ("DA", "DB", "DC")]
    ctx, _ = _petit(tmp_path, {(an_dossiers, "document"): doc, (an_dossiers, "acte"): actes,
                                 (an_dossiers, "dossier"): dos})
    tous = lignes(ctx, "SELECT * FROM texte_porte")
    t = {(x["acteur"], x["dossier"], x["role"]): x for x in tous}
    assert len(t) == len(tous) == 5
    assert t[("PA1", "DB", "auteur")]["rang"] == 1
    assert (t[("PA1", "DA", "auteur")]["etape_atteinte"], t[("PA1", "DA", "auteur")]["publiable"],
            t[("PA1", "DA", "auteur")]["raison_non_publiable"]) == ("depot", False, "pas_encore_examine_en_commission")
    assert (t[("PA1", "DB", "auteur")]["etape_atteinte"], t[("PA1", "DB", "auteur")]["publiable"]) == (
        "examen_commission", True)
    assert (t[("PA2", "DB", "rapporteur")]["document"], t[("PA2", "DB", "rapporteur")]["date_role"]) == (
        "PIONANR5L17B0011", "2025-01-20")
    # Projet de loi : chacun des signataires reçoit le rôle d'initiative gouvernementale, jamais « auteur ».
    assert {k[2] for k in t if k[1] == "DC"} == {"initiative_gouvernementale"}
    assert t[("PA9", "DC", "initiative_gouvernementale")]["gouvernement"] == "PO855052"   # Bayrou


def _mandat(uid, acteur, organe, type_organe, debut, fin=None, leg="15", **k):
    return {"uid": uid, "acteur": acteur, "organe": organe, "type_organe": type_organe,
            "legislature": leg, "date_debut": debut, "date_fin": fin, **k}


def test_periode_banc_declare_et_gouvernement(tmp_path):
    """XVe : les groupes déclaraient leur position. Un passage d'un groupe d'opposition à un autre
    groupe d'opposition ne coupe pas la période ; le passage à un groupe majoritaire, le
    changement de gouvernement et un trou de mandat la coupent."""
    org = [{"uid": "PO1", "type_organe": "ASSEMBLEE", "legislature": "15", "date_debut": "2017-06-21",
            "date_fin": "2022-06-21"},
           {"uid": "PG1", "type_organe": "GP", "legislature": "15", "sigle": "A", "libelle": "A",
            "position_politique": "Opposition"},
           {"uid": "PG2", "type_organe": "GP", "legislature": "15", "sigle": "B", "libelle": "B",
            "position_politique": "Opposition"},
           {"uid": "PG3", "type_organe": "GP", "legislature": "15", "sigle": "C", "libelle": "C",
            "position_politique": "Majoritaire"},
           {"uid": "PGOUV1", "type_organe": "GOUVERNEMENT", "libelle_abrege": "UN",
            "date_debut": "2017-05-18", "date_fin": "2020-07-06"},
           {"uid": "PGOUV2", "type_organe": "GOUVERNEMENT", "libelle_abrege": "DEUX",
            "date_debut": "2020-07-07", "date_fin": "2022-05-16"}]
    m = [_mandat("M1", "PA1", "PO1", "ASSEMBLEE", "2017-06-21", "2019-12-31"),
         _mandat("M2", "PA1", "PO1", "ASSEMBLEE", "2020-03-01", "2022-06-21"),
         _mandat("G1", "PA1", "PG1", "GP", "2017-06-27", "2018-12-31"),
         _mandat("G2", "PA1", "PG2", "GP", "2019-01-01", "2020-12-31"),
         _mandat("G3", "PA1", "PG3", "GP", "2021-01-01")]
    ctx, b = _petit(tmp_path, {(an_acteurs, "organe"): org, (an_acteurs, "mandat"): m})
    p = [(x["debut"], x["fin"], x["banc"], x["gouvernement"])
         for x in lignes(ctx, "SELECT * FROM periode_position WHERE acteur = 'PA1' ORDER BY debut")]
    assert p == [
        ("2017-06-21", "2017-06-26", "non_declaree", "PGOUV1"),   # avant l'entrée dans un groupe
        ("2017-06-27", "2019-12-31", "opposition", "PGOUV1"),     # PG1 puis PG2 : même banc
        ("2020-03-01", "2020-07-06", "opposition", "PGOUV1"),     # trou de mandat : nouvelle période
        ("2020-07-07", "2020-12-31", "opposition", "PGOUV2"),     # changement de gouvernement
        ("2021-01-01", "2022-05-16", "majoritaire", "PGOUV2"),    # changement de banc
        ("2022-05-17", "2022-06-21", "majoritaire", None)]        # aucun gouvernement publié
    assert b["R-PERIODE"]["couverture"]["periode_banc_declare"] == [5, 6]


def test_vote_jamais_deduit_d_une_absence(tmp_path):
    """Une personne que la liste du scrutin ne nomme pas n'a pas de position, même quand son
    groupe en publie une."""
    scr = [{"uid": "VTANR5L17V1", "legislature": 17, "numero": 1, "date": "2025-03-01", "code_type": "SPO",
            "titre": "l'ensemble de la proposition de loi visant à protéger les abeilles (première lecture).",
            "dossier_ref": "DA", "sort_code": "adopté"}]
    pos = [{"scrutin": "VTANR5L17V1", "acteur": "PA1", "groupe": "PG", "position": "pour"}]
    dg = [{"scrutin": "VTANR5L17V1", "organe": "PG", "occurrence": 0, "rang": 0, "nombre_membres": 2,
           "position_majoritaire": "pour", "pour": 1, "contre": 0, "abstentions": 0}]
    org = [{"uid": "PG", "type_organe": "GP", "legislature": "17", "sigle": "G", "libelle": "G"},
           {"uid": "PO838901", "type_organe": "ASSEMBLEE", "legislature": "17", "date_debut": "2024-07-01"}]
    m = [_mandat("M1", "PA1", "PO838901", "ASSEMBLEE", "2024-07-08", leg="17"),
         _mandat("M2", "PA2", "PO838901", "ASSEMBLEE", "2024-07-08", leg="17"),
         _mandat("G1", "PA1", "PG", "GP", "2024-07-19", leg="17"),
         _mandat("G2", "PA2", "PG", "GP", "2024-07-19", leg="17")]
    ctx, _ = _petit(tmp_path, {(an_scrutins, "scrutin"): scr, (an_scrutins, "position_vote"): pos,
                                 (an_scrutins, "decompte_groupe"): dg, (an_acteurs, "organe"): org,
                                 (an_acteurs, "mandat"): m,
                                 (an_dossiers, "dossier"): [{"uid": "DA", "legislature": "17"}]})
    assert [x["acteur"] for x in lignes(ctx, "SELECT acteur FROM vote_personne")] == ["PA1"]
    assert [x["acteur"] for x in lignes(ctx, "SELECT acteur FROM divergence")] == ["PA1"]


VOTE = {"scrutin": "VTANR5L17V1", "dossier": "DA", "date": "2025-03-01", "position": "contre",
        "nature": "ensemble", "derniere_lecture": True, "groupe": "PG17", "groupe_scrutin": "PG17",
        "matiere": None, "matiere_libelle": None, "sort_final": "non_connu", "origine": "proposition",
        "titre_dossier": None, "periode": None, "source_url": None}


def _divergence(tmp_path, votes, decomptes):
    """R-DIVERGENCE seule, sur des tables `vote_personne`, `groupe` et des décomptes écrits ici."""
    def _vp(ctx):
        cols = list(VOTE) + ["acteur"]
        vals = ", ".join("(" + ", ".join("NULL" if v.get(c) is None else
                                         (str(v[c]).lower() if isinstance(v[c], bool) else f"'{v[c]}'")
                                         for c in cols) + ")" for v in votes)
        ctx.ecrire("vote_personne", f"SELECT * FROM (VALUES {vals}) AS t({', '.join(cols)})")
        return {}

    def _gr(ctx):
        ctx.ecrire("groupe", """SELECT * FROM (VALUES ('PG17', 17, 'G'), ('PG13', 13, 'H'))
                                AS t(organe, legislature, sigle)""")
        ctx.ecrire("appartenance", "SELECT NULL AS acteur WHERE false")
        return {}

    vp = types.SimpleNamespace(NOM="R-VOTE-PERSONNE", VERSION=0, DEPEND=(), SORTIES=("vote_personne",), appliquer=_vp)
    gr = types.SimpleNamespace(NOM="R-APPARTENANCE", VERSION=0, DEPEND=(), SORTIES=("groupe", "appartenance"),
                               appliquer=_gr)
    z2 = tmp_path / "z2"
    os.makedirs(z2)
    ajouter(z2, an_scrutins, "decompte_groupe", decomptes)
    ctx = Contexte(str(z2), str(tmp_path / "z3"))
    bilan = {x["regle"].split("@")[0]: x for x in relier(ctx, ordonner([vp, gr, r_divergence]))}
    return ctx, bilan["R-DIVERGENCE"]["couverture"]


def _dg(scrutin, organe, pos, pour, contre, abst, occ=0):
    return {"scrutin": scrutin, "organe": organe, "occurrence": occ, "rang": 0, "nombre_membres": 10,
            "position_majoritaire": pos, "pour": pour, "contre": contre, "abstentions": abst}


def test_divergence_conditions_une_par_une(tmp_path):
    votes = [
        {**VOTE, "acteur": "PA1"},                                                  # retenue, diverge
        {**VOTE, "acteur": "PA2", "position": "pour"},                              # retenue, ne diverge pas
        {**VOTE, "acteur": "PA3", "position": "non_votant"},                        # 1 : position non publiée
        {**VOTE, "acteur": "PA4", "scrutin": "VTANR5L17V2"},                        # 2 : groupe absent (PO0)
        {**VOTE, "acteur": "PA5", "scrutin": "VTANR5L17V3"},                        # 2 : deux décomptes discordants
        {**VOTE, "acteur": "PA6", "scrutin": "VTANR5L17V4"},                        # 2 : aucun membre exprimé
        {**VOTE, "acteur": "PA7", "scrutin": "VTANR5L17V5"},                        # 2 : publiée mais contredite
        {**VOTE, "acteur": "PA8", "derniere_lecture": False},                       # 3 : pas la dernière lecture
        {**VOTE, "acteur": "PA9", "nature": "motion_censure", "derniere_lecture": False},  # 4
        {**VOTE, "acteur": "PA10", "groupe": "PG13", "groupe_scrutin": "PG13"},     # 5 : groupe sans fiche (XIIIe)
        {**VOTE, "acteur": "PA11", "groupe": None},                                 # sans groupe à la date
    ]
    dg = [_dg("VTANR5L17V1", "PG17", "pour", 6, 2, 0), _dg("VTANR5L17V1", "PG13", "pour", 6, 2, 0),
          _dg("VTANR5L17V2", "PO0", "pour", 6, 2, 0),
          _dg("VTANR5L17V3", "PG17", "pour", 6, 2, 0), _dg("VTANR5L17V3", "PG17", "contre", 2, 6, 0, occ=1),
          _dg("VTANR5L17V4", "PG17", "pour", 0, 0, 0),
          _dg("VTANR5L17V5", "PG17", "contre", 19, 7, 7)]
    ctx, c = _divergence(tmp_path, votes, dg)
    d = {x["acteur"]: x for x in lignes(ctx, "SELECT * FROM divergence")}
    assert set(d) == {"PA1", "PA2"}
    assert (d["PA1"]["position"], d["PA1"]["position_groupe"], d["PA1"]["diverge"], d["PA1"]["groupe_divise"]) == (
        "contre", "pour", True, True)
    assert d["PA2"]["diverge"] is False
    assert c["positions_comparables_sur_positions_en_derniere_lecture"] == [2, 10]   # 10 votes « ensemble »
    assert c["exclues_position_du_groupe_non_etablie"] == [4, 10]
    assert c["dont_position_publiee_contredite_par_le_decompte"] == [1, 10]
    assert c["exclues_groupe_sans_fiche"] == [1, 10]
    assert c["exclues_sans_groupe_a_la_date"] == [1, 10]
