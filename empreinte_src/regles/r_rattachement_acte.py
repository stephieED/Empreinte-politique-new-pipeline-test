"""R-RATTACHEMENT-ACTE : chaque acte du Journal officiel est rattaché à un gouvernement par sa
**date de publication**, à un ministère par le **ministère de l'acte** ; jamais à une personne
(cahier 4.6, même si le bloc des signataires est rempli : doc. 5, Q11). La règle dit aussi si
l'acte est une **mesure nominative** (rubrique du sommaire du JO, registre : R-MESURE-NOMINATIVE)
et si son titre cite une loi (R-LOI-CITEE), et elle établit la **période couverte** par les
livraisons reçues.

Pièges traités (cahier 3.6 ; mesures `autres-sources.md`, § 1) :
- **date de publication, jamais de livraison** : un acte ancien redélivré garde sa date ; il est
  rattaché au gouvernement de cette date, mais il est hors de la période couverte (`dans_periode_
  couverte`) : les livraisons ne contiennent pas tout ce qui a paru à cette date ;
- **date sentinelle `2999`** : lue comme absente par le lecteur, elle ne rattache jamais rien
  (« date de publication absente ») ;
- **texte redélivré** : la dernière livraison fait foi (état courant de la table lue) ;
- **loi en double** (original et rectificatif, deux `JORFTEXT`) : le second enregistrement est
  marqué `est_rectificatif` (titre terminé par « (rectificatif) ») et relié à l'original quand
  celui-ci est lu (même nature, même numéro) ; il garde sa propre date de publication ;
- **libellé de ministère libre** (260 libellés depuis 2007) : le ministère normalisé vient d'une
  décision `libelle_ministere` ; sans elle, « non établi » ; sans libellé (lois, autorités
  indépendantes, informations parlementaires), « ministère non précisé » ;
- **jour de changement de gouvernement** : deux gouvernements AN peuvent partager un jour
  (Fillon 1 et Fillon 2, le 18/06/2007) : l'acte va au gouvernement qui commence ce jour-là ;
  un jour sans gouvernement publié (11 au 15/05/2012) donne « non établi ».

Période couverte : un numéro du JO est **complet** quand chaque texte de son sommaire est lu.
Seuls comptent les numéros **livrés dans leur actualité** (au plus `ACTUALITE_JOURS` jours après
leur date de publication) ou par l'**archive globale** de la DILA (`jo-global`, état complet du JO
à sa date, découpé depuis la XIVe : décision du 13/11/2026) : un numéro ancien redélivré par une
livraison quotidienne (un numéro de 1950, complet par hasard) ne fait pas remonter la période. Elle va du premier au dernier de ces numéros qui soit complet ; les
numéros incomplets et les numéros manquants entre eux sont **nommés comme des trous**, sans
réduire la période. Jusqu'au
10/11/2026, la période s'arrêtait à la dernière suite continue de numéros complets : un seul
numéro incomplet (vers le 09/11) l'a ramenée à deux jours, et les actes d'octobre du
gouvernement Lecornu II ont disparu de sa fiche."""

ACTUALITE_JOURS = 7
# Point d'accès de l'archive globale : ses numéros comptent quelle que soit leur date de livraison.
POINT_ARCHIVE_GLOBALE = "jo-global"

NOM = "R-RATTACHEMENT-ACTE"
VERSION = 3
DEPEND = ("R-GOUVERNEMENTS", "R-LOI-CITEE")
SORTIES = ("acte_rattache", "couverture_jo", "couverture_jo_gouvernement")
DESCRIPTION = (
    "Un acte du Journal officiel est rattaché au gouvernement en fonction à sa date de publication "
    "(jamais à sa date de livraison), et au ministère indiqué par l'acte lui-même. Il n'est jamais "
    "rattaché à une personne, même quand le texte nomme ses signataires. Le libellé du ministère "
    "est un texte libre qui change avec les gouvernements : il est ramené à un ministère par une "
    "table de correspondance publiée ; un libellé absent de la table reste « non établi », un acte "
    "sans ministère est « ministère non précisé ». Un acte est une mesure nominative quand le "
    "sommaire du Journal officiel le range sous la rubrique « Mesures nominatives ». Les actes ne "
    "sont comptés que sur la période couverte par les livraisons reçues, dont les bornes sont "
    "publiées.")

URL_SOURCE = "https://echanges.dila.gouv.fr/OPENDATA/JORF/"

# Clé de rapprochement d'un libellé : casse, accents, apostrophes et espaces ignorés
# (« MINISTERE DE L'INTERIEUR » = « Ministère de l'intérieur »).
def _cle(x: str) -> str:
    return (f"lower(strip_accents(trim(regexp_replace(replace({x}, chr(8217), ''''), "
            f"'\\s+', ' ', 'g'))))")


def _decisions(ctx) -> str:
    """Table (cle, ministere_normalise, decision) : une ligne par libellé décidé. Deux décisions
    contradictoires pour un même libellé ne concluent pas."""
    if not ctx.existe("decision_libelle_ministere"):
        return ("SELECT NULL::VARCHAR AS cle, NULL::VARCHAR AS ministere_normalise, "
                "NULL::VARCHAR AS decision, NULL::BOOLEAN AS contradiction WHERE false")
    cols = {r[0] for r in ctx.x("SELECT column_name FROM (DESCRIBE decision_libelle_ministere)")}
    manque = {"libelle", "ministere_normalise"} - cols
    if manque:
        raise ValueError(f"décisions libelle_ministere sans {sorted(manque)}")
    return f"""SELECT {_cle('libelle')} AS cle,
                      CASE WHEN count(DISTINCT ministere_normalise) = 1
                           THEN any_value(ministere_normalise) END AS ministere_normalise,
                      string_agg(fichier, ' ; ' ORDER BY fichier) AS decision,
                      count(DISTINCT ministere_normalise) > 1 AS contradiction
               FROM decision_libelle_ministere
               WHERE libelle IS NOT NULL AND ministere_normalise IS NOT NULL
               GROUP BY 1"""


def appliquer(ctx):
    # -- 1. Période couverte par les livraisons -------------------------------------------------
    ctx.x(f"""CREATE OR REPLACE TEMP TABLE _numero_jo AS
        WITH s AS (
            SELECT s.conteneur, any_value(s.date_publication) AS date_publication,
                   any_value(s.num_jo) AS num_jo, any_value(s.titre_jo) AS titre_jo,
                   count(*) AS nb_textes, count(a.uid) AS nb_textes_lus,
                   min(strptime(substr(s.livraison, 1, 8), '%Y%m%d')::DATE) AS premiere_livraison,
                   bool_or(s.prov_point = '{POINT_ARCHIVE_GLOBALE}') AS archive_globale
            FROM jo_actes__sommaire_jo s
            LEFT JOIN jo_actes__acte_reglementaire a ON a.uid = s.acte
            WHERE s.date_publication IS NOT NULL
            GROUP BY 1)
        SELECT *, nb_textes_lus = nb_textes AS complet,
               archive_globale OR
               date_diff('day', TRY_CAST(date_publication AS DATE), premiere_livraison) <= {ACTUALITE_JOURS}
                   AS dans_son_actualite
        FROM s""")
    ctx.x("""CREATE OR REPLACE TEMP TABLE _periode AS
        SELECT min(date_publication) AS debut, max(date_publication) AS fin
        FROM _numero_jo WHERE complet AND dans_son_actualite""")
    ctx.ecrire("couverture_jo", f"""
        WITH p AS (SELECT * FROM _periode),
        n AS (SELECT j.*, TRY_CAST(num_jo AS INTEGER) AS num, substr(date_publication, 1, 4) AS an
              FROM _numero_jo j, p WHERE j.date_publication BETWEEN p.debut AND p.fin),
        -- numéros absents de la suite (la numérotation repart à 1 chaque année)
        bornes AS (SELECT an, min(num) AS a, max(num) AS b FROM n GROUP BY an),
        manquants AS (
            SELECT list(bornes.an || '/' || lpad(g.k::VARCHAR, 4, '0') ORDER BY bornes.an, g.k) AS l
            FROM bornes, LATERAL (SELECT unnest(range(bornes.a, bornes.b + 1)) AS k) g
            WHERE NOT EXISTS (SELECT 1 FROM n WHERE n.an = bornes.an AND n.num = g.k)),
        liv AS (
            SELECT DISTINCT livraison FROM (
                SELECT livraison FROM jo_actes__acte_reglementaire__hist
                UNION ALL SELECT livraison FROM jo_actes__sommaire_jo__hist
                UNION ALL SELECT livraison FROM jo_actes__version_acte__hist
                UNION ALL SELECT livraison FROM jo_actes__suppression_jo__hist)
            WHERE livraison IS NOT NULL),
        jours AS (SELECT DISTINCT strptime(substr(livraison, 1, 8), '%Y%m%d')::DATE AS j FROM liv),
        sans AS (
            SELECT list(strftime(g.j, '%Y-%m-%d') ORDER BY g.j) AS l
            FROM (SELECT unnest(range(min(j)::TIMESTAMP, max(j)::TIMESTAMP + INTERVAL 1 DAY,
                                       INTERVAL 1 DAY))::DATE AS j
                  FROM jours) g
            ANTI JOIN jours USING (j))
        SELECT p.debut AS premiere_publication, p.fin AS derniere_publication,
               (SELECT count(*) FROM n) AS nb_numeros,
               (SELECT count(*) FROM n WHERE NOT complet) AS nb_numeros_incomplets,
               (SELECT min(titre_jo) FILTER (WHERE date_publication = p.debut) FROM n) AS premier_numero,
               (SELECT min(titre_jo) FILTER (WHERE date_publication = p.fin) FROM n) AS dernier_numero,
               coalesce((SELECT l FROM manquants), []) AS numeros_manquants,
               (SELECT count(*) FROM jo_actes__acte_reglementaire a
                 WHERE a.date_publication BETWEEN p.debut AND p.fin) AS nb_actes,
               (SELECT min(livraison) FROM liv) AS premiere_livraison,
               (SELECT max(livraison) FROM liv) AS derniere_livraison,
               (SELECT count(*) FROM liv) AS nb_livraisons,
               coalesce((SELECT l FROM sans), []) AS jours_sans_livraison,
               '{URL_SOURCE}' AS source_url
        FROM p""")

    # -- 2. Rattachement de chaque acte ---------------------------------------------------------
    ctx.ecrire("acte_rattache", f"""
        WITH a AS (SELECT * FROM jo_actes__acte_reglementaire),
        g AS (
            SELECT a.uid, g.organe
            FROM a JOIN gouvernement g
              ON a.date_publication BETWEEN g.debut AND coalesce(g.fin, '9999-12-31')
            -- jour partagé par deux gouvernements : celui qui commence ce jour-là
            QUALIFY row_number() OVER (PARTITION BY a.uid ORDER BY g.debut DESC) = 1),
        premier_gouv AS (SELECT min(debut) AS d FROM gouvernement),
        s AS (
            SELECT acte, min(conteneur) AS conteneur, min(num_jo) AS num_jo,
                   min(array_to_string(rubrique, ' > ')) AS rubrique,
                   bool_or(list_contains(list_transform(rubrique, lambda r: lower(trim(r))),
                                         'mesures nominatives')) AS nominative
            FROM jo_actes__sommaire_jo GROUP BY 1),
        d AS ({_decisions(ctx)}),
        l AS (SELECT acte, count(*) AS nb FROM acte_loi_citee GROUP BY 1),
        orig AS (
            SELECT nature, numero, id_jorf, date_publication FROM a
            WHERE numero IS NOT NULL AND NOT coalesce(titre_complet, titre) ILIKE '%(rectificatif)%'),
        p AS (SELECT * FROM _periode)
        SELECT a.uid AS acte, a.id_jorf, a.date_publication,
               g.organe AS gouvernement,
               CASE WHEN g.organe IS NOT NULL THEN 'etabli' ELSE 'non_etabli' END AS gouvernement_statut,
               CASE WHEN g.organe IS NOT NULL THEN NULL
                    WHEN a.date_publication IS NULL AND a.date_publication_sentinelle
                         THEN 'date de publication sentinelle (2999)'
                    WHEN a.date_publication IS NULL THEN 'date de publication absente'
                    WHEN a.date_publication < (SELECT d FROM premier_gouv)
                         THEN 'publié avant le premier gouvernement suivi'
                    ELSE 'aucun gouvernement publié à cette date' END AS gouvernement_raison,
               a.nature, a.numero, a.nor, coalesce(a.titre_complet, a.titre) AS titre,
               a.ministere AS ministere_libelle,
               d.ministere_normalise,
               CASE WHEN a.ministere IS NULL THEN 'non_precise'
                    WHEN d.ministere_normalise IS NOT NULL THEN 'etabli'
                    ELSE 'non_etabli' END AS ministere_statut,
               CASE WHEN a.ministere IS NULL THEN 'ministère non précisé par l''acte'
                    WHEN d.contradiction THEN 'décisions contradictoires pour ce libellé'
                    WHEN d.ministere_normalise IS NULL THEN 'libellé sans décision de correspondance'
                    END AS ministere_raison,
               d.decision AS ministere_decision,
               s.nominative AS mesure_nominative,
               CASE WHEN s.acte IS NULL THEN 'acte absent des sommaires du JO reçus' END
                    AS mesure_nominative_raison,
               s.rubrique, s.conteneur AS sommaire_jo, s.num_jo,
               CASE WHEN coalesce(a.titre_complet, a.titre) IS NULL THEN NULL
                    ELSE coalesce(l.nb, 0) > 0 END AS cite_une_loi,
               CASE WHEN coalesce(a.titre_complet, a.titre) IS NOT NULL THEN coalesce(l.nb, 0) END
                    AS nb_lois_citees,
               coalesce(a.titre_complet, a.titre) ILIKE '%(rectificatif)%' AS est_rectificatif,
               CASE WHEN coalesce(a.titre_complet, a.titre) ILIKE '%(rectificatif)%' THEN
                   (SELECT 'jorf:' || min(o.id_jorf) FROM orig o
                    WHERE o.nature = a.nature AND o.numero = a.numero
                      AND o.date_publication <= a.date_publication) END AS rectificatif_de,
               coalesce(a.date_publication BETWEEN p.debut AND p.fin, false) AS dans_periode_couverte,
               a.livraison, a.prov_url AS source_url
        FROM a
        CROSS JOIN p
        LEFT JOIN g ON g.uid = a.uid
        LEFT JOIN s ON s.acte = a.uid
        LEFT JOIN d ON d.cle = {_cle('a.ministere')}
        LEFT JOIN l ON l.acte = a.uid
        ORDER BY a.date_publication, a.uid""")

    # -- 3. Couverture par gouvernement ---------------------------------------------------------
    ctx.ecrire("couverture_jo_gouvernement", """
        WITH p AS (SELECT * FROM _periode),
        c AS (
            SELECT g.organe AS gouvernement, g.debut AS gouvernement_debut, g.fin AS gouvernement_fin,
                   CASE WHEN p.debut IS NOT NULL THEN greatest(g.debut, p.debut) END AS du,
                   CASE WHEN p.fin IS NOT NULL THEN least(coalesce(g.fin, p.fin), p.fin) END AS au
            FROM gouvernement g CROSS JOIN p)
        SELECT gouvernement, gouvernement_debut, gouvernement_fin,
               CASE WHEN du <= au THEN du END AS couvert_du,
               CASE WHEN du <= au THEN au END AS couvert_au,
               CASE WHEN du IS NULL OR du > au THEN 'non_collecte'
                    WHEN du = gouvernement_debut AND (au = gouvernement_fin OR gouvernement_fin IS NULL)
                         THEN 'complet'
                    ELSE 'partiel' END AS statut,
               (SELECT count(*) FROM acte_rattache r
                 WHERE r.gouvernement = c.gouvernement AND r.dans_periode_couverte) AS nb_actes_couverts,
               (SELECT count(*) FROM acte_rattache r
                 WHERE r.gouvernement = c.gouvernement AND NOT r.dans_periode_couverte)
                    AS nb_actes_hors_periode
        FROM c ORDER BY gouvernement_debut""")

    ctx.x("DROP TABLE _numero_jo")
    ctx.x("DROP TABLE _periode")
    n = ctx.un("SELECT count(*) FROM acte_rattache")
    gouv = ctx.un("SELECT count(*) FROM acte_rattache WHERE gouvernement IS NOT NULL")
    libelle = ctx.un("SELECT count(*) FROM acte_rattache WHERE ministere_libelle IS NOT NULL")
    minis = ctx.un("SELECT count(*) FROM acte_rattache WHERE ministere_normalise IS NOT NULL")
    nomin = ctx.un("SELECT count(*) FROM acte_rattache WHERE mesure_nominative IS NOT NULL")
    couv = ctx.un("SELECT count(*) FROM acte_rattache WHERE dans_periode_couverte")
    return {"gouvernement_etabli": (gouv, n), "ministere_precise": (libelle, n),
            "ministere_etabli": (minis, libelle), "mesure_nominative_etablie": (nomin, n),
            "dans_periode_couverte": (couv, n)}
