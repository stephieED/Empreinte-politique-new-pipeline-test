# Empreinte politique — traitement de collecte (dépôt d'essai)

Dépôt d'essai de l'**étape 2** : réaliser et faire tourner chaque nuit le traitement proposé
pour Empreinte politique (collecte, entrepôt, lecture, contrôles, publication des données).
Ce n'est pas le dépôt du site ; rien n'est publié sur `empreinte-politique.fr`.

## Où est quoi

| Dossier | Contenu |
| --- | --- |
| `empreinte_src/` | le code du traitement (Python) ; la commande installée s'appelle `empreinte` |
| `empreinte_src/lecteurs/` | un lecteur par famille de données : fichiers des sources → tables de faits |
| `empreinte_src/regles/` | une règle de liaison par fichier ; sa `DESCRIPTION` est le texte de la page de méthodologie |
| `empreinte_src/composeurs/` | un composeur par type de fiche : règles → fichiers servis |
| `empreinte_src/site/` | la page minimale qui affiche les fichiers servis (contrôle, pas l'interface du site) |
| `.github/workflows/` | la mise à jour du soir et les tests |
| `config/` | les points d'accès aux sources et les réglages |
| `decisions/` | les décisions de la propriétaire, un fichier par décision |
| `tests/` | les tests sans réseau et les extraits réels des sources qu'ils utilisent |
| `docs/` | la documentation de l'export des faits |

Le fonctionnement d'ensemble (étapes, données, contrôles) est décrit dans les documents de
conception, rédigés à part.

**Documentation du code** : générée par [pdoc](https://pdoc.dev) à partir des docstrings, à
chaque envoi de code (workflow *Tests*, artefact `documentation-code`). En local :

```sh
pip install -e ".[doc]"
pdoc ./empreinte_src --docformat markdown    # ouvre la documentation dans le navigateur
```

## Ce qui tourne

Le workflow `Mise à jour` (`.github/workflows/mise-a-jour.yml`) tourne chaque soir. Il a cinq
tâches, chacune avec ses droits minimaux :

| Tâche | Ce qu'elle fait | Droits |
| --- | --- | --- |
| `preparer` | vérifie les options, décide si la nuit est à faire | lecture |
| `collecter` | relève les sources, garde chaque fichier reçu à l'octet près, versionné | lecture |
| `calculer` | lecture des fichiers collectés, règles de liaison, composition des fiches, contrôles, export des faits | lecture |
| `ecrire` | **seule tâche qui écrit** : dépose la génération dans l'entrepôt | `contents: write` |
| `alerter` | une issue par sujet d'alerte, fermée quand le sujet disparaît | `issues: write` |

L'**entrepôt** est la release `entrepot` de ce dépôt : relevés, index des versions, octets des
fichiers reçus, registres d'identité. Le fichier `manifeste.json` dit quelle est la génération
courante et l'empreinte de chaque fichier.

L'**export des faits** de chaque nuit est dans la release `export` (une ligne par fait,
documenté dans [`docs/export.md`](docs/export.md)).

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
# rapport de mesures (commande, section 5) : relit l'artefact `rapport` de chaque nuit
empreinte rapport-mesures --depot <propriétaire/dépôt> --cache mesures --sortie rapport-de-mesures.md
```

## Documentation

La conception (modèle de données, processus, justifications, estimations, recette) est
rédigée à part ; ce dépôt en est la réalisation.

Licence : AGPL-3.0.
