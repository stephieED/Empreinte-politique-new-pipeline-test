"""Volet européen, lot 1 : mandats de député européen des candidats (décision Q3 du 13/11/2026).

Collecte (`collecte_pe`, transport simulé), lecteur `pe_eurodeputes` et R-CARRIERE sur les
extraits réels de `tests/extraits/pe_eurodeputes/` (fiche `pe_eurodeputes.md`)."""
import os
import tempfile

import orjson

from empreinte_src.collecte_pe import (elements_de_la_liste, groupes_cites, identifiants_pe,
                                       relever_eurodeputes, requete_p1186)
from empreinte_src.depaquetage import _membre, depaqueter
from empreinte_src.entrepot import Entrepot
from empreinte_src.lecteurs import an_acteurs, pe_eurodeputes
from empreinte_src.lecture import Lecture
from empreinte_src.transport import Reponse
from tests.test_regles_e1 import EX, PAS, TOUTES, _ecrire_decision, _lignes, _relier

PE = os.path.join(EX, "pe_eurodeputes")
PA_PE = {"id": "pe-eurodeputes", "source": "europarl", "type": "eurodeputes_pe",
         "format": "pe_eurodeputes", "url": "https://data.europarl.europa.eu/api/v2/"}


def _lire(nom):
    with open(os.path.join(PE, nom), "rb") as f:
        return f.read()


def _sparql(paires):
    return orjson.dumps({"head": {"vars": ["item", "pe"]}, "results": {"bindings": [
        {"item": {"type": "uri", "value": f"http://www.wikidata.org/entity/{q}"},
         "pe": {"type": "literal", "value": i}} for q, i in paires]}})


class TransportSimule:
    """Rend des octets selon l'adresse ; `echec` : un morceau d'adresse qui échoue."""

    def __init__(self, reponses, echec=None):
        self.reponses, self.echec, self.adresses = reponses, echec, []
        self.session, self.delai_s = self, 1

    def get(self, url, timeout=None):
        """Requête directe (interventions en séance) : rend la réponse simulée, sinon 204."""
        self.adresses.append(url)
        for motif, octets in self.reponses.items():
            if motif in url:
                return type("R", (), {"status_code": 200, "content": octets})()
        return type("R", (), {"status_code": 204, "content": b""})()

    def telecharger(self, url, etag=None, last_modified=None):
        self.adresses.append(url)
        if self.echec and self.echec in url:
            return Reponse(url=url, issue="echec", statut_http=503, message="HTTP 503")
        for motif, octets in self.reponses.items():
            if motif in url:
                fd, chemin = tempfile.mkstemp()
                with os.fdopen(fd, "wb") as f:
                    f.write(octets)
                return Reponse(url=url, issue="nouveau", statut_http=200, chemin=chemin,
                               taille=len(octets), octets_recus=len(octets))
        return Reponse(url=url, issue="echec", statut_http=404, message="HTTP 404")


def _reponses():
    r = {"query.wikidata.org": _sparql([("Q12927", "28210")]), "meps/28210": _lire("meps-28210.json")}
    for g in ("1541", "2345", "2978", "3968", "4908"):
        r[f"corporate-bodies/{g}?"] = _lire(f"org-{g}.json")
    return r


def _decisions(dossier, entrees):
    _ecrire_decision(os.path.join(str(dossier), "candidature"), entrees)
    return str(dossier)


# =========================== Collecte ===========================================================

def test_elements_et_requete(tmp_path):
    d = _decisions(tmp_path / "d", [{"nom": "Marine Le Pen", "statut": "declaree", "wikidata": "Q12927"},
                                    {"nom": "Autre", "statut": "retiree", "wikidata": "Q5829"},
                                    {"nom": "Sans", "statut": "declaree"}])
    assert elements_de_la_liste(d) == ["Q5829", "Q12927"]          # tous statuts, triés
    assert "VALUES%20%3Fitem%20%7B%20wd%3AQ5829%20wd%3AQ12927" in requete_p1186(["Q5829", "Q12927"])
    ids = identifiants_pe(_lire("wikidata-p1186.json"))
    assert ids["Q12927"] == ["28210"] and ids["Q556149"] == ["197694"] and len(ids) == 6
    assert groupes_cites(_lire("meps-28210.json")) == ["1541", "2345", "2978", "3968", "4908"]


def test_releve_complet_puis_inchange(tmp_path):
    d = _decisions(tmp_path / "d", [{"nom": "Marine Le Pen", "statut": "declaree", "wikidata": "Q12927"}])
    e = Entrepot(str(tmp_path / "e"))
    t = TransportSimule(_reponses())
    r = relever_eurodeputes(e, t, PA_PE, {}, dossier_decisions=d, pause_s=0)
    assert (r["issue"], r["complet"], r["nb_membres"], r["nb_nouvelles_versions"]) == ("nouveau", True, 7, 7)
    assert set(e.presents("pe-eurodeputes")) == {"wikidata-p1186", "mep-28210", "org-1541", "org-2345",
                                                 "org-2978", "org-3968", "org-4908"}
    assert all("format=application%2Fld%2Bjson" in u for u in t.adresses[1:])
    e.clore("test")
    # Mêmes octets la nuit suivante : aucune version nouvelle. La personne sort de la liste :
    # rien n'est retiré (ses données restent, cahier 4.1).
    e = Entrepot(str(tmp_path / "e"))
    r = relever_eurodeputes(e, TransportSimule(_reponses()), PA_PE, {}, dossier_decisions=d, pause_s=0)
    assert (r["nb_nouvelles_versions"], r["nb_inchanges"]) == (0, 7)
    vide = _decisions(tmp_path / "d2", [{"nom": "Marine Le Pen", "statut": "non_listee", "wikidata": "Q12927"}])
    r = relever_eurodeputes(e, TransportSimule({"query.wikidata.org": _sparql([])}), PA_PE, {},
                            dossier_decisions=vide, pause_s=0)
    assert r["issue"] == "nouveau" and r["nb_retraits"] == 0
    assert "mep-28210" in e.presents("pe-eurodeputes")


def test_une_reponse_en_echec_ne_range_rien(tmp_path):
    d = _decisions(tmp_path / "d", [{"nom": "Marine Le Pen", "statut": "declaree", "wikidata": "Q12927"}])
    e = Entrepot(str(tmp_path / "e"))
    r = relever_eurodeputes(e, TransportSimule(_reponses(), echec="corporate-bodies/3968"), PA_PE, {},
                            dossier_decisions=d, pause_s=0)
    assert (r["issue"], r["complet"]) == ("echec", False)
    assert "corporate-bodies/3968" in r["message"]
    assert e.presents("pe-eurodeputes") == {}


# =========================== Lecteur et R-CARRIERE ==============================================

def _z2(d):
    e = Entrepot(str(d / "e"))
    e.versionner(PAS["amo"][0], "R0", depaqueter(os.path.join(EX, "amo30_l17_candidats_e1.zip"), "zip"),
                 complet=True)
    membres = [_membre("wikidata-p1186", "wikidata-p1186.json", _lire("wikidata-p1186.json")),
               _membre("mep-28210", "meps/28210.json", _lire("meps-28210.json")),
               _membre("mep-197694", "meps/197694.json", _lire("meps-197694.json"))]
    membres += [_membre(f"org-{g}", f"corporate-bodies/{g}.json", _lire(f"org-{g}.json"))
                for g in ("1541", "2345", "2978", "3968", "4908")]
    e.versionner(PA_PE, "R1", membres, complet=True, delta=True)
    e.clore("test")
    cfg = {"points_acces": [{"id": "an-amo30-l17", "licence": "etalab-2.0"},
                            {"id": "pe-eurodeputes", "licence": "cc-by-4.0"}]}
    lect = Lecture(Entrepot(str(d / "e")), str(d / "z2"), cfg)
    for m in (an_acteurs, pe_eurodeputes):
        b = lect.executer(m)
        assert b["illisibles"] == 0
    return d / "z2"


def test_lecteur_appartenances_et_groupes(tmp_path):
    z2 = _z2(tmp_path)
    import duckdb
    con = duckdb.connect()
    app = con.sql(f"SELECT * FROM '{z2}/pe_eurodeputes__appartenance_pe.parquet' WHERE personne = '28210'").fetchall()
    assert len(app) == 40
    mand = con.sql(f"""SELECT organisation, debut, fin FROM '{z2}/pe_eurodeputes__appartenance_pe.parquet'
                       WHERE personne = '28210' AND role = 'MEMBER_PARLIAMENT' ORDER BY debut""").fetchall()
    assert mand == [("org/ep-6", "2004-07-20", "2009-07-13"), ("org/ep-7", "2009-07-14", "2014-06-30"),
                    ("org/ep-8", "2014-07-01", "2017-06-18")]
    g = dict(con.sql(f"SELECT organisation, libelle FROM '{z2}/pe_eurodeputes__groupe_pe.parquet'").fetchall())
    assert g["org/4908"] == "Groupe Europe des Nations et des Libertés"
    p = con.sql(f"SELECT genre, naissance FROM '{z2}/pe_eurodeputes__eurodepute.parquet' WHERE personne = '28210'").fetchall()
    assert p == [("FEMALE", "1968-08-05")]


def test_frise_europeenne_le_pen_et_couverture(tmp_path):
    z2 = _z2(tmp_path)
    d = _decisions(tmp_path / "d", [
        {"nom": "Marine Le Pen", "statut": "declaree", "wikidata": "Q12927", "article_frwiki": "Marine Le Pen"},
        {"nom": "Raphaël Glucksmann", "statut": "declaree", "wikidata": "Q556149", "article_frwiki": "Raphaël Glucksmann"},
        {"nom": "Eric Zemmour", "statut": "declaree", "wikidata": "Q288477", "article_frwiki": "Éric Zemmour"}])
    ctx, bilan, _ = _relier(z2, tmp_path / "z3", tmp_path / "r", TOUTES, decisions=d)
    c = {r["nom"]: r for r in _lignes(ctx, "SELECT nom, per, eurodepute, eurodepute_connu_pe FROM candidat")}
    assert (c["Marine Le Pen"]["eurodepute"], c["Marine Le Pen"]["eurodepute_connu_pe"]) == ("28210", True)
    assert c["Éric Zemmour"]["eurodepute"] is None
    lp = _lignes(ctx, """SELECT debut, fin, libelle, groupe_sigle, groupe_libelle, groupe_statut, source,
                                legislature, lien, source_url
                         FROM carriere WHERE per = ? AND institution = 'parlement_europeen'
                         ORDER BY debut""", [c["Marine Le Pen"]["per"]])
    # ep-6 découpée par ses trois groupes (NI, ITS, NI) ; ep-7 NI ; ep-8 NI, puis ENF.
    assert [(l["debut"], l["fin"], l["groupe_sigle"]) for l in lp] == [
        ("2004-07-20", "2007-01-14", "NI"), ("2007-01-15", "2007-11-13", "ITS"),
        ("2007-11-14", "2009-07-13", "NI"), ("2009-07-14", "2014-06-30", "NI"),
        ("2014-07-01", "2015-06-14", "NI"), ("2015-06-15", "2017-06-18", "ENF")]
    assert lp[0]["libelle"] == "Députée européenne · 6e législature européenne"
    assert lp[0]["groupe_statut"] == "non_inscrit" and lp[1]["groupe_statut"] == "groupe"
    assert all(l["source"] == "pe" and l["legislature"] is None and l["lien"] is None for l in lp)
    assert lp[0]["source_url"] == "https://www.europarl.europa.eu/meps/fr/28210"
    cov = {(r["per"], r["institution"]): r["statut"] for r in _lignes(ctx, "SELECT * FROM couverture_carriere")}
    assert cov[(c["Marine Le Pen"]["per"], "parlement_europeen")] == "complet"
    assert cov[(c["Éric Zemmour"]["per"], "parlement_europeen")] == "aucun_identifiant"
    g = _lignes(ctx, """SELECT debut, fin FROM carriere WHERE per = ? AND institution = 'parlement_europeen'
                        ORDER BY debut""", [c["Raphaël Glucksmann"]["per"]])
    assert g and g[0]["debut"].startswith("2019-07")
    assert bilan["R-CARRIERE"]["couverture"]["mandats_europeens_lus"] == [2, 2]
