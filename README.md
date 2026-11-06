# Empreinte politique — traitement de collecte (dépôt d'essai)

Dépôt d'essai de l'**étape 2** : réaliser et faire tourner chaque nuit le traitement proposé
pour Empreinte politique (collecte, entrepôt, lecture, contrôles, publication des données).
Ce n'est pas le dépôt du site ; rien n'est publié sur `empreinte-politique.fr`.

## Ce qui tourne

Le workflow `Mise à jour` (`.github/workflows/mise-a-jour.yml`) tourne chaque soir. Il a cinq
tâches, chacune avec ses droits minimaux :

| Tâche | Ce qu'elle fait | Droits |
| --- | --- | --- |
| `preparer` | vérifie les options, décide si la nuit est à faire | lecture |
| `collecter` | relève les sources, garde chaque fichier reçu à l'octet près, versionné | lecture |
| `calculer` | lecture, liaison, composition, contrôles (tranche 2) | lecture |
| `ecrire` | **seule tâche qui écrit** : dépose la génération dans l'entrepôt | `contents: write` |
| `alerter` | une issue par sujet d'alerte, fermée quand le sujet disparaît | `issues: write` |

L'**entrepôt** est la release `entrepot` de ce dépôt : relevés, index des versions, octets des
fichiers reçus, registres d'identité. Le fichier `manifeste.json` dit quelle est la génération
courante et l'empreinte de chaque fichier.

Le contenu de l'entrepôt reste sous la licence de chaque source (Licence Ouverte pour
l'Assemblée nationale, le Sénat et le Journal officiel ; CC BY-SA pour Wikipédia).

## Lancer à la main

Onglet *Actions* → *Mise à jour* → *Run workflow* : mode `quotidien`, `complet` (relire toutes
les sources sans requête conditionnelle) ou `essai` (rien n'est écrit), et éventuellement une
liste de points d'accès (voir `config/points_acces.yaml`).

En local :

```sh
pip install -e ".[test]"
python -m pytest -q                          # sans réseau
empreinte collecter --entrepot entrepot --points an-agenda-l17
empreinte reconstruire --entrepot entrepot --releve <id d'un relevé>
```

## Documentation

La conception (modèle de données, processus, justifications, estimations, recette) est
rédigée à part ; ce dépôt en est la réalisation.

Licence : AGPL-3.0.
