"""R-ORATEUR : à qui attribuer chaque paragraphe d'un compte rendu de séance (doc. 1, 1.6 ;
cahier 3.1.5 ; mesures `an-amendements-cr.md`, 5.3).

Le lecteur restitue l'orateur tel que la source l'écrit ; la règle décide. Un paragraphe est
attribué à une personne seulement si la source donne un identifiant d'acteur connu **et** si le
nom affiché correspond à l'état civil de cet acteur. Sinon : `acteur = NULL` et une raison :

- `sans_orateur` : texte de séance sans orateur (résultat d'un vote, suspension…) ;
- `orateur_collectif` : « Un député du groupe RN », « Plusieurs députés… » ;
- `plusieurs_orateurs` : « MM. X et Y », « Mme X et un député… », ou deux identifiants distincts ;
- `interpellation` : orateur nommé sans identifiant d'acteur (exclamation depuis les bancs) ;
- `identifiant_nul` : `PA0` sur un orateur nommé ;
- `identifiant_negatif` : `PA-125869`… (absents du référentiel des acteurs) ;
- `identifiant_inconnu` : identifiant absent du référentiel (personne hors Assemblée) ;
- `nom_absent` : identifiant sans nom affiché, rien à vérifier ;
- `personne_hors_assemblee` : nom affiché d'une autre personne, dont la qualité écrite n'est pas
  parlementaire (« policier, lanceur d'alerte ») ;
- `identifiant_de_repli` : nom affiché d'une autre personne sous un identifiant que la source
  sait employer comme repli (`PA793214` en XVIIe) ;
- `nom_discordant` : nom affiché d'une autre personne (« Mme Alice Rufo » sous l'identifiant de
  François Ruffin), ou libellé de fonction dont la civilité contredit l'acteur (« Mme la
  ministre » sous l'identifiant d'un homme).

Nom antérieur : le nom affiché peut correspondre au nom actuel de l'acteur **ou** à un nom que
l'Assemblée a publié pour le même identifiant dans une archive plus ancienne (archive figée d'une
législature close : « Guillaume Gouffier-Cha » en XVe, « Gouffier Valente » ensuite). Le nom
affiché sur le site reste le nom actuel ; `nom_anterieur` dit que le rattachement s'est fait par
un nom antérieur. Un nom que la source n'a jamais donné à cet identifiant reste discordant
(« Mme Alice Rufo » sous l'identifiant de François Ruffin).

Présidence : `preside` est vrai quand `roledebat="president"` **ou** quand le nom affiché est
« M. le président » / « Mme la présidente » (l'attribut manque sur plus de la moitié des
paragraphes de présidence). Présider n'est pas intervenir dans le débat : la colonne le dit,
l'attribution est gardée (on sait qui préside). `interruption` distingue les exclamations
(`code_grammaire` INTERRUPTION) des interventions.
"""

NOM = "R-ORATEUR"
VERSION = 2
DEPEND = ()
SORTIES = ("intervention_attribuee",)
DESCRIPTION = (
    "Une prise de parole est attribuée à une personne quand le compte rendu donne son identifiant "
    "et que le nom affiché correspond à son état civil, actuel ou antérieur (un nom que "
    "l'Assemblée a publié pour cette même personne dans une archive plus ancienne, par exemple "
    "avant un changement de nom). Sinon elle reste non attribuée, avec sa "
    "raison : orateur collectif (« un député du groupe… »), plusieurs orateurs, exclamation sans "
    "identifiant, identifiant nul, négatif ou inconnu, ou nom affiché qui ne correspond pas à "
    "l'identifiant (par exemple une ministre déléguée publiée sous l'identifiant d'un député). "
    "La présidence de séance est reconnue par l'attribut de rôle ou par le libellé « M. le "
    "président » / « Mme la présidente » : présider n'est pas intervenir dans le débat.")

# Identifiants que la source emploie comme repli pour des orateurs qu'elle ne sait pas
# identifier (mesuré : `PA793214` porte 13 paragraphes d'autres orateurs en XVIIe).
IDENTIFIANTS_DE_REPLI = ("PA793214",)


def norm(x: str) -> str:
    """SQL : texte en minuscules sans accents, ponctuation et espaces (insécables compris)
    réduits à une espace."""
    return (f"trim(regexp_replace(lower(strip_accents(replace(replace(replace(coalesce({x}, ''), "
            f"chr(160), ' '), chr(8239), ' '), chr(8217), ''''))), '[^a-z0-9]+', ' ', 'g'))")


def classe_qualite(x: str) -> str:
    """SQL : classe d'une qualité écrite par le compte rendu (texte libre, 267 libellés en XVIIe).
    `membre_du_gouvernement`, `rapporteur`, `president_de_commission`, `autre` (personnalité
    extérieure), NULL quand rien n'est écrit. Un suppléant prend la classe de celui qu'il supplée."""
    q = f"regexp_replace({norm(x)}, '^suppl[ea]ant ', '')"
    return f"""(CASE
        WHEN {x} IS NULL OR {q} = '' OR regexp_matches({x}, '^\\s*\\(.*\\)\\s*$') THEN NULL
        WHEN regexp_matches({q}, '^(premier ministre|premiere ministre|ministre|garde des sceaux|secretaire d etat|porte parole du gouvernement|haut commissaire|haute commissaire)')
             THEN 'membre_du_gouvernement'
        WHEN regexp_matches({q}, 'rapporteu') THEN 'rapporteur'
        WHEN regexp_matches({q}, '(^| )(vice )?presidente? (de|du|des) ') THEN 'president_de_commission'
        ELSE 'autre' END)"""


def appliquer(ctx):
    repli = ", ".join(f"'{i}'" for i in IDENTIFIANTS_DE_REPLI)
    nom = "i.orateur_nom"
    n_nom = norm(nom)
    # Nom affiché réduit à « prénom nom » : sans civilité, sans « (groupe) » ni « , qualité ».
    n_aff = "regexp_replace(" + norm(f"regexp_replace({nom}, '\\s*[\\(,].*$', '')") + ", '^(m|mme|mlle) ', '')"
    n_famille = norm("regexp_replace(s.nom, '\\s*\\(.*\\)\\s*', ' ', 'g')")
    # Noms de chaque acteur : l'actuel (archive qui fait foi) et ceux des archives plus anciennes.
    archives = ("an_acteurs__identite_source__archives" if ctx.existe("an_acteurs__identite_source__archives")
                else "an_acteurs__identite_source")
    ctx.x(f"""CREATE OR REPLACE TEMP TABLE _or_noms AS
        WITH tous AS (
            SELECT a.uid, {norm('a.prenom')} AS np, {norm("regexp_replace(a.nom, '\\s*\\(.*\\)\\s*', ' ', 'g')")} AS nf,
                   false AS anterieur FROM an_acteurs__identite_source a
            UNION ALL
            SELECT a.uid, {norm('a.prenom')}, {norm("regexp_replace(a.nom, '\\s*\\(.*\\)\\s*', ' ', 'g')")},
                   true FROM {archives} a)
        SELECT uid, np, nf, bool_and(anterieur) AS anterieur FROM tous
        WHERE np <> '' AND nf <> '' GROUP BY 1, 2, 3""")
    ctx.ecrire("intervention_attribuee", f"""
        WITH i AS (
            SELECT i.*, {n_nom} AS nn,
                   {n_aff} AS na,
                   len(list_distinct(list_filter(list_transform(i.orateurs, lambda o: o.id),
                                                 lambda x: x IS NOT NULL AND x <> 'PA0'))) AS nb_ids
            FROM an_comptes_rendus__intervention i),
        c AS (
            SELECT i.*, s.uid AS connu, s.civilite,
                   {norm('s.prenom')} AS np,
                   {n_famille} AS nf,
                   nn IN ('m le president', 'mme la presidente') AS libelle_presidence,
                   regexp_matches(nn, '^(m|mme) (le|la|l) ') AS libelle_fonction,
                   CASE WHEN regexp_matches(nn, '^(mme|mlle) ') THEN 'Mme'
                        WHEN regexp_matches(nn, '^m ') THEN 'M.' END AS civilite_affichee,
                   regexp_matches(nn, '^(un|une|plusieurs|quelques|de nombreux|nombreux|des|les|tous|toutes|certains|certaines|divers) ')
                     AS collectif,
                   regexp_matches(nn, '^(mm|mmes) ') OR regexp_matches(' ' || nn || ' ', ' et ')
                     OR nb_ids > 1 AS plusieurs,
                   {classe_qualite('i.qualite')} AS classe_qualite
            FROM i LEFT JOIN an_acteurs__identite_source s ON s.uid = i.orateur),
        k AS (
            -- Concordance du nom affiché avec chaque nom connu de l'acteur (actuel ou antérieur).
            SELECT compte_rendu, id_syceron, bool_or(conc) AS concordant_actuel_ou_anterieur,
                   bool_or(conc AND NOT anterieur) AS concordant_actuel
            FROM (SELECT compte_rendu, id_syceron, anterieur,
                         reste IS NOT NULL AND reste <> '' AND (reste = nf OR starts_with(reste, nf || ' ')
                           OR ends_with(reste, ' ' || nf) OR starts_with(nf, reste || ' ')
                           OR ends_with(nf, ' ' || reste)) AS conc
                  FROM (SELECT p.compte_rendu, p.id_syceron, n.nf, n.anterieur,
                               CASE WHEN starts_with(p.na, n.np || ' ') THEN substr(p.na, length(n.np) + 2) END AS reste
                        FROM (SELECT DISTINCT compte_rendu, id_syceron, orateur, {n_aff} AS na
                              FROM an_comptes_rendus__intervention i) p
                        JOIN _or_noms n ON n.uid = p.orateur))
            GROUP BY 1, 2),
        v AS (SELECT c.*, coalesce(k.concordant_actuel_ou_anterieur, false) AS concordant_tout,
                     coalesce(k.concordant_actuel, false) AS concordant_actuel
              FROM c LEFT JOIN k USING (compte_rendu, id_syceron)),
        r AS (
            SELECT *,
                   concordant_tout AS concordant,
                   CASE
                     WHEN orateur IS NULL AND len(orateurs) = 0 THEN 'sans_orateur'
                     WHEN collectif THEN 'orateur_collectif'
                     WHEN plusieurs THEN 'plusieurs_orateurs'
                     WHEN orateur IS NULL THEN 'interpellation'
                     WHEN orateur = 'PA0' THEN 'identifiant_nul'
                     WHEN orateur LIKE 'PA-%' THEN 'identifiant_negatif'
                     WHEN connu IS NULL THEN 'identifiant_inconnu'
                     WHEN nn = '' THEN 'nom_absent'
                   END AS raison_forme
            FROM v)
        SELECT compte_rendu, id_syceron, seance, date,
               CASE WHEN raison IS NULL THEN orateur END AS acteur,
               raison AS raison_non_attribuee,
               coalesce(roledebat = 'president', false) OR libelle_presidence AS preside,
               coalesce(code_grammaire LIKE 'INTERRUPTION%', false) AS interruption,
               libelle_fonction AS nom_est_un_libelle,
               raison IS NULL AND NOT libelle_fonction AND concordant AND NOT concordant_actuel AS nom_anterieur,
               orateur AS orateur_source, orateur_nom AS nom_affiche, qualite AS qualite_ecrite_libelle,
               classe_qualite AS qualite_ecrite, prov_url AS source_url
        FROM (SELECT *, coalesce(raison_forme, CASE
                 WHEN libelle_fonction THEN
                      CASE WHEN civilite_affichee IS DISTINCT FROM civilite THEN 'nom_discordant' END
                 WHEN concordant THEN NULL
                 WHEN classe_qualite = 'autre' AND civilite_affichee IS NOT NULL THEN 'personne_hors_assemblee'
                 WHEN orateur IN ({repli}) THEN 'identifiant_de_repli'
                 ELSE 'nom_discordant' END) AS raison
              FROM r)""")
    n_orateur = ctx.un("SELECT count(*) FROM intervention_attribuee WHERE raison_non_attribuee IS DISTINCT FROM 'sans_orateur'")
    n_attr = ctx.un("SELECT count(*) FROM intervention_attribuee WHERE acteur IS NOT NULL")
    hp = ctx.x("""SELECT count(*) FILTER (acteur IS NOT NULL), count(*) FROM intervention_attribuee
                  WHERE NOT preside AND raison_non_attribuee IS DISTINCT FROM 'sans_orateur'""")[0]
    return {"paragraphe_attribue": (n_attr, n_orateur),
            "parole_hors_presidence_attribuee": (hp[0], hp[1])}
