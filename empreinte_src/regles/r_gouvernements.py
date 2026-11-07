"""R-GOUVERNEMENTS : les gouvernements (organes GOUVERNEMENT de l'Assemblée, depuis le
17/05/2007, cahier 3.1.1) et les législatures qu'ils traversent."""

NOM = "R-GOUVERNEMENTS"
VERSION = 2
DEPEND = ("R-LEGISLATURES",)
SORTIES = ("gouvernement", "gouvernement_legislature")
DESCRIPTION = ("Un gouvernement est l'organe « Gouvernement » publié par l'Assemblée, avec ses dates. "
               "Il traverse une législature quand leurs périodes se chevauchent d'au moins un jour. "
               "Quand un Premier ministre forme un second gouvernement, le premier, que l'Assemblée "
               "nomme sans numéro, est appelé « I » (Lecornu I) ; son adresse ne change pas.")


# « LECORNU II » -> « Lecornu II » (les chiffres romains restent en capitales).
NOM_COURT = """array_to_string(list_transform(string_split(libelle_abrege, ' '),
    lambda m: CASE WHEN m IN ('I', 'II', 'III', 'IV', 'V') THEN m
              ELSE upper(m[1]) || lower(m[2:]) END), ' ')"""


def appliquer(ctx):
    # L'Assemblée nomme « LECORNU » le premier gouvernement Lecornu, et « LECORNU II » le second :
    # le premier devient « Lecornu I » à l'affichage. L'adresse reste celle du nom publié
    # (`lecornu`) : une adresse publiée ne change pas (cahier 6.1).
    ctx.ecrire("gouvernement", f"""
        WITH g AS (SELECT uid AS organe, {NOM_COURT} AS nom_source, date_debut AS debut, date_fin AS fin,
                          prov_url AS source_url
                   FROM an_acteurs__organe WHERE type_organe = 'GOUVERNEMENT')
        SELECT g.organe,
               CASE WHEN EXISTS (SELECT 1 FROM g h WHERE h.nom_source = g.nom_source || ' II')
                    THEN g.nom_source || ' I' ELSE g.nom_source END AS nom,
               lower(replace(g.nom_source, ' ', '-')) AS adresse,
               g.debut, g.fin, g.fin IS NULL AS en_cours,
               row_number() OVER (ORDER BY g.debut) AS rang, g.source_url, g.nom_source
        FROM g""")
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
