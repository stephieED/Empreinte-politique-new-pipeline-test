"""Lecteur des dossiers législatifs et documents de l'Assemblée : l'arbre aplati, les actes
partagés entre deux dossiers, le 49.3 lu dans `typeDeclaration`, les scrutins du Sénat, le NOR
de la XIVe au niveau de l'acte, les documents (nature, divisions, cosignatures), et le passage
par le cadre. Extraits décrits dans `tests/extraits/an_dossiers.md`."""
import collections
import os
import zipfile

import pyarrow.parquet as pq
import pytest

from empreinte.depaquetage import depaqueter
from empreinte.entrepot import Entrepot
from empreinte.export import exporter
from empreinte.lecture import Lecture, MembreLu
from empreinte.lecteurs import an_dossiers

EXTRAITS = os.path.join(os.path.dirname(__file__), "extraits")
ZIPS = {14: "an_dossiers_l14_fragment.zip", 15: "an_dossiers_l15_extrait.zip",
        16: "an_dossiers_l16_extrait.zip", 17: "an_dossiers_l17_extrait.zip"}


def lire_zip(nom) -> dict:
    out = collections.defaultdict(list)
    with zipfile.ZipFile(os.path.join(EXTRAITS, nom)) as z:
        for n in z.namelist():
            m = MembreLu("an-dossiers", "an", "dossiers", n, n, 1, "e", z.read(n), "etalab-2.0")
            for t, rows in an_dossiers.lire(m).items():
                out[t].extend(rows)
    return out


@pytest.fixture(scope="module")
def lu():
    return {leg: lire_zip(nom) for leg, nom in ZIPS.items()}


def actes(r, dossier):
    return {a["uid"]: a for a in r["acte"] if a["dossier"] == dossier}


def test_dossier_et_arbre(lu):
    d = {x["uid"]: x for x in lu[17]["dossier"]}["DLR5L17N53259"]
    assert d["procedure_code"] == "6" and d["initiateurs_acteurs"] == ["PA643210", "PA721836"]
    assert d["prov_url"] == ("https://www.assemblee-nationale.fr/dyn/17/dossiers/"
                             "approbation_accord_Gouvernement_Agence_spatiale_europeenne_installations_France")
    a = actes(lu[17], "DLR5L17N53259")
    assert len(a) == d["nb_actes"] == 27
    assert a["L17-AN1-53259"]["parent"] is None and a["L17-AN1-53259"]["profondeur"] == 0
    assert a["L17-VD229063CFS"]["parent"] == "L17-VD229063CF" and a["L17-VD229063CFS"]["profondeur"] == 3
    assert a["L17-VD229063CFS"]["code"] == "AN1-COM-FOND-SAISIE" and a["L17-VD229063CFS"]["organe"] == "PO59047"
    assert a["L17-VD229172"]["rapporteurs"] == ["PA794030"]
    dec = a["L17-VD229940DEC"]
    assert (dec["conclusion_code"], dec["conclusion_libelle"]) == ("TSORTF01", "adopté")   # tel quel
    assert dec["reunion"] == "RUANR5L17S2026IDS30142" and dec["textes_associes"] == ["PRJLANR5L17BTA0214"]
    assert a["L17-VD231264"]["texte_adopte"] == "PRJLSNR5S479BTC0519"
    p = a["L17-VD231575PL"]
    assert (p["code_loi"], p["reference_nor"]) == ("2026-300", "EAEJ2524276L")
    assert p["prov_url"].startswith("http://www.legifrance.gouv.fr/")


def test_49_3_et_actes_partages(lu):
    a1, a2 = actes(lu[17], "DLR5L17N53597"), actes(lu[17], "DLR5L17N52428")
    dgvt = a1["L17-VD229941"]
    assert dgvt["type_acte"] == "DeclarationGouvernement_Type"
    assert dgvt["type_declaration_code"] == "Art.49.3" and dgvt["scrutins"] == []   # aucun scrutin
    # le même acte figure dans deux dossiers (examen commun) : clé (dossier, uid)
    assert "L17-VD229941" in a2 and a2["L17-VD229941"]["parent"] != dgvt["parent"]
    assert a1["L17-VD230014"]["scrutins"] == ["VTANR5L17V5154"]


def test_scrutin_du_senat_garde(lu):
    a = actes(lu[17], "DLR5L16N49107")
    assert a["L17-VD226412DEC"]["scrutins"] == ["VTSNR5L17V2215"]


def test_decision_du_conseil_constitutionnel(lu):
    cc = [a for a in lu[17]["acte"] if a["type_acte"] == "ConclusionEtapeCC_Type"]
    assert {(a["conclusion_code"], a["conclusion_libelle"], a["num_decision"]) for a in cc} == {
        ("TCD01", "Conforme", "877"), ("TCD02", "Partiellement conforme", "901")}
    assert all(a["prov_url"] == a["url_conclusion"] for a in cc)
    # le vote sur une motion de censure porte sa décision dans `decision`, lue à part
    m = actes(lu[17], "DLR5L17N53597")["L17-VD230014"]
    assert m["decision_code"] == "TSORTMOT02" and m["conclusion_code"] is None


def test_fusion_et_sans_chemin(lu):
    d = {x["uid"]: x for x in lu[17]["dossier"]}
    assert (d["DLR5L15N37118"]["fusion_cause"], d["DLR5L15N37118"]["fusion_dossier_absorbant"]) == (
        "Examen commun", "DLR5L15N37121")
    assert d["DLR5L17N51610"]["titre_chemin"] is None and d["DLR5L17N51610"]["prov_url"] is None


def test_documents(lu):
    t = {x["uid"]: x for x in lu[17]["document"]}
    assert (t["PRJLANR5L17B2155"]["nature"], t["PRJLANR5L17B2155"]["chambre"]) == ("PRJL", "AN")
    assert t["PRJLANR5L17B2155"]["prov_url"] == "https://www.assemblee-nationale.fr/dyn/opendata/PRJLANR5L17B2155.html"
    assert t["PNREANR5L17B0643"]["auteurs_acteurs"] == ["PA722328"]
    # document du Sénat : législature absente (None), pas d'adresse à l'Assemblée
    s = t["PIONSNR5S459BTA0143"]
    assert (s["nature"], s["chambre"], s["legislature"], s["prov_url"]) == ("PION", "SN", None, None)
    # division aplatie avec son parent
    div = t["RAPPANR5L17B2865-COMPA"]
    assert div["parent"] == "RAPPANR5L17B2865" and div["profondeur"] == 1
    assert div["prov_url"] == t["RAPPANR5L17B2865"]["prov_url"]
    # document supprimé à la source : la date est lue, pas d'adresse
    assert t["PRJLANR5L17BTC3188"]["date_suppression"] and t["PRJLANR5L17BTC3188"]["prov_url"] is None
    cs = [c for c in lu[17]["cosignature"] if c["document"] == "PNREANR5L17B0643"]
    assert len(cs) == 7 and [c["acteur"] for c in cs if c["date_retrait"]] == ["PA332523"]


def test_xv_rectificatif_jo(lu):
    p = actes(lu[15], "DLR5L15N36364")["L15-VD185308PL"]
    assert p["reference_nor"] == "MENX1805338L" and len(p["rectificatifs_jo"]) == 1
    assert "MENX1805338Z" in p["rectificatifs_jo"][0]


def test_xvi_texte_externe(lu):
    a = actes(lu[16], "DLR5L16N49095")["L16-VD218174"]
    assert a["type_acte"] == "ConvocationCongres_Type" and "HRUX2406047D" in a["texte_externe"]


def test_xiv_export_unique(lu):
    r = lu[14]
    assert {d["uid"] for d in r["dossier"]} == {"DLR5L14N35433", "DLR5L14N35050"}
    # un document de la XVe dans l'archive XIVe : législature lue telle quelle
    assert [(t["uid"], t["legislature"]) for t in r["document"]] == [("PIONANR5L15B0759", "15")]
    a = actes(r, "DLR5L14N35433")
    p = a["L14-VD180578PL"]
    # XIVe : NOR et adresse Légifrance au niveau de l'acte, pas dans infoJO
    assert (p["code_loi"], p["reference_nor"], p["date_jo"]) == ("2016-1767", "INTX1633947L", "2016-12-20+01:00")
    # scrutin cité absent de l'archive XIVe des scrutins (tronquée au 24/11/2016) : gardé
    assert a["L14-VD180473DEC"]["scrutins"] == ["VTANR5L14V1362"]
    assert actes(r, "DLR5L14N35050")["L14-VD178737"]["type_declaration_code"] == "Art.49.3"


def test_par_le_cadre_et_export(tmp_path):
    pa_cfg = {"id": "an-dossiers-l17", "source": "an", "type": "dossiers", "format": "zip",
              "url": "http://exemple.invalid/Dossiers_Legislatifs.json.zip"}
    e = Entrepot(str(tmp_path / "e"))
    e.versionner(pa_cfg, f"R{e.generation}", depaqueter(os.path.join(EXTRAITS, ZIPS[17]), "zip"),
                 complet=True)
    e.clore("test")
    e = Entrepot(str(tmp_path / "e"))
    b = Lecture(e, str(tmp_path / "z2"), {"points_acces": [{"id": "an-dossiers-l17",
                                                            "licence": "etalab-2.0"}]}).executer(an_dossiers)
    assert b["lues"] == 12 and b["illisibles"] == 0 and b["lignes"]["dossier"] == 7
    t = pq.read_table(tmp_path / "z2" / "an_dossiers__acte.parquet").to_pylist()
    assert all(r["licence"] == "etalab-2.0" for r in t)
    x = exporter(str(tmp_path / "z2"), [an_dossiers], str(tmp_path / "export"))
    assert x["cles_en_double"] == 0 and x["faits_par_type"]["acte"] == len(t)
