"""Contrôles C3 (données laissées de côté), C7 (personne attendue écartée en silence), règle
R-PERIMETRE, et avertissements A1 à A8 (doc. 2, 2.8), sur de petites tables à la forme exacte des
sorties des règles et de l'export des faits publiés."""
import json
import os

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

from empreinte_src.composition import IDS
from empreinte_src.controles import Controles
from empreinte_src.liaison import Contexte, ordonner, relier
from empreinte_src.regles import r_perimetre
from empreinte_src.verification import lire_page

COLS_FP = ["fiche", "section", "type_fait"] + [f"id_{k}" for k in IDS] + ["valeur", "date", "source_url"]


def _fait(fiche, section, valeur="{}", **ids):
    r = {c: None for c in COLS_FP}
    r.update({"fiche": fiche, "section": section, "type_fait": "t", "valeur": valeur})
    r.update({f"id_{k}": v for k, v in ids.items()})
    return r


TABLES = {
    "lignee": [{"lignee": "lig:000001", "adresse": "soc", "publiee": True}],
    "lignee_maillon": [{"lignee": "lig:000001", "maillon": "grp:17:PO17S", "legislature": 17, "affiche": True,
                        "organes": ["PO17S"]}],
    "appartenance": [{"acteur": "PA1", "groupe": "PO17S", "legislature": 17, "debut": "2024-07-18", "fin": None},
                     {"acteur": "PA2", "groupe": "PO17S", "legislature": 17, "debut": "2024-07-18", "fin": "2025-01-01"}],
    "candidat": [{"per": "per:000001", "nom": "Alice Martin", "acteur": "PA1", "adresse": "alice-martin",
                  "publie": True, "statut": "declaree", "raison_non_publie": None},
                 {"per": "per:000002", "nom": "Jean Homonyme", "acteur": None, "adresse": None, "publie": False,
                  "statut": "declaree", "raison_non_publie": "adresse non établie"},
                 {"per": "per:000003", "nom": "Paul Parti", "acteur": None, "adresse": "paul-parti", "publie": False,
                  "statut": "retiree", "raison_non_publie": "candidature retirée"},
                 {"per": "per:000004", "nom": "Luc Sorti", "acteur": None, "adresse": "luc-sorti", "publie": False,
                  "statut": "non_listee", "raison_non_publie": "n'est plus dans la liste des candidats"}],
    "gouvernement": [{"organe": "PO-G", "nom": "Bayrou", "adresse": "bayrou"}],
    "gouvernement_legislature": [{"gouvernement": "PO-G", "legislature": 17}],
    "membre_gouvernement": [{"gouvernement": "PO-G", "acteur": "PA7"}],
    "depute": [{"acteur": "PA1", "legislature": 17}, {"acteur": "PA9", "legislature": 17}],
    "an_scrutins__scrutin": [{"uid": "VT1", "legislature": "17", "numero": 1, "date": "2025-01-30", "nombre_votants": 3, "pour": 2,
                              "contre": 1, "abstentions": 0},
                             {"uid": "VT2", "legislature": "17", "numero": 2, "date": "2025-02-01", "nombre_votants": 1, "pour": 1,
                              "contre": 0, "abstentions": 0}],
    # VT1 (30/01/2025) : PA2 a quitté le groupe le 01/01/2025, le groupe compte 1 membre.
    "an_scrutins__decompte_groupe": [{"scrutin": "VT1", "organe": "PO17S", "nombre_membres": 1},
                                     {"scrutin": "VT2", "organe": "PO0", "nombre_membres": None}],
    "an_scrutins__position_vote": [{"scrutin": "VT1", "acteur": "PA1", "position": "pour"}],
    "amendement_canonique": [{"amendement": "AM1", "acteur": "PA1", "date_depot": "2025-01-20", "alias": ["AM1B"]},
                             {"amendement": "AM2", "acteur": "PA2", "date_depot": "2025-03-01", "alias": None},
                             {"amendement": "AM3", "acteur": "PA2", "date_depot": "2024-12-01", "alias": None}],
    "intervention_attribuee": [{"compte_rendu": "CR1", "id_syceron": "1", "acteur": "PA1", "date": "2025-01-30"},
                               {"compte_rendu": "CR1", "id_syceron": "2", "acteur": None, "date": "2025-01-30"},
                               {"compte_rendu": "CR1", "id_syceron": "3", "acteur": "PA1", "date": "2025-01-30"}],
    # CR1#3 : interruption notée sans texte par la source, rien à servir.
    "an_comptes_rendus__intervention": [{"compte_rendu": "CR1", "id_syceron": "1", "texte": "Bonjour."},
                                        {"compte_rendu": "CR1", "id_syceron": "2", "texte": "(Applaudissements.)"},
                                        {"compte_rendu": "CR1", "id_syceron": "3", "texte": None}],
    "parole_personne": [{"acteur": "PA1", "compte_rendu": "CR1", "id_syceron": "1", "date": "2025-01-30"}],
    "mandat_ouvert_organe_clos": [{"mandat": "PM9", "acteur": "PA7", "organe": "PO-G", "organe_fin": "2025-09-09"}],
    "legislature": [{"numero": 17, "debut": "2024-07-18", "fin": None}],
    "filiation": [{"maillon_avant": "grp:16:X", "maillon_apres": "grp:17:PO17S", "verdict": "a_trancher"}],
}
FICHES = {"lignee/soc", "candidat/alice-martin", "gouvernement/bayrou", "legislature/17"}
FAITS = [
    _fait("lignee/soc", "membres", acteur="PA1"), _fait("lignee/soc", "membres", acteur="PA2"),
    _fait("gouvernement/bayrou", "composition", acteur="PA7"),
    _fait("lignee/soc", "votes-17", scrutin="VT1"),
    _fait("lignee/soc", "amendements-2025", amendement="AM1"),
    # AM3 (PA2 membre au dépôt) n'est pas servi : C3 doit le voir.
    _fait("lignee/soc", "paroles-textes-2025-s1", compte_rendu="CR1", autre="1", acteur="PA1"),
]


def _con(tmp_path, tables=TABLES, faits=FAITS):
    con = duckdb.connect()
    for n, l in tables.items():
        con.register(n, pa.Table.from_pylist(l))
    p = tmp_path / "fp.parquet"
    pq.write_table(pa.Table.from_pylist(faits, schema=pa.schema([(c, pa.string()) for c in COLS_FP])), p)
    return con, str(p)


def _ctrl(tmp_path, tables=TABLES, faits=FAITS, fiches=FICHES, levees=None, manifeste=None):
    con, p = _con(tmp_path, tables, faits)
    # Population : la règle R-PERIMETRE elle-même, appliquée sur ces tables.
    ctx = Contexte(str(tmp_path / "z2"), str(tmp_path / "z3"))
    for n, l in tables.items():
        ctx.con.register(n, pa.Table.from_pylist(l))
    relier(ctx, ordonner([_faux(r) for r in r_perimetre.DEPEND] + [r_perimetre]))
    con.register("population", pq.read_table(ctx.sorties["population"]))
    c = Controles(str(tmp_path), levees=levees)
    c.preparer(con, p, fiches, manifeste or [])
    return c


def _faux(nom):
    import types
    return types.SimpleNamespace(NOM=nom, VERSION=0, DEPEND=(), SORTIES=(), appliquer=lambda ctx: {})


def _an(c, code):
    return [a for a in c.anomalies if a["controle"] == code]


def test_perimetre_populations_et_raisons(tmp_path):
    c = _ctrl(tmp_path)
    p = {(r[0], r[1] or r[2]): r for r in c.con.execute(
        "SELECT population, per, acteur, fiche_attendue, raison_sortie FROM population").fetchall()}
    assert p[("candidat", "per:000001")][3] == "candidat/alice-martin"
    assert p[("candidat", "per:000003")][4] == "candidature_retiree_a_la_source"
    assert p[("candidat", "per:000002")][4] is None                    # adresse non établie : pas une sortie
    assert p[("candidat", "per:000004")][4] == "absent_de_la_liste_des_candidats"
    assert p[("membre_groupe", "PA2")][3] == "lignee/soc"
    assert p[("membre_gouvernement", "PA7")][3] == "gouvernement/bayrou"
    assert p[("depute_ni", "PA9")][3] is None


def test_c3_bilan_par_famille_et_objet_attendu_non_servi(tmp_path):
    c = _ctrl(tmp_path)
    b = {x["famille"]: x for x in c.c3_laisses_de_cote()}
    assert b["scrutins"]["ecartes"] == {"aucun_decompte_d_un_groupe_avec_fiche": 1}
    assert b["prises_de_parole"]["ecartes"] == {"orateur_non_attribue": 1, "paragraphe_sans_texte": 1}
    # AM2 : déposé après le départ de PA2 → écarté avec raison ; AM3 : PA2 membre, non servi → bloque.
    assert b["amendements"]["ecartes"] == {"auteur_hors_groupe_a_la_date": 1}
    assert b["amendements"]["exemples"] == ["AM3"]
    assert b["questions"]["statut"] == "non_evalue"
    a = _an(c, "C3")
    assert a and a[0]["bloquant"] and a[0]["exemples"] == ["amendements: AM3"]


def test_c7_personne_absente_nommee(tmp_path):
    faits = [f for f in FAITS if not (f["section"] == "membres" and f["id_acteur"] == "PA2")]
    c = _ctrl(tmp_path, faits=faits)
    c.c7_personnes()
    a = _an(c, "C7")[0]
    assert a["bloquant"]
    assert a["exemples"] == ["candidat per:000002 Jean Homonyme → (aucune adresse) (adresse non établie)",
                             "membre_groupe PA2 → lignee/soc"]
    # Une décision `perimetre` sort la personne avec sa raison.
    t = dict(TABLES, decision_perimetre=[{"personne": "per:000002", "population": "candidat", "motif": "homonyme",
                                         "fichier": "perimetre/jh.yaml"}])
    c = _ctrl(tmp_path, tables=t)
    c.c7_personnes()
    assert not _an(c, "C7")


def test_avertissements_sans_bloquer(tmp_path):
    man = [{"fiche": "candidat/alice-martin", "type": "candidat", "sections": {"questions": {"lignes": 0}}},
           {"fiche": "candidat/bob", "type": "candidat", "sections": {"questions": {"lignes": 0}}},
           {"fiche": "lignee/soc", "type": "lignee", "sections": {"amendements-2025-1": {"lignes": 1}}}]
    faits = FAITS + [_fait("lignee/soc", "amendements-2025", amendement="AM1B"),
                     _fait("lignee/soc", "votes-17", scrutin="VT1")]          # même ligne deux fois
    c = _ctrl(tmp_path, faits=faits, manifeste=man,
              levees=[{"empreinte": "C1:0000", "fichier": "levee_controle/vieille.yaml"}])
    c.a1_hors_modele([{"objet": "candidat/bob", "motif": "test", "fichier": "fiche_hors_modele/b.yaml"}])
    c.a3_totaux()
    c.a4_double_affichage()
    c.a5_famille_a_zero()
    c.a6_couverture()
    c.a8_mandats_ouverts()
    c.a7_non_resolues({"filiation": [{"avant": "grp:15:Z", "apres": "grp:16:Z", "fichier": "filiation/z.yaml"}]})
    codes = {a["controle"] for a in c.anomalies}
    assert codes == {"A1", "A4", "A5", "A6", "A7", "A8"}          # A3 : effectifs concordants
    assert not any(a["bloquant"] for a in c.anomalies) and c.bilan()["publication_autorisee"]
    a4 = _an(c, "A4")[0]["exemples"]
    assert "lignee/soc / votes-17 : 1 lignes identiques" in a4
    assert "amendement AM1B servi alors qu'il est une copie de AM1" in a4
    assert _an(c, "A5")[0]["exemples"] == ["candidat / questions : vide sur les 2 fiches"]
    a6 = _an(c, "A6")[0]["exemples"]
    # Un décompte, jamais de nom : PA2 (aucune parole servie) n'est pas nommé.
    # Sans colonne `orateur_source` (table de test réduite), un membre sans parole servie reste signalé.
    assert ("1 membres de groupes de la XVIIe législature sur 2 ont des paroles à la source pendant leur "
            "appartenance au groupe, mais aucune n'est servie") in a6
    assert not any("PA2" in x for x in a6)
    a7 = _an(c, "A7")[0]["exemples"]
    assert "filiation à trancher : grp:16:X → grp:17:PO17S" in a7
    assert "décision filiation/z.yaml sans objet : grp:15:Z → grp:16:Z" in a7
    assert "levée levee_controle/vieille.yaml sans objet cette nuit : C1:0000" in a7
    assert _an(c, "A8")[0]["exemples"] == ["PM9 (PA7) dans PO-G, clos le 2025-09-09"]


def _fiche_servie(racine, fiche, couverture):
    import gzip
    import json
    t, _, adresse = fiche.partition("/")
    d = os.path.join(racine, f"{t}s", adresse)
    os.makedirs(d, exist_ok=True)
    with gzip.open(os.path.join(d, "fiche.json.gz"), "wt", encoding="utf-8") as f:
        json.dump({"fiche": fiche, "couverture": couverture}, f)


def test_a5_section_vide_expliquee_par_sa_couverture(tmp_path):
    """Issue #10 (14/11/2026) : une section vide partout dont chaque fiche dit pourquoi
    (« non collecté » : les budgets) est comptée, pas signalée ; sans raison déclarée, elle l'est."""
    man = [{"fiche": f"gouvernement/{g}", "type": "gouvernement",
            "sections": {"budgets": {"lignes": 0}, "textes-2025-1": {"lignes": 0}}} for g in ("a", "b")]
    man[0]["sections"]["paroles"] = man[1]["sections"]["paroles"] = {"lignes": 0}
    for g in ("a", "b"):
        _fiche_servie(str(tmp_path), f"gouvernement/{g}",
                      [{"section": "budgets", "statut": "non_collecte"}, {"section": "textes-2025-1", "statut": "complet"},
                       {"section": "paroles", "statut": "relu_aucun"}])
    c = _ctrl(tmp_path, manifeste=man)
    c.a5_famille_a_zero()
    # « Relu, rien trouvé » sur toutes les fiches est suspect : signalé (essai du 14/11/2026).
    assert _an(c, "A5")[0]["exemples"] == ["gouvernement / paroles : vide sur les 2 fiches",
                                           "gouvernement / textes : vide sur les 2 fiches"]
    assert c.bilan_a5["expliquees"] == ["gouvernement / budgets : non_collecte"]
    assert c.bilan()["expliques"]["a5"]["expliquees"] == ["gouvernement / budgets : non_collecte"]


def _paroles_a_la_source(lignes):
    t = dict(TABLES)
    t["intervention_attribuee"] = [dict(r, preside=r.get("preside", False)) for r in lignes]
    return t


def test_a6_membre_sans_paragraphe_a_la_source_explique(tmp_path):
    """Issue #11 (14/11/2026) : PA2 n'a aucun paragraphe à la source pendant son appartenance (seulement
    une présidence de séance) : compté, pas signalé. Les candidats sans fiche, tous avec une raison
    établie, sont comptés."""
    t = _paroles_a_la_source([
        {"compte_rendu": "CR1", "id_syceron": "1", "acteur": "PA1", "orateur_source": "PA1", "date": "2025-01-30"},
        {"compte_rendu": "CR2", "id_syceron": "9", "acteur": "PA2", "orateur_source": "PA2", "date": "2024-12-01",
         "preside": True}])
    c = _ctrl(tmp_path, tables=t)
    c.a6_couverture()
    assert _an(c, "A6") == []
    assert c.bilan_a6["membres_sans_parole_servie_17"] == {
        "sans_parole_servie": 1, "sans_paragraphe_a_la_source": 1, "membres": 2}
    assert c.bilan_a6["candidats_sans_fiche"] == {"absent_de_la_liste_des_candidats": 1,
                                                 "candidature_retiree_a_la_source": 1}


def test_a6_paroles_a_la_source_non_servies_signalees(tmp_path):
    """PA2 a un paragraphe sous son identifiant pendant son appartenance, mais rien n'est servi (nom
    discordant, par exemple) : signalé, en décompte, sans nom. Une parole d'après son départ du groupe
    (le 01/01/2025) n'aurait pas compté."""
    t = _paroles_a_la_source([
        {"compte_rendu": "CR1", "id_syceron": "1", "acteur": "PA1", "orateur_source": "PA1", "date": "2025-01-30"},
        {"compte_rendu": "CR2", "id_syceron": "9", "acteur": None, "orateur_source": "PA2", "date": "2024-12-01"}])
    c = _ctrl(tmp_path, tables=t)
    c.a6_couverture()
    assert _an(c, "A6")[0]["exemples"] == [
        "1 membres de groupes de la XVIIe législature sur 2 ont des paroles à la source pendant leur "
        "appartenance au groupe, mais aucune n'est servie"]
    t = _paroles_a_la_source([
        {"compte_rendu": "CR2", "id_syceron": "9", "acteur": None, "orateur_source": "PA2", "date": "2025-03-01"}])
    c = _ctrl(tmp_path, tables=t)
    c.a6_couverture()
    assert _an(c, "A6") == []


def test_a3_effectif_different_du_decompte_publie(tmp_path):
    t = dict(TABLES, an_scrutins__decompte_groupe=[{"scrutin": "VT1", "organe": "PO17S", "nombre_membres": 5}])
    c = _ctrl(tmp_path, tables=t)
    c.a3_totaux()
    assert _an(c, "A3")[0]["exemples"] == ["VT1 PO17S : publié 5, nos appartenances 1"]   # PO0 non comparé


def test_a3_ecarts_expliques_comptes_sans_etre_nommes(tmp_path):
    """Issue #9 (13/11/2026) : un écart de transition (PA2 sort du groupe le 01/01/2025, scrutin du
    03/01) ou sur un organe hors de ses dates n'est plus nommé, seulement compté ; un écart que rien
    n'explique l'est toujours."""
    scrutins = TABLES["an_scrutins__scrutin"] + [
        {"uid": "VT3", "legislature": "17", "numero": 3, "date": "2025-01-03"},
        {"uid": "VT4", "legislature": "17", "numero": 4, "date": "2026-03-01"},
        {"uid": "VT5", "legislature": "17", "numero": 5, "date": "2025-01-04"}]
    decomptes = [{"scrutin": "VT3", "organe": "PO17S", "nombre_membres": 2},     # transition : 1 sortie le 01/01
                 {"scrutin": "VT5", "organe": "PO17S", "nombre_membres": 4},     # 3 de plus : 1 seul changement
                 {"scrutin": "VT4", "organe": "PO17S", "nombre_membres": 9}]     # après la fin de l'organe
    t = dict(TABLES, an_scrutins__scrutin=scrutins, an_scrutins__decompte_groupe=decomptes,
             groupe=[{"organe": "PO17S", "debut": "2024-07-18", "fin": "2026-01-31"}])
    c = _ctrl(tmp_path, tables=t)
    c.a3_totaux()
    a3 = _an(c, "A3")[0]
    assert a3["exemples"] == ["VT5 PO17S : publié 4, nos appartenances 1"]
    assert a3["detail"] == {"decomptes_compares": 3, "ecarts": 3, "expliques_transition": 1,
                            "expliques_organe_hors_dates": 1, "inexpliques": 1}


def test_a3_tous_expliques_pas_d_avertissement(tmp_path):
    scrutins = TABLES["an_scrutins__scrutin"] + [{"uid": "VT3", "legislature": "17", "numero": 3, "date": "2025-01-03"}]
    t = dict(TABLES, an_scrutins__scrutin=scrutins,
             an_scrutins__decompte_groupe=[{"scrutin": "VT3", "organe": "PO17S", "nombre_membres": 2}])
    c = _ctrl(tmp_path, tables=t)
    c.a3_totaux()
    assert _an(c, "A3") == [] and c.bilan_a3["expliques_transition"] == 1


def test_a3_lois_contre_le_journal_officiel(tmp_path):
    """Issue #63 (décision du 15/11/2026) : les lois servies (Assemblée) contre celles du JO. Une loi
    du JO absente de l'Assemblée est expliquée si R-LOI-DOSSIER la relie, ou si elle est sans
    travaux préparatoires et antérieure à la première loi que le JO publie avec les siens ; toute
    autre est nommée, comme une loi de l'Assemblée absente du JO."""
    loi = lambda n, d, l: {"numero_loi": n, "date_promulgation": d, "legislature": l, "dossier": "D" + n}
    acte = lambda n, d, nature="LOI": {"uid": "jorf:" + n, "nature": nature, "numero": n, "date_signature": d}
    lien = lambda n, dossier=None, raison=None: {"numero_loi": n, "dossier": dossier, "raison": raison}
    t = dict(TABLES,
             legislature=[{"numero": 14, "debut": "2012-06-20", "fin": "2017-06-20"},
                          {"numero": 15, "debut": "2017-06-21", "fin": "2022-06-21"}],
             loi=[loi("2016-1", "2016-03-01", 14), loi("2017-9", "2017-01-01", 14), loi("2018-9", "2018-02-01", 15)],
             jo_actes__acte_reglementaire=[
                 acte("2016-1", "2016-03-01"), acte("2018-9", "2018-02-01"),
                 acte("2013-5", "2013-04-01"),                       # avant les travaux au JO : expliquée
                 acte("2016-8", "2016-06-01"),                       # sans travaux, mais après : nommée
                 acte("2016-7", "2016-05-01"),                       # aucun document : nommée
                 acte("2018-3", "2018-03-01"),                       # reliée par le JO : expliquée
                 acte("2018-4", "2018-04-01", "LOI_ORGANIQUE"),      # nommée
                 acte("2018-5", "2018-05-01", "DECRET")],            # pas une loi
             loi_dossier_jo=[lien("2016-1", "D2016-1"), lien("2018-9", "D2018-9"),
                             lien("2013-5", raison="pas_de_travaux_preparatoires"),
                             lien("2016-8", raison="pas_de_travaux_preparatoires"),
                             lien("2016-7", raison="aucun_document"), lien("2018-3", "D3"),
                             lien("2018-4", raison="aucun_document")])
    c = _ctrl(tmp_path, tables=t)
    c.a3_totaux()
    lois = [a for a in _an(c, "A3") if a["titre"].startswith("Lois du Journal officiel")][0]
    assert lois["exemples"] == sorted([
        "loi 2016-7 (2016-05-01) publiée au JO, absente de l'Assemblée et non reliée à un dossier (aucun_document)",
        "loi 2016-8 (2016-06-01) publiée au JO, absente de l'Assemblée et non reliée à un dossier "
        "(pas_de_travaux_preparatoires)",
        "loi 2018-4 (2018-04-01) publiée au JO, absente de l'Assemblée et non reliée à un dossier (aucun_document)",
        "loi 2017-9 (2017-01-01) promulguée selon l'Assemblée, absente du JO"])
    assert lois["detail"] == {
        "14": {"lois_au_jo": 4, "presentes_a_l_assemblee": 1, "reliees_par_le_jo": 0,
               "expliquees_avant_les_travaux_au_jo": 1, "nommees": 2, "assemblee_absentes_du_jo": 1},
        "15": {"lois_au_jo": 3, "presentes_a_l_assemblee": 1, "reliees_par_le_jo": 1,
               "expliquees_avant_les_travaux_au_jo": 0, "nommees": 1, "assemblee_absentes_du_jo": 0}}
    assert c.bilan()["expliques"]["a3_lois"] == lois["detail"]


def test_a3_lois_sans_le_jo_rien_a_comparer(tmp_path):
    c = _ctrl(tmp_path, tables=dict(TABLES, loi=[{"numero_loi": "2016-1", "date_promulgation": "2016-03-01",
                                                  "legislature": 14, "dossier": "D"}]))
    c.a3_totaux()
    assert not [a for a in _an(c, "A3") if a["titre"].startswith("Lois du Journal officiel")]


PAGE = """<div>Nombre de votants : <b>3</b></span> Pour l'adoption : <b>2</b></span>
Contre : <b>1</b></span> Abstention : <b>0</b></span>
<li data-organe-id="PO17S"><span class="h6 _colored-travaux">Pour</span><span>: 2</span>
<li class="_no-border" data-acteur-id="PA1 - PM1"><li class="_no-border" data-acteur-id="PA3 - PM3">
<span class="h6 _colored-travaux">Contre</span><li class="_no-border" data-acteur-id="PA4 - PM4">
<li data-organe-id="PO845401"><span class="h6 _colored-travaux">Non-votants</span>
<li class="_no-border" data-acteur-id="PA5 - PM5"></div>"""


def test_lire_page_de_scrutin():
    p = lire_page(PAGE)
    assert p["totaux"] == {"nombre_votants": 3, "pour": 2, "contre": 1, "abstentions": 0}
    assert p["positions"] == {"PA1": "pour", "PA3": "pour", "PA4": "contre", "PA5": "non_votant"}


def test_a2_verification_croisee(tmp_path):
    # Un vote du Parlement européen servi n'a pas de page à l'Assemblée : il n'est pas tiré.
    c = _ctrl(tmp_path, faits=FAITS + [_fait("candidat/alice-martin", "europe-votes", scrutin="MTG-PL-2020-01-15")])
    r = c.a2_verification_croisee(1, lambda url: PAGE, nb_scrutins=5)
    assert (r["tires"], r["faits"], r["verifies"], r["ecarts"]) == (1, 2, 2, [])
    assert not _an(c, "A2")
    # Une page qui dit autre chose : écart, avec l'adresse.
    c = _ctrl(tmp_path)
    r = c.a2_verification_croisee(1, lambda url: PAGE.replace("<b>2</b>", "<b>9</b>"), nb_scrutins=5)
    assert r["ecarts"] and "/dyn/17/scrutins/1" in r["ecarts"][0]
    assert _an(c, "A2")[0]["bloquant"] is False
    # Injoignable : non vérifié, jamais un écart ; tout injoignable → avertissement dédié.

    def panne(url):
        raise TimeoutError
    c = _ctrl(tmp_path)
    r = c.a2_verification_croisee(1, panne, nb_scrutins=5)
    assert r["ecarts"] == [] and len(r["non_verifies"]) == 2
    assert _an(c, "A2")[0]["titre"].startswith("Vérification croisée impossible")


PAGE_AM = """<div class="amendement-section-body"><button><b>Déposé par :</b>
<span class="@TogglableBox-a"> M. Un</span></button>
<div class="swiper-slide" data-tipsy="#t1"></div><div id="t1"><a href="/dyn/deputes/PA1">fiche</a></div>
<div id="t2"><a href="/dyn/deputes/PA3">fiche</a></div><div id="t3"><a href="/dyn/deputes/PA3">fiche</a></div>
</div><div class="amendement-section-body"><a href="/dyn/deputes/PA9">autre bloc</a></div>"""
PAGE_AM_XIV = """<meta name="AUTEUR_ID" content="267527">\n<meta name="GROUPE_ID" content="656006">
<meta name="COSIGNATAIRES_ID" content="608826;335159">"""
PAGE_AM_XIV_COMMISSION = """<meta name="AUTEURS" content=" M.&nbsp;Denaja, rapporteur pour avis">
<meta name="AUTEUR_ID" content="59051">\n<meta name="GROUPE_ID" content="">\n<meta name="COSIGNATAIRES_ID" content="">"""


def test_a2_lire_signataires_des_deux_sites():
    """Issue #63 (15/11/2026) : pages relevées le jour même. Site actuel (XVe à XVIIe) : bloc
    « Déposé par », liens vers les fiches dans l'ordre, sans doublon ; ancien site (XIVe) :
    métadonnées ; un amendement de commission y a pour auteur la commission (non comparé)."""
    from empreinte_src.verification import adresse_amendement, lire_signataires
    assert lire_signataires(PAGE_AM) == {"auteur": "PA1", "cosignataires": ["PA3"]}
    assert lire_signataires(PAGE_AM_XIV) == {"auteur": "PA267527", "cosignataires": ["PA608826", "PA335159"]}
    assert lire_signataires(PAGE_AM_XIV_COMMISSION) == {"auteur": None, "cosignataires": []}
    assert lire_signataires("<html>amendement du Gouvernement</html>") is None
    assert adresse_amendement("AMANR5L17PO838901B3211P0D1N000811", None) == \
        "https://www.assemblee-nationale.fr/dyn/17/amendements/AMANR5L17PO838901B3211P0D1N000811"
    assert adresse_amendement("AMANR5L14SEA644420BTC2553P0D1N317", "/14/amendements/2553/AN/317.pdf") == \
        "https://www.assemblee-nationale.fr/14/amendements/2553/AN/317.asp"
    assert adresse_amendement("AMANR5L14SEA644420BTC2553P0D1N317", None) is None


def test_a2_signataires_d_amendement(tmp_path):
    t = dict(TABLES,
             amendement_canonique=[{"amendement": "AM1", "acteur": "PA1", "date_depot": "2025-01-20",
                                    "alias": ["AM1B"], "document_uri": None}],
             amendement_auteur=[{"acteur": "PA1", "amendement": "AM1", "role": "auteur", "rang": 0},
                                {"acteur": "PA3", "amendement": "AM1", "role": "cosignataire", "rang": 1}])
    # AM1 n'a pas d'adresse (pas de législature dans l'identifiant de test) : non vérifié.
    c = _ctrl(tmp_path, tables=t)
    r = c.a2_signataires(1, lambda url: PAGE_AM, nb_amendements=5)
    assert (r["tires"], r["verifies"], r["ecarts"]) == (1, 0, [])
    assert r["non_verifies"] == ["AM1 signataires (adresse de la page inconnue)"]
    am = "AMANR5L17PO838901B3211P0D1N000811"
    t2 = dict(t, amendement_canonique=[dict(t["amendement_canonique"][0], amendement=am)],
              amendement_auteur=[dict(x, amendement=am) for x in t["amendement_auteur"]])
    faits = [_fait("lignee/soc", "amendements-2025", amendement=am)]
    c = _ctrl(tmp_path, tables=t2, faits=faits)
    r = c.a2_signataires(1, lambda url: PAGE_AM, nb_amendements=5)
    assert (r["tires"], r["verifies"], r["ecarts"], r["non_verifies"]) == (1, 1, [], [])
    assert not [a for a in _an(c, "A2") if "Signataires" in a["titre"]]
    # La page nomme un autre cosignataire : écart nommé, avec l'adresse.
    c = _ctrl(tmp_path, tables=t2, faits=faits)
    r = c.a2_signataires(1, lambda url: PAGE_AM.replace("PA3", "PA4"), nb_amendements=5)
    assert r["ecarts"] == [f"{am} cosignataires : 1 sur la page seulement (PA4) ; 1 chez nous seulement (PA3)"
                           f" — https://www.assemblee-nationale.fr/dyn/17/amendements/{am}"]
    a2 = [a for a in _an(c, "A2") if a["titre"].startswith("Signataires")][0]
    assert a2["bloquant"] is False and c.bilan()["a2_amendements"]["ecarts"] == 1

    def panne(url):
        raise TimeoutError
    c = _ctrl(tmp_path, tables=t2, faits=faits)
    r = c.a2_signataires(1, panne, nb_amendements=5)
    assert r["ecarts"] == [] and len(r["non_verifies"]) == 1
    assert [a for a in _an(c, "A2") if a["titre"].startswith("Vérification des signataires impossible")]


def test_a2_page_de_la_legislature_du_scrutin():
    """Un scrutin de la XIVe est relu sur sa page de la XIVe, pas sur celle de la XVIIe (qui
    porte le même numéro : écarts faux, essai du 12/11/2026)."""
    from empreinte_src.verification import verifier
    con = duckdb.connect()
    con.execute("CREATE TABLE _ctl_fp AS SELECT 'VTANR5L14V34' AS id_scrutin")
    con.execute("""CREATE TABLE an_scrutins__scrutin AS SELECT 'VTANR5L14V34' AS uid, '14' AS legislature,
                   '34' AS numero, 3 AS nombre_votants, 2 AS pour, 1 AS contre, 0 AS abstentions""")
    con.execute("CREATE TABLE an_scrutins__position_vote (scrutin VARCHAR, acteur VARCHAR, position VARCHAR)")
    lues = []
    verifier(con, 1, lambda url: lues.append(url) or PAGE, nb_scrutins=1)
    assert lues == ["https://www.assemblee-nationale.fr/dyn/14/scrutins/34"]


def _periode(mandat, debut, fin, etat="en_fonction", institution="assemblee", legislature=None):
    import json
    r = _fait("candidat/alice-martin", "entete", json.dumps(
        {"per": "per:000001", "institution": institution, "etat": etat, "legislature": legislature,
         "debut": debut, "fin": fin, "mandat": mandat}), mandat=mandat, acteur="PA1")
    r["type_fait"] = "periode_carriere"
    return r


# Carrière servie d'Alice Martin : un mandat découpé par deux groupes, un mandat suspendu (entrée au
# gouvernement), un mandat en cours découpé lui aussi, et une période d'avant 2002 lue dans Sycomore.
PERIODES = [_periode("PM15", "2017-06-21", "2018-01-01", legislature=15),
            _periode("PM15", "2018-01-02", "2022-06-21", legislature=15),
            _periode("PM16", "2022-06-22", "2022-07-22", legislature=16),
            _periode("PM16", "2022-07-23", "2024-06-09", etat="suspendu", legislature=16),
            _periode("PM17", "2024-07-08", "2024-07-18", legislature=17),
            _periode("PM17", "2024-07-19", None, legislature=17),
            _periode("sycomore:100:1997-06-01", "1997-06-01", "2002-06-18", institution="assemblee_avant_2002")]
SYCOMORE = [{"identifiant": "100", "chambre": c, "debut": d, "fin": f, "legislature": l}
            for c, d, f, l in (("assemblee", "1997-06-01", "2002-06-18", "XIe législature"),
                               ("assemblee", "2017-06-21", "2022-06-21", "XVe législature"),
                               ("assemblee", "2022-06-22", "2022-07-22", "XVIe législature"),
                               ("assemblee", "2024-07-08", None, "XVIIe législature"),
                               ("senat", "1990-10-01", "1999-09-30", None))]


def _tables_mandats(sycomore=SYCOMORE, identifiants=({"element": "Q1", "identifiant": "100"},)):
    t = dict(TABLES, candidat=[dict(c, sycomore=None, element_wikidata="Q1" if c["per"] == "per:000001" else None)
                               for c in TABLES["candidat"]])
    if sycomore is not None:
        t["sycomore__mandat_sycomore"] = list(sycomore)
    if identifiants:
        t["sycomore__identifiant_sycomore"] = list(identifiants)
    return t


def test_a2_mandats_contre_sycomore(tmp_path):
    """Issue #63 (23/11/2026) : chaque période de mandat de député servie (début, fin), contre la
    fiche Sycomore relevée la même nuit, sans page lue en plus. L'identifiant Sycomore est celui que
    Wikidata déclare pour l'élément (comme R-CARRIERE). Seul l'inexpliqué est nommé."""
    c = _ctrl(tmp_path, tables=_tables_mandats(), faits=FAITS + PERIODES)
    r = c.a2_mandats()
    # Segments d'un même mandat réunis ; la suspension et la période d'avant 2002 comptées, pas comparées.
    assert (r["faits"], r["verifies"], r["ecarts"], r["non_verifies"]) == (3, 3, [], [])
    assert (r["suspensions_non_comparees"], r["avant_2002_lues_dans_sycomore"]) == (1, 1)
    assert not [a for a in _an(c, "A2") if "mandat" in a["titre"]]
    assert c.bilan()["a2_mandats"]["verifies"] == 3
    from empreinte_src.cli import _ligne_a2
    assert "périodes de mandat (Sycomore) : 3 faits, 3 vérifiés, 0 en écart, 0 non vérifiés" in _ligne_a2(c.bilan())

    # Une fin différente, et un mandat de Sycomore que la carrière servie n'a pas : nommés.
    autre = [dict(s, fin="2022-06-20") if s["debut"] == "2017-06-21" else s for s in SYCOMORE]
    autre.append({"identifiant": "100", "chambre": "assemblee", "debut": "2012-06-20", "fin": "2017-06-20",
                  "legislature": "XIVe législature"})
    c = _ctrl(tmp_path, tables=_tables_mandats(autre), faits=FAITS + PERIODES)
    r = c.a2_mandats()
    url = "https://www2.assemblee-nationale.fr/sycomore/fiche?num_dept=100"
    assert r["ecarts"] == [
        f"candidat/alice-martin PM15 (15e législature) fin : nous 2022-06-21, Sycomore 2022-06-20 — {url}",
        f"candidat/alice-martin : mandat de Sycomore du 2012-06-20 au 2017-06-20 (XIVe législature), "
        f"absent de la carrière servie — {url}"]
    a2 = [a for a in _an(c, "A2") if a["titre"].startswith("Périodes de mandat")][0]
    assert a2["bloquant"] is False and c.bilan()["a2_mandats"]["ecarts"] == 2

    # Un mandat servi qu'aucune ligne de Sycomore ne recouvre : nommé.
    c = _ctrl(tmp_path, tables=_tables_mandats([s for s in SYCOMORE if s["debut"] != "2022-06-22"]),
              faits=FAITS + PERIODES)
    assert c.a2_mandats()["ecarts"] == [
        "candidat/alice-martin PM16 (16e législature, du 2022-06-22 au 2022-07-22) : aucun mandat de "
        f"Sycomore sur cette période — {url}"]

    # Sans identifiant Sycomore, ou sans relevé : non vérifié, jamais un écart ; tout non vérifié → averti.
    for t in (_tables_mandats(identifiants=()), _tables_mandats(sycomore=None)):
        c = _ctrl(tmp_path, tables=t, faits=FAITS + PERIODES)
        r = c.a2_mandats()
        assert (r["faits"], r["verifies"], r["ecarts"], len(r["non_verifies"])) == (3, 0, [], 3)
        assert [a for a in _an(c, "A2") if a["titre"].startswith("Vérification des mandats impossible")]


# Page de dossier de l'Assemblée, réduite à ses motifs (DLR5L16N48925, relevée le 23/11/2026).
PAGE_DOSSIER = """
<div data-id="L16-VD216427DI / Bloc de style '21'"></div>
<div data-id="L16-VD216427DI (DepotInitiative / -DEPOT)"><span>Dépôt à l&#039;Assemblée nationale</span>
<span>Vendredi 17 novembre 2023</span></div>
<div data-id="L16-AN1-48925 (Etape / AN1)"><span>Première lecture</span><span>Vendredi 17 novembre 2023</span>
 <div data-id="L16-VD216427DI (DepotInitiative / -DEPOT)"></div>
 <div data-id="L16-AN1-COM-48925 (Etape / -COM)"><div data-id="L16-VD216428CF (Etape / -COM-FOND)">
  <div data-id="L16-VD216428CFS (SaisieComFond / -COM-FOND-SAISIE)"></div>
  <span>Acte(s) de réunion : L16-VD216429R33493 - L16-VD216429R33494</span>
  <div data-id="L16-VD216534 (DepotRapport / -COM-FOND-RAPPORT)"><span>Rapport</span><span>Mardi 21 novembre 2023</span></div>
 </div></div>
 <div data-id="L16-AN1-DEBATS-48925 (Etape / -DEBATS)"><span>Discussion</span><span>Jeudi 23 novembre 2023</span>
  <button title="Acte(s) de réunion : L16-VD216453S46932">x</button><span>Acte(s) de réunion : L16-VD216453S46932</span>
  <div data-id="L16-VD216587DEC (Decision / -DEBATS-DEC)"><span>Texte adopté ✅</span><span>Jeudi 23 novembre 2023</span></div>
 </div>
</div>
<div data-id="L16-SN1-48925 (Etape / SN1)"><span>Jeudi 23 novembre 2023</span>
 <div data-id="L16-VD216596DIN (DepotInitiativeNavette / -DEPOT)"></div></div>
<div data-id="L16-PROM-48925 (Etape / PROM)"><span>Promulgation de la loi</span><span>Mardi 26 décembre 2023</span>
 <div data-id="L16-VD217259PL (Promulgation / PROM-PUB)">
 <span>Loi n°2023-1252  du mardi 26 décembre 2023 visant à prolonger…</span></div></div>
"""


def test_a2_lire_page_de_dossier():
    from empreinte_src.verification_textes import lire_dossier
    p = lire_dossier(PAGE_DOSSIER)
    actes = {a["uid"]: (a["type"], a["date"], a["palier"]) for a in p["actes"]}
    assert actes["L16-VD216427DI"] == ("DepotInitiative", "2023-11-17", 1)     # première date lue gardée
    assert actes["L16-VD216428CFS"] == ("SaisieComFond", None, None)          # une saisine ne prouve rien
    assert actes["L16-VD216534"] == ("DepotRapport", "2023-11-21", 2)
    assert actes["L16-VD216587DEC"] == ("Decision", "2023-11-23", 3)
    assert actes["L16-PROM-48925"] == ("Etape", "2023-12-26", 4)
    assert actes["L16-VD216596DIN"] == ("DepotInitiativeNavette", None, 1)
    assert [(r["uid"], r["palier"]) for r in p["reunions"]] == [
        ("L16-VD216429R33493", 2), ("L16-VD216429R33494", 2), ("L16-VD216453S46932", 3)]
    assert p["lois"] == [("2023-1252", "2023-12-26")]
    assert lire_dossier("<html>Page introuvable</html>") is None


def _texte(**k):
    v = {"dossier": "DLR5L16N48925", "date_depot": "2023-11-17", "etape": "promulgue",
         "date_etape": "2023-12-26", "numero_loi": "2023-1252", "date_promulgation": "2023-12-26",
         "source_url": "https://www.assemblee-nationale.fr/dyn/16/dossiers/tickets"}
    v.update(k)
    return v


def test_a2_textes_comparer_ne_nomme_que_l_inexplique():
    from empreinte_src.verification_textes import comparer, lire_dossier
    p = lire_dossier(PAGE_DOSSIER)
    issues = lambda v, au="2026-11-20", loi=None: [(f, i) for f, i, _ in comparer(v, 16, p, au, loi)]
    assert issues(_texte()) == [("depot", "verifie"), ("etape", "verifie"), ("loi", "verifie")]
    # Au 24/11/2023, la séance est le plus haut palier atteint ; la promulgation n'est pas encore là.
    assert issues(_texte(etape="adopte", date_etape="2023-11-23", numero_loi=None), au="2023-11-24") == \
        [("depot", "verifie"), ("etape", "verifie")]
    # Étape servie trop basse : la page montre la séance et la promulgation.
    r = comparer(_texte(etape="examen_commission", date_etape="2023-11-21", numero_loi=None), 16, p, "2026-11-20")
    assert r[1][:2] == ("etape", "ecart") and "page promulgation" in r[1][2]
    # Étape « examen en commission » datée d'une réunion : la page ne date pas les réunions.
    assert issues(_texte(etape="examen_commission", date_etape="2023-11-22", numero_loi=None),
                  au="2023-11-22")[1] == ("etape", "date_non_affichee")
    # Date de dépôt différente : écart nommé.
    r = comparer(_texte(date_depot="2023-11-16"), 16, p, "2026-11-20")
    assert r[0] == ("depot", "ecart", "dépôt : nous 2023-11-16, page 2023-11-17")
    # Date de la loi : celle du JO, que l'acte de l'Assemblée dément (A7 la nomme déjà) : expliquée.
    jo = {"source_date_promulgation": "journal_officiel", "date_assemblee": "2023-12-26"}
    assert issues(_texte(date_promulgation="2023-12-27"), loi=jo)[2] == ("loi", "date_de_promulgation_du_jo")
    assert issues(_texte(date_promulgation="2023-12-27"))[2] == ("loi", "ecart")
    # Étape d'une législature dont la page ne montre aucun acte : non vérifiée.
    assert [(f, i) for f, i, _ in comparer(_texte(), 17, p, "2026-11-20")][1] == ("etape", "non_verifie")


def test_a2_textes_tirage_et_avertissement(tmp_path):
    v = json.dumps(_texte(etape="seance", date_etape="2023-11-23", numero_loi=None))
    faits = [dict(_fait("legislature/16", "textes", v, dossier="DLR5L16N48925"), type_fait="texte_legislature",
                  source_url="https://www.assemblee-nationale.fr/dyn/16/dossiers/tickets")]
    c = _ctrl(tmp_path, faits=faits)
    r = c.a2_textes(1, lambda url: PAGE_DOSSIER, "2026-11-20", nb_textes=5)
    assert (r["tires"], r["faits"], r["verifies"], len(r["non_verifies"])) == (1, 2, 1, 0)
    assert r["ecarts"] == ["DLR5L16N48925 (legislature/16) étape : nous « seance » (2023-11-23), page "
                           "promulgation (L16-PROM-48925 du 2023-12-26, L16-VD217259PL) — "
                           "https://www.assemblee-nationale.fr/dyn/16/dossiers/tickets"]
    a2 = [a for a in _an(c, "A2") if a["titre"].startswith("Stade ou dates")][0]
    assert a2["bloquant"] is False and c.bilan()["a2_textes"]["ecarts"] == 1

    def panne(url):
        raise TimeoutError
    c = _ctrl(tmp_path, faits=faits)
    r = c.a2_textes(1, panne, "2026-11-20", nb_textes=5)
    assert r["ecarts"] == [] and len(r["non_verifies"]) == 2
    assert [a for a in _an(c, "A2") if a["titre"].startswith("Vérification des textes impossible")]
