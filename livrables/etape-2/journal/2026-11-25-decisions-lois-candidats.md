## Décisions du 25/11/2026 sur les lois et les candidats appliquées (Q61 à Q68, #118, PR #183) (25/11/2026)

La propriétaire a tranché sept questions et l'avertissement A7 de l'issue #118.

**Lois par adoption (R-LOI-ADOPTION, version 2).**
- Q65, option 1 : une loi dont le Sénat a voté en dernier sous une autre législature est comptée
  dans celle du dernier vote de l'Assemblée (preuve
  `dernier_vote_de_l_assemblee_cloture_sous_une_autre_legislature` ; 21 lois).
- Q66, option 2 : pour 2024-1039, 2025-175 et 2025-541, la législature du dernier vote enregistré
  de l'Assemblée, la XVIe (preuve `dernier_vote_enregistre_de_l_assemblee_seance_posterieure`).
- Q67 : la XIIIe est hors du périmètre, aucune issue n'est ouverte. Une loi sans dossier dont la
  dernière adoption à l'Assemblée, lue dans ses travaux préparatoires au JO (« Discussion et
  adoption le 3 octobre 2011 »), précède la XIVe prend la raison
  `dossier_anterieur_a_la_xive_hors_perimetre` (16 lois) et n'est plus comptée comme incertaine.
  Les 43 autres lois sans dossier gardent `loi_sans_dossier` : le JO les date sous la XIVe ou la
  XVe.

**Compte `lois` (Q68, option 1).** Il compte les numéros de loi distincts : la XVe passe de 335 à
334 (2017-1338, deux identifiants de dossier).

**A7 (#118, option 1).** Les 9 écarts de date de promulgation entre le JO et l'acte de
l'Assemblée sont notés comme connus (`references/date_promulgation_connue/`). A7 ne les nomme
plus et les compte (`expliques.a7_dates_de_promulgation_connues`) ; un écart nouveau ou modifié
est nommé, et la décision qui ne correspond plus à aucun écart est dite sans objet. La date du JO
reste celle qui est publiée.

**Candidats (Q61, Q62, Q63, option A).** Rien ne change.

Mesuré sur la g24 (règles rejouées) :

| Législature | Par promulgation | Par adoption | Statut du compte par adoption |
| --- | ---: | ---: | --- |
| XIVe | 396 | 400 | partiel : 36 lois sans dossier datées de la XIVe au JO, 2 suites absentes |
| XVe | 334 | 350 | partiel : 7 lois sans dossier, 2 suites absentes |
| XVIe | 136 | 141 | complet |
| XVIIe | 151 | 140 | complet |

Le compte `lois` de la XVe change de valeur, pas d'identité : ce n'est pas une perte pour C1.
Contre une publication qui sert déjà la version 1 (PR #182), A9 nommerait la liste
`sans_legislature_d_adoption` vidée des comptes de la XVIe et de la XVIIe (2 faits, non
bloquant). A7 rejoué ne nomme plus aucun écart de date (9 comptés).
