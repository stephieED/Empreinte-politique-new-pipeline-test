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
    for n in ("faits.parquet", "faits-publies.parquet"):
        (tmp_path / n).write_bytes(b"x")
    r = distant.publier_export("o/d", str(tmp_path), 3)
    assert _envois(appels) == [("export", "faits-g000003.parquet"), ("export", "faits-publies-g000003.parquet")]
    assert {x["release"] for x in r} == {"export"}


def test_export_de_tous_les_faits_derniere_nuit_seulement(tmp_path, monkeypatch):
    """Décision du 12/11/2026 : l'export de tous les faits lus n'est gardé que pour la dernière nuit
    (Parquet seul) ; les faits publiés de chaque nuit restent tous."""
    import json
    appels = []
    actifs = ["faits-g000006.parquet", "faits-g000006.csv.gz", "faits-g000008.parquet", "faits-g000008.csv.gz",
              "faits-publies-g000006.parquet", "faits-publies-g000008.parquet", "faits-g000009.parquet"]

    def faux_gh(*args, capture=True, check=True):
        appels.append(args)
        sortie = json.dumps({"assets": [{"name": n} for n in actifs]}) if "--json" in args else ""
        return subprocess.CompletedProcess(args, 0, sortie, "")
    monkeypatch.setattr(distant, "_gh", faux_gh)
    for n in ("faits.parquet", "faits-publies.parquet"):
        (tmp_path / n).write_bytes(b"x")
    distant.publier_export("o/d", str(tmp_path), 9)
    retires = sorted(a[3] for a in appels if a[:2] == ("release", "delete-asset"))
    assert retires == ["faits-g000006.csv.gz", "faits-g000006.parquet", "faits-g000008.csv.gz",
                       "faits-g000008.parquet"]
    assert all(a[2] == "export" for a in appels if a[:2] == ("release", "delete-asset"))


def test_export_echoue_rien_n_est_retire(tmp_path, monkeypatch):
    appels = []

    def faux_gh(*args, capture=True, check=True):
        appels.append(args)
        rc = 1 if args[:2] == ("release", "upload") else 0
        return subprocess.CompletedProcess(args, rc, "", "refusé")
    monkeypatch.setattr(distant, "_gh", faux_gh)
    monkeypatch.setattr(distant.time, "sleep", lambda s: None)
    (tmp_path / "faits.parquet").write_bytes(b"x")
    distant.publier_export("o/d", str(tmp_path), 9)
    assert not any(a[:2] == ("release", "delete-asset") for a in appels)


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


def test_derniere_publication_reussie(monkeypatch):
    """La base des contrôles de pertes est la dernière publication réussie, même si la nuit
    précédente a été refusée (générations 5 et 7 absentes)."""
    import json
    noms = ["faits-g000004.parquet", "faits-publies-g000002.parquet", "faits-publies-g000006.parquet",
            "faits-publies-g000004.parquet", "site-g000008.tar.gz"]

    def faux_gh(*args, capture=True, check=True):
        return subprocess.CompletedProcess(args, 0, json.dumps({"assets": [{"name": n} for n in noms]}), "")
    monkeypatch.setattr(distant, "_gh", faux_gh)
    assert distant.derniere_publication("o/d") == "faits-publies-g000006.parquet"
