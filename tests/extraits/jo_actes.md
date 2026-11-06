# Extraits du lecteur `jo_actes` (Journal officiel, livraisons de la DILA)

Origine : `https://echanges.dila.gouv.fr/OPENDATA/JORF/`, trois livraisons téléchargées le
04/11/2026 (`travail/sources/dila/JORF_20261102-213929.tar.gz`, `…20261103-214151…`,
`…20261104-004428…`). Licence Ouverte (Etalab) 2.0.

Chaque extrait est une archive `tar.gz` qui ne garde que quelques membres de la livraison
d'origine, **recopiés à l'octet près, sous leur chemin d'origine** (horodatage compris) ; seuls
l'ordre et l'en-tête tar sont ceux de la recopie. Script : `faire_extraits_jo.py` (bloc-notes de
la session, non versionné).

| Fichier | Membres | Ce qu'ils couvrent |
| --- | --- | --- |
| `jo_JORF_20261102-213929_extrait.tar.gz` (14 Ko) | plan + version de `JORFTEXT000055037137`, `…051538879`, `…051575460`, `…033703701`, `…000721454` ; plan seul de `…021262661` | décret 2026-1013 (signataires en texte libre, ministère, liens CITATION vers une loi et un article de loi) ; loi 2025-391 **en double** (deux `JORFTEXT`) ; liens `APPLICATION` ; texte de 1992 **redélivré**, avec rectificatif (`RECT`) ; plan à trois versions (`VIGUEUR`, `MODIFIE`, dates `2999`) |
| `jo_JORF_20261103-214151_extrait.tar.gz` (6 Ko) | plan + version de `JORFTEXT000051538879` et `…055047268` | la loi 2025-391 **redélivrée** d'une livraison à l'autre (même empreinte, uid nouveau dans l'entrepôt) ; loi 2026-1015 sans ministère |
| `jo_JORF_20261104-004428_extrait.tar.gz` (6 Ko) | plan + version de `JORFTEXT000055053883`, sommaire `JORFCONT000055053315`, article `JORFARTI000055053487`, section `JORFSCTA000055053400` | date de signature sentinelle `2999-01-01`, signataires vides ; sommaire du JO n° 258 avec la rubrique « Mesures nominatives » ; article et section (non lus) |

Le test `test_liste_de_suppressions` porte, dans son code, les cinq lignes de la liste de
suppressions de la livraison `20261020-214622` (`liste_suppression_jorf.dat`, rangée dans
l'entrepôt complet du 06/11/2026) : aucune des trois livraisons de `travail/sources/` n'en a.

| `jo_JORF_20261104-004428_regles_extrait.tar.gz` | 4 actes recopiés à l'octet de la livraison `JORF_20261104-004428.tar.gz` (DILA), pour les tests des règles du JO (`tests/test_regles_d.py`) | 04/11/2026 | Licence Ouverte 2.0 |
