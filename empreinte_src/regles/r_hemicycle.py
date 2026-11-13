"""R-HEMICYCLE : qui siège où, et l'effectif de chaque groupe jour par jour (cahier 4.5 ; doc. 1,
1.6).

Le siège (`placeHemicycle`) est publié **sans date** : c'est celui du jour de l'archive. Les
mandats clos reçoivent le siège actuel de la personne (piège 3.1.1) ; seule une archive figée
d'une législature close donne les sièges de cette législature (cahier 3.1). Donc :

- **législature en cours** : l'archive courante, datée du jour de constat (la date de référence
  du traitement, à défaut la dernière date publiée par la source) ;
- **législature close** : son archive figée (point `…-l<numéro>`), datée de son dernier
  événement (XVe : 05/04/2022, avant les élections ; XVIe : 09/06/2024, la dissolution), si elle
  donne le siège d'au moins 90 % des députés en fonction ce jour-là. Sinon (XIVe : pas d'archive
  figée au chemin standard, cahier 3.1), aucune ligne, et la couverture le dit.

Sont dans l'hémicycle les députés en fonction ce jour-là (R-DEPUTES : un député suspendu parce
qu'il est au gouvernement n'y est pas, son suppléant y est). Leur groupe est leur appartenance
ce jour-là (R-APPARTENANCE) ; un non-inscrit n'a pas de groupe (`rattachement = 'non_inscrit'`) ;
sans mandat GP ce jour-là, `rattachement = 'non_etabli'`.

`effectif_groupe` : pour chaque groupe, de sa création à sa fin (au plus tard le jour de
constat), le nombre de ses membres chaque jour, d'après les périodes d'appartenance. Un
décompte, jamais un ratio.
"""

NOM = "R-HEMICYCLE"
VERSION = 2
DEPEND = ("R-LEGISLATURES", "R-DEPUTES", "R-APPARTENANCE")
SORTIES = ("hemicycle", "effectif_groupe")
DESCRIPTION = (
    "Le siège de chaque député dans l'hémicycle est celui que publie l'Assemblée nationale le jour "
    "où nous lisons ses données : il n'est pas daté par la source, nous le datons du jour de "
    "lecture. Pour une législature close, nous le prenons dans l'archive figée de cette "
    "législature, à la date de l'état qu'elle publie, quand elle donne le siège de presque tous "
    "les députés ; sinon, il n'est pas donné. Un député entré au gouvernement n'y "
    "figure pas : son suppléant siège. L'effectif d'un groupe à une date est le nombre de "
    "députés qui en sont membres ce jour-là, apparentés compris ; les non-inscrits ne sont pas "
    "un groupe.")

MANDAT = """(SELECT * FROM an_acteurs__mandat
             QUALIFY row_number() OVER (PARTITION BY uid ORDER BY prov_point DESC) = 1)"""
ORGANE = """(SELECT * FROM an_acteurs__organe
             QUALIFY row_number() OVER (PARTITION BY uid ORDER BY prov_point DESC) = 1)"""
EST_NI = "(o.sigle = 'NI' OR lower(o.libelle) IN ('non inscrit', 'non inscrits', 'non-inscrits'))"


def date_constat(ctx) -> tuple[str | None, str]:
    """Rend `(date, origine)` : `(ctx.date_reference, "date_reference")` s'il est donné ; sinon la
    plus tardive des dates de début, de fin et de prise de fonction des mandats `ASSEMBLEE` et
    `GP`, avec `"derniere_date_de_la_source"`."""
    if ctx.date_reference:
        return ctx.date_reference, "date_reference"
    d = ctx.un(f"""SELECT max(x) FROM (
        SELECT greatest(date_debut, date_fin, date_prise_fonction) AS x FROM {MANDAT}
        WHERE type_organe IN ('ASSEMBLEE', 'GP'))""")
    return d, "derniere_date_de_la_source"


# Part minimale des députés dont l'archive figée donne le siège pour la servir (XIVe : 154 sièges
# pour 750 mandats, archive non figée à sa clôture).
SEUIL_ARCHIVE_FIGEE = 0.9
_LEG_POINT = "TRY_CAST(regexp_extract(prov_point, '-l([0-9]+)$', 1) AS INTEGER)"


def _figees(ctx) -> list[tuple[int, str, str]]:
    """(législature close, point de son archive figée, jour de l'état) des archives utilisables."""
    if not ctx.existe("an_acteurs__mandat__archives"):
        return []
    cands = ctx.x(f"""
        SELECT l.numero, m.prov_point,
               max(greatest(coalesce(m.date_debut, ''), coalesce(m.date_fin, ''))) AS jour
        FROM legislature l JOIN an_acteurs__mandat__archives m
          ON {_LEG_POINT.replace("prov_point", "m.prov_point")} = l.numero
         AND TRY_CAST(m.legislature AS INTEGER) = l.numero
        WHERE NOT l.en_cours AND m.type_organe IN ('ASSEMBLEE', 'GP')
        GROUP BY 1, 2""")
    out = []
    for numero, point, jour in cands:
        n, avec = ctx.x("""
            SELECT count(*), count(m.place_hemicycle) FROM depute d
            LEFT JOIN an_acteurs__mandat__archives m ON m.uid = d.mandat AND m.prov_point = ?
            WHERE d.legislature = ? AND d.debut <= ? AND coalesce(d.fin, '9999-12-31') >= ?""",
                        [point, numero, jour, jour])[0]
        if n and avec >= SEUIL_ARCHIVE_FIGEE * n:
            out.append((numero, point, jour))
    return out


def appliquer(ctx):
    """Applique R-HEMICYCLE : écrit `hemicycle` (qui siège où) et `effectif_groupe` (l'effectif de
    chaque groupe jour par jour), voir la description du module. Rend la couverture,
    `{nom: (numérateur, dénominateur)}` : `siege_connu`, `groupe_ou_non_inscrit_etabli`,
    `siege_legislatures_closes`."""
    d, origine = date_constat(ctx)
    jour = "NULL::VARCHAR" if d is None else f"'{d}'"
    figees = _figees(ctx)
    # Chaque législature servie : son jour de constat et l'archive qui donne les sièges.
    servies = " UNION ALL ".join(
        [f"SELECT numero, {jour} AS jour, NULL::VARCHAR AS point, '{origine}' AS origine "
         "FROM legislature WHERE en_cours"]
        + [f"SELECT {n}, '{j}', '{p}', 'archive_figee'" for n, p, j in figees])
    ctx.ecrire("hemicycle", f"""
        WITH l AS ({servies}),
        dep AS (SELECT d.*, l.jour, l.point, l.origine FROM depute d JOIN l ON l.numero = d.legislature
                WHERE d.debut <= l.jour AND coalesce(d.fin, '9999-12-31') >= l.jour),
        mf AS (SELECT * FROM an_acteurs__mandat__archives WHERE prov_point IN
               (SELECT point FROM l WHERE point IS NOT NULL)),
        ni AS (SELECT DISTINCT l.numero, m.acteur FROM {MANDAT} m JOIN {ORGANE} o ON o.uid = m.organe
               JOIN l ON m.date_debut <= l.jour AND coalesce(m.date_fin, '9999-12-31') >= l.jour
               WHERE m.type_organe = 'GP' AND {EST_NI}),
        grp AS (SELECT l.numero, a.acteur, any_value(a.groupe) AS groupe, count(*) AS n
                FROM appartenance a JOIN l ON a.debut <= l.jour AND coalesce(a.fin, '9999-12-31') >= l.jour
                GROUP BY 1, 2),
        m AS (SELECT dep.mandat AS uid, coalesce(f.place_hemicycle, CASE WHEN dep.point IS NULL
                                                 THEN c.place_hemicycle END) AS place_hemicycle,
                     coalesce(f.prov_url, c.prov_url) AS prov_url, coalesce(f.prov_uid, c.prov_uid) AS prov_uid
              FROM dep JOIN {MANDAT} c ON c.uid = dep.mandat
              LEFT JOIN mf f ON f.uid = dep.mandat AND f.prov_point = dep.point)
        SELECT dep.legislature, dep.jour AS date, dep.acteur,
               TRY_CAST(m.place_hemicycle AS INTEGER) AS siege,
               CASE WHEN grp.n = 1 THEN grp.groupe END AS groupe,
               CASE WHEN grp.n = 1 THEN 'groupe' WHEN grp.n > 1 THEN 'non_etabli'
                    WHEN ni.acteur IS NOT NULL THEN 'non_inscrit' ELSE 'non_etabli' END AS rattachement,
               CASE WHEN grp.n > 1 THEN 'plusieurs groupes à cette date'
                    WHEN grp.n IS NULL AND ni.acteur IS NULL THEN 'aucun mandat de groupe à cette date' END
                    AS raison_rattachement,
               CASE WHEN m.place_hemicycle IS NULL THEN 'siège non connu' END AS raison_siege,
               dep.mandat, dep.origine AS date_origine, m.place_hemicycle AS siege_source,
               m.prov_url AS source_url, m.prov_uid
        FROM dep JOIN m ON m.uid = dep.mandat
        LEFT JOIN grp ON grp.acteur = dep.acteur AND grp.numero = dep.legislature
        LEFT JOIN ni ON ni.acteur = dep.acteur AND ni.numero = dep.legislature
        ORDER BY dep.legislature, siege, dep.acteur""")

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
            "siege_legislatures_closes": (len(figees), closes)}
