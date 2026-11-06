"""Retrait à la source ou panne (cahier 6.0 ; doc. 2, 2.4)."""
from empreinte.depaquetage import depaqueter
from empreinte.entrepot import RETIRE, Entrepot
from tests.conftest import zip_avec


def _nuit(tmp_path, pa, membres, complet=True, delta=False, k=[0]):
    k[0] += 1
    z = zip_avec(str(tmp_path / f"a{k[0]}.zip"), membres)
    e = Entrepot(str(tmp_path / "e"))
    b = e.versionner(pa, f"R{k[0]}", depaqueter(z, "zip"), complet=complet, delta=delta)
    e.clore("test")
    return e, b


def test_objet_inchange_ne_cree_pas_de_version(tmp_path, pa_agenda):
    _nuit(tmp_path, pa_agenda, {"A.json": b"1", "B.json": b"2"})
    _, b = _nuit(tmp_path, pa_agenda, {"A.json": b"1", "B.json": b"2"})
    assert (b.nouvelles, b.inchanges) == (0, 2)


def test_retrait_seulement_sur_releve_complet(tmp_path, pa_agenda):
    _nuit(tmp_path, pa_agenda, {"A.json": b"1", "B.json": b"2"})
    _, b = _nuit(tmp_path, pa_agenda, {"A.json": b"1"}, complet=False)
    assert b.retraits == 0                         # lecture partielle : on ne conclut rien
    e, b = _nuit(tmp_path, pa_agenda, {"A.json": b"1"}, complet=True)
    assert b.retraits == 1 and e.presents("an-agenda-l17").keys() == {"A"}


def test_point_delta_ne_constate_jamais_de_retrait(tmp_path, pa_agenda):
    _nuit(tmp_path, pa_agenda, {"A.json": b"1"}, delta=True)
    _, b = _nuit(tmp_path, pa_agenda, {"B.json": b"2"}, delta=True)
    assert b.retraits == 0


def test_reapparition_apres_retrait(tmp_path, pa_agenda):
    _nuit(tmp_path, pa_agenda, {"A.json": b"1", "B.json": b"2"})
    _nuit(tmp_path, pa_agenda, {"A.json": b"1"})
    e, b = _nuit(tmp_path, pa_agenda, {"A.json": b"1", "B.json": b"2"})
    assert b.reapparitions == 1
    versions_b = [r for r in e._index if r["uid"] == "B"]
    assert [r["etat"] for r in versions_b] == ["present", RETIRE, "present"]


def test_prolonger_sur_304(tmp_path, pa_agenda):
    e, _ = _nuit(tmp_path, pa_agenda, {"A.json": b"1"})
    e2 = Entrepot(str(tmp_path / "e"))
    e2.prolonger("an-agenda-l17")
    assert e2.presents("an-agenda-l17")["A"]["vu_jusqu_au"] == e2.generation
