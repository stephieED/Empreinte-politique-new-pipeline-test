# Extraits du lecteur `an_questions`

Membres recopiés **à l'octet près** (mêmes noms de membres, mêmes octets ; seul le conteneur
zip est refait) depuis les archives de `travail/sources/an-questions/`, téléchargées le
04/11/2026. Licence Ouverte (Etalab) 2.0.

| Fichier | Archive d'origine | Last-Modified |
| --- | --- | --- |
| `questions_ecrites_l17_extrait.zip` | `Questions_ecrites_17.json.zip` = `…/repository/17/questions/questions_ecrites/Questions_ecrites.json.zip` | 03/11/2026 02:11 GMT |
| `questions_gouvernement_l17_extrait.zip` | `Questions_gouvernement_17.json.zip` = `…/17/questions/questions_gouvernement/Questions_gouvernement.json.zip` | 03/11/2026 01:50 GMT |
| `questions_orales_l17_extrait.zip` | `Questions_orales_sans_debat_17.json.zip` = `…/17/questions/questions_orales_sans_debat/Questions_orales_sans_debat.json.zip` | 03/11/2026 01:20 GMT |

| Membre | Pièges couverts |
| --- | --- |
| `json/QANR5L17QE17917.json` | réponse publiée deux fois (`texteReponse` en liste, la seconde avec `erratum`) |
| `json/QANR5L17QE16918.json` | erratum de question (`texteQuestion` en liste, `texte` null) ; pas de réponse, `cloture` null |
| `json/QANR5L17QE2225.json` | quatre ministères attributaires (`minAttrib` en liste) ; renouvellements en liste ; signalement ; sans réponse |
| `json/QANR5L17QG390.json` | question au gouvernement : `textesQuestion` null, question et réponse dans un seul bloc HTML, `JO_DEBAT` |
| `json/QANR5L17QOSD110.json` | question orale, deux attributaires (liste), réponse |
| `json/QANR5L17QOSD680.json` | question orale sans réponse |

La tolérance aux clés en capitales (XVe) est vérifiée en mettant en capitales les clés de ces
extraits réels : aucune archive de questions XVe n'est disponible localement.

Taille : 13,6 Ko (trois zips).
