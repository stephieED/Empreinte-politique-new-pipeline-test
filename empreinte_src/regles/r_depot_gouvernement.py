"""R-DEPOT-GOUVERNEMENT : les projets de loi, le gouvernement qui les a déposés et leur ministère
porteur (doc. 1, 1.6 ; cahier 3.1.4 et 4.4, « ce qu'il a fait déposer » ; issue #79).

Un projet de loi est un dossier dont le texte du **premier dépôt** (acte `DepotInitiative_Type`,
dans l'une ou l'autre chambre) a le préfixe `PRJL` ; le titre du dossier ne compte pas (« CETA »,
« Bioéthique »). Il est rattaché au gouvernement en fonction à la date de ce dépôt
(R-GOUVERNEMENTS). Un projet est déposé au nom du gouvernement : il n'est jamais un acte
personnel du ministre qui le présente (aucune personne n'est servie pour un projet).

**Ministère porteur** (version 2, issue #79). Un projet est « présenté au nom du Premier ministre
par » un ou plusieurs ministres. Sur le texte de dépôt, l'Assemblée publie le Premier ministre
comme **auteur** (1 296 projets sur 1 298 dont l'auteur est membre du gouvernement, g25) et les
ministres qui présentent le texte comme **cosignataires** (1 288 projets sur 1 312). L'auteur seul
ne donne donc presque jamais de ministère ; les ministres présentateurs sont :
- les cosignataires du texte de dépôt (cosignature non retirée), dans l'ordre publié ;
- un auteur membre du gouvernement à la date qui n'est pas le Premier ministre (projets déposés au
  Sénat qui citent le ministre comme auteur), placé avant les cosignataires.
Un auteur qui n'est pas membre du gouvernement (le Président de la République, auteur des projets
de loi constitutionnelle) n'est pas un présentateur.

Chaque présentateur est joint à son portefeuille (R-COMPOSITION, `membre_gouvernement`) dans le
gouvernement du dépôt, à la date du dépôt (début <= date <= fin). Le ministère de ce portefeuille
est le ministère lui-même pour un ministre de plein exercice ou le Premier ministre
(`tutelle_statut = 'sans_objet'`), sinon sa ou ses tutelles (`ministeres_tutelle` : `etabli`,
`decision`, ou `co_tutelle`, toutes servies, décision Q41 du 14/11/2026). Les ministères porteurs
sont ceux de tous les présentateurs, sans doublon, dans l'ordre des présentateurs :
- un seul : `ministere_porteur_statut = 'etabli'` et `ministere_porteur` le porte ;
- plusieurs : `plusieurs_ministeres`, tous servis dans `ministeres_porteurs`, aucun n'est choisi
  à la place de l'interface (`ministere_porteur` vide) ;
- sinon `non_etabli` et sa raison : `gouvernement_non_etabli`, `seul_le_premier_ministre_cite`
  (aucun cosignataire, l'auteur est le Premier ministre), `aucun_membre_du_gouvernement_cite`,
  `presentateur_hors_gouvernement_a_la_date`, `rattachement_non_etabli` (la tutelle d'un
  portefeuille présentateur n'est pas établie : on ne garde pas une partie des ministères),
  `composition_non_calculee` (R-COMPOSITION n'a pas été appliquée). Jamais de devinette.

Le libellé d'un ministère est celui de son organe tel que R-COMPOSITION le sert (`portefeuille`).
La teinte d'un ministère et le rapprochement de ministères d'un gouvernement à l'autre (organes
différents) relèvent de l'affichage et d'une normalisation des libellés qui n'est pas faite ici."""

from .r_lois import gouvernement_a

NOM = "R-DEPOT-GOUVERNEMENT"
VERSION = 2
DEPEND = ("R-GOUVERNEMENTS",)
# R-COMPOSITION donne les portefeuilles ; sans elle, le ministère porteur est « non établi ».
DEPEND_FACULTATIF = ("R-COMPOSITION",)
SORTIES = ("projet_gouvernement",)
DESCRIPTION = (
    "Un projet de loi est reconnu à la nature du texte déposé au début du dossier (identifiant "
    "commençant par PRJL), jamais à son titre. Il est rattaché au gouvernement en fonction le jour "
    "de son premier dépôt, à l'Assemblée ou au Sénat. Un projet de loi est déposé au nom du "
    "gouvernement : il n'est jamais présenté comme l'acte personnel d'un ministre. Son ministère "
    "porteur est celui des ministres qui le présentent, que l'Assemblée publie comme cosignataires "
    "du texte déposé (le Premier ministre, au nom duquel le projet est présenté, en est l'auteur) : "
    "chaque ministre est rattaché au portefeuille qu'il occupait ce jour-là dans ce gouvernement, "
    "et un ministre délégué ou un secrétaire d'État au ministère de tutelle de son portefeuille. "
    "Quand plusieurs ministères présentent le texte, tous sont donnés, dans l'ordre publié. Quand "
    "aucun ministre présentateur n'est publié, ou que l'un d'eux ne peut être rattaché, le "
    "ministère porteur est « non établi », avec sa raison.")

# Raisons d'un ministère porteur non établi (vocabulaire `raison_ministere_porteur`).
RAISONS = ("gouvernement_non_etabli", "composition_non_calculee", "seul_le_premier_ministre_cite",
           "aucun_membre_du_gouvernement_cite", "presentateur_hors_gouvernement_a_la_date",
           "rattachement_non_etabli")
STATUTS = ("etabli", "plusieurs_ministeres", "non_etabli")


def appliquer(ctx):
    """Applique R-DEPOT-GOUVERNEMENT : écrit `projet_gouvernement`, les projets de loi, le
    gouvernement qui les a déposés et leur ministère porteur (voir la description du module).
    Rend la couverture, `{nom: (numérateur, dénominateur)}` : `gouvernement_etabli`,
    `ministere_porteur_etabli` (un ou plusieurs ministères), `ministere_porteur_unique`."""
    ctx.x(f"""CREATE OR REPLACE TEMP TABLE _dg_projet AS
        WITH p AS (
            SELECT a.dossier, a.texte_associe AS document, a.uid AS acte,
                   coalesce(left(a.date, 10), left(doc.date_depot, 10)) AS date_depot,
                   CASE WHEN a.code LIKE 'AN%' THEN 'AN' WHEN a.code LIKE 'SN%' THEN 'SN' END AS chambre_depot,
                   TRY_CAST(regexp_extract(a.uid, '^L(\\d+)-', 1) AS INTEGER) AS legislature_depot,
                   d.procedure_code, d.procedure_libelle, d.titre AS titre_dossier,
                   coalesce(doc.prov_url, d.prov_url) AS source_url
            FROM an_dossiers__acte a
            JOIN an_dossiers__dossier d ON d.uid = a.dossier
            LEFT JOIN an_dossiers__document doc ON doc.uid = a.texte_associe
            WHERE a.type_acte = 'DepotInitiative_Type' AND a.texte_associe LIKE 'PRJL%')
        SELECT dossier, document, date_depot, {gouvernement_a('p.date_depot')} AS gouvernement,
               CASE WHEN date_depot IS NULL THEN 'date_de_depot_absente'
                    WHEN {gouvernement_a('p.date_depot')} IS NULL THEN 'aucun_gouvernement_a_la_date'
               END AS raison,
               acte, chambre_depot, legislature_depot, procedure_code, procedure_libelle,
               titre_dossier, source_url
        FROM p""")

    if ctx.existe("membre_gouvernement"):
        _ministere_porteur(ctx)
        porteur = "LEFT JOIN _dg_porteur mp USING (dossier)"
        sel = """mp.ministere_porteur, mp.ministere_porteur_libelle, mp.ministeres_porteurs,
                 mp.ministeres_porteurs_libelles, mp.portefeuilles_presentateurs,
                 mp.portefeuilles_presentateurs_libelles,
                 CASE WHEN p.gouvernement IS NULL OR mp.raison IS NOT NULL THEN 'non_etabli'
                      WHEN len(mp.ministeres_porteurs) = 1 THEN 'etabli'
                      ELSE 'plusieurs_ministeres' END AS ministere_porteur_statut,
                 CASE WHEN p.gouvernement IS NULL THEN 'gouvernement_non_etabli'
                      ELSE mp.raison END AS raison_ministere_porteur,
                 mp.presentateurs"""
    else:
        porteur = ""
        sel = """NULL::VARCHAR AS ministere_porteur, NULL::VARCHAR AS ministere_porteur_libelle,
                 NULL::VARCHAR[] AS ministeres_porteurs, NULL::VARCHAR[] AS ministeres_porteurs_libelles,
                 NULL::VARCHAR[] AS portefeuilles_presentateurs,
                 NULL::VARCHAR[] AS portefeuilles_presentateurs_libelles,
                 'non_etabli' AS ministere_porteur_statut,
                 CASE WHEN p.gouvernement IS NULL THEN 'gouvernement_non_etabli'
                      ELSE 'composition_non_calculee' END AS raison_ministere_porteur,
                 NULL::VARCHAR[] AS presentateurs"""
    ctx.ecrire("projet_gouvernement", f"""
        SELECT p.dossier, p.document, p.date_depot, p.gouvernement, p.raison, p.acte, p.chambre_depot,
               p.legislature_depot, p.procedure_code, p.procedure_libelle, p.titre_dossier,
               p.source_url, {sel}
        FROM _dg_projet p {porteur}""")
    for t in ("_dg_projet", "_dg_cite", "_dg_porteur"):
        ctx.x(f"DROP TABLE IF EXISTS {t}")

    n = ctx.un("SELECT count(*) FROM projet_gouvernement")
    gouv = ctx.un("SELECT count(*) FROM projet_gouvernement WHERE gouvernement IS NOT NULL")
    etabli = ctx.un("""SELECT count(*) FROM projet_gouvernement
                       WHERE ministere_porteur_statut IN ('etabli', 'plusieurs_ministeres')""")
    unique = ctx.un("SELECT count(*) FROM projet_gouvernement WHERE ministere_porteur_statut = 'etabli'")
    return {"gouvernement_etabli": (gouv, n), "ministere_porteur_etabli": (etabli, n),
            "ministere_porteur_unique": (unique, n)}


def _ministere_porteur(ctx):
    """Écrit `_dg_porteur` : pour chaque projet de `_dg_projet` rattaché à un gouvernement, ses
    présentateurs, leurs portefeuilles, les ministères porteurs et, s'ils ne sont pas établis, la
    raison (voir la description du module)."""
    if ctx.existe("an_dossiers__cosignature"):
        cosig = """SELECT c.document, c.acteur, 'cosignataire' AS role, 1 AS groupe, c.rang AS i
                   FROM an_dossiers__cosignature c
                   WHERE c.acteur IS NOT NULL AND c.date_retrait IS NULL
                     AND c.document IN (SELECT document FROM _dg_projet)"""
    else:
        cosig = ("SELECT NULL::VARCHAR AS document, NULL::VARCHAR AS acteur, NULL::VARCHAR AS role, "
                 "NULL::INTEGER AS groupe, NULL::INTEGER AS i WHERE false")
    # Membres du gouvernement cités sur le texte de dépôt (auteurs « auteur », cosignataires), une
    # ligne par (projet, personne, portefeuille occupé à la date dans ce gouvernement).
    ctx.x(f"""CREATE OR REPLACE TEMP TABLE _dg_cite AS
        WITH aut AS (
            SELECT * FROM (
                SELECT d.uid AS document, unnest(d.auteurs_acteurs) AS acteur,
                       unnest(d.auteurs_qualites) AS qualite,
                       unnest(range(1, len(d.auteurs_acteurs) + 1)) AS i
                FROM an_dossiers__document d WHERE d.uid IN (SELECT document FROM _dg_projet))
            WHERE qualite = 'auteur' AND acteur IS NOT NULL),
        cites AS (
            SELECT document, acteur, 'auteur' AS role, 0 AS groupe, i FROM aut
            UNION ALL {cosig}),
        un AS (   -- une personne citée deux fois (même cosignataire répété) : sa première place
            SELECT document, acteur, min((groupe, i)) AS ordre,
                   bool_or(role = 'cosignataire') AS cosignataire, bool_or(role = 'auteur') AS auteur
            FROM cites GROUP BY 1, 2)
        SELECT p.dossier, u.acteur, u.ordre, u.cosignataire, u.auteur, m.mandat, m.ministere,
               m.portefeuille, m.premier_ministre, m.tutelle_statut, m.ministeres_tutelle
        FROM _dg_projet p JOIN un u USING (document)
        LEFT JOIN membre_gouvernement m
          ON m.acteur = u.acteur AND m.gouvernement = p.gouvernement
         AND m.debut <= p.date_depot AND p.date_depot <= coalesce(m.fin, '9999-12-31')
        WHERE p.gouvernement IS NOT NULL""")
    ctx.x("""CREATE OR REPLACE TEMP TABLE _dg_porteur AS
        WITH lib AS (SELECT ministere, any_value(portefeuille) AS libelle FROM membre_gouvernement GROUP BY 1),
        pres AS (   -- présentateurs : cosignataires, et auteur membre qui n'est pas Premier ministre
            SELECT c.*,
                   CASE WHEN c.tutelle_statut = 'sans_objet' THEN [c.ministere]
                        WHEN c.tutelle_statut IN ('etabli', 'decision', 'co_tutelle') THEN c.ministeres_tutelle
                   END AS ministeres
            FROM _dg_cite c
            WHERE c.cosignataire OR (c.mandat IS NOT NULL AND NOT c.premier_ministre)),
        rang AS (   -- ministères dans l'ordre des présentateurs, puis de leurs tutelles
            SELECT dossier, ministere_porteur, min((ordre, mandat, k)) AS pos FROM (
                SELECT dossier, ordre, mandat, unnest(ministeres) AS ministere_porteur,
                       unnest(range(1, len(ministeres) + 1)) AS k
                FROM pres WHERE ministeres IS NOT NULL)
            GROUP BY 1, 2),
        mins AS (
            SELECT r.dossier, list(r.ministere_porteur ORDER BY r.pos) AS ministeres_porteurs,
                   list(coalesce(l.libelle, r.ministere_porteur) ORDER BY r.pos) AS ministeres_porteurs_libelles
            FROM rang r LEFT JOIN lib l ON l.ministere = r.ministere_porteur GROUP BY 1),
        agg AS (
            SELECT p.dossier,
                   bool_or(pr.acteur IS NOT NULL AND pr.mandat IS NULL) AS hors_gouvernement,
                   bool_or(pr.mandat IS NOT NULL AND pr.ministeres IS NULL) AS non_rattache,
                   count(pr.acteur) AS nb_presentateurs
            FROM _dg_projet p LEFT JOIN pres pr USING (dossier)
            WHERE p.gouvernement IS NOT NULL GROUP BY 1),
        ordre_pres AS (
            SELECT dossier, list(acteur ORDER BY ordre) AS presentateurs FROM (
                SELECT dossier, acteur, min(ordre) AS ordre FROM pres GROUP BY 1, 2) GROUP BY 1),
        portef AS (
            SELECT dossier, list(ministere ORDER BY ordre, mandat) AS portefeuilles_presentateurs,
                   list(portefeuille ORDER BY ordre, mandat) AS portefeuilles_presentateurs_libelles
            FROM pres WHERE mandat IS NOT NULL GROUP BY 1),
        pm AS (SELECT dossier, bool_or(auteur AND premier_ministre) AS pm_auteur FROM _dg_cite GROUP BY 1)
        SELECT a.dossier, o.presentateurs, pf.portefeuilles_presentateurs,
               pf.portefeuilles_presentateurs_libelles,
               CASE WHEN r.raison IS NULL THEN m.ministeres_porteurs END AS ministeres_porteurs,
               CASE WHEN r.raison IS NULL THEN m.ministeres_porteurs_libelles END AS ministeres_porteurs_libelles,
               CASE WHEN r.raison IS NULL AND len(m.ministeres_porteurs) = 1 THEN m.ministeres_porteurs[1]
               END AS ministere_porteur,
               CASE WHEN r.raison IS NULL AND len(m.ministeres_porteurs) = 1 THEN m.ministeres_porteurs_libelles[1]
               END AS ministere_porteur_libelle,
               r.raison
        FROM agg a
        LEFT JOIN mins m USING (dossier)
        LEFT JOIN ordre_pres o USING (dossier)
        LEFT JOIN portef pf USING (dossier)
        LEFT JOIN pm USING (dossier)
        CROSS JOIN LATERAL (SELECT CASE
            WHEN a.nb_presentateurs = 0 AND coalesce(pm.pm_auteur, false) THEN 'seul_le_premier_ministre_cite'
            WHEN a.nb_presentateurs = 0 THEN 'aucun_membre_du_gouvernement_cite'
            WHEN a.hors_gouvernement THEN 'presentateur_hors_gouvernement_a_la_date'
            WHEN a.non_rattache OR m.ministeres_porteurs IS NULL THEN 'rattachement_non_etabli'
            END AS raison) r""")
