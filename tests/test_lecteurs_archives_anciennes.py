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
