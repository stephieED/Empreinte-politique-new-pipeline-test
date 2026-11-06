"""Lecteur des scrutins de l'Assemblée : les trois schémas de clés, les dissidents seuls de la
XIVe, le groupe PO0, les mises au point `[null, null]`, et le passage par le cadre (Z2 et
export sans clé en double). Extraits décrits dans `tests/extraits/an_scrutins.md`."""
import collections
import json
import os
import zipfile

import pyarrow.parquet as pq
import pytest

from empreinte_src.depaquetage import depaqueter
from empreinte_src.entrepot import Entrepot
from empreinte_src.export import exporter
from empreinte_src.lecture import Lecture, MembreLu
from empreinte_src.lecteurs import an_scrutins

EXTRAITS = os.path.join(os.path.dirname(__file__), "extraits")
ZIPS = {14: "an_scrutins_l14_fragment.zip", 15: "an_scrutins_l15_extrait.zip",
        16: "an_scrutins_l16_congres_extrait.zip", 17: "an_scrutins_l17_extrait.zip"}


def lire_zip(nom) -> dict:
    out = collections.defaultdict(list)
    with zipfile.ZipFile(os.path.join(EXTRAITS, nom)) as z:
        for n in z.namelist():
            m = MembreLu("an-scrutins", "an", "scrutins", n, n, 1, "e", z.read(n), "etalab-2.0")
            for t, rows in an_scrutins.lire(m).items():
                out[t].extend(rows)
    return out


@pytest.fixture(scope="module")
def lu():
    return {leg: lire_zip(nom) for leg, nom in ZIPS.items()}


def du(rows, scrutin):
    return [r for r in rows if r["scrutin"] == scrutin]


def test_schema_xvii_pours_contres(lu):
    r = lu[17]
    s = {x["uid"]: x for x in r["scrutin"]}["VTANR5L17V4569"]
    assert s["code_type"] == "SPO" and s["mode_publication"] == "DecompteNominatif"
    assert (s["pour"], s["contre"], s["abstentions"], s["non_votants"]) == (114, 146, 4, 1)
    assert s["prov_url"] == "https://www.assemblee-nationale.fr/dyn/17/scrutins/4569"
    pv = du(r["position_vote"], "VTANR5L17V4569")
    assert {x["cle_source"] for x in pv} == {"pours", "contres", "abstentions", "nonVotants"}
    assert collections.Counter(x["position"] for x in pv) == {"contre": 146, "pour": 114,
                                                               "abstention": 4, "non_votant": 1}
    assert all(x["acteur"].startswith("PA") and x["prov_url"] == s["prov_url"] for x in pv)
    assert [x["cause"] for x in pv if x["position"] == "non_votant"] == ["PSE"]
    assert sum(x["par_delegation"] for x in pv) == 54          # chaîne "true" lue en booléen


def test_reference_de_dossier_xvii(lu):
    s = {x["uid"]: x for x in lu[17]["scrutin"]}
    assert s["VTANR5L17V6722"]["dossier_ref"] == "DLR5L17N54083"
    assert s["VTANR5L17V4569"]["dossier_ref"] is None          # absente : None, rien de deviné


def test_siege_absent(lu):
    pv = du(lu[17]["position_vote"], "VTANR5L17V124")
    assert sum(x["num_place"] is None for x in pv) == 2


def test_groupe_po0_garde_tel_quel(lu):
    dg = du(lu[17]["decompte_groupe"], "VTANR5L17V493")
    assert [x["organe"] for x in dg] == ["PO0"] * 12
    assert [x["occurrence"] for x in dg] == list(range(12))    # clé (scrutin, organe, occurrence)
    assert dg[0]["nombre_membres"] == 124 and dg[0]["position_majoritaire"] is not None
    assert {x["groupe"] for x in du(lu[17]["position_vote"], "VTANR5L17V493")} == {"PO0"}


def test_mises_au_point(lu):
    mp = lu[17]["mise_au_point"]
    # [null, null] : aucun votant ; un votant au 2e élément est gardé avec son rang
    v124 = du(mp, "VTANR5L17V124")
    assert ("PA793322", "non_votant", 1) in [(x["acteur"], x["position"], x["element"]) for x in v124]
    v8611 = du(mp, "VTANR5L17V8611")
    assert {(x["acteur"], x["position"], x["element"]) for x in v8611} == {
        ("PA721410", "non_votant_volontaire", 1), ("PA793342", "non_votant_volontaire", 1)}
    # sous-bloc dysfonctionnement (clés au singulier), à part
    v4569 = du(mp, "VTANR5L17V4569")
    assert [(x["acteur"], x["cle_source"]) for x in v4569 if x["dysfonctionnement"]] == [("PA2960", "contre")]
    assert len([x for x in v4569 if not x["dysfonctionnement"]]) == 3
    # aucune mise au point pour les scrutins dont tous les blocs sont vides
    assert du(mp, "VTANR5L17V6722") == [] and du(mp, "VTANR5L17V493") == []


def test_schema_xv_et_delegation(lu):
    pv = lu[15]["position_vote"]
    assert {x["cle_source"] for x in pv} == {"pours", "nonVotants"}
    assert sum(1 for x in pv if x["par_delegation"]) == 3
    assert {x["cause"] for x in pv if x["position"] == "non_votant"} == {"PAN", "PSE"}


def test_schema_congres_xvi(lu):
    r = lu[16]
    s = r["scrutin"][0]
    assert s["uid"] == "VTCGR5L16V1" and s["code_type"] == "SSG"
    assert s["prov_url"] is None                               # pas de page /dyn/16/scrutins/1 pour le Congrès
    assert {x["cle_source"] for x in r["position_vote"]} == {"pour", "contre", "abstention"}
    assert collections.Counter(x["position"] for x in r["position_vote"]) == {
        "pour": 780, "contre": 72, "abstention": 50}
    assert all(x["num_place"] is None for x in r["position_vote"])


def test_schema_xiv_et_dissidents_seuls(lu):
    r = lu[14]
    s = {x["uid"]: x for x in r["scrutin"]}
    assert set(s) == {"VTANR5L14V1", "VTANR5L14V2"}           # un membre, plusieurs scrutins
    assert s["VTANR5L14V1"]["code_type"] == "SAT"
    assert s["VTANR5L14V2"]["mode_publication"] == "DecompteDissidentsPositionGroupe"
    pv2 = du(r["position_vote"], "VTANR5L14V2")
    # 110 voix décomptées, seuls 2 dissidents nommés (et 27 non-votants nommés, avec leur cause) :
    # la position des autres membres n'est jamais déduite de celle du groupe
    assert sum((g["pour"] or 0) + (g["contre"] or 0) + (g["abstentions"] or 0)
               for g in du(r["decompte_groupe"], "VTANR5L14V2")) == 110
    assert collections.Counter(x["position"] for x in pv2) == {"non_votant": 27, "pour": 1, "abstention": 1}
    assert all(x["cause"] for x in pv2 if x["position"] == "non_votant")
    # XIVe : clés au singulier pour les décomptes (abstention, nonVotant), pas de délégation
    assert all(x["par_delegation"] is None for x in r["position_vote"])
    assert {x["cle_source"] for x in r["position_vote"]} == {"pour", "contre", "abstentions", "nonVotants"}
    # miseAuPoint : null pour V1, rempli pour V2
    assert du(r["mise_au_point"], "VTANR5L14V1") == []
    assert len(du(r["mise_au_point"], "VTANR5L14V2")) == 39
    assert s["VTANR5L14V2"]["prov_url"] == "https://www.assemblee-nationale.fr/dyn/14/scrutins/2"


def test_cle_inconnue_avec_votants_leve():
    with zipfile.ZipFile(os.path.join(EXTRAITS, ZIPS[15])) as z:
        d = json.loads(z.read(z.namelist()[0]))
    g = d["scrutin"]["ventilationVotes"]["organe"]["groupes"]["groupe"][0]["vote"]["decompteNominatif"]
    cle = next(k for k, v in g.items() if v)
    g["votesBizarres"] = g.pop(cle)
    m = MembreLu("p", "an", "scrutins", "u", "u", 1, "e", json.dumps(d).encode(), None)
    with pytest.raises(ValueError, match="inconnue"):
        an_scrutins.lire(m)


def test_par_le_cadre_et_export(tmp_path):
    pa_cfg = {"id": "an-scrutins-l17", "source": "an", "type": "scrutins", "format": "zip",
              "url": "http://exemple.invalid/Scrutins.json.zip"}
    e = Entrepot(str(tmp_path / "e"))
    e.versionner(pa_cfg, f"R{e.generation}", depaqueter(os.path.join(EXTRAITS, ZIPS[17]), "zip"),
                 complet=True)
    e.clore("test")
    e = Entrepot(str(tmp_path / "e"))
    b = Lecture(e, str(tmp_path / "z2"), {"points_acces": [{"id": "an-scrutins-l17",
                                                            "licence": "etalab-2.0"}]}).executer(an_scrutins)
    assert b["lues"] == 5 and b["illisibles"] == 0 and b["lignes"]["scrutin"] == 5
    t = pq.read_table(tmp_path / "z2" / "an_scrutins__position_vote.parquet").to_pylist()
    assert all(r["prov_url"] and r["licence"] == "etalab-2.0" and r["prov_etat"] == "present" for r in t)
    x = exporter(str(tmp_path / "z2"), [an_scrutins], str(tmp_path / "export"))
    assert x["cles_en_double"] == 0
    assert x["faits_par_type"]["scrutin"] == 5 and x["faits_par_type"]["decompte_groupe"] > 0
