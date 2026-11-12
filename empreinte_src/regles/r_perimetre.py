"""R-PERIMETRE : les personnes attendues, par population, et la fiche où chacune doit figurer
(cahier 4.1 et 6.1 ; doc. 1, 1.5.1 et 1.6 ; doc. 2, 2.8, contrôle C7).

Une ligne par (population, personne, fiche attendue) :

| population | qui | fiche attendue |
| --- | --- | --- |
| `candidat` | chaque candidature relevée (R-CANDIDATURES, R-IDENTITE) | `candidat/<adresse>` |
| `membre_groupe` | chaque député membre d'un groupe affiché d'une lignée publiée (R-LIGNEE, R-APPARTENANCE) | `lignee/<adresse>`, section `membres` |
| `membre_gouvernement` | chaque membre d'un gouvernement publié (R-COMPOSITION ; `perimetre.LEGISLATURES_GOUVERNEMENTS`) | `gouvernement/<adresse>`, section `composition` |
| `depute_ni` | député d'une législature publiée (XIVe à XVIIe) sans groupe pendant tout son mandat de cette législature | aucune (ses votes et amendements restent dans le corpus) |

Une personne ne sort d'une population que pour une **raison établie** (`raison_sortie`) :
candidature retirée à la source, ou décision `perimetre` (`personne` : `per:…` ou `PA…`,
`population`, `motif`). Un candidat déclaré sans fiche pour une raison technique (adresse non
établie) n'est **pas** sorti : C7 le nomme dans le refus, jusqu'à une décision.

Les membres des gouvernements dont un mandat reste ouvert dans un gouvernement clos (Q23, A8)
sont attendus comme les autres : la fiche les sert ou les signale ; C7 vérifie qu'ils y sont.
"""

NOM = "R-PERIMETRE"
VERSION = 1
DEPEND = ("R-IDENTITE", "R-LIGNEE", "R-APPARTENANCE", "R-COMPOSITION", "R-GOUVERNEMENTS", "R-DEPUTES")
SORTIES = ("population",)
DESCRIPTION = (
    "Le site suit quatre populations : les candidats déclarés, les membres des groupes, les membres "
    "des gouvernements et les députés non inscrits. Pour chacune, nous calculons à partir des "
    "sources qui est attendu et sur quelle fiche. Une personne attendue ne sort du site que pour une "
    "raison établie : candidature retirée, ou décision publiée. Sinon, la publication est refusée et "
    "la personne est nommée.")

from ..perimetre import LEGISLATURES, LEGISLATURES_GOUVERNEMENTS


def appliquer(ctx):
    legs = ", ".join(str(n) for n in LEGISLATURES)
    gouv = ", ".join(str(n) for n in LEGISLATURES_GOUVERNEMENTS)
    dec = ""
    if ctx.existe("decision_perimetre"):
        dec = "decision_perimetre"
    sortie = (f"""(SELECT any_value(fichier) FROM {dec} d
                    WHERE (d.personne = x.per OR d.personne = x.acteur)
                      AND (d.population IS NULL OR d.population = x.population))""" if dec else "NULL")
    ctx.ecrire("population", f"""
        WITH x AS (
            SELECT 'candidat' AS population, c.per, c.acteur,
                   CASE WHEN c.adresse IS NOT NULL THEN 'candidat/' || c.adresse END AS fiche_attendue,
                   NULL::VARCHAR AS section_attendue,
                   CASE WHEN c.statut = 'retiree' THEN 'candidature_retiree_a_la_source' END AS raison_source,
                   c.publie, c.raison_non_publie AS detail
            FROM candidat c
            UNION ALL
            SELECT DISTINCT 'membre_groupe', NULL, a.acteur, 'lignee/' || o.adresse, 'membres', NULL, true, NULL
            FROM (SELECT l.adresse, unnest(m.organes) AS organe
                  FROM lignee_maillon m JOIN lignee l USING (lignee) WHERE l.publiee AND m.affiche) o
            JOIN appartenance a ON a.groupe = o.organe
            UNION ALL
            SELECT DISTINCT 'membre_gouvernement', NULL, mg.acteur, 'gouvernement/' || g.adresse, 'composition',
                   NULL, true, NULL
            FROM membre_gouvernement mg JOIN gouvernement g ON g.organe = mg.gouvernement
            WHERE mg.gouvernement IN (SELECT gouvernement FROM gouvernement_legislature
                                      WHERE legislature IN ({gouv}))
            UNION ALL
            SELECT DISTINCT 'depute_ni', NULL, d.acteur, NULL, NULL, NULL, true, NULL
            FROM depute d WHERE d.legislature IN ({legs})
              AND NOT EXISTS (SELECT 1 FROM appartenance a WHERE a.acteur = d.acteur
                              AND a.legislature = d.legislature))
        SELECT x.population, x.per, x.acteur, x.fiche_attendue, x.section_attendue,
               coalesce(x.raison_source, CASE WHEN {sortie} IS NOT NULL THEN 'decision' END) AS raison_sortie,
               {sortie} AS decision, x.publie, x.detail
        FROM x
        ORDER BY x.population, x.fiche_attendue, x.acteur, x.per""")
    n = ctx.un("SELECT count(*) FROM population WHERE fiche_attendue IS NOT NULL OR population = 'candidat'")
    sans = ctx.un("""SELECT count(*) FROM population WHERE population = 'candidat' AND raison_sortie IS NULL
                     AND (fiche_attendue IS NULL OR NOT publie)""")
    return {"personnes_attendues_avec_une_fiche_possible": (n - sans, n)}
