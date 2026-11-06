"""Entrepôt distant : les *releases* du dépôt (doc. 3, J4).

- `restaurer` (lecture) : toutes les tâches peuvent l'appeler avec le jeton en lecture seule.
- `publier` (écriture) : appelée **seulement** par la tâche `ecrire` (correction P3).

Un fichier `a/b.parquet` de l'entrepôt devient l'actif `a__b.parquet` de la release
`entrepot`. Le manifeste est envoyé en dernier : tant qu'il n'est pas remplacé, la
génération précédente reste la génération courante, et un envoi interrompu ne laisse que des
actifs orphelins sans effet.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time

RELEASE = "entrepot"


def _gh(*args, capture=True, check=True):
    return subprocess.run(["gh", *args], capture_output=capture, text=True, check=check)


def nom_actif(rel: str) -> str:
    return rel.replace("/", "__")


def chemin_local(actif: str) -> str:
    return actif.replace("__", "/")


def manifeste_distant(depot: str) -> dict | None:
    with tempfile.TemporaryDirectory() as d:
        r = _gh("release", "download", RELEASE, "-R", depot, "-p", "manifeste.json", "-D", d,
                check=False)
        if r.returncode != 0:
            if "release not found" in (r.stderr or "").lower() or "no assets" in (r.stderr or "").lower():
                return None
            raise RuntimeError(f"lecture du manifeste distant impossible : {r.stderr.strip()}")
        with open(os.path.join(d, "manifeste.json")) as f:
            return json.load(f)


def restaurer(depot: str, dossier: str, avec_blobs: bool = False, avec_membres: bool = False) -> dict | None:
    """Rapatrie la génération courante. Sans les octets (blobs) par défaut : la collecte n'en
    a pas besoin, elle compare des empreintes."""
    os.makedirs(dossier, exist_ok=True)
    man = manifeste_distant(depot)
    if man is None:
        return None
    for rel, info in man["fichiers"].items():
        if rel.startswith("blobs/") and not avec_blobs:
            continue
        if rel.startswith("membres/") and not avec_membres:
            continue
        cible = os.path.join(dossier, rel)
        if os.path.exists(cible) and _sha(cible) == info["sha256"]:
            continue                       # déjà là (cache de GitHub Actions)
        os.makedirs(os.path.dirname(cible), exist_ok=True)
        with tempfile.TemporaryDirectory() as d:
            _gh("release", "download", RELEASE, "-R", depot, "-p", nom_actif(rel), "-D", d)
            os.replace(os.path.join(d, nom_actif(rel)), cible)
        if _sha(cible) != info["sha256"]:
            raise RuntimeError(f"empreinte fausse après téléchargement : {rel}")
    with open(os.path.join(dossier, "manifeste.json"), "w") as f:
        json.dump(man, f, indent=1, sort_keys=True, ensure_ascii=False)
    return man


def base_attendue(dossier: str, man: dict) -> int:
    """Génération que l'entrepôt distant doit avoir pour accepter cette écriture. Avec une
    nuit rattrapée, c'est la base de la nuit rattrapée (les deux sont écrites ensemble)."""
    rattrape = os.path.join(dossier, "rattrapage", "manifeste.json")
    if os.path.exists(rattrape):
        with open(rattrape) as f:
            mr = json.load(f)
        if mr["generation"] == man["base"]:
            return mr["base"]
    return man["base"]


def publier(depot: str, dossier: str) -> dict:
    """Envoie la génération préparée par la collecte. Refuse si une autre exécution a écrit
    entre-temps (la génération de base n'est plus la génération courante)."""
    with open(os.path.join(dossier, "manifeste.json")) as f:
        man = json.load(f)
    distant = manifeste_distant(depot)
    gen_distante = distant["generation"] if distant else 0
    base_admise = base_attendue(dossier, man)
    rattrape = os.path.join(dossier, "rattrapage", "manifeste.json")
    if os.path.exists(rattrape):
        with open(rattrape) as f:
            mr = json.load(f)
    if gen_distante != base_admise:
        raise RuntimeError(f"génération distante {gen_distante} ≠ base {man['base']} : "
                           "une autre exécution a écrit ; rien n'est envoyé")
    if distant is None:
        _gh("release", "create", RELEASE, "-R", depot, "--title", "Entrepôt",
            "--notes", "Entrepôt du traitement : relevés, versions des membres d'archives, registres. "
                       "Contenu des sources sous leurs licences respectives (Licence Ouverte, CC BY, ODbL…).")
    deja = (distant or {}).get("fichiers", {})
    mesures = []
    for rel, info in sorted(man["fichiers"].items()):
        if deja.get(rel, {}).get("sha256") == info["sha256"]:
            continue
        p = os.path.join(dossier, rel)
        if not os.path.exists(p):
            raise RuntimeError(f"fichier attendu absent de la copie locale : {rel}")
        mesures.append(_envoyer(depot, p, nom_actif(rel)))
    rates = [m["actif"] for m in mesures if not m["reussi"]]
    if rates:
        raise RuntimeError(f"envoi échoué pour {rates} : le manifeste n'est pas remplacé")
    if os.path.exists(rattrape):
        mesures.append(_envoyer(depot, rattrape, f"manifeste-g{mr['generation']:06d}.json"))
    with tempfile.TemporaryDirectory() as d:
        copie = os.path.join(d, f"manifeste-g{man['generation']:06d}.json")
        with open(copie, "w") as f:
            json.dump(man, f, indent=1, sort_keys=True, ensure_ascii=False)
        mesures.append(_envoyer(depot, copie, os.path.basename(copie)))
    mesures.append(_envoyer(depot, os.path.join(dossier, "manifeste.json"), "manifeste.json"))
    return {"generation": man["generation"], "envois": mesures}


def _envoyer(depot, chemin, nom, essais=3) -> dict:
    debut = time.monotonic()
    taille = os.path.getsize(chemin)
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, nom)
        os.symlink(os.path.abspath(chemin), p)
        for k in range(essais):
            r = _gh("release", "upload", RELEASE, p, "-R", depot, "--clobber", check=False)
            if r.returncode == 0:
                return {"actif": nom, "octets": taille, "duree_s": round(time.monotonic() - debut, 2),
                        "essais": k + 1, "reussi": True}
            time.sleep(10 * (k + 1))
    return {"actif": nom, "octets": taille, "duree_s": round(time.monotonic() - debut, 2),
            "essais": essais, "reussi": False, "erreur": (r.stderr or "").strip()[:300]}


def _sha(p):
    from .entrepot import sha256_fichier
    return sha256_fichier(p)


def publier_export(depot: str, dossier_export: str, generation: int) -> list[dict]:
    """Export plat de la nuit (commande, section 7) : release `export`, un jeu par génération."""
    r = _gh("release", "view", "export", "-R", depot, check=False)
    if r.returncode != 0:
        _gh("release", "create", "export", "-R", depot, "--title", "Export des faits",
            "--notes", "Export plat des faits, une ligne par fait, un jeu par nuit (génération). "
                       "Documentation : voir le dépôt. Licences : colonne `licence` de chaque ligne.")
    envois = []
    for nom in ("faits.parquet", "faits.csv.gz"):
        cible = f"{nom.split('.')[0]}-g{generation:06d}.{nom.split('.', 1)[1]}"
        envois.append(_envoyer(depot, os.path.join(dossier_export, nom), cible))
    return envois
