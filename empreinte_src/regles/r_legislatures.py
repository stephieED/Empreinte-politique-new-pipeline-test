"""R-LEGISLATURES : les législatures, bornées par les dates de l'organe Assemblée (cahier 3.1.1).

Aucun champ de la source ne dit pourquoi une législature a pris fin : le mode de fin vient
d'une décision `fin_legislature` (doc. 1, 1.3.3) ; sans elle, il est « non établi », ou « en
cours » si la législature n'est pas close."""

NOM = "R-LEGISLATURES"
VERSION = 1
DEPEND = ()
SORTIES = ("legislature",)
DESCRIPTION = ("Une législature commence et finit aux dates de l'organe « Assemblée nationale » "
               "publiées par l'Assemblée. Son mode de fin (terme ou dissolution) n'est pas publié "
               "par cette source : il vient d'une décision sourcée (décret de dissolution).")


def appliquer(ctx):
    fin = ("(SELECT any_value(mode) FROM decision_fin_legislature d WHERE d.legislature = CAST(o.legislature AS INTEGER))"
           if ctx.existe("decision_fin_legislature") else "NULL")
    ctx.ecrire("legislature", f"""
        SELECT CAST(o.legislature AS INTEGER) AS numero, o.uid AS organe, o.date_debut AS debut,
               o.date_fin AS fin, o.date_fin IS NULL AS en_cours,
               CASE WHEN o.date_fin IS NULL THEN 'en_cours'
                    ELSE coalesce({fin}, 'non_etabli') END AS mode_fin,
               o.prov_url AS source_url
        FROM an_acteurs__organe o
        WHERE o.type_organe = 'ASSEMBLEE' AND o.legislature IS NOT NULL
        ORDER BY numero""")
    n = ctx.un("SELECT count(*) FROM legislature")
    etabli = ctx.un("SELECT count(*) FROM legislature WHERE mode_fin <> 'non_etabli'")
    return {"mode_de_fin_etabli": (etabli, n)}
