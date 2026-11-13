"""R-MANDAT-LOCAL : les mandats locaux d'un candidat, lus dans le Répertoire national des élus
(lecteur `rne_elus` ; décisions du 13/11/2026 : mandats locaux réintégrés, Q34, Q35).

Le répertoire n'a **aucun identifiant de personne**. Un élu est rattaché à un candidat quand
(décision Q34) :

- son nom, son prénom et sa date de naissance concordent **exactement** avec l'identité du
  candidat (R-IDENTITE : nom et prénom de l'Assemblée, du Sénat ou de Wikipédia ; date de
  naissance de l'Assemblée, du Sénat ou de Wikidata) ; noms et prénoms comparés sans accents,
  sans casse, sans espaces ni tirets, **prénom et nom d'un seul tenant** (« Juan Branco » =
  « BRANCO » + « Juan ») : un candidat dont la seule source du nom est la liste n'a pas de prénom
  séparé ; jamais le nom seul, toujours avec la date de naissance ;
- ou une décision `elu_local` le dit, pour un candidat dont aucune source ne donne la date de
  naissance : elle nomme le candidat (nom de la liste), le nom, le prénom et la date de naissance
  de l'élu tels que le répertoire les publie, après vérification humaine.

Un élu que deux candidats revendiqueraient n'est rattaché à aucun (raison écrite).

Le répertoire ne publie **aucune date de fin**. Un mandat municipal du fichier des sortants
(mandats 2020-2026) se termine au premier tour des municipales, le **15/03/2026** : date
**déduite**, signalée (`fin_deduite`, `fin_raison` ; décision Q35). Un mandat des fichiers
trimestriels est en cours à la date du fichier. Avant 2020 : hors source (les jeux plus anciens
n'ont pas de licence).
"""
from .r_candidatures import vue_ou_vide

NOM = "R-MANDAT-LOCAL"
VERSION = 1
DEPEND = ("R-IDENTITE",)
SORTIES = ("mandat_local_candidat",)
DESCRIPTION = (
    "Les mandats locaux (conseiller municipal, maire, conseiller communautaire, départemental, "
    "régional…) viennent du Répertoire national des élus, publié par le ministère de l'Intérieur. "
    "Ce répertoire ne donne pas d'identifiant des personnes : un élu n'est rattaché à un candidat que "
    "si son nom, son prénom et sa date de naissance sont exactement ceux que donnent nos autres "
    "sources, ou si la responsable du site l'a vérifié et décidé. Le répertoire couvre les mandats en "
    "cours et les mandats municipaux de 2020 à 2026 ; rien d'antérieur. Il ne donne pas de date de "
    "fin : un mandat municipal de 2020 est montré jusqu'au premier tour des municipales du 15 mars "
    "2026, une date que nous déduisons et que la fiche signale.")

FIN_SORTANTS = "2026-03-15"
RAISON_FIN = ("fin déduite : renouvellement des conseils municipaux, premier tour du 15/03/2026 "
              "(le répertoire ne publie pas de date de fin)")


def norm(x: str) -> str:
    return f"upper(regexp_replace(strip_accents(coalesce({x}, '')), '[^A-Za-z]', '', 'g'))"


def appliquer(ctx):
    ml = vue_ou_vide(ctx, "rne_elus__mandat_local", {
        "fichier": "VARCHAR", "niveau": "VARCHAR", "sortant": "BOOLEAN", "fonction": "VARCHAR",
        "collectivite": "VARCHAR", "code_collectivite": "VARCHAR", "departement": "VARCHAR",
        "nom": "VARCHAR", "prenom": "VARCHAR", "naissance": "VARCHAR", "debut_mandat": "VARCHAR",
        "debut_fonction": "VARCHAR", "prov_url": "VARCHAR", "prov_point": "VARCHAR"})
    dec = vue_ou_vide(ctx, "decision_elu_local", {
        "candidat": "VARCHAR", "nom_elu": "VARCHAR", "prenom_elu": "VARCHAR", "naissance": "VARCHAR",
        "fichier": "VARCHAR"})
    # Identités à rechercher : celle de R-IDENTITE (nom, prénom, naissance), et celles des décisions.
    ctx.x(f"""CREATE OR REPLACE TEMP TABLE _ml_id AS
        SELECT i.per, {norm("coalesce(i.prenom, '') || i.nom")} AS np, i.naissance,
               'nom_prenom_naissance' AS methode, NULL::VARCHAR AS decision
        FROM personne_identite i
        WHERE i.naissance IS NOT NULL AND i.nom IS NOT NULL
        UNION
        SELECT c.per, {norm("coalesce(d.prenom_elu, '') || d.nom_elu")}, CAST(d.naissance AS VARCHAR),
               'decision', d.fichier
        FROM {dec} d JOIN candidat c ON c.nom_liste = d.candidat OR c.nom = d.candidat""")
    ctx.x(f"""CREATE OR REPLACE TEMP TABLE _ml AS
        SELECT x.per, x.methode, x.decision, m.*
        FROM (SELECT *, {norm("coalesce(prenom, '') || nom")} AS np FROM {ml}
              WHERE nom IS NOT NULL AND prenom IS NOT NULL) m
        JOIN _ml_id x ON x.np = m.np AND x.naissance = m.naissance""")
    # Un élu (même nom, prénom, naissance) revendiqué par deux candidats n'est rattaché à aucun.
    ctx.ecrire("mandat_local_candidat", f"""
        WITH conflit AS (SELECT np, naissance FROM _ml GROUP BY 1, 2 HAVING count(DISTINCT per) > 1),
        r AS (
            SELECT * FROM _ml m
            WHERE NOT EXISTS (SELECT 1 FROM conflit k WHERE k.np = m.np AND k.naissance = m.naissance)
            -- Le même mandat publié dans deux fichiers (un maire figure aussi parmi les conseillers
            -- municipaux) : une ligne, celle du fichier le plus précis.
            QUALIFY row_number() OVER (PARTITION BY per, sortant, code_collectivite, fonction, debut_mandat
                                       ORDER BY CASE WHEN fichier LIKE '%maires' THEN 0 ELSE 1 END, fichier) = 1)
        SELECT per, fichier, niveau, sortant, fonction, collectivite, code_collectivite, departement,
               debut_mandat, debut_fonction,
               coalesce(CASE WHEN fonction <> 'Conseiller municipal' THEN debut_fonction END, debut_mandat) AS debut,
               CASE WHEN sortant AND niveau = 'municipal' THEN '{FIN_SORTANTS}' END AS fin,
               sortant AND niveau = 'municipal' AS fin_deduite,
               CASE WHEN sortant AND niveau = 'municipal' THEN '{RAISON_FIN}' END AS fin_raison,
               methode, decision, naissance, nom AS nom_publie, prenom AS prenom_publie,
               prov_url AS source_url, prov_point AS source_point
        FROM r ORDER BY per, debut, fichier""")
    n = ctx.un("SELECT count(*) FROM candidat")
    avec = ctx.un("SELECT count(DISTINCT per) FROM mandat_local_candidat")
    cherchables = ctx.un("SELECT count(DISTINCT per) FROM _ml_id")
    conflits = ctx.un("SELECT count(*) FROM (SELECT np, naissance FROM _ml GROUP BY 1, 2 HAVING count(DISTINCT per) > 1)")
    for t in ("_ml_id", "_ml"):
        ctx.x(f"DROP TABLE IF EXISTS {t}")
    return {"candidats_avec_identite_recherchable": (cherchables, n),
            "candidats_avec_mandat_local": (avec, cherchables),
            "elus_revendiques_par_deux_candidats": (conflits, conflits)}
