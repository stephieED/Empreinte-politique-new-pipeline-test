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
- `dernier_vote_de_l_assemblee_cloture_sous_une_autre_legislature` (version 2, décision du
  25/11/2026, doc. 5, Q65 « Dans la législature du dernier vote de l'Assemblée ») : le Sénat (ou une
  CMP, le Congrès) vote en dernier sous une autre législature ; la loi est de celle du dernier vote
  de l'Assemblée, qui a voté le texte devenu loi (lois 2022-1053 et 2022-1055 : Assemblée en
  janvier et février 2022, XVe, Sénat le 19/07/2022). Les deux législatures sont servies
  (`legislature_dernier_vote_an`, `legislature_cloture`) ; 21 lois sur la g24 ;
- `dernier_vote_enregistre_de_l_assemblee_seance_posterieure` (version 2, Q66, option 2) :
  l'Assemblée a discuté le texte en séance sous une législature postérieure à son dernier vote lu,
  sans décision de l'Assemblée publiée (texte de CMP dont la décision n'a pas de chambre :
  2024-1039, 2025-175, 2025-541) ; la législature est celle du dernier vote enregistré (XVIe),
  comme pour Q65 ;
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
- `dossier_anterieur_a_la_xive_hors_perimetre` (version 2, Q67 : « La législature XIII est hors
  scope ») : aucun dossier, et la dernière adoption à l'Assemblée que citent les travaux
  préparatoires de la loi au JO (« Discussion et adoption le 3 octobre 2011 »,
  `date_adoption_an_lue_au_jo`) précède le début de la XIVe, première législature du périmètre :
  la loi n'est d'aucune législature publiée, et ne rend pas un compte partiel (16 lois sur la g24,
  dont 2012-1166, 2014-1392) ;
- `loi_sans_dossier` : aucun dossier, et pas de dernière adoption à l'Assemblée lue au JO avant la
  XIVe (la raison de R-LOI-DOSSIER est dans `raison_lien` ; 43 lois sur la g24, dont la date lue
  au JO tombe sous la XIVe ou la XVe) ;
- `suite_absente_des_archives` : la suite du dossier manque, et les bornes tombent dans deux
  législatures (2018-527, 2020-839) ;
- `aucune_adoption_de_l_assemblee_lue` : aucune décision d'adoption de l'Assemblée avant la
  promulgation ;

Version 1 (PR #182) : les cas de Q65 et Q66 n'avaient pas de législature (raisons
`cloture_hors_assemblee_sous_une_autre_legislature` et
`seance_de_l_assemblee_apres_son_dernier_vote_lu`), en attendant la décision.

Une loi peut avoir deux dossiers (même texte renuméroté d'une archive à l'autre : 2017-1338,
DLR5L14N35824 et DLR5L15N35824) : leurs décisions sont lues ensemble."""

from ..perimetre import LEGISLATURES
from .r_etape import adoptions_definitives, date_ref, decisions, legislature_acte
from .r_lois import legislature_a

NOM = "R-LOI-ADOPTION"
VERSION = 2
DEPEND = ("R-LEGISLATURES", "R-LOIS", "R-LOI-DOSSIER", "R-ETAPE")
SORTIES = ("loi_adoption",)
DESCRIPTION = (
    "Une loi est aussi comptée dans la législature où l'Assemblée l'a adoptée en dernier, à côté de "
    "la législature de sa promulgation. C'est la date de la dernière décision enregistrée de "
    "l'Assemblée qui adopte le texte avant la promulgation, même quand le Sénat vote en dernier, "
    "sous la même législature ou la suivante. Une loi adoptée par l'Assemblée avant la XIVe "
    "législature est hors du périmètre. Une loi dont le dossier manque aux archives n'a de législature "
    "d'adoption que si la fin de l'archive et la promulgation tombent dans la même ; sinon, la "
    "raison est dite.")

# Preuves d'une législature d'adoption établie (version 2 : Q65 et Q66, décisions du 25/11/2026).
PREUVES = ("vote_final_de_l_assemblee", "cloture_hors_assemblee_meme_legislature",
           "dernier_vote_de_l_assemblee_cloture_sous_une_autre_legislature",
           "dernier_vote_enregistre_de_l_assemblee_seance_posterieure", "encadree_par_la_promulgation")
# Raison d'une loi adoptée par l'Assemblée avant le périmètre (Q67, 25/11/2026) : jamais comptée
# dans une législature publiée, elle ne rend pas un compte partiel.
HORS_PERIMETRE = "dossier_anterieur_a_la_xive_hors_perimetre"
MOIS = ("janvier", "fevrier", "mars", "avril", "mai", "juin", "juillet", "aout", "septembre",
        "octobre", "novembre", "decembre")

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
        -- Version 2 (Q67) : pour une loi sans dossier, la date de sa dernière adoption à l'Assemblée,
        -- lue dans ses travaux préparatoires au JO (« Discussion et adoption le 3 octobre 2011 »).
        adoption_jo AS ({_adoptions_an_au_jo(ctx)}),
        debut_perimetre AS (SELECT min(debut) AS d FROM legislature WHERE numero = {min(LEGISLATURES)}),
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
                   aj.date AS date_adoption_an_lue_au_jo,
                   CASE WHEN l.dossiers IS NULL AND aj.date < (SELECT d FROM debut_perimetre)
                             THEN '{HORS_PERIMETRE}'
                        WHEN l.dossiers IS NULL THEN 'loi_sans_dossier'
                        -- Suite absente : le dernier vote de l'Assemblée est le dernier lu, ou tombe
                        -- entre la fin de l'archive et la promulgation.
                        WHEN i.numero_loi IS NOT NULL THEN
                             CASE WHEN {legislature_a('i.fin_archive')} = l.legislature_promulgation
                                       AND (v.legislature IS NULL OR v.legislature = l.legislature_promulgation)
                                  THEN 'encadree_par_la_promulgation'
                                  ELSE 'suite_absente_des_archives' END
                        WHEN v.acte IS NULL THEN 'aucune_adoption_de_l_assemblee_lue'
                        -- Q66 (option 2) : séance postérieure sans décision publiée : le dernier vote
                        -- enregistré de l'Assemblée fait foi, comme pour Q65.
                        WHEN s.legislature > v.legislature THEN 'dernier_vote_enregistre_de_l_assemblee_seance_posterieure'
                        WHEN c.chambre = 'AN' THEN 'vote_final_de_l_assemblee'
                        WHEN c.legislature = v.legislature THEN 'cloture_hors_assemblee_meme_legislature'
                        -- Q65 (option 1) : le Sénat clôt sous une autre législature ; la loi est de
                        -- celle du dernier vote de l'Assemblée.
                        ELSE 'dernier_vote_de_l_assemblee_cloture_sous_une_autre_legislature' END AS etat
            FROM lois l
            LEFT JOIN vote_an v USING (numero_loi)
            LEFT JOIN cloture c USING (numero_loi)
            LEFT JOIN motif m ON m.acte = c.acte
            LEFT JOIN incomplet i USING (numero_loi)
            LEFT JOIN seance_an s USING (numero_loi)
            LEFT JOIN adoption_jo aj USING (numero_loi))
        SELECT numero_loi, dossier, dossiers, lien_dossier, raison_lien, date_promulgation,
               legislature_promulgation,
               CASE WHEN etat = 'encadree_par_la_promulgation' THEN legislature_promulgation
                    WHEN etat IN {PREUVES} THEN legislature_dernier_vote_an
               END AS legislature_adoption,
               CASE WHEN etat IN {PREUVES} THEN etat END AS preuve_adoption,
               CASE WHEN etat NOT IN {PREUVES} THEN etat END AS raison_adoption,
               date_dernier_vote_an, acte_dernier_vote_an, lecture_dernier_vote_an,
               legislature_dernier_vote_an, date_cloture, acte_cloture, chambre_cloture, code_cloture,
               legislature_cloture, motif_cloture, date_derniere_seance_an,
               legislature_derniere_seance_an, fin_archive_du_dossier, date_adoption_an_lue_au_jo, source_url
        FROM x""")
    n = ctx.un("SELECT count(*) FROM loi_adoption")
    etablie = ctx.un("SELECT count(*) FROM loi_adoption WHERE legislature_adoption IS NOT NULL")
    meme = ctx.un("""SELECT count(*) FROM loi_adoption WHERE legislature_adoption IS NOT NULL
                     AND legislature_adoption IS NOT DISTINCT FROM legislature_promulgation""")
    hors = ctx.un(f"SELECT count(*) FROM loi_adoption WHERE raison_adoption = '{HORS_PERIMETRE}'")
    return {"legislature_d_adoption_etablie": (etablie, n),
            "meme_legislature_que_la_promulgation": (meme, etablie),
            "legislature_etablie_ou_hors_perimetre": (etablie + hors, n)}


def _adoptions_an_au_jo(ctx) -> str:
    """SQL (numero_loi, date) : la date la plus récente d'une adoption à l'Assemblée que citent les
    travaux préparatoires d'une loi au JO (lignes de l'Assemblée, « … adoption … le 3 octobre
    2011 »), toutes publications de la loi réunies. Vide sans les tables du JO."""
    if not (ctx.existe("jo_actes__travaux_preparatoires") and ctx.existe("jo_actes__acte_reglementaire")):
        return "SELECT NULL::VARCHAR AS numero_loi, NULL::VARCHAR AS date WHERE false"
    mois = "|".join(MOIS)
    liste = ", ".join(f"'{m}'" for m in MOIS)
    return rf"""
        WITH l AS (
            SELECT r.numero AS numero_loi,
                   regexp_extract(strip_accents(lower(t.ligne)),
                                  'adopt.*? le (1er|\d{{1,2}}) ({mois}) (\d{{4}})', ['j', 'm', 'a']) AS x
            FROM (SELECT DISTINCT uid, numero FROM jo_actes__acte_reglementaire
                  WHERE nature IN ('LOI', 'LOI_ORGANIQUE') AND numero IS NOT NULL) r
            JOIN jo_actes__travaux_preparatoires t ON t.acte = r.uid
            WHERE t.chambre = 'AN')
        SELECT numero_loi, max(x.a || '-' || lpad(CAST(list_position([{liste}], x.m) AS VARCHAR), 2, '0')
                                || '-' || lpad(replace(x.j, '1er', '1'), 2, '0')) AS date
        FROM l WHERE x.a <> '' GROUP BY 1"""
