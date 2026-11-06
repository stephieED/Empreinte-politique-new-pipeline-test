"""R-APPARTENANCE : les groupes politiques de l'Assemblée et l'appartenance de chaque député,
comme une **suite de périodes** (cahier 4.6 ; doc. 1, 1.5.2 et 1.6).

- `groupe` : un organe GP de l'Assemblée = un groupe (le rattachement de deux organes successifs
  d'un même groupe est l'affaire de R-CONTINUITE-GROUPE). Le « groupe » des non-inscrits (un
  organe GP par législature, sigle `NI`) **n'est pas un groupe** : il n'est pas dans `groupe`, et
  un passage chez les non-inscrits n'est pas une appartenance. La position déclarée
  (majoritaire, minoritaire, opposition) est celle que publie l'organe ; sans elle, « non
  déclarée » (XVIIe : aucun groupe n'en déclare ; doc. 5, Q2). Elle n'est **jamais déduite**.
- `appartenance` : lue dans les seuls mandats GP (jamais dans l'organe que porte un scrutin).
  Les mandats d'une personne dans un même groupe qui se touchent (qualité qui change : membre,
  apparenté, président) forment une seule période ; un départ suivi d'un retour en fait deux.
  Quand un député entre au gouvernement, son mandat GP est clos par la source et un nouveau
  s'ouvre à la reprise : la suspension est donc déjà dans les périodes.
- Avant la XVe, la source fait finir l'ancien mandat GP **le jour même** où commence le suivant
  (1 jour de chevauchement, 69 fois au passage UMP → R-UMP en 2012) ; depuis, il finit la veille.
  Pour qu'une personne ne compte jamais dans deux groupes le même jour, une période finit la
  veille du début du mandat GP suivant de la même personne dans un autre organe (non-inscrits
  compris). La date de fin publiée est gardée (`fin_source`).
"""

NOM = "R-APPARTENANCE"
VERSION = 2
DEPEND = ()
SORTIES = ("groupe", "appartenance")
DESCRIPTION = (
    "Un groupe politique est un organe « groupe » publié par l'Assemblée, avec ses dates. Les "
    "non-inscrits ne forment pas un groupe. La position du groupe (majoritaire, minoritaire, "
    "opposition) est celle que le groupe déclare à l'Assemblée ; quand il n'en déclare pas, nous "
    "écrivons « non déclarée » et ne la déduisons jamais. L'appartenance d'un député à un groupe "
    "est lue dans ses mandats de membre de groupe publiés par l'Assemblée : c'est une suite de "
    "périodes, interrompue quand il quitte le groupe, siège comme non-inscrit ou entre au "
    "gouvernement. Quand la source fait commencer un nouveau groupe le jour où l'ancien finit, "
    "l'ancien finit la veille, pour qu'un député ne compte jamais dans deux groupes le même jour.")

MANDAT = """(SELECT * FROM an_acteurs__mandat
             QUALIFY row_number() OVER (PARTITION BY uid ORDER BY prov_point DESC) = 1)"""
ORGANE = """(SELECT * FROM an_acteurs__organe
             QUALIFY row_number() OVER (PARTITION BY uid ORDER BY prov_point DESC) = 1)"""
EST_NI = "(o.sigle = 'NI' OR lower(o.libelle) IN ('non inscrit', 'non inscrits', 'non-inscrits'))"
FIN_OUVERTE = "'9999-12-31'"


def appliquer(ctx):
    ctx.ecrire("groupe", f"""
        SELECT o.uid AS organe, TRY_CAST(o.legislature AS INTEGER) AS legislature, o.sigle,
               o.libelle, o.date_debut AS debut, o.date_fin AS fin,
               CASE lower(o.position_politique)
                    WHEN 'majoritaire' THEN 'majoritaire' WHEN 'minoritaire' THEN 'minoritaire'
                    WHEN 'opposition' THEN 'opposition' ELSE 'non_declaree' END AS position_declaree,
               o.position_politique AS position_source, o.organe_precedent, o.libelle_abrege,
               o.prov_url AS source_url, o.prov_uid
        FROM {ORGANE} o
        WHERE o.type_organe = 'GP' AND NOT {EST_NI}
        ORDER BY legislature, debut, organe""")

    ctx.x(f"""CREATE OR REPLACE TEMP TABLE _ga_gp AS
        SELECT m.uid, m.acteur, m.organe, TRY_CAST(coalesce(m.legislature, o.legislature) AS INTEGER) AS legislature,
               m.qualite, m.date_debut AS debut, m.date_fin AS fin_source,
               coalesce(o.uid IS NOT NULL AND {EST_NI}, false) AS ni, o.uid IS NULL AS organe_inconnu
        FROM {MANDAT} m LEFT JOIN {ORGANE} o ON o.uid = m.organe
        WHERE m.type_organe = 'GP' AND m.date_debut IS NOT NULL""")
    # Fin effective : la veille du premier mandat GP suivant de la même personne dans un autre organe.
    ctx.x(f"""CREATE OR REPLACE TEMP TABLE _ga_gp2 AS
        WITH suivant AS (
            SELECT a.uid, min(b.debut) AS debut_suivant
            FROM _ga_gp a JOIN _ga_gp b
              ON b.acteur = a.acteur AND b.organe <> a.organe AND b.debut > a.debut
             AND b.debut <= coalesce(a.fin_source, {FIN_OUVERTE})
            GROUP BY 1)
        SELECT a.*,
               least(coalesce(a.fin_source, {FIN_OUVERTE}),
                     coalesce(strftime(s.debut_suivant::DATE - 1, '%Y-%m-%d'), {FIN_OUVERTE})) AS fin_eff
        FROM _ga_gp a LEFT JOIN suivant s USING (uid)""")
    # Périodes : mandats d'un même groupe qui se touchent (écart d'un jour au plus) fusionnés.
    # Le mandat (uid) départage les mandats aux dates identiques (40 dans l'archive) : sans lui,
    # l'ordre des fenêtres change d'une exécution à l'autre et les îlots peuvent se décaler.
    ctx.ecrire("appartenance", f"""
        WITH g AS (SELECT * FROM _ga_gp2 WHERE NOT ni AND NOT organe_inconnu AND fin_eff >= debut),
        o AS (SELECT *, max(fin_eff) OVER (PARTITION BY acteur, organe ORDER BY debut, fin_eff, uid
                     ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING) AS fin_avant FROM g),
        i AS (SELECT *, sum(CASE WHEN fin_avant IS NOT NULL
                                  AND debut::DATE <= fin_avant::DATE + 1 THEN 0 ELSE 1 END)
                        OVER (PARTITION BY acteur, organe ORDER BY debut, fin_eff, uid
                              ROWS UNBOUNDED PRECEDING) AS ilot FROM o)
        SELECT acteur, organe AS groupe, any_value(legislature) AS legislature, min(debut) AS debut,
               nullif(max(fin_eff), {FIN_OUVERTE}) AS fin,
               nullif(max(coalesce(fin_source, {FIN_OUVERTE})), {FIN_OUVERTE}) AS fin_source,
               list_sort(list(DISTINCT qualite)) AS qualites, list_sort(list(uid)) AS mandats
        FROM i GROUP BY acteur, organe, ilot
        ORDER BY acteur, debut""")

    n = ctx.un("SELECT count(*) FROM _ga_gp")
    inconnu = ctx.un("SELECT count(*) FROM _ga_gp WHERE organe_inconnu")
    nb_groupes = ctx.un("SELECT count(*) FROM groupe")
    declare = ctx.un("SELECT count(*) FROM groupe WHERE position_declaree <> 'non_declaree'")
    ctx.x("DROP TABLE IF EXISTS _ga_gp")
    ctx.x("DROP TABLE IF EXISTS _ga_gp2")
    return {"mandat_gp_organe_connu": (n - inconnu, n),
            "position_declaree": (declare, nb_groupes)}
