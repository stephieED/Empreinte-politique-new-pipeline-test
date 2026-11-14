"""Lecteur `an_questions` : extraits réels des trois archives de questions de la XVIIe (fiche
`tests/extraits/an_questions.md`)."""
import os
import zipfile

import orjson
import pyarrow.parquet as pq

from empreinte_src.depaquetage import depaqueter
from empreinte_src.entrepot import Entrepot
from empreinte_src.export import exporter
from empreinte_src.lecture import Lecture, MembreLu
from empreinte_src.lecteurs import an_questions

EXTRAITS = os.path.join(os.path.dirname(__file__), "extraits")
ZIPS = {t: os.path.join(EXTRAITS, f"questions_{t}_l17_extrait.zip")
        for t in ("ecrites", "gouvernement", "orales")}
TYPES = {"ecrites": "questions_ecrites", "gouvernement": "questions_gouvernement",
         "orales": "questions_orales"}


def _octets(t, uid):
    with zipfile.ZipFile(ZIPS[t]) as z:
        return z.read(f"json/{uid}.json")


def _lire_octets(octets, uid="x"):
    (q,) = an_questions.lire(MembreLu("p", "an", "questions", uid, f"json/{uid}.json", 1, "e",
                                      octets, "etalab-2.0"))["question"]
    return q


def _lire(t, uid):
    return _lire_octets(_octets(t, uid), uid)


def test_question_ecrite_avec_reponse_et_erratum():
    q = _lire("ecrites", "QANR5L17QE17917")
    assert (q["type"], q["numero"], q["legislature"]) == ("QE", "17917", "17")
    assert (q["auteur"], q["auteur_mandat"], q["auteur_groupe"]) == ("PA841295", "PM842882", "PO845419")
    assert q["ministere_interroge"] == "PO873667" and q["rubrique"] == "travail"
    assert q["date_question"] == "2026-09-01" and q["texte_question"].startswith("M. Pierrick Courbon")
    # Deux publications de la réponse : l'originale est le texte principal, l'erratum à part.
    assert q["date_reponse"] == "2026-09-29" and q["page_jo_reponse"] == "9226"
    assert q["texte_reponse"].startswith("Le Gouvernement est attentif")
    assert [e["date_jo"] for e in q["errata_reponse"]] == ["2026-10-20"]
    assert q["errata_reponse"][0]["erratum"] and q["errata_reponse"][0]["texte"].startswith("<p>")
    assert (q["code_cloture"], q["date_cloture"]) == ("REP_PUB", "2026-09-29")
    assert q["prov_url"] is None              # adresse publique non vérifiée dans les données


def test_erratum_de_question_sans_texte():
    q = _lire("ecrites", "QANR5L17QE16918")
    assert q["date_question"] == "2026-07-14"
    assert q["errata_question"] == [{"date_jo": "2026-07-21", "num_jo": "20260029",
                                     "page_jo": "6951", "texte": None,
                                     "erratum": 'Dans le titre de la question, lire "Compatibilité" au lieu de "Comptabilité"'}]
    assert q["texte_reponse"] is None and q["code_cloture"] is None   # cloture: null


def test_attributions_renouvellements_signalement_en_liste():
    q = _lire("ecrites", "QANR5L17QE2225")
    assert [a["organe"] for a in q["ministeres_attributaires"]] == \
        ["PO847668", "PO855083", "PO873437", "PO873685"]
    assert q["ministere_interroge"] == "PO847668"
    assert q["dates_renouvellement"] == ["2025-04-01", "2025-10-21", "2026-06-23"]
    assert (q["date_depot_signalement"], q["date_jo_signalement"]) == ("2026-07-06", "2026-07-07")
    assert q["date_reponse"] is None


def test_question_au_gouvernement_un_seul_bloc():
    q = _lire("gouvernement", "QANR5L17QG390")
    assert q["type"] == "QG" and q["texte_question"] is None and q["date_question"] is None
    assert q["texte_reponse"].startswith('</p><p align="CENTER"> CONTINUITÉ TERRITORIALE')
    assert (q["date_reponse"], q["type_jo_reponse"], q["page_jo_reponse"]) == \
        ("2025-02-12", "JO_DEBAT", "1125")
    assert [a["organe"] for a in q["ministeres_attributaires"]] == ["PO855072"]  # objet seul


def test_questions_orales():
    q = _lire("orales", "QANR5L17QOSD110")
    assert q["type"] == "QOSD" and len(q["ministeres_attributaires"]) == 2
    assert q["date_reponse"] == "2025-02-05"
    r = _lire("orales", "QANR5L17QOSD680")
    assert r["texte_reponse"] is None and r["date_question"] == "2026-03-31"


def _capitales(x):
    if isinstance(x, dict):
        return {k.upper(): _capitales(w) for k, w in x.items()}
    if isinstance(x, list):
        return [_capitales(w) for w in x]
    return x


def test_cles_en_capitales_tolerees():
    """XVe : les clés sont en capitales (cahier 3.1.6). Faute d'archive XVe locale, on vérifie
    la tolérance sur un extrait réel dont on a mis les clés en capitales."""
    for t, uid in (("ecrites", "QANR5L17QE17917"), ("ecrites", "QANR5L17QE2225"),
                   ("gouvernement", "QANR5L17QG390")):
        b = _octets(t, uid)
        assert _lire_octets(orjson.dumps(_capitales(orjson.loads(b))), uid) == _lire_octets(b, uid)


def test_cadre_complet_et_export_sans_doublon(tmp_path):
    e = Entrepot(str(tmp_path / "e"))
    cfg = {"points_acces": []}
    for t, z in ZIPS.items():
        pa_ = {"id": f"an-questions-{t}-l17", "source": "an", "type": TYPES[t], "format": "zip",
               "url": f"http://exemple.invalid/{t}.json.zip"}
        cfg["points_acces"].append({"id": pa_["id"], "licence": "etalab-2.0"})
        e.versionner(pa_, f"R{t}", depaqueter(z, "zip"), complet=True)
    e.clore("test")
    e = Entrepot(str(tmp_path / "e"))
    b = Lecture(e, str(tmp_path / "z2"), cfg).executer(an_questions)
    assert b["illisibles"] == 0 and b["lues"] == 6 and b["lignes"]["question"] == 6
    t = pq.read_table(tmp_path / "z2" / "an_questions__question.parquet").to_pylist()
    assert {r["type"] for r in t} == {"QE", "QG", "QOSD"}
    res = exporter(str(tmp_path / "z2"), [an_questions], str(tmp_path / "x"))
    assert res["cles_en_double"] == 0 and res["faits_par_type"] == {"question": 6}


def test_dates_de_la_xve_ramenees_au_format_iso():
    """L'archive de la XVe publie ses dates en JJ/MM/AAAA (14/11/2026) : le lecteur (version 2) les
    ramène en AAAA-MM-JJ, comme les autres législatures."""
    from empreinte_src.lecteurs.an_questions import _question, d
    assert d("28/08/2018") == "2018-08-28" and d("2023-02-14") == "2023-02-14" and d(None) is None
    q = _question({"uid": "QANR5L15QE12345", "identifiant": {"legislature": "15"},
                   "textesQuestion": {"texteQuestion": {"infoJO": {"dateJO": "28/08/2018"}, "texte": "x"}},
                   "textesReponse": {"texteReponse": {"infoJO": {"dateJO": "22/01/2019"}, "texte": "y"}},
                   "renouvellements": {"renouvellement": [{"infoJO": {"dateJO": "04/12/2018"}}]},
                   "cloture": {"dateCloture": "22/01/2019"}})
    assert (q["date_question"], q["date_reponse"], q["dates_renouvellement"], q["date_cloture"]) == (
        "2018-08-28", "2019-01-22", ["2018-12-04"], "2019-01-22")
