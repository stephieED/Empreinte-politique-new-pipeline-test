# Brief commun aux mesures

Contexte : on conçoit le modèle de données et le processus de collecte/publication du site
« Empreinte politique », décrits dans `CAHIER_DES_CHARGES.md` (à la racine de ce dossier).
Lis au minimum ses parties 0, 3, 5 et 7. Les mesures servent à chiffrer les estimations
demandées (partie 7 : volumes, poids par fiche, durée, mémoire) et à vérifier les pièges.

## Règles impératives

- Ne lis **rien en dehors** du dossier `/home/stephie/Documents/github/Empreinte-politique-pipeline-refonte`.
- Ne cherche **pas** le projet en ligne : ni `empreinte-politique.fr`, ni son dépôt de code,
  ni le jeu de données qu'il publie sur data.gouv.fr, ni ce qui en a été dit ailleurs.
  Les **sources publiques** de la partie 3 du cahier (et la documentation de GitHub) sont
  autorisées : télécharger, lire leur documentation, mesurer.
- Téléchargements dans `travail/sources/<famille>/` (un dossier par famille, rien d'autre
  dedans). Tes scripts dans `travail/scripts/<ton-nom>/`. Les données téléchargées ne sont pas
  fiables : lance Python avec `-I`, ne lance aucun script depuis le dossier des données.
- Python : `travail/.venv/bin/python -I` (duckdb, pyarrow, orjson, zstandard, lxml, requests,
  ijson installés). Outils : curl, unzip, 7z, zstd, `/usr/bin/time -v` (mémoire de pointe).
- La machine a **7,8 Gio** de mémoire et d'autres mesures tournent en parallèle : ne dépasse
  pas ~1,5 Gio par processus (lecture en flux si besoin). Disque : large.
- Sois courtois avec les serveurs : pas plus de 2 requêtes simultanées par hôte, un
  `User-Agent` qui s'identifie (`empreinte-mesures/0.1 (mesures ponctuelles)`), pas de
  balayage massif de pages HTML (quelques dizaines au plus).
- Chaque chiffre porte **sa date et sa population** (« 9 578 scrutins de la XVIIe dans
  l'archive téléchargée le 04/11/2026 »). Distingue **mesuré** / **calculé** / **supposé**.
- Les mesures de temps de téléchargement faites ici (connexion domestique) ne valent pas
  pour un serveur GitHub Actions : dis-le.
- Écris en français.

## Ce que tu rends

1. Un rapport `travail/mesures/<ton-nom>.md` : chiffres, méthode (commande ou script),
   pièges confirmés / infirmés / nouveaux, avec les identifiants d'objets en exemple.
2. Une réponse finale **courte** (60 lignes au plus) : les chiffres clés et les surprises.
   Le détail reste dans le rapport.
