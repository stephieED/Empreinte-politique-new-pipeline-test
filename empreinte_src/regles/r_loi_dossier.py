"""R-LOI-DOSSIER : le dossier de l'Assemblée d'une loi publiée au Journal officiel, par ses travaux
préparatoires (issue #35, décision Q33 du 13/11/2026 « Dire le trou, puis relier »).

Une loi promulguée sous la législature suivante n'est dans aucune archive de dossiers de
l'Assemblée (R-LOIS ; 17 dossiers de la XIVe, archive arrêtée au 22/03/2018, dont la loi
2018-287), et l'Assemblée ne publie pas de NOR dans ses documents. Le JO publie avec chaque loi
ses travaux préparatoires (lecteur `jo_actes`, table `travaux_preparatoires`) : pour l'Assemblée,
des numéros de documents (« Proposition de loi n° 1817 », « Rapport … n° 2810 », « TA n° 290 »).

Un numéro d'un document de l'Assemblée n'est unique que dans sa législature, que le JO ne dit
pas. Sont candidats, dans la législature de la promulgation et dans la précédente, chacune jugée
à part : les documents de l'Assemblée portant ce numéro et du type que nomme la ligne (proposition
→ `PION`, projet → `PRJL`, rapport → `RAPP`, avis → `AVIS` ; texte adopté → `…BTA<numéro>`). Une
législature est retenue si tous ses numéros trouvés mènent au **même** dossier, et au moins deux ;
la loi est reliée si une seule législature est retenue. Sinon : pas de lien, et la raison
(`pas_de_travaux_preparatoires`, `aucun_document`, `un_seul_numero`, `dossiers_differents`,
`deux_legislatures_possibles`).

Contrôle de la méthode : pour les lois que l'Assemblée relie elle-même (acte de promulgation,
R-LOIS), le dossier trouvé doit être le même (couverture `accord_avec_l_assemblee`)."""

NOM = "R-LOI-DOSSIER"
VERSION = 1
DEPEND = ("R-LEGISLATURES", "R-LOIS")
SORTIES = ("loi_dossier_jo",)
DESCRIPTION = (
    "Une loi promulguée après la fin de la législature où son texte a été déposé n'est dans aucune "
    "archive de l'Assemblée. Elle est reliée à son dossier par les travaux préparatoires que le "
    "Journal officiel publie avec elle : les numéros des documents de l'Assemblée (proposition ou "
    "projet, rapport, texte adopté), cherchés dans la législature de la promulgation et dans la "
    "précédente. Le lien n'est retenu que si au moins deux numéros mènent au même dossier, et aucun "
    "à un autre.")

_TABLES = ("jo_actes__acte_reglementaire", "jo_actes__travaux_preparatoires", "an_dossiers__document")


def appliquer(ctx):
    if not all(ctx.existe(t) for t in _TABLES):
        ctx.ecrire("loi_dossier_jo", """
            SELECT NULL::VARCHAR AS acte, NULL::VARCHAR AS numero_loi, NULL::VARCHAR AS date_promulgation,
                   NULL::INTEGER AS legislature, NULL::VARCHAR AS dossier, NULL::VARCHAR AS raison,
                   NULL::VARCHAR[] AS documents, NULL::INTEGER AS numeros_trouves,
                   NULL::VARCHAR AS dossier_assemblee, NULL::VARCHAR AS source_url WHERE false""")
        return {"loi_reliee_a_un_dossier": (0, 0)}
    ctx.ecrire("loi_dossier_jo", r"""
        WITH lois AS (
            SELECT uid AS acte, any_value(numero) AS numero_loi, any_value(date_signature) AS date_promulgation,
                   any_value(prov_url) AS source_url
            FROM jo_actes__acte_reglementaire
            WHERE nature IN ('LOI', 'LOI_ORGANIQUE') AND numero IS NOT NULL GROUP BY 1),
        leg AS (
            SELECT l.acte, (SELECT max(g.numero) FROM legislature g WHERE g.debut <= l.date_promulgation) AS leg
            FROM lois l),
        tp AS (
            SELECT DISTINCT t.acte, t.numero, t.numero_ta,
                   CASE t.nature WHEN 'proposition_de_loi' THEN 'PION' WHEN 'projet_de_loi' THEN 'PRJL'
                                 WHEN 'proposition_de_resolution' THEN 'PNRE' WHEN 'rapport' THEN 'RAPP'
                                 WHEN 'avis' THEN 'AVIS' END AS type_doc
            FROM jo_actes__travaux_preparatoires t
            WHERE t.chambre = 'AN' AND (t.numero IS NOT NULL OR t.numero_ta IS NOT NULL)),
        docs AS (
            SELECT DISTINCT uid, dossier, left(uid, 4) AS type_doc,
                   TRY_CAST(regexp_extract(uid, 'ANR5L(\d+)', 1) AS INTEGER) AS leg,
                   regexp_extract(uid, 'ANR5L\d+(B|BTA|BTC)\d+$', 1) AS genre,
                   TRY_CAST(regexp_extract(uid, 'ANR5L\d+(?:B|BTA|BTC)(\d+)$', 1) AS INTEGER) AS num
            FROM an_dossiers__document WHERE uid LIKE '%ANR5L%' AND dossier IS NOT NULL),
        -- Un numéro de l'Assemblée est unique dans sa législature : chaque législature candidate
        -- (celle de la promulgation, la précédente) est jugée à part ; le type du document doit
        -- être celui que nomme la ligne (proposition → PION, projet → PRJL, rapport → RAPP…).
        cand AS (
            SELECT tp.acte, d.leg, coalesce(tp.numero, 'TA' || tp.numero_ta) AS cle, d.uid, d.dossier
            FROM tp JOIN leg USING (acte)
            JOIN docs d ON d.leg IN (leg.leg, leg.leg - 1)
              AND ((tp.numero IS NOT NULL AND d.genre = 'B' AND d.num = TRY_CAST(tp.numero AS INTEGER)
                    AND d.type_doc = tp.type_doc)
                OR (tp.numero IS NULL AND tp.numero_ta IS NOT NULL AND d.genre = 'BTA'
                    AND d.num = TRY_CAST(tp.numero_ta AS INTEGER)))),
        par_leg AS (
            SELECT acte, leg, count(DISTINCT dossier) AS nb_dossiers, count(DISTINCT cle) AS numeros,
                   any_value(dossier) AS dossier, list(DISTINCT uid ORDER BY uid) AS documents
            FROM cand GROUP BY 1, 2),
        nette AS (SELECT * FROM par_leg WHERE nb_dossiers = 1 AND numeros >= 2),
        par_loi AS (
            SELECT p.acte, count(DISTINCT n.dossier) AS nb_dossiers,
                   max(p.numeros) AS numeros_trouves, any_value(n.dossier) AS dossier,
                   max(p.nb_dossiers) AS dossiers_max,
                   any_value(n.documents) AS documents
            FROM par_leg p LEFT JOIN nette n ON n.acte = p.acte AND n.leg = p.leg GROUP BY 1),
        an AS (SELECT numero_loi, any_value(dossier) AS dossier FROM loi GROUP BY 1)
        SELECT l.acte, l.numero_loi, l.date_promulgation, leg.leg AS legislature,
               CASE WHEN p.nb_dossiers = 1 THEN p.dossier END AS dossier,
               CASE WHEN p.nb_dossiers = 1 THEN NULL
                    WHEN p.acte IS NULL AND NOT EXISTS (SELECT 1 FROM jo_actes__travaux_preparatoires t
                                                        WHERE t.acte = l.acte) THEN 'pas_de_travaux_preparatoires'
                    WHEN p.acte IS NULL THEN 'aucun_document'
                    WHEN p.nb_dossiers > 1 THEN 'deux_legislatures_possibles'
                    WHEN p.dossiers_max > 1 THEN 'dossiers_differents'
                    WHEN p.nb_dossiers = 0 THEN 'un_seul_numero' END AS raison,
               p.documents, p.numeros_trouves, an.dossier AS dossier_assemblee, l.source_url
        FROM lois l JOIN leg USING (acte) LEFT JOIN par_loi p USING (acte)
        LEFT JOIN an ON an.numero_loi = l.numero_loi""")
    n = ctx.un("SELECT count(*) FROM loi_dossier_jo")
    reliees = ctx.un("SELECT count(*) FROM loi_dossier_jo WHERE dossier IS NOT NULL")
    comparables = ctx.un("SELECT count(*) FROM loi_dossier_jo WHERE dossier IS NOT NULL AND dossier_assemblee IS NOT NULL")
    accord = ctx.un("SELECT count(*) FROM loi_dossier_jo WHERE dossier IS NOT NULL AND dossier = dossier_assemblee")
    nouvelles = ctx.un("SELECT count(*) FROM loi_dossier_jo WHERE dossier IS NOT NULL AND dossier_assemblee IS NULL")
    return {"loi_reliee_a_un_dossier": (reliees, n), "accord_avec_l_assemblee": (accord, comparables),
            "loi_reliee_sans_promulgation_a_l_assemblee": (nouvelles, reliees)}
