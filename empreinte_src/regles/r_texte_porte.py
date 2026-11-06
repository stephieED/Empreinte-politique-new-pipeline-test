"""R-TEXTE-PORTE : les textes portés par une personne (doc. 1, 1.5.3 et 1.6 ; cahier 2.1, 3.1.4,
4.2 « Ce que cette personne a proposé » et 4.6 « Rôle sur un texte porté »).

Une ligne par (acteur, dossier, document, rôle), calculée pour tous les acteurs ; la fiche filtre.
Trois sources, lues telles que l'Assemblée les publie :

| rôle | preuve |
| --- | --- |
| `auteur` | qualité « auteur » d'un document **proposition** (`PION` : proposition de loi, `PNRE` : proposition de résolution), lue dans les auteurs du document |
| `cosignataire` | liste des cosignataires du document (avec date de cosignature et de retrait) |
| `rapporteur` | acte de nomination des rapporteurs (`NominRapporteurs_Type`) du dossier ; le type publié (rapporteur, pour avis, spécial, général) est gardé |
| `initiative_gouvernementale` | qualité « auteur » d'un **projet** de loi (`PRJL`) : le projet est déposé au nom du gouvernement, ce n'est **jamais** un acte personnel du ministre qui le présente ; le gouvernement du premier dépôt (R-DEPOT-GOUVERNEMENT) est servi |

La nature se lit dans le préfixe de l'identifiant du document, jamais dans le titre. L'étape
atteinte est la plus haute des législatures où le dossier a avancé (R-ETAPE : un acte qui s'est
passé, jamais un code « COM ») ; le sort est celui du dossier (R-SORT-FINAL), le 49.3 nommé à part.

**Publiable** (cahier 2.1) : seulement à partir de l'examen en commission, c'est-à-dire quand
l'étape atteinte vaut au moins `examen_commission`. Une cosignature retirée n'est pas publiable
(raison `cosignature_retiree`). La règle ne calcule aucun taux."""

NOM = "R-TEXTE-PORTE"
VERSION = 1
DEPEND = ("R-ETAPE", "R-SORT-FINAL", "R-MATIERE", "R-DEPOT-GOUVERNEMENT")
SORTIES = ("texte_porte",)
DESCRIPTION = (
    "Un texte porté par une personne est une proposition de loi ou de résolution dont elle est "
    "l'auteur ou un cosignataire, ou un texte dont elle a été nommée rapporteur, tel que le publie "
    "le dossier législatif de l'Assemblée. Un projet de loi est déposé au nom du gouvernement : il "
    "est présenté comme une initiative gouvernementale, jamais comme l'acte personnel du ministre "
    "qui le signe. La nature du texte se lit dans l'identifiant du document déposé, jamais dans son "
    "titre. Un texte porté n'est publié qu'à partir de son examen en commission, lu dans ce qui "
    "s'est effectivement passé (réunion tenue, rapport déposé), jamais dans la seule saisine. Une "
    "cosignature retirée n'est pas publiée. Le sort est celui du dossier ; l'adoption par "
    "l'article 49, alinéa 3, est signalée à part.")

# Nature lue dans le préfixe du document (cahier 3.1.4).
NATURE = """CASE left({d}, 4) WHEN 'PION' THEN 'proposition_de_loi' WHEN 'PNRE' THEN 'proposition_de_resolution'
                              WHEN 'PRJL' THEN 'projet_de_loi' END"""
RANG_EXAMEN_COMMISSION = 2          # échelle de R-ETAPE : 1 dépôt, 2 examen en commission, 3 séance…


def appliquer(ctx):
    nature = NATURE.format(d="t.document")
    ctx.x(f"""CREATE OR REPLACE TEMP TABLE _tp AS
        WITH doc AS (
            SELECT uid AS document, dossier, left(date_depot, 10) AS date_depot, chambre,
                   legislature, sous_type_code, prov_url, auteurs_acteurs, auteurs_qualites
            FROM an_dossiers__document
            WHERE profondeur = 0 AND left(uid, 4) IN ('PION', 'PNRE', 'PRJL')),
        auteurs AS (   -- les listes d'acteurs et de qualités vont de pair (même rang)
            SELECT * FROM (
                SELECT d.*, unnest(d.auteurs_acteurs) AS acteur, unnest(d.auteurs_qualites) AS qualite,
                       unnest(range(1, len(d.auteurs_acteurs) + 1)) AS rang
                FROM doc d)
            WHERE qualite = 'auteur' AND acteur IS NOT NULL),
        r_auteur AS (
            SELECT acteur, dossier, document,
                   CASE WHEN left(document, 4) = 'PRJL' THEN 'initiative_gouvernementale' ELSE 'auteur' END AS role,
                   NULL AS qualite_source, rang, date_depot AS date_role, NULL AS date_retrait,
                   NULL AS acte, chambre, prov_url AS source_url
            FROM auteurs),
        r_cosig AS (
            SELECT c.acteur, d.dossier, d.document, 'cosignataire' AS role, NULL AS qualite_source,
                   c.rang, left(c.date_cosignature, 10) AS date_role, left(c.date_retrait, 10) AS date_retrait,
                   NULL AS acte, d.chambre, d.prov_url AS source_url
            FROM an_dossiers__cosignature c JOIN doc d ON d.document = c.document
            WHERE c.acteur IS NOT NULL AND left(d.document, 4) IN ('PION', 'PNRE')),
        depot AS (   -- texte du premier dépôt du dossier (servi aux rapporteurs)
            SELECT dossier, arg_min(texte_associe, coalesce(date, '9999') || uid) AS document
            FROM an_dossiers__acte WHERE type_acte = 'DepotInitiative_Type' AND texte_associe IS NOT NULL
            GROUP BY 1),
        nomin AS (
            SELECT a.dossier, a.uid, a.date, a.code, a.prov_url,
                   unnest(a.rapporteurs) AS acteur, unnest(a.rapporteurs_types) AS type
            FROM an_dossiers__acte a WHERE a.type_acte = 'NominRapporteurs_Type'),
        r_rapp AS (
            SELECT a.acteur, a.dossier, p.document, 'rapporteur' AS role, a.type AS qualite_source,
                   NULL::BIGINT AS rang, left(a.date, 10) AS date_role, NULL AS date_retrait,
                   a.uid AS acte,
                   CASE WHEN a.code LIKE 'SN%' THEN 'SN' WHEN a.code LIKE 'AN%' THEN 'AN' END AS chambre,
                   a.prov_url AS source_url
            FROM nomin a LEFT JOIN depot p ON p.dossier = a.dossier
            WHERE a.acteur IS NOT NULL)
        SELECT * FROM r_auteur UNION ALL SELECT * FROM r_cosig UNION ALL
        -- Un rapporteur nommé plusieurs fois sur un dossier (réouverture, lecture suivante) : une
        -- ligne par dossier et type, datée de la première nomination.
        SELECT acteur, dossier, any_value(document), role, qualite_source, NULL, min(date_role), NULL,
               arg_min(acte, date_role), arg_min(chambre, date_role), arg_min(source_url, date_role)
        FROM r_rapp GROUP BY acteur, dossier, role, qualite_source""")

    ctx.ecrire("texte_porte", f"""
        WITH et AS (
            SELECT dossier, max(rang_etape) AS rang, arg_max(etape_atteinte, rang_etape) AS etape,
                   arg_max(date_etape, rang_etape) AS date_etape
            FROM etape_dossier WHERE rang_etape IS NOT NULL GROUP BY 1),
        so AS (SELECT dossier, any_value(sort) AS sort, any_value(raison_sort) AS raison_sort,
                      bool_or(par_49_3) AS par_49_3, bool_or(adopte_par_49_3) AS adopte_par_49_3,
                      any_value(titre) AS titre
               FROM etat_dossier GROUP BY 1),
        doc AS (SELECT uid, left(date_depot, 10) AS date_depot, sous_type_code
                FROM an_dossiers__document WHERE profondeur = 0)
        SELECT t.acteur, t.dossier, t.document, t.role, t.qualite_source AS qualite_rapporteur,
               {nature} AS nature, left(t.document, 4) AS nature_code, d.sous_type_code AS sous_nature_code,
               d.date_depot, t.date_role, t.date_retrait, t.rang, t.chambre,
               coalesce(et.etape, 'non_etablie') AS etape_atteinte, et.rang AS rang_etape, et.date_etape,
               coalesce(so.sort, 'non_connu') AS sort, so.raison_sort,
               coalesce(so.par_49_3, false) AS par_49_3, coalesce(so.adopte_par_49_3, false) AS adopte_par_49_3,
               m.commission AS matiere, m.statut AS matiere_statut, m.libelle AS matiere_libelle,
               CASE WHEN t.role = 'initiative_gouvernementale' THEN pg.gouvernement END AS gouvernement,
               t.date_retrait IS NULL AND coalesce(et.rang, 0) >= {RANG_EXAMEN_COMMISSION} AS publiable,
               CASE WHEN t.date_retrait IS NOT NULL THEN 'cosignature_retiree'
                    WHEN et.rang IS NULL THEN 'etape_non_etablie'
                    WHEN et.rang < {RANG_EXAMEN_COMMISSION} THEN 'pas_encore_examine_en_commission'
               END AS raison_non_publiable,
               so.titre, t.acte, t.source_url
        FROM _tp t
        LEFT JOIN doc d ON d.uid = t.document
        LEFT JOIN et ON et.dossier = t.dossier
        LEFT JOIN so ON so.dossier = t.dossier
        LEFT JOIN matiere m ON m.dossier = t.dossier
        LEFT JOIN projet_gouvernement pg ON pg.document = t.document
        -- Une personne citée deux fois dans la même liste (auteurs d'un document du Sénat : 71 fois
        -- en XVIIe ; cosignataires : 1 fois) : une seule ligne, au premier rang.
        QUALIFY row_number() OVER (PARTITION BY t.acteur, t.dossier, t.document, t.role, t.qualite_source
                                   ORDER BY t.rang NULLS LAST, t.date_role) = 1
        ORDER BY t.acteur, d.date_depot, t.dossier, t.role""")
    ctx.x("DROP TABLE IF EXISTS _tp")
    r = ctx.x("""SELECT count(*), count(*) FILTER (etape_atteinte <> 'non_etablie'),
                        count(*) FILTER (publiable),
                        count(*) FILTER (role = 'initiative_gouvernementale'),
                        count(*) FILTER (role = 'initiative_gouvernementale' AND gouvernement IS NOT NULL),
                        count(*) FILTER (matiere_statut IN ('assemblee', 'senat_seulement')),
                        count(*) FILTER (sort <> 'non_connu')
                 FROM texte_porte""")[0]
    return {"etape_etablie": (r[1], r[0]), "publiable_examine_en_commission": (r[2], r[0]),
            "initiative_gouvernementale_gouvernement_etabli": (r[4], r[3]),
            "matiere_etablie": (r[5], r[0]), "sort_connu": (r[6], r[0])}
