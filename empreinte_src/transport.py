"""Téléchargement d'un point d'accès (étape E1).

Ce que ce module garantit (doc. 2, 2.2) :
- requête conditionnelle quand la source le permet (ETag, Last-Modified) : une archive
  inchangée coûte une requête ;
- le fichier reçu est vérifié contre Content-Length : l'Assemblée coupe des transferts en
  renvoyant quand même 200 (mesuré le 04/11/2026) ;
- reprise par segments (`Range`) **vérifiée par nous** : la suite n'est recollée que si la
  réponse est un 206 qui commence exactement où le fichier s'arrête, annonce la même taille
  totale et porte le même ETag (ou, sans ETag, la même date de modification) ; sinon l'on
  repart de zéro avec la version servie, au lieu de recoller deux versions. On ne s'en remet
  pas à `If-Range` : relevé le 07/11/2026 depuis GitHub, les amendements XVe et XVIe (363 et
  649 Mo) n'ont jamais pu être repris, et le relais de diffusion (CDN) est seul à voir les
  requêtes de GitHub ;
- une coupure pendant une reprise (connexion fermée, délai dépassé) est une reprise de plus,
  pas un nouveau départ ; chaque reprise est notée (`journal_reprises`) ;
- chaque octet reçu est compté, reprises comprises (mesure de la commande, section 5) ;
- le budget de temps d'un fichier est tenu **pendant** la copie, pas seulement entre deux essais :
  un serveur qui envoie au compte-gouttes ne retient plus la collecte jusqu'à la limite de la tâche
  (issue #37) ; un point peut avoir son propre budget (`budget_s` dans la configuration : archives
  closes trop grosses pour 30 min, décision du 13/11/2026) ;
- un hôte qui ne sert plus rien est suspendu pour la nuit : après `echecs_hote_max` échecs sans un
  octet reçu, ses autres points échouent tout de suite, sans brûler chacun ses 750 s de pauses
  (35 points sur `data.assemblee-nationale.fr`, issue #37) ;
- une échéance pour toute la collecte (`fin_collecte`, horloge monotone) : passée, les points
  restants échouent tout de suite et la collecte se termine normalement, au lieu d'être coupée par
  la limite de la tâche, qui perdait tout l'acquis de la nuit (issue #38).
"""
from __future__ import annotations

import hashlib
import os
import tempfile
import time
from dataclasses import dataclass, field
from urllib.parse import urlsplit

import requests

# Bloc de lecture : à une coupure, le bloc en cours est perdu (la reprise repart de la fin du
# dernier bloc écrit). 64 Kio : au plus 64 Kio perdus par coupure.
TAILLE_BLOC = 1 << 16


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
    journal_reprises: list = field(default_factory=list)   # « 206 +12 Mo », « 200 », « coupure »…


class Transport:
    """Accès HTTP. `pauses` donne l'attente avant chaque nouvelle tentative (doc. 2 : 30 s,
    2 min, 10 min) ; les tests passent des pauses nulles."""

    def __init__(self, user_agent: str, pauses=(30, 120, 600), delai_s: float = 60.0,
                 reprises_max: int = 40, dossier_tmp: str | None = None, pause_reprise_s: float = 2.0,
                 budget_s: float | None = 1800.0, reprises_vides_max: int = 3,
                 budgets_par_url: dict[str, float] | None = None, echecs_hote_max: int = 3,
                 fin_collecte: float | None = None):
        self.session = requests.Session()
        self.session.headers["User-Agent"] = user_agent
        # Octets bruts : un encodage de transport fausserait la comparaison à Content-Length.
        self.session.headers["Accept-Encoding"] = "identity"
        self.pauses = tuple(pauses)
        self.delai_s = delai_s
        self.reprises_max = reprises_max
        self.dossier_tmp = dossier_tmp
        self.pause_reprise_s = pause_reprise_s
        # Budget de temps par fichier : au-delà, échec pour cette nuit (une archive close
        # récalcitrante ne fait pas durer la nuit des heures ; elle est retentée la suivante).
        self.budget_s = budget_s
        # Reprises de suite qui n'apportent presque rien (moins d'un bloc) avant de repartir du début :
        # mesuré le 07/11/2026, l'Assemblée sert mal une plage prise loin dans un gros fichier
        # (206 puis rien), alors qu'un transfert depuis le début avance.
        self.reprises_vides_max = reprises_vides_max
        self.budgets_par_url = dict(budgets_par_url or {})
        self.echecs_hote_max = echecs_hote_max
        self.echecs_hote: dict[str, int] = {}       # échecs de suite sans un octet, par hôte
        self.fin_collecte = fin_collecte
        self._debut = time.monotonic()
        self._budget = budget_s

    def _hors_budget(self, en_plus: float = 0.0) -> bool:
        limite = self._limite()
        return limite is not None and time.monotonic() + en_plus > limite

    def _limite(self) -> float | None:
        """Instant (horloge monotone) où le fichier en cours doit s'arrêter : fin de son budget, ou
        fin de la collecte si elle vient avant."""
        bornes = [b for b in (self._debut + self._budget if self._budget else None, self.fin_collecte)
                  if b is not None]
        return min(bornes) if bornes else None

    def _copier(self, reponse, f) -> int:
        return _copier(reponse, f, self._limite())

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
        self._debut = debut
        self._budget = self.budgets_par_url.get(url, self.budget_s)
        hote = urlsplit(url).netloc
        if self.fin_collecte is not None and time.monotonic() >= self.fin_collecte:
            rep.message = "durée maximale de la collecte atteinte : point non relevé, nouvel essai à la prochaine"
            return rep
        if self.echecs_hote_max and self.echecs_hote.get(hote, 0) >= self.echecs_hote_max:
            rep.message = (f"hôte {hote} suspendu pour cette mise à jour : {self.echecs_hote[hote]} points "
                           "de suite sans un octet reçu ; nouvel essai à la prochaine")
            return rep
        for essai in range(len(self.pauses) + 1):
            if essai:
                if self._hors_budget(self.pauses[essai - 1]):
                    break
                time.sleep(self.pauses[essai - 1])
            rep.tentatives += 1
            try:
                fini = self._un_essai(url, etag, last_modified, rep)
                if fini:
                    rep.duree_s = time.monotonic() - debut
                    self.echecs_hote[hote] = 0
                    return rep
                derniere_erreur = rep.message
            except requests.RequestException as e:
                derniere_erreur = f"{type(e).__name__}: {e}"
        rep.issue = "echec"
        rep.message = derniere_erreur or "échec sans message"
        if self._hors_budget():
            rep.message += (" ; durée maximale de la collecte atteinte" if self.fin_collecte is not None
                            and time.monotonic() >= self.fin_collecte else
                            f" ; budget de {int(self._budget)} s dépassé, nouvel essai à la prochaine nuit")
        # Un hôte qui n'a rien servi du tout : compté ; un transfert lent mais vivant ne l'est pas.
        self.echecs_hote[hote] = self.echecs_hote.get(hote, 0) + 1 if rep.octets_recus == 0 else 0
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
        date_recue = rep.entetes.get("last-modified")
        fd, chemin = tempfile.mkstemp(prefix="releve-", dir=self.dossier_tmp)
        try:
            with os.fdopen(fd, "wb") as f:
                rep.octets_recus += self._copier(r, f)
                reprises = vides = 0
                while attendu is not None and f.tell() < attendu:
                    # Transfert coupé. Reprise seulement si un validateur garantit la même version.
                    if not (etag_recu or date_recue) or reprises >= self.reprises_max or self._hors_budget():
                        rep.message = (f"transfert coupé à {f.tell()} octets sur {attendu}"
                                       + ("" if (etag_recu or date_recue) else ", sans ETag pour reprendre")
                                       + (f" ; reprises : {', '.join(rep.journal_reprises[-12:])}"
                                          if rep.journal_reprises else ""))
                        return False
                    reprises += 1
                    rep.reprises += 1
                    if self.pause_reprise_s:
                        time.sleep(min(self.pause_reprise_s * reprises, 30))
                    debut_reprise = f.tell()
                    try:
                        rr = self.session.get(url, stream=True, timeout=self.delai_s,
                                              headers={"Range": f"bytes={debut_reprise}-"})
                    except requests.RequestException as e:
                        rep.journal_reprises.append(f"coupure ({type(e).__name__})")
                        continue
                    h = {k.lower(): v for k, v in rr.headers.items()}
                    if rr.status_code == 206 and _meme_suite(h, debut_reprise, attendu, etag_recu, date_recue):
                        n = self._copier(rr, f)
                        rep.octets_recus += n
                        rep.journal_reprises.append(f"206 +{_taille_lisible(n)}")
                        vides = vides + 1 if n < TAILLE_BLOC else 0
                        if vides >= self.reprises_vides_max and f.tell() < attendu:
                            # La plage n'avance plus : repartir du début, qui avance mieux.
                            vides = 0
                            try:
                                rr = self.session.get(url, stream=True, timeout=self.delai_s)
                            except requests.RequestException as e:
                                rep.journal_reprises.append(f"coupure ({type(e).__name__})")
                                continue
                            if rr.status_code != 200:
                                rr.close()
                                continue
                            rep.journal_reprises.append("départ du début")
                            f.seek(0)
                            f.truncate()
                            rep.entetes = {k.lower(): v for k, v in rr.headers.items()}
                            attendu = _entier(rep.entetes.get("content-length"))
                            etag_recu = rep.entetes.get("etag")
                            date_recue = rep.entetes.get("last-modified")
                            rep.octets_recus += self._copier(rr, f)
                    elif rr.status_code in (200, 206):
                        # Autre version servie, ou serveur qui ignore la plage : on repart de zéro
                        # avec la version entière.
                        rr.close()
                        rep.journal_reprises.append(f"{rr.status_code} autre version : départ à zéro")
                        try:
                            rr = self.session.get(url, stream=True, timeout=self.delai_s)
                        except requests.RequestException as e:
                            rep.journal_reprises.append(f"coupure ({type(e).__name__})")
                            continue
                        if rr.status_code != 200:
                            rr.close()
                            rep.message = f"reprise refusée : HTTP {rr.status_code}"
                            return False
                        f.seek(0)
                        f.truncate()
                        rep.entetes = {k.lower(): v for k, v in rr.headers.items()}
                        attendu = _entier(rep.entetes.get("content-length"))
                        etag_recu = rep.entetes.get("etag")
                        date_recue = rep.entetes.get("last-modified")
                        rep.octets_recus += self._copier(rr, f)
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


def _taille_lisible(n: int) -> str:
    return f"{n >> 20} Mo" if n >= 1 << 20 else f"{n >> 10} Ko"


def _meme_suite(h: dict, debut: int, attendu: int, etag: str | None, date: str | None) -> bool:
    """Le 206 reçu est-il bien la suite du même fichier ? Début, taille totale, version."""
    cr = h.get("content-range", "")                 # « bytes 1000-1999/102400 »
    try:
        plage, total = cr.split(" ", 1)[1].split("/")
        debut_recu = int(plage.split("-")[0])
        total = int(total)
    except (IndexError, ValueError):
        return False
    if debut_recu != debut or total != attendu:
        return False
    if etag:
        return h.get("etag") == etag
    return bool(date) and h.get("last-modified") == date


def _copier(reponse, f, limite: float | None = None) -> int:
    """Copie la réponse dans `f` ; s'arrête à l'instant `limite` (horloge monotone), même si le
    serveur envoie encore : la taille reçue dira que le fichier est incomplet."""
    n = 0
    try:
        for bloc in reponse.iter_content(TAILLE_BLOC):
            f.write(bloc)
            n += len(bloc)
            if limite is not None and time.monotonic() > limite:
                break
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
