"""R-PAROLES-GOUVERNEMENT : les prises de parole d'un gouvernement (cahier 4.4, « Sur quoi ils
ont pris la parole » ; décision du 04/11/2026, doc. 5, Q21).

Une prise de parole est celle d'un gouvernement quand son orateur est **membre de ce
gouvernement à la date** de la séance (`membre_gouvernement`, R-COMPOSITION) **et** qu'il parle
**en qualité de membre du gouvernement** (R-QUALITE). La qualité peut être écrite par le compte
rendu ou déduite de la fonction à la date : `qualite_source` le dit, pour qu'on puisse ne
retenir que la qualité écrite. Le sujet et le dossier viennent de R-SUJET ; les exclamations
(`interruption`) restent marquées.
"""

NOM = "R-PAROLES-GOUVERNEMENT"
VERSION = 1
DEPEND = ("R-QUALITE", "R-SUJET", "R-COMPOSITION")
SORTIES = ("parole_gouvernement",)
DESCRIPTION = (
    "Les prises de parole d'un gouvernement sont celles de ses membres pendant leur fonction, "
    "quand ils parlent en qualité de membre du gouvernement. Cette qualité est celle que le "
    "compte rendu écrit, ou, quand il se tait, celle que donne la fonction à la date de la "
    "séance ; l'origine est gardée et comptée.")


def appliquer(ctx):
    """Applique R-PAROLES-GOUVERNEMENT : écrit `parole_gouvernement`, les prises de parole des
    membres d'un gouvernement (voir la description du module). Rend la couverture,
    `{nom: (numérateur, dénominateur)}` : `qualite_ecrite_par_le_compte_rendu`, `sujet_etabli`,
    `texte_relie_a_son_dossier`, `qualite_gouvernementale_retenue`."""
    ctx.ecrire("parole_gouvernement", """
        SELECT DISTINCT m.gouvernement, q.acteur, q.compte_rendu, q.id_syceron, q.date,
               s.sujet, s.dossier, s.statut AS statut_sujet, s.type_sujet, s.lien_dossier,
               q.qualite_source, q.qualite_ecrite_libelle, q.interruption,
               s.source_url
        FROM qualite_orateur q
        JOIN membre_gouvernement m
          ON m.acteur = q.acteur AND q.date >= m.debut AND q.date <= coalesce(m.fin, '9999-12-31')
        LEFT JOIN sujet_intervention s USING (compte_rendu, id_syceron)
        WHERE q.qualite = 'membre_du_gouvernement'""")
    t = ctx.x("""SELECT count(*), count(*) FILTER (qualite_source = 'compte_rendu'),
                        count(*) FILTER (statut_sujet = 'etabli'),
                        count(*) FILTER (lien_dossier IN ('lie', 'plusieurs_dossiers')),
                        count(*) FILTER (type_sujet IN ('texte', 'loi_de_finances') AND statut_sujet = 'etabli')
                 FROM parole_gouvernement""")[0]
    # Qualité gouvernementale écrite par le compte rendu, mais orateur membre d'aucun
    # gouvernement à la date : ces paroles ne sont pas retenues (comptées pour la méthodologie).
    hors = ctx.un("""SELECT count(*) FROM qualite_orateur q WHERE q.qualite = 'membre_du_gouvernement'
                     AND NOT EXISTS (SELECT 1 FROM membre_gouvernement m WHERE m.acteur = q.acteur
                         AND q.date >= m.debut AND q.date <= coalesce(m.fin, '9999-12-31'))""")
    n_qual = ctx.un("SELECT count(*) FROM qualite_orateur WHERE qualite = 'membre_du_gouvernement'")
    return {"qualite_ecrite_par_le_compte_rendu": (t[1], t[0]),
            "sujet_etabli": (t[2], t[0]),
            "texte_relie_a_son_dossier": (t[3], t[4]),
            "qualite_gouvernementale_retenue": (n_qual - hors, n_qual)}
