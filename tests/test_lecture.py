"""Cadre de lecture (E3) : incrémental, relecture complète quand le lecteur change."""
import json
import zipfile

import pyarrow.parquet as pq

from empreinte_src.depaquetage import depaqueter
from empreinte_src.entrepot import Entrepot
from empreinte_src.lecture import Lecture
from empreinte_src.lecteurs import an_agenda

CFG = {"points_acces": [{"id": "an-agenda-l17", "licence": "etalab-2.0"}]}


def _ranger(tmp_path, pa_agenda, zip_):
    e = Entrepot(str(tmp_path / "e"))
    e.versionner({**pa_agenda}, f"R{e.generation}", depaqueter(zip_, "zip"), complet=True)
    e.clore("test")
    return Entrepot(str(tmp_path / "e"))


def test_lecture_puis_incrementale(tmp_path, extrait_agenda, pa_agenda):
    e = _ranger(tmp_path, pa_agenda, extrait_agenda)
    l = Lecture(e, str(tmp_path / "z2"), CFG)
    b = l.executer(an_agenda)
    assert b["lues"] == 6 and b["illisibles"] == 0 and b["lignes"]["reunion"] == 6
    t = pq.read_table(tmp_path / "z2" / "an_agenda__reunion.parquet").to_pylist()
    assert all(r["licence"] == "etalab-2.0" and r["prov_etat"] == "present" for r in t)
    assert "participants" not in pq.read_schema(tmp_path / "z2" / "an_agenda__reunion.parquet").names
    # Nuit suivante : un seul membre change.
    with zipfile.ZipFile(extrait_agenda) as z:
        membres = {n: z.read(n) for n in z.namelist()}
    nom = sorted(membres)[0]
    d = json.loads(membres[nom])
    d["reunion"]["cycleDeVie"]["etat"] = "Annulé"
    membres[nom] = json.dumps(d).encode()
    z2 = tmp_path / "n2.zip"
    with zipfile.ZipFile(z2, "w") as z:
        for n, o in membres.items():
            z.writestr(n, o)
    e2 = _ranger(tmp_path, pa_agenda, str(z2))
    b2 = Lecture(e2, str(tmp_path / "z2"), CFG).executer(an_agenda)
    assert b2["lues"] == 1
    t = pq.read_table(tmp_path / "z2" / "an_agenda__reunion.parquet").to_pylist()
    courantes = [r for r in t if r["prov_vu_jusqu_au"] == e2.generation_base]
    assert len(courantes) == 6                 # l'état courant : une ligne par réunion
    uid_change = nom.split("/")[-1][:-5]
    assert [r["etat"] for r in courantes if r["uid"] == uid_change] == ["Annulé"]  # état de la source intact
    uid = nom.split("/")[-1][:-5]
    hist = sorted((r["prov_version"], r["prov_etat"], r["prov_vu_jusqu_au"]) for r in t if r["uid"] == uid)
    assert len(hist) == 2                      # l'ancienne version reste, datée


def test_lecteur_corrige_relit_tout_l_historique(tmp_path, extrait_agenda, pa_agenda, monkeypatch):
    e = _ranger(tmp_path, pa_agenda, extrait_agenda)
    Lecture(e, str(tmp_path / "z2"), CFG).executer(an_agenda)
    monkeypatch.setattr(an_agenda, "VERSION", an_agenda.VERSION + 1)
    b = Lecture(e, str(tmp_path / "z2"), CFG).executer(an_agenda)
    assert b["lues"] == 6
    t = pq.read_table(tmp_path / "z2" / "an_agenda__reunion.parquet").to_pylist()
    assert {r["lecteur"] for r in t} == {f"an_agenda@{an_agenda.VERSION}"}


def test_point_collecte_mais_pas_encore_lu(tmp_path, extrait_agenda, pa_agenda):
    """`lire: false` : l'archive est dans l'entrepôt, mais ne produit aucun fait tant que son
    lecteur et ses fiches ne sont pas prêts (mise en service par étapes, 07/11/2026). Quand le
    point passe à `lire: true`, ses versions sont lues à la nuit suivante."""
    e = _ranger(tmp_path, pa_agenda, extrait_agenda)
    cfg = {"points_acces": [{"id": "an-agenda-l17", "licence": "etalab-2.0", "lire": False}]}
    b = Lecture(e, str(tmp_path / "z2"), cfg).executer(an_agenda)
    assert b["lues"] == 0
    assert pq.read_table(tmp_path / "z2" / "an_agenda__reunion.parquet").num_rows == 0
    b = Lecture(e, str(tmp_path / "z2"), CFG).executer(an_agenda)
    assert b["lues"] == 6
