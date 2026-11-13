"""R-QAG : une question posée en séance (question au gouvernement, question orale sans débat) et
les prises de parole qui la posent et lui répondent (doc. 1, 1.5.4 ; cahier 3.1.6 : « une QG ne
cite aucune séance » ; décisions Q38 du 13/11/2026).

La source des questions ne cite pas de séance, et elle publie la question et la réponse d'un seul
bloc HTML, gardé tel quel. Ce bloc est celui du JO des débats : sa date (`date_reponse`) est celle
de **la publication au JO**, d'ordinaire le lendemain de la séance (3 678 questions appariées sur
3 782 à un jour d'écart, mesure locale du 13/11/2026), parfois plus tard (vacances). Son en-tête
(`<p align="CENTER"> TITRE <a name=…>`) donne l'intitulé du débat ; c'est le seul titre publié en
XVe (`analyses` y est vide).

Une question est **appariée** à un point « question » d'un compte rendu (R-SUJET) si :

- la séance a lieu au plus `FENETRE_JOURS` jours avant la date publiée de la question ;
- l'**auteur** de la question, par son identifiant (jamais par son nom), y prend la parole
  (R-ORATEUR, présidence exclue) ;
- l'**intitulé** du point est égal, à la casse, aux accents et à la ponctuation près, à l'en-tête
  du bloc JO ou au premier intitulé d'analyse.

Parmi les points qui répondent, la séance la plus proche de la date publiée est retenue ; une
question coupée en deux points d'un même compte rendu garde les deux. Deux comptes rendus à la même
distance : `ambigu`, pas de lien. Aucun repli sur l'auteur seul (décision Q38 : il désigne un
autre point que l'intitulé dans 1 à 2 % des cas où les deux répondent).

Quand plusieurs questions partagent un point (deux députés interrogent sur le même thème sous un
même intitulé), chacune reçoit les paragraphes qui vont de la première prise de parole de son
auteur à celle de l'auteur suivant ; la première reçoit aussi ceux qui précèdent (la présidence
donne la parole). Une interruption (« Exclamations », apostrophe d'un député, R-ORATEUR) ne
compte ni comme prise de parole de l'auteur ni parmi les intervenants. Le lien pointe sur le
premier paragraphe de l'auteur dans le compte rendu.

Sinon la question reste `non_appariee`, avec sa raison : `sans_date` (aucune date publiée),
`titre_non_publie`, `seance_non_lue` (aucun point de question lu dans la fenêtre : compte rendu
absent ou législature sans comptes rendus), `auteur_sans_parole` (l'auteur ne parle dans aucun
point de question de la fenêtre), `intitule_different`, `ambigu`.
"""
from .r_orateur import norm

NOM = "R-QAG"
VERSION = 1
DEPEND = ("R-SUJET", "R-ORATEUR")
DEPEND_FACULTATIF = ("R-QUALITE",)
SORTIES = ("question_reponse_parole",)
DESCRIPTION = (
    "Une question au gouvernement ou une question orale sans débat est posée en séance, mais les "
    "données des questions ne disent pas laquelle. Le site la relie au compte rendu quand trois "
    "conditions sont réunies : la séance a lieu dans les dix jours qui précèdent la publication "
    "de la question au Journal officiel, l'auteur de la question y prend la parole, et "
    "l'intitulé du débat dans le compte rendu est celui de la question. Sinon, la question reste "
    "sans lien vers sa séance, et la raison est dite. Les prises de parole reliées sont celles de "
    "l'auteur et de ceux qui lui répondent.")

FENETRE_JOURS = 10
TYPES = {"QG": "au_gouvernement", "QOSD": "orale_sans_debat"}
# Date publiée : ISO, ou JJ/MM/AAAA (XVe, lecteur an_questions au 13/11/2026).
DATE = "coalesce(try_strptime({x}, '%Y-%m-%d'), try_strptime({x}, '%d/%m/%Y'))::DATE"
# En-tête du bloc JO, sans balises ni entités.
ENTETE = ("nullif(trim(regexp_replace(regexp_extract(q.texte_reponse, "
          "'<p align=\"CENTER\">(.*?)(<a name|</p>)', 1), '<[^>]*>|&[a-z#0-9]+;', ' ', 'g')), '')")


def appliquer(ctx):
    """Applique R-QAG : écrit `question_reponse_parole`, une ligne par question au gouvernement ou
    orale sans débat (voir la description du module). Rend la couverture, `{nom: (numérateur,
    dénominateur)}` : `question_appariee` (sur les questions datées et titrées dont la fenêtre
    contient au moins un compte rendu lu), `question_appariee_toutes`, et une ligne par type."""
    types = ", ".join(f"'{k}'" for k in TYPES)
    cas = " ".join(f"WHEN '{k}' THEN '{v}'" for k, v in TYPES.items())
    date = DATE.format(x="q.date_reponse")
    # 1. Questions (une ligne par uid ; la source en publie parfois deux copies identiques).
    ctx.x(f"""CREATE OR REPLACE TEMP TABLE _q_question AS
        SELECT q.uid AS question, CASE q.type {cas} END AS type, q.type AS type_code,
               q.legislature, q.auteur AS acteur, {date} AS date_jo,
               coalesce({ENTETE}, q.analyses[1]) AS titre_jo,
               {norm(ENTETE)} AS t_entete, {norm('q.analyses[1]')} AS t_analyse
        FROM an_questions__question q
        WHERE q.type IN ({types})
        QUALIFY row_number() OVER (PARTITION BY q.uid ORDER BY q.prov_version DESC NULLS LAST) = 1""")
    # 2. Points de question des comptes rendus, avec leurs orateurs (présidence exclue).
    ctx.x(f"""CREATE OR REPLACE TEMP TABLE _q_point AS
        SELECT s.compte_rendu, s.point, any_value(s.seance) AS seance,
               any_value(left(s.date, 10))::DATE AS date_seance, any_value(s.sujet_publie) AS sujet_publie,
               {norm('any_value(s.sujet_publie)')} AS t_point,
               list(DISTINCT a.acteur) FILTER (a.acteur IS NOT NULL AND NOT coalesce(a.preside, false)
                                          AND NOT coalesce(a.interruption, false)) AS orateurs
        FROM sujet_intervention s
        LEFT JOIN intervention_attribuee a USING (compte_rendu, id_syceron)
        WHERE s.type_sujet = 'question' AND s.point IS NOT NULL AND s.date IS NOT NULL
        GROUP BY s.compte_rendu, s.point""")
    # 3. Candidats dans la fenêtre ; retenus : auteur ET intitulé, à la séance la plus proche.
    ctx.x(f"""CREATE OR REPLACE TEMP TABLE _q_cand AS
        SELECT q.question, p.compte_rendu, p.point, p.date_seance, q.date_jo - p.date_seance AS ecart,
               list_contains(p.orateurs, q.acteur) AS auteur_parle,
               p.t_point <> '' AND p.t_point IN (q.t_entete, q.t_analyse) AS titre_egal
        FROM _q_question q
        JOIN _q_point p ON p.date_seance BETWEEN q.date_jo - {FENETRE_JOURS} AND q.date_jo""")
    ctx.x("""CREATE OR REPLACE TEMP TABLE _q_retenu AS
        WITH ok AS (
            SELECT * FROM _q_cand WHERE auteur_parle AND titre_egal
            QUALIFY ecart = min(ecart) OVER (PARTITION BY question))
        SELECT question, count(DISTINCT compte_rendu) AS n_cr, any_value(compte_rendu) AS compte_rendu,
               list(DISTINCT point ORDER BY point) AS points
        FROM ok GROUP BY question""")
    # 4. Paragraphes de chaque question appariée (découpage d'un point partagé).
    ctx.x("""CREATE OR REPLACE TEMP TABLE _q_par AS
        WITH app AS (SELECT question, compte_rendu, unnest(points) AS point FROM _q_retenu WHERE n_cr = 1),
        par AS (
            SELECT s.compte_rendu, s.point, s.id_syceron, i.ordre_absolu_seance AS ordre,
                   a.acteur, coalesce(a.preside, false) AS preside,
                   coalesce(a.interruption, false) AS interruption, s.source_url
            FROM sujet_intervention s
            JOIN (SELECT DISTINCT compte_rendu, point FROM app) u USING (compte_rendu, point)
            LEFT JOIN an_comptes_rendus__intervention i USING (compte_rendu, id_syceron)
            LEFT JOIN intervention_attribuee a USING (compte_rendu, id_syceron)),
        debut AS (
            SELECT app.question, app.compte_rendu, app.point, min(par.ordre) AS debut
            FROM app JOIN _q_question q USING (question)
            JOIN par ON par.compte_rendu = app.compte_rendu AND par.point = app.point AND par.acteur = q.acteur
                    AND NOT par.interruption
            GROUP BY ALL),
        borne AS (
            SELECT *, lead(debut) OVER (PARTITION BY compte_rendu, point ORDER BY debut, question) AS fin,
                      row_number() OVER (PARTITION BY compte_rendu, point ORDER BY debut, question) AS rang
            FROM debut)
        SELECT b.question, par.*
        FROM borne b JOIN par ON par.compte_rendu = b.compte_rendu AND par.point = b.point
        WHERE (b.rang = 1 OR par.ordre >= b.debut) AND (b.fin IS NULL OR par.ordre < b.fin)""")
    qualite = ("LEFT JOIN qualite_orateur o ON o.compte_rendu = p.compte_rendu AND o.id_syceron = p.id_syceron"
               if ctx.existe("qualite_orateur") else "")
    q_col = "o.qualite" if qualite else "NULL::VARCHAR"
    ctx.ecrire("question_reponse_parole", f"""
        WITH par AS (
            SELECT p.question,
                   list(p.id_syceron ORDER BY p.ordre, p.id_syceron) AS interventions,
                   list(DISTINCT {{'acteur': p.acteur, 'qualite': {q_col}}})
                       FILTER (p.acteur IS NOT NULL AND NOT p.preside AND NOT p.interruption
                               AND p.acteur <> q.acteur) AS intervenants,
                   arg_min(p.source_url, p.ordre) FILTER (p.acteur = q.acteur AND NOT p.interruption) AS lien
            FROM _q_par p JOIN _q_question q USING (question) {qualite}
            GROUP BY p.question),
        fen AS (
            SELECT question, bool_or(auteur_parle) AS auteur, count(*) AS n FROM _q_cand GROUP BY question)
        SELECT q.question, q.type, q.type_code, q.legislature, q.acteur, strftime(q.date_jo, '%Y-%m-%d') AS date_jo,
               q.titre_jo,
               CASE WHEN r.n_cr = 1 THEN 'appariee' ELSE 'non_appariee' END AS statut,
               CASE WHEN r.n_cr = 1 THEN NULL
                    WHEN q.date_jo IS NULL THEN 'sans_date'
                    WHEN coalesce(q.t_entete, '') = '' AND coalesce(q.t_analyse, '') = '' THEN 'titre_non_publie'
                    WHEN r.n_cr > 1 THEN 'ambigu'
                    WHEN f.n IS NULL THEN 'seance_non_lue'
                    WHEN NOT f.auteur THEN 'auteur_sans_parole'
                    ELSE 'intitule_different' END AS raison,
               CASE WHEN r.n_cr = 1 THEN r.compte_rendu END AS compte_rendu,
               CASE WHEN r.n_cr = 1 THEN pt.seance END AS seance,
               CASE WHEN r.n_cr = 1 THEN strftime(pt.date_seance, '%Y-%m-%d') END AS date_seance,
               CASE WHEN r.n_cr = 1 THEN r.points END AS points,
               CASE WHEN r.n_cr = 1 THEN pt.sujet_publie END AS sujet_publie,
               par.interventions, par.intervenants,
               par.lien AS source_url
        FROM _q_question q
        LEFT JOIN _q_retenu r USING (question)
        LEFT JOIN _q_point pt ON pt.compte_rendu = r.compte_rendu AND pt.point = r.points[1]
        LEFT JOIN par USING (question)
        LEFT JOIN fen f USING (question)
        ORDER BY q.question""")
    ctx.x("DROP TABLE _q_question; DROP TABLE _q_point; DROP TABLE _q_cand; DROP TABLE _q_retenu; DROP TABLE _q_par")
    t = ctx.x("""SELECT count(*) FILTER (statut = 'appariee'), count(*),
                        count(*) FILTER (raison IS NULL OR raison IN ('auteur_sans_parole', 'intitule_different', 'ambigu'))
                 FROM question_reponse_parole""")[0]
    couv = {"question_appariee": (t[0], t[2]), "question_appariee_toutes": (t[0], t[1])}
    for code, nom in TYPES.items():
        r = ctx.x(f"""SELECT count(*) FILTER (statut = 'appariee'), count(*) FROM question_reponse_parole
                      WHERE type_code = '{code}'""")[0]
        couv[f"appariee_{nom}"] = (r[0], r[1])
    return couv
