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
VERSION = 1
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
    return (f"(SELECT l.numero FROM legislature l WHERE l.debut <= {date_sql} "
            f"AND coalesce(l.fin, '9999-12-31') >= {date_sql} ORDER BY l.debut DESC LIMIT 1)")


def appliquer(ctx):
    ctx.ecrire("loi", f"""
        WITH p AS (
            SELECT code_loi AS numero_loi, dossier, uid AS acte, left(date, 10) AS date_promulgation,
                   titre_loi, reference_nor AS nor, left(date_jo, 10) AS date_jo, num_jo,
                   url_legifrance, texte_loi, prov_url
            FROM an_dossiers__acte WHERE type_acte = 'Promulgation_Type')
        SELECT numero_loi, dossier, date_promulgation,
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
    return {"numero_de_loi_lu": (numero, n), "gouvernement_etabli": (gouv, n),
            "legislature_etablie": (leg, n)}
