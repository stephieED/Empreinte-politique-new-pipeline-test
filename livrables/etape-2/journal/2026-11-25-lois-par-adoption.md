## Lois d'une législature comptées aussi par leur adoption (issue #83, PR #182) (25/11/2026)

Nouvelle règle R-LOI-ADOPTION (`loi_adoption`). Une loi est aussi rangée dans la législature où
l'Assemblée l'a adoptée en dernier :
- dernière décision d'adoption de l'Assemblée avant la promulgation, quand elle clôt la navette ;
- ou quand le vote final du Sénat (CMP, Congrès) tombe dans la même législature ;
- ou, pour une loi reliée par le JO dont l'archive s'arrête avant la promulgation, quand la fin de
  l'archive et la promulgation tombent dans la même législature.

La clôture est la dernière décision d'adoption, et non la seule liste de R-ETAPE : la source code
« modifié » (TSORTF05) l'adoption conforme du Sénat qui clôt la navette (98 lois sur la g24).
Sinon, la loi n'a pas de législature d'adoption et la raison est servie : `loi_sans_dossier`,
`suite_absente_des_archives`, `seance_de_l_assemblee_apres_son_dernier_vote_lu`,
`cloture_hors_assemblee_sous_une_autre_legislature`. Pour cette dernière (21 lois), l'option
prudente est appliquée en attendant Q65 : la loi n'est comptée nulle part.

Fiche de législature : compte `lois_par_adoption` à côté de `lois`, qui ne change pas. Il est
`partiel` quand des lois qui ont pu être adoptées pendant la législature n'ont pas de législature
établie. Colonnes `legislature_adoption_loi`, `preuve_adoption_loi` et `raison_adoption_loi` des
textes.

Mesuré sur la g24 :

| Législature | Par promulgation | Par adoption |
| --- | ---: | ---: |
| XIVe | 396 | 396 |
| XVe | 335 | 340 |
| XVIe | 136 | 131 |
| XVIIe | 151 | 140 |

5 lois changent de législature : 2024-536, 537, 538, 582 et 850 passent à la XVIe. 10 lois du JO
absentes des actes de l'Assemblée entrent dans la XVe. 85 lois sur 1 092 n'ont pas de législature
d'adoption établie. Aucun fait servi ne disparaît (C1).
