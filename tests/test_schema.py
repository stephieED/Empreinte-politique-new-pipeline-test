"""C4 : forme des fichiers servis contre le schéma commité (issue #43)."""
import gzip
import json
import os

import yaml

from empreinte_src.controles import Controles
from empreinte_src.schema import cle_section, relever, reecrire_colonnes, verifier

SCHEMA = {"statuts_couverture": ["complet", "panne"],
          "vocabulaires": {"sort_final": ["adopte", "non_connu"]},
          "colonnes": {"lignees/votes-N": ["scrutin", "sort_final"]}}


def _ecrire(racine, chemin, contenu):
    p = os.path.join(racine, chemin)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with gzip.open(p, "wt") as f:
        json.dump(contenu, f)


def _section(colonnes, lignes, statut="complet"):
    return {"section": "s", "colonnes": colonnes, "lignes": lignes, "couverture": {"statut": statut}}


def test_cle_section():
    assert cle_section("lignees/udi/votes-14.json.gz") == "lignees/votes-N"
    assert cle_section("candidats/x/paroles-textes-2017-s2-14.json.gz") == "candidats/paroles-textes-N-sN-N"
    assert cle_section("candidats/x/fiche.json.gz") is None
    assert cle_section("catalogue.json.gz") is None
    assert cle_section("candidats/x/mots/eg.json.gz") == cle_section("candidats/y/mots/21.json.gz") == "candidats/mots/*"


def test_forme_conforme_puis_ecarts(tmp_path):
    r = str(tmp_path / "site")
    _ecrire(r, "lignees/a/votes-14.json.gz", _section(["scrutin", "sort_final"], [["V1", "adopte"], ["V2", None]]))
    _ecrire(r, "lignees/a/votes-15.json.gz", _section(["scrutin", "sort_final"], []))   # vide : colonnes libres
    _ecrire(r, "lignees/a/fiche.json.gz", {"couverture": [{"section": "votes-14", "statut": "complet"}]})
    assert verifier(r, SCHEMA) == []
    # Colonne renommée, valeur hors vocabulaire, statut inconnu, section nouvelle.
    _ecrire(r, "lignees/b/votes-16.json.gz", _section(["scrutin", "sort"], [["V3", "adopte"]], "presque"))
    _ecrire(r, "lignees/b/avec-qui-16.json.gz", _section(["x"], [[1]]))
    _ecrire(r, "lignees/c/votes-17.json.gz", _section(["scrutin", "sort_final"], [["V4", "adoptee"]]))
    e = verifier(r, SCHEMA)
    assert any("colonnes différentes" in x and "['sort']" in x and "['sort_final']" in x for x in e)
    assert any("« sort_final » = « adoptee »" in x for x in e)
    assert any("statut de couverture « presque »" in x for x in e)
    assert any("« lignees/avec-qui-N » absente du schéma" in x for x in e)
    c = Controles(r)
    with open(tmp_path / "schema.yaml", "w") as f:
        yaml.safe_dump(SCHEMA, f)
    c.c4_forme(str(tmp_path / "schema.yaml"))
    assert c.bilan()["publication_autorisee"] is False


def test_schema_absent_bloque(tmp_path):
    c = Controles(str(tmp_path))
    c.c4_forme(str(tmp_path / "absent.yaml"))
    assert not c.bilan()["publication_autorisee"]


def test_reecrire_garde_les_vocabulaires(tmp_path):
    r = str(tmp_path / "site")
    _ecrire(r, "lignees/a/votes-14.json.gz", _section(["scrutin", "sort_final", "nouvelle"], [["V1", "adopte", 1]]))
    p = tmp_path / "schema.yaml"
    with open(p, "w") as f:
        yaml.safe_dump(SCHEMA, f)
    bilan = reecrire_colonnes(str(p), r)
    s = yaml.safe_load(open(p))
    assert s["colonnes"] == {"lignees/votes-N": ["scrutin", "sort_final", "nouvelle"]} == relever(r)
    assert s["vocabulaires"] == SCHEMA["vocabulaires"] and bilan["sections"] == 1


def test_schema_du_depot_bien_forme():
    p = os.path.join(os.path.dirname(__file__), "..", "config", "schema_fichiers.yaml")
    s = yaml.safe_load(open(p))
    assert set(s) == {"statuts_couverture", "vocabulaires", "colonnes"}
    assert "trou_source" in s["statuts_couverture"] and "suite_absente_des_archives" in s["vocabulaires"]["raison_sort"]
    assert all(isinstance(v, list) and v for v in s["colonnes"].values())


def test_un_paquet_releve_du_schema_de_sa_section(tmp_path):
    """Nuit du 13/11/2026 refusée par C4 : `candidats/francois-ruffin/amendements-2023-1` (les
    amendements de la XVIe relevés pour la première fois font dépasser un paquet). Le schéma ne
    connaissait que `candidats/amendements-N`."""
    r = str(tmp_path / "site")
    schema = {"colonnes": {"candidats/amendements-N": ["amendement", "sort_final"]},
              "vocabulaires": SCHEMA["vocabulaires"], "statuts_couverture": ["complet"]}
    for nom in ("amendements-2023-1", "amendements-2023-2", "amendements-2024"):
        _ecrire(r, f"candidats/x/{nom}.json.gz", _section(["amendement", "sort_final"], [["A", "adopte"]]))
    assert verifier(r, schema) == []
    _ecrire(r, "candidats/x/amendements-2025-1.json.gz", _section(["amendement", "autre"], [["A", 1]]))
    assert any("colonnes différentes" in x for x in verifier(r, schema))      # les colonnes comptent toujours
    _ecrire(r, "candidats/x/votes-14.json.gz", _section(["scrutin"], [["V"]]))
    assert any("« candidats/votes-N » absente du schéma" in x for x in verifier(r, schema))
