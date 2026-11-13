"""Règles du groupe E1 (identité, périmètre, carrière, fonctions des candidats) : R-CANDIDATURES,
R-IDENTITE, R-CARRIERE, R-FONCTIONS.

Sur des extraits réels lus par les vrais lecteurs :
- `amo30_l17_candidats_e1.zip` (fiche `amo30_l17_candidats_e1.md`) : François Ruffin et Bruno
  Retailleau, et les organes de leurs mandats ;
- `wp_candidatures_section1.json` (+ les deux lignes « Candidatures retirées » recopiées de la
  révision 241073157, comme dans `test_lecteur_wp_candidatures.py`) ;
- `wd_identifiants_extrait.json`, `senat_export_extrait.zip` ;
et sur de petites tables écrites ici quand l'extrait ne couvre pas le cas.

Depuis le 13/11/2026, la liste des candidats est une décision `candidature` (recopiée de
franceinfo). Sauf mention contraire, chaque test reçoit une décision faite de la liste de
Wikipédia qu'il lit (`_decision_depuis_wp`) : article cité, ou nom écrit, sans élément inscrit,
ce qui reproduit la chaîne de la version 1 (article -> élément -> identifiants)."""
import os
import random
import shutil
import tempfile

import orjson
import pyarrow as pa
import yaml
import pyarrow.parquet as pq
import pytest

from empreinte_src.depaquetage import depaqueter
from empreinte_src.entrepot import Entrepot
from empreinte_src.identites import RegistreIdentites
from empreinte_src.lecteurs import an_acteurs, senat_export, wd_identifiants, wp_candidatures
from empreinte_src.lecture import COLONNES_PROVENANCE, Lecture
from empreinte_src.liaison import Contexte, ordonner, relier
from empreinte_src.regles import (r_appartenance, r_candidatures, r_carriere, r_composition,
                                  r_deputes, r_fonctions, r_gouvernements, r_hemicycle,
                                  r_identite, r_legislatures)
from tests.test_lecteur_wp_candidatures import RETIREES

EX = os.path.join(os.path.dirname(__file__), "extraits")
PAS = {
    "amo": ({"id": "an-amo30-l17", "source": "an", "type": "acteurs_organes", "format": "zip",
             "url": "http://exemple.invalid/AMO30.json.zip"}, "etalab-2.0"),
    "wp": ({"id": "wp-candidatures-2027", "source": "wikipedia", "type": "candidatures",
            "format": "api_json", "url": "http://exemple.invalid/api.php"}, "cc-by-sa-4.0"),
    "wd": ({"id": "wd-identifiants-parlementaires", "source": "wikidata",
            "type": "identifiants_wikidata", "format": "api_json",
            "url": "http://exemple.invalid/sparql"}, "cc0-1.0"),
    "senat": ({"id": "senat-export", "source": "senat", "type": "export_sens", "format": "zip",
               "url": "http://exemple.invalid/export_sens.zip"}, "etalab-2.0"),
}
TOUTES = [r_legislatures, r_gouvernements, r_composition, r_appartenance, r_deputes, r_hemicycle,
          r_candidatures, r_identite, r_carriere, r_fonctions]


def _page_wp(dossier):
    """La section réelle « Candidats déclarés » suivie des deux candidatures retirées réelles."""
    o = orjson.loads(open(os.path.join(EX, "wp_candidatures_section1.json"), "rb").read())
    o["parse"]["wikitext"] = o["parse"]["wikitext"].rstrip("\n") + "\n\n" + RETIREES
    p = os.path.join(dossier, "candidatures.json")
    with open(p, "wb") as f:
        f.write(orjson.dumps(o))
    return p


def _z2_reel(d, sources=("amo", "wp", "wd", "senat")):
    e = Entrepot(str(d / "e"))
    fichiers = {"amo": (os.path.join(EX, "amo30_l17_candidats_e1.zip"), "zip", None),
                "wp": (_page_wp(str(d)), "api_json", "candidatures-2027"),
                "wd": (os.path.join(EX, "wd_identifiants_extrait.json"), "api_json", "identifiants"),
                "senat": (os.path.join(EX, "senat_export_extrait.zip"), "zip", None)}
    for s in sources:
        chemin, fmt, uid = fichiers[s]
        e.versionner(PAS[s][0], f"R{e.generation}", depaqueter(chemin, fmt, uid), complet=True)
    e.clore("test")
    cfg = {"points_acces": [{"id": PAS[s][0]["id"], "licence": PAS[s][1]} for s in sources]}
    lect = Lecture(Entrepot(str(d / "e")), str(d / "z2"), cfg)
    mods = {"amo": an_acteurs, "wp": wp_candidatures, "wd": wd_identifiants, "senat": senat_export}
    for s in sources:
        lect.executer(mods[s])
    return d / "z2"


LISTE_URL = "https://exemple.invalid/liste-des-candidats"


def _ecrire_decision(dossier, entrees, date="2026-11-13", nom_fichier=None):
    """Une décision `candidature` (forme du fichier réel), toutes les clés dans chaque entrée."""
    os.makedirs(dossier, exist_ok=True)
    cles = ("nom", "statut", "parti", "wikidata", "article_frwiki", "nom_wikipedia",
            "rattachement_par_nom", "note")
    d = {"type": "candidature", "election": "presidentielle-2027", "date": date,
         "source": "franceinfo", "source_url": LISTE_URL, "source_titre": "Liste d'essai",
         "decisions": [{k: e.get(k, False if k == "rattachement_par_nom" else None) for k in cles}
                       for e in entrees]}
    with open(os.path.join(dossier, nom_fichier or f"{date}-liste.yaml"), "w") as f:
        yaml.safe_dump(d, f, allow_unicode=True, sort_keys=False)
    return dossier


def _decision_depuis_wp(z2, dossier):
    """La liste de Wikipédia lue dans z2 (état courant), recopiée en décision."""
    p = os.path.join(str(z2), "wp_candidatures__candidature.parquet")
    entrees = []
    if os.path.exists(p):
        t = pq.read_table(p).to_pylist()
        der = {}
        for r in t:
            der[r["prov_uid"]] = max(der.get(r["prov_uid"], 0), r["prov_version"])
        for r in t:
            if r["prov_version"] == der[r["prov_uid"]] and r["prov_etat"] == "present":
                entrees.append({"nom": r["nom"], "statut": r["statut"], "article_frwiki": r["article"],
                                "nom_wikipedia": None if r["article"] else r["nom"]})
    return _ecrire_decision(dossier, entrees)


def _relier(z2, z3, registre_dir, mods=TOUTES, generation=1, registre=True, decisions=None):
    reg = RegistreIdentites(str(registre_dir)) if registre else None
    if decisions is None:
        decisions = _decision_depuis_wp(z2, os.path.join(str(z3) + "-decisions", "candidature"))
        decisions = os.path.dirname(decisions)
    ctx = Contexte(str(z2), str(z3), dossier_decisions=str(decisions), generation=generation,
                   date_reference="2026-11-06", registre=reg)
    bilan = relier(ctx, ordonner(mods))
    return ctx, {b["regle"].split("@")[0]: b for b in bilan}, reg


def _lignes(ctx, sql, params=None):
    r = ctx.con.execute(sql, params or [])
    cols = [x[0] for x in r.description]
    return [dict(zip(cols, x)) for x in r.fetchall()]


@pytest.fixture(scope="module")
def z2_reel(tmp_path_factory):
    return _z2_reel(tmp_path_factory.mktemp("e1"))


@pytest.fixture(scope="module")
def reel(z2_reel, tmp_path_factory):
    d = tmp_path_factory.mktemp("z3")
    ctx, bilan, reg = _relier(z2_reel, d / "z3", d / "registre")
    return ctx, bilan


def _per(ctx, article):
    return ctx.un("SELECT per FROM candidat WHERE article_frwiki = ?", [article])


# --- Petites tables écrites à la main (forme exacte des faits lus) -----------------------------

def _ecrire(dossier, lecteur, table, lignes):
    os.makedirs(dossier, exist_ok=True)
    schema = pa.schema(list(lecteur.TABLES[table]) + COLONNES_PROVENANCE)
    base = {f.name: None for f in schema}
    rows = [{**base, "prov_point": "p", "prov_uid": r.pop("_uid", "u"),
             "prov_version": r.pop("_version", 1), "prov_etat": "present", **r} for r in
            (dict(x) for x in lignes)]
    pq.write_table(pa.Table.from_pylist(rows, schema=schema),
                   os.path.join(dossier, f"{lecteur.NOM}__{table}.parquet"))


def _cand(nom, article, statut="declaree", rang=0, **k):
    return {"election": "presidentielle-2027", "statut": statut, "rang": rang,
            "personne_source": article or nom, "nom": nom, "article": article,
            "references": [], "references_nommees": [], **k}


def _wd(element, article, an=None, senat=None, naissance=None):
    out = []
    for prop, ident in (("P4123", an), ("P1808", senat)):
        if ident:
            out.append({"element": element, "propriete": prop, "valeur_publiee": ident,
                        "identifiant": ident, "naissance": naissance, "article_frwiki": article})
    return out


# =========================== R-CANDIDATURES / R-IDENTITE ======================================

def test_candidats_declares_et_retires(reel):
    ctx, bilan = reel
    n = {r["statut"]: r["n"] for r in _lignes(ctx, "SELECT statut, count(*) AS n FROM candidat GROUP BY 1")}
    assert n == {"declaree": 29, "retiree": 2}
    assert bilan["R-CANDIDATURES"]["couverture"]["candidats_declares"] == [29, 31]


def test_rattachement_par_le_titre_de_l_article(reel):
    ctx, _ = reel
    c = {r["article_frwiki"]: r for r in _lignes(ctx, "SELECT * FROM candidat WHERE article_frwiki IS NOT NULL")}
    ru = c["François Ruffin"]
    assert (ru["rattachement"], ru["acteur"], ru["element_wikidata"]) == ("wikidata", "PA722142", "Q3085763")
    me = c["Jean-Luc Mélenchon"]
    assert (me["acteur"], me["matricule_senat"]) == ("PA2150", "86039K")
    re_ = c["Bruno Retailleau"]
    assert (re_["acteur"], re_["matricule_senat"], re_["sycomore"]) == ("PA2538", "04033B", "6689")
    assert re_["acteur_connu_an"] is True and re_["matricule_connu_senat"] is True
    assert ru["source_url"] == LISTE_URL
    assert ru["date_declaration_source_url"].startswith("https://fr.wikipedia.org/w/index.php?title=")
    assert (ru["origine_element"], ru["rattachement_par_nom"]) == ("lien_frwiki", False)


def test_candidat_sans_mandat_zemmour(reel):
    ctx, _ = reel
    z = _lignes(ctx, "SELECT * FROM candidat WHERE nom = 'Éric Zemmour'")[0]
    assert (z["rattachement"], z["acteur"], z["publie"], z["adresse"]) == (
        "sans_identifiant_parlementaire", None, True, "eric-zemmour")
    assert ctx.un("SELECT count(*) FROM carriere WHERE per = ?", [z["per"]]) == 0
    assert ctx.un("SELECT count(*) FROM fonction_personne WHERE per = ?", [z["per"]]) == 0
    cov = {r["institution"]: r["statut"] for r in _lignes(
        ctx, "SELECT institution, statut FROM couverture_carriere WHERE per = ?", [z["per"]])}
    assert cov["assemblee"] == "aucun_identifiant" and cov["senat"] == "aucun_identifiant"
    assert cov["parlement_europeen"] == "non_collecte" and cov["local"] == "non_collecte"
    i = _lignes(ctx, "SELECT * FROM personne_identite WHERE per = ?", [z["per"]])[0]
    assert (i["nom"], i["prenom"], i["source_nom"]) == ("Zemmour", "Éric", "wikipedia")
    assert i["naissance"] is None and i["raison_naissance"] == "non connue de nos sources"


def test_candidat_sans_article_groupe_par_le_nom_sans_rapprochement(reel):
    ctx, _ = reel
    rows = _lignes(ctx, "SELECT * FROM candidat WHERE rattachement = 'aucun_element'")
    assert len(rows) == 5
    for r in rows:
        corr = _lignes(ctx, "SELECT source, uid FROM correspondance WHERE per = ?", [r["per"]])
        assert corr == [{"source": "wikipedia-nom", "uid": r["nom"]}]


def test_retiree_gardee_non_publiee(reel):
    ctx, _ = reel
    a = _lignes(ctx, "SELECT * FROM candidat WHERE nom = 'Clémentine Autain'")[0]
    # (l'extrait Wikidata ne la porte pas : elle n'y a pas d'identifiant)
    assert (a["statut"], a["publie"], a["rattachement"]) == ("retiree", False, "sans_identifiant_parlementaire")
    assert a["per"] and a["raison_non_publie"].startswith("candidature retirée")


def test_identite_sourcee_champ_par_champ(reel):
    ctx, _ = reel
    i = _lignes(ctx, "SELECT * FROM personne_identite WHERE acteur = 'PA722142'")[0]
    assert (i["nom"], i["prenom"], i["naissance"], i["lieu_naissance"], i["profession"]) == (
        "Ruffin", "François", "1975-10-18", "Calais (Pas-de-Calais)", "Reporter")
    assert (i["source_nom"], i["source_naissance"], i["naissance_concordance"]) == ("an", "an", "concordante")
    assert i["source_url"] == "https://www.assemblee-nationale.fr/dyn/deputes/PA722142"


def test_jamais_par_le_nom_seul(tmp_path):
    z2 = tmp_path / "z2"
    _ecrire(z2, wp_candidatures, "candidature", [
        _cand("Francois Ruffin", "Francois Ruffin", rang=0),        # titre sans cédille
        _cand("Jean-Luc Mélenchon", "jean-Luc_Mélenchon", rang=1)])  # même titre, forme MediaWiki
    _ecrire(z2, wd_identifiants, "identifiant_externe",
            _wd("Q3085763", "François Ruffin", an="PA722142")
            + _wd("Q5829", "Jean-Luc Mélenchon", an="PA2150"))
    ctx, _, _ = _relier(z2, tmp_path / "z3", tmp_path / "r", [r_candidatures, r_identite])
    c = {r["nom"]: r for r in _lignes(ctx, "SELECT * FROM candidat")}
    assert c["Francois Ruffin"]["rattachement"] == "sans_identifiant_parlementaire"
    assert c["Francois Ruffin"]["acteur"] is None
    assert (c["Jean-Luc Mélenchon"]["rattachement"], c["Jean-Luc Mélenchon"]["acteur"]) == ("wikidata", "PA2150")


def test_identifiant_partage_non_retenu(tmp_path):
    z2 = tmp_path / "z2"
    _ecrire(z2, wp_candidatures, "candidature", [_cand("A", "Article A", rang=0),
                                                  _cand("B", "Article B", rang=1)])
    _ecrire(z2, wd_identifiants, "identifiant_externe",
            _wd("Q1", "Article A", an="PA1") + _wd("Q2", "Article B", an="PA1"))
    ctx, _, _ = _relier(z2, tmp_path / "z3", tmp_path / "r", [r_candidatures, r_identite])
    rows = _lignes(ctx, "SELECT * FROM candidat ORDER BY nom")
    assert [(r["rattachement"], r["acteur"]) for r in rows] == [("non_etabli", None)] * 2
    assert rows[0]["raison_rattachement"] == "identifiant déclaré pour plusieurs candidats"
    assert rows[0]["per"] != rows[1]["per"]


def test_plus_dans_la_liste_garde_non_publie(tmp_path):
    """La liste la plus récente fait foi ; une personne d'une liste plus ancienne garde sa ligne."""
    dec = tmp_path / "d" / "candidature"
    _ecrire_decision(dec, [{"nom": "Ancien", "statut": "declaree", "article_frwiki": "Ancien"},
                           {"nom": "Actuel", "statut": "declaree", "article_frwiki": "Actuel"}],
                     date="2026-11-01")
    _ecrire_decision(dec, [{"nom": "Actuel", "statut": "declaree", "article_frwiki": "Actuel"},
                           {"nom": "Parti", "statut": "non_listee", "article_frwiki": "Parti"}],
                     date="2026-11-13")
    z2 = tmp_path / "z2"
    os.makedirs(z2)
    ctx, _, _ = _relier(z2, tmp_path / "z3", tmp_path / "r", [r_candidatures, r_identite],
                        decisions=tmp_path / "d")
    c = {r["nom"]: r for r in _lignes(ctx, "SELECT * FROM candidat")}
    assert (c["Ancien"]["statut"], c["Ancien"]["publie"]) == ("non_listee", False)
    assert (c["Parti"]["statut"], c["Parti"]["publie"]) == ("non_listee", False)
    assert c["Parti"]["raison_non_publie"].startswith("n'est plus dans la liste des candidats")
    assert (c["Actuel"]["statut"], c["Actuel"]["publie"]) == ("declaree", True)
    assert c["Actuel"]["date_liste"] == "2026-11-13"


def test_element_inscrit_par_la_decision(tmp_path):
    """L'élément Wikidata inscrit fait foi ; il est contrôlé contre l'article inscrit."""
    z2 = tmp_path / "z2"
    _ecrire(z2, wd_identifiants, "identifiant_externe",
            _wd("Q3085763", "François Ruffin", an="PA722142")
            + _wd("Q5829", "Jean-Luc Mélenchon", an="PA2150"))
    dec = _ecrire_decision(tmp_path / "d" / "candidature", [
        {"nom": "François Ruffin", "statut": "declaree", "wikidata": "Q3085763", "article_frwiki": "François Ruffin"},
        {"nom": "Eric Zemmour", "statut": "declaree", "wikidata": "Q288477", "article_frwiki": "Éric Zemmour"},
        {"nom": "Jean Lassalle", "statut": "declaree", "wikidata": "Q3173022", "article_frwiki": "Jean Lassalle",
         "rattachement_par_nom": True},
        {"nom": "Christian Collovati", "statut": "declaree"},
        {"nom": "Mal Écrit", "statut": "declaree", "wikidata": "Q12x"},
        {"nom": "Autre", "statut": "declaree", "wikidata": "Q5829", "article_frwiki": "Autre article"}])
    ctx, bilan, _ = _relier(z2, tmp_path / "z3", tmp_path / "r", [r_candidatures, r_identite],
                            decisions=tmp_path / "d")
    c = {r["nom_liste"]: r for r in _lignes(ctx, "SELECT * FROM candidat")}
    ru = c["François Ruffin"]
    assert (ru["rattachement"], ru["acteur"], ru["origine_element"]) == ("wikidata", "PA722142", "decision")
    z = c["Eric Zemmour"]
    assert (z["rattachement"], z["element_wikidata"], z["acteur"]) == ("sans_identifiant_parlementaire", "Q288477", None)
    assert (z["nom"], z["adresse"]) == ("Éric Zemmour", "eric-zemmour")      # nom de l'article, adresse inchangée
    assert c["Jean Lassalle"]["rattachement_par_nom"] is True
    co = c["Christian Collovati"]
    assert (co["rattachement"], co["publie"], co["adresse"]) == ("aucun_element", True, "christian-collovati")
    assert _lignes(ctx, "SELECT source, uid, statut FROM correspondance WHERE per = ?", [co["per"]]) == [
        {"source": "liste-nom", "uid": "Christian Collovati", "statut": "validee"}]
    assert (c["Mal Écrit"]["rattachement"], c["Mal Écrit"]["raison_rattachement"]) == (
        "non_etabli", "élément Wikidata mal écrit dans la décision")
    assert c["Autre"]["rattachement"] == "non_etabli" and c["Autre"]["acteur"] is None
    assert c["Autre"]["raison_rattachement"].startswith("l'élément Wikidata inscrit a pour lien un autre article")
    i = _lignes(ctx, "SELECT * FROM personne_identite WHERE per = ?", [co["per"]])[0]
    assert (i["source_nom"], i["source_url"]) == ("franceinfo", LISTE_URL)
    w = {r["source"]: r for r in _lignes(ctx, "SELECT * FROM correspondance WHERE per = ?", [ru["per"]])}
    assert (w["wd"]["methode"], w["wd"]["statut"]) == ("element_inscrit_par_decision", "validee")
    assert (w["an"]["methode"], w["an"]["statut"]) == ("identifiant_declare_wikidata_P4123", "automatique")
    assert bilan["R-CANDIDATURES"]["couverture"]["element_wikidata_retenu"] == [3, 6]


def test_numero_garde_quand_la_liste_change_de_source(tmp_path):
    """Les numéros attribués sous la liste de Wikipédia (article, ou nom écrit) sont gardés quand
    la décision inscrit en plus l'élément Wikidata."""
    z2 = tmp_path / "z2"
    _ecrire(z2, wp_candidatures, "candidature", [
        _cand("Anasse Kazib", "Anasse Kazib", rang=0),
        _cand("Benoît Mathieu", None, rang=1, personne_source="Benoît Mathieu")])
    ctx1, _, reg = _relier(z2, tmp_path / "z3a", tmp_path / "r", [r_candidatures, r_identite])
    avant = dict(ctx1.x("SELECT nom, per FROM candidat"))
    reg.sauver()
    _ecrire_decision(tmp_path / "d" / "candidature", [
        {"nom": "Anasse Kazib", "statut": "declaree", "wikidata": "Q106405647", "article_frwiki": "Anasse Kazib"},
        {"nom": "Benoît Mathieu", "statut": "declaree", "nom_wikipedia": "Benoît Mathieu"},
        {"nom": "Joël Chevé", "statut": "declaree"}])
    ctx2, _, _ = _relier(z2, tmp_path / "z3b", tmp_path / "r", [r_candidatures, r_identite],
                         generation=2, decisions=tmp_path / "d")
    apres = dict(ctx2.x("SELECT nom, per FROM candidat"))
    assert apres["Anasse Kazib"] == avant["Anasse Kazib"]
    assert apres["Benoît Mathieu"] == avant["Benoît Mathieu"]
    assert apres["Joël Chevé"] not in avant.values()
    k = _lignes(ctx2, "SELECT * FROM candidat WHERE nom = 'Anasse Kazib'")[0]
    assert (k["element_wikidata"], k["statut_wikipedia"]) == ("Q106405647", "declaree")
    c = _lignes(ctx2, "SELECT * FROM candidat WHERE nom = 'Joël Chevé'")[0]
    assert (c["statut_wikipedia"], c["date_declaration"]) == (None, None)
    assert c["date_declaration_raison"].startswith("non connue de nos sources : franceinfo ne date pas")


def test_ecarts_avec_wikipedia(tmp_path):
    z2 = tmp_path / "z2"
    _ecrire(z2, wp_candidatures, "candidature", [
        _cand("A", "Article A", rang=0), _cand("B", "Article B", rang=1),
        _cand("C", "Article C", statut="retiree", rang=2), _cand("D", None, rang=3, personne_source="D"),
        _cand("F", "Article F", rang=4)])
    _ecrire_decision(tmp_path / "d" / "candidature", [
        {"nom": "A", "statut": "declaree", "article_frwiki": "Article A"},
        {"nom": "C", "statut": "declaree", "article_frwiki": "Article C"},
        {"nom": "D", "statut": "declaree", "nom_wikipedia": "D"},
        {"nom": "E", "statut": "declaree"},
        {"nom": "F", "statut": "retiree", "article_frwiki": "Article F"}])
    ctx, bilan, _ = _relier(z2, tmp_path / "z3", tmp_path / "r", [r_candidatures, r_identite],
                            decisions=tmp_path / "d")
    e = [(r["ecart"], r["nom"]) for r in _lignes(ctx, "SELECT * FROM candidature_ecart_wikipedia")]
    assert e == [("declare_par_wikipedia_absent_de_la_liste", "B"),
                 ("declare_selon_wikipedia_retire_dans_la_liste", "F"),
                 ("retire_selon_wikipedia_declare_dans_la_liste", "C")]
    # Un écart n'ajoute ni ne retire personne.
    assert {r["nom"] for r in _lignes(ctx, "SELECT nom FROM candidat WHERE publie")} == {"A", "C", "D", "E"}
    assert bilan["R-CANDIDATURES"]["couverture"]["ecarts_avec_wikipedia"] == [3, 4]


def test_statut_inconnu_dans_la_decision_echoue(tmp_path):
    _ecrire_decision(tmp_path / "d" / "candidature", [{"nom": "A", "statut": "declare"}])
    os.makedirs(tmp_path / "z2")
    with pytest.raises(ValueError, match="statut inconnu"):
        _relier(tmp_path / "z2", tmp_path / "z3", tmp_path / "r", [r_candidatures, r_identite],
                decisions=tmp_path / "d")


def test_decision_reelle_de_la_liste_bien_formee():
    """Le fichier recopié de franceinfo : statuts connus, éléments bien écrits et uniques, mêmes
    clés partout (la table des décisions prend ses colonnes à la première entrée)."""
    import glob
    import re
    racine = os.path.join(os.path.dirname(__file__), "..", "decisions", "candidature")
    fichiers = sorted(glob.glob(os.path.join(racine, "*.yaml")))
    assert fichiers
    for f in fichiers:
        d = yaml.safe_load(open(f))
        assert d["type"] == "candidature" and d["election"] == "presidentielle-2027" and d["date"]
        cles = {tuple(sorted(e)) for e in d["decisions"]}
        assert len(cles) == 1
        q = [e["wikidata"] for e in d["decisions"] if e["wikidata"]]
        assert all(re.fullmatch(r"Q[1-9][0-9]*", x) for x in q) and len(q) == len(set(q))
        assert {e["statut"] for e in d["decisions"]} <= set(r_candidatures.STATUTS)
        noms = [e["nom"] for e in d["decisions"]]
        assert len(noms) == len(set(noms))
    d = yaml.safe_load(open(os.path.join(racine, "2026-11-13-franceinfo.yaml")))
    assert sum(e["statut"] == "declaree" for e in d["decisions"]) == 37          # « 37 candidats au 13/11/2026 »
    assert sum(e["statut"] == "retiree" for e in d["decisions"]) == 6


def test_adresse_homonymes_annee_de_naissance(tmp_path):
    z2 = tmp_path / "z2"
    _ecrire(z2, wp_candidatures, "candidature", [
        _cand("Jean Martin", "Jean Martin (homme politique)", rang=0),
        _cand("Jean Martin", "Jean Martin (journaliste)", rang=1),
        _cand("Jean Martin", None, rang=2, personne_source="Jean Martin"),
        _cand("Œdipe Lécrivain", "Œdipe Lécrivain", rang=3)])
    _ecrire(z2, wd_identifiants, "identifiant_externe",
            _wd("Q1", "Jean Martin (homme politique)", an="PA1", naissance="1962-05-01")
            + _wd("Q2", "Jean Martin (journaliste)", senat="12345A", naissance="1970-01-01"))
    ctx, _, _ = _relier(z2, tmp_path / "z3", tmp_path / "r", [r_candidatures, r_identite])
    c = {r["personne_source"]: r for r in _lignes(ctx, "SELECT * FROM candidat")}
    assert c["Jean Martin (homme politique)"]["adresse"] == "jean-martin-1962"
    assert c["Jean Martin (journaliste)"]["adresse"] == "jean-martin-1970"
    sans = c["Jean Martin"]
    assert sans["adresse"] is None and sans["publie"] is False
    assert sans["raison_adresse"].startswith("homonyme sans année")
    assert c["Œdipe Lécrivain"]["adresse"] == "oedipe-lecrivain"


def test_naissance_aberrante_non_retenue(tmp_path):
    z2 = tmp_path / "z2"
    _ecrire(z2, wp_candidatures, "candidature", [_cand("A", "A")])
    _ecrire(z2, wd_identifiants, "identifiant_externe",
            _wd("Q1", "A", an="PA1", naissance="1900-01-01"))
    ctx, _, _ = _relier(z2, tmp_path / "z3", tmp_path / "r", [r_candidatures, r_identite])
    i = _lignes(ctx, "SELECT * FROM personne_identite")[0]
    assert i["naissance"] is None
    assert i["raison_naissance"] == "date de naissance aberrante à la source : non retenue"


def test_sans_registre_la_regle_echoue(z2_reel, tmp_path):
    with pytest.raises(RuntimeError, match="aucun registre des identités"):
        _relier(z2_reel, tmp_path / "z3", tmp_path / "r", [r_candidatures, r_identite], registre=False)


def test_per_independant_de_l_ordre_de_lecture(z2_reel, tmp_path):
    """Mêmes faits, lignes dans un autre ordre : mêmes numéros."""
    autre = tmp_path / "z2"
    shutil.copytree(z2_reel, autre)
    for nom in ("wp_candidatures__candidature", "wd_identifiants__identifiant_externe"):
        p = autre / f"{nom}.parquet"
        t = pq.read_table(p)
        ordre = list(range(t.num_rows))
        random.Random(7).shuffle(ordre)
        pq.write_table(t.take(ordre), p)
    ctx_a, _, _ = _relier(z2_reel, tmp_path / "a", tmp_path / "ra", [r_candidatures, r_identite])
    ctx_b, _, _ = _relier(autre, tmp_path / "b", tmp_path / "rb", [r_candidatures, r_identite])
    q = "SELECT personne_source, per FROM candidat ORDER BY personne_source"
    assert ctx_a.x(q) == ctx_b.x(q)


def test_attribution_acquise_d_une_generation_a_l_autre(z2_reel, tmp_path):
    ctx1, _, reg = _relier(z2_reel, tmp_path / "z3a", tmp_path / "r", [r_candidatures, r_identite])
    avant = dict(ctx1.x("SELECT personne_source, per FROM candidat"))
    reg.sauver()
    # Génération suivante : un candidat nouveau, dont le titre trie avant tous les autres.
    z2 = tmp_path / "z2"
    shutil.copytree(z2_reel, z2)
    t = pq.read_table(z2 / "wp_candidatures__candidature.parquet").to_pylist()
    nouveau = {**t[0], "personne_source": "Aaron Nouveau", "nom": "Aaron Nouveau",
               "article": "Aaron Nouveau", "rang": 99}
    pq.write_table(pa.Table.from_pylist(t + [nouveau], schema=pq.read_schema(
        z2 / "wp_candidatures__candidature.parquet")), z2 / "wp_candidatures__candidature.parquet")
    ctx2, _, _ = _relier(z2, tmp_path / "z3b", tmp_path / "r", [r_candidatures, r_identite], generation=2)
    apres = dict(ctx2.x("SELECT personne_source, per FROM candidat"))
    assert all(apres[k] == v for k, v in avant.items())
    assert apres["Aaron Nouveau"] == f"per:{len(avant) + 1:06d}"


# ================================== R-CARRIERE ================================================

def test_ruffin_trois_mandats_et_ses_groupes(reel):
    ctx, _ = reel
    p = _per(ctx, "François Ruffin")
    an = _lignes(ctx, """SELECT * FROM carriere WHERE per = ? AND institution = 'assemblee'
                         ORDER BY debut""", [p])
    assert sorted({r["legislature"] for r in an}) == [15, 16, 17]
    assert len({r["mandat"] for r in an}) == 3
    groupes = [r["groupe_sigle"] for r in an if r["groupe_statut"] == "groupe"]
    assert groupes == ["FI", "LFI-NUPES", "ECOS"]
    # Le passage chez les non-inscrits à l'ouverture d'une législature n'est pas un groupe.
    assert {r["groupe_statut"] for r in an} == {"groupe", "non_inscrit"}
    # XIVe à XVIIe publiées : chaque période renvoie à la fiche de sa législature.
    assert all(r["lien"] == f"legislature/{r['legislature']}" for r in an)
    ecos = [r for r in an if r["groupe_sigle"] == "ECOS"][0]
    assert ecos["fin"] is None and ecos["siege"] is not None and ecos["siege_date"] == "2026-11-06"
    assert an[0]["libelle"] == "Député de la 1re circonscription · Somme"
    cov = dict(ctx.x("SELECT institution, statut FROM couverture_carriere WHERE per = ?", [p]))
    assert cov["assemblee"] == "complet" and cov["assemblee_avant_2002"] == "hors_source"
    assert cov["gouvernement"] == "relu_aucun"


def test_retailleau_gouvernement_et_senat_libelle_date(reel):
    ctx, _ = reel
    p = _per(ctx, "Bruno Retailleau")
    gv = _lignes(ctx, "SELECT * FROM carriere WHERE per = ? AND institution = 'gouvernement' ORDER BY debut", [p])
    assert [r["lien"] for r in gv] == ["gouvernement/barnier", "gouvernement/bayrou", "gouvernement/lecornu"]
    assert {r["libelle"] for r in gv} == {"Ministère de l'intérieur"}
    sen = _lignes(ctx, "SELECT * FROM carriere WHERE per = ? AND institution = 'senat' ORDER BY debut", [p])
    assert sen and {r["source"] for r in sen} == {"senat"}
    par_date = {r["debut"]: r for r in sen}
    # Libellé du groupe à la date (« Groupe UMP » en 2012), jamais le libellé actuel.
    assert par_date["2012-11-07"]["groupe_libelle"] == "Groupe UMP"
    susp = [r for r in sen if r["etat"] == "suspendu"]
    assert [(r["debut"], r["fin"]) for r in susp] == [("2024-10-22", "2025-11-12")]
    assert ctx.un("SELECT count(*) FROM carriere WHERE per = ? AND institution = 'assemblee'", [p]) == 0


def test_senat_non_collecte(tmp_path):
    z2 = _z2_reel(tmp_path, sources=("amo", "wp", "wd"))
    ctx, bilan, _ = _relier(z2, tmp_path / "z3", tmp_path / "r")
    p = _per(ctx, "Jean-Luc Mélenchon")
    cov = dict(ctx.x("SELECT institution, statut FROM couverture_carriere WHERE per = ?", [p]))
    assert cov["senat"] == "non_collecte"
    assert "senat_non_collecte" in bilan["R-CARRIERE"]["couverture"]
    assert ctx.un("SELECT count(*) FROM carriere WHERE institution = 'senat'") == 0


def _an_hand(z2, mandats, organes, acteurs=("PA1",)):
    _ecrire(z2, an_acteurs, "organe", [{"organes": [], "pays": [], **o} for o in organes])
    _ecrire(z2, an_acteurs, "mandat", [{"organes": [], "suppleants": [], "_uid": m["acteur"], **m}
                                      for m in mandats])
    _ecrire(z2, an_acteurs, "identite_source", [{"uid": a, "civilite": "Mme", "prenom": "Anne",
                                                 "nom": "Essai", "date_naissance": "1970-01-01"}
                                                for a in acteurs])
    _ecrire(z2, wp_candidatures, "candidature", [_cand("Anne Essai", "Anne Essai")])
    _ecrire(z2, wd_identifiants, "identifiant_externe", _wd("Q1", "Anne Essai", an="PA1"))


ASSEMBLEES = [
    {"uid": "PO16", "type_organe": "ASSEMBLEE", "legislature": "16", "date_debut": "2022-06-22",
     "date_fin": "2024-06-09"},
    {"uid": "PO17", "type_organe": "ASSEMBLEE", "legislature": "17", "date_debut": "2024-07-18"}]


def test_suspension_sans_reprise_bornee_par_la_legislature(tmp_path):
    z2 = tmp_path / "z2"
    _an_hand(z2, [{"uid": "PM1", "acteur": "PA1", "type_organe": "ASSEMBLEE", "organe": "PO16",
                   "legislature": "16", "date_debut": "2022-06-19", "date_prise_fonction": "2022-06-22",
                   "date_fin": "2022-07-22", "cause_fin": "Nomination comme membre du Gouvernement",
                   "num_circo": "3", "departement": "Essonne", "circonscription": "PO9"}], ASSEMBLEES)
    ctx, _, _ = _relier(z2, tmp_path / "z3", tmp_path / "r")
    rows = _lignes(ctx, "SELECT * FROM carriere ORDER BY debut")
    assert [(r["etat"], r["debut"], r["fin"]) for r in rows] == [
        ("en_fonction", "2022-06-22", "2022-07-22"), ("suspendu", "2022-07-23", "2024-06-09")]
    assert rows[0]["libelle"] == "Députée de la 3e circonscription · Essonne"
    assert rows[0]["groupe_statut"] == "non_etabli"        # aucun mandat de groupe dans ces faits
    assert rows[1]["fin_raison"].startswith("aucune reprise publiée")


# ================================== R-FONCTIONS ===============================================

def test_ruffin_fonctions_par_famille_comme_la_capture(reel):
    """Capture `02-candidat-ruffin-01.png` : 9 commissions, 3 commissions d'enquête ou spéciales,
    6 missions d'information, 1 groupe d'études, 2 organismes extra-parlementaires, 2 groupes
    d'amitié ; secrétaire de la commission des affaires économiques."""
    ctx, _ = reel
    p = _per(ctx, "François Ruffin")
    n = dict(ctx.x("SELECT famille, count(DISTINCT libelle) FROM fonction_personne WHERE per = ? GROUP BY 1", [p]))
    assert n == {"commission": 9, "commission_enquete_speciale": 3, "mission_information": 6,
                 "groupe_etudes": 1, "organisme_extraparlementaire": 2, "groupe_amitie": 2}
    sec = _lignes(ctx, """SELECT * FROM fonction_personne WHERE per = ? AND qualite = 'Secrétaire'
                          AND libelle = 'Commission des affaires économiques' ORDER BY debut""", [p])
    assert sec and all(r["qualite_distinctive"] for r in sec)
    # Mission « aides à la personne » : co-rapporteur.
    assert ctx.un("""SELECT count(*) FROM fonction_personne WHERE per = ? AND qualite = 'Co-rapporteur'
                     AND libelle LIKE 'Mission d''information relative aux aides%'""", [p]) == 1


def test_ruffin_permutations_fusionnees_detail_garde(reel):
    ctx, _ = reel
    p = _per(ctx, "François Ruffin")
    eco = _lignes(ctx, """SELECT * FROM fonction_personne WHERE per = ? AND organe = 'PO419610'
                          AND qualite = 'Membre' AND legislature = 15 ORDER BY debut""", [p])
    # XVe : 16 mandats « membre » de la source, quatre périodes affichées (trous de 11 et
    # 8 jours non fusionnés ; trous de 1 à 3 jours fusionnés).
    assert [(r["debut"], r["fin"]) for r in eco] == [
        ("2017-06-29", "2018-01-22"), ("2018-02-03", "2019-02-11"),
        ("2019-02-26", "2021-12-06"), ("2021-12-15", "2022-06-21")]
    trois = eco[2]
    assert trois["nb_mandats_source"] == 10 and trois["plus_long_trou_fusionne_jours"] == 2
    # Durée réelle : jours couverts, sans les trous (1 015 jours d'enveloppe, 11 jours de trous).
    assert trois["duree_jours"] == 1004
    assert ctx.un("""SELECT count(*) FROM fonction_periode WHERE per = ? AND organe = 'PO419610'
                     AND qualite = 'Membre' AND legislature = 15""", [p]) == 16


def test_cmp_au_titre_du_senat_lue_dans_l_export_du_senat(reel):
    ctx, _ = reel
    p = _per(ctx, "Bruno Retailleau")
    assert ctx.un("SELECT count(*) FROM fonction_periode WHERE per = ? AND chambre = 'an' AND type_organe = 'CMP'", [p]) == 0
    assert ctx.un("SELECT count(*) FROM fonction_periode WHERE per = ? AND chambre = 'senat' AND type_organe = 'CMP'", [p]) > 0
    pres = _lignes(ctx, """SELECT * FROM fonction_personne WHERE per = ? AND famille = 'groupe_politique'""", [p])
    assert pres and {r["qualite"] for r in pres} == {"Président"}      # pas « membre »


def test_fusion_trois_jours_au_plus_et_duree_reelle(tmp_path):
    z2 = tmp_path / "z2"
    org = {"uid": "PO1", "type_organe": "COMPER", "libelle": "Commission essai"}
    m = lambda uid, d0, d1: {"uid": uid, "acteur": "PA1", "type_organe": "COMPER", "organe": "PO1",
                             "legislature": "17", "qualite": "Membre", "date_debut": d0, "date_fin": d1}
    _an_hand(z2, [
        {"uid": "PMA", "acteur": "PA1", "type_organe": "ASSEMBLEE", "organe": "PO17", "legislature": "17",
         "date_debut": "2024-07-07", "date_prise_fonction": "2024-07-08"},
        m("PM1", "2025-01-01", "2025-01-10"), m("PM2", "2025-01-14", "2025-01-20"),   # trou 3 j : fusion
        m("PM3", "2025-01-25", "2025-01-31"),                                        # trou 4 j : non
        m("PM4", "2026-11-01", None)], ASSEMBLEES + [org])                           # ouvert, mandat en cours
    ctx, _, _ = _relier(z2, tmp_path / "z3", tmp_path / "r")
    rows = _lignes(ctx, "SELECT * FROM fonction_personne ORDER BY debut")
    assert [(r["debut"], r["fin"], r["duree_jours"]) for r in rows] == [
        ("2025-01-01", "2025-01-20", 17), ("2025-01-25", "2025-01-31", 7), ("2026-11-01", None, 6)]
    assert rows[0]["mandats"] == ["PM1", "PM2"] and rows[0]["plus_long_trou_fusionne_jours"] == 3
    assert rows[2]["en_cours"] and rows[2]["duree_calculee_au"] == "2026-11-06"


def test_fonction_ouverte_hors_du_mandat_en_cours_duree_inconnue(tmp_path):
    z2 = tmp_path / "z2"
    _an_hand(z2, [
        {"uid": "PM1", "acteur": "PA1", "type_organe": "ASSEMBLEE", "organe": "PO16", "legislature": "16",
         "date_debut": "2022-06-19", "date_prise_fonction": "2022-06-22", "date_fin": "2024-06-09"},
        {"uid": "PM2", "acteur": "PA1", "type_organe": "GA", "organe": "PO2", "legislature": "16",
         "qualite": "Vice-Président", "date_debut": "2022-10-01"}],
        ASSEMBLEES + [{"uid": "PO2", "type_organe": "GA", "libelle": "France-Essai"}])
    ctx, bilan, _ = _relier(z2, tmp_path / "z3", tmp_path / "r")
    r = _lignes(ctx, "SELECT * FROM fonction_personne")[0]
    assert (r["famille"], r["duree_jours"], r["fin"]) == ("groupe_amitie", None, None)
    assert r["raison_duree"].startswith("fonction ouverte à la source")
    assert bilan["R-FONCTIONS"]["couverture"]["duree_etablie"] == [0, 1]


def test_types_exclus_et_inconnus(tmp_path):
    z2 = tmp_path / "z2"
    m = lambda uid, t, q="Membre": {"uid": uid, "acteur": "PA1", "type_organe": t, "organe": "PO" + t,
                                    "legislature": "17", "qualite": q, "date_debut": "2025-01-01",
                                    "date_fin": "2025-02-01"}
    _an_hand(z2, [m("PM1", "PARPOL"), m("PM2", "GP"), m("PM3", "GP", "Président"), m("PM4", "NOUVEAU"),
                  m("PM5", "COMSENAT")], ASSEMBLEES)
    ctx, bilan, _ = _relier(z2, tmp_path / "z3", tmp_path / "r")
    assert dict(ctx.x("SELECT mandat, famille FROM fonction_periode")) == {
        "PM3": "groupe_politique", "PM4": "autre"}
    assert bilan["R-FONCTIONS"]["couverture"]["periodes_source_classees_dans_une_famille"] == [1, 2]
