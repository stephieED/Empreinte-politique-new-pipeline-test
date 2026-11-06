"""R-GOUVERNEMENTS : les gouvernements (organes GOUVERNEMENT de l'Assemblée, depuis le
17/05/2007, cahier 3.1.1) et les législatures qu'ils traversent."""

NOM = "R-GOUVERNEMENTS"
VERSION = 1
DEPEND = ("R-LEGISLATURES",)
SORTIES = ("gouvernement", "gouvernement_legislature")
DESCRIPTION = ("Un gouvernement est l'organe « Gouvernement » publié par l'Assemblée, avec ses dates. "
               "Il traverse une législature quand leurs périodes se chevauchent d'au moins un jour.")


# « LECORNU II » -> « Lecornu II » (les chiffres romains restent en capitales).
NOM_COURT = """array_to_string(list_transform(string_split(libelle_abrege, ' '),
    lambda m: CASE WHEN m IN ('I', 'II', 'III', 'IV', 'V') THEN m
              ELSE upper(m[1]) || lower(m[2:]) END), ' ')"""


def appliquer(ctx):
    ctx.ecrire("gouvernement", f"""
        SELECT uid AS organe, {NOM_COURT} AS nom,
               lower(replace({NOM_COURT}, ' ', '-')) AS adresse,
               date_debut AS debut, date_fin AS fin, date_fin IS NULL AS en_cours,
               row_number() OVER (ORDER BY date_debut) AS rang, prov_url AS source_url
        FROM an_acteurs__organe WHERE type_organe = 'GOUVERNEMENT'""")
    ctx.ecrire("gouvernement_legislature", """
        SELECT g.organe AS gouvernement, l.numero AS legislature,
               greatest(g.debut, l.debut) AS debut,
               CASE WHEN g.fin IS NULL THEN l.fin WHEN l.fin IS NULL THEN g.fin
                    ELSE least(g.fin, l.fin) END AS fin
        FROM gouvernement g JOIN legislature l
          ON g.debut <= coalesce(l.fin, '9999-12-31') AND coalesce(g.fin, '9999-12-31') >= l.debut""")
    sans_nom = ctx.un("SELECT count(*) FROM gouvernement WHERE nom IS NULL")
    n = ctx.un("SELECT count(*) FROM gouvernement")
    return {"nom_etabli": (n - sans_nom, n)}
