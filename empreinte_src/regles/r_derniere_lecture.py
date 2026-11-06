"""R-DERNIERE-LECTURE : le vote retenu pour un texte (doc. 1, 1.6 ; cahier 4.6, « dernière lecture »).

Pour chaque dossier, le scrutin de nature `ensemble` relié au dossier (R-LIEN-SCRUTIN-DOSSIER)
le plus récent, choisi sur **tous les scrutins du corpus** (toutes législatures), jamais sur ceux
où une personne a voté ; égalité de date : le numéro le plus grand (puis la législature la plus
récente, les numéros repartant à 1). Une partie de texte financier (`partie_de_texte`) n'est
jamais retenue (doc. 5, Q20). Un scrutin relié à plusieurs dossiers à la fois n'est pas retenu :
il ne dit pas sur lequel il porte (raison comptée dans la couverture)."""

NOM = "R-DERNIERE-LECTURE"
VERSION = 1
DEPEND = ("R-ORIGINE", "R-LIEN-SCRUTIN-DOSSIER")
SORTIES = ("derniere_lecture",)
DESCRIPTION = (
    "Un texte passe par plusieurs lectures. Le vote retenu est le vote sur l'ensemble du texte le "
    "plus récent, choisi parmi tous les scrutins publiés sur ce texte, et non parmi ceux où une "
    "personne a voté. Deux votes le même jour : le dernier numéroté. Un vote sur une partie d'une "
    "loi de finances n'est jamais retenu.")


def appliquer(ctx):
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
    avec_vote = ctx.un("SELECT count(DISTINCT dossier) FROM lien_scrutin_dossier")
    retenus = ctx.un("SELECT count(*) FROM derniere_lecture")
    ens = ctx.un("SELECT count(*) FROM scrutin_classe WHERE nature = 'ensemble'")
    ens_un = ctx.un("""SELECT count(DISTINCT scrutin) FROM lien_scrutin_dossier l
                       JOIN scrutin_classe s USING (scrutin) WHERE s.nature = 'ensemble' AND l.nb_dossiers = 1""")
    return {"dossier_avec_derniere_lecture": (retenus, avec_vote),
            "vote_ensemble_rattache_a_un_seul_dossier": (ens_un, ens)}
