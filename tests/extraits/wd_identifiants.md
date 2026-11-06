# Extrait Wikidata (lecteur `wd_identifiants`)

| Fichier | Origine | Relevé le | Licence |
| --- | --- | --- | --- |
| `wd_identifiants_extrait.json` | réponse de `https://query.wikidata.org/sparql` à la requête du point d'accès `wd-identifiants-parlementaires` (config/points_acces.yaml), réduite aux lignes de trois personnes (articles François Ruffin, Jean-Luc Mélenchon, Bruno Retailleau) et à trois personnes sans identifiant de l'Assemblée ; lignes recopiées telles quelles | 06/11/2026 | CC0 |

Couvre : identifiant de l'Assemblée publié sans `PA`, identifiant du Sénat publié comme chemin
d'adresse, personne présente à la fois à l'Assemblée et au Sénat, personne sans article.
