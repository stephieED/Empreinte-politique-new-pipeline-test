"""Lecteur `an_comptes_rendus` sur cinq comptes rendus réels de la XVIIe (voir
extraits/an_comptes_rendus.md)."""
import os
import zipfile

import pyarrow.parquet as pq
import pytest

from empreinte.depaquetage import depaqueter
from empreinte.entrepot import Entrepot
from empreinte.export import exporter
from empreinte.lecture import Lecture, MembreLu
from empreinte.lecteurs import an_comptes_rendus

EXTRAIT = os.path.join(os.path.dirname(__file__), "extraits", "syceron_l17_extrait.zip")
PA = {"id": "an-syceron-l17", "source": "an", "type": "comptes_rendus", "format": "zip",
      "url": "http://exemple.invalid/syseron.xml.zip"}
CFG = {"points_acces": [{"id": "an-syceron-l17", "licence": "etalab-2.0"}]}
BASE = "https://www.assemblee-nationale.fr/dyn/17/comptes-rendus/seance/"


@pytest.fixture(scope="module")
def lus():
    cr, par = {}, {}
    with zipfile.ZipFile(EXTRAIT) as z:
        for n in z.namelist():
            uid = n.rsplit("/", 1)[-1][:-4]
            r = an_comptes_rendus.lire(MembreLu("an-syceron-l17", "an", "comptes_rendus", uid, n,
                                                1, "x", z.read(n), "etalab-2.0"))
            cr[uid] = r["compte_rendu"][0]
            for p in r["intervention"]:
                assert p["id_syceron"] not in par
                par[p["id_syceron"]] = p
    return cr, par


@pytest.fixture(scope="module")
def z2(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("cr")
    e = Entrepot(str(tmp / "e"))
    e.versionner(PA, f"R{e.generation}", depaqueter(EXTRAIT, "zip"), complet=True)
    e.clore("test")
    b = Lecture(Entrepot(str(tmp / "e")), str(tmp / "z2"), CFG).executer(an_comptes_rendus)
    return tmp, b


def test_lecture_une_ligne_par_paragraphe(z2):
    tmp, b = z2
    assert b["lues"] == 5 and b["illisibles"] == 0
    assert b["lignes"] == {"compte_rendu": 5, "intervention": 1109}
    with zipfile.ZipFile(EXTRAIT) as z:     # 1 109 éléments <paragraphe> dans les cinq XML
        assert sum(z.read(n).count(b"<paragraphe ") for n in z.namelist()) == 1109
    t = pq.read_table(tmp / "z2" / "an_comptes_rendus__intervention.parquet").to_pylist()
    assert all(r["prov_url"] == f"{BASE}{r['compte_rendu']}#{r['id_syceron']}" for r in t)
    assert all(r["licence"] == "etalab-2.0" and r["prov_etat"] == "present" for r in t)


def test_export_sans_cle_en_double(z2):
    tmp, _ = z2
    res = exporter(str(tmp / "z2"), [an_comptes_rendus], str(tmp / "export"))
    assert res["faits_par_type"] == {"compte_rendu": 5, "intervention": 1109}
    assert res["cles_en_double"] == 0


def test_compte_rendu(lus):
    cr, _ = lus
    c = cr["CRSANR5L17S2026O1N105"]
    assert (c["seance"], c["date"], c["statut"], c["nb_paragraphes"]) == \
        ("RUANR5L17S2026IDS30080", "2026-01-07", "complet", 102)
    assert c["prov_url"] == BASE + "CRSANR5L17S2026O1N105"
    assert c["president_seance"] == "Présidence de M.\xa0Christophe Blanchet"
    assert cr["CRSANR5L17S2027O1N051"]["statut"] == "provisoire"


def test_provisoire_sans_stime(lus):
    _, par = lus
    prov = [p for p in par.values() if p["compte_rendu"] == "CRSANR5L17S2027O1N051"]
    assert len(prov) == 407 and all(p["stime"] is None for p in prov)
    assert par["4042860"]["stime"] == "5984.81"


def test_orateur_restitue_tel_quel(lus):
    _, par = lus
    # Nom affiché qui ne correspond pas à l'identifiant (Alice Rufo sous l'identifiant de Ruffin).
    p = par["4042860"]
    assert (p["orateur"], p["orateur_nom"]) == ("PA722142", "Mme Alice Rufo")
    assert p["qualite"].startswith("ministre déléguée")
    assert [o["id"] for o in p["orateurs"]] == ["PA722142", "PA722142"]
    assert p["prov_url"] == BASE + "CRSANR5L17S2026O1N177#4042860"
    # Identifiant négatif, PA0, identifiant de repli : gardés.
    assert (par["3984143"]["orateur"], par["3984143"]["orateur_nom"]) == ("PA-126299", "M. Daniel Goldberg")
    assert par["3994515"]["orateur"] == "PA0" and len(par["3994515"]["orateurs"]) > 1
    assert par["3984220"]["orateur"] == "PA793214"
    # Orateur nommé sans attribut id_acteur : `orateur` vide, l'id de <orateur> avec son PA.
    assert par["3984146"]["orateur"] is None and par["3984146"]["orateurs"][0]["id"] == "PA0"
    # Paragraphe sans orateur.
    assert any(p["orateurs"] == [] and p["orateur"] is None for p in par.values())


def test_presidence_non_deduite(lus):
    _, par = lus
    roles = {p["roledebat"] for p in par.values()}
    assert roles == {None, "president"}
    generiques = [p for p in par.values() if p["orateur_nom"] in ("M. le président", "Mme la présidente")]
    assert any(p["roledebat"] is None for p in generiques)   # l'attribut manque : rien n'est déduit


def test_hierarchie_des_points(lus):
    _, par = lus
    pts = par["4042860"]["points"]
    assert [(x["niv"], x["titre"]) for x in pts] == [(1, "Questions au gouvernement"),
                                                    (2, "Industrie d’armement")]
    assert par["4042860"]["valeur_ptsodj"] == "2"
    # Une suspension (nivpoint 99) est un point pour la source : gardée sous le point courant.
    s = par["3673658"]["points"]
    assert [x["nivpoint"] for x in s] == ["1", "2", "3", "99"]
    assert s[-1]["code_grammaire"].startswith("SUSP_SEANCE")


def test_extraction_et_texte(lus):
    _, par = lus
    assert par["3984064"]["extraction_orateur"] and par["3984064"]["extraction_orateur"].startswith("PA")
    textes = [p["texte"] for p in par.values() if p["texte"]]
    assert any("\n" in t for t in textes)                     # <br/> → saut de ligne
    assert not any(t != t.strip() or "  " in t for t in textes)   # mise en forme XML ôtée
