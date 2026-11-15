"""Regroupements pour l'affichage (#88) : la table décidée est servie à part, les fiches gardent
les codes ; un code sans case n'est jamais rangé par défaut."""
import gzip
import json
import os
import shutil

from empreinte_src import methodologie
from empreinte_src.composeurs import regroupements
from empreinte_src.composition import Ecrivain
from empreinte_src.controles import Controles
from empreinte_src.liaison import Contexte

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DECISION = os.path.join(RACINE, "references", "regroupement", "commission_saisie.yaml")


def _contexte(tmp_path):
    d = tmp_path / "references" / "regroupement"
    d.mkdir(parents=True)
    shutil.copy(DECISION, d / "commission_saisie.yaml")       # la vraie décision
    (tmp_path / "z2").mkdir()
    ctx = Contexte(str(tmp_path / "z2"), str(tmp_path / "z3"), str(tmp_path / "references"))
    x = ctx.con.execute
    x("""CREATE VIEW matiere AS SELECT * FROM (VALUES
           ('D1', 'PO59051', 'assemblee', 'Commission des lois…', '17'),
           ('D2', 'PO59051', 'assemblee', 'Commission des lois…', '16'),
           ('D3', 'PO766718', 'assemblee', 'Commission spéciale… bioéthique', '15'),
           ('D4', NULL, 'senat_seulement', 'Saisi au Sénat seulement', '17'),
           ('D5', NULL, 'non_etablie', 'Matière non établie', '14'),
           ('D6', 'PO999', 'assemblee', 'Commission inconnue', '17'),
           ('D7', 'PO420120', 'assemblee', 'Commission des affaires sociales', '13'))
         t(dossier, commission, statut, libelle, legislature)""")
    x("""CREATE VIEW an_acteurs__organe AS SELECT * FROM (VALUES
           ('PO59051', 'COMPER'), ('PO766718', 'CNPS'), ('PO999', 'COMNL'), ('PO420120', 'COMPER'))
         t(uid, type_organe)""")
    return ctx


def test_regroupement_servi_a_part(tmp_path):
    ctx = _contexte(tmp_path)
    ecr = Ecrivain(str(tmp_path / "site"), "g000001")
    regroupements.composer(ctx, ecr)
    with gzip.open(os.path.join(ecr.racine, "regroupements.json.gz")) as f:
        (t,) = json.load(f)["regroupements"]
    assert t["nom"] == "commission_saisie" and t["decision"] == "regroupement/commission_saisie.yaml"
    cases = [g[1] for g in t["groupes"]["lignes"]]
    assert len(cases) == 11 and cases[0] == "Affaires culturelles et éducation"
    assert cases[-3:] == ["Commissions spéciales", "Saisi au Sénat seulement", "Matière non établie"]
    codes = {(l[0], l[1]): l for l in t["codes"]["lignes"]}
    assert codes[("commission", "PO59051")][3:] == ["lois", "commission = PO59051"]
    # une commission spéciale est rangée par son type
    assert codes[("commission", "PO766718")][3:] == ["commissions_speciales", "type_commission = CNPS"]
    # sans commission, le code est le statut de la matière
    assert codes[("matiere_statut", "senat_seulement")][3] == "senat_seulement"
    assert codes[("matiere_statut", "non_etablie")][3] == "non_etablie"
    # un code sans case n'est jamais rangé par défaut ; hors périmètre (XIIIe) : absent
    assert codes[("commission", "PO999")][3:] == [None, None]
    assert ("commission", "PO420120") not in codes
    faits = str(tmp_path / "faits.parquet")
    ecr.clore()
    ecr.ecrire_faits_publies(faits)
    c = Controles(ecr.racine)
    c.preparer(ctx.con, faits, set())
    c.a7_non_resolues({})
    (a7,) = [a for a in c.anomalies if a["controle"] == "A7"]
    assert a7["exemples"] == ["regroupement commission_saisie : commission PO999 (« Commission inconnue ») sans case"]


def test_sans_decision_aucun_fichier(tmp_path):
    (tmp_path / "z2").mkdir()
    ctx = Contexte(str(tmp_path / "z2"), str(tmp_path / "z3"))
    ecr = Ecrivain(str(tmp_path / "site"), "g000001")
    regroupements.composer(ctx, ecr)
    assert not os.path.exists(os.path.join(ecr.racine, "regroupements.json.gz"))


def test_methodologie_declare_le_regroupement():
    (r,) = [r for r in methodologie.regroupements() if r["nom"] == "commission_saisie"]
    assert [c["libelle"] for c in r["cases"]][-1] == "Matière non établie"
    page = methodologie.rendre(methodologie.donnees())
    assert "## 6. Les regroupements pour l'affichage" in page
    assert "| Commissions spéciales | `type_commission = CNPS` |" in page


def test_qualites_d_orateur_en_trois_cases(tmp_path):
    """#75 : trois cases ; « Député européen » n'a aucun code à l'Assemblée ; une qualité non
    établie reste hors des cases (jamais rangée par défaut, jamais signalée comme code inconnu)."""
    d = tmp_path / "references" / "regroupement"
    d.mkdir(parents=True)
    shutil.copy(os.path.join(RACINE, "references", "regroupement", "qualite_orateur.yaml"), d)
    (tmp_path / "z2").mkdir()
    ctx = Contexte(str(tmp_path / "z2"), str(tmp_path / "z3"), str(tmp_path / "references"))
    ctx.con.execute("""CREATE VIEW qualite_orateur AS SELECT * FROM (VALUES
        ('depute', NULL), ('rapporteur', 'rapporteur'), ('membre_du_gouvernement', 'ministre'),
        ('president_de_seance', NULL), ('autre', 'président du groupe'), (NULL, NULL))
        t(qualite, qualite_ecrite_libelle)""")
    ecr = Ecrivain(str(tmp_path / "site"), "g000001")
    regroupements.composer(ctx, ecr)
    with gzip.open(os.path.join(ecr.racine, "regroupements.json.gz")) as f:
        (t,) = json.load(f)["regroupements"]
    assert [g[1] for g in t["groupes"]["lignes"]] == ["Député", "Membre du gouvernement", "Député européen"]
    codes = {l[1]: l[3] for l in t["codes"]["lignes"]}
    assert codes == {"autre": "depute", "depute": "depute", "membre_du_gouvernement": "membre_du_gouvernement",
                     "president_de_seance": "depute", "rapporteur": "depute"}
    page = methodologie.rendre(methodologie.donnees())
    assert "| Député européen | *aucun code de cette source* |" in page


def test_natures_de_parole_ordre_de_legende_et_priorite(tmp_path):
    """#87 : la légende suit `ordre`, le rangement suit l'ordre du fichier (une motion de censure
    est d'abord une motion, pas un texte) ; le code d'une valeur est son premier champ non vide."""
    d = tmp_path / "references" / "regroupement"
    d.mkdir(parents=True)
    shutil.copy(os.path.join(RACINE, "references", "regroupement", "nature_parole.yaml"), d)
    (tmp_path / "z2").mkdir()
    ctx = Contexte(str(tmp_path / "z2"), str(tmp_path / "z3"), str(tmp_path / "references"))
    ctx.con.execute("""CREATE VIEW sujet_intervention AS SELECT * FROM (VALUES
        ('motion_de_censure', NULL, 'texte'), ('explications_de_vote', NULL, 'texte'),
        (NULL, 'QG', 'question'), (NULL, 'QPM', 'question'), (NULL, 'QOSD', 'question'),
        (NULL, 'QG', 'creneau'), (NULL, NULL, 'texte'), (NULL, NULL, 'loi_de_finances'),
        (NULL, NULL, 'hors_point'), (NULL, NULL, 'procedure'))
        t(genre_point, code_creneau, type_sujet)""")
    ecr = Ecrivain(str(tmp_path / "site"), "g000001")
    regroupements.composer(ctx, ecr)
    with gzip.open(os.path.join(ecr.racine, "regroupements.json.gz")) as f:
        (t,) = json.load(f)["regroupements"]
    assert t["champs"] == ["genre_point", "code_creneau", "type_sujet"]
    assert [g[1] for g in t["groupes"]["lignes"]] == [
        "Questions au gouvernement", "Questions orales", "Textes", "Motion de censure",
        "Explications de vote", "Commission", "Autres"]
    codes = {(l[0], l[1]): l[3] for l in t["codes"]["lignes"]}
    assert codes == {("genre_point", "motion_de_censure"): "motion_de_censure",
                     ("genre_point", "explications_de_vote"): "explications_de_vote",
                     ("code_creneau", "QG"): "questions_au_gouvernement",
                     ("code_creneau", "QPM"): "questions_au_gouvernement",
                     ("code_creneau", "QOSD"): "questions_orales",
                     ("type_sujet", "texte"): "textes", ("type_sujet", "loi_de_finances"): "textes",
                     ("type_sujet", "hors_point"): "autres", ("type_sujet", "procedure"): "autres"}
    # QG vient de deux lignes (question, paragraphe du créneau) : servi une fois
    assert sum(1 for l in t["codes"]["lignes"] if l[1] == "QG") == 1
    (r,) = [r for r in methodologie.regroupements() if r["nom"] == "nature_parole"]
    assert [c["libelle"] for c in r["cases"]][:3] == ["Questions au gouvernement", "Questions orales", "Textes"]
