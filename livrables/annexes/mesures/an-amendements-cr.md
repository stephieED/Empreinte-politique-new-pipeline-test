# Mesures — Assemblée nationale : amendements et comptes rendus de séance (Syceron)

Mesures faites le **04/11/2026** (après-midi) par `an-amendements-cr`.
Statut de chaque chiffre : **[M]** mesuré, **[C]** calculé à partir de mesures, **[S]** supposé ou extrapolé.
Les durées de téléchargement viennent d'une **connexion domestique** : elles ne valent pas pour un
serveur GitHub Actions.

- Données : `travail/sources/an-amendements/Amendements17.json.zip`, `travail/sources/an-syceron/syseron17.xml.zip`
  (+ lecture de `travail/sources/an-amo/AMO30_17.json.zip`, téléchargé par une autre mesure, pour les noms).
- Scripts : `travail/scripts/an-amendements-cr/` (tous lancés avec `travail/.venv/bin/python -I`) :
  `lire_amendements.py` (lecture en flux → JSONL compact), `analyse_amendements.py`, `copies.py`,
  `fiche_amendements.py`, `noms_acteurs.py`, `lire_syceron.py`, `analyse_syceron.py`,
  `analyse_syceron2.py`, `fiche_paroles.py`, `attribution.py`, `compare_web.py` ; journaux de
  téléchargement `dl_*.log` / `dl_*.headers`.

---

## 1. En-têtes HTTP des archives (HEAD du 04/11/2026)

Base : `https://data.assemblee-nationale.fr/static/openData/repository/`. Chemins lus sur les pages
de jeux (`/travaux-parlementaires/amendements/tous-les-amendements`, `/archives-16e/…`,
`/archives-anterieures/archives-15e/…`, `…/archives-14e/amendements`, `/travaux-parlementaires/debats`).

| Archive | Chemin | Taille (octets) | Last-Modified | ETag | Accept-Ranges |
| --- | --- | --- | --- | --- | --- |
| Amendements XVIIe | `17/loi/amendements_div_legis/Amendements.json.zip` | 351 881 121 (335,6 Mio) | Tue, 03 Nov 2026 15:20:58 GMT | `"14f947a1-65f60cf352bc7"` | bytes |
| Amendements XVIe | `16/loi/amendements_div_legis/Amendements.json.zip` | 363 306 362 (346,5 Mio) | Fri, 28 Jun 2024 08:25:47 GMT | `"15a79d7a-61beefe967ac2"` | bytes |
| Amendements XVe | `15/loi/amendements_legis/Amendements_XV.json.zip` | 648 539 281 (618,5 Mio) | Thu, 09 Jun 2022 12:50:37 GMT | `"26a7ec91-5e10344b1b45e"` | bytes |
| Amendements XIVe | `14/loi/amendements_legis_XIV/Amendements_XIV.json.zip` | 103 716 698 (98,9 Mio) | Wed, 21 Mar 2018 09:38:51 GMT | `"62e975a-567e8f56a20c0"` | bytes |
| Syceron XVIIe | `17/vp/syceronbrut/syseron.xml.zip` | 60 854 987 (58,0 Mio) | Tue, 03 Nov 2026 03:05:37 GMT | `"3a092cb-65f5689639791"` | bytes |
| Syceron XVIe | `16/vp/syceronbrut/syseron.xml.zip` | 57 553 703 (54,9 Mio) | Fri, 28 Jun 2024 02:05:35 GMT | `"36e3327-61be9aedaeab0"` | bytes |
| Syceron XVe | `15/vp/syceronbrut/syseron.xml.zip` | 148 954 869 (142,1 Mio) | Thu, 09 Jun 2022 02:06:26 GMT | `"8e0def5-5e0fa44f4a2dd"` | bytes |

Remarques [M] :
- Les tailles du cahier (283, 363, 618, 99 ; 149, 57, 56) sont en **Mio**. L'archive XVIIe des
  amendements est passée de 283 Mio (22/09/2026) à **335,6 Mio** (03/11/2026).
- Variantes publiées aussi : `.xml.zip` pour XIV-XVII, et `Amendements_XIV.csv.zip` pour la XIVe.
- L'archive XVIIe des amendements porte un `Last-Modified` à **15:20 GMT** le 03/11, pas la nuit :
  la republication « chaque nuit » n'est pas une heure fixe. Syceron XVIIe : 03:05 GMT.
- En-têtes utiles : `cache-control: max-age=14400` (CDN, `x-cdn-pop: rbx`), `x-cacheable`
  (« Matched cache » ; « **Not cacheable: too big** » pour les amendements XVe, 648 Mo, donc servis
  par l'origine), et **`be: f1` / `be: f2`** qui nomme le serveur d'origine. C'est par là qu'on voit
  les deux serveurs du piège « une adresse, deux fichiers ».
- `date:` de la réponse CDN : 13:12 GMT pour une requête faite à 14:52 GMT → réponse servie depuis
  le cache depuis 1 h 40.

## 2. Téléchargements (04/11/2026, 15:52-15:54 heure de Paris, connexion domestique)

| Archive | Résultat |
| --- | --- |
| Syceron XVIIe | 60 854 987 o en **27,3 s** d'une traite (2,2 Mo/s), `be: f1`, zip valide [M] |
| Amendements XVIIe, 1re tentative | **coupée à 57 751 482 o** (16 %) après 24,3 s, `be: f2`. curl rend la main sans erreur visible avec `-s` : il faut comparer la taille reçue au `content-length` [M] |
| Reprise 1 (`-r 57751482-`, `If-Range: <ETag>`) | `206`, `content-range` correct, `be: f1`, **0 octet** reçu, erreur HTTP/2 (curl 92) au bout de 2 s [M] |
| Reprise 2 | `206`, `be: f2`, **10 485 760 o** (10 Mio pile) puis coupure (curl 18) [M] |
| Reprise 3 | `206`, `be: f2`, les 283 643 879 o restants en 87,9 s [M] |
| Total | **2 min 21 s** de bout en bout, 4 requêtes ; zip reconstitué valide (`unzip -t` sans erreur, sha256 `9643f27e…d5ef`) [M] |

Ce que ça montre :
- Le piège des **coupures** est confirmé (2 coupures sur 4 requêtes pour 352 Mo). La reprise par
  segments **a fonctionné** ce jour-là : les deux serveurs (`f1`, `f2`) servaient le même ETag.
- La parade sûre : `If-Range` avec l'ETag de la première réponse. Si le serveur qui répond a une
  autre version, il renvoie `200` et le fichier entier au lieu d'un `206`, ce qui évite le mélange.
  Il faut ensuite contrôler le zip (`unzip -t`, 10,4 s et 4,7 Mo de mémoire ici) [M].

## 3. Amendements XVIIe

### 3.1 Contenu et lecture

- **144 112 fichiers** dans le zip, 985 876 657 o décompressés (6 841 o en moyenne, 153 228 au plus) [M].
- Arborescence : `json/{dossier DLR…}/{document visé}/{uid}.json`. 338 dossiers ; le chemin donne
  le document visé (`texteLegislatifRef`, égal au chemin dans 100 % des cas). **Un dossier
  `json/incorrect_data/`** contient 170 amendements sur 5 documents (`PIONANR5L17BTC2202` 96,
  `BTC2526` 50, `BTC2812` 21, `PRJLANR5L17BTC1355` 2, `PIONANR5L17BTC0492` 1) : pour eux, l'archive
  ne donne pas le dossier [M].
- 144 112 uid distincts, mais **143 766 amendements distincts** une fois écartés les doubles décrits
  en 3.2 [M]. Dépôts du 18/09/2024 au 03/11/2026.
- Lecture complète en flux (zipfile membre par membre + orjson, écriture d'un JSONL compact) :
  **38,2 s, 132 Mo de mémoire de pointe** (`/usr/bin/time -v`) [M]. Le JSONL compact
  (sans dispositif, exposé en texte brut) fait 409 Mo.
- Analyse duckdb sur ce JSONL (exposés exclus) : 3,5 s, 469 Mo de pointe [M].

### 3.2 Le piège des copies divergentes

Méthode : regrouper par (`examenRef`, `identification/numeroLong`). Un même numéro dans un même
examen sous plusieurs uid = une copie.

- **346 paires** (692 fichiers), jamais plus de 2 copies [M]. Toutes ont un uid en `…B{n}…` et un
  en `…BTC{n}…` (le texte déposé et le texte de la commission), dans 5 examens :
  `EXANR5L17PO838901BTC2755P0D1` (156), `BTC2120` (116), `BTC2202` (48, dans `incorrect_data`),
  `BTC2526` (25, idem), `BTC1364` (1). Exemple : `AMANR5L17PO838901B2202P0D1N000011` et
  `AMANR5L17PO838901BTC2202P0D1N000011`.
- Dans ces 346 paires, **les copies ne divergent pas** au 03/11/2026 : auteur, cosignataires, état,
  sous-état, sort, exposé, dispositif, libellé identiques. Seuls changent uid, `chronotag`,
  `documentURI` et `datePublication` (différente dans 220 paires) [M].
- **Une divergence de cosignataires entre copies n'a pas été observée sous la forme décrite par le
  cahier** dans cette archive. Ont été vérifiés [M] :
  - le libellé des signataires et la liste `cosignataires` concordent pour les 133 984
    amendements de député (nombre de civilités = 1 + nombre de cosignataires, ou « et les membres
    du groupe ») ;
  - dans les groupes d'amendements identiques (`discussionIdentique`), 103 cas ont deux
    amendements du même auteur, et 39 d'entre eux ont des cosignataires différents. Ce sont des
    amendements **distincts** (numéros différents, exposés de longueur différente), par exemple
    `…PO419610B3058P0D1N000343` (8 cosignataires) et `N000404` (1), pas des copies.
  Hypothèse [S] : le piège concerne d'autres législatures, ou des états successifs de l'archive
  courante (le retrait d'un cosignataire réécrit la seule copie publiée : c'est « l'archive
  courante réécrit le passé »). Il faudrait deux archives datées pour le voir.
- Règle de dédoublonnage proposée : clé (`examenRef`, `numeroLong`) ; on garde l'uid dont le
  segment de texte égale celui de `examenRef` (la copie `BTC`, qui est aussi la plus récente par
  `chronotag`) et on garde l'autre uid comme alias, puisque les deux ont une adresse publique.
- Autres anomalies [M] : 1 liste de cosignataires contient un doublon
  (`AMANR5L17PO419610B1906P2D1N000024`) ; 4 amendements de type « Député » n'ont ni auteur ni
  libellé (`AMANR5L17PO419610B3058P0D1N000723`, `…N000724`, `…PO838901B1906P1D2N000001`, `…N000002`) ;
  l'auteur n'est jamais dans sa propre liste de cosignataires.

### 3.3 Auteurs et signatures (144 112 fichiers ; 143 766 après dédoublonnage)

| Type d'auteur | Amendements |
| --- | --- |
| Député | 133 984 |
| Rapporteur | 8 618 (316 personnes ; 2 042 portent aussi `auteurRapporteurOrganeRef`) |
| Gouvernement | 1 510 (sans `acteurRef`) |

- 629 auteurs distincts, 650 cosignataires distincts [M].
- **3 532 362 cosignatures** après dédoublonnage (3 540 490 avant), soit 24,6 par amendement en
  moyenne [M]. 35 874 amendements sans cosignataire.
- **Maximum : 242 cosignataires** (`AMANR5L17PO838901B3210P2D1N001096`), puis 189 et 173 [M].
- Répartition du nombre de cosignataires [M] : 0 → 35 874 ; 1-5 → 24 345 ; 6-20 → 32 515 ;
  21-50 → 20 523 ; 51-100 → 26 220 ; plus de 100 → 4 635.
- Les cinq cosignataires les plus fréquents ont chacun environ **21 400 signatures**
  (PA793464, PA842155…) : des groupes entiers cosignent tout ce que déposent leurs membres.

### 3.4 Couples (état, sous-état) — liste complète, 144 112 fichiers

Le champ `sort` n'est rempli que pour les 81 421 amendements « Discuté » : il recopie le libellé du
sous-état. Pour les autres, l'issue ne se lit que dans le couple. Le code de sous-état « R » (libellé
« R ») apparaît sous quatre états différents, sans signification documentée.

| état (code, libellé) | sous-état (code, libellé) | n |
| --- | --- | --- |
| DI Discuté | DI Rejeté | 34 581 |
| DI Discuté | DI Adopté | 19 116 |
| ET En traitement | — | 14 192 |
| DI Discuté | DI Tombé | 13 426 |
| AC A discuter | — | 11 789 |
| DI Discuté | DI Non soutenu | 9 553 |
| RT Retiré | RT Retiré après publication | 7 771 |
| IR Irrecevable 40 | IR Charge | 6 642 |
| IRR45 Irrecevable | IRR45 Cavalier (45) | 6 036 |
| DI Discuté | DI Retiré | 4 745 |
| ET En traitement | R R | 3 754 |
| IR Irrecevable 40 | IR Cavalier social | 1 584 |
| RT Retiré | RT Retiré avant publication | 1 431 |
| IR Irrecevable 40 | IR Crédits | 1 315 |
| IRRAI Irrecevable | IRRAI Autre irrecevabilité | 1 298 |
| IRR45 Irrecevable | IRR45 Entonnoir (45) | 1 233 |
| IRRD Irrecevable | IRRD Doublon | 1 225 |
| IRRSA Irrecevable | IRRSA Sous-amendement (98) | 1 101 |
| IR Irrecevable 40 | IR Gage | 856 |
| IR Irrecevable 40 | IR Cavalier budgétaire | 551 |
| IRR42 Irrecevable | IRR42 Satisfait ou inopérant (42) | 387 |
| IRRHC Irrecevable | IRRHC Hors champ | 308 |
| IR Irrecevable 40 | IR Irr en première partie | 258 |
| IR Irrecevable 40 | IR Autres irr LOLFSS | 229 |
| IR Irrecevable 40 | IR Autres irr LOLF | 196 |
| IRR38 Irrecevable | IRR38 Champ de l'habilitation (38) | 114 |
| IRRAIF Irrecevable | IRRAIF Autre irrecevabilité 40 | 94 |
| IRRHD Irrecevable | IRRHD Hors-délais | 94 |
| IRR20 Irrecevable | IRR20 Injonction (20) | 57 |
| IR Irrecevable 40 | IR Irr en seconde partie | 50 |
| IRR48 Irrecevable | IRR48 Ordre du jour (48) | 46 |
| IRR37 Irrecevable | IRR37 Disposition réglementaire (37) | 35 |
| IRR127 Irrecevable | IRR127 Domaine loi organique (127) | 26 |
| IRR41 Irrecevable | IRR41 Domaine de la loi (41) | 6 |
| AC A discuter | R R | 4 |
| effacé effacé | — | 4 |
| RT Retiré | R R | 3 |
| IRR53 Irrecevable | IRR53 Ratification traité (53) | 1 |
| IRRD Irrecevable | R R | 1 |

Ambiguïtés [M] : « Retiré » est un état (RT, avant ou après publication) **et** un sous-état de
« Discuté » (4 745 retraits en séance). Les irrecevabilités se répartissent sur deux familles d'état
(`IR` « Irrecevable 40 », `IRR…` « Irrecevable »).

### 3.5 Exposé sommaire et dispositif (143 766 amendements distincts)

| | moyenne | médiane | 99e centile | max | vides |
| --- | --- | --- | --- | --- | --- |
| Exposé, texte brut (balises ôtées, entités décodées) | 1 201 car. | 978 | 4 846 | 21 444 (`AMANR5L17PO838901B1906P1D1N004097`) | 25 178 |
| Exposé, HTML source | 1 626 car. | | | 108 537 | |
| Dispositif, texte brut | 338 car. | 100 | 3 386 | 87 111 (`AMANR5L17PO838901BTC0930P0D1N000029`) | 45 393 |
| Dispositif, HTML source | 654 car. | | | 143 052 | |

- Volume total des exposés : **172,8 millions de caractères** ; dispositifs : 48,6 M [M].
- Constat nouveau [M] : **les amendements irrecevables n'ont ni exposé ni dispositif** (23 669 sur
  23 669) ; 1 429 retirés non plus (retirés avant publication). Le filtre par mot ne les trouvera pas.
- 11 528 amendements discutés ont un dispositif vide (non expliqué).

## 4. Personnes : amendements XVIIe

Identifiants vérifiés dans `AMO30_17.json.zip` (3 175 acteurs) : **François Ruffin = `PA722142`**.
Auteur principal le plus actif : **Bastien Lachaud, `PA720846`**, puis Thibault Bazin (`PA642847`,
2 211 dont 209 comme rapporteur) et Matthias Renault (`PA841955`, 1 606).

| | Auteur principal | dont « Rapporteur » | Signatures (cosignataire) |
| --- | --- | --- | --- |
| Bastien Lachaud PA720846 | **2 623** | 56 | 18 854 |
| François Ruffin PA722142 | **136** | 0 | **13 763** |

Chiffres après dédoublonnage. Les doubles ne touchent pas ces deux personnes. Les signatures de
Ruffin pèsent 100 fois ses amendements : c'est l'effet des cosignatures de groupe.

Sérialisation d'une liste (JSON via orjson ; champs : `id`, `num`, `date` de dépôt, `sort` (sort,
sinon libellé du sous-état, sinon de l'état), `organe` (PO de l'examen : commission ou séance),
`doc` (document visé), `art` (article visé)) [M] :

| Liste | n | brut | gzip -9 | zstd -3 | zstd -19 | gzip par amdt |
| --- | --- | --- | --- | --- | --- | --- |
| Ruffin, sans exposé | 136 | 22 126 | **2 204** | 2 536 | 1 884 | 16 o |
| Ruffin, exposé tronqué à 300 car. | 136 | 50 929 | 8 369 | 8 972 | 7 741 | 62 o |
| Ruffin, exposé intégral | 136 | 232 694 | **45 271** | 34 938 | 29 425 | 333 o |
| Ruffin, colonnaire sans exposé | 136 | 15 658 | 2 045 | 2 491 | 1 895 | 15 o |
| Ruffin, exposés seuls | 90 non vides | 209 753 | 42 065 | 31 854 | 27 132 | |
| Lachaud, sans exposé | 2 623 | 457 674 | **20 366** | 26 127 | 16 198 | 8 o |
| Lachaud, exposé tronqué à 300 car. | 2 623 | 1 276 680 | 58 540 | 57 721 | 43 922 | 22 o |
| Lachaud, exposé intégral | 2 623 | 8 065 543 | **252 070** | 168 403 | 129 917 | 96 o |
| Lachaud, colonnaire sans exposé | 2 623 | 331 830 | 19 106 | 22 856 | 14 649 | 7 o |
| Lachaud, exposés seuls | 2 561 non vides | 7 592 132 | 218 412 | 132 211 | 106 735 | |

Lecture [C] :
- La liste sans exposé est légère : 2 Ko gzip pour Ruffin, 20 Ko pour la personne la plus active.
- Les exposés en multiplient le poids par 20 (Ruffin) à 12 (Lachaud). Le filtre par mot sur les
  exposés coûte donc **45 Ko gzip pour Ruffin et 250 Ko pour Lachaud** s'il charge les exposés
  entiers. zstd -19 fait 35 à 50 % de mieux que gzip sur les exposés, parce qu'ils se répètent
  beaucoup (séries d'amendements au même exposé).
- Les exposés de Lachaud sont très redondants : 2 822 caractères en moyenne, 83 o gzip par
  amendement. Ceux de Ruffin ne le sont pas : 2 217 caractères, 309 o.
- Ruffin : 46 de ses 136 amendements n'ont pas d'exposé (irrecevables). Années de dépôt : 68 en
  2024, 37 en 2025, 31 en 2026. Lachaud : 75, 916, 1 632 ; 1 181 en traitement et 1 076 à discuter
  au 03/11/2026.

## 5. Comptes rendus Syceron XVIIe

### 5.1 Contenu et lecture

- **652 comptes rendus** (un XML par séance, `xml/compteRendu/{uid}.xml`), 652 séances distinctes,
  du 18/07/2024 au 02/11/2026 ; 650 « complet », **2 « provisoire »** (les deux séances du 02/11/2026) ;
  tous `version = avant_JO` [M]. 355 385 095 o décompressés (545 Ko par CR, 1,13 Mo au plus).
- **353 784 paragraphes** (`<paragraphe>`), 543 par CR en moyenne, 1 366 au plus [M].
- Lecture complète (zipfile membre par membre, lxml `fromstring` par CR, `resolve_entities=False`) :
  **28 à 34 s, 38 Mo de mémoire de pointe** [M].

### 5.2 Où se trouve chaque information

| Information | Emplacement |
| --- | --- |
| Identifiant de séance | `compteRendu/seanceRef` (`RUANR5L17S2026IDS29926`) ; uid du CR `compteRendu/uid` (`CRSANR5L17S2026O1N053`) ; `sessionRef` ; `metadonnees/dateSeance` au format `AAAAMMJJHHMMSSmmm` |
| Identifiant d'orateur | attribut `paragraphe/@id_acteur` (**avec** préfixe `PA`) et `@id_mandat` ; `orateurs/orateur/id` (**sans** `PA`) ; pour un bloc d'amendement, `interExtraction/@id_acteur` |
| Nom affiché | `orateurs/orateur/nom` (« M. le président », « Mme Alice Rufo »…) |
| Qualité | `orateurs/orateur/qualite` (texte libre, vide pour 82 % des paragraphes attribués) ; `@roledebat="president"` pour une partie de la présidence |
| Ancre | `paragraphe/@id_syceron` = attribut `id` de l'intervention sur la page publique. Lien : `https://www.assemblee-nationale.fr/dyn/17/comptes-rendus/seance/{uid CR}#{id_syceron}` (l'adresse par uid redirige vers l'adresse lisible, vérifié sur `CRSANR5L17S2026O1N053#3914476`) |
| Point d'ordre du jour | `<point nivpoint="…" code_grammaire="…" valeur_ptsodj="…">` et son `<texte>` (titre). Les points sont surtout des **frères successifs** : la hiérarchie se reconstruit par `nivpoint` dans l'ordre du document. Chaque paragraphe porte aussi `@valeur_ptsodj`, le numéro du point (renseigné pour 352 421 paragraphes sur 353 784). Le sommaire (`metadonnees/sommaire/sommaire1/@valeur_pts_odj`) donne le même découpage |
| Autres | `@ordre_absolu_seance` (rang), `@id_preparation`, `@code_grammaire`, `texte/@stime` (position dans la vidéo, en secondes) |

### 5.3 Attribution [M]

- 318 365 paragraphes sur 353 784 ont un `id_acteur` (**90,0 %**).
- **Présidence** : `@roledebat="president"` marque 49 842 paragraphes. Il en manque **60 275**, que
  seul le nom générique (« M. le président », « Mme la présidente ») permet de reconnaître. En tout,
  110 110 paragraphes de présidence. Un critère qui ne lit que `roledebat` compte donc des
  présidentes de séance parmi les intervenants.
- **`PA0`** sur 603 paragraphes (orateurs collectifs, « Un député du groupe RN », mais aussi
  9 paragraphes de « Mme Christine Arrighi »). 2 622 paragraphes ont un `orateur/id` sans
  `id_acteur`.
- **Identifiants négatifs** (`PA-125869` pour « M. François Bayrou », `PA-126329`…) sur 315
  paragraphes, 54 identifiants distincts, absents d'AMO (nouveau piège).
- **Identifiant de repli** confirmé en XVIIe : `PA793214` (Audrey Abadie-Amiel) est porté par
  13 paragraphes d'autres orateurs (invités comme « M. Jean-Marc Cantais, policier, lanceur
  d'alerte », « Plusieurs députés du groupe LFI-NFP »…).
- Attribution manifestement fausse : `CRSANR5L17S2026O1N177 #4042860`, « Mme Alice Rufo, ministre
  déléguée », porte `id_acteur=PA722142` (**Ruffin**). En comparant le nom affiché au nom AMO de
  l'acteur cité : **39 paragraphes discordants** et 49 à nom vide, sur 207 262 concordants (après
  normalisation des apostrophes).

### 5.4 Un identifiant stable de prise de parole ?

- `id_syceron` est **unique dans toute l'archive** (353 784 valeurs distinctes). `id_preparation`
  ne l'est pas (333 408). (`uid CR`, `ordre_absolu_seance`) est le rang que la republication
  renumérote [M].
- Test : les deux CR provisoires de l'archive (générés le 03/11 vers 00:30) comparés à leur page
  publique du 04/11 (déjà republiée : 1 263 interventions en ligne contre 407 dans l'archive pour
  `CRSANR5L17S2027O1N051`) [M] :

  | CR | paragraphes attribués (archive) | même id_syceron, même texte | même id, texte retouché | id disparu |
  | --- | --- | --- | --- | --- |
  | `CRSANR5L17S2027O1N050` | 651 | 642 | 6 | 3 |
  | `CRSANR5L17S2027O1N051` | 330 | 318 | 9 | 3 |
  | `CRSANR5L17S2026O1N053` (complet, témoin) | 280 | 277 | 3 | 0 |

  Les id disparus reviennent souvent **sous un nouvel id** : Juvin `4214884` → `4216676`,
  `4214399` → `4216768`, `4215695` → `4216336`. Les retouches de texte sont faites en place sous le
  même id (« gasoil » → « gazole », « soutiendra » → « votera pour »). Même sur un CR « complet »,
  le texte en ligne diffère de l'archive (3 paragraphes).
- `texte/@stime` est **absent des CR provisoires** (0 sur 981). Sur les CR complets, (séance,
  acteur, stime) est quasi unique : 315 539 valeurs distinctes pour 315 541 paragraphes.
- **Clé proposée** [S] : (`uid CR`, `id_syceron`), qui est aussi l'ancre publique, stable dans
  97 à 99 % des cas d'une republication à l'autre. Pour rapprocher les id qui changent : une
  empreinte (`seanceRef`, `id_acteur`, 80 premiers caractères du texte normalisé), et `stime`
  quand il existe. Il ne faut jamais utiliser `ordre_absolu_seance`. Le texte doit se recharger
  à chaque republication, même quand l'id ne change pas.

### 5.5 Totaux XVIIe (archive du 03/11/2026, séances du 18/07/2024 au 02/11/2026)

| | paragraphes | caractères |
| --- | --- | --- |
| Tous paragraphes | 353 784 | 117 837 208 |
| Attribués à un `id_acteur` | 318 365 | 116 074 951 |
| Présidence (roledebat ou nom générique) | 110 110 | 9 430 842 |
| **Prises de parole hors présidence, personne identifiée (hors PA0)** | **207 621** | **106 625 444** |

733 identifiants d'orateurs distincts hors présidence. Longueur d'un paragraphe attribué : moyenne
365 caractères, médiane 76, maximum 22 382 [M].

### 5.6 Extrapolation XVe et XVIe (supposé)

C'est une **extrapolation** au prorata de la taille compressée des archives (XVe 148,95 Mo, soit
×2,45 ; XVIe 57,55 Mo, soit ×0,95). Elle suppose la même structure XML et le même taux de
compression. Elle n'a pas été vérifiée : l'archive XVe a en outre 499 CR sans identifiant
d'orateur (cahier).

| | paragraphes | prises de parole hors présidence | caractères (hors présidence) |
| --- | --- | --- | --- |
| XVe [S] | ≈ 870 000 | ≈ 510 000 | ≈ 260 M |
| XVIe [S] | ≈ 335 000 | ≈ 195 000 | ≈ 100 M |
| XVIIe [M] | 353 784 | 207 621 | 106,6 M |
| XV-XVII [S] | ≈ 1,56 M | ≈ 0,91 M | ≈ 470 M |

Même méthode pour les amendements [S] (2 442 o compressés par amendement en XVIIe) :
≈ 149 000 en XVIe et ≈ 266 000 en XVe. La XIVe a un autre schéma et ne se prête pas au calcul.

## 6. Personnes : prises de parole XVIIe

Définition : un paragraphe dont l'`id_acteur` est la personne et dont le texte n'est pas vide.

- **Le plus de paragraphes tous rôles confondus** : Clémence Guetté (`PA795310`), 16 504, dont
  **16 328 en présidence de séance** (1,41 M caractères, 71 157 hors présidence). Les cinq premiers
  « orateurs » sont des vice-présidents. Un compte qui inclut la présidence ne dit rien de
  l'activité de débat [M].
- **Le plus de prises de parole hors présidence** : **Thibault Bazin (`PA642847`)**, 4 441
  paragraphes, 1 870 691 caractères, 266 séances. Viennent ensuite Philippe Juvin 3 331, Amélie
  de Montchalin 3 024 (la plus gros volume : 1 876 397 caractères), Antoine Léaument 2 756 et Ugo
  Bernalicis 2 638 [M].
- **François Ruffin (`PA722142`)** : **193 paragraphes, 142 929 caractères**, 45 séances, du
  22/10/2024 au 11/06/2026. 186 sont affichés « M. François Ruffin » et 6 « M. François Ruffin (EcoS) ».
  1 est une erreur de la source (Alice Rufo, voir 5.3). Aucun paragraphe affiché à son nom ne
  porte un autre identifiant [M].

Sérialisation (JSON via orjson ; liste = `d` date, `q` qualité, `odj` [point de niveau 1, point le
plus précis], `x` extrait de 300 caractères, `u` lien complet ; variante « lien reconstruit » :
`cr` + `id` au lieu de l'URL) [M] :

| Liste | n | brut | gzip -9 | zstd -3 | zstd -19 | gzip par parole |
| --- | --- | --- | --- | --- | --- | --- |
| Bazin, liste + extrait 300 + lien complet | 4 441 | 1 766 398 | **327 619** | 298 980 | 236 747 | 74 o |
| Bazin, liste + extrait, lien reconstruit | 4 441 | 1 459 969 | 317 859 | 295 151 | 231 784 | 72 o |
| Bazin, liste sans extrait | 4 441 | 693 430 | 35 091 | 36 653 | 25 172 | 8 o |
| Bazin, texte intégral (cr, id, texte) | 4 441 | 2 206 743 | **668 851** | 624 210 | 474 547 | 151 o |
| Ruffin, liste + extrait 300 + lien complet | 193 | 86 151 | **20 774** | 21 516 | 19 229 | 108 o |
| Ruffin, liste + extrait, lien reconstruit | 193 | 72 834 | 20 297 | 21 141 | 18 835 | 105 o |
| Ruffin, liste sans extrait | 193 | 28 111 | 2 701 | 2 932 | 2 474 | 14 o |
| Ruffin, texte intégral | 193 | 160 412 | **54 785** | 56 720 | 48 634 | 284 o |
| Guetté (présidence comprise), liste + extrait | 16 504 | 4 825 091 | 339 800 | 332 231 | 218 067 | 21 o |

Lecture [C] : l'extrait de 300 caractères fait l'essentiel du poids (×9 sur la liste sans extrait).
Pour la personne la plus active, la liste avec extraits pèse **≈ 320 Ko gzip** et le texte intégral
**≈ 670 Ko gzip**. Il faut paginer ou charger par période. Reconstruire le lien côté client ne fait
gagner que 3 %, car gzip absorbe déjà la partie fixe de l'URL.

## 7. Pièges : bilan

| Piège (cahier 3.1) | Statut au 04/11/2026 |
| --- | --- |
| Transferts coupés sur les grosses archives | **Confirmé** : 2 coupures sur 4 requêtes (352 Mo), curl ne signale rien avec `-s` |
| Reprise par segments pas toujours honorée | Honorée ce jour (206 corrects sur f1 et f2), mais une reprise a renvoyé 0 octet |
| Deux serveurs, deux versions | Deux serveurs visibles (`be: f1`/`f2`), même ETag ce jour. Parade : `If-Range` + contrôle du zip |
| Copies divergentes d'un amendement | **Copies confirmées** (346 paires B/BTC). **Divergence non observée** dans l'archive du 03/11 |
| Sort ambigu (état, sous-état) | Confirmé : « Retiré » à deux niveaux, sous-état « R » muet, `sort` vide hors « Discuté » |
| Plusieurs dizaines de cosignataires | Confirmé : jusqu'à 242 ; ≈ 21 400 signatures pour les plus fréquents |
| Identifiant d'orateur faux pour un orateur collectif | Confirmé en XVIIe (PA0 : 603 paragraphes ; repli PA793214 : 13) |
| Paragraphes renumérotés à la republication | Le rang (`ordre_absolu_seance`) change. `id_syceron` tient dans 97-99 % des cas, mais quelques id sont remplacés |
| Président de séance | Confirmé, et aggravé : `roledebat` en manque 55 % |
| **Nouveaux** | dossier `incorrect_data` dans le zip (170 amdts) ; irrecevables sans exposé ni dispositif (23 669) ; `id_acteur` négatifs (315 paragraphes) ; attribution fausse Rufo → Ruffin ; `stime` absent des CR provisoires ; `Last-Modified` des amendements à 15:20 GMT |
