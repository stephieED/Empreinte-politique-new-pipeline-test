"""R-IDENTITE : un identifiant interne `per:NNNNNN` pour chaque candidat, son identité sourcée et
son adresse publique (doc. 1, 1.2.2, 1.3.4 et 1.6 ; correction P1).

1. **Registre d'abord** (`ctx.registre`, `empreinte_src/identites.py`) : chaque candidat forme
   un groupe d'identifiants de source qui le désignent tous — `("wikipedia", titre de
   l'article)`, `("wd", élément)`, `("an", PA…)`, `("senat", matricule)` — tels que
   R-CANDIDATURES les a établis. Le registre rend le `per` : une attribution acquise ne change
   jamais, une personne nouvelle reçoit le numéro suivant, dans un ordre qui ne dépend pas de
   l'ordre de lecture. Un candidat sans article garde la clé sous laquelle le registre le
   connaît, `("wikipedia-nom", nom écrit par Wikipédia)`, que la décision inscrit
   (`nom_wikipedia`) ; un candidat nouveau sans article ni élément forme le groupe
   `("liste-nom", nom écrit par la liste)`, **sans rapprochement** : s'il reçoit plus tard un
   élément, c'est une décision qui réunira les deux numéros. Sans registre, la règle échoue :
   elle ne fabrique jamais de numéro de passage.
2. **Identité** : chaque champ vient d'une source nommée (`source_<champ>`), dans cet ordre :
   l'archive de l'Assemblée (si l'identifiant `PA` y est), l'export du Sénat (si le matricule
   y est), Wikidata (date de naissance), Wikipédia (nom), la liste des candidats (nom, à
   défaut de tout le reste). Une date de naissance aberrante
   (avant le 02/01/1900, dont la sentinelle 1900-01-01) n'est pas retenue ; un écart entre
   l'Assemblée et Wikidata est signalé (`naissance_concordance`).
3. **Adresse** : forme lisible du nom (`francois-ruffin`) ; si une autre personne connue (un
   autre candidat, ou un acteur de l'archive de l'Assemblée qui n'est pas lui) a la même, on
   ajoute l'année de naissance (`jean-martin-1962`) ; sans année, ou si l'année ne départage
   pas, pas d'adresse (raison écrite) et pas de fiche. L'adresse est rendue ici ; son
   inscription au registre des adresses se fait à la publication.
4. **Publié** : un candidat déclaré, avec une adresse. Retiré ou plus listé : non publié, mais
   gardé (cahier 4.1).
"""
import pyarrow as pa

from .r_candidatures import vue_ou_vide

NOM = "R-IDENTITE"
VERSION = 4
DEPEND = ("R-CANDIDATURES",)
SORTIES = ("candidat", "personne_identite", "correspondance")
DESCRIPTION = (
    "Chaque candidat reçoit un numéro interne, gardé pour toujours, attaché aux identifiants "
    "que lui donnent ses sources : l'article Wikipédia, l'élément Wikidata, l'identifiant de "
    "l'Assemblée nationale, le matricule du Sénat. Deux sources ne désignent la même personne "
    "que si un identifiant déclaré les relie, jamais par le nom seul. Le nom, la date et le "
    "lieu de naissance et la profession viennent, dans cet ordre, de l'Assemblée nationale, du "
    "Sénat, de Wikidata, de Wikipédia, puis de la liste des candidats, et la fiche dit d'où "
    "vient chaque champ. Quand l'Assemblée donne pour profession une catégorie "
    "socioprofessionnelle de l'INSEE précédée de son code (« (33) - Cadre de la fonction "
    "publique »), le code est ôté et la fiche dit qu'il s'agit d'une catégorie. Une date "
    "de naissance manifestement fausse n'est pas retenue. L'adresse de la fiche est le nom "
    "écrit simplement ; deux personnes de même nom se distinguent par leur année de naissance.")

URL_DEPUTE = "https://www.assemblee-nationale.fr/dyn/deputes/"
# Code de catégorie socioprofessionnelle en tête d'un libellé de profession (« (85) - … »).
CODE_PCS = r"^\s*\(\d+\)\s*-\s*"


def slug(x: str) -> str:
    """Forme d'adresse : minuscules sans accents, ligatures défaites, tout le reste en tirets,
    sans la précision entre parenthèses d'un titre (« (homme politique) »)."""
    s = (f"lower(strip_accents(replace(replace(replace(replace(regexp_replace({x}, '\\s*\\([^)]*\\)\\s*$', ''), "
         f"'œ', 'oe'), 'Œ', 'Oe'), 'æ', 'ae'), 'Æ', 'Ae')))")
    return f"trim(regexp_replace({s}, '[^a-z0-9]+', '-', 'g'), '-')"


def _groupe(r) -> list[tuple[str, str]]:
    g = [("wikipedia", r["article_frwiki"])] if r["article_frwiki"] else []
    if r["nom_wikipedia"]:
        g.append(("wikipedia-nom", r["nom_wikipedia"]))
    if not g:
        g.append(("liste-nom", r["nom_liste"]))
    for src, col in (("wd", "element_wikidata"), ("an", "acteur"), ("senat", "matricule_senat"),
                     ("pe", "eurodepute")):
        if r[col]:
            g.append((src, r[col]))
    return g


def appliquer(ctx):
    """Applique R-IDENTITE : attribue à chaque candidat son numéro `per:NNNNNN` dans le registre
    des identités (`ctx.registre`, complété en mémoire), puis écrit `correspondance`,
    `personne_identite` et `candidat` (voir la description du module). Lève `RuntimeError` sans
    registre ou sans génération (`ctx.generation`). Rend la couverture,
    `{nom: (numérateur, dénominateur)}` : `candidats_publies`, `rattache_assemblee`,
    `rattache_senat`, `sans_identifiant_parlementaire`, `adresse_etablie`, `naissance_connue`."""
    if ctx.registre is None:
        raise RuntimeError(
            "R-IDENTITE : aucun registre des identités (ctx.registre est None). Le numéro d'une "
            "personne est acquis et vient du registre de l'entrepôt : passer "
            "Contexte(..., registre=RegistreIdentites(<entrepôt>), generation=<n>).")
    if ctx.generation is None:
        raise RuntimeError("R-IDENTITE : génération inconnue (ctx.generation est None) : "
                           "le registre date chaque attribution par sa génération.")

    cur = ctx.con.execute("""SELECT personne_source, nom, nom_liste, nom_wikipedia, article_frwiki,
                                    element_wikidata, origine_element, acteur, matricule_senat,
                                    eurodepute, rattachement FROM candidature""")
    cols = [d[0] for d in cur.description]
    lignes = [dict(zip(cols, x)) for x in cur.fetchall()]
    groupes = [_groupe(r) for r in lignes]
    pers = ctx.registre.attribuer(groupes, ctx.generation)
    # Les clés inscrites par la décision `candidature` sont validées par la propriétaire ; les
    # identifiants parlementaires en sont tirés par Wikidata.
    methode = {"wikipedia": "article_inscrit_par_decision", "wikipedia-nom": "nom_ecrit_par_wikipedia_inscrit_par_decision",
               "liste-nom": "nom_ecrit_par_la_liste_sans_rapprochement",
               "an": "identifiant_declare_wikidata_P4123", "senat": "identifiant_declare_wikidata_P1808",
               "pe": "identifiant_declare_wikidata_P1186"}

    def meth(r, s):
        """Rend la méthode de rattachement de l'identifiant de source `s` pour la candidature `r` :
        pour Wikidata (`wd`), selon que l'élément a été inscrit par décision ou trouvé par le lien
        de l'article ; pour les autres sources, la méthode de `methode`."""
        if s == "wd":
            return ("element_inscrit_par_decision" if r["origine_element"] == "decision"
                    else "lien_frwiki_de_l_element")
        return methode[s]
    corr = [{"personne_source": r["personne_source"], "per": pers[g[0]], "source": s, "uid": u,
             "methode": meth(r, s),
             "statut": "automatique" if s in ("an", "senat", "pe") or meth(r, s) == "lien_frwiki_de_l_element"
                       else "validee"}
            for r, g in zip(lignes, groupes) for (s, u) in g]
    schema = pa.schema([(c, pa.string()) for c in
                        ("personne_source", "per", "source", "uid", "methode", "statut")])
    ctx.con.register("_ident_corr", pa.Table.from_pylist(corr, schema=schema))
    ctx.x("CREATE OR REPLACE TEMP TABLE _ident_per AS SELECT DISTINCT personne_source, per FROM _ident_corr")
    ctx.ecrire("correspondance", """
        SELECT per, source, uid, methode, statut, personne_source FROM _ident_corr ORDER BY per, source""")

    an = vue_ou_vide(ctx, "an_acteurs__identite_source", {
        "uid": "VARCHAR", "civilite": "VARCHAR", "prenom": "VARCHAR", "nom": "VARCHAR",
        "date_naissance": "VARCHAR", "ville_naissance": "VARCHAR",
        "departement_naissance": "VARCHAR", "pays_naissance": "VARCHAR", "profession": "VARCHAR",
        "date_deces": "VARCHAR"})
    sen = vue_ou_vide(ctx, "senat_export__identite_source", {
        "matricule": "VARCHAR", "civilite": "VARCHAR", "prenom": "VARCHAR", "nom": "VARCHAR",
        "date_naissance": "VARCHAR", "profession": "VARCHAR", "date_deces": "VARCHAR"})
    valide = "({d} IS NOT NULL AND {d} >= '1900-01-02' AND {d} ~ '^\\d{{4}}-\\d{{2}}-\\d{{2}}$')"

    ctx.ecrire("personne_identite", f"""
        WITH c AS (SELECT c.*, p.per FROM candidature c JOIN _ident_per p USING (personne_source)),
        a AS (SELECT * FROM {an} QUALIFY row_number() OVER (PARTITION BY uid) = 1),
        s AS (SELECT * FROM {sen} QUALIFY row_number() OVER (PARTITION BY matricule) = 1),
        j AS (
            SELECT c.per, c.personne_source, c.nom AS nom_wikipedia, c.prenom AS prenom_wikipedia,
                   c.nom_famille AS nom_famille_wikipedia, c.article_url, c.element_url,
                   (c.article_frwiki IS NOT NULL OR c.nom_wikipedia IS NOT NULL) AS nom_par_wikipedia,
                   c.source_url AS liste_url,
                   c.naissance_wikidata, c.acteur, c.matricule_senat,
                   a.uid IS NOT NULL AS an_ok, s.matricule IS NOT NULL AS sen_ok,
                   a.civilite AS civ_an, a.prenom AS prenom_an, a.nom AS nom_an,
                   a.date_naissance AS naiss_an, a.ville_naissance, a.departement_naissance,
                   a.pays_naissance, a.profession AS prof_an, a.date_deces AS deces_an,
                   s.civilite AS civ_sen, s.prenom AS prenom_sen, s.nom AS nom_sen,
                   s.date_naissance AS naiss_sen, s.profession AS prof_sen, s.date_deces AS deces_sen
            FROM c LEFT JOIN a ON a.uid = c.acteur LEFT JOIN s ON s.matricule = c.matricule_senat),
        k AS (
            SELECT j.*,
                CASE WHEN {valide.format(d='naiss_an')} THEN naiss_an
                     WHEN {valide.format(d='naiss_sen')} THEN naiss_sen
                     WHEN {valide.format(d='naissance_wikidata')} THEN naissance_wikidata END AS naissance,
                CASE WHEN {valide.format(d='naiss_an')} THEN 'an'
                     WHEN {valide.format(d='naiss_sen')} THEN 'senat'
                     WHEN {valide.format(d='naissance_wikidata')} THEN 'wikidata' END AS source_naissance,
                coalesce(naiss_an, naiss_sen, naissance_wikidata) IS NOT NULL
                    AND NOT ({valide.format(d='naiss_an')} OR {valide.format(d='naiss_sen')}
                             OR {valide.format(d='naissance_wikidata')}) AS naissance_aberrante
            FROM j),
        k2 AS (
            -- Issue #46 (décision du 14/11/2026, « Libellé sans le code ») : l'Assemblée publie
            -- parfois dans `profession` la catégorie socioprofessionnelle de l'INSEE, précédée de
            -- son code (« (33) - Cadre de la fonction publique » ; 128 acteurs sur 2 164 avec une
            -- profession, mesuré le 14/11/2026). Le code est ôté, le libellé gardé tel quel (même
            -- tronqué par la source), et `profession_nature` dit qu'il s'agit d'une catégorie.
            SELECT k.*, regexp_matches(prof_an, '{CODE_PCS}') AS prof_an_code,
                   nullif(trim(regexp_replace(prof_an, '{CODE_PCS}', '')), '') AS prof_an_net
            FROM k)
        SELECT per,
               coalesce(nom_an, nom_sen, nom_famille_wikipedia, nom_wikipedia) AS nom,
               coalesce(prenom_an, prenom_sen, prenom_wikipedia) AS prenom,
               naissance,
               CASE WHEN ville_naissance IS NOT NULL THEN ville_naissance ||
                    CASE WHEN departement_naissance IS NOT NULL THEN ' (' || departement_naissance || ')'
                         WHEN pays_naissance IS NOT NULL AND pays_naissance <> 'France' THEN ' (' || pays_naissance || ')'
                         ELSE '' END END AS lieu_naissance,
               coalesce(prof_an_net, prof_sen) AS profession,
               CASE WHEN prof_an_net IS NOT NULL AND prof_an_code THEN 'categorie_socioprofessionnelle'
                    WHEN coalesce(prof_an_net, prof_sen) IS NOT NULL THEN 'profession' END AS profession_nature,
               CASE WHEN prof_an_net IS NOT NULL AND prof_an_code THEN prof_an END AS profession_libelle_source,
               coalesce(civ_an, civ_sen) AS civilite,
               coalesce(deces_an, deces_sen) AS deces,
               nom_wikipedia AS nom_usage_wikipedia,
               CASE WHEN nom_an IS NOT NULL THEN 'an' WHEN nom_sen IS NOT NULL THEN 'senat'
                    WHEN nom_par_wikipedia THEN 'wikipedia' ELSE 'franceinfo' END AS source_nom,
               CASE WHEN prenom_an IS NOT NULL THEN 'an' WHEN prenom_sen IS NOT NULL THEN 'senat'
                    WHEN prenom_wikipedia IS NOT NULL THEN 'wikipedia' END AS source_prenom,
               source_naissance,
               CASE WHEN ville_naissance IS NOT NULL THEN 'an' END AS source_lieu_naissance,
               CASE WHEN prof_an_net IS NOT NULL THEN 'an' WHEN prof_sen IS NOT NULL THEN 'senat' END AS source_profession,
               CASE WHEN naissance IS NOT NULL THEN NULL
                    WHEN naissance_aberrante THEN 'date de naissance aberrante à la source : non retenue'
                    ELSE 'non connue de nos sources' END AS raison_naissance,
               CASE WHEN ville_naissance IS NULL THEN 'non connu de nos sources' END AS raison_lieu_naissance,
               CASE WHEN coalesce(prof_an_net, prof_sen) IS NULL THEN 'non connue de nos sources' END AS raison_profession,
               CASE WHEN naiss_an IS NULL OR naissance_wikidata IS NULL THEN 'une_source'
                    WHEN naiss_an = naissance_wikidata THEN 'concordante' ELSE 'divergente' END AS naissance_concordance,
               CASE WHEN an_ok THEN '{URL_DEPUTE}' || acteur
                    ELSE coalesce(article_url, element_url, liste_url) END AS source_url,
               article_url AS source_url_wikipedia, element_url AS source_url_wikidata,
               acteur, matricule_senat, an_ok AS acteur_present_an, sen_ok AS matricule_present_senat
        FROM k2 ORDER BY per""")

    # Adresse : homonymes parmi les candidats et parmi les acteurs de l'Assemblée (pas lui-même).
    ctx.x(f"""CREATE OR REPLACE TEMP TABLE _adr AS
        WITH c AS (
            SELECT p.per, c.personne_source, c.acteur, {slug('c.nom')} AS base,
                   left(i.naissance, 4) AS annee
            FROM candidature c JOIN _ident_per p USING (personne_source)
            JOIN personne_identite i ON i.per = p.per),
        homon AS (
            SELECT c.per,
                   (SELECT count(DISTINCT c2.per) FROM c c2 WHERE c2.base = c.base AND c2.per <> c.per)
                 + (SELECT count(*) FROM {an} a WHERE {slug("coalesce(a.prenom, '') || ' ' || coalesce(a.nom, '')")} = c.base
                     AND a.uid IS DISTINCT FROM c.acteur) AS n_homonymes
            FROM c)
        SELECT c.*, h.n_homonymes,
               CASE WHEN c.base = '' THEN NULL
                    WHEN h.n_homonymes = 0 THEN c.base
                    WHEN c.annee IS NOT NULL THEN c.base || '-' || c.annee END AS adresse_proposee
        FROM c JOIN homon h USING (per)""")
    ctx.ecrire("candidat", """
        WITH a AS (
            SELECT *, count(*) OVER (PARTITION BY adresse_proposee) AS n_meme FROM _adr),
        b AS (
            SELECT per, personne_source, n_homonymes,
                   CASE WHEN n_meme = 1 THEN adresse_proposee END AS adresse,
                   CASE WHEN base = '' THEN 'nom vide'
                        WHEN adresse_proposee IS NULL THEN 'homonyme sans année de naissance connue : décision nécessaire'
                        WHEN n_meme > 1 THEN 'homonymes nés la même année : décision nécessaire' END AS raison_adresse
            FROM a)
        SELECT b.per, c.nom, c.statut, c.date_declaration, c.article_frwiki, c.element_wikidata,
               c.acteur, c.matricule_senat, b.adresse,
               c.statut = 'declaree' AND b.adresse IS NOT NULL AS publie,
               c.rattachement,
               c.raison_rattachement, b.raison_adresse,
               CASE WHEN c.statut = 'retiree' THEN 'candidature retirée : données gardées, fiche non affichée'
                    WHEN c.statut = 'non_listee' THEN 'n''est plus dans la liste des candidats déclarés : données gardées, fiche non affichée'
                    WHEN b.adresse IS NULL THEN 'adresse non établie' END AS raison_non_publie,
               b.n_homonymes, c.statut_source, c.date_declaration_texte, c.date_declaration_raison,
               c.date_declaration_phrase, c.sycomore, c.acteur_connu_an, c.matricule_connu_senat,
               c."references", c.revision_wikipedia, c.date_declaration_source_url, c.statut_wikipedia,
               c.nom_liste, c.nom_wikipedia, c.parti, c.origine_element, c.rattachement_par_nom,
               c.source_liste, c.source_titre, c.date_liste, c.decision,
               c.eurodepute, c.eurodepute_connu_pe,
               c.source_url, c.article_url, c.element_url, c.personne_source
        FROM candidature c JOIN b USING (personne_source)
        ORDER BY c.statut, c.nom""")

    n = ctx.un("SELECT count(*) FROM candidat")
    publie = ctx.un("SELECT count(*) FROM candidat WHERE publie")
    an_ = ctx.un("SELECT count(*) FROM candidat WHERE acteur_connu_an")
    sen_ = ctx.un("SELECT count(*) FROM candidat WHERE matricule_senat IS NOT NULL")
    sans = ctx.un("SELECT count(*) FROM candidat WHERE NOT coalesce(acteur_connu_an, false) AND matricule_senat IS NULL")
    adr = ctx.un("SELECT count(*) FROM candidat WHERE adresse IS NOT NULL")
    naiss = ctx.un("SELECT count(*) FROM personne_identite WHERE naissance IS NOT NULL")
    ctx.x("DROP TABLE IF EXISTS _adr")
    ctx.x("DROP TABLE IF EXISTS _ident_per")
    ctx.con.unregister("_ident_corr")
    return {"candidats_publies": (publie, n),
            "rattache_assemblee": (an_, n),
            "rattache_senat": (sen_, n),
            "sans_identifiant_parlementaire": (sans, n),
            "adresse_etablie": (adr, n),
            "naissance_connue": (naiss, n)}
