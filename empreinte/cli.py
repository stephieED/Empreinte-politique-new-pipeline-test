"""Ligne de commande. Chaque sous-commande correspond à une tâche du workflow (doc. 2, 2.15)."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

import yaml

from .entrepot import Entrepot, maintenant
from .mesures import Mesures


def _config(chemin):
    with open(chemin) as f:
        return yaml.safe_load(f)


def _version_code():
    try:
        return subprocess.run(["git", "rev-parse", "--short=12", "HEAD"], capture_output=True,
                              text=True, check=True).stdout.strip()
    except Exception:
        return os.environ.get("GITHUB_SHA", "inconnue")[:12]


def _panne_depuis(entrepot: Entrepot, point: str) -> str | None:
    """Date du premier échec depuis le dernier relevé réussi (pour une alerte stable)."""
    depuis = None
    for r in entrepot._releves:
        if r["point_acces"] != point:
            continue
        if r["issue"] in ("nouveau", "inchange"):
            depuis = None
        elif depuis is None:
            depuis = r["debut"]
    return depuis


def cmd_preparer(a):
    cfg = _config(a.config)
    ids = {p["id"] for p in cfg["points_acces"]}
    inconnus = [p for p in (a.points or []) if p not in ids]
    if inconnus:
        sys.exit(f"Points d'accès inconnus : {', '.join(inconnus)}. Connus : {', '.join(sorted(ids))}")
    if a.mode not in ("quotidien", "complet", "essai"):
        sys.exit(f"Mode inconnu : {a.mode}")
    print(json.dumps({"mode": a.mode, "points": a.points or sorted(ids)}, ensure_ascii=False))


def cmd_collecter(a):
    from .collecte import collecter
    from .transport import Transport
    cfg = _config(a.config)
    params = cfg.get("parametres", {})
    mesures = Mesures()
    debut = maintenant()
    e = Entrepot(a.entrepot, segment_max=params.get("segment_max_octets", 90 << 20),
                 morceau_max=params.get("morceau_blob_octets", 64 << 20))
    t = Transport(params["user_agent"], dossier_tmp=a.tmp)
    if a.mode == "complet":
        for r in e._releves:            # relecture forcée : on oublie les ETag
            r["etag"] = r["last_modified"] = None
    releves = collecter(e, t, cfg, mesures, points=a.points)
    with mesures.etape("clore"):
        man = e.clore(_version_code())
    for r in releves:
        if r["issue"] in ("echec", "suspect"):
            r["panne_depuis"] = _panne_depuis(e, r["point_acces"])
    rapport = {"generation": man["generation"], "base": man["base"], "mode": a.mode,
               "debut": debut, "fin": maintenant(), "code": man["code"],
               "releves": releves, "mesures": mesures.etapes,
               "entrepot_octets": sum(f["taille"] for f in man["fichiers"].values()),
               "entrepot_fichiers": len(man["fichiers"])}
    with open(a.rapport, "w") as f:
        json.dump(rapport, f, indent=1, ensure_ascii=False, default=str)
    _resume(rapport)


def cmd_restaurer(a):
    from .distant import restaurer
    man = restaurer(a.depot, a.entrepot, avec_blobs=a.avec_blobs, avec_membres=a.avec_membres)
    print(f"génération restaurée : {man['generation'] if man else 0}")


def cmd_ecrire(a):
    from .distant import publier
    with open(a.rapport) as f:
        rapport = json.load(f)
    try:
        res = publier(a.depot, a.entrepot)
        rapport["ecriture"] = res
    except Exception as e:
        rapport["echec_ecriture"] = str(e)
    with open(a.rapport, "w") as f:
        json.dump(rapport, f, indent=1, ensure_ascii=False, default=str)
    if "echec_ecriture" in rapport:
        sys.exit(f"Écriture refusée : {rapport['echec_ecriture']}")
    env = rapport["ecriture"]["envois"]
    print(f"génération {rapport['ecriture']['generation']} écrite : {len(env)} actifs, "
          f"{sum(x['octets'] for x in env) / 1e6:.1f} Mo")


def cmd_alerter(a):
    from .alertes import sujets_du_rapport, synchroniser
    if a.rapport and os.path.exists(a.rapport):
        with open(a.rapport) as f:
            rapport = json.load(f)
    else:
        rapport = {"anomalies": [{"cle": "execution", "texte":
                   "La mise à jour s'est arrêtée avant de produire son rapport. Voir l'exécution : "
                   + os.environ.get("URL_EXECUTION", "?")}]}
    print(json.dumps(synchroniser(a.depot, sujets_du_rapport(rapport)), ensure_ascii=False))


def cmd_reconstruire(a):
    """Démonstration de P2 : le contenu exact d'une archive reçue, membre par membre."""
    e = Entrepot(a.entrepot)
    import hashlib
    membres = e.membres_du_releve(a.releve)
    octets = e.lire_plusieurs(m["empreinte"] for m in membres)
    ok = sum(1 for m in membres if m["empreinte"] in octets
             and hashlib.sha256(octets[m["empreinte"]]).hexdigest() == m["empreinte"])
    print(f"{ok} membres sur {len(membres)} retrouvés à l'octet près")
    sys.exit(0 if ok == len(membres) else 1)


def _resume(rapport):
    """Résumé lisible dans la page de l'exécution GitHub."""
    lignes = [f"## Mise à jour — génération {rapport['generation']}", "",
              "| Point d'accès | Issue | Octets reçus | Nouvelles versions | Retraits | Durée (s) | Message |",
              "| --- | --- | ---: | ---: | ---: | ---: | --- |"]
    for r in rapport["releves"]:
        msg = (r.get("message") or "").splitlines()[0][:80] if r.get("message") else ""
        lignes.append(f"| {r['point_acces']} | {r['issue']} | {r.get('octets_recus') or 0:,} | "
                      f"{r.get('nb_nouvelles_versions') or 0:,} | {r.get('nb_retraits') or 0:,} | "
                      f"{r.get('duree_s') or ''} | {msg} |")
    lignes += ["", f"Entrepôt : {rapport['entrepot_fichiers']} fichiers, "
               f"{rapport['entrepot_octets'] / 1e6:.1f} Mo."]
    texte = "\n".join(lignes)
    print(texte)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as f:
            f.write(texte + "\n")


def main(argv=None):
    p = argparse.ArgumentParser(prog="empreinte")
    sp = p.add_subparsers(dest="cmd", required=True)
    commun = argparse.ArgumentParser(add_help=False)
    commun.add_argument("--entrepot", default="entrepot")
    commun.add_argument("--config", default="config/points_acces.yaml")
    commun.add_argument("--rapport", default="sortie/rapport.json")
    commun.add_argument("--depot", default=os.environ.get("GITHUB_REPOSITORY"))

    s = sp.add_parser("preparer", parents=[commun]); s.set_defaults(f=cmd_preparer)
    s.add_argument("--mode", default="quotidien"); s.add_argument("--points", nargs="*")
    s = sp.add_parser("collecter", parents=[commun]); s.set_defaults(f=cmd_collecter)
    s.add_argument("--mode", default="quotidien"); s.add_argument("--points", nargs="*")
    s.add_argument("--tmp", default=None)
    s = sp.add_parser("restaurer", parents=[commun]); s.set_defaults(f=cmd_restaurer)
    s.add_argument("--avec-blobs", action="store_true"); s.add_argument("--avec-membres", action="store_true")
    s = sp.add_parser("ecrire", parents=[commun]); s.set_defaults(f=cmd_ecrire)
    s = sp.add_parser("alerter", parents=[commun]); s.set_defaults(f=cmd_alerter)
    s = sp.add_parser("reconstruire", parents=[commun]); s.set_defaults(f=cmd_reconstruire)
    s.add_argument("--releve", required=True)
    a = p.parse_args(argv)
    os.makedirs(os.path.dirname(a.rapport) or ".", exist_ok=True)
    a.f(a)


if __name__ == "__main__":
    main()
