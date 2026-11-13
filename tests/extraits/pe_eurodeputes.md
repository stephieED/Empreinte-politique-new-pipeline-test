# Extrait du point `pe-eurodeputes` (Parlement européen)

Dossier `pe_eurodeputes/` : réponses recopiées **à l'octet près**, reçues le 13/11/2026.
Portail du Parlement européen (`https://data.europarl.europa.eu/api/v2/`, CC BY 4.0), une requête
toutes les 2,1 s ; Wikidata (CC0). Lu par `tests/test_europe_mandats.py`.

| Fichier | Requête | Ce qu'il couvre |
| --- | --- | --- |
| `wikidata-p1186.json` | SPARQL `VALUES ?item { … } ?item wdt:P1186 ?pe` sur les 33 éléments de `decisions/candidature/2026-11-13-franceinfo.yaml` | 6 identifiants européens (Le Pen, Mélenchon, Glucksmann, Philippot, Maurel, Massard) |
| `meps-28210.json` | `meps/28210?format=application/ld+json` | Marine Le Pen : trois législatures (ep-6 à ep-8), cinq groupes, une coprésidence ; doublons « EU_INSTITUTION » des mandats |
| `meps-197694.json` | `meps/197694?format=application/ld+json` | Raphaël Glucksmann : mandat en cours (ep-9, ep-10) |
| `org-1541.json`, `org-2345.json`, `org-2978.json`, `org-3968.json`, `org-4908.json` | `corporate-bodies/<id>?format=application/ld+json&language=fr` | les groupes de Le Pen : NI (trois organes successifs), ITS, ENF |
| `decisions-MTG-PL-2019-09-19.json` | `meetings/MTG-PL-2019-09-19/decisions?format=application/ld+json` | 16 votes nominatifs de la séance du 19/09/2019 (Am, §, Résolution) ; Glucksmann (`person/197694`) figure dans les 16. Lu par `tests/test_europe_votes.py` |
