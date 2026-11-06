# Extraits du lecteur `an_scrutins`

Origine : archives des scrutins de l'Assemblée nationale téléchargées le **04/11/2026** dans
`travail/sources/an-scrutins-dossiers/` (adresses : `https://data.assemblee-nationale.fr/static/openData/repository/{14..17}/loi/scrutins/…`,
voir `livrables/annexes/mesures/an-scrutins-dossiers.md`, section 1). Licence Ouverte (Etalab) 2.0.
Chaque membre est recopié **à l'octet près**, sous son chemin d'origine dans l'archive
(seuls la date et la compression des entrées zip changent).

| Fichier | Archive source | Membres | Ce qu'il couvre |
| --- | --- | --- | --- |
| `an_scrutins_l17_extrait.zip` (18 Ko) | `17_Scrutins.json.zip` (produite le 03/11/2026) | `json/VTANR5L17V4569.json`, `V6722`, `V124`, `V493`, `V8611` | schéma XVe-XVIIe (`pours`/`contres`/`abstentions`/`nonVotants`), délégation, non-votants avec cause ; V4569 : mises au point `contres` et sous-bloc `dysfonctionnement` (clés au singulier) ; V6722 : référence de dossier ; V124 : siège `numPlace` nul, mise au point au 2e élément d'une liste `[null, {…}]` ; V493 : 12 lignes de groupe `PO0` ; V8611 : mise au point `nonVotantsVolontaires` |
| `an_scrutins_l16_congres_extrait.zip` (8 Ko) | `16_Scrutins.json.zip` (28/06/2024) | `json/VTCGR5L16V1.json` | scrutin du Congrès : clés `pour`/`contre`/`abstention`/`nonVotant`, type `SSG`, pas de page `/dyn/16/scrutins/…` |
| `an_scrutins_l15_extrait.zip` (1 Ko) | `15_Scrutins_XV.json.zip` (09/06/2022) | `json/VTANR5L15V1822.json` | schéma XVe, délégation, causes `PAN` et `PSE` |
| `an_scrutins_l14_fragment.zip` (6 Ko) | `14_Scrutins_XIV.json.zip` (09/03/2018) | `Scrutins_XIV.json` **tronqué** | voir ci-dessous |

**Fragment XIVe.** L'archive XIVe est un seul fichier de 10,3 Mo (1 354 scrutins), trop gros
pour un extrait. Le fragment est fait des **40 845 premiers octets** du fichier (l'ouverture
`{"scrutins": {"scrutin": [` et les deux premiers scrutins, `VTANR5L14V1` et `VTANR5L14V2`,
exacts), suivis des **3 derniers octets** du fichier (`]}}`, la fermeture). C'est donc un
JSON valide dont chaque octet vient du fichier, mais ce n'est pas le membre entier.
Il couvre : le schéma XIVe (`pour`/`contre`/`abstentions`/`nonVotants` ; `decompteVoix` au
singulier, `abstention`/`nonVotant`), `nonVotants` écrit `"0"` (chaîne), l'absence de
`parDelegation`, `miseAuPoint` à `null` (V1) ou rempli (V2), le type `SAT` (V1) et le mode
`DecompteDissidentsPositionGroupe` (V2 : 110 voix décomptées, 2 dissidents nommés).

Fabriqués par un script de la session (copie des membres, découpe des octets par appariement
des accolades) ; empreintes SHA-256 (16 premiers caractères) des membres XVe-XVIIe :
V4569 `5a589dfb7323fa0f`, V6722 `9f1be941f3bae6b3`, V124 `f980c6c3ab495b2b`,
V493 `0761f427be4206c6`, V8611 `c20203f046e02816`, VTCGR5L16V1 `9b31b6a040544d1d`,
VTANR5L15V1822 `b12e2101a80f9fd4`.
