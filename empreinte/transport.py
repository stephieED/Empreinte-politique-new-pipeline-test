"""Téléchargement d'un point d'accès (étape E1).

Ce que ce module garantit (doc. 2, 2.2) :
- requête conditionnelle quand la source le permet (ETag, Last-Modified) : une archive
  inchangée coûte une requête ;
- le fichier reçu est vérifié contre Content-Length : l'Assemblée coupe des transferts en
  renvoyant quand même 200 (mesuré le 04/11/2026) ;
- reprise par segments seulement avec If-Range sur l'ETag : si un autre serveur sert une
  autre version, la réponse est le fichier entier, et l'on repart de zéro au lieu de
  recoller deux versions ;
- chaque octet reçu est compté, reprises comprises (mesure de la commande, section 5).
"""
from __future__ import annotations

import hashlib
import os
import tempfile
import time
from dataclasses import dataclass, field

import requests

TAILLE_BLOC = 1 << 20


@dataclass
class Reponse:
    url: str
    issue: str                    # "nouveau", "inchange", "echec"
    statut_http: int | None = None
    chemin: str | None = None     # fichier reçu (si nouveau)
    taille: int | None = None
    empreinte: str | None = None  # SHA-256 du fichier reçu
    entetes: dict = field(default_factory=dict)
    octets_recus: int = 0         # tout ce qui a transité, reprises comprises
    tentatives: int = 0
    reprises: int = 0
    duree_s: float = 0.0
    message: str = ""


class Transport:
    """Accès HTTP. `pauses` donne l'attente avant chaque nouvelle tentative (doc. 2 : 30 s,
    2 min, 10 min) ; les tests passent des pauses nulles."""

    def __init__(self, user_agent: str, pauses=(30, 120, 600), delai_s: float = 60.0,
                 reprises_max: int = 8, dossier_tmp: str | None = None):
        self.session = requests.Session()
        self.session.headers["User-Agent"] = user_agent
        # Octets bruts : un encodage de transport fausserait la comparaison à Content-Length.
        self.session.headers["Accept-Encoding"] = "identity"
        self.pauses = tuple(pauses)
        self.delai_s = delai_s
        self.reprises_max = reprises_max
        self.dossier_tmp = dossier_tmp

    # -- requêtes simples (listes, API) -------------------------------------------------
    def texte(self, url: str) -> tuple[int, str, dict]:
        r = self.session.get(url, timeout=self.delai_s)
        return r.status_code, r.text, dict(r.headers)

    # -- téléchargement d'un fichier -----------------------------------------------------
    def telecharger(self, url: str, etag: str | None = None,
                    last_modified: str | None = None) -> Reponse:
        rep = Reponse(url=url, issue="echec")
        debut = time.monotonic()
        derniere_erreur = ""
        for essai in range(len(self.pauses) + 1):
            if essai:
                time.sleep(self.pauses[essai - 1])
            rep.tentatives += 1
            try:
                fini = self._un_essai(url, etag, last_modified, rep)
                if fini:
                    rep.duree_s = time.monotonic() - debut
                    return rep
                derniere_erreur = rep.message
            except requests.RequestException as e:
                derniere_erreur = f"{type(e).__name__}: {e}"
        rep.issue = "echec"
        rep.message = derniere_erreur or "échec sans message"
        rep.duree_s = time.monotonic() - debut
        return rep

    def _un_essai(self, url, etag, last_modified, rep: Reponse) -> bool:
        entetes = {}
        if etag:
            entetes["If-None-Match"] = etag
        if last_modified:
            entetes["If-Modified-Since"] = last_modified
        r = self.session.get(url, headers=entetes, stream=True, timeout=self.delai_s)
        rep.statut_http = r.status_code
        rep.entetes = {k.lower(): v for k, v in r.headers.items()}
        if r.status_code == 304:
            r.close()
            rep.issue, rep.message = "inchange", "304"
            return True
        if r.status_code != 200:
            r.close()
            rep.message = f"HTTP {r.status_code}"
            return False

        attendu = _entier(rep.entetes.get("content-length"))
        etag_recu = rep.entetes.get("etag")
        fd, chemin = tempfile.mkstemp(prefix="releve-", dir=self.dossier_tmp)
        try:
            with os.fdopen(fd, "wb") as f:
                rep.octets_recus += _copier(r, f)
                reprises = 0
                while attendu is not None and f.tell() < attendu:
                    # Transfert coupé. Reprise seulement si l'ETag garantit la même version.
                    if not etag_recu or reprises >= self.reprises_max:
                        rep.message = (f"transfert coupé à {f.tell()} octets sur {attendu}"
                                       + ("" if etag_recu else ", sans ETag pour reprendre"))
                        return False
                    reprises += 1
                    rep.reprises += 1
                    rr = self.session.get(url, stream=True, timeout=self.delai_s, headers={
                        "Range": f"bytes={f.tell()}-", "If-Range": etag_recu})
                    if rr.status_code == 206:
                        rep.octets_recus += _copier(rr, f)
                    elif rr.status_code == 200:
                        # Autre version servie : on repart de zéro avec elle.
                        f.seek(0)
                        f.truncate()
                        rep.entetes = {k.lower(): v for k, v in rr.headers.items()}
                        attendu = _entier(rep.entetes.get("content-length"))
                        etag_recu = rep.entetes.get("etag")
                        rep.octets_recus += _copier(rr, f)
                    else:
                        rr.close()
                        rep.message = f"reprise refusée : HTTP {rr.status_code}"
                        return False
                taille = f.tell()
            if attendu is not None and taille != attendu:
                rep.message = f"taille reçue {taille} ≠ annoncée {attendu}"
                return False
            rep.chemin, rep.taille, rep.empreinte = chemin, taille, _sha256(chemin)
            rep.issue = "nouveau"
            chemin = None  # ne pas effacer : le fichier est rendu à l'appelant
            return True
        finally:
            if chemin and os.path.exists(chemin):
                os.unlink(chemin)


def _copier(reponse, f) -> int:
    n = 0
    try:
        for bloc in reponse.iter_content(TAILLE_BLOC):
            f.write(bloc)
            n += len(bloc)
    except requests.RequestException:
        pass  # coupure : la taille reçue le dira
    finally:
        reponse.close()
    return n


def _entier(x):
    try:
        return int(x) if x is not None else None
    except ValueError:
        return None


def _sha256(chemin: str) -> str:
    h = hashlib.sha256()
    with open(chemin, "rb") as f:
        for bloc in iter(lambda: f.read(TAILLE_BLOC), b""):
            h.update(bloc)
    return h.hexdigest()
