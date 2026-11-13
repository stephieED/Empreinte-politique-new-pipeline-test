# 4. Estimations chiffrées

Ce document chiffre ce que coûte le modèle (doc. 1) et le processus (doc. 2) : volumes stockés
et servis, poids téléchargé par fiche, durée et mémoire du premier remplissage et des mises à
jour, coût. Il répond aux lignes « Premier remplissage », « Poids téléchargé par fiche »,
« Volume stocké et servi », « Durée et mémoire » et « Coût » de la recette (cahier, partie 7).

**Statut de chaque chiffre** : **[M]** mesuré (compté dans un fichier ou chronométré) ;
**[C]** calculé à partir de mesures (le calcul est donné) ; **[S]** supposé (l'hypothèse est
donnée). Sauf mention contraire, les mesures datent du **04/11/2026** et portent sur les
archives téléchargées ce jour-là (archives de l'Assemblée datées du 03/11/2026). Les durées
viennent du poste de la propriétaire (4 cœurs, 7,8 Gio), pas d'une machine GitHub.

**Débit réseau sur GitHub Actions : hypothèse [S].** Les débits mesurés depuis la connexion
domestique (AN 0,3 à 4,4 Mo/s, DILA 0,33 à 0,93 Mo/s, Parltrack ≈ 0,5 Mo/s) semblent limités
par les serveurs des sources, pas par la connexion. On suppose donc le même ordre de grandeur
depuis GitHub, avec une fourchette **1 à 4 Mo/s pour l'Assemblée**, **0,3 à 1 Mo/s pour la DILA
et Parltrack**, et une marge ×1,5 pour les coupures et reprises (mesurées : 2 coupures sur 4
requêtes pour les amendements XVIIe). Entre une machine GitHub et les *releases* GitHub, on
suppose 20 à 50 Mo/s.

Scripts et résultats bruts : `annexes/scripts/estimations/` (les numéros de section y renvoient).
Mesures de départ : `annexes/mesures/*.md`.

---

## 4.0 Les dix chiffres à retenir

| # | Chiffre | Date et population | Statut |
| --- | --- | --- | --- |
| 1 | **Entrepôt (Z0 + Z1) au premier remplissage : 1,6 à 2,2 Go**, dont Assemblée 0,68 Go et Journal officiel 0,6 à 1,2 Go | archives AN XIVe–XVIIe, JO depuis 2007, Parltrack, au 04/11/2026 | 192 Mo [M] (segments écrits) ; le reste [C] |
| 2 | **Croissance de l'entrepôt : ≈ 2,4 Mo par jour, ≈ 0,9 Go par an**, dont 0,7 Go/an pour le JO (borne haute) | rythme XVIIe (sept. 2024 → nov. 2026) et livraisons JO d'oct. 2026 | [C] |
| 3 | **Site servi (JSON du doc. 1, non compressé) : ≈ 0,82 Go** pour XIVe–XVIIe ; **+0,37 Go par législature de 5 ans** : la limite de 1 Go de GitHub Pages est atteinte vers la fin de la XVIIe | 75 fiches (34 candidats, 18 lignées, 17 gouvernements, 4 législatures + la suivante) | [C] sur prototype [M] |
| 4 | **Même site en fichiers `.json.gz` : ≈ 0,21 Go** (rapport brut/gzip mesuré : 4 à 6) | idem | [C] |
| 5 | **Personne la plus active (Thibault Bazin) : 0,9 Ko au chargement, 75 Ko toutes sections ouvertes, 308 Ko sous le filtre « 12 mois », ≤ 93 Ko sous un filtre par mot** (759 Ko sans index de mots) | XVIIe (paroles, amendements), votes XVe–XVIIe, archives du 03/11/2026 | [M] prototype |
| 6 | **Lignée socialiste (maillon XVIIe) : 124 Ko toutes sections, 215 Ko sous filtre de période ; filtre par mot 7,7 Mo sans index, ≤ 0,46 Mo avec** | groupe SOC XVIIe, 75 membres, 9 578 scrutins | [M] prototype |
| 7 | **Téléchargé chaque soir : ≈ 549 Mo**, dont 352 Mo pour la seule archive des amendements XVIIe ; 2 à 9 min de transfert à 1–4 Mo/s, hors reprises | archives XVIIe + JO + Sénat du 03-04/11/2026 | tailles [M], durée [S] |
| 8 | **Mise à jour quotidienne : 25 à 50 min, mémoire de pointe ≈ 1,1 Go** (6 h permises, 16 Go disponibles) | étapes E0–E8 | [C] sur mesures |
| 9 | **Premier remplissage : ≈ 6,1 Go téléchargés, 3 à 7 h en tout**, en 5 ou 6 tâches de moins de 6 h | ordre des chantiers du doc. 2, § 2.13 | [C] |
| 10 | **Coût : 0 €** sur un dépôt public ; **≈ 4 $ par mois** si le dépôt était privé (abonnement Pro pour Pages) | offres GitHub lues le 04/11/2026 | règles [M], prix Pro [S] |

Deux résultats ont changé la conception et sont détaillés plus bas : la **limite de 1 Go de
GitHub Pages** serait atteinte pendant la XVIIe avec des fichiers JSON bruts (4.1.4), et le
**filtre par mot** d'une lignée ou d'un gouvernement est trop lourd sans index de mots découpé
(4.2.4). Le doc. 1 (§ 1.7.1, 1.7.2) adopte donc les fichiers `.json.gz`, l'index de mots, les
extraits de parole par semestre et les actes d'un gouvernement par mois ; le doc. 2 (§ 2.4,
2.9) adopte les segments plafonnés à 90 Mo et le jeu téléchargeable mensuel.

---

## 4.1 Volume stocké et servi

### 4.1.1 Entrepôt brut (Z0 relevés, Z1 objets versionnés)

**Méthode.** `z1_mesure.py` fait ce que fera E2 : il découpe chaque archive en objets (un
acteur, un scrutin, un amendement, un compte rendu…), retire les champs interdits (présences de
l'agenda, collaborateurs), calcule l'empreinte et écrit un **segment Parquet compressé zstd**.
Mesuré sur les archives AN téléchargées le 04/11/2026 (résultats : `z1-resultats.log`).

| Archive | Objets | Archive zip | Segment Z1 | Lecture + écriture | Mémoire | Statut |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Amendements XVIIe | 144 112 | 351,9 Mo | **79,5 Mo** | 45 s | 456 Mo | [M] |
| Comptes rendus Syceron XVIIe | 652 | 60,9 Mo | **47,5 Mo** | 10 s | 283 Mo | [M] |
| Questions écrites XVIIe | 19 515 | 51,1 Mo | 25,2 Mo | 5,5 s | 371 Mo | [M] |
| Scrutins XVIIe | 9 578 | 29,6 Mo | 6,2 Mo | 5,3 s | 262 Mo | [M] |
| Acteurs, mandats, organes (AMO30) XVIIe | 14 053 | 13,7 Mo | 4,7 Mo | 2,9 s | 318 Mo | [M] |
| Dossiers XVIIe | 10 975 | 11,1 Mo | 2,4 Mo | 1,7 s | 276 Mo | [M] |
| Agenda XVIIe, sans les présences | 8 226 | 8,6 Mo | 1,5 Mo | 0,9 s | 191 Mo | [M] |
| Questions au gouvernement + orales XVIIe | 2 685 | 8,9 Mo | 4,7 Mo | 1,1 s | 177 Mo | [M] |
| Archives figées XIVe–XVIe (AMO, scrutins, dossiers, agenda XVIe) | 64 965 | 77,6 Mo | 20,7 Mo | 15 s | ≤ 317 Mo | [M] |
| **Total mesuré** | | | **192 Mo** | | | [M] |

Constat [M] : un segment Parquet est **2 à 5 fois plus petit que le zip** de la source
(scrutins XVIIe : 6,2 Mo contre 29,6), parce que zstd compresse ensemble des objets semblables
alors que le zip compresse chaque fichier à part. Seuls les comptes rendus (78 %) et les
questions (49 à 57 %) gagnent peu : leur texte est peu répétitif.

**Ce qui n'a pas été mesuré** est extrapolé au prorata de la taille du zip, avec le rapport
segment/zip mesuré pour la même famille en XVIIe (`07_calculs.py`) :

| Famille | Calcul | Résultat | Statut |
| --- | --- | ---: | --- |
| Amendements XVIe, XVe, XIVe | zip 363,3 / 648,5 / 103,7 Mo × 0,226 | 82 + 146 + 23 = **251 Mo** | [C] (la XIVe a un autre schéma : à vérifier) |
| Comptes rendus XVIe, XVe | zip 57,6 / 149,0 Mo × 0,78 | 45 + 116 = **161 Mo** | [C] |
| Agenda XVe | zip 38,3 Mo × 0,18 | 7 Mo | [C] |
| Questions XVe et XVIe | 2,4 × la XVIIe (4,7 + 2 ans de séance contre 2,1) | 72 Mo | [S] archives non relevées |
| **Assemblée, total XIVe–XVIIe** | 192 [M] + 492 [C] | **≈ 0,68 Go** | [C] |
| JO, livraisons depuis le 13/07/2025 | 884 livraisons × 2,21 Mo (moyenne des 30 derniers jours) × 0,43 (rapport segment/livraison mesuré sur 3 livraisons, `04_jo.py`) | **0,84 Go** (borne haute : chaque texte redélivré compté comme une nouvelle version) | [C] |
| JO, dump global de 2025 (1,67 Go, **non téléchargé**) | 1,67 Go × 40 % (part des textes publiés depuis 2007 : ≈ 30 000 textes par an mesurés dans les sommaires 2022-2023 du début du dump, `jo_conteneurs.py`) × 30 à 60 % (part des octets utiles) | **0,2 à 0,4 Go** | [S] |
| Parltrack (8 fichiers `ep_*`) | taille des fichiers zstd | ≤ 0,25 Go | [M] borne haute |
| Sénat, RNE, Parlement européen, EuroVoc, Wikidata, Sycomore, finances | — | ≈ 30 Mo | [S] |
| **Total Z1 au premier remplissage** | | **1,6 à 2,2 Go** | [C] |

**Z0 (relevés)** : une centaine de relevés par soir, ≈ 1 Ko chacun, soit **≈ 36 Mo par an
avant compression, quelques Mo en Parquet** [C]. Négligeable.

**Croissance quotidienne de Z1** [C] (`07_calculs.py`) : une nouvelle version n'est écrite que
si l'objet change.

| Famille | Hypothèse | Mo par jour |
| --- | --- | ---: |
| Amendements | 185 dépôts par jour en moyenne en XVIIe [M : 143 766 en 776 jours], 2,5 versions par amendement [S], 552 o par version [M] | 0,26 |
| Comptes rendus | 0,78 compte rendu par jour [M], 2 versions (provisoire puis complet) [S] | 0,11 |
| Questions, acteurs, dossiers, agenda, scrutins | rythme XVIIe [M], 300 objets réécrits par jour [S] | 0,20 |
| Journal officiel | 4,35 Mo de livraisons par jour [M, octobre 2026] × 0,43 [M] ; chaque texte redélivré compté comme changé [S] | 1,86 |
| **Total** | | **≈ 2,4 Mo/jour, ≈ 0,9 Go/an** |

**Par législature** [C] : une législature complète de 5 ans ajoute à l'Assemblée ≈ 0,35 Go
(profil de la XVe : 146 Mo d'amendements, 116 Mo de comptes rendus, questions et versions) ;
le JO ajoute ≈ 3,4 Go sur la même durée (borne haute). **Entrepôt prévu : ≈ 2 Go fin 2026,
≈ 6,5 Go fin 2031.** Les *releases* n'ont pas de limite de taille totale (documentation lue le
04/11/2026).

> Le JO pèse le plus parce que les fichiers `texte/version` portent tous les liens
> (95 222 liens « CITATION » pour 169 textes dans la livraison du 02/11/2026 [M]). Si la
> croissance gêne, on peut ne garder que les liens vers des lois (1 025 sur 125 860 dans cette
> livraison [M]) : c'est un filtre de découpeur, versionné comme les autres.

### 4.1.2 Faits lus (Z2), dans le cache de GitHub Actions

Mesuré en construisant les tables Z2 de la XVIIe (`02_z2.py`, 11,7 s, 892 Mo de pointe [M]) :
amendements avec exposé 38,2 Mo, prises de parole avec texte 40,9 Mo, signatures 2,0 Mo
(3 540 490 lignes), positions de vote XVIIe 5,8 Mo, scrutins, groupes et dossiers ≈ 2 Mo :
**≈ 89 Mo pour la XVIIe** [M].

Extrapolé à XIVe–XVIIe (×4,2 pour les amendements, ×4,4 pour les paroles, au prorata des zips)
et ajouté le JO (≈ 600 000 actes depuis 2007, liens vers les lois seulement) et Parltrack
(positions des eurodéputés français) : **≈ 0,5 à 0,7 Go** [C/S]. Le cache gratuit fait 10 Go.

### 4.1.3 Magasin des publications (traçabilité, doc. 2, § 2.14)

Chaque fichier publié est gardé une fois par empreinte. Ce qui change chaque soir, c'est tout ce
qui touche la législature et le gouvernement en cours : fichiers XVIIe des lignées, fiche de la
XVIIe, gouvernement en cours, candidats députés, tranches de l'année en cours, et `fiche.json`
de chaque fiche (champ `genere_le`).

| Hypothèse | Ajout par jour de séance (fichiers compressés) | Par an | Statut |
| --- | ---: | ---: | --- |
| Index de mots d'une lignée en un seul jeu de tranches (tout change dès qu'un mot nouveau apparaît) | ≈ 40 Mo | ≈ 6 Go (130 jours de séance × 40 Mo + 235 autres jours × 5 Mo) | [C] |
| Index de mots découpé **par année** (seules les tranches de l'année changent) | ≈ 8 Mo | ≈ 1,5 Go | [C] |

Avec la réduction prévue (au-delà d'un an, seules les publications de fin de mois sont gardées,
≈ 0,21 Go chacune en compressé), le magasin tend vers **1,5 à 6 Go glissants (la dernière année) + au plus 2,5 Go par an** (12 publications de fin de mois)
[C]. C'est supportable sur des *releases*, à condition de **découper l'index de mots par année** (adopté : doc. 1, § 1.7.1).

### 4.1.4 Site servi sur GitHub Pages (limite : 1 Go publié)

**Méthode.** Le prototype (4.2) donne le poids de chaque fichier au format du doc. 1, § 1.7.
`07_calculs.py` en tire un poids par fait servi, puis le multiplie par les volumes d'une
législature de 5 ans [S : profil de la XVe pour les paroles, de la XVIIe pour les amendements].
Population : les ~75 fiches prévues (34 candidats, 18 lignées, 17 gouvernements, 4 législatures).

| Contenu (une législature de 5 ans) | Poids brut par unité [M] | Volume | Mo bruts [C] |
| --- | --- | --- | ---: |
| Lignées : prises de parole des membres (extrait 300 car., index, index de mots) | 320 o par prise de parole | 510 000 × 90 % | 147 |
| Lignées : amendements (liste + index des mots des exposés) | 342 o par amendement | 300 000 × 93 % | 96 |
| Lignées : votes par scrutin, intitulés, « avec qui » | 276 o par scrutin et par groupe | 12 groupes × 15 000 scrutins | 50 |
| Gouvernements : extraits de parole des membres | 4,5 Mo par an (Bayrou) | 5 ans | 23 |
| Gouvernements : actes du JO | 239 o par acte | 5 × 30 000 | 36 |
| Fiche de la législature | — | — | 2 |
| Candidats | — | 34 fiches | 20 [S] |
| **Total par législature de 5 ans** | | | **≈ 373 Mo** |

Site au 04/11/2026 : XIVe (≈ 60 Mo [S], pas de comptes rendus) + XVe (373) + XVIe (2 ans,
≈ 0,45 × 373) + XVIIe (2,1 ans, ≈ 0,5 × 373) + actes 2007-2012 (36) ≈ **0,82 Go** [C].
**Fin de la XVIIe : ≈ 1,0 Go. Fin de la XVIIIe : ≈ 1,4 Go** [C]. Le code du site, les pages de
contexte et les rapports quotidiens (≈ 20 Ko par jour [S]) s'y ajoutent.

**La limite de 1 Go sera donc atteinte pendant la XVIIe**, avec une incertitude de ±30 %
(volumes de paroles et d'amendements XVe et XVIe extrapolés). Ce qui pèse : la recopie des
extraits de parole dans les fiches de lignée (doc. 1, « chaque fichier se suffit à
lui-même »), et l'index des mots des exposés.

Parades, de la plus simple à la plus lourde :

| Parade | Effet | Coût |
| --- | --- | --- |
| **Publier les fichiers déjà compressés** (`.json.gz`) et les décompresser dans le navigateur (`DecompressionStream`, disponible dans les navigateurs courants [S]) | site ÷ 4 à 6 : **≈ 0,21 Go** aujourd'hui, +0,1 Go par législature : la limite recule de plusieurs législatures | transfert inchangé (Pages ne recompresse pas un `.gz`) ; quelques lignes de code côté site |
| Extraits de 150 caractères au lieu de 300 | −30 % environ sur les paroles | moins de contexte à l'écran |
| Extraits partagés par séance (`/seances/<cr>.json`) au lieu d'être recopiés dans chaque fiche | supprime la double copie personne/lignée/gouvernement | une requête de plus au clic ; contraire au principe « chaque fichier se suffit » |
| Plusieurs sites Pages (un dépôt public par législature close) | 1 Go par site | autre adresse, en-têtes CORS à vérifier [S] |

**Recommandation** : la première parade, dès la première publication (adoptée : doc. 1, § 1.7.1). Une fiche publiée pour
**chaque** député et ministre (1 829 personnes ; doc. 3, « là où le cahier est trop étroit »,
point 4) ne tient pas dans 1 Go sans elle : les seuls exposés d'amendements XIVe–XVIIe pèsent
≈ 0,7 Go bruts [C : 172,8 millions de caractères en XVIIe [M] × 4,2].

### 4.1.5 Jeu de données téléchargeable

Mesuré sur trois tables (`08_jeu.py`, 04/11/2026) [M] :

| Table | Parquet zstd | CSV gzip |
| --- | ---: | ---: |
| Positions de vote XIVe–XVIIe (2 605 103 lignes) | 7,6 Mo | 17,7 Mo |
| Amendements XVIIe avec exposé (144 112) | 37,4 Mo | 53,0 Mo |
| Signatures XVIIe (3 540 490) | 2,0 Mo | 14,0 Mo |

Extrapolé à XIVe–XVIIe (amendements et signatures ×4,2) avec les autres tables (≈ 20 Mo) :
**≈ 0,19 Go en Parquet + 0,34 Go en CSV gzip, soit ≈ 0,53 Go par édition du jeu** [C]. Le
plus gros fichier (amendements XIVe–XVIIe en CSV gzip, ≈ 0,22 Go [C]) reste loin des 2 Gio
permis par actif ; mieux vaut un fichier par législature.

**Point de vigilance, résolu** : une *release* datée à chaque publication ferait, à 0,53 Go
par jour, **≈ 190 Go par an** [C]. GitHub ne fixe pas de limite totale, mais c'est démesuré :
le doc. 2 (§ 2.9, étape 5) publie donc une édition datée par mois (`donnees-<aaaa-mm>`) et une
`donnees-derniere` remplacée chaque soir (≈ 6 Go par an [C]).

### 4.1.6 Chaque fichier stocké face aux limites

| Fichier | Où | Taille maximale prévue | Limite | Marge |
| --- | --- | --- | --- | --- |
| Segment Z1 (une source, un type, une législature, un mois) | actif de *release* | amendements XVIIe en un mois de premier remplissage : **79,5 Mo** [M] ; amendements XVe : **≈ 146 Mo** [C] | 2 Gio par actif | large, mais au-dessus des 100 Mo visés par le doc. 3 (J4) : segments **plafonnés à 90 Mo** et découpés par tranche d'identifiants (doc. 2, § 2.4) |
| Index des versions de Z1 | actif de *release* | ≈ 1,5 million d'objets × ~45 o ≈ **70 Mo** en 2026, ≈ 150 Mo en 2031 [S] | 2 Gio | large ; découper par source si besoin |
| Nombre de segments | *release* | ≈ 20 segments par mois, ≈ 240 par an [S] | 1 000 actifs par *release* | **une *release* d'entrepôt par année** |
| Paquet quotidien du magasin des publications | actif de *release* | 8 à 40 Mo [C] | 2 Gio ; 1 000 actifs | une *release* de magasin par mois |
| Plus gros fichier servi | GitHub Pages | exposés 2026 de Lachaud : **5,1 Mo bruts** (132 Ko gzip) [M] | aucune limite par fichier ; 1 Go au total | voir 4.1.4 |
| Site entier | GitHub Pages | **0,82 Go bruts** aujourd'hui [C] | **1 Go** | **insuffisante** sans fichiers `.gz` (adoptés : ≈ 0,21 Go) |
| Artefact de déploiement Pages | Actions | ≈ 0,2 Go compressé [C] | 10 Go ; déploiement en 10 min | large pour la taille ; durée de déploiement de ~30 000 fichiers non mesurée [S] |
| Plus gros fichier du jeu | *release* | ≈ 0,22 Go [C] | 2 Gio | large |
| Fichiers du dépôt public (décisions, `registre/publications.jsonl`, `registre/adresses.csv`) | git | < 1 Mo chacun ; le registre grossit de ≈ 0,2 Mo par an [C] | 100 Mo par fichier ; dépôt < 1 Go conseillé | très large |
| Cache Z2 + index | cache Actions | ≈ 0,7 Go par entrée [C] | 10 Go ; supprimé après 7 jours sans lecture | large **si on supprime les anciennes entrées** (une nouvelle clé chaque soir s'accumule) |
| Disque de la machine | Actions | quotidien ≈ 3 Go ; premier remplissage ≈ 6 Go (dump JO 1,67 Go + entrepôt en cours ≈ 2 Go + outils) [C] | 14 Go | large si chaque archive est effacée après E2 |
| Fichier le plus gros du traitement en mémoire | Actions | scrutins XVIIe tout en mémoire : 1,1 Go [M] | 16 Go (7,8 Gio en local) | large ; lecture en flux possible (22 Mo [M]) |

---

## 4.2 Poids téléchargé par fiche

### 4.2.1 Le prototype

**Ce qui a été fait** (`03_prototype.py`, 14,3 s, 537 Mo de pointe [M]) : composer, au format
du doc. 1 (§ 1.7 : fichier d'en-tête, fichiers de section, textes à part, colonnes, libellés
embarqués), les fichiers de :

- **trois personnes** : François Ruffin (`PA722142`), Thibault Bazin (`PA642847`, le plus de
  prises de parole hors présidence en XVIIe : 4 441), Bastien Lachaud (`PA720846`, le plus
  d'amendements en XVIIe : 2 623) ; plus une **maquette** de personne sans activité
  parlementaire (une candidate jamais élue au Parlement) ;
- le **maillon XVIIe de la lignée socialiste** (groupe SOC, `PO845419`, 75 membres) ;
- le **gouvernement Bayrou** (`PO855052`, 14/12/2024 → 09/09/2025), seul gouvernement
  entièrement dans la XVIIe ; Borne est **calculé** à partir de lui ;
- la **XVIIe législature**.

**Limites déclarées** : amendements et paroles de la XVIIe seulement (archives des autres
législatures non téléchargées) ; votes XIVe–XVIIe ; textes portés et budgets non composés
(< 3 Ko [S]) ; règles simplifiées (lien scrutin-dossier par les routes du doc. 1, nature par
l'intitulé). Seuls les **poids** comptent ici. Poids compressés en **gzip niveau 6** [S :
niveau probable de GitHub Pages]. Le code du site (React) n'est pas compté : ≈ 150 à 250 Ko
compressés à la première visite, puis en cache [S].

**Gain du format en colonnes** [M] : −27 à −72 % sur le poids brut, mais seulement −6 à −19 %
une fois compressé (amendements de Lachaud : 457,7 → 331,8 Ko bruts, 20,4 → 19,1 Ko gzip ;
votes du groupe SOC : 1 630 → 452 Ko bruts, 53,1 → 42,9 Ko gzip). Le format en colonnes sert
donc surtout la limite de 1 Go et la vitesse de lecture sur téléphone, peu le transfert.

### 4.2.2 Ce que télécharge chaque fiche (Ko compressés)

« Initial » = `fiche.json` seul (en-tête, frise, compteurs, couverture). « Sections » = toutes
les sections ouvertes, sans les textes longs. Les filtres sont pris au 04/11/2026 : « 12 mois »
charge les tranches 2025 et 2026 des extraits de parole, « 6 mois » la tranche 2026. Les exposés
d'amendements ne se chargent qu'au clic ou sous un filtre par mot.

| Fiche | Initial | Sections | Filtre 12 mois | Filtre 6 mois | Filtre par mot, avec index (4.2.4) | Filtre par mot, sans index | Statut |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Personne sans activité parlementaire | 0,9 | 0,9 | 0,9 | 0,9 | 0,9 | 0,9 | [M] maquette |
| François Ruffin | 1,0 | 21,5 | 39,0 | 23,7 | ≤ 23,4 + résultats | 85,9 | [M] |
| Bastien Lachaud (le plus d'amendements) | 1,0 | 50,4 | 96,8 | 77,9 | ≤ 58,5 + résultats | 354,6 | [M] |
| **Thibault Bazin (la plus active en séance)** | **0,9** | **75,0** | **307,5** | **148,8** | **≤ 92,5 + résultats** | **759,1** | [M] |
| Bazin, carrière complète XVe–XVIIe | 0,9 | ≈ 240 (≈ 75 si sections découpées par législature) | ≈ 310 | ≈ 150 | ≈ 100 + résultats | ≈ 2 900 | [C] ×4 sur paroles et amendements |
| **Lignée socialiste, maillon XVIIe** | **0,4** | **123,8** | **214,8** | **214,8** | **≤ 456 + résultats** | **≈ 7 700** | [M] |
| Lignée socialiste XIVe–XVIIe (une législature affichée) | ≈ 3 | ≈ 160 | ≈ 250 | ≈ 250 | ≈ 500 | ≈ 9 000 | [C/S] |
| Gouvernement Bayrou | 0,5 | 18 (dont 8 [S] : actes agrégés, budgets) | 18 | 18 | ≤ 41 + résultats | 833 | [M] sauf actes |
| **Gouvernement Borne** | 0,5 | **≈ 28** | ≈ 28 (clos) | ≈ 28 | ≈ 80 + résultats | ≈ 4 600 (paroles 1 740 + actes 2 900) | [C] |
| **XVIIe législature** | **0,4** | **192,9** (ordre du jour 2026 seul) | 235 | 193 | 193 (titres déjà chargés) | 193 | [M] |

Lecture :

- **La personne sans activité** ne télécharge presque rien : `sections.*.vide` et la couverture
  (« relu, aucun ») suffisent à afficher « Aucune donnée trouvée. Pourquoi → » sans autre
  requête (doc. 1, § 1.7.3).
- **Le chargement initial reste sous 1 Ko partout** : le découpage du doc. 1 tient sa promesse.
- **La personne la plus active pèse 75 Ko sections ouvertes** ; ce sont ses **extraits de
  parole** qui coûtent sous un filtre de période (233 Ko pour 2025-2026). Des tranches **par
  semestre** au lieu de l'année diviseraient à peu près par deux le filtre « 6 mois » [S] (adopté : doc. 1, § 1.7.2).
- **Pour une lignée**, les extraits ne se chargent qu'au clic sur un débat (cahier 4.3) ; le
  filtre de période recharge seulement l'index des paroles (91 Ko) pour recompter les débats.
- **Le fichier `textes.json` de la législature** (3 194 dossiers, 137 Ko) est le plus gros
  fichier de section ; il reste raisonnable.

### 4.2.3 Détail mesuré par fichier (Ko gzip -6, brut entre parenthèses)

| Fichier | Ruffin | Bazin | Lachaud |
| --- | --- | --- | --- |
| `fiche.json` | 1,0 (2,6) | 0,9 (2,5) | 1,0 (2,6) |
| `fonctions.json` | 0,7 (1,7) | 2,0 (7,0) | 1,9 (5,7) |
| `votes.json` (positions retenues XVe–XVIIe) | 7,9 (28,4) : 176 textes | 11,0 (41,9) : 253 | 10,6 (40,0) : 242 |
| `divergences.json` | 6,9 (20,3) | 9,8 (30,2) | 9,5 (29,1) |
| `proposes.json` (amendements sans exposé) | 2,4 (11,7) : 136 | 23,3 (173,2) : 2 211 | 21,5 (231,8) : 2 623 |
| `proposes-textes-*.json` (exposés, 3 années) | 45,5 (213,1) | 417,9 (1 634,8) | 255,4 (7 713,0) |
| `paroles.json` (index sans texte) | 2,7 (11,8) : 193 | 28,0 (206,9) : 4 441 | 6,0 (33,7) : 647 |
| `paroles-textes-*.json` (extraits, 3 années) | 18,9 (46,5) | 266,1 (802,3) | 48,9 (133,4) |

Lignée SOC XVIIe : `fiche.json` 0,4 ; `membres.json` 1,5 ; `votes-17.json` (9 578 scrutins,
décomptes des membres à la date, intitulés des seuls votes sur l'ensemble) 63,7 ;
`avec-qui-17.json` (position majoritaire des 13 groupes par scrutin) 45,8 ; `paroles.json`
(débats agrégés) 11,6 ; `proposes.json` (agrégats) 0,8. À la demande : intitulés des autres
scrutins 121,8 (en un seul fichier avec les décomptes : 174,1) ; index des 15 693 prises de
parole 91,0 ; extraits 1 013,1 ; liste des 16 376 amendements 111,3 [M].

Gouvernement Bayrou : `composition.json` (36 portefeuilles) 1,7 ; `paroles.json` (débats
agrégés) 5,5 ; `deposes.json` (35 projets de loi) 2,7 ; extraits des 12 436 prises de parole
des membres pendant leur fonction, par mois : 9 à 182, total 815 [M].

XVIIe législature : `hemicycle.json` (574 sièges occupés au 03/11/2026) 9,2 ;
`ordre-du-jour-2024/2025/2026.json` (699 séances confirmées, 2 950 points) 5,3 / 42,0 / 45,1 ;
`textes.json` (3 194 dossiers et un nuage de 150 mots) 137,1 ; `commissions.json` 1,1 [M].

### 4.2.4 Le filtre par mot a besoin d'un index

Charger tous les textes d'une fiche pour y chercher un mot coûte jusqu'à **7,7 Mo** pour la
lignée socialiste (dont 6,4 Mo pour les exposés des amendements de ses membres) [M]. Le cahier
(4.7) exige pourtant ce filtre sur chaque fiche, y compris les exposés.

Proposé et mesuré (`05_index_mots.py`, `05b_index_exposes.py`) : un **index de mots** par fiche
(mot normalisé → numéros des textes qui le contiennent), **découpé par les deux premières
lettres** du mot. Taper « logement » ne charge que la tranche « lo », puis les extraits des
seuls résultats.

| Fiche | Tous les textes (gzip) | Index entier (gzip) | Tranche médiane | Plus grosse tranche |
| --- | ---: | ---: | ---: | ---: |
| Ruffin | 64 Ko | 47 Ko | 0,08 Ko | 1,9 Ko |
| Lachaud | 304 Ko | 150 Ko | 0,08 Ko | 8,1 Ko |
| Bazin | 684 Ko | 315 Ko | 0,09 Ko | 17,5 Ko |
| Gouvernement Bayrou (extraits) | 815 Ko | 457 Ko | 0,10 Ko | 22,6 Ko |
| Lignée SOC XVIIe, extraits de parole | 973 Ko | 537 Ko | — | 26,5 Ko |
| Lignée SOC XVIIe, exposés d'amendements | 6 412 Ko | 1 765 Ko | — | 103,7 Ko |

Mesures du 04/11/2026 sur les fichiers du prototype [M]. L'index ajoute environ la moitié du
poids des textes au **stockage** (déjà compté en 4.1.4), mais divise le **téléchargement** d'un
filtre par mot par 10 à 70. Adopté : doc. 1, § 1.7.1 et 1.7.2.

---

## 4.3 Premier remplissage

### 4.3.1 Méthode

Les chantiers du doc. 2 (§ 2.13), chacun dans une tâche GitHub Actions de moins de 6 h,
lancés le soir ou le week-end. Chaque chantier écrit Z0 et Z1 au fil de l'eau (E1–E2) : une
tâche interrompue reprend où elle s'était arrêtée. Le dernier chantier enchaîne le premier
E3–E7 complet.

### 4.3.2 Temps de lecture mesurés et extrapolés

Lecture = décompression + analyse de tous les objets, sur le poste de la propriétaire, un seul
cœur. Mesures des annexes [M] ; extrapolation au prorata de la taille compressée [C].

| Famille | XIVe | XVe | XVIe | XVIIe | Mémoire de pointe |
| --- | ---: | ---: | ---: | ---: | ---: |
| AMO (acteurs, mandats, organes) | 0,6 s (AMO20) [M] | 2,2 s [M] | 2,7 s [M] | 2,4 s [M] | 407 Mo [M] |
| Scrutins | 0,5 s [M] | 1,9 s [M] | 2,0 s [M] | 2,3 s en flux ; 6,4 s tout en mémoire [M] | 22 Mo en flux, 1,1 Go tout en mémoire [M] |
| Dossiers | 1,2 s [M] | 1,8 s [M] | 1,1 s [M] | 1,0 s [M] | 258 Mo [M] |
| Amendements | ≈ 11 s [C] | ≈ 70 s [C] | ≈ 39 s [C] | 36 à 38 s [M] | 132 Mo [M] |
| Comptes rendus (Syceron) | — (hors périmètre) | ≈ 66 à 83 s [C] | ≈ 26 à 32 s [C] | 27 à 34 s [M] | 38 Mo [M] |
| Agenda | — | ≈ 5 s [C] | ≈ 1 s [C] | 1,1 s [M] | 129 Mo [M] |
| Questions (3 archives) | — | ≈ 6 s [S] | ≈ 3 s [S] | 3,0 s [M] | 284 Mo [M] |

| Source hors Assemblée | Lecture | Statut |
| --- | --- | --- |
| JO, 3 livraisons (8,2 Mo compressés) | 3,15 s, 146 Mo de pointe | [M] |
| JO, 884 livraisons depuis le 13/07/2025 (1,96 Go) | ≈ 12,6 min (0,39 s par Mo compressé) | [C] |
| JO, dump global (1,67 Go, **non téléchargé**) | ≈ 11 min au même rythme, mémoire ≈ 150 Mo en flux | [S] : on suppose que le dump se lit comme les livraisons ; seul son début (30 Mo, 26 986 sommaires lus en 1,7 s) a été mesuré |
| Parltrack `ep_votes` + `ep_meps` (20,6 Mo) | 10,3 s, 38 Mo | [M] |
| Parltrack, les 8 fichiers (254 Mo) | ≈ 2 min | [C] |

**Total de lecture complète** : Assemblée XIVe–XVIIe ≈ 5 min, JO ≈ 24 min, Parltrack ≈ 2 min,
soit ≈ 31 min sur un cœur, ≈ 10 min sur les 4 cœurs d'une machine GitHub en lisant les
familles en parallèle [C].

### 4.3.3 Volume, durée et mémoire par chantier

| # | Chantier | Téléchargé | Transfert [S : débits de l'introduction] | Découpage E2 | Mémoire | Total |
| --- | --- | ---: | --- | --- | ---: | --- |
| 1 | Archives courantes de l'Assemblée XVIIe (≈ 537 Mo), puis Parltrack (254 Mo) | 0,79 Go | AN 2 à 9 min ; Parltrack 4 à 14 min (×1,5 pour les reprises) | ≈ 2 min [C] | ≈ 0,5 Go | **≈ 15 à 30 min** |
| 2 | Archives closes AN XIVe–XVIe (1,44 Go + questions XVe-XVIe ≈ 0,14 Go [S]), Sénat (8,6 Mo), 884 livraisons du JO (1,96 Go) | 3,6 Go | AN 7 à 40 min ; JO 33 à 110 min | AN ≈ 6 min ; JO ≈ 13 min | ≈ 0,5 Go | **≈ 1 à 3 h** (découpable en deux tâches) |
| 3 | Dump global du JO | 1,67 Go | 28 à 93 min (0,3 à 1 Mo/s ; mesuré ici 0,33 à 0,93 Mo/s) | ≈ 11 min, lu en flux pendant le transfert | ≈ 0,2 Go | **≈ 0,5 à 1,5 h** |
| 4 | Europe (API, EuroVoc), Wikidata (5 requêtes), Sycomore (34 pages de candidats, 1 requête par seconde), RNE (80,7 Mo), finances | ≈ 0,1 Go | ≈ 10 min ; ≈ 1 h si Sycomore est lu pour les 1 829 personnes suivies | < 2 min | < 0,3 Go | **≈ 15 min à 1 h** |
| 5 | Premier E3–E7 complet | — (entrepôt ≈ 2 Go relu depuis les *releases* : ≈ 1 à 2 min) | — | E3 ≈ 10 min, E4 ≈ 3 min, E5 ≈ 10 min, E6 ≈ 5 min, E7 ≈ 8 min | ≈ 1,1 à 2 Go | **≈ 40 min** |
| | **Total** | **≈ 6,1 Go** | | | **≤ 2 Go** | **≈ 3 à 7 h, 5 ou 6 tâches** |

Le chantier 1 passe en premier parce que l'archive courante de l'Assemblée réécrit son passé chaque nuit, et que Parltrack, figé, peut disparaître (doc. 2, § 2.13). Le
disque de la machine (14 Go) n'est jamais un problème si chaque archive est effacée après E2
(pointe ≈ 6 Go pendant le chantier 3 [C]).

---

## 4.4 Mise à jour quotidienne et mises à jour complètes

### 4.4.1 Mise à jour quotidienne (un soir de semaine)

Volume relevé chaque soir [M, tailles du 03/11/2026] : amendements XVIIe 351,9 Mo, comptes
rendus 60,9 Mo, questions écrites 51,1 Mo, scrutins 29,6 Mo, AMO30 13,7 Mo, dossiers 11,1 Mo,
agenda 8,6 Mo, questions au gouvernement et orales 8,9 Mo, Sénat 8,6 Mo, JO ≈ 4,4 Mo, plus
quelques Mo pour le Parlement européen, Wikipédia et le RNE (hebdomadaire) : **≈ 549 Mo** [C].
L'Assemblée republie ses archives chaque nuit (et parfois en journée : amendements XVIIe datés
du 03/11/2026 15:20 GMT [M]) : la requête conditionnelle épargne rarement le téléchargement.

| Étape | Ce qui prend du temps | Durée | Mémoire de pointe | Statut |
| --- | --- | --- | --- | --- |
| E0 Démarrer | installation de Python, restauration du cache Z2 (≈ 0,7 Go) | 1 à 2 min | < 0,1 Go | [S] |
| E1 Relever | 549 Mo à 1–4 Mo/s, ×1,5 pour les reprises ; ~50 requêtes au Parlement européen à 1 toutes les 2 s | **4 à 15 min** | < 0,1 Go | [S] |
| E2 Découper et versionner | découpage des archives XVIIe : 73 s mesurées (amendements 45 s) + tests de zip (amendements : 10,4 s [M]) + envoi des nouveaux segments (≈ 2,4 Mo) et de l'index (≈ 70 Mo) | **2 à 3 min** | 0,46 Go [M] | [M/C] |
| E3 Lire | seulement les objets changés (quelques centaines d'amendements, un ou deux comptes rendus) | < 1 min | ≤ 0,4 Go | [C] |
| E4 Relier et dériver | banc d'essai DuckDB (`06_e4_banc.py`) sur les 2,6 millions de positions XIVe–XVIIe et les 353 784 paragraphes XVIIe : groupe à la date, effectif à la date, décompte par groupe et par scrutin, dernière lecture, attribution des paroles : **1,7 s, 351 Mo** [M] ; la trentaine de règles du doc. 1 compte ~20 à 50 fois ce travail | **1 à 3 min** | ≤ 2 Go (limite DuckDB) | [M/S] |
| E5 Composer | prototype : 14,3 s pour 6 fiches, 537 Mo [M] ; ~75 fiches (lignées à 4 maillons) ≈ 4 min ; index de mots ; jeu téléchargeable (3 tables XVIIe exportées en 37 s [M], toutes ≈ 3 min) | **7 à 10 min** | ≈ 0,6 Go | [C] |
| E6 Contrôler | C1 fait par fait sur les seuls fichiers changés ; C4 schéma de ~0,8 Go de JSON ; vérification croisée de 40 faits sur les pages de l'AN (1 à 2 s chacun) | **3 à 5 min** | ≈ 1 Go | [S] |
| E7 Publier | construction du site (≈ 1 à 2 min [S]), envoi de l'artefact Pages (≈ 0,2 Go compressé), déploiement (≤ 10 min, limite GitHub), magasin (8 à 40 Mo), jeu (0,53 Go si publié ce soir-là) | **5 à 10 min** | < 0,5 Go | [S] |
| E8 Rendre compte | rapport, issues du dépôt privé | < 1 min | < 0,1 Go | [S] |
| **Total** | | **≈ 25 à 50 min** (fourchette basse ≈ 20 min les soirs sans séance) | **≈ 1,1 Go** (2 Go si E4 utilise toute sa limite) | |

La tâche a 6 h et 16 Go [M, documentation lue le 04/11/2026] : la marge est d'un facteur 7 en
temps et 8 en mémoire. Le budget de 5 h 15 du doc. 2 (§ 2.1) laisse donc plus de 4 h aux
chantiers.

**En local** (7,8 Gio) : un essai sur quelques personnes (doc. 2, § 2.12) reprend E3–E5 sur un
extrait ; toutes les mesures de ce document ont tenu sous 1,1 Go par processus.

### 4.4.2 Mode `complet` (relire toutes les sources sans requête conditionnelle)

Tout le chantier 1 et l'Assemblée du chantier 2 : ≈ 549 Mo + 1,58 Go d'archives closes + 254 Mo
de Parltrack + RNE ≈ **2,5 Go** [C], le JO historique **exclu** (ses livraisons ne sont jamais
réécrites ; le dump se relit seulement sur demande explicite). Transfert 15 à 60 min [S],
découpage ≈ 8 min [C], E3 seulement sur ce qui a changé, puis E4–E8 ≈ 20 min : **≈ 45 min à
1 h 30**. Avec le dump du JO : +0,5 à 1,5 h. Mémoire inchangée (≈ 1,1 Go).

### 4.4.3 Mode `recalcul` (sans collecte)

| Cas | Ce qui est relu | Durée | Statut |
| --- | --- | --- | --- |
| Règle modifiée (E3 inutile, Z2 en cache) | E4–E8 | **≈ 20 à 30 min** | [C] |
| Lecteur modifié pour une famille (ex. amendements) | téléchargement des segments de la famille depuis les *releases* (≈ 0,33 Go, < 1 min [S]) puis relecture (≈ 2,7 min pour XIVe–XVIIe [C]) | **≈ 25 à 35 min** | [C] |
| Tous les lecteurs (champ ajouté partout) | tout Z1 (≈ 2 Go, 1 à 2 min [S]) puis ≈ 10 min de lecture sur 4 cœurs | **≈ 35 à 50 min** | [C] |
| Cache Z2 évincé (plus de 7 jours sans mise à jour) | comme « tous les lecteurs » | ≈ 35 à 50 min | [C] |

---

## 4.5 Coût

### 4.5.1 Dépôt public : tout est gratuit

Documentation GitHub lue le 04/11/2026 (pages citées dans `annexes/mesures/autres-sources.md`,
§ 9, et la page de facturation d'Actions) :

| Service | Règle [M] | Notre usage [C] | Tient ? |
| --- | --- | --- | --- |
| GitHub Actions, machine standard | « free and unlimited on public repositories » ; 4 vCPU, 16 Go, 14 Go de disque ; 6 h par tâche | 25 à 50 min par soir + chantiers du week-end ≈ 20 à 35 h par mois | oui |
| *Releases* | 2 Gio par fichier, 1 000 fichiers par *release*, « no limit on the total size of a release, nor bandwidth usage » | entrepôt ≈ 2 Go puis +0,9 Go/an ; magasin ≈ 2,5 Go/an ; jeu ≈ 6 Go/an (une édition par mois) | oui |
| GitHub Pages | site ≤ 1 Go ; bande passante 100 Go/mois (limite souple) ; déploiement ≤ 10 min | site ≈ 0,82 Go bruts (≈ 0,21 Go en `.json.gz`) | **oui avec les `.json.gz`** (4.1.4) |
| Cache d'Actions | 10 Go par dépôt, entrées supprimées après 7 jours sans lecture | ≈ 0,7 Go par entrée | oui, en supprimant les anciennes entrées |
| Artefacts | rétention 1 à 90 jours ; 500 Mo de stockage inclus dans le plan gratuit, partagés avec Packages ; **la page ne dit pas si un dépôt public est exempté** | artefact de déploiement Pages (≈ 0,2 Go) et résultats d'essai ; la candidate n'est pas gardée quand la tâche tombe dans la fenêtre interdite, elle est recalculée (doc. 2, § 2.9) | oui, avec une rétention de 2 jours |
| Dépôt git | 100 Mo par fichier, dépôt < 1 Go conseillé | quelques Mo (décisions, registres) | oui |

**Dépense : 0 €.** Aucun compte tiers, aucun moyen de paiement.

### 4.5.2 Si le dépôt était privé

| Poste | Règle | Coût |
| --- | --- | --- |
| Actions | machine standard d'un dépôt privé : **2 vCPU, 8 Go** [M] ; Linux 2 cœurs à **0,006 $/min** ; plan gratuit : 12 $ de calcul inclus par mois, plan Pro : 18 $ [M] | ≈ 40 à 75 min par soir sur 2 cœurs [S : ×1,5] + chantiers ≈ 1 600 à 2 600 min/mois ≈ **10 à 16 $/mois**, en partie couverts par l'inclus |
| GitHub Pages | pour un compte personnel, Pages sur un dépôt privé demande l'abonnement **Pro** [S : règle connue, non relue ce jour] | **≈ 4 $/mois** [S] ; le Pro inclut 18 $ de calcul, ce qui couvre Actions |
| Artefacts | 500 Mo (gratuit) ou 1 Go (Pro), puis 0,25 $/Go/mois [M] | ≈ 0 avec une rétention courte |
| Cache | 10 Go inclus, 0,07 $/Go/mois au-delà [M] | 0 |
| Premier remplissage | 3 à 7 h × 1,5 sur 2 cœurs ≈ 270 à 630 min ≈ 1,6 à 3,8 $ | une fois |
| **Total** | | **≈ 4 $/mois (≈ 50 $/an)**, sous réserve du prix Pro |

Le dépôt de développement, lui, reste privé et ne fait tourner que des tests : quelques minutes
par jour, dans l'inclus gratuit [S].

### 4.5.3 Points de vigilance

| Point | Pourquoi | Ce qu'il faut faire |
| --- | --- | --- |
| **Bande passante de Pages : 100 Go/mois, limite souple** | une visite moyenne ≈ 0,3 Mo (code du site ≈ 0,2 Mo [S] + une fiche 20 à 200 Ko [M]) : la limite correspond à **≈ 300 000 visites par mois** [C] ; GitHub peut répondre 429 au-delà | suivre le trafic ; au besoin, un CDN gratuit devant Pages |
| **Tâches planifiées désactivées après 60 jours sans activité** sur un dépôt public | le doc. 2 (§ 2.3) compte sur le commit nocturne du registre ; **la documentation ne dit pas** qu'un commit fait par une tâche compte comme activité | la tâche d'import du soir vérifie l'état des workflows et les réactive par l'API si besoin (`.../actions/workflows/{id}/enable`), en ouvrant l'alerte (adopté : doc. 2, § 2.3) |
| Déclenchements planifiés retardés **et parfois abandonnés** | documenté | les deux déclenchements du doc. 2 ; alerte `planification` |
| Stockage des artefacts | 500 Mo partagés ; exemption des dépôts publics non écrite | rétention 2 jours, un seul artefact à la fois |
| Cache : une clé par soir | 7 entrées de 0,7 Go = 5 Go ; les entrées non lues partent après 7 jours | supprimer l'entrée de la veille après une restauration réussie |
| **Limite de 1 Go de Pages** | 0,82 Go bruts dès aujourd'hui (4.1.4) | fichiers `.json.gz` (adoptés) ; contrôle de taille en E7 avec alerte à 80 % (doc. 2, § 2.9) |
| Jeu daté chaque jour | ≈ 190 Go/an (4.1.5) | une édition datée par mois (adoptée) |
| Dépendance à un seul fournisseur | entrepôt, site et calcul chez GitHub | sauvegarde hebdomadaire de l'entrepôt sur le disque de la propriétaire (≈ 2 Go, +0,9 Go/an) |

---

## 4.6 Ce qui reste incertain

| Estimation fragile | Pourquoi | Comment la vérifier |
| --- | --- | --- |
| **Débits depuis GitHub** (E1, premier remplissage) | aucune mesure depuis une machine GitHub ; les débits domestiques variaient déjà de 0,3 à 4,4 Mo/s | une tâche d'essai qui télécharge AMO30, les amendements XVIIe et 100 Mo du dump JO, et note durée, coupures et serveur (`be:`) |
| **Taille du JO dans l'entrepôt** (0,6 à 1,2 Go, et 0,7 Go/an) | dump non téléchargé ; part des textes redélivrés qui changent vraiment inconnue | télécharger le dump une fois (chantier 3) ; compter les versions identiques entre deux livraisons |
| **Volumes XVe et XVIe** (amendements, paroles, questions) | extrapolés au prorata des zips ; schéma XIVe différent ; XVe avec 499 comptes rendus sans orateur | relever ces archives au chantier 2 et rejouer `07_calculs.py` |
| **Taille du site servi** (0,82 Go) et donc la date du dépassement de 1 Go | repose sur ces mêmes volumes et sur 34 candidats « moyens » | composer toutes les fiches d'une législature close (XVIe) et mesurer |
| Durées E4–E6 | E4 mesuré sur 5 opérations seulement ; E5 sur 6 fiches ; E6 non prototypé | chronométrer chaque étape dans le rapport E8 dès les premiers essais (le doc. 2 le prévoit) |
| Durée du déploiement Pages pour ~30 000 fichiers | non mesurée ; limite de 10 min | un déploiement d'essai sur un dépôt jetable |
| Effet du format compressé `.json.gz` sur le navigateur | `DecompressionStream` supposé disponible ; coût de décompression sur un téléphone non mesuré | essai sur un téléphone d'entrée de gamme avec la fiche de la lignée |
| Prix du plan Pro et règle « Pages privé = Pro » | non relus ce jour | page de tarifs de GitHub |
| Activité qui empêche la désactivation à 60 jours | non documenté | observer, ou réactiver par l'API comme proposé |
| Seuil de « couverture suffisante » (règle 7) | non fixé par la propriétaire (décision du 04/11/2026) ; sans effet sur les volumes | — |
