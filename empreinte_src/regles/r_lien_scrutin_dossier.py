"""R-LIEN-SCRUTIN-DOSSIER : sur quel dossier porte un scrutin (doc. 1, 1.6 ; mesures
`an-scrutins-dossiers.md`, 4.2).

Le scrutin ne le dit, en général, pas (cahier 3.1.2). Trois routes, dans l'ordre :

1. `reference_directe` : `objet.dossierLegislatif.dossierRef` du scrutin (XVIIe seulement) ;
2. `acte_cite` : un acte d'un dossier cite le scrutin (`voteRefs`) ; un acte partagé par deux
   dossiers (49.3 et motions de censure des lois financières) répond pour les deux ;
3. `seance` : la séance du scrutin (`seanceRef`) est la réunion (`reunionRef`) d'un acte de
   discussion en séance ou de décision ; si la séance mène à plusieurs dossiers, départage par
   le titre **parmi ces seuls dossiers** (`seance_titre`) : un seul titre de dossier, normalisé,
   contenu dans l'intitulé normalisé du scrutin ; sinon la route ne répond pas.

Accord exigé : quand plusieurs routes répondent, le lien est l'intersection de leurs réponses ;
une intersection vide est un **désaccord** : pas de lien, et une ligne dans
`scrutin_non_relie` (raison `desaccord`, candidats de chaque route). Un scrutin sans route qui
réponde y figure aussi (`seance_ambigue`, `seance_inconnue`). La route publiée est la première
qui a répondu ; `routes` les nomme toutes."""

NOM = "R-LIEN-SCRUTIN-DOSSIER"
VERSION = 1
DEPEND = ("R-NATURE-SCRUTIN",)
SORTIES = ("lien_scrutin_dossier", "scrutin_non_relie")
DESCRIPTION = (
    "Un scrutin ne dit pas toujours sur quel texte il porte. Le lien est cherché par trois routes, "
    "dans l'ordre : la référence au dossier publiée avec le scrutin ; un acte du dossier qui cite le "
    "scrutin ; la séance où le scrutin a eu lieu, quand un acte du dossier y est discuté ou décidé. "
    "Si cette séance a porté sur plusieurs textes, le scrutin n'est relié qu'à celui dont le titre "
    "figure dans l'intitulé du scrutin, et seulement s'il est le seul. Quand plusieurs routes "
    "répondent, elles doivent s'accorder : en cas de désaccord, le scrutin n'est relié à aucun "
    "texte, et le désaccord est signalé.")

# Titre normalisé pour le départage : sans accents, ponctuation -> espace.
def _norme(col: str) -> str:
    return (f"trim(regexp_replace(strip_accents(lower(replace(coalesce({col}, ''), '’', ''''))), "
            f"'[^a-z0-9]+', ' ', 'g'))")


def appliquer(ctx):
    ctx.x(f"""CREATE OR REPLACE TEMP TABLE _routes AS
        WITH s AS (SELECT scrutin, seance, dossier_ref, {_norme('titre')} AS t FROM scrutin_nature),
        r1 AS (SELECT scrutin, 'reference_directe' AS route, 1 AS rang, dossier_ref AS dossier
               FROM s WHERE dossier_ref IS NOT NULL),
        r2 AS (SELECT DISTINCT v.scrutin, 'acte_cite' AS route, 2 AS rang, a.dossier
               FROM an_dossiers__acte a, unnest(a.scrutins) AS v(scrutin)
               JOIN s ON s.scrutin = v.scrutin),
        seance AS (SELECT DISTINCT a.reunion AS seance, a.dossier, {_norme('d.titre')} AS td
                   FROM an_dossiers__acte a JOIN an_dossiers__dossier d ON d.uid = a.dossier
                   WHERE a.reunion IS NOT NULL
                     AND a.type_acte IN ('DiscussionSeancePublique_Type', 'Decision_Type')),
        nb AS (SELECT seance, count(*) AS n FROM seance GROUP BY 1),
        r3 AS (SELECT s.scrutin, 'seance' AS route, 3 AS rang, se.dossier
               FROM s JOIN seance se USING (seance) JOIN nb USING (seance) WHERE nb.n = 1),
        titre AS (SELECT s.scrutin, se.dossier
                  FROM s JOIN seance se USING (seance) JOIN nb USING (seance)
                  WHERE nb.n > 1 AND length(se.td) > 0 AND contains(s.t, se.td)),
        r4 AS (SELECT scrutin, 'seance_titre' AS route, 3 AS rang, any_value(dossier) AS dossier
               FROM titre GROUP BY 1 HAVING count(*) = 1)
        SELECT * FROM r1 UNION ALL SELECT * FROM r2 UNION ALL SELECT * FROM r3
        UNION ALL SELECT * FROM r4""")
    # Accord : un dossier est retenu s'il est dans la réponse de chaque route qui a répondu.
    ctx.x("""CREATE OR REPLACE TEMP TABLE _accord AS
        WITH par_route AS (SELECT scrutin, route, rang, list(DISTINCT dossier) AS dossiers
                           FROM _routes GROUP BY ALL),
        nb AS (SELECT scrutin, count(*) AS n_routes FROM par_route GROUP BY 1),
        votes AS (SELECT r.scrutin, r.dossier, count(DISTINCT r.route) AS n,
                         list(DISTINCT r.route ORDER BY r.route) AS routes,
                         min_by(r.route, r.rang) AS route
                  FROM _routes r GROUP BY 1, 2)
        SELECT v.*, nb.n_routes FROM votes v JOIN nb USING (scrutin)""")
    ctx.ecrire("lien_scrutin_dossier", """
        WITH premiere AS (SELECT * FROM _accord WHERE n = n_routes)
        SELECT p.scrutin, p.dossier, p.route, p.routes, p.n_routes > 1 AS recoupe,
               count(*) OVER (PARTITION BY p.scrutin) AS nb_dossiers,
               s.source_url, d.prov_url AS dossier_url
        FROM premiere p JOIN scrutin_nature s USING (scrutin)
        LEFT JOIN an_dossiers__dossier d ON d.uid = p.dossier""")
    ctx.ecrire("scrutin_non_relie", """
        WITH r AS (SELECT scrutin, list(DISTINCT route || ':' || dossier ORDER BY route || ':' || dossier)
                              AS candidats FROM _routes GROUP BY 1),
        amb AS (SELECT s.scrutin FROM scrutin_nature s
                WHERE EXISTS (SELECT 1 FROM an_dossiers__acte a WHERE a.reunion = s.seance
                              AND a.type_acte IN ('DiscussionSeancePublique_Type', 'Decision_Type')))
        SELECT s.scrutin,
               CASE WHEN r.scrutin IS NOT NULL THEN 'desaccord'
                    WHEN s.scrutin IN (SELECT scrutin FROM amb) THEN 'seance_ambigue'
                    ELSE 'seance_inconnue' END AS raison,
               r.candidats, s.source_url
        FROM scrutin_nature s LEFT JOIN r USING (scrutin)
        WHERE s.scrutin NOT IN (SELECT scrutin FROM lien_scrutin_dossier)""")
    n = ctx.un("SELECT count(*) FROM scrutin_nature")
    relies = ctx.un("SELECT count(DISTINCT scrutin) FROM lien_scrutin_dossier")
    ens = ctx.un("SELECT count(*) FROM scrutin_nature WHERE nature = 'ensemble'")
    ens_relies = ctx.un("""SELECT count(DISTINCT l.scrutin) FROM lien_scrutin_dossier l
                           JOIN scrutin_nature s USING (scrutin) WHERE s.nature = 'ensemble'""")
    recoupes = ctx.un("SELECT count(DISTINCT scrutin) FROM lien_scrutin_dossier WHERE recoupe")
    desaccords = ctx.un("SELECT count(*) FROM scrutin_non_relie WHERE raison = 'desaccord'")
    ctx.x("DROP TABLE _routes")
    ctx.x("DROP TABLE _accord")
    return {"scrutin_relie": (relies, n), "ensemble_relie": (ens_relies, ens),
            "lien_recoupe_par_deux_routes": (recoupes, relies),
            "desaccord_entre_routes": (desaccords, n)}
