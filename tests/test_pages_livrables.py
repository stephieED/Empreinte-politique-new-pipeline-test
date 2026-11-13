"""Documents de conception (`livrables/`) en HTML pour Pages (`empreinte_src.pages_livrables`) :
sur un petit dossier écrit ici, sans réseau."""
import pytest

pytest.importorskip("markdown2")

from empreinte_src import pages_livrables  # noqa: E402


@pytest.fixture
def livrables(tmp_path):
    s = tmp_path / "livrables"
    (s / "etape-2").mkdir(parents=True)
    (s / "annexes" / "mesures").mkdir(parents=True)
    (s / "annexes" / "scripts").mkdir(parents=True)
    (s / "0-LISEZMOI.md").write_text(
        "# Lisez-moi\n\nVoir [le modèle](1-modele.md), [une section](1-modele.md#les-tables), "
        "[les mesures](annexes/mesures/), [les scripts](annexes/scripts/), "
        "[un relevé](annexes/mesures/releve.tsv), [ailleurs](https://exemple.org/a.md) et "
        "[ici](#lisez-moi).\n", encoding="utf-8")
    (s / "1-modele.md").write_text(
        "# 1. Modèle\n\n## Les tables\n\n| A | B |\n| --- | --- |\n| x | y |\n\n"
        "```sql\nSELECT 1;\n```\n", encoding="utf-8")
    (s / "etape-2" / "journal.md").write_text(
        "Sans titre en tête.\n\n# Journal\n\nRetour au [lisez-moi](../0-LISEZMOI.md).\n",
        encoding="utf-8")
    (s / "annexes" / "mesures" / "an.md").write_text("# Mesures AN\n", encoding="utf-8")
    (s / "annexes" / "mesures" / "releve.tsv").write_text("a\tb\n", encoding="utf-8")
    (s / "annexes" / "scripts" / "lire.md").write_text("# Script\n", encoding="utf-8")
    return s


def test_arborescence_gardee_sans_les_scripts(livrables, tmp_path):
    sortie = tmp_path / "sortie"
    pages_livrables.convertir(str(livrables), str(sortie))
    ecrits = sorted(p.relative_to(sortie).as_posix() for p in sortie.rglob("*") if p.is_file())
    assert ecrits == ["0-LISEZMOI.html", "1-modele.html", "annexes/mesures/an.html",
                      "etape-2/journal.html", "index.html"]


def test_liens_reecrits(livrables, tmp_path):
    sortie = tmp_path / "sortie"
    pages_livrables.convertir(str(livrables), str(sortie))
    p = (sortie / "0-LISEZMOI.html").read_text(encoding="utf-8")
    assert 'href="1-modele.html"' in p and 'href="1-modele.html#les-tables"' in p
    assert '<a href="index.html">les mesures</a>' in p          # dossier publié : l'index
    assert "les scripts" in p and "annexes/scripts" not in p      # non publié : texte sans lien
    assert "un relevé" in p and "releve.tsv" not in p
    assert 'href="https://exemple.org/a.md"' in p and 'href="#lisez-moi"' in p
    assert ".md\"" not in p.replace("https://exemple.org/a.md\"", "")
    j = (sortie / "etape-2" / "journal.html").read_text(encoding="utf-8")
    assert 'href="../0-LISEZMOI.html"' in j
    assert 'href="../index.html">Documents de conception' in j and 'href="../../index.html"' in j


def test_extras_et_style(livrables, tmp_path):
    sortie = tmp_path / "sortie"
    pages_livrables.convertir(str(livrables), str(sortie))
    m = (sortie / "1-modele.html").read_text(encoding="utf-8")
    assert "<div class=\"defile\"><table>" in m and "<td>y</td>" in m      # tables
    assert 'id="les-tables"' in m                                           # header-ids
    assert "<pre" in m and "SELECT" in m and "```" not in m                # fenced-code-blocks
    assert "<title>1. Modèle</title>" in m and "prefers-color-scheme: dark" in m
    assert 'name="viewport"' in m and "<script" not in m


def test_index_avec_les_titres(livrables, tmp_path):
    sortie = tmp_path / "sortie"
    pages_livrables.convertir(str(livrables), str(sortie))
    i = (sortie / "index.html").read_text(encoding="utf-8")
    assert '<a href="0-LISEZMOI.html">Lisez-moi</a>' in i
    assert '<a href="etape-2/journal.html">Journal</a>' in i             # premier « # », pas la 1re ligne
    assert '<a href="annexes/mesures/an.html">Mesures AN</a>' in i
    assert "Script" not in i
    assert i.index("<code>livrables/</code>") < i.index("<code>livrables/annexes/mesures/</code>")


def test_sans_dossier_rien_n_est_ecrit(tmp_path, capsys):
    sortie = tmp_path / "sortie"
    assert pages_livrables.convertir(str(tmp_path / "absent"), str(sortie)) == []
    assert not sortie.exists()
    pages_livrables.main([str(tmp_path / "absent"), str(sortie)])
    assert "rien à publier" in capsys.readouterr().out
