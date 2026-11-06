"""Correction P2 : le contenu exact d'une archive reçue se retrouve dans l'entrepôt."""
import hashlib
import zipfile

from empreinte.depaquetage import depaqueter
from empreinte.entrepot import Entrepot


def test_archive_reconstruite_a_l_octet_pres(tmp_path, extrait_agenda, pa_agenda):
    e = Entrepot(str(tmp_path / "e"))
    e.versionner(pa_agenda, "R1", depaqueter(extrait_agenda, "zip"), complet=True)
    e.clore("test")
    e2 = Entrepot(str(tmp_path / "e"))           # relu depuis le disque
    membres = e2.membres_du_releve("R1")
    with zipfile.ZipFile(extrait_agenda) as z:
        origine = {i.filename: z.read(i) for i in z.infolist()}
    assert {m["chemin"] for m in membres} == set(origine)
    lus = e2.lire_plusieurs(m["empreinte"] for m in membres)
    for m in membres:
        octets = lus[m["empreinte"]]
        assert octets == origine[m["chemin"]]
        assert hashlib.sha256(octets).hexdigest() == m["empreinte"]


def test_gros_membre_range_en_morceaux(tmp_path, pa_agenda):
    from tests.conftest import zip_avec
    gros = bytes(range(256)) * 5000                # 1,28 Mo
    z = zip_avec(str(tmp_path / "a.zip"), {"json/X1.json": gros})
    e = Entrepot(str(tmp_path / "e"), morceau_max=100_000)
    e.versionner(pa_agenda, "R1", depaqueter(z, "zip"), complet=True)
    e.clore("test")
    assert Entrepot(str(tmp_path / "e")).lire_octets(hashlib.sha256(gros).hexdigest()) == gros
