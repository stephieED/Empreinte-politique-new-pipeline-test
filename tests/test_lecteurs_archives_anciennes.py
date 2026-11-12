"""Archives de la XIVe : réunions, acteurs et questions livrés dans un seul fichier, sous une
enveloppe (`reunions`, `export`, `questionsGvt`…). Les mêmes objets, lus seuls ou dans leur
enveloppe, donnent les mêmes faits (formats relevés le 07/11/2026)."""
import os
import zipfile

import orjson

from empreinte_src.depaquetage import Membre
from empreinte_src.lecteurs import an_acteurs, an_agenda, an_questions

EX = os.path.join(os.path.dirname(__file__), "extraits")


def _objets(nom_zip, cle):
    with zipfile.ZipFile(os.path.join(EX, nom_zip)) as z:
        docs = [orjson.loads(z.read(n)) for n in sorted(z.namelist()) if n.endswith(".json")]
    return [d[cle] for d in docs if cle in d]


def _m(doc):
    b = orjson.dumps(doc)
    return Membre(uid="x", chemin="x.json", octets=b, taille=len(b), crc32=0, empreinte="")


def _seuls(mod, cle, objets):
    out = {}
    for o in objets:
        for t, ls in mod.lire(_m({cle: o})).items():
            out.setdefault(t, []).extend(ls)
    return out


def test_agenda_en_un_fichier():
    r = _objets("agenda_l17_extrait.zip", "reunion")
    assert r
    assert an_agenda.lire(_m({"reunions": {"reunion": r}})) == _seuls(an_agenda, "reunion", r)


def test_acteurs_amo20_en_un_fichier():
    a = _objets("amo30_l17_extrait.zip", "acteur")
    o = _objets("amo30_l17_extrait.zip", "organe")
    assert a and o
    env = an_acteurs.lire(_m({"export": {"organes": {"organe": o}, "acteurs": {"acteur": a}}}))
    attendu = _seuls(an_acteurs, "acteur", a)
    attendu["organe"] = _seuls(an_acteurs, "organe", o)["organe"]
    for t in an_acteurs.TABLES:
        assert env[t] == attendu.get(t, []), t


def test_questions_en_un_fichier():
    q = []
    for n in sorted(os.listdir(EX)):
        if n.startswith("questions") and n.endswith(".zip"):
            q += _objets(n, "question")
    assert q
    assert an_questions.lire(_m({"questionsGvt": {"question": q}})) == an_questions.lire(_m({"question": q}))


def _lire_par_le_cadre(tmp_path, zip_, pa_cfg, mod):
    """Lecture complète par le cadre (E2 puis E3), comme une nuit."""
    from empreinte_src.depaquetage import depaqueter
    from empreinte_src.entrepot import Entrepot
    from empreinte_src.lecture import Lecture
    import pyarrow.parquet as pq
    e = Entrepot(str(tmp_path / "e"))
    e.versionner(pa_cfg, f"R{e.generation}", depaqueter(zip_, "zip"), complet=True)
    e.clore("test")
    b = Lecture(Entrepot(str(tmp_path / "e")), str(tmp_path / "z2"),
                {"points_acces": [{"id": pa_cfg["id"], "licence": "etalab-2.0"}]}).executer(mod)
    return b, {t: pq.read_table(tmp_path / "z2" / f"{mod.NOM}__{t}.parquet").to_pylist() for t in mod.TABLES}


def test_amendements_xive_schema_ancien_lus_par_lots(tmp_path):
    """XIVe : un seul fichier, schéma ancien, ramené au schéma courant (07/11/2026)."""
    from empreinte_src.lecteurs import an_amendements
    pa_cfg = {"id": "an-amendements-l14", "source": "an", "type": "amendements", "format": "zip",
              "url": "http://exemple.invalid/Amendements_XIV.json.zip"}
    b, t = _lire_par_le_cadre(tmp_path, os.path.join(EX, "amendements_l14_extrait.zip"), pa_cfg, an_amendements)
    assert b["illisibles"] == 0 and b["lues"] == 1 and len(t["amendement"]) == 9
    a = {x["uid"]: x for x in t["amendement"]}
    couples = {(x["etat_code"], x["sous_etat"]) for x in a.values()}
    assert {("DI", "Adopté"), ("DI", "Rejeté"), ("DI", "Non soutenu"), ("DI", "Retiré"), ("DI", "Tombé"),
            ("IRRXIV", None), ("RT", None)} <= couples
    x = a["AMANR5L14SEA644420B0013P0D1N7"]
    assert (x["legislature"], x["numero_long"], x["document"], x["organe_examen"]) == (
        "14", "7 (Rect)", "PIONANR5L14B0013", "PO644420")
    assert x["date_depot"] == "2014-02-14" and x["auteur"] and x["expose_sommaire"]
    assert all(s["amendement"] in a for s in t["signature"])


def test_irrecevable_xive_sans_article_n_est_pas_devine():
    from empreinte_src.regles.r_amendement import SORTS
    assert ("IRRXIV", "*", "irrecevable", "irrecevable_article_non_precise") in SORTS
    rang = {e: k for k, (e, *_r) in enumerate(SORTS)}
    assert rang["IRRXIV"] < rang["IRR%"]         # jamais confondu avec « irrecevable, autre motif »


def test_questions_xive_lues_en_flux(tmp_path, monkeypatch):
    from empreinte_src.lecteurs import an_questions
    monkeypatch.setattr(an_questions, "SEUIL_FLUX", 0)       # l'extrait est petit : flux forcé
    pa_cfg = {"id": "an-questions-ecrites-l14", "source": "an", "type": "questions_ecrites", "format": "zip",
              "url": "http://exemple.invalid/Questions_ecrites_XIV.json.zip"}
    b, t = _lire_par_le_cadre(tmp_path, os.path.join(EX, "questions_ecrites_l14_extrait.zip"), pa_cfg, an_questions)
    assert b["illisibles"] == 0 and len(t["question"]) == 3
    assert t["question"][0]["uid"].startswith("QANR5L14QE")
