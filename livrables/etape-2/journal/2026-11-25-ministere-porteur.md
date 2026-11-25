## Ministère porteur des projets de loi (issue #79) (25/11/2026)

R-DEPOT-GOUVERNEMENT passe en version 2. Chaque projet de loi reçoit son ministère porteur, qui
permet à l'interface de colorer les projets déposés d'un gouvernement.

**Constat.** L'issue partait de l'auteur du texte de dépôt (`auteurs_acteurs`). Sur la g25, cet
auteur est le Premier ministre pour 1 296 projets sur les 1 298 dont l'auteur est membre du
gouvernement : un projet est « présenté au nom du Premier ministre par » un ou plusieurs ministres.
L'Assemblée publie ces ministres comme **cosignataires** du texte de dépôt, pour 1 288 projets sur
1 312. Tous ces cosignataires sont membres du gouvernement du dépôt à la date du dépôt.

**Règle.** Les présentateurs sont les cosignataires du texte de dépôt (cosignature non retirée),
dans l'ordre publié, plus un auteur membre du gouvernement qui n'est pas le Premier ministre (cas
d'un projet déposé au Sénat). Chacun est joint à son portefeuille (`membre_gouvernement`) dans le
gouvernement du dépôt, à la date. Un ministre délégué ou un secrétaire d'État compte pour sa ou
ses tutelles (R-COMPOSITION, co-tutelle : Q41). Un seul ministère donne `etabli` ; plusieurs
donnent `plusieurs_ministeres`, tous servis sans choix (Q64). Sinon le statut est `non_etabli`,
avec sa raison : `seul_le_premier_ministre_cite`, `aucun_membre_du_gouvernement_cite`,
`presentateur_hors_gouvernement_a_la_date`, `rattachement_non_etabli`,
`gouvernement_non_etabli` ou `composition_non_calculee`.

**Fichiers servis.** `gouvernements/<adresse>/deposes.json.gz` reçoit 7 colonnes nouvelles à côté
de `ministere_porteur`, qui était toujours vide : `ministere_porteur_libelle`,
`ministeres_porteurs`, `ministeres_porteurs_libelles`, `ministere_porteur_statut`,
`raison_ministere_porteur`, `portefeuilles_presentateurs` et
`portefeuilles_presentateurs_libelles`. Aucune personne n'est servie : un projet n'est jamais
l'acte personnel d'un ministre.

Mesuré sur la g25 (tables rejouées) : ministère porteur établi pour 1 289 projets sur 1 312
(98,2 %). 1 164 ont un seul ministère, 125 en ont plusieurs. Restent 20 projets où seul le Premier
ministre est cité (dont 8 sous Castex, pour la plupart des textes sur la crise sanitaire) et 3 sans membre du gouvernement cité.
Aucun fait servi ne disparaît (C1) : mêmes projets, mêmes identifiants.
