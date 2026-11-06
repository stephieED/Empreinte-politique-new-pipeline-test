"""Lecteur `an_acteurs` (AMO30) : extraits réels des archives XVIIe et XVe (fiche
`tests/extraits/an_acteurs.md`)."""
import os
import zipfile

import orjson
import pyarrow.parquet as pq
import pytest

from empreinte.depaquetage import depaqueter
from empreinte.entrepot import Entrepot
from empreinte.export import exporter
from empreinte.lecture import Lecture, MembreLu
from empreinte.lecteurs import an_acteurs

EXTRAITS = os.path.join(os.path.dirname(__file__), "extraits")
L17 = os.path.join(EXTRAITS, "amo30_l17_extrait.zip")
L15 = os.path.join(EXTRAITS, "amo30_l15_extrait.zip")
PA17 = {"id": "an-amo30-l17", "source": "an", "type": "acteurs_organes", "format": "zip",
        "url": "http://exemple.invalid/AMO30.json.zip"}
PA15 = {**PA17, "id": "an-amo30-l15"}
CFG = {"points_acces": [{"id": "an-amo30-l17", "licence": "etalab-2.0"},
                        {"id": "an-amo30-l15", "licence": "etalab-2.0"}]}


def _lire(zip_, nom):
    with zipfile.ZipFile(zip_) as z:
        octets = z.read(nom)
    return an_acteurs.lire(MembreLu("p", "an", "acteurs_organes", nom.split("/")[-1][:-5], nom,
                                    1, "e", octets, "etalab-2.0"))


def _mandats(zip_, nom):
    return {m["uid"]: m for m in _lire(zip_, nom)["mandat"]}


def test_identite_et_vides_xsi_nil():
    r = _lire(L17, "json/acteur/PA721872.json")
    (i,) = r["identite_source"]
    assert i["uid"] == "PA721872"                       # uid objet (#text)
    assert (i["prenom"], i["nom"], i["civilite"]) == ("Brune", "Poirson", "Mme")
    assert i["date_naissance"] == "1982-09-01"
    assert i["date_deces"] is None and i["trigramme"] is None  # {"@xsi:nil": "true"}
    assert i["departement_naissance"] is None and i["uri_hatvp"] is None
    # Tout est nil : naissance, profession.
    (j,) = _lire(L17, "json/acteur/PA873626.json")["identite_source"]
    assert j["date_naissance"] is None and j["profession"] is None
    assert j["categorie_socio_pro"] is None and j["famille_socio_pro"] is None


def test_mandat_seul_en_dictionnaire_et_deces():
    r = _lire(L17, "json/acteur/PA497.json")
    assert [m["uid"] for m in r["mandat"]] == ["PM287498"]   # `mandats.mandat` est un objet
    assert r["identite_source"][0]["date_deces"] == "2017-09-15"


def test_mandat_suspendu_puis_repris_tel_quel():
    m = _mandats(L17, "json/acteur/PA721872.json")
    origine, reprise = m["PM723408"], m["PM774343"]
    assert origine["cause_fin"] == "Nomination comme membre du Gouvernement"
    assert origine["date_fin"] == "2017-07-21"
    # La source recopie la date de début du mandat d'origine ; la reprise est dans
    # datePriseFonction : le lecteur garde les deux, sans rien calculer.
    assert reprise["date_debut"] == "2017-06-18" and reprise["date_prise_fonction"] == "2020-08-04"
    assert reprise["mandat_remplace"] == "PM723408"
    assert reprise["cause_mandat"].startswith("reprise de l'exercice du mandat")
    assert reprise["circonscription"] == "PO718334"
    assert (reprise["departement"], reprise["num_circo"]) == ("Vaucluse", "3")
    assert reprise["suppleants"] == [{"suppleant": "PA721876", "date_debut": "2017-06-18",
                                      "date_fin": "2021-04-05"}]
    assert reprise["type_mandat"] == "MandatParlementaire_type"


def test_mission_aupres_de_deux_ministeres():
    m = _mandats(L17, "json/acteur/PA721872.json")["PM775823"]
    assert m["type_organe"] == "MINISTERE" and m["qualite_code"] == "en mission"
    assert m["organes"] == ["PO773376", "PO773378"]      # `organeRef` en liste
    assert m["organe"] == "PO773376"
    assert m["legislature"] == "15" and m["libelle"] == "L'éducation au développement durable"
    # Les mandats GOUVERNEMENT n'ont pas de législature : None, jamais 0.
    assert _mandats(L17, "json/acteur/PA721872.json")["PM15730082"]["legislature"] is None


def test_siege_et_collaborateurs_jamais_lus():
    nom = "json/acteur/PA840849.json"
    m = _mandats(L17, nom)["PM886221"]
    assert m["place_hemicycle"] == "227"                  # zéros et chaînes gardés tels quels
    # Les collaborateurs figurent dans l'extrait mais ne deviennent jamais des faits.
    with zipfile.ZipFile(L17) as z:
        src = orjson.loads(z.read(nom))["acteur"]
    noms = {c["nom"] for x in src["mandats"]["mandat"] if x.get("collaborateurs")
            for c in x["collaborateurs"]["collaborateur"]}
    assert noms
    tout = orjson.dumps(_lire(L17, nom)).decode()
    assert not any(n in tout for n in noms)
    for schema in an_acteurs.TABLES.values():
        assert not any("collaborateur" in c or "adresse" in c or "secretai" in c
                       for c in schema.names)


def test_organes():
    o = {n: _lire(L17, f"json/organe/{n}.json")["organe"][0]
         for n in ("PO800538", "PO845407", "PO834722", "PO851643", "PO53285", "PO762272")}
    assert o["PO800538"]["position_politique"] == "Majoritaire"
    assert o["PO800538"]["sigle"] == "RE" and o["PO800538"]["legislature"] == "16"
    assert o["PO845407"]["position_politique"] is None   # aucun groupe XVIIe ne déclare
    assert o["PO845407"]["date_fin"] is None
    assert o["PO834722"]["organe_precedent"] == "PO791615"
    assert o["PO834722"]["organe_parent"] == "PO833673"
    assert o["PO834722"]["legislature"] is None
    assert o["PO851643"]["pays"] == ["GOP756511", "GOP756529"]   # `paysRef` en liste
    assert (o["PO53285"]["type_organe"], o["PO53285"]["departement_code"]) == ("CIRCONSCRIPTION", "973")
    assert o["PO762272"]["organe_parent"] == "PO419610"


def test_deport():
    (d,) = _lire(L17, "json/deport/DPTR5L16PA719472D0001.json")["deport"]
    assert d["acteur"] == "PA719472" and d["portee_code"] == "DELIB"
    assert d["cible_reference_textuelle"] == "Amendement #966 après article 1er / PLFR 2022"
    assert d["explication"] is None and d["cible_references"] is None


def test_archive_figee_xve_meme_lecture():
    r = _lire(L15, "json/acteur/PA721872.json")
    assert r["identite_source"][0]["uid"] == "PA721872"
    assert _lire(L15, "json/organe/PO732421.json")["organe"][0]["libelle"] == \
        "Groupe La République En Marche"                 # libellé d'époque (réécrit depuis)
    assert _lire(L15, "json/organe/PO730946.json")["organe"][0]["position_politique"] == "Opposition"


def test_objet_inconnu_illisible():
    with pytest.raises(ValueError):
        an_acteurs.lire(MembreLu("p", "an", "acteurs_organes", "X", "x.json", 1, "e",
                                 b'{"autre": {}}', None))


def test_cadre_complet_et_export_sans_doublon(tmp_path):
    e = Entrepot(str(tmp_path / "e"))
    e.versionner(PA17, f"R{e.generation}", depaqueter(L17, "zip"), complet=True)
    e.versionner(PA15, f"R{e.generation}b", depaqueter(L15, "zip"), complet=True)
    e.clore("test")
    e = Entrepot(str(tmp_path / "e"))
    b = Lecture(e, str(tmp_path / "z2"), CFG).executer(an_acteurs)
    assert b["illisibles"] == 0 and b["lues"] == 14
    assert b["lignes"]["identite_source"] == 5 and b["lignes"]["deport"] == 1
    assert b["lignes"]["organe"] == 8
    t = pq.read_table(tmp_path / "z2" / "an_acteurs__mandat.parquet").to_pylist()
    assert all(r["licence"] == "etalab-2.0" and r["prov_etat"] == "present" for r in t)
    assert {r["prov_uid"] for r in t if r["uid"] == "PM775823"} == {"PA721872"}
    # Export de l'état courant d'un seul point d'accès (la XVIIe) : zéro clé en double.
    # (Deux archives d'un même lecteur donneraient deux faits `mandat|PM…` : voir la fiche.)
    seul17 = tmp_path / "z2b"
    Lecture(Entrepot(str(tmp_path / "e")), str(seul17), CFG).executer(an_acteurs,
                                                                      points=["an-amo30-l17"])
    res = exporter(str(seul17), [an_acteurs], str(tmp_path / "x17"))
    assert res["cles_en_double"] == 0
    assert res["faits_par_type"] == {"deport": 1, "identite_source": 4, "mandat": 19, "organe": 6}
