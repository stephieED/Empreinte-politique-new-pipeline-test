"""Règles du groupe B (textes et scrutins) : R-NATURE-SCRUTIN, R-LIEN-SCRUTIN-DOSSIER, R-ORIGINE,
R-DERNIERE-LECTURE, R-MATIERE, R-ETAPE, R-SORT-FINAL, R-49-3, R-LOIS, R-LOI-DOSSIER,
R-LOI-ADOPTION, R-DEPOT-GOUVERNEMENT.

Sur les extraits réels `tests/extraits/an_scrutins_l17_extrait.zip` et
`an_dossiers_l17_extrait.zip` (fiches `an_scrutins.md`, `an_dossiers.md`), lus par le vrai cadre
(`Entrepot` + `Lecture`), complétés de quelques scrutins et actes réels recopiés à la main
(valeurs relevées dans les faits lus de la XVIIe, collecte du 06/11/2026), et sur de petites
tables écrites ici pour les cas que les extraits ne couvrent pas."""
import os
import shutil

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from empreinte_src.depaquetage import depaqueter
from empreinte_src.entrepot import Entrepot
from empreinte_src.lecteurs import an_acteurs, an_dossiers, an_scrutins
from empreinte_src.lecture import Lecture
from empreinte_src.liaison import Contexte, ordonner, relier
from empreinte_src.regles import (r_49_3, r_depot_gouvernement, r_derniere_lecture, r_etape,
                              r_gouvernements, r_legislatures, r_lien_scrutin_dossier, r_loi_adoption,
                              r_loi_dossier, r_lois, r_matiere, r_nature_scrutin, r_origine, r_sort_final)

EXTRAITS = os.path.join(os.path.dirname(__file__), "extraits")
REGLES = [r_legislatures, r_gouvernements, r_nature_scrutin, r_lien_scrutin_dossier, r_origine,
          r_derniere_lecture, r_matiere, r_etape, r_49_3, r_lois, r_loi_dossier, r_sort_final,
          r_depot_gouvernement, r_loi_adoption]
_PROV = [("prov_point", pa.string()), ("prov_uid", pa.string()), ("prov_version", pa.int32()),
         ("prov_etat", pa.string()), ("prov_url", pa.string())]

# Organes réels (AMO30 XVIIe, collecte du 06/11/2026) : législatures, gouvernements, commissions.
ORGANES = [
    {"uid": "PO791932", "type_organe": "ASSEMBLEE", "legislature": "16",
     "date_debut": "2022-06-22", "date_fin": "2024-06-09"},
    {"uid": "PO838901", "type_organe": "ASSEMBLEE", "legislature": "17", "date_debut": "2024-07-01"},
    {"uid": "PO833673", "type_organe": "GOUVERNEMENT", "libelle_abrege": "ATTAL",
     "date_debut": "2024-01-10", "date_fin": "2024-09-05"},
    {"uid": "PO847639", "type_organe": "GOUVERNEMENT", "libelle_abrege": "BARNIER",
     "date_debut": "2024-09-06", "date_fin": "2024-12-13"},
    {"uid": "PO855052", "type_organe": "GOUVERNEMENT", "libelle_abrege": "BAYROU",
     "date_debut": "2024-12-14", "date_fin": "2025-09-09"},
    {"uid": "PO873418", "type_organe": "GOUVERNEMENT", "libelle_abrege": "LECORNU",
     "date_debut": "2025-09-10", "date_fin": "2025-10-10"},
    {"uid": "PO873634", "type_organe": "GOUVERNEMENT", "libelle_abrege": "LECORNU II",
     "date_debut": "2025-10-11"},
    {"uid": "PO59047", "type_organe": "COMPER", "libelle": "Commission des affaires étrangères"},
    {"uid": "PO59048", "type_organe": "COMPER",
     "libelle": "Commission des finances, de l'économie générale et du contrôle budgétaire"},
    {"uid": "PO59051", "type_organe": "COMPER", "libelle": "Commission des lois constitutionnelles, "
     "de la législation et de l'administration générale de la République"},
    {"uid": "PO419610", "type_organe": "COMPER", "libelle": "Commission des affaires économiques"},
    {"uid": "PO211491", "type_organe": "COMSENAT",
     "libelle": "Commission des affaires étrangères, de la défense et des forces armées"},
    {"uid": "PO211494", "type_organe": "COMSENAT", "libelle": "Commission des finances"},
    {"uid": "PO211495", "type_organe": "COMSENAT", "libelle": "Commission des lois constitutionnelles, "
     "de législation, du suffrage universel, du Règlement et d'administration générale"},
    {"uid": "PO516753", "type_organe": "COMSENAT", "libelle": "Commission des affaires économiques"},
]

# Scrutins réels absents des extraits, recopiés des faits lus (collecte du 06/11/2026).
SCRUTINS_REELS = [
    {"uid": "VTANR5L17V4241", "numero": 4241, "date": "2025-11-21", "code_type": "SPS",
     "libelle_type": "scrutin public solennel", "seance": "RUANR5L17S2026IDS29940", "sort_code": "rejeté",
     "titre": "la première partie du projet de loi de finances pour 2026 (première lecture)."},
    {"uid": "VTANR5L17V5154", "numero": 5154, "date": "2026-01-23", "code_type": "MOC",
     "libelle_type": "motion de censure", "seance": "RUANR5L17S2026IDS30188", "sort_code": "rejeté",
     "titre": "la motion de censure déposée en application de l'article 49, alinéa 3, de la "
              "Constitution par Mme Mathilde Panot, Mme Cyrielle Chatelain, M. Stéphane Peu et 108 députés."},
    {"uid": "VTANR5L17V2215", "numero": 2215, "date": "2025-06-03", "code_type": "SPO",
     "libelle_type": "scrutin public ordinaire", "seance": "RUANR5L17S2025IDS29499", "sort_code": "adopté",
     "titre": "l'ensemble de la proposition de loi visant à faciliter la transformation des bureaux et "
              "autres bâtiments en logements (texte de la commission mixte paritaire)."},
    {"uid": "VTANR5L17V960", "numero": 960, "date": "2025-03-12", "code_type": "SPO",
     "libelle_type": "scrutin public ordinaire", "seance": "RUANR5L17S2025IDS29162", "sort_code": "adopté",
     "titre": "l'article unique de la proposition de résolution modifiant le Règlement de l'Assemblée "
              "nationale afin de supprimer le vote par assis et levé."},
]
# La séance du 03/06/2025 (RUANR5L17S2025IDS29499) a aussi porté sur deux dossiers absents de
# l'extrait : leurs actes de séance et leurs titres, recopiés des faits lus.
ACTES_REELS = [
    {"dossier": "DLR5L17N51499", "uid": "L17-VD225684S50220", "type_acte": "DiscussionSeancePublique_Type",
     "code": "AN1-DEBATS-SEANCE", "date": "2025-06-03T00:00:00.000+02:00", "reunion": "RUANR5L17S2025IDS29499"},
    {"dossier": "DLR5L16N48739", "uid": "L17-VD224888S50161", "type_acte": "DiscussionSeancePublique_Type",
     "code": "AN2-DEBATS-SEANCE", "date": "2025-06-03T00:00:00.000+02:00", "reunion": "RUANR5L17S2025IDS29499"},
]
DOSSIERS_REELS = [
    {"uid": "DLR5L17N51499", "legislature": "17", "procedure_code": "2",
     "titre": "Reconnaissance de la Nation envers les rapatriés d’Indochine et réparation des préjudices "
              "subis par ceux-ci et leurs familles du fait de l'indignité de leurs conditions d'accueil et "
              "de vie dans certaines structures sur le territoire français"},
    {"uid": "DLR5L16N48739", "legislature": "16", "procedure_code": "2",
     "titre": "Création d'un homicide routier et visant à lutter contre la violence routière"},
]


# --- Écriture des faits (forme exacte des tables lues) -------------------------------------------

def _schema(lecteur, table):
    return pa.schema(list(lecteur.TABLES[table]) + [pa.field(n, t) for n, t in _PROV])


def _ecrire(dossier, lecteur, table, lignes, base=None):
    """Écrit `<lecteur>__<table>.parquet` : lignes `base` (déjà lues) + lignes écrites ici."""
    schema = (pa.schema([f.with_nullable(True) for f in base.schema]) if base is not None
              else _schema(lecteur, table))
    listes = {f.name for f in schema if pa.types.is_list(f.type)}
    rows = list(base.to_pylist()) if base is not None else []
    for r in lignes:
        x = {f.name: None for f in schema}
        x.update({n: [] for n in listes})
        x.update({"prov_point": "essai", "prov_uid": r.get("uid", "x"), "prov_version": 1,
                  "prov_etat": "present"})
        if "legislature" in schema.names and table == "scrutin":
            x["legislature"] = 17
        x.update(r)
        if table == "scrutin" and x.get("prov_url") is None and x["uid"].startswith("VTAN"):
            x["prov_url"] = f"https://www.assemblee-nationale.fr/dyn/17/scrutins/{x['numero']}"
        rows.append({k: v for k, v in x.items() if k in schema.names})
    os.makedirs(dossier, exist_ok=True)
    pq.write_table(pa.Table.from_pylist(rows, schema=schema),
                   os.path.join(dossier, f"{lecteur.NOM}__{table}.parquet"))


def _z2(dossier, scrutins=(), actes=(), dossiers=(), documents=(), organes=ORGANES):
    _ecrire(dossier, an_scrutins, "scrutin", scrutins)
    _ecrire(dossier, an_dossiers, "acte", actes)
    _ecrire(dossier, an_dossiers, "dossier", dossiers)
    _ecrire(dossier, an_dossiers, "document", documents)
    _ecrire(dossier, an_acteurs, "organe", organes)
    return dossier


def _relier(z2, z3, date_reference="2026-11-06"):
    ctx = Contexte(str(z2), str(z3), date_reference=date_reference)
    bilan = relier(ctx, ordonner(REGLES))
    return ctx, {b["regle"].split("@")[0]: b for b in bilan}


def _lignes(ctx, sql):
    r = ctx.con.execute(sql)
    cols = [d[0] for d in r.description]
    return [dict(zip(cols, x)) for x in r.fetchall()]


def _un(ctx, table, **cle):
    w = " AND ".join(f"{k} = '{v}'" for k, v in cle.items())
    r = _lignes(ctx, f"SELECT * FROM {table} WHERE {w}")
    assert len(r) == 1, (table, cle, r)
    return r[0]


def _lire_par_le_cadre(d, ident, type_, zip_, lecteur):
    pa_cfg = {"id": ident, "source": "an", "type": type_, "format": "zip",
              "url": "http://exemple.invalid/x.json.zip"}
    e = Entrepot(str(d / ident))
    e.versionner(pa_cfg, f"R{e.generation}", depaqueter(os.path.join(EXTRAITS, zip_), "zip"),
                 complet=True)
    e.clore("test")
    Lecture(Entrepot(str(d / ident)), str(d / "lu"),
            {"points_acces": [{"id": ident, "licence": "etalab-2.0"}]}).executer(lecteur)


@pytest.fixture(scope="module")
def reel(tmp_path_factory):
    d = tmp_path_factory.mktemp("b")
    _lire_par_le_cadre(d, "an-scrutins-l17", "scrutins", "an_scrutins_l17_extrait.zip", an_scrutins)
    _lire_par_le_cadre(d, "an-dossiers-l17", "dossiers", "an_dossiers_l17_extrait.zip", an_dossiers)
    z2 = d / "z2"
    os.makedirs(z2)
    for t in ("an_dossiers__document",):
        shutil.copy(d / "lu" / f"{t}.parquet", z2)
    lu = lambda t: pq.read_table(d / "lu" / f"{t}.parquet")
    _ecrire(z2, an_scrutins, "scrutin", SCRUTINS_REELS, base=lu("an_scrutins__scrutin"))
    _ecrire(z2, an_dossiers, "acte", ACTES_REELS, base=lu("an_dossiers__acte"))
    _ecrire(z2, an_dossiers, "dossier", DOSSIERS_REELS, base=lu("an_dossiers__dossier"))
    _ecrire(z2, an_acteurs, "organe", ORGANES)
    return _relier(z2, d / "z3")


# --- Sur les extraits réels -----------------------------------------------------------------------

def test_nature_reelle_lit_le_code_puis_l_intitule(reel):
    ctx, _ = reel
    s = _un(ctx, "scrutin_classe", scrutin="VTANR5L17V8611")      # résolution de l'article 34-1
    assert (s["nature"], s["detail_nature"], s["origine"]) == ("ensemble", "ensemble_sans_le_mot", "proposition")
    s = _un(ctx, "scrutin_classe", scrutin="VTANR5L17V4241")      # première partie du PLF 2026
    assert (s["nature"], s["solennel"], s["type_code"], s["lecture"]) == ("partie_de_texte", True, "SPS", "premiere")
    s = _un(ctx, "scrutin_classe", scrutin="VTANR5L17V5154")      # motion de censure (code MOC)
    assert (s["nature"], s["motion_censure"], s["solennel"]) == ("motion_censure", True, False)
    assert (s["origine"], s["raison_origine"]) == ("non_etablie", "pas_un_texte")
    assert _un(ctx, "scrutin_classe", scrutin="VTANR5L17V124")["nature"] == "amendement"
    s = _un(ctx, "scrutin_classe", scrutin="VTANR5L17V6722")
    assert (s["nature"], s["origine"], s["sort"]) == ("article", "projet", "adopte")
    assert s["source_url"] == "https://www.assemblee-nationale.fr/dyn/17/scrutins/6722"
    s = _un(ctx, "scrutin_classe", scrutin="VTANR5L17V960")
    assert (s["nature"], s["detail_nature"]) == ("article", "article_unique")


def test_lien_reel_par_les_trois_routes(reel):
    ctx, b = reel
    l = _un(ctx, "lien_scrutin_dossier", scrutin="VTANR5L17V6722")
    assert (l["dossier"], l["route"]) == ("DLR5L17N54083", "reference_directe")
    # Acte partagé par le PLF 2026 et le dossier d'engagement de responsabilité : deux liens.
    m = _lignes(ctx, "SELECT * FROM lien_scrutin_dossier WHERE scrutin = 'VTANR5L17V5154' ORDER BY dossier")
    assert [(x["dossier"], x["route"], x["nb_dossiers"]) for x in m] == [
        ("DLR5L17N52428", "acte_cite", 2), ("DLR5L17N53597", "acte_cite", 2)]
    l = _un(ctx, "lien_scrutin_dossier", scrutin="VTANR5L17V960")    # deux routes d'accord
    assert (l["dossier"], l["route"], l["routes"], l["recoupe"]) == (
        "DLR5L17N51481", "acte_cite", ["acte_cite", "seance"], True)
    # Scrutin du Sénat cité par un acte : aucun lien (pas de jeu de données).
    assert ctx.un("SELECT count(*) FROM lien_scrutin_dossier WHERE scrutin LIKE 'VTSN%'") == 0
    assert b["R-LIEN-SCRUTIN-DOSSIER"]["couverture"]["desaccord_entre_routes"] == [0, 9]


def test_seance_ambigue_reelle_reste_non_reliee(reel):
    """03/06/2025 : trois dossiers dans la séance ; le titre du bon dossier (« Faciliter la
    transformation des bureaux en logements ») n'est pas recopié tel quel dans l'intitulé : pas de
    lien, plutôt qu'un lien deviné."""
    ctx, _ = reel
    assert ctx.un("SELECT count(*) FROM lien_scrutin_dossier WHERE scrutin = 'VTANR5L17V2215'") == 0
    assert _un(ctx, "scrutin_non_relie", scrutin="VTANR5L17V2215")["raison"] == "seance_ambigue"


def test_49_3_reel_jamais_un_scrutin(reel):
    ctx, b = reel
    e = _lignes(ctx, "SELECT * FROM engagement_49_3 ORDER BY date, dossier")
    assert [(x["dossier"], x["date"]) for x in e] == [
        ("DLR5L17N52428", "2026-01-20"), ("DLR5L17N53597", "2026-01-20"),
        ("DLR5L17N52428", "2026-01-23"), ("DLR5L17N52428", "2026-01-30")]
    assert {x["gouvernement"] for x in e} == {"PO873634"}           # Lecornu II
    assert ctx.un("SELECT count(DISTINCT acte) FROM engagement_49_3") == 3
    assert ctx.un("""SELECT count(*) FROM engagement_49_3 e JOIN lien_scrutin_dossier l
                     ON l.scrutin = e.acte""") == 0
    plf = _un(ctx, "etat_dossier", dossier="DLR5L17N52428")
    assert (plf["sort"], plf["par_49_3"], plf["adopte_par_49_3"], plf["numero_loi"]) == (
        "promulgue", True, True, "2026-103")
    eng = _un(ctx, "etat_dossier", dossier="DLR5L17N53597")       # dossier « engagement », procédure 13
    assert (eng["sort"], eng["raison_sort"], eng["par_49_3"], eng["adopte_par_49_3"]) == (
        "non_connu", "pas_de_texte_depose", True, False)


def test_projet_de_loi_promulgue_reel(reel):
    """53259 : projet de loi déposé le 02/12/2025, adopté par l'AN, « modifié » au Sénat selon la
    conclusion, puis promulgué le 21/04/2026 : la promulgation fait foi ; la conclusion du Sénat
    ne prouve pas l'adoption définitive (elle n'est pas retrouvée)."""
    ctx, _ = reel
    p = _un(ctx, "projet_gouvernement", dossier="DLR5L17N53259")
    assert (p["document"], p["date_depot"], p["gouvernement"], p["chambre_depot"]) == (
        "PRJLANR5L17B2155", "2025-12-02", "PO873634", "AN")
    assert "acteur" not in p                                         # jamais un acte personnel
    assert {x["dossier"] for x in _lignes(ctx, "SELECT dossier FROM projet_gouvernement")} == {
        "DLR5L17N53259", "DLR5L17N52428"}                            # pas les propositions
    m = _un(ctx, "matiere", dossier="DLR5L17N53259")
    assert (m["statut"], m["commission"], m["libelle"]) == ("assemblee", "PO59047", "Commission des affaires étrangères")
    l = _un(ctx, "loi", numero_loi="2026-300")
    assert (l["dossier"], l["date_promulgation"], l["legislature"], l["gouvernement"], l["nor"]) == (
        "DLR5L17N53259", "2026-04-21", 17, "PO873634", "EAEJ2524276L")
    assert l["source_url"].startswith("http://www.legifrance.gouv.fr/")
    e = _un(ctx, "etat_dossier", dossier="DLR5L17N53259")
    assert (e["legislature"], e["etape_atteinte"], e["sort"], e["motif_adoption"]) == (17, "promulgue", "promulgue", None)
    assert e["derniere_conclusion"] == "modifié"


def test_matiere_et_etape_reelles(reel):
    ctx, _ = reel
    assert _un(ctx, "matiere", dossier="DLR5L15N37118")["statut"] == "assemblee"  # saisi aux deux chambres
    m = _un(ctx, "matiere", dossier="DLR5L17N51610")                              # mission d'information
    assert (m["statut"], m["raison"], m["libelle"]) == ("non_etablie", "aucune_saisine_au_fond", "Matière non établie")
    # 49107, texte de la XVIe adopté et promulgué en XVIIe : une ligne par législature.
    e = {x["legislature"]: x["etape_atteinte"] for x in _lignes(
        ctx, "SELECT * FROM etape_dossier WHERE dossier = 'DLR5L16N49107'")}
    assert e[17] == "promulgue" and e[16] == "seance"


# --- Sur de petites tables écrites ici ------------------------------------------------------------

def _scr(uid, titre, code="SPO", date="2025-03-01", seance=None, ref=None, numero=None):
    n = numero or int(uid.split("V")[-1])
    return {"uid": uid, "numero": n, "date": date, "code_type": code, "titre": titre,
            "seance": seance, "dossier_ref": ref, "sort_code": "adopté",
            "libelle_type": "scrutin public solennel" if code in ("SPS", "MOC") else "scrutin public ordinaire"}


@pytest.mark.parametrize("code,titre,nature,detail", [
    # Motion de censure : code MOC, même quand le libellé dit « scrutin public solennel » (XVe, XVIe).
    ("MOC", "la motion de censure déposée par M. X et 58 députés.", "motion_censure", "code_MOC"),
    ("SPS", "l'ensemble du projet de loi de finances pour 2025 (lecture définitive).", "ensemble", "ensemble"),
    ("SPO", "l'ensemble de de la proposition de loi instaurant des réponses adaptées (première lecture).",
     "ensemble", "ensemble"),                                                  # V918
    ("SPO", "l’ensemble de la proposition de résolution relative à la publicisation des doléances.",
     "ensemble", "ensemble"),
    ("SPS", "la proposition de loi apportant une réponse intégrale au phénomène des violences.",
     "ensemble", "ensemble_sans_le_mot"),                                      # V8705
    ("SPO", "le projet de loi autorisant l'approbation de l'accord entre le Gouvernement.",
     "ensemble", "ensemble_sans_le_mot"),                                      # V6284
    ("SPO", "l'ensemble de la première partie du projet de loi de finances de fin des gestion pour 2024.",
     "partie_de_texte", "partie"),                                             # V445
    ("SPO", "la deuxième partie projet de loi de financement de la sécurité sociale pour 2026.",
     "partie_de_texte", "partie"),                                             # V4595
    ("SPO", "l'amenedement n° 187 de M. Renault à l'article 35 du projet de loi de finances pour 2026.",
     "amendement", None),                                                      # V4988
    ("SPO", "le sous-amendmeent n° 776 de Mme Mansouri à l'amendement n° 609.", "amendement", None),  # V1633
    ("SPO", "les amendements identiques n° 3 et 4 à l'article 2.", "amendement", None),
    ("SPO", "l'aticle 6 du projet de loi sur la justice criminelle (première lecture).", "article", None),  # V7950
    ("SPO", "sur l' article 3 de la proposition de loi.", "article", None),   # espace parasite (XIVe)
    ("SPO", "la motion de rejet péalable, déposée par M. Patrick Hetzel, de la proposition de loi.",
     "motion_rejet", None),                                                    # V7432
    ("SPO", "la motion de renvoi en commission de la proposition de loi.", "autre", "motion_procedure"),
    ("SPS", "la déclaration du gouvernement portant sur la stratégie de défense nationale.", "declaration", None),
    ("SPO", "la demande de suspension de séance présentée par M. Lachaud.", "autre", "suspension_de_seance"),
    ("SPO", "la proposition du gouvernement de prolonger la séance en cours au-delà de minuit.",
     "autre", "prolongation_de_seance"),
    ("SPO", "les crédits de la mission « Défense » (état B).", "non_etablie", None),   # XVe : hors motifs
    ("SPO", "l'ensemble de l'article 3.", "non_etablie", None),               # « ensemble » sans texte
])
def test_nature_motifs(tmp_path, code, titre, nature, detail):
    ctx, b = _relier(_z2(tmp_path / "z2", scrutins=[_scr("VTANR5L17V1", titre, code)]), tmp_path / "z3")
    s = _un(ctx, "scrutin_classe", scrutin="VTANR5L17V1")
    assert (s["nature"], s["detail_nature"]) == (nature, detail)
    assert s["raison_nature"] == ("intitule_hors_motifs" if nature == "non_etablie" else None)
    assert s["solennel"] == (code == "SPS") and s["motion_censure"] == (code == "MOC")
    assert b["R-NATURE-SCRUTIN"]["couverture"]["nature_etablie"] == [int(nature != "non_etablie"), 1]


def test_nature_sans_intitule_et_congres_ecarte(tmp_path):
    z2 = _z2(tmp_path / "z2", scrutins=[_scr("VTANR5L17V1", None),
                                        _scr("VTCGR5L16V1", "le projet de loi constitutionnelle.")])
    ctx, _ = _relier(z2, tmp_path / "z3")
    assert _un(ctx, "scrutin_classe", scrutin="VTANR5L17V1")["raison_nature"] == "intitule_absent"
    assert ctx.un("SELECT count(*) FROM scrutin_classe WHERE scrutin LIKE 'VTCG%'") == 0


def _dos(uid, titre, procedure="2"):
    return {"uid": uid, "legislature": "17", "procedure_code": procedure, "titre": titre}


def _acte(dossier, uid, type_acte, code, date=None, **k):
    return {"dossier": dossier, "uid": uid, "type_acte": type_acte, "code": code,
            "date": date and f"{date}T00:00:00.000+01:00", **k}


def _seance(dossier, uid, reunion, date="2025-03-01"):
    return _acte(dossier, uid, "DiscussionSeancePublique_Type", "AN1-DEBATS-SEANCE", date, reunion=reunion)


def test_lien_accord_desaccord_et_departage(tmp_path):
    dossiers = [_dos("DA", "Protéger les abeilles"), _dos("DB", "Réformer les ports"),
                _dos("DC", "Simplifier la vie économique")]
    actes = [_seance("DA", "L17-A1", "RU1"), _seance("DB", "L17-B1", "RU2"),
             _seance("DA", "L17-A2", "RU3"), _seance("DB", "L17-B2", "RU3")]
    scrutins = [
        _scr("VTANR5L17V1", "l'amendement n° 1 à l'article 2.", seance="RU2", ref="DA"),  # désaccord
        _scr("VTANR5L17V2", "l'amendement n° 2 à l'article 2.", seance="RU1", ref="DA"),  # accord
        _scr("VTANR5L17V3", "l'article 1er de la proposition de loi visant à réformer les ports.", seance="RU3"),
        # Le titre d'un dossier hors de la séance (DC) ne compte pas.
        _scr("VTANR5L17V4", "l'article 1er de la proposition de loi visant à simplifier la vie économique.",
             seance="RU3"),
        _scr("VTANR5L17V5", "l'article 1er.", seance="RU9"),
    ]
    ctx, b = _relier(_z2(tmp_path / "z2", scrutins=scrutins, actes=actes, dossiers=dossiers), tmp_path / "z3")
    assert _un(ctx, "scrutin_non_relie", scrutin="VTANR5L17V1")["raison"] == "desaccord"
    assert _un(ctx, "scrutin_non_relie", scrutin="VTANR5L17V1")["candidats"] == [
        "reference_directe:DA", "seance:DB"]
    l = _un(ctx, "lien_scrutin_dossier", scrutin="VTANR5L17V2")
    assert (l["dossier"], l["route"], l["routes"], l["recoupe"]) == (
        "DA", "reference_directe", ["reference_directe", "seance"], True)
    l = _un(ctx, "lien_scrutin_dossier", scrutin="VTANR5L17V3")
    assert (l["dossier"], l["route"]) == ("DB", "seance_titre")
    assert _un(ctx, "scrutin_non_relie", scrutin="VTANR5L17V4")["raison"] == "seance_ambigue"
    assert _un(ctx, "scrutin_non_relie", scrutin="VTANR5L17V5")["raison"] == "seance_inconnue"
    c = b["R-LIEN-SCRUTIN-DOSSIER"]["couverture"]
    assert c["scrutin_relie"] == [2, 5] and c["desaccord_entre_routes"] == [1, 5]


def _depot(dossier, document, code="AN1-DEPOT", date="2025-01-10"):
    return _acte(dossier, f"L17-{dossier}-DI", "DepotInitiative_Type", code, date, texte_associe=document)


def test_origine_recoupee_par_le_document(tmp_path):
    dossiers = [_dos("DA", "Protéger les abeilles"), _dos("DR", "Résolution européenne", "8")]
    actes = [_depot("DA", "PIONANR5L17B0001"), _depot("DR", "PNREANR5L17B0002", "ANLUNI-DEPOT")]
    scrutins = [
        _scr("VTANR5L17V1", "l'ensemble du projet de loi visant à protéger les abeilles.", ref="DA"),
        _scr("VTANR5L17V2", "l'ensemble de la proposition de résolution européenne.", ref="DR"),
        _scr("VTANR5L17V3", "la demande de suspension de séance (article 58).", ref="DA"),
    ]
    ctx, _ = _relier(_z2(tmp_path / "z2", scrutins=scrutins, actes=actes, dossiers=dossiers), tmp_path / "z3")
    s = _un(ctx, "scrutin_classe", scrutin="VTANR5L17V1")
    assert (s["origine"], s["raison_origine"], s["origine_document"]) == (
        "non_etablie", "desaccord_intitule_document", "proposition")
    s = _un(ctx, "scrutin_classe", scrutin="VTANR5L17V2")
    assert (s["nature"], s["origine"], s["type_texte"]) == ("ensemble", "proposition", "PNRE")
    s = _un(ctx, "scrutin_classe", scrutin="VTANR5L17V3")           # sans catégorie : le document
    assert (s["origine"], s["origine_intitule"], s["type_texte"]) == ("proposition", None, "PION")


def test_derniere_lecture_sur_tout_le_corpus(tmp_path):
    dossiers = [_dos("DA", "Protéger les abeilles"), _dos("DB", "Réformer les ports")]
    scrutins = [
        _scr("VTANR5L17V10", "l'ensemble de la proposition de loi (première lecture).", date="2025-01-10", ref="DA"),
        _scr("VTANR5L17V20", "l'ensemble de la proposition de loi (deuxième lecture).", date="2025-06-10", ref="DA"),
        _scr("VTANR5L17V21", "l'ensemble de la proposition de loi (texte de la commission mixte paritaire).",
             date="2025-06-10", ref="DA"),
        # Plus récent, mais une partie de texte n'est jamais retenue.
        _scr("VTANR5L17V30", "la première partie du projet de loi de finances.", date="2025-09-01", ref="DA"),
        _scr("VTANR5L17V31", "l'amendement n° 1 à l'article 2.", date="2025-09-02", ref="DA"),
        _scr("VTANR5L16V99", "l'ensemble de la proposition de loi (première lecture).", date="2023-01-10", ref="DB",
             numero=99),
    ]
    ctx, b = _relier(_z2(tmp_path / "z2", scrutins=scrutins, dossiers=dossiers), tmp_path / "z3")
    d = _un(ctx, "derniere_lecture", dossier="DA")
    assert (d["scrutin"], d["lecture"], d["nb_votes_ensemble"]) == ("VTANR5L17V21", "cmp", 3)
    assert _un(ctx, "derniere_lecture", dossier="DB")["scrutin"] == "VTANR5L16V99"
    assert b["R-DERNIERE-LECTURE"]["couverture"]["dossier_avec_derniere_lecture"] == [2, 2]


def _saisie(dossier, uid, code, organe, date="2025-01-10"):
    return _acte(dossier, uid, "SaisieComFond_Type", code, date, organe=organe)


def test_matiere_senat_seulement_et_non_etablie(tmp_path):
    dossiers = [_dos("DS", "Texte du Sénat"), _dos("DN", "Sans saisine"), _dos("DI", "Incohérent"),
                _dos("DD", "Deux commissions")]
    actes = [_saisie("DS", "L17-S1", "SN1-COM-FOND-SAISIE", "PO211495"),
             # Étape du Sénat mais commission de l'Assemblée (DLR5L17N54574, 22/06/2026).
             _saisie("DI", "L17-I1", "SN1-COM-FOND-SAISIE", "PO419610"),
             _saisie("DD", "L17-D1", "AN1-COM-FOND-SAISIE", "PO59051"),
             _saisie("DD", "L17-D2", "AN2-COM-FOND-SAISIE", "PO419610")]
    ctx, b = _relier(_z2(tmp_path / "z2", actes=actes, dossiers=dossiers), tmp_path / "z3")
    m = _un(ctx, "matiere", dossier="DS")
    assert (m["statut"], m["libelle"], m["commission"], m["commissions_senat"]) == (
        "senat_seulement", "Saisi au Sénat seulement", None, ["PO211495"])
    assert (_un(ctx, "matiere", dossier="DN")["raison"]) == "aucune_saisine_au_fond"
    assert (_un(ctx, "matiere", dossier="DI")["statut"], _un(ctx, "matiere", dossier="DI")["raison"]) == (
        "non_etablie", "saisine_incoherente")
    assert (_un(ctx, "matiere", dossier="DD")["statut"], _un(ctx, "matiere", dossier="DD")["raison"]) == (
        "non_etablie", "plusieurs_commissions")
    assert b["R-MATIERE"]["couverture"]["senat_seulement"] == [1, 4]


def _decision(dossier, uid, code, conclusion, date, libelle=None):
    return _acte(dossier, uid, "Decision_Type", code, date, conclusion_code=conclusion,
                 conclusion_libelle=libelle or conclusion)


def test_etape_lue_dans_ce_qui_s_est_passe(tmp_path):
    dossiers = [_dos(f"D{i}", f"Texte {i}") for i in range(1, 4)]
    actes = [
        # D1 : saisie au fond le jour du dépôt (code « COM ») : ce n'est pas un examen.
        _depot("D1", "PIONANR5L17B0001"), _saisie("D1", "L17-D1-S", "AN1-COM-FOND-SAISIE", "PO59051"),
        # D2 : réunion de commission annoncée pour après la date de référence.
        _depot("D2", "PIONANR5L17B0002"),
        _acte("D2", "L17-D2-R", "DiscussionCommission_Type", "AN1-COM-FOND-REUNION", "2026-11-25",
              reunion="RUANR5L17S2026IDC1"),
        # D3 : réunion de commission tenue.
        _depot("D3", "PIONANR5L17B0003"),
        _acte("D3", "L17-D3-R", "DiscussionCommission_Type", "AN1-COM-FOND-REUNION", "2026-10-01",
              reunion="RUANR5L17S2026IDC2"),
    ]
    ctx, _ = _relier(_z2(tmp_path / "z2", actes=actes, dossiers=dossiers), tmp_path / "z3")
    e = {x["dossier"]: x["etape_atteinte"] for x in _lignes(ctx, "SELECT * FROM etape_dossier")}
    assert e == {"D1": "depot", "D2": "depot", "D3": "examen_commission"}


def test_sort_final_lu_dans_les_conclusions(tmp_path):
    dossiers = [_dos("PR", "PPL rejetée"), _dos("PS", "PPL du Sénat rejetée à l'AN"),
                _dos("RE", "Résolution 34-1", "22"), _dos("CM", "Texte de CMP"),
                _dos("RT", "PPL retirée"), _dos("PJ", "Projet rejeté en première lecture", "1"),
                _dos("CO", "Révision constitutionnelle", "7"), _dos("NL", "Nouvelle lecture")]
    actes = [
        _depot("PR", "PIONANR5L17B0001"),
        _decision("PR", "L17-PR-D", "AN1-DEBATS-DEC", "TSORTF07", "2025-03-01", "rejetée"),
        _depot("PS", "PIONSNR5S459B0001", "SN1-DEPOT"),
        _decision("PS", "L17-PS-D1", "SN1-DEBATS-DEC", "TSORTF01", "2025-01-01", "adoptée"),
        _decision("PS", "L17-PS-D2", "AN1-DEBATS-DEC", "TSORTF07", "2025-03-01", "rejetée"),
        _depot("RE", "PNREANR5L17B0003", "ANLUNI-DEPOT"),
        _decision("RE", "L17-RE-D", "ANLUNI-DEBATS-DEC", "TSORTF01", "2025-03-01", "adoptée"),
        _depot("CM", "PIONANR5L17B0004"),
        _decision("CM", "L17-CM-1", "AN1-DEBATS-DEC", "TSORTF01", "2025-01-01"),
        _decision("CM", "L17-CM-2", "SN1-DEBATS-DEC", "TSORTF05", "2025-02-01", "modifiée"),
        _decision("CM", "L17-CM-3", "CMP-DEBATS-AN-DEC", "TSORTF18", "2025-03-01"),
        _decision("CM", "L17-CM-4", "CMP-DEBATS-SN-DEC", "TSORTF18", "2025-03-05"),
        _depot("RT", "PIONANR5L17B0005"),
        _acte("RT", "L17-RT-R", "RetraitInitiative_Type", "AN1-RTRINI", "2025-04-01"),
        _depot("PJ", "PRJLANR5L17B0006"),
        _decision("PJ", "L17-PJ-D", "AN1-DEBATS-DEC", "TSORTF07", "2025-03-01", "rejeté"),
        _depot("CO", "PIONANR5L17B0007"),
        _decision("CO", "L17-CO-1", "AN1-DEBATS-DEC", "TSORTF01", "2025-01-01"),
        _decision("CO", "L17-CO-2", "SN1-DEBATS-DEC", "TSORTF03", "2025-02-01", "adoptée sans modification"),
        # Nouvelle lecture : l'AN vote son propre texte ; ce n'est pas une adoption conforme.
        _depot("NL", "PIONANR5L17B0008"),
        _decision("NL", "L17-NL-1", "SN1-DEBATS-DEC", "TSORTF01", "2025-01-01"),
        _decision("NL", "L17-NL-2", "ANNLEC-DEBATS-DEC", "TSORTF01", "2025-02-01"),
    ]
    ctx, b = _relier(_z2(tmp_path / "z2", actes=actes, dossiers=dossiers), tmp_path / "z3")
    s = {x["dossier"]: (x["sort"], x["raison_sort"]) for x in _lignes(ctx, "SELECT * FROM etat_dossier")}
    assert s == {"PR": ("rejete", None), "PS": ("non_connu", "aucune_decision_finale"),
                 "RE": ("adopte", None), "CM": ("adopte", None), "RT": ("retire", None),
                 "PJ": ("non_connu", "aucune_decision_finale"),
                 "CO": ("non_connu", "revision_constitutionnelle"),
                 "NL": ("non_connu", "aucune_decision_finale")}
    cm = _un(ctx, "etat_dossier", dossier="CM")
    assert (cm["motif_adoption"], cm["date_sort"], cm["etape_atteinte"]) == (
        "texte_cmp_adopte_par_les_deux_chambres", "2025-03-05", "adopte")
    assert cm["par_49_3"] is False and cm["numero_loi"] is None    # pas de 0, pas de loi inventée



def test_sort_renvoi_en_commission_et_decision_sans_conclusion(tmp_path):
    """Alerte #118 (décidé le 23/11/2026 : doc. 5, Q45 et Q46). Une motion de renvoi en commission
    adoptée (TSORTMOT01, motion TMP03) n'est ni une adoption ni un rejet : raison
    `renvoye_en_commission`, plus nommée par A7. Une décision sans conclusion (TSORTFnull) n'est
    nommée que là où elle est la dernière décision."""
    dossiers = [_dos("RC", "PPL renvoyée en commission"), _dos("SC", "Nouvelle lecture au Sénat, puis AN"),
                _dos("SD", "Nouvelle lecture au Sénat, rien ensuite")]
    actes = [
        _depot("RC", "PIONANR5L17B0001"),
        _acte("RC", "L17-RC-M", "MotionProcedure_Type", "AN1-DEBATS-MOTION", "2025-03-01",
              type_motion_code="TMP03", type_motion_libelle="Motions de renvoi en commission"),
        _decision("RC", "L17-RC-MDEC", "AN1-DEBATS-MOTION-VOTE", "TSORTMOT01", "2025-03-01", "Motion adoptée"),
        _depot("SC", "PRJLANR5L17B0002"),
        _decision("SC", "L17-SC-1", "SNNLEC-DEBATS-DEC", "TSORTFnull", "2025-03-01"),
        _decision("SC", "L17-SC-2", "ANLDEF-DEBATS-DEC", "TSORTF01", "2025-03-05", "adopté"),
        _depot("SD", "PRJLANR5L17B0003"),
        _decision("SD", "L17-SD-1", "SNNLEC-DEBATS-DEC", "TSORTFnull", "2025-03-01"),
    ]
    for a in actes:                                         # la source ne publie pas de libellé
        if a.get("conclusion_code") == "TSORTFnull":
            a["conclusion_libelle"] = None
    ctx, _ = _relier(_z2(tmp_path / "z2", actes=actes, dossiers=dossiers), tmp_path / "z3")
    s = {x["dossier"]: (x["sort"], x["raison_sort"]) for x in _lignes(ctx, "SELECT * FROM etat_dossier")}
    assert s == {"RC": ("non_connu", "renvoye_en_commission"), "SC": ("adopte", None),
                 "SD": ("non_connu", "conclusion_non_classee")}
    nc = _lignes(ctx, "SELECT * FROM conclusion_non_classee")
    assert [(x["conclusion_code"], x["conclusion_libelle"], x["decisions"], x["exemples"],
             x["dossiers_dont_c_est_la_derniere_decision"]) for x in nc] == [
        ("TSORTFnull", None, 1, ["SD"], 1)]

def test_lois_et_projets_rattaches_a_la_date(tmp_path):
    dossiers = [_dos("DL", "Loi de la dissolution"), _dos("DP", "Projet déposé au Sénat", "1"),
                _dos("DX", "Projet sans date", "1")]
    actes = [
        _acte("DL", "L16-DL-P", "Promulgation_Type", "PROM-PUB", "2024-06-20", code_loi="2024-582"),
        _depot("DP", "PRJLSNR5S479B0001", "SN1-DEPOT", "2024-12-13"),        # dernier jour de Barnier
        _depot("DX", "PRJLANR5L17B0002", "AN1-DEPOT", None),
    ]
    ctx, _ = _relier(_z2(tmp_path / "z2", actes=actes, dossiers=dossiers), tmp_path / "z3")
    l = _un(ctx, "loi", numero_loi="2024-582")
    assert (l["legislature"], l["raison_legislature"], l["gouvernement"]) == (
        None, "entre_deux_legislatures", "PO833673")                        # Attal
    p = _un(ctx, "projet_gouvernement", dossier="DP")
    assert (p["gouvernement"], p["chambre_depot"], p["date_depot"]) == ("PO847639", "SN", "2024-12-13")
    x = _un(ctx, "projet_gouvernement", dossier="DX")
    assert (x["gouvernement"], x["raison"]) == (None, "date_de_depot_absente")


def test_toutes_les_regles_rendent_leur_couverture(reel):
    _, b = reel
    for nom in ("R-NATURE-SCRUTIN", "R-LIEN-SCRUTIN-DOSSIER", "R-ORIGINE", "R-DERNIERE-LECTURE",
                "R-MATIERE", "R-ETAPE", "R-SORT-FINAL", "R-49-3", "R-LOIS", "R-DEPOT-GOUVERNEMENT",
                "R-LOI-ADOPTION"):
        c = b[nom]["couverture"]
        assert c and all(isinstance(n, int) and isinstance(d, int) and n <= d for n, d in c.values()), nom
        assert b[nom]["description"]


def test_suite_absente_des_archives(tmp_path):
    """Issue #35 : un dossier publié par la seule archive d'une législature close (XVIe ici), avec
    des actes de la législature suivante, n'a pas « aucune décision finale » : sa suite n'est dans
    aucune archive (cas réel : DLR5L14N35818, loi 2018-287, archive de la XIVe arrêtée au
    22/03/2018)."""
    pt = {"prov_point": "an-dossiers-l16"}
    dossiers = [_dos("SA", "Texte poursuivi sous la XVIIe"), _dos("SB", "Texte resté en XVIe")]
    actes = [
        {**_depot("SA", "PIONSNR5S459B0009", "SN1-DEPOT", "2024-03-01"), "uid": "L16-SA-DI", **pt},
        {**_decision("SA", "L16-SA-D1", "SN1-DEBATS-DEC", "TSORTF01", "2024-04-01"), **pt},
        {**_acte("SA", "L17-SA-DIN", "DepotInitiativeNavette_Type", "AN1-DEPOT", "2024-09-20"), **pt},
        {**_depot("SB", "PIONSNR5S459B0010", "SN1-DEPOT", "2024-03-01"), "uid": "L16-SB-DI", **pt},
        {**_decision("SB", "L16-SB-D1", "SN1-DEBATS-DEC", "TSORTF01", "2024-04-02"), **pt},
    ]
    ctx, _ = _relier(_z2(tmp_path / "z2", actes=actes, dossiers=dossiers), tmp_path / "z3")
    s = {x["dossier"]: (x["sort"], x["raison_sort"], x["fin_archive_du_dossier"])
         for x in _lignes(ctx, "SELECT DISTINCT dossier, sort, raison_sort, fin_archive_du_dossier FROM etat_dossier")}
    assert s == {"SA": ("non_connu", "suite_absente_des_archives", "2024-09-20"),
                 "SB": ("non_connu", "aucune_decision_finale", None)}


def test_suite_absente_reliee_par_le_journal_officiel(tmp_path):
    """Issue #35, décisions du 15/11/2026 : une loi du JO relie un dossier dont la suite manque aux
    archives par ses travaux préparatoires. Un seul numéro suffit pour un tel dossier s'il est celui
    du texte déposé sous la législature de la promulgation ; un numéro de la législature précédente
    qui mène ailleurs ne le contredit pas (cas réel : loi 2018-581, rapport n° 994 de la XVe, qui
    tombe sous la XIVe sur un autre dossier). Pour un dossier ordinaire, un seul numéro ne suffit
    pas (loi 2018-1068, reliée à tort au secret des sources)."""
    from empreinte_src.lecteurs import an_dossiers as lec_dossiers, jo_actes
    pt = {"prov_point": "an-dossiers-l16"}
    dossiers = [_dos("SA", "Texte poursuivi sous la XVIIe"), _dos("SB", "Texte ordinaire"),
                _dos("SX", "Autre dossier de la XVIe")]
    actes = [
        {**_depot("SA", "PIONSNR5S459B0009", "SN1-DEPOT", "2024-03-01"), "uid": "L16-SA-DI", **pt},
        {**_acte("SA", "L17-SA-DIN", "DepotInitiativeNavette_Type", "AN1-DEPOT", "2024-09-20"), **pt},
        {**_depot("SB", "PIONANR5L17B0124", "AN1-DEPOT", "2024-10-01"), "uid": "L17-SB-DI",
         "prov_point": "an-dossiers-l17"},
    ]
    z2 = _z2(tmp_path / "z2", actes=actes, dossiers=dossiers)
    _ecrire(z2, lec_dossiers, "document", [
        {"uid": "PIONANR5L17B0123", "dossier": "SA"}, {"uid": "RAPPANR5L16B0456", "dossier": "SX"},
        {"uid": "PIONANR5L17B0124", "dossier": "SB"}])
    _ecrire(z2, jo_actes, "acte_reglementaire", [
        {"uid": "jorf:A", "nature": "LOI", "numero": "2025-100", "date_signature": "2025-03-01",
         "prov_url": "https://www.legifrance.gouv.fr/jorf/id/A"},
        {"uid": "jorf:A2", "nature": "LOI", "numero": "2025-100", "date_signature": "2025-03-01"},
        {"uid": "jorf:B", "nature": "LOI", "numero": "2025-101", "date_signature": "2025-03-02"}])
    tp = lambda acte, nature, numero: {"acte": acte, "chambre": "AN", "nature": nature, "numero": numero}
    _ecrire(z2, jo_actes, "travaux_preparatoires", [
        tp("jorf:A", "proposition_de_loi", "123"), tp("jorf:A", "rapport", "456"),
        tp("jorf:B", "proposition_de_loi", "124")])
    ctx, b = _relier(z2, tmp_path / "z3")
    j = {x["numero_loi"]: x for x in _lignes(ctx, "SELECT * FROM loi_dossier_jo")}
    assert set(j) == {"2025-100", "2025-101"}                  # une ligne par loi, pas par acte
    assert (j["2025-100"]["dossier"], j["2025-100"]["preuve"], j["2025-100"]["acte"]) == (
        "SA", "texte_depose_seul", "jorf:A")
    assert (j["2025-101"]["dossier"], j["2025-101"]["raison"]) == (None, "un_seul_numero")
    s = {x["dossier"]: x for x in _lignes(ctx, "SELECT DISTINCT dossier, sort, raison_sort, numero_loi, "
                                               "date_promulgation, url_loi, lien_loi FROM etat_dossier")}
    assert (s["SA"]["sort"], s["SA"]["raison_sort"], s["SA"]["numero_loi"], s["SA"]["date_promulgation"],
            s["SA"]["lien_loi"]) == ("promulgue", None, "2025-100", "2025-03-01", "travaux_preparatoires_jo")
    assert s["SA"]["url_loi"] == "https://www.legifrance.gouv.fr/jorf/id/A"
    assert s["SB"]["sort"] == "non_connu"
    # R-LOI-ADOPTION (#83) : l'archive de SA s'arrête le 20/09/2024 (XVIIe) sans vote de l'Assemblée ;
    # son vote est entre cette date et la promulgation (01/03/2025), donc sous la XVIIe.
    a = {x["numero_loi"]: x for x in _lignes(ctx, "SELECT * FROM loi_adoption")}
    assert set(a) == {"2025-100", "2025-101"}
    assert (a["2025-100"]["legislature_adoption"], a["2025-100"]["preuve_adoption"],
            a["2025-100"]["lien_dossier"], a["2025-100"]["fin_archive_du_dossier"]) == (
        17, "encadree_par_la_promulgation", "travaux_preparatoires_jo", "2024-09-20")
    assert (a["2025-101"]["legislature_adoption"], a["2025-101"]["raison_adoption"],
            a["2025-101"]["raison_lien"]) == (None, "loi_sans_dossier", "un_seul_numero")



def test_legislature_nommee_par_le_journal_officiel(tmp_path):
    """Issue #146 (loi 2020-839) : le JO nomme la législature d'un numéro (« n° 967 (quinzième
    législature) »). Seule celle-là est candidate : sans cela, le n° 967 tombait sous la
    législature précédente sur un autre dossier, et la loi n'était reliée à rien."""
    from empreinte_src.lecteurs import an_dossiers as lec_dossiers, jo_actes
    dossiers = [_dos("SA", "Texte de la XVIe poursuivi sous la XVIIe"), _dos("SY", "Homonyme de la XVIe")]
    z2 = _z2(tmp_path / "z2", dossiers=dossiers)
    _ecrire(z2, lec_dossiers, "document", [
        {"uid": "PIONANR5L16B0123", "dossier": "SA"}, {"uid": "RAPPANR5L16B0456", "dossier": "SA"},
        {"uid": "PIONANR5L16B0789", "dossier": "SY"}])
    _ecrire(z2, jo_actes, "acte_reglementaire", [
        {"uid": "jorf:A", "nature": "LOI", "numero": "2025-200", "date_signature": "2025-03-01"},
        {"uid": "jorf:B", "nature": "LOI", "numero": "2025-201", "date_signature": "2025-03-02"}])
    tp = lambda acte, nature, numero, leg=None: {"acte": acte, "chambre": "AN", "nature": nature,
                                                 "numero": numero, "legislature": leg}
    _ecrire(z2, jo_actes, "travaux_preparatoires", [
        tp("jorf:A", "proposition_de_loi", "123", 16), tp("jorf:A", "rapport", "456"),
        tp("jorf:A", "proposition_de_loi", "789", 17),
        # Même travaux, sans législature nommée : le n° 789 de la XVIe contredit le lien.
        tp("jorf:B", "proposition_de_loi", "123"), tp("jorf:B", "rapport", "456"),
        tp("jorf:B", "proposition_de_loi", "789")])
    ctx, b = _relier(z2, tmp_path / "z3")
    j = {x["numero_loi"]: x for x in _lignes(ctx, "SELECT * FROM loi_dossier_jo")}
    assert (j["2025-200"]["dossier"], j["2025-200"]["preuve"]) == ("SA", "plusieurs_numeros")
    assert (j["2025-201"]["dossier"], j["2025-201"]["raison"]) == (None, "dossiers_differents")

def test_date_de_promulgation_lue_au_journal_officiel(tmp_path):
    """Loi 2021-191 (14/11/2026) : l'acte de promulgation de l'Assemblée est daté du 0021-02-24 ;
    le JO date la loi du 22/02/2021. La date du JO fait foi ; celle de l'Assemblée est gardée."""
    from empreinte_src.lecteurs import jo_actes
    dossiers = [_dos("DL", "Report des élections"), _dos("DM", "Loi sans JO")]
    actes = [_acte("DL", "L15-DL-P", "Promulgation_Type", "PROM-PUB", "0021-02-24", code_loi="2021-191"),
             _acte("DM", "L17-DM-P", "Promulgation_Type", "PROM-PUB", "2025-02-14", code_loi="2025-150")]
    z2 = _z2(tmp_path / "z2", actes=actes, dossiers=dossiers)
    _ecrire(z2, jo_actes, "acte_reglementaire", [
        {"uid": "jorf:JORFTEXT000043168123", "nature": "LOI", "numero": "2021-191",
         "date_signature": "2021-02-22"}])
    ctx, b = _relier(z2, tmp_path / "z3")
    l = {x["numero_loi"]: x for x in _lignes(ctx, "SELECT * FROM loi")}
    assert (l["2021-191"]["date_promulgation"], l["2021-191"]["source_date_promulgation"],
            l["2021-191"]["date_assemblee"]) == ("2021-02-22", "journal_officiel", "0021-02-24")
    assert (l["2025-150"]["date_promulgation"], l["2025-150"]["source_date_promulgation"]) == (
        "2025-02-14", "assemblee")


def test_legislature_d_adoption_d_une_loi(tmp_path):
    """Issue #83 : une loi est comptée, à côté de sa promulgation, dans la législature où
    l'Assemblée l'a adoptée en dernier. Cas recopiés des archives (g24 du 24/11/2026) :
    - AC : l'Assemblée clôt la navette (adoption conforme en deuxième lecture) ;
    - SC : le Sénat clôt dans la même législature, conclusion codée « modifié » (TSORTF05) à la
      source alors que la loi est promulguée (cas de 2021-303) ;
    - SX : le Sénat clôt sous la législature suivante (cas de 2024-1017) : décision Q65 du
      25/11/2026, la loi est de la législature du dernier vote de l'Assemblée (XVIe), les deux
      législatures servies ;
    - DI : promulguée entre la dissolution et la XVIIe (2024-536), adoptée sous la XVIe ;
    - CM : séance de l'Assemblée sur le texte de CMP sous la XVIIe, sans décision de l'Assemblée
      lue (la décision de CMP n'a pas de chambre) : décision Q66 du 25/11/2026, la législature du
      dernier vote enregistré de l'Assemblée (XVIe, 2024-1039) ;
    - lois du JO sans dossier (Q67) : adoptée à l'Assemblée le 03/10/2011 d'après ses travaux
      préparatoires (2012-1166) : hors périmètre ; adoptée le 28/11/2013 (2013-1118) : XIVe, par la
      date du JO (Q69) ; sans travaux préparatoires : pas de dossier, la raison est dite."""
    from empreinte_src.lecteurs import jo_actes
    dossiers = [_dos(d, f"Texte {d}") for d in ("AC", "SC", "SX", "DI", "CM")]
    prom = lambda d, date, loi: _acte(d, f"L17-{d}-P", "Promulgation_Type", "PROM-PUB", date, code_loi=loi)
    actes = [
        _depot("AC", "PIONANR5L17B0001"),
        _decision("AC", "L17-AC-1", "AN1-DEBATS-DEC", "TSORTF01", "2025-01-15"),
        _decision("AC", "L17-AC-2", "SN1-DEBATS-DEC", "TSORTF02", "2025-02-10", "adoptée avec modifications"),
        _decision("AC", "L17-AC-3", "AN2-DEBATS-DEC", "TSORTF01", "2025-03-05"),
        prom("AC", "2025-03-15", "2025-300"),
        _depot("SC", "PIONANR5L17B0002"),
        _decision("SC", "L17-SC-1", "AN1-DEBATS-DEC", "TSORTF01", "2025-01-20"),
        _decision("SC", "L17-SC-2", "SN1-DEBATS-DEC", "TSORTF05", "2025-04-01", "modifié"),
        prom("SC", "2025-04-10", "2025-301"),
        _depot("SX", "PIONANR5L16B0003", date="2023-10-01"),
        _decision("SX", "L16-SX-1", "AN1-DEBATS-DEC", "TSORTF01", "2024-04-10"),
        _decision("SX", "L17-SX-2", "SN1-DEBATS-DEC", "TSORTF05", "2024-11-05", "modifié"),
        prom("SX", "2024-11-13", "2024-1017"),
        _depot("DI", "PIONANR5L16B0004", date="2023-10-01"),
        _decision("DI", "L16-DI-1", "AN1-DEBATS-DEC", "TSORTF01", "2024-01-10"),
        _decision("DI", "L16-DI-2", "SN1-DEBATS-DEC", "TSORTF05", "2024-03-10", "modifié"),
        _decision("DI", "L16-DI-3", "CMP-DEBATS-SN-DEC", "TSORTF18", "2024-06-04"),
        _decision("DI", "L16-DI-4", "CMP-DEBATS-AN-DEC", "TSORTF18", "2024-06-05"),
        prom("DI", "2024-06-13", "2024-536"),
        _depot("CM", "PIONANR5L16B0005", date="2023-04-28"),
        _decision("CM", "L16-CM-1", "AN1-DEBATS-DEC", "TSORTF01", "2024-01-29"),
        _decision("CM", "L16-CM-2", "SN1-DEBATS-DEC", "TSORTF05", "2024-05-21", "modifiée"),
        _acte("CM", "L17-CM-S", "DiscussionSeancePublique_Type", "CMP-DEBATS-AN-SEANCE", "2024-11-07"),
        _decision("CM", "L17-CM-3", "CMP-DEBATS-DEC", "TSORTF18", "2024-11-07"),
        prom("CM", "2024-11-19", "2024-1039"),
    ]
    xive = {"uid": "PO644420", "type_organe": "ASSEMBLEE", "legislature": "14",
            "date_debut": "2012-06-20", "date_fin": "2017-06-20"}
    z2 = _z2(tmp_path / "z2", actes=actes, dossiers=dossiers, organes=ORGANES + [xive])
    _ecrire(z2, jo_actes, "acte_reglementaire", [
        {"uid": "jorf:J", "nature": "LOI", "numero": "2025-400", "date_signature": "2025-05-02"},
        {"uid": "jorf:K", "nature": "LOI", "numero": "2012-1166", "date_signature": "2012-10-19"},
        {"uid": "jorf:L", "nature": "LOI", "numero": "2013-1118", "date_signature": "2013-12-06"}])
    tp = lambda acte, chambre, ligne, numero=None, ta=None: {
        "acte": acte, "chambre": chambre, "nature": "discussion" if ta else "projet_de_loi",
        "numero": numero, "numero_ta": ta, "ligne": ligne}
    _ecrire(z2, jo_actes, "travaux_preparatoires", [
        tp("jorf:K", "AN", "Projet de loi n° 3139 (XIIIe législature)", "3139"),
        tp("jorf:K", "AN", "Discussion et adoption (procédure d'examen simplifiée) le 3 octobre 2011 "
                           "(TA n° 729)", ta="729"),
        tp("jorf:K", "SN", "Discussion et adoption (procédure d'examen simplifiée) le 9 octobre 2012 "
                           "(TA n° 3, 2012-2013)", ta="3"),
        tp("jorf:L", "AN", "Discussion et adoption le 28 novembre 2013 (TA n° 249)", ta="249"),
        tp("jorf:L", "SN", "Discussion les 28 février et 13 juin 2013 et adoption le 13 juin 2013 "
                           "(TA n° 168, 2012-2013)", ta="168")])
    ctx, b = _relier(z2, tmp_path / "z3")
    a = {x["numero_loi"]: x for x in _lignes(ctx, "SELECT * FROM loi_adoption")}
    v = {k: (x["legislature_promulgation"], x["legislature_adoption"], x["preuve_adoption"],
             x["raison_adoption"]) for k, x in a.items()}
    assert v == {
        "2025-300": (17, 17, "vote_final_de_l_assemblee", None),
        "2025-301": (17, 17, "cloture_hors_assemblee_meme_legislature", None),
        "2024-1017": (17, 16, "dernier_vote_de_l_assemblee_cloture_sous_une_autre_legislature", None),
        "2024-536": (None, 16, "vote_final_de_l_assemblee", None),
        "2024-1039": (17, 16, "dernier_vote_enregistre_de_l_assemblee_seance_posterieure", None),
        "2025-400": (17, None, None, "loi_sans_dossier"),
        "2012-1166": (14, None, None, "dossier_anterieur_a_la_xive_hors_perimetre"),
        "2013-1118": (14, 14, "derniere_adoption_an_lue_au_jo", None)}
    # La date lue au JO est la dernière adoption de l'Assemblée, jamais celle du Sénat.
    assert (a["2012-1166"]["date_adoption_an_lue_au_jo"], a["2013-1118"]["date_adoption_an_lue_au_jo"],
            a["2025-400"]["date_adoption_an_lue_au_jo"]) == ("2011-10-03", "2013-11-28", None)
    assert (a["2025-300"]["motif_cloture"], a["2025-300"]["acte_dernier_vote_an"]) == (
        "adoption_conforme", "L17-AC-3")
    assert (a["2025-301"]["chambre_cloture"], a["2025-301"]["motif_cloture"],
            a["2025-301"]["date_dernier_vote_an"]) == ("SN", "derniere_adoption_avant_promulgation", "2025-01-20")
    sx = a["2024-1017"]
    assert (sx["legislature_dernier_vote_an"], sx["legislature_cloture"]) == (16, 17)
    cm = a["2024-1039"]                  # la décision de CMP sans chambre est bien la clôture lue
    assert (cm["acte_cloture"], cm["chambre_cloture"], cm["legislature_derniere_seance_an"]) == (
        "L17-CM-3", None, 17)
    assert a["2025-400"]["raison_lien"] == "pas_de_travaux_preparatoires"
    assert b["R-LOI-ADOPTION"]["couverture"] == {"legislature_d_adoption_etablie": [6, 8],
                                                 "meme_legislature_que_la_promulgation": [3, 6],
                                                 "legislature_etablie_ou_hors_perimetre": [7, 8]}
    # R-LOIS ne change pas : la loi de la dissolution reste hors de toute législature.
    assert _un(ctx, "loi", numero_loi="2024-536")["legislature"] is None


def test_suite_absente_datee_par_le_journal_officiel(tmp_path):
    """Q69 (décision du 25/11/2026, « Utiliser la date du JO ») : la suite d'un dossier manque aux
    archives (archive de la XVIe arrêtée le 20/09/2024), le dernier vote lu de l'Assemblée est de
    la XVIe et la loi est promulguée sous la XVIIe : pas d'encadrement. La dernière adoption à
    l'Assemblée citée par le JO (10/02/2025) donne la XVIIe (cas réel : 2020-839, XVe). Une date du
    JO antérieure au dernier vote lu contredit les archives : la raison reste dite."""
    from empreinte_src.lecteurs import an_dossiers as lec_dossiers, jo_actes
    pt = {"prov_point": "an-dossiers-l16"}
    dossiers = [_dos("SC", "Texte voté sous la XVIe, suite absente"), _dos("SD", "Même cas, JO contradictoire")]
    actes = []
    for d, n in (("SC", "0125"), ("SD", "0126")):
        actes += [{**_depot(d, f"PIONANR5L16B{n}", "AN1-DEPOT", "2023-05-01"), "uid": f"L16-{d}-DI", **pt},
                  {**_decision(d, f"L16-{d}-D1", "AN1-DEBATS-DEC", "TSORTF01", "2023-06-01"), **pt}]
    actes.append({**_acte("SC", "L17-SC-DIN", "DepotInitiativeNavette_Type", "SN1-DEPOT", "2024-09-20"), **pt})
    z2 = _z2(tmp_path / "z2", actes=actes, dossiers=dossiers)
    _ecrire(z2, lec_dossiers, "document", [
        {"uid": "PIONANR5L16B0125", "dossier": "SC"}, {"uid": "RAPPANR5L16B0457", "dossier": "SC"},
        {"uid": "PIONANR5L16B0126", "dossier": "SD"}, {"uid": "RAPPANR5L16B0458", "dossier": "SD"}])
    _ecrire(z2, jo_actes, "acte_reglementaire", [
        {"uid": "jorf:C", "nature": "LOI", "numero": "2025-200", "date_signature": "2025-03-01"},
        {"uid": "jorf:D", "nature": "LOI", "numero": "2025-201", "date_signature": "2025-03-01"}])
    tp = lambda acte, nature, numero=None, ligne=None: {
        "acte": acte, "chambre": "AN", "nature": nature, "numero": numero, "ligne": ligne}
    _ecrire(z2, jo_actes, "travaux_preparatoires", [
        tp("jorf:C", "proposition_de_loi", "125"), tp("jorf:C", "rapport", "457"),
        tp("jorf:C", "discussion", ligne="Discussion et adoption le 10 février 2025 (TA n° 50)"),
        tp("jorf:D", "proposition_de_loi", "126"), tp("jorf:D", "rapport", "458"),
        tp("jorf:D", "discussion", ligne="Discussion et adoption le 15 mai 2023 (TA n° 12)")])
    ctx, _ = _relier(z2, tmp_path / "z3")
    a = {x["numero_loi"]: x for x in _lignes(ctx, "SELECT * FROM loi_adoption")}
    assert (a["2025-200"]["dossier"], a["2025-200"]["legislature_dernier_vote_an"],
            a["2025-200"]["fin_archive_du_dossier"]) == ("SC", 16, "2024-09-20")
    assert (a["2025-200"]["legislature_adoption"], a["2025-200"]["preuve_adoption"],
            a["2025-200"]["date_adoption_an_lue_au_jo"]) == (17, "derniere_adoption_an_lue_au_jo", "2025-02-10")
    assert (a["2025-201"]["legislature_adoption"], a["2025-201"]["raison_adoption"],
            a["2025-201"]["date_adoption_an_lue_au_jo"]) == (None, "suite_absente_des_archives", "2023-05-15")


def test_censure_apres_49_3_et_texte_de_cmp(tmp_path):
    """Issue #89 (cas réel : PLFSS 2025, DLR5L17N50588, actes recopiés de la g24). Le gouvernement
    Barnier engage sa responsabilité sur le texte de CMP le 02/12/2024 ; la motion de censure est
    adoptée le 04/12/2024 (TSORTMOT01, scrutin VTANR5L17V519) : rejet via 49.3. Le texte est repris
    et promulgué : le sort reste celui du dossier. Une motion rejetée (TSORTMOT02) n'est pas un rejet ;
    une motion dont le code ne nomme pas la lecture (« MOTION-VOTE ») est rattachée à l'engagement le
    plus récent. Un texte promulgué dont la clôture lue est une décision de CMP sans chambre
    (CMP-DEBATS-DEC) est adopté sur le texte de CMP ; cette dernière décision garde sa chambre vide
    (R-SORT-FINAL v6 : `max_by` lui donnait celle de la décision précédente)."""
    dossiers = [_dos("PS", "Projet de loi de financement de la sécurité sociale pour 2025", "4"),
                _dos("RJ", "Projet de loi, motion rejetée", "1"), _dos("CM", "Texte de CMP sans chambre")]
    actes = [
        _depot("PS", "PRJLANR5L17B0325", date="2024-10-10"),
        _decision("PS", "L17-PS-1", "AN1-DEBATS-DEC", "TSORTF01", "2024-11-05"),
        _decision("PS", "L17-PS-2", "SN1-DEBATS-DEC", "TSORTF05", "2024-11-26", "modifié"),
        _acte("PS", "L17-VD222534", "DeclarationGouvernement_Type", "CMP-DGVT", "2024-12-02",
              type_declaration_code="Art.49.3"),
        _decision("PS", "L17-VD222686DEC", "CMP-DEBATS-AN-DEC", "TSORTF24", "2024-12-04",
                  "considéré comme rejeté par l'Assemblée nationale en application de l'article 49, alinéa 3"),
        _acte("PS", "L17-VD222690", "DecisionMotionCensure_Type", "CMP-MOTION-VOTE", "2024-12-04",
              decision_code="TSORTMOT01", decision_libelle="Motion adoptée", scrutins=["VTANR5L17V519"]),
        _acte("PS", "L17-VD223530", "DeclarationGouvernement_Type", "ANNLEC-DGVT", "2025-02-03",
              type_declaration_code="Art.49.3"),
        _acte("PS", "L17-VD223655", "DecisionMotionCensure_Type", "ANNLEC-MOTION-VOTE", "2025-02-05",
              decision_code="TSORTMOT02", decision_libelle="Motion rejetée", scrutins=["VTANR5L17V694"]),
        _decision("PS", "L17-VD223800DEC", "ANNLEC-DEBATS-DEC", "TSORTF06", "2025-02-12",
                  "considéré comme adopté par l'Assemblée nationale en application de l'article 49, alinéa 3"),
        {**_decision("PS", "L17-VD223916DEC", "SNNLEC-DEBATS-DEC", "TSORTFnull", "2025-02-17"),
         "conclusion_libelle": None},
        _acte("PS", "L17-PS-P", "Promulgation_Type", "PROM-PUB", "2025-02-28", code_loi="2025-199"),
        _depot("RJ", "PRJLANR5L16B0001", date="2023-09-01"),
        _acte("RJ", "L16-RJ-E", "DeclarationGouvernement_Type", "ANNLEC-DGVT", "2023-09-27",
              type_declaration_code="Art.49.3"),
        _acte("RJ", "L16-RJ-M", "DecisionMotionCensure_Type", "MOTION-VOTE", "2023-09-30",
              decision_code="TSORTMOT02", decision_libelle="Motion rejetée"),
        _depot("CM", "PIONANR5L16B0005", date="2023-04-28"),
        _decision("CM", "L16-CM-1", "AN1-DEBATS-DEC", "TSORTF01", "2024-01-29"),
        _decision("CM", "L16-CM-2", "SN1-DEBATS-DEC", "TSORTF05", "2024-05-21", "modifiée"),
        _decision("CM", "L17-CM-3", "CMP-DEBATS-DEC", "TSORTF18", "2024-11-07"),
        _acte("CM", "L17-CM-P", "Promulgation_Type", "PROM-PUB", "2024-11-19", code_loi="2024-1039"),
    ]
    ctx, b = _relier(_z2(tmp_path / "z2", actes=actes, dossiers=dossiers), tmp_path / "z3")
    c = {x["acte_motion"]: x for x in _lignes(ctx, "SELECT * FROM censure_49_3")}
    assert {k: (x["dossier"], x["acte_engagement"], x["issue"], x["scrutin"]) for k, x in c.items()} == {
        "L17-VD222690": ("PS", "L17-VD222534", "adoptee", "VTANR5L17V519"),
        "L17-VD223655": ("PS", "L17-VD223530", "rejetee", "VTANR5L17V694"),
        "L16-RJ-M": ("RJ", "L16-RJ-E", "rejetee", None)}
    assert b["R-49-3"]["couverture"]["issue_de_la_motion_lue"] == [3, 3]
    e = {x["dossier"]: x for x in _lignes(ctx, "SELECT DISTINCT dossier, sort, par_49_3, adopte_par_49_3, "
                                               "rejete_par_censure_49_3, date_censure_49_3, scrutin_censure_49_3, "
                                               "motif_adoption, adopte_sur_texte_cmp, numero_loi FROM etat_dossier")}
    assert (e["PS"]["sort"], e["PS"]["adopte_par_49_3"], e["PS"]["rejete_par_censure_49_3"],
            e["PS"]["date_censure_49_3"], e["PS"]["scrutin_censure_49_3"], e["PS"]["numero_loi"]) == (
        "promulgue", True, True, "2024-12-04", "VTANR5L17V519", "2025-199")
    assert (e["RJ"]["par_49_3"], e["RJ"]["rejete_par_censure_49_3"]) == (True, False)
    assert (e["CM"]["sort"], e["CM"]["motif_adoption"], e["CM"]["adopte_sur_texte_cmp"]) == (
        "promulgue", None, True)
    assert e["PS"]["adopte_sur_texte_cmp"] is False
    # La dernière décision est lue ligne entière (v6) : publiée sans libellé (TSORTFnull), elle ne
    # prend plus celui de la décision précédente (« considéré comme adopté… »).
    dl = _un(ctx, "etat_dossier", dossier="PS")
    assert (dl["date_derniere_decision"], dl["derniere_conclusion"]) == ("2025-02-17", None)
