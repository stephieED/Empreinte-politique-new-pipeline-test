# 3. Justification des choix

Pour chaque choix structurant : ce qu'il sert dans le cahier, les alternatives écartées et
pourquoi. Les références entre parenthèses renvoient au cahier (« 6.0 ») ou aux documents
1 et 2 (« doc. 1, 1.3 »). Les chiffres cités sont détaillés, avec leur méthode, dans le
document 4.

---

## Architecture des données

### J1 — Séparer l'acquis (relevés, objets versionnés, décisions) du recalculé

- **Sert** : 6.0 (« une correction de lecture et un champ ajouté atteignent tout l'historique,
  sans tout recollecter » ; « ce qui a été collecté reste acquis, même si la source efface son
  historique ») ; 5.4 (une donnée publiée ne se corrige qu'en passant par le traitement).
- **Écarté : une base de faits normalisés mise à jour en place** (le schéma habituel « on
  lit, on insère, on met à jour »). Une erreur de lecture découverte six mois plus tard
  exigerait de recollecter… des archives qui ont changé entre-temps (l'archive courante
  réécrit le siège, les libellés). Le passé serait perdu.
- **Écarté : garder chaque jour les archives entières.** Le seul fichier des amendements de
  la XVIIe pèse ~283 Mo ; le garder chaque soir coûterait de l'ordre de 100 Go par an, et ne
  dirait toujours pas quel amendement a changé.
- **Pourquoi** : en gardant les objets sources (pas les archives) et seulement quand ils
  changent, on a à la fois l'historique complet et un volume qui croît avec les changements
  réels, pas avec le nombre de jours.

### J2 — Versionner au niveau de l'objet source, par empreinte du contenu

- **Sert** : 6.0 (« ne recollecte que ce qui a pu changer », retrait à la source vs panne,
  état qui évolue) ; 3.1 (l'archive courante réécrit le passé).
- **Écarté : comparer les faits normalisés d'un jour à l'autre.** On saurait qu'un fait a
  changé, pas si c'est la source ou notre lecteur qui a changé ; et on ne pourrait pas relire
  l'ancienne version avec un lecteur corrigé.
- **Écarté : les dates de modification des sources.** L'Assemblée republie toute l'archive
  chaque nuit ; les en-têtes `Last-Modified` changent même quand rien n'a changé, et deux
  serveurs répondent différemment. L'empreinte du contenu canonique est la seule mesure sûre.
- **Pourquoi** : l'empreinte rend aussi les **retraits** constatables (objet absent d'un
  relevé complet) et donne gratuitement l'histoire des champs réécrits (siège, position
  déclarée d'un groupe, libellés), datée par les versions.

### J3 — « Seul un relevé complet peut faire constater un retrait »

- **Sert** : 6.0 (« un fait retiré à la source disparaît ; un fait absent à cause d'une panne
  ne disparaît pas ; les deux cas se distinguent ») ; 6.2 (« publie comme complète une lecture
  incomplète »).
- **Écarté : retirer tout ce qui n'est pas dans le dernier fichier reçu.** Un export du Sénat
  vide servi avec HTTP 200 effacerait tous les sénateurs.
- **Pourquoi** : une seule règle, vérifiable, qui sépare les deux cas à la source même de
  l'information. La complétude d'un relevé est décidée par des contrôles écrits (intégrité,
  plancher de taille, nombre d'objets plausible).

### J4 — L'entrepôt sur les *releases* du dépôt public

- **Sert** : 5.1 (aucun coût), 5.2 (fichiers < 100 Mo dans un dépôt ; cache de 10 Go évincé),
  5.4 (l'historique ne grossit pas sans limite), 6.0 (l'acquis survit à la source).
- **Écarté : git** (y compris une branche orpheline) : chaque version de chaque segment
  resterait dans l'historique pour toujours, la limite de 100 Mo par fichier s'applique, et un
  clone devient vite impraticable.
- **Écarté : Git LFS** : le quota gratuit est de 10 Gio de stockage et 10 Gio de bande
  passante par mois (documentation lue le 04/11/2026). Le premier remplissage (≈ 2 Go,
  doc. 4) y tiendrait, mais pas la suite : chaque version poussée compte en stockage, les
  téléchargements faits par GitHub Actions comptent en bande passante (un recalcul relit
  l'entrepôt), et LFS est désactivé jusqu'au mois suivant une fois le quota dépassé. LFS ne
  peut pas non plus servir de source à GitHub Pages.
- **Écarté : le cache de GitHub Actions** comme stockage : 10 Go, éviction des entrées les
  moins récentes, suppression après une période sans accès. Il sert seulement
  d'**accélérateur** (copie de travail).
- **Écarté : les artefacts de GitHub Actions** : rétention limitée (90 jours au plus).
- **Écarté : un stockage objet externe** (offres gratuites de fournisseurs cloud) : compte
  et moyen de paiement à fournir, dépendance supplémentaire, risque de facturation (5.1).
- **Pourquoi** : les *releases* d'un dépôt public sont gratuites, sans limite de taille totale
  déclarée par GitHub (limite par fichier : 2 Gio), lisibles par n'importe qui (transparence)
  et gérables par l'API depuis GitHub Actions. On y garde des segments plafonnés à 90 Mo (un
  mois d'amendements XVe en ferait ≈ 146, doc. 4) et on les compacte ; une *release* par
  année reste sous les 1 000 actifs permis. Publics, ces segments sont un jeu republié : ceux
  de Parltrack sont sous ODbL (doc. 1, 1.7.4). **Risque** : dépendance à un seul
  fournisseur — atténuée par une sauvegarde sur le disque de la propriétaire (décision du
  04/11/2026 ; fréquence : doc. 5, Q16).

### J5 — Python, Parquet et DuckDB

- **Sert** : 5.2 (15 Gio en intégration, 7,8 Gio en développement ; relance locale sur un
  sous-ensemble), 5.6 (Python est pratiqué), 4.7 (règles publiées).
- **Écarté : PostgreSQL** ou toute base serveur : un serveur à héberger (5.1, 5.2).
- **Écarté : SQLite comme stockage principal** : un fichier unique qui dépasserait vite
  100 Mo, stockage en lignes lent pour les agrégats de la partie 4 (décomptes par groupe et
  scrutin sur des millions de positions).
- **Écarté : pandas en mémoire** : les positions de vote et les prises de parole de quatre
  législatures ne tiennent pas confortablement en mémoire sur 7,8 Gio.
- **Écarté : Spark, Dagster, Airflow** : machinerie disproportionnée pour une seule
  personne, et souvent un service à faire tourner.
- **Pourquoi** : Parquet est compact (colonnes, zstd), lisible partout, découpable en
  fichiers de taille maîtrisée ; DuckDB lit Parquet sans import, travaille hors mémoire avec
  une limite réglable (`memory_limit`), et exprime les règles en SQL lisible, que la page de
  méthodologie peut citer. Pas de serveur.

### J6 — Recalculer entièrement le graphe relié et les fiches à chaque mise à jour

- **Sert** : 4.6 (les règles « doivent produire le même résultat partout où elles
  s'appliquent »), 6.0 (une correction atteint tout l'historique), 6.2 (comparer deux
  publications).
- **Écarté : un recalcul incrémental fin** (ne recalculer que les fiches touchées). La
  « dernière lecture » d'un texte se décide sur tout le corpus : un nouveau scrutin change la
  position retenue sur des dizaines de fiches ; une décision de filiation change une lignée
  entière. Suivre ces dépendances à la main est la source classique d'incohérences.
- **Pourquoi** : l'incrémentalité est placée là où elle coûte cher (le réseau et la lecture
  des archives) ; le reste, qui tient en minutes, est recalculé en entier. Comme la
  composition est déterministe, la comparaison avec la publication précédente se fait
  fichier par fichier et fait par fait.

### J7 — Identifiants : ceux des sources, préfixés ; des identifiants internes pour ce que le site construit

- **Sert** : 6.1 (« l'adresse d'une fiche ne change pas une fois publiée »), 4.1 (une même
  personne relève de plusieurs populations), 3.1 (grammaire des identifiants, `PA` omis).
- **Écarté : l'identifiant `PA` comme clé de personne** : les candidats sans mandat de
  député n'en ont pas, un sénateur peut en recevoir un plus tard.
- **Écarté : l'adresse (nom en minuscules) comme clé** : homonymes, changements de nom
  d'usage.
- **Écarté : le rang du paragraphe comme clé d'une prise de parole** : l'Assemblée le
  renumérote en republiant un compte rendu provisoire. **Écarté aussi : une clé par empreinte
  du texte** (première idée) : le texte est retouché en place. Mesuré le 04/11/2026 :
  `id_syceron` reste le même pour 97 à 99 % des paragraphes republiés ; il devient la clé, et
  une empreinte (séance, orateur, début du texte) rattrape les rares identifiants remplacés.
- **Pourquoi** : une clé interne qui ne porte aucune information ne change jamais ; les
  identifiants des sources restent des correspondances, révisables. L'adresse publique est
  inscrite à part dans un registre en ajout seul.

### J8 — Les décisions sont des fichiers YAML commités

- **Sert** : 4.3 et 6.1 (cas que la règle ne tranche pas), 6.2 (« la propriétaire peut
  autoriser une publication refusée : geste explicite et tracé »), 4.7 (absences établies à
  la main), 5.4.
- **Écarté : une base ou une interface d'administration** : pas de serveur ; et une
  décision doit être publique et datée.
- **Écarté : les issues** comme support de décision : sur le dépôt public, c'est une activité
  visible (5.3) ; et une issue n'est pas une entrée versionnée du traitement.
- **Pourquoi** : un fichier commité est daté, attribué, public, relisible, et le traitement
  peut le valider (schéma) et dire quand il ne s'applique plus.

### J9 — La couverture est un objet calculé, pas un texte

- **Sert** : 4.7 (couverture déclarée, absences établies, comptes datés, sélections
  déclarées), règle 5 (une donnée manquante reste manquante), 6.0 (ce qui n'est pas fait se
  publie comme tel), 4.8 (page des sources).
- **Écarté : des messages rédigés à la main par fiche** (« Aucun signalement propre aux
  fiches de ce groupe ») : ils vieillissent faux.
- **Pourquoi** : en calculant le statut (vrai zéro, trou, borne, choix, panne, en cours,
  relu sans résultat) à partir des relevés et des règles, la section « Ce qu'on n'a pas pu
  lire » est toujours juste, et le contrôle C5 peut vérifier qu'aucune lecture incomplète
  n'est présentée comme complète.

### J10 — Le volet présidentiel est une population, pas un pilier

- **Sert** : partie 1 (« le modèle ne doit pas en dépendre »), 4.1 (un candidat qui renonce
  n'est plus affiché, ses données restent).
- **Pourquoi** : la fiche personne se compose à partir des mêmes objets que les fiches de
  groupe et de gouvernement ; « candidat » ne fait qu'ouvrir la publication d'une fiche.
  Après l'élection, la population peut devenir « élu en 2027 » ou disparaître sans toucher au
  reste.

---

## Données servies

### J11 — JSON statique, découpé par fiche et par section, en colonnes

- **Sert** : 4.7 (« une fiche ne doit pas télécharger ce qu'elle n'affiche pas » ; lecteurs
  sur téléphone), 5.2 (GitHub Pages, fichiers statiques, gzip), 4.2 (filtres par mot et par
  période).
- **Écarté : une base SQLite lue par requêtes HTTP partielles** (technique
  « sql.js-httpvfs ») : élégant, mais beaucoup de petites requêtes sur réseau mobile, un
  moteur de plusieurs centaines de Ko à télécharger, et un comportement de cache difficile à
  garantir.
- **Écarté : Parquet lu dans le navigateur** (DuckDB-wasm) : plusieurs Mo de moteur avant la
  première donnée.
- **Écarté : un seul JSON par fiche** : la fiche de la personne la plus active
  téléchargerait d'emblée ses exposés d'amendements et ses prises de parole (doc. 4).
- **Écarté : un format binaire (MessagePack, Protobuf)** : après gzip, le gain sur du JSON en
  colonnes est faible, et la lisibilité (débogage, réutilisation) est perdue.
- **Pourquoi** : en-tête léger + sections à la demande + textes au clic ou sous filtre ; le
  format en colonnes supprime la répétition des noms de champs (le gain est mesuré au
  doc. 4).
- **Fichiers servis déjà compressés** (`.json.gz`, décompressés par `DecompressionStream`) :
  GitHub Pages compresse au transfert, mais sa limite de 1 Go porte sur les fichiers
  publiés ; en JSON brut le site ferait ≈ 0,82 Go pour XIVe–XVIIe et +0,37 Go par
  législature, soit le dépassement pendant la XVIIe ; compressé, ≈ 0,21 Go (calculé,
  doc. 4, 4.1.4). Le format reste du JSON, lisible une fois décompressé. Écarté : réduire les
  extraits ou partager les textes entre fiches (moins de contexte ou une requête de plus),
  gardés en réserve.
- **Filtre par mot par index découpé** (deux premières lettres du mot, année) : charger tous
  les textes d'une lignée pour y chercher un mot coûte 7,7 Mo ; avec l'index, 0,46 Mo au plus
  (mesuré sur prototype, doc. 4, 4.2.4). Écarté : une recherche sur tout le site, abandonnée
  par le cahier (4.7).

### J12 — Chaque fichier embarque les libellés qu'il cite

- **Sert** : 4.7 (poids des pages), 4.7 (liens : un lien faux est pire qu'absent).
- **Écarté : des dictionnaires partagés** (tous les dossiers d'une législature dans un
  fichier commun) : la fiche d'un candidat téléchargerait les titres de 3 390 dossiers pour
  en afficher 30.
- **Pourquoi** : le site compte peu de fiches (de l'ordre de 75 au 03/11/2026 : 34 candidats,
  17 gouvernements, 18 groupes, 4 législatures — page des sources) ; la duplication coûte du
  stockage, pas de poids de page. Ce stockage compte face à la limite de 1 Go de Pages (les
  extraits de parole recopiés dans les lignées sont le premier poste, doc. 4, 4.1.4) : il est
  tenu par les fichiers `.json.gz` (J11).

### J13 — Schéma en liste blanche pour chaque fichier servi

- **Sert** : partie 2 en entier, 6.2 (« publie une donnée interdite »).
- **Pourquoi** : on ne peut pas publier par mégarde un champ qui n'existe pas dans le
  schéma ; le contrôle C4 le vérifie en plus par motifs. C'est la garantie « par
  construction » de la recette.

### J14 — Le jeu téléchargeable est séparé par régime de licence et hébergé en *release*

- **Sert** : 2.2 (ODbL : partage à l'identique pour tout jeu dérivé de Parltrack ; faits
  seulement pour Wikipédia, Sycomore, fichier des places), 4.7 (jeu référencé sur
  data.gouv.fr).
- **Écarté : un seul paquet** : tout le jeu tomberait sous ODbL dès qu'il contient un vote
  européen.
- **Écarté : une édition datée à chaque publication** : ≈ 0,53 Go par édition, ≈ 190 Go par
  an (doc. 4, 4.1.5). Une édition `donnees-derniere` remplacée chaque soir et une édition
  datée par mois suffisent ; la traçabilité au jour près relève du registre (J18).
- **Pourquoi** : chaque réutilisateur prend le paquet dont la licence lui convient ; la
  licence de chaque table est calculée depuis la provenance de ses lignes.

---

## Processus

### J15 — Neuf étapes, l'acquisition persistée avant tout calcul

- **Sert** : 6.3 (« une mise à jour interrompue ne coûte pas tout le travail déjà fait »),
  6.0, 5.5 (« une source en panne ne fait pas échouer la publication des autres »).
- **Écarté : une chaîne monolithique** « télécharger tout, calculer, publier » : une erreur à
  la fin fait tout perdre ; une source en panne bloque tout.
- **Pourquoi** : E1–E2 sont par source, isolées, persistées au fil de l'eau ; E3 est
  mémorisé par (empreinte, lecteur) ; E4–E5 sont rejouables. Une interruption coûte au plus
  le travail de la source en cours.

### J16 — Contrôles bloquants à empreinte, levée ciblée

- **Sert** : 6.2 (« ne lève que le contrôle concerné »).
- **Écarté : une case « forcer la publication »** : elle lèverait aussi les anomalies
  apparues après la décision.
- **Écarté : des seuils seuls** (« bloquer si plus de 1 % de pertes ») : 6.2 exige de
  **nommer** les faits perdus et de distinguer retrait et panne.
- **Pourquoi** : la levée vise une anomalie précise ; si l'anomalie change, il faut une
  nouvelle décision.

### J17 — Publication par artefact GitHub Pages

- **Sert** : 6.3 (« le lecteur voit l'état précédent complet ou le nouveau complet » ;
  « sans geste humain »), 5.4 (l'historique ne doit pas grossir sans limite).
- **Écarté : une branche `gh-pages` où l'on commite les données** : chaque publication
  ajouterait des dizaines de Mo à l'historique git, pour toujours.
- **Pourquoi** : le déploiement par artefact (`actions/deploy-pages`) bascule d'un site
  complet à l'autre et ne laisse rien dans l'historique ; la traçabilité est assurée à part
  (J18).

### J18 — Traçabilité : registre chaîné, magasin dédupliqué, rejouabilité

- **Sert** : 5.4 en entier (savoir ce qui était publié à une date ; prouver qu'il n'a pas été
  modifié ; réduire sans perdre cette capacité).
- **Écarté : garder chaque publication entière** : volume proportionnel au nombre de jours.
- **Écarté : ne garder que les manifestes** : on saurait l'empreinte de ce qui était publié,
  pas son contenu.
- **Pourquoi** : le registre (chaîne d'empreintes dans git, empreinte racine recopiée sur
  data.gouv.fr) prouve l'intégrité ; le magasin garde chaque fichier une seule fois ; au-delà
  d'un an, les publications intermédiaires sont reconstruites en rejouant le traitement
  depuis l'entrepôt (qui garde toutes les versions) et vérifiées par empreinte. Un contrôle
  mensuel prouve que le rejeu fonctionne encore.

### J19 — Les alertes sont des issues du dépôt privé

- **Sert** : 6.3 (« une par sujet, sans répétition quand rien ne change »), 5.3 (rien de
  visible sur le dépôt public, pas de ticket).
- **Écarté : les issues du dépôt public** : activité visible, interdite en journée.
- **Écarté : les courriels d'échec de GitHub Actions** : un par échec, sans regroupement par
  sujet, rien quand la tâche réussit en ayant refusé de publier.
- **Écarté : un service de notification externe** : un compte de plus, des données hors de
  GitHub.
- **Pourquoi** : la propriétaire travaille déjà avec les tickets du dépôt privé ; une issue
  par clé de sujet, mise à jour seulement quand son contenu change, fermée quand le sujet
  disparaît, donne exactement « une par sujet, sans répétition ».

### J20 — Le code publié est importé par une tâche planifiée du dépôt public

- **Sert** : 5.3 (historiques séparés ; aucune activité visible en journée), 6.3 (« les
  données publiées correspondent toujours au code publié » ; « publier du code n'écrase
  jamais les données »).
- **Écarté : pousser à la main sur le dépôt public** : facile de le faire à 10 h un mardi.
- **Écarté : un miroir automatique** : il recopierait l'historique de développement.
- **Pourquoi** : la propriétaire pose une étiquette quand elle veut ; l'import et la
  publication ont lieu le soir, ensemble.

### J21 — L'heure de Paris est calculée dans la tâche

- **Sert** : 5.3, 5.2 (« déclenchements planifiés servis avec un retard de quelques minutes à
  plusieurs heures »).
- **Pourquoi** : le planificateur de GitHub raisonne en UTC et ignore l'heure d'été ; un
  déclenchement prévu à 20 h peut partir à 23 h ou le lendemain matin. Seul un calcul dans la
  tâche garantit la fenêtre.

---

## Règles de liaison

### J22 — Un lien scrutin ↔ dossier exige l'accord des routes

- **Sert** : 4.7 (« un lien faux est pire qu'un lien absent »), 3.1.2 (un scrutin ne dit pas
  en général sur quel texte il porte).
- **Écarté : la recherche du titre du dossier dans l'intitulé du scrutin, sur tout le
  corpus** : homonymies (« projet de loi de finances »), titres courts trompeurs
  (« Bioéthique »). Le titre ne sert qu'à **départager** les quelques dossiers d'une même
  séance.
- **Pourquoi** : routes indépendantes (référence directe, acte qui cite le scrutin, séance) ;
  une seule suffit si elle est sans ambiguïté, plusieurs doivent concorder ; un désaccord
  donne « non lié » et une alerte. Mesuré sur la XVIIe (archive du 03/11/2026) : la
  référence directe et les actes ne relient que 3 924 scrutins sur 9 578 ; avec la séance et
  le départage, 9 108, avec 3 348 accords sur 3 350 recoupements. Le taux de liaison est
  publié sur la page de méthodologie.

### J23 — Rapprochement d'identités : identifiant déclaré, sinon état civil et date de naissance

- **Sert** : 3.2 (« le nom seul donne des faux positifs »), 3.9, 6.1 (identité d'un nouveau
  candidat validée par la propriétaire).
- **Pourquoi** : Wikidata déclare les identifiants Assemblée, Sénat et Sycomore (vérifiés
  justes sur 12 personnes sur 12 par le cahier) ; à défaut, nom normalisé **et** date de
  naissance ; tout le reste part en relecture. Une identité de candidat n'est jamais publiée
  sans validation.

---

## Là où le cahier me paraît trop étroit ou ambigu

1. **« Collecte tout » chaque soir** (6.3) : compris comme « interroge toutes les sources »,
   pas « télécharge tout ». Certaines sources sont trimestrielles ou annuelles ; les
   interroger chaque soir ne sert à rien, et la règle de fraîcheur (4.7) prévoit qu'une
   famille dise qu'elle ne suit pas le rythme quotidien.
2. **« Couverture suffisante »** (règle 7) n'a pas de seuil. Décision du 04/11/2026 : c'est un réglage de l'**interface** ; le traitement collecte et sert toujours les décomptes, jamais le ratio (doc. 5, Q1).
3. **Paroles d'un gouvernement « pendant la fonction »** (4.4) : tranché par la propriétaire
   le 04/11/2026 : une prise de parole compte si elle a lieu pendant la fonction **et** en
   qualité de membre du gouvernement selon le compte rendu. Le compte rendu ne donne la
   qualité que pour 18 % des paragraphes attribués (XVIIe) : ailleurs, elle est déduite des
   fonctions à la date et marquée comme telle (doc. 1, R-QUALITE ; à confirmer, doc. 5, Q21).
4. **Fiches de personne** : le cahier ne prévoit une fiche que pour les candidats, mais le
   périmètre suit tous les députés et ministres. Le modèle sait composer une fiche pour
   n'importe quelle personne ; le choix de les publier est éditorial (doc. 5).
5. **Jours ouvrés** (5.3) : tranché par la propriétaire le 04/11/2026 : interdiction du lundi
   au vendredi de 9 h à 19 h, jours fériés français exclus.
6. **Le cahier est dépassé sur plusieurs sources** (mesures du 04/11/2026, doc. 4 et 8) :
   Parltrack ne se met plus à jour depuis le 24/07/2026 et garde ses archives depuis 2019 ;
   aucun groupe de la XVIIe ne déclare de position, donc la « période » fondée sur le banc
   déclaré (4.2, 4.6) ne change, en XVIIe, qu'avec le gouvernement ; le Journal officiel
   publie un champ `SIGNATAIRES` en texte libre : il est collecté tel quel, jamais relié à une
   personne (règle de 4.6), et son affichage sera décidé côté interface (doc. 5, Q11) ; GitHub Pages plafonne le site à 1 Go
   (c'est une limite, pas une recommandation).
