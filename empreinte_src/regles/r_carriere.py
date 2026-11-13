"""R-CARRIERE : la frise de carrière de chaque candidat, par institution (cahier 4.2, « En bref » ;
doc. 1, 1.5.1 et 1.6).

Une ligne par période, toutes institutions :

- **Assemblée** (`assemblee`) : les mandats de député de R-DEPUTES (archive des acteurs, toutes
  législatures depuis le 19/06/2002), datés de la prise de fonction. Un mandat suspendu par
  une entrée au gouvernement donne une ligne `etat = 'suspendu'` entre la fin du mandat
  d'origine et la reprise ; sans reprise publiée, la suspension s'arrête à la fin de la
  législature (un mandat ne lui survit pas), ou reste ouverte si la législature est en cours.
  Chaque période en fonction est découpée par le groupe **à la date** (R-APPARTENANCE ; les
  passages chez les non-inscrits, qui ne sont pas un groupe, sont dits `non_inscrit`). Le siège
  (R-HEMICYCLE) n'est connu que pour la législature en cours, au jour de constat.
- **Gouvernement** (`gouvernement`) : les fonctions de R-COMPOSITION (portefeuille exact,
  qualité), depuis le 17/05/2007.
- **Sénat** (`senat`) : les mandats de sénateur de l'export du Sénat, lus par le matricule
  déclaré (R-CANDIDATURES), découpés par le groupe avec son **libellé à la date** (jamais le
  libellé actuel de l'archive de l'Assemblée). Export absent ou vide : « non collecté ».
- **Parlement européen** (`parlement_europeen`) : les mandats de député européen
  (`MEMBER_PARLIAMENT` dans `org/ep-<n>`) du portail du Parlement européen, lus par
  l'identifiant européen que Wikidata déclare (P1186, point `pe-eurodeputes` ; décision Q3 du
  13/11/2026), découpés par le groupe politique européen à la date, avec son nom de l'époque.
  Le numéro de la législature européenne est dans le libellé, jamais dans `legislature` (qui est
  celle de l'Assemblée).
- **Mandats locaux** (`local`) : R-MANDAT-LOCAL (Répertoire national des élus, depuis 2020 ;
  fin des mandats municipaux 2020-2026 déduite au 15/03/2026 et signalée). Mandats de député
  antérieurs à 2002 : hors source (Sycomore non collecté). Ces absences sont des lignes de `couverture_carriere`, pas des
  périodes inventées.

`lien` ne pointe que vers une fiche publiée : `legislature/<14 à 17>` (module `perimetre`),
`gouvernement/<adresse>` pour un gouvernement publié.
"""
from ..perimetre import LEGISLATURES, LEGISLATURES_GOUVERNEMENTS
from .r_candidatures import vue_ou_vide

NOM = "R-CARRIERE"
VERSION = 3
DEPEND = ("R-IDENTITE", "R-MANDAT-LOCAL", "R-DEPUTES", "R-APPARTENANCE", "R-COMPOSITION", "R-GOUVERNEMENTS",
          "R-HEMICYCLE")
SORTIES = ("carriere", "couverture_carriere")
DESCRIPTION = (
    "La carrière d'un candidat rassemble ses mandats de député (publiés par l'Assemblée "
    "nationale depuis juin 2002), ses fonctions au gouvernement (depuis mai 2007) et ses mandats "
    "de sénateur (publiés par le Sénat) et de député européen (publiés par le Parlement européen, "
    "pour la personne à qui Wikidata déclare un identifiant de député européen), chacun avec ses "
    "dates. Un député entré au gouvernement "
    "voit son mandat suspendu, pas terminé : la frise le montre. Le groupe affiché est celui "
    "auquel il appartenait à chaque date, et pour le Sénat avec le nom que le groupe portait "
    "alors. Les mandats locaux viennent du Répertoire national des élus, depuis 2020. Les mandats de "
    "député antérieurs à 2002 ne sont pas encore collectés : la fiche le dit au lieu de les taire.")
ORDINAL = "CASE WHEN {n} = 1 THEN '1re' ELSE {n} || 'e' END"

LEGISLATURES_PUBLIEES = LEGISLATURES
FIN_OUVERTE = "DATE '9999-12-31'"
URL_DEPUTE = "https://www.assemblee-nationale.fr/dyn/deputes/"
EST_NI = "(o.sigle = 'NI' OR lower(o.libelle) IN ('non inscrit', 'non inscrits', 'non-inscrits'))"


def segments(periodes: str, groupes: str) -> str:
    """Découpe chaque période (`cle`, `per`, `d0`, `d1` en DATE, d1 = 9999-12-31 si ouverte) par
    les périodes de groupe (`per`, `g0`, `g1`, `groupe`, `sigle`, `libelle`, `statut`,
    `priorite`) : un segment par groupe à la date ; sans groupe ce jour-là, groupe vide."""
    return f"""(
        WITH p AS (SELECT * FROM {periodes}),
        g AS (SELECT * FROM {groupes}),
        b AS (SELECT cle, d0 AS b FROM p
              UNION SELECT p.cle, g.g0 FROM p JOIN g ON g.per = p.per AND g.g0 > p.d0 AND g.g0 <= p.d1
              UNION SELECT p.cle, g.g1 + 1 FROM p JOIN g ON g.per = p.per
                     AND g.g1 < {FIN_OUVERTE} AND g.g1 + 1 > p.d0 AND g.g1 + 1 <= p.d1),
        s AS (SELECT cle, b AS s0, lead(b) OVER (PARTITION BY cle ORDER BY b) AS suivant FROM b),
        x AS (SELECT p.*, s.s0, coalesce(CAST(s.suivant - 1 AS DATE), p.d1) AS s1
              FROM p JOIN s USING (cle))
        SELECT x.*, g.groupe, g.sigle, g.libelle AS groupe_libelle, g.statut AS groupe_statut
        FROM x LEFT JOIN g ON g.per = x.per AND g.g0 <= x.s0 AND g.g1 >= x.s0
        QUALIFY row_number() OVER (PARTITION BY x.cle, x.s0
                                   ORDER BY g.priorite NULLS LAST, g.g0 DESC, g.groupe) = 1)"""


def appliquer(ctx):
    publies = ", ".join(str(n) for n in LEGISLATURES_PUBLIEES)
    gouv_publies = ", ".join(str(n) for n in LEGISLATURES_GOUVERNEMENTS)
    mandat_an = vue_ou_vide(ctx, "an_acteurs__mandat", {
        "uid": "VARCHAR", "acteur": "VARCHAR", "type_organe": "VARCHAR", "organe": "VARCHAR",
        "date_debut": "VARCHAR", "date_fin": "VARCHAR", "prov_point": "VARCHAR"})
    organe_an = vue_ou_vide(ctx, "an_acteurs__organe", {
        "uid": "VARCHAR", "sigle": "VARCHAR", "libelle": "VARCHAR", "prov_point": "VARCHAR"})
    ident_an = vue_ou_vide(ctx, "an_acteurs__identite_source", {"uid": "VARCHAR", "civilite": "VARCHAR"})
    senat_cols = {"uid": "VARCHAR", "acteur": "VARCHAR", "nature": "VARCHAR",
                  "type_mandat": "VARCHAR", "type_organe": "VARCHAR", "organe": "VARCHAR",
                  "qualite": "VARCHAR", "date_debut": "VARCHAR", "date_fin": "VARCHAR",
                  "cause_debut": "VARCHAR", "cause_fin": "VARCHAR", "circonscription": "VARCHAR",
                  "libelle_organe": "VARCHAR", "libelle_organe_court": "VARCHAR",
                  "date_libelle": "VARCHAR", "prov_url": "VARCHAR"}
    senat = vue_ou_vide(ctx, "senat_export__mandat", senat_cols)
    ident_sen = vue_ou_vide(ctx, "senat_export__identite_source", {"uid": "VARCHAR", "feminin": "BOOLEAN"})
    senat_collecte = ctx.existe("senat_export__mandat") and ctx.un(
        "SELECT count(*) > 0 FROM senat_export__mandat")
    pe_app = vue_ou_vide(ctx, "pe_eurodeputes__appartenance_pe", {
        "personne": "VARCHAR", "appartenance": "VARCHAR", "organisation": "VARCHAR",
        "classification": "VARCHAR", "role": "VARCHAR", "debut": "VARCHAR", "fin": "VARCHAR",
        "represente": "VARCHAR", "prov_url": "VARCHAR"})
    pe_grp = vue_ou_vide(ctx, "pe_eurodeputes__groupe_pe", {
        "organisation": "VARCHAR", "sigle": "VARCHAR", "libelle": "VARCHAR", "version_de": "VARCHAR"})
    pe_fiche = vue_ou_vide(ctx, "pe_eurodeputes__eurodepute", {"personne": "VARCHAR", "genre": "VARCHAR"})
    pe_collecte = ctx.existe("pe_eurodeputes__eurodepute") and ctx.un(
        "SELECT count(*) > 0 FROM pe_eurodeputes__eurodepute")
    rne_collecte = ctx.existe("rne_elus__mandat_local") and ctx.un(
        "SELECT count(*) > 0 FROM rne_elus__mandat_local")
    loc = vue_ou_vide(ctx, "mandat_local_candidat", {
        "per": "VARCHAR", "fonction": "VARCHAR", "collectivite": "VARCHAR", "debut": "VARCHAR",
        "fin": "VARCHAR", "fin_raison": "VARCHAR", "fichier": "VARCHAR", "code_collectivite": "VARCHAR",
        "source_url": "VARCHAR", "methode": "VARCHAR"})
    # Identité recherchable dans le répertoire : nom, prénom et naissance connus, ou une décision.
    ctx.x(f"""CREATE OR REPLACE TEMP TABLE _car_loc_id AS
        SELECT DISTINCT per FROM personne_identite
        WHERE naissance IS NOT NULL AND nom IS NOT NULL
        UNION SELECT DISTINCT per FROM {loc}""")

    ctx.x("""CREATE OR REPLACE TEMP TABLE _car_c AS
        SELECT per, acteur, matricule_senat, sycomore, acteur_connu_an, eurodepute FROM candidat""")

    # --- Assemblée : périodes en fonction et suspensions ----------------------------------
    ctx.x(f"""CREATE OR REPLACE TEMP TABLE _car_an AS
        WITH d AS (SELECT d.*, c.per, l.fin AS fin_legislature
                   FROM depute d JOIN _car_c c ON c.acteur = d.acteur
                   LEFT JOIN legislature l ON l.numero = d.legislature)
        SELECT per, acteur, mandat || '#f' AS cle, mandat, legislature, 'en_fonction' AS etat,
               debut::DATE AS d0, coalesce(fin::DATE, {FIN_OUVERTE}) AS d1, NULL AS fin_raison,
               circonscription, departement, num_departement, num_circo, cause_fin, source_url
        FROM d WHERE debut IS NOT NULL
        UNION ALL
        SELECT per, acteur, mandat || '#s', mandat, legislature, 'suspendu',
               suspendu_du::DATE,
               coalesce(suspendu_au::DATE, fin_legislature::DATE, {FIN_OUVERTE}),
               CASE WHEN suspendu_au IS NULL AND fin_legislature IS NOT NULL
                    THEN 'aucune reprise publiée : suspension bornée par la fin de la législature'
                    WHEN suspendu_au IS NULL THEN 'aucune reprise publiée à ce jour' END,
               circonscription, departement, num_departement, num_circo, NULL, source_url
        FROM d WHERE suspendu_du IS NOT NULL""")
    ctx.x(f"""CREATE OR REPLACE TEMP TABLE _car_gan AS
        SELECT c.per, a.debut::DATE AS g0, coalesce(a.fin::DATE, {FIN_OUVERTE}) AS g1,
               a.groupe, g.sigle, g.libelle, 'groupe' AS statut, 0 AS priorite
        FROM appartenance a JOIN _car_c c ON c.acteur = a.acteur
        LEFT JOIN groupe g ON g.organe = a.groupe
        UNION ALL
        SELECT c.per, m.date_debut::DATE, coalesce(m.date_fin::DATE, {FIN_OUVERTE}),
               m.organe, 'NI', 'Non inscrit', 'non_inscrit', 1
        FROM (SELECT * FROM {mandat_an} QUALIFY row_number() OVER (PARTITION BY uid ORDER BY prov_point DESC) = 1) m
        JOIN _car_c c ON c.acteur = m.acteur
        JOIN (SELECT * FROM {organe_an} QUALIFY row_number() OVER (PARTITION BY uid ORDER BY prov_point DESC) = 1) o
          ON o.uid = m.organe
        WHERE m.type_organe = 'GP' AND {EST_NI} AND m.date_debut IS NOT NULL""")
    ctx.x(f"""CREATE OR REPLACE TEMP TABLE _car_an_seg AS
        SELECT * FROM {segments("(SELECT * FROM _car_an WHERE etat = 'en_fonction')", "_car_gan")}
        UNION ALL BY NAME
        SELECT *, d0 AS s0, d1 AS s1, NULL::VARCHAR AS groupe, NULL::VARCHAR AS sigle,
               NULL::VARCHAR AS groupe_libelle, 'sans_objet' AS groupe_statut
        FROM _car_an WHERE etat = 'suspendu'""")

    # --- Sénat : mandats de sénateur, groupe et libellé à la date --------------------------
    ctx.x(f"""CREATE OR REPLACE TEMP TABLE _car_sen AS
        SELECT c.per, m.acteur, m.uid || '#f' AS cle, m.uid AS mandat, 'en_fonction' AS etat,
               m.date_debut::DATE AS d0, coalesce(m.date_fin::DATE, {FIN_OUVERTE}) AS d1,
               m.circonscription, m.cause_debut, m.cause_fin, m.prov_url AS source_url
        FROM {senat} m JOIN _car_c c ON m.acteur = 'senat:' || c.matricule_senat
        WHERE m.nature = 'mandat' AND m.date_debut IS NOT NULL""")
    # Suspension au Sénat : un mandat clos pour entrer au gouvernement, puis un mandat de
    # reprise de la même personne ; sans reprise, pas de suspension (le mandat est fini).
    ctx.x("""CREATE OR REPLACE TEMP TABLE _car_sen_susp AS
        SELECT o.per, o.acteur, o.mandat || '#s' AS cle, o.mandat, 'suspendu' AS etat,
               CAST(o.d1 + 1 AS DATE) AS s0, CAST(min(r.d0) - 1 AS DATE) AS s1,
               o.circonscription, NULL AS cause_fin, o.source_url
        FROM _car_sen o JOIN _car_sen r ON r.acteur = o.acteur AND r.d0 > o.d1
             AND r.cause_debut ILIKE 'reprise%'
        WHERE o.cause_fin ILIKE '%gouvernement%'
        GROUP BY ALL""")
    ctx.x(f"""CREATE OR REPLACE TEMP TABLE _car_gsen AS
        SELECT c.per, coalesce(m.date_debut::DATE, DATE '1000-01-01') AS g0,
               coalesce(m.date_fin::DATE, {FIN_OUVERTE}) AS g1, m.organe AS groupe,
               m.libelle_organe_court AS sigle, m.libelle_organe AS libelle,
               CASE WHEN m.type_organe = 'GRPPOLNI' OR m.organe = 'senat:grppol:AUCUN' THEN 'non_inscrit'
                    WHEN m.libelle_organe IS NULL THEN 'libelle_non_date' ELSE 'groupe' END AS statut,
               0 AS priorite
        FROM {senat} m JOIN _car_c c ON m.acteur = 'senat:' || c.matricule_senat
        WHERE m.nature = 'appartenance' AND m.type_organe IN ('GRPPOL', 'GRPPOLNI')""")

    # --- Parlement européen : mandats de député européen et groupe politique à la date ----------
    ctx.x(f"""CREATE OR REPLACE TEMP TABLE _car_pe AS
        SELECT DISTINCT c.per, a.personne AS acteur, a.appartenance || '#f' AS cle, a.appartenance AS mandat,
               'en_fonction' AS etat, a.debut::DATE AS d0, coalesce(a.fin::DATE, {FIN_OUVERTE}) AS d1,
               try_cast(replace(a.organisation, 'org/ep-', '') AS INTEGER) AS legislature_pe,
               a.represente, a.prov_url AS source_url
        FROM {pe_app} a JOIN _car_c c ON a.personne = c.eurodepute
        WHERE a.role = 'MEMBER_PARLIAMENT' AND a.organisation LIKE 'org/ep-%' AND a.debut IS NOT NULL""")
    # Un même groupe tenu sans interruption sous plusieurs rôles (membre, puis coprésident le
    # lendemain) est une seule période : les périodes contiguës d'un même organe sont fusionnées.
    ctx.x(f"""CREATE OR REPLACE TEMP TABLE _car_gpe AS
        WITH a AS (
            SELECT DISTINCT c.per, x.organisation AS groupe, x.debut::DATE AS g0,
                   coalesce(x.fin::DATE, {FIN_OUVERTE}) AS g1
            FROM {pe_app} x JOIN _car_c c ON x.personne = c.eurodepute
            WHERE x.classification = 'EU_POLITICAL_GROUP' AND x.debut IS NOT NULL),
        b AS (SELECT *, max(g1) OVER (PARTITION BY per, groupe ORDER BY g0, g1
                                      ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING) AS fin_avant
              FROM a),
        i AS (SELECT *, sum(CASE WHEN fin_avant IS NULL OR g0 > fin_avant + 1 THEN 1 ELSE 0 END)
                            OVER (PARTITION BY per, groupe ORDER BY g0, g1) AS ilot
              FROM b),
        f AS (SELECT per, groupe, min(g0) AS g0, max(g1) AS g1 FROM i GROUP BY per, groupe, ilot)
        SELECT f.per, f.g0, f.g1, f.groupe, g.sigle, g.libelle,
               CASE WHEN g.version_de = 'org/NI' THEN 'non_inscrit'
                    WHEN g.libelle IS NULL THEN 'non_etabli' ELSE 'groupe' END AS statut,
               0 AS priorite
        FROM f LEFT JOIN (SELECT organisation, any_value(sigle) AS sigle, any_value(libelle) AS libelle,
                                 any_value(version_de) AS version_de FROM {pe_grp} GROUP BY 1) g
          ON g.organisation = f.groupe""")

    ctx.ecrire("carriere", f"""
        WITH an AS (
            SELECT s.per, 'assemblee' AS institution, s.s0 AS d0, s.s1 AS d1,
                   CASE WHEN s.etat = 'suspendu' THEN 'Mandat suspendu (membre du Gouvernement)'
                        ELSE CASE WHEN i.civilite = 'Mme' THEN 'Députée' ELSE 'Député' END
                             || CASE WHEN s.num_circo IS NOT NULL AND s.departement IS NOT NULL
                                     THEN ' de la ' || s.num_circo || CASE WHEN s.num_circo = '1' THEN 're' ELSE 'e' END
                                          || ' circonscription · ' || s.departement ELSE '' END
                   END AS libelle,
                   s.legislature, NULL::VARCHAR AS gouvernement, s.groupe, s.sigle AS groupe_sigle,
                   s.groupe_libelle,
                   CASE WHEN s.etat = 'suspendu' THEN 'sans_objet'
                        ELSE coalesce(s.groupe_statut, 'non_etabli') END AS groupe_statut,
                   h.siege, h.date AS siege_date,
                   CASE WHEN s.etat = 'en_fonction' AND h.siege IS NULL
                        THEN CASE WHEN s.legislature IN (SELECT numero FROM legislature WHERE en_cours)
                                  THEN 'siège non publié à cette date'
                                  ELSE 'siège d''une législature close non connu (archive figée non lue)' END
                        END AS raison_siege,
                   CASE WHEN s.legislature IN ({publies}) THEN 'legislature/' || s.legislature END AS lien,
                   'an' AS source, s.etat, NULL::VARCHAR AS qualite, s.mandat, s.acteur,
                   s.circonscription, s.cause_fin, s.fin_raison,
                   coalesce(s.source_url, '{URL_DEPUTE}' || s.acteur) AS source_url
            FROM _car_an_seg s
            LEFT JOIN (SELECT acteur, any_value(civilite) AS civilite FROM (SELECT uid AS acteur, civilite FROM {ident_an}) GROUP BY 1) i
              ON i.acteur = s.acteur
            LEFT JOIN hemicycle h ON h.acteur = s.acteur AND h.mandat = s.mandat AND s.etat = 'en_fonction'
                 AND h.date::DATE BETWEEN s.s0 AND s.s1),
        gv AS (
            SELECT c.per, 'gouvernement', m.debut::DATE, coalesce(m.fin::DATE, {FIN_OUVERTE}),
                   m.portefeuille, NULL::INTEGER, m.gouvernement, NULL, NULL, NULL, 'sans_objet',
                   NULL::INTEGER, NULL, NULL,
                   CASE WHEN m.gouvernement IN (SELECT gouvernement FROM gouvernement_legislature
                                                WHERE legislature IN ({gouv_publies}))
                        THEN 'gouvernement/' || g.adresse END,
                   'an', 'en_fonction', m.qualite, m.mandat, m.acteur, NULL, NULL, NULL, m.source_url
            FROM membre_gouvernement m JOIN _car_c c ON c.acteur = m.acteur
            LEFT JOIN gouvernement g ON g.organe = m.gouvernement
            WHERE m.debut IS NOT NULL),
        sen AS (
            SELECT s.per, 'senat', s.s0, s.s1,
                   CASE WHEN s.etat = 'suspendu' THEN 'Mandat suspendu (membre du Gouvernement)'
                        WHEN si.feminin THEN 'Sénatrice' ELSE 'Sénateur' END || CASE WHEN s.circonscription IS NOT NULL THEN ' · ' || s.circonscription ELSE '' END,
                   NULL::INTEGER, NULL, s.groupe, s.sigle, s.groupe_libelle,
                   coalesce(s.groupe_statut, 'non_etabli'), NULL::INTEGER, NULL, NULL, NULL,
                   'senat', s.etat, NULL, s.mandat, s.acteur, s.circonscription, s.cause_fin, NULL,
                   s.source_url
            FROM (SELECT * FROM {segments("_car_sen", "_car_gsen")}
                  UNION ALL BY NAME
                  SELECT *, NULL::VARCHAR AS groupe, NULL::VARCHAR AS sigle,
                         NULL::VARCHAR AS groupe_libelle, 'sans_objet' AS groupe_statut
                  FROM _car_sen_susp) s
            LEFT JOIN (SELECT uid, any_value(feminin) AS feminin FROM {ident_sen} GROUP BY 1) si
              ON si.uid = s.acteur),
        pe AS (
            SELECT s.per, 'parlement_europeen', s.s0, s.s1,
                   CASE WHEN f.genre = 'FEMALE' THEN 'Députée européenne' ELSE 'Député européen' END
                   || CASE WHEN s.legislature_pe IS NOT NULL
                           THEN ' · ' || {ORDINAL.format(n="s.legislature_pe")} || ' législature européenne' ELSE '' END
                   || CASE WHEN s.represente IS NOT NULL AND s.represente <> 'FRA' THEN ' · ' || s.represente ELSE '' END,
                   NULL::INTEGER, NULL, s.groupe, s.sigle, s.groupe_libelle,
                   coalesce(s.groupe_statut, 'non_etabli'), NULL::INTEGER, NULL, NULL, NULL,
                   'pe', s.etat, NULL, s.mandat, s.acteur, NULL, NULL, NULL, s.source_url
            FROM {segments("_car_pe", "_car_gpe")} s
            LEFT JOIN (SELECT personne, any_value(genre) AS genre FROM {pe_fiche} GROUP BY 1) f
              ON f.personne = s.acteur),
        loc AS (
            SELECT l.per, 'local', l.debut::DATE, coalesce(l.fin::DATE, {FIN_OUVERTE}),
                   l.fonction || CASE WHEN l.collectivite IS NOT NULL THEN ' · ' || l.collectivite ELSE '' END,
                   NULL::INTEGER, NULL, NULL, NULL, NULL, 'sans_objet', NULL::INTEGER, NULL, NULL, NULL,
                   'rne', 'en_fonction', NULL, l.fichier || ':' || coalesce(l.code_collectivite, ''), NULL,
                   NULL, NULL, l.fin_raison, l.source_url
            FROM {loc} l WHERE l.debut IS NOT NULL)
        SELECT per, institution, strftime(d0, '%Y-%m-%d') AS debut,
               CASE WHEN d1 < {FIN_OUVERTE} THEN strftime(d1, '%Y-%m-%d') END AS fin,
               libelle, legislature, gouvernement, groupe, groupe_sigle, groupe_libelle, groupe_statut,
               siege, siege_date, raison_siege, lien, source, etat, qualite, mandat, acteur,
               circonscription, cause_fin, fin_raison, source_url
        FROM (SELECT * FROM an UNION ALL SELECT * FROM gv UNION ALL SELECT * FROM sen
              UNION ALL SELECT * FROM pe UNION ALL SELECT * FROM loc)
        ORDER BY per, debut, institution""")

    # --- Couverture, candidat par candidat et institution par institution -------------------
    ctx.ecrire("couverture_carriere", f"""
        WITH c AS (SELECT * FROM _car_c),
        n AS (SELECT per, institution, count(*) AS lignes FROM carriere GROUP BY 1, 2),
        i(institution, depuis) AS (VALUES ('assemblee', '2002-06-19'), ('assemblee_avant_2002', NULL),
              ('gouvernement', '2007-05-17'), ('senat', NULL), ('parlement_europeen', NULL), ('local', NULL))
        SELECT c.per, i.institution, i.depuis, coalesce(n.lignes, 0) AS lignes,
            CASE i.institution
              WHEN 'assemblee' THEN CASE WHEN c.acteur IS NULL THEN 'aucun_identifiant'
                                         WHEN NOT coalesce(c.acteur_connu_an, false) THEN 'identifiant_absent_de_la_source'
                                         WHEN n.lignes > 0 THEN 'complet' ELSE 'relu_aucun' END
              WHEN 'assemblee_avant_2002' THEN 'hors_source'
              WHEN 'gouvernement' THEN CASE WHEN c.acteur IS NULL THEN 'aucun_identifiant'
                                            WHEN NOT coalesce(c.acteur_connu_an, false) THEN 'identifiant_absent_de_la_source'
                                            WHEN n.lignes > 0 THEN 'complet' ELSE 'relu_aucun' END
              WHEN 'senat' THEN CASE WHEN c.matricule_senat IS NULL THEN 'aucun_identifiant'
                                     WHEN NOT {str(bool(senat_collecte)).lower()} THEN 'non_collecte'
                                     WHEN n.lignes > 0 THEN 'complet' ELSE 'non_etabli' END
              WHEN 'local' THEN CASE WHEN NOT {str(bool(rne_collecte)).lower()} THEN 'non_collecte'
                                     WHEN c.per NOT IN (SELECT per FROM _car_loc_id) THEN 'non_etabli'
                                     ELSE 'partiel' END
              WHEN 'parlement_europeen' THEN CASE WHEN c.eurodepute IS NULL THEN 'aucun_identifiant'
                                     WHEN NOT {str(bool(pe_collecte)).lower()} THEN 'non_collecte'
                                     WHEN n.lignes > 0 THEN 'complet' ELSE 'non_etabli' END
              ELSE 'non_collecte' END AS statut,
            CASE i.institution
              WHEN 'assemblee' THEN CASE WHEN c.acteur IS NULL THEN 'Aucun identifiant de l''Assemblée déclaré : nos sources ne connaissent aucun mandat de député.'
                                         WHEN NOT coalesce(c.acteur_connu_an, false) THEN 'Identifiant déclaré par Wikidata absent de l''archive de l''Assemblée.'
                                         WHEN n.lignes > 0 THEN 'Mandats depuis le 19/06/2002 (archive des acteurs de l''Assemblée).'
                                         ELSE 'Aucun mandat de député depuis le 19/06/2002 dans l''archive de l''Assemblée.' END
              WHEN 'assemblee_avant_2002' THEN 'Mandats de député antérieurs au 19/06/2002 : hors source (Sycomore non collecté)'
                   || CASE WHEN c.sycomore IS NOT NULL THEN ' ; fiche Sycomore déclarée : ' || c.sycomore ELSE '' END || '.'
              WHEN 'gouvernement' THEN CASE WHEN n.lignes > 0 THEN 'Fonctions depuis le 17/05/2007 (archive des acteurs de l''Assemblée) ; avant : hors source.'
                                            WHEN c.acteur IS NULL THEN 'Aucun identifiant de l''Assemblée déclaré : aucune fonction gouvernementale connue.'
                                            ELSE 'Aucune fonction gouvernementale depuis le 17/05/2007 ; avant : hors source.' END
              WHEN 'senat' THEN CASE WHEN c.matricule_senat IS NULL THEN 'Aucun matricule du Sénat déclaré.'
                                     WHEN NOT {str(bool(senat_collecte)).lower()} THEN 'Export du Sénat non collecté.'
                                     WHEN n.lignes > 0 THEN 'Mandats de sénateur de l''export du Sénat.'
                                     ELSE 'Matricule déclaré, aucun mandat dans l''export du Sénat.' END
              WHEN 'parlement_europeen' THEN CASE WHEN c.eurodepute IS NULL THEN 'Aucun identifiant de député européen déclaré par Wikidata : nos sources ne connaissent aucun mandat au Parlement européen.'
                                     WHEN NOT {str(bool(pe_collecte)).lower()} THEN 'Portail du Parlement européen non collecté.'
                                     WHEN n.lignes > 0 THEN 'Mandats de député européen du portail du Parlement européen, toutes législatures.'
                                     ELSE 'Identifiant européen déclaré, aucun mandat lu dans le portail du Parlement européen.' END
              WHEN 'local' THEN CASE WHEN NOT {str(bool(rne_collecte)).lower()} THEN 'Répertoire national des élus non collecté.'
                                     WHEN c.per NOT IN (SELECT per FROM _car_loc_id) THEN 'Date de naissance inconnue de nos sources : un élu du répertoire, qui n''a pas d''identifiant, ne peut pas être rattaché à cette personne sans décision.'
                                     WHEN n.lignes > 0 THEN 'Mandats en cours et mandats municipaux 2020-2026 du Répertoire national des élus, rattachés par ' || CASE WHEN c.per IN (SELECT per FROM {loc} WHERE methode = 'decision') THEN 'une décision (date de naissance inconnue de nos autres sources)' ELSE 'le nom, le prénom et la date de naissance' END || ' ; avant 2020 : hors source. La fin d''un mandat municipal de 2020 est déduite au 15/03/2026.'
                                     ELSE 'Aucun mandat dans ce que couvre le Répertoire national des élus (mandats en cours, mandats municipaux 2020-2026) ; avant 2020 et autres mandats terminés : hors source.' END
              ELSE 'Mandats locaux : non collectés dans l''essai.' END AS detail
        FROM c CROSS JOIN i
        LEFT JOIN n ON n.per = c.per AND n.institution = i.institution
        ORDER BY c.per, i.institution""")

    n = ctx.un("SELECT count(*) FROM _car_c")
    an_ = ctx.un("SELECT count(DISTINCT per) FROM carriere WHERE institution = 'assemblee'")
    gv = ctx.un("SELECT count(DISTINCT per) FROM carriere WHERE institution = 'gouvernement'")
    sen_ids = ctx.un("SELECT count(*) FROM _car_c WHERE matricule_senat IS NOT NULL")
    sen_ = ctx.un("SELECT count(DISTINCT per) FROM carriere WHERE institution = 'senat'")
    seg = ctx.un("SELECT count(*) FROM carriere WHERE institution IN ('assemblee', 'senat') AND etat = 'en_fonction'")
    seg_grp = ctx.un("""SELECT count(*) FROM carriere WHERE institution IN ('assemblee', 'senat')
                        AND etat = 'en_fonction' AND groupe_statut <> 'non_etabli'""")
    syc = ctx.un("SELECT count(*) FROM _car_c WHERE sycomore IS NOT NULL")
    pe_per = ctx.un("SELECT count(DISTINCT per) FROM carriere WHERE institution = 'parlement_europeen'")
    loc_per = ctx.un("SELECT count(DISTINCT per) FROM carriere WHERE institution = 'local'")
    pe_ids = ctx.un("SELECT count(*) FROM _car_c WHERE eurodepute IS NOT NULL")
    for t in ("_car_c", "_car_an", "_car_gan", "_car_an_seg", "_car_sen", "_car_gsen", "_car_sen_susp",
              "_car_pe", "_car_gpe", "_car_loc_id"):
        ctx.x(f"DROP TABLE IF EXISTS {t}")
    return {"candidats_avec_mandat_de_depute_depuis_2002": (an_, n),
            "candidats_avec_fonction_gouvernementale_depuis_2007": (gv, n),
            "mandats_de_senateur_lus" if senat_collecte else "senat_non_collecte": (sen_, sen_ids),
            "periode_avec_groupe_etabli": (seg_grp, seg),
            "mandats_anterieurs_a_2002_hors_source_sycomore_declare": (syc, n),
            "mandats_europeens_lus": (pe_per, pe_ids),
            "mandats_locaux_lus": (loc_per, n)}
