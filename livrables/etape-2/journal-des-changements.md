# Journal des changements de l'étape 2

Ce qui a changé dans les documents 1 à 8 depuis leur première version (04/11/2026). Une ligne
par changement, la plus récente en bas.

## Décisions de la propriétaire intégrées après la première version

| Date | Décision | Documents touchés |
| --- | --- | --- |
| 04/11/2026 | Q1 : le seuil de couverture des ratios de groupe relève de l'interface ; le traitement sert les décomptes, jamais le ratio | 1 (R-RATIO), 2 (C4), 3, 5, 8 |
| 04/11/2026 | Q2 : en XVIIe, le site publie « non déclaré » pour le banc | 1 (R-BANC), 5, 7, 8 |
| 04/11/2026 | Q4 : un mandat effacé et remplacé est une correction ; effacé sans remplaçant, un retrait à la source | 1 (R-ARBITRAGE-ARCHIVES), 5, 8 |
| 04/11/2026 | Q6 : fiches de personne pour les seuls candidats | 5 |
| 04/11/2026 | Q9 : rétention des publications validée | 5 |
| 04/11/2026 | Q10 : articles datés = état connu à la date | 2 (instantané), 5 |
| 04/11/2026 | Q11 : signataires du JO collectés et servis tels quels ; la règle de 4.6 vaut pour le site | 1 (1.4 E), 3, 5, 8 |
| 04/11/2026 | Q19 : matière « saisi au Sénat seulement » | 1 (R-MATIERE), 5, 7, 8 |
| 06/11/2026 | Un candidat listé comme déclaré sur Wikipédia est validé sans décision ; son identité est rattachée par un identifiant déclaré (Wikidata), jamais par le nom seul | 1 (R-IDENTITE, R-PERIMETRE), 2 (sources : Wikidata relevé chaque nuit), 5 (Q8) |
| 06/11/2026 | Q30 : divergence avec le groupe comparée à la position publiée seulement quand elle concorde avec le décompte ; sinon « non établie » | 1 (R-DIVERGENCE), 5 |
| 13/11/2026 | Q8 (suite) : la liste des candidats suit franceinfo, tenue à la main dans `decisions/` (type `candidature`) avec l'élément Wikidata de chacun ; la page n'est pas collectée (réserve de fouille de données, robots d'IA exclus) ; Wikipédia devient un détecteur d'écart | 1 (R-CANDIDATURES, 1.3.3), 2 (sources), 5 (Q8) |
| 13/11/2026 | Q3 : volet européen = Parltrack (ODbL) jusqu'en juin 2019, portail du Parlement européen (CC BY 4.0) ensuite | 1 (sources, licences), 2 (points d'accès), 5 (Q3) |
| 13/11/2026 | Q33 : votes au Parlement européen = tous les votes nominatifs du candidat, chacun avec sa nature (ensemble, partie, non établie) | 1 (fiche personne, `europe`), 5 (Q33) |
| 13/11/2026 | Mandats locaux des candidats réintégrés au périmètre de validation (« oui il faudrait les intégrer ») ; rattachement à instruire | 0 (fait), 1 (1.5.1, R-CARRIERE), 2 (sources) |
| 13/11/2026 | Q34 : mandats locaux rattachés par nom, prénom et date de naissance exacte ; sans date connue, par décision | 1 (R-IDENTITE, R-CARRIERE), 5 (Q34) |
| 13/11/2026 | Q35 : un mandat municipal 2020-2026 (fichier des sortants) se termine au 15/03/2026, date déduite et signalée ; avant 2020, borne historique | 1 (R-CARRIERE), 5 (Q35) |
| 13/11/2026 | Q38 : R-QAG relie une question au gouvernement ou orale sans débat à sa séance par l'auteur **et** l'intitulé, dans les 10 jours qui précèdent sa publication au JO ; pas de repli sur l'auteur seul ; les questions orales sans débat comprises | 1 (1.5.4, R-QAG), 5 (Q38) |

## Corrections demandées par la commande de réalisation

| Date | Point | Changement | Documents touchés |
| --- | --- | --- | --- |
| 06/11/2026 | P1 | Registre des identités (ZI), acquis, en ajout seul ; R-IDENTITE le lit d'abord ; le registre des adresses y est rangé | 1 (1.1, 1.2.2, 1.3.4, R-IDENTITE) |
| 06/11/2026 | P2 | E2 ne découpe plus : il dépaquette et garde chaque membre d'archive à l'octet près, sans filtrage (décision du 06/11/2026 : présences et collaborateurs gardés dans l'entrepôt public, jamais servis) ; le découpage logique passe dans les lecteurs ; liste des membres gardée par relevé | 1 (1.1, 1.3.2), 2 (2.4) |
| 06/11/2026 | P3 | Tâches du workflow et leurs droits ; seule `ecrire` écrit ; l'acquis est écrit même si le calcul échoue | 2 (2.4, 2.15) |

## Restant à aligner

- Documents 3, 4, 6, 7 et 8 : ils parlent encore de « découpage » et de « filtrage avant
  stockage » (P2) et ne mentionnent ni le registre des identités (P1) ni les tâches du
  workflow (P3). À aligner avec les chiffres mesurés pendant l'étape 2, en fin d'étape.

## Écarts entre la conception et le code (à résorber)

| Date | Écart | Prévu |
| --- | --- | --- |
| 06/11/2026 | La reprise par la nuit suivante d'un acquis non écrit (tâche `ecrire` perdue) n'est pas encore codée : l'artefact reste 14 jours, mais rien ne le relit | tranche 2, avec le droit `actions: read` pour la seule tâche `preparer` |
| 06/11/2026 | `concurrency` sans l'option `queue: max` (syntaxe non vérifiée) : une exécution en attente peut être remplacée par une plus récente | à vérifier dans la documentation de GitHub |

## Tranche 2 (06/11/2026) : lecture et export

| Changement | Pourquoi | Documents à aligner |
| --- | --- | --- |
| Les tables de faits (Z2) gardent les faits de **toutes** les versions conservées, avec leur validité dans l'entrepôt (`prov_vu_du`, `prov_vu_jusqu_au`, `prov_etat`) | l'état courant et l'historique se lisent dans la même table | 1 (1.4) |
| Le cache de lecture est indexé par (point d'accès, uid, version), pas par empreinte | un objet retiré puis réapparu à l'identique doit être relu | 2 (2.5) |
| Colonnes de provenance préfixées `prov_` | la colonne `etat` d'une source (« Confirmé », « Annulé ») était écrasée par l'état de la version | 1 (1.4) |
| Identifiant d'un membre du JO qualifié par son dossier, sans l'horodatage de livraison ; requalification automatique de l'historique quand la règle change | un même texte figure deux fois par livraison (plan et version) ; sans cela, chaque redélivraison créait un objet nouveau | 1 (1.3.2), 2 (2.4) |
| Export : une ligne par fait de l'état courant ; ordre des lignes non garanti (comparer par `cle_fait`) | trier six millions de faits avec leur valeur JSON dépassait la mémoire | export (docs/export.md) |
| Mémoire de DuckDB bornée et réglable (1 Go par défaut, 4 Go sur GitHub) | les tables larges (prises de parole, amendements) dépassaient 2 Go | 4 |
| Rattrapage d'une nuit non écrite codé et testé | prévu en tranche 1 | 2 (2.4) |

Écart restant : l'index de l'entrepôt est chargé en dictionnaires Python (≈ 600 Mo pour la
XVIIe) ; à passer en tables Arrow si la mémoire devient un sujet sur la machine de
développement.

## Tranche 3 (06/11/2026) : règles, fiches législature et gouvernement, contrôles

| Changement | Pourquoi | Documents à aligner |
| --- | --- | --- |
| 23 règles de liaison (gouvernements, Assemblée, textes et scrutins, paroles et ordre du jour, Journal officiel), chacune avec sa couverture et son texte de méthodologie ; dépendances facultatives entre règles | doc. 1, 1.5 et 1.6 | 1 (1.6 : R-MESURE-NOMINATIVE intégrée à R-RATTACHEMENT-ACTE ; tables intermédiaires) |
| Fiches composées : XVIIe législature et ses cinq gouvernements ; fichiers servis pré-compressés ; page minimale de contrôle | ordre choisi par la propriétaire le 06/11/2026 | 1 (1.7.2 : arborescence réelle) |
| Export « fiche par fiche » des **faits publiés** (`faits-publies-gNNNNNN.parquet`), à côté de l'export de tous les faits lus | commande, section 7 | export |
| Contrôles C1, C2, C4, C5, C6 et levée par décision ; publication refusée → l'acquis est écrit, rien d'autre | doc. 2, 2.8 | 2 (C3 et C7 restent à faire) |
| Décisions : plusieurs du même type dans un fichier (`decisions:`) | 152 libellés de ministère à normaliser | 1 (1.3.3) |
| Wikidata relevé chaque nuit (identifiants parlementaires) ; sa réponse n'est pas stable à l'octet : une version par nuit, à mesurer | rattachement des candidats sans passer par le nom (décision du 06/11/2026) | 2 (2.2, 2.3) |
| Paquet renommé `empreinte_src/` (la commande reste `empreinte`) ; documentation du code par pdoc | demandes de la propriétaire du 06/11/2026 | — |
| Statut de couverture « partiel » manquant (actes du JO couverts sur une partie de la période) : servi comme `non_collecte` avec `etendue: partiel` | vocabulaire de 1.5.5 incomplet | 1 (1.5.5) |

Restent ouverts pour la suite : effectif minimal d'un gouvernement (le Premier ministre seul
les premiers jours compte pour 1 ; la capture donne « entre 27 et 42 ») ; ministère porteur
d'un projet de loi ; remaniements (R-VAGUE ne qualifie pas la formation) ; licence et point
d'accès absents des sorties de règles ; contrôles C3 et C7 ; questions Q27 à Q29.

## Fiche de lignée de groupe (06/11/2026)

| Changement | Pourquoi | Documents à aligner |
| --- | --- | --- |
| R-CONTINUITE-GROUPE : un organe ouvert au plus 7 jours après la fin d'un autre, avec ≥ 5 membres communs et une moyenne harmonique des deux parts ≥ 80 %, forme avec lui un seul maillon (`grp:<lég.>:<premier organe>`). **Le sigle n'est plus un critère** | 8 des 11 changements d'organe d'un même groupe (XIIe → XVIIe) changent de sigle avec 97 à 100 % de membres communs ; les dissidents restent sous le seuil (R-UMP 55 %, Agir ensemble 41 %, EDS 4 %) | 1 (1.5.2, 1.6), 5 (Q15) |
| R-FILIATION calculée en nombres entiers (10 × communs ≥ 3 × (réélus + anciens députés)) : la table et la fiche servent les décomptes (réélus, anciens députés, communs), jamais une part | aucun ratio dans les fichiers servis ; la moyenne harmonique des deux parts vaut 2 × communs / (réélus + anciens députés) | 1 (1.5.2) |
| `a_trancher` seulement quand un ancien groupe aurait deux suites qui passent le seuil ; aucun cas sur l'archive du 06/11/2026 | cahier 4.3 : « seuls les cas qu'elle ne tranche pas attendent une décision » | 5 (Q22) |
| Décisions `filiation` et `continuite_groupe` écrites en champs (`avant`, `apres`, `verdict`) plutôt qu'en phrase (`decision: suite_de [...]`) | lisibles sans analyse de texte | 1 (1.3.3, exemple) |
| R-LIGNEE : registre des lignées dans l'entrepôt (`registres/lignee_*.parquet`), en ajout seul comme celui des personnes : numéro `lig:NNNNNN` acquis, adresse inscrite une fois (forme lisible du nom le plus récent à la première attribution), fusion → le plus ancien numéro reste, l'adresse absorbée redirige | cahier 6.1 : « l'adresse d'une fiche ne change pas une fois publiée », alors que le nom d'un groupe change | 1 (1.2.2 : `lig:000002` au lieu de `lig:socialistes`, 1.3.4) |
| Lignées publiées : celles qui ont un groupe de la XIVe à la XVIIe (cahier 4.1) ; XIIe et XIIIe servent au calcul et ne sont pas affichées. 18 lignées | cahier 4.1 | — |
| R-DIVERGENCE (version 2) : « le groupe a une fiche » = il appartient à une lignée publiée | les groupes de la XIVe à la XVIe ont maintenant une fiche | — |
| Fiche candidat : le « groupe actuel » renvoie à la fiche de sa lignée | lien demandé par la passation | — |
| Fichiers d'une lignée : `fiche`, `effectifs` (aux seuls jours de changement), `membres`, `paroles` + `paroles-textes-*`, `proposes`, `amendements` + `amendements-<année>`, `votes-17`, `avec-qui-17`, `mots/` | doc. 1, 1.7.2 (`votes-<législature>`, `avec-qui-<législature>` déjà prévus) | 1 (1.7.2 : `effectifs.json.gz`, listes d'amendements) |
| Une section qui n'est qu'un index d'une autre section (index léger des paroles) n'est pas inscrite comme faits publiés | un paragraphe affiché est un seul fait | export (docs/export.md) |

Mesures locales (machine de développement, collecte du 06/11/2026, sans Wikidata ni Sénat) :
toutes les règles en 44 s ; fiches de lignée composées en 71 s ; pic de mémoire 1,9 Go pour
la chaîne entière ; 18 fiches, 2 à 13 Ko au chargement initial, 6 à 5 443 Ko toutes sections
ouvertes (La France insoumise) ; 5 431 fichiers, 57 Mo ; 564 008 faits publiés (export des
faits publiés : 609 000 lignes, 33,7 Mo). À remesurer sur GitHub.

Recoupement avec la capture `04-groupe-soc` : SRC XIVe 350 personnes et 265 membres au
20/06/2017 ; XVe 39 (28 déjà là, 11 nouveaux) ; XVIe 31 (17, 1 revenu, 13) ; XVIIe 71 (27, 5, 39)
et 68 membres : identiques.

Restent : la fiche ne compte pas encore les « membres sans données » de « Ce qu'on n'a pas pu
lire » ; l'index de mots d'une lignée compte jusqu'à quelques centaines de tranches (5 431
fichiers pour 18 fiches) ; le seuil de quorum de « Ce qu'ils ont voté » reste un choix
d'affichage (Q1).

## Contrôles C3, C7 et avertissements A1 à A8 (06/11/2026)

| Changement | Pourquoi | Documents à aligner |
| --- | --- | --- |
| R-PERIMETRE : table `population` (candidats, membres des groupes affichés, membres des gouvernements de la XVIIe, députés non inscrits), avec la fiche où chacun doit figurer et sa raison de sortie (candidature retirée à la source, ou décision `perimetre`) | C7 exige les populations attendues ; la règle n'était pas codée | 1 (1.5.1, 1.6) |
| C3 : bilan par famille (scrutins, amendements, prises de parole, actes du JO, dossiers, questions) : lus = servis + écartés avec une raison ; un objet « attendu » non servi bloque. Mesuré en local : **aucun écart inexpliqué** | doc. 2, 2.8.1 | 2 (2.8 : familles et raisons) |
| C7 : chaque personne attendue est sur sa fiche, ou sortie avec une raison établie ; un candidat sans adresse (homonyme sans année de naissance) **bloque** jusqu'à une décision `perimetre` | doc. 2, 2.8.1 ; une raison technique n'est pas une raison établie | 2 (2.8) |
| A2 : 20 scrutins servis tirés au sort (reproductible par génération), page publique relue : totaux et une position nominative chacun, soit 40 faits (Q14). Mesuré en local : 40 vérifiés, 0 écart, 24 à 26 s. Une page injoignable est « non vérifiée », jamais un écart | doc. 2, 2.8.2 ; cahier 3.1.9 | 2 (2.8 : A2 limité aux scrutins ; sorts d'amendement et mandats à venir) |
| A1, A3 à A8 : fiche hors modèle (décision) ; effectifs des groupes à chaque scrutin contre le décompte publié, lois sans dossier ; même objet servi deux fois (copies d'amendement, lignes identiques) ; section vide pour toutes les fiches d'un type ; couverture (candidats sans fiche, **nombre** de membres sans prise de parole servie, jamais leurs noms) ; filiations à trancher, décisions et levées sans objet, législature en cours sans fiche ; mandats ouverts dans un organe clos | doc. 2, 2.8.2 ; les textes d'alerte sont publics : décomptes et identifiants, jamais d'indice individuel (2.10) | 2 (2.8) |
| Chaque avertissement fait une issue (`avertissement:A3`…), mise à jour seulement quand son contenu change ; la publication n'est pas bloquée | doc. 2, 2.10 | — |

Mesures locales (collecte du 06/11/2026) : contrôles C3, C7 et A1 à A8 en 54 s, dont A2
24 s ; pic de mémoire de la chaîne entière 3,1 Go (1,9 Go sans ces contrôles) : à remesurer sur
GitHub. Premiers avertissements attendus : A3, 1 330 décomptes de groupe sur 107 215 où le nombre
de membres publié diffère de nos appartenances à la date (surtout en début de législature) ;
A8, 9 mandats ouverts dans le gouvernement Bayrou clos (7 relevés le 03/11/2026).

## Défauts trouvés par les essais du 06/11 et correctifs (06–07/11/2026)

| Changement | Pourquoi | Documents à aligner |
| --- | --- | --- |
| Le texte des avertissements écrasait le bilan de l'export (variable `ex`) : le calcul s'arrêtait après les contrôles (PR #7) | trouvé par une mise à jour d'essai sur `main` avant la nuit | — |
| L'acquis d'un essai s'appelle `essai-gNNNNNN` : la nuit suivante ne le reprend plus comme une nuit perdue (PR #7) | le second essai avait rattrapé le premier ; la nuit l'aurait écrit (une génération de trop) | 2 (2.4) |
| Garde du second déclenchement : seule une génération écrite depuis le début de la nuit en cours (20 h UTC) l'arrête, plus « moins de 20 heures » | la mise à jour manuelle du 06/11 à 16 h 44 UTC a fait sauter les deux déclenchements de la nuit : **nuit 1 perdue** | 2 (2.3) |
| Export et archive du site déposés dans leurs releases (`export`, `publication`) : la fonction d'envoi les mettait tous dans `entrepot` | les releases `export` et `publication` étaient vides depuis la tranche 3 ; 611 Mo de la génération 2 sont dans `entrepot` | export (docs/export.md) |
| R-VAGUE (version 2) : nature de chaque vague (formation, remaniement, complément) et ses arrivées, départs, changements ; la fiche gouvernement compte les remaniements et lit l'effectif minimal après la formation (Bayrou : plus 1, mais l'effectif après les nominations du 24/12/2024) | décision Q31 du 07/11/2026 | 1 (1.6 R-VAGUE), 5 |
| « Lecornu » affiché « Lecornu I » dès qu'un « Lecornu II » existe ; l'adresse `lecornu` ne change pas | nom usuel ; une adresse publiée ne change pas | — |
| Adresses publiques des amendements (`/dyn/17/amendements/<uid>`, redirige vers la page) et des questions (`/dyn/17/questions/<uid>`), vérifiées le 06/11/2026 (identifiant inventé : 404) | elles étaient dites « non vérifiables » | 1 (1.4) |
| Source en panne : une section dite `complet` dont un point d'accès n'a pas pu être relevé passe en `panne`, avec la date du premier échec, et la publication continue (marquage fait une fois, par l'Ecrivain) | 07/11/2026, mise à jour manuelle (génération 3) : export du Sénat de 444 octets (« suspect »), C5 a refusé toute la publication à cause des fonctions de sénateur d'un candidat ; le doc. 2 (C5) et le scénario 2 demandent « la panne se voit, rien ne disparaît » | 2 (2.8) |

Nettoyage du 07/11/2026 (décision de la propriétaire, « déplacer 2, supprimer 2 ») : dans la
release `entrepot`, hors manifeste, `faits-publies-g000002.parquet` (4 Mo) déplacé vers `export`
et `site-g000002.tar.gz` (3 Mo) vers `publication`, vérifiés par empreinte ; `faits-g000002.parquet`
et `faits-g000002.csv.gz` (604 Mo, export de tous les faits lus, reconstructible depuis la
génération 2) supprimés. Manifeste de l'entrepôt intact (génération 3, 19 fichiers).

## Périmètre de validation élargi (07/11/2026)

Décision de la propriétaire : les 7 nuits et les scénarios portent sur le cahier 4.1 sans budgets
ni mandats locaux (voir `0-cadrage-et-decisions.md`). Plan : (1) collecte des archives closes
XIVe–XVIe (≈ 1,55 Go relevés le 07/11/2026 : XVIe 492 Mo, XVe 955 Mo, XIVe 102 Mo) et du dump
global du JO ; (2) lecteurs adaptés aux formats XIVe et XVe ; (3) fiches étendues (législatures
XIVe–XVIIe, gouvernements depuis 2007, activité complète des lignées et des candidats) ;
(4) volet européen ; (5) faits publiés écrits au fil de l'eau (mémoire) ; (6) puis 7 nuits de
suite, scénarios, rapport de mesures. Estimation avant mesure : entrepôt ≈ 0,75 Go hors JO,
calcul ≈ 15 à 25 min par nuit, pic de mémoire ≈ 7 à 9 Go, ≈ 2 millions de faits publiés.

### Premier remplissage des archives closes : essais du 07/11/2026 sur GitHub (sans écriture)

| Mesure | Résultat |
| --- | --- |
| 24 des 26 archives XIVe–XVIe | reçues en 0,4 à 138 s chacune (questions écrites XVe : 138 s pour 110 Mo) ; entrepôt de travail 734 Mo (dont ≈ 250 Mo déjà acquis) |
| Amendements XVIe (363 Mo) et XVe (649 Mo), ancien transport | jamais reçus : coupures à 70 et 242 Mo, 45 min de tentatives |
| Les mêmes, transport corrigé | XVe reçue en 74 min (1,29 Go transférés pour 649 Mo) ; XVIe toujours en échec après 95 min ; collecte de 2 h 50 |
| Cause, mesurée depuis la machine de développement aussi | l'Assemblée sert mal une plage prise loin dans un gros fichier : à 100 Mo, 117 Ko/s ; à 300 Mo, « 206 » puis rien (HTTP/1.1 comme HTTP/2) ; data.gouv.fr n'en a pas de copie |
| Lecteurs actuels sur les archives XIVe–XVIe | scrutins et dossiers lus sans erreur ; agenda, acteurs (AMO20) et questions de la XIVe en un seul fichier sous une enveloppe : adaptés |

Transport corrigé : blocs de 64 Kio (le bloc en cours était perdu à chaque coupure), coupure
pendant une reprise = reprise de plus, plage vérifiée par nous (pas par If-Range), départ du
début après trois reprises vides, budget de 30 min par fichier (nouvel essai la nuit suivante).
Une archive close n'a besoin d'arriver qu'une fois.

## Nuits du 07 au 11/11/2026 et correctifs du 12/11

| Nuit | Génération | Résultat |
| --- | --- | --- |
| 07/11 | 4 | publiée |
| 08/11 | 5 | refusée (C1 : 2 609 « pertes ») |
| 09/11 | 6 | publiée, **sans contrôle des pertes** |
| 10/11 | 7 | refusée (C1 : 5 249, C6 : actes Lecornu II) ; Sénat en panne |
| 11/11 | 8 | publiée, **sans contrôle des pertes**, avec la perte des actes d'octobre (1 465) |

| Changement | Pourquoi | Documents à aligner |
| --- | --- | --- |
| C1 et C6 comparent à la **dernière publication réussie** (release `export`), plus aux faits de la nuit précédente | une nuit refusée ne publie pas ses faits : la nuit suivante ne trouvait rien à comparer et sautait C1 et C6 sans le dire (09 et 11/11) | 2 (2.8) |
| C1 reconnaît un fait à son **identité** (fiche, type, identifiants de source ; sans identifiant : valeur sans sa date de compte), plus à sa valeur | les comptes datés (« au ») changeaient chaque nuit et passaient pour perdus (08 et 10/11) ; rejoué sur les générations 4→6 : 2 pertes au lieu de milliers ; 6→8 : la perte réelle (2 750 faits) est trouvée | 2 (2.8) |
| R-RATTACHEMENT-ACTE (version 2) : la période couverte du JO va du premier au dernier numéro complet **livré dans son actualité** (≤ 7 jours) ; un numéro incomplet est un trou nommé | un numéro incomplet vers le 09/11 réduisait la période à deux jours et retirait les actes d'octobre ; les numéros anciens redélivrés restent écartés | 1 (1.6) |

## Lecteurs des archives closes XIVe–XVIe (12/11/2026)

Lus en local sur les archives rangées par les essais du 07/11 (sans écriture), **aucun fichier
illisible** :

| Famille | Lu | Durée | Pic mémoire |
| --- | --- | ---: | ---: |
| Acteurs et mandats | 270 463 mandats | 12 s | 1,2 Go |
| Amendements XIVe (un fichier de 677 Mo, schéma ancien) | 167 420 | 36 s | 3,0 Go |
| Amendements XVe | 311 934 | 74 s | 1,6 Go |
| Comptes rendus XVe–XVIe | 2 167 comptes rendus, 1 128 352 paragraphes | 173 s | — |
| Questions (dont XIVe en un fichier de 575 Mo) | 184 257 | 52 s | 4,1 Go |
| Scrutins | 9 877 scrutins, 1 186 357 positions | 12 s | — |

| Changement | Pourquoi |
| --- | --- |
| Un lecteur peut rendre ses lignes par lots (générateur) ; lecture en flux (`ijson`, épinglé) | fichiers uniques de 575 et 677 Mo |
| Amendements XIVe : schéma ancien ramené au schéma courant ; état et sort en texte → (code, sous-état) de la table des sorts | `identifiant` au lieu de `identification`, sort dans `sort.sortEnSeance`, pas de `cycleDeVie` |
| R-AMENDEMENT (version 3) : famille `irrecevable_article_non_precise` (code `IRRXIV`, 9 714 amendements) | la XIVe ne dit pas si une irrecevabilité relève de l'article 40 ou 45 : on ne devine pas |

Reste : le pic de 4,1 Go vient des fichiers uniques gardés entiers en mémoire (octets bruts) ;
les archives restent `lire: false` tant que les fiches ne servent pas la XIVe–XVIe (sinon C3
bloquerait, à juste titre).

## Fiches étendues à la XIVe–XVIIe, archives closes lues (12/11/2026)

Branche `etape-2-fiches-xiv-xvi`. Les 26 points des archives closes passent en lecture
(`lire: false` retiré). Les gouvernements restent ceux de la XVIIe : leur extension depuis 2007
attend l'archive globale du Journal officiel (lot suivant).

| Changement | Pourquoi | Documents à aligner |
| --- | --- | --- |
| Module `perimetre` : législatures publiées (XIVe à XVIIe), paroles à partir de la XVe, gouvernements publiés, point d'accès d'une famille pour une législature. Composeurs, R-CARRIERE, R-PERIMETRE et A6 le lisent ; plus aucun « XVIIe » codé en dur | décision du 07/11/2026 (cahier 4.1) ; un seul endroit à changer pour étendre | 1 (1.7), 2 (2.8) |
| Fiches de législature XIVe, XVe, XVIe. Législature close : comptes à sa fin, hémicycle « borne historique » (l'Assemblée ne publie que l'hémicycle en cours), effectifs des groupes au dernier jour sans comparaison aux sièges ; chaque groupe renvoie à sa lignée ; un gouvernement sans fiche n'a pas de lien (raison écrite) | cahier 4.1 et 4.5 ; C2 | 1 (1.7.2) |
| Ordre du jour sans aucune séance : `trou_source`, plus « 0 séance, complet ». L'archive « Agenda XIV » de l'Assemblée ne contient que 11 450 réunions de groupes et de délégations (20/06/2017 → 21/12/2018), aucune séance | une donnée manquante reste manquante | 1 (1.4, agenda) |
| Lignées : textes, amendements et votes de chaque groupe de la XIVe à la XVIIe ; `votes-<n>` et `avec-qui-<n>` par législature, comptés à la fin du maillon s'il est clos ; législature close : autres groupes rangés par sigle (hémicycle non publié) ; paroles à partir de la XVe, un maillon de la XIVe est `hors_perimetre` | cahier 4.1 et 4.3 | 1 (1.7.2) |
| Candidats : activité lue depuis le début de la XIVe (20/06/2012), paroles depuis la XVe (21/06/2017), chacune avec son propre périmètre (`perimetre_activite`, limite `paroles`) ; un député de la XIVe seulement a ses votes comptés et ses paroles « hors périmètre », sans zéro ; questions de la XIVe à la XVIIe, point d'accès de leur législature. Clés servies renommées : `jours_dans_le_perimetre`, `statut_comptes`, `depuis`, `anterieurs_au_perimetre` | cahier 4.1 et 4.2 | 1 (1.7.2) |
| Gouvernements : dossiers lus depuis la XIVe, comptes rendus depuis la XVe ; ce qui précède est `hors_perimetre` (plus `non_collecte` « essai »). Attal, entré en fonction en XVIe, est maintenant entier | cahier 4.1 et 4.4 | — |
| R-PERIMETRE : députés non inscrits de la XIVe à la XVIIe | cahier 4.1 (quatrième population) | 1 (1.5.1) |
| **Archives successives** (liaison, `ARCHIVES_SUCCESSIVES`) : un objet que plusieurs archives de l'Assemblée portent n'est lu qu'une fois, dans la plus récente. Acteurs, organes, mandats, déports : l'archive courante seule (elle republie tout depuis la XIe ; un mandat qu'elle n'a plus est corrigé ou retiré, Q4). Dossiers, documents, réunions : par objet ; actes par dossier (chaque archive les renumérote : `L16-VD220135DI` → `L17-VD220135DI`). La vue `<table>__archives` garde toutes les archives | sans cela, chaque acteur figurait jusqu'à 4 fois : R-ORATEUR rendait 4,2 millions de lignes pour 1,5 million de paragraphes, les prises de parole par personne 40 millions, et la composition des lignées dépassait la mémoire (6,2 Go, processus tué) ; 600 amendements de la XVe comptés deux fois (document rattaché à deux dossiers) | 1 (1.3.2, 1.6 R-ARBITRAGE-ARCHIVES) |
| C3 : raison `paragraphe_sans_texte` (paragraphe publié sans texte, écarté par R-PAROLE-PERSONNE) | 7 paragraphes de la XVe et de la XVIe bloquaient la publication sans raison | 2 (2.8) |
| A6 : un décompte par législature (XVe à XVIIe), sur les paroles servies pendant cette législature | périmètre des paroles | 2 (2.8) |
| Faits publiés écrits **au fil de l'eau** (Parquet par lots de 50 000) au lieu d'une liste en mémoire | 2,07 millions de faits publiés sur le périmètre complet | 4 |

Mesures locales (machine de développement, 7,8 Gio ; entrepôt de la génération 8 restauré et
complété des 25 archives closes rangées par les essais du 07/11 — sans les amendements de la
XVIe, jamais reçus ; sans Wikidata ni Sénat frais ; A2 désactivé) :

| Étape | Durée | Pic de mémoire |
| --- | ---: | ---: |
| Lecture de tout le périmètre (E3) | ≈ 12 min | 2,4 Go |
| Export de tous les faits lus | ≈ 10 min | — |
| Règles (E4, 39 règles) | 86 s | 3,3 Go |
| Fiches (E5) | 299 s | 3,1 Go |
| Contrôles (E6, sans A2) | 120 s | 3,0 Go |

56 fiches (29 candidats, 18 lignées, 5 gouvernements, 4 législatures), **2 069 482 faits
publiés** (fichier de 127 Mo), 14 208 fichiers servis (203 Mo). Publication autorisée ; C3 :
aucun écart inexpliqué (scrutins 19 683 lus, 19 670 servis ; amendements 479 556 / 451 132 ;
prises de parole 1 488 747 / 1 229 852 ; dossiers 14 455 / 12 498). Avertissements : A3 (2 187
décomptes de groupe), A5 (budgets), A6, A8 (9 mandats Bayrou).

**Export de tous les faits lus** (release `export`) : 1,15 Go en Parquet et 1,25 Go en CSV
compressé par nuit sur le périmètre complet, contre ≈ 0,6 Go pour la XVIIe ; avec la limite
DuckDB locale de 1 Go il échoue (mémoire), il passe à 3 Go. L'arbitrage en attente (garder,
réduire, abandonner le CSV) est tranché le même jour : **dernière nuit, Parquet seul**. Le CSV
n'est plus écrit ; la mise à jour qui dépose `faits-gN.parquet` retire de la release les
`faits-g*.parquet` et `faits-g*.csv.gz` des nuits précédentes (g4, g6, g8 et leurs CSV partiront
à la première nuit publiée avec ce code) ; les `faits-publies-g*.parquet` restent tous (C1 les
lit). Documents à aligner : export (`docs/export.md`, fait), 2 (2.13).

Restent : gouvernements depuis 2007 et Journal officiel depuis 2007 (archive globale) ; lois de
la XIVe (396 comptées, l'écart avec le décompte publié par l'Assemblée n'est pas expliqué, comme
pour la XVIIe) ; amendements de la XVIe tant que l'Assemblée ne les sert pas en entier.

### Mise à jour d'essai sur la branche (12/11/2026, 16 h 51 → 19 h 42 UTC)

Collecte 2 h 41, calcul 7 min 42 s (lecture, export, règles 23 s, fiches 123 s, contrôles 101 s ;
pic 3,6 Go). **Cinq archives closes non reçues** : l'Assemblée coupe le transfert après quelques
Mo et le budget de 30 min par fichier est atteint — amendements XVe (649 Mo) et XVIe (363 Mo),
comptes rendus XVe (149 Mo), questions écrites XVe (110 Mo) et XIVe (134 Mo). D'où 1 110 479 faits
publiés (2 069 482 en local, où les XVe étaient là) et A6 : 604 membres de la XVe sans parole.

| Défaut trouvé | Correction |
| --- | --- |
| C1 a refusé la publication pour une « perte » : la ligne « Non-inscrits » des groupes de la XVIIe, sans identifiant, reconnue à sa valeur, qui avait gagné une colonne `lien` | le lien vers la lignée n'est ajouté qu'aux lignes de groupe (piège déjà connu : ne pas changer la valeur d'un fait sans identifiant) |
| A2 relisait la page `/dyn/17/scrutins/<numéro>` pour un scrutin de la XIVe à la XVIe : 6 « écarts » faux sur 20 scrutins | page de la législature du scrutin |
| Export de tous les faits lus : 648 799 clés en double (mandats, organes, identités, actes, réunions… portés par plusieurs archives) | même choix d'archive que la liaison (`ARCHIVES_SUCCESSIVES`) ; mesuré en local : 14,6 millions de faits, 1 min 45 s, 1,4 Go, **370** clés en double restantes |

Les 370 restantes viennent de la source : dans 370 comptes rendus de la XVe, le paragraphe de fin
de séance est publié deux fois sous le même `id_syceron` (« La séance est levée… » et la
signature du service du compte rendu), sans orateur. L'alerte `export:doublons` les comptera.

### Nuit du 12/11 et derniers essais sur la branche (13/11/2026)

Nuit du 12/11 (génération 9, `main`, première avec les correctifs de la PR #24) : publiée, C1 sans
fausse perte, actes d'octobre de Lecornu II revenus (2 162, comme en g6 ; 0 en g8) ; collecte
2 h 13 ; 23 archives closes rangées (entrepôt 735 Mo) ; amendements XVe et XVIe et comptes rendus
XVe toujours coupés par l'Assemblée (alertes `panne` #27 à #29).

Essai sur la branche (00 h 17 → 01 h 57 UTC) : A2 39 faits vérifiés sur 40, aucun écart ; C3
sans écart ; export sans doublon ; mais **C1 refuse** pour 4 lignes de décompte d'amendements
« commission non établie, 2026 », vidées parce que 122 amendements ont reçu leur commission à la
source. Correction : C1 ne compte pas comme perte une ligne de décompte dont les amendements sont
vérifiés un par un (`DECOMPTES_VERIFIES_UN_PAR_UN`) ; la perte d'un amendement, elle, bloque. Ce
défaut touchait aussi `main`.

Essai suivant (02 h 04 → 02 h 15 UTC, collecte limitée aux amendements de la XVIIe et au Journal
officiel) : **publication autorisée**, 56 fiches, 1 114 824 faits publiés (sans les trois archives
non reçues), calcul 4 min 36 s, pic 3,6 Go (E4 ; « 2,4 Go » écrit d'abord d'après `time -v`, corrigé le 13/11).

## Gouvernements depuis la XIVe, sièges des législatures closes, statut « partiel » (13/11/2026)

Mise à jour manuelle du 13/11 (génération 10, 06 h 32 → 07 h 51 UTC) : première publication sur le
périmètre XIVe–XVIIe ; 56 fiches, 1 766 930 faits publiés ; collecte 1 h 07, calcul 10 min (pic
4,7 Go en E4 ; « 2,7 Go » écrit d'abord d'après `time -v`, corrigé le 13/11) ; comptes rendus XVe enfin reçus (alerte #29 fermée) ; amendements XVe et XVIe toujours
coupés (#27, #28) ; alerte #30 `export:doublons` (370, attendue) ; release `export` : seul
`faits-g000010.parquet` (933 Mo) pour tous les faits lus.

| Changement | Pourquoi | Documents à aligner |
| --- | --- | --- |
| Gouvernements publiés : ceux qui traversent la XIVe à la XVIIe (Ayrault II à Lecornu II, 13 fiches) ; Journal officiel à partir de la même date | décision du 13/11/2026 (« on commence à la même période que la 14e leg »), à la place de « depuis 2007 » (cahier 4.1) | 0 (fait), 1 (1.7.2), cahier 4.1 |
| Statut de couverture `partiel` : section lue sur une partie de sa période (gouvernement commencé avant ce qui est lu et en fonction après ; candidat ayant siégé avant et depuis le 20/06/2012). Les chiffres portent sur la partie lue ; un zéro n'est pas servi pour un gouvernement ; une source en panne fait passer `partiel` à `panne` comme `complet` | Philippe II (20/06/2017, la veille de la XVe) avait toutes ses paroles « hors périmètre » pour un jour ; Ayrault II (19/06/2012) ses projets de loi | 1 (1.5.5 : statut ajouté) |
| R-HEMICYCLE (version 2) : le siège d'une législature close vient de son **archive figée**, à la date de l'état qu'elle publie (XVe : 567 députés au 02/06/2022 ; XVIe : 577 au 09/06/2024), si elle donne le siège d'au moins 90 % des députés en fonction ; XIVe : pas d'archive figée utilisable (154 sièges pour 750 mandats), « borne historique » | cahier 3.1 : « seule l'archive figée d'une législature close donne le siège » ; l'agent avait écrit à tort que l'Assemblée ne publie que l'hémicycle en cours | 1 (1.6 R-HEMICYCLE) |

Mesuré en local (entrepôt g8 + archives closes) : publication autorisée, 64 fiches, 2 181 591 faits
publiés. Les actes du Journal officiel des gouvernements d'avant octobre 2026 restent
« non collectés » jusqu'à la lecture de l'archive globale (depuis 2012).

## Journal officiel depuis la XIVe : archive globale (13/11/2026)

La DILA publie une archive globale datée du 08/11/2026 (`Freemium_jorf_global_20261108-140000.tar.gz`,
1,75 Go, 7 188 987 fichiers, 13,7 Go décompressés, depuis 1861) et a retiré les livraisons
quotidiennes antérieures (8 restent, du 08 au 13/11). Décision du 13/11/2026 (« Archive à part +
2012 ») : voir `0-cadrage-et-decisions.md`.

| Changement | Pourquoi | Documents à aligner |
| --- | --- | --- |
| Point `jo-global` (format `archive_globale`) : relevé une fois ; archive vérifiée et lue en flux ; découpés les seuls fichiers lus (métadonnées et plan des actes, sommaires) publiés depuis le 20/06/2012, chemin préfixé de l'horodatage de l'archive (mêmes uid et même `livraison` qu'une livraison quotidienne) ; archive reçue gardée à l'octet (`brutes/`, release `archives-brutes`, jamais rapatriée la nuit) | décision du 13/11 ; P2 respecté sans recharger 1,75 Go chaque nuit | 1 (1.3.2), 2 (2.2, 2.4), cahier 3.6 |
| Liaison et export : un acte, son plan, ses liens, un sommaire de numéro : la livraison la plus récente fait foi (archive globale ou livraison quotidienne) | un même acte peut venir des deux points | 1 (1.6) |
| R-RATTACHEMENT-ACTE (version 3) : les numéros de l'archive globale comptent dans la période couverte | ils ne sont pas « livrés dans leur actualité » | 1 (1.6) |
| Entrepôt : lignes d'index compactes ; liste des membres écrite au fil de l'eau ; vérification des tar en flux | mesuré en local : le relevé est tué à 5,7 Go (la vérification ouvrait le tar en mode indexé, 9,6 millions d'entrées en mémoire) ; l'index prenait 1,36 Go pour 815 000 lignes (642 Mo après) | 4 (mémoire) |

Mesures locales (machine de développement ; archive copiée, non téléchargée — le téléchargement a
pris 8 min 36 s en local) : relevé 25 min (copie, vérification, découpage), pic 1,9 Go ;
843 579 fichiers découpés ; index de l'entrepôt 1 658 106 lignes. Calcul : lecture du JO
327 s (pic 2,3 Go), règles 138 s, fiches 421 s, contrôles 199 s, pic 3,5 Go ; **publication
autorisée**, 64 fiches, 2 600 535 faits publiés. Période couverte du JO : du 20/06/2012 au
11/11/2026, 4 392 numéros, aucun manquant, 16 incomplets ; 419 064 actes dans la période ;
gouvernements de Valls à Lecornu II `complet`, Ayrault II `partiel` (il commence le 19/06/2012).

## Liste des candidats d'après franceinfo (13/11/2026)

Branche `etape-2-candidats-franceinfo`. Décision du 13/11/2026 : « la liste de candidats doit se
baser sur celle de franceinfo ». franceinfo interdit tout son site aux robots d'IA (`robots.txt` :
`Disallow: /` pour `Claude-Code`, `ClaudeBot`… ; relevé le 13/11/2026) et réserve la fouille de
textes et de données avec obligation d'obtenir le consentement de France Télévisions
(`tdm-reservation: 1`, `tdm-policy.json`). Option « A » retenue : la page n'est pas collectée ;
la liste est recopiée à la main dans une décision.

Page lue le 13/11/2026 (copie enregistrée par la propriétaire, « 37 candidats au 13/11/2026 ») :
43 cartes, 37 candidats déclarés et 6 retirés ; par carte : bloc, statut, nom, âge, parti, texte
de présentation (non repris) ; **aucun lien**. Comparée aux 29 fiches de la génération 10 :
28 communes, 1 sortante (X. Bertrand, ni déclaré ni retiré sur franceinfo), 9 entrantes.

| Changement | Pourquoi | Documents à aligner |
| --- | --- | --- |
| Décision `candidature` (`decisions/candidature/2026-11-13-franceinfo.yaml`) : 44 entrées (37 déclarés, 6 retirés, X. Bertrand `non_listee`) ; nom, statut, parti tels qu'affichés, élément Wikidata, article Wikipédia ou nom écrit par Wikipédia (clés du registre) | la page n'est pas collectée ; la liste en vigueur est celle du fichier le plus récent | 1 (1.3.3, fait), `decisions/LISEZMOI.md` (fait) |
| Éléments Wikidata : 24 par le lien déclaré de l'article Wikipédia que la liste de Wikipédia citait ; 3 déclarés trouvés par le nom et validés par la propriétaire (Lassalle Q3173022, Branco Q21890311, Egger Q108584624 ; âge de franceinfo concordant) ; 6 retirés trouvés par le nom (non affichés) ; 11 déclarés sans article ni élément | jamais par le nom seul | 5 (Q8, fait) |
| R-CANDIDATURES v2 : la liste vient de la décision ; l'identité suit l'élément inscrit (contrôlé contre l'article inscrit), puis Wikidata → `PA…` / matricule ; Wikipédia ne donne plus que la date de déclaration (ligne qui cite le même article) et un détecteur d'écart (`candidature_ecart_wikipedia`, avertissement A9 : déclaré selon Wikipédia et absent de la liste ou retiré dans la liste ; retiré selon Wikipédia et déclaré dans la liste ; le troisième cas ajouté à la demande de la propriétaire, 13/11/2026) | décision du 13/11/2026 | 1 (G, fait) |
| R-IDENTITE v2 : garde les clés du registre (article, nom écrit par Wikipédia) ; un candidat nouveau sans article ni élément forme `("liste-nom", nom)` ; nom et adresse des fiches existantes inchangés (nom de la ligne de Wikipédia, sinon titre de l'article, sinon nom de la liste) | correction P1 : une attribution ne change jamais | — |
| R-PERIMETRE v2 : un candidat `non_listee` sort avec la raison `absent_de_la_liste_des_candidats` | sans elle, C7 aurait bloqué la publication (défaut latent depuis la version 1, jamais déclenché) | — |
| C1 et C6 : les faits d'une fiche de candidat retiré ou non listé qui disparaît sont expliqués ; A9 nomme la fiche retirée la nuit où elle part, et les écarts avec Wikipédia | la fiche de X. Bertrand aurait fait refuser la nuit | 2 (2.8) |

Mesure locale (entrepôt de la génération 10 restauré ; lecture de Wikipédia, Wikidata, acteurs de
l'Assemblée et export du Sénat, puis les deux règles ; 46 s, pic 1,5 Go) : 44 candidats, 37
publiés, 17 rattachés à l'Assemblée, 2 au Sénat, date de déclaration connue pour 26 des 37,
aucun écart avec Wikipédia (ses 29 déclarés sont dans la décision) ; les 28 candidats communs
gardent leur numéro, leur adresse et leur identifiant de l'Assemblée ; Autain et Massard
retrouvent leur numéro (per:000007, per:000020, attribués sous la liste de Wikipédia) ; 13
numéros nouveaux.

## Couverture honnête : trous des scrutins et sources jamais relevées (13/11/2026)

Branche `etape-2-couverture-honnete`, issues #36 et #33 (revue de code du 13/11, constats sur la
g10). Mesures sur l'entrepôt g10 restauré en local.

| Changement | Pourquoi | Documents à aligner |
| --- | --- | --- |
| Règle R-CONTINUITE-SCRUTINS (`trou_scrutins`) : numéros de scrutin de l'Assemblée absents entre 1 et le plus grand numéro lu, datés par leurs voisins ; archive tronquée d'une législature close quand un acte de dossier cite un scrutin absent postérieur au dernier scrutin lu. Scrutins `VTANR` seulement (le Congrès, `VTCGR5L16V1`, a son propre n° 1) ; une législature en cours n'est jamais dite tronquée | #36 : `votes-14` des lignées se disait `complet`, « 1354 scrutins de la législature (sur 1354) », au 20/06/2017, alors que l'archive s'arrête au 24/11/2016. Mesuré : XIVe arrêtée au n° 1 354, actes de décembre 2016 citant les n° 1 358, 1 362, 1 364 ; XVe : n° 3 781 et 3 782 absents (25–26/05/2021) ; le n° 4 689 de la XVe, cité le 26/01/2022 avant la fin de l'archive, n'est pas un trou daté | 1 (1.5.5 et 1.6 : faits) |
| Sections de votes touchées par un trou : `trou_source` (statut d'origine gardé dans `statut_sans_trou`), trou dit en clair dans le détail et décrit (`trous_source`) ; date des données = dernier scrutin lu pour une archive tronquée. Lignées : `votes-<n>`, `avec-qui-<n>` si un maillon recouvre le trou ; candidats : `votes`, `votes-motions`, `divergences` si un mandat de député le recouvre (un compte nul n'est alors pas servi) ; législature : compteur `votes_solennels` | doc. 1, 1.5.5 : « scrutins XIVe après le 24/11/2016 : `trou_source` » et « un contrôle de continuité par législature déclare chaque numéro manquant », annoncés, jamais écrits | 1 (1.5.5) |
| Section en panne : « aucun relevé n'a encore abouti pour <point> : ses données manquent ici » quand le point n'a jamais été relevé avec succès ; sinon « données du dernier relevé complet, du <date> » ; `dernier_releve_reussi` dans la couverture. Même distinction dans l'alerte `panne:<point>` (champ `dernier_releve_reussi` du rapport) | #33 : amendements XVe et XVIe, jamais reçus (aucun relevé réussi dans l'entrepôt g10), annoncés comme « données du dernier relevé complet » | 2 (2.10, 2.11) |
| Une section d'une année (amendements, exposés, paroles par semestre) ne déclare que les sources des législatures qui recouvrent cette année | trouvé en vérifiant #33 : 310 sections en panne en local, dont les amendements de 2012 à 2016 et de 2025–2026, complets, déclarés en panne par l'archive de la XVe ou de la XVIe ; les années réellement privées de données (2018 à 2023) n'ont, elles, aucune section : seule la section `amendements` (décomptes) dit la panne | 1 (1.5.5) |

Essai sur GitHub (13/11/2026, 11 h 40 → 12 h 30 UTC, collecte limitée à `jo-global` et
`jo-livraisons`) : archive globale téléchargée, vérifiée et découpée en 1 375 s (23 min ;
1 754 209 938 octets, 843 579 fichiers découpés) ; collecte 34 min, pic 1,7 Go ; calcul 11 min
(lecture du JO comprise), pic 5,0 Go (E4 ; « 4,2 Go » écrit d'abord d'après `time -v`, corrigé le 13/11) ; **publication autorisée**, 64 fiches, 2 297 983 faits
publiés (sans les amendements XVe et XVIe, jamais reçus en production, d'où l'écart avec le
calcul local) ; export de tous les faits : 12 621 265 faits, 370 clés en double (alerte #30).

## Sort des textes : codes de conclusion non classés (13/11/2026)

Branche `etape-2-sort-des-textes`, issue #45. Mesuré sur l'entrepôt g10 (règles seules, en local).

| Changement | Pourquoi | Documents à aligner |
| --- | --- | --- |
| R-ETAPE (version 2) : adoptions `TSORTF04` (« adoptée définitivement »), `TSORTF12`, `TSORTF20`, `TSORTF21` (résolutions adoptées ou « considérées comme définitives », articles 151-3, 151-7, 151-9 du Règlement), `TSORTF14` (« en termes identiques », aussi conforme), `TSORTF23` (« modifié par le Sénat… ») ; rejet `TSORTF13` (« rejeté définitivement ») | #45 citait `TSORTF13` et `TSORTF14` ; la mesure trouve 9 codes hors des deux listes. 14 résolutions européennes passent de « non connu » à « adopté » | 1 (1.6 R-ETAPE) |
| R-SORT-FINAL (version 2) : raison `conclusion_non_classee` quand la dernière décision a un code non classé ; table `conclusion_non_classee` (code, libellé, décisions, dossiers, exemples) ; l'avertissement A7 les nomme | restent `TSORTMOT01` « Motion adoptée » (25 dossiers de la XIVe, en première lecture, sans décision ensuite : la source ne dit pas si c'est un rejet préalable ou un renvoi en commission, rien n'est deviné ; 22 dont c'est la dernière décision) et `TSORTFnull` (11 décisions sans libellé, XVe) | 1 (1.6), 2 (2.8.2 A7) |

PR #50 fusionnée le 13/11/2026 à 12 h 41 UTC, avant l'essai. Essai sur `main` aussitôt après
(12 h 42 → 13 h 00 UTC, collecte limitée à Wikipédia et Wikidata, calcul sur tout l'entrepôt) :
**publication autorisée**, 72 fiches (37 candidats), 1 882 326 faits publiés (1 766 930 en g10),
calcul 7 min 37 s, pic 3,7 Go (d'après `time -v` : minorant, rapport de cet essai plus disponible). Le même calcul en local (entrepôt g10, comparé aux faits publiés de
g10) donne les mêmes chiffres, en 21 min avec un pic de 3,3 Go ; avertissements : A9 nomme
« candidat/xavier-bertrand retirée cette nuit », A6 compte les 7 candidats sans fiche (X. Bertrand
et les 6 retirés, chacun avec sa raison), A3, A5, A8 inchangés. Fiches vérifiées : Lassalle
`partiel` (député de 2002 à 2022), Branco et Zemmour `hors_perimetre` avec leur élément Wikidata,
Collovati `aucun_element`.

## Dernière lecture : vote plus récent non relié signalé (13/11/2026)

Branche `etape-2-derniere-lecture`, issue #34, décision Q32 (« Garder, signalé », doc. 5).

| Changement | Pourquoi | Documents à aligner |
| --- | --- | --- |
| R-DERNIERE-LECTURE (version 2) : `votes_posterieurs_non_relies`, les votes sur l'ensemble non reliés (`scrutin_non_relie`), plus récents que le vote retenu, dont le dossier est candidat (discuté ou décidé dans la séance du vote, ou candidat d'une route en désaccord). Servi dans `votes-<n>` des lignées, `votes` et `divergences` des candidats ; nouvelle couverture `derniere_lecture_sans_vote_posterieur_non_relie` | #34 : `VTANR5L15V314` (première lecture) publié comme dernière lecture de `DLR5L15N35986`, le texte de CMP (`VTANR5L15V386`, 06/02/2018) n'étant relié à aucun dossier. Mesuré sur la g10 : 170 votes sur l'ensemble non reliés, 75 dernières lectures sur 665 signalées. Relier par « le seul dossier décidé dans la séance » a été mesuré et écarté (6 erreurs sur 309 votes déjà reliés par un acte) | 1 (1.6 R-DERNIERE-LECTURE) |

## Contrôles qui se taisaient (13/11/2026)

Branche `etape-2-controles-silencieux`, issues #39, #40, #41.

| Changement | Pourquoi | Documents à aligner |
| --- | --- | --- |
| Lecture : une version qu'un lecteur ne peut pas lire n'est plus inscrite comme lue (relue la fois suivante) ; les lots déjà écrits avant l'erreur (gros membre lu par lots) sont retirés ; `Lecture.illisibles` la nomme | #39 : la version illisible était tenue pour lue pour toujours (jusqu'à un changement de version du lecteur), et un membre lu par lots pouvait laisser des faits partiels | 2 (2.5, 2.11) |
| C1 : la perte des faits d'un fichier modifié cette nuit n'est plus « expliquée » si le lecteur n'a pas pu lire ce fichier | #39 : un changement de format à la source faisait disparaître les faits sans que C1 bloque | 2 (2.8.1 C1) |
| `derniere_publication` : « aucune publication » seulement si la release `export` n'existe pas ; une erreur de l'API est réessayée 3 fois, puis fait échouer le calcul (rien n'est publié, alerte « publication : calcul absent ou échoué ») ; un calcul sans publication précédente le dit (avertissement `C1-C6`) | #40 : une erreur passagère de l'API faisait publier sans C1 ni C6, sans rien dire | 2 (2.8.1) |
| Rattrapage : une erreur de l'API est réessayée 3 fois, puis la nuit continue sans rattrapage ; l'erreur va au rapport (`rattrapage_erreur`) et ouvre l'alerte `rattrapage` ; le workflow décide la nuit (`faire`) avant de chercher un acquis, et passe le message par l'environnement | #41 : une erreur de l'API arrêtait `preparer`, donc la nuit **et** l'alerte | 2 (2.1, 2.4) |

## Q23 : mandats restés ouverts dans un organe clos, bornés par décision (13/11/2026)

Branche `etape-2-q23-bornage`, PR #49, issue #12 (A8). Décision Q23 du 13/11/2026 : « borner »
(doc. 5). PR fusionnée par la propriétaire le 13/11/2026 à 13 h 31 UTC.

| Changement | Pourquoi | Documents à aligner |
| --- | --- | --- |
| Décision `decisions/borne_mandat/2026-11-13-mandats-ouverts-organes-clos.yaml` : 9 mandats, chacun avec son organe et la date de fin de l'organe — 7 mandats GOUVERNEMENT du gouvernement Bayrou (`PO855052`, fin 09/09/2025), une mission auprès d'une ministre déléguée à l'industrie (`PM287498`, organe clos le 30/03/2004), une fonction à la Présidence de la République (`PM588892`, organe clos le 15/05/2012) ; type ajouté à `decisions/LISEZMOI.md` | Q23 : ces mandats n'entraient pas dans la composition et étaient signalés chaque nuit (A8) | 1 (1.3.3 : type `borne_mandat`) |
| Liaison : la vue `an_acteurs__mandat` prend la date de fin de la décision quand la source n'en donne pas (`fin_par_decision`, `decision_fin`) ; la vue `an_acteurs__mandat__source` garde la source telle quelle. Toutes les règles lisent la vue bornée ; l'entrepôt n'est pas réécrit | une décision ne corrige jamais une donnée à la main : la source reste ce qu'elle publie | 1 (1.3.3, 1.6 R-COMPOSITION) |
| A7 : une décision `borne_mandat` est « sans objet » quand la source a fermé le mandat ou ne le publie plus | une décision devenue inutile ne doit pas masquer une correction de la source | 2 (2.8.2 A7) |

Essais sur la branche (calcul sur tout l'entrepôt, sans écriture) :

| Essai | Code | Collecte limitée à | Calcul | `time -v` (voir plus bas) | Résultat |
| --- | --- | --- | ---: | ---: | --- |
| `43420979090` (12 h 30 → 12 h 40 UTC) | `79abef0` | — (essai de la branche avant fusion de `main`) | 7 min 28 s | 3,5 Go | publication autorisée, 64 fiches, 1 879 039 faits publiés |
| `43428964601` (13 h 00 → 13 h 10 UTC) | `643b749` (branche + `main` avec #48 et #50 ; conflit sur `decisions/LISEZMOI.md` réglé par fusion, 352 tests verts) | `jo-livraisons` | 7 min 15 s | 3,2 Go | **publication autorisée**, 72 fiches (37 candidats, PR #50), 1 882 326 faits publiés ; avertissements A3 (2 187), A5 (budgets), A6, A9 (fiche de X. Bertrand) ; **plus d'A8, aucun A7** ; A2 : 40 faits vérifiés sur 40, aucun écart ; C3 sans écart inexpliqué |

Mesures par étape du second essai (rapport) : export 48 s ; règles (E4) 35 s, pic 4 333 Mo ;
fiches (E5) 198 s, pic 2 539 Mo ; contrôles (E6) 129 s, pic 3 282 Mo. **Le pic du calcul est donc
4,3 Go, pas les 3,2 Go de `time -v`.**

**Défaut de mesure trouvé (13/11/2026) : le « pic » de `time -v` n'est que celui de la dernière
étape.** `mesures.Mesures.etape` remet le pic du processus à zéro au début de chaque étape
(`/proc/self/clear_refs`), et `time -v` lit ce même compteur à la fin du processus. Vérifié sur
trois rapports : le `Maximum resident set size` de `time -v` est, au kilo-octet près, le pic de la
dernière étape (calcul : E6 ; collecte : `clore`). Exemple, nuit g10 : `time -v` 2 747 468 Ko
(E6, 2 683 Mo), pic réel du calcul **4 813 Mo**. Les pics de calcul cités plus haut dans ce journal
d'après `time -v` (« pic 2,7 Go », « pic 3,6 Go », « pic 4,2 Go »…) sont des minorants ; le pic
réel est le maximum des `pic_memoire_mo` des étapes du rapport. À reprendre dans le rapport de
mesures et dans `migration-vers-le-vrai-depot.md` (« pic 4,2 Go mesuré le 13/11 »).

L'issue #12 (A8) se ferme d'elle-même à la première nuit publiée avec ce code (tâche `alerter`),
attendue le 13/11/2026 au soir.

## Volet européen, lot 1 : mandats de député européen (13/11/2026)

Branche `etape-2-europe-mandats`. Décision Q3 du 13/11/2026 (« Les deux, raccordées en 2019 ») ;
ce lot ne lit que le portail du Parlement européen, pour les mandats.

| Changement | Pourquoi | Documents à aligner |
| --- | --- | --- |
| Point `pe-eurodeputes` (format `pe_eurodeputes`, module `collecte_pe`) : Wikidata (P1186) pour les éléments de la liste des candidats, puis `meps/<id>` de chaque député européen déclaré et `corporate-bodies/<id>` de ses groupes ; une requête toutes les 2,1 s (`Crawl-delay: 2`) ; une réponse en échec fait échouer le relevé (rien n'est rangé) ; rangé sans retrait (un candidat qui sort garde ses données) | le portail ne dit pas qui est candidat ; la réponse Wikidata de la nuit n'est pas relisible pendant la collecte (fichier d'octets ouvert), le point est donc autonome | 2 (2.2, points d'accès) |
| Lecteur `pe_eurodeputes` : `identifiant_pe`, `eurodepute`, `appartenance_pe`, `groupe_pe` | — | 1 (1.4) |
| R-CANDIDATURES v3, R-IDENTITE v3 : identifiant européen (`eurodepute`) de l'élément retenu ; clé `("pe", id)` au registre | rattachement par identifiant déclaré | — |
| R-CARRIERE v2 : institution `parlement_europeen`, mandats `MEMBER_PARLIAMENT` découpés par le groupe européen à la date (périodes contiguës d'un même groupe fusionnées, quel que soit le rôle) ; législature européenne dans le libellé, jamais dans `legislature` ; couverture `aucun_identifiant` / `non_collecte` / `complet` au lieu de `non_collecte` pour tous | cahier 4.2 (frise par institution) | 1 (1.5.1) |

Mesures (13/11/2026) : collecte réelle 43 s, 21 requêtes, 84 Ko (33 éléments, 6 députés européens,
14 groupes) ; relancée aussitôt : 0 version nouvelle sur 21 (octets stables). Règles sur les données
de la génération 10 plus ce relevé : 6 candidats sur 6 à identifiant européen ont leurs mandats ;
Le Pen 2004 → 2017 (NI, ITS, NI, NI, NI, ENF), Mélenchon 2009 → 2017 (GUE/NGL), Philippot 2014 → 2019
(NI, ENF, un jour NI le 03/10/2017, EFDD), Glucksmann depuis le 02/07/2019 (S&D, en cours).

## Rapport de mesures (13/11/2026)

Branche `etape-2-rapport-mesures`, PR #56. Livrable : `3-rapport-de-mesures.md` (commande, 9.3),
généré par la commande, à refaire après chaque nuit.

| Changement | Pourquoi | Documents à aligner |
| --- | --- | --- |
| Commande `empreinte rapport-mesures` (module `rapport_mesures`) : relit l'artefact `rapport` de chaque mise à jour qui écrit (gardé 90 jours ; un cache local garde les nuits dont l'artefact a expiré) et les durées de tâches de GitHub ; un tableau par mesure de la section 5, une ligne par nuit. Le premier relevé d'un point est compté à part (premier remplissage), pas dans les objets nouveaux de la nuit | commande, section 5 : chaque mesure avec sa date, sa population, sa méthode, sur GitHub Actions | 4 (estimations remplacées par les mesures) |
| Pic de mémoire d'une tâche = maximum des pics de ses étapes | `time -v` ne voit que la dernière étape (voir la section Q23 ci-dessus) | 4, migration (« pic 4,2 Go ») |

Premiers chiffres (g1 à g10, aucune nuit de la série) : pic réel du calcul 3,6 à 3,9 Go sur la XVIIe
(E5), **4,7 Go en g10** (E4, périmètre XIVe–XVIIe) ; collecte d'une nuit ordinaire 1 à 5 min sur la
XVIIe, 1 h 06 en g10, dont 1 h 01 pour les amendements XVe et XVIe, coupés par l'Assemblée et
abandonnés après ≈ 30 min chacun (#32) ; entrepôt 864 Mo en g10, +12 à
+23 Mo par nuit sur la XVIIe ; aucune écriture réessayée ni échouée ; fiche de candidat : 5 Ko au
chargement initial (médiane), 11 Ko toutes sections ouvertes (médiane), 590 Ko au plus (F. Ruffin, g10).
Sénat en panne 4 nuits sur 10 (g1, g3, g4, g7).

## Sort des textes : suite absente des archives (13/11/2026)

Branche `etape-2-suite-absente`, issue #35 (première partie), décision du 13/11/2026 « Dire le trou, puis relier ».

| Changement | Pourquoi | Documents à aligner |
| --- | --- | --- |
| R-SORT-FINAL (version 3) : raison `suite_absente_des_archives` et date `fin_archive_du_dossier` pour un dossier publié par la seule archive d'une législature close, avec des actes de la législature suivante | #35 : `DLR5L14N35818` (loi 2018-287) n'est publié que par l'archive de la XIVe, arrêtée au 22/03/2018 (son dernier acte : dépôt en CMP le 16/02/2018) ; l'archive de la XVe ne le publie pas. Mesuré sur la g10 : 17 dossiers, jusqu'ici « aucune décision finale » (16) ou « aucune décision en séance » (1). L'Assemblée ne publie pas de NOR dans ses documents : pas de clé directe avec la loi au JO | 1 (1.6 R-SORT-FINAL) |

Reste (seconde partie, avec la session Journal officiel) : R-LOI-DOSSIER, relier une loi du JO à son dossier par les travaux préparatoires publiés avec la loi (numéros des documents de l'Assemblée), puis l'écart « lois de la XIVe : 396 ».

Essai sur la branche (13/11/2026, 13 h 58 → 14 h 07 UTC, `points=pe-eurodeputes`) : publication
autorisée, 72 fiches, 1 882 340 faits publiés (+14 par rapport à `main` : les 14 périodes
européennes), calcul 6 min 34 s, pic 3,4 Go.

## Cache des faits lus et vérification des workflows (13/11/2026)

Branche `etape-2-cache-et-workflow` (sur `etape-2-controles-silencieux`), issues #44 et #47.

| Changement | Pourquoi | Documents à aligner |
| --- | --- | --- |
| Cache de Z2 : une version lue se reconnaît à (point, uid, version, **empreinte**) ; un cache sans empreinte (d'avant ce changement) ne reconnaît rien, tout est relu une fois (≈ 10 min de lecture de plus, une nuit) | #44 : le numéro de version ne dépend pas du contenu ; une version N lue par un essai (ou une nuit non écrite) et remplacée ensuite par d'autres octets sous le même numéro était tenue pour lue. La docstring de `lecture` disait déjà « indexé par empreinte » | 2 (2.5) |
| `tests.yml` : tâche `workflows`, actionlint 1.7.7 (archive vérifiée par les empreintes publiées avec cette version) et shellcheck sur chaque bloc `run:` ; trois remarques corrigées dans `mise-a-jour.yml` (sorties de `preparer` en un bloc, SC2129 ; `find` au lieu de `ls`, SC2012) | #47 : le shell des workflows n'était vérifié par rien. Le constat de l'issue sur les commentaires YAML est inexact : dans un bloc `run: |`, `#` n'est pas un commentaire YAML ; c'est le shell qui coupe la ligne. actionlint n'a trouvé aucune erreur réelle | 2 (2.15), 4 |

## Transport : budget tenu, hôte suspendu, échéance de la collecte, relevé dédié (13/11/2026)

Branche `etape-2-transport`, issues #37, #38 et première partie de #32 (décision Q34, doc. 5).

| Changement | Pourquoi | Documents à aligner |
| --- | --- | --- |
| Le budget d'un fichier est tenu **pendant** la copie (arrêt au bloc suivant), pas seulement entre deux essais | #37 : un serveur au compte-gouttes, sans 60 s de silence, retenait la collecte jusqu'à la limite de la tâche | 2 (2.2) |
| Un hôte suspendu pour la mise à jour après 3 points de suite sans un octet reçu ; ses points suivants échouent tout de suite | #37 : un hôte qui répond 500 à tout brûlait 750 s de pauses par point (35 points sur `data.assemblee-nationale.fr`) | 2 (2.2, 2.11) |
| Échéance de toute la collecte (`duree_collecte_max_s`, 270 min) : passée, les points restants ne sont pas relevés et la collecte se termine normalement, acquis déposé | #38 : une collecte coupée par la limite de la tâche (330 min) perdait les relevés réussis de la nuit. Reste non couvert : un runner arrêté | 2 (2.11) |
| `budget_s` propre à un point (`an-amendements-l15`, `-l16` : 7 200 s), appliqué seulement quand la mise à jour nomme ces points | #32, décision Q34 : relevé dédié, la nuit garde 30 min par fichier | 2 (2.2), 4 |

## Valeurs vidées : avertissement A9, en-tête des candidats publié (13/11/2026)

Branche `etape-2-valeurs-et-forme`, issue #42, décision Q35 (doc. 5).

| Changement | Pourquoi | Documents à aligner |
| --- | --- | --- |
| A9 (avertissement) : pour les faits présents les deux nuits sous une identité unique, champs qui passent d'un nombre non nul à 0 ou à rien, ou d'une valeur à rien ; par type de fait et champ, au-delà de 1 % des faits du type ou de 50 faits | #42 : C1 compare l'identité (à ne pas rouvrir) ; rien ne voyait un compteur passer de 6 à 0. Mesuré entre la g10 et `main` du 13/11 après-midi : 3 signalements, tous des changements voulus du jour (gouvernements de la XIVe avec fiche : `raison_lien` vidée ; sièges des législatures closes : `raison_siege`). Première version écartée : appariement de faits sous une même identité (un effectif par date d'un maillon), qui donnait de faux « passés à 0 » | 2 (2.8.2 : A9) |
| En-tête d'une fiche de candidat publié comme fait `identite_personne`, reconnu à son `per` | #42 : le bloc `personne` (profession, naissance…) n'était pas un fait publié, donc surveillé par rien | export (`docs/export.md` ne liste pas les types) |

## Volet européen, lot 2 : votes nominatifs depuis juillet 2019 (13/11/2026)

Branche `etape-2-europe-votes` (contient le lot 1). Décisions Q3 et Q33 du 13/11/2026.

| Changement | Pourquoi | Documents à aligner |
| --- | --- | --- |
| Point `pe-votes` (format `pe_votes`) : liste des séances plénières de chaque année depuis le 02/07/2019, puis les décisions de chaque séance (`meetings/<séance>/decisions`), gardées à l'octet, réponse vide comprise (404 ou 204 : séance sans décision, un lundi) ; une séance rangée n'est relue que si elle a moins de 60 jours ; budget de 40 min, reprise la nuit suivante ; GET direct, 404 et 204 acceptés, seuls une erreur réseau et un 5xx réessayés | le transport des archives traite un 404 comme une panne (pauses de 30 s, 2 et 10 min) | 2 (2.2) |
| Lecteur `pe_votes` : `seance_pe`, `vote_pe` (une ligne par décision), `position_pe` (une ligne par décision et par position, avec la **liste** des députés européens) | une ligne par député et par vote ferait 15 à 20 millions de lignes | 1 (1.4) |
| R-VOTE-PE : les positions des candidats (pour, contre, abstention, telles que publiées ; correction d'intention à part ; deux listes pour une même personne : position non établie) ; nature lue dans la fin du libellé : `ensemble`, `partie`, `procedure`, `non_etablie` | Q33 ; la nature `procedure` ajoutée après mesure (votes de renvoi, demandes de groupe, procédure d'urgence) | 1 (1.6) |
| Fiche candidat : index `europe` et `europe-votes-<année>` ; couverture `complet` (mandat depuis 2019), `partiel` (mandats avant et après), `non_collecte` (mandats avant 2019 seulement : Parltrack, lot 3) ; rapports et paroles au PE : `non_collecte` | cahier 4.2, volet européen à part | 1 (1.7.2) |

Mesures (13/11/2026) : collecte réelle en local 17 min 15 s, 407 requêtes (399 séances, dont 39 sans
décision), 382 Mo reçus, 51 Mo dans l'entrepôt, pic 0,2 Go ; 35 691 décisions, dont 25 780
nominatives, du 15/07/2019 au 12/11/2026. R. Glucksmann : 24 002 votes nominatifs (juillet 2019 →
octobre 2026), nature établie pour 23 900 (ensemble 2 241, partie 21 441, procédure 218 ; non
établie 102), une position non établie, 54 corrections d'intention ; 8 fichiers annuels de ≈ 220 Ko
compressés. Lecture des décisions 19 s ; règles 106 s, pic 2,2 Go.

## Forme des fichiers servis : schéma commité (13/11/2026)

Branche `etape-2-forme-des-fichiers`, issue #43, décision du 13/11/2026 « Schéma commité, bloquant ».

| Changement | Pourquoi | Documents à aligner |
| --- | --- | --- |
| `config/schema_fichiers.yaml` : colonnes de chaque section (nom où les nombres deviennent `N` ; index de mots `<type>/mots/*`), vocabulaires de 14 champs fermés (sort final, raison du sort, étape, origine, matière, lecture, positions, partage, banc, rôle, nature du sujet), statuts de couverture du doc. 1 (1.5.5). C4 refuse une section inconnue, des colonnes changées, une valeur hors vocabulaire, ou un schéma absent. `empreinte schema --site <sortie>/site` réécrit les colonnes d'après un calcul ; les vocabulaires se modifient à la main | #43 : rien ne vérifiait la forme ; doc. 2, 2.8.1 prévoyait déjà « validation de chaque fichier contre son schéma en liste blanche ». Colonnes tirées du calcul local du 13/11 (42 sections, aucun écart), puis complétées sur le site de l'essai 43458918104 (branche des mandats locaux, volet européen compris) : 44 sections, dont `candidats/europe` et `candidats/europe-votes-N`, aucun écart. Essai de la PR sur l'entrepôt de production (43460310627) : publication autorisée. Ordre de fusion convenu : après #64 et #91 | 2 (2.8.1 C4), 7 (contrat des fichiers servis) ; **toute PR qui change une section met le schéma à jour** |

## Mandats locaux des candidats (13/11/2026)

Branche `etape-2-mandats-locaux` (sur `etape-2-europe-votes`). Décisions du 13/11/2026 : mandats
locaux réintégrés au périmètre ; Q34 (nom, prénom et date de naissance, sinon décision) ; Q35 (fin
déduite au 15/03/2026 pour un mandat municipal 2020-2026).

| Changement | Pourquoi | Documents à aligner |
| --- | --- | --- |
| 11 points `rne-*` (format `fichier`, adresse stable `/datasets/r/<id>`, requête conditionnelle, plancher de taille) : 9 fichiers du Répertoire national des élus (municipaux, maires, communautaires, départementaux, régionaux, d'arrondissement, collectivités à statut particulier, Français de l'étranger ×2) et les 2 fichiers des sortants des municipales 2026 ; députés, sénateurs, députés européens non relevés (sources propres) | cahier 3.9 | 2 (2.2) |
| Lecteur `rne_elus` : `mandat_local`, une ligne par ligne publiée, colonnes lues par leur nom ; dates `JJ/MM/AA` des sortants converties (naissance au XXe siècle au-delà de `08`), date publiée gardée ; clé d'export du doc. 1 (pas le numéro de ligne, qui se décale) | — | 1 (1.4, G) |
| Point `pe-eurodeputes` : la requête Wikidata des éléments de la liste demande aussi la date de naissance (P569) → table `naissance_wikidata` ; R-CANDIDATURES v4 l'utilise quand la grande requête ne couvre pas la personne | 16 candidats n'avaient de date de naissance que par Wikidata hors identifiant parlementaire (dont Lisnard) | — |
| R-MANDAT-LOCAL : rattachement par prénom et nom d'un seul tenant (sans accents, casse, espaces ni tirets) **et** date de naissance exacte, ou par décision `elu_local` ; un élu revendiqué par deux candidats n'est rattaché à aucun ; même mandat dans deux fichiers : une ligne ; fin déduite au 15/03/2026 pour les sortants municipaux, signalée | Q34, Q35 | 1 (1.5.1, 1.6) |
| R-CARRIERE v3 : institution `local` ; couverture `partiel` (depuis 2020), `non_etabli` (date de naissance inconnue, servie `non_relu`), `non_collecte` | cahier 4.2 | 1 (1.5.5) |
| Décision `elu_local/2026-11-13-platret.yaml` : Gilles Platret, élu unique de ce nom, né le 19/04/1973, âge concordant avec la liste (53 ans) | Q34 : candidat sans date de naissance connue | — |

Mesures (13/11/2026, fichiers du 11/08/2026 et sortants du 27/02/2026, 1 136 316 lignes ; lecture
25 s) : 34 candidats sur 44 à identité recherchable (33 par date de naissance, Platret par
décision) ; 14 avec des mandats locaux, dont 10 déclarés (Lisnard, Bouamrane, Roussel, É. Philippe,
Dupont-Aignan, Becht, Attal, Tondelier, Retailleau, Platret) ; aucun élu revendiqué par deux
candidats ; homonymes écartés par la date (Roussel : 3). Benoît Mathieu : l'élu de ce nom a 51
ans, le candidat 27 : non rattaché.

Essai du lot 2 sur la branche (13/11/2026, 14 h 55 → 15 h 21 UTC, `points=pe-eurodeputes pe-votes`) :
publication autorisée, 72 fiches, 1 906 342 faits publiés (+24 002 : les votes de R. Glucksmann) ;
premier remplissage 17 min 14 s (407 requêtes, 382 Mo) ; calcul 6 min 29 s.

Essais de la branche des mandats locaux (13/11/2026) : 43456313070 (15 h 48 → 16 h 03 UTC,
`rne-*` et `pe-eurodeputes`) : publication autorisée, +29 faits publiés (les périodes de mandat
local) ; collecte des 11 fichiers d'élus 1 min 20 s (145 Mo) ; **23 clés d'export en double** :
adjoints et maires délégués dont la même fonction est attribuée deux fois dans un mandat (Petit-Bourg,
2020 puis 2021) ; corrigé en ajoutant la date de début de fonction à la clé. Puis 43458918104
(16 h 04 → 16 h 38 UTC, branche à jour de `main`, élus, députés européens et votes européens :
lots 2 et mandats locaux ensemble, avec les contrôles de valeurs de #62) : publication autorisée,
72 fiches, 1 906 408 faits publiés, **0 clé en double** dans l'export ; collecte 17 min 25 s ;
calcul 14 min 06 s (sans cache des faits lus, #92). Le site de cet essai a servi à régénérer le
schéma des fichiers servis de #66 (sections `europe`, `europe-votes-<année>` des candidats).

Fusionnées le 13/11/2026 : #50 (liste franceinfo) 12 h 40, #55 (mandats européens) 14 h 09,
#64 (votes européens) 16 h 49, #91 (mandats locaux, décision Platret), puis #66 (schéma) ; ordre
fixé avec la session « New pipeline issues » pour que C4 connaisse les sections nouvelles. La nuit
du 13/11 fait le premier remplissage des décisions du Parlement européen (≈ 17 min, une fois) et
le premier relevé des fichiers d'élus.

## Essais en parallèle ; un essai ne garde plus les faits lus (13/11/2026)

Branche `etape-2-essais-paralleles`, proposée par la session candidats, validée par la propriétaire.

| Changement | Pourquoi | Documents à aligner |
| --- | --- | --- |
| Chaque essai (`workflow_dispatch`, mode `essai`) a sa propre file de concurrence ; la nuit, `quotidien` et `complet` gardent la file `mise-a-jour` | six essais de trois sessions s'attendaient les uns les autres ; un essai n'écrit rien. Règle gardée : aucun essai qui déborde sur 20 h 30 UTC (il lirait l'entrepôt pendant qu'il s'écrit) | 2 (2.3, 2.15) |
| Un essai n'enregistre plus le cache des faits lus (`z2-…`) | #44, seconde moitié : la nuit reprend le cache le plus récent, qu'un essai écrivait avec le code de sa branche | 2 (2.5) |

Validé le 13/11 : deux essais lancés ensemble à 15 h 32 UTC (exécutions 43453567542 et 43453573057), en même temps qu'un troisième (PR #62) ; les trois réussis, aucun cache `z2-` enregistré par les deux premiers.

## Pic de mémoire : le plus haut des étapes (13/11/2026)

Branche `etape-2-pic-memoire`, PR #58. Défaut décrit plus haut (section Q23) : le `Maximum resident
set size` de `time -v` n'est que le pic de la dernière étape.

| Changement | Pourquoi | Documents à aligner |
| --- | --- | --- |
| `Mesures.pic()` : le plus haut des pics des étapes d'une tâche, avec l'étape ; la collecte et le calcul l'impriment dans leur résumé ; le workflow ne cite plus que la durée de `time -v` | les pics cités jusqu'au 13/11 étaient des minorants (g10 : 2,6 Go selon `time -v`, 4,7 Go réels) | 4 (remplacé par le rapport de mesures) |

Essai sur la branche (`43441446764`, 14 h 18 UTC) : publication autorisée ; « Pic de mémoire :
4,460 Mo (étape E4) » affiché.

## Comptes rendus : paragraphe publié deux fois sous le même identifiant (13/11/2026)

Branche `etape-2-paragraphes-doubles`, PR #65, alerte #30 (`export:doublons`). Recommandation validée
par la propriétaire le 13/11/2026.

| Changement | Pourquoi | Documents à aligner |
| --- | --- | --- |
| Lecteur `an_comptes_rendus` version 2 : colonne `occurrence`, rang du paragraphe parmi ceux qui portent le même `id_syceron` dans le compte rendu (0 pour le premier) | 370 comptes rendus de la XVe publient deux fois la fin de séance sous le même identifiant (« La séance est levée… », puis la signature du service) : 370 clés en double dans l'export | 1 (1.2.2 : clé d'une prise de parole) |
| Export : option `rang` de la déclaration `EXPORT` ; `#<rang>` ajouté à la clé à partir du second, la clé du premier ne change pas (`docs/export.md`) | les 1,49 million de clés existantes restent stables d'une nuit à l'autre | export (fait) |

Essai sur la branche (`43451890423`, 15 h 22 UTC) : 2 861 comptes rendus relus par la version 2,
aucun illisible ; **0 clé en double** ; 11 278 464 faits exportés et 1 882 326 faits publiés, comme
avant ; publication autorisée ; calcul 7 min 06 s, pic 4,7 Go (E4).

## Paroles prononcées sous un ancien nom (13/11/2026)

Branche `etape-2-noms-anterieurs`, PR #67. Trouvé en analysant l'avertissement A6 (#11). Décision de
la propriétaire du 13/11/2026 : deux noms par personne, l'actuel et, facultatif, un ancien ; une parole
est rattachée si le nom écrit correspond à l'un ou à l'autre (« si l'identifiant ne change pas, on peut
toujours faire le rattachement »).

Analyse de A6 (entrepôt g10, export de l'essai `43441446764`) : les membres de groupe sans parole servie
sont, pour la XVIIe (19), 6 entrés depuis juillet 2026, 10 aux mandats courts (2 jours à 4 mois,
souvent des suppléants de ministres ; 3 n'ont parlé qu'après avoir quitté le groupe) et 3 présents
toute la législature à qui la source n'attribue aucun paragraphe ; pour la XVIe (2), deux mandats
courts ; pour la XVe, deux mandats courts et un nom changé (2 cas sur 5 non retrouvés par cette
méthode).

| Changement | Pourquoi | Documents à aligner |
| --- | --- | --- |
| R-ORATEUR version 2 : le nom affiché est comparé au nom actuel **et** à tout nom publié pour le même identifiant dans une archive plus ancienne (`an_acteurs__identite_source__archives`, archive figée d'une législature close) ; colonne `nom_anterieur` | la règle exige que le nom écrit corresponde à l'état civil ; un député qui a changé de nom perdait ses paroles antérieures (`nom_discordant`) : PA721296, « Gouffier-Cha » en XVe, « Gouffier Valente » ensuite (567 paragraphes) ; PA719756, « Cloarec-Le Nabour » en XVe, « Le Nabour » ensuite (27). Un nom que la source n'a jamais donné à l'identifiant reste discordant (« Alice Rufo » sous l'identifiant de F. Ruffin ; « Arnaud Sanvert » sous celui de M. Simion, 1 paragraphe) | 1 (1.6 R-ORATEUR) |

Essai sur la branche (`43457980715`, 15 h 58 UTC, en parallèle de celui de #90) : **594 paragraphes
rattachés en plus** (1 338 508 → 1 339 102) et autant de faits publiés ; A6, XVe : 3 → 2 membres
sans parole ; publication autorisée ; calcul 14 min 08 s, pic 4,6 Go.

## A3 : seuls les écarts d'effectif inexpliqués sont nommés (13/11/2026)

Branche `etape-2-a3-affine`, PR #90, avertissement A3 (#9). Décision de la propriétaire du 13/11/2026
(« oui, affine A3 »), après analyse.

Analyse (entrepôt g10) : 2 187 décomptes de groupe sur 193 821 ont un effectif publié différent de nos
appartenances ; **aucun n'est inexpliqué**. 1 592 sont des **transitions** : au moins autant de membres
entrent dans le groupe ou en sortent à 7 jours ou moins du scrutin que l'écart en compte (ministres
remplacés par leurs suppléants le 22/10/2024 et le 13/11/2025 : un jour où les sortants ont quitté le
groupe et les suppléants n'y sont pas encore inscrits ; création de R-UMP le 27/11/2012, où notre règle
fait finir l'appartenance à l'UMP la veille). 595 portent sur un **organe hors de ses dates** :
l'Assemblée rattache le décompte à un organe de groupe clos (groupe socialiste de la XVIe : organe clos
le 18/10/2023, employé jusqu'au 14/03/2024, 581 décomptes ; SOC-A 8, UDI-AGIR 4, UDI-A-I 2). Rien ne
change à l'écran : les 584 scrutins socialistes concernés sont servis dans `votes-16` de la lignée.

| Changement | Pourquoi | Documents à aligner |
| --- | --- | --- |
| A3 classe chaque écart (`transition`, `organe_hors_dates`, `inexplique`) ; seuls les inexpliqués sont nommés, les autres comptés dans le détail ; fenêtre de 7 jours réglable (`A3_FENETRE_TRANSITION` ; avec 3 jours, 75 écarts resteraient inexpliqués) | l'avertissement criait chaque nuit pour des écarts tous expliqués | 2 (2.8.2 A3) |

Essai sur la branche (`43457985883`, 15 h 58 UTC) : **plus d'avertissement A3** ; publication
autorisée ; calcul 11 min 33 s, pic 4,7 Go. L'issue #9 se ferme d'elle-même à la première nuit publiée
avec ce code.

## Pages du dépôt d'essai (13/11/2026)

Décisions de la propriétaire du 13/11/2026 : « je pense que je vais activer la page du depot de test afin
de visualiser à minima la doc », puis « Doc + page minimale » ; plus tard, publier aussi les livrables
(cadrage). PR #93, puis #99 (issue #95, faite par un agent).

| Changement | Pourquoi | Documents à aligner |
| --- | --- | --- |
| Workflow `pages.yml` : documentation du code (pdoc) et page minimale avec les fichiers servis de la dernière publication (archive de la release `publication`), après chaque mise à jour réussie sur `main` et chaque envoi de code ; seule la tâche `deployer` a les droits de Pages (`pages: write`, `id-token: write`), testé | voir la doc et ce que chargent les fiches sans télécharger d'artefact | 2 (2.12), migration (fait) |
| Page `traitement/`, générée depuis le code (`methodologie.py`) : étapes E0–E8, périmètre, 12 lecteurs et leurs sources, 40 règles dans leur ordre avec leur description, 7 contrôles bloquants et 10 avertissements | la doc pdoc ne dit pas comment fonctionne le traitement (issue #95) | — |
| Page `livrables/` : les documents de conception et de l'étape 2 convertis en HTML (`pages_livrables.py`, markdown2 épinglé) | décision du 13/11/2026 | — |

Premier déploiement (13/11/2026, 16 h 08 UTC) : construction 29 s, déploiement 14 s ; 159 Mo, dont
13 269 fichiers pour la page minimale (g10). Les fichiers servis `.json.gz` sont servis tels quels
(`application/gzip`), la page minimale les décompresse : vérifié. Restes signalés par l'agent de #99 :
10 contrôles sans docstring (C2, C4, C7, A1, A2, A4–A8), le même code A9 pour deux avertissements.

## Livrables versés dans le dépôt ; doc. 4 remplacé par le rapport de mesures (13/11/2026)

PR #97, fusionnée à 16 h 32 UTC. Décisions de la propriétaire du 13/11/2026 : « on remplace le point 4
par le rapport de mesure », et, pour publier les livrables, « Déplacés dans le dépôt ».

| Changement | Pourquoi | Documents à aligner |
| --- | --- | --- |
| Les livrables vivent dans le dépôt (`livrables/` : docs 0 à 8, `etape-2/`, `annexes/mesures/`) ; chaque modification passe par une PR. L'ancien dossier hors dépôt est gelé (note `DEPLACE-DANS-LE-DEPOT.md`), rien n'y est supprimé ; identique au dépôt à la bascule (`diff -r`). `annexes/scripts/` n'est pas versé (non relu) | publication sur Pages, toujours à jour | 0 (LISEZMOI) |
| Le doc. 4 (estimations) n'est pas réaligné : le rapport de mesures (`3-rapport-de-mesures.md`) le remplace | commande 1.4 : chaque estimation remplacée par une mesure | 4 |

Les sessions « candidats » et « issues » ont confirmé n'avoir rien écrit dans l'ancien dossier après la
bascule. Issues ouvertes le même jour : #94 (177 fonctions publiques sans docstring) et #95 (page
« traitement », faite par #99).

Essai sur `main` après ces fusions (`43464134163`, 13/11/2026, 16 h 35 → 16 h 48 UTC, `fd1fa8a` :
#65, #67, #90, #93, #97 ensemble ; collecte limitée à Wikipédia, calcul sur tout l'entrepôt) :
**publication autorisée** ; 0 clé en double ; 1 339 102 paragraphes attribués (+594) ; plus
d'avertissement A3 ; 72 fiches, 1 882 957 faits publiés ; calcul 11 min 31 s, pic 4,7 Go (E4).


## Documents illustrés fusionnés dans les spécifications (13/11/2026)

Demande de la propriétaire, le 13/11/2026 : « dans document de conception, il faudrait mettre
la section 6 dans la section 2 (peut-être au début). et la section 7 dans la section 1. L'idée
étant que on ait les illustration à coté. Pour info, les diagramme flux sont visible en code et
non en schéma compilé. Il faudrait aussi que les tables de matière soit accessible peut importe
ou on se trouve pour facilité la navigation (pas que dans le doc de conception. » Choix : les
illustrations à côté de chaque section. Les schémas dessinés et le sommaire viennent du passage
de toute la documentation au format pdoc (décision de la propriétaire du 13/11/2026, traité à
part) : les blocs Mermaid restent tels quels dans le Markdown.

| Changement | Pourquoi | Documents à aligner |
| --- | --- | --- |
| Le document 6 (le processus, expliqué) est réparti dans le document 2 et le document 7 (le modèle, expliqué) dans le document 1 : chaque schéma et son texte sont sous un intertitre « En image » dans la section qu'ils illustrent ; les vues d'ensemble (6.1, 7.1) ouvrent les documents. Aucune section des documents 1 et 2 n'est renumérotée. Les fichiers 6 et 7 deviennent des notes qui disent où chaque partie est passée | lire la spécification et son illustration ensemble | 0 (liste des documents) |

Les écarts entre un schéma et le texte de la spécification ne sont pas tranchés ici : la
spécification fait foi, et les écarts relevés sont listés dans la PR.

## Restes de #41 et #44, issues rouvertes (13/11/2026)

Branche `etape-2-restes-41-44`. Les issues #41, #42 et #44 ont été rouvertes à 16 h 34 UTC par une relecture du code (`main` fd1fa8a).

| Changement | Pourquoi | Documents à aligner |
| --- | --- | --- |
| `planification` : trois essais ; si le manifeste reste illisible, la nuit se fait (`true`), l'erreur au journal de la tâche ; le workflow retombe aussi sur `true` | #41 : sur une nuit planifiée, la planification appelle l'API avant d'écrire `faire` ; une erreur y supprimait la nuit et l'alerte. Au pis, le second déclenchement refait une nuit déjà faite | 2 (2.3) |
| Lecture : seules les versions encore portées par l'entrepôt restent inscrites comme lues | #44 : une version sortie de l'entrepôt perd ses lignes mais restait « lue » ; revenue avec les mêmes octets, elle n'aurait plus aucun fait (déduit du code, non observé). Le second point de la réouverture (« les essais sur `main` sauvent toujours le cache ») ne tient pas : essai sur `main` 43467867327 du 13/11, étape « Garder les faits lus » sautée, aucun cache `z2-` | 2 (2.5) |

## A9 : un compteur à 0 toujours signalé, identités partagées appariées (13/11/2026, soir)

Branche `etape-2-a9-compteurs`, issue #42 rouverte, décision Q35 révisée (« Nombre à 0 : toujours »).

| Changement | Pourquoi | Documents à aligner |
| --- | --- | --- |
| Un nombre qui passe à 0 ou à rien est signalé même seul ; le seuil (1 % ou 50) ne vaut plus que pour les autres champs vidés | relecture du 13/11 : `positions_textes` d'un candidat, 165 → 0 (1 fait sur 638), ne déclenchait rien ; c'est le cas même de l'issue | 2 (2.8.2 A9) |
| Plusieurs faits sous une même identité s'apparient par les champs discriminants de leur valeur (`institution`, `date`, `legislature`, `role`…) ; seuls les doublons restants sont écartés | 203 des 638 `compte_candidat` partageaient leur identité (un compte par institution) : `mandats` 6 → 0 passait inaperçu | — |
| Connexion DuckDB de A9 sous la limite de mémoire du traitement ; extraction des discriminants pour les seules identités partagées | première version tuée en local (mémoire) ; mesurée ensuite : 41 s, 2,2 Go, g10 contre `main` du 13/11 : mêmes 3 signalements que l'après-midi | 4 |

Restent hors de A9 : les faits sans identifiant (94 `actes_compte`) et `parole_sujet`, dont le numéro d'ordre se décale.

## Amendements de la XIVe : examen tiré de l'uid (13/11/2026, soir)

Branche `etape-2-amendements-xiv-examen`, issue #111 (constat transmis par la session d'analyse, à la demande de la propriétaire).

| Changement | Pourquoi | Documents à aligner |
| --- | --- | --- |
| Lecteur `an_amendements` (version 2) : l'examen d'un amendement de la XIVe est tiré de son uid, qui a la même grammaire qu'aux législatures suivantes (`AMANR5L14PO419610B1179P0D1N482` → `EXANR5L14PO419610B1179P0D1`) | #111 : le schéma de la XIVe n'a pas d'examen ; R-AMENDEMENT dédoublonnait par le seul numéro : 167 420 amendements lus, 22 159 gardés (g10). Après : 167 420 gardés ; Delphine Batho, 65 → 158 amendements de la XIVe (CE435 revient). Relecture des amendements une fois (≈ 3 min en local) | 1 (1.6 R-AMENDEMENT) |
| C6 compte une section avec ses paquets (`amendements-2013` et `amendements-2013-1`, `-2`… : numéro de paquet après une année ou un semestre) | premier essai de la branche (43477541508) refusé par C6 : 21 sections « tombées à 0 », dont `lignee/droite-republicaine/amendements-2013` 551 → 0, parce qu'avec les amendements retrouvés l'année est découpée en paquets. Rejoué avec la correction : ni C1 ni C6 | 2 (2.8.1 C6) |

## Volet européen, lot 3 : votes nominatifs avant juillet 2019, depuis Parltrack (13/11/2026)

Branche `etape-2-europe-parltrack`. Décision Q3 du 13/11/2026 (« Les deux, raccordées en 2019 ») :
Parltrack pour les votes antérieurs au 02/07/2019.

| Changement | Pourquoi | Documents à aligner |
| --- | --- | --- |
| Point `parltrack-votes` (format `fichier`, `ep_votes.json.zst` gardé à l'octet, ODbL 1.0) : requête conditionnelle, 304 tant que Parltrack ne bouge pas ; `robots.txt` de parltrack.org : aucune règle pour les robots en général (seuls des robots d'IA d'entraînement sont exclus) | Q3 | 2 (2.2) |
| Lecteur `parltrack_votes` : lu en flux (zstandard), `vote_pt` et `position_pt` (positions `+`, `-`, `0` → `favor`, `against`, `abstention`, listes aplaties par groupe), mêmes noms que `pe_votes` | une seule règle pour les deux sources | 1 (1.4) |
| R-VOTE-PE v2 : votes de Parltrack avant le 02/07/2019, du portail ensuite ; chaque ligne dit sa source (`source`, `source_point`) ; formes anciennes des libellés reconnues (« approbation », « Proposition modifiée », « par. 10 », « cons. B », « vote procédural »…) | Q3, Q33 | 1 (1.6) |
| Fiche : licence de chaque vote selon sa source (ODbL pour Parltrack) ; couverture `complet` quand chaque période de mandat a sa source ; colonnes servies inchangées (schéma de #66) | cahier 2.2 | — |

Mesures (13/11/2026) : fichier de 11,25 Mo (44 648 scrutins, dont 21 549 avant le 02/07/2019) ;
lecture 37 s. Votes rattachés : Le Pen 10 670 (15/09/2004 → 17/05/2017), Philippot 8 470
(17/07/2014 → 18/04/2019), Mélenchon 7 823 (25/11/2009 → 16/03/2017) ; aucun vote en double ; les
deux sources se raccordent sans recouvrement (Maurel : Parltrack jusqu'au 18/04/2019, portail
dès le 18/07/2019). Nature non établie : 85 votes de Le Pen sur 10 670, 71 de Mélenchon, 49 de
Philippot. Les quatre candidats anciens ou actuels députés européens ont un volet européen
`complet`.



## Volet européen : activité hors votes (13/11/2026)

Branche `etape-2-europe-activite` (sur `etape-2-europe-parltrack`). Décision Q37 du 13/11/2026 (« Tout,
chacun dans sa section »).

| Changement | Pourquoi | Documents à aligner |
| --- | --- | --- |
| Point `parltrack-activites` (`ep_mep_activities.json.zst`, ODbL, gardé à l'octet) ; point `pe-eurodeputes` : interventions en séance de chaque député européen déclaré (`speeches`, pages de 500 jusqu'au 204) | Q37 | 2 (2.2) |
| Lecteurs `parltrack_activites` (date de republication du 22/11/2016 écartée : date relue dans l'adresse ou la référence, sinon l'année, sinon la législature ; champs publiés parfois en liste) et `pe_eurodeputes` v3 (`intervention_pe`) | cahier 3.4 | 1 (1.4) |
| R-ACTIVITE-PE : interventions de Parltrack avant le 02/07/2019, du portail ensuite ; rapports (rôle : rapporteur, fictif, pour avis), résolutions, questions, explications de vote (extrait de 300 caractères), autres : Parltrack à toutes dates | Q37 | 1 (1.6) |
| Fiche : six sections `europe-<famille>` (déclarées dans `config/schema_fichiers.yaml`) ; colonne `role_pe` (pas `role`, au vocabulaire fermé) ; couverture `partiel` après le gel de Parltrack (24/07/2026) et pour un trou du portail | cahier 4.2 ; C4 | 1 (1.7.2) |

Mesures (13/11/2026, données réelles) : 6 425 activités pour les 6 personnes à identifiant européen,
date établie pour 4 899 ; Mélenchon 2 158 interventions (2009-2017), Le Pen 808, Philippot 749 (et 766
explications de vote, toutes sans date sûre : législature 8) ; Glucksmann 112 interventions au portail,
**aucune avant le 06/07/2021 ni dans Parltrack** (trou de source, section `partiel`) ; 0 écart au schéma
des fichiers servis. Défaut trouvé en route : une résolution de conflit de fusion avait effacé la
licence du point `parltrack-activites` (corrigé, vérifié : chaque point a sa licence).

## Mandats de député antérieurs à 2002, depuis Sycomore (13/11/2026)

Branche `etape-2-sycomore`. Décision Q36 du 13/11/2026 (« Oui, les faits seulement »).

| Changement | Pourquoi | Documents à aligner |
| --- | --- | --- |
| Point `sycomore-fiches` (format `sycomore_fiches`, module `collecte_sycomore`) : identifiants Sycomore déclarés par Wikidata (P1045) pour les éléments de la liste (réponse gardée à l'octet, CC0), puis chaque fiche, dont seuls les **faits** sont gardés (JSON : nom, mandats avec chambre, régime, législature, dates, département, groupe ; version de l'extracteur) ; la page n'est pas gardée ; une requête toutes les 2,1 s ; pas de `robots.txt` sur www2.assemblee-nationale.fr (404) | cahier 2.2 et 3.11 : « tous droits réservés », des faits seulement ; conséquence : une erreur d'extraction se corrige en relevant de nouveau, pas en relisant l'entrepôt (P2 impossible sans droit de garder la page) | 1 (1.3.2, 1.7.4), 2 (2.2) |
| Lecteur `sycomore` : `identifiant_sycomore`, `mandat_sycomore` | — | 1 (1.4) |
| R-CARRIERE v4 : institution `assemblee_avant_2002`, mandats de député antérieurs au 19/06/2002 (ceux d'après viennent de l'archive des acteurs : jamais deux fois) ; couverture `complet`, `relu_aucun` (fiche lue, aucun mandat avant 2002), `aucun_identifiant`, ou `hors_source` (non collecté) | cahier 4.2 | 1 (1.5.1, 1.5.5) |

Mesures (13/11/2026) : relevé réel 53 s, 17 fiches (711 Ko reçus, faits seulement rangés) ;
mandats d'avant 2002 pour Retailleau (Vendée, 27/11/1994 → 21/04/1997), Dupont-Aignan (Essonne,
01/06/1997 → 18/06/2002) et Royal, retirée (Deux-Sèvres, 1988 → 1997, trois mandats) ; raccord exact
avec l'archive des acteurs (19/06/2002) ; 14 fiches lues sans mandat avant 2002 ; 27 candidats sans
fiche Sycomore déclarée.


## Nuit du 13/11 refusée par C4 : un paquet relève du schéma de sa section (13/11/2026, soir)

Branche `etape-2-schema-paquets`. Nuit du 13/11 (exécution 43502893975) : acquis écrit, publication refusée par C4 (alerte #120) : `candidats/francois-ruffin/amendements-2023-1.json.gz`, section `candidats/amendements-N-N` absente du schéma.

| Changement | Pourquoi | Documents à aligner |
| --- | --- | --- |
| C4 : un paquet (`amendements-2023-1`, numéro après une année ou un semestre) relève du schéma de sa section (`amendements-N`) quand sa forme n'est pas déclarée ; les colonnes restent vérifiées | les amendements de la XVIe, relevés pour la première fois cette nuit, font dépasser un paquet aux amendements de 2023 de François Ruffin : forme absente de toutes les données d'où le schéma avait été tiré. Vérifié sur les fichiers servis de la nuit : 0 écart avec la correction | 2 (2.8.1 C4) |
| C1 : un fichier changé à la source depuis la **dernière publication** (et non seulement dans la génération courante) explique la perte de ses faits | défaut antérieur, révélé par l'essai de cette branche (43521640358, génération 12) : la nuit (génération 11) a été écrite sans être publiée, l'essai se compare à la g10 et ne connaissait que les changements de la g12 ; 9 points de l'ordre du jour de la XVIIe, changés à la source en g11, passaient pour perdus. Une nuit normale n'est pas touchée (dernière publication = génération précédente) | 2 (2.8.1 C1) |

## Relevé dédié des amendements XVe et XVIe (14/11/2026)

Décision Q34 (« Relevé dédié, budget long »), issue #32. Mise à jour `quotidien` limitée à `an-amendements-l15` et `-l16` (budget de 7 200 s chacun), exécution 43531638337, 0 h 04 → 2 h 01 UTC.

| Point | Résultat |
| --- | --- |
| `an-amendements-l16` (363 Mo) | reçu par la nuit du 13/11 (163 789 membres, premier relevé) ; ici `304` |
| `an-amendements-l15` (649 Mo) | échec après 6 181 s : 1,03 Go transmis, transfert coupé à 30,7 Mo sur 648,5 Mo ; reprises « 206 +832 Ko », « 206 +0 » ; budget de 2 h non atteint |
| Calcul | publication autorisée, 72 fiches, 2 620 084 faits publiés, calcul 8 min 26 s, pic 5,9 Go ; génération 12 écrite et publiée (la nuit du 13/11, refusée par C4, est ainsi publiée, PR #122) |

#32 reste ouverte pour les amendements de la XVe.

Le même jour, après l'essai de la branche des octets gardés (43567645702 : amendements XVe reçus en 2 min 45 s, une reprise de 600 Mo en 123 s), relevé dédié relancé à 6 h 58 UTC (exécution 43568873116) : `an-amendements-l15` **reçu** en 315 s (648 539 281 octets, 311 934 versions nouvelles) ; publication autorisée, 72 fiches, 2 927 482 faits publiés (génération 13). #32 fermée.
