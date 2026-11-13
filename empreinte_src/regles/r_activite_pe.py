"""R-ACTIVITE-PE : l'activité d'un candidat au Parlement européen, hors votes (décision Q37 du
13/11/2026 : « Tout, chacun dans sa section » ; cahier 4.2).

Pour chaque candidat à qui Wikidata déclare un identifiant de député européen :

- **interventions en séance** : Parltrack (`CRE`) avant le 02/07/2019, le portail du PE
  (`speeches`) ensuite, comme pour les votes (décision Q3) ; ni l'une ni l'autre source ne donne le
  texte : le titre du débat, la date et le lien vers le compte rendu ;
- **rapports** (Parltrack, toutes dates) : `REPORT` → rapporteur, `REPORT-SHADOW` → rapporteur
  fictif, `COMPARL` → rapporteur pour avis, `COMPARL-SHADOW` → rapporteur fictif pour avis ;
- **propositions de résolution** : `MOTION` (avec d'autres députés), `IMOTION` (individuelle) ;
- **questions** : `WQ` (écrite), `OQ` (orale), `MINT` (interpellation majeure) ;
- **explications de vote** : `WEXP`, avec un extrait de 300 caractères de leur texte ;
- **autres** : `WDECL` (déclaration écrite), `PRUNACT`.

Parltrack est figé depuis le 24/07/2026 : ses activités s'arrêtent là (la fiche le dit). La date
d'une activité vient du lecteur (date de republication du 22/11/2016 écartée) : une activité sans
date sûre garde son année, et sa raison. Aucun décompte rapporté à quoi que ce soit.
"""
NOM = "R-ACTIVITE-PE"
VERSION = 1
DEPEND = ("R-IDENTITE",)
SORTIES = ("activite_pe",)
DESCRIPTION = (
    "Au Parlement européen, le site montre aussi l'activité d'un candidat hors des votes : ses "
    "interventions en séance (le titre du débat et le lien vers le compte rendu), ses rapports "
    "(comme rapporteur ou rapporteur fictif), ses propositions de résolution, ses questions écrites "
    "et orales, ses explications de vote (un extrait). Jusqu'en juin 2019, les interventions viennent "
    "de Parltrack ; ensuite, du portail du Parlement européen ; les autres activités viennent de "
    "Parltrack, qui ne se met plus à jour depuis juillet 2026.")

BASCULE = "2019-07-02"
FAMILLE = {"CRE": "interventions", "REPORT": "rapports", "REPORT-SHADOW": "rapports",
           "COMPARL": "rapports", "COMPARL-SHADOW": "rapports", "MOTION": "resolutions",
           "IMOTION": "resolutions", "WQ": "questions", "OQ": "questions", "MINT": "questions",
           "WEXP": "explications", "WDECL": "autres", "PRUNACT": "autres"}
ROLE = {"REPORT": "rapporteur", "REPORT-SHADOW": "rapporteur_fictif", "COMPARL": "rapporteur_pour_avis",
        "COMPARL-SHADOW": "rapporteur_fictif_pour_avis", "MOTION": "coauteur", "IMOTION": "auteur",
        "WQ": "question_ecrite", "OQ": "question_orale", "MINT": "interpellation_majeure",
        "WDECL": "declaration_ecrite", "PRUNACT": "autre"}


def appliquer(ctx):
    ids = [r[0] for r in ctx.x("SELECT DISTINCT eurodepute FROM candidat WHERE eurodepute IS NOT NULL")]
    parts = []
    fam = "CASE type " + " ".join(f"WHEN '{k}' THEN '{v}'" for k, v in FAMILLE.items()) + " ELSE 'autres' END"
    role = "CASE type " + " ".join(f"WHEN '{k}' THEN '{v}'" for k, v in ROLE.items()) + " END"
    if ctx.existe("parltrack_activites__activite_pt"):
        parts.append(f"""
            SELECT mep AS eurodepute, {fam} AS famille, type AS type_source, {role} AS role_pe,
                   date, annee, date_raison, terme AS legislature_pe, titre, reference, dossiers, commission,
                   CASE WHEN texte IS NOT NULL THEN left(texte, 300) END AS extrait,
                   prov_url AS source_url, 'parltrack' AS source, 'parltrack-activites' AS source_point,
                   mep || ':' || type || ':' || rang AS activite
            FROM parltrack_activites__activite_pt
            WHERE NOT (type = 'CRE' AND coalesce(date, annee || '-12-31') >= '{BASCULE}')""")
    if ctx.existe("pe_eurodeputes__intervention_pe"):
        parts.append(f"""
            SELECT personne AS eurodepute, 'interventions' AS famille, 'speech' AS type_source,
                   NULL::VARCHAR AS role_pe, date, left(date, 4) AS annee, NULL::VARCHAR AS date_raison,
                   NULL::VARCHAR AS legislature_pe,
                   debat AS titre, compte_rendu AS reference, NULL::VARCHAR AS dossiers,
                   NULL::VARCHAR AS commission, NULL::VARCHAR AS extrait, prov_url AS source_url,
                   'pe' AS source, 'pe-eurodeputes' AS source_point, intervention AS activite
            FROM pe_eurodeputes__intervention_pe WHERE date >= '{BASCULE}'""")
    if not parts or not ids:
        ctx.ecrire("activite_pe", """
            SELECT NULL::VARCHAR AS per, NULL::VARCHAR AS eurodepute, NULL::VARCHAR AS famille,
                   NULL::VARCHAR AS date, NULL::VARCHAR AS source WHERE false""")
        return {"activites": (0, 0)}
    liste = ", ".join(f"'{i}'" for i in ids)
    ctx.ecrire("activite_pe", f"""
        SELECT c.per, a.*
        FROM ({" UNION ALL BY NAME ".join(parts)}) a
        JOIN (SELECT per, eurodepute FROM candidat WHERE eurodepute IS NOT NULL) c USING (eurodepute)
        WHERE a.eurodepute IN ({liste})
        QUALIFY row_number() OVER (PARTITION BY c.per, a.source, a.activite ORDER BY a.date) = 1
        ORDER BY c.per, a.famille, coalesce(a.date, a.annee), a.activite""")
    n = ctx.un("SELECT count(*) FROM activite_pe")
    datees = ctx.un("SELECT count(*) FROM activite_pe WHERE date IS NOT NULL")
    return {"activites": (n, n), "date_etablie": (datees, n),
            "candidats_avec_activite": (ctx.un("SELECT count(DISTINCT per) FROM activite_pe"), len(ids))}
