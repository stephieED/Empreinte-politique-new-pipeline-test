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


RELEASE_BRUTES = "archives-brutes"


def _release_de(rel: str) -> str:
    """Release d'un fichier de l'entrepôt : les archives brutes à part (décision du 13/11/2026)."""
    return RELEASE_BRUTES if rel.startswith("brutes/") else RELEASE


def nom_actif(rel: str) -> str:
    """Rend le nom d'actif de release d'un fichier de l'entrepôt : son chemin relatif `rel`, les
    `/` remplacés par `__` (`a/b.parquet` donne `a__b.parquet`)."""
    return rel.replace("/", "__")


def chemin_local(actif: str) -> str:
    """Inverse de `nom_actif` : rend le chemin relatif d'un actif, les `__` remplacés par `/`."""
    return actif.replace("__", "/")


def manifeste_distant(depot: str) -> dict | None:
    """Télécharge `manifeste.json` de la release `entrepot` du dépôt `depot` (avec `gh`) et le rend
    lu. Rend `None` si la release ou l'actif n'existe pas ; lève `RuntimeError` pour toute autre
    erreur de lecture."""
    with tempfile.TemporaryDirectory() as d:
        r = _gh("release", "download", RELEASE, "-R", depot, "-p", "manifeste.json", "-D", d,
                check=False)
        if r.returncode != 0:
            if "release not found" in (r.stderr or "").lower() or "no assets" in (r.stderr or "").lower():
                return None
            raise RuntimeError(f"lecture du manifeste distant impossible : {r.stderr.strip()}")
        with open(os.path.join(d, "manifeste.json")) as f:
            return json.load(f)


def restaurer(depot: str, dossier: str, avec_blobs: bool = False, avec_membres: bool = False,
              avec_brutes: bool = False) -> dict | None:
    """Rapatrie la génération courante. Sans les octets (blobs) par défaut : la collecte n'en
    a pas besoin, elle compare des empreintes. Jamais les archives brutes (`brutes/`, release
    `archives-brutes`) sauf demande : elles ne servent qu'à refaire un découpage."""
    os.makedirs(dossier, exist_ok=True)
    man = manifeste_distant(depot)
    if man is None:
        return None
    for rel, info in man["fichiers"].items():
        if rel.startswith("blobs/") and not avec_blobs:
            continue
        if rel.startswith("membres/") and not avec_membres:
            continue
        if rel.startswith("brutes/") and not avec_brutes:
            continue
        cible = os.path.join(dossier, rel)
        if os.path.exists(cible) and _sha(cible) == info["sha256"]:
            continue                       # déjà là (cache de GitHub Actions)
        os.makedirs(os.path.dirname(cible), exist_ok=True)
        with tempfile.TemporaryDirectory() as d:
            _gh("release", "download", _release_de(rel), "-R", depot, "-p", nom_actif(rel), "-D", d)
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
        release = _release_de(rel)
        if release != RELEASE and _gh("release", "view", release, "-R", depot, check=False).returncode != 0:
            _gh("release", "create", release, "-R", depot, "--title", "Archives brutes",
                "--notes", "Archives reçues dont seule une partie est découpée dans l'entrepôt (archive "
                           "globale du Journal officiel), gardées à l'octet pour pouvoir refaire le "
                           "découpage. Empreintes : manifeste de l'entrepôt. Licence de chaque source.")
        mesures.append(_envoyer(depot, p, nom_actif(rel), release=release))
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


def _envoyer(depot, chemin, nom, essais=3, release=RELEASE) -> dict:
    """Dépose un fichier dans une release (par défaut l'entrepôt), avec reprise."""
    debut = time.monotonic()
    taille = os.path.getsize(chemin)
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, nom)
        os.symlink(os.path.abspath(chemin), p)
        for k in range(essais):
            r = _gh("release", "upload", release, p, "-R", depot, "--clobber", check=False)
            if r.returncode == 0:
                return {"actif": nom, "release": release, "octets": taille,
                        "duree_s": round(time.monotonic() - debut, 2), "essais": k + 1, "reussi": True}
            time.sleep(10 * (k + 1))
    return {"actif": nom, "release": release, "octets": taille, "duree_s": round(time.monotonic() - debut, 2),
            "essais": essais, "reussi": False, "erreur": (r.stderr or "").strip()[:300]}


def _sha(p):
    from .entrepot import sha256_fichier
    return sha256_fichier(p)


def publier_export(depot: str, dossier_export: str, generation: int) -> list[dict]:
    """Export plat de la nuit (commande, section 7) : release `export`.

    Les **faits publiés** de chaque nuit sont tous gardés (`faits-publies-gNNNNNN.parquet` : ce que
    demande la commande, et la base du contrôle des pertes C1). L'export de **tous les faits lus**
    (`faits-gNNNNNN.parquet`, ≈ 1,2 Go sur le périmètre complet) n'est gardé que pour la dernière
    nuit, en Parquet seul : déposé, il remplace ceux des nuits précédentes, et leurs anciens CSV
    sont retirés (décision du 12/11/2026)."""
    import re
    r = _gh("release", "view", "export", "-R", depot, check=False)
    if r.returncode != 0:
        _gh("release", "create", "export", "-R", depot, "--title", "Export des faits",
            "--notes", "Export plat des faits, une ligne par fait. Faits publiés : un fichier par nuit "
                       "(génération). Tous les faits lus : la dernière nuit seulement. "
                       "Documentation : voir le dépôt. Licences : colonne `licence` de chaque ligne.")
    envois = []
    for nom in ("faits.parquet", "faits-publies.parquet"):
        if not os.path.exists(os.path.join(dossier_export, nom)):
            continue
        cible = f"{nom.split('.')[0]}-g{generation:06d}.{nom.split('.', 1)[1]}"
        envois.append(_envoyer(depot, os.path.join(dossier_export, nom), cible, release="export"))
    depose = next((e for e in envois if e["actif"] == f"faits-g{generation:06d}.parquet"), None)
    if depose and depose["reussi"]:
        r = _gh("release", "view", "export", "-R", depot, "--json", "assets", check=False)
        anciens = sorted(a["name"] for a in (json.loads(r.stdout or "{}").get("assets", []) if r.returncode == 0 else [])
                         if re.fullmatch(r"faits-g\d{6}\.(parquet|csv\.gz)", a["name"])
                         and a["name"] != depose["actif"])
        for nom in anciens:
            x = _gh("release", "delete-asset", "export", nom, "-R", depot, "-y", check=False)
            envois.append({"actif": nom, "release": "export", "retire": True, "reussi": x.returncode == 0})
    return envois


def publier_site(depot: str, dossier_site: str, generation: int) -> list[dict]:
    """Fichiers servis et page minimale de la nuit (release `publication`), en une archive.
    La dernière archive est servie par Pages avec la documentation du code (workflow `pages.yml`,
    décision du 13/11/2026) ; elle s'ouvre aussi en local."""
    import tarfile
    r = _gh("release", "view", "publication", "-R", depot, check=False)
    if r.returncode != 0:
        _gh("release", "create", "publication", "-R", depot, "--title", "Publications",
            "--notes", "Fichiers servis aux fiches et page minimale, une archive par nuit. "
                       "Pour la regarder : extraire, puis `python -m http.server` dans le dossier.")
    with tempfile.TemporaryDirectory() as d:
        archive = os.path.join(d, f"site-g{generation:06d}.tar.gz")
        with tarfile.open(archive, "w:gz") as t:
            t.add(dossier_site, arcname=f"site-g{generation:06d}")
        return [_envoyer(depot, archive, os.path.basename(archive), release="publication")]


def derniere_publication(depot: str, essais: int = 3, pause_s: float = 20) -> str | None:
    """Nom des faits publiés de la dernière publication réussie (release `export`), ou None s'il
    n'y en a jamais eu (release absente ou sans faits publiés).

    Une erreur de l'API GitHub n'est **pas** « aucune publication » : elle passait pour un premier
    calcul, et C1 et C6 étaient sautés sans rien dire (issue #40). Après `essais` tentatives, elle
    lève une erreur : le calcul échoue, rien n'est publié, l'alerte « publication » le dit."""
    import re
    import time
    for k in range(essais):
        r = _gh("release", "view", "export", "-R", depot, "--json", "assets", check=False)
        if r.returncode == 0 or "release not found" in (r.stderr or "").lower():
            break
        if k + 1 < essais:
            time.sleep(pause_s)
    else:
        raise RuntimeError(f"release `export` illisible après {essais} essais : {(r.stderr or '').strip()[:300]}")
    if r.returncode != 0:
        return None
    noms = sorted(a["name"] for a in json.loads(r.stdout).get("assets", [])
                  if re.fullmatch(r"faits-publies-g\d{6}\.parquet", a["name"]))
    return noms[-1] if noms else None


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("commande", choices=["derniere-publication"])
    p.add_argument("--depot", required=True)
    a = p.parse_args()
    print(derniere_publication(a.depot) or "")
