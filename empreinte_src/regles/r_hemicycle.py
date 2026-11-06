"""R-HEMICYCLE : qui siège où, et l'effectif de chaque groupe jour par jour (cahier 4.5 ; doc. 1,
1.6).

Le siège (`placeHemicycle`) est publié **sans date** : c'est celui du jour de l'archive. Les
mandats clos reçoivent le siège actuel de la personne (piège 3.1.1) ; seule une archive figée
après la clôture d'une législature donne les sièges de cette législature. La règle ne sert donc
le siège que pour la **législature en cours**, daté du jour de constat : la date de référence
du traitement (le jour de la génération), à défaut la dernière date publiée par la source. Pour
une législature close, le siège n'est pas connu tant que son archive figée n'est pas lue
(R-ARBITRAGE-ARCHIVES) : aucune ligne, et la couverture le dit.

Sont dans l'hémicycle les députés en fonction ce jour-là (R-DEPUTES : un député suspendu parce
qu'il est au gouvernement n'y est pas, son suppléant y est). Leur groupe est leur appartenance
ce jour-là (R-APPARTENANCE) ; un non-inscrit n'a pas de groupe (`rattachement = 'non_inscrit'`) ;
sans mandat GP ce jour-là, `rattachement = 'non_etabli'`.

`effectif_groupe` : pour chaque groupe, de sa création à sa fin (au plus tard le jour de
constat), le nombre de ses membres chaque jour, d'après les périodes d'appartenance. Un
décompte, jamais un ratio.
"""

NOM = "R-HEMICYCLE"
VERSION = 1
DEPEND = ("R-LEGISLATURES", "R-DEPUTES", "R-APPARTENANCE")
SORTIES = ("hemicycle", "effectif_groupe")
DESCRIPTION = (
    "Le siège de chaque député dans l'hémicycle est celui que publie l'Assemblée nationale le jour "
    "où nous lisons ses données : il n'est pas daté par la source, nous le datons du jour de "
    "lecture, et nous ne le donnons que pour la législature en cours (pour une législature "
    "close, seul l'état publié à sa clôture vaudrait). Un député entré au gouvernement n'y "
    "figure pas : son suppléant siège. L'effectif d'un groupe à une date est le nombre de "
    "députés qui en sont membres ce jour-là, apparentés compris ; les non-inscrits ne sont pas "
    "un groupe.")

MANDAT = """(SELECT * FROM an_acteurs__mandat
             QUALIFY row_number() OVER (PARTITION BY uid ORDER BY prov_point DESC) = 1)"""
ORGANE = """(SELECT * FROM an_acteurs__organe
             QUALIFY row_number() OVER (PARTITION BY uid ORDER BY prov_point DESC) = 1)"""
EST_NI = "(o.sigle = 'NI' OR lower(o.libelle) IN ('non inscrit', 'non inscrits', 'non-inscrits'))"


def date_constat(ctx) -> tuple[str | None, str]:
    if ctx.date_reference:
        return ctx.date_reference, "date_reference"
    d = ctx.un(f"""SELECT max(x) FROM (
        SELECT greatest(date_debut, date_fin, date_prise_fonction) AS x FROM {MANDAT}
        WHERE type_organe IN ('ASSEMBLEE', 'GP'))""")
    return d, "derniere_date_de_la_source"


def appliquer(ctx):
    d, origine = date_constat(ctx)
    jour = "NULL::VARCHAR" if d is None else f"'{d}'"
    ctx.ecrire("hemicycle", f"""
        WITH l AS (SELECT numero FROM legislature WHERE en_cours),
        dep AS (SELECT * FROM depute
                WHERE legislature IN (SELECT numero FROM l)
                  AND debut <= {jour} AND coalesce(fin, '9999-12-31') >= {jour}),
        ni AS (SELECT DISTINCT m.acteur FROM {MANDAT} m JOIN {ORGANE} o ON o.uid = m.organe
               WHERE m.type_organe = 'GP' AND {EST_NI}
                 AND m.date_debut <= {jour} AND coalesce(m.date_fin, '9999-12-31') >= {jour}),
        grp AS (SELECT acteur, any_value(groupe) AS groupe, count(*) AS n FROM appartenance
                WHERE debut <= {jour} AND coalesce(fin, '9999-12-31') >= {jour} GROUP BY 1)
        SELECT dep.legislature, {jour} AS date, dep.acteur,
               TRY_CAST(m.place_hemicycle AS INTEGER) AS siege,
               CASE WHEN grp.n = 1 THEN grp.groupe END AS groupe,
               CASE WHEN grp.n = 1 THEN 'groupe' WHEN grp.n > 1 THEN 'non_etabli'
                    WHEN ni.acteur IS NOT NULL THEN 'non_inscrit' ELSE 'non_etabli' END AS rattachement,
               CASE WHEN grp.n > 1 THEN 'plusieurs groupes à cette date'
                    WHEN grp.n IS NULL AND ni.acteur IS NULL THEN 'aucun mandat de groupe à cette date' END
                    AS raison_rattachement,
               CASE WHEN m.place_hemicycle IS NULL THEN 'siège non connu' END AS raison_siege,
               dep.mandat, '{origine}' AS date_origine, m.place_hemicycle AS siege_source,
               m.prov_url AS source_url, m.prov_uid
        FROM dep JOIN {MANDAT} m ON m.uid = dep.mandat
        LEFT JOIN grp ON grp.acteur = dep.acteur LEFT JOIN ni ON ni.acteur = dep.acteur
        ORDER BY siege, dep.acteur""")

    # Effectif jour par jour : +1 à l'entrée, -1 le lendemain de la sortie, cumulés, puis
    # étalés sur chaque jour de vie du groupe (au plus tard le jour de constat).
    ctx.ecrire("effectif_groupe", f"""
        WITH ev AS (
            SELECT groupe, debut::DATE AS j, 1 AS dlt FROM appartenance
            UNION ALL
            SELECT groupe, fin::DATE + 1, -1 FROM appartenance WHERE fin IS NOT NULL),
        cum AS (SELECT groupe, j, sum(sum(dlt)) OVER (PARTITION BY groupe ORDER BY j) AS effectif
                FROM ev GROUP BY groupe, j),
        jours AS (
            SELECT g.organe AS groupe, g.legislature,
                   unnest(range(g.debut::DATE,
                                least(coalesce(g.fin::DATE, {jour}::DATE), {jour}::DATE) + 1,
                                INTERVAL 1 DAY))::DATE AS j
            FROM groupe g WHERE g.debut IS NOT NULL AND g.debut <= {jour})
        SELECT jours.groupe, strftime(jours.j, '%Y-%m-%d') AS date,
               CAST(coalesce(cum.effectif, 0) AS INTEGER) AS effectif, jours.legislature
        FROM jours ASOF LEFT JOIN cum ON cum.groupe = jours.groupe AND jours.j >= cum.j
        ORDER BY jours.groupe, date""")

    n = ctx.un("SELECT count(*) FROM hemicycle")
    siege = ctx.un("SELECT count(*) FROM hemicycle WHERE siege IS NOT NULL")
    rat = ctx.un("SELECT count(*) FROM hemicycle WHERE rattachement <> 'non_etabli'")
    closes = ctx.un("SELECT count(*) FROM legislature WHERE NOT en_cours")
    return {"siege_connu": (siege, n), "groupe_ou_non_inscrit_etabli": (rat, n),
            "siege_legislatures_closes": (0, closes)}
