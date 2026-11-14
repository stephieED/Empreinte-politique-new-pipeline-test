# Décisions de la propriétaire

Les décisions sont des **entrées du traitement** (doc. 1, 1.3.3) : un fichier YAML par
décision, rangé dans un dossier par type. Elles sont datées et attribuées par le commit qui
les ajoute ; elles ne corrigent jamais une donnée publiée à la main.

Exemple, pour autoriser une publication refusée par un contrôle (une seule anomalie, celle
dont l'empreinte est donnée dans l'alerte) :

```yaml
# decisions/levee_controle/2026-11-12-pertes-scrutins.yaml
type: levee_controle
date: 2026-11-12
empreinte: "C1:3f9a0c2b7d1e4a55"
motif: "L'Assemblée a renuméroté les scrutins du 10/11 ; vérifié sur les pages publiques."
```

Types en usage : `levee_controle`, `fin_legislature`, `rattachement_portefeuille`,
`libelle_ministere`, `filiation`, `identite`, `perimetre`, `candidature`, `borne_mandat` (mandat resté ouvert dans un organe clos, borné à une date : Q23) (voir le document 1, 1.3.3).

Une décision `rattachement_portefeuille` donne le ou les ministères de tutelle d'un portefeuille
(`rattache_a PO…`, ou `rattache_a PO… PO…` pour une co-tutelle, dans l'ordre où la source les
nomme), avec le texte qui l'établit (`source`).

La liste des candidats est une décision `candidature` (`candidature/<date>-franceinfo.yaml`),
recopiée à la main de la page de franceinfo, qui n'est pas collectée : une nouvelle lecture de
la page est un nouveau fichier, la liste en vigueur est celle du fichier le plus récent.

Plusieurs décisions du même type peuvent tenir dans un seul fichier, sous la clé
`decisions:` (chaque élément hérite des champs communs du fichier) :

```yaml
# decisions/libelle_ministere/table.yaml
type: libelle_ministere
date: 2026-11-06
decisions:
  - libelle: "Ministère de l'intérieur"
    ministere_normalise: "Intérieur"
  - libelle: "Ministère de l'intérieur et des outre-mer"
    ministere_normalise: "Intérieur"
```
