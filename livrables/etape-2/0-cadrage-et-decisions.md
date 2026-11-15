# Étape 2 — cadrage et décisions de la propriétaire

Ce que la propriétaire a fixé pendant l'étape 2, en plus de la commande (`REALISATION.md`) et
des questions tranchées du document 5. Chaque ligne cite sa formulation quand elle a été
donnée mot pour mot. Le document 5 porte les décisions éditoriales (Q1 à Q30) ; ici, le cadre
de travail.

## Le dépôt d'essai

| Sujet | Décision | Date |
| --- | --- | --- |
| Dépôt | `stephieED/Empreinte-politique-new-pipeline-test`, public ; code dans `depot-essai/` (clone local) | 06/11/2026 |
| Site et Pages | « tout ce qui est page et site est hors périmètre », puis « tu peux faire un html minimal mais pas besoin de déployer » : page minimale de contrôle livrée dans une archive (release `publication`), aucun déploiement | 06/11/2026 |
| Pages du dépôt d'essai | « je pense que je vais activer la page du depot de test afin de visualiser à minima la doc », puis « Doc + page minimale » : Pages sert la documentation du code (pdoc) et la page minimale de contrôle avec les fichiers servis de la dernière publication (workflow `pages.yml`, seule sa tâche `deployer` a les droits de Pages). Ce n'est toujours pas le site. Écartés : la doc seule ; pas de Pages avant la migration. Le réglage (source « GitHub Actions ») est fait par la propriétaire | 13/11/2026 |
| Migration | « Si le nouveau workflow est validé vs l'ancien, on migrera le travail sur le vrai dépot ou Page est activé » : voir `migration-vers-le-vrai-depot.md` | 06/11/2026 |
| Migration (organisation) | Le dépôt d'essai est renommé `Empreinte-politique-np` (non prod) et passé en privé : développement, branches, essais, décisions, alertes ; `Empreinte-politique` (public) est synchronisé sur lui et porte la mise à jour de chaque nuit, l'entrepôt, l'export et Pages (« Oui ta recommandation correspond à ce que j'avais en tête »). Écarté : la nuit dans le dépôt privé (machines de 7 Go, minutes et stockage décomptés). La date et le lancement du « remaniement » sont fixés par la propriétaire | 13/11/2026 |
| Fenêtre 9 h–19 h | « non, pas de fenêtre sur le dépôt de test » (la commande disait l'inverse ; la propriétaire a tranché après) ; gardée dans le code, désactivée par le réglage `fenetre_interdite` | 06/11/2026 |
| Alertes | dans les issues du dépôt d'essai (la propriétaire les a activées) ; aucun secret, le jeton de chaque exécution suffit | 06/11/2026 |
| Fusion des pull requests | « je préférerai que tu me laisse mergé les pr » : l'agent pousse une branche et ouvre une PR ; la propriétaire fusionne | 06/11/2026 |
| Réglages du dépôt | appliqués à sa demande : règle `protection-main` (pas de force-push ni de suppression sur `main`), approbation des workflows de contributeurs externes, actions de GitHub et des créateurs vérifiés seulement, wiki désactivé (issues réactivées ensuite) | 06/11/2026 |
| Périmètre | XVIIe pour toutes les familles de l'Assemblée ; Journal officiel depuis l'ouverture de la XVIIe ; Sénat ; candidats ; volet européen pour les seuls candidats anciens eurodéputés (proposition acceptée : « je suis ok avec tes propositions ») | 06/11/2026 |
| Périmètre de validation | Le périmètre XVIIe valait pour la première phase de développement, pas pour la validation (« j'étais d'accord en première phase de développement mais là, tu es en train de faire un plan de validation sur 7 nuits en mode restreint »). Les 7 nuits et les scénarios se font sur le **cahier 4.1, sans budgets ni mandats locaux** : scrutins, amendements, dossiers XIVe–XVIIe ; paroles XVe–XVIIe ; législatures XIVe–XVIIe ; gouvernements depuis 2007 (Journal officiel depuis 2007) ; Sénat ; candidats ; volet européen. Les nuits qui tournent avant ne comptent pas dans la série. La commande ne restreint pas le périmètre (section 4 : interface seulement) | 07/11/2026 |
| Gouvernements et Journal officiel | « On commence à la même période que la 14e leg » : gouvernements publiés à partir de la XIVe législature (20/06/2012), soit ceux qui la traversent, d'Ayrault II à aujourd'hui ; Journal officiel à partir de la même date. Remplace « depuis 2007 (Fillon I) » du cahier 4.1 et de la ligne du 07/11 | 13/11/2026 |
| Mandats locaux | « oui il faudrait les intégrer », puis « oui, confirme et lance l'instruction des mandats locaux » : les mandats locaux des candidats reviennent dans le périmètre de validation, que la ligne du 07/11 excluait (« sans budgets ni mandats locaux » ; les budgets restent exclus). Le rattachement d'un élu du Répertoire national des élus à un candidat est à instruire avant tout code (pas d'identifiant de personne à la source ; jamais par le nom seul) | 13/11/2026 |
| Section 3 de la commande | seuls P1 à P3 sont à corriger (la table s'arrête là) | 06/11/2026 |

## Les corrections de conception (P1 à P3)

| Point | Décision | Date |
| --- | --- | --- |
| P2, archives brutes | « Tout garder, public » : l'entrepôt garde chaque fichier reçu à l'octet près, présences et collaborateurs compris (données déjà publiques à la source, jamais servies). Écartés : filtrer et garder le brut 35 jours dans un dépôt privé (secret, réparable 35 jours seulement) ; filtrer sans brut (filtre irréparable) | 06/11/2026 |
| P2, archive globale du Journal officiel | « Archive à part + 2012 » : l'archive reçue de la DILA (`Freemium_jorf_global_…tar.gz`, 1,75 Go, 7,2 millions de fichiers depuis 1861) est gardée à l'octet dans une release à part, non rechargée chaque nuit ; l'entrepôt ne découpe que les actes et sommaires publiés depuis le 20/06/2012 (≈ 870 000 fichiers). Écartés : tout découper (13,7 Go, index de l'entrepôt à refaire) ; 2012 seulement sans garder l'archive (découpage irréparable) | 13/11/2026 |
| P2, exception : réponse de Wikidata | « Choix 2, exception à P2 » : pour le seul point `wd-identifiants-parlementaires`, l'entrepôt garde la réponse sous sa **forme canonique** (clés triées, écriture compacte, lignes sans doublon, dans l'ordre de la source), pas les octets reçus ; l'empreinte des octets reçus reste dans le relevé. Raison : Wikidata varie l'ordre des clés de chaque ligne d'une réponse à l'autre, ce qui faisait une version nouvelle sans changement réel (2 nuits sur 9, mesuré le 14/11/2026 ; annexe `autres-sources.md`, § 10). Rien du contenu n'est perdu ; la présentation exacte de Wikidata l'est. Écartés : ne rien changer (P2 intact, faux changements gardés) ; forme canonique et brute gardée à part (P2 intact, plus de place que sans rien changer) | 14/11/2026 |
| Rattrapage d'une nuit non écrite | gardé (« ça m'a l'air intelligent comme idée ») après proposition de le retirer | 06/11/2026 |

## Ordre et forme du travail

| Sujet | Décision | Date |
| --- | --- | --- |
| Doc. 4 (estimations) | « on remplace le point 4 par le rapport de mesure » : le document 4 de l'étape 1 n'est pas réaligné ; le rapport de mesures (`etape-2/3-rapport-de-mesures.md`, commande 9.3) le remplace (commande 1.4 : chaque estimation remplacée par une mesure) | 13/11/2026 |
| Livrables sur Pages | « j'aimerai publié ces livrables sur la page (peut-être pas tous mais on verra après coup ce qu'on garde) » : les livrables sont publiés sur le Pages du dépôt d'essai ; le choix de ce qui reste se fera après coup | 13/11/2026 |
| Ordre des fiches | « commence par legislature et gouvernement », puis « ok, commence par la fiche candidat » ; ensuite (proposé, non contredit) : lignée de groupe, volet européen, contrôles restants, scénarios, rapports | 06/11/2026 |
| Validation des candidats | « s'ils sont sur wikipedia alors c'est validé » (Q8) | 06/11/2026 |
| Source de la liste des candidats | « la liste de candidats doit se baser sur celle de franceinfo » : la page https://www.franceinfo.fr/elections/presidentielle/portraits-qui-sont-les-candidats-declares-a-l-election-presidentielle-de-2027_8208032.html remplace la liste de Wikipédia comme source des candidats déclarés. Restent à établir avec la propriétaire : le rattachement de l'identité (jusqu'ici article Wikipédia → Wikidata → identifiant Assemblée/Sénat, jamais par le nom seul) et ce que l'entrepôt garde d'une page sous droits | 13/11/2026 |
| Liste des candidats tenue à la main (option « A ») | franceinfo interdit tout son site aux robots d'IA (`robots.txt` : `Disallow: /` pour `Claude-Code`, `ClaudeBot`…) et réserve la fouille de textes et de données, avec obligation d'obtenir le consentement de France Télévisions (`tdm-reservation: 1`, `tdm-policy.json`, relevés le 13/11/2026). Réponse « A » : la liste est tenue dans `decisions/` (type `candidature`), une entrée par candidat déclaré sur franceinfo, avec l'adresse de la page, la date de lecture et l'élément Wikidata ; la propriétaire la valide en fusionnant la PR. L'identité suit l'élément Wikidata inscrit (méthode « décision », doc. 1, 1.5.1), puis Wikidata → identifiant Assemblée/Sénat. La page n'est pas collectée : l'entrepôt n'en garde que l'adresse et la date de lecture. Wikipédia reste lu comme détecteur : un écart entre les deux listes ouvre une issue. Écartée pour l'instant : demander l'accord de France Télévisions pour une collecte automatique | 13/11/2026 |
| Nom du paquet | `empreinte_src` (« sinon on peut l'appeler empreinte_src »), après examen de `empreinte/`, `traitement/`, `src/empreinte/`, `empreinte-src/` ; la commande reste `empreinte` | 06/11/2026 |
| Documentation du code | pdoc (« ajoute pdoc »), générée par le workflow des tests, artefact `documentation-code` | 06/11/2026 |
| Export de tous les faits lus | « Dernière nuit, Parquet » : la release `export` ne garde que l'export de la dernière nuit publiée, sans CSV (≈ 1,2 Go au lieu de 2,4 Go qui s'ajoutaient chaque nuit sur le périmètre complet) ; les faits publiés de chaque nuit restent tous. Écartés : tout garder ; hebdomadaire ; abandonner cet export | 12/11/2026 |

## Principes qu'elle a corrigés (à ne pas rouvrir)

- **Les règles du site ne s'appliquent pas au corpus.** Corrigé deux fois : Q1 (« ceci
  n'affecte pas la collecte. Cela relève du périmètre de l'interface ») et Q11 (« cette règle
  4.6 s'applique au site pas au corpus »). Une donnée se collecte et se stocke ; la décision de
  l'afficher est celle du site. Exception maintenue : un ratio n'est jamais écrit dans les
  fichiers servis (les décomptes, oui), parce que les fichiers servis sont publics.
