"""R-ETAPE (version 4, décision Q48 du 23/11/2026, « Ranger par la date ») : la législature d'un acte
est celle où tombe sa date ; son identifiant ne sert que faute de date, ou pour une date qui ne
tombe dans aucune législature. Actes réels de l'archive des dossiers (export de la g20)."""
from empreinte_src.lecteurs import an_dossiers
from empreinte_src.liaison import Contexte
from empreinte_src.regles import r_etape
from empreinte_src.regles.r_etape import decisions

from .test_regles_c import ecrire_table

LEGISLATURES = """CREATE VIEW legislature AS SELECT * FROM (VALUES
    (14, '2012-06-20', '2017-06-20'), (15, '2017-06-21', '2022-06-21'),
    (16, '2022-06-22', '2024-06-09'), (17, '2024-07-01', NULL)) t(numero, debut, fin)"""


def _ctx(tmp_path, actes, legislatures=True):
    z2, z3 = tmp_path / "z2", tmp_path / "z3"
    z2.mkdir()
    ecrire_table(z2, an_dossiers, "dossier", [{"uid": d, "legislature": d[6:8], "procedure_code": "1"}
                                              for d in {a["dossier"] for a in actes}])
    ecrire_table(z2, an_dossiers, "acte", actes)
    ctx = Contexte(str(z2), str(z3), date_reference="2026-11-20")
    if legislatures:
        ctx.x(LEGISLATURES)
    ctx.regle_courante = r_etape
    return ctx


def _acte(dossier, uid, type_acte, date, code="SN1", conclusion=None):
    return {"dossier": dossier, "uid": uid, "type_acte": type_acte, "code": code,
            "date": date + "T00:00:00", "conclusion_code": conclusion}


# DLR5L14N35418 (accord Chili–Bolivie) : déposé au Sénat sous la XIVe ; l'archive close de la XIVe
# numérote `L14-` le rapport du Sénat du 17/01/2018, que la page publique range sous la XVe.
CHILI = [_acte("DLR5L14N35418", "L14-VD180307DI", "DepotInitiative_Type", "2016-11-30", "SN1-DEPOT"),
         _acte("DLR5L14N35418", "L14-VD184205", "DepotRapport_Type", "2018-01-17", "SN1-COM-FOND-RAPPORT"),
         _acte("DLR5L14N35418", "L15-VD184244DEC", "Decision_Type", "2018-01-25", "SN1-DEBATS-DEC", "TSORTF01")]
# DLR5L16N49029 : promulgation du 13/06/2024, entre la dissolution (09/06) et l'ouverture de la
# XVIIe (01/07) : aucune législature ne couvre la date, l'identifiant décide.
DISSOLUTION = [_acte("DLR5L16N49029", "L16-VD1DI", "DepotInitiative_Type", "2024-03-01", "AN1-DEPOT"),
               _acte("DLR5L16N49029", "L16-VD9PL", "Promulgation_Type", "2024-06-13", "PROM-PUB")]


def test_etape_rangee_par_la_date(tmp_path):
    ctx = _ctx(tmp_path, CHILI + DISSOLUTION)
    r_etape.appliquer(ctx)
    lignes = {(d, l): (e, dt) for d, l, e, dt in ctx.x(
        "SELECT dossier, legislature, etape_atteinte, date_etape FROM etape_dossier")}
    assert lignes == {
        ("DLR5L14N35418", 14): ("depot", "2016-11-30"),          # le rapport de 2018 n'y est plus
        ("DLR5L14N35418", 15): ("seance", "2018-01-25"),         # rapport et décision : XVe
        ("DLR5L16N49029", 16): ("promulgue", "2024-06-13")}      # date hors législature : identifiant
    leg = dict(ctx.x(f"SELECT acte, legislature FROM ({decisions(ctx)})"))
    assert leg == {"L15-VD184244DEC": 15}


def test_sans_table_des_legislatures_l_identifiant_decide(tmp_path):
    ctx = _ctx(tmp_path, CHILI, legislatures=False)
    r_etape.appliquer(ctx)
    lignes = {(d, l): e for d, l, e in ctx.x("SELECT dossier, legislature, etape_atteinte FROM etape_dossier")}
    assert lignes == {("DLR5L14N35418", 14): "examen_commission", ("DLR5L14N35418", 15): "seance"}
