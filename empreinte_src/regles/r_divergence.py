"""R-DIVERGENCE : la position d'une personne à côté de la position majoritaire de son groupe, scrutin
par scrutin (doc. 1, 1.5.3 et 1.6, R-POSITION-GROUPE et R-DIVERGENCE ; cahier 2, règle 7 ; 4.2 « Où
cette personne a voté autrement que son groupe » et 4.6).

Une ligne par (acteur, scrutin) **seulement si les 5 conditions de la section 4.2 sont réunies** :

1. **position de la personne publiée** : la source la nomme, et elle a voté pour, contre ou
   s'est abstenue (un non-votant — présidence de séance, membre du gouvernement — n'a pas de
   position à comparer) ;
2. **position du groupe établie** : la position majoritaire **publiée par la source** pour ce
   groupe à ce scrutin (`an_scrutins__decompte_groupe`), jamais recalculée ; elle n'est pas
   établie si le groupe n'y figure pas (organe `PO0`, piège S3), s'il y figure deux fois avec des
   positions différentes, si aucun de ses membres ne s'est exprimé (la source publie alors une
   position par défaut), ou si elle est **contredite par le décompte publié sur la même ligne** :
   une autre position y réunit strictement plus de voix (mesuré : 3 308 lignes de groupe sur
   106 507 où un membre s'est exprimé, hors `PO0`, XVIIe, collecte du 06/11/2026 ; ex. `VTANR5L17V8431`,
   groupe `PO845439` : « contre » publié pour 19 pour, 7 contre, 7 abstentions, que les listes
   nominatives confirment) ;
3. **dernière lecture** du texte (R-DERNIERE-LECTURE) ;
4. vote sur l'**ensemble** du texte (même source) ;
5. **groupe ayant une fiche** : le groupe de la personne **à la date** du scrutin
   (R-APPARTENANCE, jamais l'organe que porte le scrutin) appartient à une lignée publiée
   (R-LIGNEE : groupes de la XIVe à la XVIIe, `LEGISLATURES_AVEC_FICHE`). Sans R-LIGNEE, la
   règle s'en tient aux législatures de `LEGISLATURES_AVEC_FICHE`.

`diverge` dit si les deux positions diffèrent. La bande de la fiche montre chaque ligne ; les
divergences y sont cliquables. **Aucun total** de divergences n'est calculé, par personne ni par
groupe (règle 7) : la couverture ne compte que les comparaisons retenues. `groupe_divise` (les
membres du groupe n'ont pas tous voté de même, critère brut sans seuil, cahier 4.6) et les
décomptes du groupe sont servis tels que publiés."""

NOM = "R-DIVERGENCE"
VERSION = 2
DEPEND = ("R-VOTE-PERSONNE", "R-APPARTENANCE")
DEPEND_FACULTATIF = ("R-LIGNEE",)
SORTIES = ("divergence",)

# Législatures dont les groupes ont une fiche (fiches de lignée, cahier 4.1).
from .r_lignee import LEGISLATURES_AVEC_FICHE  # noqa: E402

DESCRIPTION = (
    "Sur un scrutin, la position d'une personne est placée à côté de la position majoritaire de "
    "son groupe, telle que l'Assemblée la publie, seulement quand cinq conditions sont réunies : la "
    "position de la personne est publiée (pour, contre ou abstention) ; la position de son groupe "
    "est publiée par l'Assemblée et n'est pas contredite par le décompte des voix du groupe publié "
    "avec elle ; le scrutin est la dernière lecture du texte ; il porte sur "
    "l'ensemble du texte ; le groupe auquel la personne appartient à la date du vote a une fiche "
    "sur le site (les groupes de la XIVe législature à aujourd'hui). Le groupe est divisé dès "
    "que ses membres n'ont pas tous voté de même, sans seuil. Les divergences ne sont jamais "
    "comptées ni transformées en fréquence.")

POSITIONS = "('pour', 'contre', 'abstention')"


def appliquer(ctx):
    """Applique R-DIVERGENCE : écrit `divergence`, la position de chaque personne comparée à la
    position majoritaire de son groupe, scrutin par scrutin ; les lignées (`lignee_maillon`) sont
    lues si elles existent (voir la description du module). Rend la couverture,
    `{nom: (numérateur, dénominateur)}` :
    `positions_comparables_sur_positions_en_derniere_lecture`,
    `exclues_position_du_groupe_non_etablie`, `dont_position_publiee_contredite_par_le_decompte`,
    `exclues_groupe_sans_fiche`, `exclues_sans_groupe_a_la_date`,
    `exclues_position_personne_non_votant`."""
    legs = ", ".join(str(x) for x in LEGISLATURES_AVEC_FICHE)
    avec_fiche = ("AND g.organe IN (SELECT unnest(m.organes) FROM lignee_maillon m "
                  "JOIN lignee l USING (lignee) WHERE l.publiee AND m.affiche)"
                  if ctx.existe("lignee_maillon") else "")
    ctx.x(f"""CREATE OR REPLACE TEMP TABLE _dv AS
        WITH dg AS (   -- position publiée d'un groupe à un scrutin ; deux occurrences discordantes : non établie
            SELECT scrutin, organe AS groupe,
                   CASE WHEN count(DISTINCT position_majoritaire) = 1 THEN any_value(position_majoritaire) END AS position_groupe,
                   count(*) AS occurrences, any_value(pour) AS pour, any_value(contre) AS contre,
                   any_value(abstentions) AS abstentions, any_value(non_votants) AS non_votants,
                   any_value(nombre_membres) AS nombre_membres
            FROM an_scrutins__decompte_groupe WHERE organe <> 'PO0' GROUP BY 1, 2),
        dgc AS (
            SELECT *, CASE position_groupe WHEN 'pour' THEN pour WHEN 'contre' THEN contre
                                           WHEN 'abstention' THEN abstentions END
                      < greatest(pour, contre, abstentions) AS contredite
            FROM dg)
        SELECT v.acteur, v.scrutin, v.dossier, v.date, v.position, v.groupe, v.groupe_scrutin,
               v.nature, v.derniere_lecture, v.matiere, v.matiere_libelle, v.sort_final, v.origine,
               v.titre_dossier, v.periode, v.source_url,
               g.organe IS NOT NULL AS groupe_a_une_fiche, g.sigle,
               dg.position_groupe, dg.occurrences, dg.pour, dg.contre, dg.abstentions,
               dg.non_votants, dg.nombre_membres,
               CASE WHEN v.position NOT IN {POSITIONS} OR v.position IS NULL THEN 'position_personne_non_publiee'
                    WHEN v.nature <> 'ensemble' THEN 'pas_un_vote_sur_l_ensemble'
                    WHEN NOT v.derniere_lecture THEN 'pas_la_derniere_lecture'
                    WHEN v.groupe IS NULL THEN 'sans_groupe_a_la_date'
                    WHEN g.organe IS NULL THEN 'groupe_sans_fiche'
                    WHEN dg.groupe IS NULL THEN 'groupe_absent_du_decompte'
                    WHEN dg.position_groupe IS NULL THEN 'positions_du_groupe_discordantes'
                    WHEN coalesce(dg.pour, 0) + coalesce(dg.contre, 0) + coalesce(dg.abstentions, 0) = 0
                         THEN 'aucun_membre_exprime'
                    WHEN dg.position_groupe NOT IN {POSITIONS} THEN 'position_du_groupe_non_publiee'
                    WHEN dg.contredite THEN 'position_publiee_contredite_par_le_decompte'
               END AS raison_exclusion
        FROM vote_personne v
        LEFT JOIN groupe g ON g.organe = v.groupe AND g.legislature IN ({legs}) {avec_fiche}
        LEFT JOIN dgc dg ON dg.scrutin = v.scrutin AND dg.groupe = v.groupe
        WHERE v.nature = 'ensemble'""")
    ctx.ecrire("divergence", """
        SELECT acteur, scrutin, date, position, position_groupe, groupe, position <> position_groupe AS diverge,
               dossier, sigle, groupe_scrutin, groupe_scrutin IS DISTINCT FROM groupe AS groupe_scrutin_different,
               (CASE WHEN pour > 0 THEN 1 ELSE 0 END + CASE WHEN contre > 0 THEN 1 ELSE 0 END
                + CASE WHEN abstentions > 0 THEN 1 ELSE 0 END) > 1 AS groupe_divise,
               pour AS groupe_pour, contre AS groupe_contre, abstentions AS groupe_abstentions,
               non_votants AS groupe_non_votants, nombre_membres AS groupe_membres,
               matiere, matiere_libelle, sort_final, origine, titre_dossier, periode, source_url
        FROM _dv WHERE raison_exclusion IS NULL
        ORDER BY acteur, date, scrutin""")
    r = ctx.x("""SELECT count(*), count(*) FILTER (raison_exclusion IS NULL),
                        count(*) FILTER (raison_exclusion IN ('groupe_absent_du_decompte',
                            'positions_du_groupe_discordantes', 'aucun_membre_exprime',
                            'position_du_groupe_non_publiee', 'position_publiee_contredite_par_le_decompte')),
                        count(*) FILTER (raison_exclusion = 'position_publiee_contredite_par_le_decompte'),
                        count(*) FILTER (raison_exclusion = 'groupe_sans_fiche'),
                        count(*) FILTER (raison_exclusion = 'sans_groupe_a_la_date'),
                        count(*) FILTER (raison_exclusion = 'position_personne_non_publiee')
                 FROM _dv""")[0]
    ctx.x("DROP TABLE IF EXISTS _dv")
    return {"positions_comparables_sur_positions_en_derniere_lecture": (r[1], r[0]),
            "exclues_position_du_groupe_non_etablie": (r[2], r[0]),
            "dont_position_publiee_contredite_par_le_decompte": (r[3], r[0]),
            "exclues_groupe_sans_fiche": (r[4], r[0]),
            "exclues_sans_groupe_a_la_date": (r[5], r[0]),
            "exclues_position_personne_non_votant": (r[6], r[0])}
