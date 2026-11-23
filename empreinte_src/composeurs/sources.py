"""Référentiel des points d'accès (issue #73 ; doc. 1, 1.7.2 : `sources.json.gz`).

L'interface termine chaque bulle d'aide par « {Source} ↗ · à jour au {date} ». Pour chaque point
d'accès de la configuration (`config/points_acces.yaml`), `sources.json.gz` sert :

- son identifiant, sa source, son adresse (`url`) et sa licence, tels que la configuration les
  donne (une licence absente reste vide) ;
- son **nom affiché**, un choix éditorial : la table `references/nom_point_acces/table.yaml`
  (décisions `nom_point_acces`, validées en fusionnant). Un point sans nom est servi avec un nom
  vide et sa raison, jamais avec un nom deviné ; un nom pour un point inconnu de la configuration
  est servi à part (`noms_sans_point`) ;
- ses dates, prises dans l'état des points de l'Ecrivain (`Ecrivain.etat_points`, le même que
  `couverture.json.gz`, issue #74) : `date_source`, la date de la donnée à la source, référence de
  « à jour au » (cahier des charges, 4.7), vide avec sa raison quand on ne la connaît pas, jamais
  remplacée par la date de notre passage ; `dernier_releve_reussi` ; `panne_depuis`."""
from __future__ import annotations

from ..composition import CONTRAT

NOM = "sources"
VERSION = 1
DEPEND = ()

COLONNES = ["point_acces", "source", "nom", "raison_nom", "url", "licence", "date_source",
            "raison_date_source", "dernier_releve_reussi", "raison_dernier_releve", "panne_depuis"]


def composer(ctx, ecr):
    """Écrit `sources.json.gz` à la racine de la publication (voir la description)."""
    noms: dict[str, dict] = {}
    for d in ctx.decisions.get("nom_point_acces", []):
        noms.setdefault(d.get("point_acces"), d)        # le premier nom donné pour un point
    cfg = {p["id"]: p for p in (ecr.points_acces or []) if p.get("id")}
    lignes = []
    for e in ecr.etat_points():
        p, c, d = e["point_acces"], cfg.get(e["point_acces"], {}), noms.get(e["point_acces"])
        nom = (d or {}).get("nom") or None
        raison_nom = None if nom else "aucun nom proposé dans references/nom_point_acces"
        lignes.append({"point_acces": p, "source": e["source"], "nom": nom, "raison_nom": raison_nom,
                       "url": c.get("url"), "licence": c.get("licence"),
                       **{k: e[k] for k in COLONNES[6:]}})
    connus = {l["point_acces"] for l in lignes}
    sans_point = [[p, d.get("nom"), d.get("fichier")] for p, d in sorted(noms.items(), key=lambda x: str(x[0]))
                  if p not in connus]
    if not lignes and not sans_point:
        return
    ecr.ecrire("sources.json.gz", {
        "contrat": CONTRAT, "publication": ecr.id_publication, "genere_le": ecr.genere_le,
        "raison": None if ecr.points_acces is not None else "configuration des points d'accès non transmise",
        "points_acces": {"colonnes": COLONNES, "lignes": [[l[k] for k in COLONNES] for l in lignes]},
        "noms_sans_point": {"colonnes": ["point_acces", "nom", "decision"], "lignes": sans_point}})
