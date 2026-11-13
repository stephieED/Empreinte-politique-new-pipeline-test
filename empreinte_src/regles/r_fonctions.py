"""R-FONCTIONS : les fonctions exercées par chaque candidat au sein des organes du Parlement
(cahier 4.2, « Les fonctions exercées » ; doc. 1, 1.6 R-CARRIERE ; doc. 5, Q24).

Sources : les mandats d'organe de l'archive des acteurs de l'Assemblée (commissions, missions,
groupes d'études et d'amitié, organismes extraparlementaires, bureau…), et pour un sénateur
les fonctions de l'export du Sénat (libellé de l'organe **à la date**). Chaque type d'organe
est classé dans une **famille** par une table publiée (`famille_organe`) ; un type absent de la
table tombe dans « autre » et se compte, il n'est jamais écarté sans le dire.

Ne sont pas des fonctions (elles sont dans la carrière, R-CARRIERE, ou hors sujet) : le mandat
de député ou de sénateur, l'appartenance à un groupe (sauf une fonction distinctive dans le
groupe : présidence, vice-présidence…), les fonctions gouvernementales, l'adhésion à un parti,
la circonscription ; ni les organes du Sénat recopiés dans l'archive de l'Assemblée (libellé
actuel seulement : lus dans l'export du Sénat).

Permutations de commission (doc. 5, Q24) : la source publie un mandat neuf à chaque
remplacement de quelques jours (141 mandats pour François Ruffin dans l'archive du 03/11/2026, 142 dans celle du 06/11). À
l'affichage, les périodes d'un même organe, d'une même qualité et d'une même législature
séparées de **3 jours au plus** sont fusionnées ; la durée rendue est la **durée réelle**
(jours couverts, sans les trous). Le détail reste dans `fonction_periode`, une ligne par mandat
de la source. Une fonction encore ouverte compte jusqu'au jour de constat, si le mandat
parlementaire de la personne est en cours ; sinon sa fin n'est pas publiée et sa durée reste
inconnue (raison écrite), jamais calculée jusqu'à aujourd'hui.
"""
from .r_candidatures import vue_ou_vide

NOM = "R-FONCTIONS"
VERSION = 1
DEPEND = ("R-IDENTITE", "R-DEPUTES")
SORTIES = ("fonction_personne", "fonction_periode", "famille_organe")
DESCRIPTION = (
    "Les fonctions d'un candidat au Parlement sont ses mandats dans les organes de l'Assemblée "
    "nationale (commissions, commissions d'enquête, missions d'information, groupes d'études et "
    "d'amitié, organismes extérieurs, bureau…) et, s'il a été sénateur, du Sénat, avec sa "
    "qualité (président, rapporteur, secrétaire, membre…) et ses dates. Les organes sont rangés "
    "par familles selon une table publiée. Quand un député quitte une commission quelques jours "
    "pour en remplacer un autre puis revient, l'Assemblée publie deux mandats : nous les "
    "montrons comme une seule période si l'interruption dure trois jours au plus, et la durée "
    "affichée ne compte que les jours réellement passés dans la fonction.")

ECART_FUSION_JOURS = 3          # doc. 5, Q24

# (chambre, type d'organe, famille, libellé de la famille, rang d'affichage)
FAMILLES = [
    ("an", "BUREAU", "bureau", "Bureau et conférence des présidents", 1),
    ("an", "DELEGBUREAU", "bureau", "Bureau et conférence des présidents", 1),
    ("an", "CONFPT", "bureau", "Bureau et conférence des présidents", 1),
    ("an", "GP", "groupe_politique", "Fonctions dans un groupe politique", 2),
    ("an", "COMPER", "commission", "Commissions", 3),
    ("an", "COMNL", "commission", "Commissions", 3),
    ("an", "CNPE", "commission_enquete_speciale", "Commissions d'enquête et commissions spéciales", 4),
    ("an", "CNPS", "commission_enquete_speciale", "Commissions d'enquête et commissions spéciales", 4),
    ("an", "MISINFO", "mission_information", "Missions d'information", 5),
    ("an", "MISINFOCOM", "mission_information", "Missions d'information", 5),
    ("an", "MISINFOPRE", "mission_information", "Missions d'information", 5),
    ("an", "DELEG", "delegation", "Délégations et offices", 6),
    ("an", "OFFPAR", "delegation", "Délégations et offices", 6),
    ("an", "CMP", "cmp", "Commissions mixtes paritaires", 7),
    ("an", "GE", "groupe_etudes", "Groupes d'études", 8),
    ("an", "GEVI", "groupe_etudes", "Groupes d'études", 8),
    ("an", "ORGEXTPARL", "organisme_extraparlementaire", "Organismes extra-parlementaires", 9),
    ("an", "GA", "groupe_amitie", "Groupes d'amitié", 10),
    ("an", "API", "assemblee_internationale", "Assemblées parlementaires internationales", 11),
    ("an", "CJR", "juridiction", "Cour de justice de la République et Haute Cour", 12),
    ("an", "HCJ", "juridiction", "Cour de justice de la République et Haute Cour", 12),
    ("senat", "BUREAU", "bureau", "Bureau et conférence des présidents", 1),
    ("senat", "GRPPOL", "groupe_politique", "Fonctions dans un groupe politique", 2),
    ("senat", "GRPPOLNI", "groupe_politique", "Fonctions dans un groupe politique", 2),
    ("senat", "COM", "commission", "Commissions", 3),
    ("senat", "COMEUR", "commission", "Commissions", 3),
    ("senat", "COMAPLEG", "commission", "Commissions", 3),
    ("senat", "COMENQ", "commission_enquete_speciale", "Commissions d'enquête et commissions spéciales", 4),
    ("senat", "COMSPE", "commission_enquete_speciale", "Commissions d'enquête et commissions spéciales", 4),
    ("senat", "COMSPEAPU", "commission_enquete_speciale", "Commissions d'enquête et commissions spéciales", 4),
    ("senat", "MISINFCOM", "mission_information", "Missions d'information", 5),
    ("senat", "MISCOM", "mission_information", "Missions d'information", 5),
    ("senat", "COMSENCOMMU", "mission_information", "Missions d'information", 5),
    ("senat", "CMP", "cmp", "Commissions mixtes paritaires", 7),
]
# Types d'organe qui ne sont pas des fonctions, et pourquoi.
EXCLUS = [
    ("an", "ASSEMBLEE", "mandat de député : dans la carrière"),
    ("an", "GOUVERNEMENT", "fonction gouvernementale : dans la carrière"),
    ("an", "MINISTERE", "fonction gouvernementale : dans la carrière"),
    ("an", "PRESREP", "présidence de la République : hors fonctions parlementaires"),
    ("an", "PARPOL", "adhésion à un parti : pas une fonction"),
    ("an", "CIRCONSCRIPTION", "circonscription : attribut du mandat"),
    ("an", "SENAT", "organe du Sénat recopié par l'Assemblée : lu dans l'export du Sénat"),
    ("an", "COMSENAT", "organe du Sénat recopié par l'Assemblée : lu dans l'export du Sénat"),
    ("an", "GROUPESENAT", "organe du Sénat recopié par l'Assemblée : lu dans l'export du Sénat"),
    ("an", "DELEGSENAT", "organe du Sénat recopié par l'Assemblée : lu dans l'export du Sénat"),
    ("an", "COMSPSENAT", "organe du Sénat recopié par l'Assemblée : lu dans l'export du Sénat"),
]
# Dans un groupe politique, ces qualités disent l'appartenance (dans la carrière), pas une fonction.
QUALITES_APPARTENANCE = ("membre", "membre du", "apparenté au", "apparenté", "membre apparenté",
                         "rattaché", "membre rattaché", "député non-inscrit")


def _q(s):
    return "'" + s.replace("'", "''") + "'"


def date_constat(ctx) -> str | None:
    """Rend la date du constat : `ctx.date_reference` s'il est donné ; sinon la plus tardive des
    dates de début et de fin des mandats `ASSEMBLEE` et `GP` ; `None` si la vue
    `an_acteurs__mandat` n'existe pas."""
    if ctx.date_reference:
        return ctx.date_reference
    if not ctx.existe("an_acteurs__mandat"):
        return None
    return ctx.un("""SELECT max(greatest(date_debut, date_fin)) FROM an_acteurs__mandat
                     WHERE type_organe IN ('ASSEMBLEE', 'GP')""")


def appliquer(ctx):
    """Applique R-FONCTIONS : écrit `famille_organe`, `fonction_periode` et `fonction_personne`,
    les fonctions exercées par chaque candidat dans les organes du Parlement (voir la description
    du module). Rend la couverture, `{nom: (numérateur, dénominateur)}` :
    `candidats_avec_fonction`, `periodes_source_classees_dans_une_famille`, `duree_etablie`."""
    familles = ", ".join(f"({_q(c)}, {_q(t)}, {_q(f)}, {_q(l)}, {r}, NULL)" for c, t, f, l, r in FAMILLES)
    exclus = ", ".join(f"({_q(c)}, {_q(t)}, 'exclu', NULL, NULL, {_q(x)})" for c, t, x in EXCLUS)
    ctx.ecrire("famille_organe", f"""
        SELECT * FROM (VALUES {familles}, {exclus})
            AS t(chambre, type_organe, famille, libelle_famille, rang, raison_exclusion)
        ORDER BY chambre, rang NULLS LAST, type_organe""")

    constat = date_constat(ctx)
    jour = "NULL::DATE" if constat is None else f"DATE '{constat}'"
    mandat_an = vue_ou_vide(ctx, "an_acteurs__mandat", {
        "uid": "VARCHAR", "acteur": "VARCHAR", "type_organe": "VARCHAR", "organe": "VARCHAR",
        "legislature": "VARCHAR", "qualite": "VARCHAR", "date_debut": "VARCHAR",
        "date_fin": "VARCHAR", "prov_point": "VARCHAR", "prov_url": "VARCHAR"})
    organe_an = vue_ou_vide(ctx, "an_acteurs__organe", {
        "uid": "VARCHAR", "libelle": "VARCHAR", "prov_point": "VARCHAR"})
    senat = vue_ou_vide(ctx, "senat_export__mandat", {
        "uid": "VARCHAR", "acteur": "VARCHAR", "nature": "VARCHAR", "type_organe": "VARCHAR",
        "organe": "VARCHAR", "appartenance": "VARCHAR", "qualite": "VARCHAR",
        "date_debut": "VARCHAR", "date_fin": "VARCHAR", "libelle_organe": "VARCHAR",
        "prov_url": "VARCHAR"})
    organe_sen = vue_ou_vide(ctx, "senat_export__organe", {"uid": "VARCHAR", "libelle": "VARCHAR"})
    appart = ", ".join(_q(q) for q in QUALITES_APPARTENANCE)

    # Une ligne par mandat de la source (le détail).
    ctx.ecrire("fonction_periode", f"""
        WITH c AS (SELECT per, acteur, matricule_senat FROM candidat),
        an AS (
            SELECT c.per, 'an' AS chambre, m.type_organe, m.organe, o.libelle,
                   TRY_CAST(m.legislature AS INTEGER) AS legislature, m.qualite, m.uid AS mandat,
                   m.date_debut AS debut, m.date_fin AS fin, m.acteur,
                   coalesce(m.prov_url, 'https://www.assemblee-nationale.fr/dyn/deputes/' || m.acteur) AS source_url,
                   EXISTS (SELECT 1 FROM depute d WHERE d.acteur = m.acteur AND d.fin IS NULL
                           AND d.debut <= m.date_debut) AS ouverte_dans_le_mandat_en_cours
            FROM (SELECT * FROM {mandat_an} QUALIFY row_number() OVER (PARTITION BY uid ORDER BY prov_point DESC) = 1) m
            JOIN c ON c.acteur = m.acteur
            LEFT JOIN (SELECT * FROM {organe_an} QUALIFY row_number() OVER (PARTITION BY uid ORDER BY prov_point DESC) = 1) o
              ON o.uid = m.organe
            -- Une commission mixte paritaire réunit députés et sénateurs : l'archive de
            -- l'Assemblée y inscrit aussi les sénateurs. Hors mandat de député, la place est
            -- celle d'un sénateur, lue dans l'export du Sénat.
            WHERE NOT (m.type_organe = 'CMP' AND NOT EXISTS (
                SELECT 1 FROM depute d WHERE d.acteur = m.acteur AND d.debut <= m.date_debut
                   AND coalesce(d.fin, '9999-12-31') >= m.date_debut))),
        sen AS (
            SELECT c.per, 'senat', f.type_organe, coalesce(f.organe, 'senat:bureau'),
                   coalesce(a.libelle_organe, org.libelle,
                            CASE WHEN f.type_organe = 'BUREAU' THEN 'Bureau du Sénat' END),
                   NULL::INTEGER, f.qualite, f.uid, f.date_debut, f.date_fin, f.acteur, f.prov_url,
                   EXISTS (SELECT 1 FROM {senat} s WHERE s.acteur = f.acteur AND s.nature = 'mandat'
                           AND s.date_fin IS NULL AND s.date_debut <= f.date_debut)
            FROM {senat} f JOIN c ON f.acteur = 'senat:' || c.matricule_senat
            LEFT JOIN {senat} a ON a.uid = f.appartenance
            LEFT JOIN (SELECT uid, any_value(libelle) AS libelle FROM {organe_sen} GROUP BY 1) org
              ON org.uid = f.organe
            WHERE f.nature = 'fonction' AND coalesce(f.organe, '') <> 'senat:com:NEANT'
              AND NOT (f.type_organe = 'BUREAU' AND f.qualite = 'Sénateur'))
        SELECT x.*, coalesce(fo.famille, 'autre') AS famille,
               coalesce(fo.libelle_famille, 'Autres organes') AS libelle_famille,
               coalesce(fo.rang, 99) AS rang_famille
        FROM (SELECT * FROM an UNION ALL SELECT * FROM sen) x
        LEFT JOIN famille_organe fo ON fo.chambre = x.chambre AND fo.type_organe = x.type_organe
        WHERE coalesce(fo.famille, '') <> 'exclu'
          AND NOT (coalesce(fo.famille, '') = 'groupe_politique' AND lower(x.qualite) IN ({appart}))
          AND x.debut IS NOT NULL
        ORDER BY x.per, x.organe, x.debut""")

    # Fusion d'affichage : d'abord l'union des jours (périodes qui se touchent ou se recouvrent),
    # puis les morceaux séparés de ECART_FUSION_JOURS jours au plus.
    cle = "per, chambre, organe, lower(qualite), legislature"
    # Toutes les fenêtres sont ordonnées jusqu'au mandat (clé unique) : deux mandats de mêmes
    # dates (membre et secrétaire) rangés différemment par deux fenêtres décaleraient les îlots.
    ctx.x(f"""CREATE OR REPLACE TEMP TABLE _fn_b AS
        SELECT *, debut::DATE AS d0,
               CASE WHEN fin IS NOT NULL THEN fin::DATE
                    WHEN ouverte_dans_le_mandat_en_cours THEN {jour} END AS d1,
               fin IS NULL AS ouvert
        FROM fonction_periode""")
    ctx.x("""CREATE OR REPLACE TEMP TABLE _fn_org AS
            SELECT per, chambre, organe, sum(date_diff('day', d0, d1) + 1) AS duree_organe_jours
            FROM (SELECT per, chambre, organe, min(d0) AS d0, max(d1) AS d1 FROM (
                      SELECT *, sum(CASE WHEN fa IS NOT NULL AND d0 <= fa + 1 THEN 0 ELSE 1 END)
                                OVER (PARTITION BY per, chambre, organe ORDER BY d0, d1, mandat ROWS UNBOUNDED PRECEDING) AS ilot
                      FROM (SELECT per, chambre, organe, d0, d1, mandat,
                                   max(d1) OVER (PARTITION BY per, chambre, organe ORDER BY d0, d1, mandat
                                                 ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING) AS fa
                            FROM _fn_b WHERE d1 IS NOT NULL AND d1 >= d0))
                  GROUP BY per, chambre, organe, ilot)
            GROUP BY ALL""")
    ctx.ecrire("fonction_personne", f"""
        WITH b AS (SELECT * FROM _fn_b),
        b2 AS (SELECT * FROM b WHERE d1 IS NOT NULL AND d1 >= d0),
        o1 AS (SELECT *, max(d1) OVER (PARTITION BY {cle} ORDER BY d0, d1, mandat
                         ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING) AS f_avant FROM b2),
        i1 AS (SELECT *, sum(CASE WHEN f_avant IS NOT NULL AND d0 <= f_avant + 1 THEN 0 ELSE 1 END)
                         OVER (PARTITION BY {cle} ORDER BY d0, d1, mandat ROWS UNBOUNDED PRECEDING) AS ilot FROM o1),
        u AS (SELECT per, chambre, organe, lower(qualite) AS qk, legislature, ilot,
                     min(d0) AS d0, max(d1) AS d1, bool_or(ouvert) AS ouvert, list(mandat) AS mandats
              FROM i1 GROUP BY ALL),
        o2 AS (SELECT *, max(d1) OVER (PARTITION BY per, chambre, organe, qk, legislature ORDER BY d0, d1, ilot
                         ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING) AS f_avant FROM u),
        i2 AS (SELECT *, date_diff('day', f_avant, d0) - 1 AS trou,
                      sum(CASE WHEN f_avant IS NOT NULL AND date_diff('day', f_avant, d0) - 1 <= {ECART_FUSION_JOURS}
                               THEN 0 ELSE 1 END)
                      OVER (PARTITION BY per, chambre, organe, qk, legislature ORDER BY d0, d1, ilot
                            ROWS UNBOUNDED PRECEDING) AS affichage FROM o2),
        f AS (SELECT per, chambre, organe, qk, legislature, affichage,
                     min(d0) AS d0, max(d1) AS d1, bool_or(ouvert) AS ouvert,
                     sum(date_diff('day', d0, d1) + 1) AS duree_jours,
                     count(*) AS nb_morceaux, max(trou) FILTER (WHERE trou >= 0 AND trou <= {ECART_FUSION_JOURS}) AS trou_max,
                     flatten(list(mandats)) AS mandats
              FROM i2 GROUP BY ALL),
        meta AS (SELECT per, chambre, organe, lower(qualite) AS qk, legislature,
                        any_value(qualite ORDER BY debut DESC) AS qualite, any_value(libelle) AS libelle,
                        any_value(type_organe) AS type_organe, any_value(famille) AS famille,
                        any_value(libelle_famille) AS libelle_famille, any_value(rang_famille) AS rang_famille,
                        any_value(acteur) AS acteur, any_value(source_url) AS source_url
                 FROM fonction_periode GROUP BY ALL),
        -- Fonction ouverte qui a commencé avant le mandat parlementaire en cours (ou sans mandat
        -- en cours) : fin non publiée, durée inconnue. Fin antérieure au début : idem.
        sans_fin AS (
            SELECT per, chambre, organe, lower(qualite) AS qk, legislature, debut::DATE AS d0,
                   CASE WHEN fin IS NOT NULL THEN fin::DATE END AS d1, fin IS NULL AS ouvert,
                   NULL::BIGINT AS duree_jours, 1 AS nb_morceaux, NULL::BIGINT AS trou_max,
                   [mandat] AS mandats,
                   CASE WHEN d1 IS NULL THEN 'fonction ouverte à la source, commencée avant le mandat parlementaire en cours : fin non publiée'
                        ELSE 'fin antérieure au début à la source' END AS raison_duree
            FROM b WHERE d1 IS NULL OR d1 < d0)
        SELECT f.per, m.famille, f.organe, m.libelle, m.qualite, strftime(f.d0, '%Y-%m-%d') AS debut,
               CASE WHEN NOT f.ouvert THEN strftime(f.d1, '%Y-%m-%d') END AS fin,
               f.duree_jours, f.raison_duree, org.duree_organe_jours,
               f.ouvert AS en_cours,
               CASE WHEN f.ouvert AND f.duree_jours IS NOT NULL THEN {jour}::VARCHAR END AS duree_calculee_au,
               lower(m.qualite) NOT LIKE 'membre%' AND lower(m.qualite) NOT IN ('titulaire', 'député non-inscrit')
                   AS qualite_distinctive,
               m.libelle_famille, m.rang_famille, m.type_organe, f.chambre, f.legislature,
               f.nb_morceaux AS nb_periodes_fusionnees, f.trou_max AS plus_long_trou_fusionne_jours,
               len(f.mandats) AS nb_mandats_source, list_sort(f.mandats) AS mandats, m.acteur, m.source_url
        FROM (SELECT *, NULL::VARCHAR AS raison_duree FROM f
              UNION ALL BY NAME SELECT *, 0 AS affichage FROM sans_fin) f
        LEFT JOIN _fn_org org ON org.per = f.per AND org.chambre = f.chambre AND org.organe = f.organe
        JOIN meta m ON m.per = f.per AND m.chambre = f.chambre AND m.organe = f.organe AND m.qk = f.qk
             AND m.legislature IS NOT DISTINCT FROM f.legislature
        ORDER BY f.per, m.rang_famille, f.organe, debut""")

    ctx.x("DROP TABLE IF EXISTS _fn_b")
    ctx.x("DROP TABLE IF EXISTS _fn_org")
    n_per = ctx.un("SELECT count(*) FROM candidat")
    avec = ctx.un("SELECT count(DISTINCT per) FROM fonction_periode")
    n_src = ctx.un("SELECT count(*) FROM fonction_periode")
    autre = ctx.un("SELECT count(*) FROM fonction_periode WHERE famille = 'autre'")
    n_aff = ctx.un("SELECT count(*) FROM fonction_personne")
    duree = ctx.un("SELECT count(*) FROM fonction_personne WHERE duree_jours IS NOT NULL")
    return {"candidats_avec_fonction": (avec, n_per),
            "periodes_source_classees_dans_une_famille": (n_src - autre, n_src),
            "duree_etablie": (duree, n_aff)}
