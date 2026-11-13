# Rapport de mesures (commande de réalisation, section 5)

Généré le 13/11/2026 à 13 h 53 UTC par `empreinte rapport-mesures` à partir du rapport de chaque mise à jour qui
écrit (artefact `rapport` des exécutions de `stephieED/Empreinte-politique-new-pipeline-test`), et des durées de tâches publiées par GitHub
Actions. Toutes les mesures sont prises **sur GitHub Actions** (machine `ubuntu-latest` d'un dépôt
public), aucune sur une connexion domestique. Une case vide (« — ») est une mesure absente du rapport
de cette nuit, jamais un zéro.

**Population.** Chaque ligne est une génération de l'entrepôt (`gN`) : une mise à jour en mode
`quotidien` (« nuit » : déclenchement planifié ; « à la main » : lancée à la main). Les essais
(`mode=essai`) n'écrivent rien et ne sont pas comptés. Le périmètre a changé pendant la période
(journal des changements) : XVIIe seule jusqu'à g8, archives closes XIVe–XVIe à partir de g9,
gouvernements et fiches de législature XIVe–XVIIe à partir de g10 ; voir le journal pour la suite.
**Aucune de ces nuits ne compte encore dans la série des sept nuits** : le périmètre de validation n'est pas complet en production.

**Pic de mémoire.** Maximum des pics des étapes d'une tâche (`VmHWM` du processus, remis à zéro au
début de chaque étape). Le `Maximum resident set size` de `time -v` du journal des tâches ne vaut
que pour la dernière étape et n'est pas repris ici.

## Durée et pic de mémoire de chaque mise à jour

Méthode : durées des tâches selon GitHub (du début à la fin de chaque tâche) ; mise à jour entière : du début de la première tâche à la fin de la dernière. Pics en Go (1 Go = 1 024 Mo).

| Nuit | Début (UTC) | Déclenchement | Code | Collecte | Calcul | Écriture | Mise à jour entière | Pic collecte | Pic calcul (étape) | Publication | Fiches | Faits publiés |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| g1 | 06/11 14:23 | à la main | `508af32` | 18 min 13 s | 2 s | 37 s | 19 min 35 s | 0,8 | — | — | — | — |
| g2 | 06/11 16:44 | à la main | `25d2275` | 3 min 57 s | 3 min 42 s | 1 min 35 s | 9 min 53 s | 1,1 | 2,3 (export) | autorisée | 6 | 44 561 |
| g3 | 07/11 06:54 | à la main | `87c1e61` | 1 min 16 s | 6 min 02 s | 1 min 30 s | 9 min 29 s | 0,9 | 3,8 (E5) | **refusée** | 52 | 617 647 |
| g4 | 07/11 20:35 | nuit | `6f603d0` | 1 min 09 s | 6 min 03 s | 1 min 14 s | 9 min 02 s | 0,9 | 3,6 (E5) | autorisée | 52 | 617 935 |
| g5 | 08/11 20:35 | nuit | `6f603d0` | 3 min 34 s | 5 min 59 s | 1 min 03 s | 11 min 19 s | 1,1 | 3,6 (E5) | **refusée** | 52 | 617 935 |
| g6 | 09/11 20:35 | nuit | `6f603d0` | 5 min 06 s | 6 min 15 s | 1 min 18 s | 13 min 24 s | 1,1 | 3,6 (E5) | autorisée | 53 | 618 439 |
| g7 | 10/11 20:35 | nuit | `6f603d0` | 1 min 17 s | 6 min 31 s | 35 s | 9 min 10 s | 0,9 | 3,6 (E5) | **refusée** | 53 | 617 011 |
| g8 | 11/11 21:04 | nuit | `6f603d0` | 1 min 39 s | 5 min 58 s | 1 min 06 s | 9 min 34 s | 1,1 | 3,7 (E5) | autorisée | 53 | 618 337 |
| g9 | 12/11 20:36 | nuit | `4d241fa` | 2 h 13 min | 4 min 34 s | 1 min 46 s | 2 h 20 min | 2,5 | 3,9 (E5) | autorisée | 53 | 624 420 |
| g10 | 13/11 06:33 | à la main | `e1819fc` | 1 h 06 min | 10 min 06 s | 1 min 36 s | 1 h 19 min | 1,4 | 4,7 (E4) | autorisée | 56 | 1 766 930 |

## Durée et pic de mémoire de chaque étape du calcul

Méthode : mesures du traitement (`mesures.Mesures`) ; E3 additionne les lecteurs, son pic est le plus haut d'entre eux. E3 lecture, export de tous les faits lus, E4 règles, E5 fiches, E6 contrôles. Durée, puis pic en Go.

| Nuit | E3 | export | E4 | E5 | E6 |
| --- | ---: | ---: | ---: | ---: | ---: |
| g2 | 1 min 25 s · 1,9 | 1 min 29 s · 2,3 | 3 s · 1,3 | 3 s · 1,3 | 1 s · 1,1 |
| g3 | 10 s · 2,0 | 2 min 19 s · 2,3 | 13 s · 2,7 | 1 min 02 s · 3,8 | 1 min 11 s · 3,3 |
| g4 | 10 s · 2,0 | 2 min 22 s · 2,3 | 15 s · 2,8 | 1 min 11 s · 3,6 | 53 s · 3,3 |
| g5 | 10 s · 2,2 | 2 min 19 s · 2,3 | 14 s · 2,8 | 1 min 03 s · 3,6 | 1 min 13 s · 3,4 |
| g6 | 10 s · 2,2 | 2 min 07 s · 2,4 | 11 s · 2,8 | 56 s · 3,6 | 1 min 41 s · 3,5 |
| g7 | 10 s · 2,0 | 2 min 38 s · 2,2 | 14 s · 2,8 | 1 min 02 s · 3,6 | 1 min 06 s · 3,2 |
| g8 | 12 s · 2,2 | 2 min 24 s · 2,4 | 14 s · 2,7 | 1 min 04 s · 3,7 | 57 s · 3,5 |
| g9 | 9 s · 2,3 | 1 min 32 s · 2,7 | 9 s · 2,9 | 46 s · 3,9 | 51 s · 3,7 |
| g10 | 3 min 18 s · 4,0 | 34 s · 3,0 | 25 s · 4,7 | 2 min 49 s · 3,0 | 1 min 44 s · 2,6 |

## Octets téléchargés et durée de relevé par source

Méthode : somme des octets reçus par les relevés de la nuit (`octets_recus`), en Mo (10⁶ octets) ; durée des relevés de la source (mesure E1-E2 de chaque point : téléchargement, vérification, découpage ; les points d'une source sont relevés l'un après l'autre). Une requête conditionnelle qui répond « inchangé » ne reçoit rien.

| Nuit | an | senat | dila | wikidata | wikipedia | Total | Points en panne |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| g1 | 537,2 · 1 min 42 s | 0,0 · 12 min 34 s | 134,3 · 3 min 26 s | 0,0 · — | 0,1 · 0 s | 671,6 | `senat-export` |
| g2 | 373,6 · 3 min 03 s | 8,6 · 10 s | 0,0 · 1 s | 4,3 · 7 s | 0,1 · 0 s | 386,6 | — |
| g3 | 539,8 · 36 s | 0,0 · 1 s | 5,5 · 10 s | 4,3 · 4 s | 0,1 · 0 s | 549,8 | `senat-export` |
| g4 | 405,5 · 31 s | 0,0 · 1 s | 5,3 · 8 s | 4,3 · 2 s | 0,1 · 0 s | 415,2 | `senat-export` |
| g5 | 540,7 · 2 min 55 s | 8,6 · 9 s | 1,6 · 3 s | 4,3 · 6 s | 0,1 · 0 s | 555,4 | — |
| g6 | 541,4 · 4 min 13 s | 8,6 · 13 s | 3,9 · 7 s | 4,3 · 10 s | 0,1 · 0 s | 558,4 | — |
| g7 | 542,7 · 41 s | 0,0 · 2 s | 0,1 · 1 s | 4,3 · 7 s | 0,1 · 0 s | 547,3 | `senat-export` |
| g8 | 543,1 · 53 s | 8,6 · 10 s | 5,9 · 8 s | 4,3 · 8 s | 0,1 · 0 s | 562,1 | — |
| g9 | 1 800,8 · 2 h 12 min | 8,6 · 10 s | 1,4 · 3 s | 4,3 · 4 s | 0,1 · 0 s | 1 815,3 | `an-amendements-l15`, `an-amendements-l16`, `an-syceron-l15` |
| g10 | 1 101,8 · 1 h 05 min | 8,6 · 12 s | 0,2 · 2 s | 4,3 · 20 s | 0,1 · 0 s | 1 115,1 | `an-amendements-l15`, `an-amendements-l16` |

## Objets nouveaux ou modifiés par nuit, par famille

Méthode : nouvelles versions de fichiers de la source rangées dans l'entrepôt (`nb_nouvelles_versions` des relevés : un fichier nouveau ou dont les octets ont changé), par famille de points d'accès, toutes législatures confondues. Le premier relevé d'un point n'est pas compté ici (tableau du premier remplissage). Entre parenthèses : fichiers retirés à la source, quand il y en a.

| Famille | g1 | g2 | g3 | g4 | g5 | g6 | g7 | g8 | g9 | g10 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `an-acteurs` | — | 0 | 72 | 0 | 10 | 5 | 111 | 46 | 5 | 40 |
| `an-agenda` | — | 40 | 67 | 0 | 0 | 33 | 108 | 78 | 63 | 76 |
| `an-amendements` | — | 2 027 | 313 | 281 | 15 | 548 | 610 | 146 | 2 339 | 247 |
| `an-dossiers` | — | 171 | 12 | 25 | 0 | 12 | 113 | 21 | 45 | 40 |
| `an-questions-ecrites` | — | 0 | 0 | 0 | 480 | 0 | 290 | 294 | 6 | 0 |
| `an-questions-gouvernement` | — | 0 | 0 | 0 | 69 | 0 | 0 | 0 | 0 | 0 |
| `an-questions-orales` | — | 0 | 0 | 0 | 23 | 0 | 0 | 0 | 0 | 0 |
| `an-scrutins` | — | 0 | 5 | 0 | 0 | 10 | 42 | 5 | 67 | 25 |
| `an-syceron` | — | 0 | 11 | 0 | 2 | 4 | 6 | 4 | 3 | 7 |
| `jo-livraisons` | — | 0 | 3 436 | 2 516 | 550 | 830 | 235 | 1 580 | 273 | 907 |
| `senat-export` | 0 | — | 0 | 0 | 1 | 1 | 0 | 1 | 1 | 1 |
| `wd-identifiants-parlementaires` | — | — | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `wp-candidatures-2027` | — | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |

## Taille de l'entrepôt et croissance par nuit

Méthode : somme des octets des fichiers de l'entrepôt après l'écriture de la nuit (`entrepot_octets`, release `entrepot`, archives brutes comprises si elles y sont), en Mo.

| Nuit | Entrepôt (Mo) | Croissance (Mo) |
| --- | ---: | ---: |
| g1 | 266,6 | — |
| g2 | 283,6 | +16,9 |
| g3 | 299,3 | +15,8 |
| g4 | 311,9 | +12,6 |
| g5 | 332,4 | +20,5 |
| g6 | 353,6 | +21,1 |
| g7 | 365,8 | +12,2 |
| g8 | 389,1 | +23,3 |
| g9 | 734,8 | +345,8 |
| g10 | 864,0 | +129,1 |

## Écritures dans les releases

Méthode : chaque envoi d'un fichier par la tâche `ecrire` (`gh release upload`), avec sa durée, son nombre d'essais et sa réussite. Une nuit refusée n'écrit que l'entrepôt.

| Nuit | Release | Envois | Mo | Durée totale | Plus long | Réessais | Échecs |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| g1 | `entrepot` | 10 | 266,6 | 19 s | 4 s | 0 | 0 |
| g2 | `entrepot` | 11 | 672,1 | 38 s | 15 s | 0 | 0 |
| g3 | `entrepot` | 14 | 27,5 | 17 s | 2 s | 0 | 0 |
| g4 | `entrepot` | 7 | 24,4 | 11 s | 2 s | 0 | 0 |
| g4 | `export` | 3 | 672,7 | 26 s | 14 s | 0 | 0 |
| g4 | `publication` | 1 | 47,9 | 3 s | 3 s | 0 | 0 |
| g5 | `entrepot` | 7 | 32,6 | 11 s | 2 s | 0 | 0 |
| g6 | `entrepot` | 9 | 33,2 | 15 s | 2 s | 0 | 0 |
| g6 | `export` | 3 | 673,5 | 28 s | 16 s | 0 | 0 |
| g6 | `publication` | 1 | 47,9 | 3 s | 3 s | 0 | 0 |
| g7 | `entrepot` | 7 | 24,4 | 9 s | 2 s | 0 | 0 |
| g8 | `entrepot` | 7 | 35,5 | 9 s | 2 s | 0 | 0 |
| g8 | `export` | 3 | 675,9 | 19 s | 10 s | 0 | 0 |
| g8 | `publication` | 1 | 47,9 | 3 s | 3 s | 0 | 0 |
| g9 | `entrepot` | 11 | 358,1 | 25 s | 4 s | 0 | 0 |
| g9 | `export` | 3 | 682,9 | 30 s | 15 s | 0 | 0 |
| g9 | `publication` | 1 | 48,2 | 4 s | 4 s | 0 | 0 |
| g10 | `entrepot` | 8 | 150,2 | 13 s | 3 s | 0 | 0 |
| g10 | `export` | 2 | 1 056,4 | 29 s | 25 s | 0 | 0 |
| g10 | `publication` | 1 | 157,3 | 9 s | 9 s | 0 | 0 |

## Poids téléchargé par fiche de candidat

Méthode : octets compressés (gzip) servis, comme les compte la page de contrôle : chargement initial = l'en-tête `fiche.json` ; toutes sections ouvertes = en-tête et toutes les sections. Population : les fiches de candidat composées cette nuit-là (publiées si la publication est autorisée). En Ko (10³ octets).

| Nuit | Fiches | Initial, médiane | Initial, max | Ouvertes, médiane | Ouvertes, max | Ouvertes, toutes fiches |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| g3 | 28 | 4,8 | 8,7 | 11,1 | 179,7 | 894,7 |
| g4 | 28 | 4,8 | 8,7 | 11,1 | 179,7 | 895,4 |
| g5 | 28 | 4,8 | 8,7 | 11,1 | 179,7 | 895,2 |
| g6 | 29 | 4,8 | 8,7 | 11,1 | 179,7 | 906,3 |
| g7 | 29 | 4,8 | 8,7 | 11,1 | 179,7 | 906,5 |
| g8 | 29 | 4,8 | 8,7 | 11,1 | 179,7 | 906,1 |
| g9 | 29 | 4,8 | 8,7 | 11,1 | 179,7 | 906,3 |
| g10 | 29 | 5,0 | 10,9 | 11,4 | 590,2 | 3 638,5 |

Détail de la dernière nuit (g10), du plus lourd au plus léger :

| Fiche | Initial (Ko) | Toutes sections ouvertes (Ko) |
| --- | ---: | ---: |
| `candidat/francois-ruffin` | 9,3 | 590,2 |
| `candidat/gabriel-attal` | 9,6 | 548,2 |
| `candidat/jean-luc-melenchon` | 7,7 | 449,3 |
| `candidat/delphine-batho` | 10,9 | 420,2 |
| `candidat/edouard-philippe` | 7,5 | 334,0 |
| `candidat/fabien-roussel` | 7,8 | 294,0 |
| `candidat/marine-le-pen` | 8,9 | 288,7 |
| `candidat/nicolas-dupont-aignan` | 8,2 | 227,3 |
| `candidat/olivier-becht` | 8,8 | 161,4 |
| `candidat/bruno-retailleau` | 6,8 | 81,8 |
| `candidat/xavier-bertrand` | 7,2 | 39,1 |
| `candidat/francois-asselineau` | 5,0 | 11,4 |
| `candidat/raphael-glucksmann` | 5,0 | 11,4 |
| `candidat/florian-philippot` | 5,0 | 11,4 |
| `candidat/karim-bouamrane` | 5,0 | 11,4 |
| `candidat/nathalie-arthaud` | 5,0 | 11,4 |
| `candidat/sylvain-durif` | 5,0 | 11,4 |
| `candidat/marine-tondelier` | 5,0 | 11,4 |
| `candidat/david-lisnard` | 5,0 | 11,4 |
| `candidat/francis-lalanne` | 5,0 | 11,4 |
| `candidat/anasse-kazib` | 5,0 | 11,4 |
| `candidat/eric-zemmour` | 5,0 | 11,4 |
| `candidat/natacha-polony` | 5,0 | 11,4 |
| `candidat/teddy-riner` | 5,0 | 11,4 |
| `candidat/mira-markovic` | 4,9 | 11,2 |
| `candidat/benoit-mathieu` | 4,9 | 11,2 |
| `candidat/gilles-platret` | 4,9 | 11,2 |
| `candidat/manolo-mlekuz` | 4,9 | 11,2 |
| `candidat/selma-labib` | 4,9 | 11,2 |

## Premier remplissage

Méthode : premier relevé réussi de chaque point d'accès dans la période (les nuits suivantes ne rapportent que ce qui change). Durée du relevé (téléchargement, vérification, découpage), octets reçus, fichiers découpés.

| Nuit | Point d'accès | Mo reçus | Durée | Fichiers |
| --- | ---: | ---: | ---: | ---: |
| g1 | `an-amo30-l17` | 13,7 | 3 s | 14 056 |
| g1 | `an-scrutins-l17` | 30,2 | 4 s | 9 759 |
| g1 | `an-dossiers-l17` | 11,1 | 1 s | 10 975 |
| g1 | `an-amendements-l17` | 351,9 | 31 s | 144 112 |
| g1 | `an-syceron-l17` | 61,5 | 49 s | 657 |
| g1 | `an-agenda-l17` | 8,7 | 2 s | 8 263 |
| g1 | `an-questions-ecrites-l17` | 51,2 | 8 s | 19 515 |
| g1 | `an-questions-gouvernement-l17` | 5,6 | 4 s | 1 857 |
| g1 | `an-questions-orales-l17` | 3,3 | 0 s | 828 |
| g1 | `jo-livraisons` (62 livraisons) | 134,3 | 3 min 26 s | 169 352 |
| g1 | `wp-candidatures-2027` | 0,1 | 0 s | 1 |
| g2 | `senat-export` | 8,6 | 10 s | 1 |
| g2 | `wd-identifiants-parlementaires` | 4,3 | 7 s | 1 |
| g9 | `an-amo30-l16` | 11,9 | 11 s | 12 589 |
| g9 | `an-scrutins-l16` | 10,1 | 9 s | 4 106 |
| g9 | `an-dossiers-l16` | 9,1 | 4 s | 9 090 |
| g9 | `an-syceron-l16` | 57,6 | 23 s | 605 |
| g9 | `an-agenda-l16` | 7,9 | 7 s | 8 320 |
| g9 | `an-questions-ecrites-l16` | 46,6 | 24 s | 18 710 |
| g9 | `an-questions-gouvernement-l16` | 6,1 | 23 s | 1 940 |
| g9 | `an-questions-orales-l16` | 3,0 | 0 s | 833 |
| g9 | `an-amo30-l15` | 15,7 | 1 min 46 s | 10 954 |
| g9 | `an-scrutins-l15` | 9,2 | 1 s | 4 417 |
| g9 | `an-dossiers-l15` | 15,2 | 1 s | 15 486 |
| g9 | `an-agenda-l15` | 38,3 | 20 s | 55 283 |
| g9 | `an-questions-ecrites-l15` | 248,0 | 28 min 34 s | 45 665 |
| g9 | `an-questions-gouvernement-l15` | 14,6 | 10 s | 4 851 |
| g9 | `an-questions-orales-l15` | 6,5 | 2 s | 1 716 |
| g9 | `an-amo20-l14` | 0,9 | 1 s | 1 |
| g9 | `an-scrutins-l14` | 0,7 | 1 s | 1 |
| g9 | `an-dossiers-l14` | 2,6 | 1 s | 1 |
| g9 | `an-amendements-l14` | 103,7 | 1 min 06 s | 1 |
| g9 | `an-agenda-l14` | 1,0 | 1 s | 1 |
| g9 | `an-questions-ecrites-l14` | 195,8 | 6 min 53 s | 1 |
| g9 | `an-questions-gouvernement-l14` | 8,4 | 3 s | 1 |
| g9 | `an-questions-orales-l14` | 4,3 | 6 s | 1 |
| g10 | `an-syceron-l15` | 149,0 | 2 min 47 s | 1 562 |

g1 : 11 points relevés pour la première fois, 671,6 Mo, 5 min 09 s de relevé ; relevés en échec 12 min 34 s ; collecte entière 18 min 13 s.

g9 : 23 points relevés pour la première fois, 817,2 Mo, 40 min 48 s de relevé ; relevés en échec 1 h 31 min ; collecte entière 2 h 13 min.

## Déploiement Pages

Sans objet dans le dépôt d'essai : aucun déploiement (décision du 06/11/2026, « tu peux faire un html minimal mais pas besoin de déployer »). Ce qui serait déployé est mesuré à la place : nombre de fichiers servis (un en-tête et une section par fichier) et taille de l'archive du site (release `publication`).

| Nuit | Fichiers servis | Archive du site (Mo) |
| --- | ---: | ---: |
| g2 | 118 | — |
| g3 | 1 203 | — |
| g4 | 1 203 | 47,9 |
| g5 | 1 203 | — |
| g6 | 1 213 | 47,9 |
| g7 | 1 212 | — |
| g8 | 1 215 | 47,9 |
| g9 | 1 221 | 48,2 |
| g10 | 2 752 | 157,3 |
