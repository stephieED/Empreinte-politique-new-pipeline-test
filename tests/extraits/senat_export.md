# Extrait du lecteur `senat_export` (Sénat, `export_sens.zip`)

Origine : `https://data.senat.fr/data/senateurs/export_sens.zip`, téléchargé le 04/11/2026
(`travail/sources/senat/export_sens.zip`, dump du 04/11/2026 04:16). Licence Ouverte (Etalab) 2.0.

`senat_export_extrait.zip` (24 Ko) contient un `export_sens.sql` fait de **lignes du dump
recopiées à l'octet près** : les 16 lignes d'en-tête, puis, pour chaque table gardée, sa ligne
`COPY … FROM stdin;`, les lignes choisies et la fin de bloc `\.`. Script :
`faire_extrait_senat.py` (bloc-notes de la session, non versionné).

- Tables entières (nomenclatures) : `dpt`, `etadebman`, `etafinman`, `typapppol`, `fongrppol`,
  `foncom`, `bur`, `grppol`, `libgrppol`, et `typorg` (hors liste blanche du lecteur : elle doit
  être sautée).
- Quatre sénateurs : Jean-Luc Mélenchon (`86039K`, ancien : trois mandats, sortie pour le
  Gouvernement puis le Parlement européen, groupes SOC puis CRC, appartenance sans date de
  début), Bruno Retailleau (`04033B`), Hélène Conway-Mouret (`11027H`, en exercice) et Gérard
  Larcher (`86034E`, président du Sénat) : leurs lignes de `sen`, `elusen`, `memgrppol`,
  `fonmemgrppol`, `memcom`, `fonmemcom`, `senbur`, et les lignes de `com`/`libcom` des
  commissions où ils ont siégé.
- **Aucune ligne des tables de présence ou de participation** (`activite_participant` et
  semblables) n'est recopiée (règle 3). Le test qui vérifie que ces tables sont sautées ajoute
  un bloc fictif, sans donnée de personne.
