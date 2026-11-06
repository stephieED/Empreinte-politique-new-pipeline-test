"""R-CANDIDATURES : les candidats à l'élection présidentielle de 2027 et leurs identifiants de
source (cahier 3.10 et 4.1 ; décision de la propriétaire du 06/11/2026).

Un candidat listé comme déclaré dans l'article Wikipédia « Candidatures à l'élection
présidentielle française de 2027 » est **validé**. Son identité est rattachée par des
identifiants **déclarés**, jamais par le nom :

    titre de l'article cité dans la liste  ==  lien frwiki (sitelink) d'un élément Wikidata
    élément Wikidata  ->  identifiant Assemblée (P4123, `PA…`), Sénat (P1808, matricule),
                          Sycomore (P1045)

Les deux titres sont comparés **après la seule normalisation de MediaWiki** (espaces et
soulignés équivalents, première lettre en capitale) : c'est le même titre, pas un nom
rapproché. Un titre qui est une redirection ne retrouve pas son élément (« non établi » par
défaut de lien, jamais deviné).

La requête Wikidata collectée ne rend que les éléments qui portent un identifiant de
l'Assemblée ou du Sénat : un candidat dont l'article n'y est pas est « sans identifiant
parlementaire » (son élément Wikidata n'est pas connu). Rattachements :

- `wikidata` : un seul élément porte ce titre, et au plus un identifiant de chaque chambre ;
- `aucun_article` : la liste ne lie aucun article (`nolink`) : fiche avec ce que dit Wikipédia ;
- `sans_identifiant_parlementaire` : article cité, aucun élément à identifiant parlementaire ;
- `non_etabli` : plusieurs éléments pour un titre, plusieurs identifiants d'une même chambre,
  ou un identifiant déclaré pour deux candidats : rien n'est retenu, la raison est écrite.

Une candidature « retirée » reste une ligne (statut `retiree`) ; un candidat qui n'est plus
dans la liste mais l'a été dans une version lue garde sa ligne (statut `non_listee`) : ses
données ne sont pas détruites (cahier 4.1), il n'est simplement plus affiché.
"""

NOM = "R-CANDIDATURES"
VERSION = 1
DEPEND = ()
SORTIES = ("candidature",)
DESCRIPTION = (
    "La liste des candidats est celle de l'article de Wikipédia « Candidatures à l'élection "
    "présidentielle française de 2027 » : un candidat qu'il présente comme déclaré est retenu ; "
    "un candidat qui a retiré sa candidature n'est plus affiché, mais ses données sont gardées. "
    "Pour savoir qui est la personne, nous suivons le lien de la liste vers l'article de la "
    "personne, puis l'élément Wikidata relié à cet article, qui déclare ses identifiants à "
    "l'Assemblée nationale et au Sénat. Nous ne rapprochons jamais une personne par son seul "
    "nom : un candidat sans article, ou dont l'article ne mène à aucun identifiant "
    "parlementaire, a une fiche faite de ce que dit Wikipédia, et la fiche le dit.")

ELECTION = "presidentielle-2027"

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


def vue_ou_vide(ctx, nom: str, colonnes: dict) -> str:
    """Le nom de la vue si elle existe, sinon une table vide de même forme (source non lue)."""
    if ctx.existe(nom):
        return nom
    cols = ", ".join(f"NULL::{t} AS {c}" for c, t in colonnes.items())
    return f"(SELECT {cols} WHERE false)"


def titre_wp(x: str) -> str:
    """Titre d'article sous sa forme canonique MediaWiki (soulignés = espaces, première lettre
    en capitale) : ni accent retiré, ni casse changée ailleurs."""
    t = f"trim(regexp_replace(replace({x}, '_', ' '), '\\s+', ' ', 'g'))"
    return f"(CASE WHEN {x} IS NULL OR {t} = '' THEN NULL ELSE upper(left({t}, 1)) || substr({t}, 2) END)"


def appliquer(ctx):
    cand = vue_ou_vide(ctx, "wp_candidatures__candidature", COLONNES_CANDIDATURE)
    hist = vue_ou_vide(ctx, "wp_candidatures__candidature__hist", COLONNES_CANDIDATURE)
    wd = vue_ou_vide(ctx, "wd_identifiants__identifiant_externe", COLONNES_WD)
    an = vue_ou_vide(ctx, "an_acteurs__identite_source", {"uid": "VARCHAR"})
    sen = vue_ou_vide(ctx, "senat_export__identite_source", {"matricule": "VARCHAR"})

    # Une ligne par personne citée (clé de la source : le titre de l'article, à défaut le nom
    # écrit). Déclarée l'emporte sur retirée si la page cite deux fois la même personne.
    ctx.x(f"""CREATE OR REPLACE TEMP TABLE _cand AS
        WITH cur AS (SELECT * FROM {cand} WHERE election = '{ELECTION}'),
        c AS (SELECT *, statut AS statut_retenu FROM cur
              QUALIFY row_number() OVER (PARTITION BY personne_source
                      ORDER BY CASE statut WHEN 'declaree' THEN 0 ELSE 1 END, rang) = 1),
        h AS (SELECT *, 'non_listee' AS statut_retenu FROM {hist} x
              WHERE x.election = '{ELECTION}'
                AND x.personne_source NOT IN (SELECT personne_source FROM cur)
              QUALIFY row_number() OVER (PARTITION BY personne_source
                      ORDER BY prov_version DESC, CASE statut WHEN 'declaree' THEN 0 ELSE 1 END, rang) = 1)
        SELECT personne_source, nom, prenom, nom_famille, forme_nom, statut AS statut_source,
               statut_retenu AS statut, {titre_wp('article')} AS article_frwiki,
               date_declaration, date_declaration_texte, date_declaration_raison,
               date_declaration_phrase, "references", nb_references, revision, page,
               prov_url AS source_url
        FROM (SELECT * FROM c UNION ALL BY NAME SELECT * FROM h)""")

    # Éléments Wikidata dont le lien frwiki est le titre cité, et leurs identifiants.
    ctx.x(f"""CREATE OR REPLACE TEMP TABLE _wd AS
        SELECT {titre_wp('w.article_frwiki')} AS titre, w.element, w.propriete, w.identifiant,
               w.naissance
        FROM {wd} w
        WHERE w.article_frwiki IS NOT NULL
          AND {titre_wp('w.article_frwiki')} IN (SELECT article_frwiki FROM _cand)""")
    ctx.x(f"""CREATE OR REPLACE TEMP TABLE _ids AS
        SELECT c.personne_source,
               coalesce(list_sort(list(DISTINCT w.element) FILTER (WHERE w.element IS NOT NULL)), []::VARCHAR[]) AS elements,
               coalesce(list_sort(list(DISTINCT w.identifiant) FILTER (WHERE w.propriete = 'P4123' AND w.identifiant IS NOT NULL)), []::VARCHAR[]) AS ids_an,
               coalesce(list_sort(list(DISTINCT w.identifiant) FILTER (WHERE w.propriete = 'P1808' AND w.identifiant IS NOT NULL)), []::VARCHAR[]) AS ids_senat,
               coalesce(list_sort(list(DISTINCT w.identifiant) FILTER (WHERE w.propriete = 'P1045' AND w.identifiant IS NOT NULL)), []::VARCHAR[]) AS ids_sycomore,
               coalesce(list_sort(list(DISTINCT w.naissance) FILTER (WHERE w.naissance IS NOT NULL)), []::VARCHAR[]) AS naissances
        FROM _cand c LEFT JOIN _wd w ON w.titre = c.article_frwiki
        GROUP BY 1""")
    # Un identifiant déclaré pour deux candidats différents n'est retenu pour aucun.
    ctx.x("""CREATE OR REPLACE TEMP TABLE _partages AS
        SELECT id FROM (
            SELECT personne_source, unnest(elements || ids_an || ids_senat) AS id FROM _ids)
        GROUP BY id HAVING count(DISTINCT personne_source) > 1""")

    ctx.ecrire("candidature", f"""
        WITH r AS (
            SELECT c.*, i.elements, i.ids_an, i.ids_senat, i.ids_sycomore, i.naissances,
                   EXISTS (SELECT 1 FROM _partages p
                           WHERE list_contains(i.elements || i.ids_an || i.ids_senat, p.id)) AS partage
            FROM _cand c JOIN _ids i USING (personne_source)),
        s AS (
            SELECT r.*,
                CASE WHEN article_frwiki IS NULL THEN 'aucun_article'
                     WHEN len(elements) = 0 THEN 'sans_identifiant_parlementaire'
                     WHEN len(elements) > 1 OR len(ids_an) > 1 OR len(ids_senat) > 1 OR partage
                          THEN 'non_etabli'
                     ELSE 'wikidata' END AS rattachement
            FROM r)
        SELECT personne_source, nom, prenom, nom_famille, forme_nom, statut, statut_source,
               date_declaration, date_declaration_texte, date_declaration_raison,
               date_declaration_phrase, article_frwiki,
               CASE WHEN rattachement = 'wikidata' THEN elements[1] END AS element_wikidata,
               CASE WHEN rattachement = 'wikidata' AND len(ids_an) = 1 THEN ids_an[1] END AS acteur,
               CASE WHEN rattachement = 'wikidata' AND len(ids_senat) = 1 THEN ids_senat[1] END AS matricule_senat,
               CASE WHEN rattachement = 'wikidata' AND len(ids_sycomore) = 1 THEN ids_sycomore[1] END AS sycomore,
               CASE WHEN rattachement = 'wikidata' AND len(naissances) = 1 THEN naissances[1] END AS naissance_wikidata,
               rattachement,
               CASE rattachement
                    WHEN 'aucun_article' THEN 'la liste ne lie aucun article à ce nom'
                    WHEN 'sans_identifiant_parlementaire' THEN 'aucun élément Wikidata à identifiant de l''Assemblée ou du Sénat n''a cet article pour lien'
                    WHEN 'non_etabli' THEN
                         CASE WHEN partage THEN 'identifiant déclaré pour plusieurs candidats'
                              WHEN len(elements) > 1 THEN 'plusieurs éléments Wikidata ont cet article pour lien'
                              ELSE 'plusieurs identifiants d''une même chambre pour cet élément' END
               END AS raison_rattachement,
               elements AS elements_candidats, ids_an AS identifiants_an, ids_senat AS identifiants_senat,
               CASE WHEN rattachement = 'wikidata' AND len(ids_an) = 1
                    THEN ids_an[1] IN (SELECT uid FROM {an}) END AS acteur_connu_an,
               CASE WHEN rattachement = 'wikidata' AND len(ids_senat) = 1
                    THEN ids_senat[1] IN (SELECT matricule FROM {sen}) END AS matricule_connu_senat,
               "references", nb_references, revision, page, source_url,
               CASE WHEN article_frwiki IS NOT NULL
                    THEN 'https://fr.wikipedia.org/wiki/' || url_encode(replace(article_frwiki, ' ', '_'))
                    END AS article_url,
               CASE WHEN rattachement = 'wikidata' THEN 'https://www.wikidata.org/wiki/' || elements[1]
                    END AS element_url
        FROM s ORDER BY statut, nom""")

    n = ctx.un("SELECT count(*) FROM candidature")
    decl = ctx.un("SELECT count(*) FROM candidature WHERE statut = 'declaree'")
    art = ctx.un("SELECT count(*) FROM candidature WHERE article_frwiki IS NOT NULL")
    wdk = ctx.un("SELECT count(*) FROM candidature WHERE rattachement = 'wikidata'")
    an_ = ctx.un("SELECT count(*) FROM candidature WHERE acteur IS NOT NULL")
    an_connu = ctx.un("SELECT count(*) FROM candidature WHERE acteur_connu_an")
    sen_ = ctx.un("SELECT count(*) FROM candidature WHERE matricule_senat IS NOT NULL")
    date = ctx.un("SELECT count(*) FROM candidature WHERE statut = 'declaree' AND date_declaration IS NOT NULL")
    for t in ("_cand", "_wd", "_ids", "_partages"):
        ctx.x(f"DROP TABLE IF EXISTS {t}")
    return {"candidats_declares": (decl, n),
            "article_wikipedia_cite": (art, n),
            "rattache_par_wikidata": (wdk, art),
            "identifiant_assemblee_declare": (an_, n),
            "identifiant_assemblee_present_dans_l_archive": (an_connu, an_),
            "identifiant_senat_declare": (sen_, n),
            "date_de_declaration_connue": (date, decl)}
