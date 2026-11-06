"""R-DEPOT-GOUVERNEMENT : les projets de loi et le gouvernement qui les a déposés (doc. 1, 1.6 ;
cahier 3.1.4 et 4.4, « ce qu'il a fait déposer »).

Un projet de loi est un dossier dont le texte du **premier dépôt** (acte `DepotInitiative_Type`,
dans l'une ou l'autre chambre) a le préfixe `PRJL` ; le titre du dossier ne compte pas (« CETA »,
« Bioéthique »). Il est rattaché au gouvernement en fonction à la date de ce dépôt
(R-GOUVERNEMENTS). Un projet est déposé au nom du gouvernement : il n'est jamais un acte
personnel du ministre qui le présente (aucune personne dans cette table).

Le ministère porteur (auteur du document de dépôt, via les fonctions gouvernementales) relève
d'une tranche suivante ; il n'est pas servi ici."""

from .r_lois import gouvernement_a

NOM = "R-DEPOT-GOUVERNEMENT"
VERSION = 1
DEPEND = ("R-GOUVERNEMENTS",)
SORTIES = ("projet_gouvernement",)
DESCRIPTION = (
    "Un projet de loi est reconnu à la nature du texte déposé au début du dossier (identifiant "
    "commençant par PRJL), jamais à son titre. Il est rattaché au gouvernement en fonction le jour "
    "de son premier dépôt, à l'Assemblée ou au Sénat. Un projet de loi est déposé au nom du "
    "gouvernement : il n'est jamais présenté comme l'acte personnel d'un ministre.")


def appliquer(ctx):
    ctx.ecrire("projet_gouvernement", f"""
        WITH p AS (
            SELECT a.dossier, a.texte_associe AS document, a.uid AS acte,
                   coalesce(left(a.date, 10), left(doc.date_depot, 10)) AS date_depot,
                   CASE WHEN a.code LIKE 'AN%' THEN 'AN' WHEN a.code LIKE 'SN%' THEN 'SN' END AS chambre_depot,
                   TRY_CAST(regexp_extract(a.uid, '^L(\\d+)-', 1) AS INTEGER) AS legislature_depot,
                   d.procedure_code, d.procedure_libelle, d.titre AS titre_dossier,
                   coalesce(doc.prov_url, d.prov_url) AS source_url
            FROM an_dossiers__acte a
            JOIN an_dossiers__dossier d ON d.uid = a.dossier
            LEFT JOIN an_dossiers__document doc ON doc.uid = a.texte_associe
            WHERE a.type_acte = 'DepotInitiative_Type' AND a.texte_associe LIKE 'PRJL%')
        SELECT dossier, document, date_depot, {gouvernement_a('p.date_depot')} AS gouvernement,
               CASE WHEN date_depot IS NULL THEN 'date_de_depot_absente'
                    WHEN {gouvernement_a('p.date_depot')} IS NULL THEN 'aucun_gouvernement_a_la_date'
               END AS raison,
               acte, chambre_depot, legislature_depot, procedure_code, procedure_libelle,
               titre_dossier, source_url
        FROM p""")
    n = ctx.un("SELECT count(*) FROM projet_gouvernement")
    gouv = ctx.un("SELECT count(*) FROM projet_gouvernement WHERE gouvernement IS NOT NULL")
    return {"gouvernement_etabli": (gouv, n)}
