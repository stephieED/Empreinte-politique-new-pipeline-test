"""Mandats locaux des candidats (Répertoire national des élus ; décisions du 13/11/2026, Q34 et Q35).

Lecteur `rne_elus` et R-MANDAT-LOCAL, R-CARRIERE sur l'extrait réel `rne_elus/` (fiche
`rne_elus.md`) : Lisnard (rattaché par nom, prénom et naissance Wikidata), Roussel (trois
homonymes d'une autre naissance, écartés), Platret (sans date de naissance connue : décision)."""
import os

import pyarrow.parquet as pq
import pytest
import yaml

from empreinte_src.depaquetage import _membre, depaqueter
from empreinte_src.entrepot import Entrepot
from empreinte_src.lecteurs import an_acteurs, pe_eurodeputes, rne_elus
from empreinte_src.lecture import Lecture
from empreinte_src.regles import r_candidatures, r_carriere, r_identite, r_mandat_local
from tests.test_regles_e1 import EX, PAS, TOUTES, _ecrire, _ecrire_decision, _lignes, _relier

RNE = os.path.join(EX, "rne_elus")
UIDS = ("elus-maires", "elus-cm", "elus-cd", "elus-cr", "elus-sortants-maires")


@pytest.mark.parametrize("v, naissance, attendu", [
    ("1969-02-02", True, "1969-02-02"), ("02/02/69", True, "1969-02-02"), ("04/05/07", True, "2007-05-04"),
    ("18/05/20", False, "2020-05-18"), ("", True, None)])
def test_dates_du_repertoire(v, naissance, attendu):
    assert rne_elus.date_iso(v, naissance) == attendu


def _z2(d):
    e = Entrepot(str(d / "e"))
    e.versionner(PAS["amo"][0], "R0", depaqueter(os.path.join(EX, "amo30_l17_candidats_e1.zip"), "zip"),
                 complet=True)
    for uid in UIDS:
        pa_cfg = {"id": f"rne-{uid[5:]}", "source": "rne", "type": "elus_rne", "format": "fichier",
                  "url": "https://www.data.gouv.fr/fr/datasets/r/x", "uid": uid}
        with open(os.path.join(RNE, f"{uid}.csv"), "rb") as f:
            e.versionner(pa_cfg, f"R-{uid}", [_membre(uid, f"{uid}.csv", f.read())], complet=True)
    e.clore("test")
    cfg = {"points_acces": [{"id": f"rne-{u[5:]}", "licence": "etalab-2.0"} for u in UIDS]
           + [{"id": "an-amo30-l17", "licence": "etalab-2.0"}]}
    lect = Lecture(Entrepot(str(d / "e")), str(d / "z2"), cfg)
    for m in (an_acteurs, rne_elus):
        assert lect.executer(m)["illisibles"] == 0
    # Dates de naissance déclarées par Wikidata pour les éléments de la liste (point pe-eurodeputes).
    _ecrire(d / "z2", pe_eurodeputes, "naissance_wikidata", [
        {"element": "Q3018298", "naissance": "1969-02-02", "_uid": "wikidata-p1186"},
        {"element": "Q30388733", "naissance": "1969-04-16", "_uid": "wikidata-p1186"}])
    return d / "z2"


def test_lecteur_lignes_et_dates(tmp_path):
    z2 = _z2(tmp_path)
    t = {(r["fichier"], r["collectivite"], r["naissance"], r["fonction"]): r
         for r in pq.read_table(z2 / "rne_elus__mandat_local.parquet").to_pylist()}
    assert len(t) == 14
    s = t[("sortants-maires", "Cannes", "1969-02-02", "Maire")]
    assert (s["naissance_publiee"], s["debut_mandat"], s["sortant"]) == ("02/02/69", "2020-05-18", True)
    # Un conseiller municipal sans fonction : la fonction par défaut du fichier.
    assert ("cm", "Voulx", "1972-12-19", "Conseiller municipal") in t


def _decisions(d, platret=True):
    _ecrire_decision(os.path.join(str(d), "candidature"), [
        {"nom": "David Lisnard", "statut": "declaree", "wikidata": "Q3018298", "article_frwiki": "David Lisnard"},
        {"nom": "Fabien Roussel", "statut": "declaree", "wikidata": "Q30388733", "article_frwiki": "Fabien Roussel"},
        {"nom": "Gilles Platret", "statut": "declaree"}])
    if platret:
        os.makedirs(os.path.join(str(d), "elu_local"), exist_ok=True)
        with open(os.path.join(str(d), "elu_local", "platret.yaml"), "w") as f:
            yaml.safe_dump({"type": "elu_local", "date": "2026-11-13", "candidat": "Gilles Platret",
                            "nom_elu": "PLATRET", "prenom_elu": "Gilles", "naissance": "1973-04-19",
                            "motif": "test"}, f, allow_unicode=True)
    return d


def test_rattachement_par_nom_prenom_naissance_et_decision(tmp_path):
    z2 = _z2(tmp_path)
    d = _decisions(tmp_path / "d")
    ctx, bilan, _ = _relier(z2, tmp_path / "z3", tmp_path / "r", TOUTES, decisions=d)
    c = {r["nom_liste"]: r["per"] for r in _lignes(ctx, "SELECT nom_liste, per FROM candidat")}
    m = {}
    for r in _lignes(ctx, "SELECT * FROM mandat_local_candidat ORDER BY debut, fichier"):
        m.setdefault(r["per"], []).append(r)
    # Deux lignes (Q50) : le mandat, daté de son début, et la fonction, datée de la sienne.
    li = sorted(m[c["David Lisnard"]], key=lambda r: (r["debut"], r["nature_periode"]))
    assert [(r["nature_periode"], r["fonction"], r["collectivite"], r["debut"], r["fin"]) for r in li] == [
        ("mandat", "Conseiller municipal", "Cannes", "2020-05-18", "2026-03-15"),
        ("fonction", "Maire", "Cannes", "2020-05-23", "2026-03-15"),
        ("fonction", "3ème Vice-président du conseil départemental", "Cannes-2 · Alpes-Maritimes", "2021-07-01", None),
        ("mandat", "Conseiller départemental", "Cannes-2 · Alpes-Maritimes", "2021-07-01", None),
        ("mandat", "Conseiller municipal", "Cannes", "2026-03-15", None),
        ("fonction", "Maire", "Cannes", "2026-03-21", None)]
    assert li[0]["fin_deduite"] is True and li[0]["fin_raison"].startswith("fin déduite")
    assert li[0]["fin_nature"] == "deduite" and li[4]["fin_nature"] is None
    assert {r["methode"] for r in li} == {"nom_prenom_naissance"}
    # Une fonction garde l'identifiant de la ligne d'avant ; un mandat qui le partagerait prend `:mandat`.
    assert [r["mandat_id"] for r in li] == ["sortants-maires:06029:mandat", "sortants-maires:06029",
                                           "cd:0608", "cd:0608:mandat", "cm:06029", "maires:06029"]
    # Roussel : seul l'élu de même naissance ; les trois homonymes sont écartés. Conseiller municipal
    # depuis 2020, maire depuis le 30/01/2025 dans ce même mandat (sortants), réélu en 2026.
    ro = sorted(m[c["Fabien Roussel"]], key=lambda r: (r["debut"], r["nature_periode"]))
    assert [(r["nature_periode"], r["collectivite"], r["naissance"], r["debut"], r["fin"]) for r in ro] == [
        ("mandat", "Saint-Amand-Les-Eaux", "1969-04-16", "2020-05-18", "2026-03-15"),
        ("fonction", "Saint-Amand-Les-Eaux", "1969-04-16", "2025-01-30", "2026-03-15"),
        ("mandat", "Saint-Amand-Les-Eaux", "1969-04-16", "2026-03-15", None),
        ("fonction", "Saint-Amand-Les-Eaux", "1969-04-16", "2026-03-22", None)]
    # Platret : par la décision.
    pl = m[c["Gilles Platret"]]
    assert {r["methode"] for r in pl} == {"decision"} and len(pl) == 5      # 2 mandats municipaux, 2 fois maire, région
    assert bilan["R-MANDAT-LOCAL"]["couverture"]["candidats_avec_mandat_local"] == [3, 3]
    # Frise et couverture.
    car = _lignes(ctx, "SELECT * FROM carriere WHERE per = ? AND institution = 'local' ORDER BY debut",
                  [c["David Lisnard"]])
    assert car[0]["libelle"] == "Conseiller municipal · Cannes" and car[0]["fin"] == "2026-03-15"
    assert car[0]["source"] == "rne" and car[0]["nature_periode"] == "mandat" and car[0]["fin_nature"] == "deduite"
    cov = {r["per"]: r["statut"] for r in _lignes(ctx, "SELECT * FROM couverture_carriere WHERE institution = 'local'")}
    assert cov[c["David Lisnard"]] == "partiel"


def test_sans_date_de_naissance_ni_decision_rien_n_est_rattache(tmp_path):
    z2 = _z2(tmp_path)
    d = _decisions(tmp_path / "d", platret=False)
    ctx, _, _ = _relier(z2, tmp_path / "z3", tmp_path / "r", TOUTES, decisions=d)
    per = ctx.un("SELECT per FROM candidat WHERE nom_liste = 'Gilles Platret'")
    assert ctx.un("SELECT count(*) FROM mandat_local_candidat WHERE per = ?", [per]) == 0
    k = _lignes(ctx, "SELECT * FROM couverture_carriere WHERE per = ? AND institution = 'local'", [per])[0]
    assert k["statut"] == "non_etabli" and "sans décision" in k["detail"]
    # Q51 : un seul élu de ce nom (né le 19/04/1973), non rattaché sans décision.
    assert "homonyme non rattaché : 1 élu de ce nom" in k["detail"]
    r = _lignes(ctx, "SELECT * FROM mandat_local_recherche WHERE per = ?", [per])[0]
    assert (r["raison"], r["elus_de_ce_nom"]) == ("homonyme_non_rattache", 1)


# -- Décisions du 23/11/2026 : fin observée (Q49), « non relu » (Q51), Wikidata P39 (Q52), homonymes (Q53).

def _relier_dates(z2, d, decisions, dates=None):
    from empreinte_src.identites import RegistreIdentites
    from empreinte_src.liaison import Contexte, ordonner, relier
    ctx = Contexte(str(z2), str(d / "z3"), dossier_decisions=str(decisions), generation=2,
                   date_reference="2026-11-23", registre=RegistreIdentites(str(d / "r")))
    ctx.dates_generations = dates or {}
    bilan = relier(ctx, ordonner(TOUTES))
    return ctx, {b["regle"].split("@")[0]: b for b in bilan}


def _entete(uid):
    with open(os.path.join(RNE, f"{uid}.csv"), encoding="utf-8") as f:
        return f.readline()


def test_fin_observee_entre_deux_releves(tmp_path):
    """Q49 : Lisnard n'est plus dans la publication suivante des conseillers départementaux ; ses
    lignes restent, finies à la date du premier relevé qui ne les porte plus."""
    z2 = _z2(tmp_path)
    e = Entrepot(str(tmp_path / "e"))
    pa_cfg = {"id": "rne-cd", "source": "rne", "type": "elus_rne", "format": "fichier",
              "url": "https://www.data.gouv.fr/fr/datasets/r/x", "uid": "elus-cd"}
    autre = ("06;Alpes-Maritimes;0601;Antibes-1;DUPONT;Jean;M;1960-01-01;85;Retraité;2021-07-01;;\n")
    e.versionner(pa_cfg, "R-cd2", [_membre("elus-cd", "elus-cd.csv", (_entete("elus-cd") + autre).encode())],
                 complet=True)
    e.clore("test")
    cfg = {"points_acces": [{"id": f"rne-{u[5:]}", "licence": "etalab-2.0"} for u in UIDS]}
    assert Lecture(Entrepot(str(tmp_path / "e")), str(z2), cfg).executer(rne_elus)["illisibles"] == 0
    ctx, bilan = _relier_dates(z2, tmp_path, _decisions(tmp_path / "d"), {1: "2026-11-13", 2: "2026-11-20"})
    per = ctx.un("SELECT per FROM candidat WHERE nom_liste = 'David Lisnard'")
    cd = _lignes(ctx, "SELECT * FROM mandat_local_candidat WHERE per = ? AND fichier = 'cd' ORDER BY nature_periode",
                 [per])
    assert [(r["nature_periode"], r["fin"], r["fin_nature"]) for r in cd] == [
        ("fonction", "2026-11-20", "observee"), ("mandat", "2026-11-20", "observee")]
    assert "relevé le 2026-11-13" in cd[0]["fin_raison"] and "relevé le 2026-11-20" in cd[0]["fin_raison"]
    # Les lignes municipales, toujours publiées, restent en cours.
    assert ctx.un("""SELECT count(*) FROM mandat_local_candidat WHERE per = ? AND fichier IN ('cm', 'maires')
                     AND fin IS NULL""", [per]) == 2
    assert bilan["R-MANDAT-LOCAL"]["couverture"]["fins_observees"] == [2, 2]


def test_wikidata_p39_mandats_passes(tmp_path):
    """Q52 : les fonctions locales terminées que déclare Wikidata, hors des périodes du répertoire."""
    from empreinte_src.lecteurs import wd_fonctions
    z2 = _z2(tmp_path)

    def w(decl, poste, debut, fin, jur=None):
        return {"element": "Q3018298", "declaration": f"Q3018298-{decl}", "poste": "Q1", "poste_libelle": poste,
                "debut": debut, "fin": fin, "juridiction": jur, "objet": None,
                "prov_url": "https://www.wikidata.org/wiki/Q3018298#P39", "_uid": "wikidata-p39"}
    _ecrire(z2, wd_fonctions, "fonction_wikidata", [
        w("a", "maire de Cannes", "2014-04-05", "2020-05-22"),                       # gardée : avant le répertoire
        w("b", "conseiller municipal de Cannes", "2020-05-18", "2026-03-14"),        # chevauche le répertoire
        w("c", "conseiller général des Alpes-Maritimes", "2008-03-16", None),        # sans fin
        w("d", "inspecteur général des finances", "2001-01-01", "2005-01-01"),       # pas locale
        w("e", "conseillère générale", "1990-03-01", "1995-03-01", "Var"),           # gardée
        w("f", "président du conseil de surveillance", "2010-01-01", "2012-01-01")])  # pas locale
    ctx, bilan = _relier_dates(z2, tmp_path, _decisions(tmp_path / "d"))
    per = ctx.un("SELECT per FROM candidat WHERE nom_liste = 'David Lisnard'")
    wd = _lignes(ctx, "SELECT * FROM mandat_local_candidat WHERE per = ? AND source = 'wikidata' ORDER BY debut", [per])
    assert [(r["fonction"], r["niveau"], r["nature_periode"], r["debut"], r["fin"], r["mandat_id"]) for r in wd] == [
        ("conseillère générale", "departemental", "mandat", "1990-03-01", "1995-03-01", "wikidata:Q3018298-e"),
        ("maire de Cannes", "municipal", "fonction", "2014-04-05", "2020-05-22", "wikidata:Q3018298-a")]
    assert {(r["declare_par"], r["fin_nature"]) for r in wd} == {("wikidata", "declaree")}
    car = _lignes(ctx, "SELECT * FROM carriere WHERE per = ? AND source = 'wikidata' ORDER BY debut", [per])
    assert car[0]["libelle"] == "conseillère générale · Var" and car[0]["declare_par"] == "wikidata"
    assert car[0]["mandat"] == "wikidata:Q3018298-e" and car[0]["institution"] == "local"
    assert bilan["R-MANDAT-LOCAL"]["couverture"]["lignes_declarees_par_wikidata"] == [2, 2]


def test_homonymes_nes_le_meme_jour_non_rattaches_et_a10(tmp_path):
    """Q53 : la clé de Lisnard désigne deux conseillers municipaux de deux communes : aucun
    rattachement par la clé, une ligne dans `mandat_local_ambigu`, l'avertissement A10."""
    from empreinte_src.controles_mandats_locaux import a10_elus_ambigus
    z2 = _z2(tmp_path)
    e = Entrepot(str(tmp_path / "e"))
    pa_cfg = {"id": "rne-cm", "source": "rne", "type": "elus_rne", "format": "fichier",
              "url": "https://www.data.gouv.fr/fr/datasets/r/x", "uid": "elus-cm"}
    with open(os.path.join(RNE, "elus-cm.csv"), encoding="utf-8") as f:
        cm = f.read()
    homonyme = "59;Nord;;;59350;Lille;LISNARD;David;M;1969-02-02;85;Retraité;2026-03-15;;;FR\n"
    e.versionner(pa_cfg, "R-cm2", [_membre("elus-cm", "elus-cm.csv", (cm + homonyme).encode())], complet=True)
    e.clore("test")
    cfg = {"points_acces": [{"id": f"rne-{u[5:]}", "licence": "etalab-2.0"} for u in UIDS]}
    Lecture(Entrepot(str(tmp_path / "e")), str(z2), cfg).executer(rne_elus)
    ctx, bilan = _relier_dates(z2, tmp_path, _decisions(tmp_path / "d"))
    per = ctx.un("SELECT per FROM candidat WHERE nom_liste = 'David Lisnard'")
    assert ctx.un("SELECT count(*) FROM mandat_local_candidat WHERE per = ? AND source = 'rne'", [per]) == 0
    amb = _lignes(ctx, "SELECT * FROM mandat_local_ambigu")
    assert [(a["candidat"], a["fichier"], a["collectivites_distinctes"]) for a in amb] == [("David Lisnard", "cm", 2)]
    assert ctx.un("SELECT raison FROM mandat_local_recherche WHERE per = ?", [per]) == "ambigu_non_rattache"
    k = _lignes(ctx, "SELECT * FROM couverture_carriere WHERE per = ? AND institution = 'local'", [per])[0]
    assert k["statut"] == "non_etabli" and k["detail"].startswith("Homonyme non rattaché")
    # Roussel, sans ambiguïté, reste rattaché.
    ro = ctx.un("SELECT per FROM candidat WHERE nom_liste = 'Fabien Roussel'")
    assert ctx.un("SELECT count(*) FROM mandat_local_candidat WHERE per = ?", [ro]) == 4

    class Ctrl:
        def __init__(s, con):
            s.con, s.anomalies = con, []

        def _a(s, *t):
            return all(ctx.existe(x) for x in t)

        def _x(s, sql, params=None):
            return s.con.execute(sql, params or []).fetchall()

        def _avertir(s, code, titre, objets, detail=None):
            s.anomalies.append((code, objets))
    c = Ctrl(ctx.con)
    a10_elus_ambigus(c)
    assert c.anomalies[0][0] == "A10" and "David Lisnard : 2 élus" in c.anomalies[0][1][0]


def test_lecteur_wd_fonctions():
    import orjson
    from empreinte_src.lecteurs import wd_fonctions

    class M:
        uid = "wikidata-p39"
        octets = orjson.dumps({"results": {"bindings": [
            {"item": {"value": "http://www.wikidata.org/entity/Q12961"},
             "st": {"value": "http://www.wikidata.org/entity/statement/Q12961-ABC"},
             "pos": {"value": "http://www.wikidata.org/entity/Q30185"}, "posLabel": {"value": "maire de Yerres"},
             "debut": {"value": "1995-06-25T00:00:00Z"}, "fin": {"value": "2017-07-23T00:00:00Z"}},
            {"item": {"value": "http://www.wikidata.org/entity/Q12961"},
             "st": {"value": "http://www.wikidata.org/entity/statement/Q12961-ABC"},
             "pos": {"value": "http://www.wikidata.org/entity/Q30185"}, "posLabel": {"value": "maire de Yerres"},
             "debut": {"value": "1995-06-25T00:00:00Z"}, "fin": {"value": "2017-07-23T00:00:00Z"}}]}})
    t = wd_fonctions.lire(M())["fonction_wikidata"]
    assert len(t) == 1 and t[0]["declaration"] == "Q12961-ABC" and t[0]["debut"] == "1995-06-25"
    assert t[0]["fin"] == "2017-07-23" and t[0]["poste_libelle"] == "maire de Yerres"
