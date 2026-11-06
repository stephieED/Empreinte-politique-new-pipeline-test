# Export des faits

Chaque nuit, le traitement publie un **export plat** de ses faits : une ligne par fait, avec
ses identifiants de source, sa valeur, sa date et sa source. Il sert à comparer deux versions
(deux nuits, ou ce traitement et un autre) **fait par fait**, sans connaître le modèle interne
(commande de réalisation, section 7).

## Où le trouver

Release `export` du dépôt, un jeu par nuit, nommé d'après la génération de l'entrepôt :

| Fichier | Contenu |
| --- | --- |
| `faits-gNNNNNN.parquet` | l'export, en Parquet (zstd) |
| `faits-gNNNNNN.csv.gz` | le même, en CSV UTF-8 compressé, avec une ligne d'en-tête |

La génération `NNNNNN` est celle du manifeste de l'entrepôt (release `entrepot`) : elle relie
l'export aux relevés et aux versions de la même nuit.

## Colonnes

| Colonne | Sens |
| --- | --- |
| `cle_fait` | identifiant du fait, stable d'une nuit à l'autre : `type|clé` (voir les types) |
| `type_fait` | type de fait (`mandat`, `position_vote`, `signature`, `acte_reglementaire`…) |
| `fiche` | la fiche du site qui publie ce fait ; vide tant que les fiches ne sont pas composées |
| `id_acteur` | identifiant de personne de la source (`PA…` pour l'Assemblée, matricule pour le Sénat) |
| `id_organe` | organe (groupe, commission, ministère, gouvernement…) |
| `id_mandat` | mandat (`PM…`) |
| `id_scrutin` | scrutin (`VTANR5L17V…`) |
| `id_amendement` | amendement (`AMANR5L17…`) |
| `id_dossier` | dossier législatif (`DLR5L17N…`) |
| `id_document` | document (texte déposé, rapport…) |
| `id_reunion` | séance ou réunion (`RUANR5L17S…`) |
| `id_compte_rendu` | compte rendu de séance (`CRSANR5L17S…`) |
| `id_question` | question écrite, au gouvernement ou orale |
| `id_acte` | acte : acte de procédure d'un dossier, ou texte du Journal officiel (`JORFTEXT…`) |
| `id_autre` | un identifiant utile qui n'entre dans aucune colonne (point d'ordre du jour, `id_syceron`…) |
| `valeur` | le fait lui-même, en JSON : tous les champs lus dans la source |
| `date` | la date du fait (texte ISO) quand il en a une |
| `source_url` | adresse publique du fait quand elle existe et a été vérifiée |
| `source` | source (`an`, `senat`, `dila`, `wikipedia`) |
| `licence` | licence de la source (`etalab-2.0`, `cc-by-sa-4.0`…) |
| `prov_uid`, `prov_version` | le fichier de la source dont le fait est lu, et sa version dans l'entrepôt |
| `lecteur` | le lecteur qui a produit le fait, avec sa version (`an_scrutins@1`) |

Ordre des lignes : groupées par type de fait ; dans un type, l'ordre n'est pas garanti d'une
nuit à l'autre. Pour comparer, joindre sur `cle_fait`, qui est unique dans un export.

## Ce qui est exporté

L'**état courant** : pour chaque fichier de la source, sa dernière version, s'il est encore
présent à la source. Un fait retiré à la source n'est plus exporté ; un fait absent à cause
d'une panne l'est encore (sa source n'a pas été relue). Les listes livrées en complément
(suppressions du Journal officiel) sont exportées livraison par livraison.

Les présences et les noms des collaborateurs parlementaires, gardés dans l'entrepôt comme à la
source, ne sont jamais lus, donc jamais exportés.

## Comparer deux nuits

Avec DuckDB, par exemple :

```sql
-- faits apparus, disparus, ou dont la valeur a changé entre les générations 12 et 13
SELECT coalesce(a.cle_fait, b.cle_fait) AS cle_fait,
       CASE WHEN a.cle_fait IS NULL THEN 'apparu'
            WHEN b.cle_fait IS NULL THEN 'disparu'
            ELSE 'modifié' END AS changement
FROM 'faits-g000012.parquet' a
FULL JOIN 'faits-g000013.parquet' b USING (cle_fait)
WHERE a.cle_fait IS NULL OR b.cle_fait IS NULL OR a.valeur <> b.valeur;
```

## Types de faits

La liste à jour se lit dans le code : chaque lecteur (`empreinte_src/lecteurs/*.py`) déclare ses
types dans `EXPORT` (clé, identifiants, date).
