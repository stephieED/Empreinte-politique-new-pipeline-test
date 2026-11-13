# Empreinte politique — les données

<!-- À la migration vers le dépôt public : remplacer les adresses de Pages
     (stephieed.github.io/Empreinte-politique-new-pipeline-test) et l'état ci-dessous.
     Voir livrables/etape-2/migration-vers-le-vrai-depot.md. -->

**Empreinte politique** est un tableau de bord de la vie parlementaire et gouvernementale
française. Les institutions publient déjà leurs données, mais chacune de son côté. Le projet
**relie** ce qu'elles publient séparément : une personne, son groupe, un gouvernement, un texte,
un vote, un amendement, un décret. Puis il **le donne à voir** au grand public.

Ce dépôt contient **le traitement des données** : chaque nuit, il relève les sources publiques,
garde tout ce qu'il reçoit, relie les faits entre eux, vérifie le résultat et publie les fichiers
que lit le site. Le site est gratuit et sans publicité. Il est édité par une seule personne, sur
son temps libre.

> **État actuel** : le traitement est **en cours de validation**. Il tourne chaque nuit et publie
> ses données, mais ne sert pas encore `empreinte-politique.fr`.

## Ce que l'on trouve sur le site

- **Les groupes de l'Assemblée nationale**, suivis d'une législature à l'autre : leurs membres,
  leurs votes, leurs textes, leurs amendements, leurs prises de parole.
- **Les gouvernements** depuis 2012 : leur composition, leurs textes, leurs décrets.
- **Les législatures** depuis 2012 (XIVe à XVIIe).
- **Les candidats déclarés à l'élection présidentielle de 2027** : leur parcours et leur activité
  publique (Assemblée, Sénat, Parlement européen, mandats locaux).

## Les principes

- **Chaque fait publié renvoie à sa source primaire.**
- **Aucun jugement, aucun score, aucun classement**, ni des personnes ni des groupes.
- **Une donnée manquante reste manquante.** Elle n'est jamais remplacée par un zéro, et le site
  dit pourquoi elle manque.
- **Chaque lien entre deux objets est une règle écrite**, publiée avec sa description. On peut la
  relire et la vérifier.

## Les sources

| Source | Ce qui en vient | Licence |
| --- | --- | --- |
| Assemblée nationale | députés, groupes, mandats, scrutins, amendements, dossiers, questions, comptes rendus | Licence Ouverte |
| Sénat | sénateurs et leurs mandats | Licence Ouverte |
| Journal officiel (DILA) | lois, décrets et autres actes, depuis 2012 | Licence Ouverte |
| Parlement européen | mandats et votes des candidats anciens députés européens | CC BY 4.0 |
| Répertoire national des élus | mandats locaux des candidats | Licence Ouverte |
| Wikidata | identifiants qui relient une même personne d'une source à l'autre | CC0 |
| Wikipédia | dates de déclaration des candidats (détecteur d'écart) | CC BY-SA |

Chaque fichier reçu est gardé à l'octet près. Une erreur de lecture peut donc être corrigée
après coup, sans dépendre de ce que la source publie encore.

## Par où commencer

| Vous voulez… | Allez à |
| --- | --- |
| **comprendre** ce que fait le traitement | la [documentation](https://stephieed.github.io/Empreinte-politique-new-pipeline-test/doc/) : sa présentation, puis « Le traitement, étape par étape » |
| **consulter les données** | la release [`export`](../../releases/tag/export) : un fichier Parquet par nuit, une ligne par fait publié, avec ses identifiants de source ([description des colonnes](docs/export.md)) |
| **voir ce que charge une fiche** | la [page minimale de contrôle](https://stephieed.github.io/Empreinte-politique-new-pipeline-test/site/index.html), avec les fiches de la dernière nuit publiée |
| **lire les choix de conception** | la documentation, rubriques « Conception » et « Décisions » |
| **faire tourner le traitement** ou contribuer | [Exploiter le dépôt](docs/exploitation.md), puis la [documentation du code](https://stephieed.github.io/Empreinte-politique-new-pipeline-test/doc/empreinte_src.html) |

## En local

```sh
pip install -e ".[test]"
python -m pytest -q                       # tests sans réseau, sur des extraits réels des sources
empreinte collecter --entrepot entrepot --points an-agenda-l17
```

Le reste (les tâches de la nuit, les releases, le périmètre détaillé, le lancement à la main) est
dans [Exploiter le dépôt](docs/exploitation.md).

## Licence

Le code est publié sous licence **AGPL-3.0**. Les données gardent la licence de leur source (voir
le tableau ci-dessus).
