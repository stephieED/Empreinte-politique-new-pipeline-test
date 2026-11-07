"""Contrôles bloquants (E6) : C1, C2, C4, C6 et la levée ciblée."""
import pyarrow as pa
import pyarrow.parquet as pq

from empreinte_src.composition import Ecrivain
from empreinte_src.controles import Controles


def _faits(p, lignes):
    pq.write_table(pa.Table.from_pylist(lignes), p)
    return str(p)


def _f(fiche, section, valeur):
    return {"fiche": fiche, "section": section, "type_fait": "t", "valeur": valeur}


def test_c1_perte_non_expliquee_puis_levee(tmp_path):
    avant = _faits(tmp_path / "a.parquet", [_f("legislature/17", "textes", '{"dossier":"DLR1"}'),
                                            _f("legislature/17", "textes", '{"dossier":"DLR2"}')])
    apres = _faits(tmp_path / "b.parquet", [_f("legislature/17", "textes", '{"dossier":"DLR1"}')])
    c = Controles(str(tmp_path))
    c.c1_c6_comparer(avant, apres)
    b = c.bilan()
    assert not b["publication_autorisee"] and b["anomalies"][0]["controle"] == "C1"
    # La source a modifié DLR2 cette nuit : la perte est expliquée.
    c = Controles(str(tmp_path))
    c.c1_c6_comparer(avant, apres, uids_changes_a_la_source={"DLR2"})
    assert c.bilan()["publication_autorisee"]
    # Levée par décision, pour cette anomalie précise.
    e = b["anomalies"][0]["empreinte"]
    c = Controles(str(tmp_path), levees=[{"empreinte": e, "fichier": "decisions/levee/x.yaml"}])
    c.c1_c6_comparer(avant, apres)
    assert c.bilan()["publication_autorisee"]
    assert c.bilan()["anomalies"][0]["levee_par"] == "decisions/levee/x.yaml"


def test_c6_effondrement(tmp_path):
    avant = _faits(tmp_path / "a.parquet", [_f("g/x", "actes", f'{{"i":{i}}}') for i in range(20)])
    apres = _faits(tmp_path / "b.parquet", [_f("g/x", "actes", f'{{"i":{i}}}') for i in range(5)])
    c = Controles(str(tmp_path))
    c.c1_c6_comparer(avant, apres, uids_changes_a_la_source=None)
    assert {a["controle"] for a in c.anomalies} == {"C1", "C6"}


def test_c2_et_c4_sur_les_fichiers_servis(tmp_path):
    ecr = Ecrivain(str(tmp_path), "p1")
    f = ecr.fiche("legislature", "17", "XVIIe législature")
    f.section("gouvernements", [{"nom": "Bayrou", "lien": "gouvernement/bayrou"}], type_fait="g")
    f.section("deputes", [{"acteur": "PA1", "taux_de_presence": 0.9}], type_fait="d")
    ecr.clore()
    c = Controles(ecr.racine)
    c.c2_liens({"legislature/17"})
    c.c4_interdits()
    assert {a["controle"] for a in c.anomalies} == {"C2", "C4"}
    assert not c.bilan()["publication_autorisee"]


def test_c5_section_complete_avec_source_en_panne(tmp_path):
    ecr = Ecrivain(str(tmp_path), "p1")
    f = ecr.fiche("legislature", "17", "XVIIe législature")
    f.section("textes", [{"dossier": "DLR1"}], type_fait="t",
              couverture={"statut": "complet", "points_acces": ["an-dossiers-l17"]})
    ecr.clore()
    c = Controles(ecr.racine)
    c.c5_couverture([{"point_acces": "an-dossiers-l17", "issue": "echec"}])
    assert [a["controle"] for a in c.anomalies] == ["C5"]   # section et en-tête : une seule anomalie
    c = Controles(ecr.racine)
    c.c5_couverture([{"point_acces": "an-dossiers-l17", "issue": "inchange"}])
    assert not c.anomalies


def test_source_en_panne_la_section_le_dit_et_la_publication_continue(tmp_path):
    """Scénario 2 de la commande : le Sénat ne répond plus ; la section « fonctions » qui en dépend
    passe en « panne », datée, et C5 ne bloque pas (constaté le 07/11/2026 : export du Sénat de
    444 octets, publication refusée faute de ce marquage)."""
    import gzip
    import json
    import os
    releve = {"point_acces": "senat-export", "issue": "suspect", "debut": "2026-11-07T06:55:26+00:00"}
    ecr = Ecrivain(str(tmp_path), "g000003", pannes={"senat-export": "2026-11-07T06:55:26+00:00"})
    f = ecr.fiche("candidat", "x", "X")
    f.section("fonctions", [{"a": 1}], "fonction",
              couverture={"famille": "fonctions", "statut": "complet", "detail": "Mandats.",
                          "points_acces": ["an-amo30-l17", "senat-export"]})
    f.section("votes", [{"a": 1}], "vote",
              couverture={"famille": "votes", "statut": "complet", "points_acces": ["an-scrutins-l17"]})
    ecr.clore()
    with gzip.open(os.path.join(ecr.racine, "candidats", "x", "fonctions.json.gz")) as fi:
        c = json.load(fi)["couverture"]
    assert (c["statut"], c["statut_sans_panne"], c["points_en_panne"]) == ("panne", "complet", ["senat-export"])
    assert c["panne_depuis"].startswith("2026-11-07") and "Source en panne depuis le 2026-11-07" in c["detail"]
    with gzip.open(os.path.join(ecr.racine, "candidats", "x", "fiche.json.gz")) as fi:
        entete = {x["section"]: x["statut"] for x in json.load(fi)["couverture"]}
    assert entete == {"fonctions": "panne", "votes": "complet"}
    ctrl = Controles(ecr.racine)
    ctrl.c5_couverture([releve])
    assert ctrl.bilan()["publication_autorisee"], ctrl.bilan()
