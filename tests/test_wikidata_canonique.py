"""Réponse de Wikidata gardée sous sa forme canonique (réglage `canonique: json` ; décision Q40
du 14/11/2026, exception à P2).

Mesuré le 14/11/2026 sur les versions 1 à 10 du point `wd-identifiants-parlementaires` : la
réponse ne différait, 2 nuits sur 9, que par l'ordre des clés de chaque ligne (« article » puis
« an », ou « article » puis « naissance »), et chaque réponse portait 144 lignes en double. Les
tests partent de l'extrait réel `tests/extraits/wd_identifiants_extrait.json`."""
import hashlib
import json
import os

from empreinte_src.collecte import relever_archive
from empreinte_src.depaquetage import _membre, canoniser_json
from empreinte_src.entrepot import Entrepot
from empreinte_src.lecteurs import wd_identifiants
from empreinte_src.lecture import Lecture
from empreinte_src.transport import Reponse
from tests.test_regles_e1 import EX

PA = {"id": "wd-identifiants-parlementaires", "source": "wikidata", "type": "identifiants_wikidata",
      "url": "https://query.wikidata.org/sparql?format=json&query=x", "format": "api_json",
      "uid": "identifiants-parlementaires", "canonique": "json", "licence": "cc0-1.0"}


def _reel():
    with open(os.path.join(EX, "wd_identifiants_extrait.json"), "rb") as f:
        return f.read()


def _cles_inversees(octets, doublon=True):
    """La même réponse, clés de chaque ligne dans l'ordre inverse, première ligne répétée :
    ce que Wikidata envoie une autre nuit, sans changement réel."""
    d = json.loads(octets)
    lignes = [dict(reversed(list(x.items()))) for x in d["results"]["bindings"]]
    if doublon:
        lignes.append(lignes[0])
    d["results"]["bindings"] = lignes
    return json.dumps(d, indent=2).encode()


class Faux:
    def __init__(self, octets, dossier):
        self.octets, self.dossier = octets, dossier

    def telecharger(self, url, etag=None, last_modified=None):
        c = os.path.join(self.dossier, "recu.json")
        with open(c, "wb") as f:
            f.write(self.octets)
        return Reponse(url=url, issue="nouveau", statut_http=200, chemin=c, taille=len(self.octets),
                       empreinte=hashlib.sha256(self.octets).hexdigest())


def _relever(dossier, octets, pa=PA):
    e = Entrepot(str(dossier / "e"))
    r = relever_archive(e, Faux(octets, str(dossier)), pa, {})
    e.clore("test")
    return r


def test_forme_canonique_sans_perte():
    brut = _reel()
    m = canoniser_json(_membre("u", "c.json", brut))
    a, b = json.loads(brut), json.loads(m.octets)
    sans_doublon = []
    for x in a["results"]["bindings"]:
        if x not in sans_doublon:
            sans_doublon.append(x)
    # Mêmes lignes, dans le même ordre ; seules les lignes répétées sont retirées.
    assert a["head"] == b["head"] and b["results"]["bindings"] == sans_doublon
    assert len(sans_doublon) < len(a["results"]["bindings"])        # l'extrait réel en a
    # Même contenu, autre présentation, une ligne répétée : même forme canonique.
    m2 = canoniser_json(_membre("u", "c.json", _cles_inversees(brut)))
    assert m2.octets == m.octets and m2.empreinte == m.empreinte
    assert m.octets != brut


def test_une_nuit_sans_vrai_changement_ne_fait_pas_de_version(tmp_path):
    brut = _reel()
    r1 = _relever(tmp_path, brut)
    assert (r1["issue"], r1["nb_nouvelles_versions"]) == ("nouveau", 1)
    r2 = _relever(tmp_path, _cles_inversees(brut))
    assert (r2["nb_nouvelles_versions"], r2["nb_inchanges"]) == (0, 1)
    # Le relevé garde l'empreinte des octets reçus, qui diffère d'une nuit à l'autre.
    assert r2["empreinte"] == hashlib.sha256(_cles_inversees(brut)).hexdigest() != r1["empreinte"]
    # Un vrai changement (un article retiré, comme les suppressions mesurées) fait une version.
    d = json.loads(brut)
    d["results"]["bindings"][0].pop("article")
    r3 = _relever(tmp_path, json.dumps(d).encode())
    assert r3["nb_nouvelles_versions"] == 1


def test_sans_le_reglage_l_ordre_des_cles_fait_une_version(tmp_path):
    pa = {k: v for k, v in PA.items() if k != "canonique"}
    _relever(tmp_path, _reel(), pa)
    r = _relever(tmp_path, _cles_inversees(_reel()), pa)
    assert r["nb_nouvelles_versions"] == 1


def test_le_lecteur_lit_la_forme_canonique_comme_la_brute(tmp_path):
    lus = {}
    for nom, pa in (("canonique", PA), ("brut", {k: v for k, v in PA.items() if k != "canonique"})):
        d = tmp_path / nom
        d.mkdir()
        _relever(d, _reel(), pa)
        lect = Lecture(Entrepot(str(d / "e")), str(d / "z2"), {"points_acces": [pa]})
        assert lect.executer(wd_identifiants)["illisibles"] == 0
        import pyarrow.parquet as pq
        t = pq.read_table(d / "z2" / "wd_identifiants__identifiant_externe.parquet").to_pylist()
        lus[nom] = sorted(json.dumps({k: v for k, v in r.items() if not k.startswith("prov_")},
                                     sort_keys=True, default=str) for r in t)
    assert lus["canonique"] == lus["brut"] and lus["brut"]
