# Extrait `syceron_l17_extrait.zip` (lecteur `an_comptes_rendus`)

- **Origine** : `https://data.assemblee-nationale.fr/static/openData/repository/17/vp/syceronbrut/syseron.xml.zip`,
  archive téléchargée le 04/11/2026 (`travail/sources/an-syceron/syseron17.xml.zip`,
  sha256 `d964ad634a0de016…`, `Last-Modified` du 03/11/2026).
- **Licence** : Licence Ouverte (Etalab) 2.0.
- **Contenu** : 5 comptes rendus recopiés **à l'octet près**, sous leur chemin d'origine
  (`xml/compteRendu/{uid}.xml`) ; 1 109 paragraphes ; 230 Ko compressés.

| Membre | Octets | sha256 (début) | Ce qu'il couvre |
| --- | --- | --- | --- |
| `CRSANR5L17S2026O1N177.xml` | 404 118 | `9ad4f78575e1c9b6` | nom affiché qui ne correspond pas à l'identifiant (`#4042860`, « Mme Alice Rufo, ministre déléguée » sous `PA722142`) ; deux `<orateur>` dans un paragraphe ; questions au gouvernement (points de niveau 1 et 2) ; suspension (`nivpoint="99"`) |
| `CRSANR5L17S2026O1N105.xml` | 156 669 | `db2e51405502edf5` | identifiants négatifs (`PA-126299`…) ; identifiant de repli `PA793214` porté par d'autres orateurs ; orateur sans `id_acteur` (`<id>0</id>`) ; bloc `interExtraction` ; suspension |
| `CRSANR5L17S2026O1N120.xml` | 118 887 | `28bb326cdf937ab8` | `id_acteur="PA0"` sur un paragraphe à plusieurs orateurs |
| `CRSANR5L17S2025O1N139.xml` | 179 574 | `394628ae275b4352` | points imbriqués sur quatre niveaux (1, 2, 3, 99) ; orateurs sans `id_acteur` ; `interExtraction` |
| `CRSANR5L17S2027O1N051.xml` | 363 798 | `5176525665ff75d0` | compte rendu **provisoire** (`etat = provisoire`), sans `stime` |
