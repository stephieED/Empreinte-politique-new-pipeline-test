"""Mesures d'exécution (commande de réalisation, section 5) : durée, pic de mémoire, octets."""
from __future__ import annotations

import os
import resource
import time
from contextlib import contextmanager


def _pic_rss_ko() -> int | None:
    try:
        with open("/proc/self/status") as f:
            for ligne in f:
                if ligne.startswith("VmHWM:"):
                    return int(ligne.split()[1])
    except OSError:
        pass
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss


def _remettre_pic_a_zero():
    """Linux : écrire 5 dans clear_refs remet le pic de mémoire (VmHWM) à la valeur courante."""
    try:
        with open("/proc/self/clear_refs", "w") as f:
            f.write("5")
    except OSError:
        pass


class Mesures:
    """Les mesures des étapes d'une tâche, dans l'ordre où elles ont fini (`etapes`, une liste de
    dictionnaires)."""
    def __init__(self):
        self.etapes: list[dict] = []

    @contextmanager
    def etape(self, nom: str, **extra):
        """Gestionnaire de contexte qui mesure une étape : `with mesures.etape("E4") as m:`.

        Remet à zéro le pic de mémoire du processus en entrant, rend le dictionnaire `m`
        (`{"etape": nom, **extra}`, que l'appelant peut compléter), et en sortant, même sur une
        erreur, y ajoute la durée (`duree_s`) et le pic de mémoire (`pic_memoire_mo`, `None` si non
        lu) avant de l'ajouter à `etapes`."""
        _remettre_pic_a_zero()
        debut = time.monotonic()
        m = {"etape": nom, **extra}
        try:
            yield m
        finally:
            m["duree_s"] = round(time.monotonic() - debut, 2)
            pic = _pic_rss_ko()
            m["pic_memoire_mo"] = round(pic / 1024, 1) if pic else None
            self.etapes.append(m)

    def pic(self) -> str:
        """Pic de mémoire de la tâche : le plus haut des pics de ses étapes. Le pic du processus est
        remis à zéro au début de chaque étape : `time -v`, qui le lit à la fin, ne voit que la
        dernière (constaté le 13/11/2026 : 2 683 Mo selon `time -v`, 4 813 Mo en E4)."""
        avec = [m for m in self.etapes if m.get("pic_memoire_mo") is not None]
        if not avec:
            return "Pic de mémoire : non mesuré."
        m = max(avec, key=lambda x: x["pic_memoire_mo"])
        nom = m["etape"] + (f" {m['point_acces']}" if m.get("point_acces") else "") + \
            (f" {m['lecteur']}" if m.get("lecteur") else "")
        return f"Pic de mémoire : {m['pic_memoire_mo']:,.0f} Mo (étape {nom})."
