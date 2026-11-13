# Mesures — Assemblée nationale : acteurs, organes, mandats (AMO), agenda, questions

Auteur : agent `an-acteurs`. Mesures faites le **04/11/2026 entre 14:53 et 15:10 UTC**, depuis une
connexion domestique (4 cœurs, 7,8 Gio). Les durées de téléchargement **ne valent pas** pour un
serveur GitHub Actions ; les durées de lecture donnent un ordre de grandeur (machine locale).

Légende : **[M]** mesuré, **[C]** calculé à partir de mesures, **[S]** supposé / interprétation.

Scripts : `travail/scripts/an-acteurs/` — `heads.sh` (HEAD espacés), `dl.sh` (téléchargement +
contrôle zip + reprise), `schema_amo.py` (inventaire des chemins de clés et des nœuds « dict ou
liste », marche sur n'importe quelle archive zip de JSON), `explore_amo.py`, `explore_amo2.py`,
`explore_amo3.py` (structure et comptes AMO30), `lire_amo.py` (lecture complète minimale, temps et
mémoire), `compare_fige.py` (archive figée ↔ archive courante), `agenda.py`,
`agenda_sans_presence.py`, `frise.py`. Tous se lancent avec `travail/.venv/bin/python -I <script> <archive>`.
Données : `travail/sources/an-amo/`, `travail/sources/an-agenda/`, `travail/sources/an-questions/`.

---

## 1. AMO30 XVIIe (archive courante)

`https://data.assemblee-nationale.fr/static/openData/repository/17/amo/tous_acteurs_mandats_organes_xi_legislature/AMO30_tous_acteurs_tous_mandats_tous_organes_historique.json.zip`

### 1.1 En-têtes HTTP [M]

Trois HEAD espacés de 2 min 30 (14:53:16, 14:55:47, 14:58:18 UTC), chacun doublé d'un HEAD avec un
paramètre anti-cache (`?nc=…`) pour atteindre l'origine derrière le CDN (OVH, `x-cdn-pop: rbx`) :

| Requête | `be` (serveur d'origine) | Content-Length | Last-Modified | ETag | Accept-Ranges | Cache CDN |
| --- | --- | --- | --- | --- | --- | --- |
| HEAD 1 | b2 | 13 721 016 | Tue, 03 Nov 2026 01:34:28 GMT | `"d15db8-65f55436da006"` | bytes | Matched cache |
| HEAD 1 anti-cache | f2 | idem | idem | idem | bytes | force cache |
| HEAD 2 | f1 | idem | idem | idem | bytes | Matched cache |
| HEAD 2 anti-cache | b2 | idem | idem | idem | bytes | force cache |
| HEAD 3 | f1 | idem | idem | idem | bytes | Matched cache |
| HEAD 3 anti-cache | f1 | idem | idem | idem | bytes | force cache |

- **Trois** serveurs d'origine distincts vus (`be: b2`, `f1`, `f2`), pas deux. Ce jour-là, à cette
  heure-là, **tous servaient la même version** (même ETag, même taille, même date) : le piège
  « deux versions » n'est pas reproduit en milieu de journée. [S] Il se produit vraisemblablement
  pendant la fenêtre de republication nocturne (≈ 01:00–03:00 UTC d'après les Last-Modified), quand
  un serveur a la nouvelle version et pas l'autre.
- L'ETag est de forme Apache `"<taille hex>-<mtime µs hex>"` : `0xd15db8` = 13 721 016 octets,
  `0x65f55436da006` µs = 03/11/2026 01:34:28 UTC. [M] Deux versions différentes ont donc
  forcément des ETag différents : comparer l'ETag de chaque segment détecte le mélange.
- `cache-control: max-age=14400` (4 h) côté CDN.
- Requêtes conditionnelles : `If-None-Match` → **304** ; `If-Modified-Since` → **304** ; `Range` →
  **206** avec `content-range` correct. [M] (un essai chacun, sur `f1`/`f2`). Une collecte quotidienne
  peut donc sauter un fichier inchangé pour le prix d'un HEAD.
- `http://` redirige en 301 vers `https://`.

### 1.2 Téléchargement [M]

| Essai (UTC) | Serveur | Octets reçus | Durée | Résultat |
| --- | --- | --- | --- | --- |
| 14:53:20 | b2 | **10 485 760** (= 10 Mio pile) | 19,1 s | **tronqué**, statut HTTP 200, zip illisible (« End-of-central-directory signature not found ») |
| 14:53:44 | f1 | 13 721 016 | 31,1 s | OK |
| 14:54:15 | f1 | 13 721 016 | 21,7 s | OK |

- **Piège confirmé et précisé** : une coupure franche même sur une archive de 13,7 Mo, à
  exactement 10 Mio, avec un statut 200. Le fichier tronqué est un préfixe exact du fichier complet
  (SHA-256 du préfixe identique). Contrôle indispensable : taille reçue = Content-Length **et**
  `unzip -t`. (Code de sortie de curl non capturé sur cet essai ; `dl.sh` le capture désormais.)
- Débit domestique : 0,45 à 0,7 Mo/s sur ce fichier, 1 à 4,4 Mo/s sur les autres fichiers du même
  hôte quelques minutes plus tard.

### 1.3 Contenu [M]

Archive du 03/11/2026 01:34 UTC : 13 721 016 o compressés, **95 864 315 o décompressés**,
14 053 fichiers JSON : **3 175 acteurs, 10 819 organes, 59 déports** (confirme le cahier).

**173 869 mandats** au total. Par `typeOrgane` :

| Type | Mandats | Type | Mandats | Type | Mandats |
| --- | --- | --- | --- | --- | --- |
| GA (amitié) | 39 830 | CNPE | 3 672 | MISINFOPRE | 1 622 |
| GE (études) | 37 726 | PARPOL | 3 670 | DELEGSENAT | 1 466 |
| COMPER | 26 141 | COMSENAT | 3 122 | COMSPSENAT | 1 414 |
| CMP | 17 350 | CNPS | 2 762 | **MINISTERE** | **1 174** |
| **GP** | **7 774** | API | 2 709 | DELEG | 1 160 |
| ORGEXTPARL | 3 996 | COMNL | 1 944 | MISINFOCOM | 708 |
| **ASSEMBLEE** | **3 960** | GEVI | 1 913 | OFFPAR | 701 |
| MISINFO | 3 675 | SENAT | 1 910 | **GOUVERNEMENT** | **659** |
| | | GROUPESENAT | 1 649 | DELEGBUREAU 522, BUREAU 315, CONFPT 178, CJR 107, HCJ 31, CONSTITU 6, PRESREP 3 | |

Organes par `codeType` : CIRCONSCRIPTION 6 555, GA 937, MINISTERE 758, GE 637, CMP 557,
MISINFO 483, ORGEXTPARL 334, CNPE 88, **GP 63**, PARPOL 58, DELEGBUREAU 48, GEVI 47, MISINFOCOM 45,
MISINFOPRE 40, CNPS 32, COMSPSENAT 24, **GOUVERNEMENT 17**, BUREAU 11, GROUPESENAT 11, DELEGSENAT 10,
COMPER 10, API 9, OFFPAR 9, COMSENAT 8, DELEG 7, ASSEMBLEE 6, COMNL 4, CONFPT 4, PRESREP 3,
CONSTITU / SENAT / CJR / HCJ 1. **Aucun organe de type commission d'enquête** (voir 4).

Déports : 59 (XVIe 41, XVIIe 9, XVe 9) ; cible textuelle (`cible.referenceTextuelle`), portée,
instance ; `explication` en HTML échappé.

Quatre `@xsi:type` de mandat : MandatSimple 158 341, MandatMission 6 413 (dont les missions auprès
d'un ministère), MandatParlementaire 6 363 (ASSEMBLEE, SENAT, BUREAU, CONFPT : seuls à porter
`election` et `mandature`), MandatAvecSuppleant 2 752.

### 1.4 Temps de lecture et mémoire [M]

| Lecture | Durée (mur) | Mémoire de pointe (RSS) |
| --- | --- | --- |
| Zip → tous les objets en dictionnaires Python, `orjson` (`lire_amo.py`) | 2,4 s | 407 Mo |
| Idem avec `json` de la bibliothèque standard | 3,0 s | 390 Mo |
| Exploration complète (dictionnaires + index, `explore_amo.py`) | 3,4 s | 406 Mo |
| Parcours en flux, objet par objet, sans rien garder (`schema_amo.py`) | 4,8 s | 28 Mo |

`/usr/bin/time -v`, lecture directe dans le zip (pas de décompression sur disque).

---

## 2. Structure utile au modèle

### 2.1 Position déclarée des groupes

- Champ : `organe.positionPolitique` (organes `GP` seulement), valeurs `Majoritaire`,
  `Minoritaire`, `Opposition` ou `null`. **Aucune date** : la position vaut pour toute la vie de
  l'organe (`viMoDe.dateDebut` → `viMoDe.dateFin`). Un changement de position passe donc par un
  changement d'organe [S].
- Groupes (organes GP) par législature dans l'archive courante du 03/11/2026 [M] :

| Législature | Organes GP | dont NI | Position déclarée | Détail |
| --- | --- | --- | --- | --- |
| XIIe | 5 | — | 0 | |
| XIIIe | 5 | 1 | 4 | |
| XIVe | 10 | 1 | 9 | 2 Majoritaire (SRC, SER), 3 Minoritaire, 4 Opposition |
| XVe | 17 | 1 | 16 | 1 Majoritaire (LAREM), 5 Minoritaire, 10 Opposition |
| XVIe | 12 | 1 | 11 | 1 Majoritaire (RE), 2 Minoritaire, 8 Opposition |
| **XVIIe** | **14** | 1 | **0** | **aucune position déclarée** sur les 14 organes (y compris UDR et UDDPLR) |

- **Nouveau piège (majeur)** : en XVIIe, `positionPolitique` est `null` pour **tous** les groupes,
  dans AMO30 comme dans AMO10 (députés actifs, archive du 03/11/2026 : 12 GP, tous `null`). La
  règle « période = banc déclaré du groupe » (4.6) n'a aucune donnée source en XVIIe.
- Les positions XVe et XVIe sont **identiques** dans les archives figées et dans la courante
  (mesuré sur les 17 + 12 organes) ; les libellés des GP aussi.
- Le NI est un organe GP par législature (`libelleAbrev` = `NI`), sans position. Qualités des
  mandats GP : Membre 4 651, Député non-inscrit 2 772, Membre apparenté 265, Président 86.
- Exemples : `PO800538` RE (XVIe, Majoritaire), `PO845407` EPR (XVIIe, null).

### 2.2 Gouvernements et ministres

- 17 organes `GOUVERNEMENT` (Fillon 1 `PO382939`, 17/05/2007 → Lecornu II `PO873634`, depuis le
  11/10/2025), avec dates. **Les ministères n'existent qu'une fois par gouvernement** : 758 organes
  `MINISTERE`, tous rattachés par `organeParent` à leur gouvernement (757 ; 1 sans parent).
- **Deux mandats par ministre** :
  - un mandat `GOUVERNEMENT` (659), qualité toujours `membre`, sur la durée de présence dans
    ce gouvernement ;
  - un mandat `MINISTERE` (766 hors missions) qui porte le **portefeuille** et la **qualité** :
    Ministre 343, Secrétaire d'État 218, Ministre délégué 146, Ministre d'État 22, Premier
    ministre 17, Garde des sceaux 16, Haut-commissaire 4. Un changement de portefeuille dans le
    même gouvernement = un nouveau mandat MINISTERE sous le même mandat GOUVERNEMENT (ex. Benoist
    Apparu `PA333224`, Fillon 3 : `PM425797` Secrétaire d'État puis `PM514480` Ministre, un seul
    `PM15425797` GOUVERNEMENT).
  - Appariement : l'uid du mandat GOUVERNEMENT est `PM15` + le numéro du mandat MINISTERE
    (`PM15425797` ↔ `PM425797`) pour 652 des 659 ; le gouvernement du premier est toujours le
    parent du ministère du second (652/652). [M] La convention n'est documentée nulle part [S].
  - Ces mandats n'ont **pas de législature** (`legislature: null`, 766 MINISTERE + 659
    GOUVERNEMENT).
- **Piège nouveau** : `typeOrgane = MINISTERE` ne veut pas dire ministre. **408 mandats MINISTERE
  sont des missions** (`codeQualite = "en mission"`, `MandatMission_Type`) confiées à un
  parlementaire auprès d'un ministère (407 sur 408 ont un mandat de député) ; 181 d'entre eux
  citent **deux organes** (`organeRef` en liste). Ex. `PM763154`.
- **Piège nouveau** : 7 mandats GOUVERNEMENT orphelins (sans mandat MINISTERE apparié), tous dans
  le gouvernement Bayrou, **ouverts** (`dateFin: null`) alors que le gouvernement est clos le
  09/09/2025 et que la même personne a un second mandat Bayrou correctement clos. Ex. François
  Bayrou `PA410` : `PM15855580` (14/12/2024 → 09/09/2025) et `PM15855113` (14/12/2024 → null).
  Même famille d'anomalie vue en XVe : `PM15711289` (Valls 2, ouvert) présent dans les archives
  figées, retiré depuis. Contrôle à prévoir : un mandat GOUVERNEMENT ouvert dans un gouvernement clos.
- **Ministre délégué → ministère de tutelle : aucun champ.** Les organes MINISTERE n'ont que
  `organeParent` (le gouvernement) et `organePrecedentRef`. Le rattachement ne se lit que dans le
  **libellé** de l'organe : 322 des 758 libellés contiennent « auprès » (« Ministère délégué auprès
  du ministre de l'économie, des finances et de la souveraineté industrielle et numérique, chargé de
  l'intelligence artificielle et du numérique », `PO855104`). Il faut donc apparier un texte libre
  au ministère du même gouvernement (coquilles réelles : « Secrétariat d'État **après** de la
  ministre… » `PO762315`, « professions **libééérales** » `PO425712`). `preseance` de l'organe
  MINISTERE : null pour 543 sur 758.
- **Succession des ministères** : `organe.organePrecedentRef`, renseigné sur **149** organes, tous
  de type MINISTERE (confirme le cahier) et **seulement depuis Borne** : Borne 20, Attal 35,
  Barnier 1, Bayrou 35, Lecornu 19, Lecornu II 39. **Aucune succession avant mai 2022.** Ex.
  `PO834722` (Attal) ← `PO791615` (Borne), « transformation et fonction publiques ». Le lien relie
  aussi des organes du même gouvernement (`PO801856` ← `PO791637`, Borne : secrétariat devenu
  ministère).
- Membres de gouvernement par gouvernement (personnes distinctes) : Fillon 1 21, Fillon 2 52,
  Fillon 3 39, Ayrault 1 35, Ayrault 2 40, Valls 33, Valls 2 50, Cazeneuve 38, Philippe 23,
  Philippe 2 50, Castex 43, Borne 55, Attal 35, Barnier 42, Bayrou 36, Lecornu 19, Lecornu II 39
  (35 mandats encore ouverts). [M]

### 2.3 Suspension du mandat de député

Pas de champ « suspension ». Elle se lit dans une chaîne de **mandats ASSEMBLEE** [M] :

1. mandat d'origine clos avec `mandature.causeFin = "Nomination comme membre du Gouvernement"`
   (220 cas), **environ un mois après** l'entrée au gouvernement (écart mesuré sur 220 cas :
   30 j 108 fois, 29 j 65 fois, 28 j 12, 31 j 9, 62 j 9…) ;
2. mandat du suppléant : `election.causeMandat = "remplacement d'un député nommé au Gouvernement"`
   (248), clos par `"Reprise de l'exercice du mandat d'un ancien membre du Gouvernement"` (127) ;
   son `mandatRemplaceRef` n'est renseigné que 8 fois sur 248 ;
3. mandat de reprise : `causeMandat = "reprise de l'exercice du mandat d'un ancien membre du
   Gouvernement"` (113), `mandature.mandatRemplaceRef` = **le mandat suspendu de la même
   personne** (113/113, jamais celui du suppléant).

**Piège nouveau** : sur les 113 mandats de reprise, `dateDebut` = la date de début **du mandat
d'origine** (113/113) ; la vraie date de reprise est `mandature.datePriseFonction` (postérieure dans
113/113). Ex. Benoist Apparu : `PM386013` 20/06/2007 → 23/07/2009 (nomination), `PM642582`
« 20/06/2007 » → 19/06/2012 avec `datePriseFonction` 17/06/2012. Un calcul d'appartenance par
`dateDebut`/`dateFin` superpose les deux mandats et efface la suspension.

Causes de fin (ASSEMBLEE) : Fin de législature 2 825, null 574 (mandats en cours et anciens),
Nomination au Gouvernement 220, Reprise 127, Démission pour incompatibilité 60, Démission 51,
Annulation 29, Décès 25, Élection au Sénat 25, Prolongation de mission 13, Démission d'office 6,
Élection au PE 2, Déchéance 1, Élection à la présidence de la République 1, Démission avant
entrée en fonction 1. Aucun champ ne dit « dissolution » (confirmé).

### 2.4 Siège dans l'hémicycle

- Champ : `mandat.mandature.placeHemicycle` (chaîne, zéros en tête : `"077"`), **uniquement**
  sur les mandats `ASSEMBLEE`, sans date. [M]
- Archive courante : les 574 députés en cours ont un siège. Les mandats clos n'ont un siège que si
  la personne **siège encore** : XIVe 49 mandats avec siège sur 691 (47 = siège actuel XVIIe),
  XVe 175/688 (162 = siège actuel), XVIe 397/633 (371 = siège actuel), XVIIe clos 22/109 (22 =
  siège actuel). Sur les écarts (2, 13, 26), 1, 4 et 9 mandats portent un siège alors que la
  personne ne siège plus aujourd'hui [M] ; le reste [S] tient à des personnes dont le mandat en
  cours porte un autre numéro.
- Archive figée XVIe (28/06/2024) : 591 mandats sur 633 ont un siège ; **dans la courante, 66 ont
  le même, 323 un autre, 202 aucun.** Archive figée XVe (09/06/2022) : 579 sièges, 1 seul identique
  dans la courante. **Piège confirmé** : seul le figé donne le siège d'une législature close.
  Ex. François Ruffin `PA722142` : siège 627 (figée XVe), 637 (figée XVIe), **505 sur ses trois
  mandats** dans la courante.

### 2.5 Nœuds « un objet seul = dictionnaire, plusieurs = liste » rencontrés [M]

| Archive | Chemin | Dict / chaîne | Liste |
| --- | --- | --- | --- |
| AMO30 | `acteur.adresses.adresse` | 917 | 2 163 |
| AMO30 | `acteur.mandats.mandat` | 5 acteurs | 3 170 |
| AMO30 | `mandat.organes.organeRef` | 173 683 (chaîne) | 181 (missions MINISTERE) |
| AMO30 | `mandat.collaborateurs` / `.collaborateur` | 573 / 3 | 1 (liste de `null`) / 570 |
| AMO30 | `organe.listePays.paysRef` | 403 (chaîne) | 10 |
| AMO30 | `mandat.suppleants.suppleant` | 3 585 | 0 (toujours un seul ici) |
| Agenda XVIIe | `ODJ.pointsODJ.pointODJ` | 1 320 | 1 196 |
| Agenda XVIIe | `pointODJ.dossiersLegislatifsRefs.dossierRef` | 2 959 | 87 |
| Agenda XVIIe | `ODJ.convocationODJ.item`, `ODJ.resumeODJ.item` | 5 837 ; 4 886 | 1 224 ; 1 503 |
| Agenda XVIIe | `infosReunionsInternationale.listePays.paysRef` | 422 | 51 |
| Agenda XVIIe | `participants.personnesAuditionnees.personneAuditionnee` | 59 (null) | 153 |
| Questions écrites | `minAttribs.minAttrib` | 9 469 | 10 046 |
| Questions écrites | `renouvellements.renouvellement` | 1 532 | 642 |
| Questions écrites | `textesQuestion.texteQuestion`, `textesReponse.texteReponse` | 19 512 ; 12 416 | 3 ; 5 |
| QOSD | `minAttribs.minAttrib` | 776 | 52 |

Autre forme piège (AMO30) : **le « vide » s'écrit de trois façons** — `null`, chaîne vide, ou
objet `{"@xsi:nil": "true"}` (ce dernier pour `dateDeces` 2 895, `trigramme` 2 601, `uri_hatvp`
2 602, `dateNais` 33, `villeNais` 940, `depNais` 1 097, `paysNais` 1 319, `profession.libelleCourant`
1 013, `catSocPro`/`famSocPro` 992). L'uid d'un acteur est un objet (`uid.#text`), celui d'un organe
une chaîne.

---

## 3. Ordres de grandeur (archive courante du 03/11/2026)

| Grandeur | Valeur | Nature |
| --- | --- | --- |
| Personnes ayant au moins un mandat ASSEMBLEE actif un jour depuis le 20/06/2012 | **1 686** (= personnes avec un mandat ASSEMBLEE des législatures XIV–XVII) | [M] |
| Personnes membres d'au moins un gouvernement depuis le 17/05/2007 | **311** (659 mandats GOUVERNEMENT, 766 mandats ministériels) | [M] |
| dont jamais député (aucun mandat ASSEMBLEE, depuis 2002) | 124 | [M] |
| Population « députés depuis 2012 ∪ gouvernement » | 1 829 personnes, 136 234 mandats | [M] |
| Mandats par acteur (3 175 acteurs) | moyenne 54,8 ; médiane 35 ; max 814 (Marc Le Fur `PA1874`) | [M] |
| Mandats par personne de la population suivie (1 829) | moyenne 74,5 ; max 814 ; sans GA/GE/GEVI : moyenne 39,1 | [M] |
| Top 5 | Le Fur 814, Lionnel Luca `PA2011` 632, Michel Voisin `PA2936` 517, Rudy Salles `PA2667` 516, Patrice Martin-Lalande `PA2099` 507 | [M] |

**François Ruffin : `PA722142`**, **141 mandats** : COMPER 105, GP 6, COMNL 5, PARPOL 4, MISINFO 4,
GA 4, MISINFOCOM 3, CNPE 3, ASSEMBLEE 3 (`PM723484` XVe, `PM797673` XVIe, `PM843500` XVIIe),
ORGEXTPARL 2, CNPS 1, GE 1. GP : NI → FI (XVe), NI → LFI-NUPES (XVIe), NI → ECOS (XVIIe).
Les 105 mandats de commission permanente viennent de **permutations** : allers-retours de
quelques jours entre commissions (ex. `PM747549` 10/01/2018 → 11/01/2018), avec doublons
Membre/Secrétaire et `nominPrincipale = 0` sur 15 d'entre eux.

---

## 4. Agenda XVIIe

`…/17/vp/reunions/Agenda.json.zip` — **8 623 160 o** compressés, 25 867 969 o décompressés,
8 226 fichiers (un par réunion). Last-Modified **04/11/2026 11:41 GMT** : republié en journée, pas
seulement la nuit [M]. Téléchargement 7,3 s.

| Mesure | Valeur [M] |
| --- | --- |
| Réunions | **8 226** : 6 878 réunions de commission, 1 155 séances (`seance_type`), 193 réunions d'initiative parlementaire (groupes d'études) |
| Séances publiques de l'Assemblée (organe `PO838901`) | 997, dont **699 confirmées** et 298 « Supprimé » |
| Séances du **Sénat** (organe `PO78718`) dans l'archive | 158 (157 confirmées) |
| États des réunions de commission | Confirmé 5 880, Annulé 956, Éventuel 38, Supprimé 4 |
| Réunions avec `compteRenduRef` | 3 108 commissions, 819 séances |
| Points d'ordre du jour | **6 377** (séances AN 3 587, séances Sénat 428, commissions permanentes 2 056, autres 306) |
| Points citant ≥ 1 dossier | **3 046 (47,8 %)** ; séances AN 1 001 / 3 587 (**27,9 %**) ; commissions permanentes 1 514 / 2 056 ; ≥ 2 dossiers : 87 |
| Points de séance par type (cités/avec dossier) | Suite de la discussion 2 182/591, Discussion 1 391/687, QAG 165/0, Débat d'initiative parlementaire 108/0, Vote solennel 91/45, QOSD 28/0 |
| Réunions dont l'organe réuni est **absent d'AMO30** (et d'AMO10) | **984 réunions, 68 organes** (ex. `PO847238`, `PO850654`, `PO875682`) — [S] commissions d'enquête ou d'évaluation, aucun organe de ce type dans AMO |

Lecture [M] : zip → dictionnaires (orjson) 1,1 s, **129 Mo** ; idem en écartant la présence
(`ijson`, clé `participants` ignorée) 1,3 s, **83 Mo** ; comptes complets avec organes AMO30 1,4 s,
57 Mo (sans rétention).

**Présence nominative séparable : oui.** Elle est entièrement dans la clé de premier niveau
`reunion.participants.participantsInternes.participantInterne[]` (`acteurRef`, `presence`) :
**190 885 entrées** (absent 99 471, présent 73 125, excusé 18 289) sur 3 563 réunions ; ce
sous-objet pèse **36 %** des octets JSON (9,2 Mo sur 25,9). Aucun autre chemin de l'agenda ne
porte d'`acteurRef`. Le même sous-objet `participants` contient `personnesAuditionnees` (non
nominatives ici : `null`).

---

## 5. Questions XVIIe

| Archive | Zip | Décompressé | Questions | Dates (JO) | Clôture |
| --- | --- | --- | --- | --- | --- |
| `…/17/questions/questions_ecrites/Questions_ecrites.json.zip` | 51 051 631 o | 137 681 549 o | **19 515** | 01/10/2024 → 03/11/2026 | réponse publiée 12 527, sans clôture 6 384, fin de mandat 510, autres 94 |
| `…/17/questions/questions_gouvernement/Questions_gouvernement.json.zip` | 5 620 768 o | 14 443 937 o | **1 857** | 03/10/2024 → 15/10/2026 | réponse publiée 1 857 |
| `…/17/questions/questions_orales_sans_debat/Questions_orales_sans_debat.json.zip` | 3 265 325 o | 9 306 841 o | **828** | 19/11/2024 → 23/06/2026 | réponse publiée 815, autres 13 |

Le cahier annonçait 45 / 5,2 / 3,1 Mo : l'écart vient de la croissance ou d'une unité en Mio
(51 051 631 o = 48,7 Mio) [S].

**Question au gouvernement : aucune référence de séance (confirmé).** Champs : auteur
(`acteurRef`, `mandatRef`, groupe), ministère interrogé (`minInt.organeRef`) et attributaire,
rubrique, analyse, et seulement `infoJO` (`dateJO`, `pageJO` renseignée 1 042/1 857, `typeJO =
JO_DEBAT`). Aucune chaîne `RUANR5L17…` ni `CRSANR5L17…` dans les trois archives (recherche brute
sur tout le JSON). En QG, `textesQuestion` est **toujours null** : question et réponse sont dans
un seul HTML `textesReponse.texteReponse.texte`.

Lecture [M] : questions écrites 2,7 s, 284 Mo ; QG 0,3 s, 47 Mo (zip → dictionnaires, orjson).

---

## 6. Archives des législatures closes

| Législature | Archive | Chemin (sous `…/repository/`) | Taille | Last-Modified | Constat |
| --- | --- | --- | --- | --- | --- |
| XVIe | AMO30 | `16/amo/tous_acteurs_mandats_organes_xi_legislature/AMO30_tous_acteurs_tous_mandats_tous_organes_historique.json.zip` | 11 890 924 | 28/06/2024 | téléchargée : 2 885 acteurs, 9 654 organes, 50 déports ; mandats XVIe tous clos |
| XVIe | AMO20 | `16/amo/deputes_senateurs_ministres_legislature/AMO20_dep_sen_min_tous_mandats_et_organes.json.zip` | 2 368 484 | 28/06/2024 | HEAD seulement |
| XVIe | Agenda | `16/vp/reunions/Agenda.json.zip` | 7 888 186 | 28/06/2024 | téléchargée : 8 320 réunions |
| XVe | AMO30 | `15/amo/tous_acteurs_mandats_organes_xi_legislature/AMO30_tous_acteurs_tous_mandats_tous_organes_historique.json.zip` | 10 081 925 | **09/06/2022** | **non listée** sur la page des archives XVe (trouvée par HEAD) ; téléchargée : 2 416 acteurs, 8 529 organes ; **prise avant la fin de la XVe** (21/06/2022) : 567 mandats ASSEMBLEE XVe sans date de fin, GP sans date de fin |
| XVe | AMO20 | `15/amo/deputes_senateurs_ministres_legislature/AMO20_dep_sen_min_tous_mandats_et_organes_XV.json.zip` | 3 213 545 | 09/06/2022 | suffixe `_XV` |
| XVe | Agenda | `15/vp/reunions/Agenda_XV.json.zip` | 38 258 296 | 09/06/2022 | suffixe `_XV`, HEAD seulement (> 20 Mo) |
| XVe | Séances | `15/vp/seances/seances_publique_excel.csv` | 35 o | 20/06/2022 | 35 octets : pratiquement vide (contenu non lu) |
| XIVe | AMO30 | `14/amo/tous_acteurs_mandats_organes_xi_legislature/…historique.json.zip` | — | — | **404 : pas d'AMO30 figée pour la XIVe** (confirmé) |
| XIVe | AMO20 | `14/amo/deputes_senateurs_ministres_legislatures_XIV/AMO20_dep_sen_min_tous_mandats_et_organes_XIV.json.zip` | 922 349 | **21/03/2018** | la page en liste aussi une variante sans `_XIV` dans le dossier : **404**. Un seul JSON (`export.acteurs.acteur[]`, `export.organes.organe[]`) : 1 242 acteurs, 1 179 organes, 750 mandats ASSEMBLEE XIVe (691 dans la courante, 59 en plus non analysés), 154 avec siège — état de mars 2018 [S], pas un siège de la XIVe |
| XIVe | Agenda | `14/vp/reunions/Agenda_XIV.json.zip` | 956 779 | 21/03/2018 | page « agendas » XIVe en **404** ; fichier trouvé par HEAD. Un seul JSON, 11 450 réunions **toutes datées du 20/06/2017 au 21/12/2018** (uid `RUANR5L14…` 6 491, `RUANR5L15…` 4 874) : **ce n'est pas l'agenda de la XIVe** |

Comparaison figée ↔ courante [M] :

- 99 mandats de l'AMO30 figée XVIe et 402 de la figée XVe **n'existent plus** dans la courante
  (surtout Sénat : DELEGSENAT, GROUPESENAT, ORGEXTPARL, API ; plus 1 GOUVERNEMENT). La source
  **supprime** des mandats : la collecte doit savoir dire « disparu à la source ».
- Libellés d'organes réécrits : XVe → courante 16 (9 GROUPESENAT, ex. `PO77707` « communiste
  républicain et citoyen » → « Communiste Républicain Citoyen et Écologiste - Kanaky » ;
  `PO732421` « Groupe La République En Marche » → « Rassemblement des démocrates, progressistes et
  indépendants ») ; XVIe → courante 2 (ORGEXTPARL). Aucun GP de l'Assemblée renommé.
- Positions des groupes XVe et XVIe : identiques.

Autres jeux AMO XVIIe vus (HEAD) : AMO10 4 884 178 o (03/11/2026), AMO20 2 668 595 o (03/11/2026),
**AMO50 14 342 787 o, Last-Modified 11/07/2024** : le jeu « acteurs mandats organes divisés » n'est
plus mis à jour depuis le début de la XVIIe [M].

---

## 7. Poids d'une frise de carrière

Lignes `[personne, organe, type, qualité, début, fin]` triées par date, JSON compact (`frise.py`) :

| Échantillon | Lignes | Brut | gzip -9 | zstd -19 | zstd -3 |
| --- | --- | --- | --- | --- | --- |
| Ruffin, liste de listes | 141 | 9 658 o | **1 368 o** | 1 198 o | 1 512 o |
| Ruffin, objets à clés nommées | 141 | 16 849 o | 1 497 o | 1 305 o | 1 686 o |
| Ruffin, sans GA/GE/GEVI | 135 | 9 252 o | 1 301 o | 1 132 o | 1 417 o |
| Le Fur (max), liste de listes | 814 | 51 733 o | 4 649 o | 3 670 o | 5 045 o |
| Le Fur, sans GA/GE/GEVI | 89 | 6 237 o | 1 199 o | 1 110 o | 1 293 o |
| Fichier source de l'acteur Ruffin (pour comparaison) | — | 68 827 o | 4 668 o | | |

- ≈ 68 o par ligne brute, ≈ 10 o par ligne après gzip [C].
- Fusionner les périodes contiguës (écart ≤ 1 jour) d'un même organe et d'une même qualité ne
  gagne presque rien (Ruffin 141 → 140, tous acteurs 173 869 → 171 855) : les permutations
  alternent entre commissions, avec des trous de 1 à 3 jours [M]. Une fusion utile pour l'affichage
  demande une règle plus lâche (même organe, même législature, trou ≤ N jours) [S].
- Une frise « par institution » (ASSEMBLEE + GP + GOUVERNEMENT/MINISTERE, ce que montre l'en-bref)
  tient pour Ruffin en 9 lignes, ≈ 0,6 Ko brut [C].
- Toutes les frises (3 175 acteurs, un fichier par acteur) : 11,4 Mo brut, 2,0 Mo en gzip -9
  cumulé [M].

---

## 8. Pièges : bilan

| Piège | Statut |
| --- | --- |
| Transferts coupés | **confirmé**, même à 13,7 Mo (coupure à 10 Mio, statut 200) |
| Deux serveurs, deux versions | **non reproduit** à 14:53–14:58 UTC : 3 serveurs (`b2`, `f1`, `f2`), même ETag ; l'ETag (taille-mtime) permet de détecter le mélange |
| Reprise par segments | `Range` honoré (206) sur `f1` ce jour-là |
| Siège réécrit dans la courante | **confirmé et chiffré** (XVIe : 323 différents, 202 effacés sur 591) |
| Pas d'AMO30 figée XIVe | **confirmé** (404) ; seul AMO20 XIVe (mars 2018) |
| Archive figée = état de fin | **infirmé pour la XVe** : figée le 09/06/2022, avant la fin (21/06/2022) |
| Un objet seul = dict | confirmé, 15 chemins listés en 2.5, plus la forme `{"@xsi:nil":"true"}` |
| Mandat suspendu, pas terminé | confirmé ; **nouveau** : `dateDebut` du mandat de reprise = début du mandat d'origine, la vraie date est `datePriseFonction` |
| Ministère et non gouvernement | confirmé ; **nouveau** : 408 mandats MINISTERE sont des missions de parlementaires, pas des fonctions ministérielles |
| Succession des ministères (149) | confirmé, **seulement depuis mai 2022** |
| Rattachement ministre délégué → tutelle | **aucun champ**, libellé libre seulement |
| Position déclarée des groupes | **nouveau** : `null` pour les 14 GP de la XVIIe |
| Mandats GOUVERNEMENT ouverts dans un gouvernement clos | **nouveau** : 7 (Bayrou) |
| QG sans référence de séance | confirmé |
| Agenda mélange Sénat, commissions | confirmé (158 séances du Sénat) ; **nouveau** : 984 réunions d'organes absents d'AMO |
| Agenda XIVe | **nouveau** : le fichier `Agenda_XIV` ne couvre que 2017-2018 |
| Mandats supprimés à la source | **nouveau** : 99 (figée XVIe) et 402 (figée XVe) absents de la courante |
| AMO50 | **nouveau** : plus mis à jour depuis le 11/07/2024 |
