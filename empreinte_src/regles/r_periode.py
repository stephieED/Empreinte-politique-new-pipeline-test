"""R-PERIODE : les périodes d'une position (doc. 1, 1.5.2 et 1.6, R-BANC / R-PERIODE ; cahier 4.2
« Ce que cette personne a voté » et 4.6 « Période d'une position » ; doc. 5, Q2).

Une période est un intervalle de dates pendant lequel la personne siège comme députée (mandats de
R-DEPUTES : la suspension d'un député entré au gouvernement est déjà un trou entre deux mandats),
et pendant lequel ni son **banc** ni le **gouvernement** ne changent :

- le banc est la position que **déclare** son groupe à l'Assemblée à la date (R-APPARTENANCE :
  majoritaire, minoritaire, opposition), sinon `non_declaree` — jamais déduit, jamais cherché
  ailleurs. XVIIe : aucun groupe n'en déclare, tous les bancs sont « non déclaré » et les
  périodes ne changent qu'avec le gouvernement. Un député sans groupe à la date (non-inscrit) a le
  banc `non_declaree` (raison `sans_groupe`) ;
- le gouvernement est celui en fonction à la date (dates publiées de l'organe Gouvernement) ;
  entre deux gouvernements (jours sans gouvernement publié), `gouvernement` est vide.

Un changement de groupe sans changement de banc ne coupe pas la période. Deux morceaux ne sont
fusionnés que s'ils se touchent (le second commence le lendemain du premier) dans la même
législature. Une période ouverte (mandat en cours) a `fin` vide.

`periode` = `acteur/debut` : identifiant stable tant que la période ne change pas."""

from .r_etape import date_ref

NOM = "R-PERIODE"
VERSION = 1
DEPEND = ("R-DEPUTES", "R-APPARTENANCE", "R-GOUVERNEMENTS")
SORTIES = ("periode_position",)
DESCRIPTION = (
    "Les positions d'une personne sont regroupées par période. Une période change quand change son "
    "banc — la position (majoritaire, minoritaire, opposition) que son groupe déclare à "
    "l'Assemblée — ou quand change le gouvernement, d'après ses dates officielles. Le banc n'est "
    "jamais déduit : quand le groupe n'en déclare pas, il est « non déclaré ». Dans la XVIIe, aucun "
    "groupe ne déclare de position : les périodes ne changent qu'avec le gouvernement. Les périodes "
    "couvrent les seuls jours où la personne siège comme députée.")

FIN_OUVERTE = "'9999-12-31'"


def appliquer(ctx):
    """Applique R-PERIODE : écrit `periode_position`, les périodes d'une position (voir la
    description du module). Rend la couverture, `{nom: (numérateur, dénominateur)}` :
    `periode_banc_declare`, `periode_gouvernement_etabli`."""
    ref = date_ref(ctx)
    ctx.x(f"""CREATE OR REPLACE TEMP TABLE _pp AS
        WITH spans AS (
            SELECT acteur, legislature, mandat, debut, least(coalesce(fin, '{ref}'), '{ref}') AS fin,
                   fin IS NULL AS ouvert
            FROM depute WHERE debut IS NOT NULL AND debut <= least(coalesce(fin, '{ref}'), '{ref}')),
        bornes AS (
            SELECT mandat, debut AS d FROM spans
            UNION SELECT s.mandat, g.debut FROM spans s JOIN gouvernement g
                ON g.debut > s.debut AND g.debut <= s.fin
            UNION SELECT s.mandat, strftime(g.fin::DATE + 1, '%Y-%m-%d') FROM spans s JOIN gouvernement g
                ON g.fin IS NOT NULL AND strftime(g.fin::DATE + 1, '%Y-%m-%d') > s.debut
               AND strftime(g.fin::DATE + 1, '%Y-%m-%d') <= s.fin
            UNION SELECT s.mandat, a.debut FROM spans s JOIN appartenance a
                ON a.acteur = s.acteur AND a.debut > s.debut AND a.debut <= s.fin
            UNION SELECT s.mandat, strftime(a.fin::DATE + 1, '%Y-%m-%d') FROM spans s JOIN appartenance a
                ON a.acteur = s.acteur AND a.fin IS NOT NULL
               AND strftime(a.fin::DATE + 1, '%Y-%m-%d') > s.debut
               AND strftime(a.fin::DATE + 1, '%Y-%m-%d') <= s.fin),
        morceaux AS (
            SELECT s.acteur, s.legislature, s.mandat, s.ouvert, b.d AS debut,
                   coalesce(strftime(lead(b.d::DATE) OVER (PARTITION BY s.mandat ORDER BY b.d) - 1, '%Y-%m-%d'),
                            s.fin) AS fin,
                   lead(b.d) OVER (PARTITION BY s.mandat ORDER BY b.d) IS NULL AS dernier
            FROM bornes b JOIN spans s USING (mandat)),
        etat AS (
            SELECT m.*,
                   (SELECT g.organe FROM gouvernement g WHERE g.debut <= m.debut
                      AND coalesce(g.fin, {FIN_OUVERTE}) >= m.debut ORDER BY g.debut DESC LIMIT 1) AS gouvernement,
                   (SELECT {{'groupe': a.groupe, 'banc': gr.position_declaree}}
                    FROM appartenance a JOIN groupe gr ON gr.organe = a.groupe
                    WHERE a.acteur = m.acteur AND a.debut <= m.debut
                      AND coalesce(a.fin, {FIN_OUVERTE}) >= m.debut
                    ORDER BY a.debut DESC LIMIT 1) AS g
            FROM morceaux m)
        SELECT acteur, legislature, mandat, debut, fin, ouvert AND dernier AS ouvert, gouvernement,
               coalesce(g.banc, 'non_declaree') AS banc,
               CASE WHEN g.groupe IS NULL THEN 'sans_groupe'
                    WHEN g.banc = 'non_declaree' THEN 'position_non_declaree_par_le_groupe' END AS raison_banc
        FROM etat""")
    ctx.ecrire("periode_position", f"""
        WITH o AS (
            SELECT *, lag(fin) OVER w AS fin_prec, lag(banc) OVER w AS banc_prec,
                      lag(gouvernement) OVER w AS gouv_prec, lag(legislature) OVER w AS leg_prec,
                      lag(raison_banc) OVER w AS raison_prec
            FROM _pp WINDOW w AS (PARTITION BY acteur ORDER BY debut)),
        i AS (
            SELECT *, sum(CASE WHEN fin_prec IS NOT NULL AND debut::DATE = fin_prec::DATE + 1
                                    AND banc = banc_prec AND gouvernement IS NOT DISTINCT FROM gouv_prec
                                    AND legislature = leg_prec THEN 0 ELSE 1 END)
                      OVER (PARTITION BY acteur ORDER BY debut ROWS UNBOUNDED PRECEDING) AS ilot
            FROM o)
        SELECT acteur, acteur || '/' || min(debut) AS periode, min(debut) AS debut,
               CASE WHEN bool_or(ouvert) THEN NULL ELSE max(fin) END AS fin,
               any_value(banc) AS banc, any_value(gouvernement) AS gouvernement,
               any_value(legislature) AS legislature,
               CASE WHEN any_value(gouvernement) IS NULL THEN 'aucun_gouvernement_a_la_date' END AS raison_gouvernement,
               list_sort(list_distinct(list(raison_banc))) AS raisons_banc,
               list_sort(list_distinct(list(mandat))) AS mandats
        FROM i GROUP BY acteur, ilot
        ORDER BY acteur, debut""")
    ctx.x("DROP TABLE IF EXISTS _pp")
    r = ctx.x("""SELECT count(*), count(*) FILTER (banc <> 'non_declaree'),
                        count(*) FILTER (gouvernement IS NOT NULL) FROM periode_position""")[0]
    return {"periode_banc_declare": (r[1], r[0]), "periode_gouvernement_etabli": (r[2], r[0])}
