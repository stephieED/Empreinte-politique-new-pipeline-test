"""R-ETAPE (version 2) : codes de conclusion classés d'après leur libellé ; ceux qui restent sont
nommés (issue #45). Codes et libellés de l'archive des dossiers (entrepôt g10, 13/11/2026)."""
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
    ("DLR5L14N29478", "1", "AN1-DEBATS-MOTION-VOTE", "TSORTMOT01", "Motion adoptée"),
    ("DLR5L15N37327", "1", "SNNLEC-DEBATS-DEC", "TSORTFnull", None),
]


def test_conclusions_classees_et_restantes(tmp_path):
    z2, z3 = tmp_path / "z2", tmp_path / "z3"
    z2.mkdir()
    z3.mkdir()
    ecrire_table(z2, an_dossiers, "dossier", [{"uid": d, "legislature": d[6:8], "procedure_code": p}
                                              for d, p, *_ in CAS])
    ecrire_table(z2, an_dossiers, "acte", [
        {"dossier": d, "uid": f"L{d[6:8]}-{d}-{k}", "code": code, "type_acte": "Decision_Type",
         "date": "2016-12-01T00:00:00", "conclusion_code": c, "conclusion_libelle": l}
        for k, (d, p, code, c, l) in enumerate(CAS)])
    ctx = Contexte(str(z2), str(z3), date_reference="2026-11-13")
    issue = dict(ctx.x(f"SELECT conclusion_code, issue FROM ({decisions(ctx)})"))
    assert issue == {"TSORTF21": "adopte", "TSORTF20": "adopte", "TSORTF12": "adopte", "TSORTF13": "rejete",
                     "TSORTF04": "adopte", "TSORTF14": "adopte", "TSORTF23": "adopte",
                     "TSORTMOT01": None, "TSORTFnull": None}
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
        ('TSORTMOT01', 'Motion adoptée', 25, 25, ['DLR5L14N29478', 'DLR5L14N29698'], 22))
        t(conclusion_code, conclusion_libelle, decisions, dossiers, exemples,
          dossiers_dont_c_est_la_derniere_decision)""")
    c = Controles(str(tmp_path))
    c.preparer(con, str(faits), set())
    c.a7_non_resolues({})
    a7 = [a for a in c.bilan()["anomalies"] if a["controle"] == "A7"]
    assert a7 and not a7[0]["bloquant"]
    assert a7[0]["exemples"] == ["conclusion TSORTMOT01 (« Motion adoptée ») non classée : 25 décisions, "
                                 "25 dossiers (22 dont c'est la dernière décision), dont DLR5L14N29478, DLR5L14N29698"]
