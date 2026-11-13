"""Forme des fichiers servis : schéma en liste blanche (C4, doc. 2, 2.8.1 ; issue #43).

Le schéma est un fichier commité, `config/schema_fichiers.yaml` (décision du 13/11/2026,
« Schéma commité, bloquant ») :

- `colonnes` : pour chaque section, repérée par le type de fiche et son nom où chaque nombre
  devient `N` (`lignees/votes-N`, `candidats/amendements-N` ; les index de mots d'une fiche,
  `candidats/mots/*`), la liste ordonnée de ses colonnes ;
- `vocabulaires` : pour quelques champs fermés, dont les valeurs sont fixées par nos règles
  (sort, raison du sort, étape, positions…), les valeurs permises ; une valeur vide est toujours
  permise (une donnée manquante reste manquante) ;
- `statuts_couverture` : les statuts du doc. 1, 1.5.5.

Un écart (section inconnue, colonne ajoutée, retirée ou renommée, valeur hors vocabulaire)
refuse la publication. Une forme nouvelle et voulue s'ajoute au schéma dans la même PR :
`python -m empreinte_src.cli schema --site <sortie>/site` réécrit les colonnes d'après les
fichiers servis d'un calcul, sans toucher aux vocabulaires, qui se modifient à la main.
"""
from __future__ import annotations

import gzip
import json
import os
import re

import yaml


def cle_section(chemin: str) -> str | None:
    """`candidats/x/votes-14.json.gz` → `candidats/votes-N` ; None pour un fichier qui n'est pas
    une section (en-tête de fiche, catalogue, manifeste)."""
    morceaux = chemin.replace(os.sep, "/").split("/")
    nom = morceaux[-1]
    if not nom.endswith(".json.gz") or nom == "fiche.json.gz" or len(morceaux) < 3:
        return None
    if len(morceaux) > 3:
        # Sous-dossier d'une fiche (index de mots `mots/<préfixe>.json.gz`) : une seule forme.
        return f"{morceaux[0]}/{'/'.join(morceaux[2:-1])}/*"
    return f"{morceaux[0]}/{re.sub(r'[0-9]+', 'N', nom[:-len('.json.gz')])}"


def _fichiers(racine: str):
    for dossier, _, noms in os.walk(racine):
        for n in sorted(noms):
            if n.endswith(".json.gz"):
                p = os.path.join(dossier, n)
                with gzip.open(p) as f:
                    yield os.path.relpath(p, racine), json.load(f)


def _statuts(couverture):
    for x in (couverture if isinstance(couverture, list) else [couverture]):
        if isinstance(x, dict) and x.get("statut") is not None:
            yield x["statut"]
        if isinstance(x, dict) and isinstance(x.get("maillons_hors_perimetre"), dict):
            yield from _statuts(x["maillons_hors_perimetre"])


def relever(racine: str) -> dict[str, list[str]]:
    """Colonnes de chaque section servie (sections vides exclues : leurs colonnes ne disent rien)."""
    out: dict[str, list[str]] = {}
    for chemin, contenu in _fichiers(racine):
        cle = cle_section(chemin)
        if cle and isinstance(contenu, dict) and "colonnes" in contenu and contenu.get("lignes"):
            out.setdefault(cle, list(contenu["colonnes"]))
    return dict(sorted(out.items()))


def charger(chemin: str) -> dict:
    with open(chemin) as f:
        return yaml.safe_load(f) or {}


def verifier(racine: str, schema: dict) -> list[str]:
    """Écarts entre les fichiers servis et le schéma ; un par (section, nature d'écart, champ)."""
    colonnes = schema.get("colonnes") or {}
    vocab = {k: set(map(str, v)) for k, v in (schema.get("vocabulaires") or {}).items()}
    statuts = set(schema.get("statuts_couverture") or [])
    ecarts: dict[str, str] = {}
    for chemin, contenu in _fichiers(racine):
        if not isinstance(contenu, dict):
            continue
        for s in _statuts(contenu.get("couverture")):
            if statuts and s not in statuts:
                ecarts.setdefault(f"statut:{s}", f"{chemin} : statut de couverture « {s} » hors du schéma")
        cle = cle_section(chemin)
        if not cle or "colonnes" not in contenu:
            continue
        cols, lignes = contenu["colonnes"], contenu.get("lignes") or []
        if lignes:
            attendu = colonnes.get(cle)
            if attendu is None:
                ecarts.setdefault(f"section:{cle}", f"{chemin} : section « {cle} » absente du schéma")
            elif list(cols) != list(attendu):
                en_plus = [c for c in cols if c not in attendu]
                en_moins = [c for c in attendu if c not in cols]
                ecarts.setdefault(f"colonnes:{cle}", f"{chemin} : colonnes différentes du schéma "
                                  f"(en plus : {en_plus or '—'} ; en moins : {en_moins or '—'}"
                                  + ("" if en_plus or en_moins else " ; ordre changé") + ")")
        for i, c in enumerate(cols):
            if c not in vocab:
                continue
            for l in lignes:
                v = l[i]
                if v is not None and v != "" and str(v) not in vocab[c]:
                    ecarts.setdefault(f"valeur:{c}:{v}", f"{chemin} : « {c} » = « {v} », hors du vocabulaire")
    return [ecarts[k] for k in sorted(ecarts)]


def reecrire_colonnes(chemin_schema: str, racine: str) -> dict:
    """Remplace les colonnes du schéma par celles des fichiers servis ; garde le reste."""
    schema = charger(chemin_schema) if os.path.exists(chemin_schema) else {}
    avant = schema.get("colonnes") or {}
    schema["colonnes"] = relever(racine)
    entete = ("# Schéma des fichiers servis (C4, issue #43). Colonnes : `python -m empreinte_src.cli schema\n"
              "# --site <sortie>/site` ; vocabulaires et statuts : à la main. Voir empreinte_src/schema.py.\n")
    with open(chemin_schema, "w") as f:
        f.write(entete)
        yaml.safe_dump(schema, f, allow_unicode=True, sort_keys=False, width=110)
    return {"sections": len(schema["colonnes"]),
            "ajoutees": sorted(set(schema["colonnes"]) - set(avant)),
            "retirees": sorted(set(avant) - set(schema["colonnes"]))}
