"""Règles du groupe D (Journal officiel) : R-LOI-CITEE et R-RATTACHEMENT-ACTE.

D'abord sur les faits lus des extraits réels de quatre livraisons de la DILA (fiches
`tests/extraits/jo_actes.md`), puis sur de petites tables écrites ici pour les pièges que les
extraits ne couvrent pas (jour partagé par deux gouvernements, numéro du JO manquant…)."""
import os

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from empreinte_src.depaquetage import depaqueter
from empreinte_src.entrepot import Entrepot
from empreinte_src.lecture import Lecture
from empreinte_src.lecteurs import jo_actes
from empreinte_src.liaison import Contexte, relier
from empreinte_src.regles import r_loi_citee, r_rattachement_acte

EXTRAITS = os.path.join(os.path.dirname(__file__), "extraits")
TARS = [("20261102-213929", "jo_JORF_20261102-213929_extrait.tar.gz"),
        ("20261103-214151", "jo_JORF_20261103-214151_extrait.tar.gz"),
        ("20261104-004428", "jo_JORF_20261104-004428_extrait.tar.gz"),
        ("20261104-004428", "jo_JORF_20261104-004428_regles_extrait.tar.gz")]
PA_JO = {"id": "jo-livraisons", "source": "dila", "type": "jorf", "format": "liste_tar",
         "url": "http://exemple.invalid/JORF/",
         "qualifier_uid": r"^\d{8}-\d{6}/jorf/global/(?P<q>.+?)/JORF/"}
CFG = {"points_acces": [{"id": "jo-livraisons", "licence": "etalab-2.0"}]}

# Les gouvernements tels que l'organe GOUVERNEMENT de l'Assemblée les date (AMO, XVIIe,
# collecte du 06/11/2026) : sortie de R-GOUVERNEMENTS.
GOUVERNEMENTS = [
    ("PO382939", "2007-05-17", "2007-06-18"), ("PO384206", "2007-06-18", "2010-11-13"),
    ("PO425695", "2010-11-14", "2012-05-10"), ("PO590011", "2012-05-16", "2012-06-18"),
    ("PO653199", "2012-06-19", "2014-03-31"), ("PO700706", "2014-04-01", "2014-08-25"),
    ("PO702883", "2014-08-26", "2016-12-06"), ("PO715793", "2016-12-07", "2017-05-17"),
    ("PO717173", "2017-05-18", "2017-06-19"), ("PO725688", "2017-06-20", "2020-07-06"),
    ("PO773371", "2020-07-07", "2022-05-16"), ("PO791579", "2022-05-17", "2024-01-09"),
    ("PO833673", "2024-01-10", "2024-09-05"), ("PO847639", "2024-09-06", "2024-12-13"),
    ("PO855052", "2024-12-14", "2025-09-09"), ("PO873418", "2025-09-10", "2025-10-10"),
    ("PO873634", "2025-10-11", None)]
BAYROU, LECORNU, LECORNU_II = "PO855052", "PO873418", "PO873634"


def _gouvernements(ctx):
    valeurs = ", ".join(f"('{o}', '{d}', {repr(f) if f else 'NULL'})" for o, d, f in GOUVERNEMENTS)
    ctx.x(f"CREATE VIEW gouvernement AS SELECT * FROM (VALUES {valeurs}) g(organe, debut, fin)")


def _decisions(dossier, decisions):
    os.makedirs(dossier, exist_ok=True)
    for i, (libelle, normalise) in enumerate(decisions):
        with open(os.path.join(dossier, f"d{i}.yaml"), "w") as f:
            f.write(f'type: libelle_ministere\nlibelle: "{libelle}"\n'
                    f'ministere_normalise: "{normalise}"\nmotif: essai\n')
    return dossier


def _relier(z2, z3, decisions=None):
    ctx = Contexte(str(z2), str(z3), decisions)
    _gouvernements(ctx)
    bilan = relier(ctx, [r_loi_citee, r_rattachement_acte])
    return ctx, {b["regle"].split("@")[0]: b for b in bilan}


def _lignes(ctx, sql):
    rel = ctx.con.execute(sql)
    noms = [d[0] for d in rel.description]
    return [dict(zip(noms, r)) for r in rel.fetchall()]


# -- faits lus des extraits réels -----------------------------------------------------------

@pytest.fixture(scope="module")
def z2_extraits(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("jo")
    e = Entrepot(str(tmp / "e"))
    for k, (livraison, tar) in enumerate(TARS):
        e.versionner(PA_JO, f"R{k}-{livraison}", depaqueter(os.path.join(EXTRAITS, tar), "liste_tar"),
                     complet=True, delta=True)
    e.clore("test")
    Lecture(Entrepot(str(tmp / "e")), str(tmp / "z2"), CFG).executer(jo_actes)
    return tmp / "z2"


@pytest.fixture(scope="module")
def relie(z2_extraits, tmp_path_factory):
    tmp = tmp_path_factory.mktemp("z3")
    dec = _decisions(str(tmp / "decisions"), [("MINISTERE DE L'INTERIEUR", "Intérieur")])
    ctx, bilan = _relier(z2_extraits, tmp / "z3", dec)
    actes = {r["id_jorf"]: r for r in _lignes(ctx, "SELECT * FROM acte_rattache")}
    return ctx, bilan, actes


def test_gouvernement_par_date_de_publication_jamais_une_personne(relie):
    ctx, _, actes = relie
    d = actes["JORFTEXT000055037137"]        # décret 2026-1013, publié le 31/10/2026
    assert (d["date_publication"], d["gouvernement"], d["gouvernement_statut"]) == (
        "2026-10-31", LECORNU_II, "etabli")
    # Le bloc des signataires nomme Sébastien LECORNU et Laurent NUNEZ : aucune colonne ne
    # rattache l'acte à une personne, et aucun nom n'est repris.
    colonnes = [c[0] for c in ctx.x("SELECT column_name FROM (DESCRIBE acte_rattache)")]
    assert not [c for c in colonnes if any(m in c for m in ("signat", "acteur", "personne", "auteur"))]
    assert "LECORNU" not in " ".join(str(v) for v in d.values())
    # Avis dont la date de signature est la sentinelle 2999 : la date de publication suffit.
    assert actes["JORFTEXT000055053883"]["gouvernement"] == LECORNU_II
    # Loi 2025-391 publiée le 02/05/2025 : gouvernement Bayrou.
    assert actes["JORFTEXT000051538879"]["gouvernement"] == BAYROU


def test_texte_ancien_redelivre_date_de_publication_pas_de_livraison(relie):
    _, _, actes = relie
    a = actes["JORFTEXT000000721454"]        # loi de 1991, publiée en 1992, redélivrée le 02/11/2026
    assert a["date_publication"] < "2000" and a["livraison"] == "20261102-213929"
    assert a["gouvernement"] is None and a["gouvernement_statut"] == "non_etabli"
    assert a["gouvernement_raison"] == "publié avant le premier gouvernement suivi"
    assert a["dans_periode_couverte"] is False
    d = actes["JORFTEXT000033703701"]        # décret de 2016 redélivré : gouvernement Cazeneuve
    assert d["gouvernement"] == "PO715793"


def test_texte_redelivre_une_ligne_par_acte(relie):
    ctx, _, _ = relie
    # Loi 2025-391 livrée le 02/11 puis le 03/11 : une seule ligne ; huit actes en tout.
    assert ctx.un("SELECT count(*) FROM acte_rattache WHERE id_jorf = 'JORFTEXT000051538879'") == 1
    assert ctx.un("SELECT count(*) FROM acte_rattache") == ctx.un(
        "SELECT count(DISTINCT acte) FROM acte_rattache") == 11


def test_loi_en_double_original_et_rectificatif(relie):
    _, _, actes = relie
    o, r = actes["JORFTEXT000051538879"], actes["JORFTEXT000051575460"]
    assert (o["est_rectificatif"], o["rectificatif_de"]) == (False, None)
    assert (r["est_rectificatif"], r["rectificatif_de"]) == (True, "jorf:JORFTEXT000051538879")
    assert r["date_publication"] == "2025-05-10"     # garde sa propre date


def test_ministere_normalise_par_decision_sinon_non_etabli(relie):
    _, bilan, actes = relie
    d = actes["JORFTEXT000055037137"]
    # La décision porte le libellé en capitales sans accents : même clé.
    assert (d["ministere_libelle"], d["ministere_normalise"], d["ministere_statut"]) == (
        "Ministère de l'intérieur", "Intérieur", "etabli")
    assert d["ministere_decision"] == "d0.yaml"
    p = actes["JORFTEXT000055053645"]
    assert (p["ministere_libelle"], p["ministere_normalise"], p["ministere_statut"]) == (
        "Premier ministre", None, "non_etabli")
    assert p["ministere_raison"] == "libellé sans décision de correspondance"
    # Autorité indépendante et loi : pas de ministère à la source.
    for id_ in ("JORFTEXT000055053925", "JORFTEXT000055047268"):
        assert actes[id_]["ministere_libelle"] is None
        assert actes[id_]["ministere_statut"] == "non_precise"
        assert actes[id_]["ministere_normalise"] is None
    precise, total = bilan["R-RATTACHEMENT-ACTE"]["couverture"]["ministere_precise"]
    etabli, libelles = bilan["R-RATTACHEMENT-ACTE"]["couverture"]["ministere_etabli"]
    assert libelles == precise and etabli == sum(
        1 for a in actes.values() if a["ministere_libelle"] == "Ministère de l'intérieur")


def test_mesure_nominative_lue_dans_la_rubrique_du_sommaire(relie):
    _, _, actes = relie
    m = actes["JORFTEXT000055053645"]        # JO n° 258, « Mesures nominatives »
    assert m["mesure_nominative"] is True and m["sommaire_jo"] == "JORFCONT000055053315"
    assert "Mesures nominatives" in m["rubrique"] and m["num_jo"] == "0258"
    t = actes["JORFTEXT000055053477"]        # même numéro, « Textes généraux »
    assert t["mesure_nominative"] is False and t["mesure_nominative_raison"] is None
    # Le sommaire du JO du 31/10 n'est pas dans les extraits : non établi, jamais « faux ».
    d = actes["JORFTEXT000055037137"]
    assert d["mesure_nominative"] is None
    assert d["mesure_nominative_raison"] == "acte absent des sommaires du JO reçus"


def test_loi_citee_dans_le_titre(relie):
    ctx, bilan, actes = relie
    cit = _lignes(ctx, "SELECT * FROM acte_loi_citee ORDER BY acte, rang")
    assert [(c["acte"], c["numero_loi"]) for c in cit] == [
        ("jorf:JORFTEXT000055053573", "2021-1754")]
    c = cit[0]
    # Identifiée par le lien CITATION du JO ; la loi 2025-1403, citée dans les seuls liens,
    # n'est pas « citée dans le titre ».
    assert (c["loi_jorf"], c["loi_identifiee_par"], c["type_loi"]) == (
        "JORFTEXT000044553428", "lien_jo", "loi")
    assert c["loi_source_url"] == "https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000044553428"
    assert c["source_url"] == "https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000055053573"
    a = actes["JORFTEXT000055053573"]
    assert (a["cite_une_loi"], a["nb_lois_citees"]) == (True, 1)
    # « … de la loi de finances pour 2026 » : le titre ne donne pas de numéro. Les liens du JO
    # visent la loi 2026-103, mais le titre ne le dit pas : faux, et « faux » ne veut pas dire
    # « sans loi ».
    t = actes["JORFTEXT000055053477"]
    assert t["cite_une_loi"] is False and t["nb_lois_citees"] == 0
    assert ctx.un("SELECT count(*) FROM jo_actes__lien_acte_loi WHERE acte = 'jorf:JORFTEXT000055053477' "
                  "AND cible_numero = '2026-103'") == 2
    # Le titre d'une loi porte son propre numéro : pas une citation.
    for id_ in ("JORFTEXT000051538879", "JORFTEXT000051575460", "JORFTEXT000055047268"):
        assert actes[id_]["cite_une_loi"] is False
    assert bilan["R-LOI-CITEE"]["couverture"] == {"titre_lu": [11, 11], "loi_citee_identifiee": [1, 1]}


def test_aucun_numero_complet_pas_de_periode_couverte(relie):
    """Le sommaire du JO n° 258 liste 91 textes, dont 5 seulement sont dans les extraits : le
    numéro est incomplet, aucune période n'est déclarée couverte."""
    ctx, _, actes = relie
    (c,) = _lignes(ctx, "SELECT * FROM couverture_jo")
    assert c["premiere_publication"] is None and c["derniere_publication"] is None
    assert c["nb_numeros"] == 0 and c["nb_actes"] == 0
    assert (c["premiere_livraison"], c["derniere_livraison"], c["nb_livraisons"]) == (
        "20261102-213929", "20261104-004428", 3)
    assert c["jours_sans_livraison"] == []
    assert not any(a["dans_periode_couverte"] for a in actes.values())
    assert {r[0] for r in ctx.x("SELECT DISTINCT statut FROM couverture_jo_gouvernement")} == {"non_collecte"}


# -- petites tables écrites ici ------------------------------------------------------------

PROV = [("prov_point", pa.string()), ("prov_uid", pa.string()), ("prov_version", pa.int32()),
        ("prov_url", pa.string()), ("prov_etat", pa.string())]


def _ecrire_z2(dossier, actes=(), sommaires=(), liens=()):
    os.makedirs(dossier, exist_ok=True)
    for table, lignes, cle in (("acte_reglementaire", actes, "uid"),
                               ("sommaire_jo", sommaires, "conteneur"),
                               ("lien_acte_loi", liens, "acte"), ("version_acte", (), "acte"),
                               ("suppression_jo", (), "livraison")):
        schema = pa.schema(list(jo_actes.TABLES[table]) + PROV)
        rows = []
        for k, l in enumerate(lignes):
            r = {c: None for c in schema.names}
            r.update({"prov_point": "jo", "prov_uid": f"{l[cle]}#{k}", "prov_version": 1,
                      "prov_etat": "present"})
            r.update(l)
            rows.append(r)
        pq.write_table(pa.Table.from_pylist(rows, schema=schema),
                       os.path.join(dossier, f"jo_actes__{table}.parquet"))


def _acte(id_, date, titre="Arrêté du 1er janvier", nature="ARRETE", ministere=None, numero=None,
          livraison="20261006-002605", sentinelle=False):
    return {"uid": f"jorf:{id_}", "id_jorf": id_, "livraison": livraison, "nature": nature,
            "titre": titre, "titre_complet": titre, "numero": numero, "ministere": ministere,
            "date_publication": date, "date_publication_sentinelle": sentinelle,
            "prov_url": f"https://www.legifrance.gouv.fr/jorf/id/{id_}"}


def _sommaire(conteneur, date, num, actes, livraison, rubrique=("JO", "Textes généraux")):
    return [{"conteneur": conteneur, "livraison": livraison, "rang": k, "num_jo": num,
             "titre_jo": f"JORF n°{num} du {date}", "date_publication": date,
             "acte": f"jorf:{a}", "id_jorf": a, "rubrique": list(rubrique), "niveau": len(rubrique)}
            for k, a in enumerate(actes)]


def test_jour_partage_jour_sans_gouvernement_et_sentinelle(tmp_path):
    _ecrire_z2(tmp_path / "z2", actes=[
        _acte("T1", "2007-06-18"),       # Fillon 1 finit et Fillon 2 commence ce jour-là
        _acte("T2", "2012-05-12"),       # entre Fillon 3 (fin 10/05) et Ayrault 1 (début 16/05)
        _acte("T3", None, sentinelle=True),
        _acte("T4", "2025-10-10"), _acte("T5", "2025-10-11"),
        _acte("T6", "2021-03-02", livraison="20261020-214622")])    # redélivré en 2026 : Castex
    ctx, bilan = _relier(tmp_path / "z2", tmp_path / "z3")
    g = {r[0]: r[1:] for r in ctx.x(
        "SELECT id_jorf, gouvernement, gouvernement_raison FROM acte_rattache")}
    assert g["T1"] == ("PO384206", None)
    assert g["T2"] == (None, "aucun gouvernement publié à cette date")
    assert g["T3"] == (None, "date de publication sentinelle (2999)")
    assert g["T4"][0] == LECORNU and g["T5"][0] == LECORNU_II and g["T6"][0] == "PO773371"
    assert bilan["R-RATTACHEMENT-ACTE"]["couverture"]["gouvernement_etabli"] == [4, 6]


def test_periode_couverte_suite_continue_et_numero_manquant(tmp_path):
    actes = [_acte("A30", "2026-10-02", livraison="20261006-212213"),
             _acte("V1950", "1950-07-14", livraison="20261006-212213"),
             _acte("A33", "2026-10-06"), _acte("A34", "2026-10-07", livraison="20261007-002326"),
             _acte("A36", "2026-10-09", livraison="20261009-003010"),
             _acte("A36b", "2026-10-09", livraison="20261009-003010")]
    sommaires = (
        # numéro du 02/10 redélivré : un texte sur deux seulement est lu -> incomplet
        _sommaire("C30", "2026-10-02", "0230", ["A30", "ABSENT"], "20261006-212213")
        # numéro de 1950 redélivré, complet par hasard : avant la coupure, il ne compte pas
        + _sommaire("C1950", "1950-07-14", None, ["V1950"], "20261006-212213")
        + _sommaire("C33", "2026-10-06", "0233", ["A33"], "20261006-002605")
        + _sommaire("C34", "2026-10-07", "0234", ["A34"], "20261007-002326")
        # le n° 0235 n'a jamais été reçu
        + _sommaire("C36", "2026-10-09", "0236", ["A36", "A36b"], "20261009-003010",
                    rubrique=("JO", "Décrets, arrêtés, circulaires", "MESURES NOMINATIVES")))
    _ecrire_z2(tmp_path / "z2", actes=actes, sommaires=sommaires)
    ctx, bilan = _relier(tmp_path / "z2", tmp_path / "z3")
    (c,) = _lignes(ctx, "SELECT * FROM couverture_jo")
    assert (c["premiere_publication"], c["derniere_publication"]) == ("2026-10-06", "2026-10-09")
    assert (c["nb_numeros"], c["numeros_manquants"], c["nb_actes"]) == (3, ["2026/0235"], 4)
    assert c["premier_numero"] == "JORF n°0233 du 2026-10-06"
    assert c["jours_sans_livraison"] == ["2026-10-08"]
    dans = dict(ctx.x("SELECT id_jorf, dans_periode_couverte FROM acte_rattache"))
    assert dans == {"A30": False, "V1950": False, "A33": True, "A34": True, "A36": True, "A36b": True}
    # rubrique en capitales : toujours une mesure nominative
    nomin = dict(ctx.x("SELECT id_jorf, mesure_nominative FROM acte_rattache"))
    assert nomin["A36"] is True and nomin["A33"] is False
    (lc,) = _lignes(ctx, f"SELECT * FROM couverture_jo_gouvernement WHERE gouvernement = '{LECORNU_II}'")
    assert (lc["couvert_du"], lc["couvert_au"], lc["statut"]) == ("2026-10-06", "2026-10-09", "partiel")
    assert (lc["nb_actes_couverts"], lc["nb_actes_hors_periode"]) == (4, 1)
    (ca,) = _lignes(ctx, "SELECT * FROM couverture_jo_gouvernement WHERE gouvernement = 'PO773371'")
    assert ca["statut"] == "non_collecte" and ca["couvert_du"] is None


def test_decisions_contradictoires_et_absentes(tmp_path):
    _ecrire_z2(tmp_path / "z2", actes=[
        _acte("M1", "2026-10-06", ministere="Ministère de la culture"),
        _acte("M2", "2026-10-06", ministere="MINISTERE DE LA CULTURE"),
        _acte("M3", "2026-10-06", ministere="Ministère de la justice")])
    ctx, _ = _relier(tmp_path / "z2", tmp_path / "z3")       # aucune décision
    assert {r[0] for r in ctx.x("SELECT DISTINCT ministere_statut FROM acte_rattache")} == {"non_etabli"}
    dec = _decisions(str(tmp_path / "dec"), [("Ministère de la culture", "Culture"),
                                             ("MINISTERE DE LA CULTURE", "Culture et communication"),
                                             ("Ministère de la justice", "Justice")])
    ctx, bilan = _relier(tmp_path / "z2", tmp_path / "z3b", dec)
    m = {r[0]: r[1:] for r in ctx.x(
        "SELECT id_jorf, ministere_normalise, ministere_raison FROM acte_rattache")}
    assert m["M1"] == m["M2"] == (None, "décisions contradictoires pour ce libellé")
    assert m["M3"] == ("Justice", None)
    assert bilan["R-RATTACHEMENT-ACTE"]["couverture"]["ministere_etabli"] == [1, 3]


def test_formes_de_citation_d_une_loi(tmp_path):
    actes = [
        _acte("L1", "2026-10-06", titre="Décret n° 2026-1 pris pour l'application de la loi "
              "organique n° 2009-403 et de la loi n° 2006-1640 du 21 décembre 2006 ; "
              "loi n° 2006-1640 (bis)"),
        _acte("L2", "2026-10-06", titre="Arrêté relatif aux emplois n° 12-4 et à l'ordonnance "
              "n° 58-1270 portant loi organique"),
        _acte("L3", "2026-10-06", nature="LOI", numero="2026-1015",
              titre="LOI n° 2026-1015 du 2 novembre 2026 modifiant la loi no 86-33"),
        _acte("L4", "2026-10-06", nature="LOI", numero="2009-403", titre="LOI organique n° 2009-403"),
        _acte("L5", "2026-10-06", nature="LOI", numero="2009-403",
              titre="LOI organique n° 2009-403 (rectificatif)")]
    _ecrire_z2(tmp_path / "z2", actes=actes)
    ctx, _ = _relier(tmp_path / "z2", tmp_path / "z3")
    cit = ctx.x("SELECT acte, numero_loi, rang, type_loi, loi_jorf, loi_identifiee_par "
                "FROM acte_loi_citee ORDER BY acte, rang")
    assert cit == [
        ("jorf:L1", "2009-403", 1, "loi organique", "L4", "acte_lu"),   # pas le rectificatif
        ("jorf:L1", "2006-1640", 2, "loi", None, None),                  # cité deux fois : une ligne
        ("jorf:L3", "86-33", 1, "loi", None, None)]                      # son propre numéro exclu
    c = dict(ctx.x("SELECT id_jorf, cite_une_loi FROM acte_rattache"))
    assert c == {"L1": True, "L2": False, "L3": True, "L4": False, "L5": False}


def test_numero_incomplet_au_milieu_ne_reduit_pas_la_periode(tmp_path):
    """10/11/2026 : un numéro incomplet vers le 09/11 a ramené la période couverte à deux jours et
    retiré les actes d'octobre de la fiche Lecornu II. Un numéro incomplet est un trou nommé ;
    la période va du premier au dernier numéro complet livré dans son actualité."""
    actes = [_acte("A33", "2026-10-06"), _acte("A34", "2026-10-07", livraison="20261007-002326"),
             _acte("A36", "2026-10-09", livraison="20261009-003010")]
    sommaires = (
        _sommaire("C33", "2026-10-06", "0233", ["A33"], "20261006-002605")
        # le n° 0234 du 07/10 a un texte non reçu : incomplet
        + _sommaire("C34", "2026-10-07", "0234", ["A34", "ABSENT"], "20261007-002326")
        + _sommaire("C36", "2026-10-09", "0236", ["A36"], "20261009-003010"))
    _ecrire_z2(tmp_path / "z2", actes=actes, sommaires=sommaires)
    ctx, _ = _relier(tmp_path / "z2", tmp_path / "z3")
    (c,) = _lignes(ctx, "SELECT * FROM couverture_jo")
    assert (c["premiere_publication"], c["derniere_publication"]) == ("2026-10-06", "2026-10-09")
    assert c["nb_numeros_incomplets"] == 1
    dans = dict(ctx.x("SELECT id_jorf, dans_periode_couverte FROM acte_rattache"))
    assert dans == {"A33": True, "A34": True, "A36": True}
