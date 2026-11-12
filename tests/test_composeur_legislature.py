"""Composeur `legislature` (cahier 4.5 ; doc. 1, 1.7) sur de petites tables Z3 écrites à la main.

Les identifiants et dates sont ceux de la XVIIe (collecte du 06/11/2026) ; les effectifs sont
réduits. On vérifie : les fichiers produits, les comptes datés de l'en-tête, les liens, l'ordre
neutre, les `null` gardés, le 49.3 compté comme fait de procédure, la couverture de chaque
section, les faits publiés et les contrôles C2 et C4."""
import gzip
import json
import os

import pyarrow as pa
import pytest

from empreinte_src.composeurs import legislature as comp
from empreinte_src.composition import Ecrivain, composeurs
from empreinte_src.controles import Controles
from empreinte_src.liaison import Contexte, regles

REF = "2026-11-06"
STATUTS = {"complet", "trou_source", "borne_historique", "non_collecte", "panne", "en_cours",
           "relu_aucun", "non_relu", "hors_perimetre"}
AMO = {"prov_point": "an-amo30-l17", "licence": "etalab-2.0"}
DOS = {"prov_point": "an-dossiers-l17", "licence": "etalab-2.0"}
AGE = {"prov_point": "an-agenda-l17", "licence": "etalab-2.0"}
SCR = {"prov_point": "an-scrutins-l17", "licence": "etalab-2.0"}
URL = "https://www.assemblee-nationale.fr/dyn/17/dossiers/"


def vue(ctx, nom, rows):
    cols = list(dict.fromkeys(k for r in rows for k in r))
    arrays = {}
    for c in cols:
        vals = [r.get(c) for r in rows]
        arrays[c] = pa.array(vals, type=pa.string()) if all(v is None for v in vals) else pa.array(vals)
    ctx.con.register(f"_src_{nom}", pa.table(arrays))
    ctx.x(f"CREATE OR REPLACE VIEW {nom} AS SELECT * FROM _src_{nom}")


def gouv(uid, nom, debut, fin):
    return {"organe": uid, "nom": nom, "adresse": nom.lower().replace(" ", "-"), "debut": debut,
            "fin": fin, "en_cours": fin is None, "regle": "R-GOUVERNEMENTS@1", "source_url": None}


def dossier(uid, titre, procedure="Proposition de loi ordinaire", leg="17"):
    return {"uid": uid, "legislature": leg, "titre": titre, "procedure_libelle": procedure,
            "prov_uid": uid, "prov_url": URL + uid, **DOS}


def depot(dossier, texte, date, code="AN1-DEPOT"):
    return {"uid": f"L17-{dossier}-DEP", "dossier": dossier, "type_acte": "DepotInitiative_Type",
            "texte_associe": texte, "date": date, "code": code, **DOS}


def etat(dossier, etape, sort, date_etape, procedure="2", date_sort=None, par_49_3=False,
         adopte_49_3=False, numero_loi=None):
    return {"dossier": dossier, "legislature": 17, "etape_atteinte": etape, "sort": sort,
            "par_49_3": par_49_3, "adopte_par_49_3": adopte_49_3, "date_promulgation":
            date_sort if sort == "promulgue" else None, "numero_loi": numero_loi,
            "date_sort": date_sort, "raison_sort": None if sort != "non_connu" else "aucune_decision_en_seance",
            "date_etape": date_etape, "raison_etape": None, "procedure_code": procedure,
            "titre": f"Titre {dossier}", "url_loi": None, "source_url": URL + dossier,
            "regle": "R-SORT-FINAL@1"}


def matiere(dossier, statut, commission=None, libelle=None):
    return {"dossier": dossier, "statut": statut, "commission": commission,
            "libelle": libelle or {"senat_seulement": "Saisi au Sénat seulement",
                                   "non_etablie": "Matière non établie"}.get(statut),
            "raison": "aucune_saisine_au_fond" if statut == "non_etablie" else None,
            "regle": "R-MATIERE@1"}


@pytest.fixture
def ctx(tmp_path):
    z2, z3 = tmp_path / "z2", tmp_path / "z3"
    z2.mkdir()
    c = Contexte(str(z2), str(z3), date_reference=REF)
    # --- Z2 lue directement (libellés, points d'accès, licences)
    vue(c, "an_acteurs__organe", [
        {"uid": "PO838901", "type_organe": "ASSEMBLEE", "libelle": "Assemblée nationale", "prov_uid": "PO838901", **AMO},
        {"uid": "PO791932", "type_organe": "ASSEMBLEE", "libelle": "Assemblée nationale", "prov_uid": "PO791932", **AMO},
        {"uid": "PO847639", "type_organe": "GOUVERNEMENT", "libelle": "Barnier", "prov_uid": "PO847639", **AMO},
        {"uid": "PO873634", "type_organe": "GOUVERNEMENT", "libelle": "Lecornu II", "prov_uid": "PO873634", **AMO},
        {"uid": "PO845401", "type_organe": "GP", "libelle": "Rassemblement National", "prov_uid": "PO845401", **AMO},
        {"uid": "PO845419", "type_organe": "GP", "libelle": "Socialistes et apparentés", "prov_uid": "PO845419", **AMO},
        {"uid": "PO845520", "type_organe": "GP", "libelle": "À droite", "prov_uid": "PO845520", **AMO},
        {"uid": "PO59051", "type_organe": "COMPER", "libelle": "Commission des lois", "prov_uid": "PO59051", **AMO},
        {"uid": "PO59048", "type_organe": "COMPER", "libelle": "Commission des finances", "prov_uid": "PO59048", **AMO},
    ])
    vue(c, "an_acteurs__mandat", [{"uid": f"PM{i}", "prov_uid": f"PA{i}", **AMO} for i in range(1, 6)])
    vue(c, "an_acteurs__identite_source", [
        {"uid": "PA1", "prenom": "Anne", "nom": "Zola", "nom_alpha": "Zola"},
        {"uid": "PA2", "prenom": "Paul", "nom": "Martin", "nom_alpha": "Martin"},
        {"uid": "PA3", "prenom": "Léa", "nom": "Bernard", "nom_alpha": "Bernard"},
        {"uid": "PA4", "prenom": "Marc", "nom": "Abel", "nom_alpha": "Abel"},
    ])
    vue(c, "an_dossiers__dossier", [
        dossier("D-PLF", "Projet de loi de finances pour 2026", "Projet de loi de finances de l'année"),
        dossier("D-PPL", "Proposition de loi visant à protéger les forêts"),
        dossier("D-SEN", "Proposition de loi adoptée par le Sénat"),
        dossier("D-RAP", "Rapport d'information sur les forêts", "Rapport d'information sans mission"),
        dossier("D-49", "Engagement de la responsabilité du Gouvernement", "Engagement de la responsabilité gouvernementale"),
        dossier("D-OLD", "Proposition de loi ancienne", leg="16"),
    ])
    vue(c, "an_dossiers__acte", [
        depot("D-PLF", "PRJLANR5L17B1906", "2025-10-14"),
        depot("D-PPL", "PIONANR5L17B0100", "2024-10-02"),
        depot("D-SEN", "PIONSNR5L17B0050", "2025-03-01", "SN1-DEPOT"),
        depot("D-OLD", "PIONANR5L16B0001", "2023-01-10"),
    ])
    vue(c, "an_agenda__reunion", [{"uid": "RU1", "prov_uid": "RU1", **AGE},
                                  {"uid": "RU2", "prov_uid": "RU2", **AGE}])
    vue(c, "an_agenda__point_odj", [{"uid": "PT1", **AGE}])
    vue(c, "an_scrutins__scrutin", [{"uid": "VT1", **SCR}])
    # --- sorties de règles (Z3)
    vue(c, "legislature", [
        {"numero": 16, "organe": "PO791932", "debut": "2022-06-22", "fin": "2024-06-09",
         "en_cours": False, "mode_fin": "non_etabli", "source_url": None, "regle": "R-LEGISLATURES@1"},
        {"numero": 17, "organe": "PO838901", "debut": "2024-07-01", "fin": None,
         "en_cours": True, "mode_fin": "en_cours", "source_url": None, "regle": "R-LEGISLATURES@1"}])
    vue(c, "gouvernement", [gouv("PO847639", "Barnier", "2024-09-06", "2024-12-13"),
                            gouv("PO873634", "Lecornu II", "2025-10-11", None),
                            gouv("PO839000", "Attal", "2024-01-09", "2024-09-05")])
    vue(c, "gouvernement_legislature", [
        {"gouvernement": "PO847639", "legislature": 17, "debut": "2024-09-06", "fin": "2024-12-13", "regle": "R-GOUVERNEMENTS@1"},
        {"gouvernement": "PO873634", "legislature": 17, "debut": "2025-10-11", "fin": None, "regle": "R-GOUVERNEMENTS@1"},
        # Attal ne traverse ici que la XVIe : pas de fiche (gouvernements de la XVIIe seulement, pour l'instant).
        {"gouvernement": "PO839000", "legislature": 16, "debut": "2024-01-09", "fin": "2024-06-09", "regle": "R-GOUVERNEMENTS@1"}])
    dep = lambda a, m, debut, fin=None, s_du=None, s_au=None: {
        "acteur": a, "legislature": 17, "mandat": m, "debut": debut, "fin": fin,
        "suspendu_du": s_du, "suspendu_au": s_au, "regle": "R-DEPUTES@1"}
    vue(c, "depute", [dep("PA1", "PM1", "2024-07-08"), dep("PA2", "PM2", "2024-07-08"),
                      dep("PA3", "PM3", "2024-07-08"), dep("PA4", "PM4", "2024-07-08"),
                      dep("PA5", "PM5", "2024-07-08", "2025-11-10", "2025-11-11")])
    hem = lambda a, m, siege, groupe, ratt: {
        "legislature": 17, "date": REF, "acteur": a, "siege": siege, "groupe": groupe,
        "rattachement": ratt, "raison_rattachement": None,
        "raison_siege": None if siege else "siège non connu", "mandat": m,
        "date_origine": "date_reference", "source_url": None, "prov_uid": a, "regle": "R-HEMICYCLE@1"}
    vue(c, "hemicycle", [hem("PA2", "PM2", 12, "PO845419", "groupe"),
                         hem("PA1", "PM1", 300, "PO845401", "groupe"),
                         hem("PA3", "PM3", 45, "PO845401", "groupe"),
                         hem("PA4", "PM4", None, None, "non_inscrit")])
    grp = lambda o, sigle, debut, fin: {"organe": o, "legislature": 17, "sigle": sigle,
                                        "libelle": sigle, "debut": debut, "fin": fin,
                                        "position_declaree": "non_declaree", "regle": "R-APPARTENANCE@1"}
    vue(c, "groupe", [grp("PO845401", "RN", "2024-07-18", None), grp("PO845419", "SOC", "2024-07-18", None),
                      grp("PO845520", "AD", "2024-07-18", "2024-09-11"),
                      {**grp("PO800484", "RE", "2022-06-28", "2024-06-09"), "legislature": 16}])
    vue(c, "effectif_groupe", [
        {"groupe": "PO845401", "date": REF, "effectif": 2, "legislature": 17, "regle": "R-HEMICYCLE@1"},
        {"groupe": "PO845419", "date": REF, "effectif": 1, "legislature": 17, "regle": "R-HEMICYCLE@1"},
        {"groupe": "PO845520", "date": "2024-09-11", "effectif": 3, "legislature": 17, "regle": "R-HEMICYCLE@1"},
        {"groupe": "PO800484", "date": "2024-06-09", "effectif": 169, "legislature": 16, "regle": "R-HEMICYCLE@1"}])
    vue(c, "loi", [
        {"numero_loi": "2026-103", "dossier": "D-PLF", "date_promulgation": "2026-02-19", "legislature": 17, "regle": "R-LOIS@1"},
        {"numero_loi": "2024-1", "dossier": "D-OLD", "date_promulgation": "2024-11-10", "legislature": 17, "regle": "R-LOIS@1"},
        {"numero_loi": "2023-9", "dossier": "D-OLD", "date_promulgation": "2023-03-01", "legislature": 16, "regle": "R-LOIS@1"}])
    sn = lambda uid, date, solennel, moc, sort, nature: {
        "scrutin": uid, "legislature": 17, "date": date, "solennel": solennel, "motion_censure": moc,
        "sort": sort, "nature": nature, "regle": "R-NATURE-SCRUTIN@1"}
    vue(c, "scrutin_nature", [sn("VT1", "2024-12-04", False, True, "adopte", "motion_censure"),
                              sn("VT2", "2025-01-16", False, True, "rejete", "motion_censure"),
                              sn("VT3", "2025-10-14", True, False, "adopte", "ensemble"),
                              sn("VT4", "2025-10-15", False, False, "rejete", "amendement")])
    vue(c, "engagement_49_3", [
        {"dossier": "D-PLF", "date": "2026-01-20", "acte": "L17-VD229941", "procedure_code": "3", "regle": "R-49-3@1"},
        {"dossier": "D-49", "date": "2026-01-20", "acte": "L17-VD229941", "procedure_code": "13", "regle": "R-49-3@1"}])
    vue(c, "etat_dossier", [
        etat("D-PLF", "promulgue", "promulgue", "2026-02-19", "3", "2026-02-19", True, True, "2026-103"),
        etat("D-PPL", "depot", "non_connu", "2024-10-02"),
        etat("D-SEN", "examen_commission", "non_connu", "2025-04-01"),
        etat("D-OLD", "promulgue", "promulgue", "2024-11-10", "2", "2024-11-10", numero_loi="2024-1"),
        etat("D-RAP", "non_etablie", "non_connu", None, "21"),
        etat("D-49", "seance", "non_connu", "2026-01-20", "13", par_49_3=True)])
    vue(c, "matiere", [matiere("D-PLF", "assemblee", "PO59048", "Commission des finances"),
                       matiere("D-PPL", "assemblee", "PO59051", "Commission des lois"),
                       matiere("D-SEN", "senat_seulement"), matiere("D-OLD", "non_etablie"),
                       matiere("D-RAP", "non_etablie"), matiere("D-49", "non_etablie")])
    vue(c, "etape_dossier", [{"dossier": "D-PLF", "legislature": 17, "regle": "R-ETAPE@1"}])
    odj = lambda date, ru, rang, objet, dossier, statut="confirmee": {
        "date": date, "reunion": ru, "rang": rang, "objet": objet, "dossier": dossier,
        "dossiers": [dossier] if dossier else [], "statut_seance": statut, "statut_point": "confirme",
        "lien_dossier": "lie" if dossier else "non_lie", "commission": None,
        "commission_libelle": None, "matiere_statut": None, "legislature": 17, "point": f"{ru}PT{rang}",
        "type_point": "Discussion", "compte_rendu": None, "source_url": None, "regle": "R-ORDRE-DU-JOUR@1"}
    vue(c, "ordre_du_jour", [odj("2025-10-14", "RU1", 1, "Questions au Gouvernement", None),
                             odj("2025-10-14", "RU1", 2, "Projet de loi de finances pour 2026", "D-PLF"),
                             odj("2026-11-20", "RU2", 1, "Proposition de loi forêts", "D-PPL")])
    return c


def composer(ctx, tmp_path, numero=17):
    ecr = Ecrivain(str(tmp_path / "site"), "essai")
    comp.composer(ctx, ecr)
    man = ecr.clore()
    racine = os.path.join(str(tmp_path / "site"), "donnees", "essai")

    def lire(nom):
        with gzip.open(os.path.join(racine, "legislatures", str(numero), nom + ".json.gz")) as f:
            return json.load(f)
    return ecr, man, racine, lire


def lignes(section):
    return [dict(zip(section["colonnes"], l)) for l in section["lignes"]]


def test_contrat_et_dependances():
    assert comp.NOM == "legislature" and comp.VERSION >= 1
    assert comp in composeurs()
    noms = {r.NOM for r in regles()}
    assert set(comp.DEPEND) <= noms


def test_fichiers_et_entete(ctx, tmp_path):
    ecr, man, racine, lire = composer(ctx, tmp_path)
    assert [f["fiche"] for f in man["fiches"]] == ["legislature/16", "legislature/17"]   # XIVe à XVIIe
    fichiers = {k.split("/")[-1] for k in man["fichiers"] if k.startswith("legislatures/17/")}
    assert fichiers == {"fiche.json.gz", "hemicycle.json.gz", "groupes.json.gz",
                        "ordre-du-jour-2025.json.gz", "ordre-du-jour-2026.json.gz",
                        "textes.json.gz", "textes-deposes-2024.json.gz", "commissions.json.gz"}
    f = lire("fiche")
    assert f["titre"] == "XVIIe législature"
    assert f["legislature"]["mode_fin"] == "en_cours" and f["au"] == REF
    g = lignes(f["gouvernements"])
    assert [x["lien"] for x in g] == ["gouvernement/barnier", "gouvernement/lecornu-ii"]
    assert g[0]["duree_jours"] == 98 and g[1]["fin"] is None and g[1]["duree_jours"] == 391
    c = {x["famille"]: x for x in f["compteurs"]}
    assert all(x["au"] == REF and x["regle"] for x in c.values())
    assert c["gouvernements"]["valeur"] == 2
    assert c["deputes_en_fonction"]["valeur"] == 4          # PA5 suspendu : pas en fonction
    assert c["deputes_ayant_siege"]["valeur"] == 5
    assert c["lois"]["valeur"] == 2                         # promulguées dans la XVIIe seulement
    assert c["lois"]["par_legislature_du_dossier"] == [{"legislature": 16, "lois": 1},
                                                       {"legislature": 17, "lois": 1}]
    assert c["votes_solennels"]["valeur"] == 1
    assert c["motions_censure"]["valeur"] == 2 and c["motions_censure"]["adoptees"] == 1
    # 49.3 : le texte adopté compte, pas le dossier « engagement » (procédure 13) ; un acte.
    assert c["textes_adoptes_49_3"]["valeur"] == 1
    assert c["textes_adoptes_49_3"]["engagements_distincts"] == 1
    assert {l["sujet"] for l in f["limites"]} >= {"senat", "commissions", "nuage_de_mots",
                                                   "place_mediane"}
    assert "hemicycle_legislature_close" not in {l["sujet"] for l in f["limites"]}
    assert f["licences"] == ["etalab-2.0"]


def test_qui_siege(ctx, tmp_path):
    _, _, _, lire = composer(ctx, tmp_path)
    h = lire("hemicycle")
    assert h["ordre"] == "hemicycle"
    ls = lignes(h)
    assert [l["siege"] for l in ls] == [12, 45, 300, None]      # ordre de l'hémicycle
    assert ls[-1]["rattachement"] == "non_inscrit" and ls[-1]["groupe"] is None
    assert all(l["licence"] == "etalab-2.0" and l["source_point"] == "an-amo30-l17" for l in ls)
    g = lire("groupes")
    gs = lignes(g)
    assert [x["sigle"] for x in gs] == ["AD", "RN", "SOC", "NI"]    # alphabétique, NI à part
    ad = gs[0]
    assert ad["effectif"] is None and ad["effectif_a_la_fin"] == 3  # groupe clos : null, pas 0
    assert {x["position_declaree"] for x in gs[:3]} == {"non_declaree"}
    assert gs[1]["effectif"] == 2 and gs[3]["effectif"] == 1
    assert g["couverture"]["statut"] == "complet"


def test_ordre_du_jour_par_annee(ctx, tmp_path):
    _, _, _, lire = composer(ctx, tmp_path)
    a = lignes(lire("ordre-du-jour-2025"))
    assert [l["rang"] for l in a] == [1, 2]
    assert a[1]["titre_dossier"] == "Projet de loi de finances pour 2026"
    assert a[0]["lien_dossier"] == "non_lie" and a[0]["dossier"] is None
    b = lire("ordre-du-jour-2026")
    assert lignes(b)[0]["a_venir"] is True
    assert b["couverture"]["numerateur"] == 1 and b["couverture"]["denominateur"] == 1


def test_textes_et_commissions(ctx, tmp_path):
    _, _, _, lire = composer(ctx, tmp_path)
    t = lire("textes")
    ls = {l["dossier"]: l for l in lignes(t)}
    # Sans texte déposé (rapport, engagement) : écartés et déclarés.
    assert set(ls) == {"D-PLF", "D-SEN", "D-OLD"}
    assert {e["procedure_libelle"] for e in t["dossiers_ecartes"]} == {
        "Rapport d'information sans mission", "Engagement de la responsabilité gouvernementale"}
    assert ls["D-PLF"]["initiateur"] == "gouvernement" and ls["D-PLF"]["adopte_par_49_3"] is True
    assert ls["D-SEN"]["initiateur"] == "senateurs"
    assert ls["D-SEN"]["commission_libelle"] == "Saisi au Sénat seulement"
    assert ls["D-OLD"]["commission"] is None and ls["D-OLD"]["matiere_statut"] == "non_etablie"
    assert ls["D-OLD"]["sort_pendant_la_legislature"] is True
    d = lignes(lire("textes-deposes-2024"))
    assert [x["dossier"] for x in d] == ["D-PPL"] and d[0]["initiateur"] == "deputes"
    c = lignes(lire("commissions"))
    assert {(x["commission_libelle"], x["etape"]): x["dossiers"] for x in c} == {
        ("Commission des finances", "promulgue"): 1, ("Commission des lois", "depot"): 1,
        ("Saisi au Sénat seulement", "examen_commission"): 1,
        ("Matière non établie", "promulgue"): 1}
    assert not any(k.startswith(("ratio", "taux")) for k in lire("commissions")["colonnes"])


def test_couverture_faits_et_controles(ctx, tmp_path):
    ecr, man, racine, lire = composer(ctx, tmp_path)
    f = lire("fiche")
    for nom in f["sections"]:
        cv = lire(nom)["couverture"]
        assert cv["statut"] in STATUTS and cv["detail"] and cv["points_acces"], nom
    assert {c["section"] for c in f["couverture"]} == set(f["sections"])
    n_lignes = sum(s["lignes"] for s in f["sections"].values())
    entete = len(lignes(f["gouvernements"])) + len(f["compteurs"])
    assert len([x for x in ecr.faits if x["fiche"] == "legislature/17"]) == n_lignes + entete
    assert {x["fiche"] for x in ecr.faits} == {"legislature/16", "legislature/17"}
    ctrl = Controles(racine)
    ctrl.c4_interdits()
    ctrl.c2_liens({"legislature/17", "gouvernement/barnier", "gouvernement/lecornu-ii"})
    assert ctrl.anomalies == []
    ctrl = Controles(racine)
    ctrl.c2_liens({"legislature/17"})                         # gouvernements non publiés : bloque
    assert ctrl.anomalies and ctrl.anomalies[0]["controle"] == "C2"


def test_sortie_de_regle_absente(ctx, tmp_path):
    ctx.x("DROP VIEW hemicycle")
    ctx.x("DROP VIEW ordre_du_jour")
    _, man, _, lire = composer(ctx, tmp_path)
    h = lire("hemicycle")
    assert h["lignes"] == [] and h["couverture"]["statut"] == "non_relu"
    assert "hemicycle" in h["couverture"]["detail"]
    assert lire("ordre-du-jour")["couverture"]["statut"] == "non_relu"
    assert lire("groupes")["couverture"]["statut"] == "non_relu"


def test_legislature_close_sans_hemicycle(ctx, tmp_path):
    """XVIe, close : comptes à sa fin ; l'hémicycle n'est pas publié pour une législature close,
    donc ni sièges ni écart effectif/sièges, et la limite le dit. Chaque groupe renvoie à sa lignée
    quand elle est publiée."""
    ecr, man, racine, lire = composer(ctx, tmp_path, numero=16)
    f = lire("fiche")
    assert f["titre"] == "XVIe législature" and f["au"] == "2024-06-09"
    assert "hemicycle_legislature_close" in {l["sujet"] for l in f["limites"]}
    assert lire("hemicycle")["couverture"]["statut"] == "borne_historique"
    # Aucune séance de la XVIe dans l'agenda du jeu d'essai : un trou de la source, pas « 0, complet ».
    odj = lire("ordre-du-jour-vide")["couverture"]
    assert odj["statut"] == "trou_source" and odj["numerateur"] is None
    g = lignes(f["gouvernements"])
    assert [(x["nom"], x["lien"], x["raison_lien"]) for x in g] == [("Attal", None, "gouvernement sans fiche publiée")]
    g = lignes(lire("groupes"))
    assert [(x["sigle"], x["effectif"], x["au"], x["sieges_dans_l_hemicycle"]) for x in g] == \
        [("RE", 169, "2024-06-09", None)]                    # effectif au dernier jour de la législature
    cv = lire("groupes")["couverture"]
    assert cv["statut"] == "complet" and "hémicycle de cette législature close" in cv["detail"]
    assert all(x["fiche"] != "legislature/16" or x["date"] is None or x["date"] <= "2024-06-09"
               for x in ecr.faits)
