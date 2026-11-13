"""Description du traitement servie par Pages (`empreinte_src.methodologie`, issue #95) : tirée du
code, complète, en Markdown pour pdoc (module `documentation.comprendre.traitement`). Sans réseau."""
import re

import pytest

from empreinte_src import lecture, liaison, methodologie, pages_doc


@pytest.fixture(scope="module")
def page():
    return methodologie.rendre(methodologie.donnees(), commit="0123456789abcdef0123",
                               depot="https://github.com/exemple/depot")


def test_etapes_e0_a_e8():
    etapes = methodologie.etapes()
    assert [e["etape"].split()[0] for e in etapes] == [f"E{i}" for i in range(9)]
    assert all(e["quoi"] and e["modules"] for e in etapes)


def test_chaque_regle_dans_l_ordre_d_application(page):
    attendu = [m.NOM for m in liaison.regles()]
    assert [r["nom"] for r in methodologie.regles()] == attendu
    positions = [page.index(f"\n### {i}. `{n}`\n") for i, n in enumerate(attendu, 1)]
    assert positions == sorted(positions)
    for m in liaison.regles():
        assert " ".join(m.DESCRIPTION.split()) in page
        for s in m.SORTIES:
            assert f"`{s}`" in page


def test_dependances_et_lecteurs_de_chaque_regle():
    r = {x["nom"]: x for x in methodologie.regles()}
    for m in liaison.regles():
        for d in m.DEPEND:
            assert m.NOM in r[d]["lue_par"]
        assert r[m.NOM]["version"] == m.VERSION


def test_chaque_lecteur_ses_tables_et_colonnes(page):
    decrits = {l["nom"]: l for l in methodologie.lecteurs()}
    for m in lecture.lecteurs():
        l = decrits[m.NOM]
        assert l["version"] == m.VERSION and l["types"] == tuple(m.TYPES)
        assert l["points"], f"{m.NOM} : aucun point d'accès de ses types"
        assert f"\n### `{m.NOM}`\n" in page
        for t, schema in m.TABLES.items():
            assert f"{m.NOM}__{t}</code>" in page
            assert [c for c, _ in l["tables"][t]] == schema.names
    assert "prov_empreinte" in page


def test_types_de_colonnes_lisibles():
    import pyarrow as pa
    assert methodologie._type(pa.string()) == "texte"
    assert methodologie._type(pa.list_(pa.int32())) == "liste de entier"
    assert methodologie._type(pa.struct([("a", pa.string()), ("b", pa.bool_())])) == "structure (a, b)"


def test_controles_bloquants_et_avertissements(page):
    ctl = methodologie.controles()
    bloquants = {c["code"] for c in ctl if c["bloquant"]}
    avert = {c["code"] for c in ctl if not c["bloquant"]}
    assert bloquants == {f"C{i}" for i in range(1, 8)}
    assert {f"A{i}" for i in range(1, 10)} <= avert
    # Chaque contrôle a un titre ; chaque code bloquant a un résumé dans la docstring du module.
    assert all(c["titres"] and c["methodes"] for c in ctl)
    assert all(c["bref"] for c in ctl if c["bloquant"])
    for c in ctl:
        mot = "bloquant" if c["bloquant"] else "avertissement"
        assert re.search(rf"^#### `{re.escape(c['code'])}` .* \({mot}\)$", page, re.M), c["code"]
    # C1 et C6 partagent une méthode : l'explication de chacun est la sienne.
    par = {(c["code"], c["bloquant"]): c for c in ctl}
    assert par[("C6", True)]["explications"] != par[("C1", True)]["explications"]


def test_controles_lus_sans_executer(tmp_path):
    source = tmp_path / "controles.py"
    source.write_text('''"""Contrôles bloquants : C1 (pertes). **Avertissements** : A1 fiche hors modèle."""
class Controles:
    def c1(self, x):
        """Vérifie les pertes."""
        self._signaler("C1", "Perdus", x)
        self._signaler(code, titre, x)           # non constant : ignoré

    def deux(self, x):
        # Premier cas.
        self._avertir("A1", "Hors modèle", x)
        y = 1
        # Second cas, sur deux
        # lignes.
        self._signaler("C9", "Autre", x, bloquant=False)
''', encoding="utf-8")
    ctl = methodologie.controles(str(source))
    assert [(c["code"], c["bloquant"]) for c in ctl] == [("C1", True), ("A1", False), ("C9", False)]
    par = {c["code"]: c for c in ctl}
    assert par["C1"]["bref"] == "pertes" and par["C1"]["explications"] == ["Vérifie les pertes."]
    assert par["A1"]["bref"] == "fiche hors modèle" and par["A1"]["explications"] == ["Premier cas."]
    assert par["C9"]["explications"] == ["Second cas, sur deux lignes."]


def test_perimetre(page):
    from empreinte_src import perimetre
    assert f"de la {perimetre.plage()}" in page
    assert methodologie.perimetre()["paroles"] == perimetre.plage(perimetre.LEGISLATURES_PAROLES)


def test_liens_de_la_page(page):
    assert page.startswith("# Le traitement, étape par étape\n")
    assert "<script" not in page and "<style" not in page and "<img" not in page
    assert "[`0123456789ab`](https://github.com/exemple/depot/commit/0123456789abcdef0123)" in page
    # Chaque lien interne mène à l'ancre que pdoc donnera à un titre de la page.
    ancres = set(pages_doc.ancres(page).values())
    internes = re.findall(r"\]\(#([^)]+)\)", page)
    assert len(internes) > 100
    for cible in internes:
        assert cible in ancres, cible
    # Les autres liens relatifs mènent à la documentation (pages pdoc), vue depuis
    # `documentation/comprendre/traitement.html`.
    for lien in re.findall(r"\]\((\.\./[^)]+)\)", page):
        assert lien.startswith(("../../empreinte_src", "../../documentation.html")), lien
    assert "](../../empreinte_src/controles.html#Controles." in page


def test_titres_des_docstrings_reprises_sous_ceux_de_la_page():
    assert methodologie._encart("Texte.\n\n## Titre\n\nSuite.") == "Texte.\n\n###### Titre\n\nSuite."
    assert methodologie._cellule("a | b\n  c") == "a \\| b c"
