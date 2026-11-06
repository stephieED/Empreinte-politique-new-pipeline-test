# Extrait `amendements_l17_extrait.zip` (lecteur `an_amendements`)

- **Origine** : `https://data.assemblee-nationale.fr/static/openData/repository/17/loi/amendements_div_legis/Amendements.json.zip`,
  archive téléchargée le 04/11/2026 (`travail/sources/an-amendements/Amendements17.json.zip`,
  sha256 `9643f27e26aa74cd…`, `Last-Modified` du 03/11/2026).
- **Licence** : Licence Ouverte (Etalab) 2.0.
- **Contenu** : 13 membres recopiés **à l'octet près**, sous leur chemin d'origine dans l'archive
  (`json/{dossier}/{document}/{uid}.json`) ; 27 Ko compressés.

| Membre | Octets | sha256 (début) | Ce qu'il couvre |
| --- | --- | --- | --- |
| `AMANR5L17PO838901B2202P0D1N000011.json` | 8 510 | `79eea3367f93f209` | copie `B` d'une paire `B`/`BTC`, rangée dans `json/incorrect_data/` |
| `AMANR5L17PO838901BTC2202P0D1N000011.json` | 8 514 | `e6f093588e71d401` | copie `BTC` de la même paire (même examen, même numéro) |
| `AMANR5L17PO419610B1906P2D1N000024.json` | 13 552 | `a95f4fd161c26df6` | liste de cosignataires avec un **doublon** (`PA795482` deux fois) ; amendement de crédits PLF ; mission visée ; groupe de l'auteur |
| `AMANR5L17PO838901B3210P2D1N001096.json` | 13 450 | `5dc7a74e54a1f4ad` | le maximum de la XVIIe : 242 cosignataires ; auteur « Rapporteur » |
| `AMANR5L17PO838901B1906P1D2N000001.json` | 2 681 | `0917d26b95c59168` | amendement « effacé » : type « Député » sans auteur, sans corps, sans date |
| `AMANR5L17PO838901BTC2468P0D1N000300.json` | 3 632 | `3a63d6b3193c7b32` | auteur « Gouvernement » (sans `acteurRef`) ; adopté ; séance de discussion ; discussion identique |
| `AMANR5L17PO838901B1851P0D1N000018.json` | 3 510 | `c66c7d3dd5f9577c` | auteur « Rapporteur » avec `auteurRapporteurOrganeRef` ; retiré avant publication |
| `AMANR5L17PO838901BTC1245P0D1N000038.json` | 3 528 | `d45551be4525c439` | irrecevable (doublon) : ni exposé ni dispositif |
| `AMANR5L17PO59051B1105P0D1N000015.json` | 3 511 | `7fa8932fcc9ea5c8` | un seul cosignataire, écrit en chaîne et non en liste |
| `AMANR5L17PO838901B1907P0D1N002663.json` | 3 458 | `5d4e293fd4072112` | sous-amendement (`amendementParentRef`) |
| `AMANR5L17PO420120B1907P0D1N000779.json` | 3 556 | `008db7c444cac82f` | `suffixe` renseigné |
| `AMANR5L17PO838901B0622P0D1N000312.json` | 3 993 | `deba9370a6f73c3c` | sous-état « R » (code et libellé « R ») sous l'état « En traitement » |
| `AMANR5L17PO838901BTC2146P0D1N000007.json` | 5 461 | `11a0391e0a41ef68` | dispositif de crédits PLFR (`dispositifAmdtCreditPLFR`) |

Les variantes de forme non présentes en XVIIe (identifiant sans `PA`, cosignataire écrit en objet
seul, date écrite `xsi:nil`) sont testées en modifiant un membre en mémoire, jamais sur disque.
