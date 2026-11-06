"""Lecteur `an_amendements` sur des amendements réels de la XVIIe (voir extraits/an_amendements.md)."""
import json
import os
import zipfile

import pyarrow.parquet as pq
import pytest

from empreinte_src.depaquetage import depaqueter
from empreinte_src.entrepot import Entrepot
from empreinte_src.export import exporter
from empreinte_src.lecture import Lecture, MembreLu
from empreinte_src.lecteurs import an_amendements

EXTRAIT = os.path.join(os.path.dirname(__file__), "extraits", "amendements_l17_extrait.zip")
PA = {"id": "an-amendements-l17", "source": "an", "type": "amendements", "format": "zip",
      "url": "http://exemple.invalid/Amendements.json.zip"}
CFG = {"points_acces": [{"id": "an-amendements-l17", "licence": "etalab-2.0"}]}


def _membres():
    with zipfile.ZipFile(EXTRAIT) as z:
        return {n: z.read(n) for n in z.namelist()}


def _lire(chemin, octets):
    uid = chemin.rsplit("/", 1)[-1][:-5]
    return an_amendements.lire(MembreLu("an-amendements-l17", "an", "amendements", uid, chemin,
                                        1, "x", octets, "etalab-2.0"))


@pytest.fixture(scope="module")
def lus():
    """{uid: (ligne amendement, signatures)} pour tout l'extrait."""
    out = {}
    for chemin, octets in _membres().items():
        r = _lire(chemin, octets)
        out[r["amendement"][0]["uid"]] = (r["amendement"][0], r["signature"])
    return out


@pytest.fixture(scope="module")
def z2(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("am")
    e = Entrepot(str(tmp / "e"))
    e.versionner(PA, f"R{e.generation}", depaqueter(EXTRAIT, "zip"), complet=True)
    e.clore("test")
    b = Lecture(Entrepot(str(tmp / "e")), str(tmp / "z2"), CFG).executer(an_amendements)
    return tmp, b


def test_lecture_complete_sans_illisible(z2):
    tmp, b = z2
    assert b["lues"] == 13 and b["illisibles"] == 0
    assert b["lignes"] == {"amendement": 13, "signature": 464}
    t = pq.read_table(tmp / "z2" / "an_amendements__amendement.parquet").to_pylist()
    assert all(r["licence"] == "etalab-2.0" and r["prov_etat"] == "present" for r in t)
    assert all(r["lecteur"] == f"an_amendements@{an_amendements.VERSION}" for r in t)


def test_export_sans_cle_en_double(z2):
    tmp, _ = z2
    res = exporter(str(tmp / "z2"), [an_amendements], str(tmp / "export"))
    assert res["faits_par_type"] == {"amendement": 13, "signature": 464}
    assert res["cles_en_double"] == 0


def test_copies_b_btc_lues_toutes_les_deux(lus):
    """Les deux copies sont lues sous leur uid ; le dédoublonnage est la règle R-AMENDEMENT."""
    b, sb = lus["AMANR5L17PO838901B2202P0D1N000011"]
    btc, sbtc = lus["AMANR5L17PO838901BTC2202P0D1N000011"]
    assert (b["examen"], b["numero_long"]) == (btc["examen"], btc["numero_long"]) \
        == ("EXANR5L17PO838901BTC2202P0D1", "11")
    assert b["chronotag"] < btc["chronotag"]
    assert b["document_uri"] == "/base/AMANR5L17PO838901B2202P0D1N000011?format=pdf"
    # Rangés dans json/incorrect_data/ : pas de dossier dans le chemin, le document reste lu.
    assert b["chemin"].startswith("json/incorrect_data/") and b["dossier_chemin"] is None
    assert b["document"] == "PIONANR5L17BTC2202"
    assert [s["acteur"] for s in sb] == [s["acteur"] for s in sbtc]


def test_liste_complete_et_doublon_de_cosignataire(lus):
    a, sig = lus["AMANR5L17PO419610B1906P2D1N000024"]
    assert sig[0] == {"amendement": a["uid"], "acteur": "PA793532", "role": "auteur", "rang": 0}
    cos = [s for s in sig if s["role"] == "cosignataire"]
    assert len(cos) == a["nb_cosignataires"] == 71
    assert [s["rang"] for s in sig] == list(range(72))
    # La source cite deux fois PA795482 : deux lignes, gardées telles quelles.
    assert [s["rang"] for s in cos if s["acteur"] == "PA795482"] == [6, 71]
    assert "PA793532" not in {s["acteur"] for s in cos}
    _, sig = lus["AMANR5L17PO838901B3210P2D1N001096"]
    assert len(sig) == 243                     # le maximum de la XVIIe : 242 cosignataires


def test_cosignataire_seul_ecrit_en_chaine(lus):
    a, sig = lus["AMANR5L17PO59051B1105P0D1N000015"]
    assert a["nb_cosignataires"] == 1 and [s["role"] for s in sig] == ["auteur", "cosignataire"]


def test_types_d_auteur(lus):
    g, sig = lus["AMANR5L17PO838901BTC2468P0D1N000300"]
    assert g["type_auteur"] == "Gouvernement" and g["auteur"] is None
    assert g["gouvernement"] == "PO873634" and sig == []
    assert (g["etat"], g["sous_etat"], g["sort"]) == ("Discuté", "Adopté", "Adopté")
    assert g["seance_discussion"] == "RUANR5L17S2026IDS30490"
    assert (g["discussion_identique"], g["discussion_identique_position"]) == ("89531", "Premier")
    r, _ = lus["AMANR5L17PO838901B1851P0D1N000018"]
    assert (r["type_auteur"], r["auteur"], r["organe_rapporteur"]) == ("Rapporteur", "PA841955", "PO59048")
    d, _ = lus["AMANR5L17PO419610B1906P2D1N000024"]
    assert (d["groupe_auteur"], d["organe_examen"], d["prefixe_organe_examen"]) == \
        ("PO845413", "PO419610", "CION-ECO")


def test_efface_sans_auteur_ni_corps(lus):
    a, sig = lus["AMANR5L17PO838901B1906P1D2N000001"]
    assert a["etat"] == "effacé" and a["type_auteur"] == "Député"
    assert a["auteur"] is None and sig == []
    assert a["date_depot"] is None and a["expose_sommaire"] is None and a["article_titre"] is None
    assert a["document_uri"] is None


def test_irrecevable_sans_expose_ni_dispositif(lus):
    a, _ = lus["AMANR5L17PO838901BTC1245P0D1N000038"]
    assert (a["etat_code"], a["sous_etat"]) == ("IRRD", "Doublon")
    assert a["expose_sommaire"] is None and a["dispositif"] is None   # None, jamais ""
    assert a["sort"] is None


def test_sort_tel_que_publie(lus):
    a, _ = lus["AMANR5L17PO838901B0622P0D1N000312"]
    assert (a["etat_code"], a["sous_etat_code"], a["sous_etat"], a["sort"]) == ("ET", "R", "R", None)
    d, _ = lus["AMANR5L17PO419610B1906P2D1N000024"]
    assert (d["etat_code"], d["sous_etat"], d["sort"]) == ("DI", "Rejeté", "Rejeté")


def test_textes_tels_que_publies(lus):
    a, _ = lus["AMANR5L17PO838901BTC2468P0D1N000300"]
    assert a["dispositif"] == "<p>Supprimer cet article</p>"
    assert a["expose_sommaire"].startswith("<p>Cet amendement vise &#x00E0; supprimer")
    assert (a["article_titre"], a["article_designation_courte"]) == ("Article 9", "ART. 9")
    # Amendement de crédits : le dispositif est une structure, gardée en JSON.
    c, _ = lus["AMANR5L17PO838901BTC2146P0D1N000007"]
    assert c["dispositif"] is None
    assert "listeProgrammes" in json.loads(c["dispositif_credits"])
    p, _ = lus["AMANR5L17PO419610B1906P2D1N000024"]
    assert p["mission"] == "Agriculture, alimentation, forêt et affaires rurales"


def test_sous_amendement_et_suffixe(lus):
    s, _ = lus["AMANR5L17PO838901B1907P0D1N002663"]
    assert s["amendement_parent"] and s["amendement_parent"].startswith("AMANR5L17")
    x, _ = lus["AMANR5L17PO420120B1907P0D1N000779"]
    assert x["suffixe"] is not None


def test_variantes_de_forme():
    """Identifiants sans `PA`, cosignataires écrits en objet seul, vide écrit `xsi:nil`."""
    chemin = "json/DLR5L15N43846/PIONANR5L17B1105/AMANR5L17PO59051B1105P0D1N000015.json"
    d = json.loads(_membres()[chemin])
    sig = d["amendement"]["signataires"]
    sig["auteur"]["acteurRef"] = sig["auteur"]["acteurRef"][2:]
    sig["cosignataires"] = {"acteurRef": "795482"}
    d["amendement"]["cycleDeVie"]["dateDepot"] = {"@xsi:nil": "true"}
    r = _lire(chemin, json.dumps(d).encode())
    assert [s["acteur"] for s in r["signature"]] == ["PA720644", "PA795482"]
    assert r["amendement"][0]["date_depot"] is None
