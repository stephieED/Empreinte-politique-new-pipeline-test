"""R-LEGISLATURES : les législatures, bornées par les dates de l'organe Assemblée (cahier 3.1.1).

Aucun champ de la source ne dit pourquoi une législature a pris fin : le mode de fin vient
d'une décision `fin_legislature` (doc. 1, 1.3.3) ; sans elle, il est « non établi », ou « en
cours » si la législature n'est pas close.

Version 2 (issue #81) : le **terme légal**, date à laquelle les pouvoirs de l'Assemblée
expirent hors dissolution. La source ne le publie pas ; il découle de la loi : article L.O. 121
du code électoral (loi organique n° 2001-419 du 15 mai 2001), « les pouvoirs de l'Assemblée
nationale expirent le troisième mardi de juin de la cinquième année qui suit son élection ».
L'année de l'élection est celle du début de la législature. La loi s'applique depuis
l'Assemblée élue en juin 1997 (XIe) ; avant, le terme n'est pas calculé (`terme_legal` vide,
`raison_terme_legal`). Exemples : XIVe (2012) → 20/06/2017, sa date de fin ; XVIe (2022) →
15/06/2027, dissoute le 09/06/2024."""

NOM = "R-LEGISLATURES"
VERSION = 2
# L.O. 121 du code électoral, version issue de la loi organique n° 2001-419 du 15 mai 2001.
SOURCE_TERME = "https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000006353288"
PREMIERE_ELECTION_TERME = 1997
DEPEND = ()
SORTIES = ("legislature",)
DESCRIPTION = ("Une législature commence et finit aux dates de l'organe « Assemblée nationale » "
               "publiées par l'Assemblée. Son mode de fin (terme ou dissolution) n'est pas publié "
               "par cette source : il vient d'une décision sourcée (décret de dissolution). Son "
               "terme légal, que la source ne publie pas non plus, découle du code électoral (article "
               "L.O. 121) : les pouvoirs de l'Assemblée expirent le troisième mardi de juin de la "
               "cinquième année qui suit son élection.")


def appliquer(ctx):
    """Applique R-LEGISLATURES : écrit `legislature`, les législatures bornées par les dates de
    l'organe Assemblée, avec le mode de fin donné par les décisions `fin_legislature` s'il y en a
    (voir la description du module). Rend la couverture, `{nom: (numérateur, dénominateur)}` :
    `mode_de_fin_etabli`, `terme_legal_etabli`."""
    fin = ("(SELECT any_value(mode) FROM decision_fin_legislature d WHERE d.legislature = CAST(o.legislature AS INTEGER))"
           if ctx.existe("decision_fin_legislature") else "NULL")
    ctx.ecrire("legislature", f"""
        SELECT CAST(o.legislature AS INTEGER) AS numero, o.uid AS organe, o.date_debut AS debut,
               o.date_fin AS fin, o.date_fin IS NULL AS en_cours,
               CASE WHEN o.date_fin IS NULL THEN 'en_cours'
                    ELSE coalesce({fin}, 'non_etabli') END AS mode_fin,
               o.prov_url AS source_url,
               CASE WHEN year(CAST(o.date_debut AS DATE)) >= {PREMIERE_ELECTION_TERME} THEN
                    CAST(make_date(year(CAST(o.date_debut AS DATE)) + 5, 6, 1)
                         + INTERVAL ((2 - dayofweek(make_date(year(CAST(o.date_debut AS DATE)) + 5, 6, 1)) + 7) % 7 + 14) DAY
                         AS DATE)::VARCHAR END AS terme_legal,
               CASE WHEN o.date_debut IS NULL THEN 'debut_inconnu'
                    WHEN year(CAST(o.date_debut AS DATE)) < {PREMIERE_ELECTION_TERME} THEN 'avant_la_loi_de_2001'
               END AS raison_terme_legal,
               '{SOURCE_TERME}' AS source_terme_legal
        FROM an_acteurs__organe o
        WHERE o.type_organe = 'ASSEMBLEE' AND o.legislature IS NOT NULL
        ORDER BY numero""")
    n = ctx.un("SELECT count(*) FROM legislature")
    etabli = ctx.un("SELECT count(*) FROM legislature WHERE mode_fin <> 'non_etabli'")
    terme = ctx.un("SELECT count(*) FROM legislature WHERE terme_legal IS NOT NULL")
    return {"mode_de_fin_etabli": (etabli, n), "terme_legal_etabli": (terme, n)}
