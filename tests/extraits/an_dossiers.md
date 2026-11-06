# Extraits du lecteur `an_dossiers`

Origine : archives des dossiers législatifs de l'Assemblée nationale téléchargées le
**04/11/2026** dans `travail/sources/an-scrutins-dossiers/` (adresses :
`https://data.assemblee-nationale.fr/static/openData/repository/{14..17}/loi/dossiers_legislatifs/…`,
voir `livrables/annexes/mesures/an-scrutins-dossiers.md`, section 1). Licence Ouverte (Etalab) 2.0.
Chaque membre est recopié **à l'octet près**, sous son chemin d'origine dans l'archive.

| Fichier | Archive source | Membres | Ce qu'il couvre |
| --- | --- | --- | --- |
| `an_dossiers_l17_extrait.zip` (28 Ko) | `17_Dossiers_Legislatifs.json.zip` (produite le 03/11/2026) | `json/dossierParlementaire/` : `DLR5L17N53259`, `DLR5L17N53597`, `DLR5L17N52428`, `DLR5L16N49107`, `DLR5L17N51481`, `DLR5L15N37118`, `DLR5L17N51610` ; `json/document/` : `PNREANR5L17B0643`, `RAPPANR5L17B2865`, `PRJLANR5L17BTC3188`, `PIONSNR5S459BTA0143`, `PRJLANR5L17B2155` | arbre complet d'un projet de loi promulgué (53259 : saisine au fond, rapporteur, décision, texte adopté, NOR) ; **49.3** et motions de censure, actes **partagés** entre 53597 et le PLF 2026 (52428, avec ses études PLF) ; scrutin **du Sénat** cité (49107) ; décision du Conseil constitutionnel (51481) ; fusion de dossiers (37118) ; `titreChemin` nul (51610) ; documents : cosignataire retiré (B0643), division aplatie (B2865-COMPA), document supprimé (`metadatas.dateSuppression`, BTC3188), document du Sénat sans législature, projet de loi |
| `an_dossiers_l15_extrait.zip` (2 Ko) | `15_Dossiers_Legislatifs_XV.json.zip` (09/06/2022) | `json/dossierParlementaire/DLR5L15N36364.json` | rectificatif au JO (`infoJORect`) |
| `an_dossiers_l16_extrait.zip` (2 Ko) | `16_Dossiers_Legislatifs.json.zip` (28/06/2024) | `json/dossierParlementaire/DLR5L16N49095.json` | convocation du Congrès (`texteExterneAssocie`, `initiateur.organes`) |
| `an_dossiers_l14_fragment.zip` (3 Ko) | `14_Dossiers_Legislatifs_XIV.json.zip` (09/03/2018) | `Dossiers_Legislatifs_XIV.json` **tronqué** | voir ci-dessous |

**Fragment XIVe.** L'archive XIVe est un seul fichier `export` de 36,2 Mo. Le fragment est la
mise bout à bout de tranches **exactes** du fichier (positions en octets, fin exclue) :
`[0, 1541)` — l'ouverture et le premier document, `PIONANR5L15B0759` (un document de la XVe
dans l'archive XIVe) ; `[21639051, 21639091)` — la jonction `]}, "dossiersLegislatifs": {"dossier": [` ;
`[30769019, 30778748)` — le dossier `DLR5L14N35433` (promulgation avec `referenceNOR` et
`urlLegifrance` **au niveau de l'acte**, décision citant `VTANR5L14V1362`, absent de l'archive
XIVe des scrutins) ; puis le séparateur `, ` (2 octets, celui qui sépare les éléments dans le
fichier) ; `[34304394, 34305800)` — le dossier `DLR5L14N35050` (49.3) ; `[36246390, 36246394)` —
la fermeture `]}}}`. JSON valide dont chaque octet vient du fichier, mais pas le membre entier.

Empreintes SHA-256 (16 premiers caractères) des membres XVe-XVIIe : DLR5L17N53259 `828965a7c3524916`,
DLR5L17N53597 `6cca454b50e78a38`, DLR5L17N52428 `4ac48da8a34eeb47`, DLR5L16N49107 `13fe97879b0f6481`,
DLR5L17N51481 `e4045b2c2a9533cc`, DLR5L15N37118 `88c3359b560a85a3`, DLR5L17N51610 `972baa9612a3b169`,
PNREANR5L17B0643 `04250db7315e8a0d`, RAPPANR5L17B2865 `26057a4c776cd025`, PRJLANR5L17BTC3188 `25d8269de253124a`,
PIONSNR5S459BTA0143 `9de96844a809c7d9`, PRJLANR5L17B2155 `d9849e0ed8c49b3c`, DLR5L15N36364 `5f5555266d122b76`,
DLR5L16N49095 `a0a6c460b711ce9a`.
