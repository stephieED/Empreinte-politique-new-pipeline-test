"""R-CONTINUITE-GROUPE : les organes successifs d'un même groupe dans une législature forment un
seul « maillon » (doc. 1, 1.2.2, 1.5.2 et 1.6 ; cahier 3.1.1 et 4.3 ; doc. 5, Q15).

L'Assemblée ferme parfois l'organe d'un groupe en cours de législature et en ouvre un autre le
lendemain, avec les mêmes membres : changement de nom (UMP → Les Républicains en 2015, SRC → SER
en 2016, Nouvelle Gauche → Socialistes en 2018, À Droite → UDR en 2024) ou simple renumérotation
(UDR en 2025). Aucun champ ne relie les deux organes (`organe_precedent` est vide partout,
archive du 06/11/2026). La règle les relie quand :

1. l'organe suivant commence entre le jour de fin de l'organe précédent et 7 jours après ;
2. au moins 5 membres sont communs : membres de l'organe précédent le jour de sa fin, membres de
   l'organe suivant dans ses 7 premiers jours (R-APPARTENANCE) ;
3. les deux parts — communs parmi les membres de l'ancien, communs parmi ceux du nouveau —
   combinées (moyenne harmonique) atteignent 80 %. En nombres entiers : 2 × communs ≥ 0,8 ×
   (membres de l'ancien + membres du nouveau), soit 10 × communs ≥ 4 × (ancien + nouveau).

Le sigle n'est **pas** un critère, contrairement au défaut écrit dans le doc. 1 (« même sigle ») :
8 des 11 changements d'organe d'un même groupe mesurés de la XIIe à la XVIIe changent aussi de
sigle, avec 97 à 100 % de membres communs ; les groupes dissidents restent loin du seuil (R-UMP
55 %, Agir ensemble 41 %, EDS 4 %).

Un organe qui aurait deux prédécesseurs, ou un prédécesseur avec deux suites, qui passent tous
le seuil : la règle ne tranche pas (`a_trancher`) et ne relie rien ; une décision
`continuite_groupe` le fait (`avant`, `apres`, `verdict: continuite | pas_continuite`). Une
décision l'emporte toujours sur le calcul.

Sorties :
- `continuite_groupe` : une ligne par paire d'organes candidate (critère 1), avec ses décomptes
  et son verdict ;
- `maillon` : une ligne par organe de groupe, avec son maillon `grp:<législature>:<premier
  organe>`, son rang dans le maillon, et la position déclarée du maillon (`divergente` quand deux
  de ses organes déclarent des positions différentes, cahier 4.3).
"""

NOM = "R-CONTINUITE-GROUPE"
VERSION = 1
DEPEND = ("R-APPARTENANCE",)
SORTIES = ("continuite_groupe", "maillon")
DESCRIPTION = (
    "Quand l'Assemblée ferme le groupe d'une législature et en ouvre un autre dans les sept jours "
    "qui suivent, les deux ne font qu'un groupe si au moins cinq députés sont communs et si les "
    "deux parts de députés communs — parmi les membres de l'ancien groupe le jour de sa fin, et "
    "parmi ceux du nouveau dans sa première semaine — atteignent ensemble 80 % (moyenne "
    "harmonique). Le changement de nom ou de sigle n'empêche pas la continuité. Un cas où deux "
    "groupes pourraient prendre la même suite, ou un groupe deux suites, attend une décision.")

ECART_MAX_JOURS = 7
COMMUNS_MIN = 5
# Seuil de la moyenne harmonique, en fraction entière (numérateur, dénominateur) : 80 %.
SEUIL = (4, 5)


def appliquer(ctx):
    """Applique R-CONTINUITE-GROUPE : écrit `continuite_groupe` (le verdict sur chaque paire
    d'organes de groupe successifs, décisions `continuite_groupe` comprises) et `maillon` (les
    chaînes d'organes reliés par une continuité), voir la description du module. Rend la
    couverture, `{nom: (numérateur, dénominateur)}` : `paires_d_organes_tranchees`."""
    n, d = SEUIL
    ctx.x(f"""CREATE OR REPLACE TEMP TABLE _cg AS
        WITH g AS (SELECT organe, legislature, debut, coalesce(fin, '9999-12-31') AS fin FROM groupe),
        p AS (SELECT a.organe AS avant, b.organe AS apres, a.legislature, a.fin AS fin_avant,
                     b.debut AS debut_apres
              FROM g a JOIN g b ON a.legislature = b.legislature AND a.organe <> b.organe
               AND a.fin <> '9999-12-31'
               AND b.debut::DATE BETWEEN a.fin::DATE AND a.fin::DATE + {ECART_MAX_JOURS}),
        ma AS (SELECT DISTINCT p.avant, p.apres, x.acteur FROM p JOIN appartenance x
                 ON x.groupe = p.avant AND x.debut <= p.fin_avant
                AND coalesce(x.fin, '9999-12-31') >= p.fin_avant),
        mb AS (SELECT DISTINCT p.avant, p.apres, x.acteur FROM p JOIN appartenance x
                 ON x.groupe = p.apres AND x.debut::DATE <= p.debut_apres::DATE + {ECART_MAX_JOURS}),
        c AS (SELECT p.avant, p.apres,
                     (SELECT count(*) FROM ma WHERE ma.avant = p.avant AND ma.apres = p.apres) AS membres_avant,
                     (SELECT count(*) FROM mb WHERE mb.avant = p.avant AND mb.apres = p.apres) AS membres_apres,
                     (SELECT count(*) FROM ma JOIN mb USING (avant, apres, acteur)
                       WHERE ma.avant = p.avant AND ma.apres = p.apres) AS communs
              FROM p)
        SELECT p.legislature, p.avant AS organe_avant, p.apres AS organe_apres, p.fin_avant, p.debut_apres,
               c.membres_avant, c.membres_apres, c.communs,
               c.communs >= {COMMUNS_MIN}
                 AND 2 * {d} * c.communs >= {n} * (c.membres_avant + c.membres_apres) AS passe_le_seuil
        FROM p JOIN c USING (avant, apres)""")
    # Conflits : un organe avec deux suites (ou deux prédécesseurs) qui passent le seuil.
    dec = "decision_continuite_groupe"
    a_dec = ctx.existe(dec)
    jointure = (f"""LEFT JOIN (SELECT avant, apres, any_value(verdict) AS verdict, any_value(fichier) AS fichier
                               FROM {dec} GROUP BY 1, 2) d
                      ON d.avant = c.organe_avant AND d.apres = c.organe_apres""" if a_dec else
                "LEFT JOIN (SELECT NULL::VARCHAR AS verdict, NULL::VARCHAR AS fichier) d ON false")
    ctx.ecrire("continuite_groupe", f"""
        WITH c AS (
            SELECT *,
                   count(*) FILTER (passe_le_seuil) OVER (PARTITION BY organe_avant) AS suites,
                   count(*) FILTER (passe_le_seuil) OVER (PARTITION BY organe_apres) AS precedents
            FROM _cg)
        SELECT c.legislature, c.organe_avant, c.organe_apres, c.fin_avant, c.debut_apres,
               c.membres_avant, c.membres_apres, c.communs,
               CASE WHEN d.verdict IN ('continuite', 'pas_continuite') THEN d.verdict
                    WHEN NOT c.passe_le_seuil THEN 'pas_continuite'
                    WHEN c.suites > 1 OR c.precedents > 1 THEN 'a_trancher'
                    ELSE 'continuite' END AS verdict,
               CASE WHEN d.verdict IN ('continuite', 'pas_continuite') THEN 'decision'
                    WHEN c.communs < {COMMUNS_MIN} THEN 'moins_de_{COMMUNS_MIN}_communs'
                    WHEN NOT c.passe_le_seuil THEN 'sous_le_seuil'
                    WHEN c.suites > 1 THEN 'plusieurs_suites'
                    WHEN c.precedents > 1 THEN 'plusieurs_precedents'
                    ELSE 'regle' END AS raison,
               d.fichier AS decision
        FROM c {jointure}
        ORDER BY c.legislature, c.debut_apres, c.organe_apres, c.organe_avant""")

    # Maillons : chaînes d'organes reliés par une continuité (union des liens retenus).
    liens = ctx.x("SELECT organe_avant, organe_apres FROM continuite_groupe WHERE verdict = 'continuite'")
    parent: dict[str, str] = {}

    def racine(x):
        """Rend la racine de `x` dans la forêt `parent` (union des liens retenus), en remontant les
        parents ; un organe sans parent est sa propre racine."""
        while parent.get(x, x) != x:
            x = parent[x]
        return x

    organes = ctx.x("SELECT organe, legislature, debut FROM groupe ORDER BY debut, organe")
    ordre = {o: k for k, (o, _, _) in enumerate(organes)}
    for a, b in liens:
        ra, rb = racine(a), racine(b)
        if ra != rb:
            # La racine d'un maillon est son organe le plus ancien.
            premier, second = (ra, rb) if ordre.get(ra, 0) <= ordre.get(rb, 0) else (rb, ra)
            parent[second] = premier
    import pyarrow as pa
    t = pa.table({"organe": [o for o, _, _ in organes],
                  "premier": [racine(o) for o, _, _ in organes]})
    ctx.con.register("_cg_racine", t)
    ctx.ecrire("maillon", """
        WITH r AS (SELECT r.organe, r.premier, g.legislature, g.sigle, g.libelle, g.debut, g.fin,
                          g.position_declaree, g.source_url
                   FROM _cg_racine r JOIN groupe g USING (organe)),
        m AS (SELECT premier,
                     CASE WHEN count(DISTINCT position_declaree) = 1 THEN any_value(position_declaree)
                          ELSE 'divergente' END AS position_maillon,
                     min(debut) AS debut_maillon,
                     CASE WHEN bool_or(fin IS NULL) THEN NULL ELSE max(fin) END AS fin_maillon,
                     count(*) AS nb_organes
              FROM r GROUP BY 1)
        SELECT 'grp:' || r.legislature || ':' || r.premier AS maillon, r.legislature, r.organe,
               row_number() OVER (PARTITION BY r.premier ORDER BY r.debut, r.organe) AS rang,
               r.sigle, r.libelle, r.debut, r.fin, r.position_declaree,
               m.position_maillon, m.debut_maillon, m.fin_maillon, m.nb_organes, r.source_url
        FROM r JOIN m USING (premier)
        ORDER BY r.legislature, maillon, rang""")
    ctx.con.unregister("_cg_racine")
    ctx.x("DROP TABLE IF EXISTS _cg")

    paires = ctx.un("SELECT count(*) FROM continuite_groupe")
    tranchees = ctx.un("SELECT count(*) FROM continuite_groupe WHERE verdict <> 'a_trancher'")
    return {"paires_d_organes_tranchees": (tranchees, paires)}
