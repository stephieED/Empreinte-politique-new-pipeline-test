"""R-VAGUE : les vagues de nominations d'un gouvernement, et ce que chacune est (cahier 4.4 ;
décision de la propriétaire du 07/11/2026, doc. 5).

Une nomination est le début d'un portefeuille (`membre_gouvernement.debut`), y compris un
changement de portefeuille dans le même gouvernement. Deux nominations séparées de **moins de
8 jours** appartiennent à la même vague ; la vague suivante commence après un écart de 8 jours
ou plus.

**Nature** de chaque vague (décision du 07/11/2026, règle « départ ou changement ») :
- `formation` : la première vague ; et la deuxième quand la première ne nomme que le Premier
  ministre (Bayrou : le Premier ministre seul le 14/12/2024, ses ministres le 24/12) ;
- `remaniement` : une vague suivante où au moins un membre part (fin d'un portefeuille entre la
  veille du début de la vague et sa fin, hors fin du gouvernement) ou change de portefeuille ;
- `complement` : une vague suivante qui ne fait qu'ajouter des membres (Castex, 27/07/2020).

Les nombres d'arrivées, de départs et de changements de chaque vague sont servis ; la fiche
compte les remaniements. Mesuré sur l'archive du 06/11/2026 : Borne 4, Castex 2, Attal 1
(février 2024 : 1 départ, 1 changement), Lecornu II 1, Barnier, Bayrou et Lecornu I 0."""

NOM = "R-VAGUE"
VERSION = 2
DEPEND = ("R-COMPOSITION", "R-GOUVERNEMENTS")
SORTIES = ("vague",)
DESCRIPTION = ("Une vague de nominations regroupe les nominations d'un même gouvernement séparées "
               "de moins de 8 jours. Une nomination est l'entrée dans un portefeuille, "
               "y compris un changement de portefeuille en cours de gouvernement. La formation "
               "du gouvernement est sa première vague, et aussi la deuxième quand la première ne "
               "nomme que le Premier ministre. Ensuite, une vague où au moins un membre quitte le "
               "gouvernement ou change de portefeuille est un remaniement ; une vague qui ne fait "
               "qu'ajouter des membres est un complément.")

ECART_JOURS = 8


def appliquer(ctx):
    """Applique R-VAGUE : écrit `vague`, les vagues de nominations de chaque gouvernement et ce que
    chacune est (voir la description du module). Rend la couverture,
    `{nom: (numérateur, dénominateur)}` : `nomination_datee`."""
    ctx.x(f"""CREATE OR REPLACE TEMP TABLE _vg AS
        WITH d AS (SELECT gouvernement, debut, count(*) AS n, list(DISTINCT acteur) AS acteurs
                   FROM membre_gouvernement WHERE debut IS NOT NULL GROUP BY 1, 2),
        s AS (SELECT *, CASE WHEN date_diff('day',
                                 lag(debut::DATE) OVER (PARTITION BY gouvernement ORDER BY debut),
                                 debut::DATE) < {ECART_JOURS} THEN 0 ELSE 1 END AS nouvelle
              FROM d),
        v AS (SELECT *, sum(nouvelle) OVER (PARTITION BY gouvernement ORDER BY debut
                                            ROWS UNBOUNDED PRECEDING) AS vague FROM s)
        SELECT gouvernement, CAST(vague AS INTEGER) AS vague, min(debut) AS debut, max(debut) AS fin,
               CAST(sum(n) AS INTEGER) AS nb_nominations,
               CAST(len(list_distinct(flatten(list(acteurs)))) AS INTEGER) AS nb_personnes,
               CAST(count(*) AS INTEGER) AS nb_jours_de_nomination
        FROM v GROUP BY gouvernement, vague""")
    ctx.ecrire("vague", """
        WITH x AS (
            SELECT v.*,
                   (SELECT count(DISTINCT m.acteur) FROM membre_gouvernement m
                     WHERE m.gouvernement = v.gouvernement AND m.debut BETWEEN v.debut AND v.fin
                       AND NOT coalesce(m.premier_ministre, false)) AS nb_hors_premier_ministre,
                   (SELECT count(DISTINCT m.acteur) FROM membre_gouvernement m JOIN gouvernement g
                       ON g.organe = m.gouvernement
                     WHERE m.gouvernement = v.gouvernement AND m.fin IS NOT NULL
                       AND m.fin::DATE BETWEEN v.debut::DATE - 1 AND v.fin::DATE
                       AND (g.fin IS NULL OR m.fin < g.fin)) AS nb_departs,
                   (SELECT count(DISTINCT m.acteur) FROM membre_gouvernement m
                     WHERE m.gouvernement = v.gouvernement AND m.debut BETWEEN v.debut AND v.fin
                       AND EXISTS (SELECT 1 FROM membre_gouvernement p WHERE p.gouvernement = m.gouvernement
                                   AND p.acteur = m.acteur AND p.debut < v.debut)) AS nb_changements,
                   (SELECT count(DISTINCT m.acteur) FROM membre_gouvernement m
                     WHERE m.gouvernement = v.gouvernement AND m.debut BETWEEN v.debut AND v.fin
                       AND NOT EXISTS (SELECT 1 FROM membre_gouvernement p WHERE p.gouvernement = m.gouvernement
                                       AND p.acteur = m.acteur AND p.debut < v.debut)) AS nb_arrivees
            FROM _vg v),
        p AS (SELECT gouvernement, bool_or(vague = 1 AND nb_hors_premier_ministre = 0) AS pm_seul
              FROM x GROUP BY 1)
        SELECT x.gouvernement, x.vague, x.debut, x.fin, x.nb_nominations, x.nb_personnes,
               x.nb_jours_de_nomination, CAST(x.nb_arrivees AS INTEGER) AS nb_arrivees,
               CAST(x.nb_departs AS INTEGER) AS nb_departs, CAST(x.nb_changements AS INTEGER) AS nb_changements,
               CASE WHEN x.vague = 1 OR (x.vague = 2 AND p.pm_seul) THEN 'formation'
                    WHEN x.nb_departs > 0 OR x.nb_changements > 0 THEN 'remaniement'
                    ELSE 'complement' END AS nature
        FROM x JOIN p USING (gouvernement)
        ORDER BY x.gouvernement, x.vague""")
    ctx.x("DROP TABLE IF EXISTS _vg")
    sans_date = ctx.un("SELECT count(*) FROM membre_gouvernement WHERE debut IS NULL")
    n = ctx.un("SELECT count(*) FROM membre_gouvernement")
    return {"nomination_datee": (n - sans_date, n)}
