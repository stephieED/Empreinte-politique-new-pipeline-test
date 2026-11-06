# Extrait des règles du groupe E1 (candidats : carrière et fonctions)

`amo30_l17_candidats_e1.zip` (61 membres, 36 Ko) : membres recopiés **à l'octet près** (mêmes
noms, mêmes octets ; seul le conteneur zip est refait) depuis `travail/sources/an-amo/AMO30_17.json.zip`
= `…/repository/17/amo/tous_acteurs_mandats_organes_xi_legislature/AMO30_tous_acteurs_tous_mandats_tous_organes_historique.json.zip`,
Last-Modified 03/11/2026 01:34 GMT, téléchargée le 04/11/2026. Licence Ouverte (Etalab) 2.0.
Lu par `tests/test_regles_e1.py`, avec `wp_candidatures_section1.json`,
`wd_identifiants_extrait.json` et `senat_export_extrait.zip`.

Choix des membres (script `faire_extrait_amo.py`, bloc-notes de la session, non versionné) :
les deux acteurs ci-dessous, chaque organe cité par l'un de leurs mandats (`organeRef`), et le
parent (`organeParent`) de chacun de ces organes.

| Membre | Ce qu'il couvre |
| --- | --- |
| `json/acteur/PA722142.json` | François Ruffin : trois mandats de député (XVe, XVIe, XVIIe), groupes FI, LFI-NUPES, ECOS et passages chez les non-inscrits ; 141 mandats (142 dans l'archive du 06/11/2026) dont les **permutations de commission** (trous de 1 à 3 jours, et de 8 à 14 jours) ; secrétaire de la commission des affaires économiques, co-rapporteur d'une mission, vice-président de deux groupes d'amitié ; organisme extraparlementaire encore ouvert ; adhésion à un parti (PARPOL, écartée) |
| `json/acteur/PA2538.json` | Bruno Retailleau : sénateur (les organes du Sénat recopiés par l'Assemblée), ministre de l'intérieur des gouvernements Barnier, Bayrou et Lecornu ; places en commission mixte paritaire inscrites par l'Assemblée au titre du Sénat |
| `json/organe/PO*.json` (59) | Assemblées XVe à XVIIe, groupes et non-inscrits, commissions, missions, groupes d'études et d'amitié, organismes extraparlementaires, CMP, ministères et gouvernements cités |
