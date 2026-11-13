"""Budget tenu pendant la copie, budget propre à un point, hôte suspendu (issue #37)."""
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from empreinte_src.transport import Transport

TAILLE = 200_000


class Goutte(BaseHTTPRequestHandler):
    """Serveur au compte-gouttes : 1 000 octets toutes les 20 ms, jamais 60 s de silence."""
    def log_message(self, *a):
        pass

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Length", str(TAILLE))
        self.send_header("ETag", '"g"')
        self.end_headers()
        try:
            for _ in range(TAILLE // 1000):
                self.wfile.write(b"x" * 1000)
                self.wfile.flush()
                time.sleep(0.02)
        except (BrokenPipeError, ConnectionResetError):
            pass


class Panne(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        self.send_response(500)
        self.send_header("Content-Length", "0")
        self.end_headers()


def _serveur(gestion):
    s = ThreadingHTTPServer(("127.0.0.1", 0), gestion)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s


@pytest.fixture
def goutte():
    s = _serveur(Goutte)
    yield f"http://127.0.0.1:{s.server_port}"
    s.shutdown()


@pytest.fixture
def panne():
    s = _serveur(Panne)
    yield f"http://127.0.0.1:{s.server_port}"
    s.shutdown()


def test_budget_tenu_pendant_la_copie(goutte, tmp_path):
    """Avant : le budget n'était vérifié qu'entre deux essais ; un serveur lent retenait la
    collecte jusqu'à la limite de la tâche (≈ 4 s ici, des heures en vrai)."""
    t = Transport("test", pauses=(0,), delai_s=5, dossier_tmp=str(tmp_path), pause_reprise_s=0, budget_s=0.5)
    debut = time.monotonic()
    r = t.telecharger(goutte + "/lent.zip")
    assert r.issue == "echec" and time.monotonic() - debut < 2.5
    assert "budget de 0 s dépassé" in r.message
    assert 0 < r.octets_recus < TAILLE
    # Un transfert lent mais vivant ne compte pas comme un hôte en panne.
    assert sum(t.echecs_hote.values()) == 0


def test_budget_propre_a_un_point(goutte, tmp_path):
    t = Transport("test", pauses=(0,), delai_s=5, dossier_tmp=str(tmp_path), pause_reprise_s=0, budget_s=0.3,
                  budgets_par_url={goutte + "/archive-close.zip": 30})
    assert t.telecharger(goutte + "/court.zip").issue == "echec"           # budget commun : 0,3 s
    r = t.telecharger(goutte + "/archive-close.zip")                        # son budget : 30 s
    assert r.issue == "nouveau" and r.taille == TAILLE


def test_hote_en_panne_suspendu(panne, tmp_path):
    """Un hôte qui répond 500 à tout : après 3 points sans un octet, les suivants échouent sans
    attendre (en vrai : 35 points × 750 s de pauses)."""
    appels = []
    t = Transport("test", pauses=(0, 0), delai_s=5, dossier_tmp=str(tmp_path), pause_reprise_s=0)
    vrai_get = t.session.get

    def get(*a, **k):
        appels.append(a[0])
        return vrai_get(*a, **k)
    t.session.get = get
    reps = [t.telecharger(f"{panne}/p{k}.zip") for k in range(6)]
    assert [r.issue for r in reps] == ["echec"] * 6
    assert len(appels) == 3 * 3                       # 3 points × 3 tentatives, puis plus rien
    assert "suspendu" in reps[3].message and "suspendu" in reps[5].message


def test_fin_de_collecte_atteinte(goutte, tmp_path):
    """Issue #38 : passée l'échéance de la collecte, le fichier en cours s'arrête et les suivants
    ne sont pas relevés ; la collecte se termine d'elle-même au lieu d'être coupée par GitHub."""
    t = Transport("test", pauses=(0,), delai_s=5, dossier_tmp=str(tmp_path), pause_reprise_s=0,
                  budget_s=60, fin_collecte=time.monotonic() + 0.4)
    debut = time.monotonic()
    r1 = t.telecharger(goutte + "/a.zip")
    r2 = t.telecharger(goutte + "/b.zip")
    assert time.monotonic() - debut < 2.5
    assert r1.issue == "echec" and "durée maximale de la collecte atteinte" in r1.message
    assert r2.issue == "echec" and r2.tentatives == 0 and "point non relevé" in r2.message
