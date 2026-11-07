"""Chaque écriture va dans sa release : entrepôt, export, publication (défaut corrigé le
06/11/2026 : l'export et l'archive du site étaient déposés dans `entrepot`)."""
import subprocess

from empreinte_src import distant


def _espion(monkeypatch):
    appels = []

    def faux_gh(*args, capture=True, check=True):
        appels.append(args)
        return subprocess.CompletedProcess(args, 0, "", "")
    monkeypatch.setattr(distant, "_gh", faux_gh)
    return appels


def _envois(appels):
    return [(a[2], a[3].rsplit("/", 1)[-1]) for a in appels if a[:2] == ("release", "upload")]


def test_export_dans_la_release_export(tmp_path, monkeypatch):
    appels = _espion(monkeypatch)
    for n in ("faits.parquet", "faits.csv.gz", "faits-publies.parquet"):
        (tmp_path / n).write_bytes(b"x")
    r = distant.publier_export("o/d", str(tmp_path), 3)
    assert _envois(appels) == [("export", "faits-g000003.parquet"), ("export", "faits-g000003.csv.gz"),
                               ("export", "faits-publies-g000003.parquet")]
    assert {x["release"] for x in r} == {"export"}


def test_site_dans_la_release_publication(tmp_path, monkeypatch):
    appels = _espion(monkeypatch)
    (tmp_path / "site").mkdir()
    (tmp_path / "site" / "index.html").write_text("ok")
    distant.publier_site("o/d", str(tmp_path / "site"), 3)
    assert _envois(appels) == [("publication", "site-g000003.tar.gz")]


def test_entrepot_par_defaut(tmp_path, monkeypatch):
    appels = _espion(monkeypatch)
    (tmp_path / "f").write_bytes(b"x")
    distant._envoyer("o/d", str(tmp_path / "f"), "f")
    assert _envois(appels) == [("entrepot", "f")]
