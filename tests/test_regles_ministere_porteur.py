"""R-DEPOT-GOUVERNEMENT version 2 : le ministère porteur d'un projet de loi (issue #79).

Sur de petites tables écrites ici, à la forme exacte des faits lus (`an_acteurs`, `an_dossiers`).
Les cas reprennent ce que montrent les faits réels (g25, 25/11/2026) : le Premier ministre est
l'auteur du texte de dépôt, les ministres qui le présentent en sont les cosignataires ; un
ministre délégué est rattaché à sa tutelle (R-COMPOSITION)."""
import os

import pyarrow as pa
import pyarrow.parquet as pq

from empreinte_src.lecteurs import an_acteurs, an_dossiers
from empreinte_src.liaison import Contexte, ordonner, relier
from empreinte_src.regles import r_composition, r_depot_gouvernement, r_gouvernements, r_legislatures

_PROV = [("prov_point", pa.string()), ("prov_uid", pa.string()), ("prov_version", pa.int32()),
         ("prov_etat", pa.string()), ("prov_url", pa.string())]
G = "PO1"
DEPOT = "2024-11-15"


def _ecrire(dossier, lecteur, table, lignes):
    schema = pa.schema(list(lecteur.TABLES[table]) + [pa.field(n, t) for n, t in _PROV])
    listes = {f.name for f in schema if pa.types.is_list(f.type)}
    rows = []
    for r in lignes:
        x = {f.name: None for f in schema}
        x.update({n: [] for n in listes})
        x.update({"prov_point": "essai", "prov_uid": r.get("uid", r.get("document", "x")),
                  "prov_version": 1, "prov_etat": "present"})
        x.update(r)
        rows.append({k: v for k, v in x.items() if k in schema.names})
    os.makedirs(dossier, exist_ok=True)
    pq.write_table(pa.Table.from_pylist(rows, schema=schema),
                   os.path.join(dossier, f"{lecteur.NOM}__{table}.parquet"))


def _min(uid, libelle):
    return {"uid": uid, "type_organe": "MINISTERE", "organe_parent": G, "libelle": libelle}


def _mm(uid, acteur, organe, qualite, debut="2024-09-21", fin="2024-12-13"):
    return {"uid": uid, "acteur": acteur, "type_organe": "MINISTERE", "organe": organe,
            "qualite_code": qualite, "qualite": qualite, "date_debut": debut, "date_fin": fin}


ORGANES = [
    {"uid": G, "type_organe": "GOUVERNEMENT", "libelle_abrege": "BARNIER",
     "date_debut": "2024-09-06", "date_fin": "2024-12-13"},
    _min("PO10", "Premier ministre"),
    _min("PO11", "Ministère de l’Europe et des affaires étrangères"),
    _min("PO12", "Ministère de l’économie et des finances"),
    _min("PO13", "Ministère de la justice"),
    _min("PO20", "Ministère délégué auprès du ministre de l’économie et des finances, chargé de l’industrie"),
    _min("PO23", "Ministère chargé du budget"),            # pas de « auprès » : tutelle non établie
]
MANDATS = [
    _mm("PM10", "PA1", "PO10", "Premier ministre", "2024-09-06"),
    _mm("PM11", "PA2", "PO11", "Ministre"),
    _mm("PM12", "PA3", "PO12", "Ministre"),
    _mm("PM13", "PA6", "PO13", "Ministre", fin="2024-10-31"),     # part avant le dépôt
    _mm("PM14", "PA7", "PO13", "Ministre", debut="2024-11-01"),   # lui succède
    _mm("PM20", "PA4", "PO20", "Ministre délégué"),
    _mm("PM23", "PA5", "PO23", "Ministre délégué"),
]
MANDATS += [{**m, "uid": "PM15" + m["uid"][2:], "type_organe": "GOUVERNEMENT", "organe": G,
             "qualite_code": "membre", "qualite": "membre"} for m in list(MANDATS)]


def _projet(dossier, auteurs=(), cosignataires=(), date=DEPOT, organes=()):
    """Un dossier, son acte de premier dépôt et son texte PRJL ; `cosignataires` : (acteur, rang)
    ou (acteur, rang, date de retrait)."""
    doc = f"PRJLANR5L17B{dossier[1:].zfill(4)}"
    d = {"uid": dossier, "legislature": "17", "procedure_code": "1", "titre": f"Projet {dossier}"}
    a = {"dossier": dossier, "uid": f"L17-{dossier}-DI", "type_acte": "DepotInitiative_Type",
         "code": "AN1-DEPOT", "date": date and f"{date}T00:00:00.000+01:00", "texte_associe": doc}
    t = {"uid": doc, "dossier": dossier, "profondeur": 0, "date_depot": date,
         "auteurs_acteurs": list(auteurs), "auteurs_qualites": ["auteur"] * len(auteurs),
         "auteurs_organes": list(organes)}
    c = [{"document": doc, "acteur": x[0], "rang": x[1], "date_cosignature": date,
          "date_retrait": x[2] if len(x) > 2 else None, "edite": "true"} for x in cosignataires]
    return d, a, t, c


PROJETS = {
    "D1": _projet("D1", ["PA1"], [("PA2", 0)]),                         # un ministre
    "D2": _projet("D2", ["PA1"], [("PA4", 0)]),                         # ministre délégué -> tutelle
    "D3": _projet("D3", ["PA1"], [("PA3", 0), ("PA4", 1), ("PA2", 2)]), # économie (x2), Europe
    "D4": _projet("D4", ["PA1"]),                                       # le Premier ministre seul
    "D5": _projet("D5", ["PA1"], [("PA6", 0)]),                         # ministre parti avant le dépôt
    "D6": _projet("D6", ["PA2"]),                                       # ministre auteur (Sénat)
    "D7": _projet("D7", ["PA1"], [("PA5", 0)]),                         # tutelle non établie
    "D8": _projet("D8", organes=["PO78718"]),                           # aucun membre cité
    "D9": _projet("D9", ["PA1"], [("PA2", 0)], date=None),              # pas de date de dépôt
    "D10": _projet("D10", ["PA1"], [("PA2", 0), ("PA2", 1), ("PA3", 2, "2024-11-20")]),
    "D11": _projet("D11", ["PA99"], [("PA1", 0), ("PA7", 1)]),          # Président auteur ; PM présente
}


def _z2(dossier):
    _ecrire(dossier, an_acteurs, "organe", ORGANES)
    _ecrire(dossier, an_acteurs, "mandat", MANDATS)
    _ecrire(dossier, an_dossiers, "dossier", [p[0] for p in PROJETS.values()])
    _ecrire(dossier, an_dossiers, "acte", [p[1] for p in PROJETS.values()])
    _ecrire(dossier, an_dossiers, "document", [p[2] for p in PROJETS.values()])
    _ecrire(dossier, an_dossiers, "cosignature", [c for p in PROJETS.values() for c in p[3]])
    return dossier


def _relier(tmp_path, regles):
    ctx = Contexte(str(_z2(tmp_path / "z2")), str(tmp_path / "z3"), date_reference="2026-11-25")
    bilan = {b["regle"].split("@")[0]: b for b in relier(ctx, ordonner(regles))}
    r = ctx.con.execute("SELECT * FROM projet_gouvernement")
    cols = [d[0] for d in r.description]
    return {x["dossier"]: x for x in (dict(zip(cols, v)) for v in r.fetchall())}, bilan


def test_ministere_porteur(tmp_path):
    p, bilan = _relier(tmp_path, [r_legislatures, r_gouvernements, r_composition, r_depot_gouvernement])

    def porteur(d):
        x = p[d]
        return (x["ministere_porteur_statut"], x["ministere_porteur"], x["ministeres_porteurs"],
                x["raison_ministere_porteur"])

    # le cosignataire présente le projet ; le Premier ministre, auteur, ne compte pas
    assert porteur("D1") == ("etabli", "PO11", ["PO11"], None)
    assert p["D1"]["ministere_porteur_libelle"] == "Ministère de l’Europe et des affaires étrangères"
    assert p["D1"]["presentateurs"] == ["PA2"]
    # un ministre délégué : le ministère de tutelle, le portefeuille est gardé à part
    assert porteur("D2") == ("etabli", "PO12", ["PO12"], None)
    assert p["D2"]["portefeuilles_presentateurs"] == ["PO20"]
    assert p["D2"]["portefeuilles_presentateurs_libelles"] == [
        "Ministère délégué auprès du ministre de l’économie et des finances, chargé de l’industrie"]
    # plusieurs ministères : tous, sans doublon, dans l'ordre publié ; aucun n'est choisi
    assert porteur("D3") == ("plusieurs_ministeres", None, ["PO12", "PO11"], None)
    assert p["D3"]["ministeres_porteurs_libelles"] == [
        "Ministère de l’économie et des finances", "Ministère de l’Europe et des affaires étrangères"]
    assert p["D3"]["portefeuilles_presentateurs"] == ["PO12", "PO20", "PO11"]
    # jamais de devinette
    assert porteur("D4") == ("non_etabli", None, None, "seul_le_premier_ministre_cite")
    assert porteur("D5") == ("non_etabli", None, None, "presentateur_hors_gouvernement_a_la_date")
    assert porteur("D7") == ("non_etabli", None, None, "rattachement_non_etabli")
    assert porteur("D8") == ("non_etabli", None, None, "aucun_membre_du_gouvernement_cite")
    assert porteur("D9") == ("non_etabli", None, None, "gouvernement_non_etabli")
    # un ministre auteur (projets déposés au Sénat) présente le projet
    assert porteur("D6") == ("etabli", "PO11", ["PO11"], None)
    # cosignataire répété : une fois ; cosignature retirée : ignorée
    assert porteur("D10") == ("etabli", "PO11", ["PO11"], None) and p["D10"]["presentateurs"] == ["PA2"]
    # le Président de la République, auteur, n'est pas membre du gouvernement : il ne compte pas ;
    # le Premier ministre cosignataire présente lui-même le projet
    assert porteur("D11") == ("plusieurs_ministeres", None, ["PO10", "PO13"], None)
    assert p["D11"]["presentateurs"] == ["PA1", "PA7"]
    # le gouvernement du dépôt ne change pas
    assert {x["gouvernement"] for d, x in p.items() if d != "D9"} == {G}
    c = bilan["R-DEPOT-GOUVERNEMENT"]["couverture"]
    assert c == {"gouvernement_etabli": [10, 11], "ministere_porteur_etabli": [6, 11],
                 "ministere_porteur_unique": [4, 11]}


def test_sans_composition_le_ministere_porteur_n_est_pas_etabli(tmp_path):
    p, _ = _relier(tmp_path, [r_legislatures, r_gouvernements, r_depot_gouvernement])
    assert {x["ministere_porteur_statut"] for x in p.values()} == {"non_etabli"}
    assert p["D1"]["raison_ministere_porteur"] == "composition_non_calculee"
    assert p["D9"]["raison_ministere_porteur"] == "gouvernement_non_etabli"
    assert p["D1"]["gouvernement"] == G


def test_vocabulaires_du_schema_servi():
    import yaml
    with open(os.path.join(os.path.dirname(__file__), "..", "config", "schema_fichiers.yaml")) as f:
        voc = yaml.safe_load(f)["vocabulaires"]
    assert tuple(voc["ministere_porteur_statut"]) == r_depot_gouvernement.STATUTS
    assert tuple(voc["raison_ministere_porteur"]) == r_depot_gouvernement.RAISONS
