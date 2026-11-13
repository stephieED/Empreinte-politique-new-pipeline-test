"""Rattrapage d'une nuit non écrite (doc. 2, 2.4 ; étape 2).

Si la tâche `ecrire` d'une nuit n'a pas eu lieu, l'acquis de cette nuit reste disponible comme
artefact `acquis-gNNNNNN` de son exécution (14 jours). La nuit suivante le retrouve ici, le
superpose à sa copie de travail avant de collecter, et l'écrit avec sa propre génération : la
nuit perdue n'en est pas une. On ne rattrape qu'un acquis qui s'appuie exactement sur la
génération courante de l'entrepôt ; sinon, rien n'est écrit et une alerte le dit.

Écrit sur la sortie standard un JSON : {} ou {"run": <id>, "nom": "acquis-g…", "generation": N}.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess

from .distant import manifeste_distant


def chercher(depot: str, run_actuel: str | None) -> dict:
    man = manifeste_distant(depot)
    gen = man["generation"] if man else 0
    sortie = subprocess.run(["gh", "api", f"repos/{depot}/actions/artifacts?per_page=100"],
                            capture_output=True, text=True, check=True).stdout
    candidats = []
    for a in json.loads(sortie).get("artifacts", []):
        m = re.fullmatch(r"acquis-g(\d{6})", a["name"])
        if not m or a.get("expired"):
            continue
        run = str((a.get("workflow_run") or {}).get("id"))
        if run_actuel and run == str(run_actuel):
            continue
        g = int(m.group(1))
        if g == gen + 1:                     # s'appuie sur la génération courante
            candidats.append({"run": run, "nom": a["name"], "generation": g,
                              "cree_le": a.get("created_at")})
    candidats.sort(key=lambda c: c["cree_le"] or "", reverse=True)
    return candidats[0] if candidats else {}


def main():
    """Une erreur de l'API GitHub ne doit ni arrêter la nuit ni empêcher l'alerte (issue #41) :
    après trois essais, la nuit continue sans rattrapage, et l'erreur est remise à la collecte,
    qui la met dans le rapport (alerte `rattrapage`). Un acquis non repris reste disponible
    14 jours : la nuit suivante le reprendra."""
    import time
    p = argparse.ArgumentParser()
    p.add_argument("--depot", required=True)
    p.add_argument("--run-actuel")
    p.add_argument("--essais", type=int, default=3)
    p.add_argument("--pause", type=float, default=20)
    a = p.parse_args()
    for k in range(a.essais):
        try:
            print(json.dumps(chercher(a.depot, a.run_actuel)))
            return
        except Exception as e:                        # API, réseau, réponse illisible
            erreur = f"{type(e).__name__}: {str(e).strip()[:300]}"
            if k + 1 < a.essais:
                time.sleep(a.pause)
    print(json.dumps({"erreur": erreur}, ensure_ascii=False))


if __name__ == "__main__":
    main()
