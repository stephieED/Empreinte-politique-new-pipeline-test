import os

from empreinte_src.lecture import MembreLu
from empreinte_src.lecteurs import wd_identifiants

EXTRAIT = os.path.join(os.path.dirname(__file__), "extraits", "wd_identifiants_extrait.json")


def _lire():
    with open(EXTRAIT, "rb") as f:
        o = f.read()
    return wd_identifiants.lire(MembreLu("wd", "wikidata", "identifiants_wikidata", "u", "c", 1,
                                         "e", o, "cc0-1.0"))["identifiant_externe"]


def test_identifiant_assemblee_avec_pa():
    r = [x for x in _lire() if x["article_frwiki"] == "François Ruffin" and x["propriete"] == "P4123"]
    assert r and r[0]["identifiant"] == "PA722142" and r[0]["valeur_publiee"] == "722142"


def test_matricule_senat_tire_du_chemin():
    r = [x for x in _lire() if x["article_frwiki"] == "Jean-Luc Mélenchon" and x["propriete"] == "P1808"]
    assert r and r[0]["identifiant"] == "86039K" and r[0]["valeur_publiee"].startswith("senateur/")


def test_chaque_ligne_a_sa_source():
    assert all(x["prov_url"].startswith("https://www.wikidata.org/wiki/Q") for x in _lire())
