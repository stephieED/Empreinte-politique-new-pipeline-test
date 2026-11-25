"""R-49-3 : les engagements de responsabilité du gouvernement sur un texte (article 49, alinéa 3 ;
doc. 1, 1.6 ; mesures `an-scrutins-dossiers.md`, 4.3).

Un engagement est un acte `DeclarationGouvernement_Type` dont `typeDeclaration.fam_code` vaut
`Art.49.3` ; jamais lu dans la conclusion d'une décision (5 fois seulement en XVIIe), jamais un
scrutin (aucun `voteRefs` sur ces actes) : c'est un fait de procédure, pas une position de vote
(cahier, partie 2, règle 4). Il est rattaché au gouvernement en fonction à sa date.

Un même acte figure dans deux dossiers (le texte, et le dossier « Engagement de la
responsabilité du Gouvernement », procédure 13) : une ligne par (dossier, acte), avec
`procedure_code` pour les distinguer. Le nombre d'engagements distincts est celui des actes.

Version 2 (issue #89, 25/11/2026) : `censure_49_3`, les motions de censure mises aux voix après un
engagement. Une motion est la décision `DecisionMotionCensure_Type` du dossier ; son issue se lit
dans son code de décision (`TSORTMOT01` « Motion adoptée », `TSORTMOT02` « Motion rejetée »),
jamais dans son libellé, et son scrutin dans les scrutins de l'acte. Elle est rattachée à
l'engagement le plus récent du même dossier, au plus tard le jour du vote, dans la même lecture
(préfixe du code : `CMP-MOTION-VOTE` → `CMP`) ; une motion dont le code ne nomme pas la lecture
(`MOTION-VOTE`, 6 décisions de la XVIe) est rattachée au plus récent engagement du dossier. Une
motion sans engagement avant elle dans le dossier n'est pas une censure après 49.3 (article 49,
alinéa 2) : elle n'est pas écrite. Une motion **adoptée** rejette le texte engagé : c'est le
« rejet via 49.3 » (cas réel : PLFSS 2025, DLR5L17N50588, gouvernement Barnier, engagement du
02/12/2024 sur le texte de CMP, motion adoptée le 04/12/2024, scrutin VTANR5L17V519 ; la navette a
repris et la loi 2025-199 a été promulguée le 28/02/2025)."""

from .r_lois import gouvernement_a

NOM = "R-49-3"
VERSION = 2
DEPEND = ("R-GOUVERNEMENTS",)
SORTIES = ("engagement_49_3", "censure_49_3")
DESCRIPTION = (
    "Un recours à l'article 49, alinéa 3, de la Constitution est lu dans l'acte du dossier "
    "législatif où le gouvernement engage sa responsabilité sur le texte. Ce n'est pas un vote : "
    "c'est un fait de procédure, présenté comme tel. Il est rattaché au gouvernement en fonction "
    "à sa date. Une motion de censure adoptée après l'engagement rejette le texte : elle est "
    "rattachée à l'engagement, avec son scrutin.")


def appliquer(ctx):
    """Applique R-49-3 : écrit `engagement_49_3`, les engagements de responsabilité du gouvernement
    sur un texte, avec le gouvernement qui les a pris (voir la description du module). Rend la
    couverture, `{nom: (numérateur, dénominateur)}` : `gouvernement_etabli`."""
    ctx.ecrire("engagement_49_3", f"""
        SELECT a.dossier, left(a.date, 10) AS date, {gouvernement_a('left(a.date, 10)')} AS gouvernement,
               a.uid AS acte, split_part(a.code, '-', 1) AS etape, a.texte_associe AS declaration,
               d.procedure_code, d.procedure_libelle, d.titre AS titre_dossier,
               a.prov_url AS source_url
        FROM an_dossiers__acte a JOIN an_dossiers__dossier d ON d.uid = a.dossier
        WHERE a.type_acte = 'DeclarationGouvernement_Type' AND a.type_declaration_code = 'Art.49.3'""")
    ctx.ecrire("censure_49_3", """
        WITH m AS (
            SELECT a.dossier, a.uid AS acte_motion, left(a.date, 10) AS date_motion,
                   split_part(a.code, '-', 1) AS lecture, a.decision_code,
                   CASE a.decision_code WHEN 'TSORTMOT01' THEN 'adoptee' WHEN 'TSORTMOT02' THEN 'rejetee'
                   END AS issue, a.scrutins, a.prov_url
            FROM an_dossiers__acte a WHERE a.type_acte = 'DecisionMotionCensure_Type' AND a.date IS NOT NULL)
        SELECT m.dossier, e.procedure_code, e.acte AS acte_engagement, e.date AS date_engagement,
               e.etape AS lecture, e.gouvernement, m.acte_motion, m.date_motion, m.decision_code, m.issue,
               m.scrutins[1] AS scrutin, m.scrutins,
               date_diff('day', CAST(e.date AS DATE), CAST(m.date_motion AS DATE)) AS jours_apres_engagement,
               m.prov_url AS source_url
        FROM m JOIN engagement_49_3 e ON e.dossier = m.dossier AND e.date <= m.date_motion
              AND (e.etape = m.lecture OR m.lecture = 'MOTION')
        QUALIFY row_number() OVER (PARTITION BY m.dossier, m.acte_motion ORDER BY e.date DESC, e.acte DESC) = 1""")
    n = ctx.un("SELECT count(*) FROM engagement_49_3")
    gouv = ctx.un("SELECT count(*) FROM engagement_49_3 WHERE gouvernement IS NOT NULL")
    motions = ctx.un("SELECT count(*) FROM censure_49_3")
    issue = ctx.un("SELECT count(*) FROM censure_49_3 WHERE issue IS NOT NULL")
    return {"gouvernement_etabli": (gouv, n), "issue_de_la_motion_lue": (issue, motions)}
