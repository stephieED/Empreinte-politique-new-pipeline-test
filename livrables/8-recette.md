# 8. Recette

Ce document reprend un par un les critères de la partie 7 du cahier. Pour chacun, il montre
quels mécanismes du modèle (doc. 1) et du processus (doc. 2) le tiennent. Il **n'invente
aucun mécanisme**. Quand un besoin, une règle, un piège ou une exigence n'est couvert par
aucun des documents 1 à 3, la cellule l'indiquait (« à ajouter »), avec un renvoi `Txx`. Ces
trous ont été comblés dans les documents 1, 2 et 5 le 04/11/2026 : chaque cellule renvoie
désormais au mécanisme ajouté, avec son numéro `Txx` ; l'état de chaque trou est en 8.7.

Rédigé le 04/11/2026, consolidé le même jour. Le document 4 (estimations) donne les chiffres
auxquels renvoient les cellules « doc. 4 ».

**Conventions**

| Notation | Sens |
| --- | --- |
| « doc. 1, 1.6 R-MATIERE » | document 1, section 1.6, règle R-MATIERE |
| « doc. 2, 2.8.1 C1 » | document 2, contrôle bloquant C1 (C1–C7) ; `A1`–`A8` = avertissements de 2.8.2 |
| « cahier 3.1.4 » | `CAHIER_DES_CHARGES.md`, section 3.1.4 |
| « mes. an-acteurs §2.1 » | `livrables/annexes/mesures/an-acteurs.md`, § 2.1 (de même `an-scrutins-dossiers`, `an-amendements-cr`, `autres-sources`) |
| E0 … E8 | étapes du doc. 2, 2.0 : E0 démarrer, E1 relever, E2 découper et versionner, E3 lire, E4 relier et dériver, E5 composer, E6 contrôler, E7 publier, E8 rendre compte |
| ZD | décision de la propriétaire (fichier YAML, doc. 1, 1.3.3) |
| État | `couvert` · `partiel` (couvert en partie, le reste est dit) |
| Chiffres | Sauf mention contraire, mesurés le 04/11/2026 sur les archives téléchargées ce jour-là ; la population est nommée dans la cellule |

**Décisions de la propriétaire du 04/11/2026**, prises en compte partout :

- l'entrepôt est public, sur les *releases* du dépôt public ;
- la fenêtre d'interdiction court du lundi au vendredi, de 9 h à 19 h (heure de Paris), hors
  jours fériés ;
- les paroles d'un gouvernement sont celles tenues **pendant** la fonction **et** en qualité de
  membre du gouvernement ;
- le seuil de « couverture suffisante » (règle 7) sera fixé plus tard.

---

## 8.1 Besoin → objets et données

Fichiers servis : arborescence du doc. 1, 1.7.2, sous `/donnees/<id-publication>/` ; ils sont
servis compressés (`.json.gz`, doc. 1, 1.7.1) : les noms ci-dessous omettent l'extension `.gz`. Objets :
Z2 = faits lus (doc. 1, 1.4) ; Z3 = graphe relié (doc. 1, 1.5) ; règles : doc. 1, 1.6.

### 8.1.1 Fiche d'une personne (cahier 4.2)

| Section | Z2 | Z3 et règles | Fichier servi | État |
| --- | --- | --- | --- | --- |
| En-tête | `identite_source`, `mandat` (GP) | `personne`, `correspondance` (R-IDENTITE) ; `appartenance` → groupe actuel → lignée | `personnes/<adr>/fiche.json` (`personne`, `sources`) | couvert |
| En bref : frise | `mandat` (AN, Sénat, Sycomore), `fonction_gouvernementale`, `mandat_pe`, `mandat_local`, `siege` | `carriere` (R-CARRIERE) : lien vers la législature ou le gouvernement, périodes absentes déclarées ; siège : R-HEMICYCLE | `fiche.json` `carriere` | couvert : priorités entre sources (AMO > Sycomore, libellé daté du Sénat), doc. 1, 1.6 R-CARRIERE (T23) |
| En bref : compteurs | idem | compteurs datés (`au`) + couverture (R-COUVERTURE) | `fiche.json` `compteurs` | couvert |
| Fonctions exercées | `mandat.qualite` (président, rapporteur, questeur…), `acte.rapporteurs` | `carriere` | `fonctions.json` | couvert : familles de fonctions et fusion d'affichage des permutations, doc. 1, 1.6 R-CARRIERE (T32 ; seuil : doc. 5, Q24) |
| Ce qu'elle a proposé | `document`, `dossier`, `acte`, `amendement`, `signature` ; `dossier_pe`, `concept` | `texte_porte` (R-TEXTE-PORTE), `etape_dossier` (R-ETAPE), `sort_dossier`, `amendement_canonique` (R-AMENDEMENT, R-SORT-AMENDEMENT), `matiere` (commission du dossier visé), banc au dépôt (`periode_position`) | `proposes.json`, `proposes-textes-<annee>.json`, `europe.json` | couvert : étape d'un texte européen, doc. 1, 1.6 R-SORT-FINAL / R-ETAPE (T26) |
| Ce qu'elle a voté | `scrutin`, `position_vote`, `acte`, `document` ; `scrutin_pe`, `position_vote_pe` | `scrutin_classe` (R-NATURE-SCRUTIN, R-ORIGINE), `lien_scrutin_dossier`, `derniere_lecture`, `matiere`, `sort_dossier` (`par_49_3`), `periode_position` (R-BANC, R-PERIODE), `membre_gouvernement` | `votes.json`, `europe.json` | couvert : 49.3 lu dans l'acte `DeclarationGouvernement_Type`, doc. 1, 1.6 R-SORT-FINAL (T02) ; non-votes de fonction, doc. 1, 1.4 C (T42) |
| Voté autrement que son groupe | `position_vote`, `decompte_groupe` | `appartenance` à la date, `position_groupe_scrutin`, `divergence` (R-DIVERGENCE, 5 conditions) ; ce qui est écarté est déclaré en couverture | `divergences.json` | couvert |
| Ce qu'elle a dit | `intervention`, `point_odj`, `compte_rendu`, `question` ; `activite_pe` | `intervention_attribuee` (R-ORATEUR, R-QUALITE, `preside`), `sujet_intervention` (R-SUJET), `question_reponse_parole` (R-QAG) | `paroles.json`, `paroles-textes-<periode>.json`, `europe.json` | couvert : doc. 1, 1.6 R-QUALITE (T01) ; qualité déduite, à confirmer : doc. 5, Q21 |
| Ce qu'on n'a pas pu lire | relevés Z0 ; ZD `absence_etablie` | `couverture` (portée = fiche, par famille) | `fiche.json` `couverture`, `sections.*.vide` | couvert |
| Pied | colonne `licence` de chaque fait | union calculée des licences | `fiche.json` `licences` | couvert |
| Filtres par mot et par période | intitulés, exposés, extraits | — | index de mots par tranche (`mots/<annee>-<xx>`), exposés par année, extraits de parole par semestre ; filtrage dans le navigateur ; `?periode=&mot=` (doc. 1, 1.7.1, 1.7.2) | couvert : couverture du filtre (23 669 irrecevables sans exposé, XVIIe), doc. 1, 1.5.5 (T31) |

### 8.1.2 Fiche d'un groupe, une lignée (cahier 4.3)

| Section ou besoin | Z2 | Z3 et règles | Fichier servi | État |
| --- | --- | --- | --- | --- |
| Règle de filiation, fusion, scission | `organe`, `mandat` GP | `groupe` (R-CONTINUITE-GROUPE), `filiation` (R-FILIATION) ; ZD `filiation`, `continuite_groupe` | `catalogue/lignees.json` | couvert |
| Positions « divergentes » | `organe.position` (versions Z1) | `position_declaree.divergente` (R-BANC) | `lignees/<adr>/fiche.json` | couvert |
| Ancienne adresse → lignée | — | registre des adresses, page de redirection (doc. 1, 1.2.2) | — | couvert |
| En-tête | — | `lignee`, maillons | `fiche.json` | couvert |
| En bref | `mandat` GP, `organe` ASSEMBLEE | `appartenance` (effectif jour par jour), `position_declaree` | `fiche.json` | couvert (en XVIIe, les 14 GP sont « non déclarés » : AMO30 du 03/11/2026) |
| Qui sont-ils | — | `appartenance`, drapeau `population = candidat` | `membres.json` | couvert |
| Sur quoi ils ont pris la parole | — | `intervention_attribuee` ∩ `appartenance`, `sujet_intervention` | `paroles.json` | couvert (qualité : R-QUALITE, T01) |
| Ce qu'ils ont proposé | — | `texte_porte`, `amendement_canonique` (distincts, par type de déposant), `signature` comptée à part | `proposes.json` | couvert |
| Ce qu'ils ont voté | — | `position_groupe_scrutin` (numérateur, dénominateur, position majoritaire publiée, `divise`) ; R-RATIO | `votes-<leg>.json` | couvert : décomptes servis, ratio et seuil calculés par l'interface (doc. 5, Q1) ; lignes `PO0` : doc. 1, 1.6 R-APPARTENANCE (T09) |
| Avec qui ils votent | `decompte_groupe` | position majoritaire publiée de chaque groupe ; `place_mediane` (R-HEMICYCLE) | `avec-qui-<leg>.json` | couvert |
| Ce qu'on n'a pas pu lire | — | couverture par maillon | `fiche.json` | couvert |
| Pied | — | `genere_le`, licences | `fiche.json` | couvert |

### 8.1.3 Fiche d'un gouvernement (cahier 4.4)

| Section | Z2 | Z3 et règles | Fichier servi | État |
| --- | --- | --- | --- | --- |
| En-tête | `organe` GOUVERNEMENT | — | `gouvernements/<adr>/fiche.json` | couvert |
| En bref : frise, législatures traversées | `organe` GOUVERNEMENT, ASSEMBLEE | — | `fiche.json`, `accueil.json` | couvert |
| En bref : composition, remaniements, vagues | `mandat` GOUVERNEMENT et MINISTERE | `membre_gouvernement` (R-COMPOSITION, R-VAGUE) | `fiche.json` | couvert : mandat sans MINISTERE apparié hors composition, doc. 1, 1.6 R-COMPOSITION ; signalé par A8, doc. 2, 2.8.2 (T12) ; doc. 5, Q23 |
| En bref : majorité à l'Assemblée | `organe.position` | `position_declaree` à la date | `fiche.json` | couvert (« non déclarée » en XVIIe) |
| En bref : projets déposés, adoptés, promulgués ; 49.3 | `document` (`PRJL`), `acte`, `loi` | `projet_gouvernement` (R-DEPOT-GOUVERNEMENT), `texte_porte` (`initiative_gouvernementale`), `sort_dossier`, `etape_dossier` | `fiche.json`, `deposes.json` | couvert : doc. 1, 1.5.4 et 1.6 R-DEPOT-GOUVERNEMENT (T11) ; 49.3 : R-SORT-FINAL (T02) |
| Qui le composait | `mandat` MINISTERE (portefeuille, qualité) | `membre_gouvernement`, ministère de rattachement (libellé « auprès » + ZD `rattachement_portefeuille`), lien vers la fiche par `per:` | `composition.json` | couvert |
| Sur quoi ils ont pris la parole | `intervention` | `intervention_attribuee` ∩ `membre_gouvernement` (pendant la fonction) ∩ qualité de membre du gouvernement (décision du 04/11/2026 ; doc. 3, « trop étroit » 3) | `paroles.json` | couvert : doc. 1, 1.6 R-QUALITE (T01) ; qualité déduite : doc. 5, Q21 |
| Ce qu'il a fait déposer | `document`, `acte`, `dossier` | `matiere`, `sort_dossier`, `par_49_3` | `deposes.json` | couvert : ministère porteur, doc. 1, 1.6 R-DEPOT-GOUVERNEMENT (T11) |
| Ce qu'il a fait entrer en vigueur | `acte_reglementaire`, `lien_acte_loi` | `acte_rattache` (R-RATTACHEMENT-ACTE, ZD `libelle_ministere`) ; loi citée dans le titre (`lien_acte_loi`, source « titre ») | `actes.json` (agrégats par ministère) + `actes-<aaaa-mm>.json` (listes par mois) | couvert : doc. 1, 1.6 R-MESURE-NOMINATIVE (T21) |
| Les budgets qu'il a fait voter | `montant_budget`, `montant_protection_sociale`, `loi` | `exercice_rattache` (R-EXERCICE) | `budgets.json` | partiel : séries mensuelles antérieures à 2024 absentes de l'API, déclarées `trou_source` (doc. 2, 2.2 ; T21) |
| Ce qu'on n'a pas pu lire | — | couverture (pas de texte avant le 20/06/2012, majorité non déclarée, paroles sans intitulé) | `fiche.json` | couvert |
| Articles de la période | — | — | `catalogue/articles.json`, lu par chevauchement de dates (doc. 1, 1.7.2) | couvert (T34) |

### 8.1.4 Fiche d'une législature (cahier 4.5)

| Section | Z2 | Z3 et règles | Fichier servi | État |
| --- | --- | --- | --- | --- |
| En-tête : bornes, mode de fin | `organe` ASSEMBLEE | ZD `fin_legislature` (mode, décret Légifrance) | `legislatures/<n>/fiche.json` | couvert |
| En bref : comptes | `scrutin` (SPS, MOC), `acte` (49.3), `loi`, `mandat` ASSEMBLEE, `organe` GOUVERNEMENT | comptes datés | `fiche.json` | couvert : terme légal, doc. 1, 1.6 R-TERME-LEGAL (T35) ; motions de censure par le code `MOC`, doc. 1, 1.4 C (T07) ; archive XIVe tronquée, doc. 1, 1.5.5 (T10) |
| Qui siégeait | `siege`, `mandat` GP | `place_mediane`, `appartenance` à une date | `hemicycle.json` | couvert |
| À l'ordre du jour | `reunion` (statut), `point_odj` (dossiers cités) | séances confirmées ; dossier lié, sinon « non lié » en couverture | `ordre-du-jour-<annee>.json` | couvert : borne de la XIVe, doc. 1, 1.5.5 (T16) |
| Les textes de la législature | `dossier`, `document`, `acte`, `loi` | `etape_dossier` (par législature), `sort_dossier`, `matiere`, initiateurs | `textes.json` | couvert : lois promulguées sous la législature suivante, doc. 1, 1.6 R-LOI-DOSSIER (T18) |
| Le travail des commissions | `acte` (saisie au fond) | `matiere`, `etape_dossier` | `commissions.json` | couvert (dossiers saisis au seul Sénat : « saisi au Sénat seulement », doc. 5, Q19) |
| Ce qu'on n'a pas pu lire | — | couverture | `fiche.json` | couvert |
| Articles de la période | — | — | `catalogue/articles.json` (doc. 1, 1.7.2) | couvert (T34) |

### 8.1.5 Besoins transverses (cahier 4.7)

| Besoin | Objets et règles | Fichier servi | Contrôle | État |
| --- | --- | --- | --- | --- |
| Liens entre fiches | `correspondance`, `appartenance`, `filiation`, `carriere`, `membre_gouvernement` ; un rapprochement douteux part en relecture (R-IDENTITE `a_relire`), il ne devient pas un lien | `catalogue/*.json` | C2 | couvert |
| Liens à créer : texte ↔ scrutin ↔ amendement ↔ décret ↔ loi | `lien_scrutin_dossier` (accord des routes) ; `amendement` → `document` → `dossier` ; `dossier` → `loi:<numéro>` ; `lien_acte_loi` | `votes.json`, `proposes.json`, `textes.json`, `actes.json` | C2 | couvert : échéancier, doc. 1, 1.4 C `echeancier` (forme à mesurer) ; « applique » non posé depuis 2024 en `trou_source`, doc. 1, 1.4 E (T19) ; lois hors archive, doc. 1, 1.6 R-LOI-DOSSIER (T18) |
| Une source par fait | `prov_url`, `licence` (doc. 1, 1.4) ; index `src` (1.7.1) | tous | C4 (schéma) | couvert |
| Couverture déclarée | `couverture`, 9 statuts (doc. 1, 1.5.5) | `fiche.json` | C5 | couvert |
| Absences établies à la main | ZD `absence_etablie` ; `relu_aucun` distinct de `non_relu` | `fiche.json` | — | couvert |
| Comptes datés | compteurs avec `au` (doc. 1, 1.7.3) | `fiche.json` | — | couvert : doc. 1, 1.7.1, « Comptes » (T33) |
| Sélections déclarées | `couverture.detail` ; C3 : lu = servi + écarté avec sa raison | `fiche.json` | C3 | couvert |
| Plusieurs thèmes | `concept` (EuroVoc, plusieurs par dossier) ; à l'AN, matière unique (jamais deux commissions au fond, XVIIe, archive du 03/11/2026) | compte des objets distincts à côté des comptes par thème (doc. 1, 1.7.1) | — | couvert (T33) |
| Cosignataires | `signature` (liste complète) | jeu téléchargeable (1.7.4) | — | couvert |
| Fraîcheur | `releve.date_source` ; cadence (doc. 2, 2.3) | `fraicheur.json`, `fiche.json.fraicheur` | — | couvert |
| Filtre par mot, filtre par période | index de mots ; tranches par année (exposés) ou par semestre (paroles) (doc. 1, 1.7.1, 1.7.2) | fichiers de textes découpés | — | couvert (T31) |
| Navigation | `catalogue/*.json`, `accueil.json` | idem | C2 | couvert |
| Poids des pages | en-tête léger, sections à la demande, textes au clic (doc. 1, 1.7.1 ; doc. 3, J11) | — | — | couvert ; chiffres : doc. 4 |
| Méthodologie et chiffres de couverture | registre des règles, couverture recalculée à chaque passage (doc. 1, 1.6) | `methodologie.json` | — | couvert |
| Articles datés | copie figée `articles/<date>/donnees.json`, jamais recomposée (doc. 2, 2.7) ; « à une date » : versions Z1 et rejeu (doc. 2, 2.14) | — | — | couvert : commande `empreinte instantane`, doc. 2, 2.12 ; catalogue, doc. 1, 1.7.2 (T34) |
| Données téléchargeables | paquets par régime de licence, *release*, data.gouv.fr (doc. 1, 1.7.4) | *releases* `donnees-derniere` et `donnees-<aaaa-mm>` (mensuelle) | — | couvert |

### 8.1.6 Pages de contexte (cahier 4.8)

| Page | Ce qui la sert | Fichier | État |
| --- | --- | --- | --- |
| À propos, FAQ, nous soutenir | texte rédigé, sans donnée | code du site | couvert (hors modèle) |
| Méthodologie | registre des règles, versions, chiffres de couverture | `methodologie.json` | couvert |
| Sources | catalogue `source`, `point_acces`, `licence` (doc. 1, 1.4 G) + couverture de portée « corpus » | `sources.json` | couvert : points d'accès non retenus déclarés, doc. 1, 1.4 G (T36) |
| Mentions légales (licences) | licences par source ; union par page et par paquet | `sources.json` | couvert : licence de l'entrepôt public (segments Parltrack sous ODbL), doc. 1, 1.7.4 (T27) |
| Articles | `articles/<date>-<titre>/` | copies figées | couvert (catalogue : T34) |

### 8.1.7 Règles de lecture (cahier 4.6) → règle du registre

| Règle de lecture | Règle (doc. 1, 1.6) | État |
| --- | --- | --- |
| Vote sur l'ensemble d'un texte | R-NATURE-SCRUTIN + ZD `exception_regle` | couvert : nature `partie_de_texte`, doc. 1, 1.6 R-NATURE-SCRUTIN (T06) ; statut des résolutions : doc. 5, Q20 |
| Dernière lecture, sur tout le corpus | R-DERNIERE-LECTURE | couvert |
| Matière | R-MATIERE (« matière non établie ») | couvert |
| Origine d'un texte voté | R-ORIGINE | couvert |
| Rôle sur un texte porté | R-TEXTE-PORTE | couvert |
| Sort final, 49.3 nommé à part | R-SORT-FINAL | couvert (T02) |
| Période d'une position | R-BANC, R-PERIODE | couvert |
| Appartenance à une date | R-APPARTENANCE (suite de périodes) | couvert |
| Divergence, sans seuil | R-POSITION-GROUPE (`divise`), R-DIVERGENCE | couvert |
| Rattachement d'un acte réglementaire | R-RATTACHEMENT-ACTE | couvert |
| Rattachement d'un exercice | R-EXERCICE | couvert |

---

## 8.2 Règle éditoriale → mécanisme

| Règle | Par construction (quoi, où) | Par contrôle (lequel, quand) | État |
| --- | --- | --- | --- |
| 1. Ni jugement, ni score, ni classement | schéma en liste blanche : aucun champ de score ni de rang (doc. 1, 1.7.1 ; doc. 3, J13) ; aucune règle du registre ne produit de score | C4, motifs « score, rang » (E6) | couvert : ordre neutre déclaré par le schéma, doc. 1, 1.7.1 ; vérifié par C4, doc. 2, 2.8.1 (T28) |
| 2. Traçabilité intégrale | provenance obligatoire (doc. 1, 1.0 principe 2) ; `prov_*`, `prov_url`, `licence` en Z2 ; index `src` dans chaque fichier (1.7.1) | C4 (schéma : `src` requis), E6 ; A2 : 40 faits relus sur les pages publiques (tirés en E1, comparés en E6) | couvert |
| 3. Aucun taux de présence individuel | présences filtrées **avant stockage** : clé `participants` de l'agenda AN (190 885 entrées XVIIe), `activite_participant` du Sénat (683 522 lignes, export du 04/11/2026) ; aucun champ prévu (doc. 1, 1.0 principe 7, 1.3.2 ; doc. 2, 2.4) | C4, motif « taux de présence » (E6) | couvert |
| 4. Un 49.3 n'est pas une position de vote | le 49.3 est un acte (`sort_dossier.par_49_3`), jamais une `position_vote` (aucun scrutin à la source, cahier 3.1.4) ; motion de censure = scrutin de nature `motion_censure` | C4, motif « 49.3 en position de vote » (E6) | couvert : 49.3 repéré par l'acte qui l'engage, doc. 1, 1.6 R-SORT-FINAL (T02) |
| 5. Une donnée manquante reste manquante | `null` + raison (principe 4) ; couverture à 9 statuts ; une règle qui ne conclut pas produit « non établi » (principe 6) ; R-NOMINATIF (scrutins XIVe à dissidents seuls) | C5 : `complet` exige un relevé complet ; un 0 ou une liste vide exige `complet` ou `relu_aucun` (E6) | couvert : doc. 2, 2.8.1 C5 (T29) |
| 6. Position dans l'hémicycle sourcée | R-BANC : position déclarée seulement, datée par les versions Z1, jamais déduite ; sinon « non déclaré » (XVIIe : 14 GP sans position, AMO30 du 03/11/2026) | — | couvert par construction |
| 7a. Ratio de groupe avec numérateur, dénominateur, couverture | R-RATIO, sinon « N/D » | C4, « ratio sans numérateur ou dénominateur » (E6) | couvert par construction : seuls les décomptes sont servis, le ratio et le seuil relèvent de l'interface (décision du 04/11/2026 ; doc. 5, Q1) |
| 7b. Indice individuel rapporté au groupe : jamais publié | absent de Z3 servi et du jeu (doc. 1, 1.7.4) ; calculé seulement par `empreinte audit`, en local, hors dépôt, hors journaux (doc. 2, 2.8.3) | C4, « indices individuels » (E6) | couvert |
| 7c. Position face au groupe : fait publiable, jamais compté | `divergence` par scrutin, sans total (doc. 1, 1.5.3) ; `divergences.json` n'a pas de champ de total | C4, « total de divergences » (E6) | couvert |
| 8. Étiquettes thématiques = aides à la lecture | matière lue (R-MATIERE), domaines EuroVoc lus, jamais devinés ; champ marqué `aide_a_la_lecture` dans le schéma, dit par l'interface et la méthodologie (doc. 1, 1.7.1) | — | couvert (T28) |
| 2.1 Aucun taux d'adoption des amendements | aucun champ ; le sort est donné amendement par amendement | C4, motif « taux d'adoption » (E6) | couvert |
| 2.1 Un amendement cosigné compte une fois ; signatures à part | `amendement_canonique` + `signature` (R-AMENDEMENT) | A4 (copies) (E6) | couvert : clé de dédoublonnage, doc. 1, 1.6 R-AMENDEMENT (T05) |
| 2.1 Texte porté publié à partir de l'examen en commission | R-TEXTE-PORTE (publiable à partir de l'examen) ; R-ETAPE (« COM » ne prouve pas l'examen) | C4 : aucun texte porté servi avant son examen en commission (E6) | couvert : texte européen, doc. 1, 1.6 R-SORT-FINAL / R-ETAPE ; contrôle, doc. 2, 2.8.1 C4 (T26, T30) |
| 2.1 Part des actes « appliquant » une loi : jamais publiée | aucun champ ; `lien_acte_loi` servi sans part | C4, motif (E6) | couvert |
| 2.2 Licences de chaque page | union calculée des licences des faits (doc. 1, 1.7.3) | C4 : licences du fichier = union des licences de ses `src` (E6) | couvert (T27) |
| 2.2 Licences de chaque jeu ; ODbL à l'identique | un paquet par régime (`empreinte-etalab`, `-odbl`, `-ccby`), `datapackage.json` (doc. 1, 1.7.4 ; doc. 3, J14) | — | couvert : l'entrepôt public déclare ses licences par segment, Parltrack sous ODbL (doc. 1, 1.7.4 ; T27) |
| 2.2 Page HTML = œuvre produite, l'attribution suffit | liste `sources` et licences en pied de fiche | — | couvert |
| 2.2 Faits seulement (Wikipédia, Sycomore, places) | contenu non recopié : faits, adresse et empreinte seulement (doc. 1, 1.3.2) ; licence `faits-seulement` | — | couvert |
| 2.2 EuroVoc CC BY : modifications à indiquer | modifications dites sur la page des sources et dans `datapackage.json` (doc. 1, 1.7.4) | — | couvert (T27) |

---

## 8.3 Piège → traitement

### 8.3.1 Pièges du cahier (partie 3)

| # | Cahier | Piège | Étape | Traitement | Où | État |
| --- | --- | --- | --- | --- | --- | --- |
| P01 | 3.1 | Le nom du jeu et du fichier change selon la législature | E1, config | chemins découverts sur les pages de jeux, rangés en configuration par législature, jamais supposés | doc. 2, 2.2 ; doc. 1, 1.8 | partiel (archive figée absente des pages : N15) |
| P02 | 3.1 | Plusieurs schémas pour un même objet | E2, E3 | découpeur à variantes ; schéma reconnu par l'empreinte des clés, sinon relevé `suspect` | doc. 2, 2.2 étape 3, 2.4 | couvert |
| P03 | 3.1 | Un objet seul = dictionnaire, plusieurs = liste | E2, E3 | normalisation ; tests « liste au lieu de dictionnaire » | doc. 2, 2.4, 2.12 | couvert |
| P04 | 3.1 | Une adresse, deux fichiers | E1 | reprise seulement avec `If-Range` sur l'`ETag`, sinon fichier entier ; test du zip | doc. 2, 2.2 étape 2 | couvert |
| P05 | 3.1 | Transferts coupés ; reprise non honorée | E1 | taille = `Content-Length`, CRC ; 3 tentatives ; sinon relevé `echec`, rien ne change | doc. 2, 2.2, 2.11 | couvert |
| P06 | 3.1 | L'archive courante réécrit le passé | E2, E4 | versions par empreinte, datées, rangées par archive ; R-ARBITRAGE-ARCHIVES | doc. 1, 1.3.2, 1.6 | couvert |
| P07 | 3.1 | Documentation des schémas (2016) périmée | E2, E3 | lecteurs écrits sur le JSON réel ; tests sur extraits réels | doc. 2, 2.12 | couvert |
| P08 | 3.1 | Grammaire des identifiants ; `PA` omis | E3 | grammaire vérifiée ; `PA` rétabli ; non conforme → anomalie de lecture | doc. 1, 1.2.1 | couvert |
| P09 | 3.1.1 | « Acteur » ne veut pas dire « député » | E4 | populations calculées depuis les mandats (R-PERIMETRE) | doc. 1, 1.5.1 | couvert |
| P10 | 3.1.1 | Pas de député avant le 19/06/2002, pas de gouvernement avant le 17/05/2007 | E4 | `borne_historique` ; Sycomore avant 2002 (R-CARRIERE) | doc. 1, 1.5.1, 1.5.5 | couvert |
| P11 | 3.1.1 | Siège à la date de l'archive ; pas d'archive figée XIVe | E2, E4 | table `siege` (origine, date de constat) ; R-HEMICYCLE | doc. 1, 1.4 B, 1.6 | partiel (N16) |
| P12 | 3.1.1 | Le dossier cite le mandat de ministère, pas celui de gouvernement | E3, E4 | `fonction_gouvernementale` apparie les deux mandats | doc. 1, 1.4 B | couvert : ministère porteur, doc. 1, 1.6 R-DEPOT-GOUVERNEMENT (T11) |
| P13 | 3.1.1 | Groupes du Sénat : seul le libellé actuel dans AMO | E3, E4 | mandats sénatoriaux lus aussi dans l'export du Sénat | doc. 1, 1.4 B | couvert : libellé daté du Sénat, doc. 1, 1.6 R-CARRIERE (T23) |
| P14 | 3.1.1 | « Non inscrit » : un organe par législature, passage obligé à l'ouverture | E4 | population `depute_ni`, pas de lignée ; condition 5 de R-DIVERGENCE | doc. 1, 1.5.1, 1.5.3 | couvert |
| P15 | 3.1.1 | Un groupe change d'organe en cours de législature | E4 | maillon = chaîne d'organes (R-CONTINUITE-GROUPE), sinon ZD | doc. 1, 1.2.2, 1.5.2 | couvert |
| P16 | 3.1.1 | Élection annulée : deux mandats | E4 | appartenance = suite de périodes | doc. 1, 1.5.2 | couvert |
| P17 | 3.1.1 | Mandat suspendu, pas terminé | E3 | `mandat_suspension` reconstruite | doc. 1, 1.4 B | couvert |
| P18 | 3.1.1 | Organe créateur d'une mission ; mission commune sans commission | E3 | `organe.organe_createur` | doc. 1, 1.4 B | couvert |
| P19 | 3.1.1 | La circonscription est un attribut du mandat | E3 | `mandat.circonscription` | doc. 1, 1.4 B | couvert |
| P20 | 3.1.1 | Rien ne dit pourquoi une législature a pris fin | ZD | décision `fin_legislature` + décret | doc. 1, 1.3.3 | couvert |
| P21 | 3.1.1 | Collaborateurs nommés | E2 | filtrés avant stockage ; ZD `publication_donnee` (refus par défaut) | doc. 1, 1.3.2, 1.3.3 | couvert |
| P22 | 3.1.2 | Le numéro repart à 1 ; le Congrès est hors périmètre | E3 | identifiant complet comme clé | doc. 1, 1.2.1 | couvert : Congrès lu puis écarté avec sa raison, doc. 1, 1.2.1 (T08) |
| P23 | 3.1.2 | Trois schémas de listes nominatives | E3 | table de correspondance du lecteur | doc. 2, 2.4 | couvert (précisé en N31) |
| P24 | 3.1.2 | Un scrutin ne dit pas son texte (référence : 3 752 sur 9 578, XVIIe, 04/11/2026) | E4 | R-LIEN-SCRUTIN-DOSSIER, trois routes, accord exigé | doc. 1, 1.6 ; doc. 3, J22 | couvert |
| P25 | 3.1.2 | « Ordinaire » couvre tout ; nature dans l'intitulé | E4 | R-NATURE-SCRUTIN, sinon `non_etablie` | doc. 1, 1.6 | partiel (N34) |
| P26 | 3.1.3 | XIVe : autre schéma, autre page | E1, E2 | chemin découvert ; découpeur XIVe | doc. 2, 2.2, 2.4 | couvert |
| P27 | 3.1.3 | Couple (état, sous-état) ambigu | E4 | R-SORT-AMENDEMENT (table publiée), sinon « sort non établi » | doc. 1, 1.6 | couvert |
| P28 | 3.1.3 | Copies divergentes ; fait foi la liste du premier signataire | E3, E4 | `signature` lue dans la copie du premier signataire ; R-AMENDEMENT ; A4 | doc. 1, 1.4 C, 1.6 | couvert : clé (`examenRef`, `numeroLong`), doc. 1, 1.6 R-AMENDEMENT ; découpage par uid, doc. 2, 2.4 (T05) |
| P29 | 3.1.3 | L'amendement vise un document | E3 | `amendement.document` → `document.dossier` | doc. 1, 1.4 C | couvert |
| P30 | 3.1.3 | Des dizaines de cosignataires | E3, E5 | table `signature` ; liste complète dans le jeu | doc. 1, 1.4 C, 1.7.4 | couvert ; volume : doc. 4 |
| P31 | 3.1.4 | Loi promulguée sous la législature suivante : dans aucune archive (71 sur 1 085, 04/11/2026) | E6 | A3 compare avec le JO (détection) | doc. 2, 2.8.2 A3 | couvert : rattachement, doc. 1, 1.6 R-LOI-DOSSIER (T18) |
| P32 | 3.1.4 | L'état se lit dans la conclusion ; « COM » ne prouve pas l'examen | E4 | R-SORT-FINAL, R-ETAPE | doc. 1, 1.6 | couvert |
| P33 | 3.1.4 | Le 49.3 n'a jamais de scrutin | E4 | `par_49_3`, jamais une position | doc. 1, 1.5.3 | partiel (N36, T02) |
| P34 | 3.1.4 | Un acte cite un scrutin du Sénat | E3 | `acte` : scrutins cités, AN et Sénat | doc. 1, 1.4 C | couvert : servi sans lien interne, doc. 1, 1.5.5 (T10) |
| P35 | 3.1.4 | NOR manquant : le numéro de loi est le lien sûr | E3 | clé `loi:<numéro>` | doc. 1, 1.2.1 | couvert |
| P36 | 3.1.4 | Nature par préfixe ; le préfixe ne dit pas l'auteur | E3, E4 | `document.nature` ; R-ORIGINE ; `initiative_gouvernementale` | doc. 1, 1.4 C, 1.6 | couvert |
| P37 | 3.1.4 | 30 dossiers XIVe réapparaissent ensuite | E2, E6 | un objet, plusieurs archives ; A4 | doc. 1, 1.3.2 ; doc. 2, A4 | couvert |
| P38 | 3.1.5 | Ni thème ni lien direct aux dossiers | E4 | R-SUJET (point d'ODJ, séance) | doc. 1, 1.6 | couvert |
| P39 | 3.1.5 | 2021, XVe : 499 CR sans orateur ; repli faux | E4 | R-ORATEUR → `non_attribuee` + raison | doc. 1, 1.6 | couvert |
| P40 | 3.1.5 | Un CR de la XVe dans l'archive XVIe | E2, E6 | même uid = même objet ; A4 | doc. 1, 1.3.2 | couvert |
| P41 | 3.1.5 | La republication renumérote les paragraphes | E2, E3 | clé `id_syceron` ; rang = attribut ; empreinte de rapprochement, alias | doc. 1, 1.2.2 | couvert |
| P42 | 3.1.5 | Interpellations, orateurs collectifs, personnes hors Assemblée | E4 | `non_attribuee` ; couverture | doc. 1, 1.6 | couvert |
| P43 | 3.1.5 | Présider n'est pas intervenir | E4 | `preside` (`roledebat` ou libellé) | doc. 1, 1.6 | couvert |
| P44 | 3.1.5 | Un créneau n'est pas un sujet ; codes des lois de finances | E4 | R-SUJET | doc. 1, 1.6 | couvert |
| P45 | 3.1.6 | Schéma en capitales à partir de la XVe | E3 | variantes du lecteur | doc. 2, 2.4 | couvert |
| P46 | 3.1.6 | Une QG ne cite aucune séance | E4 | R-QAG (date + sujet), sinon `non_appariee` | doc. 1, 1.6 | couvert |
| P47 | 3.1.7 | Présence nominative dans l'agenda | E2 | `participants` filtré avant stockage | doc. 1, 1.3.2 | couvert |
| P48 | 3.1.7 | Séances du Sénat, du Congrès et commissions mêlées | E3 | `reunion.type` | doc. 1, 1.4 D | couvert |
| P49 | 3.1.7 | Points sans dossier ; un titre → deux dossiers | E3, E4 | `point_odj.dossiers` (liste) ; « non lié » en couverture | doc. 1, 1.4 D | couvert |
| P50 | 3.1.8 | Texte des articles : 404 sur la XIVe ; autre gabarit pour les lois de finances | — | source non retenue (aucun besoin de la partie 4), déclarée sur la page des sources | doc. 1, 1.4 G | couvert (T36) |
| P51 | 3.1.9 | Pages publiques = seconde route | E1, E6 | A2 (40 faits) ; `prov_url` | doc. 2, 2.2, 2.8.2 | couvert |
| P52 | 3.1.10 | Fichier des places XIVe : sans `PA`, état déduit, usage commercial interdit | E2, E3 | faits seulement ; `PA` rétabli ; `siege.origine` | doc. 1, 1.2.1, 1.3.2, 1.4 B | couvert |
| P53 | 3.2 | Export du Sénat servi vide (444 o, HTTP 200) | E1 | plancher de taille, nombre de tables | doc. 2, 2.2 | couvert |
| P54 | 3.2 | Les extraits CSV ne donnent que le groupe courant | E1 | export complet | doc. 2, 2.2 | couvert |
| P55 | 3.2 | CSV latin-1 précédés de commentaires | E1 | export SQL (UTF-8) | doc. 2, 2.2 | couvert |
| P56 | 3.2 | Aucun identifiant commun avec l'AN | E4 | Wikidata P1808, sinon état civil + date de naissance | doc. 1, 1.6 R-IDENTITE | partiel (N70) |
| P57 | 3.2 | Tables de présence | E2 | écartées au découpage | doc. 1, 1.3.2 ; doc. 2, 2.2 | couvert |
| P58 | 3.3 | `data` : objet ou liste | E3 | normalisation | doc. 2, 2.12 | couvert |
| P59 | 3.3 | Limitation de débit muette (pas de 429) | E1 | délai d'attente de 30 s, débit adaptatif | doc. 2, 2.2 étape 5 | couvert |
| P60 | 3.3 | 404 passagers pendant la pagination | E1, E2 | nouvelles tentatives ; un relevé incomplet ne fait constater aucun retrait | doc. 2, 2.2, 2.4 | couvert |
| P61 | 3.3 | VIIe législature : 404 | E4 | couverture `trou_source` | doc. 1, 1.5.5 | couvert (infirmé : I06) |
| P62 | 3.3 | 1,8 à 3,5 s par requête | E0, E1 | budget de temps ; seulement les personnes du volet européen | doc. 2, 2.1, 2.2 | couvert ; durée : doc. 4 |
| P63 | 3.3 | `www.europarl.europa.eu` : pare-feu anti-robot | — | jamais interrogé ; on n'y écrit que des liens | doc. 2, 2.2 (aucun collecteur) | couvert |
| P64 | 3.3 | Aucun identifiant commun PE ↔ AN | E4 | R-IDENTITE | doc. 1, 1.6 | couvert |
| P65 | 3.3 | CC BY 4.0, `User-Agent` qui identifie | E1 | `User-Agent` qui nomme le site et un contact | doc. 2, 2.2 | couvert (T26) |
| P66 | 3.4 | Trois jours de rétention | E1 | premier remplissage commencé par Parltrack | doc. 2, 2.13 | dépassé (I01) |
| P67 | 3.4 | Un tableau JSON, un objet par ligne | E2 | découpeur Parltrack | doc. 2, 2.4 | couvert |
| P68 | 3.4 | Deux formes d'identifiant de scrutin | E3 | forme canonique + alias | doc. 1, 1.2.1 | couvert |
| P69 | 3.4 | Scrutins sans dossier | E3 | `null` + raison | doc. 1, 1.0 principe 4 | couvert |
| P70 | 3.4 | Aucun sort d'amendement, aucune issue de dossier | E3 | `amendement_pe` sans sort, rien de déduit | doc. 1, 1.4 F | couvert |
| P71 | 3.4 | Dates impossibles ; 548 598 activités au 22/11/2016 | E3 | indicateur de date douteuse | doc. 1, 1.4 F | couvert |
| P72 | 3.4 | Des législatures de paroles manquent selon la personne | E4 | `trou_source` par personne | doc. 1, 1.5.5 | couvert |
| P73 | 3.4 | Explications de vote sans lien | E3 | `activite_pe.type`, aucun lien inventé | doc. 1, 1.4 F | couvert |
| P74 | 3.4 | Une position se rattache à son scrutin par numéro + date | E3 | positions lues dans la liste de votants que porte chaque scrutin d'`ep_votes` | doc. 1, 1.4 F | couvert (T26) |
| P75 | 3.4 | ODbL | E5, E7 | paquet `empreinte-odbl` | doc. 1, 1.7.4 | couvert : entrepôt public, doc. 1, 1.7.4 (T27) |
| P76 | 3.5 | EuroVoc : couverture inégale | E4 | couverture du domaine | doc. 1, 1.5.5 | couvert |
| P77 | 3.5 | CC BY 4.0, modifications à indiquer | E5 | modifications dites (page des sources, `datapackage.json`) | doc. 1, 1.7.4 | couvert (T27) |
| P78 | 3.6 | Le signataire n'est jamais publié | E4 | R-RATTACHEMENT-ACTE : jamais à une personne | doc. 1, 1.6 | couvert (infirmé : I03) |
| P79 | 3.6 | Rattachement au gouvernement par la date de publication | E4 | R-RATTACHEMENT-ACTE | doc. 1, 1.6 | couvert |
| P80 | 3.6 | Dates sentinelles `2999` | E3 | `null` + « date sentinelle » | doc. 2, 2.5 ; doc. 1, 1.4 E | couvert (T20) |
| P81 | 3.6 | Textes anciens redélivrés | E1, E2 | toutes les livraisons depuis la dernière traitée ; filtre par date de publication ; dernière version d'un `ID` | doc. 2, 2.2 ; doc. 1, 1.3.2 | couvert |
| P82 | 3.6 | « Applique » plus posé depuis 2024 | E4 | lien gardé quand il existe ; la part n'est jamais publiée | doc. 1, 1.4 E | couvert : `trou_source` depuis 2024, doc. 1, 1.4 E ; échéancier, doc. 1, 1.4 C (T19) |
| P83 | 3.6 | Une loi en deux enregistrements | E3, E6 | `version` original / rectificatif ; A4 | doc. 1, 1.4 E ; doc. 2, A4 | couvert |
| P84 | 3.6 | Libellé de ministère libre (260 depuis 2007) | E4, ZD | ZD `libelle_ministere` ; libellés inconnus en relecture | doc. 1, 1.3.3 ; doc. 2, 2.6 | couvert |
| P85 | 3.6 | Serveur en panne trois jours | E1 | rattrapage à partir de la dernière livraison traitée | doc. 2, 2.2 | couvert |
| P86 | 3.7 | Légifrance fermé aux programmes | ZD | liens seulement ; décrets lus à la main dans les ZD | doc. 1, 1.3.3 | couvert |
| P87 | 3.8 | 11 formats ; UTF-16 sans en-tête ; exécution 2021-2022 en PDF ; 2023-2025 sans ministère ; exercice sans code ; décalage d'un an | E2, E3 | découpeur par format (empreinte de schéma) ; exécution 2021-2022 en PDF : `non_collecte` ; ministère `null` + raison ; format large remis en long | doc. 2, 2.2 ; doc. 1, 1.4 G | partiel : la règle de recalage du « décalage d'un an » attend la lecture des jeux (non mesuré) (T21) |
| P88 | 3.8 | Budget de l'année : seulement sur `budget.gouv.fr` | E4 | `trou_source` | doc. 2, 2.2 | couvert (T21) |
| P89 | 3.8 | Licence à vérifier jeu par jeu | E1 | licence lue jeu par jeu dans le catalogue ; sans licence : non collecté | doc. 2, 2.2 ; doc. 1, 1.4 G | couvert (T21) |
| P90 | 3.8 | Drees : classeur renommé à chaque édition | E1 | classeur retrouvé sur la page du jeu à chaque édition | doc. 2, 2.2 | couvert (T21) |
| P91 | 3.8 | Dernière année provisoire | E3 | indicateur `provisoire` | doc. 1, 1.4 G | couvert (T21) |
| P92 | 3.8 | Republication silencieuse | E1, E2 | empreinte chaque semaine ; une révision devient une version | doc. 2, 2.2 ; doc. 1, 1.4 G | couvert |
| P93 | 3.8 | Ressources caisse par caisse non publiées | E4 | `trou_source` | doc. 1, 1.5.5 | couvert |
| P94 | 3.9 | Couverture à partir de 2020 | E4 | `borne_historique` | doc. 1, 1.5.5 | couvert |
| P95 | 3.9 | Aucun identifiant de personne | E4, ZD | nom, prénom, date de naissance + relecture | doc. 1, 1.6 R-IDENTITE | couvert |
| P96 | 3.9 | L'identifiant de ressource change | E1 | relu sur la fiche du jeu | doc. 2, 2.2 | couvert |
| P97 | 3.9 | Un même mandat dans deux fichiers | E3, E6 | dédoublonnage par (nom, prénom, naissance, collectivité, fonction, début) ; A4 | doc. 1, 1.4 G ; doc. 2, 2.8.2 | couvert (T22) |
| P98 | 3.9 | Années de naissance au mauvais siècle | E4 | date aberrante ou sentinelle : pas de rapprochement, `a_relire` | doc. 1, 1.6 R-IDENTITE ; doc. 2, 2.5 | couvert (T20) |
| P99 | 3.9 | Aucune date de fin de mandat | E3 | `null` + raison | doc. 1, 1.4 G | couvert |
| P100 | 3.9 | Erreurs 504 et 429 | E1 | nouvelles tentatives espacées | doc. 2, 2.2 | couvert |
| P101 | 3.9 | Le répertoire contient aussi les mandats parlementaires | E3 | ressources des mandats parlementaires non relevées | doc. 2, 2.2 ; doc. 1, 1.4 G | couvert (T22) |
| P102 | 3.10 | Wikipédia : source secondaire | ZD | ZD `candidature` avant publication | doc. 1, 1.3.3 | couvert |
| P103 | 3.10 | P4123 sans `PA` | E3 | `PA` rétabli | doc. 1, 1.2.1 | couvert |
| P104 | 3.10 | « Candidat à » : 1 candidat sur 30 | — | non utilisé | doc. 1, 1.4 A | couvert |
| P105 | 3.10 | P39 incomplète | — | non utilisée (fonctions lues dans AMO) | doc. 1, 1.4 A | couvert |
| P106 | 3.11 | Sycomore, tous droits réservés | E2 | faits + adresse + empreinte | doc. 1, 1.3.2 | couvert |
| P107 | 3.11 | Pas de fonctions ministérielles | E4 | AMO à partir de 2007, `borne_historique` avant | doc. 1, 1.5.1 | couvert |
| P108 | 3.11 | Dates différentes de quelques jours | E4 | dates d'AMO prioritaires sur la période commune ; Sycomore avant 2002 | doc. 1, 1.6 R-CARRIERE | couvert (T23) |

**Ce qui ne fonctionne pas (cahier 3.12).** Aucun collecteur ne vise ces points d'accès (doc. 2,
2.2). Ce qu'ils auraient apporté est déclaré en couverture, et ils sont eux-mêmes
déclarés sur la page des sources (doc. 1, 1.4 G ; T36).

| # | Point d'accès | Traitement | État |
| --- | --- | --- | --- |
| P109 | NosDéputés, NosSénateurs, `archive.nossenateurs.fr` | non utilisés | couvert |
| P110 | Sénat : scrutins, comptes rendus | votes et paroles du Sénat : `trou_source` | couvert (déclaré : T36) |
| P111 | Sénat : amendements (dump de 717 Mo), textes sans auteur | non utilisés | couvert (déclaré : T36) |
| P112 | PE : `www`, `/plenary-documents`, OEIL | non interrogés ; liens seulement | couvert |
| P113 | Légifrance, PISTE, JORFSearch, `budget.gouv.fr`, `docparl` | liens ou lecture à la main seulement | couvert |
| P114 | AMO10 (députés en cours seulement) | AMO30 utilisée ; AMO10 sert au recoupement (doc. 1, 1.6 R-BANC) | couvert |
| P115 | Archives XIIe-XIIIe ; CR de la XIVe | `borne_historique` (« pas de comptes rendus avant 2017 ») | couvert |
| P116 | Organismes extra-parlementaires (noms sans identifiant) ; RNE 2014 et 2020 sans licence | non utilisés ; mandats locaux bornés à 2020 | couvert |

### 8.3.2 Pièges révélés par les mesures du 04/11/2026

| # | Mesure | Piège nouveau | Étape | Traitement | Où | État |
| --- | --- | --- | --- | --- | --- | --- |
| N01 | an-acteurs §1.1 | Trois serveurs d'origine (`b2`, `f1`, `f2`), et non deux ; ETag = taille + date | E1 | `If-Range` sur l'ETag | doc. 2, 2.2 | couvert |
| N02 | an-acteurs §1.2 | Coupure à exactement 10 Mio, HTTP 200, même sur 13,7 Mo | E1 | `Content-Length` + test du zip | doc. 2, 2.2 | couvert |
| N03 | an-acteurs §2.5 | Le « vide » s'écrit de trois façons (`null`, `""`, `{"@xsi:nil":"true"}`) ; l'uid d'un acteur est un objet | E3 | normalisations communes des lecteurs | doc. 2, 2.5 | couvert (T15) |
| N04 | an-acteurs §2.1 | XVIIe : aucun des 14 GP ne déclare de position (AMO30 et AMO10 du 03/11/2026) | E4 | « non déclaré » (décision du 04/11/2026, doc. 5, Q2) ; périodes changées par le seul gouvernement | doc. 1, 1.6 R-BANC ; doc. 3, point 6 | couvert |
| N05 | an-acteurs §2.1 | La position n'est pas datée : elle vaut pour toute la vie de l'organe | E2, E4 | datée par les versions Z1 | doc. 1, 1.3.2 | couvert |
| N06 | an-acteurs §2.2 | 408 mandats MINISTERE sont des missions de parlementaires | E3 | écartés par leur qualité | doc. 1, 1.4 B | couvert |
| N07 | an-acteurs §2.2 | Appariement par `PM15` + numéro (652 sur 659), convention non documentée | E3 | `fonction_gouvernementale` | doc. 1, 1.4 B | couvert |
| N08 | an-acteurs §2.2 | 7 mandats GOUVERNEMENT ouverts dans le gouvernement Bayrou, clos le 09/09/2025 | E6 | hors composition (R-COMPOSITION) ; A8 « mandat ouvert dans un organe clos » | doc. 1, 1.6 ; doc. 2, 2.8.2 | couvert (T12) ; doc. 5, Q23 |
| N09 | an-acteurs §2.2 | Délégué → tutelle : aucun champ ; 322 libellés « auprès » sur 758, avec coquilles | E4, ZD | R-COMPOSITION + ZD | doc. 1, 1.6 | couvert |
| N10 | an-acteurs §2.2 | Succession des ministères seulement depuis Borne (149 organes) | E4 | dit dans R-COMPOSITION | doc. 1, 1.6 | couvert |
| N11 | an-acteurs §2.3 | Mandat de reprise : `dateDebut` = début du mandat d'origine ; vraie date = `datePriseFonction` (113 sur 113) | E3 | `mandat_suspension` | doc. 1, 1.4 B | couvert |
| N12 | an-acteurs §2.4 | Siège réécrit : figée XVIe 591, dont 323 différents et 202 effacés dans la courante | E2, E4 | R-ARBITRAGE-ARCHIVES | doc. 1, 1.3.2, 1.6 | couvert |
| N13 | an-acteurs §6 | Figée XVe datée du 09/06/2022, **avant** la fin (567 mandats sans date de fin) | E4 | archive figée retenue seulement si postérieure à la clôture | doc. 1, 1.6 | couvert |
| N14 | an-acteurs §6 | Mandats supprimés à la source : 99 (figée XVIe) et 402 (figée XVe) | E2, E4 | remplacé dans la courante → correction (l'ancien est retiré) ; sans remplaçant → retrait à la source, nommé au rapport, accepté par C1 (décision du 04/11/2026, doc. 5, Q4) | doc. 1, 1.6 R-ARBITRAGE | couvert |
| N15 | an-acteurs §6 | L'AMO30 figée XVe n'est pas listée sur la page des archives (trouvée par HEAD) | E1, config | chemin saisi en configuration, vérifié par HEAD à chaque relevé | doc. 2, 2.2 | couvert (T14) |
| N16 | an-acteurs §6 | L'AMO20 XIVe (mars 2018) porte des sièges de 2018, pas ceux de la XIVe | E4 | R-ARBITRAGE : siège XIVe tiré du seul fichier des places | doc. 1, 1.6 | couvert (T13, X3) |
| N17 | an-acteurs §6 | `Agenda_XIV` ne couvre que du 20/06/2017 au 21/12/2018 | E2, E4 | même uid = même objet que dans l'agenda XVe | doc. 1, 1.3.2 | couvert : borne de l'ordre du jour XIVe, doc. 1, 1.5.5 (T16) |
| N18 | an-acteurs §4 | 984 réunions de 68 organes absents d'AMO (agenda XVIIe) | E3, E4 | « organe non référencé », sans lien | doc. 1, 1.4 D | couvert (T17) |
| N19 | an-acteurs §2.4 ; mes. amendements §1 | Republication aussi en journée (agenda à 11 h 41 GMT, amendements à 15 h 20 GMT) | E1 | relevé le soir ; « à jour au » = date de la source | doc. 2, 2.3 | couvert |
| N20 | an-acteurs §5 | QG : question et réponse dans un seul bloc HTML | E3 | bloc gardé tel quel ; paroles séparées par R-QAG | doc. 1, 1.4 C | couvert (T15) |
| N21 | an-acteurs §6 | AMO50 figée depuis le 11/07/2024 | — | non utilisée | doc. 1, 1.4 B (AMO30) | couvert |
| N22 | an-scrutins §2.5 S1 | XIVe : 710 scrutins (17/07/2012 → 26/02/2014) ne nomment que les dissidents | E4 | R-NOMINATIF : « position non nominative » | doc. 1, 1.6 | couvert : exclus de A3, doc. 2, 2.8.2 (T09) |
| N23 | an-scrutins §2.5 S2 | Archive XIVe des scrutins tronquée au 24/11/2016 ; au moins 10 scrutins cités par les dossiers sont absents | E4, E6 | `trou_source` après le 24/11/2016 ; scrutins cités servis sans lien | doc. 1, 1.5.5 | couvert (T10) |
| N24 | an-scrutins §2.2 | Libellé du type MOC = « scrutin public solennel » en XV-XVI | E3 | type lu par `codeTypeVote` | doc. 1, 1.4 C, 1.6 R-NATURE-SCRUTIN | couvert (T07) |
| N25 | an-scrutins §2.2 | `nonVotantsVolontaires` à 0, sans liste ; non-votants = PAN, PSE, MG (pas des absents) | E3 | non-votant gardé comme position | doc. 1, 1.4 C | couvert : cause du non-vote, doc. 1, 1.4 C (T42) |
| N26 | an-scrutins §2.5 S3 | 14 scrutins XVIIe ont des lignes de groupe `PO0` (146 lignes) | E4 | groupe reconstruit depuis l'appartenance à la date (R-POSITION-GROUPE) | doc. 1, 1.6 | couvert : exclus de A3 (doc. 2, 2.8.2) ; R-APPARTENANCE (T09) |
| N27 | an-scrutins §2.5 S4 | L'organe d'un groupe fait des allers-retours dans les scrutins (SOC XVIe) | E4 | appartenance lue dans les mandats ; maillon = chaîne d'organes | doc. 1, 1.6 R-APPARTENANCE | couvert (T09) |
| N28 | an-scrutins §2.5 S5 | XVe : les numéros 3 781 et 3 782 manquent | E4 | contrôle de continuité → `trou_source` | doc. 1, 1.5.5 | couvert (T10) |
| N29 | an-scrutins §2.5 S8 | Apostrophes typographiques et coquilles dans les intitulés | E4 | normalisation + exceptions décidées | doc. 1, 1.6 R-NATURE-SCRUTIN | couvert |
| N30 | an-scrutins §2.4 | `miseAuPoint` présent partout (`[null, null]`) ; `nonVotants` chaîne (XIV) ; `parDelegation` chaîne | E3 | lecteur ; « bloc présent ≠ mise au point » | doc. 2, 2.5, 2.12 | couvert |
| N31 | an-scrutins §2.2 | Trois jeux de clés (XIV ; XV-XVII ; Congrès XVI) + variantes dans les décomptes | E3 | table de correspondance | doc. 2, 2.4 | couvert |
| N32 | an-scrutins §3.3 | Seuls 84 des 241 scrutins « ensemble » (XVIIe) ont une référence de dossier | E4 | routes 2 et 3 : 225 sur 225 reliés | doc. 1, 1.6 | couvert |
| N33 | an-scrutins §4.1 | L'archive « XIV » contient 102 documents de la XVe | E2 | un objet, plusieurs archives | doc. 1, 1.3.2 | couvert |
| N34 | an-scrutins §3.2 | « Partie » d'un texte financier ; ensemble sans le mot ; résolutions 34-1 | E4 | nature `partie_de_texte` ; « ensemble » sans le mot | doc. 1, 1.6 R-NATURE-SCRUTIN | couvert (T06) ; résolutions : doc. 5, Q20 |
| N35 | an-scrutins §4.3 | Dossiers saisis au seul Sénat (521 en XVIIe) | E4 | matière « saisi au Sénat seulement » | doc. 1, 1.6 R-MATIERE | couvert (décision du 04/11/2026, doc. 5, Q19) |
| N36 | an-scrutins §4.3 | 49.3 : seules 5 des 16 décisions XVIIe le disent dans la conclusion | E4 | acte `DeclarationGouvernement_Type`, `fam_code = Art.49.3` | doc. 1, 1.6 R-SORT-FINAL | couvert (T02, X4) |
| N37 | an-amendements §3.1 | Dossier `incorrect_data/` : 170 amendements hors de leur dossier | E2 | découpage par uid, jamais par chemin | doc. 2, 2.4 | couvert (T05) |
| N38 | an-amendements §3.2 | 346 paires de copies `B` / `BTC`, identiques (XVIIe) | E3, E4 | clé (`examenRef`, `numeroLong`), copie `BTC` retenue, autre uid en alias | doc. 1, 1.6 R-AMENDEMENT | couvert (T05, X5) |
| N39 | an-amendements §3.5 | 23 669 irrecevables sans exposé ni dispositif ; 11 528 discutés sans dispositif | E3, E5 | `null` + raison | doc. 1, 1.0 principe 4 | couvert : couverture du filtre, doc. 1, 1.5.5 (T31) |
| N40 | an-amendements §3.4 | `sort` rempli pour « Discuté » seulement ; sous-état « R » muet | E4 | R-SORT-AMENDEMENT : « sort non établi » | doc. 1, 1.6 | couvert |
| N41 | an-amendements §3.2 | Un doublon dans une liste de cosignataires ; 4 amendements de député sans auteur | E3 | clé (amendement, personne) ; `null` + raison | doc. 1, 1.4 C | couvert |
| N42 | an-amendements §5.3 | `PA0` (603 paragraphes), identifiants négatifs (315), repli `PA793214` (13), nom ≠ identifiant (39) | E4 | R-ORATEUR | doc. 1, 1.6 | couvert |
| N43 | an-amendements §5.3 | `roledebat` manque sur 60 275 des 110 110 paragraphes de présidence | E4 | présidence reconnue aussi par le libellé | doc. 1, 1.6 | couvert |
| N44 | an-amendements §5.2 | `qualite` vide pour 82 % des paragraphes attribués | E4 | R-QUALITE : qualité du compte rendu, sinon fonctions à la date | doc. 1, 1.6 | couvert (T01) ; doc. 5, Q21 |
| N45 | an-amendements §5.4 | `id_syceron` stable à 97-99 % ; texte retouché en place ; `stime` absent des CR provisoires | E2, E3 | clé `id_syceron` ; texte rechargé à chaque version ; empreinte sans `stime` | doc. 1, 1.2.2 | couvert |
| N46 | an-amendements §5.4 | CR provisoire partiel : 407 interventions dans l'archive, 1 263 en ligne (`…N051`) | E4 | `compte_rendu.statut` | doc. 1, 1.4 D | couvert : séance `en_cours`, doc. 1, 1.5.5 (T31) |
| N47 | autres-sources §1 | JO : la livraison de nuit ne porte que des citations ; les liens riches arrivent le soir | E2 | la dernière version d'un `ID` remplace la précédente | doc. 1, 1.3.2 | couvert |
| N48 | autres-sources §1 | JO : `MINISTERE` vide sur 17 à 26 % des actes (3 livraisons) ; les lois n'ont pas de ministère | E4 | « ministère non précisé » | doc. 1, 1.6 | couvert |
| N49 | autres-sources §2 | `parltrack.org/dumps` sans barre finale → 502 | E1 | adresse avec barre | doc. 2, 2.2 | couvert |
| N50 | autres-sources §3 | PE : fin de pagination = 204 sans corps ; ni ETag ni Last-Modified | E1 | 204 ≠ silence ; empreinte | doc. 2, 2.2 | couvert |
| N51 | autres-sources §3 | PE : un groupe est une référence (`org/7150`) ; un changement de rôle crée une nouvelle appartenance | E1, E3 | libellés lus dans `corporate-bodies/{id}` ; changement de rôle = nouvelle appartenance | doc. 2, 2.2 ; doc. 1, 1.4 F | couvert (T26) |
| N52 | autres-sources §4 | Sénat : 95 tables ; ETag et date changent chaque nuit | E1, E2 | 95 tables ; comparaison des objets par empreinte | doc. 2, 2.2 ; doc. 3, J2 | couvert |
| N53 | autres-sources §4, §6 | Wikidata P1808 = chemin de la fiche (`…86039k`), pas le matricule | E3 | matricule = fin du chemin, en majuscules | doc. 1, 1.2.1 | couvert (T24) |
| N54 | autres-sources §6 | Libellés Wikidata non fiables (« Q5829 ») | — | seuls les identifiants sont utilisés | doc. 1, 1.4 A | couvert |
| N55 | autres-sources §5 | Wikipédia : formes variables (`TriNom`, lien direct, `nolink`) ; homonymies ; 29 candidats à la révision 240980797 | E1, E4 | ZD `candidature` | doc. 1, 1.3.3 | couvert : contrôle de complétude et homonymies, doc. 2, 2.2 (T25) |
| N56 | autres-sources §7 | RNE : `Last-Modified` différent de la date du catalogue | E1 | empreinte | doc. 2, 2.2 | couvert |
| N57 | autres-sources §7 | Séries longues budgétaires : API limitée à 2024-2026, une colonne de plus par mois ; situation mensuelle = liens vers des PDF | E1, E3 | format large remis en long ; séries antérieures à 2024 en `trou_source` | doc. 1, 1.4 G ; doc. 2, 2.2 | couvert (T21) |
| N58 | autres-sources §7 | EuroVoc : `inScheme` renvoie aussi le schéma global `100141` | E3 | schéma `100141` exclu | doc. 1, 1.4 F | couvert (T26) |
| N59 | autres-sources §9 | GitHub Pages : 1 Go est une limite ; un déploiement échoue au-delà de 10 min | E7 | taille contrôlée avant envoi ; fichiers servis en `.json.gz` (≈ 0,21 Go, doc. 4) | doc. 2, 2.9 ; doc. 1, 1.7.1 | partiel : délai de 10 min (doc. 4) |
| N60 | autres-sources §9 | `schedule` parfois abandonné ; désactivé après 60 jours d'inactivité | E0 | deux déclenchements ; alerte `planification` ; commit nocturne | doc. 2, 2.3 | couvert (un commit du robot compte-t-il comme activité ? non documenté : l'alerte le surveille) |
| N61 | autres-sources §9 | `concurrency` : une seule exécution en attente, la suivante l'annule | E0 | `concurrency` avec `queue: max` | doc. 2, 2.1 | couvert (T37) |
| N62 | autres-sources §9 | *Releases* : 1 000 fichiers au plus par *release* | E2, E7 | segments plafonnés à 90 Mo, une *release* d'entrepôt par année | doc. 2, 2.4, 2.9 | couvert ; nombre : doc. 4 |
| N63 | autres-sources §9 | Artefacts : 500 Mo inclus ; gratuité non dite pour un dépôt public | E7 | la candidate n'est plus gardée en artefact : recalculée hors de la fenêtre interdite ; artefacts : déploiement Pages et essais | doc. 2, 2.9, 2.12 | partiel : gratuité à vérifier (doc. 4) |

### 8.3.3 Pièges du cahier infirmés ou dépassés par les mesures

| # | Cahier | Ce que dit le cahier | Mesure du 04/11/2026 | Conséquence | Où | État |
| --- | --- | --- | --- | --- | --- | --- |
| I01 | 3.4, 6.0 | Parltrack : quotidien, trois jours conservés | Aucun fichier changé depuis le 24/07/2026 (`ep_votes` arrêté au 26/03/2026) ; `dumps/arch/` garde 3 492 instantanés depuis 2019 | famille affichée « source figée depuis le … » ; la priorité de Parltrack au premier remplissage (doc. 2, 2.13) n'a plus de raison | doc. 2, 2.2, 2.13 | couvert (X1 corrigé) |
| I02 | 3.1.3 | Les copies d'un amendement divergent | 346 paires XVIIe identiques (hors uid, date, `chronotag`) | la divergence passe par **l'archive courante qui réécrit** l'unique copie (scénario 8.5.1) | doc. 1, 1.3.2 | couvert : doc. 1, 1.6 R-AMENDEMENT (T05) |
| I03 | 3.6 | Le signataire d'un acte n'est jamais publié | `SIGNATAIRES` rempli en texte libre (153 actes sur 169, livraison du 02/11/2026) | non utilisé : la règle de 4.6 (« jamais à une personne ») est ferme | doc. 3, point 6 | collecté et servi tel quel avec l'acte, sans identifiant de personne ; affichage décidé par l'interface, la règle de 4.6 s'appliquant au site (décision du 04/11/2026, doc. 5, Q11) |
| I04 | 3.6 | Panne de trois jours en octobre 2026 | aucun jour sans livraison en octobre 2026 | le rattrapage reste utile | doc. 2, 2.2 | couvert |
| I05 | 3.3 | `data` arrive en objet | toujours une liste sur 12 réponses | la normalisation est gardée | doc. 2, 2.12 | couvert |
| I06 | 3.3 | VIIe législature : 404 | `/meps?parliamentary-term=7` → 200 en 7,7 s | couverture établie point d'accès par point d'accès | doc. 1, 1.5.5 | couvert |
| I07 | 3.3 | Limitation de débit muette | non observée sur 13 requêtes | délai d'attente gardé | doc. 2, 2.2 | couvert |
| I08 | 3.2 | 93 tables | 95 | plancher à 95 | doc. 2, 2.2 | couvert |
| I09 | 3.1.7 | 9 578 séances citées par les scrutins XVIIe | 553 séances distinctes | aucun effet sur la route « séance » | doc. 1, 1.6 | couvert |
| I10 | 3.1 | Une archive figée = état de fin | figée XVe prise 12 jours avant la fin | R-ARBITRAGE vérifie la date | doc. 1, 1.6 | couvert |
| I11 | 3.1 | Deux serveurs, deux versions | non reproduit en journée ; trois serveurs, même ETag | `If-Range` garde son sens (fenêtre de nuit) | doc. 2, 2.2 | couvert |
| I12 | 3.1.2 | 1 354 scrutins XIVe | archive tronquée au 24/11/2016 : ce n'est pas le total de la XIVe | N23 | doc. 1, 1.5.5 | couvert (T10) |
| I13 | 5.2 | 1 Go de site « recommandé » | c'est une limite | contrôle avant envoi | doc. 2, 2.9 | couvert |
| I14 | 3.10 | 30 candidats déclarés | 29 à la révision 240980797 (03/11/2026) | le compte se relit à chaque révision | doc. 2, 2.2 | couvert |
| I15 | 3.1.3, 3.1.5 | Tailles en Mo | ce sont des Mio ; amendements XVIIe passés de 283 Mio (22/09/2026) à 335,6 Mio (03/11/2026) | chiffres de volume | doc. 4 | renvoi |

---

## 8.4 Exigence → mécanisme

### 8.4.1 Exigences de la partie 6

| # | Exigence | Mécanisme | Où | État |
| --- | --- | --- | --- | --- |
| E01 | 6.0 Partir de l'acquis ; ne recollecter que ce qui a pu changer | Z0/Z1 dans l'entrepôt ; requête conditionnelle, `HEAD` ou empreinte ; nouvelle version seulement si l'empreinte change | doc. 1, 1.1, 1.3.2 ; doc. 2, 2.2, 2.4 ; doc. 3, J1, J2 | couvert |
| E02 | 6.0 L'acquis reste, même si la source efface | Z0, Z1, ZD conservées ; un retrait marque l'objet sans l'effacer ; entrepôt hors de la source | doc. 1, 1.1 ; doc. 3, J4 | couvert (sauvegarde : décision du 04/11/2026 ; fréquence : doc. 5, Q16) |
| E03 | 6.0 Retrait à la source ≠ panne ; le site le dit | seul un relevé complet fait constater un retrait ; une panne donne la couverture `panne depuis le …` ; les retraits sont nommés dans le compte rendu public | doc. 1, 1.3.1 ; doc. 2, 2.4, 2.10, 2.11 ; doc. 3, J3 | couvert : retrait à l'intérieur d'un objet, doc. 2, 2.8.1 C1 (T03) |
| E04 | 6.0 Un état qui évolue est mis à jour | nouvelle version → E3 → recalcul complet en E4 | doc. 2, 2.5, 2.6 | couvert |
| E05 | 6.0 Correction et champ ajouté atteignent l'historique | cache (empreinte, version du lecteur) : un nouveau lecteur relit Z1 | doc. 1, 1.8 ; doc. 2, 2.5 | partiel : les sources « faits seulement » exigent de relire les pages (doc. 1, 1.3.2) ; X2 corrigé (doc. 2, 2.5 relit toutes les versions) |
| E06 | 6.0 Le travail long avance ; ce qui n'est pas fait se publie comme tel | chantiers, budget de 5 h 15, couverture `en_cours` | doc. 2, 2.0, 2.1 | couvert |
| E07 | 6.0 Forcer une relecture complète | mode `complet` | doc. 2, 2.12 | couvert |
| E08 | 6.0 Construire à partir de rien | chantiers ordonnés | doc. 2, 2.13 ; doc. 4 | couvert (X1 corrigé) |
| E09 | 6.1 Candidatures relevées automatiquement ; identité validée avant publication | collecteur Wikipédia (par révision) ; ZD `candidature`, `identite` ; aucune fiche tant que l'identité n'est pas validée ; A7 | doc. 2, 2.2 ; doc. 1, 1.3.3, 1.6 | couvert : contrôle de complétude, doc. 2, 2.2 (T25) |
| E10 | 6.1 Groupe nouveau rattaché par la règle | R-FILIATION ; `a_trancher` → ZD ; A7 | doc. 1, 1.6 ; doc. 2, 2.6 | couvert ; statut d'un groupe en attente de décision : doc. 5, Q22 (T40) |
| E11 | 6.1 Sortie pour une raison établie ; plus mise à jour ; données gardées | ZD `perimetre` ; population bornée avec sa raison ; Z1 gardé | doc. 1, 1.3.3, 1.5.1 | couvert : relevés propres arrêtés, doc. 2, 2.1 point 5 (T39) |
| E12 | 6.1 Aucune personne attendue écartée en silence | R-PERIMETRE ; contrôle bloquant C7 | doc. 1, 1.6 ; doc. 2, 2.8.1 | couvert (T04) |
| E13 | 6.1 L'adresse d'une fiche ne change pas | registre des adresses (ajout seul) ; redirections ; C2 | doc. 1, 1.2.2 ; doc. 2, C2 | couvert |
| E14 | 6.2 Anomalies | voir 8.4.2 | doc. 2, 2.8 | voir 8.4.2 |
| E15 | 6.3 Mise à jour chaque soir, qui collecte tout | `schedule` à 19 h 30 et 21 h 30 Europe/Paris ; alerte `planification` au-delà de 26 h ; « tout » = toutes les sources interrogées | doc. 2, 2.3 ; doc. 3, point 1 | couvert |
| E16 | 6.3 Lancement manuel aux options lisibles | `workflow_dispatch` à listes de choix | doc. 2, 2.12 | couvert (refusé entre 9 h et 19 h les jours ouvrés) |
| E17 | 6.3 Essai sur quelques personnes | mode `essai` ; `empreinte essai --hors-ligne` | doc. 2, 2.12 | couvert |
| E18 | 6.3 Erreur de lancement signalée tout de suite | E0 valide les options ; cause en tête du résumé + alerte | doc. 2, 2.1 | couvert |
| E19 | 6.3 Jamais deux mises à jour à la fois | `concurrency` avec `queue: max` + numéro de génération | doc. 2, 2.1 | couvert (T37) |
| E20 | 6.3 Le développement continue ; données = code publié | étiquettes `publiable` → `code-publie` ; import le soir ; `recalcul` | doc. 2, 2.12 ; doc. 3, J20 | couvert |
| E21 | 6.3 Une interruption ne coûte pas tout | E1-E2 persistées par source ; cache E3 | doc. 2, 2.11 ; doc. 3, J15 | couvert |
| E22 | 6.3 État précédent complet ou nouveau complet | préfixe `/donnees/<id-publication>/` ; une 404 recharge la page | doc. 1, 1.7.2 ; doc. 2, 2.9 | couvert |
| E23 | 6.3 Sans geste humain | `deploy-pages` | doc. 2, 2.9 | couvert |
| E24 | 6.3 Une publication = données + code seulement | — | doc. 2, 2.9 | couvert |
| E25 | 6.3 Le code n'écrase jamais les données | une publication d'interface reprend les données de la dernière publication | doc. 2, 2.12 | couvert |
| E26 | 6.3 Compte rendu de chaque mise à jour | `/rapports/<date>.json` + résumé de la tâche | doc. 2, 2.10 | couvert |
| E27 | 6.3 Alertes : une par sujet, sans répétition | issues du dépôt privé, clé de sujet stable | doc. 2, 2.10 ; doc. 3, J19 | couvert |
| E28 | 6.3 Journaux publics conformes aux règles | indices de contrôle en local seulement ; le rapport ne donne que des comptes et des identifiants | doc. 2, 2.8.3, 2.10 | couvert : catalogue fermé de messages, doc. 2, 2.10 (T38) |
| E29 | 6.3 Test sans réseau sur extraits réels | transport remplaçable ; extraits datés et sourcés ; fichiers de référence | doc. 2, 2.12 | couvert |
| E30 | 6.4 Ajouter une source, un champ, un type de fiche sans réécriture à la main | collecteur, découpeur, lecteur, composeur et schéma ajoutés ; Z0-Z1 intacts | doc. 1, 1.8 ; scénario 8.5.3 | couvert |
| E31 | 6.4 XVIIIe sans réécrire le traitement | configuration ; variantes de schéma détectées | doc. 1, 1.8 ; scénario 8.5.4 | couvert : détection et alerte, doc. 1, 1.8 ; A7 (T40) |

### 8.4.2 Chaque anomalie de 6.2 : contrôle, moment, avertissement

Moment commun : E6 tourne après E5, sur la candidate complète, et avant E7. Un refus laisse le site
dans son état précédent complet (doc. 2, 2.11). Moyens d'avertir (doc. 2, 2.10) : une **issue
privée** par sujet (notification GitHub, rien quand rien ne change), le **compte rendu public**
`/rapports/<date>.json` et le résumé de la tâche.

| Anomalie (cahier 6.2) | Contrôle | Moment | La propriétaire est avertie par | Levée |
| --- | --- | --- | --- | --- |
| **Bloquant** : perd des faits sans explication (faits nommés) | C1 : différence fait par fait avec la dernière publication | E6 | issue `controle:C1` avec les faits nommés (identifiant, fiche, famille) ; rapport « non publiée » | ZD `levee_controle` sur l'empreinte de l'anomalie, pour une publication |
| **Bloquant** : lien vers un objet absent | C2 : chaque lien vise un fichier de la candidate ou une adresse du registre | E6 | issue `controle:C2` | idem |
| **Bloquant** : données collectées laissées de côté | C3 : lu = servi + écarté avec sa raison | E6 | issue `controle:C3` | idem |
| **Bloquant** : donnée interdite | C4 : schéma en liste blanche + motifs interdits | E6 | issue `controle:C4` | idem |
| **Bloquant** : lecture incomplète présentée comme complète | C5 : `complet` exige le dernier relevé complet de chaque source contributrice | E6 | issue `controle:C5` | idem |
| **Bloquant** : objets tombés à zéro d'un coup | C6 : une famille à zéro pour tout un type de fiche, ou en baisse de plus de 20 % sans retrait constaté | E6 | issue `controle:C6` | idem |
| **Bloquant** : personne attendue écartée en silence (6.1) | C7 : chaque personne attendue (R-PERIMETRE) est servie ou sortie avec une raison | E6 | issue `controle:C7` avec les personnes nommées | idem |
| **Avertissement** : fiche hors modèle (par décision) | A1 | E6 | issue par sujet ; rapport | — (décision `fiche_hors_modele`, doc. 1, 1.3.3 ; T41) |
| **Avertissement** : faits tirés au sort ≠ autre route | A2 : 40 faits (votes, sorts, mandats, dates) relus sur les pages publiques de l'AN | tirage en E1, comparaison en E6 | issue avec le fait et l'adresse | — |
| **Avertissement** : un total diffère d'une autre source | A3 : effectif de chaque groupe à chaque scrutin ; lois promulguées comparées au JO | E6 | issue par sujet | — (scrutins XIVe à dissidents seuls et lignes `PO0` exclus : T09) |
| **Avertissement** : un objet risque de s'afficher deux fois | A4 : copies d'amendement, dossiers XIVe réapparus, CR XVe dans la XVIe, loi et son rectificatif | E6 | issue par sujet | — (doublons RNE compris : T22) |
| **Avertissement** : famille à zéro pour tout le monde | A5 (famille nouvelle ou optionnelle) | E6 | issue par sujet | — |
| **Avertissement** : couverture insuffisante | A6 : candidats sans fiche, personnes sans parole sur une période couverte, groupes trop peu couverts | E6 | issue par sujet | — (seuil : doc. 5, Q1) |
| **Avertissement** : entrées non résolues, relectures | A7 : files de relecture (E4), décisions qui ne s'appliquent plus | E4 → E6 | issue `relecture:<file>` | — |
| **Avertissement** (ajouté) : mandat ouvert dans un organe clos | A8 | E6 | issue par sujet | — |
| **À la main** : audit, indices de contrôle | `empreinte audit` : volumes, complétude, cohérence, fraîcheur, cohésion et participation individuelles | à la demande, sur la machine de la propriétaire | sortie locale, hors dépôt, jamais dans les journaux publics | — |

Une levée est un commit sur le dépôt public : elle respecte la fenêtre (pas entre 9 h et 19 h
du lundi au vendredi, hors fériés) et prend effet à la mise à jour suivante.

---

## 8.5 Scénarios déroulés

Dates et identifiants **fictifs**, choisis pour l'exemple. Les heures sont celles de Paris.

### 8.5.1 Un cosignataire se retire d'un amendement

Situation : l'amendement `AMANR5L17PO420120B1234P0D1N000056` (fictif), déposé par A, cosigné
par B, C et D. B retire sa signature le jeudi 12/11/2026. Mesure utile : dans l'archive XVIIe
du 03/11/2026, le retrait se lit dans l'**unique copie réécrite** ; les 346 paires de copies
`B`/`BTC` ne divergent pas (I02).

| Étape | Ce qui se passe | La propriétaire voit | Le lecteur voit |
| --- | --- | --- | --- |
| Avant | Publication du 11/11 : `signature(AM…N000056, B)` est servie dans le jeu téléchargeable (`signatures`) et comptée « à part » dans la lignée de B (`proposes.json`) | — | la signature de B |
| Nuit du 12 au 13 | L'AN republie l'archive (heure variable : N19) | — | inchangé |
| 13/11 19 h 30, E0-E1 | Requête conditionnelle → nouvel ETag ; téléchargement vérifié (`Content-Length`, zip) → relevé `nouveau`, `complet`. Si l'archive est coupée → relevé `echec` : **rien ne change**, nouvelle tentative le lendemain (doc. 2, 2.2, 2.11) | si l'échec dure, une issue `panne:an-amendements` | inchangé |
| E2 | Découpage **par uid**, pas par chemin (doc. 2, 2.4 : un déplacement vers `incorrect_data/` n'est pas un retrait). L'empreinte de l'amendement change → version 2 ; la version 1 est gardée (`vu_jusqu_au` = 12/11) | — | — |
| E3 | Le lecteur produit les lignes `signature` de la version 2, sans B. S'il existe deux copies et qu'elles divergent, R-AMENDEMENT retient la copie de la clé (`examenRef`, `numeroLong`) dont le texte égale celui de l'examen (doc. 1, 1.6) et A4 signale le double | — | — |
| E4 | `amendement_canonique` ne change pas : il compte toujours une fois. La signature de B disparaît ; les signatures de son groupe baissent de 1 | — | — |
| E5 | Composition déterministe : seuls les fichiers touchés changent (`proposes.json` de la lignée de B, table `signatures` du jeu) | — | — |
| E6 | C1 voit disparaître le fait `signature(…, B)` et l'accepte : son objet source a une nouvelle version, issue d'un relevé complet, qui ne le porte plus (retrait à l'intérieur d'un objet, doc. 2, 2.8.1 C1 ; T03) | rien | — |
| E7 | Publication après 19 h, préfixe `/donnees/<id>/` neuf ; une ligne au registre | — | la nouvelle publication complète, d'un seul coup |
| E8 | Compte rendu public : « retraits : 1 signature (AM…N000056 / B), retrait à la source, version 2 du 13/11/2026 » ; aucune alerte | le rapport du 13/11 | `/rapports/2026-11-13.json` ; le compte de la lignée daté du 13/11 ; B absent de la liste des cosignataires du jeu |
| Après | Z1 garde les deux versions ; le registre et le magasin gardent la publication du 11/11 | peut prouver ce que le site publiait le 11/11 | — |

### 8.5.2 Le portail du Parlement européen ne répond plus pendant deux jours

Situation : `data.europarl.europa.eu` reste muet le mardi 17/11 et le mercredi 18/11/2026. Il
répond de nouveau le jeudi 19/11. Les personnes du volet européen sont relevées
chaque soir (doc. 2, 2.3). Parltrack, lui, est un collecteur distinct, figé depuis le 24/07/2026
(I01).

| Moment | Ce qui se passe | La propriétaire voit | Le lecteur voit |
| --- | --- | --- | --- |
| 17/11 19 h 30, E1 | Les requêtes tombent dans le délai d'attente de 30 s ; le débit ralentit ; trois tentatives (30 s, 2 min, 10 min) → relevé `echec` (« silence »). Les autres collecteurs continuent, isolés (doc. 2, 2.2) | — | — |
| E2 | Rien ne change dans Z1 pour le PE ; aucun retrait, puisque le relevé est incomplet (doc. 1, 1.3.1) | — | — |
| E3-E4 | Les faits européens restent ceux du dernier relevé complet (16/11). R-COUVERTURE : famille Europe en `panne` depuis le 17/11, dernier succès le 16/11 | — | — |
| E5 | `fraicheur.pe` = « 2026-11-16 (panne depuis le 2026-11-17) » ; couverture de la section Europe ; état de la source dans `sources.json` | — | — |
| E6 | C1 : aucun fait perdu. C5 : satisfait, puisque le statut est `panne` et non `complet`. C6 : rien | — | — |
| E7-E8 | Publication (mardi après 19 h : autorisé) ; issue `panne:pe` ouverte **une fois** ; rapport « source en panne depuis le 17/11 » | **une** notification | fiche d'un candidat ancien eurodéputé : données européennes au 16/11, et dans « Ce qu'on n'a pas pu lire » : « Parlement européen : panne depuis le 17/11/2026 » ; page des sources : panne |
| 18/11 | Même chose ; l'issue ne change pas, donc pas de notification (doc. 2, 2.10) | rien de neuf | même mention, toujours « depuis le 17/11 » |
| 19/11 | Le portail répond ; pagination menée jusqu'au 204 ; relevé `complet` ; nouvelles versions si les empreintes changent ; couverture `complet` ; issue fermée | fermeture de l'issue ; rapport « panne close » | la mention de panne disparaît ; « à jour au 19/11 » |
| Variante | Le portail se tait au milieu de la pagination : relevé `complet = false`, aucun retrait (doc. 1, 1.3.1). Une réponse 204 est une fin, un silence ne l'est pas (N50) | idem | idem |

### 8.5.3 Ajouter un champ à tout l'historique

Exemple : la **cause d'un non-vote** (`causePositionVote` : PAN président de l'Assemblée, PSE
président de séance, MG membre du gouvernement ; mes. an-scrutins §2.2). Elle permet de ne pas
compter comme votes les 9 834 non-votes de fonction de Yaël Braun-Pivet, sur ses 10 976
positions de la XIVe à la XVIIe (archives du 04/11/2026). Ce champ est désormais prévu dès la
conception (doc. 1, 1.4 C ; T42) : le scénario montre comment il se serait ajouté.

| Étape | Ce qui se passe | La propriétaire voit | Le lecteur voit |
| --- | --- | --- | --- |
| Développement (dépôt privé) | Le lecteur `scrutin` passe à la version suivante et ajoute `cause_non_vote` (`null` + raison quand la source ne la porte pas). Le schéma de `votes.json` passe de 1.0 à 1.1, une version mineure (doc. 1, 1.8). Tests sur des extraits réels des quatre législatures ; fichiers de référence mis à jour (doc. 2, 2.12) | revue sur le dépôt privé | — |
| Étiquette | `publiable` posée quand elle veut | — | — |
| Soir (hors fenêtre) | Le dépôt public importe le code (`code-publie`) puis lance un `recalcul` : aucune collecte (doc. 2, 2.12) | — | — |
| E3 | Le cache (empreinte, version du lecteur) ne correspond plus pour aucun scrutin : relecture depuis Z1 de 19 455 scrutins (XIV-XVII, archives du 04/11/2026), sans réseau ; toutes les versions conservées sont relues (doc. 2, 2.5 ; X2 corrigé) | — | — |
| E4 | Recalcul complet. Si une règle utilise le champ (compteurs sans non-votes de fonction), elle change de version et la méthodologie publie l'ancienne et la nouvelle | — | — |
| E5-E6 | Tous les `votes.json` changent. C1 : aucun fait perdu. C3 : bilan équilibré. C4 : le schéma 1.1 admet le champ | rapport : « lecteur scrutin, version n+1 », faits ajoutés par famille | — |
| E7-E8 | Code et données publiés **ensemble** ; les articles datés gardent leur copie figée | rapport public | le champ apparaît sur toutes les fiches, pour tout l'historique |
| Limites | Champ d'une source « faits seulement » (Sycomore, Wikipédia) : chantier de relecture des pages (doc. 1, 1.3.2). Champ filtré en E2 (présences) : impossible, et interdit. Champ absent d'une ancienne version : `null` + raison | — | — |

### 8.5.4 Ajouter la XVIIIe législature

Situation : un décret de dissolution, puis des élections, puis l'ouverture de la XVIIIe ;
l'Assemblée crée `repository/18/…`.

| Étape | Ce qui se passe | La propriétaire voit | Le lecteur voit |
| --- | --- | --- | --- |
| Décret au JO | Collecté comme tout acte (E1, JO). Dans AMO : l'organe ASSEMBLEE XVII reçoit sa `dateFin` ; les mandats se ferment (« Fin de législature ») | alerte `legislature:17` et entrée de relecture (doc. 1, 1.8 ; A7) | fiche XVII : période close, « mode de fin non établi » |
| ZD | Décision `fin_legislature` (dissolution, lien Légifrance du décret), commitée hors fenêtre | — | mode de fin affiché |
| Archive XVII | Relevée une dernière fois, marquée `figee`, vérifiée par HEAD chaque mois (doc. 2, 2.2). R-ARBITRAGE ne retient ses sièges que si elle est postérieure à la clôture (I10) ; sinon, siège = dernier constat daté de l'archive courante avant la clôture (table `siege`) | — | hémicycle XVII |
| Configuration | Chemins `/18/` lus sur les pages de jeux et mis en configuration : un changement de code sur le dépôt privé → `publiable` → import du soir. Les noms ne sont jamais supposés (P01) ; une archive absente des pages se saisit en configuration, vérifiée par HEAD (doc. 2, 2.2 ; T14) | — | — |
| Premiers relevés | Empreinte de schéma : connue → lecture ; inconnue → relevé `suspect` + alerte, puis variante du lecteur | issue si le schéma change | — |
| Identifiants | `VTANR5L18V…`, `AMANR5L18…` : la grammaire vérifiée à la lecture (doc. 1, 1.2.1) doit accepter `L18` | — | — |
| Groupes | À l'ouverture, tous les députés passent par l'organe NI (P14) ; les GP 18 sont créés ; R-CONTINUITE-GROUPE ; R-FILIATION contre les groupes XVII → `suite`, `pas_suite` ou `a_trancher` | file `relecture:filiations` (A7) ; elle décide par ZD | un groupe `a_trancher` est publié comme sa propre lignée, « filiation en attente de décision » (doc. 5, Q22) |
| Bancs | Lus seulement s'ils sont déclarés ; sinon « non déclaré » (N04) | — | « non déclarée » |
| Gouvernement | Le nouveau gouvernement arrive par AMO (`membre_gouvernement`) | — | frise de l'accueil |
| Dossiers | Un dossier XVII repris en XVIII garde son uid (un objet, plusieurs archives) ; R-ETAPE travaille par législature ; une loi promulguée sous la XVIII pour un dossier XVII relève de T18 | — | étape dans chaque législature |
| E5-E6 | Nouvelles adresses inscrites au registre (`/legislatures/18`, `/groupes/<lignee>/18`) ; C2 vérifie les liens ; une famille encore vide sur la seule fiche XVIII ne déclenche pas C6 | — | fiche XVIII, couverture `en_cours` ; fiche XVII close, comptes datés à la fin |
| Volume | Croissance par législature et limite de 100 Mo par fichier : doc. 4 | — | — |

---

## 8.6 Renvois

| Critère de la partie 7 | Où |
| --- | --- |
| Premier remplissage : méthode | doc. 2, 2.13 (X1 corrigé) |
| Premier remplissage : durée, mémoire | doc. 4 |
| Poids par fiche : sans activité, la plus active, lignée, gouvernement, législature, au chargement et sous filtre | doc. 4 (mesures de poids dans les annexes : Ruffin et Lachaud pour les amendements, Bazin pour les paroles, groupe SOC pour les votes) |
| Volume stocké et servi, par famille, croissance par législature | doc. 4 |
| Durée et mémoire d'une mise à jour complète et quotidienne | doc. 4 |
| Coût nul | doc. 4 ; choix gratuits : doc. 3, J4 ; à vérifier : stockage des artefacts (N63) |
| Questions ouvertes | doc. 5 |

Questions que cette recette a mises au jour, et où elles sont au doc. 5 :

| Question | Ce qu'elle bloque | Doc. 5 |
| --- | --- | --- |
| Seuil de « couverture suffisante » (décision du 04/11/2026 : réglage de l'interface) | R-RATIO, A6 | Q1 (déjà) |
| Matière des dossiers saisis au seul Sénat (521 en XVIIe, archive du 03/11/2026) | R-MATIERE | Q19 (ajoutée) |
| Statut des votes sur une partie de texte financier et sur les résolutions de l'article 34-1 | R-NATURE-SCRUTIN, dernières lectures | Q20 (ajoutée) |
| Qualité d'un orateur déduite des fonctions à la date (T01) | paroles d'un gouvernement | Q21 (ajoutée) |
| Publier ou non un groupe dont la filiation attend une décision | registre des adresses, R-FILIATION | Q22 (ajoutée) |
| Les 7 mandats GOUVERNEMENT ouverts (Bayrou) : bornés par décision ou laissés ouverts ? | R-COMPOSITION | Q23 (ajoutée) |
| Fiches pour tous les députés et ministres (doc. 3, « trop étroit » 4) | volume, poids, limite de 1 Go | Q6 (déjà ; contrainte de 1 Go ajoutée) |
| Sauvegarde hors GitHub | E02 | tranchée le 04/11/2026 (disque de la propriétaire) ; fréquence : Q16 (déjà) |

---

## 8.7 État des trous et des incohérences

Consolidation du 04/11/2026. Sur 42 trous : **38 comblés** par un mécanisme, **4 comblés en
partie, le reste renvoyé en question ouverte** (T01, T06, T12, T40), **aucun sans objet**.
Deux comblements laissent un point à mesurer : la forme de l'échéancier des décrets
d'application (T19) et le « décalage d'un an » des données budgétaires (T21). Les cinq
incohérences sont corrigées.

### 8.7.1 Trous

| # | Trou | État | Où |
| --- | --- | --- | --- |
| T01 | Qualité d'un orateur quand `qualite` est vide (82 % des paragraphes attribués) | comblé ; renvoyé en question pour la qualité déduite | doc. 1, 1.6 R-QUALITE, 1.5.4 ; doc. 5, Q21 |
| T02 | 49.3 repéré par l'acte `DeclarationGouvernement_Type` (`Art.49.3`) | comblé | doc. 1, 1.6 R-SORT-FINAL, 1.4 C `acte` |
| T03 | C1 : fait absent de la nouvelle version de son objet | comblé | doc. 2, 2.8.1 C1 |
| T04 | Contrôle bloquant de périmètre | comblé | doc. 2, 2.8.1 C7 ; doc. 1, 1.6 R-PERIMETRE |
| T05 | Copies d'amendement : clé, copie retenue, alias ; découpage par uid | comblé | doc. 1, 1.6 R-AMENDEMENT, 1.4 C ; doc. 2, 2.4 |
| T06 | Nature `partie_de_texte` ; « ensemble » sans le mot | comblé ; statut des résolutions et des parties renvoyé en question | doc. 1, 1.5.3, 1.6 R-NATURE-SCRUTIN ; doc. 5, Q20 |
| T07 | Type de scrutin lu par son code | comblé | doc. 1, 1.4 C `scrutin`, 1.6 R-NATURE-SCRUTIN |
| T08 | Congrès écarté avec sa raison | comblé | doc. 1, 1.2.1, 1.6 R-PERIMETRE |
| T09 | A3 sans scrutins à dissidents seuls ni `PO0` ; appartenance jamais datée par le scrutin | comblé | doc. 2, 2.8.2 A3 ; doc. 1, 1.6 R-APPARTENANCE |
| T10 | Archive XIVe tronquée, trous de numérotation, scrutins cités absents | comblé | doc. 1, 1.5.5 |
| T11 | Projet de loi → gouvernement ; ministère porteur | comblé | doc. 1, 1.5.4 `projet_gouvernement`, 1.6 R-DEPOT-GOUVERNEMENT |
| T12 | Mandat ouvert dans un organe clos | comblé (A8, hors composition) ; bornage par décision renvoyé en question | doc. 2, 2.8.2 A8 ; doc. 1, 1.6 R-COMPOSITION ; doc. 5, Q23 |
| T13 | Sièges XIVe : fichier des places seul | comblé | doc. 1, 1.6 R-ARBITRAGE-ARCHIVES, 1.4 B `siege` |
| T14 | Chemins absents des pages : configuration + HEAD | comblé | doc. 2, 2.2 |
| T15 | Vide en trois formes, uid objet ; bloc des QG | comblé | doc. 2, 2.5 ; doc. 1, 1.4 C `question` |
| T16 | Borne de l'ordre du jour XIVe | comblé | doc. 1, 1.5.5 |
| T17 | « Organe non référencé » | comblé | doc. 1, 1.4 D `reunion` |
| T18 | Lois promulguées sous la législature suivante | comblé | doc. 1, 1.5.3 `lien_loi_dossier`, 1.6 R-LOI-DOSSIER, 1.3.3 `rattachement_loi` |
| T19 | Échéancier des décrets d'application ; « applique » depuis 2024 | comblé (forme de l'échéancier à mesurer) | doc. 1, 1.4 C `echeancier`, 1.4 E |
| T20 | Dates sentinelles ; naissances aberrantes | comblé | doc. 2, 2.5 ; doc. 1, 1.6 R-IDENTITE, 1.4 E |
| T21 | Finances (formats, PDF, ministère, licence, Drees, provisoire, budget en cours, séries de l'API) ; mesures nominatives | comblé, sauf la règle de recalage d'exercice (à mesurer) | doc. 2, 2.2 ; doc. 1, 1.4 G, 1.6 R-MESURE-NOMINATIVE |
| T22 | RNE : doublons ; mandats parlementaires écartés | comblé | doc. 1, 1.4 G ; doc. 2, 2.2, 2.8.2 A4 |
| T23 | Priorités AMO > Sycomore ; libellé daté du Sénat | comblé | doc. 1, 1.6 R-CARRIERE |
| T24 | Matricule tiré de Wikidata P1808 | comblé | doc. 1, 1.2.1 |
| T25 | Wikipédia : complétude de l'extraction, homonymies | comblé | doc. 2, 2.2 |
| T26 | PE : `User-Agent`, positions d'`ep_votes`, `corporate-bodies`, EuroVoc `100141`, phase préparatoire | comblé | doc. 2, 2.2 ; doc. 1, 1.4 F, 1.6 R-SORT-FINAL |
| T27 | Licence de l'entrepôt public ; EuroVoc ; licences = union des `src` | comblé | doc. 1, 1.7.1, 1.7.4 ; doc. 2, 2.8.1 C4 |
| T28 | Ordre neutre des listes ; étiquettes « aide à la lecture » | comblé | doc. 1, 1.7.1 ; doc. 2, 2.8.1 C4 |
| T29 | Un 0 exige `complet` ou `relu_aucun` | comblé | doc. 2, 2.8.1 C5 ; doc. 1, 1.5.5 |
| T30 | Aucun texte porté servi avant l'examen en commission | comblé | doc. 2, 2.8.1 C4 |
| T31 | Couverture du filtre par mot et des comptes rendus provisoires | comblé | doc. 1, 1.5.5 |
| T32 | Familles de fonctions ; fusion d'affichage des permutations | comblé (seuil en réglage) | doc. 1, 1.6 R-CARRIERE ; doc. 5, Q24 |
| T33 | Comptes d'un maillon clos ; objets distincts | comblé | doc. 1, 1.7.1 |
| T34 | Catalogue des articles ; commande d'instantané | comblé | doc. 1, 1.7.2 ; doc. 2, 2.12 |
| T35 | Terme légal d'une législature | comblé | doc. 1, 1.6 R-TERME-LEGAL |
| T36 | Sources non retenues déclarées | comblé | doc. 1, 1.4 G |
| T37 | `concurrency` avec `queue: max` | comblé | doc. 2, 2.1 |
| T38 | Journaux publics de la tâche | comblé | doc. 2, 2.10 |
| T39 | Relevés propres arrêtés pour une personne sortie | comblé | doc. 2, 2.1 point 5 |
| T40 | Fin ou ouverture de législature ; groupe `a_trancher` | comblé (alerte) ; publication du groupe renvoyée en question | doc. 1, 1.8 ; doc. 2, 2.8.2 A7 ; doc. 5, Q22 |
| T41 | Décision « fiche hors modèle » | comblé | doc. 1, 1.3.3 `fiche_hors_modele` ; doc. 2, A1 |
| T42 | Non-votes de fonction distingués | comblé | doc. 1, 1.4 C `position_vote` |

### 8.7.2 Incohérences

| # | Incohérence | État |
| --- | --- | --- |
| X1 | Premier remplissage commencé par Parltrack au nom d'une rétention de trois jours | corrigé (doc. 2, 2.13) |
| X2 | Relecture des « versions courantes » contre « toutes les versions » | corrigé (doc. 2, 2.5) |
| X3 | Sièges XIVe lus dans l'AMO20 de 2018 | corrigé (doc. 1, 1.6 R-ARBITRAGE-ARCHIVES ; T13) |
| X4 | 49.3 lu dans la conclusion | corrigé (doc. 1, 1.6 R-SORT-FINAL ; T02) |
| X5 | `signature` « lue dans la copie du premier signataire » | corrigé : lue dans la copie retenue (doc. 1, 1.4 C, 1.6 R-AMENDEMENT ; T05) |

### 8.7.3 Ajouts venus du document 4 (04/11/2026)

| Ajout | Où |
| --- | --- |
| Fichiers servis pré-compressés (`.json.gz`) : ≈ 0,21 Go au lieu de ≈ 0,82 Go | doc. 1, 1.7.1, 1.7.2 ; doc. 2, 2.9 ; doc. 3, J11, J12 |
| Index de mots par fiche, découpé par deux lettres et par année ; paroles par semestre | doc. 1, 1.7.1, 1.7.2 ; doc. 3, J11 |
| Actes d'un gouvernement : agrégats + listes par mois | doc. 1, 1.7.2 |
| Jeu téléchargeable : `donnees-derniere` + édition mensuelle | doc. 1, 1.7.4 ; doc. 2, 2.9 ; doc. 3, J14 |
| Segments de l'entrepôt plafonnés à 90 Mo ; contenu canonique | doc. 1, 1.1, 1.3.2 ; doc. 2, 2.4 ; doc. 3, J4 |
| Réactivation des tâches planifiées par l'API | doc. 2, 2.3 |
