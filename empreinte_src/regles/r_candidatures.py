"""R-CANDIDATURES : les candidats à l'élection présidentielle de 2027 et leurs identifiants de
source (cahier 3.10 et 4.1 ; décisions de la propriétaire du 06/11 et du 13/11/2026).

**La liste** est celle de franceinfo (« la liste de candidats doit se baser sur celle de
franceinfo », 13/11/2026). franceinfo réserve la fouille de textes et de données et interdit son
site aux robots d'IA : la page n'est pas collectée. Elle est recopiée à la main dans une décision
`candidature` (`decisions/candidature/<date>-franceinfo.yaml`, une entrée par candidat : nom,
statut, parti, élément Wikidata), que la propriétaire valide en fusionnant la pull request
(option « A » du 13/11/2026). La liste en vigueur est celle du fichier le plus récent (champ
`date`) ; une personne d'une liste plus ancienne qui n'est plus dans la dernière garde sa ligne,
statut `non_listee` : ses données ne sont pas détruites (cahier 4.1), elle n'est plus affichée.

**L'identité** n'est jamais rattachée par le nom seul :

    élément Wikidata inscrit dans la décision  ->  identifiant Assemblée (P4123, `PA…`),
                                                   Sénat (P1808), Sycomore (P1045),
                                                   député européen (P1186, point `pe-eurodeputes`)

À défaut d'élément inscrit, l'article Wikipédia inscrit est suivi comme en version 1 (titre de
l'article == lien frwiki d'un élément, après la seule normalisation de MediaWiki). La requête
Wikidata collectée ne rend que les éléments qui portent un identifiant de l'Assemblée ou du
Sénat. Rattachements :

- `wikidata` : l'élément est connu de la requête, avec au plus un identifiant de chaque chambre ;
- `sans_identifiant_parlementaire` : élément inscrit (ou article) sans identifiant parlementaire ;
- `aucun_element` : ni élément ni article inscrits : fiche faite de ce que dit la liste ;
- `non_etabli` : élément mal écrit, élément dont l'article diffère de celui inscrit, plusieurs
  éléments ou identifiants d'une même chambre, ou identifiant déclaré pour deux candidats : rien
  n'est retenu, la raison est écrite.

**Wikipédia** (article « Candidatures à l'élection présidentielle française de 2027 ») reste lu,
pour deux usages : la date de déclaration (la ligne qui cite le même article, ou à défaut le même
nom écrit que celui inscrit dans `nom_wikipedia`), et un **détecteur** : un candidat que
Wikipédia dit déclaré et que la liste ne cite pas ou dit retiré, ou que la liste dit déclaré et
Wikipédia retiré, est un écart (table `candidature_ecart_wikipedia`, avertissement A9). L'écart n'ajoute ni
ne retire personne : seule une nouvelle décision le fait.
"""

NOM = "R-CANDIDATURES"
VERSION = 3
DEPEND = ()
SORTIES = ("candidature", "candidature_ecart_wikipedia")
DESCRIPTION = (
    "La liste des candidats est celle de franceinfo (« Qui sont les candidats déclarés à "
    "l'élection présidentielle de 2027 ? »), recopiée à la main et validée par la responsable du "
    "site : franceinfo n'autorise pas sa lecture par des programmes. Un candidat qui a retiré sa "
    "candidature, ou qui n'est plus dans la liste, n'est plus affiché, mais ses données sont "
    "gardées. Pour savoir qui est la personne, la liste inscrit son élément Wikidata, qui déclare "
    "ses identifiants à l'Assemblée nationale et au Sénat. Nous ne rapprochons jamais une "
    "personne par son seul nom : un candidat sans élément Wikidata, ou dont l'élément ne mène à "
    "aucun identifiant parlementaire, a une fiche faite de ce que dit la liste, et la fiche le "
    "dit. La date de déclaration vient de l'article de Wikipédia « Candidatures à l'élection "
    "présidentielle française de 2027 », qui sert aussi à signaler un candidat absent de la liste.")

ELECTION = "presidentielle-2027"
STATUTS = ("declaree", "retiree", "non_listee")

COLONNES_DECISION = {
    "election": "VARCHAR", "date": "VARCHAR", "source": "VARCHAR", "source_url": "VARCHAR",
    "source_titre": "VARCHAR", "nom": "VARCHAR", "statut": "VARCHAR", "parti": "VARCHAR",
    "wikidata": "VARCHAR", "article_frwiki": "VARCHAR", "nom_wikipedia": "VARCHAR",
    "rattachement_par_nom": "BOOLEAN", "note": "VARCHAR", "fichier": "VARCHAR",
}
COLONNES_CANDIDATURE = {
    "election": "VARCHAR", "statut": "VARCHAR", "rang": "INTEGER", "personne_source": "VARCHAR",
    "nom": "VARCHAR", "prenom": "VARCHAR", "nom_famille": "VARCHAR", "forme_nom": "VARCHAR",
    "article": "VARCHAR", "date_declaration": "VARCHAR", "date_declaration_texte": "VARCHAR",
    "date_declaration_raison": "VARCHAR", "date_declaration_phrase": "VARCHAR",
    "references": "VARCHAR[]", "nb_references": "INTEGER", "revision": "BIGINT",
    "page": "VARCHAR", "prov_url": "VARCHAR", "prov_version": "INTEGER",
}
COLONNES_WD = {"element": "VARCHAR", "propriete": "VARCHAR", "identifiant": "VARCHAR",
               "naissance": "VARCHAR", "article_frwiki": "VARCHAR", "prov_url": "VARCHAR"}

RAISON_SANS_DATE = ("non connue de nos sources : franceinfo ne date pas les candidatures, et la "
                    "liste de Wikipédia ne cite pas cette personne")


def vue_ou_vide(ctx, nom: str, colonnes: dict) -> str:
    """Le nom de la vue si elle existe, sinon une table vide de même forme (source non lue)."""
    if ctx.existe(nom):
        return nom
    cols = ", ".join(f'NULL::{t} AS "{c}"' for c, t in colonnes.items())
    return f"(SELECT {cols} WHERE false)"


def _decisions(ctx) -> str:
    """Les entrées des décisions `candidature`, colonnes normalisées (une colonne absente de
    tous les fichiers est NULL)."""
    if "candidature" not in getattr(ctx, "decisions", {}):
        return vue_ou_vide(ctx, "_aucune_decision_candidature", COLONNES_DECISION)
    presentes = {r[0] for r in ctx.x("DESCRIBE decision_candidature")}
    cols = ", ".join((f'CAST("{c}" AS {t}) AS "{c}"' if c in presentes else f'NULL::{t} AS "{c}"')
                     for c, t in COLONNES_DECISION.items())
    return f"(SELECT {cols} FROM decision_candidature)"


def titre_wp(x: str) -> str:
    """Titre d'article sous sa forme canonique MediaWiki (soulignés = espaces, première lettre
    en capitale) : ni accent retiré, ni casse changée ailleurs."""
    t = f"trim(regexp_replace(replace({x}, '_', ' '), '\\s+', ' ', 'g'))"
    return f"(CASE WHEN {x} IS NULL OR {t} = '' THEN NULL ELSE upper(left({t}, 1)) || substr({t}, 2) END)"


def _verifier_statuts(ctx, dec: str):
    mauvais = ctx.x(f"""SELECT fichier, nom, statut FROM {dec}
                        WHERE statut IS NULL OR statut NOT IN {STATUTS} ORDER BY 1""")
    if mauvais:
        raise ValueError("R-CANDIDATURES : statut inconnu dans une décision `candidature` "
                         f"(attendu : {', '.join(STATUTS)}) : {mauvais[:5]}")


def appliquer(ctx):
    dec = _decisions(ctx)
    _verifier_statuts(ctx, dec)
    wp = vue_ou_vide(ctx, "wp_candidatures__candidature", COLONNES_CANDIDATURE)
    wd = vue_ou_vide(ctx, "wd_identifiants__identifiant_externe", COLONNES_WD)
    an = vue_ou_vide(ctx, "an_acteurs__identite_source", {"uid": "VARCHAR"})
    sen = vue_ou_vide(ctx, "senat_export__identite_source", {"matricule": "VARCHAR"})
    pe = vue_ou_vide(ctx, "pe_eurodeputes__identifiant_pe", {"element": "VARCHAR", "identifiant": "VARCHAR"})
    pe_fiche = vue_ou_vide(ctx, "pe_eurodeputes__eurodepute", {"personne": "VARCHAR"})

    # Une ligne par personne : la liste la plus récente fait foi ; une personne d'une liste plus
    # ancienne absente de la dernière est « non listée ». Clé : l'élément inscrit, à défaut
    # l'article, à défaut le nom écrit.
    ctx.x(f"""CREATE OR REPLACE TEMP TABLE _cand AS
        WITH d AS (
            SELECT *, {titre_wp('article_frwiki')} AS article,
                   coalesce(trim(wikidata), {titre_wp('article_frwiki')}, nom_wikipedia, nom) AS personne_source
            FROM {dec} WHERE election = '{ELECTION}'),
        derniere AS (SELECT max("date") AS "date" FROM d),
        cur AS (SELECT d.*, statut AS statut_retenu FROM d, derniere WHERE d."date" = derniere."date"),
        h AS (SELECT d.*, 'non_listee' AS statut_retenu FROM d, derniere
              WHERE d."date" < derniere."date"
                AND d.personne_source NOT IN (SELECT personne_source FROM cur)
              QUALIFY row_number() OVER (PARTITION BY d.personne_source ORDER BY d."date" DESC) = 1)
        SELECT * FROM (SELECT * FROM cur UNION ALL BY NAME SELECT * FROM h)
        QUALIFY row_number() OVER (PARTITION BY personne_source
                ORDER BY CASE statut_retenu WHEN 'declaree' THEN 0 WHEN 'retiree' THEN 1 ELSE 2 END) = 1""")

    # Ligne de Wikipédia qui cite la même personne : même article, ou, sans article, le nom
    # écrit inscrit dans la décision (`nom_wikipedia`). Déclarée l'emporte sur retirée.
    ctx.x(f"""CREATE OR REPLACE TEMP TABLE _wp AS
        SELECT *, {titre_wp('article')} AS titre FROM {wp}
        WHERE election = '{ELECTION}'
        QUALIFY row_number() OVER (PARTITION BY coalesce({titre_wp('article')}, 'nom:' || nom)
                ORDER BY CASE statut WHEN 'declaree' THEN 0 ELSE 1 END, rang) = 1""")
    ctx.x("""CREATE OR REPLACE TEMP TABLE _cand_wp AS
        SELECT c.personne_source, any_value(w) AS w FROM _cand c JOIN _wp w
          ON (c.article IS NOT NULL AND w.titre = c.article)
          OR (c.article IS NULL AND w.titre IS NULL AND w.nom = c.nom_wikipedia)
        GROUP BY 1""")

    # Éléments : celui inscrit, sinon ceux dont le lien frwiki est l'article inscrit.
    ctx.x(f"""CREATE OR REPLACE TEMP TABLE _el AS
        SELECT c.personne_source, trim(c.wikidata) AS element, 'decision' AS origine
        FROM _cand c WHERE c.wikidata IS NOT NULL
        UNION ALL
        SELECT DISTINCT c.personne_source, w.element, 'lien_frwiki'
        FROM _cand c JOIN {wd} w ON {titre_wp('w.article_frwiki')} = c.article
        WHERE c.wikidata IS NULL AND c.article IS NOT NULL""")
    ctx.x(f"""CREATE OR REPLACE TEMP TABLE _ids AS
        SELECT c.personne_source,
               coalesce(list_sort(list(DISTINCT e.element) FILTER (WHERE e.element IS NOT NULL)), []::VARCHAR[]) AS elements,
               any_value(e.origine) AS origine,
               coalesce(list_sort(list(DISTINCT w.element) FILTER (WHERE w.element IS NOT NULL)), []::VARCHAR[]) AS elements_connus,
               coalesce(list_sort(list(DISTINCT w.identifiant) FILTER (WHERE w.propriete = 'P4123' AND w.identifiant IS NOT NULL)), []::VARCHAR[]) AS ids_an,
               coalesce(list_sort(list(DISTINCT w.identifiant) FILTER (WHERE w.propriete = 'P1808' AND w.identifiant IS NOT NULL)), []::VARCHAR[]) AS ids_senat,
               coalesce(list_sort(list(DISTINCT w.identifiant) FILTER (WHERE w.propriete = 'P1045' AND w.identifiant IS NOT NULL)), []::VARCHAR[]) AS ids_sycomore,
               coalesce(list_sort(list(DISTINCT w.naissance) FILTER (WHERE w.naissance IS NOT NULL)), []::VARCHAR[]) AS naissances,
               coalesce(list_sort(list(DISTINCT {titre_wp('w.article_frwiki')}) FILTER (WHERE w.article_frwiki IS NOT NULL)), []::VARCHAR[]) AS articles_element
        FROM _cand c LEFT JOIN _el e USING (personne_source)
        LEFT JOIN {wd} w ON w.element = e.element
        GROUP BY 1""")
    # Identifiant de député européen déclaré par Wikidata (P1186) pour l'élément retenu, lu par le
    # point `pe-eurodeputes` (décision Q3 du 13/11/2026).
    ctx.x(f"""CREATE OR REPLACE TEMP TABLE _pe AS
        SELECT element AS pe_element, list_sort(list(DISTINCT identifiant)) AS pe_ids
        FROM {pe} WHERE identifiant IS NOT NULL GROUP BY 1""")
    # Un identifiant déclaré pour deux candidats différents n'est retenu pour aucun.
    ctx.x("""CREATE OR REPLACE TEMP TABLE _partages AS
        SELECT id FROM (
            SELECT personne_source, unnest(elements || ids_an || ids_senat) AS id FROM _ids)
        GROUP BY id HAVING count(DISTINCT personne_source) > 1""")

    ctx.ecrire("candidature", f"""
        WITH r AS (
            SELECT c.*, i.elements, i.origine, i.elements_connus, i.ids_an, i.ids_senat,
                   i.ids_sycomore, i.naissances, i.articles_element, cw.w,
                   EXISTS (SELECT 1 FROM _partages p
                           WHERE list_contains(i.elements || i.ids_an || i.ids_senat, p.id)) AS partage
            FROM _cand c JOIN _ids i USING (personne_source)
            LEFT JOIN _cand_wp cw USING (personne_source)),
        s AS (
            SELECT r.*,
                CASE WHEN wikidata IS NOT NULL AND NOT regexp_full_match(trim(wikidata), 'Q[1-9][0-9]*')
                          THEN 'element_mal_ecrit'
                     WHEN wikidata IS NOT NULL AND article IS NOT NULL AND len(articles_element) > 0
                          AND NOT list_contains(articles_element, article) THEN 'article_different'
                     WHEN partage THEN 'partage'
                     WHEN len(elements) > 1 THEN 'plusieurs_elements'
                     WHEN len(ids_an) > 1 OR len(ids_senat) > 1 THEN 'plusieurs_identifiants'
                END AS defaut
            FROM r),
        t AS (
            SELECT s.*,
                CASE WHEN defaut IS NOT NULL THEN 'non_etabli'
                     WHEN len(elements) = 0 AND article IS NULL THEN 'aucun_element'
                     WHEN len(elements_connus) = 0 THEN 'sans_identifiant_parlementaire'
                     ELSE 'wikidata' END AS rattachement
            FROM s)
        SELECT '{ELECTION}' AS election, personne_source,
               -- Nom : celui de la ligne de Wikipédia qui cite le même article (la fiche ne
               -- change pas de nom ni d'adresse), sinon le titre de l'article sans sa précision
               -- entre parenthèses, sinon le nom écrit par la liste.
               coalesce(w.nom, regexp_replace(article, '\\s*\\([^)]*\\)\\s*$', ''), nom_wikipedia, nom) AS nom,
               nom AS nom_liste, w.prenom AS prenom, w.nom_famille AS nom_famille, w.forme_nom AS forme_nom,
               statut_retenu AS statut, statut AS statut_source, parti,
               w.statut AS statut_wikipedia,
               w.date_declaration AS date_declaration,
               w.date_declaration_texte AS date_declaration_texte,
               CASE WHEN w.date_declaration IS NOT NULL THEN w.date_declaration_raison
                    WHEN w IS NOT NULL THEN coalesce(w.date_declaration_raison, 'non connue')
                    ELSE '{RAISON_SANS_DATE}' END AS date_declaration_raison,
               w.date_declaration_phrase AS date_declaration_phrase,
               CASE WHEN w IS NOT NULL THEN w.prov_url END AS date_declaration_source_url,
               w.revision AS revision_wikipedia,
               article AS article_frwiki, nom_wikipedia,
               CASE WHEN rattachement IN ('wikidata', 'sans_identifiant_parlementaire') AND len(elements) = 1
                    THEN elements[1] END AS element_wikidata,
               CASE WHEN rattachement IN ('wikidata', 'sans_identifiant_parlementaire') THEN origine END AS origine_element,
               coalesce(rattachement_par_nom, false) AS rattachement_par_nom,
               CASE WHEN rattachement = 'wikidata' AND len(ids_an) = 1 THEN ids_an[1] END AS acteur,
               CASE WHEN rattachement = 'wikidata' AND len(ids_senat) = 1 THEN ids_senat[1] END AS matricule_senat,
               CASE WHEN rattachement = 'wikidata' AND len(ids_sycomore) = 1 THEN ids_sycomore[1] END AS sycomore,
               CASE WHEN rattachement = 'wikidata' AND len(naissances) = 1 THEN naissances[1] END AS naissance_wikidata,
               CASE WHEN len(pe_ids) = 1 THEN pe_ids[1] END AS eurodepute,
               CASE WHEN len(pe_ids) = 1 THEN pe_ids[1] IN (SELECT personne FROM {pe_fiche}) END AS eurodepute_connu_pe,
               rattachement,
               CASE rattachement
                    WHEN 'aucun_element' THEN 'la liste n''inscrit ni élément Wikidata ni article pour ce nom'
                    WHEN 'sans_identifiant_parlementaire' THEN 'l''élément Wikidata de cette personne ne déclare aucun identifiant de l''Assemblée ou du Sénat'
                    WHEN 'non_etabli' THEN CASE defaut
                         WHEN 'element_mal_ecrit' THEN 'élément Wikidata mal écrit dans la décision'
                         WHEN 'article_different' THEN 'l''élément Wikidata inscrit a pour lien un autre article que celui inscrit'
                         WHEN 'partage' THEN 'identifiant déclaré pour plusieurs candidats'
                         WHEN 'plusieurs_elements' THEN 'plusieurs éléments Wikidata ont cet article pour lien'
                         ELSE 'plusieurs identifiants d''une même chambre pour cet élément' END
               END AS raison_rattachement,
               elements AS elements_candidats, ids_an AS identifiants_an, ids_senat AS identifiants_senat,
               CASE WHEN rattachement = 'wikidata' AND len(ids_an) = 1
                    THEN ids_an[1] IN (SELECT uid FROM {an}) END AS acteur_connu_an,
               CASE WHEN rattachement = 'wikidata' AND len(ids_senat) = 1
                    THEN ids_senat[1] IN (SELECT matricule FROM {sen}) END AS matricule_connu_senat,
               w."references" AS "references", w.nb_references AS nb_references,
               source AS source_liste, source_url, source_titre, "date" AS date_liste, fichier AS decision,
               note,
               CASE WHEN article IS NOT NULL
                    THEN 'https://fr.wikipedia.org/wiki/' || url_encode(replace(article, ' ', '_'))
                    END AS article_url,
               CASE WHEN rattachement IN ('wikidata', 'sans_identifiant_parlementaire') AND len(elements) = 1
                    THEN 'https://www.wikidata.org/wiki/' || elements[1] END AS element_url
        FROM t LEFT JOIN _pe ON len(t.elements) = 1 AND _pe.pe_element = t.elements[1]
             AND t.rattachement IN ('wikidata', 'sans_identifiant_parlementaire')
        ORDER BY statut, nom""")

    # Détecteur : écarts entre la liste et Wikipédia (jamais une entrée ni une sortie de liste).
    ctx.ecrire("candidature_ecart_wikipedia", """
        WITH lies AS (
            SELECT w.titre, w.nom AS nom_wp, w.statut AS statut_wp, c.statut AS statut_liste,
                   c.nom AS nom_liste
            FROM _wp w LEFT JOIN _cand c
              ON (w.titre IS NOT NULL AND c.article = w.titre)
              OR (w.titre IS NULL AND c.article IS NULL AND c.nom_wikipedia = w.nom))
        SELECT CASE WHEN statut_liste IS NULL THEN 'declare_par_wikipedia_absent_de_la_liste'
                    WHEN statut_wp = 'declaree' THEN 'declare_selon_wikipedia_retire_dans_la_liste'
                    ELSE 'retire_selon_wikipedia_declare_dans_la_liste' END AS ecart,
               coalesce(nom_liste, nom_wp) AS nom, nom_wp AS nom_wikipedia, titre AS article_frwiki,
               statut_wp AS statut_wikipedia, statut_liste
        FROM lies
        WHERE (statut_wp = 'declaree' AND statut_liste IS NULL)
           OR (statut_wp = 'declaree' AND statut_liste = 'retiree')
           OR (statut_wp = 'retiree' AND statut_liste = 'declaree')
        ORDER BY 1, 2""")

    n = ctx.un("SELECT count(*) FROM candidature")
    decl = ctx.un("SELECT count(*) FROM candidature WHERE statut = 'declaree'")
    el = ctx.un("SELECT count(*) FROM candidature WHERE element_wikidata IS NOT NULL")
    par_nom = ctx.un("SELECT count(*) FROM candidature WHERE rattachement_par_nom")
    wdk = ctx.un("SELECT count(*) FROM candidature WHERE rattachement = 'wikidata'")
    an_ = ctx.un("SELECT count(*) FROM candidature WHERE acteur IS NOT NULL")
    an_connu = ctx.un("SELECT count(*) FROM candidature WHERE acteur_connu_an")
    sen_ = ctx.un("SELECT count(*) FROM candidature WHERE matricule_senat IS NOT NULL")
    pe_ = ctx.un("SELECT count(*) FROM candidature WHERE eurodepute IS NOT NULL")
    date = ctx.un("SELECT count(*) FROM candidature WHERE statut = 'declaree' AND date_declaration IS NOT NULL")
    ecarts = ctx.un("SELECT count(*) FROM candidature_ecart_wikipedia")
    wp_decl = ctx.un("SELECT count(*) FROM _wp WHERE statut = 'declaree'")
    for t in ("_cand", "_wp", "_cand_wp", "_el", "_ids", "_partages", "_pe"):
        ctx.x(f"DROP TABLE IF EXISTS {t}")
    return {"candidats_declares": (decl, n),
            "element_wikidata_retenu": (el, n),
            "element_trouve_par_le_nom_valide_par_decision": (par_nom, n),
            "rattache_par_wikidata": (wdk, n),
            "identifiant_assemblee_declare": (an_, n),
            "identifiant_assemblee_present_dans_l_archive": (an_connu, an_),
            "identifiant_senat_declare": (sen_, n),
            "identifiant_parlement_europeen_declare": (pe_, n),
            "date_de_declaration_connue": (date, decl),
            "ecarts_avec_wikipedia": (ecarts, wp_decl)}
