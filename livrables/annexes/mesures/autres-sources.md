# Mesures — sources hors Assemblée nationale, et limites de GitHub

Mesures faites le **04/11/2026 entre 14 h 50 et 15 h 05 UTC**, depuis une connexion
domestique, avec le `User-Agent` `empreinte-mesures/0.1 (mesures ponctuelles)`, au plus deux
requêtes simultanées par hôte.

Légende : **[M]** mesuré, **[C]** calculé à partir de mesures, **[S]** supposé.

Les **temps de téléchargement** et les latences mesurés ici valent pour cette connexion
domestique. Ils **ne valent pas** pour une machine GitHub Actions (réseau différent, autre
région, autres limites de débit).

- Scripts : `travail/scripts/autres-sources/`
- Données téléchargées : `travail/sources/{dila,parltrack,europarl,senat,wikipedia,wikidata,datagouv,economie,eurovoc,sycomore}/`

---

## Synthèse : comment savoir « ce qui a changé depuis la dernière fois »

| Source | ETag | Last-Modified | Content-Length | Accept-Ranges | Mécanisme de détection proposé |
| --- | --- | --- | --- | --- | --- |
| DILA JORF (Apache) | oui | oui | oui | bytes | liste du répertoire : un fichier `JORF_AAAAMMJJ-HHMMSS.tar.gz` par livraison, jamais réécrit → mémoriser le dernier nom traité |
| Parltrack (nginx) | oui | oui | oui | bytes | `ETag`/`Last-Modified` par fichier (HEAD, 3 à 4,7 s chacun) |
| Parlement européen API | **non** | **non** | oui | non | aucun : `Cache-Control: no-cache, no-store` → comparer le contenu (empreinte) |
| Sénat `export_sens.zip` | oui | oui | oui | bytes | `Last-Modified` change **chaque nuit** (régénéré à 03 h 17 UTC) → comparer l'empreinte du SQL décompressé [S : une seule observation] |
| Wikipédia (API) | non | non | — | — | `lastrevid` (prop=info) ou `revid` |
| Wikidata SPARQL | non | non | — | — | aucun ; `Cache-Control: public, max-age=300` → comparer le résultat |
| data.gouv.fr (fichier statique) | oui | oui | oui | bytes | `last_modified` et `url` de la ressource via l'API catalogue, `ETag` du fichier |
| data.gouv.fr API tabulaire | non | non | — | — | aucun ; `created_at` de l'indexation dans `/api/resources/{id}/` |
| data.economie.gouv.fr (ODS) | non | non | — | — | champ `modified` / `data_processed` du catalogue |
| EuroVoc SPARQL | non | non | — | — | aucun (thésaurus quasi stable) |
| Sycomore | non | non | — | bytes | aucun : `Cache-Control: private, max-age=0` |

---

## 1. Journal officiel — DILA (`echanges.dila.gouv.fr/OPENDATA/JORF/`)

### Liste des fichiers [M]

- Page d'index Apache : 151 378 octets, 0,28 s. 887 entrées : 2 PDF de documentation,
  **1 dump global**, **884 livraisons** `JORF_*.tar.gz` (du 13/07/2025 00 h 25 au 04/11/2026 00 h 44).
- **Dump global** `Freemium_jorf_global_20250713-140000.tar.gz` (HEAD) : `Content-Length`
  **1 674 608 486** octets, `Last-Modified: Sun, 13 Jul 2025 08:51:50 GMT`,
  `ETag: "63d07f66-639cba767b580"`, `Accept-Ranges: bytes`. Toujours un seul dump global :
  confirmé.
- **Rythme : deux livraisons par jour**, y compris samedi et dimanche, et parfois une
  troisième à midi (15/10 et 21/10/2026) :
  - une livraison **du soir** (≈ 19 h 50–20 h 50 UTC) : 2,0 à 6,1 Mo ;
  - une livraison **de nuit** (≈ 22 h 20–00 h 00 UTC) : 63 à 395 Ko.
- Livraisons par mois : 53 à 62 (octobre 2026 : 62).
- **Jours sans livraison** depuis le 13/07/2025 : 8 seulement (14/07/2025, 16/08/2025,
  02/11/2025, 25/12/2025, 06/04/2026, 01/05/2026, 09/05/2026, 16/08/2026). **Aucun trou en
  octobre 2026** : la « panne de trois jours en octobre 2026 » du cahier (§ 3.6) ne se voit pas
  dans les livraisons. Elle concernait donc le serveur, et les livraisons ont été déposées
  avec leur date normale, ou rattrapées [S].

### Les 30 derniers jours (05/10 → 04/11/2026) [M] (`dila_head.py`, `sources/dila/head_30j.json`)

- **59 livraisons**, total **130 524 476 octets** (≈ 130,5 Mo), minimum 63 365, médiane
  2 078 675, maximum 6 114 248 octets.
- Latence d'un HEAD : médiane 0,029 s.
- En-têtes d'une livraison : `Last-Modified`, `ETag`, `Content-Length` et
  `Accept-Ranges: bytes` sont tous présents.
- [C] ≈ 4,4 Mo/jour compressés, soit ≈ 1,6 Go/an de livraisons si l'on gardait tout.

### Trois livraisons téléchargées [M] (`dila_livraison.py`)

| Livraison | Compressé | Téléchargement | Fichiers | Décompressé | `texte/version` (actes) | Lecture en flux |
| --- | --- | --- | --- | --- | --- | --- |
| `JORF_20261102-213929` (soir) | 4 960 186 o | 6,96 s | 5 930 | 54,1 Mo | 169 | 1,68 s |
| `JORF_20261103-214151` (soir) | 3 077 137 o | 3,39 s | 2 408 | 38,9 Mo | 113 | 1,36 s |
| `JORF_20261104-004428` (nuit) | 115 897 o | 1,26 s | 404 | 0,95 Mo | 91 | 0,05 s |

- Lecture des trois en flux (`tarfile` mode `r|gz` + lxml) : **3,15 s au total**,
  **146 Mo de mémoire de pointe** (`/usr/bin/time -v`).
- Arborescence : `<horodatage>/jorf/global/{conteneur,texte/struct,texte/version,section_ta,article}/JORF/<TYPE>/00/00/55/04/72/JORF<TYPE>000055047268.xml`.
  Un acte = un `JORFTEXT…` en double (`texte/struct` pour le plan, `texte/version` pour les
  métadonnées et les liens) + ses `JORFARTI` (articles) + ses `JORFSCTA` (sections) ; les
  `JORFCONT` sont les sommaires du JO.
- Aucun fichier non XML dans les trois livraisons : **pas de liste de suppressions** vue.
- Champs de `texte/version` (exemple `JORFTEXT000055040950`, arrêté, NOR `CPTP2620897A`,
  ministère « Premier ministre », publié le 2026-11-01) :
  `META_COMMUN/{ID, ID_ELI, NATURE}`, `META_TEXTE_CHRONICLE/{CID, NUM, NUM_PARUTION, NOR,
  DATE_PUBLI, DATE_TEXTE, ORIGINE_PUBLI}`, `META_TEXTE_VERSION/{TITRE, TITREFULL, MINISTERE,
  AUTORITE, LIENS/LIEN[@typelien,@sens,@naturetexte,@cidtexte,@numtexte,@datesignatexte]}`,
  puis `VISAS`, `SIGNATAIRES`, `TP`, `NOTICE`, `ABRO`, `RECT`, `SM`, `ENTREPRISE`.
- Natures (livraison du 02/11 soir) : ARRETE 95, DECRET 48, LOI 20, ORDONNANCE 3,
  DELIBERATION 2, DECISION 1. Livraison de nuit du 04/11 : ARRETE 46, DECRET 15, AVIS 12,
  INFORMATIONS_PARLEMENTAIRES 12, DECISION 5, ANNONCES 1.
- NOR vide : 10/169, 8/113, 1/91. MINISTERE vide : 28/169, 29/113, 20/91. Les lois n'ont
  pas de ministère (exemple `JORFTEXT000055047268`, loi n° 2026-1015, ministère vide).
- Types de liens (livraison du 02/11 soir, 169 actes) : CITATION 95 222, CODIFICATION
  17 734, CREATION 3 866, **APPLICATION 4 522**, ABROGATION 2 483, TXT_SOURCE 1 276,
  MODIFIE 317, TXT_ASSOCIE 159, ABROGE 123, SPEC_APPLI 75, MODIFICATION 44, TRANSPOSITION 25,
  RECTIFICATION 11, CONCORDANCE 3. Liens vers une `naturetexte="LOI"` : 1 025.
  La livraison de nuit ne porte **que des CITATION « source »** (204) : les liens riches
  arrivent plus tard, dans les livraisons du soir.

### Pièges du cahier (§ 3.6)

| Piège | Verdict | Preuve |
| --- | --- | --- |
| Un seul dump global (13/07/2025, 1,67 Go) | **confirmé** | HEAD : 1 674 608 486 o, `Last-Modified` 13/07/2025 |
| Textes anciens redélivrés : filtrer par date de publication | **confirmé, et massif** | livraison du 02/11 soir : **134 actes sur 169** publiés avant le 01/10/2026 (ex. `JORFTEXT000044394397`, décret 2021-1550 publié le 02/12/2021) ; du 03/11 soir : 66/113. La livraison de nuit ne contient que des actes du jour (91/91 publiés le 04/11). Un même acte revient d'une livraison à l'autre (`JORFTEXT000051538879` dans celles du 02/11 et du 03/11) → la dernière version reçue d'un `ID` remplace la précédente |
| Dates sentinelles `2999` | **confirmé** | `DATE_TEXTE = 2999-01-01` sur 28 actes publiés le 03 ou le 04/11/2026 (ex. `JORFTEXT000055053883`) ; `debut/fin="2999-01-01"` partout dans `texte/struct` |
| « applique » plus posé depuis 2024 | **confirmé sur l'échantillon** | 0 lien `APPLICATION` de sens « cible » sur les lois publiées depuis 2025 présentes dans les trois livraisons (ex. `JORFTEXT000053508155`, loi de finances 2026, 134 liens dont 0 APPLICATION). Le type existe toujours ailleurs (4 522 liens dans une livraison, sur des textes plus anciens) |
| Une loi a parfois deux enregistrements | **confirmé** | loi 2025-391 : `JORFTEXT000051538879` (02/05/2025) et `JORFTEXT000051575460` (10/05/2025) ; loi 2025-1403 : `JORFTEXT000053226384` et `JORFTEXT000054125097` |
| Libellé de ministère en texte libre | confirmé (non dénombré ici) | « Premier ministre », « Ministère de l'intérieur »… |
| **« Le signataire n'est jamais publié »** | **INFIRMÉ, avec nuance** | `SIGNATAIRES` est rempli pour 153/169, 94/113 et 48/91 actes. C'est un **bloc de texte libre** (HTML), pas un champ structuré : ex. `JORFTEXT000055037137` : « Fait le 28 octobre 2026. Sébastien LECORNU Par le Premier ministre : Le ministre de l'intérieur, Laurent NUNEZ La ministre de l'aménagement du territoire et de la décentralisation, Françoise GATEL… ». Un rattachement acte → personne est donc possible par analyse de texte (noms en capitales + fonction), avec les risques d'une extraction. Le contrôle du cahier (« champ vide sur 380 décrets ») a dû porter sur un autre champ (`AUTORITE`, vide partout ici) [S] |
| Panne de trois jours en octobre 2026 | **non visible** dans les livraisons | aucun jour manquant en octobre 2026 dans l'index |

### Dump global : non téléchargé

- Débit mesuré sur une plage de 30 Mo (requête `Range`, HTTP 206) : **0,93 Mo/s** au
  premier essai, **0,33 Mo/s** au second (en parallèle d'autres téléchargements) [M].
- [C] 1,67 Go à ce débit = **30 à 85 minutes**, au-delà des 15 minutes autorisées → HEAD
  seulement, comme prévu par la consigne.
- Échantillon : les 30 premiers Mo, lus en flux (`dila_global_partiel.py`), donnent
  **26 986 fichiers**, tous des sommaires (`conteneur`), et 181 Mo décompressés, en 1,7 s.
  L'archive commence par tous les `conteneur`, puis viennent les textes. L'échantillon ne
  permet pas d'extrapoler le nombre total de fichiers.
- `Accept-Ranges: bytes` : une reprise de téléchargement interrompu est possible.

---

## 2. Parltrack (`parltrack.org/dumps/`)

### Accès [M]

- **`https://parltrack.org/dumps` (sans barre finale) et `https://parltrack.org/` :
  HTTP 502 Bad Gateway** (nginx) le 04/11/2026 à 14 h 52 UTC. **`https://parltrack.org/dumps/`
  (avec barre finale) répond 200**, et les fichiers aussi. L'adresse donnée par le cahier
  échoue.
- HEAD d'un fichier : **3,0 à 4,7 s** (lent). Débit de téléchargement ≈ 0,5 Mo/s.

### Fichiers `ep_*.json.zst` (HEAD, 04/11/2026) [M]

| Fichier | Taille | Last-Modified | ETag |
| --- | --- | --- | --- |
| `ep_amendments.json.zst` | 119 965 785 | **03/02/2026** 01:37 | `"69815155-7268859"` |
| `ep_com_votes.json.zst` | 28 779 | 24/07/2026 00:56 | `"6a62b859-706b"` |
| `ep_comagendas.json.zst` | 1 293 603 | **28/02/2026** 00:36 | `"69a23879-13bd23"` |
| `ep_dossiers.json.zst` | 55 253 515 | 24/07/2026 01:02 | `"6a62b98c-34b1a0b"` |
| `ep_mep_activities.json.zst` | 49 746 437 | 24/07/2026 01:04 | `"6a62ba2e-2f71205"` |
| `ep_meps.json.zst` | 9 357 470 | 24/07/2026 00:34 | `"6a62b321-8ec89e"` |
| `ep_plenary_amendments.json.zst` | 7 047 700 | 24/07/2026 00:57 | `"6a62b87c-6b8a14"` |
| `ep_votes.json.zst` | 11 252 459 | **28/03/2026** 00:40 | `"69c7238b-abb2eb"` |

- [C] Total des `ep_*.json.zst` : **253 945 748 octets** (≈ 254 Mo).
- Tous portent `ETag`, `Last-Modified`, `Content-Length` et `Accept-Ranges: bytes`.
- Le répertoire contient aussi d'anciens formats (`.json.lz`, `ep_amendments.json` non
  compressé de 1,4 Go daté du 15/07/2024) : il faut nommer les fichiers explicitement.

### Surprise : Parltrack ne se met plus à jour

- **Aucun fichier n'a été modifié depuis le 24/07/2026** (plus de trois mois). `ep_votes`
  est figé depuis le **28/03/2026** : son scrutin le plus récent date du
  **26/03/2026 11:40:25** ; `ep_amendments` depuis le 03/02/2026. Dans `ep_meps`, le champ
  `meta.updated` le plus récent est le 2026-07-24T00:32:55.
- **« Seuls les trois derniers jours sont conservés » : INFIRMÉ.** Le dossier
  `https://parltrack.org/dumps/arch/` garde **3 492 instantanés `.zst`** plus d'anciens
  `.lz`, depuis 2019 : 966 de `ep_meps`, 957 de `ep_dossiers`, 236 de `ep_votes`, etc. Le
  dernier est daté du 23/07/2026 (`ep_plenary_amendments-2026-07-23.json.zst`).
  Les instantanés successifs sont souvent identiques en taille : `ep_plenary_amendments`
  fait 7 047 700 octets du 30/06 au 23/07/2026.
- Le chiffre « 44 648 scrutins » du cahier est **exactement** celui du fichier actuel : le
  fichier n'a pas changé depuis la mesure du cahier.

### Lecture en flux (zstandard + lecture ligne à ligne + orjson) [M] (`parltrack_flux.py`)

| Fichier | Objets | Décompressé | Ligne la plus longue | Durée | Mémoire de pointe |
| --- | --- | --- | --- | --- | --- |
| `ep_meps` | **4 603** eurodéputés (645 avec une circonscription « France ») | 210 473 451 o | 863 763 o | 2,28 s | 37,9 Mo |
| `ep_votes` | **44 648** scrutins (2004 → 26/03/2026) | 649 767 256 o | 159 158 o | 8,01 s | 28,4 Mo |

- Téléchargements : `ep_meps` 18,7 s, `ep_votes` 23,6 s.
- Format confirmé : `[` puis `{…}` sur la première ligne, `,{…}` sur les suivantes, `]`
  seul à la fin.
- **Deux formes d'identifiant de scrutin : confirmé.** `voteid` est un entier dans 40 230
  cas (ex. `7754`) et une chaîne dans 4 418 cas (ex. `"2017-12-12 00:00:00-1."`).
- 92 scrutins n'ont pas de clé `votes` ; 5 710 n'ont pas de `doc` (« des scrutins sans
  référence de dossier » : confirmé).
- Scrutins par année : 212 en 2004 … 5 213 en 2021, 2 891 en 2025, 838 en 2026 (jusqu'au
  26/03).
- La position d'un eurodéputé est `{"mepid": 28268}` dans `votes["+"].groups["ALDE"]` : le
  scrutin porte la liste des votants (lecture scrutin → personnes).

---

## 3. Parlement européen (`data.europarl.europa.eu/api/v2/`) — 13 requêtes [M] (`europarl.py`, `sources/europarl/log.json`)

| Requête | HTTP | Durée | Taille | `data` |
| --- | --- | --- | --- | --- |
| `meps?parliamentary-term=10&offset=0&limit=50` | 200 | 0,22 s | 7 870 o | liste de 50 |
| idem `offset=50` | 200 | 0,05 s | 7 992 o | liste de 50 |
| `meps?parliamentary-term=7&limit=5` | **200** | **7,66 s** | 888 o | liste de 5 |
| `meps/show-current?country-of-representation=FR&limit=100` | 200 | 0,04 s | 17 998 o | liste de **81** |
| `meps/131580` (Jordan Bardella) | 200 | 0,04 s | 10 989 o | **liste d'un élément** |
| `meps/197533` (Manon Aubry) | 200 | 0,04 s | 16 563 o | liste d'un élément |
| `meps/999999999` (inventé) | 404 | 1,95 s | 0 o | — |
| `adopted-texts?year=2025&limit=5` | 200 | 0,93 s | 171 915 o | liste de 5, plus `meta.total = 347` et `searchResults` |
| `corporate-bodies?limit=5` | 200 | 0,65 s | 825 o | liste de 5 |
| `meps/131580` (2ᵉ fois) | 200 | 0,04 s | 10 989 o | identique |
| `corporate-bodies/7150?language=fr` | 200 | 0,17 s | 561 o | liste d'un élément (« Groupe Patriotes pour l'Europe ») |
| `meps?parliamentary-term=9&limit=1000` | 200 | **3,01 s** | 140 103 o | **875** eurodéputés en une page |
| `meps?parliamentary-term=10&offset=900&limit=100` | **204** | 0,26 s | **0 o** | — |

- **En-têtes** : ni `ETag` ni `Last-Modified`, `Cache-Control: no-cache, no-store, max-age=0,
  must-revalidate`, aucun en-tête de limitation de débit. **Aucune détection de changement
  côté serveur.**
- **Pagination** : `offset`/`limit`, sans lien « suivant » ni total (sauf `meta.total` sur
  `adopted-texts`). **La fin de pagination est une réponse 204 sans corps**, pas une liste
  vide. Or le cahier décrit une limitation « muette sans erreur » : un client qui s'arrête au
  premier corps vide ne distingue pas une vraie fin (204) d'une limitation silencieuse.
  Il faut compter les éléments reçus et les comparer au palier attendu.
- **Forme de `data`** : sur 12 réponses JSON, `data` est **toujours une liste**, y compris pour
  une personne seule. La forme « objet » du cahier n'a pas été revue ici, mais elle reste
  possible sur d'autres points d'accès ; le code doit la gérer.
- **VIIe législature** : `meps?parliamentary-term=7` répond **200** (lent : 7,66 s). Le
  « 404 » du cahier ne vaut donc pas pour ce point d'accès. Il a pu concerner un autre point
  d'accès [S].
- **Silence ou limitation** : rien observé sur 13 requêtes espacées de 1,5 à 2 s.
- **Latence** : 0,04 à 0,2 s pour la plupart des requêtes depuis ici, mais 1,95 s (404),
  3,0 s (875 eurodéputés) et 7,66 s (législature 7). Le cahier mesurait 1,8 à 3,5 s par
  requête depuis un serveur d'intégration ; les deux ne se comparent pas.
- **Mandats de Jordan Bardella** (`meps/131580`, 04/11/2026) : **23 `hasMembership`**.
  Chacun porte une `organization` qui est **une référence** (`org/7150`) ; le libellé
  demande une requête de plus (`corporate-bodies/7150`). Il porte aussi un `role`, une
  `membershipClassification` et une période `memberDuring{startDate,endDate}`.
  - Mandat au Parlement : `org/ep-9` `MEMBER_PARLIAMENT` du 02/07/2019 au 15/07/2024,
    `org/ep-10` depuis le 16/07/2024, avec `represents` = `…/country/FRA`.
  - Groupe : `org/5588` MEMBER (2019-2024), puis `org/7150` (Patriotes pour l'Europe) avec le
    rôle CHAIR du 16/07/2024 au 19/10/2026 et **CHAIR_CO depuis le 20/10/2026**. Ce
    changement de rôle date de deux semaines : un changement de fonction se lit comme une
    nouvelle appartenance.
  - Parti national : `NATIONAL_POLITICAL_GROUP` `org/5494` puis `org/6848`.
  - Le reste : commissions, délégations, groupes de travail.
  - Deux entrées n'ont pas de `membershipClassification` (celles du mandat de député
    européen).
- 81 eurodéputés « en cours » pour la France ; chaque entrée donne `api:political-group`
  (ex. `person/124760` Nicolas BAY, ECR).

---

### Votes nominatifs, interventions et mandats des candidats (13/11/2026) [M]

Une requête toutes les 2,1 s (`robots.txt` du portail : `Crawl-delay: 2`, `/api/` autorisé).

- **Séances** (`meetings?year=AAAA`) : 47 à 59 séances plénières par an de 2014 à 2026 ; aucune
  avant 2014 (réponse 204 pour 2005, 2010 à 2013). Une liste annuelle prend de 0,4 à 13 s.
- **Décisions** (`meetings/<séance>/decisions`) : chaque vote nominatif porte les listes
  `had_voter_favor`, `had_voter_against`, `had_voter_abstention` (et
  `had_voter_intended_abstention`) en `person/<id>`, le résultat (`decision_outcome`), le
  document voté (`decided_on_a_realization_of`, par exemple `A-10-2025-0272-AM-247`), le
  numéro de vote. Échantillon de 4 séances par an : **aucune décision de 2014 à 2018** (404) ;
  2019 : la séance du 28/03/2019 a 93 votes « nominatifs » avec **un seul votant distinct**
  (inutilisables) ; à partir de la législature ouverte en juillet 2019, des listes réelles
  (19/09/2019 : 673 votants distincts, 653 par vote en médiane). Un 404 tombe sur un lundi
  (jour sans vote) ou une séance à venir.
- **Glucksmann** (`person/197694`) vote dans 63 des 67 votes nominatifs du 20/01/2026, 222 des
  225 du 28/04/2026, 144 des 152 du 21/10/2026 ; 0 des 69 du 11/09/2025 (absent ce jour-là).
- **Interventions** (`speeches?person-id=`) : aucune pour Mélenchon (`96742`) ni Le Pen
  (`28210`) ; le filtre `year` paraît ignoré (une requête « 2025 » rend des interventions de
  2023).
- **Mandats** (`meps/<id>`) : toutes les législatures, avec dates : Le Pen `ep-6` à `ep-8`
  (20/07/2004 → 18/06/2017), Mélenchon `ep-7` et `ep-8` (14/07/2009 → 18/06/2017), Philippot
  `ep-8` (01/07/2014 → 01/07/2019).
- **Candidats anciens eurodéputés** (identifiant européen P1186 déclaré par Wikidata sur les 33
  éléments de la liste du 13/11/2026) : Mélenchon, Le Pen, Glucksmann, Philippot (déclarés),
  Maurel, Massard (retirés).

## 4. Sénat (`data.senat.fr`) [M]

### `export_sens.zip`

- HEAD : 200, 0,21 s, **`Content-Length: 8 577 088`**,
  `Last-Modified: Wed, 04 Nov 2026 03:17:18 GMT`, `ETag: "1c05a-82e040-65f6ad101eb80"`,
  `Accept-Ranges: bytes`, un cookie de répartiteur de charge (`BIGipServer…`).
- Téléchargement : 2,44 s. Contenu : **un seul fichier `export_sens.sql`** (dump PostgreSQL,
  `client_encoding = 'UTF8'`) de **60 264 053 octets**, horodaté du 04/11/2026 04:16.
- **95 tables** (`CREATE TABLE`), et non 93 comme dans le cahier.
  - Lignes les plus nombreuses : `activite_participant` 683 522, `activite` 43 194,
    `fonmemgrpsen` 39 845, `memgrpsen` 32 576, `elutit` 30 802, `fonmemcom` 21 246,
    `memcom` 17 883, `activite_senateur` 11 192, `activite_loi` 5 369, `mandat_local` 5 366,
    `memextpar` 4 537, `sen` 2 015.
- Le fichier est régénéré chaque nuit : `Last-Modified` à 03 h 17 UTC le jour même. Si
  l'`ETag` change chaque nuit même quand le contenu ne change pas [S : une seule
  observation], il ne sert pas à détecter un changement : il faut comparer une empreinte du
  contenu.

### Tables de présence et de participation (règle éditoriale 3) — **confirmé**

- `activite` : 43 194 réunions (séance plénière, commissions, CMP, délégations, groupes
  d'études…), avec `nb_participants`, de 2015 à 2026 (plus 9 dates en l'an **0015** et
  quelques-unes entre 2001 et 2014).
- **`activite_participant`** : **683 522 lignes**, une par sénateur et par réunion, avec
  `typactparcod` ∈ {**PRESENT** : 657 536, **EXCUSE** : 25 986} et `teleparticipation`.
  C'est un **registre de présence individuel** : la règle 3 interdit d'en tirer un taux.
- `activite_senateur` : 11 192 lignes d'agenda individuel (réunions avec le Gouvernement,
  élus locaux, cérémonies…).
- Types associés : `type_activite`, `type_activite_participant`, `type_activite_senateur`,
  `fonact_participant`.
- → À exclure dès l'ingestion, par une liste blanche des tables chargées : le moyen le plus
  simple de tenir la règle 3 par construction.

### CSV ODSEN

- `ODSEN_GENERAL.csv` : 443 305 octets, 0,34 s, `Last-Modified` identique à celui de
  l'export (régénéré à la même heure), `ETag` présent.
- **Encodage ISO-8859-1 (latin-1) : confirmé.** Le fichier n'est pas de l'UTF-8 valide
  (octet `0xEA` dès la position 6), contient 8 185 octets > 0x7F et a des fins de ligne
  **CRLF**.
- **18 lignes de commentaire préfixées par `%`** (la requête SQL source, puis
  « 2012 ligne(s) de résultat ») avant l'en-tête : confirmé.
- Contraste : l'export SQL, lui, est en **UTF-8**.
- Le CSV ne compte que 2 012 sénateurs (états ACTIF et ANCIEN), contre 2 015 lignes dans la
  table `sen`.

### Identifiant Sénat et Wikidata

- **P1808 (Wikidata) n'est pas le matricule** : c'est le chemin de l'adresse de la fiche,
  ex. `senateur/melenchon_jean_luc86039k` (Q5829) et `senateur/retailleau_bruno04033b`
  (Q2926942).
- Le matricule du Sénat (`sen.senmat`, ex. `86039K`, `04033B`) se lit **à la fin, en
  minuscules**. La correspondance est vérifiée dans la table `sen` pour ces deux personnes.

---

## 5. Wikipédia fr — « Candidatures à l'élection présidentielle française de 2027 » [M] (`wikipedia.py`, `wikipedia2.py`, `wikipedia_candidats.py`)

- Un appel avec des caractères UTF-8 non encodés dans l'adresse (curl brut) renvoie
  **HTTP 400 « Invalid HTTP Request »** : il faut encoder le titre (requests le fait).
- `action=query&prop=info|revisions|pageprops` : 200, 511 octets, 0,25 s.
  - `pageid` **17573391**, `lastrevid` **240980797** (2026-11-03T12:05:06Z),
    `parentid` 240980631, `length` **128 863** octets, `sha1` `56b9b464…`.
  - **Détection d'un changement** : comparer `lastrevid`, une requête de 511 octets.
  - Pas d'`ETag`, `Cache-Control: private, must-revalidate, max-age=0`.
  - `pageprops` de l'article : pas de `wikibase_item`.
- Sections (`action=parse&prop=sections`, 0,19 s) : 1 « Candidats déclarés », 2
  « Candidats pressentis », 3 « Élection primaire » (4 « Primaire socialiste »), 5
  « Candidatures retirées », 6 « Candidats pressentis ayant décliné » (7 à 12 par
  sensibilité), 13 à 15 notes et références, 16 « Voir aussi ».
- Section 1 (`action=parse&section=1&prop=wikitext|links`) : 90 803 octets, 1,41 s, 73 015
  caractères de wikitexte, 196 liens d'articles.
- **Structure** : un tableau `wikitable sortable`, une ligne par candidat. **Le nom est dans
  la cellule d'en-tête de ligne**, sous des formes variables :
  - `! {{TriNom|Nathalie|Arthaud}}` — cas général ;
  - `!{{TriNom|Olivier|Becht}}` — sans espace ;
  - `![[Raphaël Glucksmann]]` et `![[Natacha Polony]]` — lien direct, sans TriNom ;
  - `{{TriNom|Selma|Labib|nolink=oui}}` — **sans article**, 5 cas : Selma Labib,
    Mira Markovic, Benoît Mathieu, Manolo Mlekuz, Gilles Platret.

  L'âge se lit tantôt `({{Âge|23|02|1970|18|04|2027}})`, tantôt `(48 ans)` en clair ; le mois
  est parfois en lettres (`{{Âge|23|août|1986|…}}`). Le parti suit, en lien.
- **Résultat à la révision 240980797 : 29 candidats déclarés** (pas 30). 24 ont un article,
  et **les 24 ont un identifiant Wikidata** via `prop=pageprops&ppprop=wikibase_item`
  (4 requêtes de 50 titres, 0,14 à 0,17 s chacune). Exemples : Nathalie Arthaud `Q439490`,
  Marine Le Pen `Q12927`, Jean-Luc Mélenchon `Q5829`, Édouard Philippe `Q3579995`.
  - Liste : `sources/wikipedia/candidats.json`.
  - Expression régulière utilisée : `^!\s*(\{\{TriNom\|P\|N(\|nolink=oui)?\}\}|\[\[Titre\]\])`.
  - L'extraction est **propre mais fragile** : elle dépend de conventions de rédaction
    (TriNom, `nolink`) que n'importe quel contributeur peut changer. Un contrôle « nombre de
    candidats extrait = nombre de lignes du tableau » s'impose.
  - Le titre reconstitué « Prénom Nom » peut tomber sur une page d'homonymie : c'est à
    vérifier par `pageprops` (`disambiguation`).

---

## 6. Wikidata SPARQL (`query.wikidata.org/sparql`) [M] (`wikidata.py`)

| Requête | Résultat | Durée |
| --- | --- | --- |
| Entités ayant **P4123** (identifiant Assemblée) | **2 456** entités, 2 461 valeurs | 0,25 s |
| Entités ayant P1045 (Sycomore) | 18 060 entités, 18 062 valeurs | 0,24 s |
| Entités ayant P1808 (Sénat) | 4 829 entités, 5 198 valeurs | **12,89 s** |
| P4123/P1045/P1808 pour les 24 candidats (`VALUES`) | 24 lignes, 7 937 o | 0,23 s |
| Même requête simplifiée, 2ᵉ fois | 3 855 o | 0,14 s |

- En-têtes : `Cache-Control: public, max-age=300`, ni `ETag` ni `Last-Modified`.
- Sur les 24 candidats : **13 ont P4123**, **13 ont P1045**, **2 ont P1808**.
  - Avec P4123 : Mélenchon 2150, Le Pen 720614, Dupont-Aignan 1206, Bertrand 267080, Batho
    335999, Cazeneuve 785, Retailleau 2538, Ruffin 722142, Philippe 345619, Attal 722190,
    Becht 642935, Roussel 720692.
  - Sans P4123 alors qu'ils ont siégé au Palais-Bourbon : à vérifier [S].
  - Valeurs **sans préfixe `PA`** : confirmé.
- Une valeur P4123 peut être **courte** (`785`, `1206`, `2150`) : ce sont les identifiants
  anciens de l'Assemblée.
- Le service de libellés a renvoyé « Q5829 » au lieu de « Jean-Luc Mélenchon » pour
  l'étiquette française. C'est peut-être passager ; il ne faut pas compter sur les libellés
  Wikidata.
- **P1808** est un chemin d'adresse (voir § 4), pas un matricule.

---

## 7. data.gouv.fr (Répertoire national des élus), data.economie.gouv.fr, EuroVoc [M]

### Répertoire national des élus (`datagouv.py`, `datagouv_tab.py`, `datagouv_tab2.py`)

- Jeu `5c34c4d1634f4173183a64f1` (`repertoire-national-des-elus-1`, ministère de
  l'Intérieur, licence `lov2`, fréquence `quarterly`, dernière mise à jour le 11/08/2026).
  Recherche par l'API catalogue : 0,69 s.
- **12 ressources** (identifiant, taille), au 04/11/2026 :
  - `d5f400de-ae3f-4966-8cb6-a85c70c6c24a` conseillers municipaux, **65 305 658 o** ;
  - `41d95d7d-…` conseillers communautaires, 9 952 941 o ;
  - `2876a346-…` maires, 4 257 507 o ;
  - `601ef073-…` conseillers départementaux, 534 173 o ;
  - `430e13f9-…` conseillers régionaux, 219 488 o ;
  - `3b6b2281-…` conseillers d'arrondissement, 153 450 o ;
  - `a595be27-…` membres d'assemblée, 86 092 o ;
  - `84949a7b-…` conseillers des Français de l'étranger, 80 448 o ;
  - `1ac42ff4-…` députés, 73 423 o ;
  - `b78f8945-…` sénateurs, 34 586 o ;
  - `41cea915-…` Assemblée des Français de l'étranger, 10 897 o ;
  - `70957bb0-…` eurodéputés, 6 581 o.

  [C] **Total ≈ 80,7 Mo**, dont 65,3 Mo pour le seul fichier municipal (le cahier dit
  « 76 Mo » pour le fichier complet).
- L'adresse de chaque fichier contient un horodatage de publication
  (`…/20260811-154802/elus-conseiller-municipal-cm.csv`). Une adresse stable existe :
  `https://www.data.gouv.fr/fr/datasets/r/<id_ressource>` (301 vers l'API). Elle ne vaut que
  tant que l'identifiant de ressource ne change pas : le cahier dit qu'il change à chaque
  publication, ce qui ne se vérifie pas en une seule observation.
- Fichier statique (HEAD) : `Content-Length: 65305658`, `ETag` (MD5), `Accept-Ranges: bytes`,
  `cache-control: max-age=2592000`. Son `Last-Modified` (**21/10/2026**) **ne correspond
  pas** à la date de la ressource dans le catalogue (11/08/2026) : l'objet a été retouché
  après publication. Il faut se fier à l'empreinte.
- **API tabulaire** (`tabular-api.data.gouv.fr/api/resources/<id>/`) :
  - métadonnées : 0,16 s, `created_at` 2026-10-28 (date d'indexation) ;
  - `/profile/` : 0,02 s, 16 colonnes ;
  - `/data/?page_size=…` : **511 225 lignes** de conseillers municipaux, 0,17 à 0,37 s par
    page ;
  - filtre exact `Nom de l'élu__exact=TONDELIER` : 0,90 s, 1 ligne ; deux filtres combinés :
    0,59 s ;
  - filtre `Date de naissance__less=1910-01-01` : 0,40 s, **8 lignes**, dont **1072-03-05**
    (MARTINEZ, Massieux) et plusieurs **1900-01-01** (date sentinelle). Les années de
    naissance aberrantes : **confirmé**.
  - pagination par `page`/`page_size` avec `links.next` ; ni `ETag` ni en-tête de limitation ;
    pas d'erreur 504 ni 429 sur 8 requêtes espacées.
  - Colonnes : `Nom de l'élu`, `Prénom de l'élu`, `Date de naissance`, `Code sexe`,
    `Code de la commune`, `Date de début du mandat`, `Libellé de la fonction`,
    `Date de début de la fonction`… **Aucun identifiant de personne ni date de fin de
    mandat** : confirmé.

### data.economie.gouv.fr (Opendatasoft v2.1) (`economie.py`)

- Catalogue `situation mensuelle` : 0,19 s. En-têtes : **`X-RateLimit-Limit: 50000`** par
  jour, `X-RateLimit-Remaining`, `X-RateLimit-Reset: 2026-11-05 00:00:00+00:00`,
  `Cache-Control: public, max-age=300`, pas d'`ETag`.
- Le nom d'un champ inconnu dans `select` renvoie un 400 explicite (`ODSQLError`).
- `situation-mensuelle-de-l-etat` (modifié le 30/10/2026) : **213 enregistrements**. Ce sont
  des **liens vers des PDF** (ex. `sme_2025-12_provisoire.pdf`), pas des chiffres.
- `situations-mensuelles-budgetaires-series-longues` (titre : « exercices 2013 à nos
  jours », modifié le **04/11/2026 à 10 h 38**) : 26 lignes au **format large**. Une colonne
  par fin de mois, **33 colonnes de `31_01_2024` à `30_09_2026` seulement** : l'API ne sert
  pas 2013-2023, contrairement au titre. Le schéma gagne une colonne chaque mois : nouveau
  piège pour un modèle à colonnes fixes.
  - Exemple : « Solde budgétaire » au 31/12/2024 = −155 929 972 365,41.
- Détection d'un changement : `modified` / `data_processed` dans le catalogue.

### EuroVoc SPARQL (`eurovoc.py`)

- Libellé français, microthésaurus et domaine de trois concepts (1474, 4038, 5181) :
  **0,25 s** puis **0,07 s** (deux fois la même requête), 2 600 octets.
  - Ex. `4038` « Commission européenne » → microthésaurus « 1006 institutions de l'Union
    européenne… » → domaine « 10 UNION EUROPÉENNE ».
  - Ex. `5181` « protection des données » → « 3231 information et traitement de
    l'information » → « 32 ÉDUCATION ET COMMUNICATION ».
- Piège : `skos:inScheme` renvoie aussi le schéma global `100141` « EuroVoc ». Il faut
  l'exclure pour ne garder que le microthésaurus.
- Ni `ETag` ni `Last-Modified`, ni `Cache-Control`.

---

## 8. Sycomore — une page [M]

- `https://www2.assemblee-nationale.fr/sycomore/fiche?num_dept=19278` (Jean-Luc Mélenchon,
  identifiant tiré de Wikidata P1045) : 200, **39 933 octets**, 0,94 s, sans redirection,
  UTF-8.
- En-têtes : `cache-control: max-age=0, must-revalidate, private`,
  `x-cacheable: Not cacheable: private`, `accept-ranges: bytes`, **ni `ETag` ni
  `Last-Modified`**, servi par un CDN (`x-cdn-pop: rbx`).
- Structure : `h1` (nom), puis des `dl` faits de paires `dt`/`dd` :
  - « Informations générales » / « Né le 19 août 1951 à Tanger ( - Maroc) » ;
  - une section `h2` « Mandats à l'Assemblée nationale… » : Régime, Législature, Mandat
    (« Du 21 juin 2017 au 21 juin 2022 »), Département, Groupe ;
  - une section `h2` « Mandats au Sénat ou à la Chambre des pairs » : « du 2 octobre 1986
    au 1 octobre 1995 »…
- Les dates sont en **français en toutes lettres**, avec une casse variable (« Du » / « du »)
  et « 1 octobre », pas « 1er ».
- Pas de fonction ministérielle, comme le dit le cahier.

---

## 9. GitHub — documentation officielle

Lue le **04/11/2026** en Markdown, par
`https://docs.github.com/api/article/body?pathname=/en/<chemin>` (le même contenu que la
page `https://docs.github.com/en/<chemin>`).

### GitHub Pages

Pages lues :
[github-pages-limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits),
[using-custom-workflows-with-github-pages](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages),
[configuring-a-publishing-source…](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site).

- **« Published GitHub Pages sites may be no larger than 1 GB »** : c'est une **limite**,
  pas une recommandation, contrairement à ce que dit le cahier (§ 5.2). Le dépôt source a
  une limite **recommandée** de 1 Go.
- Un déploiement échoue s'il dépasse **10 minutes** (« deployments will timeout »).
- Bande passante : limite **souple** de **100 Go par mois**.
- Limite souple de **10 builds par heure**, qui **ne s'applique pas** si le site est construit
  et publié par un workflow Actions personnalisé.
- Une limitation de débit est possible : HTTP **429**.
- Déploiement par artefact : `actions/upload-pages-artifact@v4` produit une archive gzip
  contenant **un seul tar de moins de 10 Go**, sans lien symbolique ni physique.
  `actions/deploy-pages@v4` exige les permissions `pages: write` et `id-token: write`, un
  `needs` vers la tâche de construction et l'environnement `github-pages`.
- **Atomicité** : **la documentation lue n'en dit rien.** Le terme « atomic » n'apparaît dans
  aucune des pages lues. Le modèle (un artefact entier remplace le site) le laisse supposer,
  mais c'est une hypothèse [S].
- **Git LFS ne peut pas servir de source à un site GitHub Pages** (note de la page Git LFS).

### GitHub Actions (dépôt public, machine standard)

Pages lues :
[actions/reference/limits](https://docs.github.com/en/actions/reference/limits),
[runners/github-hosted-runners](https://docs.github.com/en/actions/reference/runners/github-hosted-runners),
[dependency-caching](https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching),
[events-that-trigger-workflows](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows),
[workflow-syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax),
[billing … github-actions](https://docs.github.com/en/billing/concepts/product-billing/github-actions),
[managing-github-actions-settings-for-a-repository](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-github-actions-settings-for-a-repository).

- **Durée d'une tâche** : **6 heures** sur une machine hébergée par GitHub. La valeur par
  défaut de `timeout-minutes` est 360. Exception : la machine à 1 vCPU `ubuntu-slim` est
  limitée à **15 minutes**.
- **Durée d'un workflow** : **35 jours** par exécution, attentes comprises.
- Matrice : 256 tâches au plus. **20 tâches simultanées** sur le plan Free.
- **Machine standard pour un dépôt public** (`ubuntu-latest` = 24.04, aussi 22.04 et 26.04) :
  **4 vCPU, 16 Go de RAM, 14 Go de SSD**, x64 (existe aussi en arm64). `ubuntu-slim` :
  1 vCPU, 5 Go, 14 Go. Le cahier parle de « 15 Gio mesurés », ce qui est cohérent avec
  16 Go annoncés.
- Gratuité : « Use of the standard GitHub-hosted runners is **free and unlimited on public
  repositories** ». Les machines plus grandes (*larger runners*) sont facturées même pour
  un dépôt public.
- **Cache** : 10 Go par dépôt par défaut. Les entrées **non lues depuis 7 jours sont
  supprimées**. Au-delà de 10 Go, éviction (des plus anciennes) jusqu'à repasser sous la
  limite. Débit : 200 écritures et 1 500 lectures par minute et par dépôt.
  - Pour un dépôt d'utilisateur, la taille et la rétention peuvent être augmentées, jusqu'à
    90 jours de rétention pour un dépôt public. C'est une option payante, réservée aux
    comptes avec moyen de paiement ou plan Pro et au-delà.
- **Artefacts** : **rétention de 90 jours par défaut**, réglable de 1 à 90 jours pour un
  dépôt public. Stockage inclus sur le plan Free : 500 Mo, partagé avec GitHub Packages.
  - La page de facturation **ne dit pas explicitement** si le stockage d'artefacts est gratuit
    pour un dépôt public : seule l'exécution l'est explicitement. À vérifier avant d'en
    dépendre.
  - Changement récent : depuis le **1er octobre 2026**, la rétention s'applique aussi aux
    exécutions de workflow, aux *checks* et aux statuts de commit, qui étaient gardés plus de
    400 jours.
- **`concurrency`** : au plus une exécution en cours et **une en attente** par groupe ; une
  nouvelle exécution en attente **annule** la précédente en attente. `cancel-in-progress`
  arrête aussi celle en cours.
  - **Nouveau** : `queue: max` permet jusqu'à **100** exécutions en file par groupe. Il est
    incompatible avec `cancel-in-progress: true`.
- **`schedule`** :
  - « can be delayed during periods of high loads… **some queued jobs may be dropped** » :
    les déclenchements ne sont pas seulement retardés, certains **peuvent être perdus**. La
    doc conseille d'éviter le début d'heure.
  - Intervalle minimal : 5 minutes. Exécution sur la branche par défaut uniquement.
  - **En UTC par défaut, mais une clé `timezone:` (nom IANA) existe désormais**
    (ex. `timezone: "Europe/Paris"`), avec un traitement documenté du passage à l'heure
    d'été.
  - **Dans un dépôt public, les workflows planifiés sont désactivés automatiquement après
    60 jours sans activité sur le dépôt.** Point critique pour un dépôt de publication sans
    activité humaine. Que des commits faits par le workflow comptent comme activité n'est pas
    dit dans la page [S] : à vérifier ou à surveiller.
- Fichier de workflow : 500 Ko au plus.

### Releases

Page lue : [about-releases](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases).

- « Each file included in a release must be **under 2 GiB**. There is **no limit on the total
  size of a release, nor bandwidth usage**. »
- **1 000 fichiers au plus par release.**

### Git LFS (plan Free)

Pages lues :
[about-git-large-file-storage](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-git-large-file-storage),
[billing … git-lfs](https://docs.github.com/en/billing/concepts/product-billing/git-lfs).

- Fichier : **2 Go** au plus.
- Quota gratuit : **10 Gio de stockage et 10 Gio de bande passante par mois**.
- Le stockage compte **chaque version poussée** : modifier un octet d'un fichier de 500 Mo
  ajoute 500 Mo.
- Les téléchargements faits par GitHub Actions **comptent dans la bande passante**.
- Une fois le quota de bande passante dépassé sans moyen de paiement, **LFS est désactivé
  jusqu'au mois suivant**. Une fois le quota de stockage dépassé, plus aucun envoi n'est
  possible.
- Incompatible avec GitHub Pages (voir plus haut).

### Taille des fichiers et des dépôts

Page lue : [about-large-files-on-github](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github).

- Avertissement au-delà de **50 Mio**, refus au-delà de **100 Mio**, 25 Mio par le navigateur.
- Dépôt : idéalement moins de 1 Go, **moins de 5 Go fortement recommandé**.

---

## 10. Wikidata — la réponse des identifiants parlementaires, nuit après nuit (14/11/2026) [M]

Point `wd-identifiants-parlementaires` (requête SPARQL triée par `ORDER BY`, 7 145 éléments) :
les 10 versions de l'entrepôt, générations 2 à 11 (06/11 → 13/11/2026), comparées ligne à ligne.

| Mesure | Résultat |
| --- | --- |
| Version nouvelle | à chaque nuit relevée (9 transitions sur 9) |
| Dont **ordre des clés seul** (`"article"` puis `"an"`, ou `"article"` puis `"naissance"`), mêmes lignes au même rang | 2 sur 9 (v1 → v2, v3 → v4) |
| Dont changements réels | 7 sur 9 : 22 liens d'article sur 16 éléments, 2 dates de naissance, 1 élément nouveau |
| Liens d'article en va-et-vient | 4 éléments (députés de la XVIIe) : l'historique de Wikidata montre l'article supprimé sur Wikipédia (`clientsitelink-remove`) puis recréé, jusqu'à deux fois en une semaine (Q85632476 : retiré le 06/11, rajouté le 10/11, retiré le 12/11, rajouté le 13/11) ; nos versions suivent avec une nuit de décalage |
| Identifiants de l'Assemblée, du Sénat, de Sycomore changés | aucun |
| Candidats de la liste touchés | aucun (17 des 33 éléments de la liste sont dans la réponse) |
| Lignes en double dans chaque réponse | 144 (la même ligne, par les deux branches de l'`UNION`) |
| Taille | 4,34 Mo reçus ; 2,80 Mo sous forme canonique ; 218 Ko compressés (zstd 9) |

Décision Q40 (14/11/2026, exception à P2) : la réponse est gardée sous sa forme canonique.
Rejouée sur les 10 versions, elle en fait 8, et le lecteur `wd_identifiants` en tire exactement
les mêmes lignes.

---

## Pièges du cahier : récapitulatif

| Piège (cahier) | Verdict 04/11/2026 |
| --- | --- |
| JORF : signataire jamais publié | **Infirmé** : `SIGNATAIRES` est rempli en texte libre (153/169 actes) |
| JORF : redélivraisons, sentinelle 2999, « applique » absent depuis 2024, lois en double | Confirmés |
| JORF : panne d'octobre 2026 | Aucune livraison manquante en octobre |
| Parltrack : quotidien, trois derniers jours conservés | **Infirmé** : rien n'a bougé depuis le 24/07/2026, et l'archive `arch/` remonte à 2019 |
| Parltrack : deux formes d'identifiant de scrutin, scrutins sans dossier | Confirmés (4 418 chaînes, 5 710 sans `doc`) |
| PE : `data` objet ou liste | Toujours une liste sur 12 réponses |
| PE : VIIe législature en 404 | Infirmé pour `/meps` (200 en 7,7 s) |
| PE : limitation muette | Non observée ; **nouveau** : la fin de pagination est un 204 sans corps |
| Sénat : CSV latin-1 avec commentaires | Confirmé (18 lignes `%`, CRLF) ; l'export SQL est en UTF-8 |
| Sénat : 93 tables | 95 tables |
| Sénat : tables de présence | Confirmé : `activite_participant` (683 522 lignes PRESENT/EXCUSE) |
| Wikidata : P4123 sans préfixe `PA` | Confirmé ; **nouveau** : P1808 est un chemin d'adresse qui contient le matricule |
| RNE : naissances au mauvais siècle, ni identifiant ni date de fin | Confirmés |
| GitHub Pages : 1 Go « recommandé » | C'est une **limite** pour le site publié |
| GitHub : `schedule` retardé | Retardé **et parfois abandonné** ; désactivé après 60 jours sans activité ; fuseau réglable |
