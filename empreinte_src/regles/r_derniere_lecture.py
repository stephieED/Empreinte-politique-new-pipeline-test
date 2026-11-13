"""R-DERNIERE-LECTURE : le vote retenu pour un texte (doc. 1, 1.6 ; cahier 4.6, « dernière lecture »).

Pour chaque dossier, le scrutin de nature `ensemble` relié au dossier (R-LIEN-SCRUTIN-DOSSIER)
le plus récent, choisi sur **tous les scrutins du corpus** (toutes législatures), jamais sur ceux
où une personne a voté ; égalité de date : le numéro le plus grand (puis la législature la plus
récente, les numéros repartant à 1). Une partie de texte financier (`partie_de_texte`) n'est
jamais retenue (doc. 5, Q20). Un scrutin relié à plusieurs dossiers à la fois n'est pas retenu :
il ne dit pas sur lequel il porte (raison comptée dans la couverture).

Version 2 (issue #34, décision du 13/11/2026 « Garder, signalé ») : un vote sur l'ensemble que
R-LIEN-SCRUTIN-DOSSIER n'a relié à aucun dossier (`scrutin_non_relie`) peut être la vraie dernière
lecture d'un texte. Le vote retenu est gardé, mais `votes_posterieurs_non_relies` nomme chaque vote
sur l'ensemble non relié, plus récent, dont ce dossier est candidat : dossier discuté ou décidé dans
la séance du vote (séance ambiguë), ou candidat d'une route (désaccord). Un vote sans séance
connue ne désigne aucun dossier. Mesuré sur la g10 : 170 votes sur l'ensemble non reliés ; 75
dernières lectures sur 665 signalées (exemple : `DLR5L15N35986`, dont le texte de CMP,
`VTANR5L15V386` du 06/02/2018, n'est pas relié)."""

NOM = "R-DERNIERE-LECTURE"
VERSION = 2
DEPEND = ("R-ORIGINE", "R-LIEN-SCRUTIN-DOSSIER")
SORTIES = ("derniere_lecture",)
DESCRIPTION = (
    "Un texte passe par plusieurs lectures. Le vote retenu est le vote sur l'ensemble du texte le "
    "plus récent, choisi parmi tous les scrutins publiés sur ce texte, et non parmi ceux où une "
    "personne a voté. Deux votes le même jour : le dernier numéroté. Un vote sur une partie d'une "
    "loi de finances n'est jamais retenu. Quand un vote plus récent sur l'ensemble n'a pu être relié "
    "à aucun texte, mais a pu porter sur celui-ci, il est nommé à côté du vote retenu.")


def appliquer(ctx):
    """Applique R-DERNIERE-LECTURE : écrit `derniere_lecture`, le vote retenu pour chaque texte
    (voir la description du module) ; la sortie est écrite une première fois, puis réécrite avec la
    colonne `votes_posterieurs_non_relies` (votes sur l'ensemble postérieurs au vote retenu et non
    reliés au dossier). Rend la couverture, `{nom: (numérateur, dénominateur)}` :
    `dossier_avec_derniere_lecture`, `derniere_lecture_sans_vote_posterieur_non_relie`,
    `vote_ensemble_rattache_a_un_seul_dossier`."""
    ctx.ecrire("derniere_lecture", """
        WITH c AS (
            SELECT l.dossier, s.scrutin, s.date, s.numero, s.legislature, s.lecture, s.sort,
                   s.origine, s.type_texte, s.source_url,
                   count(*) OVER (PARTITION BY l.dossier) AS nb_votes_ensemble
            FROM lien_scrutin_dossier l JOIN scrutin_classe s USING (scrutin)
            WHERE s.nature = 'ensemble' AND l.nb_dossiers = 1)
        SELECT dossier, scrutin, date, numero, legislature, lecture, sort, origine, type_texte,
               nb_votes_ensemble, source_url
        FROM c
        QUALIFY row_number() OVER (PARTITION BY dossier
                                   ORDER BY date DESC, numero DESC, legislature DESC) = 1""")
    # Votes sur l'ensemble non reliés, et les dossiers qu'ils ont pu concerner.
    seance = ("""SELECT DISTINCT n.scrutin, a.dossier FROM scrutin_non_relie n
                 JOIN scrutin_classe s USING (scrutin)
                 JOIN an_dossiers__acte a ON a.reunion = s.seance
                 WHERE a.type_acte IN ('DiscussionSeancePublique_Type', 'Decision_Type')"""
              if ctx.existe("an_dossiers__acte") else
              "SELECT NULL::VARCHAR AS scrutin, NULL::VARCHAR AS dossier WHERE false")
    ctx.x(f"""CREATE OR REPLACE TEMP TABLE _dl_dl AS SELECT * FROM derniere_lecture""")
    ctx.ecrire("derniere_lecture", f"""
        WITH cand AS (
            {seance}
            UNION
            SELECT DISTINCT n.scrutin, split_part(x, ':', 2) AS dossier
            FROM scrutin_non_relie n, unnest(coalesce(n.candidats, [])) AS t(x)),
        tard AS (
            SELECT d.dossier, list(DISTINCT s.scrutin ORDER BY s.scrutin) AS votes
            FROM _dl_dl d JOIN cand c ON c.dossier = d.dossier
            JOIN scrutin_classe s ON s.scrutin = c.scrutin
            WHERE s.nature = 'ensemble'
              AND (s.date > d.date OR (s.date = d.date AND (s.legislature > d.legislature
                   OR (s.legislature = d.legislature AND s.numero > d.numero))))
            GROUP BY 1)
        SELECT d.* EXCLUDE (regle), coalesce(t.votes, []::VARCHAR[]) AS votes_posterieurs_non_relies
        FROM _dl_dl d LEFT JOIN tard t USING (dossier)""")
    avec_vote = ctx.un("SELECT count(DISTINCT dossier) FROM lien_scrutin_dossier")
    retenus = ctx.un("SELECT count(*) FROM derniere_lecture")
    ens = ctx.un("SELECT count(*) FROM scrutin_classe WHERE nature = 'ensemble'")
    ens_un = ctx.un("""SELECT count(DISTINCT scrutin) FROM lien_scrutin_dossier l
                       JOIN scrutin_classe s USING (scrutin) WHERE s.nature = 'ensemble' AND l.nb_dossiers = 1""")
    signalees = ctx.un("SELECT count(*) FROM derniere_lecture WHERE len(votes_posterieurs_non_relies) > 0")
    return {"dossier_avec_derniere_lecture": (retenus, avec_vote),
            "derniere_lecture_sans_vote_posterieur_non_relie": (retenus - signalees, retenus),
            "vote_ensemble_rattache_a_un_seul_dossier": (ens_un, ens)}
