"""Contrôles C3 (données laissées de côté), C7 (personne attendue écartée en silence), règle
R-PERIMETRE, et avertissements A1 à A8 (doc. 2, 2.8), sur de petites tables à la forme exacte des
sorties des règles et de l'export des faits publiés."""
import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

from empreinte_src.composition import IDS
from empreinte_src.controles import Controles
from empreinte_src.liaison import Contexte, ordonner, relier
from empreinte_src.regles import r_perimetre
from empreinte_src.verification import lire_page

COLS_FP = ["fiche", "section", "type_fait"] + [f"id_{k}" for k in IDS] + ["valeur", "date", "source_url"]


def _fait(fiche, section, valeur="{}", **ids):
    r = {c: None for c in COLS_FP}
    r.update({"fiche": fiche, "section": section, "type_fait": "t", "valeur": valeur})
    r.update({f"id_{k}": v for k, v in ids.items()})
    return r


TABLES = {
    "lignee": [{"lignee": "lig:000001", "adresse": "soc", "publiee": True}],
    "lignee_maillon": [{"lignee": "lig:000001", "maillon": "grp:17:PO17S", "legislature": 17, "affiche": True,
                        "organes": ["PO17S"]}],
    "appartenance": [{"acteur": "PA1", "groupe": "PO17S", "legislature": 17, "debut": "2024-07-18", "fin": None},
                     {"acteur": "PA2", "groupe": "PO17S", "legislature": 17, "debut": "2024-07-18", "fin": "2025-01-01"}],
    "candidat": [{"per": "per:000001", "nom": "Alice Martin", "acteur": "PA1", "adresse": "alice-martin",
                  "publie": True, "statut": "declaree", "raison_non_publie": None},
                 {"per": "per:000002", "nom": "Jean Homonyme", "acteur": None, "adresse": None, "publie": False,
                  "statut": "declaree", "raison_non_publie": "adresse non établie"},
                 {"per": "per:000003", "nom": "Paul Parti", "acteur": None, "adresse": "paul-parti", "publie": False,
                  "statut": "retiree", "raison_non_publie": "candidature retirée"}],
    "gouvernement": [{"organe": "PO-G", "nom": "Bayrou", "adresse": "bayrou"}],
    "gouvernement_legislature": [{"gouvernement": "PO-G", "legislature": 17}],
    "membre_gouvernement": [{"gouvernement": "PO-G", "acteur": "PA7"}],
    "depute": [{"acteur": "PA1", "legislature": 17}, {"acteur": "PA9", "legislature": 17}],
    "an_scrutins__scrutin": [{"uid": "VT1", "numero": 1, "date": "2025-01-30", "nombre_votants": 3, "pour": 2,
                              "contre": 1, "abstentions": 0},
                             {"uid": "VT2", "numero": 2, "date": "2025-02-01", "nombre_votants": 1, "pour": 1,
                              "contre": 0, "abstentions": 0}],
    # VT1 (30/01/2025) : PA2 a quitté le groupe le 01/01/2025, le groupe compte 1 membre.
    "an_scrutins__decompte_groupe": [{"scrutin": "VT1", "organe": "PO17S", "nombre_membres": 1},
                                     {"scrutin": "VT2", "organe": "PO0", "nombre_membres": None}],
    "an_scrutins__position_vote": [{"scrutin": "VT1", "acteur": "PA1", "position": "pour"}],
    "amendement_canonique": [{"amendement": "AM1", "acteur": "PA1", "date_depot": "2025-01-20", "alias": ["AM1B"]},
                             {"amendement": "AM2", "acteur": "PA2", "date_depot": "2025-03-01", "alias": None},
                             {"amendement": "AM3", "acteur": "PA2", "date_depot": "2024-12-01", "alias": None}],
    "intervention_attribuee": [{"compte_rendu": "CR1", "id_syceron": "1", "acteur": "PA1", "date": "2025-01-30"},
                               {"compte_rendu": "CR1", "id_syceron": "2", "acteur": None, "date": "2025-01-30"}],
    "parole_personne": [{"acteur": "PA1", "compte_rendu": "CR1", "id_syceron": "1", "date": "2025-01-30"}],
    "mandat_ouvert_organe_clos": [{"mandat": "PM9", "acteur": "PA7", "organe": "PO-G", "organe_fin": "2025-09-09"}],
    "legislature": [{"numero": 17, "debut": "2024-07-18", "fin": None}],
    "filiation": [{"maillon_avant": "grp:16:X", "maillon_apres": "grp:17:PO17S", "verdict": "a_trancher"}],
}
FICHES = {"lignee/soc", "candidat/alice-martin", "gouvernement/bayrou", "legislature/17"}
FAITS = [
    _fait("lignee/soc", "membres", acteur="PA1"), _fait("lignee/soc", "membres", acteur="PA2"),
    _fait("gouvernement/bayrou", "composition", acteur="PA7"),
    _fait("lignee/soc", "votes-17", scrutin="VT1"),
    _fait("lignee/soc", "amendements-2025", amendement="AM1"),
    # AM3 (PA2 membre au dépôt) n'est pas servi : C3 doit le voir.
    _fait("lignee/soc", "paroles-textes-2025-s1", compte_rendu="CR1", autre="1", acteur="PA1"),
]


def _con(tmp_path, tables=TABLES, faits=FAITS):
    con = duckdb.connect()
    for n, l in tables.items():
        con.register(n, pa.Table.from_pylist(l))
    p = tmp_path / "fp.parquet"
    pq.write_table(pa.Table.from_pylist(faits, schema=pa.schema([(c, pa.string()) for c in COLS_FP])), p)
    return con, str(p)


def _ctrl(tmp_path, tables=TABLES, faits=FAITS, fiches=FICHES, levees=None, manifeste=None):
    con, p = _con(tmp_path, tables, faits)
    # Population : la règle R-PERIMETRE elle-même, appliquée sur ces tables.
    ctx = Contexte(str(tmp_path / "z2"), str(tmp_path / "z3"))
    for n, l in tables.items():
        ctx.con.register(n, pa.Table.from_pylist(l))
    relier(ctx, ordonner([_faux(r) for r in r_perimetre.DEPEND] + [r_perimetre]))
    con.register("population", pq.read_table(ctx.sorties["population"]))
    c = Controles(str(tmp_path), levees=levees)
    c.preparer(con, p, fiches, manifeste or [])
    return c


def _faux(nom):
    import types
    return types.SimpleNamespace(NOM=nom, VERSION=0, DEPEND=(), SORTIES=(), appliquer=lambda ctx: {})


def _an(c, code):
    return [a for a in c.anomalies if a["controle"] == code]


def test_perimetre_populations_et_raisons(tmp_path):
    c = _ctrl(tmp_path)
    p = {(r[0], r[1] or r[2]): r for r in c.con.execute(
        "SELECT population, per, acteur, fiche_attendue, raison_sortie FROM population").fetchall()}
    assert p[("candidat", "per:000001")][3] == "candidat/alice-martin"
    assert p[("candidat", "per:000003")][4] == "candidature_retiree_a_la_source"
    assert p[("candidat", "per:000002")][4] is None                    # adresse non établie : pas une sortie
    assert p[("membre_groupe", "PA2")][3] == "lignee/soc"
    assert p[("membre_gouvernement", "PA7")][3] == "gouvernement/bayrou"
    assert p[("depute_ni", "PA9")][3] is None


def test_c3_bilan_par_famille_et_objet_attendu_non_servi(tmp_path):
    c = _ctrl(tmp_path)
    b = {x["famille"]: x for x in c.c3_laisses_de_cote()}
    assert b["scrutins"]["ecartes"] == {"aucun_decompte_d_un_groupe_avec_fiche": 1}
    assert b["prises_de_parole"]["ecartes"] == {"orateur_non_attribue": 1}
    # AM2 : déposé après le départ de PA2 → écarté avec raison ; AM3 : PA2 membre, non servi → bloque.
    assert b["amendements"]["ecartes"] == {"auteur_hors_groupe_a_la_date": 1}
    assert b["amendements"]["exemples"] == ["AM3"]
    assert b["questions"]["statut"] == "non_evalue"
    a = _an(c, "C3")
    assert a and a[0]["bloquant"] and a[0]["exemples"] == ["amendements: AM3"]


def test_c7_personne_absente_nommee(tmp_path):
    faits = [f for f in FAITS if not (f["section"] == "membres" and f["id_acteur"] == "PA2")]
    c = _ctrl(tmp_path, faits=faits)
    c.c7_personnes()
    a = _an(c, "C7")[0]
    assert a["bloquant"]
    assert a["exemples"] == ["candidat per:000002 Jean Homonyme → (aucune adresse) (adresse non établie)",
                             "membre_groupe PA2 → lignee/soc"]
    # Une décision `perimetre` sort la personne avec sa raison.
    t = dict(TABLES, decision_perimetre=[{"personne": "per:000002", "population": "candidat", "motif": "homonyme",
                                         "fichier": "perimetre/jh.yaml"}])
    c = _ctrl(tmp_path, tables=t)
    c.c7_personnes()
    assert not _an(c, "C7")


def test_avertissements_sans_bloquer(tmp_path):
    man = [{"fiche": "candidat/alice-martin", "type": "candidat", "sections": {"questions": {"lignes": 0}}},
           {"fiche": "candidat/bob", "type": "candidat", "sections": {"questions": {"lignes": 0}}},
           {"fiche": "lignee/soc", "type": "lignee", "sections": {"amendements-2025-1": {"lignes": 1}}}]
    faits = FAITS + [_fait("lignee/soc", "amendements-2025", amendement="AM1B"),
                     _fait("lignee/soc", "votes-17", scrutin="VT1")]          # même ligne deux fois
    c = _ctrl(tmp_path, faits=faits, manifeste=man,
              levees=[{"empreinte": "C1:0000", "fichier": "levee_controle/vieille.yaml"}])
    c.a1_hors_modele([{"objet": "candidat/bob", "motif": "test", "fichier": "fiche_hors_modele/b.yaml"}])
    c.a3_totaux()
    c.a4_double_affichage()
    c.a5_famille_a_zero()
    c.a6_couverture()
    c.a8_mandats_ouverts()
    c.a7_non_resolues({"filiation": [{"avant": "grp:15:Z", "apres": "grp:16:Z", "fichier": "filiation/z.yaml"}]})
    codes = {a["controle"] for a in c.anomalies}
    assert codes == {"A1", "A4", "A5", "A6", "A7", "A8"}          # A3 : effectifs concordants
    assert not any(a["bloquant"] for a in c.anomalies) and c.bilan()["publication_autorisee"]
    a4 = _an(c, "A4")[0]["exemples"]
    assert "lignee/soc / votes-17 : 1 lignes identiques" in a4
    assert "amendement AM1B servi alors qu'il est une copie de AM1" in a4
    assert _an(c, "A5")[0]["exemples"] == ["candidat / questions : vide sur les 2 fiches"]
    a6 = _an(c, "A6")[0]["exemples"]
    # Un décompte, jamais de nom : PA2 (aucune parole servie) n'est pas nommé.
    assert "1 membres de groupes de la XVIIe sur 2 sans prise de parole servie" in a6
    assert not any("PA2" in x for x in a6)
    a7 = _an(c, "A7")[0]["exemples"]
    assert "filiation à trancher : grp:16:X → grp:17:PO17S" in a7
    assert "décision filiation/z.yaml sans objet : grp:15:Z → grp:16:Z" in a7
    assert "levée levee_controle/vieille.yaml sans objet cette nuit : C1:0000" in a7
    assert _an(c, "A8")[0]["exemples"] == ["PM9 (PA7) dans PO-G, clos le 2025-09-09"]


def test_a3_effectif_different_du_decompte_publie(tmp_path):
    t = dict(TABLES, an_scrutins__decompte_groupe=[{"scrutin": "VT1", "organe": "PO17S", "nombre_membres": 5}])
    c = _ctrl(tmp_path, tables=t)
    c.a3_totaux()
    assert _an(c, "A3")[0]["exemples"] == ["VT1 PO17S : publié 5, nos appartenances 1"]   # PO0 non comparé


PAGE = """<div>Nombre de votants : <b>3</b></span> Pour l'adoption : <b>2</b></span>
Contre : <b>1</b></span> Abstention : <b>0</b></span>
<li data-organe-id="PO17S"><span class="h6 _colored-travaux">Pour</span><span>: 2</span>
<li class="_no-border" data-acteur-id="PA1 - PM1"><li class="_no-border" data-acteur-id="PA3 - PM3">
<span class="h6 _colored-travaux">Contre</span><li class="_no-border" data-acteur-id="PA4 - PM4">
<li data-organe-id="PO845401"><span class="h6 _colored-travaux">Non-votants</span>
<li class="_no-border" data-acteur-id="PA5 - PM5"></div>"""


def test_lire_page_de_scrutin():
    p = lire_page(PAGE)
    assert p["totaux"] == {"nombre_votants": 3, "pour": 2, "contre": 1, "abstentions": 0}
    assert p["positions"] == {"PA1": "pour", "PA3": "pour", "PA4": "contre", "PA5": "non_votant"}


def test_a2_verification_croisee(tmp_path):
    c = _ctrl(tmp_path)
    r = c.a2_verification_croisee(1, lambda url: PAGE, nb_scrutins=5)
    assert (r["tires"], r["faits"], r["verifies"], r["ecarts"]) == (1, 2, 2, [])
    assert not _an(c, "A2")
    # Une page qui dit autre chose : écart, avec l'adresse.
    c = _ctrl(tmp_path)
    r = c.a2_verification_croisee(1, lambda url: PAGE.replace("<b>2</b>", "<b>9</b>"), nb_scrutins=5)
    assert r["ecarts"] and "/dyn/17/scrutins/1" in r["ecarts"][0]
    assert _an(c, "A2")[0]["bloquant"] is False
    # Injoignable : non vérifié, jamais un écart ; tout injoignable → avertissement dédié.

    def panne(url):
        raise TimeoutError
    c = _ctrl(tmp_path)
    r = c.a2_verification_croisee(1, panne, nb_scrutins=5)
    assert r["ecarts"] == [] and len(r["non_verifies"]) == 2
    assert _an(c, "A2")[0]["titre"].startswith("Vérification croisée impossible")
