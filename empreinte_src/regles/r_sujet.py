"""R-SUJET : le sujet de chaque paragraphe d'un compte rendu, et le dossier qu'il discute
(doc. 1, 1.6 ; cahier 3.1.5 : « un intitulé de créneau n'est pas un sujet »).

Les points d'ordre du jour d'un compte rendu forment une chaîne par paragraphe (niveau 1, 2, 3…,
les suspensions au niveau 99 sont ignorées). Le sujet est :

- sous un **créneau** (point de niveau 1 « Questions au gouvernement », « Questions orales sans
  débat », « Questions au premier ministre », reconnu à ses sous-points de question `QG_1_1`,
  `QOSD_1_1`, `QPM_1_1` ou à son intitulé) : le point de niveau 2, c'est-à-dire la question ;
  un paragraphe du créneau hors de toute question a le statut `creneau_seul` ;
- sinon le point de niveau 1 : le texte discuté, y compris les lois de finances, dont le point
  porte un code propre (`APPEL_PLF_1_20`) ; « (suite) » est ôté de l'intitulé ;
- « Ordre du jour de la prochaine séance » (`FIN_SEAN_1_2`) est un point de procédure : statut
  `procedure`, pas de sujet ;
- un paragraphe hors de tout point, ou dont le point n'a pas d'intitulé : `intitule_non_publie`.

Le dossier d'un sujet de texte se cherche **parmi les seuls dossiers de la séance** : ceux dont un
acte cite la réunion, et ceux que l'agenda cite pour un point de la séance. Une discussion
commune (« Texte A – Texte B ») est découpée en ses parties. Pour chaque partie, un dossier est
retenu si son titre (ou l'objet du point d'agenda qui le cite) **contient** l'intitulé ; sinon si
c'est le seul à partager le plus de mots significatifs avec l'intitulé (au moins la moitié de
ceux de l'intitulé, et deux au moins, les mots étant réduits à leurs cinq premières lettres).
Plusieurs dossiers à égalité : `ambigu`, pas de lien. En dernier recours, quand le compte rendu
ne discute qu'un texte et que la séance ne cite qu'un dossier, ce dossier est retenu. Aucun :
`non_lie`.
Une question au gouvernement n'a pas de dossier : `sans_objet`.
"""

from .r_orateur import norm

NOM = "R-SUJET"
VERSION = 1
DEPEND = ()
SORTIES = ("sujet_intervention",)
DESCRIPTION = (
    "Le sujet d'une prise de parole est le point de l'ordre du jour sous lequel elle est publiée "
    "dans le compte rendu. Un créneau (« Questions au gouvernement ») n'est pas un sujet : le sujet "
    "est alors la question posée, un niveau plus bas. Pour un texte (y compris les lois de "
    "finances), le sujet est son intitulé ; le dossier législatif est cherché parmi les seuls "
    "dossiers de la séance, d'après leur titre. Une prise de parole sans intitulé publié est "
    "comptée sous « intitulé non publié ».")

CODES_QUESTION = ("QG_1_1", "QOSD_1_1", "QPM_1_1")
CODES_PROCEDURE = ("FIN_SEAN_1_2",)
# Mots trop généraux pour départager deux titres.
MOTS_VIDES = ("proposition", "projet", "visant", "relative", "relatif", "portant", "pour", "dans",
              "avec", "suite", "discussion", "lecture", "nouvelle", "adopte", "adoptee", "senat",
              "assemblee", "nationale", "sous", "reserve", "depot", "organique", "resolution",
              "article", "constitution", "titre", "debat", "theme", "loi", "lois", "entre", "leur",
              "leurs", "cette", "certaines", "certains", "diverses", "dispositions")


def _mots(x):
    vides = ", ".join(f"'{m}'" for m in MOTS_VIDES)
    # Mots de 4 lettres au moins, hors mots vides, réduits à leurs 5 premières lettres
    # (« protection » et « protéger » se rejoignent).
    return (f"list_distinct(list_transform(list_filter(string_split({norm(x)}, ' '), "
            f"lambda w: length(w) >= 4 AND w NOT IN ({vides})), lambda w: left(w, 5)))")


def appliquer(ctx):
    """Applique R-SUJET : écrit `sujet_intervention`, le sujet de chaque paragraphe d'un compte
    rendu et le dossier qu'il discute (voir la description du module). Rend la couverture,
    `{nom: (numérateur, dénominateur)}` : `sujet_etabli`, `texte_relie_a_son_dossier`."""
    q = ", ".join(f"'{c}'" for c in CODES_QUESTION)
    proc = ", ".join(f"'{c}'" for c in CODES_PROCEDURE)
    creneau_titre = f"regexp_matches({norm('ch[1].titre')}, '^questions (au gouvernement|orales sans debat|au premier ministre)')"
    ctx.x(f"""CREATE OR REPLACE TEMP TABLE _c_sujet AS
        WITH p AS (
            SELECT compte_rendu, id_syceron, seance, date, prov_url,
                   list_filter(points, lambda x: x.niv IS DISTINCT FROM 99) AS ch
            FROM an_comptes_rendus__intervention),
        cr AS (
            SELECT DISTINCT compte_rendu, ch[1].id_syceron AS pid FROM p
            WHERE len(ch) >= 1 AND ch[1].niv = 1
              AND ((len(ch) >= 2 AND ch[2].code_grammaire IN ({q})) OR {creneau_titre}))
        SELECT p.compte_rendu, p.id_syceron, p.seance, p.date, p.prov_url,
               CASE WHEN len(p.ch) = 0 OR p.ch[1].niv IS DISTINCT FROM 1 THEN 'hors_point'
                    WHEN cr.pid IS NOT NULL THEN
                         CASE WHEN len(p.ch) >= 2 AND p.ch[2].niv = 2 THEN 'question' ELSE 'creneau' END
                    WHEN p.ch[1].code_grammaire IN ({proc}) THEN 'procedure'
                    WHEN p.ch[1].code_grammaire LIKE 'APPEL_PLF%'
                      OR regexp_matches({norm('p.ch[1].titre')}, '^projet de loi de (finances|financement de la securite sociale)')
                         THEN 'loi_de_finances'
                    ELSE 'texte' END AS type_sujet,
               CASE WHEN cr.pid IS NOT NULL THEN p.ch[1].titre END AS creneau,
               CASE WHEN cr.pid IS NOT NULL THEN (CASE WHEN len(p.ch) >= 2 AND p.ch[2].niv = 2 THEN p.ch[2] END)
                    WHEN len(p.ch) >= 1 AND p.ch[1].niv = 1 THEN p.ch[1] END AS point
        FROM p LEFT JOIN cr ON cr.compte_rendu = p.compte_rendu AND cr.pid = p.ch[1].id_syceron""")
    # Lien au dossier, par sujet de texte (une fois par point de compte rendu).
    mots_part, mots_titre, mots_objets = _mots("s.part"), _mots("d.titre"), _mots("c.objets")
    ctx.x(f"""CREATE OR REPLACE TEMP TABLE _c_lien AS
        WITH s AS (
            SELECT DISTINCT compte_rendu, seance, point.id_syceron AS pid,
                   unnest(regexp_split_to_array(point.titre, '\\s*\\n\\s*-\\s*\\n\\s*')) AS part
            FROM _c_sujet WHERE type_sujet IN ('texte', 'loi_de_finances') AND point.titre IS NOT NULL),
        cand AS (
            SELECT seance, dossier, string_agg(objet, ' | ') AS objets FROM (
                SELECT a.reunion AS seance, a.dossier, o.objet
                FROM an_dossiers__acte a LEFT JOIN an_agenda__point_odj o ON o.uid = a.odj
                WHERE a.reunion IS NOT NULL
                UNION ALL
                SELECT reunion, unnest(dossiers), objet FROM an_agenda__point_odj)
            GROUP BY ALL),
        sc AS (
            SELECT s.compte_rendu, s.pid, s.part, c.dossier,
                   {norm('s.part')} <> '' AND (contains({norm('d.titre')}, {norm('s.part')})
                       OR contains({norm('c.objets')}, {norm('s.part')})) AS contient,
                   greatest(len(list_intersect({mots_part}, {mots_titre})),
                            len(list_intersect({mots_part}, {mots_objets}))) AS communs,
                   len({mots_part}) AS nb_mots
            FROM s JOIN cand c ON c.seance = s.seance
            LEFT JOIN an_dossiers__dossier d ON d.uid = c.dossier),
        partie AS (
            SELECT compte_rendu, pid, part,
                   count(*) FILTER (contient) AS n_contient,
                   any_value(dossier) FILTER (contient) AS d_contient,
                   max(communs) AS mx, any_value(nb_mots) AS nb_mots,
                   list(dossier ORDER BY communs DESC) AS ordre,
                   list(communs ORDER BY communs DESC) AS scores
            FROM sc GROUP BY ALL),
        choix AS (
            SELECT *, n_contient = 0 AND (mx >= 2 OR (mx = 1 AND nb_mots = 1)) AND 2 * mx >= nb_mots AS assez
            FROM partie),
        par_partie AS (
            SELECT compte_rendu, pid, part, len(ordre) AS n_cand, ordre[1] AS premier,
                   CASE WHEN n_contient = 1 THEN d_contient
                        WHEN assez AND (len(scores) = 1 OR scores[2] < mx) THEN ordre[1] END AS dossier,
                   CASE WHEN n_contient = 1 THEN 'titre_contenu'
                        WHEN assez AND (len(scores) = 1 OR scores[2] < mx) THEN 'mots_communs' END AS route,
                   n_contient > 1 OR (assez AND len(scores) > 1 AND scores[2] = mx) AS ambigu
            FROM choix),
        par_point AS (
            SELECT compte_rendu, pid, coalesce(list_distinct(list(dossier) FILTER (dossier IS NOT NULL)), []) AS dossiers,
                   string_agg(DISTINCT route, '+') AS route, bool_or(ambigu) AS ambigu,
                   count(*) AS n_parts, max(n_cand) AS n_cand, any_value(premier) AS premier
            FROM par_partie GROUP BY ALL),
        n_textes AS (SELECT compte_rendu, count(DISTINCT pid) AS n FROM s GROUP BY 1)
        -- Dernier recours : la séance ne discute qu'un texte et ne cite qu'un dossier.
        SELECT p.compte_rendu, p.pid,
               CASE WHEN len(p.dossiers) = 0 AND NOT p.ambigu AND p.n_parts = 1 AND p.n_cand = 1 AND t.n = 1
                    THEN [p.premier] ELSE p.dossiers END AS dossiers,
               CASE WHEN len(p.dossiers) = 0 AND NOT p.ambigu AND p.n_parts = 1 AND p.n_cand = 1 AND t.n = 1
                    THEN 'seul_dossier_de_la_seance' ELSE p.route END AS route,
               p.ambigu
        FROM par_point p JOIN n_textes t USING (compte_rendu)""")
    ctx.ecrire("sujet_intervention", f"""
        SELECT s.compte_rendu, s.id_syceron, s.seance, s.date,
               CASE WHEN s.point.titre IS NOT NULL AND s.type_sujet NOT IN ('procedure', 'creneau', 'hors_point')
                    THEN trim(regexp_replace(s.point.titre, '\\s*\\(suite\\)\\s*$', '')) END AS sujet,
               CASE WHEN len(l.dossiers) = 1 THEN l.dossiers[1] END AS dossier,
               CASE WHEN s.type_sujet = 'procedure' THEN 'procedure'
                    WHEN s.type_sujet = 'creneau' THEN 'creneau_seul'
                    WHEN s.point.titre IS NULL THEN 'intitule_non_publie'
                    ELSE 'etabli' END AS statut,
               s.type_sujet, s.creneau, s.point.titre AS sujet_publie, s.point.id_syceron AS point,
               s.point.code_grammaire AS code_point, coalesce(l.dossiers, []) AS dossiers,
               CASE WHEN s.type_sujet NOT IN ('texte', 'loi_de_finances') OR s.point.titre IS NULL THEN 'sans_objet'
                    WHEN len(l.dossiers) = 1 THEN 'lie'
                    WHEN len(l.dossiers) > 1 THEN 'plusieurs_dossiers'
                    WHEN l.ambigu THEN 'ambigu'
                    ELSE 'non_lie' END AS lien_dossier,
               l.route, s.prov_url AS source_url
        FROM _c_sujet s LEFT JOIN _c_lien l ON l.compte_rendu = s.compte_rendu AND l.pid = s.point.id_syceron""")
    ctx.x("DROP TABLE _c_sujet; DROP TABLE _c_lien")
    n = ctx.un("SELECT count(*) FROM sujet_intervention WHERE statut <> 'procedure'")
    etabli = ctx.un("SELECT count(*) FROM sujet_intervention WHERE statut = 'etabli'")
    t = ctx.x("""SELECT count(*) FILTER (lien_dossier IN ('lie', 'plusieurs_dossiers')), count(*)
                 FROM sujet_intervention WHERE type_sujet IN ('texte', 'loi_de_finances') AND statut = 'etabli'""")[0]
    return {"sujet_etabli": (etabli, n), "texte_relie_a_son_dossier": (t[0], t[1])}
