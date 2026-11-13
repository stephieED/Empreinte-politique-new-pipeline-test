"""Volet européen, lot 2 : votes nominatifs au Parlement européen depuis juillet 2019 (décisions Q3
et Q33 du 13/11/2026).

Collecte `relever_votes` (session HTTP simulée), lecteur `pe_votes` et R-VOTE-PE, sur l'extrait
réel `pe_eurodeputes/decisions-MTG-PL-2019-09-19.json` (16 votes nominatifs, fiche
`pe_eurodeputes.md`) et la fiche réelle de Raphaël Glucksmann."""
import os

import orjson
import pytest

from empreinte_src.collecte_pe import relever_votes, seances_a_relire
from empreinte_src.depaquetage import _membre, depaqueter
from empreinte_src.entrepot import Entrepot
from empreinte_src.lecteurs import an_acteurs, pe_eurodeputes, pe_votes
from empreinte_src.lecture import Lecture
from empreinte_src.regles import r_vote_pe
from tests.test_europe_mandats import PA_PE, _lire
from tests.test_regles_e1 import EX, PAS, TOUTES, _ecrire_decision, _lignes, _relier

PA_VOTES = {"id": "pe-votes", "source": "europarl", "type": "votes_pe", "format": "pe_votes",
            "url": "https://data.europarl.europa.eu/api/v2/meetings", "depuis": "2019-07-02",
            "fenetre_jours": 60, "budget_s": 2400}


class _Rep:
    def __init__(self, code, octets):
        self.status_code, self.content = code, octets


class SessionSimulee:
    def __init__(self, reponses, defaut=(404, b"")):
        self.reponses, self.defaut, self.adresses = reponses, defaut, []

    def get(self, url, timeout=None):
        self.adresses.append(url)
        for motif, (code, octets) in self.reponses.items():
            if motif in url:
                return _Rep(code, octets)
        return _Rep(*self.defaut)


class TransportSimule:
    def __init__(self, session):
        self.session, self.delai_s = session, 1


def _seances(ids):
    return orjson.dumps({"data": [{"id": f"eli/dl/event/{i}", "activity_id": i,
                                   "activity_date": i[7:17]} for i in ids]})


# =========================== Collecte ===========================================================

def test_seances_a_relire():
    s = ["MTG-PL-2019-07-01", "MTG-PL-2019-07-02", "MTG-PL-2026-09-01", "MTG-PL-2026-11-10",
         "MTG-PL-2026-12-14"]
    deja = {"decisions-MTG-PL-2019-07-02", "decisions-MTG-PL-2026-09-01", "decisions-MTG-PL-2026-11-10"}
    # Avant le début : non ; ancienne et déjà rangée : non ; récente : relue ; à venir : non.
    assert seances_a_relire(s, deja, "2019-07-02", "2026-11-13", 60) == ["MTG-PL-2026-11-10"]
    assert seances_a_relire(s, set(), "2019-07-02", "2026-11-13", 60) == [
        "MTG-PL-2019-07-02", "MTG-PL-2026-09-01", "MTG-PL-2026-11-10"]


def _session():
    dec = _lire("decisions-MTG-PL-2019-09-19.json")
    return SessionSimulee({
        "meetings?year=2019": (200, _seances(["MTG-PL-2019-09-16", "MTG-PL-2019-09-19"])),
        "meetings?year=2020": (204, b""),
        "MTG-PL-2019-09-19/decisions": (200, dec)})


def test_releve_lundi_sans_decision_et_reprise(tmp_path):
    e = Entrepot(str(tmp_path / "e"))
    s = _session()
    r = relever_votes(e, TransportSimule(s), PA_VOTES, {}, pause_s=0, aujourd_hui="2020-03-01")
    assert (r["issue"], r["complet"], r["requetes"]) == ("nouveau", True, 4)
    pres = e.presents("pe-votes")
    assert set(pres) == {"seances-2019", "seances-2020", "decisions-MTG-PL-2019-09-16",
                         "decisions-MTG-PL-2019-09-19"}
    assert pres["decisions-MTG-PL-2019-09-16"]["taille"] == 0      # le lundi : réponse vide, gardée
    e.clore("t")
    # La nuit suivante : séances anciennes déjà rangées, seules les listes annuelles sont relues.
    e = Entrepot(str(tmp_path / "e"))
    s2 = _session()
    r = relever_votes(e, TransportSimule(s2), PA_VOTES, {}, pause_s=0, aujourd_hui="2020-03-02")
    assert r["requetes"] == 2 and r["nb_nouvelles_versions"] == 0
    assert not any("decisions" in u for u in s2.adresses)


def test_budget_atteint_puis_suite(tmp_path):
    e = Entrepot(str(tmp_path / "e"))
    temps = iter([0, 0, 0, 0, 5000, 5000, 5000, 5000, 5000])
    r = relever_votes(e, TransportSimule(_session()), {**PA_VOTES, "budget_s": 100}, {}, pause_s=0,
                      aujourd_hui="2020-03-01", horloge=lambda: next(temps, 5000))
    assert (r["issue"], r["complet"]) == ("nouveau", False)
    assert "budget" in r["message"]


def test_erreur_du_serveur_echec_mais_rien_de_perdu(tmp_path):
    e = Entrepot(str(tmp_path / "e"))
    s = _session()
    s.reponses["MTG-PL-2019-09-19/decisions"] = (503, b"")
    import empreinte_src.collecte_pe as cp
    ancien = cp._obtenir_brut.__defaults__
    cp._obtenir_brut.__defaults__ = (3, (0, 0))
    try:
        r = relever_votes(e, TransportSimule(s), PA_VOTES, {}, pause_s=0, aujourd_hui="2020-03-01")
    finally:
        cp._obtenir_brut.__defaults__ = ancien
    assert (r["issue"], r["complet"]) == ("echec", False)
    assert "HTTP 503" in r["message"]
    # Ce qui a été reçu avant l'erreur est rangé : la nuit suivante reprend là.
    assert "decisions-MTG-PL-2019-09-16" in e.presents("pe-votes")


# =========================== Lecteur et R-VOTE-PE ===============================================

def _z2(d):
    e = Entrepot(str(d / "e"))
    e.versionner(PAS["amo"][0], "R0", depaqueter(os.path.join(EX, "amo30_l17_candidats_e1.zip"), "zip"),
                 complet=True)
    e.versionner(PA_PE, "R1", [_membre("wikidata-p1186", "wikidata-p1186.json", _lire("wikidata-p1186.json")),
                               _membre("mep-197694", "meps/197694.json", _lire("meps-197694.json"))],
                 complet=True, delta=True)
    e.versionner(PA_VOTES, "R2", [
        _membre("decisions-MTG-PL-2019-09-19", "x", _lire("decisions-MTG-PL-2019-09-19.json")),
        _membre("decisions-MTG-PL-2019-09-16", "x", b"")], complet=True, delta=True)
    e.clore("test")
    cfg = {"points_acces": [{"id": "an-amo30-l17", "licence": "etalab-2.0"},
                            {"id": "pe-eurodeputes", "licence": "cc-by-4.0"},
                            {"id": "pe-votes", "licence": "cc-by-4.0"}]}
    lect = Lecture(Entrepot(str(d / "e")), str(d / "z2"), cfg)
    for m in (an_acteurs, pe_eurodeputes, pe_votes):
        assert lect.executer(m)["illisibles"] == 0
    return d / "z2"


def test_lecteur_votes_et_listes(tmp_path):
    z2 = _z2(tmp_path)
    import duckdb
    con = duckdb.connect()
    v = con.sql(f"SELECT nominatif, seance FROM '{z2}/pe_votes__vote_pe.parquet'").fetchall()
    assert len(v) == 16 and all(n for n, _ in v) and {x for _, x in v} == {"MTG-PL-2019-09-19"}
    p = dict(con.sql(f"""SELECT position, sum(len(personnes)) FROM '{z2}/pe_votes__position_pe.parquet'
                         GROUP BY 1""").fetchall())
    assert {"favor", "against", "abstention"} <= set(p)
    # Les listes publiées de ce jour : 653 votants par vote en médiane (mesure du 13/11/2026).
    assert 16 * 600 < p["favor"] + p["against"] + p["abstention"] < 16 * 700


@pytest.mark.parametrize("objet, nature", [
    ("Résolution", "ensemble"), ("Proposition de résolution (ensemble du texte)", "ensemble"),
    ("Proposition de la Commission", "ensemble"), ("Accord provisoire", "ensemble"),
    ("Am 12", "partie"), ("am 3S", "partie"), ("§ 69/1", "partie"), ("Considérant G/2", "partie"),
    ("Visa 4", "partie"), ("Bloc 3", "partie"), ("Procédure d'approbation", "ensemble"),
    ("Motion for a resolution (text as a whole)", "ensemble"), ("Vote final", "ensemble"),
    ("Demande de procéder au vote sur les amendements", "procedure"),
    ("Renvoi (article 59, paragraphe 4 du règlement)", "procedure"), ("Antrag der ECR-Fraktion", "procedure"),
    ("approbation", "ensemble"), ("vote : approbation", "ensemble"), ("Proposition modifiée", "ensemble"),
    ("proposition Commission", "ensemble"), ("AFCO résolution", "ensemble"), ("par. 10", "partie"),
    ("cons. B/1", "partie"), ("Vote procédural", "procedure"), ("Modification de l'ordre du jour", "procedure"),
    ("Gaza", "non_etablie")])
def test_nature_du_vote(objet, nature):
    import duckdb
    litteral = "'" + objet.replace("'", "''") + "'"
    assert duckdb.sql(f"SELECT {r_vote_pe.nature_sql(litteral)}").fetchall()[0][0] == nature


def test_votes_de_glucksmann(tmp_path):
    z2 = _z2(tmp_path)
    d = tmp_path / "d"
    _ecrire_decision(os.path.join(str(d), "candidature"), [
        {"nom": "Raphaël Glucksmann", "statut": "declaree", "wikidata": "Q556149",
         "article_frwiki": "Raphaël Glucksmann"},
        {"nom": "Eric Zemmour", "statut": "declaree", "wikidata": "Q288477", "article_frwiki": "Éric Zemmour"}])
    ctx, bilan, _ = _relier(z2, tmp_path / "z3", tmp_path / "r", TOUTES + [r_vote_pe], decisions=d)
    rows = _lignes(ctx, "SELECT * FROM vote_personne_pe ORDER BY numero")
    assert len(rows) == 16 and {r["eurodepute"] for r in rows} == {"197694"}
    assert all(r["position"] in ("pour", "contre", "abstention") for r in rows)
    nat = {}
    for r in rows:
        nat[r["nature"]] = nat.get(r["nature"], 0) + 1
    assert nat == {"partie": 13, "ensemble": 3}
    assert all(r["date"] == "2019-09-19" and r["source_url"].startswith("https://data.europarl.europa.eu/")
               for r in rows)
    assert bilan["R-VOTE-PE"]["couverture"]["nature_etablie"] == [16, 16]
