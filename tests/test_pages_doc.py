"""Toute la documentation de Pages au format pdoc (`empreinte_src.pages_doc`) : le paquet
`documentation` écrit depuis `livrables/`, puis la documentation rendue par pdoc avec le code.
Sans réseau (Mermaid n'est chargé que par le navigateur)."""
import importlib
import os
import re
import shutil
import sys

import pytest

from empreinte_src import pages_doc

LIVRABLES = os.path.join(os.path.dirname(os.path.dirname(__file__)), "livrables")


@pytest.fixture
def livrables(tmp_path):
    s = tmp_path / "livrables"
    for d in ("etape-2", "annexes/mesures", "annexes/scripts"):
        (s / d).mkdir(parents=True)
    (s / "0-LISEZMOI.md").write_text(
        "# Lisez-moi\n\nVoir [le modèle](1-modele.md), [la cadence](1-modele.md#215--la-cadence), "
        "[les données](1-modele.md#données-servies), [la seconde](1-modele.md#données-servies-1), "
        "[les mesures](annexes/mesures/), [les scripts](annexes/scripts/), "
        "[un relevé](annexes/mesures/releve.tsv), [ailleurs](https://exemple.org/a.md), "
        "[ici](#lisez-moi) et [le README](../README.md).\n\n"
        "`[pas un lien](1-modele.md)` ![image](schema.png)\n\n"
        "```\n[dans un bloc](1-modele.md)\n```\n", encoding="utf-8")
    (s / "1-modele.md").write_text(
        "# 1. Modèle\n\n## 2.15 — La cadence\n\n## Données servies\n\n## Données servies\n\n"
        "| A | B |\n| --- | --- |\n| x | y |\n\n```mermaid\nflowchart LR\n  A --> B\n```\n",
        encoding="utf-8")
    (s / "10-suite.md").write_text("# 10. Suite\n", encoding="utf-8")
    (s / "etape-2" / "journal.md").write_text(
        "Sans titre en tête.\n\n# Journal\n\nRetour au [lisez-moi](../0-LISEZMOI.md#lisez-moi).\n",
        encoding="utf-8")
    (s / "annexes" / "mesures" / "an.md").write_text("# Mesures AN\n\nUn mot rare : xylophone.\n",
                                                     encoding="utf-8")
    (s / "annexes" / "mesures" / "releve.tsv").write_text("a\tb\n", encoding="utf-8")
    (s / "annexes" / "scripts" / "lire.md").write_text("# Script\n", encoding="utf-8")
    return s


def test_noms_des_modules():
    assert pages_doc.module("0-LISEZMOI.md") == "documentation.d0_lisezmoi"
    assert pages_doc.module("etape-2/1-corrections-P1-P3.md") == "documentation.etape_2.d1_corrections_p1_p3"
    assert pages_doc.module("annexes/mesures/an-acteurs.md") == "documentation.annexes.mesures.an_acteurs"
    assert pages_doc.module("annexes/mesures") == "documentation.annexes.mesures"
    assert pages_doc.identifiant("Éléments servis") == "elements_servis"
    assert pages_doc.identifiant("import") == "import_"
    assert pages_doc.lien("documentation.etape_2.journal", "documentation.d0_lisezmoi") == "../d0_lisezmoi.html"
    assert pages_doc.lien("documentation", "documentation.annexes.mesures") == "documentation/annexes/mesures.html"


def test_documents_decouverts_dans_l_ordre_du_menu(livrables):
    assert pages_doc.documents(str(livrables)) == [
        "0-LISEZMOI.md", "1-modele.md", "10-suite.md", "etape-2/journal.md", "annexes/mesures/an.md"]
    assert pages_doc.documents(str(livrables / "absent")) == []


def test_ancres_github_vers_pdoc():
    texte = ("# 1. Modèle\n\n## 2.15 — La cadence\n\n## Données servies\n\n## Données servies\n\n"
             "```\n# pas un titre\n```\n\nSouligné\n---\n")
    a = pages_doc.ancres(texte)
    assert a["215--la-cadence"] == "215-la-cadence"            # GitHub → pdoc
    assert a["données-servies"] == "donnees-servies"            # accents
    assert a["données-servies-1"] == "donnees-servies-2"        # doublons : -1 (GitHub), -2 (pdoc)
    assert a["donnees-servies-2"] == "donnees-servies-2"        # l'ancre de pdoc elle-même
    assert a["souligné"] == "souligne"
    assert "pas-un-titre" not in a


def test_ancres_comme_markdown2():
    """`ancre` suit ce que fait markdown2 (celui de pdoc) ; on le vérifie sur des titres variés."""
    markdown2 = pytest.importorskip("markdown2")
    for t in ("2.15 — La cadence", "Données « servies » : l'essai", "`R-COMPOSITION` (bloquant)",
              "Œuvre & co_x", "C1–C7, A1 à A8"):
        assert pages_doc.ancre(t) == markdown2._slugify(t), t


def test_liens_reecrits(livrables):
    textes = {c: (livrables / c).read_text(encoding="utf-8") for c in pages_doc.documents(str(livrables))}
    publies = {c: pages_doc.ancres(t) for c, t in textes.items()}
    t, remarques = pages_doc.relier(textes["0-LISEZMOI.md"], "0-LISEZMOI.md", publies)
    assert "[le modèle](d1_modele.html)" in t
    assert "[la cadence](d1_modele.html#215-la-cadence)" in t
    assert "[les données](d1_modele.html#donnees-servies)" in t
    assert "[la seconde](d1_modele.html#donnees-servies-2)" in t
    assert "[les mesures](annexes/mesures.html)" in t
    assert "[ailleurs](https://exemple.org/a.md)" in t and "[ici](#lisez-moi)" in t
    # Non publié : le texte reste, sans lien.
    assert "les scripts," in t and "annexes/scripts" not in t
    assert "un relevé," in t and "releve.tsv" not in t
    assert " le README." in t and "README.md" not in t
    # Ni le code, ni les blocs, ni les images ne sont touchés.
    assert "`[pas un lien](1-modele.md)`" in t and "[dans un bloc](1-modele.md)" in t
    assert "![image](schema.png)" in t
    assert len(remarques) == 3
    j, _ = pages_doc.relier(textes["etape-2/journal.md"], "etape-2/journal.md", publies)
    assert "[lisez-moi](../d0_lisezmoi.html#lisez-moi)" in j


def test_paquet_ecrit(livrables, tmp_path):
    sortie = tmp_path / "paquet"
    ecrits, remarques = pages_doc.ecrire(str(livrables), str(sortie), commit="abcdef0123456789")
    assert set(ecrits) == {
        "documentation", "documentation.d0_lisezmoi", "documentation.d1_modele",
        "documentation.d10_suite", "documentation.traitement", "documentation.etape_2",
        "documentation.etape_2.journal", "documentation.annexes", "documentation.annexes.mesures",
        "documentation.annexes.mesures.an"}
    assert not list(sortie.rglob("*script*"))
    sys.path.insert(0, str(sortie))
    try:
        for nom in [n for n in sys.modules if n.split(".")[0] == "documentation"]:
            del sys.modules[nom]
        racine = importlib.import_module("documentation")
        # L'ordre du menu : les documents numérotés, le traitement, puis les dossiers (annexes en dernier).
        assert racine.__all__ == ["d0_lisezmoi", "d1_modele", "d10_suite", "traitement", "etape_2", "annexes"]
        assert "(commit `abcdef012345`)" in racine.__doc__
        assert "[1. Modèle](documentation/d1_modele.html)" in racine.__doc__
        assert "](../site/index.html)" in racine.__doc__ and "](empreinte_src.html)" in racine.__doc__
        m = importlib.import_module("documentation.d1_modele")
        assert m.__doc__.startswith("# 1. Modèle\n")
        assert "```mermaid\nflowchart LR" in m.__doc__
        assert m.__doc__.rstrip().endswith("*Repris tel quel de `livrables/1-modele.md`.*")
        assert importlib.import_module("documentation.etape_2").__all__ == ["journal"]
        assert importlib.import_module("documentation.annexes").__all__ == ["mesures"]
        t = importlib.import_module("documentation.traitement")
        assert t.__doc__.startswith("# Le traitement, étape par étape")
    finally:
        sys.path.remove(str(sortie))
        for nom in [n for n in sys.modules if n.split(".")[0] == "documentation"]:
            del sys.modules[nom]


def test_un_livrable_ne_prend_pas_le_nom_du_traitement(livrables, tmp_path):
    (livrables / "traitement.md").write_text("# Autre\n", encoding="utf-8")
    with pytest.raises(ValueError, match="même nom de module"):
        pages_doc.ecrire(str(livrables), str(tmp_path / "paquet"))


def test_sections_pour_la_recherche():
    item = {"fullname": "documentation.d1", "modulename": "documentation.d1", "kind": "module",
            "doc": '<h1 id="t">T</h1><p>intro</p><h2 id="a">A <code>x</code></h2><p>un</p>'
                   '<h3 id="b">B</h3><p>deux</p><h4 id="c">C</h4><p>trois</p>'}
    s = pages_doc.sections(item, "1. Modèle")
    assert s[0]["doc"] == '<h1 id="t">T</h1><p>intro</p>' and s[0]["kind"] == "module"
    assert s[0]["fullname"] == "1. Modèle"
    assert [(x["fullname"], x["qualname"], x["doc"]) for x in s[1:]] == [
        ("1. Modèle › A x", "a", "<p>un</p>"),
        ("1. Modèle › B", "b", '<p>deux</p><h4 id="c">C</h4><p>trois</p>')]
    assert all(x["modulename"] == "documentation.d1" for x in s)


@pytest.fixture(scope="module")
def doc(tmp_path_factory):
    """Toute la documentation, rendue par pdoc, sur une copie des vrais `livrables/` augmentée des
    cas de liens ci-dessus (dans `essai/`)."""
    pytest.importorskip("pdoc")
    base = tmp_path_factory.mktemp("pages")
    source = base / "livrables"
    if os.path.isdir(LIVRABLES):
        shutil.copytree(LIVRABLES, source)
    (source / "zz-essai").mkdir(parents=True)
    (source / "zz-essai" / "liens.md").write_text(
        "# Essai de liens\n\n## 2.15 — Une section\n\n[retour](#215--une-section), "
        "[ailleurs](../zz-essai/liens.md#215--une-section), [le dossier](./), "
        "[un mot rare](autre.md#xylophone-rare).\n", encoding="utf-8")
    (source / "zz-essai" / "autre.md").write_text("# Autre\n\n## Xylophone rare\n\nTexte.\n",
                                                  encoding="utf-8")
    sortie = base / "doc"
    remarques = pages_doc.construire(str(source), str(sortie), commit="0123456789abcdef")
    return sortie, remarques


def test_pages_ecrites_avec_le_code(doc):
    sortie, _ = doc
    for p in ("index.html", "documentation.html", "documentation/traitement.html",
              "empreinte_src.html", "empreinte_src/lecture.html", "search.js",
              "documentation/zz_essai/liens.html"):
        assert (sortie / p).is_file(), p
    assert 'url=./documentation.html' in (sortie / "index.html").read_text(encoding="utf-8")


def test_gabarits(doc):
    sortie, _ = doc
    page = (sortie / "documentation" / "zz_essai" / "liens.html").read_text(encoding="utf-8")
    assert '<html lang="fr">' in page and "<title>Essai de liens — Empreinte politique</title>" in page
    # Le menu commun, avec la page minimale de contrôle servie à côté de doc/.
    assert 'href="../../documentation.html"' in page and 'href="../../empreinte_src.html"' in page
    assert 'href="../../../site/index.html">Page minimale de contrôle' in page
    assert 'placeholder="Rechercher…"' in page
    # Mermaid épinglé à une version exacte ; thème sombre ; pas de bouton « source » pour un document.
    assert re.search(r"mermaid@\d+\.\d+\.\d+/dist/mermaid\.esm\.min\.mjs", page)
    assert "prefers-color-scheme: dark" in page
    assert 'class="view-source-button"' not in page and 'class="modulename"' not in page
    code = (sortie / "empreinte_src" / "lecture.html").read_text(encoding="utf-8")
    assert 'class="view-source-button"' in code and 'href="../../site/index.html"' in code


def test_liens_et_ancres_resolus(doc):
    """Chaque lien relatif d'une page de la documentation (hors `site/` et l'accueil, servis à
    côté) mène à une page écrite, et son ancre à un `id` de cette page."""
    sortie, remarques = doc
    ids: dict = {}

    def ancres(chemin):
        if chemin not in ids:
            ids[chemin] = set(re.findall(r'\bid="([^"]+)"', open(chemin, encoding="utf-8").read()))
        return ids[chemin]

    verifies = 0
    for page in sorted((sortie / "documentation").rglob("*.html")) + [sortie / "documentation.html"]:
        texte = page.read_text(encoding="utf-8")
        main = texte[texte.index('<main class="pdoc">'):texte.index("</main>")]
        for h in re.findall(r'href="([^"]+)"', main):
            if re.match(r"[a-z][a-z0-9+.-]*:", h, re.I):
                continue
            chemin, _, a = h.partition("#")
            cible = os.path.normpath(os.path.join(page.parent, chemin)) if chemin else str(page)
            if os.path.relpath(cible, sortie).startswith(".."):
                assert h.endswith(("site/index.html", "../index.html")), f"{page} : {h}"
                continue
            assert os.path.isfile(cible), f"{page} : {h}"
            if a:
                assert a in ancres(cible), f"{page} : {h}"
            verifies += 1
    assert verifies > 300
    assert not [r for r in remarques if "ancre inconnue" in r]
    liens = (sortie / "documentation" / "zz_essai" / "liens.html").read_text(encoding="utf-8")
    main = liens[liens.index('<main class="pdoc">'):liens.index("</main>")]
    assert main.count('href="#215-une-section"') == 2            # vers soi-même : l'ancre seule
    assert 'href="../zz_essai.html"' in main and 'href="autre.html#xylophone-rare"' in main


def test_mermaid_et_tableaux_rendus(doc):
    sortie, _ = doc
    a = (sortie / "documentation.html").read_text(encoding="utf-8")
    assert "<h2" in a
    if os.path.isfile(os.path.join(LIVRABLES, "6-doc-processus.md")):
        texte = open(os.path.join(LIVRABLES, "6-doc-processus.md"), encoding="utf-8").read()
        p = (sortie / "documentation" / "d6_doc_processus.html").read_text(encoding="utf-8")
        assert p.count('class="mermaid"') == texte.count("```mermaid")
        assert "<table>" in p and "```" not in p


def test_recherche_par_section(doc):
    sortie, _ = doc
    js = (sortie / "search.js").read_text(encoding="utf-8")
    assert "Essai de liens \\u203a 2.15 \\u2014 Une section" in js or "Essai de liens › 2.15 — Une section" in js
    assert "xylophone-rare" in js
    assert "empreinte_src.lecture" in js
