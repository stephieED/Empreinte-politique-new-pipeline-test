"""R-SORT-FINAL : le sort d'un dossier, et `etat_dossier` (doc. 1, 1.5.3 et 1.6 ; cahier 4.6,
« sort final »).

Le sort est celui du **dossier**, pas celui d'un vote : un texte adopté à l'Assemblée peut
échouer au terme de la navette. Il se lit dans la conclusion des décisions (jamais dans leur
code), dans l'ordre :

| sort | preuve |
| --- | --- |
| `promulgue` | acte de promulgation (R-LOIS : numéro et date) ; à défaut, loi du JO reliée au dossier par ses travaux préparatoires (R-LOI-DOSSIER, version 4) |
| `adopte` | adoption définitive (R-ETAPE, `adoptions_definitives`), pas encore promulguée |
| `retire` | acte de retrait de l'initiative |
| `rejete` | rejet qui clôt le dossier : lecture définitive rejetée ; résolution rejetée ; proposition de loi rejetée en première lecture par la chambre où elle a été déposée |
| `non_connu` | aucune de ces preuves (navette en cours, texte non examiné, révision constitutionnelle…) |

Raison `renvoye_en_commission` (version 5, alerte #118, décidé le 23/11/2026 : doc. 5, Q45) : la
dernière décision du dossier est l'adoption d'une motion de renvoi en commission (R-ETAPE,
`renvoi_en_commission`) ; le texte n'est ni adopté ni rejeté, et aucune décision ne suit (il peut
être revenu en commission ou en séance sans être voté). Une décision publiée sans conclusion
(`sans_conclusion`, TSORTFnull) n'est nommée que si elle laisse le sort non connu : dernière
décision d'un dossier sans autre preuve (raison `conclusion_non_classee`, Q46).

Raison `suite_absente_des_archives` (version 3) : le dossier n'est publié que par l'archive d'une
législature close, qui s'arrête (`fin_archive_du_dossier`) alors que le texte a continué sous la
suivante, dont l'archive ne le publie pas : son issue n'est pas lue. Depuis la version 4,
R-LOI-DOSSIER le relie à sa loi quand il le peut (travaux préparatoires publiés au Journal
officiel) : il est alors `promulgue`, avec `lien_loi = 'travaux_preparatoires_jo'` (sinon
`acte_de_promulgation`). Mesuré sur l'archive globale du JO (g14) : 6 des 17 dossiers de la XIVe.

Version 6 (issue #89, 25/11/2026) :
- **adoption sur le texte de CMP** (`adopte_sur_texte_cmp`) : le motif de l'adoption définitive
  (`motif_adoption`, R-ETAPE) est `texte_cmp_adopte_par_les_deux_chambres` ; ou le texte est
  promulgué, R-ETAPE ne reconnaît pas sa clôture (décision de CMP sans chambre, `CMP-DEBATS-DEC`),
  et sa dernière décision d'adoption avant la promulgation est prise en CMP (6 dossiers sur la
  g24, dont celui de la loi 2024-1039). Faux pour un texte ni adopté ni promulgué ;
- **rejet via 49.3** (`rejete_par_censure_49_3`, avec la date, le scrutin et l'acte de la motion) :
  une motion de censure a été adoptée après un engagement de responsabilité sur le texte (R-49-3,
  `censure_49_3`). Le texte engagé est alors rejeté à cette lecture ; le sort reste celui du
  dossier, car la navette peut reprendre (PLFSS 2025, DLR5L17N50588 : censure du 04/12/2024,
  scrutin VTANR5L17V519, puis loi 2025-199 promulguée le 28/02/2025) ;
- la dernière décision du dossier est lue ligne entière : `max_by` sautait une valeur vide, et
  une dernière décision sans chambre (texte de CMP `CMP-DEBATS-DEC`, Congrès) prenait la chambre de
  la décision précédente (3 dossiers sur la g24, sans effet sur le sort mesuré).

Le **49.3** est nommé à part (`par_49_3`) : le gouvernement a engagé sa responsabilité sur le
texte (R-49-3) ; `adopte_par_49_3` quand, en plus, le texte a été adopté ou promulgué. Ce n'est
jamais une position de vote. Une ligne par (dossier, législature où il a avancé), l'étape étant
celle de la législature (R-ETAPE) et le sort celui du dossier."""

from .r_etape import UNE_CHAMBRE, adoptions_definitives, decisions
from .r_loi_dossier import suite_absente_sql

NOM = "R-SORT-FINAL"
VERSION = 6
DEPEND = ("R-ETAPE", "R-49-3", "R-LOIS", "R-LOI-DOSSIER")
SORTIES = ("etat_dossier", "conclusion_non_classee")
DESCRIPTION = (
    "Le sort d'un texte est celui de son dossier, lu dans la conclusion des décisions des deux "
    "chambres : promulgué, adopté définitivement, retiré, rejeté, ou non connu. Il peut différer du "
    "vote affiché : un texte adopté par l'Assemblée peut échouer au terme de la navette. Une "
    "proposition de loi rejetée en première lecture par la chambre où elle a été déposée est "
    "rejetée. Un texte renvoyé en commission par une motion, sans décision ensuite, n'est ni adopté "
    "ni rejeté : son sort reste non connu, avec cette raison. L'adoption sans vote par l'article 49, "
    "alinéa 3, est signalée à part : c'est un fait de procédure, pas un vote.")


def appliquer(ctx):
    censures = ("censure_49_3" if ctx.existe("censure_49_3") else
                "(SELECT NULL::VARCHAR AS dossier, NULL::VARCHAR AS date_motion, NULL::VARCHAR AS scrutin, "
                "NULL::VARCHAR AS acte_motion, NULL::VARCHAR AS issue WHERE false)")
    jo = ("loi_dossier_jo" if ctx.existe("loi_dossier_jo") else
          "(SELECT NULL::VARCHAR AS dossier, NULL::VARCHAR AS numero_loi, NULL::VARCHAR AS date_promulgation, "
          "NULL::VARCHAR AS source_url WHERE false)")
    ctx.ecrire("etat_dossier", f"""
        WITH dec AS ({decisions(ctx)}),
        adopt AS (SELECT dossier, max(date) AS date, max_by(acte, date) AS acte,
                         max_by(motif, date) AS motif
                  FROM ({adoptions_definitives(ctx)}) GROUP BY 1),
        -- Suite absente des archives (version 3, issue #35, décision du 13/11/2026) : dossier publié
        -- par la seule archive d'une législature close, avec des actes d'une législature suivante ;
        -- l'archive de la législature suivante ne le publie pas (17 dossiers de la XIVe, archive
        -- arrêtée au 22/03/2018, g10). Son sort n'est pas « sans décision finale » : il n'est pas lu.
        suite_absente AS ({suite_absente_sql()}),
        depot AS (SELECT dossier, any_value(substr(texte_associe, 1, 4)) AS type_texte,
                         any_value(CASE WHEN code LIKE 'AN%' THEN 'AN' WHEN code LIKE 'SN%' THEN 'SN' END)
                             AS chambre_depot
                  FROM an_dossiers__acte WHERE type_acte = 'DepotInitiative_Type' GROUP BY 1),
        retrait AS (SELECT dossier, min(left(date, 10)) AS date FROM an_dossiers__acte
                    WHERE type_acte = 'RetraitInitiative_Type' GROUP BY 1),
        -- La dernière décision, la ligne entière (version 6) : max_by sautait une valeur vide, et une
        -- décision sans chambre (CMP, Congrès) prenait celle de la décision précédente.
        derniere AS (SELECT dossier, issue, date, acte, lecture, chambre, conclusion_libelle AS conclusion
                     FROM dec
                     QUALIFY row_number() OVER (PARTITION BY dossier ORDER BY date || acte DESC) = 1),
        rejet AS (
            SELECT r.dossier, r.date, r.acte FROM derniere r JOIN depot p USING (dossier)
            JOIN an_dossiers__dossier d ON d.uid = r.dossier
            WHERE r.issue = 'rejete'
              AND (r.lecture = 'ANLDEF'
                   OR d.procedure_code IN {UNE_CHAMBRE} OR r.lecture = 'ANLUNI'
                   OR (p.type_texte = 'PION' AND r.lecture IN ('AN1', 'SN1')
                       AND r.chambre = p.chambre_depot))),
        e49 AS (SELECT dossier, count(DISTINCT acte) AS n, min(date) AS premier FROM engagement_49_3 GROUP BY 1),
        -- Rejet via 49.3 (version 6, issue #89) : motion de censure adoptée après un engagement sur
        -- le texte (R-49-3, `censure_49_3`) ; la première, avec son scrutin.
        cen AS (SELECT dossier, min(date_motion) AS date, arg_min(scrutin, date_motion) AS scrutin,
                       arg_min(acte_motion, date_motion) AS acte
                FROM {censures} WHERE issue = 'adoptee' GROUP BY 1),
        -- La loi d'un dossier : par l'acte de promulgation de l'Assemblée (R-LOIS) ; à défaut, par
        -- les travaux préparatoires publiés au JO (R-LOI-DOSSIER, version 4, issue #35).
        loi_an AS (SELECT dossier, any_value(numero_loi) AS numero_loi,
                          any_value(date_promulgation) AS date_promulgation, any_value(source_url) AS url_loi,
                          'acte_de_promulgation' AS lien_loi
                   FROM loi WHERE dossier IS NOT NULL GROUP BY 1),
        loi_jo AS (SELECT dossier, min(numero_loi) AS numero_loi, min(date_promulgation) AS date_promulgation,
                          min_by(source_url, numero_loi) AS url_loi, 'travaux_preparatoires_jo' AS lien_loi
                   FROM {jo} WHERE dossier IS NOT NULL
                     AND dossier NOT IN (SELECT dossier FROM loi_an) GROUP BY 1),
        loi1 AS (SELECT * FROM loi_an UNION ALL SELECT * FROM loi_jo),
        -- Adoption sur le texte de CMP (version 6, issue #89) : motif de R-ETAPE, ou, pour un texte
        -- promulgué dont R-ETAPE ne reconnaît pas la clôture, dernière décision d'adoption avant la
        -- promulgation prise en CMP (même lecture de la clôture que R-LOI-ADOPTION).
        cmp_prom AS (SELECT dossier FROM (
                         SELECT d.dossier, d.lecture FROM dec d JOIN loi1 l USING (dossier)
                         WHERE d.issue = 'adopte' AND d.date <= l.date_promulgation
                         QUALIFY row_number() OVER (PARTITION BY d.dossier ORDER BY d.date DESC, d.acte DESC) = 1)
                     WHERE lecture = 'CMP'),
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
                             WHEN dr.issue = 'renvoi_en_commission' THEN 'renvoye_en_commission'
                             WHEN dr.issue IS NULL OR dr.issue = 'sans_conclusion' THEN 'conclusion_non_classee'
                             ELSE 'aucune_decision_finale' END END AS raison_sort,
                   a.motif AS motif_adoption, coalesce(a.acte, rj.acte) AS acte_decisif,
                   (l.dossier IS NOT NULL OR a.dossier IS NOT NULL)
                       AND (coalesce(a.motif = 'texte_cmp_adopte_par_les_deux_chambres', false)
                            OR cp.dossier IS NOT NULL) AS adopte_sur_texte_cmp,
                   dr.conclusion AS derniere_conclusion, dr.date AS date_derniere_decision,
                   sa.fin_archive AS fin_archive_du_dossier,
                   e.dossier IS NOT NULL AS par_49_3, coalesce(e.n, 0) AS nb_engagements_49_3,
                   cen.dossier IS NOT NULL AS rejete_par_censure_49_3, cen.date AS date_censure_49_3,
                   cen.scrutin AS scrutin_censure_49_3, cen.acte AS acte_censure_49_3,
                   l.date_promulgation, l.numero_loi, l.url_loi, l.lien_loi, p.type_texte,
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
            LEFT JOIN e49 e ON e.dossier = d.uid
            LEFT JOIN cen ON cen.dossier = d.uid
            LEFT JOIN cmp_prom cp ON cp.dossier = d.uid)
        SELECT s.dossier, coalesce(et.legislature, s.legislature_dossier) AS legislature,
               coalesce(et.etape_atteinte, 'non_etablie') AS etape_atteinte, s.sort, s.par_49_3,
               s.date_promulgation, s.numero_loi,
               s.par_49_3 AND s.sort IN ('adopte', 'promulgue') AS adopte_par_49_3,
               s.nb_engagements_49_3, s.adopte_sur_texte_cmp, s.rejete_par_censure_49_3, s.date_censure_49_3,
               s.scrutin_censure_49_3, s.acte_censure_49_3, s.date_sort, s.raison_sort, s.motif_adoption, s.acte_decisif,
               s.derniere_conclusion, s.date_derniere_decision, s.fin_archive_du_dossier, s.lien_loi, et.date_etape,
               CASE WHEN et.dossier IS NULL THEN 'aucun_acte_date' ELSE et.raison END AS raison_etape,
               s.type_texte, s.procedure_code, s.titre, s.url_loi, s.source_url
        FROM s LEFT JOIN etape_dossier et USING (dossier)""")
    # Codes de conclusion qu'aucune liste de R-ETAPE ne classe : nommés, jamais devinés (#45). Une
    # décision sans conclusion (TSORTFnull) ne l'est que là où elle laisse le sort non connu : dernière
    # décision d'un dossier ni promulgué, ni adopté, ni retiré, ni rejeté (#118, Q46). Le
    # libellé est le premier dans l'ordre alphabétique : la source écrit « Motion adoptée » et
    # « Motion adopté(e) », et l'avertissement ne doit pas changer d'une nuit à l'autre pour si peu.
    ctx.ecrire("conclusion_non_classee", f"""
        WITH dec AS ({decisions(ctx)}),
             nc AS (SELECT d.* FROM dec d
                    WHERE d.issue IS NULL
                       OR (d.issue = 'sans_conclusion' AND d.dossier IN (
                           SELECT dossier FROM etat_dossier WHERE raison_sort = 'conclusion_non_classee')))
        SELECT conclusion_code, min(conclusion_libelle) AS conclusion_libelle,
               count(*) AS decisions, count(DISTINCT dossier) AS dossiers,
               list(DISTINCT dossier ORDER BY dossier)[:5] AS exemples,
               count(DISTINCT dossier) FILTER (dossier IN (
                   SELECT dossier FROM etat_dossier WHERE raison_sort = 'conclusion_non_classee'))
                   AS dossiers_dont_c_est_la_derniere_decision
        FROM nc GROUP BY 1 ORDER BY 1""")
    n = ctx.un("SELECT count(DISTINCT dossier) FROM etat_dossier")
    connu = ctx.un("SELECT count(DISTINCT dossier) FROM etat_dossier WHERE sort <> 'non_connu'")
    prom = ctx.un("SELECT count(DISTINCT dossier) FROM etat_dossier WHERE sort = 'promulgue'")
    prom_adopt = ctx.un(f"""SELECT count(DISTINCT dossier) FROM etat_dossier e
                            WHERE sort = 'promulgue' AND EXISTS (
                              SELECT 1 FROM ({adoptions_definitives(ctx)}) a WHERE a.dossier = e.dossier)""")
    return {"sort_connu": (connu, n),
            "loi_promulguee_dont_adoption_definitive_retrouvee": (prom_adopt, prom)}
