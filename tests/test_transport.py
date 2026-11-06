"""Transferts coupés avec un statut 200, reprise par If-Range, 304 (doc. 2, 2.2).

Un serveur local imite les comportements mesurés sur l'Assemblée le 04/11/2026."""
import hashlib
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from empreinte.transport import Transport

V1 = bytes(range(256)) * 400        # 102 400 octets
V2 = bytes(reversed(range(256))) * 400


class Etat:
    contenu = V1
    etag = '"v1"'
    couper_au = None          # couper le premier envoi complet à cet octet
    changer_apres_coupure = False
    sans_etag = False
    requetes = []


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
        if rng and if_range == Etat.etag:
            debut = int(rng.split("=")[1].rstrip("-"))
            corps = Etat.contenu[debut:]
            self.send_response(206)
            self.send_header("Content-Length", str(len(corps)))
            self.send_header("ETag", Etat.etag)
            self.end_headers()
            self.wfile.write(corps)
            return
        self.send_response(200)
        self.send_header("Content-Length", str(len(Etat.contenu)))
        if not Etat.sans_etag:
            self.send_header("ETag", Etat.etag)
        self.end_headers()
        if Etat.couper_au:
            self.wfile.write(Etat.contenu[:Etat.couper_au])
            Etat.couper_au = None
            if Etat.changer_apres_coupure:      # un autre serveur sert une autre version
                Etat.contenu, Etat.etag = V2, '"v2"'
            self.wfile.flush()
            self.connection.close()
            return
        self.wfile.write(Etat.contenu)


@pytest.fixture
def serveur():
    Etat.contenu, Etat.etag, Etat.couper_au = V1, '"v1"', None
    Etat.changer_apres_coupure, Etat.sans_etag, Etat.requetes = False, False, []
    s = ThreadingHTTPServer(("127.0.0.1", 0), Gestion)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{s.server_port}/a.zip"
    s.shutdown()


def _t(tmp_path):
    return Transport("test", pauses=(0, 0), delai_s=5, dossier_tmp=str(tmp_path))


def test_coupure_a_200_reprise_par_if_range(serveur, tmp_path):
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
    t = Transport("test", pauses=(), delai_s=5, dossier_tmp=str(tmp_path))
    rep = t.telecharger(serveur)
    assert rep.issue == "echec" and "coupé" in rep.message


def test_304_ne_telecharge_rien(serveur, tmp_path):
    rep = _t(tmp_path).telecharger(serveur, etag='"v1"')
    assert rep.issue == "inchange" and rep.octets_recus == 0
