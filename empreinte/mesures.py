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
    def __init__(self):
        self.etapes: list[dict] = []

    @contextmanager
    def etape(self, nom: str, **extra):
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
