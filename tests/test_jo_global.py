"""Archive globale du Journal officiel (décision du 13/11/2026) : relevée une fois, gardée à
l'octet à part, découpée depuis la XIVe seulement."""
import io
import json
import os
import shutil
import subprocess
import tarfile

from empreinte_src import distant
from empreinte_src.collecte import relever_archive_globale
from empreinte_src.depaquetage import depaqueter_tar_flux
from empreinte_src.entrepot import Entrepot
from empreinte_src.transport import Reponse

NOM = "Freemium_jorf_global_20261108-140000.tar.gz"
PA = {"id": "jo-global", "source": "dila", "type": "jorf", "url": "https://exemple.invalid/JORF/",
      "format": "archive_globale", "motif": r"^Freemium_jorf_global_\d{8}-\d{6}\.tar\.gz$",
      "qualifier_uid": r"^\d{8}-\d{6}/jorf/global/(?P<q>.+?)/JORF/", "depuis": "2012-06-20",
      "licence": "etalab-2.0"}
FICHIERS = {
    "jorf/global/texte/version/JORF/TEXT/00/00/JORFTEXT000000000001.xml": "2011-05-01",   # avant
    "jorf/global/texte/version/JORF/TEXT/00/00/JORFTEXT000000000002.xml": "2013-03-01",
    "jorf/global/texte/struct/JORF/TEXT/00/00/JORFTEXT000000000002.xml": "2013-03-01",
    "jorf/global/conteneur/JORF/CONT/00/00/JORFCONT000000000003.xml": "2013-03-01",
    "jorf/global/article/JORF/ARTI/00/00/JORFARTI000000000004.xml": "2013-03-01",          # non lu
}


def _archive(chemin):
    with tarfile.open(chemin, "w:gz") as t:
        for nom, date in FICHIERS.items():
            octets = f"<X><DATE_PUBLI>{date}</DATE_PUBLI></X>".encode()
            i = tarfile.TarInfo(nom)
            i.size = len(octets)
            t.addfile(i, io.BytesIO(octets))


class Faux:
    def __init__(self, source):
        self.source, self.appels = source, 0

    def texte(self, url):
        return 200, f'<a href="{NOM}">x</a><a href="JORF_20261113-010101.tar.gz">y</a>', {}

    def telecharger(self, url, etag=None, last_modified=None):
        self.appels += 1
        c = self.source + ".recu"
        shutil.copy(self.source, c)
        return Reponse(url=url, issue="nouveau", statut_http=200, chemin=c, taille=os.path.getsize(c))


def test_flux_filtre_et_prefixe(tmp_path):
    a = str(tmp_path / NOM)
    _archive(a)
    m = list(depaqueter_tar_flux(a, lambda c, o: "/version/" in c, "20261108-140000/"))
    assert [x.chemin for x in m] == ["20261108-140000/" + k for k in FICHIERS if "/version/" in k]


def test_relevee_une_fois_gardee_a_l_octet_decoupee_depuis_la_xive(tmp_path):
    a = str(tmp_path / NOM)
    _archive(a)
    e = Entrepot(str(tmp_path / "e"))
    t = Faux(a)
    r = relever_archive_globale(e, t, PA, {})
    assert r["issue"] == "nouveau" and r["nb_membres"] == 3 and r["curseur"] == NOM
    assert r["archive_brute"] == f"brutes/{NOM}"
    with open(a, "rb") as f1, open(tmp_path / "e" / "brutes" / NOM, "rb") as f2:
        assert f1.read() == f2.read()                          # à l'octet
    chemins = sorted(x["chemin"] for x in e._membres)
    assert all(c.startswith("20261108-140000/jorf/global/") for c in chemins)
    assert not any("article" in c or "000000000001" in c for c in chemins)
    e.enregistrer_releve(r)
    man = e.clore("essai")
    assert f"brutes/{NOM}" in man["fichiers"]
    r2 = relever_archive_globale(e, t, PA, {})
    assert r2["issue"] == "inchange" and t.appels == 1           # une seule fois


def test_archive_brute_dans_sa_release_et_jamais_restauree(tmp_path, monkeypatch):
    appels = []

    def faux_gh(*args, capture=True, check=True):
        appels.append(args)
        rc = 1 if args[:2] == ("release", "download") and "manifeste.json" in args else 0
        return subprocess.CompletedProcess(args, rc, "", "release not found")
    monkeypatch.setattr(distant, "_gh", faux_gh)
    d = tmp_path / "e"
    (d / "brutes").mkdir(parents=True)
    (d / "brutes" / NOM).write_bytes(b"x")
    (d / "index.parquet").write_bytes(b"y")
    man = {"generation": 1, "base": 0, "fichiers": {
        f"brutes/{NOM}": {"sha256": "a", "taille": 1}, "index.parquet": {"sha256": "b", "taille": 1}}}
    (d / "manifeste.json").write_text(json.dumps(man))
    distant.publier("o/d", str(d))
    envois = {a[3].rsplit("/", 1)[-1]: a[2] for a in appels if a[:2] == ("release", "upload")}
    assert envois[f"brutes__{NOM}"] == "archives-brutes" and envois["index.parquet"] == "entrepot"
    assert distant._release_de("blobs/x") == "entrepot"
