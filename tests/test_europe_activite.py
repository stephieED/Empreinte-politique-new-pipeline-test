"""Volet européen : activité hors votes (décision Q37 du 13/11/2026).

Lecteurs `parltrack_activites` (extrait réel : un député européen, `mep_id` 4554) et
`pe_eurodeputes` (deux interventions réelles de R. Glucksmann), règle R-ACTIVITE-PE."""
import os

import pyarrow.parquet as pq

from empreinte_src.depaquetage import _membre, depaqueter
from empreinte_src.entrepot import Entrepot
from empreinte_src.lecteurs import an_acteurs, parltrack_activites, pe_eurodeputes
from empreinte_src.lecteurs.parltrack_activites import date_reelle
from empreinte_src.lecture import Lecture
from empreinte_src.regles import r_activite_pe
from tests.test_europe_mandats import PA_PE, _lire
from tests.test_regles_e1 import EX, PAS, TOUTES, _ecrire_decision, _lignes, _relier

PA_ACT = {"id": "parltrack-activites", "source": "parltrack", "type": "activites_parltrack",
          "format": "fichier", "url": "https://parltrack.org/dumps/ep_mep_activities.json.zst",
          "uid": "ep_mep_activities"}


def test_date_reelle():
    rep = {"date": "2016-11-22T19:07:00", "date-type": "datePublished"}
    assert date_reelle({**rep, "url": "http://x/CRE-8-2017-02-15-INT-3-02"})[0] == "2017-02-15"
    assert date_reelle({**rep, "reference": "P8_CRE-REV(2017)02-15(3-026-0000)"})[0] == "2017-02-15"
    assert date_reelle({**rep, "reference": "A7-0342/2011"})[:2] == (None, "2011")
    assert date_reelle(rep)[:2] == (None, None)
    assert date_reelle({"date": "2022-10-12T00:00:00", "reference": "B9-0462/2022"}) == ("2022-10-12", "2022", None)
    assert date_reelle({"date": ["2020-01-02T00:00:00"]})[0] == "2020-01-02"         # champ publié en liste


def _sparql():
    """Réponse Wikidata **fabriquée** : l'élément réel de R. Glucksmann, et un élément fictif (Q999)
    rattaché au député européen 4554 de l'extrait Parltrack, pour faire passer la règle sur de
    vraies lignes de Parltrack."""
    import orjson
    return orjson.dumps({"head": {"vars": ["item", "pe"]}, "results": {"bindings": [
        {"item": {"type": "uri", "value": f"http://www.wikidata.org/entity/{q}"},
         "pe": {"type": "literal", "value": i}} for q, i in (("Q556149", "197694"), ("Q999", "4554"))]}})


def _z2(d):
    e = Entrepot(str(d / "e"))
    e.versionner(PAS["amo"][0], "R0", depaqueter(os.path.join(EX, "amo30_l17_candidats_e1.zip"), "zip"),
                 complet=True)
    e.versionner(PA_PE, "R1", [
        _membre("wikidata-p1186", "wikidata-p1186.json", _sparql()),
        _membre("mep-197694", "meps/197694.json", _lire("meps-197694.json")),
        _membre("interventions-197694-0", "speeches/197694-0.json", _lire("interventions-197694-0.json"))],
        complet=True, delta=True)
    with open(os.path.join(EX, "parltrack_ep_mep_activities_extrait.json.zst"), "rb") as f:
        e.versionner(PA_ACT, "R2", [_membre("ep_mep_activities", "x.json.zst", f.read())], complet=True)
    e.clore("test")
    cfg = {"points_acces": [{"id": "an-amo30-l17", "licence": "etalab-2.0"},
                            {"id": "pe-eurodeputes", "licence": "cc-by-4.0"},
                            {"id": "parltrack-activites", "licence": "odbl-1.0"}]}
    lect = Lecture(Entrepot(str(d / "e")), str(d / "z2"), cfg)
    for m in (an_acteurs, pe_eurodeputes, parltrack_activites):
        assert lect.executer(m)["illisibles"] == 0
    return d / "z2"


def test_lecteurs(tmp_path):
    z2 = _z2(tmp_path)
    a = pq.read_table(z2 / "parltrack_activites__activite_pt.parquet").to_pylist()
    assert {r["mep"] for r in a} == {"4554"} and len(a) == 17
    assert {r["licence"] for r in a} == {"odbl-1.0"}
    cre = [r for r in a if r["type"] == "CRE"]
    assert all(r["date"] and r["date"] != "2016-11-22" for r in cre)       # republication écartée
    i = pq.read_table(z2 / "pe_eurodeputes__intervention_pe.parquet").to_pylist()
    assert sorted(r["date"] for r in i) == ["2023-01-17", "2025-11-25"]
    assert all(r["prov_url"].startswith("https://www.europarl.europa.eu/doceo/document/CRE-") and r["debat"] for r in i)


def test_activite_par_famille_et_bascule(tmp_path):
    z2 = _z2(tmp_path)
    d = tmp_path / "d"
    _ecrire_decision(os.path.join(str(d), "candidature"), [
        {"nom": "Raphaël Glucksmann", "statut": "declaree", "wikidata": "Q556149", "article_frwiki": "Raphaël Glucksmann"},
        {"nom": "Député fictif", "statut": "declaree", "wikidata": "Q999"}])
    ctx, bilan, _ = _relier(z2, tmp_path / "z3", tmp_path / "r", TOUTES + [r_activite_pe], decisions=d)
    g = _lignes(ctx, "SELECT a.* FROM activite_pe a JOIN candidat c USING (per) WHERE c.nom_liste = 'Raphaël Glucksmann'")
    assert sorted((r["famille"], r["source"], r["date"]) for r in g) == [
        ("interventions", "pe", "2023-01-17"), ("interventions", "pe", "2025-11-25")]
    f = _lignes(ctx, "SELECT a.* FROM activite_pe a JOIN candidat c USING (per) WHERE c.nom_liste = 'Député fictif'")
    brut = pq.read_table(z2 / "parltrack_activites__activite_pt.parquet").to_pylist()
    attendu = sum(1 for r in brut if not (r["type"] == "CRE" and (r["date"] or (r["annee"] or "") + "-12-31") >= "2019-07-02"))
    assert len(f) == attendu and {r["source"] for r in f} == {"parltrack"}
    # Ses 5 interventions datent d'après le 02/07/2019 : le portail les donne, Parltrack est écarté.
    assert not [r for r in brut if r["type"] == "CRE" and (r["date"] or "") < "2019-07-02"]
    assert {r["famille"] for r in f} == {"rapports", "resolutions", "questions"}
    assert {r["role_pe"] for r in f if r["famille"] == "rapports"} == {"rapporteur"}
    assert bilan["R-ACTIVITE-PE"]["couverture"]["candidats_avec_activite"] == [2, 2]
