# Migration vers le vrai dépôt (si le nouveau traitement est retenu)

Ce que le dépôt d'essai fait autrement que le vrai dépôt ne le fera, et ce qu'il faudra
activer au transfert. À tenir à jour.

## Organisation retenue (13/11/2026)

La propriétaire fixe la date et lance le « remaniement » elle-même.

| Dépôt | Visibilité | Rôle |
| --- | --- | --- |
| `Empreinte-politique-np` (le dépôt d'essai, renommé ; « np » : non prod) | **privé** | développement : code, branches, PR, essais, décisions, alertes |
| `Empreinte-politique` | public | **la mise à jour de chaque nuit**, l'entrepôt (releases), l'export, Pages ; son code est synchronisé depuis `np` (« import du soir », doc. 2, 2.12) |

Pourquoi la nuit dans le public : sur un dépôt public, les machines de GitHub Actions ont
16 Go de mémoire et des minutes non décomptées ; sur un dépôt privé, 7 Go, et les minutes
(≈ 60 à 100 h par mois mesurées en novembre 2026) et le stockage des artefacts (1 à 2,5 Go
par calcul) sont décomptés du forfait. Chiffres de GitHub à vérifier sur le compte avant le
remaniement. L'entrepôt reste public (décision du 04/11/2026).

## Ce qui change au transfert

| Point | Dépôt d'essai aujourd'hui | Au transfert |
| --- | --- | --- |
| Visibilité, nom | public, `Empreinte-politique-new-pipeline-test` | renommé `Empreinte-politique-np`, privé ; GitHub redirige l'ancien nom ; le nom écrit en dur dans les documents et les prompts est à corriger (le code le lit dans `GITHUB_REPOSITORY`) |
| Mise à jour de chaque nuit | dans le dépôt d'essai | dans `Empreinte-politique` ; dans `np`, seulement des essais (`mode=essai`), qui consomment des minutes du forfait, sur des machines de 7 Go : régler `EMPREINTE_DUCKDB_MEMOIRE` (4 Go aujourd'hui) et vérifier le pic (**5,0 Go** mesuré le 13/11 sur le calcul avec le JO depuis 2012, en E4 ; « 4,2 Go » écrit d'abord, lu à tort dans `time -v`, qui ne voit que la dernière étape) |
| Entrepôt, export, publication, archives brutes | releases du dépôt d'essai (`entrepot`, `export`, `publication`, `archives-brutes`) | releases de `Empreinte-politique` ; les essais de `np` doivent pouvoir les lire (jeton de lecture, ou dépôt public lisible sans jeton) |
| Synchronisation du code | — | import du soir de `np` vers `Empreinte-politique` : clé de lecture du dépôt privé dans les secrets du dépôt public (Q5) |
| Déploiement | depuis le 13/11/2026, workflow `pages.yml` : documentation du code et page minimale de la dernière publication (archive de la release `publication`), après chaque mise à jour sur `main` ; le site n'est pas déployé | ajouter à la tâche `ecrire` une étape `actions/deploy-pages` (droits `pages: write`, `id-token: write`) ; source Pages « GitHub Actions » ; arborescence déjà prête (`donnees/<publication>/…`, fichiers pré-compressés) |
| Fenêtre 9 h–19 h | désactivée (`fenetre_interdite: false`) | `fenetre_interdite: true` ; fériés exclus |
| Interface | page minimale de contrôle (`empreinte_src/site/`) | le site (JavaScript) dans son propre dossier, qui lit les fichiers servis (contrat `1.0`) ; écrire le contrat une fois en schémas partagés (`contrat/`) |
| Documentation du code | artefact du workflow des tests | servie par Pages à côté du site |
| Réglages du dépôt | règle `protection-main`, approbation des contributions externes, actions vérifiées | à refaire à l'identique dans les deux dépôts |
| Alertes | issues du dépôt d'essai | issues de `np` (privé : les textes d'alerte ne sont plus publics) ; jeton à granularité fine limité à ce dépôt pour que la nuit du dépôt public y écrive (Q5) |
| Décisions et journal | `decisions/` dans le dépôt ; journal, cadrage et questions dans `livrables/`, hors dépôt | les verser dans `np` |
| Jeu téléchargeable | release `export` | data.gouv.fr (clé d'API, Q5) |
