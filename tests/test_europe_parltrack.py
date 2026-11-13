"""Volet européen, lot 3 : votes nominatifs de Parltrack avant le 02/07/2019 (décision Q3).

Lecteur `parltrack_votes` et R-VOTE-PE sur l'extrait réel `parltrack_ep_votes_extrait.json.zst`
(cinq scrutins de décembre 2004, fiche `parltrack_ep_votes_extrait.md`) et la fiche réelle de
Marine Le Pen au portail du PE (`pe_eurodeputes/meps-28210.json`)."""
import os

import pyarrow.parquet as pq

from empreinte_src.depaquetage import _membre, depaqueter
from empreinte_src.entrepot import Entrepot
from empreinte_src.lecteurs import an_acteurs, parltrack_votes, pe_eurodeputes
from empreinte_src.lecture import Lecture
from empreinte_src.regles import r_vote_pe
from tests.test_europe_mandats import PA_PE, _lire
from tests.test_regles_e1 import EX, PAS, TOUTES, _ecrire_decision, _lignes, _relier

PA_PT = {"id": "parltrack-votes", "source": "parltrack", "type": "votes_parltrack", "format": "fichier",
         "url": "https://parltrack.org/dumps/ep_votes.json.zst", "uid": "ep_votes"}


def _z2(d):
    e = Entrepot(str(d / "e"))
    e.versionner(PAS["amo"][0], "R0", depaqueter(os.path.join(EX, "amo30_l17_candidats_e1.zip"), "zip"),
                 complet=True)
    e.versionner(PA_PE, "R1", [_membre("wikidata-p1186", "wikidata-p1186.json", _lire("wikidata-p1186.json")),
                               _membre("mep-28210", "meps/28210.json", _lire("meps-28210.json"))],
                 complet=True, delta=True)
    with open(os.path.join(EX, "parltrack_ep_votes_extrait.json.zst"), "rb") as f:
        e.versionner(PA_PT, "R2", [_membre("ep_votes", "ep_votes.json.zst", f.read())], complet=True)
    e.clore("test")
    cfg = {"points_acces": [{"id": "an-amo30-l17", "licence": "etalab-2.0"},
                            {"id": "pe-eurodeputes", "licence": "cc-by-4.0"},
                            {"id": "parltrack-votes", "licence": "odbl-1.0"}]}
    lect = Lecture(Entrepot(str(d / "e")), str(d / "z2"), cfg)
    for m in (an_acteurs, pe_eurodeputes, parltrack_votes):
        assert lect.executer(m)["illisibles"] == 0
    return d / "z2"


def test_lecteur_scrutins_et_listes(tmp_path):
    z2 = _z2(tmp_path)
    v = {r["vote"]: r for r in pq.read_table(z2 / "parltrack_votes__vote_pt.parquet").to_pylist()}
    assert set(v) == {"pt-7754", "pt-7818", "pt-7759", "pt-7755", "pt-7760"}
    d = v["pt-7759"]
    assert (d["date"], d["document_ref"], d["objet"], d["licence"]) == (
        "2004-12-14", "A6-0034/2004", "résolution", "odbl-1.0")
    assert d["prov_url"].startswith("http://www.europarl.europa.eu/RegData/seance_pleniere/proces_verbal/2004/12-14/")
    p = pq.read_table(z2 / "parltrack_votes__position_pt.parquet").to_pylist()
    assert {r["position"] for r in p} == {"favor", "against", "abstention"}
    tot = {(r["vote"], r["position"]): len(r["personnes"]) for r in p}
    # Le total publié est celui des listes aplaties.
    assert tot[("pt-7759", "favor")] == d["pour"]


def test_votes_de_le_pen_avant_2019(tmp_path):
    z2 = _z2(tmp_path)
    dec = tmp_path / "d"
    _ecrire_decision(os.path.join(str(dec), "candidature"), [
        {"nom": "Marine Le Pen", "statut": "declaree", "wikidata": "Q12927", "article_frwiki": "Marine Le Pen"}])
    ctx, bilan, _ = _relier(z2, tmp_path / "z3", tmp_path / "r", TOUTES + [r_vote_pe], decisions=dec)
    rows = _lignes(ctx, "SELECT * FROM vote_personne_pe ORDER BY date")
    assert {r["source"] for r in rows} == {"parltrack"} and {r["source_point"] for r in rows} == {"parltrack-votes"}
    assert {r["eurodepute"] for r in rows} == {"28210"}
    nat = {r["vote"]: r["nature"] for r in rows}
    assert nat["pt-7759"] == "ensemble" and nat["pt-7760"] == "partie"
    assert all(r["position"] in ("pour", "contre", "abstention") for r in rows)
    assert bilan["R-VOTE-PE"]["couverture"]["votes_parltrack"][0] == len(rows)


def test_bascule_au_2_juillet_2019(tmp_path):
    """Un scrutin Parltrack daté après la bascule n'est pas lu (le portail le donne)."""
    z2 = _z2(tmp_path)
    t = pq.read_table(z2 / "parltrack_votes__vote_pt.parquet").to_pylist()
    k = next(i for i, r in enumerate(t) if r["vote"] == "pt-7759")      # Le Pen y vote
    t[k]["date"] = "2019-07-03"
    import pyarrow as pa
    pq.write_table(pa.Table.from_pylist(t, schema=pq.read_schema(z2 / "parltrack_votes__vote_pt.parquet")),
                   z2 / "parltrack_votes__vote_pt.parquet")
    dec = tmp_path / "d"
    _ecrire_decision(os.path.join(str(dec), "candidature"), [
        {"nom": "Marine Le Pen", "statut": "declaree", "wikidata": "Q12927", "article_frwiki": "Marine Le Pen"}])
    ctx, _, _ = _relier(z2, tmp_path / "z3", tmp_path / "r", TOUTES + [r_vote_pe], decisions=dec)
    lus = {r[0] for r in ctx.x("SELECT vote FROM vote_personne_pe")}
    assert "pt-7759" not in lus and "pt-7755" in lus
