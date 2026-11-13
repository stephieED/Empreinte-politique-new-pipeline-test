"""Règles du groupe A (gouvernements et Assemblée) : R-COMPOSITION, R-VAGUE, R-APPARTENANCE,
R-DEPUTES, R-HEMICYCLE.

Sur l'extrait réel `tests/extraits/amo30_l17_regles_a.zip` (fiche `amo30_l17_regles_a.md`), lu
par le vrai lecteur, et sur de petites tables écrites ici quand l'extrait ne couvre pas le cas."""
import os

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
import yaml

from empreinte_src.depaquetage import depaqueter
from empreinte_src.entrepot import Entrepot
from empreinte_src.lecteurs import an_acteurs
from empreinte_src.lecture import Lecture
from empreinte_src.liaison import Contexte, ordonner, relier
from empreinte_src.regles import (r_appartenance, r_composition, r_deputes, r_gouvernements,
                              r_hemicycle, r_legislatures, r_vague)

EXTRAIT = os.path.join(os.path.dirname(__file__), "extraits", "amo30_l17_regles_a.zip")
PA17 = {"id": "an-amo30-l17", "source": "an", "type": "acteurs_organes", "format": "zip",
        "url": "http://exemple.invalid/AMO30.json.zip"}
CFG = {"points_acces": [{"id": "an-amo30-l17", "licence": "etalab-2.0"}]}
REGLES = [r_legislatures, r_gouvernements, r_composition, r_vague, r_appartenance, r_deputes,
          r_hemicycle]


def _relier(z2, z3, date_reference="2026-11-06", decisions=None):
    ctx = Contexte(str(z2), str(z3), dossier_decisions=decisions and str(decisions),
                   date_reference=date_reference)
    bilan = relier(ctx, ordonner(REGLES))
    return ctx, {b["regle"].split("@")[0]: b for b in bilan}


def _lignes(ctx, sql):
    r = ctx.con.execute(sql)
    cols = [d[0] for d in r.description]
    return [dict(zip(cols, x)) for x in r.fetchall()]


@pytest.fixture(scope="module")
def z2_reel(tmp_path_factory):
    d = tmp_path_factory.mktemp("a")
    e = Entrepot(str(d / "e"))
    e.versionner(PA17, f"R{e.generation}", depaqueter(EXTRAIT, "zip"), complet=True)
    e.clore("test")
    Lecture(Entrepot(str(d / "e")), str(d / "z2"), CFG).executer(an_acteurs)
    return d / "z2"


@pytest.fixture(scope="module")
def reel(z2_reel, tmp_path_factory):
    return _relier(z2_reel, tmp_path_factory.mktemp("z3"))


# --- Petites tables écrites à la main (forme exacte des faits lus) -----------------------------

_PROV = [("prov_point", pa.string()), ("prov_uid", pa.string()), ("prov_version", pa.int32()),
         ("prov_etat", pa.string()), ("prov_url", pa.string())]


def _ecrire_z2(dossier, organes, mandats):
    os.makedirs(dossier, exist_ok=True)
    for nom, lignes in (("organe", organes), ("mandat", mandats)):
        schema = pa.schema(list(an_acteurs.TABLES[nom]) + [pa.field(n, t) for n, t in _PROV])
        rows = [{**{f.name: None for f in schema}, "organes": [], "pays": [], "suppleants": [],
                 "prov_point": "an-amo30-l17", "prov_uid": r.get("acteur", r["uid"]),
                 "prov_version": 1, "prov_etat": "present", **r} for r in lignes]
        rows = [{k: v for k, v in r.items() if k in schema.names} for r in rows]
        pq.write_table(pa.Table.from_pylist(rows, schema=schema),
                       os.path.join(dossier, f"an_acteurs__{nom}.parquet"))
    return dossier


def _gouv(uid, debut, fin=None, abrege="ESSAI"):
    return {"uid": uid, "type_organe": "GOUVERNEMENT", "libelle_abrege": abrege,
            "date_debut": debut, "date_fin": fin}


def _min(uid, gouv, libelle):
    return {"uid": uid, "type_organe": "MINISTERE", "organe_parent": gouv, "libelle": libelle}


def _mm(uid, acteur, organe, qualite, debut, fin=None):
    return {"uid": uid, "acteur": acteur, "type_organe": "MINISTERE", "organe": organe,
            "qualite_code": qualite, "qualite": qualite, "date_debut": debut, "date_fin": fin}


def _mg(uid, acteur, gouv, debut, fin=None):
    return {"uid": uid, "acteur": acteur, "type_organe": "GOUVERNEMENT", "organe": gouv,
            "qualite_code": "membre", "qualite": "membre", "date_debut": debut, "date_fin": fin}


# --- R-COMPOSITION ----------------------------------------------------------------------------

def test_composition_premier_ministre_delegue_et_mission(reel):
    ctx, bilan = reel
    m = {r["mandat"]: r for r in _lignes(ctx, "SELECT * FROM membre_gouvernement")}
    borne = m["PM791583"]
    assert borne["premier_ministre"] and borne["gouvernement"] == "PO791579"
    assert borne["portefeuille"] == "Première ministre" and borne["tutelle_statut"] == "sans_objet"
    assert borne["mandat_gouvernement"] == "PM15791583" and borne["appariement"] == "uid"
    # Ministre déléguée « auprès de la Première ministre » : rattachée par le libellé.
    rome = next(r for r in m.values() if r["acteur"] == "PA791654")
    assert rome["ministere"] == "PO791627" and rome["qualite"] == "Ministre délégué"
    assert (rome["ministere_tutelle"], rome["tutelle_statut"]) == ("PO791580", "etabli")
    culture = next(r for r in m.values() if r["acteur"] == "PA791650")
    assert culture["tutelle_statut"] == "sans_objet" and culture["ministere_tutelle"] is None
    # Une mission auprès de la Première ministre n'est pas une fonction ministérielle.
    assert "PM822029" not in m and not any(r["acteur"] == "PA795908" for r in m.values())
    assert all(r["regle"] == "R-COMPOSITION@1" for r in m.values())


def test_mandat_gouvernement_ouvert_dans_un_gouvernement_clos(reel):
    ctx, bilan = reel
    a8 = _lignes(ctx, "SELECT * FROM mandat_ouvert_organe_clos")
    assert [(r["mandat"], r["organe"], r["hors_composition"], r["ministere_apparie"]) for r in a8] == \
        [("PM15855113", "PO855052", True, False)]
    bayrou = _lignes(ctx, "SELECT * FROM membre_gouvernement WHERE acteur = 'PA410'")
    assert [(r["mandat"], r["mandat_gouvernement"], r["fin"]) for r in bayrou
            if r["gouvernement"] == "PO855052"] == [("PM855580", "PM15855580", "2025-09-09")]
    # Le mandat ouvert n'entre pas dans la composition.
    assert bilan["R-COMPOSITION"]["couverture"]["mandats_gouvernement_dans_la_composition"][0] < \
        bilan["R-COMPOSITION"]["couverture"]["mandats_gouvernement_dans_la_composition"][1]


def test_tutelle_par_le_libelle(tmp_path):
    g = "PO1"
    organes = [_gouv(g, "2022-05-17", "2024-01-09"),
               _min("PO10", g, "Première ministre"),
               _min("PO11", g, "Ministère de l’intérieur"),
               _min("PO12", g, "Ministère de l’intérieur et des outre-mer"),
               _min("PO13", g, "Ministère de la transition écologique et de la cohésion des territoires"),
               _min("PO14", g, "Ministère de l' économie et des finances"),   # espace après l'apostrophe
               # deux ministres désignés : non établi
               _min("PO20", g, "Ministère auprès du ministre de l’intérieur et des outre-mer et du ministre "
                               "de la transition écologique et de la cohésion des territoires, chargé des collectivités"),
               # « de l'intérieur » est contenu dans « de l'intérieur et des outre-mer » : à la date,
               # seul le second est tenu
               _min("PO21", g, "Ministère auprès du ministre de l’intérieur et des outre-mer, chargé des outre-mer"),
               # « auprès du ministère de… » (formulation Valls 2)
               _min("PO22", g, "Secrétariat d'État, auprès du ministère de l'économie et des finances, chargé du budget"),
               # pas de « auprès » : la tutelle n'est pas dans le libellé
               _min("PO23", g, "Ministère chargé du budget"),
               # libellé qui ne correspond à aucun ministère du gouvernement
               _min("PO24", g, "Ministère auprès du ministre du travail, chargé de l'emploi"),
               # résolu par une décision
               _min("PO25", g, "Ministère chargé des sports"),
               # deux ministres désignés, un seul reconnu (coquille réelle « affaires étrangère », Castex) :
               # on ne garde pas la moitié d'une co-tutelle
               _min("PO26", g, "Ministère auprès du ministre de l’intérieur et des outre-mer et du ministre "
                               "de la mer, chargé des ports")]
    mandats = [_mm("PM100", "PA1", "PO10", "Premier ministre", "2022-05-17", "2024-01-09"),
               _mm("PM101", "PA2", "PO11", "Ministre", "2022-05-21", "2022-07-04"),
               _mm("PM102", "PA2", "PO12", "Ministre", "2022-07-05", "2024-01-09"),
               _mm("PM103", "PA3", "PO13", "Ministre", "2022-05-21", "2024-01-09"),
               _mm("PM104", "PA4", "PO14", "Ministre", "2022-05-21", "2024-01-09"),
               _mm("PM120", "PA5", "PO20", "Ministre délégué", "2022-07-05", "2024-01-09"),
               _mm("PM121", "PA6", "PO21", "Ministre délégué", "2022-07-05", "2024-01-09"),
               _mm("PM122", "PA7", "PO22", "Secrétaire d'État", "2022-07-05", "2024-01-09"),
               _mm("PM123", "PA8", "PO23", "Ministre délégué", "2022-07-05", "2024-01-09"),
               _mm("PM124", "PA9", "PO24", "Ministre délégué", "2022-07-05", "2024-01-09"),
               _mm("PM125", "PA10", "PO25", "Ministre délégué", "2022-07-05", "2024-01-09"),
               _mm("PM126", "PA11", "PO10", "en mission", "2022-07-05", "2023-01-05"),
               _mm("PM127", "PA12", "PO26", "Ministre délégué", "2022-07-05", "2024-01-09")]
    mandats += [_mg("PM15" + m["uid"][2:], m["acteur"], g, m["date_debut"], m["date_fin"])
                for m in mandats if m["qualite_code"] != "en mission"]
    dec = tmp_path / "decisions" / "rattachement_portefeuille"
    dec.mkdir(parents=True)
    (dec / "PO25.yaml").write_text(yaml.safe_dump(
        {"type": "rattachement_portefeuille", "date": "2026-11-05", "objet": "PO25",
         "decision": "rattache_a PO10", "motif": "décret d'attributions"}))
    ctx, bilan = _relier(_ecrire_z2(tmp_path / "z2", organes, mandats), tmp_path / "z3",
                         decisions=tmp_path / "decisions")
    t = {r["ministere"]: r for r in _lignes(ctx, "SELECT * FROM membre_gouvernement")}
    assert "PO10" in t and len(t) == 12                        # la mission est écartée
    assert t["PO20"]["tutelle_statut"] == "non_etabli"
    assert t["PO20"]["raison_tutelle"] == "le libellé désigne plusieurs ministres"
    assert t["PO20"]["tutelles_candidates"] == ["PO12", "PO13"]
    assert (t["PO21"]["ministere_tutelle"], t["PO21"]["tutelle_statut"]) == ("PO12", "etabli")
    assert (t["PO22"]["ministere_tutelle"], t["PO22"]["tutelle_statut"]) == ("PO14", "etabli")
    assert t["PO23"]["tutelle_statut"] == "non_etabli" and "auprès" in t["PO23"]["raison_tutelle"]
    assert t["PO24"]["tutelle_statut"] == "non_etabli" and t["PO24"]["ministere_tutelle"] is None
    assert t["PO24"]["raison_tutelle"].startswith("aucun ministre")
    assert (t["PO25"]["ministere_tutelle"], t["PO25"]["tutelle_statut"]) == ("PO10", "decision")
    assert t["PO25"]["decision"] == "rattachement_portefeuille/PO25.yaml"
    assert t["PO11"]["tutelle_statut"] == "sans_objet"
    assert (t["PO26"]["tutelle_statut"], t["PO26"]["tutelles_candidates"]) == ("non_etabli", ["PO12"])
    assert t["PO26"]["raison_tutelle"] == "le libellé désigne plusieurs ministres"
    # établis : PO21, PO22 (règle) + PO25 (décision) ; à rattacher : PO20 à PO26
    assert bilan["R-COMPOSITION"]["couverture"]["tutelle_etablie"] == [3, 7]


def test_tutelle_a_la_date_du_portefeuille(tmp_path):
    """Le libellé « auprès du ministre de l'intérieur » désigne le ministère tenu à cette date."""
    g = "PO1"
    organes = [_gouv(g, "2022-05-17"),
               _min("PO11", g, "Ministère de l’intérieur"),
               _min("PO12", g, "Ministère de l’intérieur"),           # même libellé, autre organe
               _min("PO20", g, "Secrétariat d'État auprès du ministre de l’intérieur, chargé de la citoyenneté")]
    mandats = [_mm("PM101", "PA2", "PO11", "Ministre", "2022-05-21", "2022-07-04"),
               _mm("PM102", "PA3", "PO12", "Ministre", "2022-07-05"),
               _mm("PM120", "PA5", "PO20", "Secrétaire d'État", "2022-07-12")]
    mandats += [_mg("PM15" + m["uid"][2:], m["acteur"], g, m["date_debut"], m["date_fin"]) for m in mandats]
    ctx, _ = _relier(_ecrire_z2(tmp_path / "z2", organes, mandats), tmp_path / "z3")
    (r,) = _lignes(ctx, "SELECT * FROM membre_gouvernement WHERE ministere = 'PO20'")
    assert (r["ministere_tutelle"], r["tutelle_statut"]) == ("PO12", "etabli")


def test_changement_de_portefeuille_sous_un_meme_mandat_gouvernement(tmp_path):
    g = "PO1"
    organes = [_gouv(g, "2010-11-14", "2012-05-10"),
               _min("PO11", g, "Secrétariat d'État chargé du logement"),
               _min("PO12", g, "Ministère chargé du logement")]
    mandats = [_mm("PM425797", "PA9", "PO11", "Secrétaire d'État", "2010-11-14", "2011-11-30"),
               _mm("PM514480", "PA9", "PO12", "Ministre", "2011-12-01", "2012-05-10"),
               _mg("PM15425797", "PA9", g, "2010-11-14", "2012-05-10")]
    ctx, _ = _relier(_ecrire_z2(tmp_path / "z2", organes, mandats), tmp_path / "z3")
    r = {x["mandat"]: x for x in _lignes(ctx, "SELECT * FROM membre_gouvernement")}
    assert (r["PM425797"]["mandat_gouvernement"], r["PM425797"]["appariement"]) == ("PM15425797", "uid")
    assert (r["PM514480"]["mandat_gouvernement"], r["PM514480"]["appariement"]) == ("PM15425797", "periode")


# --- R-VAGUE ----------------------------------------------------------------------------------

def test_vagues_moins_de_8_jours(tmp_path):
    g = "PO1"
    organes = [_gouv(g, "2022-05-17")] + [_min(f"PO1{i}", g, f"Ministère {i}") for i in range(6)]
    dates = ["2022-05-17", "2022-05-21", "2022-05-24",       # 4 puis 3 jours : une vague
             "2022-07-05", "2022-07-12",                     # 7 jours : une vague
             "2022-07-20"]                                   # 8 jours : nouvelle vague
    mandats = [_mm(f"PM{i}", f"PA{i}", f"PO1{i}", "Ministre", d) for i, d in enumerate(dates)]
    mandats += [_mg("PM15" + m["uid"][2:], m["acteur"], g, m["date_debut"]) for m in mandats]
    ctx, _ = _relier(_ecrire_z2(tmp_path / "z2", organes, mandats), tmp_path / "z3")
    v = _lignes(ctx, "SELECT vague, debut, fin, nb_nominations FROM vague ORDER BY vague")
    assert [(x["vague"], x["debut"], x["fin"], x["nb_nominations"]) for x in v] == [
        (1, "2022-05-17", "2022-05-24", 3), (2, "2022-07-05", "2022-07-12", 2),
        (3, "2022-07-20", "2022-07-20", 1)]


def test_vagues_extrait_reel(reel):
    ctx, _ = reel
    v = _lignes(ctx, "SELECT * FROM vague WHERE gouvernement = 'PO791579' ORDER BY vague")
    # Dans l'extrait : Borne (17/05/2022), Rome et Abdul-Malak (21/05), Béchu (21/05 puis 05/07).
    assert [(x["vague"], x["debut"], x["fin"]) for x in v] == [
        (1, "2022-05-17", "2022-05-21"), (2, "2022-07-05", "2022-07-05")]


# --- R-APPARTENANCE ---------------------------------------------------------------------------

def test_groupes_position_declaree_et_non_inscrits(reel):
    ctx, bilan = reel
    g = {r["organe"]: r for r in _lignes(ctx, "SELECT * FROM groupe")}
    assert set(g) == {"PO800538", "PO845407"}                  # NI : pas un groupe
    assert g["PO800538"]["position_declaree"] == "majoritaire"
    assert g["PO845407"]["position_declaree"] == "non_declaree"  # XVIIe : rien n'est déduit
    assert g["PO845407"]["legislature"] == 17 and g["PO845407"]["sigle"] == "EPR"
    assert bilan["R-APPARTENANCE"]["couverture"]["position_declaree"] == [1, 2]


def test_appartenance_suite_de_periodes_et_suspension(reel):
    ctx, _ = reel
    a = _lignes(ctx, "SELECT * FROM appartenance WHERE acteur = 'PA717161' ORDER BY debut")
    assert [(x["groupe"], x["debut"], x["fin"]) for x in a] == [
        ("PO800538", "2022-06-29", "2022-07-22"),   # XVIe, avant la nomination
        ("PO800538", "2024-02-10", "2024-06-09"),   # après la reprise
        ("PO845407", "2024-07-19", "2025-01-23"),   # XVIIe : le passage chez les NI n'est pas une période
        ("PO845407", "2025-11-14", None)]           # membre puis apparentée : une seule période
    assert a[-1]["qualites"] == ["Apparenté au", "Membre du"]
    assert len(a[-1]["mandats"]) == 2


def test_chevauchement_d_un_jour_avant_la_xve(tmp_path):
    """Avant la XVe, l'ancien mandat GP finit le jour où le suivant commence (UMP → R-UMP, 2012)."""
    organes = [{"uid": "PO1", "type_organe": "GP", "sigle": "UMP", "libelle": "UMP", "legislature": "14",
                "date_debut": "2012-06-26", "date_fin": "2013-01-15"},
               {"uid": "PO2", "type_organe": "GP", "sigle": "R-UMP", "libelle": "R-UMP", "legislature": "14",
                "date_debut": "2012-11-27", "date_fin": "2013-01-15"},
               {"uid": "PO3", "type_organe": "GP", "sigle": "NI", "libelle": "Non inscrit", "legislature": "14",
                "date_debut": "2012-06-20", "date_fin": "2017-06-20"}]
    gp = lambda u, a, o, d, f, q="Membre du": {"uid": u, "acteur": a, "type_organe": "GP", "organe": o,
                                              "qualite": q, "legislature": "14", "date_debut": d, "date_fin": f}
    mandats = [gp("PM1", "PA1", "PO1", "2012-06-26", "2012-11-27"),
               gp("PM2", "PA1", "PO2", "2012-11-27", "2013-01-15"),
               gp("PM3", "PA2", "PO3", "2014-06-02", "2014-06-02", "Député non-inscrit"),
               gp("PM4", "PA2", "PO1", "2014-06-02", "2015-06-01"),
               gp("PM5", "PA3", "PO1", "2012-06-26", "2012-09-30"),
               gp("PM6", "PA3", "PO1", "2012-10-01", "2013-01-15", "Président du"),
               gp("PM7", "PA3", "PO1", "2012-10-05", "2012-12-01")]       # chevauchement interne
    ctx, _ = _relier(_ecrire_z2(tmp_path / "z2", organes, mandats), tmp_path / "z3",
                     date_reference="2013-01-15")
    a = {(x["acteur"], x["groupe"]): x for x in _lignes(ctx, "SELECT * FROM appartenance")}
    assert (a[("PA1", "PO1")]["fin"], a[("PA1", "PO1")]["fin_source"]) == ("2012-11-26", "2012-11-27")
    assert a[("PA1", "PO2")]["debut"] == "2012-11-27"
    assert a[("PA2", "PO1")]["debut"] == "2014-06-02"
    assert (a[("PA3", "PO1")]["debut"], a[("PA3", "PO1")]["fin"]) == ("2012-06-26", "2013-01-15")
    e = {(x["groupe"], x["date"]): x["effectif"] for x in _lignes(ctx, "SELECT * FROM effectif_groupe")}
    assert e[("PO1", "2012-11-26")] == 2 and e[("PO1", "2012-11-27")] == 1
    assert e[("PO2", "2012-11-27")] == 1 and e[("PO2", "2013-01-15")] == 1
    assert not any(g == "PO3" for g, _ in e)                    # les non-inscrits n'ont pas d'effectif de groupe


# --- R-DEPUTES --------------------------------------------------------------------------------

def test_suspension_et_reprise_datee_par_la_prise_de_fonction(reel):
    ctx, bilan = reel
    d = {r["mandat"]: r for r in _lignes(ctx, "SELECT * FROM depute WHERE acteur = 'PA717161'")}
    o = d["PM842396"]
    assert (o["legislature"], o["debut"], o["fin"]) == (17, "2024-07-08", "2025-01-23")
    assert o["cause_fin"] == "Nomination comme membre du Gouvernement"
    assert (o["suspendu_du"], o["suspendu_au"]) == ("2025-01-24", "2025-11-12")
    assert (o["suspension_statut"], o["mandat_reprise"]) == ("reprise", "PM874997")
    r = d["PM874997"]
    assert r["debut"] == "2025-11-13" and r["date_debut_source"] == "2024-07-07"   # piège : date recopiée
    assert r["fin"] is None and r["mandat_suspendu"] == "PM842396" and r["suspendu_du"] is None
    xvi = d["PM796311"]
    assert (xvi["suspendu_du"], xvi["suspendu_au"]) == ("2022-07-23", "2024-02-09")
    assert d["PM834836"]["debut"] == "2024-02-10"
    assert r["circonscription"] == o["circonscription"] is not None


def test_suppleant_et_suspension_sans_reprise(tmp_path):
    a = lambda u, ac, d, pf, f, cm, cf=None, mr=None: {
        "uid": u, "acteur": ac, "type_organe": "ASSEMBLEE", "organe": "PO838901", "legislature": "17",
        "date_debut": d, "date_prise_fonction": pf, "date_fin": f, "cause_mandat": cm, "cause_fin": cf,
        "circonscription": "PO9", "mandat_remplace": mr}
    nomme = "Nomination comme membre du Gouvernement"
    mandats = [a("PM1", "PA1", "2024-07-07", "2024-07-08", "2024-10-21", "élections générales", nomme),
               a("PM2", "PA2", "2024-07-07", "2024-10-22", None,
                 "remplacement d'un député nommé au Gouvernement")]
    organes = [{"uid": "PO838901", "type_organe": "ASSEMBLEE", "legislature": "17", "date_debut": "2024-07-01"}]
    ctx, bilan = _relier(_ecrire_z2(tmp_path / "z2", organes, mandats), tmp_path / "z3")
    d = {r["mandat"]: r for r in _lignes(ctx, "SELECT * FROM depute")}
    assert (d["PM1"]["suspendu_du"], d["PM1"]["suspendu_au"]) == ("2024-10-22", None)
    assert d["PM1"]["suspension_statut"] == "sans_reprise" and d["PM1"]["mandat_suppleant"] == "PM2"
    assert d["PM2"]["debut"] == "2024-10-22"                    # pas la date d'élection recopiée
    assert bilan["R-DEPUTES"]["couverture"]["suspension_close_par_une_reprise"] == [0, 1]
    # Hémicycle du jour : le suppléant siège, le ministre suspendu non.
    h = _lignes(ctx, "SELECT acteur, siege, rattachement FROM hemicycle")
    assert h == [{"acteur": "PA2", "siege": None, "rattachement": "non_etabli"}]
    assert bilan["R-HEMICYCLE"]["couverture"]["siege_connu"] == [0, 1]


# --- R-HEMICYCLE ------------------------------------------------------------------------------

def test_hemicycle_legislature_en_cours_datee(reel):
    ctx, bilan = reel
    h = _lignes(ctx, "SELECT * FROM hemicycle")
    assert [(x["legislature"], x["date"], x["acteur"], x["siege"], x["groupe"], x["rattachement"])
            for x in h] == [(17, "2026-11-06", "PA717161", 253, "PO845407", "groupe"),
                            (17, "2026-11-06", "PA795908", 311, "PO845407", "groupe")]
    assert {x["date_origine"] for x in h} == {"date_reference"}
    # XVIe close : le siège de l'archive courante n'est pas celui de la XVIe, rien n'est servi.
    assert bilan["R-HEMICYCLE"]["couverture"]["siege_legislatures_closes"] == [0, 1]


def test_effectif_jour_par_jour(reel):
    ctx, _ = reel
    e = {r["date"]: r["effectif"] for r in _lignes(
        ctx, "SELECT date, effectif FROM effectif_groupe WHERE groupe = 'PO845407'")}
    assert min(e) == "2024-07-18" and max(e) == "2026-11-06"   # création du groupe → jour de constat
    assert len(e) == 842                                        # chaque jour
    # Deux députés EPR dans l'extrait : PA795908 depuis le 19/07/2024, Élisabeth Borne suspendue
    # du 24/01/2025 au 12/11/2025 (et non-inscrite le 13/11/2025, jour de sa reprise).
    assert (e["2024-07-18"], e["2024-07-19"], e["2025-01-23"], e["2025-01-24"]) == (0, 2, 2, 1)
    assert (e["2025-11-13"], e["2025-11-14"], e["2026-11-06"]) == (1, 2, 2)


def test_hemicycle_sans_date_de_reference(z2_reel, tmp_path):
    ctx, _ = _relier(z2_reel, tmp_path / "z3", date_reference=None)
    h = _lignes(ctx, "SELECT DISTINCT date, date_origine FROM hemicycle")
    # Dernière date publiée de l'extrait : l'entrée d'Élisabeth Borne comme apparentée EPR.
    assert h == [{"date": "2026-09-26", "date_origine": "derniere_date_de_la_source"}]


def test_hemicycle_legislature_close_depuis_son_archive_figee(tmp_path):
    """Cahier 3.1 : seule l'archive figée d'une législature close donne le siège de cette législature.
    L'archive courante donne au mandat clos le siège actuel de la personne : il n'est pas repris."""
    a = lambda u, ac, leg, organe, d, f, place, point: {
        "uid": u, "acteur": ac, "type_organe": "ASSEMBLEE", "organe": organe, "legislature": leg,
        "date_debut": d, "date_prise_fonction": d, "date_fin": f, "cause_mandat": "élections générales",
        "place_hemicycle": place, "prov_point": point}
    organes = [{"uid": "PO791932", "type_organe": "ASSEMBLEE", "legislature": "16", "date_debut": "2022-06-22",
                "date_fin": "2024-06-09"},
               {"uid": "PO838901", "type_organe": "ASSEMBLEE", "legislature": "17", "date_debut": "2024-07-18"}]
    mandats = [a("PM16", "PA1", "16", "PO791932", "2022-06-22", "2024-06-09", "300", "an-amo30-l17"),
               a("PM16", "PA1", "16", "PO791932", "2022-06-22", "2024-06-09", "42", "an-amo30-l16"),
               a("PM17", "PA2", "17", "PO838901", "2024-07-18", None, "7", "an-amo30-l17")]
    ctx, bilan = _relier(_ecrire_z2(tmp_path / "z2", organes, mandats), tmp_path / "z3")
    h = _lignes(ctx, "SELECT legislature, date, acteur, siege, date_origine FROM hemicycle ORDER BY 1")
    assert h == [{"legislature": 16, "date": "2024-06-09", "acteur": "PA1", "siege": 42, "date_origine": "archive_figee"},
                 {"legislature": 17, "date": "2026-11-06", "acteur": "PA2", "siege": 7, "date_origine": "date_reference"}]
    assert bilan["R-HEMICYCLE"]["couverture"]["siege_legislatures_closes"] == [1, 1]
