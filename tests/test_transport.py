"""Transferts coupés avec un statut 200, reprise par plages vérifiée, 304 (doc. 2, 2.2).

Un serveur local imite les comportements mesurés sur l'Assemblée le 04/11/2026."""
import hashlib
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from empreinte_src.transport import Transport

V1 = bytes(range(256)) * 400        # 102 400 octets
V2 = bytes(reversed(range(256))) * 400


class Etat:
    contenu = V1
    etag = '"v1"'
    couper_au = None          # couper le premier envoi complet à cet octet
    changer_apres_coupure = False
    sans_etag = False
    requetes = []
    couper_chaque = None      # couper chaque réponse (206 comprises) après ce nombre d'octets
    fermer_reprises = 0       # fermer la connexion sans répondre aux n prochaines reprises
    ignorer_plage = False     # serveur (ou relais) qui ignore Range : renvoie 200 entier
    plage_vide = False        # 206 annoncé, puis rien (mesuré sur l'Assemblée, plage à 300 Mo)


class Gestion(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        Etat.requetes.append(dict(self.headers))
        if self.headers.get("If-None-Match") == Etat.etag:
            self.send_response(304)
            self.end_headers()
            return
        rng, if_range = self.headers.get("Range"), self.headers.get("If-Range")
        if rng and Etat.fermer_reprises:
            Etat.fermer_reprises -= 1
            self.connection.close()
            return
        if rng and not Etat.ignorer_plage and (if_range is None or if_range == Etat.etag):
            debut = int(rng.split("=")[1].rstrip("-"))
            corps = Etat.contenu[debut:]
            self.send_response(206)
            self.send_header("Content-Length", str(len(corps)))
            self.send_header("Content-Range", f"bytes {debut}-{len(Etat.contenu) - 1}/{len(Etat.contenu)}")
            if not Etat.sans_etag:
                self.send_header("ETag", Etat.etag)
            self.end_headers()
            if Etat.plage_vide:
                self.wfile.flush()
                self.connection.close()
                return
            if Etat.couper_chaque:
                self.wfile.write(corps[:Etat.couper_chaque])
                self.wfile.flush()
                self.connection.close()
                return
            self.wfile.write(corps)
            return
        self.send_response(200)
        self.send_header("Content-Length", str(len(Etat.contenu)))
        if not Etat.sans_etag:
            self.send_header("ETag", Etat.etag)
        self.end_headers()
        if Etat.couper_chaque and not rng:
            self.wfile.write(Etat.contenu[:Etat.couper_chaque])
            self.wfile.flush()
            self.connection.close()
            return
        if Etat.couper_au:
            self.wfile.write(Etat.contenu[:Etat.couper_au])
            Etat.couper_au = None
            if Etat.changer_apres_coupure:      # un autre serveur sert une autre version
                Etat.contenu, Etat.etag = V2, '"v2"'
            self.wfile.flush()
            self.connection.close()
            return
        self.wfile.write(Etat.contenu)


@pytest.fixture(autouse=True)
def petits_blocs(monkeypatch):
    """Blocs de 512 octets : à l'échelle des fichiers de test (100 Ko), comme 64 Kio pour
    des archives de centaines de Mo."""
    from empreinte_src import transport
    monkeypatch.setattr(transport, "TAILLE_BLOC", 512)


@pytest.fixture
def serveur():
    Etat.contenu, Etat.etag, Etat.couper_au = V1, '"v1"', None
    Etat.changer_apres_coupure, Etat.sans_etag, Etat.requetes = False, False, []
    Etat.couper_chaque, Etat.fermer_reprises, Etat.ignorer_plage = None, 0, False
    Etat.plage_vide = False
    s = ThreadingHTTPServer(("127.0.0.1", 0), Gestion)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{s.server_port}/a.zip"
    s.shutdown()


def _t(tmp_path):
    return Transport("test", pauses=(0, 0), delai_s=5, dossier_tmp=str(tmp_path), pause_reprise_s=0)


def test_coupure_a_200_reprise_par_plage(serveur, tmp_path):
    Etat.couper_au = 10 * 1024
    rep = _t(tmp_path).telecharger(serveur)
    assert rep.issue == "nouveau" and rep.reprises == 1
    assert open(rep.chemin, "rb").read() == V1
    assert rep.empreinte == hashlib.sha256(V1).hexdigest()


def test_autre_version_servie_pendant_la_reprise(serveur, tmp_path):
    Etat.couper_au, Etat.changer_apres_coupure = 10 * 1024, True
    rep = _t(tmp_path).telecharger(serveur)
    assert rep.issue == "nouveau"
    assert open(rep.chemin, "rb").read() == V2      # jamais un mélange de V1 et V2


def test_coupure_sans_etag_est_un_echec(serveur, tmp_path):
    Etat.sans_etag = True
    Etat.couper_au = 10 * 1024
    t = Transport("test", pauses=(), delai_s=5, dossier_tmp=str(tmp_path), pause_reprise_s=0)
    rep = t.telecharger(serveur)
    assert rep.issue == "echec" and "coupé" in rep.message


def test_304_ne_telecharge_rien(serveur, tmp_path):
    rep = _t(tmp_path).telecharger(serveur, etag='"v1"')
    assert rep.issue == "inchange" and rep.octets_recus == 0


def test_coupures_repetees_reprises_jusqu_au_bout(serveur, tmp_path):
    """Cas des amendements XVe et XVIe depuis GitHub (07/11/2026) : chaque réponse est coupée.
    Chaque reprise ajoute sa part ; le fichier final est exact."""
    Etat.couper_chaque = 7 * 1024
    rep = _t(tmp_path).telecharger(serveur)
    assert rep.issue == "nouveau" and open(rep.chemin, "rb").read() == V1
    assert rep.tentatives == 1 and 14 <= rep.reprises <= 16
    assert rep.journal_reprises[0].startswith("200 +7 Ko") and all(j.startswith("206 +") for j in rep.journal_reprises[1:])


def test_connexion_fermee_pendant_une_reprise_n_est_pas_un_nouveau_depart(serveur, tmp_path):
    Etat.couper_au, Etat.fermer_reprises = 10 * 1024, 2
    rep = _t(tmp_path).telecharger(serveur)
    assert rep.issue == "nouveau" and open(rep.chemin, "rb").read() == V1
    assert rep.tentatives == 1 and rep.journal_reprises[1:3] == ["coupure (ConnectionError)"] * 2


def test_serveur_qui_ignore_la_plage(serveur, tmp_path):
    """Un relais qui renvoie le fichier entier à une demande de plage : départ à zéro avec la
    version servie, jamais un recollage."""
    Etat.couper_au, Etat.ignorer_plage = 10 * 1024, True
    rep = _t(tmp_path).telecharger(serveur)
    assert rep.issue == "nouveau" and open(rep.chemin, "rb").read() == V1
    assert rep.journal_reprises[1:] == ["200 autre version : départ à zéro"]


def test_echec_dit_ce_que_les_reprises_ont_recu(serveur, tmp_path):
    Etat.couper_chaque = 1024
    t = Transport("test", pauses=(), delai_s=5, dossier_tmp=str(tmp_path), reprises_max=3, pause_reprise_s=0)
    rep = t.telecharger(serveur)
    assert rep.issue == "echec" and "reprises : 200 +1 Ko en 0 s (fin à 1 Ko), 206 +1 Ko en 0 s, 206 +1 Ko en 0 s" in rep.message


def test_plages_vides_on_repart_du_debut(serveur, tmp_path):
    """L'Assemblée répond 206 à une plage prise loin, puis n'envoie rien : après trois reprises
    vides, on repart du début, qui avance (07/11/2026)."""
    Etat.couper_au, Etat.plage_vide = 10 * 1024, True
    rep = _t(tmp_path).telecharger(serveur)
    assert rep.issue == "nouveau" and open(rep.chemin, "rb").read() == V1
    assert rep.journal_reprises[-1].startswith("départ du début +100 Ko") and rep.tentatives == 1


def test_budget_de_temps_par_fichier(serveur, tmp_path):
    Etat.couper_chaque = 512
    t = Transport("test", pauses=(0, 0), delai_s=5, dossier_tmp=str(tmp_path), pause_reprise_s=0.05,
                  budget_s=0.3)
    rep = t.telecharger(serveur)
    assert rep.issue == "echec" and "budget de 0 s dépassé" in rep.message



def test_octets_gardes_d_une_mise_a_jour_a_l_autre(serveur, tmp_path):
    """#32 (décision du 14/11/2026) : un transfert coupé laisse son début de côté ; la mise à jour
    suivante, si la source sert la même version, le reprend et ne demande que la suite."""
    Etat.couper_chaque = 30 * 1024
    t = Transport("test", pauses=(), delai_s=5, dossier_tmp=str(tmp_path), reprises_max=0, pause_reprise_s=0,
                  dossier_partiels=str(tmp_path / "partiels"), partiel_min_octets=0)
    r1 = t.telecharger(serveur)
    assert r1.issue == "echec" and len(list((tmp_path / "partiels").glob("*.part"))) == 1
    Etat.couper_chaque = None
    Etat.requetes = []
    t2 = Transport("test", pauses=(), delai_s=5, dossier_tmp=str(tmp_path), pause_reprise_s=0,
                   dossier_partiels=str(tmp_path / "partiels"), partiel_min_octets=0)
    r2 = t2.telecharger(serveur)
    assert r2.issue == "nouveau" and open(r2.chemin, "rb").read() == V1
    assert r2.journal_reprises[0] == "début gardé repris : 30 Ko"
    assert Etat.requetes[-1].get("Range") == f"bytes={30 * 1024}-"         # seule la suite est demandée
    assert not list((tmp_path / "partiels").glob("*.part"))                  # oublié une fois reçu


def test_octets_gardes_d_une_autre_version_ignores(serveur, tmp_path):
    Etat.couper_chaque = 30 * 1024
    kw = dict(pauses=(), delai_s=5, dossier_tmp=str(tmp_path), pause_reprise_s=0,
              dossier_partiels=str(tmp_path / "partiels"), partiel_min_octets=0)
    Transport("test", reprises_max=0, **kw).telecharger(serveur)
    Etat.couper_chaque, Etat.contenu, Etat.etag = None, V2, '"v2"'               # la source a changé
    r = Transport("test", **kw).telecharger(serveur)
    assert r.issue == "nouveau" and open(r.chemin, "rb").read() == V2
    assert not any(j.startswith("début gardé") for j in r.journal_reprises)
