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
    """Des documents rangés par la table (`0-LISEZMOI.md`, `8-recette.md`, le cadrage) et d'autres
    rangés par défaut (`1-modele.md`, `10-suite.md`, le journal, les annexes)."""
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
    (s / "8-recette.md").write_text("# 8. Recette\n", encoding="utf-8")
    (s / "etape-2" / "0-cadrage-et-decisions.md").write_text(
        "# Étape 2 — cadrage\n\nVoir [la seconde](../1-modele.md#données-servies-1) et "
        "[le journal](journal.md#journal) et [l'étape 2](./).\n", encoding="utf-8")
    (s / "etape-2" / "journal.md").write_text(
        "Sans titre en tête.\n\n# Journal\n\nRetour au [lisez-moi](../0-LISEZMOI.md#lisez-moi).\n",
        encoding="utf-8")
    (s / "annexes" / "mesures" / "an.md").write_text("# Mesures AN\n\nUn mot rare : xylophone.\n",
                                                     encoding="utf-8")
    (s / "annexes" / "mesures" / "releve.tsv").write_text("a\tb\n", encoding="utf-8")
    (s / "annexes" / "nouveau.md").write_text("# Une annexe nouvelle\n", encoding="utf-8")
    (s / "annexes" / "scripts" / "lire.md").write_text("# Script\n", encoding="utf-8")
    return s


def test_noms_des_modules():
    m = pages_doc.module
    # Rangés par la table.
    assert m("0-LISEZMOI.md") == "documentation.comprendre.d0_lisezmoi"
    assert m(pages_doc.TRAITEMENT) == "documentation.comprendre.traitement"
    assert m("1-modele-de-donnees.md") == "documentation.conception.d1_modele_de_donnees"
    assert m("5-questions-ouvertes.md") == "documentation.decisions.d5_questions_ouvertes"
    assert m("etape-2/1-corrections-P1-P3.md") == "documentation.decisions.d1_corrections_p1_p3"
    assert m("etape-2/3-rapport-de-mesures.md") == "documentation.mise_en_oeuvre.d3_rapport_de_mesures"
    assert m("annexes/mesures/an-acteurs.md") == "documentation.annexes.mesures.an_acteurs"
    assert m("4-estimations.md") == "documentation.annexes.archives.d4_estimations"
    # Rangés par défaut : selon le dossier.
    assert m("9-nouveau.md") == "documentation.conception.d9_nouveau"
    assert m("etape-2/nouveau.md") == "documentation.mise_en_oeuvre.nouveau"
    assert m("annexes/mesures/senat.md") == "documentation.annexes.mesures.senat"
    assert m("annexes/autre/note.md") == "documentation.annexes.note"
    # Un dossier : la rubrique où vont ses fichiers nouveaux.
    assert m("annexes/mesures") == m("annexes/mesures/") == "documentation.annexes.mesures"
    assert m("etape-2") == "documentation.mise_en_oeuvre" and m("annexes") == "documentation.annexes"
    assert m("") == m(".") == "documentation"
    assert pages_doc.identifiant("Éléments servis") == "elements_servis"
    assert pages_doc.identifiant("import") == "import_"
    assert pages_doc.lien("documentation.mise_en_oeuvre.journal", "documentation.comprendre.d0_lisezmoi") == \
        "../comprendre/d0_lisezmoi.html"
    assert pages_doc.lien("documentation", "documentation.annexes.mesures") == "documentation/annexes/mesures.html"


def test_la_table_du_rangement():
    """Chaque rubrique de `DOCUMENTS` existe, chaque fichier y est une fois, et chacun existe
    encore dans `livrables/` (un fichier renommé doit l'être aussi dans la table)."""
    rubriques = [r for r, _, _ in pages_doc.RUBRIQUES]
    assert len(set(rubriques)) == len(rubriques)
    assert all(r.rpartition(".")[0] in ("", *rubriques) for r in rubriques)
    fichiers = [c for c, _, _ in pages_doc.DOCUMENTS]
    assert len(set(fichiers)) == len(fichiers)
    assert all(r in rubriques for _, r, _ in pages_doc.DOCUMENTS)
    assert all(r in rubriques for _, r in pages_doc.PAR_DEFAUT) and pages_doc.PAR_DEFAUT[-1][0] == ""
    if os.path.isdir(LIVRABLES):
        publies = set(pages_doc.documents(LIVRABLES))
        assert [c for c in fichiers if c != pages_doc.TRAITEMENT and c not in publies] == []


def test_documents_decouverts_dans_l_ordre_du_menu(livrables):
    # Rubrique par rubrique ; dans une rubrique, les documents de la table d'abord (dans son ordre),
    # puis ceux rangés par défaut, dans l'ordre naturel de leur nom (1 avant 10).
    assert pages_doc.documents(str(livrables)) == [
        "0-LISEZMOI.md", "8-recette.md", "1-modele.md", "10-suite.md",
        "etape-2/0-cadrage-et-decisions.md", "etape-2/journal.md", "annexes/nouveau.md",
        "annexes/mesures/an.md"]
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
    # De « Comprendre » vers « Conception », ancres comprises.
    assert "[le modèle](../conception/d1_modele.html)" in t
    assert "[la cadence](../conception/d1_modele.html#215-la-cadence)" in t
    assert "[les données](../conception/d1_modele.html#donnees-servies)" in t
    assert "[la seconde](../conception/d1_modele.html#donnees-servies-2)" in t
    assert "[les mesures](../annexes/mesures.html)" in t
    assert "[ailleurs](https://exemple.org/a.md)" in t and "[ici](#lisez-moi)" in t
    # Non publié : le texte reste, sans lien.
    assert "les scripts," in t and "annexes/scripts" not in t
    assert "un relevé," in t and "releve.tsv" not in t
    assert " le README." in t and "README.md" not in t
    # Ni le code, ni les blocs, ni les images ne sont touchés.
    assert "`[pas un lien](1-modele.md)`" in t and "[dans un bloc](1-modele.md)" in t
    assert "![image](schema.png)" in t
    assert len(remarques) == 3
    # De la mise en œuvre vers « Comprendre » ; des décisions vers la conception et la mise en œuvre : le même dossier
    # `etape-2/` est rangé dans deux rubriques.
    j, _ = pages_doc.relier(textes["etape-2/journal.md"], "etape-2/journal.md", publies)
    assert "[lisez-moi](../comprendre/d0_lisezmoi.html#lisez-moi)" in j
    c, r = pages_doc.relier(textes["etape-2/0-cadrage-et-decisions.md"],
                            "etape-2/0-cadrage-et-decisions.md", publies)
    assert "[la seconde](../conception/d1_modele.html#donnees-servies-2)" in c
    assert "[le journal](../mise_en_oeuvre/journal.html#journal)" in c
    assert "[l'étape 2](../mise_en_oeuvre.html)" in c and r == []
    # Vu depuis une autre page (`de`) : l'introduction d'une rubrique.
    i, _ = pages_doc.relier("Voir [le modèle](1-modele.md#données-servies).", "(intro)", publies,
                            de="documentation.annexes.archives")
    assert i == "Voir [le modèle](../conception/d1_modele.html#donnees-servies)."


def test_paquet_ecrit(livrables, tmp_path):
    sortie = tmp_path / "paquet"
    ecrits, remarques = pages_doc.ecrire(str(livrables), str(sortie), commit="abcdef0123456789")
    assert set(ecrits) == {
        "documentation", "documentation.comprendre", "documentation.comprendre.d0_lisezmoi",
        "documentation.comprendre.traitement", "documentation.conception",
        "documentation.conception.d8_recette", "documentation.conception.d1_modele",
        "documentation.conception.d10_suite", "documentation.decisions",
        "documentation.decisions.d0_cadrage_et_decisions", "documentation.mise_en_oeuvre",
        "documentation.mise_en_oeuvre.journal", "documentation.annexes", "documentation.annexes.nouveau",
        "documentation.annexes.mesures", "documentation.annexes.mesures.an"}
    # Une rubrique sans document (les archives, ici) n'est pas écrite.
    assert "documentation.annexes.archives" not in ecrits
    assert not list(sortie.rglob("*script*"))
    sys.path.insert(0, str(sortie))
    try:
        for nom in [n for n in sys.modules if n.split(".")[0] == "documentation"]:
            del sys.modules[nom]
        imp = importlib.import_module
        racine = imp("documentation")
        # L'ordre du menu : les rubriques ; dans chacune, la table puis les fichiers par défaut.
        assert racine.__all__ == ["comprendre", "conception", "decisions", "mise_en_oeuvre", "annexes"]
        assert imp("documentation.comprendre").__all__ == ["d0_lisezmoi", "traitement"]
        assert imp("documentation.conception").__all__ == ["d8_recette", "d1_modele", "d10_suite"]
        assert imp("documentation.annexes").__all__ == ["mesures", "nouveau"]
        assert imp("documentation.annexes.mesures").__all__ == ["an"]
        assert "(commit `abcdef012345`)" in racine.__doc__
        # La page d'entrée : les rubriques, avec le titre du menu, et le code avant les annexes.
        d = racine.__doc__
        assert "[Présentation](documentation/comprendre/d0_lisezmoi.html) — `livrables/0-LISEZMOI.md`" in d
        assert "[1. Modèle](documentation/conception/d1_modele.html)" in d
        assert "    - [Mesures AN](documentation/annexes/mesures/an.html)" in d
        assert (d.index("## Comprendre") < d.index("## Conception") < d.index("## Décisions")
                < d.index("## Mise en œuvre") < d.index("## Le code")
                < d.index("## Annexes et archives"))
        assert "](empreinte_src.html)" in d and "site/index.html" not in d
        # Une rubrique : un titre, une introduction, ses documents.
        c = imp("documentation.conception").__doc__
        assert c.startswith("# Conception\n\n") and "[8. Recette](conception/d8_recette.html)" in c
        m = imp("documentation.conception.d1_modele")
        assert m.__doc__.startswith("# 1. Modèle\n")
        assert "```mermaid\nflowchart LR" in m.__doc__
        assert m.__doc__.rstrip().endswith("*Repris tel quel de `livrables/1-modele.md`.*")
        t = imp("documentation.comprendre.traitement")
        assert t.__doc__.startswith("# Le traitement, étape par étape")
        assert "](../../empreinte_src.html)" in t.__doc__
    finally:
        sys.path.remove(str(sortie))
        for nom in [n for n in sys.modules if n.split(".")[0] == "documentation"]:
            del sys.modules[nom]


def test_paquet_sans_livrables(tmp_path):
    ecrits, _ = pages_doc.ecrire(str(tmp_path / "absent"), str(tmp_path / "paquet"))
    assert set(ecrits) == {"documentation", "documentation.comprendre",
                           "documentation.comprendre.traitement"}
    assert "Aucun document" in (tmp_path / "paquet" / "documentation" / "__init__.py").read_text(
        encoding="utf-8")


def test_titres_du_menu(livrables):
    textes = {c: (livrables / c).read_text(encoding="utf-8") for c in pages_doc.documents(str(livrables))}
    t = pages_doc.titres_menu(textes)
    assert t["documentation.comprendre.d0_lisezmoi"] == "Présentation"       # titre de la table
    assert t["documentation.conception.d1_modele"] == "1. Modèle"            # titre du document
    assert t["documentation.mise_en_oeuvre.journal"] == "Journal"
    assert t["documentation.mise_en_oeuvre"] == "Mise en œuvre"
    assert t["documentation"] == "Documentation"


def test_un_livrable_ne_prend_pas_le_nom_d_une_rubrique(livrables, tmp_path):
    (livrables / "annexes" / "mesures.md").write_text("# Autre\n", encoding="utf-8")
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
    for p in ("index.html", "documentation.html", "documentation/comprendre/traitement.html",
              "documentation/comprendre/d0_lisezmoi.html", "documentation/conception.html",
              "empreinte_src.html", "empreinte_src/lecture.html", "search.js",
              "documentation/conception/liens.html"):
        assert (sortie / p).is_file(), p
    assert 'url=./documentation.html' in (sortie / "index.html").read_text(encoding="utf-8")


def _nav(page) -> str:
    texte = page.read_text(encoding="utf-8")
    return texte[texte.index('<nav class="pdoc">'):texte.index("</nav>")]


def test_gabarits(doc):
    sortie, _ = doc
    page = (sortie / "documentation" / "conception" / "liens.html").read_text(encoding="utf-8")
    assert '<html lang="fr">' in page and "<title>Essai de liens — Empreinte politique</title>" in page
    # Le menu commun, avec la page minimale de contrôle servie à côté de doc/.
    menu = re.findall(r'<a href="([^"]+)">([^<]+)</a>', page[page.index('class="menu-global"'):
                                                            page.index("</ul>")])
    assert menu == [("../../documentation.html", "Documentation"),
                    ("../../documentation/comprendre/traitement.html", "Le traitement, étape par étape"),
                    ("../../empreinte_src.html", "Le code"),
                    ("../../../site/index.html", "Page minimale de contrôle"),
                    ("../../../index.html", "Accueil")]
    assert 'placeholder="Rechercher…"' in page
    # Mermaid épinglé à une version exacte ; thème sombre ; pas de bouton « source » pour un document.
    assert re.search(r"mermaid@\d+\.\d+\.\d+/dist/mermaid\.esm\.min\.mjs", page)
    assert "prefers-color-scheme: dark" in page
    assert 'class="view-source-button"' not in page and 'class="modulename"' not in page
    code = (sortie / "empreinte_src" / "lecture.html").read_text(encoding="utf-8")
    assert 'class="view-source-button"' in code and 'href="../../site/index.html"' in code
    assert 'href="../documentation/comprendre/traitement.html"' in code
    # Le titre du menu, pas celui du document, dans l'onglet et dans la liste de la rubrique.
    lisez = (sortie / "documentation" / "comprendre" / "d0_lisezmoi.html").read_text(encoding="utf-8")
    assert "<title>Présentation — Empreinte politique</title>" in lisez
    assert ">Présentation</a>" in _nav(sortie / "documentation" / "comprendre.html")


def test_menu_de_la_page_d_entree(doc):
    """La barre latérale de la page d'entrée : toutes les rubriques et leurs documents, dans
    l'ordre voulu, le code avant les annexes ; pas de sommaire qui redirait la même chose."""
    sortie, _ = doc
    nav = _nav(sortie / "documentation.html")
    arbre = nav[nav.index("<h2>Rubriques</h2>"):]
    titres = [re.sub(r"\s+", " ", t).strip() for t in re.findall(r"<a [^>]*>([^<]+)</a>", arbre)]
    attendu = ["Comprendre", "Présentation", "Le traitement, étape par étape",
               "Conception", "1. Modèle de données", "2. Processus de collecte et de publication",
               "3. Justification des choix", "8. Recette",
               "Décisions", "Cadrage et décisions de la propriétaire", "5. Questions ouvertes",
               "Corrections P1 à P3",
               "Mise en œuvre", "Journal des changements", "Rapport de mesures",
               "Migration vers le vrai dépôt",
               "Le code (empreinte_src)",
               "Annexes et archives", "Mesures de l&#39;étape 1"]
    if os.path.isdir(LIVRABLES):
        # Les fichiers nouveaux (ici `zz-essai/`) se rangent dans la conception, après la table.
        attendu[8:8] = ["Autre", "Essai de liens"]
        assert titres[:len(attendu)] == attendu
        i = titres.index("Archives : documents remplacés")
        assert titres[i + 1:i + 4] == ["4. Estimations chiffrées", "6. Le processus, expliqué",
                                       "7. Le modèle de données, expliqué"]
    assert "<h2>Sommaire</h2>" not in nav
    assert "<h2>Sommaire</h2>" not in _nav(sortie / "documentation" / "annexes.html")
    assert "<h2>Sommaire</h2>" in _nav(sortie / "documentation" / "conception" / "liens.html")


def test_liens_et_ancres_resolus(doc):
    """Chaque lien relatif d'une page de la documentation, menu compris (hors `site/` et l'accueil,
    servis à côté), mène à une page écrite, et son ancre à un `id` de cette page."""
    sortie, remarques = doc
    ids: dict = {}

    def ancres(chemin):
        if chemin not in ids:
            ids[chemin] = set(re.findall(r'\bid="([^"]+)"', open(chemin, encoding="utf-8").read()))
        return ids[chemin]

    verifies = 0
    for page in sorted((sortie / "documentation").rglob("*.html")) + [sortie / "documentation.html"]:
        texte = page.read_text(encoding="utf-8")
        nav_main = _nav(page) + texte[texte.index('<main class="pdoc">'):texte.index("</main>")]
        for h in re.findall(r'href="([^"]+)"', nav_main):
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
    liens = (sortie / "documentation" / "conception" / "liens.html").read_text(encoding="utf-8")
    main = liens[liens.index('<main class="pdoc">'):liens.index("</main>")]
    assert main.count('href="#215-une-section"') == 2            # vers soi-même : l'ancre seule
    assert 'href="../conception.html"' in main and 'href="autre.html#xylophone-rare"' in main


def test_mermaid_et_tableaux_rendus(doc):
    sortie, _ = doc
    a = (sortie / "documentation.html").read_text(encoding="utf-8")
    assert "<h2" in a
    for c in ("1-modele-de-donnees.md", "2-processus-collecte-publication.md"):
        if os.path.isfile(os.path.join(LIVRABLES, c)):
            texte = open(os.path.join(LIVRABLES, c), encoding="utf-8").read()
            p = (sortie / pages_doc.page(pages_doc.module(c))).read_text(encoding="utf-8")
            assert p.count('class="mermaid"') == texte.count("```mermaid") > 0, c
            assert "<table>" in p and "```" not in p


def test_recherche_par_section(doc):
    sortie, _ = doc
    js = (sortie / "search.js").read_text(encoding="utf-8")
    assert "Essai de liens \\u203a 2.15 \\u2014 Une section" in js or "Essai de liens › 2.15 — Une section" in js
    assert "xylophone-rare" in js
    assert "empreinte_src.lecture" in js
    if os.path.isdir(LIVRABLES):
        assert "Pr\\u00e9sentation" in js or "Présentation" in js
