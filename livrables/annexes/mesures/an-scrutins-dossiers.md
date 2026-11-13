# Mesures — Assemblée nationale : scrutins et dossiers législatifs (XIVe → XVIIe)

Mesures faites le **04/11/2026** (téléchargements entre 14 h 50 et 14 h 55 UTC) par l'agent `an-scrutins-dossiers`.
Toutes les populations sont « dans l'archive téléchargée le 04/11/2026 » sauf mention contraire.

- **Mesuré** : compté dans les fichiers ou chronométré.
- **Calculé** : dérivé de chiffres mesurés.
- **Supposé** : non vérifié, signalé comme tel.

Chemins :

- archives : `travail/sources/an-scrutins-dossiers/` (8 zips + la liste CSV des députés en exercice ; en-têtes HTTP dans `headers/`)
- scripts : `travail/scripts/an-scrutins-dossiers/` (Python lancé avec `-I`, `.venv` du dossier `travail`)
- tables intermédiaires (parquet) : dans le dossier temporaire de la session, recréées par les scripts (`extraire_scrutins.py <zip> <sortie>`, `extraire_dossiers.py <zip> <sortie> <leg>`).

Machine : poste domestique, Python 3.12.3, orjson 3.13, duckdb 2.0, pyarrow 26. **Les durées de
téléchargement ne valent pas pour un serveur GitHub Actions** (réseau différent) ; les durées de lecture
donnent un ordre de grandeur, pas une borne.

---

## 1. Les archives : chemins, tailles, en-têtes

Les chemins viennent des pages de jeux (`/archives-anterieures/archives-14e/scrutins`, `…-15e/scrutins`,
`/archives-16e/votes`, `/travaux-parlementaires/votes`, et leurs équivalents « dossiers-legislatifs »).
Base : `https://data.assemblee-nationale.fr/static/openData/repository/`.

| Archive | Chemin exact | Content-Length (o) | Last-Modified | ETag | Décompressé | Fichiers | Durée de téléchargement (domestique) |
| --- | --- | ---: | --- | --- | ---: | ---: | --- |
| Scrutins XIV | `14/loi/scrutins/Scrutins_XIV.json.zip` | 671 420 | 21/03/2018 09:38:52 GMT | `"a3ebc-567e8f5796300"` | 10,3 Mo | 1 | 0,2 s |
| Scrutins XV | `15/loi/scrutins/Scrutins_XV.json.zip` | 9 202 661 | 09/06/2022 10:22:14 GMT | `"8c6be5-5e101320f0e00"` | 57,1 Mo | 4 417 | 19 s (2e essai, voir piège T1) |
| Scrutins XVI | `16/loi/scrutins/Scrutins.json.zip` | 10 107 912 | 28/06/2024 10:22:27 GMT | `"9a3c08-61bf09fcdb1f3"` | 68,4 Mo | 4 106 | 2,4 s |
| Scrutins XVII | `17/loi/scrutins/Scrutins.json.zip` | 29 637 633 | 03/11/2026 11:26:44 GMT | `"1c43c01-65f5d898979c6"` | 193,8 Mo | 9 578 | 7,7 s |
| Dossiers XIV | `14/loi/dossiers_legislatifs/Dossiers_Legislatifs_XIV.json.zip` | 2 570 692 | 21/03/2018 09:38:52 GMT | `"2739c4-567e8f5796300"` | 36,2 Mo | 1 | 3,7 s |
| Dossiers XV | `15/loi/dossiers_legislatifs/Dossiers_Legislatifs_XV.json.zip` | 15 220 496 | 09/06/2022 13:16:57 GMT | `"e83f10-5e103a2e29c9e"` | 50,5 Mo | 15 486 | 13,3 s |
| Dossiers XVI | `16/loi/dossiers_legislatifs/Dossiers_Legislatifs.json.zip` | 9 085 119 | 28/06/2024 10:16:19 GMT | `"8aa0bf-61bf089dced66"` | 31,4 Mo | 9 090 | 29,6 s |
| Dossiers XVII | `17/loi/dossiers_legislatifs/Dossiers_Legislatifs.json.zip` | 11 134 377 | 03/11/2026 14:16:29 GMT | `"a9e5a9-65f5fe89ecd77"` | 39,4 Mo | 10 975 | 24,8 s |

- Les noms changent bien d'une législature à l'autre (`_XIV`, `_XV`, puis sans suffixe) : confirmé.
- HEAD et GET donnent les mêmes ETag / Last-Modified / Content-Length. Serveur derrière un CDN (`x-cdn-pop: rbx`, `x-cacheable`).
  ETag et Last-Modified sont exploitables pour une requête conditionnelle (non testé : `If-None-Match`).
- Débit observé : 0,3 à 4,2 Mo/s selon le fichier ; 8 archives ≈ 118 Mo compressés, ≈ 100 s au total.
- Les archives XVII sont produites la veille (03/11/2026, 11 h 26 et 14 h 16 GMT) : la « fraîcheur » d'une collecte du 04/11 est celle du 03/11.

---

## 2. Scrutins

### 2.1 Volumes, durée, mémoire (mesuré)

| | XIV | XV | XVI | XVII |
| --- | ---: | ---: | ---: | ---: |
| Scrutins dans l'archive | 1 354 | 4 417 | 4 106 (dont 1 du Congrès) | 9 578 |
| Dates | 03/07/2012 → **24/11/2016** | 04/07/2017 → 24/02/2022 | 11/07/2022 → 07/06/2024 | 08/10/2024 → 02/11/2026 |
| Numéros | 1 → 1 354 | 1 → 4 419 (**3 781 et 3 782 absents**) | 1 → 4 105 + `VTCGR5L16V1` | 1 → 9 578 |
| Lignes groupe × scrutin | 9 406 | 40 415 | 45 175 | 114 936 |
| **Positions nominatives (personne × scrutin)** | **109 913** | **472 631** | **603 813** | **1 418 746** |
| dont « non-votant » (président de séance, membre du gouvernement, président de l'AN) | 2 982 | 7 967 | 3 991 | 25 168 |
| Personnes distinctes | 642 | 651 | 962 | 652 |
| Séances distinctes citées | 523 | 1 150 | 508 | 553 |
| Lecture en flux, comptage seul (`compter.py`) | 0,36 s / 104 Mo | — | — | 2,3 s / 22 Mo |
| Lecture + lignes gardées en mémoire (`extraire_scrutins.py --lecture`) | 0,5 s / 104 Mo | 1,9 s / 268 Mo | 2,0 s / 329 Mo | 6,4 s / 824 Mo |
| Extraction complète vers parquet | 0,7 s / 175 Mo | 2,8 s / 393 Mo | 3,1 s / 484 Mo | **8,5 s / 1 106 Mo** |

Total : 19 455 scrutins, **2 605 103 positions nominatives**, 1 991 personnes distinctes (XIV → XVII).
Aucun doublon (personne, scrutin) dans les listes (mesuré).

Mémoire : garder toutes les positions XVII en dictionnaires Python coûte ≈ 1,1 Gio ; la lecture en flux
tient en 22 Mo. **Le pipeline doit écrire au fil de l'eau** (par lots) pour rester sous ~1,5 Gio quand la
XVIIe grossira (calculé : +≈ 0,1 Gio par 1 000 scrutins en mode « tout en mémoire »). Parquet zstd des
positions des 4 législatures : 9,0 Mo (mesuré).

### 2.2 Schémas de clés des listes nominatives (mesuré, `formes.py`)

| Législature | Clés de `decompteNominatif` | Clés de `decompteVoix` (groupe) | Champs du votant |
| --- | --- | --- | --- |
| XIV | `pour`, `contre`, `abstentions`, `nonVotants` | `pour`, `contre`, **`abstention`**, **`nonVotant`** (ce dernier sur 1 821 lignes sur 9 406) | `acteurRef`, `mandatRef`, `causePositionVote` (non-votants) |
| XV | `pours`, `contres`, `abstentions`, `nonVotants` | `pour`, `contre`, `abstentions`, `nonVotants`, `nonVotantsVolontaires` | + `parDelegation` |
| XVI | idem XV ; **le scrutin du Congrès `VTCGR5L16V1` a `pour`, `contre`, `abstention`, `nonVotant`** | idem XV | + `parDelegation` |
| XVII | idem XV | idem XV | + `parDelegation`, **`numPlace`** (null sur 122 positions) |

- Il y a donc **trois jeux de clés pour les listes** (XIV ; XV-XVII ; Congrès XVI), plus des variantes
  singulier/pluriel dans les décomptes et dans les mises au point (voir 2.4). Un lecteur doit
  normaliser une table de correspondance (celle de `extraire_scrutins.py`).
- XIV : `nonVotants` vaut une **chaîne** (pas `null`) sur 7 585 lignes de groupe sans non-votant.
- Partout : un votant seul est un dictionnaire, plusieurs une liste (confirmé, ex. `VTANR5L17V2657`).
- `nonVotantsVolontaires` existe dans les décomptes mais vaut 0 sur tous les scrutins XV-XVII et
  **n'a pas de liste nominative**.
- Les non-votants nominatifs sont ceux qui ont une cause : `PAN` (président de l'AN), `PSE` (président de
  séance), `MG` (membre du gouvernement). Ce n'est **pas** la liste des absents.
- Le type « motion de censure » (`MOC`) a pour libellé `motion de censure` en XIV et XVII mais
  **`scrutin public solennel` en XV et XVI** : se fier au code, pas au libellé.

### 2.3 Cohérence nominatif ↔ décomptes ↔ totaux officiels (mesuré)

| | Lignes groupe où nominatif = décompte | Totaux du scrutin = somme des groupes | Exprimés = pour + contre ; votants = pour + contre + abst. |
| --- | --- | --- | --- |
| XIV | 4 428 / 4 428 en mode `DecompteNominatif` ; **1 427 / 4 978 en mode `DecompteDissidentsPositionGroupe`** | 1 354 / 1 354 | 1 354 / 1 354 |
| XV | 40 398 / 40 415 (17 écarts d'une voix, ex. `VTANR5L15V2887` groupe `PO774834`) | 4 404 / 4 417 | 4 417 / 4 417 |
| XVI | 45 171 / 45 175 (ex. `VTANR5L16V1948`) | 4 106 / 4 106 | 4 106 / 4 106 |
| XVII | 114 792 / 114 936 (écarts : groupes `PO0`, voir piège S3) | 9 578 / 9 578 | 9 578 / 9 578 |

Les totaux officiels (`nombreVotants`, `suffragesExprimes`, `nbrSuffragesRequis`, décompte global) sont
présents sur 100 % des scrutins des quatre archives.

### 2.4 Mises au point, délégation, position majoritaire (mesuré)

- **Mises au point** (scrutins ayant au moins une personne en `miseAuPoint`, hors bloc `dysfonctionnement`) :
  XIV 353, XV 1 226, XVI 929, **XVII 1 608** (le chiffre du cahier est confirmé). Avec le bloc
  `dysfonctionnement` (vote mal enregistré par la machine) : 353 / 1 229 / 935 / 1 710. Lignes : 1 338 / 2 625 / 1 916 / 3 535.
  - Piège : en XV-XVII, `miseAuPoint` est **présent sur tous les scrutins** (9 578 en XVII) et
    `abstentions`, `nonVotants`, `nonVotantsVolontaires` y sont des **listes de deux éléments souvent `[null, null]`** ;
    `pours`/`contres` y sont des dictionnaires ; le sous-bloc `dysfonctionnement` utilise `pour`/`contre` au singulier.
    En XIV : `pour`/`contre` et `miseAuPoint` = `null` sur 1 001 scrutins. « Bloc présent » ≠ « mise au point ».
- **Vote par délégation** (`parDelegation = "true"`) : absent en XIV ; XV 52 110 positions (11 %), XVI 51 737 (8,6 %),
  XVII 215 114 (15,2 %). Chaîne `"true"`/`"false"`, pas un booléen.
- **Position majoritaire publiée par groupe** : présente sur 100 % des lignes groupe, valeurs `pour`/`contre`/`abstention` seulement.
- **Siège** (`numPlace`) : XVII seulement.

### 2.5 Pièges confirmés, infirmés, nouveaux — scrutins

- **S1 (nouveau, important) — XIV : la moitié des scrutins n'ont que les dissidents.** 710 scrutins
  publics ordinaires du 17/07/2012 au 26/02/2014 sont en mode `DecompteDissidentsPositionGroupe` : seuls
  les membres qui ont voté autrement que leur groupe sont nommés (1 552 voix nommées sur 79 997 décomptées).
  La page publique (`/dyn/14/scrutins/100`) ne nomme pas davantage (7 députés liés). La position individuelle
  des autres membres **n'existe pas à la source** : donnée manquante, jamais déduite de la position du groupe.
- **S2 (nouveau, important) — l'archive XIV des scrutins est tronquée.** Dernier scrutin : n° 1 354 du
  24/11/2016 (archive construite le 09/03/2018). Les dossiers XIV citent `VTANR5L14V1358` (07/12/2016,
  loi de finances rectificative 2016), `…V1362` (13/12/2016, état d'urgence), `…V1364` (20/12/2016, statut de Paris),
  absents de l'archive ; `/dyn/14/scrutins/1355` répond 404. 107 décisions de séance AN des dossiers XIV sont
  postérieures au 24/11/2016. Combien de scrutins manquent : **non établi** (au moins 10).
- **S3 (nouveau) — groupe `PO0`.** 14 scrutins XVII (ex. `VTANR5L17V489`–`V500` du 02/12/2024, `VTANR5L17V1302`)
  ont 146 lignes groupe dont l'organe vaut `PO0` : l'identité du groupe est perdue, les décomptes par
  « groupe » ne correspondent plus. Le groupe d'une position doit pouvoir se reconstruire depuis le mandat à la date.
- **S4 (nouveau) — l'organe d'un groupe alterne dans les scrutins.** Groupe socialiste XVI : `PO800496`
  et `PO830170` se succèdent dans les scrutins **en va-et-vient** (`PO830170` dès le 14/12/2022, puis
  `PO800496` du 07/11/2023 au 14/03/2024, puis `PO830170`). Le cahier dit « un même groupe peut changer
  d'organe » : c'est pire, l'ordre n'est pas monotone. Ne pas dater l'appartenance d'après l'organe porté par le scrutin.
- **S5 (nouveau)** — XV : numéros 3 781 et 3 782 absents de l'archive.
- **S6** — Numérotation par législature et scrutin du Congrès dans l'archive XVI (`VTCGR5L16V1`, préfixe `VTCG`) : confirmé.
- **S7** — Référence au dossier : XVII seulement, 3 752 / 9 578 (confirmé), dans `objet.dossierLegislatif.dossierRef`.
  XIV-XVI : `objet.referenceLegislative` toujours `null`.
- **S8** — Intitulés : apostrophe typographique `’` (au moins 61 intitulés XVII commencent par `l’`), coquilles
  (`amenedement` `VTANR5L17V4988`, `sous-amendmeent` `V1633`, `aticle` `V7950`, `l'ensemble de de` `V918`), espaces parasites en XIV (`l' amendement`).
- **S9 (correction du cahier, 3.1.7)** — les scrutins XVII citent **553 séances distinctes**, pas 9 578.

---

## 3. Classification des scrutins XVIIe

### 3.1 Par type (mesuré, `typeVote.codeTypeVote`)

| Code | Libellé | XIV | XV | XVI | XVII |
| --- | --- | ---: | ---: | ---: | ---: |
| SPO | scrutin public ordinaire | 1 213 | 4 288 | 4 034 | 9 481 |
| SPS | scrutin public solennel | 128 | 124 | 37 | 74 |
| MOC | motion de censure | 4 | 5 | 34 | 23 |
| SAT | scrutin à la tribune | 9 | — | — | — |
| SSG | scrutin solennel Congrès | — | — | 1 | — |

Sort XVII : 3 178 adoptés, 6 400 rejetés.

### 3.2 Nature d'après l'intitulé (règle essayée, `classer.py`)

Règle : intitulé mis en minuscules, `’` → `'`, `sur ` initial retiré, puis, dans l'ordre :
`MOC` ou « la motion de censure » → censure ; « l'ensemble … première/deuxième/… partie » ou « la première partie … » → **partie de texte** ;
« l'ensemble » → **ensemble** ; « la proposition de loi / de résolution », « le projet de loi » en tête → **ensemble sans le mot** ;
« l'amendement / le sous-amendement / les amendements » (tolérant aux coquilles) → amendement ; « l'article / les articles » → article ;
« la motion » → motion de procédure ; « la déclaration » → déclaration ; « la demande … / la proposition du Gouvernement de prolonger » → procédure.

| Nature (XVII) | Scrutins | dont SPS | avec `dossierRef` |
| --- | ---: | ---: | ---: |
| amendement / sous-amendement | 8 263 | 0 | 3 306 |
| article | 959 | 1 | 328 |
| **ensemble** (« l'ensemble … ») | **225** | 65 | 77 |
| ensemble sans le mot (PPR art. 34-1, projet de loi d'accord, 2 PPL solennelles) | 16 | 2 | 7 |
| motion de procédure (rejet préalable, renvoi…) | 60 | 0 | 20 |
| motion de censure | 23 | (MOC) | 1 |
| procédure (suspension, seconde délibération, prolongation de séance) | 18 | 0 | 12 |
| partie de texte (1re/2e/3e partie PLF, PLFSS) | 10 | 2 | 1 |
| déclaration (art. 49-1, 50-1) | 4 | 4 | 0 |

**Part « ensemble d'un texte » en XVII : 225 / 9 578 = 2,3 % (règle stricte), 241 = 2,5 % (élargie).**
Mêmes règles : XIV 121 (+35), XV 376 (+61), XVI 221 (+23).
Aucun intitulé XVII hors règle ; XIV-XV en ont 17 et 50 (« les crédits de la mission … État B »,
`VTANR5L15V3127` ; « l'opposition à la demande de constitution de la commission spéciale », `VTANR5L15V2672` ;
`VTANR5L14V1195` engagement en Syrie).

Cas ambigus (à trancher dans la méthodologie) :

- **Partie d'un texte financier** : `VTANR5L17V445` « l'ensemble de la première partie du PLFG 2024 », `V242`
  « l'ensemble de la deuxième partie du PLFSS 2025 », `V438`/`V4241` (SPS) « la première partie du PLF ». Ce n'est pas l'ensemble du texte.
- **Sans le mot « ensemble »** : `VTANR5L17V8705` et `V8706` (SPS, « la proposition de loi apportant… ») sont des
  votes sur l'ensemble ; `V6284` « le projet de loi autorisant l'approbation… » aussi ; les 13 propositions
  de résolution art. 34-1 (`V1196`, `V3260`…) sont des votes sur l'ensemble d'un texte qui n'est pas une loi.
- **« Ensemble » d'une résolution** : 6 intitulés « l'ensemble de la proposition de résolution » (création de commission d'enquête, résolution européenne).
- **Déclarations** (49-1, 50-1, `V3054`, `V4698`) et motions de censure : ni texte ni ensemble.
- **Origine du texte** (projet / proposition) : lisible dans l'intitulé pour les « ensemble » (« du projet de loi », « de la proposition de loi »).

### 3.3 Part des scrutins XVII avec référence de dossier

3 752 / 9 578 (39,2 %), confirmé. Mais **seuls 84 des 241 scrutins « ensemble » (35 %)** en portent une :
la référence directe couvre surtout les amendements (3 306).

---

## 4. Dossiers législatifs

### 4.1 Volumes, durée, mémoire (mesuré)

| | XIV | XV | XVI | XVII |
| --- | ---: | ---: | ---: | ---: |
| Dossiers | 3 432 | 4 980 | 2 943 (dont 149 d'autres législatures) | 3 390 (dont 196 d'autres législatures : 88 XVI, 64 XV, 27 XIV, 17 avant) |
| Documents | 7 120 (**dont 102 de la XV**, 1 923 sans législature) | 10 506 | 6 147 | 7 585 (4 500 de la XVII, 2 557 sans législature) |
| Actes (arbre complet) | 35 346 | 39 225 | 23 157 | 28 562 |
| Références de scrutin dans les actes | 136 | 262 | 222 | 304 |
| Promulgations | 412 | 319 | 147 | 153 |
| Extraction complète (lecture + parquet) | 1,4 s / 258 Mo | 1,9 s / 157 Mo | 1,2 s / 124 Mo | 1,4 s / 136 Mo |

Dossiers distincts sur les quatre archives : **14 422** (cahier : 14 377 au 22/10/2026). Lois distinctes
(numéro de loi) : 1 020, dont 412 sans NOR — **toute la XIV** — (cahier : 412 sur 1 015) ; une loi apparaît dans deux archives, avec et sans NOR.

Structure : XIV = un seul fichier `export` (`textesLegislatifs.document[]` + `dossiersLegislatifs.dossier[].dossierParlementaire`) ;
XV-XVII = un JSON par objet sous `json/dossierParlementaire/` et `json/document/`. Arbre d'actes récursif
(`actesLegislatifs.acteLegislatif`, dict ou liste), 26 à 29 types `@xsi:type`.

Piège nouveau : **l'archive « XIV », construite en mars 2018, contient 102 documents de la XV** (ex. `PIONANR5L15B0759`).

### 4.2 Lien scrutin → dossier en XVIIe (mesuré, `q6.sql`, `q7.sql`, `desambig.py`)

Routes :

1. **Directe** : `objet.dossierLegislatif.dossierRef` du scrutin.
2. **Acte** : un acte de dossier cite le scrutin (`voteRefs.voteRef`), sur les codes `…-DEBATS-DEC` (décision de séance) et `…-MOTION-VOTE` (motion de censure).
3. **Séance** : `seanceRef` du scrutin = `reunionRef` d'un acte `DiscussionSeancePublique` ou `Decision` (`RUANR5L17S2025IDS29580`).
   Univoque si la séance ne mène qu'à un dossier ; sinon départage si **un seul** titre de dossier candidat est contenu dans l'intitulé du scrutin.

| XVII, 9 578 scrutins | Scrutins |
| --- | ---: |
| Route 1 (directe) | 3 752 |
| Route 2 (acte qui cite le scrutin) | 262 (291 références distinctes vers des scrutins connus ; 2 vers des scrutins **du Sénat** `VTSNR5L17…`, 29 vers XV-XVI) |
| Route 1 ou 2 | 3 924 (41 %) |
| **Sans dossier par les routes 1 et 2** | **5 654** |
| Route 3 : séance retrouvée dans les actes | 9 509 (546 des 553 séances) |
| Route 3 univoque, ajout aux routes 1-2 | + 4 021 |
| Route 3 ambiguë (2 à 6 dossiers dans la séance), départagée par le titre | + 1 163 |
| Ambigus restants | 401 |
| Aucune séance correspondante | 69 (PLF/PLFSS en nouvelle lecture, ex. `VTANR5L17V5038`, `V3482`) |
| **Total relié** | **9 108 (95,1 %)** (9 107 dans `poids.py`, qui ne garde qu'un dossier par référence d'acte) |

Fiabilité de la route 3, mesurée contre la route 1 : univoque conforme 2 761 / 2 762 ; départage par titre
conforme 587 / 588. Routes 1 et 2 concordent 89 / 90 (écart : `VTANR5L17V8707`, `DLR5L17N54629` contre `DLR5L17N54951`).

Pour les seuls scrutins « ensemble » : routes 1-2 = 201 / 225, routes 1-2-3 univoque = 209, toutes routes = 225 / 225.

Même méthode XIV-XVI (sans route 1) : XIV 1 091 / 1 354 reliés, XV 3 888 / 4 417, XVI 3 605 / 4 105.

Scrutins cités par au moins un acte, par législature : XIV 124, XV 261, XVI 206, XVII 262.

### 4.3 Commission saisie au fond, 49.3, promulgation (XVII, mesuré)

- **Commission au fond** : acte `@xsi:type = SaisieComFond_Type`, code `{étape}-COM-FOND-SAISIE`
  (`AN1-`, `ANLUNI-`, `AN2-`, `ANNLEC-`, `ANLDEF-` à l'Assemblée ; `SN1-`, `SN2-`, `SNNLEC-` au Sénat), organe dans `organeRef`.
  **2 293 dossiers sur 3 390** ont une saisine au fond à l'Assemblée ; 521 de plus n'en ont qu'une au Sénat.
  Jamais deux commissions AN au fond différentes dans un même dossier. 13 organes : 8 commissions permanentes
  (`PO59051` 799 dossiers, `PO420120` 480, `PO419610` 321…) et 5 commissions spéciales.
  Par procédure (dossiers de la XVII) : PPL ordinaires 1 712 / 2 153, projets de loi 40 / 73, résolutions 195 / 257,
  résolutions art. 34-1 0 / 212, rapports d'information 0 / 226.
- **49.3** : acte `DeclarationGouvernement_Type` dont `typeDeclaration.fam_code = "Art.49.3"`
  (« Déclaration engageant la responsabilité du Gouvernement… »), codes `AN21-DGVT`, `ANNLEC-DGVT`, `CMP-DGVT`, `ANLDEF-DGVT`.
  Engagements : XIV 12 (8 dossiers), XV 2 (2), XVI 46 (29), **XVII 16 (11)**. Aucun `voteRefs` sur ces actes (confirmé).
  Seules 5 décisions XVII le disent dans la conclusion (« considéré comme adopté … article 49, alinéa 3 », `TSORTF06`) :
  la conclusion ne suffit pas à repérer le 49.3. La motion de censure qui suit est un acte `DecisionMotionCensure_Type` avec `voteRefs` (32 actes XVII).
- **Promulgation** : acte `Promulgation_Type`, champ `codeLoi` (numéro de loi, ex. `2026-1015`), `titreLoi`,
  `infoJO.referenceNOR` (ex. `MOMO2613546L`), `dateJO`, `numJO`, `urlLegifrance` ; `texteLoiRef` sur 119 / 153.
  XVII : 153 promulgations, 153 numéros de loi, **153 NOR** ; XV, XVI : NOR partout ; XIV : 0 NOR.

---

## 5. Ordres de grandeur pour le site

- **François Ruffin** : `PA722142` (trouvé dans `17/amo/deputes_actifs_csv_opendata/liste_deputes_libre_office.csv`,
  identifiant **sans** `PA`, groupe EcoS ; même identifiant dans les listes nominatives).
  - Positions nominatives : **XV 705** (groupe `PO730958`), **XVI 444** (`PO800490`), **XVII 580** (`PO845439`) ; total 1 729, dont 1 au Congrès 2024.
    Par délégation : 43 / 24 / 57.
  - Scrutins « ensemble d'un texte » où il a voté : **XV 145, XVI 60 (+ 1 au Congrès), XVII 77 = 282** (règle élargie ; 132 / 56 / 71 en règle stricte, Congrès compris en XVI).
- **Le plus de positions nominatives en XVII** : brut, `PA721908` (Yaël Braun-Pivet) avec **9 578, une par scrutin**,
  la présidente de l'Assemblée, inscrite comme non-votante (« PAN » ou « PSE ») : sur les quatre législatures, 9 834 de ses 10 976 positions sont des non-votes. Hors non-votants : **`PA795900`
  (Marine Hamelet, RN) 7 224**, puis `PA841563` 7 055, `PA794954` 6 887. Médiane XVII : 2 051 votes par député.
- **XIV → XVII** : brut `PA721908` 10 976 ; hors non-votants `PA795900` **9 593** (2 législatures), `PA794954` 9 128, `PA722366` (Jean-Luc Fugit, 3 législatures) 8 403.
- Organe du groupe SOC XVII dans les scrutins : `PO845419` (celui de Boris Vallaud, `PA719930`).

## 6. Poids d'une fiche (mesuré, `poids.py`)

Lien au dossier : route 1 > 2 > 3 univoque > 3 + titre.

| Contenu | Lignes | JSON compact brut | gzip -9 | zstd -3 | zstd -19 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Ruffin, toutes positions XV-XVII, objets `{scrutin, date, position, position_groupe, dossier}` | 1 728 (1 580 avec dossier) | 205 198 o | **8 973 o** | 11 238 o | 6 891 o |
| idem, colonnes + identifiants courts + positions codées 0-3 | 1 728 | 64 244 o | 7 451 o | 7 527 o | 4 922 o |
| Ruffin, seulement « ensemble d'un texte » (objets) | 282 | 34 062 o | **2 916 o** | 3 366 o | 2 228 o |
| Groupe SOC XVII, par scrutin `{scrutin, date, pour, contre, abstention, non_votants, membres, position_majoritaire, dossier}` | 9 566 | 1 629 723 o | **53 068 o** | 69 156 o | 42 933 o |
| idem, colonnes + identifiants courts | 9 566 | 452 233 o | 42 886 o | 28 324 o | 21 389 o |

Lecture : une fiche personne pèse moins de 10 Ko compressés pour ses votes, même pour un député très actif
(calculé : 7 224 positions ≈ 4 × Ruffin ≈ 35 Ko gzip en objets). Une fiche groupe d'une législature longue pèse ≈ 50 Ko
gzip pour la seule liste par scrutin ; les intitulés de scrutins (non comptés ici) pèseront plus que les décomptes.
12 scrutins XVII manquent à SOC : ceux où les groupes sont `PO0`.

---

## 7. Récapitulatif des pièges du cahier

| Piège du cahier | Verdict |
| --- | --- |
| Nom du fichier varie selon la législature | confirmé |
| XIV en un seul fichier, autres clés | confirmé (+ XIV dossiers aussi en un seul fichier `export`) |
| Dict seul / liste | confirmé partout (votants, groupes, actes, mises au point) |
| Transferts coupés | **confirmé** : premier GET de `Scrutins_XV.json.zip` arrêté à 1 331 326 o sur 9 202 661 annoncés, code 200, zip illisible ; 2e essai complet. Contrôler taille = Content-Length puis `unzip -t`. |
| Trois schémas de clés nominatives | confirmé, avec précision : XIV / XV-XVII / Congrès XVI, plus variantes dans `decompteVoix` et `miseAuPoint` |
| Référence de dossier : XVII seulement, 3 752 / 9 578 | confirmé |
| Type ordinaire couvre tout, nature dans l'intitulé | confirmé |
| 1 608 scrutins XVII avec mise au point | confirmé (1 710 avec les dysfonctionnements) |
| 49.3 sans scrutin associé | confirmé |
| Acte qui cite un scrutin du Sénat | confirmé (2 références XVII, 1 XVI) |
| NOR manquant sur 412 textes, toute la XIV | confirmé (412 sur 1 020 lois distinctes au 04/11/2026) |
| « 9 578 séances citées par les scrutins » (3.1.7) | **infirmé** : 553 séances distinctes |
| Nouveaux | S1 XIV dissidents seuls ; S2 XIV tronquée au 24/11/2016 ; S3 groupes `PO0` ; S4 organe de groupe en va-et-vient ; S5 trous de numérotation XV ; documents XV dans l'archive XIV ; libellé MOC variable ; `miseAuPoint` toujours présent ; `nonVotants` chaîne en XIV ; référence directe rare sur les votes « ensemble » |
