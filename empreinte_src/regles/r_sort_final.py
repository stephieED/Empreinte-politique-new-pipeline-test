"""R-SORT-FINAL : le sort d'un dossier, et `etat_dossier` (doc. 1, 1.5.3 et 1.6 ; cahier 4.6,
« sort final »).

Le sort est celui du **dossier**, pas celui d'un vote : un texte adopté à l'Assemblée peut
échouer au terme de la navette. Il se lit dans la conclusion des décisions (jamais dans leur
code), dans l'ordre :

| sort | preuve |
| --- | --- |
| `promulgue` | acte de promulgation (R-LOIS : numéro et date) |
| `adopte` | adoption définitive (R-ETAPE, `adoptions_definitives`), pas encore promulguée |
| `retire` | acte de retrait de l'initiative |
| `rejete` | rejet qui clôt le dossier : lecture définitive rejetée ; résolution rejetée ; proposition de loi rejetée en première lecture par la chambre où elle a été déposée |
| `non_connu` | aucune de ces preuves (navette en cours, texte non examiné, révision constitutionnelle…) |

Raison `suite_absente_des_archives` (version 3) : le dossier n'est publié que par l'archive d'une
législature close, qui s'arrête (`fin_archive_du_dossier`) alors que le texte a continué sous la
suivante, dont l'archive ne le publie pas : son issue n'est pas lue. R-LOI-DOSSIER (à venir) le
reliera à sa loi par les travaux préparatoires publiés au Journal officiel.

Le **49.3** est nommé à part (`par_49_3`) : le gouvernement a engagé sa responsabilité sur le
texte (R-49-3) ; `adopte_par_49_3` quand, en plus, le texte a été adopté ou promulgué. Ce n'est
jamais une position de vote. Une ligne par (dossier, législature où il a avancé), l'étape étant
celle de la législature (R-ETAPE) et le sort celui du dossier."""

from .r_etape import UNE_CHAMBRE, adoptions_definitives, decisions

NOM = "R-SORT-FINAL"
VERSION = 3
DEPEND = ("R-ETAPE", "R-49-3", "R-LOIS")
SORTIES = ("etat_dossier", "conclusion_non_classee")
DESCRIPTION = (
    "Le sort d'un texte est celui de son dossier, lu dans la conclusion des décisions des deux "
    "chambres : promulgué, adopté définitivement, retiré, rejeté, ou non connu. Il peut différer du "
    "vote affiché : un texte adopté par l'Assemblée peut échouer au terme de la navette. Une "
    "proposition de loi rejetée en première lecture par la chambre où elle a été déposée est "
    "rejetée. L'adoption sans vote par l'article 49, alinéa 3, est signalée à part : c'est un fait "
    "de procédure, pas un vote.")


def appliquer(ctx):
    ctx.ecrire("etat_dossier", f"""
        WITH dec AS ({decisions(ctx)}),
        adopt AS (SELECT dossier, max(date) AS date, max_by(acte, date) AS acte,
                         max_by(motif, date) AS motif
                  FROM ({adoptions_definitives(ctx)}) GROUP BY 1),
        -- Suite absente des archives (version 3, issue #35, décision du 13/11/2026) : dossier publié
        -- par la seule archive d'une législature close, avec des actes d'une législature suivante ;
        -- l'archive de la législature suivante ne le publie pas (17 dossiers de la XIVe, archive
        -- arrêtée au 22/03/2018, g10). Son sort n'est pas « sans décision finale » : il n'est pas lu.
        pts AS (SELECT prov_point, TRY_CAST(regexp_extract(prov_point, 'l(\d+)$', 1) AS INTEGER) AS leg,
                       max(left(date, 10)) AS fin_archive
                FROM an_dossiers__acte GROUP BY 1),
        par_dossier AS (SELECT dossier, count(DISTINCT prov_point) AS n, any_value(prov_point) AS pt,
                               max(TRY_CAST(regexp_extract(uid, '^L(\d+)-', 1) AS INTEGER)) AS leg_acte
                        FROM an_dossiers__acte GROUP BY 1),
        suite_absente AS (
            SELECT x.dossier, pts.fin_archive FROM par_dossier x JOIN pts ON pts.prov_point = x.pt
            JOIN legislature lg ON lg.numero = pts.leg
            WHERE x.n = 1 AND lg.fin IS NOT NULL AND x.leg_acte > pts.leg),
        depot AS (SELECT dossier, any_value(substr(texte_associe, 1, 4)) AS type_texte,
                         any_value(CASE WHEN code LIKE 'AN%' THEN 'AN' WHEN code LIKE 'SN%' THEN 'SN' END)
                             AS chambre_depot
                  FROM an_dossiers__acte WHERE type_acte = 'DepotInitiative_Type' GROUP BY 1),
        retrait AS (SELECT dossier, min(left(date, 10)) AS date FROM an_dossiers__acte
                    WHERE type_acte = 'RetraitInitiative_Type' GROUP BY 1),
        derniere AS (SELECT dossier, max_by(issue, date || acte) AS issue, max(date) AS date,
                            max_by(acte, date || acte) AS acte, max_by(lecture, date || acte) AS lecture,
                            max_by(chambre, date || acte) AS chambre,
                            max_by(conclusion_libelle, date || acte) AS conclusion
                     FROM dec GROUP BY 1),
        rejet AS (
            SELECT r.dossier, r.date, r.acte FROM derniere r JOIN depot p USING (dossier)
            JOIN an_dossiers__dossier d ON d.uid = r.dossier
            WHERE r.issue = 'rejete'
              AND (r.lecture = 'ANLDEF'
                   OR d.procedure_code IN {UNE_CHAMBRE} OR r.lecture = 'ANLUNI'
                   OR (p.type_texte = 'PION' AND r.lecture IN ('AN1', 'SN1')
                       AND r.chambre = p.chambre_depot))),
        e49 AS (SELECT dossier, count(DISTINCT acte) AS n, min(date) AS premier FROM engagement_49_3 GROUP BY 1),
        loi1 AS (SELECT dossier, any_value(numero_loi) AS numero_loi,
                        any_value(date_promulgation) AS date_promulgation, any_value(source_url) AS url_loi
                 FROM loi GROUP BY 1),
        s AS (
            SELECT d.uid AS dossier,
                   CASE WHEN l.dossier IS NOT NULL THEN 'promulgue'
                        WHEN a.dossier IS NOT NULL THEN 'adopte'
                        WHEN rt.dossier IS NOT NULL THEN 'retire'
                        WHEN rj.dossier IS NOT NULL THEN 'rejete'
                        ELSE 'non_connu' END AS sort,
                   CASE WHEN l.dossier IS NOT NULL THEN l.date_promulgation
                        WHEN a.dossier IS NOT NULL THEN a.date
                        WHEN rt.dossier IS NOT NULL THEN rt.date
                        WHEN rj.dossier IS NOT NULL THEN rj.date END AS date_sort,
                   CASE WHEN l.dossier IS NULL AND a.dossier IS NULL AND rt.dossier IS NULL
                             AND rj.dossier IS NULL THEN
                        CASE WHEN p.dossier IS NULL THEN 'pas_de_texte_depose'
                             WHEN d.procedure_code = '7' AND dr.dossier IS NOT NULL THEN 'revision_constitutionnelle'
                             WHEN sa.dossier IS NOT NULL THEN 'suite_absente_des_archives'
                             WHEN dr.dossier IS NULL THEN 'aucune_decision_en_seance'
                             WHEN dr.issue IS NULL THEN 'conclusion_non_classee'
                             ELSE 'aucune_decision_finale' END END AS raison_sort,
                   a.motif AS motif_adoption, coalesce(a.acte, rj.acte) AS acte_decisif,
                   dr.conclusion AS derniere_conclusion, dr.date AS date_derniere_decision,
                   sa.fin_archive AS fin_archive_du_dossier,
                   e.dossier IS NOT NULL AS par_49_3, coalesce(e.n, 0) AS nb_engagements_49_3,
                   l.date_promulgation, l.numero_loi, l.url_loi, p.type_texte,
                   d.procedure_code, d.titre, TRY_CAST(d.legislature AS INTEGER) AS legislature_dossier,
                   d.prov_url AS source_url
            FROM an_dossiers__dossier d
            LEFT JOIN loi1 l ON l.dossier = d.uid
            LEFT JOIN adopt a ON a.dossier = d.uid
            LEFT JOIN retrait rt ON rt.dossier = d.uid
            LEFT JOIN rejet rj ON rj.dossier = d.uid
            LEFT JOIN derniere dr ON dr.dossier = d.uid
            LEFT JOIN suite_absente sa ON sa.dossier = d.uid
            LEFT JOIN depot p ON p.dossier = d.uid
            LEFT JOIN e49 e ON e.dossier = d.uid)
        SELECT s.dossier, coalesce(et.legislature, s.legislature_dossier) AS legislature,
               coalesce(et.etape_atteinte, 'non_etablie') AS etape_atteinte, s.sort, s.par_49_3,
               s.date_promulgation, s.numero_loi,
               s.par_49_3 AND s.sort IN ('adopte', 'promulgue') AS adopte_par_49_3,
               s.nb_engagements_49_3, s.date_sort, s.raison_sort, s.motif_adoption, s.acte_decisif,
               s.derniere_conclusion, s.date_derniere_decision, s.fin_archive_du_dossier, et.date_etape,
               CASE WHEN et.dossier IS NULL THEN 'aucun_acte_date' ELSE et.raison END AS raison_etape,
               s.type_texte, s.procedure_code, s.titre, s.url_loi, s.source_url
        FROM s LEFT JOIN etape_dossier et USING (dossier)""")
    # Codes de conclusion qu'aucune liste de R-ETAPE ne classe : nommés, jamais devinés (#45).
    ctx.ecrire("conclusion_non_classee", f"""
        SELECT conclusion_code, any_value(conclusion_libelle) AS conclusion_libelle,
               count(*) AS decisions, count(DISTINCT dossier) AS dossiers,
               list(DISTINCT dossier ORDER BY dossier)[:5] AS exemples,
               count(DISTINCT dossier) FILTER (dossier IN (
                   SELECT dossier FROM etat_dossier WHERE raison_sort = 'conclusion_non_classee'))
                   AS dossiers_dont_c_est_la_derniere_decision
        FROM ({decisions(ctx)}) WHERE issue IS NULL GROUP BY 1 ORDER BY 1""")
    n = ctx.un("SELECT count(DISTINCT dossier) FROM etat_dossier")
    connu = ctx.un("SELECT count(DISTINCT dossier) FROM etat_dossier WHERE sort <> 'non_connu'")
    prom = ctx.un("SELECT count(DISTINCT dossier) FROM etat_dossier WHERE sort = 'promulgue'")
    prom_adopt = ctx.un(f"""SELECT count(DISTINCT dossier) FROM etat_dossier e
                            WHERE sort = 'promulgue' AND EXISTS (
                              SELECT 1 FROM ({adoptions_definitives(ctx)}) a WHERE a.dossier = e.dossier)""")
    return {"sort_connu": (connu, n),
            "loi_promulguee_dont_adoption_definitive_retrouvee": (prom_adopt, prom)}
