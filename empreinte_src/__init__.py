"""
Traitement d'Empreinte politique : collecte des sources, entrepôt versionné, lecture, liaison,
composition des fiches, contrôles et publication.

Ce paquet est appelé par le workflow `.github/workflows/mise-a-jour.yml`, tâche par tâche,
au travers de la commande `empreinte` (module `empreinte_src.cli`). Le même code tourne en
local.

## Les étapes, et où elles sont

| Étape | Ce qu'elle fait | Modules |
| --- | --- | --- |
| E0 Démarrer | options, plan de la nuit, rattrapage d'une nuit non écrite | `cli`, `planification`, `rattrapage` |
| E1 Relever | télécharger les sources (requêtes conditionnelles, taille vérifiée, reprise sûre) | `transport`, `collecte` |
| E2 Dépaqueter et versionner | garder chaque fichier reçu à l'octet près, une version par changement | `depaquetage`, `entrepot` |
| E3 Lire | fichiers des sources → tables de faits (zone Z2) | `lecture`, `lecteurs` |
| E4 Relier | règles de liaison → graphe relié (zone Z3) | `liaison`, `regles`, `identites` |
| E5 Composer | fichiers servis des fiches, faits publiés | `composition`, `composeurs` |
| E6 Contrôler | contrôles bloquants avant publication, levée par décision | `controles` |
| E7 Publier | seule tâche qui écrit : entrepôt, export, publication | `distant`, `export` |
| E8 Rendre compte | rapport de la nuit, une issue par sujet d'alerte | `alertes`, `mesures` |

## Les zones de données

- **Z0, Z1** (`entrepot`) : les relevés et les fichiers reçus, versionnés ; c'est l'acquis,
  gardé pour toujours dans la release `entrepot` du dépôt.
- **ZI** (`identites`) : le registre des identités, en ajout seul.
- **ZD** (dossier `decisions/`) : les décisions de la propriétaire.
- **Z2** (`lecture`) : les faits lus, recalculés depuis Z1.
- **Z3** (`liaison`) : le graphe relié, recalculé à chaque mise à jour.
- **Z4** (`composition`) : les fichiers servis des fiches.

## Ajouter une source, un lecteur, une règle, une fiche

- une source : un point d'accès dans `config/points_acces.yaml` ;
- un lecteur : un module dans `empreinte_src/lecteurs/` (contrat dans `lecture`) ;
- une règle : un module dans `empreinte_src/regles/` (contrat dans `liaison`) ;
- une fiche : un module dans `empreinte_src/composeurs/` (contrat dans `composition`).

Chacun est découvert automatiquement ; aucun registre à mettre à jour.
"""
