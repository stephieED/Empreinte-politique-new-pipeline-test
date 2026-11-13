"""A9 : valeurs vidées d'une publication à l'autre (issue #42, décision du 13/11/2026)."""
import json

import pyarrow as pa
import pyarrow.parquet as pq

from empreinte_src.controles import Controles, _videes

COLS = ["fiche", "section", "type_fait", "id_acteur", "id_autre", "valeur"]


def _faits(chemin, lignes):
    pq.write_table(pa.table({c: [l.get(c) for l in lignes] for c in COLS}), chemin)


def test_feuilles_videes():
    avant = {"nb": 6, "zero": 0, "nom": "X", "naissance": {"valeur": "1970-01-01", "source": "wd"},
             "liste": ["a"], "drapeau": True, "au": "2026-11-12"}
    apres = {"nb": 0, "zero": 0, "nom": "X", "naissance": {"valeur": None, "source": "wd"},
             "liste": [], "drapeau": False, "au": "2026-11-13"}
    assert sorted(_videes(avant, apres)) == [("liste", "vide"), ("naissance.valeur", "vide"), ("nb", "a_zero")]
    assert list(_videes({"nb": 3}, {})) == [("nb", "a_zero")]             # champ disparu


def test_a9_avertit_au_dela_du_seuil_et_ignore_les_identites_multiples(tmp_path):
    avant = [{"fiche": f"candidat/c{k}", "section": "entete", "type_fait": "identite_personne",
              "id_autre": f"per:{k}", "valeur": json.dumps({"profession": {"valeur": "avocat"}})} for k in range(3)]
    avant += [{"fiche": "lignee/l", "section": "s", "type_fait": "effectif", "id_autre": "m",
               "valeur": json.dumps({"date": d, "effectif": e})} for d, e in (("1", 0), ("2", 62))]
    apres = [dict(x) for x in avant]
    apres[0]["valeur"] = json.dumps({"profession": {"valeur": None}})     # un en-tête vidé
    apres[3]["valeur"], apres[4]["valeur"] = apres[4]["valeur"], apres[3]["valeur"]  # même identité, ordre changé
    _faits(tmp_path / "a.parquet", avant)
    _faits(tmp_path / "b.parquet", apres)
    c = Controles(str(tmp_path))
    c.a9_valeurs_videes(str(tmp_path / "a.parquet"), str(tmp_path / "b.parquet"))
    a9 = [a for a in c.bilan()["anomalies"] if a["controle"] == "A9"]
    assert len(a9) == 1 and not a9[0]["bloquant"]
    assert a9[0]["exemples"] == ["identite_personne.profession.valeur : valeur vidée pour 1 faits sur 3, "
                                 "dont candidat/c0|identite_personne|per:0"]
    # Sans publication précédente : rien (C1-C6 le dit déjà).
    c2 = Controles(str(tmp_path))
    c2.a9_valeurs_videes(None, str(tmp_path / "b.parquet"))
    assert c2.bilan()["anomalies"] == []


def test_a9_compteur_isole_et_identite_partagee(tmp_path):
    """#42 rouverte (décision du 13/11 « Nombre à 0 : toujours ») : un seul compteur qui tombe à 0
    est signalé ; les comptes d'un candidat par institution, sous une même identité, s'apparient."""
    def compte(inst, v):
        return {"fiche": "candidat/x", "section": "entete", "type_fait": "compte_candidat",
                "id_autre": "mandats", "valeur": json.dumps({"institution": inst, "famille": "mandats", "valeur": v})}
    autres = [{"fiche": f"candidat/c{k}", "section": "votes", "type_fait": "positions", "id_autre": f"p{k}",
               "valeur": json.dumps({"nb": 10})} for k in range(200)]
    avant = [compte("assemblee", 6), compte("senat", None)] + autres
    apres = [compte("assemblee", 0), compte("senat", None)] + autres[:-1] + [
        {**autres[-1], "valeur": json.dumps({"nb": 0})}]                # 1 sur 200 : sous l'ancien seuil
    _faits(tmp_path / "a.parquet", avant)
    _faits(tmp_path / "b.parquet", apres)
    c = Controles(str(tmp_path))
    c.a9_valeurs_videes(str(tmp_path / "a.parquet"), str(tmp_path / "b.parquet"))
    ex = [a for a in c.bilan()["anomalies"] if a["controle"] == "A9"][0]["exemples"]
    assert any(x.startswith("compte_candidat.valeur : nombre passé à 0 ou à rien pour 1 faits") for x in ex)
    assert any(x.startswith("positions.nb : nombre passé à 0 ou à rien pour 1 faits sur 200") for x in ex)
