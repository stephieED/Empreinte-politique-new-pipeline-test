"""R-MANDAT-LOCAL : les mandats locaux d'un candidat, lus dans le Répertoire national des élus
(lecteur `rne_elus` ; décisions du 13/11/2026 : mandats locaux réintégrés, Q34, Q35), complétés
des mandats locaux passés que Wikidata déclare (lecteur `wd_fonctions` ; décisions du 23/11/2026,
Q49 à Q53).

**Rattachement.** Le répertoire n'a **aucun identifiant de personne**. Un élu est rattaché à un
candidat quand (décision Q34) :

- son nom, son prénom et sa date de naissance concordent **exactement** avec l'identité du
  candidat (R-IDENTITE : nom et prénom de l'Assemblée, du Sénat ou de Wikipédia ; date de
  naissance de l'Assemblée, du Sénat ou de Wikidata) ; noms et prénoms comparés sans accents,
  sans casse, sans espaces ni tirets, **prénom et nom d'un seul tenant** (« Juan Branco » =
  « BRANCO » + « Juan ») ; jamais le nom seul, toujours avec la date de naissance ;
- ou une décision `elu_local` le dit, pour un candidat dont aucune source ne donne la date de
  naissance.

Un élu que deux candidats revendiqueraient n'est rattaché à aucun. **Garde-fou d'homonymie
(Q53)** : quand la clé d'un candidat désigne, dans un même fichier où une personne n'a qu'un
siège (conseillers municipaux, maires, communautaires, départementaux, régionaux), deux
collectivités différentes, ce sont deux élus distincts nés le même jour : aucun n'est rattaché
(raison `ambigu_non_rattache`), et l'avertissement A10 les nomme (table `mandat_local_ambigu`).

**Ce qu'on dit d'un candidat non rattaché (Q51).** Table `mandat_local_recherche`, une ligne
par candidat : `rattache` ; `aucun_elu_de_ce_nom` (date de naissance inconnue, et aucun élu du
répertoire ne porte ce prénom et ce nom) ; `homonyme_non_rattache` (date de naissance inconnue,
un ou plusieurs élus de ce nom, jamais rattachés sans décision) ; `ambigu_non_rattache` (Q53) ;
`aucun_mandat` (identité recherchable, rien dans le répertoire). R-CARRIERE en fait le statut
`non_etabli` (servi `non_relu`) et son détail.

**Deux lignes, mandat et fonction (Q50).** Un mandat (conseiller municipal, communautaire,
départemental…) est une période datée du début du mandat ; une fonction exercée dans ce mandat
(maire, adjoint, président, vice-président…) en est une autre, datée du début de la fonction.
Le même mandat publié dans deux fichiers (un maire figure aussi parmi les conseillers
municipaux) ne fait qu'une ligne. Une ligne garde l'identifiant qu'elle avait (`<fichier>:<code
de la collectivité>`) ; une ligne de mandat qui partagerait celui de sa fonction prend le
suffixe `:mandat`.

**Fins.** Le répertoire ne publie **aucune date de fin** :

- un mandat municipal du fichier des sortants (2020-2026) se termine au premier tour des
  municipales, le **15/03/2026** : date **déduite** (`fin_nature = deduite` ; Q35) ;
- **fin observée (Q49)** : un mandat (ou une fonction) présent dans une version d'un fichier
  trimestriel et absent de la version suivante s'est terminé entre les deux relevés. L'entrepôt
  garde toutes les versions (vue `rne_elus__mandat_local__hist`) : la ligne reste, sa fin est la
  date du premier relevé qui ne la porte plus (`fin_nature = observee`), et `fin_raison` donne
  les deux relevés. Une ligne du fichier figé des sortants qui disparaît n'est pas une fin ;
- un mandat des fichiers trimestriels encore présent est en cours.

**Wikidata (Q52).** Les déclarations P39 des éléments de la liste qui désignent un mandat ou une
fonction **locale** (libellé du poste, de son ressort ou de son objet : conseiller municipal,
maire, adjoint au maire, conseiller de Paris, conseiller communautaire ou métropolitain,
président d'une communauté ou d'une métropole, conseiller général ou départemental, conseiller
régional, et leurs présidences), **terminées** (début et fin déclarés, fin passée), et qui ne
chevauchent aucune période du répertoire du même niveau pour le même candidat. Elles sont
inscrites `declare_par = wikidata`, source et adresse de l'élément nommées sur chaque ligne. Une
déclaration sans fin n'est pas reprise : en cours, elle est dans le répertoire ; terminée,
Wikidata ne dit pas quand.
"""
from .r_candidatures import vue_ou_vide

NOM = "R-MANDAT-LOCAL"
VERSION = 2
DEPEND = ("R-IDENTITE",)
SORTIES = ("mandat_local_candidat", "mandat_local_recherche", "mandat_local_ambigu")
DESCRIPTION = (
    "Les mandats locaux (conseiller municipal, maire, conseiller communautaire, départemental, "
    "régional…) viennent du Répertoire national des élus, publié par le ministère de l'Intérieur. "
    "Ce répertoire ne donne pas d'identifiant des personnes : un élu n'est rattaché à un candidat que "
    "si son nom, son prénom et sa date de naissance sont exactement ceux que donnent nos autres "
    "sources, ou si la responsable du site l'a vérifié et décidé ; quand ces trois éléments désignent "
    "deux élus différents, aucun n'est rattaché. Le mandat et la fonction exercée (maire, président…) "
    "sont deux périodes. Le répertoire ne couvre que les mandats en cours et les mandats municipaux de "
    "2020 à 2026, sans date de fin : un mandat municipal de 2020 est montré jusqu'au premier tour des "
    "municipales du 15 mars 2026 (date déduite), et un mandat qui disparaît du répertoire se termine "
    "entre les deux relevés qui l'encadrent (date observée). Les mandats locaux plus anciens, ou "
    "terminés hors des municipales, sont ceux que déclare Wikidata, signalés comme tels.")

FIN_SORTANTS = "2026-03-15"
RAISON_FIN = ("fin déduite : renouvellement des conseils municipaux, premier tour du 15/03/2026 "
              "(le répertoire ne publie pas de date de fin)")
RAISON_WIKIDATA = ("dates déclarées par Wikidata (P39) ; période que le Répertoire national des élus "
                   "ne couvre pas")
# Fichiers où une personne n'a qu'un siège : une même clé dans deux collectivités = deux élus.
SIEGE_UNIQUE = ("cm", "sortants-cm", "maires", "sortants-maires", "epci", "cd", "cr")
# Libellé du mandat de chaque fichier (la fonction par défaut du lecteur, sauf pour les maires).
MANDAT = {"cm": "Conseiller municipal", "sortants-cm": "Conseiller municipal",
          "maires": "Conseiller municipal", "sortants-maires": "Conseiller municipal",
          "epci": "Conseiller communautaire", "cd": "Conseiller départemental",
          "cr": "Conseiller régional", "ca": "Conseiller d'arrondissement", "ma": "Membre de l'assemblée",
          "consfde": "Conseiller des Français de l'étranger",
          "afe": "Membre de l'Assemblée des Français de l'étranger"}
# Fonctions locales déclarées par Wikidata : (niveau, motif sur « poste · ressort · objet » en
# minuscules). Le premier motif qui correspond donne le niveau ; « fonction » si le poste est une
# fonction (maire, adjoint, président, vice-président), sinon « mandat ».
NIVEAUX_WD = (
    ("intercommunal", r"(conseill\S* (communautaire|métropolitain)|présiden\S*.*(communauté|agglomération|métropole|intercommunal))"),
    ("departemental", r"(conseill\S* (général|départemental)|présiden\S*.*conseil (général|départemental))"),
    ("regional", r"(conseill\S* régional|présiden\S*.*conseil régional)"),
    ("municipal", r"(^maire( |$)|^maire adjoint|adjoint\S* au maire|^premier adjoint|conseill\S* municipal|conseill\S* de paris|conseill\S* d'arrondissement)"),
)
EXCLUS_WD = r"(député|sénat|ministre|parlement|surveillance|inspect|économique, social)"
FONCTION_WD = r"^(maire|adjoint|premier adjoint|présiden|vice-présiden)"


def _niveau_wd_sql(t: str) -> str:
    """Le niveau d'une déclaration P39 (`NIVEAUX_WD`) d'après le texte `t` (poste · ressort · objet,
    en minuscules) ; NULL si elle ne désigne pas une fonction locale."""
    return "CASE " + " ".join(
        "WHEN regexp_matches({}, '{}') THEN '{}'".format(t, motif.replace("'", "''"), niv)
        for niv, motif in NIVEAUX_WD) + " END"


def declarations_wikidata(ctx) -> dict[str, bool]:
    """{déclaration P39 de la réponse Wikidata en vigueur : son libellé désigne-t-il une fonction
    locale ?}, selon les motifs de la règle (`NIVEAUX_WD`, `EXCLUS_WD`), sans tenir compte des
    dates. C1 s'en sert pour expliquer la disparition d'une ligne déclarée par Wikidata (décision
    Q55 du 23/11/2026, « Perte expliquée dans C1 ») : déclaration absente de la réponse alors que
    son élément y est encore (supprimée dans Wikidata), ou présente mais plus locale. Vide si la
    réponse n'a jamais été lue."""
    if not ctx.existe("wd_fonctions__fonction_wikidata"):
        return {}
    return dict(ctx.x(f"""
        WITH w AS (SELECT declaration, any_value(poste_libelle) AS poste_libelle,
                          lower(concat_ws(' · ', any_value(poste_libelle), string_agg(DISTINCT juridiction, ' · '),
                                          string_agg(DISTINCT objet, ' · '))) AS t
                   FROM wd_fonctions__fonction_wikidata WHERE declaration IS NOT NULL GROUP BY 1)
        SELECT declaration, coalesce({_niveau_wd_sql("t")} IS NOT NULL
                                     AND NOT regexp_matches(lower(coalesce(poste_libelle, '')), '{EXCLUS_WD}'), false)
        FROM w"""))


def norm(x: str) -> str:
    return f"upper(regexp_replace(strip_accents(coalesce({x}, '')), '[^A-Za-z]', '', 'g'))"


def _valeurs(d: dict) -> str:
    return ", ".join("('{}', '{}')".format(k, v.replace("'", "''")) for k, v in d.items())


def appliquer(ctx):
    cols = {"fichier": "VARCHAR", "niveau": "VARCHAR", "sortant": "BOOLEAN", "fonction": "VARCHAR",
            "collectivite": "VARCHAR", "code_collectivite": "VARCHAR", "departement": "VARCHAR",
            "nom": "VARCHAR", "prenom": "VARCHAR", "naissance": "VARCHAR", "naissance_publiee": "VARCHAR",
            "debut_mandat": "VARCHAR", "debut_fonction": "VARCHAR", "prov_url": "VARCHAR",
            "prov_point": "VARCHAR"}
    ml = vue_ou_vide(ctx, "rne_elus__mandat_local", cols)
    hist = vue_ou_vide(ctx, "rne_elus__mandat_local__hist", {
        **cols, "prov_uid": "VARCHAR", "prov_version": "INTEGER", "prov_vu_du": "INTEGER",
        "prov_vu_jusqu_au": "INTEGER", "prov_etat": "VARCHAR"})
    dec = vue_ou_vide(ctx, "decision_elu_local", {
        "candidat": "VARCHAR", "nom_elu": "VARCHAR", "prenom_elu": "VARCHAR", "naissance": "VARCHAR",
        "fichier": "VARCHAR"})
    wd = vue_ou_vide(ctx, "wd_fonctions__fonction_wikidata", {
        "element": "VARCHAR", "declaration": "VARCHAR", "poste": "VARCHAR", "poste_libelle": "VARCHAR",
        "debut": "VARCHAR", "fin": "VARCHAR", "juridiction": "VARCHAR", "objet": "VARCHAR",
        "prov_url": "VARCHAR", "prov_point": "VARCHAR"})
    ref = getattr(ctx, "date_reference", None) or "9999-12-31"
    gens = getattr(ctx, "dates_generations", None) or {}
    ctx.x("CREATE OR REPLACE TEMP TABLE _ml_gen (g INTEGER, d VARCHAR)")
    if gens:
        ctx.x("INSERT INTO _ml_gen VALUES " + ", ".join(f"({int(g)}, '{str(d)[:10]}')" for g, d in gens.items()))
    ctx.x(f"CREATE OR REPLACE TEMP TABLE _ml_mandat (fichier VARCHAR, libelle VARCHAR); "
          f"INSERT INTO _ml_mandat VALUES {_valeurs(MANDAT)}")

    # --- Lignes du répertoire : celles des versions courantes, et celles qui en ont disparu (Q49).
    cle = ("concat_ws('|', fichier, coalesce(nom, ''), coalesce(prenom, ''), coalesce(naissance_publiee, ''), "
           "coalesce(code_collectivite, ''), coalesce(fonction, ''), coalesce(debut_mandat, ''), "
           "coalesce(debut_fonction, ''))")
    ctx.x(f"""CREATE OR REPLACE TEMP TABLE _ml_v AS
        SELECT prov_point AS p, prov_uid AS u, prov_version AS n, any_value(prov_vu_du) AS du,
               any_value(prov_vu_jusqu_au) AS au, any_value(prov_etat) AS et
        FROM {hist} GROUP BY 1, 2, 3""")
    ctx.x(f"""CREATE OR REPLACE TEMP TABLE _ml_fin AS
        WITH der AS (SELECT p, u, max(n) AS n FROM _ml_v GROUP BY 1, 2),
        h AS (SELECT *, {cle} AS k FROM {hist} WHERE NOT coalesce(sortant, false)),
        cour AS (SELECT DISTINCT h.prov_point, h.prov_uid, h.k FROM h
                 JOIN der ON der.p = h.prov_point AND der.u = h.prov_uid AND der.n = h.prov_version),
        partis AS (
            SELECT h.prov_point, h.prov_uid, h.k, max(h.prov_version) AS n_der
            FROM h JOIN der ON der.p = h.prov_point AND der.u = h.prov_uid
            JOIN _ml_v vd ON vd.p = der.p AND vd.u = der.u AND vd.n = der.n AND vd.et = 'present'
            WHERE h.prov_version < der.n
              AND NOT EXISTS (SELECT 1 FROM cour c WHERE c.prov_point = h.prov_point
                              AND c.prov_uid = h.prov_uid AND c.k = h.k)
            GROUP BY 1, 2, 3)
        SELECT x.* EXCLUDE (k, prov_uid, prov_version, prov_vu_du, prov_vu_jusqu_au, prov_etat),
               coalesce(gs.d, '{ref}') AS fin_obs,
               'fin observée : présent dans le répertoire relevé le '
                   || coalesce(g0.d, 'génération ' || v0.au) || ', absent de celui relevé le '
                   || coalesce(gs.d, 'génération ' || vs.du)
                   || ' (le répertoire ne publie pas de date de fin)' AS fin_obs_raison
        FROM partis pt
        JOIN h x ON x.prov_point = pt.prov_point AND x.prov_uid = pt.prov_uid AND x.k = pt.k
                AND x.prov_version = pt.n_der
        JOIN _ml_v v0 ON v0.p = pt.prov_point AND v0.u = pt.prov_uid AND v0.n = pt.n_der
        JOIN (SELECT p, u, n, du, lag(n) OVER (PARTITION BY p, u ORDER BY n) AS n_avant FROM _ml_v) vs
          ON vs.p = pt.prov_point AND vs.u = pt.prov_uid AND vs.n_avant = pt.n_der
        LEFT JOIN _ml_gen g0 ON g0.g = v0.au
        LEFT JOIN _ml_gen gs ON gs.g = vs.du""")
    ctx.x(f"""CREATE OR REPLACE TEMP TABLE _ml_src AS
        SELECT *, NULL::VARCHAR AS fin_obs, NULL::VARCHAR AS fin_obs_raison FROM
            (SELECT {", ".join(cols)} FROM {ml})
        UNION ALL BY NAME
        SELECT * FROM (SELECT {", ".join(cols)}, fin_obs, fin_obs_raison FROM _ml_fin)""")

    # --- Identités à rechercher : R-IDENTITE (nom, prénom, naissance), et les décisions.
    ctx.x(f"""CREATE OR REPLACE TEMP TABLE _ml_id AS
        SELECT i.per, {norm("coalesce(i.prenom, '') || i.nom")} AS np, i.naissance,
               'nom_prenom_naissance' AS methode, NULL::VARCHAR AS decision
        FROM personne_identite i
        WHERE i.naissance IS NOT NULL AND i.nom IS NOT NULL
        UNION
        SELECT c.per, {norm("coalesce(d.prenom_elu, '') || d.nom_elu")}, CAST(d.naissance AS VARCHAR),
               'decision', d.fichier
        FROM {dec} d JOIN candidat c ON c.nom_liste = d.candidat OR c.nom = d.candidat""")
    ctx.x(f"""CREATE OR REPLACE TEMP TABLE _ml_tout AS
        SELECT x.per, x.methode, x.decision, m.*
        FROM (SELECT *, {norm("coalesce(prenom, '') || nom")} AS np FROM _ml_src
              WHERE nom IS NOT NULL AND prenom IS NOT NULL) m
        JOIN _ml_id x ON x.np = m.np AND x.naissance = m.naissance""")
    # Garde-fou d'homonymie (Q53) : dans un fichier à siège unique, la clé désigne deux collectivités.
    ctx.x(f"""CREATE OR REPLACE TEMP TABLE _ml_amb AS
        SELECT per, np, naissance, fichier, count(DISTINCT code_collectivite) AS n,
               string_agg(DISTINCT collectivite, ' ; ' ORDER BY collectivite) AS collectivites
        FROM _ml_tout
        WHERE methode = 'nom_prenom_naissance' AND fin_obs IS NULL
          AND fichier IN ({", ".join(f"'{f}'" for f in SIEGE_UNIQUE)})
        GROUP BY 1, 2, 3, 4 HAVING count(DISTINCT code_collectivite) > 1""")
    ctx.ecrire("mandat_local_ambigu", """
        SELECT a.per, c.nom_liste AS candidat, a.naissance, a.fichier, a.n AS collectivites_distinctes,
               a.collectivites
        FROM _ml_amb a LEFT JOIN candidat c ON c.per = a.per ORDER BY 2, 4""")
    # Un élu (même nom, prénom, naissance) revendiqué par deux candidats n'est rattaché à aucun.
    ctx.x("""CREATE OR REPLACE TEMP TABLE _ml AS
        SELECT * FROM _ml_tout m
        WHERE NOT EXISTS (SELECT 1 FROM (SELECT np, naissance FROM _ml_tout GROUP BY 1, 2
                                         HAVING count(DISTINCT per) > 1) k
                          WHERE k.np = m.np AND k.naissance = m.naissance)
          AND NOT (m.methode = 'nom_prenom_naissance' AND m.per IN (SELECT per FROM _ml_amb))""")

    # --- Deux lignes : le mandat et la fonction (Q50).
    ctx.x("""CREATE OR REPLACE TEMP TABLE _ml2 AS
        SELECT m.*, mm.libelle AS libelle_mandat,
               CASE WHEN fichier IN ('cm', 'sortants-cm', 'maires', 'sortants-maires') THEN 'municipal'
                    ELSE fichier END AS famille,
               fonction IS NOT NULL AND fonction <> mm.libelle AS est_fonction
        FROM _ml m JOIN _ml_mandat mm USING (fichier)""")
    ctx.x(f"""CREATE OR REPLACE TEMP TABLE _ml_lignes AS
        WITH g AS (   -- un mandat : candidat, sortant, famille de fichiers, collectivité, début
            SELECT per, sortant, famille, code_collectivite, debut_mandat,
                   bool_or(fin_obs IS NULL) AS courant, max(fin_obs) AS fin_obs,
                   arg_max(fin_obs_raison, fin_obs) AS fin_obs_raison
            FROM _ml2 GROUP BY ALL),
        mand AS (
            SELECT *, row_number() OVER (PARTITION BY per, sortant, famille, code_collectivite, debut_mandat
                                         ORDER BY CASE WHEN fichier LIKE '%maires' THEN 1 ELSE 0 END,
                                                  fin_obs NULLS FIRST, fichier) AS r
            FROM _ml2),
        fonc AS (
            SELECT f.*, row_number() OVER (PARTITION BY f.per, f.sortant, f.code_collectivite, f.fonction,
                                                        coalesce(f.debut_fonction, f.debut_mandat)
                                           ORDER BY CASE WHEN f.fichier LIKE '%maires' THEN 0 ELSE 1 END,
                                                    f.fin_obs NULLS FIRST, f.fichier) AS r,
                   -- Une fonction se termine quand plus aucune ligne courante du même mandat ne la porte.
                   NOT EXISTS (SELECT 1 FROM _ml2 c WHERE c.per = f.per AND c.sortant = f.sortant
                               AND c.famille = f.famille AND c.code_collectivite IS NOT DISTINCT FROM f.code_collectivite
                               AND c.debut_mandat IS NOT DISTINCT FROM f.debut_mandat
                               AND c.fonction = f.fonction AND c.fin_obs IS NULL) AS fonction_finie
            FROM _ml2 f WHERE f.est_fonction),
        lf AS (
            SELECT per, fichier, niveau, sortant, 'fonction' AS nature_periode, fonction, collectivite,
                   code_collectivite, departement, debut_mandat, debut_fonction,
                   coalesce(debut_fonction, debut_mandat) AS debut,
                   CASE WHEN fonction_finie THEN fin_obs END AS fin_obs,
                   CASE WHEN fonction_finie THEN fin_obs_raison END AS fin_obs_raison,
                   methode, decision, naissance, nom, prenom, prov_url, prov_point,
                   fichier || ':' || coalesce(code_collectivite, '') AS mandat_id
            FROM fonc WHERE r = 1),
        lm AS (
            SELECT m.per, m.fichier, m.niveau, m.sortant, 'mandat' AS nature_periode,
                   m.libelle_mandat AS fonction, m.collectivite, m.code_collectivite, m.departement,
                   m.debut_mandat, NULL::VARCHAR AS debut_fonction, m.debut_mandat AS debut,
                   CASE WHEN NOT g.courant THEN g.fin_obs END AS fin_obs,
                   CASE WHEN NOT g.courant THEN g.fin_obs_raison END AS fin_obs_raison,
                   m.methode, m.decision, m.naissance, m.nom, m.prenom, m.prov_url, m.prov_point,
                   m.fichier || ':' || coalesce(m.code_collectivite, '') AS mandat_id
            FROM mand m JOIN g ON g.per = m.per AND g.sortant = m.sortant AND g.famille = m.famille
                 AND g.code_collectivite IS NOT DISTINCT FROM m.code_collectivite
                 AND g.debut_mandat IS NOT DISTINCT FROM m.debut_mandat
            WHERE m.r = 1)
        SELECT * FROM lf
        UNION ALL
        SELECT * REPLACE (CASE WHEN mandat_id IN (SELECT lf.mandat_id FROM lf WHERE lf.per = lm.per)
                               THEN mandat_id || ':mandat' ELSE mandat_id END AS mandat_id)
        FROM lm""")

    # --- Wikidata P39 : mandats locaux terminés hors du répertoire (Q52).
    niveau_wd = _niveau_wd_sql("t")
    ctx.x(f"""CREATE OR REPLACE TEMP TABLE _ml_wd AS
        WITH w AS (
            SELECT element, declaration, any_value(poste_libelle) AS poste_libelle, min(debut) AS debut,
                   max(fin) AS fin, string_agg(DISTINCT juridiction, ' · ') AS juridiction,
                   string_agg(DISTINCT objet, ' · ') AS objet, any_value(prov_url) AS prov_url,
                   any_value(prov_point) AS prov_point
            FROM {wd} GROUP BY 1, 2),
        t AS (SELECT w.*, lower(concat_ws(' · ', poste_libelle, juridiction, objet)) AS t FROM w)
        SELECT c.per, t.*, {niveau_wd} AS niveau,
               CASE WHEN regexp_matches(lower(coalesce(t.poste_libelle, '')), '{FONCTION_WD}') THEN 'fonction'
                    ELSE 'mandat' END AS nature_periode
        FROM t JOIN candidat c ON c.element_wikidata = t.element
        WHERE t.debut IS NOT NULL AND t.fin IS NOT NULL AND t.fin < '{ref}' AND t.debut <= t.fin
          AND NOT regexp_matches(lower(coalesce(t.poste_libelle, '')), '{EXCLUS_WD}')""")
    ctx.x("""DELETE FROM _ml_wd WHERE niveau IS NULL""")
    # Chevauchement d'une période du répertoire de même niveau et de même nature (mandat ou
    # fonction), au-delà de 7 jours : les dates des deux sources diffèrent souvent de quelques jours.
    ctx.x(f"""DELETE FROM _ml_wd w WHERE EXISTS (
        SELECT 1 FROM _ml_lignes l WHERE l.per = w.per AND l.nature_periode = w.nature_periode
          AND CASE WHEN l.niveau = 'arrondissement' THEN 'municipal' ELSE l.niveau END = w.niveau
          AND least(w.fin::DATE, coalesce(l.fin_obs, CASE WHEN l.sortant AND l.niveau = 'municipal'
                                                         THEN '{FIN_SORTANTS}' END, '9999-12-31')::DATE)
              > greatest(w.debut::DATE, l.debut::DATE) + INTERVAL 7 DAY)""")

    ctx.ecrire("mandat_local_candidat", f"""
        SELECT per, fichier, niveau, sortant, nature_periode, fonction, collectivite, code_collectivite,
               departement, debut_mandat, debut_fonction, debut,
               coalesce(fin_obs, CASE WHEN sortant AND niveau = 'municipal' THEN '{FIN_SORTANTS}' END) AS fin,
               CASE WHEN fin_obs IS NOT NULL THEN 'observee'
                    WHEN sortant AND niveau = 'municipal' THEN 'deduite' END AS fin_nature,
               fin_obs IS NULL AND sortant AND niveau = 'municipal' AS fin_deduite,
               coalesce(fin_obs_raison, CASE WHEN sortant AND niveau = 'municipal' THEN '{RAISON_FIN}' END) AS fin_raison,
               methode, decision, naissance, nom AS nom_publie, prenom AS prenom_publie, mandat_id,
               'rne' AS source, NULL::VARCHAR AS declare_par,
               prov_url AS source_url, prov_point AS source_point
        FROM _ml_lignes
        UNION ALL
        SELECT per, 'wikidata', niveau, false,
               nature_periode, poste_libelle,
               CASE WHEN juridiction IS NOT NULL OR objet IS NOT NULL
                    THEN concat_ws(' · ', juridiction, objet) END,
               NULL, NULL, debut, NULL, debut, fin, 'declaree', false, '{RAISON_WIKIDATA}',
               'element_wikidata', NULL, NULL, NULL, NULL, 'wikidata:' || declaration,
               'wikidata', 'wikidata', prov_url, prov_point
        FROM _ml_wd
        ORDER BY per, debut, fichier, nature_periode""")

    # --- Ce qu'on dit d'un candidat (Q51, Q53).
    ctx.ecrire("mandat_local_recherche", f"""
        WITH nom_seul AS (   -- candidats sans date de naissance ni décision : élus de ce nom
            SELECT i.per, count(DISTINCT m.np || '|' || coalesce(m.naissance, '')) AS n
            FROM personne_identite i
            LEFT JOIN (SELECT DISTINCT {norm("coalesce(prenom, '') || nom")} AS np, naissance FROM {ml}) m
              ON m.np = {norm("coalesce(i.prenom, '') || i.nom")}
            WHERE i.naissance IS NULL AND i.nom IS NOT NULL
            GROUP BY 1)
        SELECT c.per,
               CASE WHEN c.per IN (SELECT per FROM mandat_local_candidat WHERE source = 'rne') THEN 'rattache'
                    WHEN c.per IN (SELECT per FROM _ml_amb) THEN 'ambigu_non_rattache'
                    WHEN c.per IN (SELECT per FROM _ml_id) THEN 'aucun_mandat'
                    WHEN coalesce(n.n, 0) = 0 THEN 'aucun_elu_de_ce_nom'
                    ELSE 'homonyme_non_rattache' END AS raison,
               coalesce(n.n, 0) AS elus_de_ce_nom,
               c.per IN (SELECT per FROM _ml_id) AS identite_recherchable
        FROM candidat c LEFT JOIN nom_seul n ON n.per = c.per ORDER BY c.per""")

    n = ctx.un("SELECT count(*) FROM candidat")
    avec = ctx.un("SELECT count(DISTINCT per) FROM mandat_local_candidat WHERE source = 'rne'")
    cherchables = ctx.un("SELECT count(DISTINCT per) FROM _ml_id")
    conflits = ctx.un("SELECT count(*) FROM (SELECT np, naissance FROM _ml_tout GROUP BY 1, 2 HAVING count(DISTINCT per) > 1)")
    ambigus = ctx.un("SELECT count(DISTINCT per) FROM _ml_amb")
    observees = ctx.un("SELECT count(*) FROM mandat_local_candidat WHERE fin_nature = 'observee'")
    wd_per = ctx.un("SELECT count(DISTINCT per) FROM mandat_local_candidat WHERE source = 'wikidata'")
    wd_n = ctx.un("SELECT count(*) FROM mandat_local_candidat WHERE source = 'wikidata'")
    for t in ("_ml_gen", "_ml_mandat", "_ml_v", "_ml_fin", "_ml_src", "_ml_id", "_ml_tout", "_ml_amb",
              "_ml", "_ml2", "_ml_lignes", "_ml_wd"):
        ctx.x(f"DROP TABLE IF EXISTS {t}")
    return {"candidats_avec_identite_recherchable": (cherchables, n),
            "candidats_avec_mandat_local": (avec, cherchables),
            "elus_revendiques_par_deux_candidats": (conflits, conflits),
            "candidats_ambigus_non_rattaches": (ambigus, ambigus),
            "fins_observees": (observees, observees),
            "candidats_avec_mandat_local_declare_par_wikidata": (wd_per, n),
            "lignes_declarees_par_wikidata": (wd_n, wd_n)}
