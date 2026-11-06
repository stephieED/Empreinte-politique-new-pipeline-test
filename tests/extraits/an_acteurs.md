# Extraits du lecteur `an_acteurs` (AMO30)

Membres recopiés **à l'octet près** (mêmes noms de membres, mêmes octets ; seul le conteneur
zip est refait) depuis les archives de `travail/sources/an-amo/`. Licence Ouverte (Etalab) 2.0.

| Fichier | Archive d'origine | Version de l'archive |
| --- | --- | --- |
| `amo30_l17_extrait.zip` (11 membres) | `AMO30_17.json.zip` = `…/repository/17/amo/tous_acteurs_mandats_organes_xi_legislature/AMO30_tous_acteurs_tous_mandats_tous_organes_historique.json.zip` | Last-Modified 03/11/2026 01:34 GMT, téléchargée le 04/11/2026 |
| `amo30_l15_extrait.zip` (3 membres) | `AMO30_15.json.zip` = `…/repository/15/amo/tous_acteurs_mandats_organes_xi_legislature/AMO30_tous_acteurs_tous_mandats_tous_organes_historique.json.zip` (archive figée XVe) | Last-Modified 09/06/2022 00:33 GMT, téléchargée le 04/11/2026 |

Ce que couvre chaque membre :

| Membre | Pièges couverts |
| --- | --- |
| `json/acteur/PA721872.json` (XVIIe et XVe) | uid objet (`#text`) ; mandat suspendu par nomination au gouvernement (`PM723408`) puis repris (`PM774343` : `dateDebut` du mandat d'origine, `datePriseFonction` 2020-08-04, `mandatRemplaceRef`) ; suppléant ; mission auprès de **deux** ministères (`PM775823`, `organeRef` en liste) ; mandats GOUVERNEMENT / MINISTERE sans législature ; `trigramme`, `uri_hatvp`, `dateDeces`, `depNais` en `{"@xsi:nil":"true"}` |
| `json/acteur/PA497.json` | `mandats.mandat` objet seul (un seul mandat) ; date de décès renseignée |
| `json/acteur/PA873626.json` | naissance, profession, catégorie socio-professionnelle toutes `xsi:nil` |
| `json/acteur/PA840849.json` | député en cours, siège `placeHemicycle` ; **porte des collaborateurs** (`mandat.collaborateurs`) et des adresses : le test vérifie qu'aucun n'est lu |
| `json/organe/PO800538.json` | groupe XVIe, position déclarée `Majoritaire` |
| `json/organe/PO845407.json` | groupe XVIIe, position `null`, sans date de fin |
| `json/organe/PO834722.json` | ministère avec `organePrecedentRef` et `organeParent` (gouvernement), sans législature |
| `json/organe/PO851643.json` | `listePays.paysRef` en liste |
| `json/organe/PO53285.json` | circonscription (`lieu.departement`, `lieu.region`) |
| `json/organe/PO762272.json` | mission d'information rattachée à une commission (`organeParent`) |
| `json/deport/DPTR5L16PA719472D0001.json` | déport, `explication` null, `cible.references` null |
| `json/organe/PO732421.json` (XVe) | libellé d'époque, réécrit depuis dans l'archive courante |
| `json/organe/PO730946.json` (XVe) | groupe XVe, position `Opposition` |

Taille : 11,1 Ko (deux zips).
