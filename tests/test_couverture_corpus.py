"""Couverture du corpus servie à la racine (`couverture.json.gz`, issue #74) : l'état de chaque
point d'accès et les manques fiche par fiche, assemblés à partir de ce qui existe déjà."""
import gzip
import json
import os

from empreinte_src.composition import Ecrivain, _date_source
from empreinte_src.controles import Controles
from empreinte_src.schema import verifier

POINTS = [
    {"id": "an-scrutins-l17", "source": "an", "type": "scrutins", "legislature": 17},
    {"id": "an-amendements-l15", "source": "an", "type": "amendements", "legislature": 15},
    {"id": "senat-export", "source": "senat", "type": "export_sens"},
    {"id": "pe-votes", "source": "europarl", "type": "votes_pe", "depuis": "2019-07-02"},
    {"id": "jo-global", "source": "dila", "type": "jorf"},
    {"id": "sycomore-fiches", "source": "sycomore", "type": "fiches_sycomore"},
]
RELEVES = [
    {"point_acces": "an-scrutins-l17", "source": "an", "issue": "nouveau",
     "debut": "2026-11-22T20:31:00+00:00", "date_source": "Sat, 22 Nov 2026 03:12:00 GMT"},
    {"point_acces": "an-amendements-l15", "source": "an", "issue": "echec",
     "debut": "2026-11-22T20:40:00+00:00", "date_source": None},
    {"point_acces": "senat-export", "source": "senat", "issue": "inchange",
     "debut": "2026-11-22T20:41:00+00:00", "date_source": "Mon, 17 Nov 2026 06:00:00 GMT"},
    {"point_acces": "pe-votes", "source": "europarl", "issue": "nouveau",
     "debut": "2026-11-22T20:50:00+00:00"},
    {"point_acces": "jo-global", "source": "dila", "issue": "inchange",
     "debut": "2026-11-22T20:52:00+00:00", "date_source": "pas une date"},
]


def _lire(ecr, chemin):
    with gzip.open(os.path.join(ecr.racine, chemin)) as f:
        return json.load(f)


def _table(t):
    return [dict(zip(t["colonnes"], l)) for l in t["lignes"]]


def _ecrivain(tmp_path, **kw):
    return Ecrivain(str(tmp_path), "g000020",
                    pannes={"an-amendements-l15": "2026-11-20T20:40:00+00:00"},
                    releves_reussis={"an-scrutins-l17": "2026-11-22T20:31:00+00:00",
                                     "an-amendements-l15": None,
                                     "senat-export": "2026-11-22T20:41:00+00:00",
                                     "pe-votes": "2026-11-22T20:50:00+00:00",
                                     "jo-global": "2026-11-22T20:52:00+00:00",
                                     "sycomore-fiches": "2026-11-15T21:00:00+00:00"},
                    **kw)


def test_etat_des_points_dates_de_la_source_et_raisons(tmp_path):
    ecr = _ecrivain(tmp_path, releves_nuit=RELEVES, points_acces=POINTS)
    etat = {p["point_acces"]: p for p in ecr.etat_points()}
    assert list(etat) == [p["id"] for p in POINTS]                  # ordre de la configuration
    s = etat["an-scrutins-l17"]
    assert (s["releve_cette_nuit"], s["date_source"], s["raison_date_source"]) == (
        "nouveau", "2026-11-22T03:12:00+00:00", None)
    assert s["dernier_releve_reussi"] == "2026-11-22T20:31:00+00:00" and s["panne_depuis"] is None
    # une panne : date de la source inconnue, jamais remplacée par la date de passage
    a = etat["an-amendements-l15"]
    assert (a["releve_cette_nuit"], a["date_source"]) == ("echec", None)
    assert a["raison_date_source"] == "relevé de cette nuit en échec (echec)"
    assert (a["dernier_releve_reussi"], a["raison_dernier_releve"]) == (None, "aucun relevé complet n'a encore abouti")
    assert a["panne_depuis"] == "2026-11-20T20:40:00+00:00"
    # 304 : la date de la source reste celle de la donnée, pas celle du relevé
    assert etat["senat-export"]["date_source"] == "2026-11-17T06:00:00+00:00"
    # source sans date (API) : vide avec sa raison
    pe = etat["pe-votes"]
    assert (pe["date_source"], pe["raison_date_source"], pe["depuis"]) == (
        None, "la source ne donne pas de date", "2019-07-02")
    assert etat["jo-global"]["raison_date_source"] == "date donnée par la source illisible : pas une date"
    # point non relevé cette nuit : son dernier relevé réussi reste daté
    sy = etat["sycomore-fiches"]
    assert (sy["releve_cette_nuit"], sy["date_source"], sy["raison_date_source"]) == (
        None, None, "point non relevé cette nuit")
    assert sy["dernier_releve_reussi"] == "2026-11-15T21:00:00+00:00"


def test_etat_des_points_sans_releves_transmis(tmp_path):
    """Sans les relevés de la nuit ni la configuration (ancien appel), l'état le dit."""
    ecr = Ecrivain(str(tmp_path), "g1", pannes={"senat-export": "2026-11-20"},
                   releves_reussis={"senat-export": "2026-11-19"})
    (p,) = ecr.etat_points()
    assert p["point_acces"] == "senat-export" and p["panne_depuis"] == "2026-11-20"
    assert (p["date_source"], p["raison_date_source"]) == (None, "relevés de la nuit non transmis")
    assert p["dernier_releve_reussi"] == "2026-11-19"


def test_releve_en_plusieurs_fois_garde_la_pire_issue_et_la_date_la_plus_recente(tmp_path):
    rs = [{"point_acces": "jo-livraisons", "issue": "nouveau", "date_source": "Thu, 20 Nov 2026 01:00:00 GMT"},
          {"point_acces": "jo-livraisons", "issue": "nouveau", "date_source": "Fri, 21 Nov 2026 01:00:00 GMT"}]
    ecr = Ecrivain(str(tmp_path), "g1", releves_nuit=rs)
    (p,) = ecr.etat_points()
    assert (p["releve_cette_nuit"], p["date_source"]) == ("nouveau", "2026-11-21T01:00:00+00:00")
    assert p["raison_dernier_releve"] == "dernier relevé réussi non transmis"
    ecr = Ecrivain(str(tmp_path), "g2", releves_nuit=rs + [{"point_acces": "jo-livraisons", "issue": "echec"}])
    assert ecr.etat_points()[0]["releve_cette_nuit"] == "echec"
    assert ecr.etat_points()[0]["date_source"] is None


def test_date_source():
    assert _date_source("Sat, 22 Nov 2026 03:12:00 GMT") == "2026-11-22T03:12:00+00:00"
    assert _date_source("2026-11-22T05:12:00+02:00") == "2026-11-22T03:12:00+00:00"
    assert _date_source("2026-11-22") == "2026-11-22T00:00:00+00:00"
    assert _date_source(None) is None and _date_source("") is None and _date_source("n/a") is None


def test_couverture_json_manques_fiche_par_fiche(tmp_path):
    ecr = _ecrivain(tmp_path, releves_nuit=RELEVES, points_acces=POINTS)
    f = ecr.fiche("candidat", "x", "X")
    f.entete({"limites": [{"famille": "banc", "statut": "relu_aucun", "detail": "Aucun banc relu."},
                          {"famille": "activite", "statut": "complet", "detail": "Tout est lu."}]})
    f.section("votes", [{"a": 1}], "vote",
              couverture={"famille": "votes", "statut": "complet", "points_acces": ["an-scrutins-l17"]})
    f.section("amendements-2016", [], "amendement",
              couverture={"famille": "amendements", "statut": "complet", "detail": "D.",
                          "points_acces": ["an-amendements-l15"]})
    f.section("questions", [], "question",
              couverture={"famille": "questions", "statut": "non_relu", "detail": "Règle absente."})
    g = ecr.fiche("gouvernement", "y", "Y")
    g.entete({"limites": [{"sujet": "senat", "statut": "hors_perimetre", "detail": "Sénat non lu."}]})
    g.section("actes", [], "acte",
              couverture={"famille": "actes", "statut": "partiel", "detail": "Avant 2012 : non lu.",
                          "points_acces": ["jo-global"],
                          "periode_couverte": {"du": "2012-06-20", "au": "2014-03-31"}})
    l = ecr.fiche("lignee", "z", "Z")
    l.entete({"limites": ["Une limite écrite comme une phrase."]})
    ecr.clore()
    c = _lire(ecr, "couverture.json.gz")
    assert (c["contrat"], c["publication"]) == ("1.0", "g000020")
    assert [p[0] for p in c["points_acces"]["lignes"]] == [p["id"] for p in POINTS]
    manques = _table(c["manques"])
    assert [(m["fiche"], m["origine"], m["nom"], m["statut"]) for m in manques] == [
        ("candidat/x", "section", "amendements-2016", "panne"),
        ("candidat/x", "section", "questions", "non_relu"),
        ("candidat/x", "limite", "banc", "relu_aucun"),
        ("gouvernement/y", "section", "actes", "partiel"),
        ("gouvernement/y", "limite", "senat", "hors_perimetre"),
        ("lignee/z", "limite", None, None)]
    am = manques[0]
    assert (am["statut_sans_panne"], am["panne_depuis"], am["points_acces"]) == (
        "complet", "2026-11-20T20:40:00+00:00", ["an-amendements-l15"])
    assert (manques[3]["du"], manques[3]["au"], manques[3]["titre"]) == ("2012-06-20", "2014-03-31", "Y")
    assert manques[5]["detail"] == "Une limite écrite comme une phrase."
    # « relu, aucun » et « non relu » restent distincts ; les sections complètes sont comptées
    dec = {tuple(l[:4]): l[4] for l in c["decomptes"]["lignes"]}
    assert dec[("candidat", "section", "votes", "complet")] == 1
    assert dec[("candidat", "section", "amendements", "panne")] == 1
    assert dec[("candidat", "limite", "banc", "relu_aucun")] == 1
    assert dec[("candidat", "section", "questions", "non_relu")] == 1
    assert dec[("candidat", "limite", "activite", "complet")] == 1
    assert "couverture.json.gz" in json.load(open(os.path.join(ecr.racine, "manifeste.json")))["fichiers"]


def test_couverture_json_passe_les_controles(tmp_path):
    """Fichier à la racine : pas une section pour C4 (forme), aucune clé interdite, aucun lien, et
    pas de clé `couverture` au premier niveau (C5 ne le lit pas comme une section complète)."""
    import yaml
    ecr = _ecrivain(tmp_path, releves_nuit=RELEVES, points_acces=POINTS)
    f = ecr.fiche("candidat", "x", "X")
    f.section("amendements", [], "amendement",
              couverture={"famille": "amendements", "statut": "complet", "points_acces": ["an-amendements-l15"]})
    m = ecr.clore()
    c = _lire(ecr, "couverture.json.gz")
    assert "couverture" not in c
    schema = yaml.safe_load(open(os.path.join(os.path.dirname(__file__), "..", "config", "schema_fichiers.yaml")))
    assert [e for e in verifier(ecr.racine, schema) if "couverture.json" in e] == []
    ctrl = Controles(ecr.racine)
    ctrl.c2_liens({x["fiche"] for x in m["fiches"]})
    ctrl.c4_interdits()
    ctrl.c5_couverture(RELEVES)
    assert ctrl.bilan()["publication_autorisee"], ctrl.bilan()


def test_couverture_json_sans_fiche(tmp_path):
    ecr = Ecrivain(str(tmp_path), "g1")
    ecr.clore()
    c = _lire(ecr, "couverture.json.gz")
    assert c["points_acces"]["lignes"] == [] and c["manques"]["lignes"] == [] and c["decomptes"]["lignes"] == []
