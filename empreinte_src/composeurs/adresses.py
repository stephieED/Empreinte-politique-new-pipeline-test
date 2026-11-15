"""Adresses de fiches citées par des articles publiés (issue #86 ; doc. 1, 1.7.2).

La forme des adresses des fiches est libre (décision de la propriétaire du 14/11/2026), sauf
pour douze adresses de l'ancien site citées par des articles datés, qui ne seront plus modifiés
(`/groupes/AN-SOC`, `/gouvernements/LECORNU_II`…). Elles doivent continuer à mener à la bonne
fiche, quelle que soit son adresse.

La correspondance est une décision de la propriétaire (`decisions/adresse_citee/`) : chaque
adresse citée y désigne sa fiche par un **identifiant stable**, jamais par une adresse lisible,
pour qu'un renommage ne la casse pas :

- une lignée par son identifiant `lig:…` (registre des lignées, R-LIGNEE), résolu vers son
  adresse active (une lignée fusionnée dans une autre mène à celle qui l'a reçue) ;
- un gouvernement par son organe `PO…` (R-GOUVERNEMENTS).

Ce composeur n'écrit aucune fiche : il inscrit chaque correspondance auprès de l'Ecrivain, qui la
sert dans le catalogue (`catalogue.json.gz`, table `adresses_citees` ; colonne `lien` vérifiée
par C2). Une adresse dont la fiche n'est pas publiée garde un `lien` vide et sa raison, et A7 la
signale : un lien faux est pire qu'un lien absent (cahier 4.7)."""
from __future__ import annotations

NOM = "adresses"
VERSION = 1
DEPEND = ("R-LIGNEE", "R-GOUVERNEMENTS")

# type de fiche → (table, colonne de l'identifiant stable, colonne de l'adresse)
TABLES = {"lignee": ("lignee", "lignee", "adresse"),
          "gouvernement": ("gouvernement", "organe", "adresse")}


def composer(ctx, ecr):
    """Résout chaque décision `adresse_citee` vers une fiche et l'inscrit auprès de `ecr`."""
    for d in ctx.decisions.get("adresse_citee", []):
        type_fiche, objet = d.get("type_fiche"), d.get("objet")
        cible, raison = None, None
        if type_fiche not in TABLES:
            raison = f"type de fiche inconnu : {type_fiche}"
        else:
            table, col_id, col_adr = TABLES[type_fiche]
            if type_fiche == "lignee" and ctx.existe("lignee_adresse"):
                # une lignée fusionnée dans une autre mène à la lignée qui l'a reçue (registre)
                objet = (ctx.x("SELECT any_value(lignee) FROM lignee_adresse WHERE lignee_inscrite = ?",
                               [objet])[0][0] or objet)
            rows = ctx.x(f"SELECT {col_adr} FROM {table} WHERE {col_id} = ?", [objet]) \
                if ctx.existe(table) else []
            if rows and rows[0][0]:
                cible = f"{type_fiche}/{rows[0][0]}"
            else:
                raison = f"{objet} introuvable dans les {type_fiche}s"
        ecr.citer(d.get("adresse"), cible, d.get("fichier"), raison)
