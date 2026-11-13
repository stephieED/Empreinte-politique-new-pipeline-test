"""R-VOTE-PE : les votes nominatifs d'un candidat au Parlement européen (décisions Q3 et Q33 du
13/11/2026 ; cahier 4.2, « volet européen à part »).

Deux sources, raccordées au **02/07/2019** (décision Q3) : Parltrack (ODbL, lecteur
`parltrack_votes`) pour les votes antérieurs, le portail du PE (CC BY 4.0, lecteur `pe_votes`)
ensuite. Chaque vote dit sa source (`source`, `source_point`) : la licence de la ligne en dépend.

Pour chaque candidat à qui Wikidata déclare un identifiant de député européen (R-CANDIDATURES),
chaque vote nominatif du portail du PE (depuis le 02/07/2019) où il figure dans une liste
publiée : `favor` → `pour`, `against` → `contre`, `abstention` → `abstention`. Une correction
d'intention publiée après le vote (`intended_…`) est gardée à part (`intention`) : elle ne
change jamais la position enregistrée. Un vote où il ne figure dans aucune liste n'est pas une
ligne : rien n'est déduit d'une absence (aucun taux, cahier 2, règle 3).

**Nature** (décision Q33 : tous les votes nominatifs, chacun avec sa nature), lue dans la fin du
libellé du vote (après le dernier « - ») :

- `ensemble` : « Résolution », « Résolution législative », « Proposition de résolution (ensemble
  du texte) », « Proposition de la Commission », « Accord provisoire », « Vote unique », « Projet
  de recommandation / de décision / de résolution », « Proposition de décision », « Décision » ;
- `partie` : amendement (« Am 12 »), bloc d'amendements, paragraphe (« § 4 », « § 69/1 »),
  considérant, visa, article, annexe, point ;
- `procedure` : un vote sur la procédure, pas sur le texte (renvoi en commission, demande
  d'un groupe, procédure d'urgence, rejet, report, ouverture de négociations) ;
- `non_etablie` : tout autre libellé, compté dans la couverture, jamais deviné.

Le portail écrit parfois ses libellés en anglais ou en allemand : leurs formes connues sont lues
de même. Mesuré le 13/11/2026 sur les 24 002 votes de R. Glucksmann : la liste a été construite
sur ces libellés réels.
"""
NOM = "R-VOTE-PE"
VERSION = 2
DEPEND = ("R-IDENTITE",)
SORTIES = ("vote_personne_pe",)
DESCRIPTION = (
    "Au Parlement européen, le site montre chaque vote nominatif d'un candidat, tel que le Parlement "
    "le publie : pour, contre ou abstention. Jusqu'en juin 2019, les votes viennent de Parltrack, qui "
    "a recueilli les procès-verbaux du Parlement (licence ODbL) ; depuis juillet 2019, du portail de "
    "données du Parlement européen. Une correction de vote déposée "
    "après la séance est montrée à côté, sans remplacer le vote enregistré. Un vote où la personne "
    "ne figure pas n'est pas montré, et rien n'en est déduit. Chaque vote dit sa nature, lue dans son "
    "intitulé : sur l'ensemble d'un texte (une résolution, un accord, la proposition de la "
    "Commission…), sur une partie (un amendement, un paragraphe, un considérant), sur la procédure "
    "(un renvoi en commission, une demande d'urgence), ou « non établie » quand l'intitulé ne le dit "
    "pas.")

ENSEMBLE = (r"^(résolution( législative)?|propositions? de résolution( commune)?( \(ensemble du texte\))?"
            r"|propositions? de la commission|accord provisoire|vote unique|vote final|projet commun"
            r"|projets? de (recommandation|recommendation|décision|résolution|règlement)|projet du conseil"
            r"|propositions? de (décision|recommandation)|recommandation|procédure d'approbation"
            r"|élection de la commission|ensemble du texte|décision"
            r"|motion for a resolution|proposal for a resolution|draft (legislative )?resolution"
            r"|commission proposal|provisional agreement|single vote|joint text|consent procedure"
            r"|entschließungsantrag"
            # Formes anciennes (Parltrack, 2004-2019) : « approbation », « vote : approbation »,
            # « Proposition modifiée », « proposition (modifiée) Commission », « AFCO résolution ».
            r"|(vote : )?approbation|propositions? modifiée|propositions? (modifiée )?(de la )?commission"
            r"|[a-z]{2,6} résolution|consent)\b")
PARTIE = (r"^(am(endement)?s?\b|§|considérant|visa|article|art\.|annexe|point|bloc|\d"
          r"|recital|citation|paragraph|amendment|par\.|cons\.|sous-titre)")
PROCEDURE = (r"^(renvoi|demande|antrag|request|motion de|motion d'|objection|ordre du jour"
             r"|proposition de rejet|rejet|application de l'article|vote séparé|procédure d'urgence"
             r"|report|ajournement|irrecevabilit|decision to enter|vote procédural"
             r"|modification de l'ordre du jour|proposition de report)")
POSITIONS = {"favor": "pour", "against": "contre", "abstention": "abstention"}


def nature_sql(x: str) -> str:
    e = lambda r: r.replace("'", "''")
    return (f"(CASE WHEN regexp_matches(lower(trim({x})), '{e(ENSEMBLE)}') THEN 'ensemble' "
            f"WHEN regexp_matches(lower(trim({x})), '{e(PARTIE)}') THEN 'partie' "
            f"WHEN regexp_matches(lower(trim({x})), '{e(PROCEDURE)}') THEN 'procedure' "
            f"ELSE 'non_etablie' END)")


BASCULE = "2019-07-02"     # décision Q3 : Parltrack avant cette date, le portail du PE ensuite
POINT = {"pe": "pe-votes", "parltrack": "parltrack-votes"}


def _sources(ctx):
    """Votes et positions des deux sources, raccordées au 02/07/2019 (décision Q3), mêmes colonnes."""
    v, p = [], []
    if ctx.existe("pe_votes__vote_pe") and ctx.existe("pe_votes__position_pe"):
        v.append(f"""SELECT vote, numero, seance, date, heure, libelle, document_ref, objet, rubrique,
                            reference, resultat, pour, contre, abstention, methode, prov_url,
                            'pe' AS source FROM pe_votes__vote_pe WHERE date >= '{BASCULE}'""")
        p.append(f"""SELECT p.vote, p.position, p.personnes FROM pe_votes__position_pe p
                     SEMI JOIN pe_votes__vote_pe v ON v.vote = p.vote AND v.date >= '{BASCULE}'""")
    if ctx.existe("parltrack_votes__vote_pt") and ctx.existe("parltrack_votes__position_pt"):
        v.append(f"""SELECT vote, voteid AS numero, NULL AS seance, date, heure, libelle, document_ref,
                            objet, NULL AS rubrique, NULL AS reference, NULL AS resultat, pour, contre,
                            abstention, NULL AS methode, prov_url, 'parltrack' AS source
                     FROM parltrack_votes__vote_pt WHERE date < '{BASCULE}'""")
        p.append(f"""SELECT p.vote, p.position, p.personnes FROM parltrack_votes__position_pt p
                     SEMI JOIN parltrack_votes__vote_pt v ON v.vote = p.vote AND v.date < '{BASCULE}'""")
    return v, p


def appliquer(ctx):
    ids = [r[0] for r in ctx.x("SELECT DISTINCT eurodepute FROM candidat WHERE eurodepute IS NOT NULL ORDER BY 1")]
    votes, positions = _sources(ctx)
    if not votes or not ids:
        ctx.ecrire("vote_personne_pe", """
            SELECT NULL::VARCHAR AS per, NULL::VARCHAR AS eurodepute, NULL::VARCHAR AS vote,
                   NULL::VARCHAR AS date, NULL::VARCHAR AS nature, NULL::VARCHAR AS position,
                   NULL::VARCHAR AS source
            WHERE false""")
        return {"positions": (0, 0)}
    ctx.x("CREATE OR REPLACE TEMP TABLE _v AS " + " UNION ALL BY NAME ".join(votes))
    ctx.x("CREATE OR REPLACE TEMP TABLE _p AS " + " UNION ALL BY NAME ".join(positions))
    liste = "[" + ", ".join(f"'{i}'" for i in ids) + "]"
    ctx.x(f"""CREATE OR REPLACE TEMP TABLE _vpe AS
        WITH p AS (
            SELECT vote, position, unnest(list_intersect(personnes, {liste}::VARCHAR[])) AS eurodepute
            FROM _p
            WHERE len(list_intersect(personnes, {liste}::VARCHAR[])) > 0)
        SELECT eurodepute, vote,
               any_value(CASE position WHEN 'favor' THEN 'pour' WHEN 'against' THEN 'contre'
                                       WHEN 'abstention' THEN 'abstention' END)
                   FILTER (WHERE position IN ('favor', 'against', 'abstention')) AS position,
               count(*) FILTER (WHERE position IN ('favor', 'against', 'abstention')) AS nb_positions,
               any_value(CASE WHEN position LIKE 'intended_%'
                              THEN coalesce(CASE replace(position, 'intended_', '')
                                    WHEN 'favor' THEN 'pour' WHEN 'against' THEN 'contre'
                                    WHEN 'abstention' THEN 'abstention' END, position) END)
                   FILTER (WHERE position LIKE 'intended_%') AS intention
        FROM p GROUP BY 1, 2""")
    ctx.ecrire("vote_personne_pe", f"""
        SELECT c.per, x.eurodepute, v.vote, v.numero, v.seance, v.date, v.heure, v.libelle,
               v.document_ref, v.objet, v.rubrique, v.reference,
               {nature_sql("coalesce(v.objet, v.reference)")} AS nature,
               -- Deux listes pour la même personne : position non établie (jamais choisie).
               CASE WHEN x.nb_positions = 1 THEN x.position END AS position,
               CASE WHEN x.nb_positions > 1 THEN 'plusieurs positions publiées' END AS raison_position,
               x.intention, v.resultat, v.pour, v.contre, v.abstention, v.methode,
               v.source, CASE v.source WHEN 'pe' THEN '{POINT["pe"]}' ELSE '{POINT["parltrack"]}' END AS source_point,
               v.prov_url AS source_url
        FROM _vpe x JOIN _v v USING (vote)
        JOIN (SELECT per, eurodepute FROM candidat WHERE eurodepute IS NOT NULL) c USING (eurodepute)
        ORDER BY c.per, v.date, v.heure, v.numero""")
    n = ctx.un("SELECT count(*) FROM vote_personne_pe")
    nat = ctx.un("SELECT count(*) FROM vote_personne_pe WHERE nature <> 'non_etablie'")
    pos = ctx.un("SELECT count(*) FROM vote_personne_pe WHERE position IS NOT NULL")
    pt = ctx.un("SELECT count(*) FROM vote_personne_pe WHERE source = 'parltrack'")
    for t in ("_vpe", "_v", "_p"):
        ctx.x(f"DROP TABLE IF EXISTS {t}")
    return {"position_etablie": (pos, n), "nature_etablie": (nat, n), "votes_parltrack": (pt, n),
            "candidats_avec_votes": (ctx.un("SELECT count(DISTINCT per) FROM vote_personne_pe"), len(ids))}
