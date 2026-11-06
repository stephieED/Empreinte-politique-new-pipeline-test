"""R-AMENDEMENT : un amendement compté une fois, son sort normalisé, la commission et le dossier
visés, et ses signatures à part (doc. 1, 1.5.3 et 1.6, R-AMENDEMENT et R-SORT-AMENDEMENT ; cahier
2.1, 3.1.3, 4.2 ; mesures `an-amendements-cr.md`, 3.2 à 3.4).

**Copies.** Un même amendement peut exister sous deux uid (copie `B` du texte déposé, copie `BTC`
du texte de la commission : 346 paires dans l'archive XVIIe). Clé : (`examen`, `numero_long`). La
copie retenue est celle dont l'uid commence comme l'examen (`EXANR…BTC2755…` → `AMANR…BTC2755…`),
sinon la plus récente par `chronotag` ; l'autre uid reste un **alias** (`alias`). La liste de
signatures qui fait foi est celle de la copie retenue ; si deux copies divergeaient (auteur,
cosignataires, état, sous-état, sort), `copies_divergentes` le dit (alerte A4) : jamais observé
en XVIIe.

**Sort** : la source ne remplit `sort` que pour les amendements discutés ; l'issue se lit dans le
couple (état, sous-état), par la table `SORTS` ci-dessous, publiée sur la page de méthodologie.
Les irrecevabilités au titre de l'article 40 (famille `irrecevable_40`) et de l'article 45
(`irrecevable_45`) sont comptées à part. Un couple absent de la table : « sort non établi ».
Aucun taux d'adoption n'est calculé (cahier 2.1).

**Commission** : l'organe d'examen quand c'est une commission (permanente ou spéciale) ; en
séance, la matière du dossier visé (R-MATIERE). **Dossier** : celui du document visé (un
amendement vise un document, pas un dossier) ; les 170 amendements du dossier `incorrect_data`
visent un document absent des dossiers : dossier non établi.

**Banc de l'auteur au dépôt** : la position déclarée du groupe de l'auteur à la date de dépôt
(appartenance à la date, R-APPARTENANCE) ; « non déclaré » en XVIIe (aucun groupe ne déclare).

**Adresse publique** : la source ne donne qu'un chemin relatif (`document_uri`) sans hôte ;
aucune adresse de page n'est vérifiable dans les données : `source_url` reste vide, avec la
raison, et l'identifiant de l'amendement est servi.

Sorties :
- `amendement_canonique` : une ligne par amendement (copies dédoublonnées), `acteur` = auteur
  principal (vide pour le gouvernement, `type_auteur` le dit) ;
- `amendement_auteur` : une ligne par signature (auteur ou cosignataire) d'un amendement retenu ;
  une personne citée deux fois dans la même liste ne signe qu'une fois."""

NOM = "R-AMENDEMENT"
VERSION = 1
DEPEND = ("R-MATIERE", "R-APPARTENANCE")
SORTIES = ("amendement_canonique", "amendement_auteur")

# (code d'état, libellé du sous-état ou « * », sort normalisé, famille). Lue dans l'ordre : la
# première ligne qui convient s'applique. Couples relevés dans l'archive XVIIe (cahier 3.1.3).
SORTS = [
    ("DI", "Adopté", "adopte", "discute"),
    ("DI", "Rejeté", "rejete", "discute"),
    ("DI", "Tombé", "tombe", "discute"),
    ("DI", "Non soutenu", "non_soutenu", "discute"),
    ("DI", "Retiré", "retire", "retire"),                       # retiré au moment de la discussion
    ("RT", "Retiré avant publication", "retire_avant_publication", "retire"),
    ("RT", "*", "retire", "retire"),                            # après publication, ou sous-état « R »
    ("IR", "*", "irrecevable", "irrecevable_40"),               # « Irrecevable 40 » : charge, gage, crédits…
    ("IRRAIF", "*", "irrecevable", "irrecevable_40"),           # « Autre irrecevabilité 40 »
    ("IRR45", "*", "irrecevable", "irrecevable_45"),            # cavalier, entonnoir (article 45)
    ("IRR%", "*", "irrecevable", "irrecevable_autre"),          # doublon, hors champ, articles 37, 38, 41…
    ("ET", "*", "en_traitement", "en_cours"),
    ("AC", "*", "a_discuter", "en_cours"),
    ("effacé", "*", "efface", "efface"),
]

DESCRIPTION = (
    "Un amendement est compté une fois. L'Assemblée publie parfois le même amendement sous deux "
    "identifiants (texte déposé et texte de la commission) : ils sont reconnus à leur examen et à "
    "leur numéro, la copie retenue est celle du texte examiné, l'autre identifiant reste un alias. "
    "Un amendement cosigné compte une fois ; les signatures sont comptées à part, sous ce nom. Le "
    "sort d'un amendement se lit dans le couple (état, sous-état) publié, selon cette table : "
    + "; ".join(f"{e} / {'tout sous-état' if se == '*' else se} → {s} ({f})" for e, se, s, f in SORTS)
    + ". Les irrecevabilités au titre de l'article 40 (charges, gages, crédits…) et de l'article 45 "
    "(cavaliers, entonnoir) sont comptées à part. La commission est celle qui examine l'amendement ; "
    "en séance, c'est la commission saisie au fond du texte visé. Aucun taux d'adoption n'est "
    "calculé. Le banc de l'auteur au dépôt est celui que déclare son groupe ; en XVIIe, aucun groupe "
    "n'en déclare : « non déclaré ».")


def _q(s):
    return "'" + s.replace("'", "''") + "'"


def table_sorts() -> str:
    """La table SORTS en SQL (VALUES), avec son rang de priorité."""
    return "(VALUES " + ", ".join(f"({k}, {_q(e)}, {_q(se)}, {_q(s)}, {_q(f)})"
                                  for k, (e, se, s, f) in enumerate(SORTS)) + \
           ") AS t(priorite, etat_code, sous_etat, sort, famille)"


def appliquer(ctx):
    ctx.x(f"""CREATE OR REPLACE TEMP TABLE _am AS
        WITH sig AS (
            SELECT amendement, list(acteur ORDER BY rang) FILTER (role = 'cosignataire') AS cosignataires
            FROM an_amendements__signature GROUP BY 1),
        a AS (   -- colonnes utiles seulement : l'exposé et le dispositif pèsent 220 millions de caractères
            SELECT a.uid, a.examen, a.numero_long, a.chronotag, a.auteur, a.type_auteur, a.groupe_auteur,
                   a.date_depot, a.date_sort, a.etat_code, a.etat, a.sous_etat, a.sort, a.document,
                   a.organe_examen, a.organe_rapporteur, a.amendement_parent, a.article_designation,
                   a.mission, a.document_uri,
                   a.expose_sommaire IS NULL AND a.dispositif IS NULL AS sans_texte, s.cosignataires,
                   starts_with(a.uid, replace(a.examen, 'EXANR', 'AMANR')) AS copie_de_l_examen,
                   count(*) OVER (PARTITION BY a.examen, a.numero_long) AS nb_copies,
                   count(DISTINCT md5(concat_ws('|', a.auteur, a.etat_code, a.sous_etat, a.sort,
                                                array_to_string(s.cosignataires, ','))))
                       OVER (PARTITION BY a.examen, a.numero_long) AS nb_versions
            FROM an_amendements__amendement a LEFT JOIN sig s ON s.amendement = a.uid)
        SELECT *,
               row_number() OVER (PARTITION BY examen, numero_long
                                  ORDER BY copie_de_l_examen DESC, TRY_CAST(chronotag AS BIGINT) DESC NULLS LAST,
                                           uid DESC) AS rang_copie,
               list(uid) OVER (PARTITION BY examen, numero_long) AS uids
        FROM a""")
    ctx.ecrire("amendement_canonique", f"""
        WITH c AS (SELECT * FROM _am WHERE rang_copie = 1),
        so AS (
            SELECT c.uid, arg_min(t.sort, t.priorite) AS sort, arg_min(t.famille, t.priorite) AS famille
            FROM c JOIN {table_sorts()}
              ON c.etat_code LIKE t.etat_code AND (t.sous_etat = '*' OR c.sous_etat = t.sous_etat)
            GROUP BY 1),
        doc AS (SELECT DISTINCT uid, dossier FROM an_dossiers__document),
        org AS (SELECT uid, type_organe, coalesce(libelle, libelle_abrege) AS libelle
                FROM an_acteurs__organe QUALIFY row_number() OVER (PARTITION BY uid ORDER BY prov_point DESC) = 1),
        app AS (
            SELECT c.uid, a.groupe, g.position_declaree
            FROM c JOIN appartenance a ON a.acteur = c.auteur AND c.date_depot >= a.debut
                                      AND c.date_depot <= coalesce(a.fin, '9999-12-31')
            JOIN groupe g ON g.organe = a.groupe
            QUALIFY row_number() OVER (PARTITION BY c.uid ORDER BY a.debut DESC) = 1),
        x AS (
            SELECT c.*, so.sort AS sort_normalise, so.famille, d.dossier AS dossier_document,
                   o.type_organe AS type_organe_examen, o.libelle AS libelle_organe_examen,
                   app.groupe AS groupe_au_depot, app.position_declaree AS banc_groupe
            FROM c LEFT JOIN so USING (uid) LEFT JOIN doc d ON d.uid = c.document
            LEFT JOIN org o ON o.uid = c.organe_examen LEFT JOIN app USING (uid))
        SELECT x.auteur AS acteur, x.uid AS amendement, x.type_auteur, x.date_depot,
               coalesce(x.sort_normalise, 'non_etabli') AS sort, coalesce(x.famille, 'non_etablie') AS famille_sort,
               x.etat_code, x.etat, x.sous_etat, x.sort AS sort_source,
               CASE WHEN x.type_organe_examen IN ('COMPER', 'CNPS') THEN x.organe_examen
                    WHEN x.type_organe_examen = 'ASSEMBLEE' AND m.statut = 'assemblee' THEN m.commission
               END AS commission,
               CASE WHEN x.type_organe_examen IN ('COMPER', 'CNPS') THEN x.libelle_organe_examen
                    WHEN x.type_organe_examen = 'ASSEMBLEE' THEN m.libelle END AS commission_libelle,
               CASE WHEN x.type_organe_examen IN ('COMPER', 'CNPS') THEN 'organe_examen'
                    WHEN x.type_organe_examen = 'ASSEMBLEE' AND m.statut = 'assemblee' THEN 'matiere_du_dossier'
               END AS commission_source,
               CASE WHEN x.type_organe_examen IN ('COMPER', 'CNPS') THEN NULL
                    WHEN x.type_organe_examen = 'ASSEMBLEE' AND m.statut = 'assemblee' THEN NULL
                    WHEN x.type_organe_examen = 'ASSEMBLEE' AND x.dossier_document IS NULL THEN 'dossier_non_etabli'
                    WHEN x.type_organe_examen = 'ASSEMBLEE' THEN 'matiere_' || coalesce(m.statut, 'non_etablie')
                    ELSE 'organe_examen_inconnu' END AS raison_commission,
               x.dossier_document AS dossier,
               CASE WHEN x.dossier_document IS NULL THEN 'document_vise_absent_des_dossiers' END AS raison_dossier,
               x.document, x.examen, x.numero_long, x.organe_examen, x.type_organe_examen AS type_organe_examen,
               x.amendement_parent IS NOT NULL AS sous_amendement, x.amendement_parent,
               x.nb_copies, list_filter(x.uids, lambda u: u <> x.uid) AS alias,
               x.nb_versions > 1 AS copies_divergentes,
               coalesce(len(x.cosignataires), 0) AS nb_cosignataires_liste,
               x.groupe_auteur AS groupe_auteur_source, x.groupe_au_depot,
               CASE WHEN x.auteur IS NULL THEN NULL
                    ELSE coalesce(x.banc_groupe, 'non_declaree') END AS banc_au_depot,
               CASE WHEN x.auteur IS NULL THEN 'pas_d_auteur_personne'
                    WHEN x.groupe_au_depot IS NULL THEN 'sans_groupe_a_la_date'
                    WHEN x.banc_groupe = 'non_declaree' THEN 'position_non_declaree_par_le_groupe' END AS raison_banc,
               x.organe_rapporteur, x.article_designation, x.mission, x.date_sort,
               x.sans_texte,
               x.document_uri, NULL::VARCHAR AS source_url,
               'adresse_non_publiee_dans_les_donnees' AS raison_source_url
        FROM x LEFT JOIN matiere m ON m.dossier = x.dossier_document
        ORDER BY x.uid""")
    ctx.ecrire("amendement_auteur", """
        WITH s AS (
            SELECT s.amendement, s.acteur,
                   CASE WHEN bool_or(s.role = 'auteur') THEN 'auteur' ELSE 'cosignataire' END AS role,
                   min(s.rang) AS rang, count(*) AS nb_mentions
            FROM an_amendements__signature s
            WHERE s.amendement IN (SELECT amendement FROM amendement_canonique)
            GROUP BY 1, 2)
        SELECT s.acteur, s.amendement, s.role, s.rang, s.nb_mentions > 1 AS cite_plusieurs_fois,
               c.type_auteur, c.date_depot, c.sort, c.famille_sort, c.commission, c.dossier, c.document
        FROM s JOIN amendement_canonique c USING (amendement)
        ORDER BY s.acteur, c.date_depot, s.amendement""")
    ctx.x("DROP TABLE IF EXISTS _am")
    r = ctx.x("""SELECT count(*), count(*) FILTER (sort <> 'non_etabli'),
                        count(*) FILTER (commission IS NOT NULL), count(*) FILTER (dossier IS NOT NULL),
                        count(*) FILTER (nb_copies > 1), count(*) FILTER (copies_divergentes),
                        count(*) FILTER (famille_sort = 'irrecevable_40'),
                        count(*) FILTER (famille_sort = 'irrecevable_45'),
                        count(*) FILTER (acteur IS NOT NULL),
                        count(*) FILTER (banc_au_depot IS NOT NULL AND banc_au_depot <> 'non_declaree')
                 FROM amendement_canonique""")[0]
    uids = ctx.un("SELECT count(*) FROM an_amendements__amendement")
    return {"amendements_distincts_sur_uid": (r[0], uids), "sort_etabli": (r[1], r[0]),
            "commission_etablie": (r[2], r[0]), "dossier_etabli": (r[3], r[0]),
            "amendement_avec_copie": (r[4], r[0]), "copies_divergentes": (r[5], r[4]),
            "irrecevable_article_40": (r[6], r[0]), "irrecevable_article_45": (r[7], r[0]),
            "banc_au_depot_declare": (r[9], r[8])}
