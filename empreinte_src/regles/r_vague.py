"""R-VAGUE : les vagues de nominations d'un gouvernement (cahier 4.4).

Une nomination est le début d'un portefeuille (`membre_gouvernement.debut`), y compris un
changement de portefeuille dans le même gouvernement. Deux nominations séparées de **moins de
8 jours** appartiennent à la même vague ; la vague suivante commence après un écart de 8 jours
ou plus. La règle compte, elle ne qualifie pas : elle ne dit pas quelle vague est « la
formation » (gouvernement Bayrou : le Premier ministre seul le 14/12/2024, les ministres dix
jours plus tard, soit deux vagues), ni « remaniement d'ampleur »."""

NOM = "R-VAGUE"
VERSION = 1
DEPEND = ("R-COMPOSITION",)
SORTIES = ("vague",)
DESCRIPTION = ("Une vague de nominations regroupe les nominations d'un même gouvernement séparées "
               "de moins de 8 jours. Une nomination est l'entrée dans un portefeuille, "
               "y compris un changement de portefeuille en cours de gouvernement.")

ECART_JOURS = 8


def appliquer(ctx):
    ctx.ecrire("vague", f"""
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
        FROM v GROUP BY gouvernement, vague ORDER BY gouvernement, vague""")
    sans_date = ctx.un("SELECT count(*) FROM membre_gouvernement WHERE debut IS NULL")
    n = ctx.un("SELECT count(*) FROM membre_gouvernement")
    return {"nomination_datee": (n - sans_date, n)}
