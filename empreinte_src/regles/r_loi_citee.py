"""R-LOI-CITEE : les lois que le **titre** d'un acte du Journal officiel cite par leur numéro
(« … de l'article 43 de la loi n° 2021-1754 du 23 décembre 2021 … »), cahier 4.4.

Ce que la règle ne fait pas, et pourquoi :
- elle ne dit jamais qu'un acte « applique » une loi : la qualification « APPLICATION » du JO
  n'est plus posée depuis 2024 (cahier 3.6), et la part des actes qui appliquent une loi n'est
  jamais publiée (cahier 2.1) ;
- un titre qui ne cite pas de numéro de loi ne prouve pas que l'acte est « sans loi » : un arrêté
  « relatif à l'application … de la loi de finances pour 2026 » cite une loi sans son numéro, et
  ses liens JO la désignent (`JORFTEXT000055053477`). La règle dit seulement ce que le titre
  dit ; l'interface écrit « le titre ne le dit pas », jamais « sans loi » ;
- le titre d'une loi porte son propre numéro : il n'est pas une citation.

La loi citée est identifiée, quand c'est possible, par un lien du JO de l'acte vers ce numéro
(`lien_acte_loi`, sens `source`), sinon par l'acte « loi » de ce numéro lu dans les livraisons ;
sinon elle reste un numéro, sans adresse (« loi non identifiée »)."""

NOM = "R-LOI-CITEE"
VERSION = 1
DEPEND = ()
SORTIES = ("acte_loi_citee",)
DESCRIPTION = ("Une loi est « citée dans le titre » d'un acte du Journal officiel quand le titre de "
               "l'acte la désigne par son numéro (« loi n° 2023-270 », « loi organique n° … »). "
               "Le titre d'une loi ne se cite pas lui-même. Un titre qui ne cite aucun numéro de loi "
               "ne veut pas dire que l'acte est sans rapport avec une loi : le titre ne le dit pas, "
               "c'est tout. Le site ne calcule jamais la part des actes qui « appliquent » une loi.")

NATURES_LOI = "('LOI', 'LOI_ORGANIQUE', 'LOI_CONSTIT', 'LOI_PROGRAMME')"

# Titre ramené à une forme simple : espaces insécables -> espace, apostrophe typographique -> '.
TITRE = r"""lower(regexp_replace(replace(coalesce(titre_complet, titre), chr(8217), ''''),
                                  '[\x{00A0}\x{202F}\x{2009}]', ' ', 'g'))"""
# « loi n° 2023-270 », « lois n° … », « loi organique n° 2009-403 », « loi constitutionnelle n°
# 2008-724 », « loi no 86-33 », « loi n°2006-1640 ». Le numéro : année (2 ou 4 chiffres) - rang.
MOTIF = (r"\blois?\s+(?:organiques?\s+|constitutionnelles?\s+|de programmation\s+)?"
         r"n(?:°|º|o\.?)\s*\d{2,4}-\d+")


def appliquer(ctx):
    """Applique R-LOI-CITEE : écrit `acte_loi_citee`, les lois que le titre d'un acte du Journal
    officiel cite par leur numéro (voir la description du module). Rend la couverture,
    `{nom: (numérateur, dénominateur)}` : `titre_lu`, `loi_citee_identifiee`."""
    ctx.ecrire("acte_loi_citee", f"""
        WITH t AS (
            SELECT uid AS acte, id_jorf, nature, numero, prov_url,
                   regexp_extract_all({TITRE}, '{MOTIF}') AS cites
            FROM jo_actes__acte_reglementaire),
        c AS (
            SELECT acte, id_jorf, nature, numero, prov_url,
                   unnest(cites) AS libelle_cite, generate_subscripts(cites, 1) AS rang
            FROM t),
        n AS (
            SELECT *, regexp_extract(libelle_cite, '(\\d{{2,4}}-\\d+)$', 1) AS numero_loi,
                   CASE WHEN libelle_cite LIKE '%organique%' THEN 'loi organique'
                        WHEN libelle_cite LIKE '%constitutionnelle%' THEN 'loi constitutionnelle'
                        WHEN libelle_cite LIKE '%de programmation%' THEN 'loi de programmation'
                        ELSE 'loi' END AS type_loi
            FROM c),
        -- une loi citée deux fois dans le même titre compte une fois ; le titre d'une loi
        -- porte son propre numéro, qui n'est pas une citation
        u AS (
            SELECT * FROM n
            WHERE NOT (nature IN {NATURES_LOI} AND numero_loi = numero)
            QUALIFY row_number() OVER (PARTITION BY acte, numero_loi ORDER BY rang) = 1),
        par_lien AS (
            SELECT acte, cible_numero AS numero_loi, min(cible_texte) AS loi
            FROM jo_actes__lien_acte_loi
            WHERE sens = 'source' AND nature_cible IN {NATURES_LOI} AND cible_texte IS NOT NULL
            GROUP BY 1, 2),
        par_acte AS (
            SELECT numero AS numero_loi, min(id_jorf) AS loi
            FROM jo_actes__acte_reglementaire
            WHERE nature IN {NATURES_LOI} AND numero IS NOT NULL
              AND NOT coalesce(titre_complet, titre) ILIKE '%(rectificatif)%'
            GROUP BY 1)
        SELECT u.acte, u.numero_loi,
               row_number() OVER (PARTITION BY u.acte ORDER BY u.rang) AS rang,
               u.type_loi, u.libelle_cite,
               coalesce(pl.loi, pa.loi) AS loi_jorf,
               CASE WHEN pl.loi IS NOT NULL THEN 'lien_jo'
                    WHEN pa.loi IS NOT NULL THEN 'acte_lu' END AS loi_identifiee_par,
               'https://www.legifrance.gouv.fr/jorf/id/' || coalesce(pl.loi, pa.loi) AS loi_source_url,
               u.id_jorf, u.prov_url AS source_url
        FROM u
        LEFT JOIN par_lien pl ON pl.acte = u.acte AND pl.numero_loi = u.numero_loi
        LEFT JOIN par_acte pa ON pa.numero_loi = u.numero_loi
        ORDER BY u.acte, rang""")
    actes = ctx.un("SELECT count(*) FROM jo_actes__acte_reglementaire")
    titres = ctx.un("SELECT count(*) FROM jo_actes__acte_reglementaire "
                    "WHERE coalesce(titre_complet, titre) IS NOT NULL")
    cit = ctx.un("SELECT count(*) FROM acte_loi_citee")
    ident = ctx.un("SELECT count(*) FROM acte_loi_citee WHERE loi_jorf IS NOT NULL")
    return {"titre_lu": (titres, actes), "loi_citee_identifiee": (ident, cit)}
