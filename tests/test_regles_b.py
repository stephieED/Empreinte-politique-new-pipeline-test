"""Règles du groupe B (textes et scrutins) : R-NATURE-SCRUTIN, R-LIEN-SCRUTIN-DOSSIER, R-ORIGINE,
R-DERNIERE-LECTURE, R-MATIERE, R-ETAPE, R-SORT-FINAL, R-49-3, R-LOIS, R-DEPOT-GOUVERNEMENT.

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
                              r_gouvernements, r_legislatures, r_lien_scrutin_dossier, r_lois,
                              r_matiere, r_nature_scrutin, r_origine, r_sort_final)

EXTRAITS = os.path.join(os.path.dirname(__file__), "extraits")
REGLES = [r_legislatures, r_gouvernements, r_nature_scrutin, r_lien_scrutin_dossier, r_origine,
          r_derniere_lecture, r_matiere, r_etape, r_49_3, r_lois, r_sort_final,
          r_depot_gouvernement]
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
                "R-MATIERE", "R-ETAPE", "R-SORT-FINAL", "R-49-3", "R-LOIS", "R-DEPOT-GOUVERNEMENT"):
        c = b[nom]["couverture"]
        assert c and all(isinstance(n, int) and isinstance(d, int) and n <= d for n, d in c.values()), nom
        assert b[nom]["description"]
