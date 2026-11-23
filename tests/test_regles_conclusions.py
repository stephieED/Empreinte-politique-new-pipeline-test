"""R-ETAPE (version 2) : codes de conclusion classés d'après leur libellé ; ceux qui restent sont
nommés (issue #45). Codes et libellés de l'archive des dossiers (entrepôt g10, 13/11/2026).
Version 3 (alerte #118, classement à valider : doc. 5, Q45 et Q46) : TSORTMOT01 lu avec le type
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
