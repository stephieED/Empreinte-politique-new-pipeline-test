"""R-COMPOSITION : qui composait chaque gouvernement, portefeuille par portefeuille (cahier 4.4 ;
doc. 1, 1.6).

Source : l'archive AMO de l'Assemblée. Un ministre y a **deux** mandats : un mandat GOUVERNEMENT
(qualité toujours « membre », durée de présence dans le gouvernement) et un ou plusieurs mandats
MINISTERE, qui portent le portefeuille (l'organe ministère, son libellé) et la qualité (Premier
ministre, ministre, ministre délégué, secrétaire d'État…). Un changement de portefeuille dans le
même gouvernement est un nouveau mandat MINISTERE sous le même mandat GOUVERNEMENT.

Ce que fait la règle (mesures `an-acteurs.md`, 2.2) :
- une ligne de composition = un mandat MINISTERE dont la qualité n'est **pas** « en mission »
  (408 mandats MINISTERE sont des missions confiées à des parlementaires : écartés) ;
- le gouvernement est le parent (`organeParent`) de l'organe ministère ; le portefeuille exact
  est le libellé de cet organe (le champ `libelle` du mandat est vide pour tous les ministres) ;
- le mandat GOUVERNEMENT apparié est celui dont l'uid vaut `PM15` + le numéro du mandat
  MINISTERE (652 cas sur 659), sinon le mandat GOUVERNEMENT de la même personne, dans le même
  gouvernement, qui couvre ses dates (changement de portefeuille) ;
- un mandat GOUVERNEMENT sans mandat MINISTERE n'entre pas dans la composition : la composition
  part des mandats MINISTERE. Les mandats restés ouverts dans un organe clos (7 dans le
  gouvernement Bayrou) sont listés dans `mandat_ouvert_organe_clos` (avertissement A8). Q23,
  tranchée le 13/11/2026 (« borner ») : une décision `borne_mandat` leur donne la fin de leur
  organe (vue `an_acteurs__mandat`, liaison) ; ils ne sont plus signalés ;
- un ministre délégué, un secrétaire d'État, un haut-commissaire n'ont **aucun champ** qui dise
  leur ministère de tutelle : il se lit dans le libellé (« … auprès du ministre de l'économie… »).
  La règle rattache le portefeuille quand le libellé désigne **un seul** ministre de plein
  exercice (ou le Premier ministre) du même gouvernement, en fonction à la même date
  (`etabli`). Quand il en désigne **plusieurs** (« auprès du ministre de l'intérieur et du
  ministre de la transition écologique ») et que chacun est reconnu, c'est une co-tutelle
  (`co_tutelle`, version 2, issue #80, décision du 14/11/2026 « Tous les ministres ») : toutes
  les tutelles sont servies, dans l'ordre du libellé, et aucune n'est choisie à la place de
  l'interface. Sinon `tutelle_statut = 'non_etabli'` et sa raison (libellé sans « auprès »,
  aucun ministère correspondant, plusieurs ministres désignés dont l'un au moins n'est pas
  reconnu). Une décision `rattachement_portefeuille` (objet : l'organe ministère délégué ou le
  mandat ; décision : `rattache_a` suivi du ou des organes de tutelle `PO…`, dans l'ordre du
  libellé) l'emporte toujours ;
- `ministeres_tutelle` est la liste de toutes les tutelles (une seule pour `etabli`, plusieurs
  pour `co_tutelle`, celles de la décision pour `decision`) ; `ministere_tutelle` ne porte une
  valeur que s'il n'y en a qu'une.
"""

NOM = "R-COMPOSITION"
VERSION = 2
DEPEND = ("R-GOUVERNEMENTS",)
SORTIES = ("membre_gouvernement", "mandat_ouvert_organe_clos")
DESCRIPTION = (
    "La composition d'un gouvernement vient des mandats « ministère » publiés par l'Assemblée "
    "nationale : chaque mandat donne un portefeuille exact (le libellé du ministère), une qualité "
    "(Premier ministre, ministre, ministre délégué, secrétaire d'État…) et des dates. Les missions "
    "confiées à des parlementaires auprès d'un ministère, publiées sous la même forme, ne sont pas "
    "des fonctions ministérielles et sont écartées. Aucun champ ne dit à quel ministère un ministre "
    "délégué ou un secrétaire d'État est rattaché : nous le lisons dans le libellé (« auprès du "
    "ministre de… ») et ne le retenons que si le libellé désigne un seul ministre du même "
    "gouvernement en fonction à la même date. Quand le libellé désigne plusieurs ministres et que "
    "chacun est reconnu, le portefeuille est rattaché à tous, dans l'ordre du libellé (co-tutelle). "
    "Sinon le rattachement est « non établi », sauf décision publiée.Un mandat de membre du gouvernement resté ouvert alors que le gouvernement "
    "est clos n'entre pas dans la composition : il est signalé.")

# Archive courante : si plusieurs archives AMO portent le même mandat, la plus récente
# (point d'accès de la législature la plus haute) l'emporte.
MANDAT = """(SELECT * FROM an_acteurs__mandat
             QUALIFY row_number() OVER (PARTITION BY uid ORDER BY prov_point DESC) = 1)"""
ORGANE = """(SELECT * FROM an_acteurs__organe
             QUALIFY row_number() OVER (PARTITION BY uid ORDER BY prov_point DESC) = 1)"""


def norm(x: str) -> str:
    """Libellé comparable : minuscules, sans accents, apostrophes et espaces normalisés."""
    return (f"lower(strip_accents(regexp_replace(regexp_replace(replace(replace(trim({x}), '’', ''''), "
            f"chr(160), ' '), '\\s+', ' ', 'g'), ''' ', '''', 'g')))")


# Un ministère est désigné dans un libellé par « ministre <clé> » ou « ministère <clé> », la clé
# étant suivie d'une fin de désignation (virgule, « et », tiret, point, « chargé », fin du texte).
_BORNES = (",", " et ", " - ", " – ", ".", " charge")
DESIGNE = " OR ".join(
    f"strpos(d.texte_tutelle || ',', '{x} ' || t.cle || '{b}') > 0"
    for x in ("ministre", "ministere") for b in _BORNES)
# Où le libellé désigne ce ministère (première occurrence) : ordonne les tutelles d'une co-tutelle.
POSITION = "list_min(list_filter([" + ", ".join(
    f"strpos(d.texte_tutelle || ',', '{x} ' || t.cle || '{b}')"
    for x in ("ministre", "ministere") for b in _BORNES) + "], lambda p: p > 0))"
POSITION_PM = ("list_min(list_filter([strpos(d.texte_tutelle, 'premier ministre'), "
               "strpos(d.texte_tutelle, 'premiere ministre')], lambda p: p > 0))")


# Qualités qui supposent un ministère de tutelle même quand le libellé ne dit pas « auprès ».
QUALITES_RATTACHEES = "('Ministre délégué', 'Secrétaire d''État', 'Haut-commissaire')"


def appliquer(ctx):
    """Applique R-COMPOSITION : écrit `membre_gouvernement` (qui composait chaque gouvernement,
    portefeuille par portefeuille) et `mandat_ouvert_organe_clos`, voir la description du module.
    Rend la couverture, `{nom: (numérateur, dénominateur)}` : `tutelle_etablie`,
    `mandat_gouvernement_apparie`, `mandats_gouvernement_dans_la_composition`."""
    # 1. Portefeuilles : mandats MINISTERE hors missions, dans un gouvernement connu.
    ctx.x(f"""CREATE OR REPLACE TEMP TABLE _ga_portefeuille AS
        SELECT m.uid AS mandat, m.acteur, o.organe_parent AS gouvernement, m.organe AS ministere,
               coalesce(m.libelle, o.libelle) AS portefeuille,
               {norm('coalesce(m.libelle, o.libelle)')} AS lib_norm,
               m.qualite, m.qualite_code, m.qualite_sexe,
               TRY_CAST(m.preseance AS INTEGER) AS preseance,
               m.date_debut AS debut, m.date_fin AS fin, m.date_publication,
               m.qualite_code = 'Premier ministre' AS premier_ministre,
               o.organe_precedent AS ministere_precedent,
               m.prov_url AS source_url, m.prov_uid
        FROM {MANDAT} m JOIN {ORGANE} o ON o.uid = m.organe
        WHERE m.type_organe = 'MINISTERE' AND coalesce(m.qualite_code, '') <> 'en mission'
          AND o.organe_parent IN (SELECT organe FROM gouvernement)""")
    ctx.x("""CREATE OR REPLACE TEMP TABLE _ga_portefeuille2 AS
        SELECT p.*,
               (strpos(lib_norm, 'aupres ') > 0 OR strpos(lib_norm, ' apres d') > 0
                OR qualite_code IN """ + QUALITES_RATTACHEES + """) AS a_rattacher,
               CASE WHEN strpos(lib_norm, 'aupres ') > 0 THEN substr(lib_norm, strpos(lib_norm, 'aupres '))
                    WHEN strpos(lib_norm, ' apres d') > 0 THEN substr(lib_norm, strpos(lib_norm, ' apres d'))
               END AS texte_tutelle
        FROM _ga_portefeuille p""")
    # Combien de ministres le libellé désigne-t-il ? (« auprès du ministre X et de la ministre Y »,
    # « auprès des ministres… ») : s'il en désigne plusieurs et qu'un seul est reconnu, la tutelle
    # n'est pas établie (on ne garde pas la moitié d'une co-tutelle).
    ctx.x("""CREATE OR REPLACE TEMP TABLE _ga_portefeuille2 AS
        SELECT *, (des_ministres OR nb_designes > 1) AS plusieurs_designes
        FROM (SELECT *, strpos(coalesce(texte_tutelle, ''), 'des ministres') > 0 AS des_ministres,
                     len(regexp_extract_all(coalesce(texte_tutelle, ''),
                         '(^|\\s)(du|de la|des) (ministre|ministere|premier ministre|premiere ministre|garde des sceaux)'))
                       AS nb_designes
              FROM _ga_portefeuille2)""")

    # 2. Ministères de plein exercice (et Premier ministre) : candidats à la tutelle, avec la clé
    #    qui permet de les reconnaître dans un libellé (« Ministère de la culture » -> « de la culture »).
    ctx.x("""CREATE OR REPLACE TEMP TABLE _ga_candidat AS
        SELECT DISTINCT gouvernement, ministere, premier_ministre,
               regexp_replace(regexp_replace(lib_norm, '^\\S+ ', ''), '^d''etat, ministre ', '') AS cle
        FROM _ga_portefeuille2 WHERE NOT a_rattacher""")
    ctx.x("""CREATE OR REPLACE TEMP TABLE _ga_tenue AS          -- qui tient chaque candidat, quand
        SELECT c.*, p.debut AS t_debut, coalesce(p.fin, '9999-12-31') AS t_fin
        FROM _ga_candidat c JOIN _ga_portefeuille2 p
          ON p.ministere = c.ministere AND NOT p.a_rattacher""")
    ctx.x("""CREATE OR REPLACE TEMP TABLE _ga_correspond AS
        SELECT d.mandat, t.ministere AS tutelle, t.cle,
               min(CASE WHEN t.premier_ministre THEN """ + POSITION_PM + """
                        ELSE """ + POSITION + """ END) AS pos,
               -- en fonction au début du portefeuille (un ministre qui part ce jour-là ne compte pas)
               bool_or(t.t_debut <= d.debut AND d.debut < t.t_fin) AS au_debut,
               bool_or(t.t_debut <= coalesce(d.fin, '9999-12-31') AND d.debut <= t.t_fin) AS chevauche
        FROM _ga_portefeuille2 d JOIN _ga_tenue t
          ON t.gouvernement = d.gouvernement AND t.ministere <> d.ministere
         AND d.texte_tutelle IS NOT NULL
         AND CASE WHEN t.premier_ministre
                  THEN strpos(d.texte_tutelle, 'premier ministre') > 0
                       OR strpos(d.texte_tutelle, 'premiere ministre') > 0
                  ELSE """ + DESIGNE + """ END
        GROUP BY ALL""")
    # À la même date : d'abord les ministres en fonction au début du portefeuille, sinon ceux dont
    # la fonction chevauche le portefeuille ; puis une clé contenue dans une autre plus longue
    # (« de l'intérieur » dans « de l'intérieur et des outre-mer ») s'efface.
    ctx.x("""CREATE OR REPLACE TEMP TABLE _ga_retenu AS
        WITH r AS (
            SELECT c.* FROM _ga_correspond c
            WHERE c.au_debut OR (c.chevauche AND NOT EXISTS (
                SELECT 1 FROM _ga_correspond x WHERE x.mandat = c.mandat AND x.au_debut)))
        SELECT r.mandat, r.tutelle, r.pos FROM r
        WHERE NOT EXISTS (SELECT 1 FROM r r2 WHERE r2.mandat = r.mandat AND r2.cle <> r.cle
                          AND starts_with(r2.cle, r.cle))""")
    ctx.x("""CREATE OR REPLACE TEMP TABLE _ga_tutelle AS
        SELECT mandat, list(tutelle ORDER BY pos, tutelle) AS candidates
        FROM (SELECT mandat, tutelle, min(pos) AS pos FROM _ga_retenu GROUP BY 1, 2) GROUP BY 1""")
    # Une seule tutelle ; ou une co-tutelle : le libellé désigne plusieurs ministres (sans « des
    # ministres », dont on ne sait pas compter les désignations) et autant de ministres du
    # gouvernement sont reconnus que de désignations (on ne garde pas une partie d'une co-tutelle).
    seul = "(len(t.candidates) = 1 AND NOT p.plusieurs_designes)"
    co = ("(p.plusieurs_designes AND NOT p.des_ministres AND len(t.candidates) >= 2 "
          "AND len(t.candidates) = p.nb_designes)")

    if ctx.existe("decision_rattachement_portefeuille"):
        # « rattache_a PO1 » ; pour une co-tutelle « rattache_a PO1 PO2 », dans l'ordre du libellé
        decision = """(SELECT objet, regexp_extract_all(CAST(decision AS VARCHAR), 'PO[0-9]+') AS tutelles,
                              fichier FROM decision_rattachement_portefeuille
                       WHERE len(regexp_extract_all(CAST(decision AS VARCHAR), 'PO[0-9]+')) > 0)"""
    else:
        decision = ("(SELECT NULL::VARCHAR AS objet, NULL::VARCHAR[] AS tutelles, NULL::VARCHAR AS fichier "
                    "WHERE false)")

    # 3. Mandat GOUVERNEMENT apparié : par l'uid (PM15 + numéro), sinon par la période.
    ctx.ecrire("membre_gouvernement", f"""
        WITH g AS (SELECT uid, acteur, organe, date_debut, coalesce(date_fin, '9999-12-31') AS fin_g,
                          date_fin IS NULL AS ouvert
                   FROM {MANDAT} WHERE type_organe = 'GOUVERNEMENT'),
        app AS (
            SELECT p.mandat,
                   coalesce(
                     (SELECT any_value(g.uid) FROM g WHERE g.uid = 'PM15' || substr(p.mandat, 3)
                        AND g.acteur = p.acteur AND g.organe = p.gouvernement),
                     (SELECT arg_min(g.uid, g.ouvert::INT) FROM g WHERE g.acteur = p.acteur
                        AND g.organe = p.gouvernement AND g.date_debut <= p.debut
                        AND g.fin_g >= coalesce(p.fin, '9999-12-31'))) AS mandat_gouvernement,
                   EXISTS (SELECT 1 FROM g WHERE g.uid = 'PM15' || substr(p.mandat, 3)
                             AND g.acteur = p.acteur AND g.organe = p.gouvernement) AS par_uid
            FROM _ga_portefeuille2 p),
        dec AS (SELECT p.mandat, any_value(d.tutelles) AS tutelles, any_value(d.fichier) AS fichier
                FROM _ga_portefeuille2 p JOIN {decision} d ON d.objet IN (p.ministere, p.mandat)
                GROUP BY 1)
        SELECT p.gouvernement, p.acteur, p.portefeuille, p.qualite, p.ministere,
               CASE WHEN dec.tutelles IS NOT NULL THEN (CASE WHEN len(dec.tutelles) = 1 THEN dec.tutelles[1] END)
                    WHEN NOT p.a_rattacher THEN NULL
                    WHEN {seul} THEN t.candidates[1] END AS ministere_tutelle,
               CASE WHEN dec.tutelles IS NOT NULL THEN dec.tutelles
                    WHEN NOT p.a_rattacher THEN NULL
                    WHEN {seul} OR {co} THEN t.candidates END AS ministeres_tutelle,
               CASE WHEN dec.tutelles IS NOT NULL THEN 'decision'
                    WHEN NOT p.a_rattacher THEN 'sans_objet'
                    WHEN {seul} THEN 'etabli'
                    WHEN {co} THEN 'co_tutelle'
                    ELSE 'non_etabli' END AS tutelle_statut,
               p.debut, p.fin, p.premier_ministre,
               CASE WHEN dec.tutelles IS NOT NULL OR NOT p.a_rattacher OR {seul} THEN NULL
                    WHEN {co} THEN 'le libellé désigne plusieurs ministres'
                    WHEN p.texte_tutelle IS NULL THEN 'le libellé ne désigne aucun ministre (pas de « auprès »)'
                    WHEN t.candidates IS NULL THEN 'aucun ministre du gouvernement en fonction à cette date ne correspond au libellé'
                    ELSE 'le libellé désigne plusieurs ministres' END AS raison_tutelle,
               t.candidates AS tutelles_candidates, dec.fichier AS decision,
               p.mandat, a.mandat_gouvernement,
               CASE WHEN a.par_uid THEN 'uid' WHEN a.mandat_gouvernement IS NOT NULL THEN 'periode'
                    ELSE 'aucun' END AS appariement,
               p.qualite_code, p.qualite_sexe, p.preseance, p.date_publication,
               p.ministere_precedent, p.source_url, p.prov_uid
        FROM _ga_portefeuille2 p
        JOIN app a USING (mandat)
        LEFT JOIN _ga_tutelle t USING (mandat)
        LEFT JOIN dec USING (mandat)
        ORDER BY p.gouvernement, p.debut, p.preseance, p.mandat""")

    # 4. Avertissement A8 : mandats sans fin dans un organe clos (tous types d'organes).
    ctx.ecrire("mandat_ouvert_organe_clos", f"""
        SELECT m.uid AS mandat, m.acteur, m.type_organe, m.organe, m.qualite,
               m.date_debut AS debut, o.date_fin AS organe_fin,
               m.type_organe = 'GOUVERNEMENT' AS hors_composition,
               CASE WHEN m.type_organe = 'GOUVERNEMENT' THEN EXISTS (
                    SELECT 1 FROM {MANDAT} x WHERE x.uid = 'PM' || substr(m.uid, 5)
                      AND x.type_organe = 'MINISTERE') END AS ministere_apparie,
               'A8' AS avertissement, m.prov_url AS source_url, m.prov_uid
        FROM {MANDAT} m JOIN {ORGANE} o ON o.uid = m.organe
        WHERE m.date_fin IS NULL AND o.date_fin IS NOT NULL
        ORDER BY m.type_organe, m.organe, m.uid""")

    n = ctx.un("SELECT count(*) FROM membre_gouvernement")
    a_ratt = ctx.un("SELECT count(*) FROM membre_gouvernement WHERE tutelle_statut <> 'sans_objet'")
    ratt = ctx.un("SELECT count(*) FROM membre_gouvernement WHERE tutelle_statut IN ('etabli', 'co_tutelle', 'decision')")
    apparie = ctx.un("SELECT count(*) FROM membre_gouvernement WHERE mandat_gouvernement IS NOT NULL")
    gouv = ctx.un(f"SELECT count(*) FROM {MANDAT} WHERE type_organe = 'GOUVERNEMENT'")
    gouv_compo = ctx.un("SELECT count(DISTINCT mandat_gouvernement) FROM membre_gouvernement")
    for t in ("_ga_portefeuille", "_ga_portefeuille2", "_ga_candidat", "_ga_tenue",
              "_ga_correspond", "_ga_retenu", "_ga_tutelle"):
        ctx.x(f"DROP TABLE IF EXISTS {t}")
    return {"tutelle_etablie": (ratt, a_ratt),
            "mandat_gouvernement_apparie": (apparie, n),
            "mandats_gouvernement_dans_la_composition": (gouv_compo, gouv)}
