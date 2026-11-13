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
| `empreinte_src/perimetre.py` | le périmètre publié, en un seul endroit : législatures, paroles, gouvernements (voir plus bas) |
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

Ce qu'écrit la tâche `ecrire`, une release par usage :

| Release | Contenu |
| --- | --- |
| `entrepot` | l'**entrepôt** : relevés, index des versions, octets des fichiers reçus, registres d'identité. `manifeste.json` dit quelle est la génération courante et l'empreinte de chaque fichier |
| `archives-brutes` | les archives reçues trop grosses pour être rechargées chaque nuit, gardées à l'octet près : l'archive globale du Journal officiel (1,75 Go, depuis 1861). Elles ne servent qu'à refaire un découpage ; `restaurer` ne les rapatrie que sur demande (`avec_brutes`) |
| `export` | l'**export des faits** : les faits publiés de chaque nuit, et tous les faits lus de la dernière nuit (une ligne par fait, documenté dans [`docs/export.md`](docs/export.md)) |
| `publication` | les fichiers servis et la page minimale de chaque nuit, en une archive (aucun déploiement Pages ici) |

Le contenu de l'entrepôt reste sous la licence de chaque source : Licence Ouverte pour
l'Assemblée nationale, le Sénat et le Journal officiel ; CC BY-SA pour Wikipédia ; CC0 pour
Wikidata ; CC BY pour le Parlement européen.

## Périmètre

Cahier des charges 4.1, sans budgets ni mandats locaux (décision du 07/11/2026), écrit une seule
fois dans `empreinte_src/perimetre.py` :

| Objet | Périmètre |
| --- | --- |
| Législatures, groupes, lignées ; scrutins, amendements, dossiers, questions | XIVe à XVIIe (depuis le 20/06/2012) |
| Prises de parole en séance | XVe à XVIIe |
| Gouvernements, Journal officiel | depuis la XIVe (20/06/2012 ; décision du 13/11/2026), d'Ayrault II à aujourd'hui. Pour le JO : l'archive globale, relevée une fois, puis les livraisons quotidiennes |
| Sénat | mandats des sénateurs |
| Candidats | la liste tenue dans `decisions/candidature/` ; volet européen pour les anciens eurodéputés |

Les budgets des gouvernements ne sont pas collectés : leur section est vide et le dit.

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
