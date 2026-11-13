"""Mandats de député antérieurs au 19/06/2002, lus dans Sycomore (décision Q36 du 13/11/2026).

Sycomore est « tous droits réservés » : aucune page réelle n'est recopiée ici. La page de test
est **fabriquée** : elle reproduit la structure observée le 13/11/2026 (`h1` du nom, `h2`
« Mandats à l'Assemblée nationale… » suivi de `dl` faits de paires `dt`/`dd`, dates en toutes
lettres « Du 1 juin 1997 au 18 juin 2002 »), avec des mandats inventés pour une personne inventée
et les mandats publics d'un ancien député, Nicolas Dupont-Aignan (1997-2002, puis 2002-2007)."""
import os

import orjson

from empreinte_src.collecte_sycomore import date_iso, faits_sycomore, relever_sycomore
from empreinte_src.depaquetage import _membre, depaqueter
from empreinte_src.entrepot import Entrepot
from empreinte_src.lecteurs import an_acteurs, sycomore
from empreinte_src.lecture import Lecture
from tests.test_europe_votes import SessionSimulee, TransportSimule
from tests.test_regles_e1 import EX, PAS, TOUTES, _ecrire_decision, _lignes, _relier

PAGE = """<html><body><div class="titre"><h1>Nicolas Dupont-Aignan</h1><span>1961 - </span></div>
<h2>Mandats à l&#039;Assemblée nationale ou à la Chambre des députés</h2>
<dl class="deputes-liste-attributs sycomore">
 <dt>Régime politique</dt> <dd>Cinquième République - Assemblée nationale</dd>
 <dt>Législature</dt> <dd> XIe législature </dd>
 <dt>Mandat</dt> <dd> Du 1 juin 1997 au 18 juin 2002 </dd>
 <dt>Département</dt> <dd>Essonne</dd>
 <dt>Groupe</dt> <dd>Rassemblement pour la République</dd></dl>
<dl class="deputes-liste-attributs sycomore">
 <dt>Régime politique</dt> <dd>Cinquième République - Assemblée nationale</dd>
 <dt>Législature</dt> <dd> XIIe législature </dd>
 <dt>Mandat</dt> <dd> Du 19 juin 2002 au 19 juin 2007 </dd>
 <dt>Département</dt> <dd>Essonne</dd>
 <dt>Groupe</dt> <dd>Union pour la majorité présidentielle</dd></dl>
<h2>Mandats au Sénat ou à la Chambre des pairs</h2>
<dl class="deputes-liste-attributs sycomore">
 <dt>Mandat</dt> <dd> du 1er octobre 1990 au 30 septembre 1999 </dd>
 <dt>Département</dt> <dd>Inventé</dd></dl>
<h2>Contenus annexes</h2><p>Biographie : non reprise.</p></body></html>"""
PA_SYC = {"id": "sycomore-fiches", "source": "sycomore", "type": "fiches_sycomore",
          "format": "sycomore_fiches", "url": "https://www2.assemblee-nationale.fr/sycomore/fiche"}


def test_dates_en_toutes_lettres():
    assert date_iso("Du 1 juin 1997") == "1997-06-01"
    assert date_iso("du 1er octobre 1990") == "1990-10-01"
    assert date_iso("le 18 août 2002") == "2002-08-18"
    assert date_iso("") is None


def test_faits_de_la_fiche():
    f = faits_sycomore(PAGE, "2721")
    assert (f["nom"], f["url"], len(f["mandats"])) == (
        "Nicolas Dupont-Aignan", "https://www2.assemblee-nationale.fr/sycomore/fiche?num_dept=2721", 3)
    m = f["mandats"][0]
    assert (m["chambre"], m["legislature"], m["debut"], m["fin"], m["departement"], m["groupe"]) == (
        "assemblee", "XIe législature", "1997-06-01", "2002-06-18", "Essonne", "Rassemblement pour la République")
    assert f["mandats"][2]["chambre"] == "senat" and f["mandats"][2]["debut"] == "1990-10-01"
    # Rien d'autre de la page : ni biographie ni contenus annexes.
    assert "Biographie" not in orjson.dumps(f).decode()


def _sparql(paires):
    return orjson.dumps({"head": {"vars": ["item", "sycomore"]}, "results": {"bindings": [
        {"item": {"type": "uri", "value": f"http://www.wikidata.org/entity/{q}"},
         "sycomore": {"type": "literal", "value": i}} for q, i in paires]}})


def _decisions(d):
    _ecrire_decision(os.path.join(str(d), "candidature"), [
        {"nom": "Nicolas Dupont-Aignan", "statut": "declaree", "wikidata": "Q12961",
         "article_frwiki": "Nicolas Dupont-Aignan"},
        {"nom": "Eric Zemmour", "statut": "declaree", "wikidata": "Q288477", "article_frwiki": "Éric Zemmour"}])
    return str(d)


def test_releve_garde_les_faits_pas_la_page(tmp_path):
    d = _decisions(tmp_path / "d")
    e = Entrepot(str(tmp_path / "e"))
    s = SessionSimulee({"query.wikidata.org": (200, _sparql([("Q12961", "2721")])),
                        "num_dept=2721": (200, PAGE.encode())})
    r = relever_sycomore(e, TransportSimule(s), PA_SYC, {}, dossier_decisions=d, pause_s=0)
    assert (r["issue"], r["complet"], r["nb_membres"]) == ("nouveau", True, 2)
    e.clore("t")
    e = Entrepot(str(tmp_path / "e"))
    emp = e.presents("sycomore-fiches")["sycomore-2721"]["empreinte"]
    octets = e.lire_octets(emp)
    assert b"<html" not in octets and orjson.loads(octets)["extracteur"] == "sycomore@1"


def test_fiche_illisible_echec(tmp_path):
    d = _decisions(tmp_path / "d")
    e = Entrepot(str(tmp_path / "e"))
    s = SessionSimulee({"query.wikidata.org": (200, _sparql([("Q12961", "2721")])),
                        "num_dept=2721": (200, b"<html>page changee</html>")})
    r = relever_sycomore(e, TransportSimule(s), PA_SYC, {}, dossier_decisions=d, pause_s=0)
    assert r["issue"] == "echec" and "nom introuvable" in r["message"]
    assert e.presents("sycomore-fiches") == {}


def test_frise_avant_2002_et_couverture(tmp_path):
    e = Entrepot(str(tmp_path / "e"))
    e.versionner(PAS["amo"][0], "R0", depaqueter(os.path.join(EX, "amo30_l17_candidats_e1.zip"), "zip"),
                 complet=True)
    e.versionner(PA_SYC, "R1", [
        _membre("wikidata-p1045", "wikidata-p1045.json", _sparql([("Q12961", "2721")])),
        _membre("sycomore-2721", "sycomore/2721.json", orjson.dumps(faits_sycomore(PAGE, "2721")))],
        complet=True, delta=True)
    e.clore("t")
    cfg = {"points_acces": [{"id": "an-amo30-l17", "licence": "etalab-2.0"},
                            {"id": "sycomore-fiches", "licence": None}]}
    lect = Lecture(Entrepot(str(tmp_path / "e")), str(tmp_path / "z2"), cfg)
    for m in (an_acteurs, sycomore):
        assert lect.executer(m)["illisibles"] == 0
    ctx, bilan, _ = _relier(tmp_path / "z2", tmp_path / "z3", tmp_path / "r", TOUTES, decisions=_decisions(tmp_path / "d"))
    c = {r["nom_liste"]: r["per"] for r in _lignes(ctx, "SELECT nom_liste, per FROM candidat")}
    l = _lignes(ctx, "SELECT * FROM carriere WHERE institution = 'assemblee_avant_2002'")
    # Le seul mandat d'avant le 19/06/2002 ; celui de 2002-2007 vient de l'archive des acteurs.
    assert [(x["per"], x["debut"], x["fin"], x["libelle"], x["groupe_libelle"], x["source"]) for x in l] == [
        (c["Nicolas Dupont-Aignan"], "1997-06-01", "2002-06-18", "Député · XIe législature · Essonne",
         "Rassemblement pour la République", "sycomore")]
    assert l[0]["source_url"] == "https://www2.assemblee-nationale.fr/sycomore/fiche?num_dept=2721"
    cov = {(r["per"]): r["statut"] for r in _lignes(
        ctx, "SELECT per, statut FROM couverture_carriere WHERE institution = 'assemblee_avant_2002'")}
    assert cov[c["Nicolas Dupont-Aignan"]] == "complet" and cov[c["Eric Zemmour"]] == "aucun_identifiant"
    assert bilan["R-CARRIERE"]["couverture"]["mandats_anterieurs_a_2002_lus_dans_sycomore"] == [1, 1]
