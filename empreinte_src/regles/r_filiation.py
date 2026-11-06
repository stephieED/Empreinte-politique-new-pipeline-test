"""R-FILIATION : un groupe d'une législature prend-il la suite d'un groupe de la précédente ?
(cahier 4.3 et 6.1 ; doc. 1, 1.5.2 et 1.6 ; doc. 5, Q22).

L'Assemblée ferme tous les groupes à chaque législature, sans lien officiel de succession. Pour
chaque paire (maillon de la législature N-1, maillon de la législature N) qui a au moins un
membre commun (maillons de R-CONTINUITE-GROUPE ; membre = au moins une période d'appartenance,
R-APPARTENANCE) :

- **réélus** : membres de l'ancien maillon qui sont députés pendant la législature N (R-DEPUTES) ;
- **anciens députés** : membres du nouveau maillon qui étaient députés pendant la législature N-1 ;
- **communs** : membres des deux maillons. Ce sont à la fois les réélus de l'ancien passés dans le
  nouveau et les anciens députés du nouveau venus de l'ancien ;
- **suite** quand les deux parts (communs / réélus, communs / anciens députés) combinées par leur
  moyenne harmonique atteignent 60 % et qu'il y a au moins 5 communs. La moyenne harmonique des
  deux parts vaut 2 × communs / (réélus + anciens députés) : la règle compare donc des nombres
  entiers (10 × communs ≥ 3 × (réélus + anciens députés)) et **n'écrit aucun ratio** ; les
  décomptes sont servis, l'interface affiche les parts si elle le veut.

Vérifié sur les deux exemples du cahier (archive du 06/11/2026) : la Nouvelle Gauche (XVe) prend
la suite du groupe socialiste de la XIVe (28 communs sur 55 réélus et 28 anciens députés : 51 % et
100 %, combinées 67 %) ; Les Républicains (XVe) ne prennent pas la suite de R-UMP (17 communs sur
17 réélus et 56 anciens députés : 100 % et 30 %, combinées 47 %).

Fusion : un nouveau maillon peut prendre la suite de plusieurs anciens (chaque paire passe le
seuil). Scission : la part qui part ne passe pas le seuil, elle n'est pas la suite. Si un ancien
maillon avait **deux** suites qui passent le seuil, la règle ne tranche pas : `a_trancher` pour
les deux, jusqu'à une décision `filiation` (`avant`, `apres` : identifiants de maillon
`grp:…`, `verdict: suite | pas_suite`). Une décision l'emporte toujours sur le calcul.
"""

NOM = "R-FILIATION"
VERSION = 1
DEPEND = ("R-CONTINUITE-GROUPE", "R-DEPUTES", "R-APPARTENANCE")
SORTIES = ("filiation",)
DESCRIPTION = (
    "Un groupe d'une nouvelle législature prend la suite d'un groupe de la précédente quand deux "
    "parts, combinées par leur moyenne harmonique, atteignent 60 %, avec au moins cinq députés "
    "communs : la part des réélus de l'ancien groupe qui sont passés dans le nouveau, et la part "
    "des anciens députés du nouveau groupe qui venaient de l'ancien. Un groupe peut prendre la "
    "suite de plusieurs groupes (fusion) ; la partie qui quitte un groupe n'est pas sa suite "
    "(scission). Un ancien groupe qui aurait deux suites attend une décision. Les nombres de "
    "députés de chaque comparaison sont publiés.")

COMMUNS_MIN = 5
SEUIL = (3, 5)        # 60 %


def appliquer(ctx):
    n, d = SEUIL
    ctx.x("""CREATE OR REPLACE TEMP TABLE _fi_m AS
        SELECT DISTINCT m.maillon, m.legislature, a.acteur
        FROM appartenance a JOIN maillon m ON m.organe = a.groupe""")
    ctx.x("""CREATE OR REPLACE TEMP TABLE _fi_dep AS
        SELECT DISTINCT acteur, legislature FROM depute WHERE legislature IS NOT NULL""")
    ctx.x(f"""CREATE OR REPLACE TEMP TABLE _fi AS
        WITH paires AS (
            SELECT a.maillon AS avant, b.maillon AS apres, a.legislature AS leg_avant,
                   b.legislature AS leg_apres, count(*) AS communs
            FROM _fi_m a JOIN _fi_m b ON b.acteur = a.acteur AND b.legislature = a.legislature + 1
            GROUP BY 1, 2, 3, 4),
        reelus AS (SELECT m.maillon, count(*) AS reelus FROM _fi_m m
                   SEMI JOIN _fi_dep d ON d.acteur = m.acteur AND d.legislature = m.legislature + 1
                   GROUP BY 1),
        anciens AS (SELECT m.maillon, count(*) AS anciens FROM _fi_m m
                    SEMI JOIN _fi_dep d ON d.acteur = m.acteur AND d.legislature = m.legislature - 1
                    GROUP BY 1)
        SELECT p.*, r.reelus, a.anciens,
               p.communs >= {COMMUNS_MIN} AND 2 * {d} * p.communs >= {n} * (r.reelus + a.anciens)
                   AS passe_le_seuil
        FROM paires p JOIN reelus r ON r.maillon = p.avant JOIN anciens a ON a.maillon = p.apres""")
    dec = "decision_filiation"
    jointure = (f"""LEFT JOIN (SELECT avant, apres, any_value(verdict) AS verdict, any_value(fichier) AS fichier
                               FROM {dec} GROUP BY 1, 2) d ON d.avant = f.avant AND d.apres = f.apres"""
                if ctx.existe(dec) else
                "LEFT JOIN (SELECT NULL::VARCHAR AS verdict, NULL::VARCHAR AS fichier) d ON false")
    ctx.ecrire("filiation", f"""
        WITH f AS (SELECT *, count(*) FILTER (passe_le_seuil) OVER (PARTITION BY avant) AS suites FROM _fi)
        SELECT f.avant AS maillon_avant, f.apres AS maillon_apres, f.leg_avant AS legislature_avant,
               f.leg_apres AS legislature_apres, f.reelus, f.anciens AS anciens_deputes, f.communs,
               CASE WHEN d.verdict IN ('suite', 'pas_suite') THEN d.verdict
                    WHEN NOT f.passe_le_seuil THEN 'pas_suite'
                    WHEN f.suites > 1 THEN 'a_trancher'
                    ELSE 'suite' END AS verdict,
               CASE WHEN d.verdict IN ('suite', 'pas_suite') THEN 'decision'
                    WHEN f.communs < {COMMUNS_MIN} THEN 'moins_de_{COMMUNS_MIN}_communs'
                    WHEN NOT f.passe_le_seuil THEN 'sous_le_seuil'
                    WHEN f.suites > 1 THEN 'ancien_groupe_avec_plusieurs_suites'
                    ELSE 'regle' END AS raison,
               d.fichier AS decision
        FROM f {jointure}
        ORDER BY f.leg_avant, f.avant, f.apres""")
    for t in ("_fi", "_fi_m", "_fi_dep"):
        ctx.x(f"DROP TABLE IF EXISTS {t}")
    tot = ctx.un("SELECT count(*) FROM filiation")
    tranche = ctx.un("SELECT count(*) FROM filiation WHERE verdict <> 'a_trancher'")
    nouveaux = ctx.un("""SELECT count(DISTINCT maillon) FROM maillon m
                         WHERE legislature > (SELECT min(legislature) FROM maillon)""")
    rattaches = ctx.un("SELECT count(DISTINCT maillon_apres) FROM filiation WHERE verdict = 'suite'")
    return {"paires_tranchees": (tranche, tot),
            "maillons_qui_prennent_une_suite": (rattaches, nouveaux)}
