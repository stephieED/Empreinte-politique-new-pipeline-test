# Empreinte politique — traitement de collecte (dépôt d'essai)

Dépôt d'essai de l'**étape 2** : réaliser et faire tourner chaque nuit le traitement proposé
pour Empreinte politique (collecte, entrepôt, lecture, contrôles, publication des données).
Ce n'est pas le dépôt du site ; rien n'est publié sur `empreinte-politique.fr`.

**À lire en ligne** : <https://stephieed.github.io/Empreinte-politique-new-pipeline-test/> mène à
la [documentation du code](https://stephieed.github.io/Empreinte-politique-new-pipeline-test/doc/),
à la description du traitement, aux livrables et à la
[page minimale de contrôle](https://stephieed.github.io/Empreinte-politique-new-pipeline-test/site/index.html)
(les fiches de la dernière nuit publiée). Mises à jour après chaque nuit publiée et chaque envoi de
code sur `main`.

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
| `config/` | les points d'accès aux sources (`points_acces.yaml`) et la forme attendue de chaque fichier servi (`schema_fichiers.yaml`, contrôlée par C4) |
| `decisions/` | les décisions de la propriétaire, un fichier par décision |
| `tests/` | les tests sans réseau et les extraits réels des sources qu'ils utilisent |
| `docs/` | la documentation de l'export des faits |
| `livrables/` | les documents de conception et de l'étape 2 : modèle, processus, justifications, questions ouvertes, recette (docs 0 à 8), cadrage, journal des changements, rapport de mesures, migration ; versés dans le dépôt le 13/11/2026 pour être publiés sur Pages |

Le fonctionnement d'ensemble (étapes, données, contrôles) est décrit dans les documents de
conception (`livrables/`) et sur la page « traitement », écrite à partir du code.

**Documentation du code** : générée par [pdoc](https://pdoc.dev) à partir des docstrings, servie
par Pages (lien en tête de ce fichier) et déposée à chaque envoi de code comme artefact
`documentation-code` (workflow *Tests*). En local :

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
| `publication` | les fichiers servis et la page minimale de chaque nuit, en une archive ; la dernière est servie par Pages (voir plus bas) |

Le contenu de l'entrepôt reste sous la licence de chaque source : Licence Ouverte pour
l'Assemblée nationale, le Sénat et le Journal officiel ; CC BY-SA pour Wikipédia ; CC0 pour
Wikidata ; CC BY pour le Parlement européen ; Licence Ouverte pour le Répertoire national des élus.

## Périmètre

Cahier des charges 4.1, sans les budgets (décision du 07/11/2026) ; les mandats locaux des
candidats y sont revenus le 13/11/2026. Les législatures et les gouvernements sont écrits une
seule fois, dans `empreinte_src/perimetre.py` :

| Objet | Périmètre |
| --- | --- |
| Législatures, groupes, lignées ; scrutins, amendements, dossiers, questions | XIVe à XVIIe (depuis le 20/06/2012) |
| Prises de parole en séance | XVe à XVIIe |
| Gouvernements, Journal officiel | depuis la XIVe (20/06/2012 ; décision du 13/11/2026), d'Ayrault II à aujourd'hui. Pour le JO : l'archive globale, relevée une fois, puis les livraisons quotidiennes |
| Sénat | mandats des sénateurs |
| Candidats | la liste des candidats déclarés selon franceinfo, recopiée à la main dans `decisions/candidature/` (la page n'est pas collectée) ; identité par Wikidata, jamais par le nom seul |
| Volet européen (candidats anciens eurodéputés) | mandats et groupes au Parlement européen (portail du Parlement européen) ; votes nominatifs depuis juillet 2019. Avant 2019 (Parltrack) : à venir |
| Mandats locaux des candidats | Répertoire national des élus (mandats en cours et sortants, depuis 2020) ; rattachement par prénom, nom et date de naissance, sinon par décision (`decisions/elu_local/`) |

Les budgets des gouvernements ne sont pas collectés : leur section est vide et le dit.

## Pages

Le workflow `Pages` (`.github/workflows/pages.yml`) sert, à
<https://stephieed.github.io/Empreinte-politique-new-pipeline-test/>, la documentation du code
(pdoc), la description du traitement (`traitement/` : étapes, périmètre, lecteurs, règles,
contrôles, écrite à partir du code par `empreinte_src/methodologie.py`), les documents de
`livrables/` convertis en HTML (`empreinte_src/pages_livrables.py`) et la page minimale de
contrôle avec les fichiers servis de la dernière publication. Il
tourne après chaque mise à jour sur `main` et après chaque envoi de code sur `main`. Ce n'est pas
le site : l'interface reste hors périmètre (décision du 13/11/2026).

## Lancer à la main

Onglet *Actions* → *Mise à jour* → *Run workflow* : mode `quotidien`, `complet` (relire toutes
les sources sans requête conditionnelle) ou `essai` (rien n'est écrit), et éventuellement une
liste de points d'accès (voir `config/points_acces.yaml`). Chaque essai a sa propre file et peut
tourner en même temps qu'un autre ; la nuit, `quotidien` et `complet` passent un par un (file
`mise-a-jour`). Un essai ne doit pas déborder sur la nuit (20 h 30 UTC).

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

La conception (modèle de données, processus, justifications, questions ouvertes, recette) est
dans `livrables/` ; le code de ce dépôt en est la réalisation. Le document 4 (estimations) est
remplacé par le rapport de mesures (`livrables/etape-2/3-rapport-de-mesures.md`, décision du
13/11/2026).

Licence : AGPL-3.0.
