"""Contrôles qui se taisaient (issues #39, #40, #41)."""
import json
import subprocess
import types

import pyarrow.parquet as pq
import pytest

from empreinte_src import distant, rattrapage
from empreinte_src.alertes import sujets_du_rapport
from empreinte_src.controles import Controles
from empreinte_src.lecture import Lecture
from empreinte_src.lecteurs import an_agenda

from .test_lecture import CFG, _ranger


# -- #39 : lecteur en erreur ---------------------------------------------------------------------

def test_lecteur_en_erreur_au_milieu_rien_de_partiel_et_relu_ensuite(tmp_path, extrait_agenda, pa_agenda,
                                                                     monkeypatch):
    """Un lecteur qui rend un premier lot puis lève une exception : le lot partiel n'est pas
    gardé, la version n'est pas inscrite comme lue (elle sera relue), et elle est nommée."""
    e = _ranger(tmp_path, pa_agenda, extrait_agenda)
    vrai = an_agenda.lire
    vise = sorted(r["uid"] for r in e._index)[0]

    def lire(m):
        if m.uid != vise:
            return vrai(m)

        def lots():
            yield vrai(m)                        # un lot complet est rendu…
            raise ValueError("format changé")    # … puis le lecteur tombe
        return lots()
    monkeypatch.setattr(an_agenda, "lire", lire)
    l = Lecture(e, str(tmp_path / "z2"), CFG)
    b = l.executer(an_agenda)
    assert b["illisibles"] == 1 and {u for _, u, _ in l.illisibles} == {vise}
    t = pq.read_table(tmp_path / "z2" / "an_agenda__reunion.parquet").to_pylist()
    assert len(t) == 5 and vise not in {r["prov_uid"] for r in t}
    # Le lecteur réparé : la version est relue, sans attendre un changement de version du lecteur.
    monkeypatch.setattr(an_agenda, "lire", vrai)
    l2 = Lecture(e, str(tmp_path / "z2"), CFG)
    assert l2.executer(an_agenda)["lues"] == 1 and not l2.illisibles


# -- #40 : publication précédente introuvable ----------------------------------------------------

def _gh_sequence(reponses):
    appels = []

    def faux(*args, capture=True, check=True):
        code, out, err = reponses[min(len(appels), len(reponses) - 1)]
        appels.append(args)
        return subprocess.CompletedProcess(args, code, out, err)
    return faux, appels


def test_derniere_publication_absente_seulement_si_la_release_n_existe_pas(monkeypatch):
    faux, _ = _gh_sequence([(1, "", "release not found")])
    monkeypatch.setattr(distant, "_gh", faux)
    assert distant.derniere_publication("o/d", pause_s=0) is None


def test_derniere_publication_erreur_api_leve_au_lieu_de_sauter_c1(monkeypatch):
    faux, appels = _gh_sequence([(1, "", "HTTP 502: Bad Gateway")])
    monkeypatch.setattr(distant, "_gh", faux)
    with pytest.raises(RuntimeError, match="illisible après 3 essais"):
        distant.derniere_publication("o/d", pause_s=0)
    assert len(appels) == 3


def test_derniere_publication_erreur_passagere_puis_reponse(monkeypatch):
    ok = json.dumps({"assets": [{"name": "faits-publies-g000010.parquet"}]})
    faux, appels = _gh_sequence([(1, "", "HTTP 502"), (0, ok, "")])
    monkeypatch.setattr(distant, "_gh", faux)
    assert distant.derniere_publication("o/d", pause_s=0) == "faits-publies-g000010.parquet"
    assert len(appels) == 2


def test_c1_c6_sans_publication_precedente_le_disent(tmp_path):
    c = Controles(str(tmp_path))
    c.c1_c6_comparer(None, str(tmp_path / "faits.parquet"))
    a = c.bilan()["anomalies"]
    assert [(x["controle"], x["bloquant"]) for x in a] == [("C1-C6", False)]


# -- #41 : rattrapage ------------------------------------------------------------------------------

def test_rattrapage_en_erreur_la_nuit_continue(monkeypatch, capsys):
    appels = []

    def chercher(depot, run):
        appels.append(1)
        raise subprocess.CalledProcessError(1, ["gh", "api"], stderr="HTTP 500")
    monkeypatch.setattr(rattrapage, "chercher", chercher)
    monkeypatch.setattr("sys.argv", ["rattrapage", "--depot", "o/d", "--pause", "0"])
    rattrapage.main()                                   # ne lève pas : la nuit continue
    sortie = json.loads(capsys.readouterr().out)
    assert set(sortie) == {"erreur"} and "CalledProcessError" in sortie["erreur"] and len(appels) == 3
    sujets = sujets_du_rapport({"releves": [], "rattrapage_erreur": sortie["erreur"]})
    assert "a continué sans rattrapage" in sujets["rattrapage"]


def test_workflow_decide_la_nuit_avant_le_rattrapage():
    import os
    wf = open(os.path.join(os.path.dirname(__file__), "..", ".github", "workflows", "mise-a-jour.yml")).read()
    assert wf.index('echo "faire=$FAIRE"') < wf.index("python -m empreinte_src.rattrapage")
    assert "--rattrapage-erreur" in wf
