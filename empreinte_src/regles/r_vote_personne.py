"""R-VOTE-PERSONNE : ce que chaque député a voté, une position par texte (doc. 1, 1.5.3 et 1.6,
R-NOMINATIF ; cahier 2, règle 4, 3.1.2, 4.2 « Ce que cette personne a voté » et 4.6).

Une ligne par (acteur, scrutin), calculée pour tous les votants nommés ; la fiche filtre.

- **Textes** (`nature = 'ensemble'`) : pour chaque dossier, le seul scrutin retenu est sa
  **dernière lecture** (R-DERNIERE-LECTURE : le vote sur l'ensemble le plus récent, choisi sur
  tout le corpus, jamais parmi les seuls votes de la personne). La position est celle que la
  source **nomme** pour la personne à ce scrutin (pour, contre, abstention, ou non-votant avec sa
  cause : président de séance, membre du gouvernement…). Une personne que la liste ne nomme pas
  n'a pas de ligne : sa position n'est jamais déduite (ni de son groupe, ni d'une absence). La
  mise au point (« a voulu voter… ») est servie à part ; elle ne remplace pas le vote enregistré.
- **Motions de censure** (`nature = 'motion_censure'`) : à part, jamais comptées parmi les
  positions sur un texte (`derniere_lecture = false`).
- **49.3** : un engagement de responsabilité n'est **jamais** une position de vote (cahier 2,
  règle 4) ; il n'a pas de ligne ici. Le dossier qui l'a subi est signalé (`par_49_3`).

Chaque position porte : la matière (commission saisie au fond, R-MATIERE), l'origine du texte
(projet ou proposition, R-ORIGINE), le sort final du dossier (R-SORT-FINAL), le groupe de la
personne **à la date** (R-APPARTENANCE : jamais l'organe que porte le scrutin, gardé à part dans
`groupe_scrutin`), le gouvernement et la période (R-PERIODE)."""

NOM = "R-VOTE-PERSONNE"
VERSION = 1
DEPEND = ("R-DERNIERE-LECTURE", "R-ORIGINE", "R-LIEN-SCRUTIN-DOSSIER", "R-MATIERE",
          "R-SORT-FINAL", "R-APPARTENANCE", "R-PERIODE")
SORTIES = ("vote_personne",)
DESCRIPTION = (
    "Pour chaque texte, la position retenue est celle du vote le plus récent sur l'ensemble du "
    "texte, choisi parmi tous les scrutins publiés sur ce texte (la dernière lecture). La position "
    "d'une personne est celle que l'Assemblée publie en la nommant ; une personne que la liste ne "
    "nomme pas n'a pas de position, qui n'est jamais déduite de celle de son groupe. Les motions "
    "de censure sont présentées à part. Un recours à l'article 49, alinéa 3, n'est jamais une "
    "position de vote : le texte qui l'a subi est seulement signalé. Chaque position est classée "
    "par matière (commission saisie au fond), origine du texte (projet du gouvernement ou "
    "proposition) et sort final du dossier, et rattachée au groupe de la personne à la date du "
    "vote, au gouvernement en fonction et à sa période.")

FIN_OUVERTE = "'9999-12-31'"


def appliquer(ctx):
    ctx.ecrire("vote_personne", f"""
        WITH retenus AS (
            SELECT d.scrutin, d.dossier, 'ensemble' AS nature, true AS derniere_lecture, NULL::VARCHAR[] AS dossiers
            FROM derniere_lecture d
            UNION ALL
            SELECT s.scrutin,
                   CASE WHEN count(l.dossier) = 1 THEN any_value(l.dossier) END,
                   'motion_censure', false, list(l.dossier ORDER BY l.dossier) FILTER (l.dossier IS NOT NULL)
            FROM scrutin_classe s LEFT JOIN lien_scrutin_dossier l USING (scrutin)
            WHERE s.nature = 'motion_censure' GROUP BY s.scrutin),
        pos AS (
            SELECT r.*, p.acteur, p.position, p.cause, p.par_delegation, p.groupe AS groupe_scrutin,
                   p.mandat, p.num_place
            FROM retenus r JOIN an_scrutins__position_vote p USING (scrutin)
            WHERE p.acteur IS NOT NULL),
        map AS (   -- mise au point : la position que la personne déclare avoir voulu exprimer
            SELECT scrutin, acteur, arg_max(position, element) AS position, bool_or(dysfonctionnement) AS dysf
            FROM an_scrutins__mise_au_point GROUP BY 1, 2),
        so AS (SELECT dossier, any_value(sort) AS sort, bool_or(par_49_3) AS par_49_3,
                      any_value(titre) AS titre FROM etat_dossier GROUP BY 1),
        x AS (
            SELECT p.*, s.date, s.numero, s.lecture, s.origine, s.raison_origine, s.type_texte,
                   s.solennel, s.titre AS intitule, s.source_url
            FROM pos p JOIN scrutin_classe s USING (scrutin)),
        grp AS (
            SELECT x.scrutin, x.acteur, a.groupe
            FROM x JOIN appartenance a ON a.acteur = x.acteur AND a.debut <= x.date
                                      AND coalesce(a.fin, {FIN_OUVERTE}) >= x.date
            QUALIFY row_number() OVER (PARTITION BY x.scrutin, x.acteur ORDER BY a.debut DESC) = 1),
        per AS (
            SELECT x.scrutin, x.acteur, p.periode, p.banc, p.gouvernement
            FROM x JOIN periode_position p ON p.acteur = x.acteur AND p.debut <= x.date
                                         AND coalesce(p.fin, {FIN_OUVERTE}) >= x.date)
        SELECT x.acteur, x.scrutin, x.dossier, x.date, x.position, x.nature, x.derniere_lecture,
               m.commission AS matiere, coalesce(m.statut, 'non_etablie') AS matiere_statut,
               coalesce(m.libelle, 'Matière non établie') AS matiere_libelle,
               x.origine, x.raison_origine, x.type_texte,
               coalesce(so.sort, CASE WHEN x.dossier IS NOT NULL THEN 'non_connu' END) AS sort_final,
               coalesce(so.par_49_3, false) AS par_49_3,
               g.groupe, x.groupe_scrutin,
               CASE WHEN g.groupe IS NULL THEN 'sans_groupe_a_la_date' END AS raison_groupe,
               pe.periode, pe.banc, pe.gouvernement,
               CASE WHEN pe.periode IS NULL THEN 'hors_mandat_a_la_date' END AS raison_periode,
               x.cause AS cause_non_votant, x.par_delegation,
               mp.position AS mise_au_point, mp.dysf AS mise_au_point_dysfonctionnement,
               x.lecture, x.numero, x.solennel, x.dossiers, so.titre AS titre_dossier, x.intitule,
               x.mandat, x.num_place, x.source_url
        FROM x
        LEFT JOIN matiere m ON m.dossier = x.dossier
        LEFT JOIN so ON so.dossier = x.dossier
        LEFT JOIN grp g ON g.scrutin = x.scrutin AND g.acteur = x.acteur
        LEFT JOIN per pe ON pe.scrutin = x.scrutin AND pe.acteur = x.acteur
        LEFT JOIN map mp ON mp.scrutin = x.scrutin AND mp.acteur = x.acteur
        ORDER BY x.acteur, x.date, x.scrutin""")
    r = ctx.x("""SELECT count(*), count(*) FILTER (matiere_statut IN ('assemblee', 'senat_seulement')),
                        count(*) FILTER (origine <> 'non_etablie'),
                        count(*) FILTER (sort_final <> 'non_connu'),
                        count(*) FILTER (groupe IS NOT NULL), count(*) FILTER (periode IS NOT NULL)
                 FROM vote_personne WHERE nature = 'ensemble'""")[0]
    nominatives = ctx.un("""SELECT count(*) FROM an_scrutins__position_vote
                            WHERE scrutin IN (SELECT scrutin FROM derniere_lecture)""")
    nommees = ctx.un("""SELECT count(*) FROM an_scrutins__position_vote
                        WHERE scrutin IN (SELECT scrutin FROM derniere_lecture) AND acteur IS NOT NULL""")
    return {"matiere_etablie": (r[1], r[0]), "origine_etablie": (r[2], r[0]),
            "sort_final_connu": (r[3], r[0]), "groupe_a_la_date_etabli": (r[4], r[0]),
            "periode_etablie": (r[5], r[0]), "position_nommee_en_derniere_lecture": (nommees, nominatives)}
