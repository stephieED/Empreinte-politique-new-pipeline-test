# Empreinte politique — proposition de modèle de données et de processus

Réponse à la mission décrite en partie 0 du cahier des charges (version du 04/11/2026).
Livrables rédigés le 04/11/2026, à partir du cahier, des captures et de **mesures faites ce
jour-là sur les sources publiques** (aucun accès au site, à son code ni à ses données).

## En une page

**L'idée centrale** : ne conserver pour toujours que trois choses, ce qu'on a **relevé** aux
sources, les **objets sources versionnés** qu'on en a tirés (un acteur, un scrutin, un
amendement… gardé à nouveau seulement quand il change), et les **décisions** de la
propriétaire. Tout le reste (faits lus, liens, positions, comptes, fiches) est **recalculé**
à chaque mise à jour. Cela donne, sans mécanisme supplémentaire :

- une collecte incrémentale (on ne relit que les objets dont l'empreinte a changé) ;
- des corrections de lecture et des champs nouveaux qui atteignent tout l'historique sans
  recollecte ;
- la distinction entre un **retrait à la source** (objet absent d'un relevé complet) et une
  **panne** (relevé incomplet : rien ne change, la fiche dit « panne depuis le … ») ;
- l'histoire des champs que l'archive courante de l'Assemblée réécrit chaque nuit (siège,
  libellés, positions).

**Le processus** : neuf étapes chaque soir, de E0 à E8 : démarrer, relever, découper et
versionner, lire, relier et dériver, composer, contrôler, publier, rendre compte.
L'acquisition est enregistrée avant tout calcul. Sept contrôles bloquent la publication, dont
les faits perdus sans explication, nommés un par un, et les données interdites ; huit
autres alertent sans bloquer. La propriétaire peut lever une anomalie précise par une
décision tracée. Les alertes arrivent comme des issues du dépôt privé, une par sujet.

**L'hébergement, sans coût** : Python, DuckDB et Parquet sur GitHub Actions (dépôt public).
L'entrepôt et le magasin des publications sont des actifs de *releases*, le site est servi
par GitHub Pages et la traçabilité tient dans un registre chaîné d'empreintes.

## Chiffres à retenir

Ce sont des estimations. Le détail, la méthode et le statut de chaque chiffre (mesuré,
calculé ou supposé) sont dans le document 4.

| | Estimation |
| --- | --- |
| Entrepôt au premier remplissage | 1,6 à 2,2 Go, puis environ 0,9 Go de plus par an |
| Premier remplissage | environ 6,1 Go téléchargés, 3 à 7 h réparties sur 5 ou 6 tâches, moins de 2 Go de mémoire |
| Mise à jour du soir | environ 549 Mo téléchargés, 25 à 50 min, environ 1,1 Go de mémoire au plus fort |
| Chargement initial d'une fiche | moins de 1 Ko compressé ; la personne la plus active, toutes sections ouvertes : 75 Ko |
| Site servi | environ 0,2 Go avec des fichiers pré-compressés ; non compressé, il dépasserait la limite de 1 Go de GitHub Pages pendant la XVIIe |
| Coût | 0 € sur le dépôt public |

## Ce que les mesures ont changé

Les mesures du 04/11/2026 contredisent plusieurs points du cahier :

- **Positions des groupes** : aucun des 14 groupes de la XVIIe ne déclare sa position.
- **Parltrack** : il ne se met plus à jour depuis le 24/07/2026, mais il garde ses archives
  depuis 2019.
- **Transferts de l'Assemblée** : ils sont coupés avec un statut 200, ce qui oblige à
  vérifier la taille reçue.
- **Prises de parole** : l'identifiant de paragraphe des comptes rendus est stable dans 97 à
  99 % des cas. C'est le rang qui est renuméroté.
- **Lien scrutin → dossier** : il atteint 95 % des scrutins de la XVIIe par la séance, alors
  que les références directes n'en relient que 41 %.
- **Signataires du JO** : le champ `SIGNATAIRES` existe, en texte libre.
- **Copies d'amendements** : elles ne divergent pas dans l'archive de la XVIIe.

Le détail est dans les documents 3 et 8 et dans `annexes/mesures/`.

## Les documents

| # | Document | Pour |
| --- | --- | --- |
| 1 | [Modèle de données](1-modele-de-donnees.md) | la spécification : objets, identifiants, relations, stocké/dérivé, données servies, évolution |
| 2 | [Processus de collecte et de publication](2-processus-collecte-publication.md) | la spécification : étapes, cadence, pannes, contrôles, publication, exploitation |
| 3 | [Justifications](3-justifications.md) | chaque choix, les alternatives écartées, et là où le cahier paraît trop étroit |
| 4 | [Estimations](4-estimations.md) | volumes, poids par fiche, durées, mémoire, coût, avec leur méthode |
| 5 | [Questions ouvertes](5-questions-ouvertes.md) | ce qui reste à trancher, ce que ça bloque, ce qu'on fait en attendant |
| 6 | [Le processus, illustré](6-doc-processus.md) | comprendre le fonctionnement d'ensemble, schémas à l'appui |
| 7 | [Le modèle, illustré](7-doc-modele.md) | comprendre les objets et comment une fiche se compose |
| 8 | [Recette](8-recette.md) | les tables de la partie 7 : besoins, règles, pièges, exigences, scénarios |
| — | [annexes/mesures](annexes/mesures/) et [annexes/scripts](annexes/scripts/) | les rapports de mesure et les scripts qui fondent les chiffres |

Ordre de lecture conseillé : ce fichier, puis les documents 7 et 6 (illustrés), puis 5
(questions), puis les spécifications 1 et 2 au besoin.

## Périmètre de ce qui a été fait

- **Mesures** : sur les sources publiques de la partie 3 et la documentation de GitHub,
  le 04/11/2026, depuis une connexion domestique (les temps de téléchargement ne valent pas
  pour GitHub Actions).
- **Prototype** : un prototype de composition, limité et déclaré, a servi à mesurer des
  poids de fiche. Il couvre la XVIIe, les votes des XIVe à XVIIe, trois personnes, le groupe
  socialiste de la XVIIe, un gouvernement et la XVIIe législature.
- **Ce qui n'a pas été fait** : aucun code de production n'a été écrit. Le dump global du
  Journal officiel (1,67 Go) n'a pas été téléchargé ; sa part dans les estimations est
  extrapolée.
- **Questions tranchées le 04/11/2026** par la propriétaire :
  - l'entrepôt est public ;
  - la fenêtre d'interdiction court du lundi au vendredi, de 9 h à 19 h, jours fériés
    exclus ;
  - les paroles d'un gouvernement comptent pendant la fonction et en qualité de membre du
    gouvernement.
