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


def test_l_acquis_d_un_essai_n_est_jamais_rattrape():
    """Un essai n'écrit rien : son artefact ne s'appelle pas `acquis-g…`, seul nom que le
    rattrapage reprend (défaut constaté le 06/11/2026 : la nuit suivante aurait écrit l'essai)."""
    import re
    from empreinte_src import rattrapage
    wf = _wf()
    etapes = wf["jobs"]["collecter"]["steps"]
    collecte = next(e for e in etapes if e.get("id") == "collecte")["run"]
    assert 'then echo "acquis=essai-g$G"; else echo "acquis=acquis-g$G"' in collecte
    envoi = next(e for e in etapes if e.get("uses", "").startswith("actions/upload-artifact"))
    assert envoi["with"]["name"] == "${{ steps.collecte.outputs.acquis }}"
    # Le rattrapage ne reconnaît que `acquis-gNNNNNN`.
    assert "acquis-g(\\d{6})" in open(rattrapage.__file__).read()
    assert not re.fullmatch(r"acquis-g(\d{6})", "essai-g000003")
