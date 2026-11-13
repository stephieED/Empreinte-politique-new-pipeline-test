"""R-QUALITE : à quel titre parle l'orateur d'un paragraphe attribué (doc. 1, 1.6 ; doc. 5, Q21).

Deux origines, toujours distinguées (`qualite_source`) pour qu'on puisse n'utiliser que la
qualité écrite si la question Q21 est tranchée en ce sens :

- `compte_rendu` : la qualité **écrite** par le compte rendu (texte libre, classé en
  `membre_du_gouvernement`, `rapporteur`, `president_de_commission`, `autre`), ou la
  présidence de séance reconnue par R-ORATEUR (`president_de_seance`) ;
- `deduite` : quand le compte rendu se tait, la fonction **à la date** de la séance : membre
  d'un gouvernement (`membre_gouvernement`, R-COMPOSITION), sinon rapporteur du dossier du
  sujet (acte du dossier, R-SUJET), sinon député (mandat à l'Assemblée couvrant la date).

Une personne à la fois membre d'un gouvernement et titulaire d'un mandat de député à la date
(ministres démissionnaires élus députés en juillet 2024, premier mois d'un député nommé
ministre) ne reçoit pas de qualité déduite : `raison_non_etablie =
'gouvernement_et_assemblee_a_la_date'` (le 19/07/2024, Marc Fesneau parle comme président de
groupe alors qu'il est encore ministre). Sinon : `qualite = NULL`, `raison_non_etablie =
'qualite_non_etablie'`. La colonne
`qualite_ecrite` garde à part la classe de la qualité écrite (NULL si rien n'est écrit).
"""


NOM = "R-QUALITE"
VERSION = 1
DEPEND = ("R-ORATEUR", "R-SUJET", "R-COMPOSITION")
SORTIES = ("qualite_orateur",)
DESCRIPTION = (
    "La qualité d'un orateur (membre du gouvernement, rapporteur, président de commission, "
    "président de séance, député) est celle que le compte rendu écrit. Quand le compte rendu ne "
    "l'écrit pas (c'est le cas de la plupart des paragraphes), elle est déduite de ses fonctions "
    "à la date de la séance : membre du gouvernement, sinon rapporteur du texte discuté, sinon "
    "député ; quand la personne est à la fois membre du gouvernement et députée à cette date, "
    "rien n'est déduit. L'origine de chaque qualité, écrite ou déduite, est gardée et comptée.")


def appliquer(ctx):
    """Applique R-QUALITE : écrit `qualite_orateur`, le titre auquel parle l'orateur de chaque
    paragraphe attribué (voir la description du module). Rend la couverture,
    `{nom: (numérateur, dénominateur)}` : `qualite_etablie`,
    `qualite_ecrite_par_le_compte_rendu_hors_presidence`."""
    ctx.ecrire("qualite_orateur", f"""
        WITH a AS (
            SELECT a.compte_rendu, a.id_syceron, a.acteur, a.date, a.preside, a.interruption,
                   a.qualite_ecrite_libelle, a.qualite_ecrite, s.dossier
            FROM intervention_attribuee a
            LEFT JOIN sujet_intervention s USING (compte_rendu, id_syceron)
            WHERE a.acteur IS NOT NULL),
        gouv AS (
            SELECT a.compte_rendu, a.id_syceron, m.gouvernement
            FROM a JOIN membre_gouvernement m
              ON m.acteur = a.acteur AND a.date >= m.debut AND a.date <= coalesce(m.fin, '9999-12-31')
            QUALIFY row_number() OVER (PARTITION BY a.compte_rendu, a.id_syceron ORDER BY m.debut DESC) = 1),
        rapp AS (
            SELECT DISTINCT dossier, unnest(rapporteurs) AS acteur FROM an_dossiers__acte
            WHERE len(rapporteurs) > 0),
        dep AS (
            SELECT DISTINCT acteur, date_debut, coalesce(date_fin, '9999-12-31') AS date_fin
            FROM an_acteurs__mandat WHERE type_organe = 'ASSEMBLEE'),
        q AS (
            SELECT a.*, g.gouvernement,
                   EXISTS (SELECT 1 FROM rapp r WHERE r.dossier = a.dossier AND r.acteur = a.acteur) AS rapporteur,
                   EXISTS (SELECT 1 FROM dep d WHERE d.acteur = a.acteur AND a.date >= d.date_debut
                                                AND a.date <= d.date_fin) AS depute
            FROM a LEFT JOIN gouv g USING (compte_rendu, id_syceron)),
        d AS (
            SELECT q.*,
                   CASE WHEN preside THEN 'president_de_seance'
                        WHEN qualite_ecrite IS NOT NULL THEN qualite_ecrite END AS ecrite,
                   CASE WHEN gouvernement IS NOT NULL AND depute THEN NULL
                        WHEN gouvernement IS NOT NULL THEN 'membre_du_gouvernement'
                        WHEN rapporteur THEN 'rapporteur'
                        WHEN depute THEN 'depute' END AS deduite
            FROM q)
        SELECT compte_rendu, id_syceron, acteur, date,
               coalesce(ecrite, deduite) AS qualite,
               CASE WHEN ecrite IS NOT NULL THEN 'compte_rendu'
                    WHEN deduite IS NOT NULL THEN 'deduite' END AS qualite_source,
               ecrite AS qualite_ecrite, qualite_ecrite_libelle,
               gouvernement AS gouvernement_a_la_date,
               CASE WHEN ecrite IS NOT NULL OR deduite IS NOT NULL THEN NULL
                    WHEN gouvernement IS NOT NULL AND depute THEN 'gouvernement_et_assemblee_a_la_date'
                    ELSE 'qualite_non_etablie' END AS raison_non_etablie,
               interruption
        FROM d""")
    t = ctx.x("""SELECT count(*), count(*) FILTER (qualite IS NOT NULL),
                        count(*) FILTER (qualite <> 'president_de_seance' OR qualite IS NULL),
                        count(*) FILTER (qualite <> 'president_de_seance' AND qualite_source = 'compte_rendu')
                 FROM qualite_orateur""")[0]
    return {"qualite_etablie": (t[1], t[0]),
            "qualite_ecrite_par_le_compte_rendu_hors_presidence": (t[3], t[2])}
