"""R-49-3 : les engagements de responsabilité du gouvernement sur un texte (article 49, alinéa 3 ;
doc. 1, 1.6 ; mesures `an-scrutins-dossiers.md`, 4.3).

Un engagement est un acte `DeclarationGouvernement_Type` dont `typeDeclaration.fam_code` vaut
`Art.49.3` ; jamais lu dans la conclusion d'une décision (5 fois seulement en XVIIe), jamais un
scrutin (aucun `voteRefs` sur ces actes) : c'est un fait de procédure, pas une position de vote
(cahier, partie 2, règle 4). Il est rattaché au gouvernement en fonction à sa date.

Un même acte figure dans deux dossiers (le texte, et le dossier « Engagement de la
responsabilité du Gouvernement », procédure 13) : une ligne par (dossier, acte), avec
`procedure_code` pour les distinguer. Le nombre d'engagements distincts est celui des actes."""

from .r_lois import gouvernement_a

NOM = "R-49-3"
VERSION = 1
DEPEND = ("R-GOUVERNEMENTS",)
SORTIES = ("engagement_49_3",)
DESCRIPTION = (
    "Un recours à l'article 49, alinéa 3, de la Constitution est lu dans l'acte du dossier "
    "législatif où le gouvernement engage sa responsabilité sur le texte. Ce n'est pas un vote : "
    "c'est un fait de procédure, présenté comme tel. Il est rattaché au gouvernement en fonction "
    "à sa date.")


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
    n = ctx.un("SELECT count(*) FROM engagement_49_3")
    gouv = ctx.un("SELECT count(*) FROM engagement_49_3 WHERE gouvernement IS NOT NULL")
    return {"gouvernement_etabli": (gouv, n)}
