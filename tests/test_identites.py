"""Correction P1 : l'attribution d'un identifiant de personne ne change jamais."""
import random

import pytest

from empreinte_src.identites import RegistreIdentites, RegistreModifie, verifier_ajout_seul

GROUPES = [
    {("an", "PA722142"), ("wd", "Q3082206")},
    {("an", "PA720846")},
    {("an", "PA795900")},
    {("senat", "19830x"), ("wd", "Q1")},
]


def test_meme_numeros_quel_que_soit_l_ordre(tmp_path):
    a = RegistreIdentites(str(tmp_path / "a"))
    ra = a.attribuer(GROUPES, generation=1)
    melange = GROUPES[:]
    random.Random(4).shuffle(melange)
    b = RegistreIdentites(str(tmp_path / "b"))
    rb = b.attribuer(melange, generation=1)
    assert ra == rb


def test_attribution_conservee_d_une_mise_a_jour_a_l_autre(tmp_path):
    r = RegistreIdentites(str(tmp_path))
    avant = r.attribuer(GROUPES, generation=1)
    r.sauver()
    r2 = RegistreIdentites(str(tmp_path))       # nuit suivante : relu depuis l'entrepôt
    apres = r2.attribuer(list(reversed(GROUPES)) + [{("an", "PA1")}], generation=2)
    for cle, p in avant.items():
        assert apres[cle] == p
    assert apres[("an", "PA1")] == "per:000005"   # le suivant, et lui seul


def test_fusion_garde_le_plus_ancien(tmp_path):
    r = RegistreIdentites(str(tmp_path))
    r.attribuer([{("senat", "S1")}], generation=1)          # per:000001
    r.attribuer([{("an", "PA9")}], generation=2)            # per:000002
    res = r.attribuer([{("senat", "S1"), ("an", "PA9"), ("wd", "Q9")}], generation=3)
    assert set(res.values()) == {"per:000001"}
    assert r.fusions[-1]["per_absorbe"] == "per:000002"
    assert r.resoudre("per:000002") == "per:000001"


def test_separation_donne_un_numero_neuf(tmp_path):
    r = RegistreIdentites(str(tmp_path))
    r.attribuer([{("an", "PA1"), ("wd", "Q1")}], generation=1)
    neuf = r.separer("wd", "Q1", generation=2, decision="decisions/identite/x.yaml")
    assert neuf == "per:000002" and r.numero("an", "PA1") == "per:000001"


def test_registre_ampute_refuse(tmp_path):
    r = RegistreIdentites(str(tmp_path))
    r.attribuer(GROUPES, generation=1)
    ancien = [dict(x) for x in r.attributions]
    with pytest.raises(RegistreModifie):
        verifier_ajout_seul(ancien, ancien[1:])
    modifie = [dict(x) for x in ancien]
    modifie[0]["per"] = "per:999999"
    with pytest.raises(RegistreModifie):
        verifier_ajout_seul(ancien, modifie)
    clos = [dict(x) for x in ancien]
    clos[0]["jusqu_au"] = 2                      # seule modification permise
    verifier_ajout_seul(ancien, clos)
