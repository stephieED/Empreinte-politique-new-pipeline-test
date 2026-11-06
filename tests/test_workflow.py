"""Correction P3 : chaque tâche a les droits minimaux, et seule `ecrire` écrit."""
import os

import yaml

WF = os.path.join(os.path.dirname(__file__), "..", ".github", "workflows", "mise-a-jour.yml")


def _wf():
    with open(WF) as f:
        return yaml.safe_load(f)


def test_droit_par_defaut_en_lecture_seule():
    assert _wf()["permissions"] == {"contents": "read"}


def test_chaque_tache_declare_ses_droits():
    for nom, tache in _wf()["jobs"].items():
        assert "permissions" in tache, f"la tâche {nom} ne déclare pas ses droits"


def test_seule_ecrire_ecrit_le_contenu():
    for nom, tache in _wf()["jobs"].items():
        droits = tache["permissions"]
        if nom == "ecrire":
            assert droits == {"contents": "write"}
        elif nom == "alerter":
            assert droits == {"issues": "write"}
        elif nom in ("preparer", "collecter"):      # lisent l'artefact d'une nuit à rattraper
            assert droits == {"contents": "read", "actions": "read"}, f"{nom} : {droits}"
        else:
            assert droits == {"contents": "read"}, f"{nom} : {droits}"


def test_aucune_autre_tache_n_ecrit():
    for nom, tache in _wf()["jobs"].items():
        ecritures = {k for k, v in tache["permissions"].items() if v == "write"}
        assert ecritures <= ({"contents"} if nom == "ecrire" else {"issues"} if nom == "alerter" else set())


def test_ecrire_tourne_meme_si_le_calcul_echoue():
    cond = _wf()["jobs"]["ecrire"]["if"]
    assert "always()" in cond and "needs.collecter.result == 'success'" in cond
