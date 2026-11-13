"""Description du traitement servie par Pages (`empreinte_src.methodologie`, issue #95) : tirée du
code, complète, sans script ni ressource externe. Sans réseau."""
import re

import pytest

from empreinte_src import lecture, liaison, methodologie


@pytest.fixture(scope="module")
def page(tmp_path_factory):
    dossier = tmp_path_factory.mktemp("pages") / "traitement"
    chemin = methodologie.ecrire(str(dossier), commit="0123456789abcdef0123",
                                 depot="https://github.com/exemple/depot")
    with open(chemin, encoding="utf-8") as f:
        return f.read()


def test_etapes_e0_a_e8():
    etapes = methodologie.etapes()
    assert [e["etape"].split()[0] for e in etapes] == [f"E{i}" for i in range(9)]
    assert all(e["quoi"] and e["modules"] for e in etapes)


def test_chaque_regle_dans_l_ordre_d_application(page):
    attendu = [m.NOM for m in liaison.regles()]
    assert [r["nom"] for r in methodologie.regles()] == attendu
    positions = [page.index(f'<h3 id="regle-{methodologie._ancre(n)}">') for n in attendu]
    assert positions == sorted(positions)
    for m in liaison.regles():
        assert methodologie._inline(m.DESCRIPTION) in page
        for s in m.SORTIES:
            assert f"<code>{s}</code>" in page


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
        assert f'id="lecteur-{m.NOM}"' in page
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
        assert f'id="controle-{methodologie._ancre(c["code"])}-{mot}"' in page
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


def test_page_autonome(page):
    assert page.startswith("<!doctype html>") and '<html lang="fr">' in page
    assert "<script" not in page and "<link" not in page and "<img" not in page
    assert "@import" not in page and "url(" not in page
    assert "prefers-color-scheme: dark" in page and 'name="viewport"' in page
    assert 'href="https://github.com/exemple/depot/commit/0123456789abcdef0123"' in page
    # Les liens internes mènent à une ancre de la page.
    ancres = set(re.findall(r'id="([^"]+)"', page))
    for cible in re.findall(r'href="#([^"]+)"', page):
        assert cible in ancres, cible
    # Les liens vers la documentation du code restent dans Pages.
    for lien in re.findall(r'href="(\.\./[^"]+)"', page):
        assert lien.startswith(("../doc/empreinte_src", "../index.html")), lien


def test_markdown_des_docstrings():
    h = methodologie.markdown("""Titre `code` et **gras** <b>.

    | A | B |
    | --- | --- |
    | x | `y` |

    Texte :
    - un
      suite
    - deux""")
    assert "<p>Titre <code>code</code> et <strong>gras</strong> &lt;b&gt;.</p>" in h
    assert "<th>A</th>" in h and "<td><code>y</code></td>" in h and "---" not in h
    assert "<p>Texte :</p><ul><li>un suite</li><li>deux</li></ul>" in h.replace("\n", "")


def test_ligne_de_commande(tmp_path, capsys):
    methodologie.main([str(tmp_path / "t"), "--commit", "abc"])
    assert (tmp_path / "t" / "index.html").read_text(encoding="utf-8").count("<code>abc</code>") == 1
    assert capsys.readouterr().out.strip().endswith("index.html")
