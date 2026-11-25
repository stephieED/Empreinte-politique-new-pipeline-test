"""R-ETAPE (version 2) : codes de conclusion classés d'après leur libellé ; ceux qui restent sont
nommés (issue #45). Codes et libellés de l'archive des dossiers (entrepôt g10, 13/11/2026).
Version 3 (alerte #118, décidé le 23/11/2026 : doc. 5, Q45 et Q46) : TSORTMOT01 lu avec le type
de sa motion (renvoi en commission), TSORTFnull « sans conclusion »."""
from empreinte_src.lecteurs import an_dossiers
from empreinte_src.liaison import Contexte
from empreinte_src.regles.r_etape import adoptions_definitives, decisions

from .test_regles_c import ecrire_table

CAS = [  # dossier, procédure, code de l'acte, conclusion, libellé
    ("DLR5L14N35259", "15", "ANLUNI-DEBATS-DEC", "TSORTF21",
     "considérée comme définitive en application de l'article 151-9 du Règlement"),
    ("DLR5L14N29958", "15", "ANLUNI-DEBATS-DEC", "TSORTF20", "adoptée en application de l'article 151-7 du Règlement"),
    ("DLR5L16N47461", "15", "ANLUNI-DEBATS-DEC", "TSORTF12",
     "considérée comme définitive en application de l'article 151-3 du Règlement"),
    ("DLR5L16N45929", "1", "ANLDEF-DEBATS-DEC", "TSORTF13", "rejeté définitivement"),
    ("DLR5L14N10001", "1", "ANLDEF-DEBATS-DEC", "TSORTF04", "adoptée définitivement"),
    ("DLR5L14N10002", "1", "AN2-DEBATS-DEC", "TSORTF14",
     "voté par les deux assemblées du Parlement en termes identiques"),
    ("DLR5L14N33632", "1", "SN1-DEBATS-DEC", "TSORTF23",
     "modifié par le Sénat, considéré comme adopté par l’Assemblée nationale en application de l’article 49, "
     "alinéa 3, de la Constitution après engagement de la procédure accélérée"),
    ("DLR5L14N29478", "2", "AN1-DEBATS-MOTION-VOTE", "TSORTMOT01", "Motion adopté(e)"),
    ("DLR5L15N37327", "2", "SNNLEC-DEBATS-DEC", "TSORTFnull", None),
    # Motion adoptée qui n'est pas un renvoi en commission (aucun cas aux archives) : non classée.
    ("DLR5L17N99999", "2", "AN1-DEBATS-MOTION-VOTE", "TSORTMOT01", "Motion adoptée"),
]
# Motions (`MotionProcedure_Type`, même uid que la décision sans le suffixe `DEC`).
MOTIONS = {"DLR5L14N29478": ("TMP03", "Motions de renvoi en commission"),
           "DLR5L17N99999": ("TMP02", "Question préalable")}


def _actes(cas=CAS, motions=MOTIONS):
    actes = []
    for k, (d, p, code, c, l) in enumerate(cas):
        uid = f"L{d[6:8]}-VD{k}"
        actes.append({"dossier": d, "uid": f"{uid}DEC", "code": code, "type_acte": "Decision_Type",
                      "date": "2016-12-01T00:00:00", "conclusion_code": c, "conclusion_libelle": l})
        if d in motions:
            actes.append({"dossier": d, "uid": uid, "code": "AN1-DEBATS-MOTION",
                          "type_acte": "MotionProcedure_Type", "date": "2016-12-01T00:00:00",
                          "type_motion_code": motions[d][0], "type_motion_libelle": motions[d][1]})
    return actes


def test_conclusions_classees_et_restantes(tmp_path):
    z2, z3 = tmp_path / "z2", tmp_path / "z3"
    z2.mkdir()
    z3.mkdir()
    ecrire_table(z2, an_dossiers, "dossier", [{"uid": d, "legislature": d[6:8], "procedure_code": p}
                                              for d, p, *_ in CAS])
    ecrire_table(z2, an_dossiers, "acte", _actes())
    ctx = Contexte(str(z2), str(z3), date_reference="2026-11-13")
    issue = dict(ctx.x(f"SELECT dossier, issue FROM ({decisions(ctx)})"))
    assert len(issue) == len(CAS)                           # la jointure à la motion ne double rien
    assert {c: issue[d] for d, _, _, c, _ in CAS if c != "TSORTMOT01"} == {
        "TSORTF21": "adopte", "TSORTF20": "adopte", "TSORTF12": "adopte", "TSORTF13": "rejete",
        "TSORTF04": "adopte", "TSORTF14": "adopte", "TSORTF23": "adopte", "TSORTFnull": "sans_conclusion"}
    # TSORTMOT01 : renvoi en commission d'après la motion ; une autre motion reste non classée.
    assert (issue["DLR5L14N29478"], issue["DLR5L17N99999"]) == ("renvoi_en_commission", None)
    # Résolutions européennes adoptées (art. 151) et lecture définitive : adoptions définitives.
    assert {d for (d,) in ctx.x(f"SELECT dossier FROM ({adoptions_definitives(ctx)})")} == \
        {"DLR5L14N35259", "DLR5L14N29958", "DLR5L16N47461", "DLR5L14N10001"}


def test_a7_nomme_les_conclusions_non_classees(tmp_path):
    import duckdb
    import pyarrow as pa
    import pyarrow.parquet as pq

    from empreinte_src.controles import Controles
    faits = tmp_path / "faits.parquet"
    pq.write_table(pa.table({"fiche": pa.array([], pa.string())}), faits)
    con = duckdb.connect()
    con.execute("""CREATE VIEW conclusion_non_classee AS SELECT * FROM (VALUES
        ('TSORTMOT01', 'Motion adoptée', 25, 25, ['DLR5L14N29478', 'DLR5L14N29698'], 22),
        ('TSORTFnull', NULL, 1, 1, ['DLR5L17N50588'], 1))
        t(conclusion_code, conclusion_libelle, decisions, dossiers, exemples,
          dossiers_dont_c_est_la_derniere_decision)""")
    c = Controles(str(tmp_path))
    c.preparer(con, str(faits), set())
    c.a7_non_resolues({})
    a7 = [a for a in c.bilan()["anomalies"] if a["controle"] == "A7"]
    assert a7 and not a7[0]["bloquant"]
    assert a7[0]["exemples"] == ["conclusion TSORTFnull (sans libellé) non classée : 1 décisions, 1 dossiers "
                                 "(1 dont c'est la dernière décision), dont DLR5L17N50588",
                                 "conclusion TSORTMOT01 (« Motion adoptée ») non classée : 25 décisions, "
                                 "25 dossiers (22 dont c'est la dernière décision), dont DLR5L14N29478, DLR5L14N29698"]


def test_a7_dates_de_promulgation_connues(tmp_path):
    """Issue #118 (décision du 25/11/2026, option 1) : un écart de date de promulgation entre le JO
    et l'acte de l'Assemblée noté comme connu (décision `date_promulgation_connue`) n'est plus
    nommé par A7 ; il est compté dans le bilan. Un écart nouveau, ou un écart connu qui change
    (autre date), est nommé ; la décision qui ne correspond plus à rien est dite sans objet."""
    import duckdb
    import pyarrow as pa
    import pyarrow.parquet as pq

    from empreinte_src.controles import Controles
    faits = tmp_path / "faits.parquet"
    pq.write_table(pa.table({"fiche": pa.array([], pa.string())}), faits)
    con = duckdb.connect()
    con.execute("""CREATE VIEW loi AS SELECT * FROM (VALUES
        ('2021-191', '2021-02-22', '0021-02-24', 'journal_officiel'),
        ('2017-115', '2017-02-01', '2017-01-15', 'journal_officiel'),
        ('2026-5', '2026-01-10', '2026-01-11', 'journal_officiel'),
        ('2026-6', '2026-01-12', '2026-01-12', 'journal_officiel'))
        t(numero_loi, date_promulgation, date_assemblee, source_date_promulgation)""")
    fichier = "date_promulgation_connue/2026-11-25-ecarts-jo-assemblee.yaml#"
    connues = [{"numero_loi": "2021-191", "date_jo": "2021-02-22", "date_assemblee": "0021-02-24",
                "fichier": fichier + "0"},
               # connu avec une autre date à l'Assemblée : l'écart a changé
               {"numero_loi": "2017-115", "date_jo": "2017-02-01", "date_assemblee": "2017-01-01",
                "fichier": fichier + "1"}]
    c = Controles(str(tmp_path))
    c.preparer(con, str(faits), set())
    c.a7_non_resolues({"date_promulgation_connue": connues})
    a7 = [a for a in c.bilan()["anomalies"] if a["controle"] == "A7"]
    assert a7[0]["exemples"] == [
        f"décision {fichier}1 sans objet : loi 2017-115, le 2017-02-01 au JO, le 2017-01-01 selon "
        "l'acte de l'Assemblée, n'est plus un écart publié",
        "loi 2017-115 : promulguée le 2017-02-01 au JO, le 2017-01-15 selon l'acte de l'Assemblée",
        "loi 2026-5 : promulguée le 2026-01-10 au JO, le 2026-01-11 selon l'acte de l'Assemblée"]
    assert c.bilan()["expliques"] == {"a7_dates_de_promulgation_connues": 1}


def test_decision_des_dates_de_promulgation_connues():
    """Le fichier de référence (issue #118) note les 9 écarts de la nuit du 24/11/2026, avec un motif."""
    import os
    from empreinte_src.liaison import Contexte
    racine = os.path.join(os.path.dirname(__file__), "..", "references")
    c = Contexte.__new__(Contexte)
    import duckdb
    c.con = duckdb.connect()
    c._charger_decisions(racine)
    d = c.decisions["date_promulgation_connue"]
    assert len(d) == 9 and all(x["motif"] and x["date_jo"] != x["date_assemblee"] for x in d)
    assert {x["numero_loi"] for x in d} >= {"2021-191", "2016-1973", "2025-136"}
