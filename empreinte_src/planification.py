"""Second déclenchement planifié : ne rien refaire si la nuit en cours a déjà écrit une génération
(doc. 2, 2.3). Écrit « true » ou « false ».

La nuit commence à 20 h UTC (les déclenchements sont à 20 h 30 et 23 h 30 UTC). Une génération
écrite **depuis le début de la nuit en cours** arrête le déclenchement ; une génération écrite
dans la journée (mise à jour lancée à la main) ne l'arrête pas. Défaut corrigé le 07/11/2026 :
la règle disait « moins de 20 heures », et la mise à jour manuelle du 06/11 à 16 h 44 UTC a fait
sauter les deux déclenchements de la nuit.
"""
from __future__ import annotations

import argparse
import datetime as dt

from .distant import manifeste_distant

DEBUT_NUIT_UTC = 20


def debut_de_nuit(maintenant: dt.datetime, heure: int = DEBUT_NUIT_UTC) -> dt.datetime:
    """Le dernier « heure:00 UTC » passé : début de la nuit en cours."""
    d = maintenant.astimezone(dt.timezone.utc).replace(hour=heure, minute=0, second=0, microsecond=0)
    return d if d <= maintenant else d - dt.timedelta(days=1)


def a_faire(cree_le: str | None, maintenant: dt.datetime | None = None) -> bool:
    """Vrai si la mise à jour est à lancer : aucune génération n'est connue (`cree_le` vide), ou la
    dernière (`cree_le`, date ISO) a été écrite avant le début de la nuit en cours. `maintenant`
    vaut l'heure courante par défaut."""
    if not cree_le:
        return True
    maintenant = maintenant or dt.datetime.now(dt.timezone.utc)
    return dt.datetime.fromisoformat(cree_le) < debut_de_nuit(maintenant)


def main():
    """Point d'entrée : lit le manifeste distant du dépôt `--depot` et écrit `true` si la mise à
    jour est à faire (`a_faire`), `false` sinon."""
    p = argparse.ArgumentParser()
    p.add_argument("--depot", required=True)
    a = p.parse_args()
    man = manifeste_distant(a.depot)
    print("true" if a_faire((man or {}).get("cree_le")) else "false")


if __name__ == "__main__":
    main()
