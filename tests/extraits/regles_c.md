# Extraits des règles du groupe C (paroles et ordre du jour)

Membres recopiés **à l'octet près** (mêmes noms de membres, mêmes octets ; seul le conteneur zip
est refait). Licence Ouverte (Etalab) 2.0. Utilisés par `tests/test_regles_c.py` avec
`syceron_l17_extrait.zip` (fiche `an_comptes_rendus.md`).

## `amo30_l17_orateurs_extrait.zip` (11 membres, 27 Ko)

Origine : `travail/sources/an-amo/AMO30_17.json.zip` = `…/repository/17/amo/tous_acteurs_mandats_organes_xi_legislature/AMO30_tous_acteurs_tous_mandats_tous_organes_historique.json.zip`
(Last-Modified 03/11/2026 01:34 GMT, téléchargée le 04/11/2026, sha256 `41561aa52d8f4617…`).

| Membre | Octets | sha256 (début) | Pourquoi |
| --- | --- | --- | --- |
| `json/acteur/PA722142.json` | 68 827 | `8fa15bedd3b1f2f9` | François Ruffin : son identifiant porte « Mme Alice Rufo, ministre déléguée » (`CRSANR5L17S2026O1N177 #4042860`) |
| `json/acteur/PA793214.json` | 12 512 | `f706f4009385784c` | Audrey Abadie-Amiel : identifiant de repli de la source (`CRSANR5L17S2026O1N105`) |
| `json/acteur/PA873629.json` | 2 341 | `ac52fc30ed28d2c0` | Alice Rufo (identité réelle de l'oratrice du #4042860) |
| `json/acteur/PA721908.json` | 117 553 | `7dee17886c3b9572` | vice-présidente ; préside `N177` sous « Mme la présidente », parfois sans `roledebat` |
| `json/acteur/PA870010.json` | 14 302 | `94d987d56472b870` | Sébastien Martin, ministre délégué (gouvernement Lecornu II) dans `N177` |
| `json/acteur/PA795990.json` | 27 338 | `1e6f16c6fd50b3d0` | Maud Bregeon, ministre déléguée, qualité écrite composée (« porte-parole du gouvernement… ») |
| `json/acteur/PA718850.json` | 57 557 | `40974910d6034aa6` | Pierre Cordier, député sans qualité écrite dans `N177` |
| `json/acteur/PA2538.json` | 21 561 | `de592ae6faa1ea29` | Bruno Retailleau, ministre d'État (gouvernement Bayrou) dans `N139` |
| `json/organe/PO838901.json` | 628 | `a4f208ea94a14e22` | Assemblée nationale, XVIIe législature |
| `json/organe/PO873634.json` | 481 | `96c3781b2da30a1b` | gouvernement Lecornu II |
| `json/organe/PO855052.json` | 485 | `6a7b10e8816c9457` | gouvernement Bayrou |

## `agenda_l17_seances_extrait.zip` (6 membres, 7 Ko)

Origine : `travail/sources/an-agenda/Agenda_17.json.zip` = `…/repository/17/vp/reunions/Agenda.json.zip`
(Last-Modified 04/11/2026 11:41 GMT, téléchargée le 04/11/2026, sha256 `e16f09ad81dbafa8…`).

| Membre | Octets | sha256 (début) | Pourquoi |
| --- | --- | --- | --- |
| `json/reunion/RUANR5L17S2026IDS30399.json` | 3 073 | `a45e322660b0cd15` | séance du compte rendu `N177` (questions au gouvernement, débats) : points sans dossier |
| `json/reunion/RUANR5L17S2025IDS29213.json` | 10 396 | `38b8c34a5ac21a82` | séance de `N139` : 13 points dont 11 supprimés, deux dossiers cités (narcotrafic, procureur) |
| `json/reunion/RUANR5L17S2026IDS30144.json` | 6 848 | `ce48348e2d74ac0f` | séance de `N120` |
| `json/reunion/RUANR5L17S2025IDS28653.json` | 1 492 | `07f16252c785302f` | séance de l'Assemblée **supprimée** |
| `json/reunion/RUSNR5L17S2026IDS30498.json` | 1 267 | `28d2ff8868b247b7` | séance du **Sénat** (à écarter) |
| `json/reunion/RUANR5L17S2025IDC453385.json` | 5 239 | `b6e7a2baf47d8c08` | réunion de **commission** (à écarter) |

Les dossiers et actes nécessaires au lien sujet → dossier (trois dossiers, trois actes de
discussion en séance, archive `17_Dossiers_Legislatifs.json.zip` du 04/11/2026) sont recopiés
champ par champ dans le test, en petite table : leurs fichiers JSON pèsent plusieurs centaines
de Ko.
