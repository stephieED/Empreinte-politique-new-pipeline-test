"""Une nuit dont l'écriture n'a pas eu lieu est écrite par la nuit suivante (doc. 2, 2.4)."""
import json
import shutil

from empreinte import rattrapage
from empreinte.cli import main
from empreinte.depaquetage import depaqueter
from empreinte.distant import base_attendue
from empreinte.entrepot import Entrepot
from tests.conftest import zip_avec


def _nuit(dossier, pa, membres, tmp_path, n):
    e = Entrepot(str(dossier))
    z = zip_avec(str(tmp_path / f"n{n}.zip"), membres)
    e.versionner(pa, f"R{n}", depaqueter(z, "zip"), complet=True)
    return e.clore("test")


def test_nuit_non_ecrite_puis_rattrapee(tmp_path, pa_agenda):
    distant = tmp_path / "distant"                      # ce que l'entrepôt distant contient
    _nuit(distant, pa_agenda, {"A.json": b"1"}, tmp_path, 1)          # génération 1, écrite
    # Nuit 2 : collectée sur une copie, mais jamais écrite (son acquis reste en artefact).
    nuit2 = tmp_path / "artefact" / "entrepot"
    shutil.copytree(distant, nuit2)
    m2 = _nuit(nuit2, pa_agenda, {"A.json": b"1", "B.json": b"2"}, tmp_path, 2)
    assert (m2["generation"], m2["base"]) == (2, 1)
    # Nuit 3 : part du distant (génération 1), superpose la nuit 2, puis collecte.
    nuit3 = tmp_path / "travail3"
    shutil.copytree(distant, nuit3)
    main(["superposer", "--entrepot", str(nuit3), "--depuis", str(nuit2),
          "--rapport", str(tmp_path / "r.json")])
    m3 = _nuit(nuit3, pa_agenda, {"A.json": b"1", "B.json": b"2", "C.json": b"3"}, tmp_path, 3)
    assert (m3["generation"], m3["base"]) == (3, 2)
    assert base_attendue(str(nuit3), m3) == 1           # écrite sur la génération 1 distante
    e = Entrepot(str(nuit3))
    assert {r["uid"]: r["vu_du"] for r in e._index} == {"A": 1, "B": 2, "C": 3}   # aucune nuit perdue
    assert "rattrapage/manifeste.json" not in m3["fichiers"]


def test_chercher_ne_prend_que_la_nuit_qui_suit_la_courante(monkeypatch):
    monkeypatch.setattr(rattrapage, "manifeste_distant", lambda depot: {"generation": 5})
    artefacts = {"artifacts": [
        {"name": "acquis-g000005", "expired": False, "workflow_run": {"id": 1}, "created_at": "1"},
        {"name": "acquis-g000006", "expired": False, "workflow_run": {"id": 2}, "created_at": "2"},
        {"name": "acquis-g000006", "expired": True, "workflow_run": {"id": 3}, "created_at": "3"},
        {"name": "acquis-g000007", "expired": False, "workflow_run": {"id": 4}, "created_at": "4"},
    ]}

    class R:
        stdout = json.dumps(artefacts)
    monkeypatch.setattr(rattrapage.subprocess, "run", lambda *a, **k: R())
    assert rattrapage.chercher("d", run_actuel="9") == {"run": "2", "nom": "acquis-g000006",
                                                        "generation": 6, "cree_le": "2"}
    assert rattrapage.chercher("d", run_actuel="2") == {}
