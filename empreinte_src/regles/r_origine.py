"""R-ORIGINE : projet (gouvernement) ou proposition (parlement), et `scrutin_classe` (doc. 1, 1.5.3
et 1.6 ; cahier 4.6, « origine d'un texte voté »).

Deux lectures, recoupées :
- l'**intitulé officiel** du scrutin, qui nomme la catégorie juridique : la première mention de
  « projet de loi », « proposition de loi » ou « proposition de résolution » ;
- le **document de dépôt** du dossier relié (R-LIEN-SCRUTIN-DOSSIER, un seul dossier) : préfixe
  `PRJL` (projet), `PION` (proposition de loi), `PNRE` (proposition de résolution) du texte
  cité par l'acte de dépôt initial (cahier 3.1.4).

L'intitulé fait foi ; si le document le contredit, l'origine est « non établie » (raison
`desaccord_intitule_document`). Sans catégorie dans l'intitulé, le document décide. Pour une
proposition de résolution, l'origine est celle du document, et sa nature (`PNRE`) est servie
dans `type_texte` (décision provisoire, doc. 5, Q20). Une motion de censure ou une déclaration du
gouvernement ne porte pas sur un texte voté : origine « non établie », raison `pas_un_texte`.

`scrutin_classe` réunit la nature (R-NATURE-SCRUTIN, colonne `regle_nature`) et l'origine."""

NOM = "R-ORIGINE"
VERSION = 1
DEPEND = ("R-NATURE-SCRUTIN", "R-LIEN-SCRUTIN-DOSSIER")
SORTIES = ("scrutin_classe",)
DESCRIPTION = (
    "L'origine d'un texte voté — projet de loi du gouvernement ou proposition d'un parlementaire — "
    "est lue dans l'intitulé officiel du scrutin, qui nomme la catégorie du texte. Elle est "
    "recoupée par la nature du document déposé au début du dossier (projet de loi, proposition de "
    "loi, proposition de résolution). Si les deux se contredisent, l'origine n'est pas établie. Une "
    "motion de censure ou une déclaration du gouvernement ne porte pas sur un texte : elle n'a pas "
    "d'origine.")

CATEGORIE = r"(projet de loi|proposition de loi|proposition de resolution)"


def appliquer(ctx):
    ctx.ecrire("scrutin_classe", f"""
        WITH depot AS (
            SELECT dossier, any_value(substr(texte_associe, 1, 4)) AS type_texte
            FROM an_dossiers__acte WHERE type_acte = 'DepotInitiative_Type'
              AND texte_associe IS NOT NULL GROUP BY 1),
        lien1 AS (SELECT scrutin, dossier FROM lien_scrutin_dossier WHERE nb_dossiers = 1),
        x AS (
            SELECT s.*, l.dossier, d.type_texte,
                   regexp_extract(s.titre_normalise, '{CATEGORIE}', 1) AS cat,
                   CASE d.type_texte WHEN 'PRJL' THEN 'projet' WHEN 'PION' THEN 'proposition'
                                     WHEN 'PNRE' THEN 'proposition' END AS origine_document
            FROM scrutin_nature s LEFT JOIN lien1 l USING (scrutin)
            LEFT JOIN depot d USING (dossier)),
        y AS (
            SELECT *, CASE WHEN cat = 'projet de loi' THEN 'projet'
                           WHEN cat IN ('proposition de loi', 'proposition de resolution')
                                THEN 'proposition' END AS origine_intitule
            FROM x)
        SELECT scrutin, legislature, numero, date, type_code, nature, origine, lecture, sort,
               solennel, motion_censure, detail AS detail_nature, raison AS raison_nature,
               raison_origine, origine_intitule, origine_document, type_texte,
               nullif(cat, '') AS categorie_intitule, dossier AS dossier_document,
               seance, titre, source_url, regle_nature
        FROM (
            SELECT *, regle AS regle_nature,
                   CASE WHEN nature IN ('motion_censure', 'declaration') THEN 'non_etablie'
                        WHEN origine_intitule IS NOT NULL AND origine_document IS NOT NULL
                             AND origine_intitule <> origine_document THEN 'non_etablie'
                        ELSE coalesce(origine_intitule, origine_document, 'non_etablie') END AS origine,
                   CASE WHEN nature IN ('motion_censure', 'declaration') THEN 'pas_un_texte'
                        WHEN origine_intitule IS NOT NULL AND origine_document IS NOT NULL
                             AND origine_intitule <> origine_document THEN 'desaccord_intitule_document'
                        WHEN origine_intitule IS NULL AND origine_document IS NULL
                             THEN 'ni_intitule_ni_document' END AS raison_origine
            FROM y)""")
    n = ctx.un("SELECT count(*) FROM scrutin_classe WHERE nature NOT IN ('motion_censure', 'declaration')")
    ok = ctx.un("""SELECT count(*) FROM scrutin_classe WHERE origine <> 'non_etablie'""")
    ens = ctx.un("SELECT count(*) FROM scrutin_classe WHERE nature = 'ensemble'")
    ens_ok = ctx.un("SELECT count(*) FROM scrutin_classe WHERE nature = 'ensemble' AND origine <> 'non_etablie'")
    recoupe = ctx.un("""SELECT count(*) FROM scrutin_classe
                        WHERE origine_intitule IS NOT NULL AND origine_intitule = origine_document""")
    return {"origine_etablie": (ok, n), "origine_etablie_ensemble": (ens_ok, ens),
            "origine_recoupee_par_le_document": (recoupe, ok)}
