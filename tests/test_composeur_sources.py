"""Référentiel des points d'accès (`sources.json.gz`, issue #73)."""
import gzip
import json
import os

import yaml

from empreinte_src.composeurs import sources
from empreinte_src.composition import Ecrivain
from empreinte_src.controles import Controles
from empreinte_src.liaison import Contexte

RACINE = os.path.join(os.path.dirname(__file__), "..")
POINTS = [
    {"id": "an-scrutins-l17", "source": "an", "url": "https://exemple/scrutins.zip", "licence": "etalab-2.0"},
    {"id": "pe-votes", "source": "europarl", "url": "https://exemple/pe", "licence": "cc-by-4.0"},
    {"id": "sycomore-fiches", "source": "sycomore", "url": "https://exemple/sycomore", "licence": None},
]
RELEVES = [
    {"point_acces": "an-scrutins-l17", "issue": "inchange", "date_source": "Sat, 22 Nov 2026 03:12:00 GMT"},
    {"point_acces": "pe-votes", "issue": "nouveau"},
    {"point_acces": "sycomore-fiches", "issue": "echec"},
]


def _contexte(tmp_path, decisions):
    d = tmp_path / "decisions" / "nom_point_acces"
    d.mkdir(parents=True)
    (d / "table.yaml").write_text(yaml.safe_dump(
        {"type": "nom_point_acces", "date": "2026-11-23", "decisions": decisions}, allow_unicode=True))
    (tmp_path / "z2").mkdir()
    return Contexte(str(tmp_path / "z2"), str(tmp_path / "z3"), str(tmp_path / "decisions"))


def _lire(ecr):
    with gzip.open(os.path.join(ecr.racine, "sources.json.gz")) as f:
        return json.load(f)


def test_referentiel_nom_adresse_licence_dates(tmp_path):
    ctx = _contexte(tmp_path, [
        {"point_acces": "an-scrutins-l17", "nom": "Assemblée nationale — scrutins de la XVIIe"},
        {"point_acces": "pe-votes", "nom": "Parlement européen — votes"},
        {"point_acces": "point-disparu", "nom": "Point retiré de la configuration"}])
    ecr = Ecrivain(str(tmp_path / "site"), "g000021", pannes={"sycomore-fiches": "2026-11-21T20:00:00+00:00"},
                   releves_reussis={"an-scrutins-l17": "2026-11-22T20:31:00+00:00", "pe-votes": None,
                                    "sycomore-fiches": "2026-11-15T21:00:00+00:00"},
                   releves_nuit=RELEVES, points_acces=POINTS)
    sources.composer(ctx, ecr)
    m = ecr.clore()
    s = _lire(ecr)
    pts = {l[0]: dict(zip(s["points_acces"]["colonnes"], l)) for l in s["points_acces"]["lignes"]}
    assert list(pts) == ["an-scrutins-l17", "pe-votes", "sycomore-fiches"]
    a = pts["an-scrutins-l17"]
    assert (a["nom"], a["raison_nom"], a["url"], a["licence"]) == (
        "Assemblée nationale — scrutins de la XVIIe", None, "https://exemple/scrutins.zip", "etalab-2.0")
    assert (a["date_source"], a["dernier_releve_reussi"]) == ("2026-11-22T03:12:00+00:00", "2026-11-22T20:31:00+00:00")
    # source sans date : vide avec sa raison, jamais la date de passage
    assert (pts["pe-votes"]["date_source"], pts["pe-votes"]["raison_date_source"]) == (
        None, "la source ne donne pas de date")
    # point sans nom proposé : il se voit
    sy = pts["sycomore-fiches"]
    assert (sy["nom"], sy["raison_nom"]) == (None, "aucun nom proposé dans references/nom_point_acces")
    assert (sy["licence"], sy["panne_depuis"]) == (None, "2026-11-21T20:00:00+00:00")
    assert s["noms_sans_point"]["lignes"] == [
        ["point-disparu", "Point retiré de la configuration", "nom_point_acces/table.yaml#2"]]
    # mêmes dates que la couverture du corpus (issue #74) : un seul calcul
    with gzip.open(os.path.join(ecr.racine, "couverture.json.gz")) as f:
        c = json.load(f)["points_acces"]
    i, j = c["colonnes"].index("date_source"), s["points_acces"]["colonnes"].index("date_source")
    assert [l[i] for l in c["lignes"]] == [l[j] for l in s["points_acces"]["lignes"]]
    ctrl = Controles(ecr.racine)
    ctrl.c2_liens({x["fiche"] for x in m["fiches"]})
    ctrl.c4_interdits()
    assert ctrl.bilan()["publication_autorisee"], ctrl.bilan()


def test_sans_configuration_transmise(tmp_path):
    ctx = _contexte(tmp_path, [])
    ecr = Ecrivain(str(tmp_path / "site"), "g1", pannes={"senat-export": "2026-11-20"})
    sources.composer(ctx, ecr)
    s = _lire(ecr)
    assert s["raison"] == "configuration des points d'accès non transmise"
    assert s["points_acces"]["lignes"][0][:6] == [
        "senat-export", None, None, "aucun nom proposé dans references/nom_point_acces", None, None]


def test_rien_a_servir(tmp_path):
    ecr = Ecrivain(str(tmp_path / "site"), "g1")
    sources.composer(_contexte(tmp_path, []), ecr)
    assert not os.path.exists(os.path.join(ecr.racine, "sources.json.gz"))


def test_table_des_noms_couvre_la_configuration():
    """Chaque point de `config/points_acces.yaml` a exactement un nom proposé, court, et aucun nom ne
    vise un point inconnu."""
    with open(os.path.join(RACINE, "config", "points_acces.yaml")) as f:
        ids = [p["id"] for p in yaml.safe_load(f)["points_acces"]]
    with open(os.path.join(RACINE, "references", "nom_point_acces", "table.yaml")) as f:
        table = yaml.safe_load(f)
    assert table["type"] == "nom_point_acces"
    noms = [d["point_acces"] for d in table["decisions"]]
    assert sorted(noms) == sorted(ids) and len(set(noms)) == len(noms)
    assert all(d["nom"] and len(d["nom"]) <= 80 for d in table["decisions"])
