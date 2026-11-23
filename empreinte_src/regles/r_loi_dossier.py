"""R-LOI-DOSSIER : le dossier de l'Assemblée d'une loi publiée au Journal officiel, par ses travaux
préparatoires (issue #35, décision Q33 du 13/11/2026 « Dire le trou, puis relier »).

Une loi promulguée sous la législature suivante n'est dans aucune archive de dossiers de
l'Assemblée (R-LOIS ; 17 dossiers de la XIVe, archive arrêtée au 22/03/2018, dont la loi
2018-287), et l'Assemblée ne publie pas de NOR dans ses documents. Le JO publie avec chaque loi
ses travaux préparatoires (lecteur `jo_actes`, table `travaux_preparatoires`) : pour l'Assemblée,
des numéros de documents (« Proposition de loi n° 1817 », « Rapport … n° 2810 », « TA n° 290 »).

Un numéro d'un document de l'Assemblée n'est unique que dans sa législature, que le JO dit
rarement. Sont candidats, dans la législature de la promulgation et dans la précédente, chacune jugée
à part : les documents de l'Assemblée portant ce numéro et du type que nomme la ligne (proposition
→ `PION`, projet → `PRJL`, rapport → `RAPP`, avis → `AVIS` ; texte adopté → `…BTA<numéro>`) ; quand
le JO nomme la législature du numéro (« n° 4348 (quatorzième législature) », version 2, issue #146),
seule celle-là est candidate (loi 2020-839 : sans cela, le n° 967 de la XVe tombait sous la XIVe
sur un autre dossier). Une
législature est retenue si tous ses numéros trouvés mènent au **même** dossier, et au moins deux ;
la loi est reliée si une seule législature est retenue. Sinon : pas de lien, et la raison
(`pas_de_travaux_preparatoires`, `aucun_document`, `un_seul_numero`, `dossiers_differents`,
`deux_legislatures_possibles`).

Exception (décision du 15/11/2026), pour un dossier dont la suite est absente des archives
(`suite_absente_sql`, le même critère que R-SORT-FINAL) : un seul numéro suffit s'il est celui du
texte déposé (proposition ou projet, du type exact), dans la législature de la promulgation, que
l'archive range dans ce dossier, et qu'aucun autre numéro de cette législature ne mène ailleurs
(décision du même jour : un numéro n'est unique que dans sa législature ; `preuve` :
`texte_depose_seul`, sinon `plusieurs_numeros`). Mesuré sur l'archive globale du JO (g14) : 5 lois
de plus (2018-581, 2018-582, 2018-869, 2018-957, 2019-744). Accepter un seul numéro partout serait
faux : la loi 2018-1068 irait au dossier du secret des sources (même numéro, législature précédente).

Une loi est publiée par plusieurs actes du JO (rectificatifs, republications : 490 actes pour 448
lois sous la XIVe) : une ligne par numéro de loi, ses travaux préparatoires réunis, l'acte retenu
étant le premier publié.

Avant 2016, le JO publie les travaux préparatoires d'une loi à la fin du bloc des signataires,
la balise `TP` restant vide : le lecteur `jo_actes` (version 3, issue #146) les y lit. Sur la g20,
987 lois reliées sur 1 221 au lieu de 644, 975 sur 975 en accord avec l'Assemblée.

Contrôle de la méthode : pour les lois que l'Assemblée relie elle-même (acte de promulgation,
R-LOIS), le dossier trouvé doit être le même (couverture `accord_avec_l_assemblee` : 633 sur 633
sur l'archive globale)."""

NOM = "R-LOI-DOSSIER"
VERSION = 2
DEPEND = ("R-LEGISLATURES", "R-LOIS")
SORTIES = ("loi_dossier_jo",)
DESCRIPTION = (
    "Une loi promulguée après la fin de la législature où son texte a été déposé n'est dans aucune "
    "archive de l'Assemblée. Elle est reliée à son dossier par les travaux préparatoires que le "
    "Journal officiel publie avec elle : les numéros des documents de l'Assemblée (proposition ou "
    "projet, rapport, texte adopté), cherchés dans la législature de la promulgation et dans la "
    "précédente. Le lien n'est retenu que si au moins deux numéros mènent au même dossier, et aucun "
    "à un autre ; un seul suffit pour un dossier dont la suite manque aux archives, s'il est celui du "
    "texte déposé sous la législature de la promulgation.")

_TABLES = ("jo_actes__acte_reglementaire", "jo_actes__travaux_preparatoires", "an_dossiers__document")

_VIDE = """
    SELECT NULL::VARCHAR AS acte, NULL::VARCHAR AS numero_loi, NULL::VARCHAR AS date_promulgation,
           NULL::INTEGER AS legislature, NULL::VARCHAR AS dossier, NULL::VARCHAR AS preuve,
           NULL::VARCHAR AS raison, NULL::VARCHAR[] AS documents, NULL::INTEGER AS numeros_trouves,
           NULL::VARCHAR AS dossier_assemblee, NULL::VARCHAR AS source_url WHERE false"""


def suite_absente_sql() -> str:
    """Dossiers dont la suite est absente des archives (issue #35) : publiés par la seule archive
    d'une législature close, avec des actes d'une législature suivante, que l'archive suivante ne
    publie pas. Rend (dossier, fin_archive). Partagé avec R-SORT-FINAL (raison
    `suite_absente_des_archives`)."""
    return r"""
        WITH pts AS (SELECT prov_point, TRY_CAST(regexp_extract(prov_point, 'l(\d+)$', 1) AS INTEGER) AS leg,
                            max(left(date, 10)) AS fin_archive
                     FROM an_dossiers__acte GROUP BY 1),
             par_dossier AS (SELECT dossier, count(DISTINCT prov_point) AS n, any_value(prov_point) AS pt,
                                    max(TRY_CAST(regexp_extract(uid, '^L(\d+)-', 1) AS INTEGER)) AS leg_acte
                             FROM an_dossiers__acte GROUP BY 1)
        SELECT x.dossier, pts.fin_archive FROM par_dossier x JOIN pts ON pts.prov_point = x.pt
        JOIN legislature lg ON lg.numero = pts.leg
        WHERE x.n = 1 AND lg.fin IS NOT NULL AND x.leg_acte > pts.leg"""


def appliquer(ctx):
    if not all(ctx.existe(t) for t in _TABLES):
        ctx.ecrire("loi_dossier_jo", _VIDE)
        return {"loi_reliee_a_un_dossier": (0, 0)}
    suite = suite_absente_sql() if ctx.existe("an_dossiers__acte") else \
        "SELECT NULL::VARCHAR AS dossier WHERE false"
    ctx.ecrire("loi_dossier_jo", rf"""
        WITH actes AS (
            SELECT DISTINCT uid, numero, date_signature, prov_url FROM jo_actes__acte_reglementaire
            WHERE nature IN ('LOI', 'LOI_ORGANIQUE') AND numero IS NOT NULL),
        -- Une ligne par loi : ses actes (rectificatifs, republications) réunis, le premier retenu.
        lois AS (
            SELECT numero AS numero_loi, min(uid) AS acte, min(date_signature) AS date_promulgation,
                   min_by(prov_url, uid) AS source_url
            FROM actes GROUP BY 1),
        leg AS (
            SELECT l.numero_loi, (SELECT max(g.numero) FROM legislature g WHERE g.debut <= l.date_promulgation) AS leg
            FROM lois l),
        tp AS (
            SELECT DISTINCT a.numero AS numero_loi, t.numero, t.numero_ta, t.legislature AS leg_citee,
                   CASE t.nature WHEN 'proposition_de_loi' THEN 'PION' WHEN 'projet_de_loi' THEN 'PRJL'
                                 WHEN 'proposition_de_resolution' THEN 'PNRE' WHEN 'rapport' THEN 'RAPP'
                                 WHEN 'avis' THEN 'AVIS' END AS type_doc
            FROM jo_actes__travaux_preparatoires t JOIN actes a ON a.uid = t.acte
            WHERE t.chambre = 'AN' AND (t.numero IS NOT NULL OR t.numero_ta IS NOT NULL)),
        avec_tp AS (SELECT DISTINCT a.numero AS numero_loi FROM jo_actes__travaux_preparatoires t
                    JOIN actes a ON a.uid = t.acte),
        docs AS (
            SELECT DISTINCT uid, dossier, left(uid, 4) AS type_doc,
                   TRY_CAST(regexp_extract(uid, 'ANR5L(\d+)', 1) AS INTEGER) AS leg,
                   regexp_extract(uid, 'ANR5L\d+(B|BTA|BTC)\d+$', 1) AS genre,
                   TRY_CAST(regexp_extract(uid, 'ANR5L\d+(?:B|BTA|BTC)(\d+)$', 1) AS INTEGER) AS num
            FROM an_dossiers__document WHERE uid LIKE '%ANR5L%' AND dossier IS NOT NULL),
        -- Un numéro de l'Assemblée est unique dans sa législature : chaque législature candidate
        -- (celle de la promulgation, la précédente) est jugée à part ; le type du document doit
        -- être celui que nomme la ligne (proposition → PION, projet → PRJL, rapport → RAPP…) ;
        -- la législature que le JO nomme, s'il en nomme une, est la seule candidate.
        cand AS (
            SELECT tp.numero_loi, d.leg, d.leg = leg.leg AS leg_promulgation, d.type_doc, d.genre,
                   coalesce(tp.numero, 'TA' || tp.numero_ta) AS cle, d.uid, d.dossier
            FROM tp JOIN leg USING (numero_loi)
            JOIN docs d ON d.leg IN (leg.leg, leg.leg - 1) AND (tp.leg_citee IS NULL OR d.leg = tp.leg_citee)
              AND ((tp.numero IS NOT NULL AND d.genre = 'B' AND d.num = TRY_CAST(tp.numero AS INTEGER)
                    AND d.type_doc = tp.type_doc)
                OR (tp.numero IS NULL AND tp.numero_ta IS NOT NULL AND d.genre = 'BTA'
                    AND d.num = TRY_CAST(tp.numero_ta AS INTEGER)))),
        par_leg AS (
            SELECT numero_loi, leg, count(DISTINCT dossier) AS nb_dossiers, count(DISTINCT cle) AS numeros,
                   any_value(dossier) AS dossier, list(DISTINCT uid ORDER BY uid) AS documents
            FROM cand GROUP BY 1, 2),
        nette AS (SELECT * FROM par_leg WHERE nb_dossiers = 1 AND numeros >= 2),
        par_loi AS (
            SELECT p.numero_loi, count(DISTINCT n.dossier) AS nb_dossiers,
                   max(p.numeros) AS numeros_trouves, any_value(n.dossier) AS dossier,
                   max(p.nb_dossiers) AS dossiers_max, any_value(n.documents) AS documents
            FROM par_leg p LEFT JOIN nette n ON n.numero_loi = p.numero_loi AND n.leg = p.leg GROUP BY 1),
        -- Exception (15/11/2026) : dossier dont la suite est absente des archives, un seul numéro,
        -- celui du texte déposé dans la législature de la promulgation, rangé dans ce dossier ; la
        -- contradiction se juge dans cette législature (un numéro n'est unique que dans la sienne).
        seul AS (
            SELECT numero_loi, any_value(dossier) AS dossier, list(DISTINCT uid ORDER BY uid) AS documents
            FROM cand WHERE leg_promulgation GROUP BY 1
            HAVING count(DISTINCT dossier) = 1 AND count(DISTINCT cle) = 1
               AND bool_and(genre = 'B' AND type_doc IN ('PION', 'PRJL'))
               AND any_value(dossier) IN (SELECT dossier FROM ({suite}))),
        an AS (SELECT numero_loi, any_value(dossier) AS dossier FROM loi GROUP BY 1)
        SELECT l.acte, l.numero_loi, l.date_promulgation, leg.leg AS legislature,
               CASE WHEN p.nb_dossiers = 1 THEN p.dossier ELSE s.dossier END AS dossier,
               CASE WHEN p.nb_dossiers = 1 THEN 'plusieurs_numeros'
                    WHEN s.dossier IS NOT NULL THEN 'texte_depose_seul' END AS preuve,
               CASE WHEN p.nb_dossiers = 1 OR s.dossier IS NOT NULL THEN NULL
                    WHEN p.numero_loi IS NULL AND t.numero_loi IS NULL THEN 'pas_de_travaux_preparatoires'
                    WHEN p.numero_loi IS NULL THEN 'aucun_document'
                    WHEN p.nb_dossiers > 1 THEN 'deux_legislatures_possibles'
                    WHEN p.dossiers_max > 1 THEN 'dossiers_differents'
                    WHEN p.nb_dossiers = 0 THEN 'un_seul_numero' END AS raison,
               CASE WHEN p.nb_dossiers = 1 THEN p.documents ELSE s.documents END AS documents,
               p.numeros_trouves, an.dossier AS dossier_assemblee, l.source_url
        FROM lois l JOIN leg USING (numero_loi) LEFT JOIN par_loi p USING (numero_loi)
        LEFT JOIN seul s USING (numero_loi) LEFT JOIN avec_tp t USING (numero_loi)
        LEFT JOIN an USING (numero_loi)""")
    n = ctx.un("SELECT count(*) FROM loi_dossier_jo")
    reliees = ctx.un("SELECT count(*) FROM loi_dossier_jo WHERE dossier IS NOT NULL")
    comparables = ctx.un("SELECT count(*) FROM loi_dossier_jo WHERE dossier IS NOT NULL AND dossier_assemblee IS NOT NULL")
    accord = ctx.un("SELECT count(*) FROM loi_dossier_jo WHERE dossier IS NOT NULL AND dossier = dossier_assemblee")
    nouvelles = ctx.un("SELECT count(*) FROM loi_dossier_jo WHERE dossier IS NOT NULL AND dossier_assemblee IS NULL")
    return {"loi_reliee_a_un_dossier": (reliees, n), "accord_avec_l_assemblee": (accord, comparables),
            "loi_reliee_sans_promulgation_a_l_assemblee": (nouvelles, reliees)}
