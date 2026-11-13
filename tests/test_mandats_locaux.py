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
    li = m[c["David Lisnard"]]
    assert [(r["fonction"], r["collectivite"], r["debut"], r["fin"]) for r in li] == [
        ("Maire", "Cannes", "2020-05-23", "2026-03-15"),
        ("3ème Vice-président du conseil départemental", "Cannes-2 · Alpes-Maritimes", "2021-07-01", None),
        ("Maire", "Cannes", "2026-03-21", None)]
    assert li[0]["fin_deduite"] is True and li[0]["fin_raison"].startswith("fin déduite")
    assert {r["methode"] for r in li} == {"nom_prenom_naissance"}
    # Roussel : seul l'élu de même naissance ; les trois homonymes sont écartés.
    ro = m[c["Fabien Roussel"]]
    # Maire depuis le 30/01/2025 dans le conseil élu en 2020 (sortants), réélu en 2026.
    assert [(r["collectivite"], r["naissance"], r["debut"], r["fin"]) for r in ro] == [
        ("Saint-Amand-Les-Eaux", "1969-04-16", "2025-01-30", "2026-03-15"),
        ("Saint-Amand-Les-Eaux", "1969-04-16", "2026-03-22", None)]
    # Platret : par la décision.
    pl = m[c["Gilles Platret"]]
    assert {r["methode"] for r in pl} == {"decision"} and len(pl) == 3      # maire 2020, maire 2026, région
    assert bilan["R-MANDAT-LOCAL"]["couverture"]["candidats_avec_mandat_local"] == [3, 3]
    # Frise et couverture.
    car = _lignes(ctx, "SELECT * FROM carriere WHERE per = ? AND institution = 'local' ORDER BY debut",
                  [c["David Lisnard"]])
    assert car[0]["libelle"] == "Maire · Cannes" and car[0]["fin"] == "2026-03-15" and car[0]["source"] == "rne"
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
