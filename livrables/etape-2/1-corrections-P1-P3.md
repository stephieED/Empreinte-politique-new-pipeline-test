# Étape 2 — Corrections P1 à P3

Réponse à la section 3 de la commande de réalisation (`REALISATION.md`). Pour chaque point :
le défaut, ce qui change, où c'est écrit, et comment c'est vérifié. Les documents 1 et 2 sont
mis à jour en conséquence ; le journal de l'étape 2 (`journal-des-changements.md`) liste
chaque modification.

---

## P1 — L'attribution d'un identifiant de personne est conservée pour toujours

**Le défaut.** `per:000123` était dit « séquentiel, jamais réutilisé », mais il était
calculé par R-IDENTITE dans le graphe relié (Z3), refait chaque soir. Rien de conservé ne
gardait l'attribution : un changement d'ordre de lecture, une source en plus ou une fusion
pouvaient renuméroter des personnes, donc changer des adresses.

**Ce qui change.** L'attribution devient un objet **acquis**, au même titre que les relevés
et les objets sources : le **registre des identités** (ZI), dans l'entrepôt.

| Table | Une ligne par | Colonnes |
| --- | --- | --- |
| `attribution` | (source, uid) rattaché à une personne | `per`, `source`, `uid`, `depuis` (génération), `jusqu_au` (génération, vide tant qu'elle vaut), `motif` (`nouvelle_personne`, `rapprochement`, `decision`) |
| `fusion` | personne absorbée | `per_absorbe`, `per_retenu`, `generation`, `decision` |
| `compteur` | — | dernier numéro attribué |

Règles :

1. R-IDENTITE lit **d'abord** le registre. Un (source, uid) déjà attribué garde son `per`,
   quel que soit l'ordre de lecture ou l'arrivée d'autres sources.
2. Une personne nouvelle (aucun de ses identifiants de source n'est attribué) reçoit
   `compteur + 1`, ajouté au registre.
3. Deux personnes reconnues comme une seule (un sénateur devenu député, rapproché par
   Wikidata) : le numéro **le plus ancien** est retenu, l'autre devient un alias (`fusion`) ;
   son adresse devient une redirection. Aucun numéro n'est réattribué.
4. Un rapprochement reconnu faux : l'attribution fautive est close (`jusqu_au`) et le
   (source, uid) reçoit un numéro neuf. L'ancien numéro reste à la personne qu'il désignait.
5. Le registre ne fait que croître : aucune ligne n'est modifiée sauf `jusqu_au`, et le
   contrôle C1 refuse une publication dont le registre a perdu une ligne.

La même construction vaut pour le **registre des adresses** (déjà en ajout seul, doc. 1,
1.2.2) : il est désormais rangé dans l'entrepôt avec le registre des identités.

**Vérification.** Tests du dépôt d'essai, dans `tests/test_identites.py` :

- deux exécutions de R-IDENTITE sur les mêmes sources lues dans un ordre différent donnent
  les mêmes numéros ;
- une personne ajoutée reçoit le numéro suivant, les autres ne bougent pas ;
- une fusion garde le numéro le plus ancien et inscrit l'alias ;
- un registre amputé d'une ligne est refusé.

---

## P2 — Un découpage erroné doit pouvoir être refait

**Le défaut.** L'entrepôt gardait des objets **découpés et filtrés** (re-sérialisés sans les
présences ni les collaborateurs), et seulement l'empreinte de l'archive reçue. Si le
découpage ou le filtre se trompait, la version passée était perdue : l'Assemblée réécrit son
archive courante chaque nuit, on ne peut pas la retélécharger telle qu'elle était.

**Ce qui change** (décision de la propriétaire du 06/11/2026 : tout garder, entrepôt public).

1. **Plus de filtrage avant stockage.** Les présences et les noms des collaborateurs sont
   gardés dans l'entrepôt comme à la source. Ce sont des données déjà publiques à la source ;
   les règles de la partie 2 s'appliquent au site, pas au corpus. Ils ne sont **jamais
   servis** : aucun lecteur ne les lit, aucun schéma de fichier servi n'a de champ pour eux,
   et le contrôle C4 le vérifie.
2. **Le découpage devient un dépaquetage.** E2 ne fait plus que sortir de l'archive chacun
   de ses fichiers membres (un JSON d'acteur, de scrutin, d'amendement ; un XML de séance ou
   de texte du JO ; le fichier unique d'une archive de la XIVe ; le dump du Sénat) et le
   garder **à l'octet près**, compressé, avec son chemin dans l'archive. L'empreinte est celle
   des octets exacts.
3. **Le découpage logique passe dans la lecture.** Tout ce qui interprète le contenu (un
   fichier qui contient plusieurs objets, le choix des champs, la reconnaissance du schéma)
   est fait par les lecteurs (E3), versionnés et rejouables sur toutes les versions
   conservées. Une erreur de lecture se corrige donc comme une autre : nouvelle version du
   lecteur, relecture de l'historique.
4. **L'archive se reconstruit.** Chaque relevé garde la **liste des membres** de l'archive
   (chemin, taille, CRC, empreinte des octets). Avec les versions de Z1, on retrouve le
   contenu exact de chaque archive reçue, fichier par fichier. Seul l'emballage zip (niveau
   de compression, ordre des entrées) n'est pas reproduit, et il ne porte aucune donnée.

| Source | Ce qui est gardé à l'octet près | Retrouvable à la source ? |
| --- | --- | --- |
| Assemblée, archives courantes | chaque fichier membre | non (réécrites chaque nuit) : d'où l'entrepôt |
| Assemblée, archives figées | chaque fichier membre | oui, mais gardé aussi |
| Journal officiel | chaque texte XML des livraisons | oui (livraisons et dump conservés par la DILA) |
| Sénat | le dump de l'export | non : gardé à chaque changement |
| Parltrack | chaque instantané lu | oui (`dumps/arch/` depuis 2019) |
| Wikipédia | — (faits seulement) | oui : chaque révision est conservée par Wikipédia, on garde son numéro |
| Sycomore, fichier des places | — (faits seulement, tous droits réservés) | oui tant que la page est en ligne ; on garde l'adresse et l'empreinte de la page lue |

**Coût.** Le volume s'écarte peu de l'entrepôt filtré prévu au document 4 : les octets
filtrés étaient surtout les présences de l'agenda (36 % de l'archive de l'agenda de la XVIIe,
qui pèse 8,6 Mo compressés, mesuré le 04/11/2026), et le dump du Sénat est gardé à chaque
changement (8,6 Mo compressés au plus par nuit). Le coût réel sera **mesuré** chaque nuit
pendant l'étape 2 (taille de l'entrepôt et croissance par nuit, section 5 de la commande).

**Vérification.** Test `tests/test_reconstruction.py` : une archive d'extraits réels est
dépaquetée, puis reconstruite depuis l'entrepôt ; chaque membre a la même empreinte que dans
l'archive d'origine. Scénario « erreur de lecture corrigée » (section 6 de la commande) :
une correction de lecteur relit l'historique sans recollecte.

---

## P3 — Seule l'étape qui publie peut écrire

**Le défaut.** Aucun document ne disait quelle tâche peut écrire quoi. Et le document 2
faisait téléverser l'acquis par E2, avant tout calcul : la collecte avait donc besoin du
droit d'écrire.

**Ce qui change.** Le workflow est découpé en tâches GitHub Actions. Chaque tâche déclare ses
droits dans le workflow (clé `permissions`), et le droit par défaut du dépôt est la lecture
seule.

| Tâche | Étapes | Droits | Ce qu'elle produit |
| --- | --- | --- | --- |
| `preparer` | E0 | `contents: read` | le plan de la nuit ; refus immédiat d'une option invalide |
| `collecter` | E1, E2, E3 | `contents: read` | un artefact « acquis » : relevés, nouvelles versions, liste des membres ; cache de lecture |
| `calculer` | E4, E5, E6 | `contents: read` | un artefact « candidate » : fichiers servis, export plat, ajouts au registre des identités, rapport et anomalies |
| `ecrire` | E7 | `contents: write` | **seule tâche qui écrit** : entrepôt (acquis + registres), magasin des publications, export, page minimale, rapport |
| `alerter` | E8 | `issues: write` | les issues d'alerte, une par sujet ; ne touche à aucun fichier |

Comment l'acquis reste acquis sans que la collecte écrive : `ecrire` tourne **même si
`calculer` échoue ou si un contrôle bloque** (condition `always()` sur le succès de
`collecter`). Dans ce cas, elle écrit l'acquis et les ajouts au registre, et rien d'autre. Si
la tâche `ecrire` elle-même n'a pas lieu (machine perdue), l'artefact « acquis » reste
disponible : la nuit suivante le récupère et l'écrit en premier.

Aucun secret n'est nécessaire : le jeton fourni à chaque exécution suffit, avec les droits
ci-dessus. Les alertes vont dans les issues du dépôt d'essai.

**Vérification.** Le workflow est relu par un test (`tests/test_workflow.py`) : droits par
défaut en lecture seule ; `contents: write` dans la seule tâche `ecrire` ; `issues: write`
dans la seule tâche `alerter` ; aucune autre permission.
