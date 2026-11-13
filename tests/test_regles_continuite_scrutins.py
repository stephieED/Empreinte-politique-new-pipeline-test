"""R-CONTINUITE-SCRUTINS : trous de l'archive des scrutins (issue #36).

Petites tables recopiées des faits lus de l'entrepôt g10 (13/11/2026) :
- XIVe : archive arrêtée au n° 1 354 (24/11/2016) ; des actes de dossiers de décembre 2016 citent
  les n° 1 358, 1 362 et 1 364 ; législature close le 20/06/2017 ;
- XVe : n° 3 781 et 3 782 absents (entre le 25 et le 26/05/2021) ; le n° 4 689, cité le
  26/01/2022 mais au-delà du dernier numéro, n'est pas daté après la fin de l'archive ;
- XVIe : le scrutin du Congrès `VTCGR5L16V1` porte aussi le numéro 1 ;
- XVIIe, en cours : un acte cite un scrutin plus récent que l'archive (archive des dossiers plus
  fraîche que celle des scrutins) : ce n'est pas une archive tronquée."""
import types

import pyarrow as pa
import pyarrow.parquet as pq

from empreinte_src.lecteurs import an_dossiers
from empreinte_src.liaison import Contexte, ordonner, relier
from empreinte_src.regles import r_continuite_scrutins as r

from .test_regles_c import ecrire_table

SCRUTINS = (
    [("VTANR5L14V%d" % n, 14, n, "2012-07-03" if n == 1 else "2016-11-24") for n in range(1, 1355)]
    + [("VTANR5L15V%d" % n, 15, n, "2021-05-25" if n <= 3780 else "2021-05-26" if n <= 3784 else "2022-02-24")
       for n in range(1, 4420) if n not in (3781, 3782)]
    + [("VTANR5L16V1", 16, 1, "2022-07-11"), ("VTCGR5L16V1", 16, 1, "2024-03-04"),
       ("VTANR5L16V2", 16, 2, "2022-07-12")]
    + [("VTANR5L17V1", 17, 1, "2024-10-08"), ("VTANR5L17V2", 17, 2, "2026-11-12")]
)
LEGISLATURES = [(14, "2012-06-20", "2017-06-20"), (15, "2017-06-21", "2022-06-21"),
                (16, "2022-06-22", "2024-06-09"), (17, "2024-07-18", None)]
ACTES = [
    {"dossier": "DLR5L14N1", "uid": "L14-A1", "date": "2016-12-07T00:00:00", "scrutins": ["VTANR5L14V1358"]},
    {"dossier": "DLR5L14N2", "uid": "L14-A2", "date": "2016-12-20T00:00:00",
     "scrutins": ["VTANR5L14V1362", "VTANR5L14V1364"]},
    {"dossier": "DLR5L14N3", "uid": "L14-A3", "date": "2016-11-24T00:00:00", "scrutins": ["VTANR5L14V1354"]},
    {"dossier": "DLR5L15N1", "uid": "L15-A1", "date": "2022-01-26T00:00:00", "scrutins": ["VTANR5L15V4689"]},
    {"dossier": "DLR5L16N1", "uid": "L16-A1", "date": "2023-07-06T00:00:00", "scrutins": ["VTSNR5L16V2137"]},
    {"dossier": "DLR5L17N1", "uid": "L17-A1", "date": "2026-11-13T00:00:00", "scrutins": ["VTANR5L17V3"]},
]


def _ecrire(z3, nom, table):
    pq.write_table(table, z3 / f"{nom}.parquet")


def _substituts(z3):
    def nature(ctx):
        ctx.ecrire("scrutin_nature", "SELECT * FROM read_parquet('%s')" % (z3 / "_sn.parquet"))
        return {}

    def legs(ctx):
        ctx.ecrire("legislature", "SELECT * FROM read_parquet('%s')" % (z3 / "_lg.parquet"))
        return {}
    _ecrire(z3, "_sn", pa.table({"scrutin": [s[0] for s in SCRUTINS], "legislature": [s[1] for s in SCRUTINS],
                                 "numero": [s[2] for s in SCRUTINS], "date": [s[3] for s in SCRUTINS]}))
    _ecrire(z3, "_lg", pa.table({"numero": [x[0] for x in LEGISLATURES], "debut": [x[1] for x in LEGISLATURES],
                                 "fin": pa.array([x[2] for x in LEGISLATURES], pa.string())}))
    return [types.SimpleNamespace(NOM="R-NATURE-SCRUTIN", VERSION=0, DEPEND=(), SORTIES=("scrutin_nature",),
                                  appliquer=nature),
            types.SimpleNamespace(NOM="R-LEGISLATURES", VERSION=0, DEPEND=(), SORTIES=("legislature",),
                                  appliquer=legs)]


def _ctx(tmp_path, actes=True):
    z2, z3 = tmp_path / "z2", tmp_path / "z3"
    z2.mkdir()
    z3.mkdir()
    if actes:
        ecrire_table(z2, an_dossiers, "acte", ACTES)
    ctx = Contexte(str(z2), str(z3))
    bilan = relier(ctx, ordonner([*_substituts(z3), r]))
    return ctx, {b["regle"].split("@")[0]: b for b in bilan}


def test_archive_tronquee_et_numeros_manquants(tmp_path):
    ctx, bilan = _ctx(tmp_path)
    ts = {(t["legislature"], t["nature"]): t for t in r.trous(ctx)}
    assert set(ts) == {(14, "archive_tronquee"), (15, "numeros_manquants")}
    t14 = ts[(14, "archive_tronquee")]
    assert (t14["du"], t14["au"], list(t14["numeros"]), t14["nb"]) == \
        ("2016-11-24", "2017-06-20", [1358, 1362, 1364], None)
    assert t14["cites_absents"] == 3
    t15 = ts[(15, "numeros_manquants")]
    assert (t15["du"], t15["au"], list(t15["numeros"]), t15["nb"]) == ("2021-05-25", "2021-05-26", [3781, 3782], 2)
    # Le n° 4 689 cité avant la fin de l'archive, le Sénat, le Congrès, la XVIIe en cours : aucun trou.
    assert t15["cites_absents"] == 1
    assert bilan["R-CONTINUITE-SCRUTINS"]["couverture"]["legislature_sans_trou_de_scrutins"] == [2, 4]


def test_phrases_et_marquage(tmp_path):
    ctx, _ = _ctx(tmp_path)
    t14, t15 = r.trous(ctx)
    assert r.phrase(t14) == (
        "L'archive des scrutins de la XIVe législature publiée par l'Assemblée s'arrête au 24/11/2016 : "
        "les scrutins suivants, jusqu'à la fin de la législature le 20/06/2017, manquent à la source "
        "(des dossiers citent les n° 1 358, 1 362, 1 364, absents de l'archive), et leur "
        "nombre n'est pas connu.")
    assert r.phrase(t15) == ("2 scrutins de la XVe législature manquent à la source (n° 3 781 et "
                             "3 782, entre le 25/05/2021 et le 26/05/2021).")
    c = r.marquer({"statut": "complet", "detail": "1354 scrutins."}, [t14])
    assert c["statut"] == "trou_source" and c["statut_sans_trou"] == "complet"
    assert c["detail"].startswith("1354 scrutins. L'archive des scrutins de la XIVe")
    assert c["trous_source"][0]["numeros"] == [1358, 1362, 1364]
    # Un statut plus grave est gardé ; sans trou, rien ne change.
    assert r.marquer({"statut": "hors_perimetre", "detail": "x"}, [t14])["statut"] == "hors_perimetre"
    assert r.marquer({"statut": "complet"}, []) == {"statut": "complet"}
    assert r.date_des_donnees("2017-06-20", [t14]) == "2016-11-24"
    assert r.date_des_donnees("2022-06-21", [t15]) == "2022-06-21"


def test_periode_couverte(tmp_path):
    ctx, _ = _ctx(tmp_path)
    t14, t15 = r.trous(ctx)
    assert r.couvre(t14, "2012-06-20", None)                    # mandat en cours à la fin
    assert r.couvre(t14, "2016-12-01", "2017-06-20")            # entré pendant le trou
    assert not r.couvre(t14, "2012-06-20", "2016-11-24")        # parti le jour du dernier scrutin lu
    assert not r.couvre(t14, "2017-06-21", None)                # après la législature
    assert r.couvre(t15, "2021-05-26", "2021-06-30")            # jour d'un numéro manquant
    assert not r.couvre(t15, "2021-05-27", None)


def test_sans_actes_de_dossiers(tmp_path):
    """Sans les dossiers, la troncature n'est pas établie ; les numéros manquants le sont."""
    ctx, _ = _ctx(tmp_path, actes=False)
    assert [(t["legislature"], t["nature"]) for t in r.trous(ctx)] == [(15, "numeros_manquants")]


def test_points_d_une_section_annuelle(tmp_path):
    """#33 : une section d'une année ne déclare que les sources des législatures de cette année
    (« amendements de 2026 » ne dépend pas de l'archive de la XVIe, close en 2024)."""
    from empreinte_src.composeurs.candidat import points_de_l_annee
    ctx, _ = _ctx(tmp_path)
    pts = ["an-amendements-l14", "an-amendements-l15", "an-amendements-l16", "an-amendements-l17"]
    assert points_de_l_annee(ctx, pts, "2026") == ["an-amendements-l17"]
    assert points_de_l_annee(ctx, pts, "2017") == ["an-amendements-l14", "an-amendements-l15"]
    assert points_de_l_annee(ctx, pts, "2024") == ["an-amendements-l16", "an-amendements-l17"]
    assert points_de_l_annee(ctx, pts, "sans-date") == pts
    assert points_de_l_annee(ctx, ["senat-export"], "2013") == ["senat-export"]
