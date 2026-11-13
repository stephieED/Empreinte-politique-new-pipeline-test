# 5. Questions ouvertes

Les questions que le cahier laisse ouvertes et qui bloquent un choix. Pour chacune : ce
qu'elle bloque, et ce que la conception fait **en attendant** (un défaut prudent, toujours
réversible par une décision ou un paramètre, jamais par une réécriture de données).

Les questions sont classées par urgence : **A** = à trancher avant la première
publication ; **B** = à trancher avant d'activer la fonction concernée ; **C** = réglage, le
défaut peut rester.

---

## Tranchées (04/11 et 06/11/2026)

| Question | Réponse de la propriétaire | Où c'est appliqué |
| --- | --- | --- |
| L'entrepôt des données collectées peut-il être public (*releases* du dépôt public) ? | Oui, avec une sauvegarde sur son disque | doc. 1, 1.1 et 1.3.2 ; doc. 3, J4 |
| Les jours fériés comptent-ils comme jours ouvrés (5.3) ? Jusqu'à quelle heure ? | Fériés libres ; interdiction du lundi au vendredi de 9 h à 19 h | doc. 2, 2.1 |
| Paroles d'un gouvernement « pendant la fonction » : lesquelles ? | Pendant la fonction **et** en qualité de membre du gouvernement selon le compte rendu | doc. 1, R-QUALITE ; doc. 3 ; qualité déduite quand le compte rendu se tait : Q21 |
| Q2. XVIIe : aucun des 14 groupes ne déclare sa position (mesuré le 04/11/2026, AMO30 et AMO10). Que publier ? | Le site publie « non déclaré » : la donnée n'existe pas à la source, elle n'est ni déduite ni cherchée ailleurs. La position déclarée reste collectée chaque soir : si un groupe en déclare une, elle apparaît d'elle-même | doc. 1, 1.6 R-BANC ; doc. 8 |
| Q4. Mandats présents dans une archive figée de l'Assemblée mais effacés de l'archive courante (99 de la XVIe figée, 402 de la XVe figée ; aucun mandat de député ni de groupe AN ; remesuré le 04/11/2026) : retrait ou non ? | Un mandat effacé que la courante **remplace** (même personne, même organe, période qui recouvre l'ancienne : 259 cas) est une **correction** : l'ancien est retiré, le remplaçant affiché. Un mandat effacé **sans remplaçant** est un **retrait à la source** : il disparaît du site, et le rapport de mise à jour le nomme | doc. 1, 1.3.2 et 1.6 R-ARBITRAGE-ARCHIVES ; doc. 8, N14 |
| Q19. 521 dossiers de la XVIIe n'ont de commission saisie au fond qu'au Sénat (archive du 03/11/2026). Quelle matière ? | « Saisi au Sénat seulement », distinct de « matière non établie » | doc. 1, 1.6 R-MATIERE ; doc. 8, N35 |
| Q6. Publier une fiche pour les personnes non candidates ? | Non : fiches de personne pour les seuls candidats validés. Les autres personnes restent collectées (groupes, gouvernements, législatures) | doc. 1, 1.5.1 ; doc. 4 |
| Q9. Au-delà d'un an, ne garder que les publications de fin de mois, les autres étant rejouées et vérifiées par empreinte : est-ce suffisant pour « dire ce qui était publié à une date » ? | Oui | doc. 2, 2.14 |
| Q10. Articles datés : quelles données « à une date » ? | L'état **connu** à la date (ce que le site savait ce jour-là) | doc. 2, 2.12 (instantané) |
| Q11. Le JO publie les signataires en texte libre : qu'en faire ? | Les collecter et les servir tels quels avec l'acte, sans en tirer d'identifiant de personne ; l'interface décidera si et comment les afficher. La règle de 4.6 (« jamais à une personne ») vaut pour le site, pas pour le corpus | doc. 1, 1.4 E et 1.7.1 ; doc. 8, I03 |
| Q30. Divergence avec le groupe : la position majoritaire publiée par l'Assemblée contredit son propre décompte dans 3 308 décomptes de groupe sur 106 507 (XVIIe, collecte du 06/11/2026). Laquelle retenir ? | La position publiée quand elle concorde avec le décompte ; sinon, la position du groupe est « non établie » et le scrutin n'entre pas dans la comparaison (1 839 positions de personnes écartées), ce que la couverture dit | règle R-DIVERGENCE (dépôt d'essai) ; doc. 1, 1.6 |
| Q31. Remaniements d'un gouvernement : le cahier (4.4) les demande sans les définir ; les données ne donnent que des vagues de nominations. Comment compter ? | « A. Départ ou changement » (07/11/2026) : la formation (première vague, et la deuxième quand la première ne nomme que le Premier ministre) n'est jamais un remaniement ; ensuite, une vague où au moins un membre part ou change de portefeuille est un remaniement, une vague qui ne fait qu'ajouter des membres un complément. Écartés : toute vague après la formation (compte les compléments) ; lister sans compter. L'effectif minimal se lit après la formation | règle R-VAGUE (version 2), fiche gouvernement |
| Q23. Mandats restés ouverts dans un organe clos (7 mandats GOUVERNEMENT du gouvernement Bayrou, clos le 09/09/2025, et 2 anciens : une mission de 2002, une fonction présidentielle de 2012 ; avertissement A8) | « borner » (13/11/2026) : chacun est borné à la date de fin de son organe par une décision (`decisions/borne_mandat/`) ; la date de fin vient de la décision, la source n'est pas réécrite ; une décision devenue sans objet (la source a fermé le mandat) est signalée (A7) | décisions `borne_mandat`, vue des mandats (liaison), A7, A8 |
| Q8. Candidatures : Wikipédia comme détecteur, avec validation de chaque candidature ? | « Pour la validation des candidats, s'ils sont sur wikipedia alors c'est validé » (06/11/2026). L'identité est rattachée par Wikidata, jamais par le nom seul | règles R-CANDIDATURES et R-IDENTITE (dépôt d'essai) |
| Q8 (suite, 13/11/2026). Source de la liste des candidats | « la liste de candidats doit se baser sur celle de franceinfo » (page des portraits des candidats déclarés à la présidentielle de 2027) : remplace la liste de Wikipédia. Réponse « A » (13/11/2026), franceinfo réservant la fouille de données et interdisant son site aux robots d'IA : liste tenue dans `decisions/` (type `candidature`), validée par la propriétaire, chaque candidat avec son élément Wikidata ; la page n'est pas collectée (adresse et date de lecture seulement) ; Wikipédia reste lu comme détecteur d'écart. Liste du 13/11/2026 : 37 candidats déclarés, 6 retirés ; trois rattachements trouvés par le nom puis validés par la propriétaire (« Valider les trois », 13/11/2026) : Jean Lassalle Q3173022, Juan Branco Q21890311, Clara Egger Q108584624 | décisions `candidature`, règle R-CANDIDATURES (version 2, PR #50 fusionnée le 13/11/2026) |
| Q3. Parltrack ne se met plus à jour (votes figés au 26/03/2026) : quelle source pour le volet européen ? | « Les deux, raccordées en 2019 » (13/11/2026) : Parltrack (ODbL) pour 2004 → juin 2019, législatures closes que le gel ne touche pas ; portail du Parlement européen (CC BY 4.0) à partir de la législature ouverte en juillet 2019, à jour. Mesuré le 13/11/2026 : le portail n'a aucun vote nominatif avant juillet 2019 (2014–2018 : aucune décision ; mars 2019 : un seul votant fictif par vote) ; Glucksmann y vote dans 222 des 225 votes nominatifs du 28/04/2026. Écartés : portail seul (Le Pen, Mélenchon, Philippot sans votes) ; Parltrack seul (Glucksmann figé au 26/03/2026) ; mandats seulement. La partie Parltrack relève de l'ODbL : jeu téléchargeable dérivé à part (doc. 1, 1.7.4) | à réaliser (session « New pipeline candidats ») |
| Q32 (13/11/2026, issue #34). 170 votes sur l'ensemble ne sont reliés à aucun dossier (g10 : XIVe 59, XVe 92, XVIe 11, XVIIe 8 ; séance ambiguë 127, désaccord des routes 38, séance inconnue 5) ; pour 75 dossiers sur 665, l'un d'eux, plus récent que la dernière lecture retenue, a pu porter sur le texte. Que montrer ? | « Garder, signalé » : la dernière lecture retenue reste publiée, et `votes_posterieurs_non_relies` nomme chaque vote plus récent non relié dont le dossier est candidat (dossier discuté ou décidé dans sa séance, ou candidat d'une route). Écartés : « non établie » (75 textes retirés des fiches, levée de C1) ; relier au seul dossier décidé dans la séance (51 votes sur 170 résolus, 6 erreurs sur 309 cas vérifiables) | R-DERNIERE-LECTURE version 2 ; sections `votes-<n>` des lignées, `votes` et `divergences` des candidats |
| Q33. Votes au Parlement européen sur la fiche d'un candidat : 88 % des votes nominatifs portent sur un amendement ou un paragraphe, 12 % sur l'ensemble d'un texte (échantillon de 774 votes nominatifs de 7 séances, 2019 → 2026, portail du PE, mesuré le 13/11/2026). Que montrer ? | « Tous les votes nominatifs » (13/11/2026) : chaque vote nominatif du candidat, amendements et paragraphes compris, avec sa nature (`ensemble`, `partie`, `non_etablie`, lue dans le libellé du vote ; 2 libellés non reconnus sur 774). Écartés : une position par texte (règle de l'Assemblée) ; l'ensemble en tête et le détail à part. Les règles éditoriales restent : aucun décompte rapporté au groupe, aucun taux | volet européen, lots 2 (portail) et 3 (Parltrack) |
| Q34. Mandats locaux des candidats : le Répertoire national des élus n'a aucun identifiant de personne. Mesuré le 13/11/2026 (1 136 316 lignes : fichiers en cours du 11/08/2026 et sortants des municipales 2020-2026) : par nom, prénom et date de naissance exacte (date de l'Assemblée, du Sénat ou de Wikidata), 9 candidats déclarés retrouvés (Lisnard, Bouamrane, Roussel, É. Philippe, Dupont-Aignan, Becht, Attal, Tondelier, Retailleau) ; le nom seul prendrait des homonymes (Roussel 3, Faure 6) ; 11 candidats sans date de naissance connue (dont Platret, maire de Chalon-sur-Saône). Comment rattacher ? | « Nom + naissance, et décision pour les autres » (13/11/2026) : rattachement automatique quand nom, prénom normalisés et date de naissance exacte concordent (doc. 1, R-IDENTITE) ; un candidat sans date de naissance connue n'est rattaché que par une décision qui valide l'élu proposé. Écartés : automatique seulement ; une décision pour chacun. Le répertoire ne couvre que depuis 2020 et ne publie aucune date de fin | mandats locaux (à réaliser) |
| Q35. Mandats locaux : le Répertoire national des élus ne publie aucune date de fin ; les mandats 2020-2026 viennent du fichier des sortants des municipales 2026 (publié le 27/02/2026), les mandats en cours du fichier trimestriel ; rien avant 2020 (jeux sans licence). Que montre la frise pour un mandat de 2020 ? | « Fin au renouvellement de mars 2026 » (13/11/2026) : un mandat du fichier des sortants se termine au premier tour des municipales, le 15/03/2026, date **déduite** et signalée comme telle sur la fiche ; avant 2020 : « borne historique ». Écartés : fin non publiée (« sortant ») ; mandats en cours seulement | mandats locaux (à réaliser) |
| Q36. Mandats de député d'avant 2002 (Sycomore) : le cahier 4.2 les demande dans la frise ; Sycomore est une page HTML par personne, « tous droits réservés » (cahier 3.11). Faut-il les intégrer à la validation ? | « Oui, les faits seulement » (13/11/2026) : relevé des fiches des candidats (identifiant Sycomore déclaré par Wikidata, P1045) ; l'entrepôt ne garde que les faits extraits (mandat, dates, département, groupe) et l'adresse de la fiche, pas la page ; la frise montre les mandats de député antérieurs au 19/06/2002. Écartés : garder la borne historique ; plus tard | point `sycomore-fiches`, R-CARRIERE v4 |
| Q37. Activité au Parlement européen (hors votes) des candidats anciens ou actuels députés européens : interventions en séance (Mélenchon 2 158, Le Pen 808, Philippot 749, Glucksmann 43 dans Parltrack et 112 au portail), rapports, propositions de résolution, questions écrites à la Commission, explications de vote (Parltrack et portail du PE, mesuré le 13/11/2026) ; ni l'une ni l'autre source ne donne le texte des interventions. Que montrer ? | « Tout, chacun dans sa section » (13/11/2026) : interventions (titre du débat, date, lien vers le compte rendu), rapports et rôle (rapporteur, rapporteur fictif), propositions de résolution, questions écrites, explications de vote ; tout ce que publient les deux sources, aucun décompte rapporté à quoi que ce soit. Écartés : interventions, rapports et résolutions seulement ; interventions seulement | volet européen, activité (à réaliser) |
| Q33 (13/11/2026, issue #35). 17 dossiers de la XIVe ont continué sous la XVe, mais aucune archive de l'Assemblée ne publie leur suite (archive de la XIVe arrêtée au 22/03/2018 ; exemple : loi 2018-287). Que faire ? | « Dire le trou, puis relier » : raison `suite_absente_des_archives` maintenant ; ensuite, avec la session Journal officiel, relier la loi au dossier par les travaux préparatoires publiés au JO. Écartés : dire le trou seulement ; relier par le titre (titres de dossiers résumés, fragile) | R-SORT-FINAL version 3 ; R-LOI-DOSSIER (à faire) |
| Q34 (13/11/2026, issue #32). Les amendements de la XVe (649 Mo) et de la XVIe (363 Mo), archives closes, n'arrivent jamais dans le budget de 30 min (passés une fois en 74 min, le 07/11). Comment les obtenir ? | « Relevé dédié, budget long » : budget de 2 h pour ces deux points, appliqué seulement dans une mise à jour qui les nomme (`-f points=…`), lancée à la main un jour hors nuit choisi par la propriétaire ; la nuit garde 30 min par fichier. D'abord, le budget est tenu pendant la copie et un hôte muet est suspendu (#37), la collecte a une échéance (#38). Écartés : garder le fichier partiel d'une nuit à l'autre (l'Assemblée sert mal la suite d'un gros fichier, mesuré le 07/11) ; accepter l'échec affiché | `budget_s` dans `config/points_acces.yaml` ; `transport` |
| Q35 (13/11/2026, issue #42). C1 reconnaît un fait à son identité (correctif du 12/11, à ne pas rouvrir) : un compteur qui passe à 0 ou un champ qui se vide ne sont signalés par rien, et l'en-tête des fiches n'est pas surveillé. Quel contrôle à part ? | « Avertissement, en-tête compris » : A9 compte, pour les faits présents les deux nuits sous une identité unique, chaque champ qui passe d'un nombre non nul à 0 ou à rien, ou d'une valeur à rien ; avertissement (non bloquant) par type de fait et champ au-delà de 1 % du type ou de 50 faits, avec décomptes et identifiants. L'en-tête des fiches de candidat devient le fait `identite_personne`, reconnu à son `per`. Écartés : bloquant au-delà du seuil ; rien. **Révisée le 13/11/2026 au soir** (issue rouverte : un compteur isolé, 165 → 0, passait sous le seuil) : « Nombre à 0 : toujours » ; un nombre qui passe à 0 ou à rien est signalé même seul, le seuil ne vaut plus que pour les autres champs vidés ; les faits d'une même identité s'apparient par leurs champs discriminants (institution, date…). Écartés : aucun seuil ; garder le seuil | `controles.a9_valeurs_videes` ; composeur candidat |
| Q38 (13/11/2026). R-QAG : la source des questions ne cite aucune séance. Mesuré le 13/11/2026 (calcul local, comptes rendus de la XVe à la XVIIe) : la date publiée d'une question au gouvernement est celle du JO, en général le lendemain de la séance ; en exigeant que l'auteur (par identifiant) parle sous un intitulé égal à l'en-tête du bloc JO, dans les 10 jours qui précèdent, 4 746 questions sur 4 850 sont appariées en XVe, 1 935 sur 1 940 en XVIe, 1 830 sur 1 857 en XVIIe, sans cas ambigu. Faut-il un repli sur l'auteur seul quand l'intitulé diffère ? Et les questions orales sans débat ? | « Auteur + intitulé seuls » : pas de repli (il ajouterait une quarantaine de questions, mais là où les deux règles répondent, il désigne un autre point dans 1 à 2 % des cas) ; une question sans lien garde sa raison (`intitule_different`, `auteur_sans_parole`, `seance_non_lue`, `ambigu`, `sans_date`, `titre_non_publie`). « Oui, QG et QOSD » : la même règle relie les questions orales sans débat (1 488 sur 1 643 en XVe, 715 sur 739 en XVIe, 791 sur 815 en XVIIe). Écartés : repli sur l'auteur ; questions au gouvernement seules | règle R-QAG ; section `questions` des candidats (`statut_seance`, `raison_seance`, `date_seance`, `lien_seance`, `intervenants`) |

---

## A — À trancher avant la première publication

### Q5. Jeton d'alerte et clés d'API dans les secrets du dépôt public

- **Bloque** : les alertes (issues du dépôt privé, doc. 2, 2.10), la mise à jour du jeu sur
  data.gouv.fr, l'import du code depuis le dépôt privé.
- **Ce qu'il faut** : un jeton à granularité fine limité aux issues du dépôt privé ; une
  clé de déploiement en lecture seule du dépôt privé ; une clé d'API data.gouv.fr. Les
  secrets ne sont pas exposés aux contributions externes d'un dépôt public, mais ils y sont
  stockés.
- **En attendant** : rien n'est créé ; les alertes ne vont que dans le résumé de la tâche.

### Q20. Votes sur une partie de texte financier, sur une résolution

- **Constat** (scrutins XVIIe, archive du 04/11/2026) : 10 votes portent sur une partie d'un
  PLF, d'un PLFSS ou d'un PLFG (« l'ensemble de la première partie… ») ; 13 propositions de
  résolution de l'article 34-1 et 6 « ensemble » de propositions de résolution sont des votes
  sur l'ensemble d'un texte qui n'est pas une loi.
- **Bloque** : R-NATURE-SCRUTIN, donc les dernières lectures et la section « Ce que cette
  personne a voté ».
- **En attendant** : la partie de texte a sa nature (`partie_de_texte`) et n'est jamais
  retenue comme dernière lecture ; les résolutions sont des votes `ensemble`, avec la nature
  du document (`PNRE`) affichée. Un changement est une nouvelle version de la règle.

---

### Q27. Un vote sur « l'article unique » d'un texte vaut-il vote sur l'ensemble ?

- **Constat** (scrutins XVIIe, collecte du 06/11/2026) : 47 scrutins portent sur l'article
  unique d'un texte. Ce vote vaut souvent adoption du texte, mais pas toujours (un vote sur
  l'ensemble peut suivre).
- **Bloque** : R-NATURE-SCRUTIN, donc les dernières lectures et la section « Ce que cette
  personne a voté ».
- **En attendant** : `article`, avec le détail `article_unique` ; jamais retenu comme
  dernière lecture.

### Q28. Ministres en « affaires courantes » après la fin officielle du gouvernement

- **Constat** (comptes rendus XVIIe) : 27 prises de parole écrites « ministre » tombent après
  la date de fin du gouvernement (exemple : le 16/12/2024, après la fin du gouvernement
  Barnier le 13/12, en affaires courantes).
- **Bloque** : `membre_gouvernement` (dates de fin), donc les paroles d'un gouvernement.
- **En attendant** : la fonction s'arrête à la date de fin publiée par l'Assemblée ; ces
  paroles ne sont rattachées à aucun gouvernement.

### Q29. Identifiants négatifs des comptes rendus

- **Constat** : François Bayrou, Premier ministre, porte l'identifiant `PA-125869` dans
  43 paragraphes du 17/12/2024 (315 paragraphes XVIIe à identifiant négatif en tout), absent
  de l'archive des acteurs.
- **Bloque** : l'attribution de ces paroles (R-ORATEUR), donc les paroles du gouvernement
  Bayrou ce jour-là.
- **En attendant** : non attribuées, avec la raison. Une décision `identite` pourrait associer
  un identifiant négatif à un `PA…` après vérification.

## B — À trancher avant d'activer la fonction

### Q7. Déports et collaborateurs

- Les **collaborateurs** sont une donnée personnelle « à ne pas publier sans décision » :
  par défaut ils ne sont **pas même stockés** (filtrés au découpage). Une décision contraire
  demanderait de relire les archives.
- Les **déports** (59 au 04/11/2026) ne sont ni interdits ni prévus par une section de fiche.
- **En attendant** : déports stockés, non affichés.

### Q21. Qualité d'un orateur quand le compte rendu ne la donne pas

- **Constat** (Syceron XVIIe du 03/11/2026) : le champ `qualite` est vide pour 82 % des
  paragraphes attribués. La décision du 04/11/2026 retient pour un gouvernement les paroles
  tenues « en qualité de membre du gouvernement **selon le compte rendu** ».
- **Bloque** : la section « Sur quoi ils ont pris la parole » des gouvernements (4.4) et la
  qualité affichée sur la fiche personne (4.2).
- **En attendant** : R-QUALITE (doc. 1, 1.6) déduit la qualité des fonctions à la date quand
  le compte rendu se tait (un membre du gouvernement à la date parle comme tel) ; l'origine de
  chaque qualité est gardée et le décompte publié dans la méthodologie. Un paramètre permet de
  ne retenir que la qualité écrite par le compte rendu.

### Q22. Publier un groupe dont la filiation attend une décision

- **Constat** : R-FILIATION peut laisser un groupe nouveau `a_trancher` (cahier 4.3, 6.1) : la règle ne
  le fait que lorsqu'un ancien groupe aurait **deux** suites qui passent le seuil. Mesuré sur l'archive du
  06/11/2026 (XIIe → XVIIe) : **aucun cas** ; 28 filiations retenues, 18 lignées publiées. La règle
  retrouve les deux exemples du cahier (Nouvelle Gauche : 51 % et 100 % ; Les Républicains après
  R-UMP : 100 % et 30 %).
- **Bloque** : la fiche de lignée de ce groupe, son adresse (registre, jamais changée), ses
  membres sur les fiches personne.
- **En attendant** : le groupe est publié comme sa propre lignée, marqué « filiation en
  attente de décision » ; si la décision le rattache ensuite à une lignée existante, son
  adresse devient une redirection (doc. 1, 1.2.2). Rien n'est perdu ni deviné.

### Q23. Mandats GOUVERNEMENT restés ouverts dans un gouvernement clos

- **Constat** (AMO30 du 03/11/2026) : 7 mandats GOUVERNEMENT du gouvernement Bayrou, clos le
  09/09/2025, n'ont pas de date de fin ni de mandat MINISTERE apparié ; la même personne a un
  autre mandat Bayrou correctement clos.
- **Bloque** : l'effectif et la composition du gouvernement (R-COMPOSITION).
- **En attendant** : ces mandats n'entrent pas dans la composition et sont signalés (A8) ; la
  propriétaire peut, par décision, les borner à la fin du gouvernement ou les faire signaler à
  la source.

---

## C — Réglages (le défaut peut rester)

### Q1. Seuil de « couverture suffisante » d'un ratio de groupe (règle 7) — interface

- **Décision de la propriétaire (04/11/2026)** : ce seuil relève de l'**affichage**, pas de
  la collecte. Les données sont collectées et calculées en entier, quel que soit le seuil.
- **Ce que fait le traitement** : pour chaque groupe et chaque scrutin, il sert les décomptes
  bruts (numérateur, dénominateur, part des membres à la date dont la position est connue).
  Il ne sert **pas** le ratio lui-même : les fichiers servis sont publics et téléchargeables
  directement, un ratio sous le seuil y serait déjà « publié » au sens de la règle 7.
- **Ce que fait l'interface** : elle calcule le ratio, ou affiche « N/D » sous le seuil.
- **Reste à fixer, côté interface** : le sens de « couverture » (part des membres dont la
  position est connue, ou part des scrutins où le groupe atteint un quorum, comme la fiche
  actuelle : « sur les 1 063 scrutins où le quorum du groupe est atteint, sur 9 509 ») et la
  valeur du seuil. Le seuil retenu est publié sur la page de méthodologie.
- **Ne bloque** ni la collecte ni la première publication des données.

| # | Réglage | Défaut |
| --- | --- | --- |
| Q12 | Relevé « suspect » si le nombre d'objets baisse de plus de… | 5 % |
| Q13 | Effondrement bloquant (C6) si une famille baisse de plus de… | 20 % sans retrait constaté |
| Q14 | Faits tirés au sort pour la vérification croisée (A2) | 40 par mise à jour |
| Q15 | Continuité d'un groupe qui change d'organe (R-CONTINUITE-GROUPE) | organe suivant ouvert au plus 7 jours après la fin du précédent, ≥ 5 membres communs, moyenne harmonique des deux parts ≥ 80 %. **Sans** le critère « même sigle » du premier défaut : 8 des 11 changements d'organe d'un même groupe de la XIIe à la XVIIe changent de sigle (UMP → LES-REP, SRC → SER, NG → SOC, AD → UDR…) avec 97 à 100 % de membres communs ; les dissidents restent loin du seuil (R-UMP 55 %, Agir ensemble 41 %, EDS 4 %) — archive du 06/11/2026 |
| Q16 | Sauvegarde de l'entrepôt sur le disque de la propriétaire | hebdomadaire, commande `empreinte sauvegarde` |
| Q17 | Mise à jour du jeu sur data.gouv.fr | hebdomadaire, la nuit du samedi |
| Q18 | Alerte de planification si aucune mise à jour depuis… | 26 h |
| Q24 | Fusion à l'affichage des permutations de commission (R-CARRIERE) : trou maximal entre deux périodes d'un même organe | 3 jours (trous mesurés : 1 à 3 jours, AMO30 du 03/11/2026) |
| Q25 | Plafond d'un segment de l'entrepôt | 90 Mo |
| Q26 | Édition datée du jeu téléchargeable | une par mois, plus `donnees-derniere` chaque soir |
