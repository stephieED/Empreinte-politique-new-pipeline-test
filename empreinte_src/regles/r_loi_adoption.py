"""R-LOI-ADOPTION : la législature où l'Assemblée a adopté une loi pour la dernière fois (issue #83 ;
cahier 3.1.4, « les lois de la législature »).

R-LOIS compte une loi dans la législature de sa **promulgation**. L'interface veut aussi compter
les lois « votées définitivement par l'Assemblée de cette législature, puis promulguées » : une
loi adoptée en mai 2017 et promulguée en septembre 2017 est une loi de la XIVe à ce compte, de la
XVe à l'autre. Les deux comptes sont servis côte à côte ; R-LOIS ne change pas.

Les lois comptées : celles de R-LOIS (acte de promulgation de l'Assemblée), et celles du Journal
officiel que l'Assemblée ne publie pas (R-LOI-DOSSIER, `dossier_assemblee` vide), promulguées
depuis le début de la plus ancienne législature dont les dossiers sont lus (une loi promulguée
avant a forcément été adoptée avant). Le dossier d'une loi est celui de son acte de promulgation,
à défaut celui que donnent ses travaux préparatoires (R-LOI-DOSSIER).

Les décisions lues sont celles de R-ETAPE (`decisions` : conclusion classée, législature d'un acte
par sa date, Q48 et Q54), datées au plus tard du jour de la promulgation :
- **dernier vote de l'Assemblée** : la dernière décision de l'Assemblée qui adopte le texte
  (adoption avec ou sans modification, texte de CMP, lecture définitive, 49.3 « considéré comme
  adopté ») ;
- **clôture** : la dernière décision d'adoption, des deux chambres (ou du Congrès), ou publiée sans
  conclusion (TSORTFnull, Sénat en nouvelle lecture : jamais un vote de l'Assemblée). La promulgation
  prouve que la navette s'est close par une adoption ; la source code parfois « modifié »
  (`TSORTF05`) l'adoption conforme du Sénat qui la clôt (98 lois sur la g24, par exemple 2021-303),
  d'où ce choix plutôt que la seule liste de R-ETAPE (`adoptions_definitives`), dont le motif est
  repris quand elle reconnaît la décision (`motif_cloture`, sinon `derniere_adoption_avant_promulgation`).

La législature d'adoption (`legislature_adoption`), avec sa preuve :
- `vote_final_de_l_assemblee` : la clôture est une décision de l'Assemblée ; sa législature ;
- `cloture_hors_assemblee_meme_legislature` : le Sénat (ou une CMP, le Congrès) vote en dernier,
  dans la législature du dernier vote de l'Assemblée ; cette législature ;
- `encadree_par_la_promulgation` : la loi n'a pas d'acte de promulgation à l'Assemblée (reliée par
  le JO) et l'archive de son dossier s'arrête avant la promulgation (`fin_archive_du_dossier`, date
  du dernier acte passé de cette archive) ; le dernier vote de l'Assemblée est alors le dernier lu,
  ou tombe entre la fin de l'archive et la promulgation. Si la fin de l'archive, la promulgation et
  le dernier vote lu (s'il y en a un) tombent dans la même législature, le vote final aussi (une
  législature ne revient pas). Cas réels : 2018-581, 2018-582, 2018-869, 2018-957, 2019-744 (aucun
  vote de l'Assemblée avant la fin de l'archive de la XIVe, le 22/03/2018 : XVe) et 2018-287.
  La loi 2018-527 montre pourquoi ce critère, et non celui de R-SORT-FINAL : dernier vote lu le
  13/10/2016 (XIVe), promulguée le 28/06/2018 (XVe), son dossier n'a aucun acte numéroté de la XVe.

Sinon, pas de législature, et la raison (`raison_adoption`) :
- `loi_sans_dossier` : aucun dossier (la raison de R-LOI-DOSSIER est dans `raison_lien`) ;
- `suite_absente_des_archives` : la suite du dossier manque, et les bornes tombent dans deux
  législatures (2018-527, 2020-839) ;
- `aucune_adoption_de_l_assemblee_lue` : aucune décision d'adoption de l'Assemblée avant la
  promulgation ;
- `seance_de_l_assemblee_apres_son_dernier_vote_lu` : l'Assemblée a discuté le texte en séance
  sous une législature postérieure à son dernier vote lu, sans décision de l'Assemblée publiée
  (texte de CMP dont la décision n'a pas de chambre : 2024-1039, 2025-175, 2025-541 ; doc. 5, Q66) ;
- `cloture_hors_assemblee_sous_une_autre_legislature` : le Sénat (ou une CMP, le Congrès) vote en
  dernier sous une autre législature que le dernier vote de l'Assemblée (lois 2022-1053 et
  2022-1055 : Assemblée en janvier et février 2022, Sénat le 19/07/2022). Option prudente en
  attendant la décision (doc. 5, Q65) : la loi n'est comptée nulle part par adoption ; les deux
  législatures sont servies (`legislature_dernier_vote_an`, `legislature_cloture`).

Une loi peut avoir deux dossiers (même texte renuméroté d'une archive à l'autre : 2017-1338,
DLR5L14N35824 et DLR5L15N35824) : leurs décisions sont lues ensemble."""

from .r_etape import adoptions_definitives, date_ref, decisions, legislature_acte
from .r_lois import legislature_a

NOM = "R-LOI-ADOPTION"
VERSION = 1
DEPEND = ("R-LEGISLATURES", "R-LOIS", "R-LOI-DOSSIER", "R-ETAPE")
SORTIES = ("loi_adoption",)
DESCRIPTION = (
    "Une loi est aussi comptée dans la législature où l'Assemblée l'a adoptée en dernier, à côté de "
    "la législature de sa promulgation. C'est la date de la dernière décision de l'Assemblée qui "
    "adopte le texte avant la promulgation, quand cette décision clôt la navette. Quand le Sénat "
    "vote en dernier, la loi n'est comptée que si son vote tombe dans la même législature que le "
    "dernier vote de l'Assemblée. Une loi dont le dossier manque aux archives n'a de législature "
    "d'adoption que si la fin de l'archive et la promulgation tombent dans la même ; sinon, la "
    "raison est dite.")

_VIDE_LIEN = ("SELECT NULL::VARCHAR AS numero_loi, NULL::VARCHAR AS dossier, NULL::VARCHAR AS raison, "
              "NULL::VARCHAR AS date_promulgation, NULL::VARCHAR AS dossier_assemblee, "
              "NULL::VARCHAR AS source_url WHERE false")


def appliquer(ctx):
    """Applique R-LOI-ADOPTION : écrit `loi_adoption`, une ligne par loi, avec la législature de son
    dernier vote à l'Assemblée et la preuve, ou la raison qui l'empêche (voir la description du
    module). Rend la couverture, `{nom: (numérateur, dénominateur)}` :
    `legislature_d_adoption_etablie`, `meme_legislature_que_la_promulgation`."""
    jo = "loi_dossier_jo" if ctx.existe("loi_dossier_jo") else f"({_VIDE_LIEN})"
    ctx.ecrire("loi_adoption", f"""
        WITH dec AS ({decisions(ctx)}),
        ad AS ({adoptions_definitives(ctx)}),
        -- Les lois : actes de promulgation de l'Assemblée (R-LOIS), puis lois du JO qu'elle ne
        -- publie pas (R-LOI-DOSSIER), promulguées depuis le début de la plus ancienne législature lue.
        an AS (
            SELECT numero_loi, list(DISTINCT dossier ORDER BY dossier) AS dossiers,
                   min(date_promulgation) AS date_promulgation, any_value(legislature) AS legislature_promulgation,
                   'acte_de_promulgation' AS lien_dossier, NULL::VARCHAR AS raison_lien,
                   min(source_url) AS source_url
            FROM loi WHERE numero_loi IS NOT NULL GROUP BY 1),
        -- Plus ancienne archive de dossiers lue (suffixe `-l<n>` de son point d'accès) ; sans suffixe
        -- reconnu, toutes les lois du JO sont prises.
        debut AS (
            SELECT coalesce(min(g.debut), '0000-01-01') AS d FROM legislature g
            WHERE g.numero = (SELECT min(TRY_CAST(regexp_extract(prov_point, '-l(\\d+)$', 1) AS INTEGER))
                              FROM an_dossiers__acte)),
        jo AS (
            SELECT j.numero_loi, CASE WHEN j.dossier IS NOT NULL THEN [j.dossier] END AS dossiers,
                   j.date_promulgation, {legislature_a('j.date_promulgation')} AS legislature_promulgation,
                   CASE WHEN j.dossier IS NOT NULL THEN 'travaux_preparatoires_jo' END AS lien_dossier,
                   j.raison AS raison_lien, j.source_url
            FROM {jo} j
            WHERE j.dossier_assemblee IS NULL AND j.numero_loi NOT IN (SELECT numero_loi FROM an)
              AND j.date_promulgation >= (SELECT d FROM debut)),
        lois AS (SELECT * FROM an UNION ALL SELECT * FROM jo),
        ld AS (SELECT numero_loi, unnest(dossiers) AS dossier FROM lois WHERE dossiers IS NOT NULL),
        -- Décisions d'adoption de chaque loi, au plus tard le jour de la promulgation ; une décision
        -- publiée sans conclusion (TSORTFnull, Sénat en nouvelle lecture) peut clore la navette, elle
        -- ne compte jamais comme vote de l'Assemblée.
        adop AS (
            SELECT ld.numero_loi, d.* FROM ld JOIN lois l USING (numero_loi)
            JOIN dec d ON d.dossier = ld.dossier
            WHERE d.issue IN ('adopte', 'sans_conclusion') AND d.date <= l.date_promulgation),
        -- La dernière décision, la ligne entière (arg_max sauterait une chambre vide : CMP, Congrès).
        vote_an AS (
            SELECT numero_loi, date, acte, lecture, legislature FROM adop WHERE chambre = 'AN' AND issue = 'adopte'
            QUALIFY row_number() OVER (PARTITION BY numero_loi ORDER BY date DESC, acte DESC) = 1),
        cloture AS (
            SELECT numero_loi, date, acte, chambre, code, legislature FROM adop
            QUALIFY row_number() OVER (PARTITION BY numero_loi ORDER BY date DESC, acte DESC) = 1),
        -- Dernière séance de l'Assemblée sur le texte (discussion en séance publique, CMP comprise).
        seance_an AS (
            SELECT ld.numero_loi, left(a.date, 10) AS date, a.uid AS acte,
                   {legislature_acte(ctx, "a.date", "a.uid")} AS legislature
            FROM ld JOIN lois l USING (numero_loi) JOIN an_dossiers__acte a ON a.dossier = ld.dossier
            WHERE a.type_acte = 'DiscussionSeancePublique_Type'
              AND (a.code LIKE 'AN%' OR a.code LIKE 'CMP-DEBATS-AN%')
              AND left(a.date, 10) <= l.date_promulgation
            QUALIFY row_number() OVER (PARTITION BY ld.numero_loi ORDER BY a.date DESC, a.uid DESC) = 1),
        motif AS (SELECT acte, any_value(motif) AS motif FROM ad GROUP BY 1),
        -- Suite absente des archives : loi sans acte de promulgation à l'Assemblée (reliée par le JO),
        -- dont l'archive du dossier s'arrête avant la promulgation (date de son dernier acte passé).
        fin_point AS (
            SELECT prov_point, max(left(date, 10)) AS fin FROM an_dossiers__acte
            WHERE left(date, 10) <= '{date_ref(ctx)}' GROUP BY 1),
        fin_dossier AS (
            SELECT a.dossier, max(f.fin) AS fin FROM an_dossiers__acte a JOIN fin_point f USING (prov_point)
            GROUP BY 1),
        incomplet AS (
            SELECT ld.numero_loi, max(f.fin) AS fin_archive FROM ld JOIN fin_dossier f USING (dossier)
            JOIN lois l USING (numero_loi)
            WHERE l.lien_dossier = 'travaux_preparatoires_jo' AND f.fin < l.date_promulgation GROUP BY 1),
        x AS (
            SELECT l.*, l.dossiers[1] AS dossier,
                   v.date AS date_dernier_vote_an, v.acte AS acte_dernier_vote_an,
                   v.lecture AS lecture_dernier_vote_an, v.legislature AS legislature_dernier_vote_an,
                   c.date AS date_cloture, c.acte AS acte_cloture, c.chambre AS chambre_cloture,
                   c.code AS code_cloture, c.legislature AS legislature_cloture,
                   CASE WHEN c.acte IS NOT NULL THEN coalesce(m.motif, 'derniere_adoption_avant_promulgation')
                   END AS motif_cloture,
                   i.fin_archive AS fin_archive_du_dossier,
                   s.date AS date_derniere_seance_an, s.legislature AS legislature_derniere_seance_an,
                   CASE WHEN l.dossiers IS NULL THEN 'loi_sans_dossier'
                        -- Suite absente : le dernier vote de l'Assemblée est le dernier lu, ou tombe
                        -- entre la fin de l'archive et la promulgation.
                        WHEN i.numero_loi IS NOT NULL THEN
                             CASE WHEN {legislature_a('i.fin_archive')} = l.legislature_promulgation
                                       AND (v.legislature IS NULL OR v.legislature = l.legislature_promulgation)
                                  THEN 'encadree_par_la_promulgation'
                                  ELSE 'suite_absente_des_archives' END
                        WHEN v.acte IS NULL THEN 'aucune_adoption_de_l_assemblee_lue'
                        WHEN s.legislature > v.legislature THEN 'seance_de_l_assemblee_apres_son_dernier_vote_lu'
                        WHEN c.chambre = 'AN' THEN 'vote_final_de_l_assemblee'
                        WHEN c.legislature = v.legislature THEN 'cloture_hors_assemblee_meme_legislature'
                        ELSE 'cloture_hors_assemblee_sous_une_autre_legislature' END AS etat
            FROM lois l
            LEFT JOIN vote_an v USING (numero_loi)
            LEFT JOIN cloture c USING (numero_loi)
            LEFT JOIN motif m ON m.acte = c.acte
            LEFT JOIN incomplet i USING (numero_loi)
            LEFT JOIN seance_an s USING (numero_loi))
        SELECT numero_loi, dossier, dossiers, lien_dossier, raison_lien, date_promulgation,
               legislature_promulgation,
               CASE WHEN etat IN ('vote_final_de_l_assemblee', 'cloture_hors_assemblee_meme_legislature')
                         THEN legislature_dernier_vote_an
                    WHEN etat = 'encadree_par_la_promulgation' THEN legislature_promulgation
               END AS legislature_adoption,
               CASE WHEN etat IN ('vote_final_de_l_assemblee', 'cloture_hors_assemblee_meme_legislature',
                                  'encadree_par_la_promulgation') THEN etat END AS preuve_adoption,
               CASE WHEN etat NOT IN ('vote_final_de_l_assemblee', 'cloture_hors_assemblee_meme_legislature',
                                      'encadree_par_la_promulgation') THEN etat END AS raison_adoption,
               date_dernier_vote_an, acte_dernier_vote_an, lecture_dernier_vote_an,
               legislature_dernier_vote_an, date_cloture, acte_cloture, chambre_cloture, code_cloture,
               legislature_cloture, motif_cloture, date_derniere_seance_an,
               legislature_derniere_seance_an, fin_archive_du_dossier, source_url
        FROM x""")
    n = ctx.un("SELECT count(*) FROM loi_adoption")
    etablie = ctx.un("SELECT count(*) FROM loi_adoption WHERE legislature_adoption IS NOT NULL")
    meme = ctx.un("""SELECT count(*) FROM loi_adoption WHERE legislature_adoption IS NOT NULL
                     AND legislature_adoption IS NOT DISTINCT FROM legislature_promulgation""")
    return {"legislature_d_adoption_etablie": (etablie, n),
            "meme_legislature_que_la_promulgation": (meme, etablie)}
