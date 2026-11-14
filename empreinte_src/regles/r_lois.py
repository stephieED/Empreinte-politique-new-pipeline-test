"""R-LOIS : les lois promulguées, lues dans les actes de promulgation des dossiers (cahier 3.1.4 ;
mesures `an-scrutins-dossiers.md`, 4.3).

Une loi = un acte `Promulgation_Type` : numéro de loi (`codeLoi`, le lien sûr avec le Journal
officiel, le NOR manquant sur toute la XIVe), date de promulgation (date de l'acte, celle du
titre « loi n° … du … »), NOR, publication au JO et adresse Légifrance. Elle est rattachée :
- à la législature dont la période contient la date de promulgation (aucune si la date tombe
  entre deux législatures : raison `entre_deux_legislatures`) ;
- au gouvernement en fonction à cette date (R-GOUVERNEMENTS).

Une loi promulguée sous la législature suivante n'est dans aucune archive de dossiers (71 des
1 085 lois depuis 2012, cahier 3.1.4) : elle manque ici, et R-LOI-DOSSIER (tranche suivante)
la rattachera."""

NOM = "R-LOIS"
VERSION = 2
DEPEND = ("R-LEGISLATURES", "R-GOUVERNEMENTS")
SORTIES = ("loi",)
DESCRIPTION = (
    "Une loi est repérée par l'acte de promulgation de son dossier législatif : son numéro (le lien "
    "sûr avec le Journal officiel), sa date de promulgation, sa référence NOR et son adresse sur "
    "Légifrance. Elle est comptée dans la législature en cours à sa date de promulgation, et "
    "rattachée au gouvernement en fonction ce jour-là.")


def gouvernement_a(date_sql: str) -> str:
    """Gouvernement en fonction à une date (texte ISO) : début <= date <= fin (ou en cours) ;
    si deux périodes se touchent, le plus récent."""
    return (f"(SELECT g.organe FROM gouvernement g WHERE g.debut <= {date_sql} "
            f"AND coalesce(g.fin, '9999-12-31') >= {date_sql} ORDER BY g.debut DESC LIMIT 1)")


def legislature_a(date_sql: str) -> str:
    """Rend une sous-requête SQL qui donne le numéro de la législature en cours à la date
    `date_sql` (une expression SQL) : celle qui a commencé le plus récemment parmi celles qui la
    couvrent, une fin vide valant « en cours »."""
    return (f"(SELECT l.numero FROM legislature l WHERE l.debut <= {date_sql} "
            f"AND coalesce(l.fin, '9999-12-31') >= {date_sql} ORDER BY l.debut DESC LIMIT 1)")


def appliquer(ctx):
    """Applique R-LOIS : écrit `loi`, les lois promulguées lues dans les actes de promulgation des
    dossiers, avec leur gouvernement et leur législature (voir la description du module). Rend la
    couverture, `{nom: (numérateur, dénominateur)}` : `numero_de_loi_lu`, `gouvernement_etabli`,
    `legislature_etablie`."""
    # Date de promulgation : celle du Journal officiel (date de signature de la loi) quand il la
    # connaît, sinon celle de l'acte de promulgation de l'Assemblée. Sept lois ont une date
    # fausse à l'Assemblée (acte ou JO cité), par exemple 2021-191 : acte daté du 0021-02-24, loi du
    # 22/02/2021 au JO (version 2, 14/11/2026). Les désaccords sont gardés et nommés (A7).
    jo = ("""SELECT numero, min(date_signature) AS d FROM jo_actes__acte_reglementaire
             WHERE nature IN ('LOI', 'LOI_ORGANIQUE', 'LOI_CONSTIT') AND numero IS NOT NULL
               AND date_signature IS NOT NULL GROUP BY 1"""
          if ctx.existe("jo_actes__acte_reglementaire")
          else "SELECT NULL::VARCHAR AS numero, NULL::VARCHAR AS d WHERE false")
    ctx.ecrire("loi", f"""
        WITH jo AS ({jo}),
        p0 AS (
            SELECT code_loi AS numero_loi, dossier, uid AS acte, left(date, 10) AS date_assemblee,
                   titre_loi, reference_nor AS nor, left(date_jo, 10) AS date_jo, num_jo,
                   url_legifrance, texte_loi, prov_url
            FROM an_dossiers__acte WHERE type_acte = 'Promulgation_Type'),
        p AS (
            SELECT p0.*, coalesce(jo.d, p0.date_assemblee) AS date_promulgation,
                   CASE WHEN jo.d IS NOT NULL THEN 'journal_officiel'
                        WHEN p0.date_assemblee IS NOT NULL THEN 'assemblee' END AS source_date_promulgation
            FROM p0 LEFT JOIN jo ON jo.numero = p0.numero_loi)
        SELECT numero_loi, dossier, date_promulgation, source_date_promulgation, date_assemblee,
               {legislature_a('p.date_promulgation')} AS legislature,
               {gouvernement_a('p.date_promulgation')} AS gouvernement,
               CASE WHEN date_promulgation IS NULL THEN 'date_absente'
                    WHEN {legislature_a('p.date_promulgation')} IS NULL THEN 'entre_deux_legislatures'
               END AS raison_legislature,
               CASE WHEN date_promulgation IS NULL THEN 'date_absente'
                    WHEN {gouvernement_a('p.date_promulgation')} IS NULL THEN 'aucun_gouvernement_a_la_date'
               END AS raison_gouvernement,
               acte, titre_loi, nor, date_jo, num_jo, texte_loi, prov_url AS source_url
        FROM p""")
    n = ctx.un("SELECT count(*) FROM loi")
    numero = ctx.un("SELECT count(*) FROM loi WHERE numero_loi IS NOT NULL")
    gouv = ctx.un("SELECT count(*) FROM loi WHERE gouvernement IS NOT NULL")
    leg = ctx.un("SELECT count(*) FROM loi WHERE legislature IS NOT NULL")
    par_jo = ctx.un("SELECT count(*) FROM loi WHERE source_date_promulgation = 'journal_officiel'")
    return {"numero_de_loi_lu": (numero, n), "gouvernement_etabli": (gouv, n),
            "legislature_etablie": (leg, n), "date_de_promulgation_lue_au_jo": (par_jo, n)}
