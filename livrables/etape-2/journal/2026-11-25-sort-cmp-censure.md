## Sort d'un texte : adoption sur le texte de CMP et rejet via 49.3 (issue #89, partie traitement, PR #186) (25/11/2026)

Deux faits du sort d'un texte, lus jusqu'ici sans être servis ou sans être établis, sont servis
dans les textes de la fiche de législature. Le regroupement en neuf sorts affichés n'est pas fait :
il attend l'arbitrage de la propriétaire.

- **Adoption sur le texte de CMP** (R-SORT-FINAL version 6) : `motif_adoption` (lu par R-ETAPE,
  jusqu'ici non servi) et `adopte_sur_texte_cmp`. Ce dernier vaut aussi pour un texte promulgué dont
  la dernière adoption avant la promulgation est prise en CMP, quand R-ETAPE ne reconnaît pas la
  clôture (décision de CMP sans chambre : 6 dossiers sur la g24, dont la loi 2024-1039).
- **Rejet via 49.3** (R-49-3 version 2, nouvelle sortie `censure_49_3`) : une motion de censure
  adoptée après un engagement de responsabilité sur le texte, avec son scrutin. Cas réel unique
  depuis 2012 : le PLFSS 2025 (DLR5L17N50588), gouvernement Barnier, engagement du 02/12/2024 sur le
  texte de CMP, motion adoptée le 04/12/2024 (scrutin VTANR5L17V519). Le sort reste celui du dossier,
  `promulgue` : la navette a repris et la loi 2025-199 a été promulguée le 28/02/2025.
- **Correction** : R-SORT-FINAL lit la dernière décision d'un dossier ligne entière. `max_by` sautait
  une valeur vide : une décision sans chambre ou sans libellé prenait ceux de la décision précédente
  (3 dossiers sur la g24 ; la dernière conclusion, non servie, change, le sort ne change pas).

Colonnes ajoutées aux textes : `motif_adoption`, `adopte_sur_texte_cmp`, `rejete_par_censure_49_3`,
`date_censure_49_3`, `scrutin_censure_49_3`. Mesuré sur la g24 : aucun fait servi ne disparaît (C1),
A9 ne nomme rien.
