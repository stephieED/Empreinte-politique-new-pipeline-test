"""Second déclenchement planifié : ne rien refaire si une génération a été écrite il y a
moins de 20 heures (doc. 2, 2.3). Écrit « true » ou « false »."""
from __future__ import annotations

import argparse
import datetime as dt

from .distant import manifeste_distant


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--depot", required=True)
    p.add_argument("--heures", type=float, default=20)
    a = p.parse_args()
    man = manifeste_distant(a.depot)
    if not man or not man.get("cree_le"):
        print("true")
        return
    age = dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(man["cree_le"])
    print("false" if age < dt.timedelta(hours=a.heures) else "true")


if __name__ == "__main__":
    main()
