"""Étape E6 — Contrôler (doc. 2, 2.8).

Contrôles **bloquants** : si l'un d'eux trouve une anomalie, la publication est refusée (la
tâche `ecrire` écrit alors l'acquis, et rien d'autre). Chaque anomalie a une **empreinte**
(contrôle + objets concernés) ; une décision `levee_controle` dont le champ `empreinte` est
égal à celle de l'anomalie la lève, pour cette anomalie seulement : si l'anomalie change, la
levée ne vaut plus (doc. 3, J16).

Contrôles bloquants : C1 (pertes non expliquées), C2 (liens pendants), C3 (données laissées de
côté), C4 (données interdites), C5 (lecture incomplète présentée comme complète), C6
(effondrement), C7 (personne attendue écartée en silence).

**Avertissements** (doc. 2, 2.8.2) : la publication est maintenue, la propriétaire est avertie
(une issue par avertissement). A1 fiche hors modèle, A2 vérification croisée sur les pages
publiques (module `verification`), A3 totaux d'une autre source, A4 double affichage, A5 famille
à zéro pour tout le monde, A6 couverture insuffisante, A7 entrées non résolues, A8 mandat ouvert
dans un organe clos. Les textes d'avertissement donnent des **décomptes et des identifiants**,
jamais un indice individuel (doc. 2, 2.10) : A6 compte les membres sans prise de parole servie,
sans les nommer.

C3, C7 et les avertissements lisent les tables des règles (Z2, Z3) par la connexion du contexte
et l'export des faits publiés de la candidate : `preparer(con, faits_publies, fiches)` d'abord.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import re

import duckdb

# Clés et motifs interdits dans un fichier servi (cahier, partie 2 et 2.1).
CLES_INTERDITES = re.compile(
    r"(taux_?de_?presence|presence|participation_individuelle|score|classement|rang_personne|"
    r"cohesion|nb_divergences|total_divergences|taux_adoption|part_appliquant|indice_)", re.I)
VALEURS_49_3_INTERDITES = {"49.3", "49-3", "art.49.3"}     # jamais une position de vote
# C1 : faits dont l'identifiant servi est un numéro d'ordre (`sujet_id`), qui se décale quand un
# sujet plus ancien change : leur identité est ce que le lecteur voit (12/11/2026).
IDENTITE_PAR_CONTENU = {"parole_sujet": ("sujet", "type_sujet", "dossiers")}
# Décomptes de faits que C1 vérifie un par un ailleurs (les amendements, dans les listes de chaque
# année). Une ligne de décompte (commission × année) qui disparaît parce que sa case s'est vidée
# n'est pas un fait perdu : ses amendements ont changé de case (commission établie à la source,
# essai du 13/11/2026 : 122 amendements de 2026 passés de « commission non établie » à PO419610).
DECOMPTES_VERIFIES_UN_PAR_UN = {"amendements_compte", "amendements_compte_lignee"}


def _vide(v) -> bool:
    return v is None or v == "" or v == [] or v == {}


def _videes(avant, apres, chemin=""):
    """Feuilles de `avant` qui se vident dans `apres` : (chemin, "a_zero" | "vide")."""
    if isinstance(avant, dict):
        apres = apres if isinstance(apres, dict) else {}
        for k, v in avant.items():
            yield from _videes(v, apres.get(k), f"{chemin}.{k}" if chemin else k)
        return
    if isinstance(avant, bool):
        return
    if isinstance(avant, (int, float)):
        if avant != 0 and (apres is None or apres == 0):
            yield chemin, "a_zero"
        return
    if not _vide(avant) and _vide(apres):
        yield chemin, "vide"


def _empreinte(controle: str, objets) -> str:
    h = hashlib.sha256((controle + "|" + "|".join(sorted(map(str, objets)))).encode()).hexdigest()
    return f"{controle}:{h[:16]}"


class Controles:
    def __init__(self, racine_publication: str, levees: list[dict] | None = None):
        self.racine = racine_publication
        self.levees = {l.get("empreinte"): l for l in (levees or []) if l.get("empreinte")}
        self.anomalies: list[dict] = []

    def _signaler(self, controle, titre, objets, bloquant=True, detail=None):
        e = _empreinte(controle, objets)
        levee = self.levees.get(e)
        self.anomalies.append({"controle": controle, "titre": titre, "empreinte": e,
                               "bloquant": bloquant and levee is None,
                               "levee_par": (levee or {}).get("fichier"),
                               "nb_objets": len(objets), "exemples": sorted(map(str, objets))[:10],
                               "detail": detail})

    # -- lecture des fichiers servis -----------------------------------------------------
    def _fichiers(self):
        for racine, _, noms in os.walk(self.racine):
            for n in noms:
                if n.endswith(".json.gz"):
                    p = os.path.join(racine, n)
                    with gzip.open(p) as f:
                        yield os.path.relpath(p, self.racine), json.load(f)

    # -- C2 : liens pendants -------------------------------------------------------------
    def c2_liens(self, fiches_publiees: set[str]):
        pendants = []
        for chemin, contenu in self._fichiers():
            for cible in _liens(contenu):
                if cible not in fiches_publiees:
                    pendants.append(f"{chemin} -> {cible}")
        if pendants:
            self._signaler("C2", "Liens vers une fiche absente", pendants)

    # -- C4 : données interdites -----------------------------------------------------------
    def c4_interdits(self):
        trouves = []
        for chemin, contenu in self._fichiers():
            for cle in _cles(contenu):
                if CLES_INTERDITES.search(cle):
                    trouves.append(f"{chemin}: clé « {cle} »")
            if contenu.get("section") and "colonnes" in contenu:
                cols = contenu["colonnes"]
                if "position" in cols:
                    i = cols.index("position")
                    for l in contenu["lignes"]:
                        if str(l[i]).lower() in VALEURS_49_3_INTERDITES:
                            trouves.append(f"{chemin}: 49.3 présenté comme une position de vote")
                for c in cols:
                    if c.startswith("ratio") or c.startswith("taux"):
                        trouves.append(f"{chemin}: ratio servi tout fait (« {c} »)")
        if trouves:
            self._signaler("C4", "Données interdites dans les fichiers servis", trouves)

    def c4_forme(self, chemin_schema: str):
        """Forme des fichiers servis contre le schéma commité en liste blanche (doc. 2, 2.8.1 ;
        issue #43, décision du 13/11/2026 « Schéma commité, bloquant »). Sans schéma : bloque,
        on ne publie pas une forme que rien ne vérifie."""
        from .schema import charger, verifier
        if not os.path.exists(chemin_schema):
            self._signaler("C4", "Forme des fichiers servis : schéma absent", [chemin_schema])
            return
        ecarts = verifier(self.racine, charger(chemin_schema))
        if ecarts:
            self._signaler("C4", "Forme des fichiers servis différente du schéma", ecarts)

    # -- C5 : lecture incomplète présentée comme complète --------------------------------
    def c5_couverture(self, releves: list[dict]):
        """Une section dite complète pour une source dont le dernier relevé a échoué."""
        en_panne = {r["point_acces"] for r in releves if r.get("issue") in ("echec", "suspect")}
        fautives = []
        for chemin, contenu in self._fichiers():
            c = contenu.get("couverture") or {}
            # Une section porte un dictionnaire ; l'en-tête d'une fiche, la liste de ses sections.
            for x in (c if isinstance(c, list) else [c]):
                if (isinstance(x, dict) and x.get("statut") == "complet"
                        and set(x.get("points_acces") or []) & en_panne):
                    fautives.append(f"{chemin} ({x.get('section', 'section')})")
        if fautives:
            self._signaler("C5", "Section dite complète alors qu'une de ses sources est en panne", fautives)

    # -- A9 : valeurs vidées (issue #42, décision du 13/11/2026) ---------------------------
    def a9_valeurs_videes(self, faits_avant: str | None, faits_apres: str, seuil_part=0.01, seuil_nb=50):
        """C1 reconnaît un fait à son identité (correctif délibéré du 12/11) : un compteur qui passe
        de 6 à 0, un champ qui se vide, ne sont pas des pertes pour lui. A9 les compte, à part, sans
        bloquer : pour les faits présents les deux nuits (même identité), chaque feuille de la
        valeur qui passe d'un nombre non nul à 0 ou à rien, ou d'une valeur non vide à rien (absente,
        nulle, chaîne ou liste vide). Avertissement par (type de fait, champ) au-delà de 1 % des faits
        du type **ou** de 50 faits ; décomptes et identifiants seulement."""
        if not faits_avant or not os.path.exists(faits_avant):
            return
        from .composition import IDS
        con = duckdb.connect()

        def ids(fichier):
            cols = {r[0] for r in con.execute(f"DESCRIBE SELECT * FROM read_parquet('{fichier}')").fetchall()}
            return [f"id_{k}" if f"id_{k}" in cols else "NULL::VARCHAR" for k in IDS]

        def cle(fichier):
            return (f"fiche || '|' || type_fait || '|' || concat_ws('|', "
                    + ", ".join(f"coalesce({x}, '')" for x in ids(fichier)) + ")")

        def avec_id(fichier):
            return "NOT (" + " AND ".join(f"{x} IS NULL" for x in ids(fichier)) + ")"
        totaux = dict(con.execute(f"SELECT type_fait, count(*) FROM read_parquet('{faits_avant}') "
                                  f"WHERE {avec_id(faits_avant)} GROUP BY 1").fetchall())
        cur = con.execute(f"""
            -- Seulement les identités uniques des deux côtés : plusieurs faits sous la même identité
            -- (un effectif par date d'un maillon, plusieurs rôles sur un texte) ne s'apparient pas.
            WITH a AS (SELECT type_fait, {cle(faits_avant)} AS k, any_value(valeur) AS valeur
                       FROM read_parquet('{faits_avant}') WHERE {avec_id(faits_avant)}
                       GROUP BY 1, 2 HAVING count(*) = 1),
                 b AS (SELECT {cle(faits_apres)} AS k, any_value(valeur) AS valeur
                       FROM read_parquet('{faits_apres}') WHERE {avec_id(faits_apres)}
                       GROUP BY 1 HAVING count(*) = 1)
            SELECT a.type_fait, a.k, a.valeur, b.valeur FROM a JOIN b USING (k) WHERE a.valeur <> b.valeur""")
        compte: dict[tuple, list] = {}
        while True:
            lot = cur.fetchmany(20_000)
            if not lot:
                break
            for type_fait, k, va, vb in lot:
                try:
                    x, y = json.loads(va), json.loads(vb)
                except ValueError:
                    continue
                for chemin, nature in _videes(x, y):
                    compte.setdefault((type_fait, chemin, nature), []).append(
                        "|".join(x for x in k.split("|") if x))
        con.close()
        objets = []
        for (type_fait, chemin, nature), ks in sorted(compte.items()):
            total = totaux.get(type_fait, 0)
            if len(ks) > seuil_nb or (total and len(ks) > seuil_part * total):
                quoi = "nombre passé à 0 ou à rien" if nature == "a_zero" else "valeur vidée"
                objets.append(f"{type_fait}.{chemin} : {quoi} pour {len(ks)} faits sur {total}, dont "
                              + ", ".join(sorted(ks)[:3]))
        self._avertir("A9", "Valeurs vidées d'une publication à l'autre (C1 compare l'identité)", objets)

    # -- C1 et C6 : comparaison avec la publication précédente ----------------------------
    def c1_c6_comparer(self, faits_avant: str | None, faits_apres: str,
                       uids_changes_a_la_source: set[str] | None = None, seuil_effondrement=0.2,
                       fiches_retirees: dict[str, str] | None = None):
        """`fiches_retirees` : {fiche: raison} des fiches qui ne sont plus publiées pour une raison
        établie (candidature retirée, candidat qui n'est plus dans la liste). Leurs faits perdus
        sont expliqués ; la fiche retirée cette nuit est nommée dans l'avertissement A9."""
        fiches_retirees = fiches_retirees or {}
        self.fiches_retirees_cette_nuit = {}
        if not faits_avant or not os.path.exists(faits_avant):
            # Rien à comparer : dit, jamais silencieux (issue #40). Attendu au premier calcul
            # seulement ; ensuite, le signe d'une publication précédente introuvable.
            self._avertir("C1-C6", "Pertes non contrôlées : aucune publication précédente à comparer",
                          ["C1 (pertes) et C6 (effondrement) non appliqués à cette publication"])
            return
        con = duckdb.connect()
        # Un fait se reconnaît à son identité (fiche, type, identifiants de source), pas à sa
        # valeur : un compte daté « au 09/11 » qui devient « au 10/11 » est le même fait, modifié,
        # pas un fait perdu (défaut constaté les 08 et 10/11/2026). Le fichier servi (section)
        # n'en fait pas partie : les paquets sont redécoupés d'une nuit à l'autre. Un fait sans
        # aucun identifiant se reconnaît à sa valeur, sans sa date de compte.
        from .composition import IDS

        def ids(fichier):
            cols = {r[0] for r in con.execute(f"DESCRIBE SELECT * FROM read_parquet('{fichier}')").fetchall()}
            return [f"id_{k}" if f"id_{k}" in cols else "NULL::VARCHAR" for k in IDS]

        def cle(fichier):
            i = ids(fichier)
            return (f"fiche || '|' || type_fait || '|' || "
                    f"concat_ws('|', {', '.join(f'coalesce({x}, {chr(39)}{chr(39)})' for x in i)})")

        def sans_id(fichier):
            # Faits identifiés par leur contenu (pas d'identifiant de source, ou un numéro d'ordre
            # qui se décale) : traités plus bas par leur descripteur.
            return ("(" + " AND ".join(f"{x} IS NULL" for x in ids(fichier)) + ") OR type_fait IN ("
                    + ", ".join(f"'{t}'" for t in IDENTITE_PAR_CONTENU) + ")")
        perdus = con.execute(f"""
            WITH a AS (SELECT *, {cle(faits_avant)} AS cle FROM read_parquet('{faits_avant}')
                       WHERE NOT ({sans_id(faits_avant)})),
                 b AS (SELECT DISTINCT {cle(faits_apres)} AS cle FROM read_parquet('{faits_apres}'))
            SELECT a.fiche, a.section, a.type_fait, a.valeur FROM a ANTI JOIN b USING (cle)""").fetchall()
        # Faits sans aucun identifiant (comptes par ministère et par nature, par exemple) : leur
        # identité est leur valeur sans ses comptes ni ses dates, qui changent légitimement.
        def descripteur(fiche, type_fait, valeur):
            try:
                v = json.loads(valeur)
            except ValueError:
                return (fiche, type_fait, valeur)
            if isinstance(v, dict) and type_fait in IDENTITE_PAR_CONTENU:
                v = {k: v.get(k) for k in IDENTITE_PAR_CONTENU[type_fait]}
            elif isinstance(v, dict):
                v = {k: x for k, x in v.items() if not (k in ("au", "du", "date_reference")
                                                        or k.startswith(("nb_", "effectif")))}
            return (fiche, type_fait, json.dumps(v, sort_keys=True, ensure_ascii=False))
        sans_a = con.execute(f"SELECT fiche, section, type_fait, valeur FROM read_parquet('{faits_avant}') "
                             f"WHERE {sans_id(faits_avant)}").fetchall()
        apres_d = {descripteur(f, t, v) for f, _, t, v in con.execute(
            f"SELECT fiche, section, type_fait, valeur FROM read_parquet('{faits_apres}') "
            f"WHERE {sans_id(faits_apres)}").fetchall()}
        perdus += [p for p in sans_a if descripteur(p[0], p[2], p[3]) not in apres_d]
        # Un fait qui disparaît parce que sa source a changé ou l'a retiré est expliqué : sa
        # valeur cite l'identifiant d'un fichier source modifié ou retiré cette nuit.
        self.fiches_retirees_cette_nuit = {p[0]: fiches_retirees[p[0]] for p in perdus
                                           if p[0] in fiches_retirees}
        non_expliques = [p for p in perdus
                         if p[2] not in DECOMPTES_VERIFIES_UN_PAR_UN
                         and p[0] not in fiches_retirees
                         and not (uids_changes_a_la_source and _touche(p[3], uids_changes_a_la_source))]
        if non_expliques:
            self._signaler("C1", "Faits publiés perdus sans explication",
                           [f"{p[0]} / {p[1]} / {p[2]}: {p[3][:120]}" for p in non_expliques])
        # C6 : une section qui tombe à zéro ou baisse fortement d'un coup.
        avant = dict(((f, s), n) for f, s, n in con.execute(
            f"SELECT fiche, section, count(*) FROM read_parquet('{faits_avant}') GROUP BY 1, 2").fetchall())
        apres = dict(((f, s), n) for f, s, n in con.execute(
            f"SELECT fiche, section, count(*) FROM read_parquet('{faits_apres}') GROUP BY 1, 2").fetchall())
        chutes = [f"{f}/{s}: {n} → {apres.get((f, s), 0)}" for (f, s), n in avant.items()
                  if n >= 10 and apres.get((f, s), 0) < n * (1 - seuil_effondrement)
                  and f not in fiches_retirees]
        if chutes:
            self._signaler("C6", "Effondrement d'une section", chutes)
        con.close()

    # -- préparation : faits publiés et tables communes à C3, C7 et aux avertissements --------
    def preparer(self, con, faits_publies: str, fiches: set[str], manifeste_fiches: list | None = None):
        self.con, self.fiches = con, set(fiches)
        self.manifeste_fiches = manifeste_fiches or []
        # Vue sur le fichier, pas une copie en mémoire : 600 000 faits avec leur valeur JSON.
        con.execute(f"CREATE OR REPLACE TEMP VIEW _ctl_fp AS SELECT * FROM read_parquet('{faits_publies}')")
        con.execute("CREATE OR REPLACE TEMP TABLE _ctl_fiches (fiche VARCHAR)")
        if fiches:
            con.executemany("INSERT INTO _ctl_fiches VALUES (?)", [[f] for f in sorted(fiches)])
        vues = {r[0] for r in con.execute("SELECT view_name FROM duckdb_views()").fetchall()}
        vues |= {r[0] for r in con.execute("SELECT table_name FROM duckdb_tables()").fetchall()}
        self._vues = vues
        # Appartenances aux groupes affichés des lignées publiées ; organes de ces groupes.
        if {"lignee", "lignee_maillon", "appartenance"} <= vues:
            con.execute("""CREATE OR REPLACE TEMP TABLE _ctl_lm AS
                WITH o AS (SELECT lm.legislature, unnest(lm.organes) AS organe
                           FROM lignee_maillon lm JOIN lignee l USING (lignee) WHERE l.publiee AND lm.affiche)
                SELECT o.legislature, o.organe, a.acteur, a.debut, coalesce(a.fin, '9999-12-31') AS fin
                FROM o JOIN appartenance a ON a.groupe = o.organe""")
        else:
            con.execute("""CREATE OR REPLACE TEMP TABLE _ctl_lm (legislature INTEGER, organe VARCHAR,
                           acteur VARCHAR, debut VARCHAR, fin VARCHAR)""")
        con.execute("CREATE OR REPLACE TEMP TABLE _ctl_cand (acteur VARCHAR)")
        if "candidat" in vues:
            con.execute("""INSERT INTO _ctl_cand SELECT DISTINCT c.acteur FROM candidat c
                           JOIN _ctl_fiches f ON f.fiche = 'candidat/' || c.adresse
                           WHERE c.acteur IS NOT NULL""")
        con.execute("CREATE OR REPLACE TEMP TABLE _ctl_gouv (organe VARCHAR)")
        if "gouvernement" in vues:
            con.execute("""INSERT INTO _ctl_gouv SELECT g.organe FROM gouvernement g
                           JOIN _ctl_fiches f ON f.fiche = 'gouvernement/' || g.adresse""")

    def _a(self, *tables) -> bool:
        return set(tables) <= self._vues

    def _x(self, sql, params=None):
        return self.con.execute(sql, params or []).fetchall()

    # -- C3 : données laissées de côté ----------------------------------------------------
    def c3_laisses_de_cote(self) -> list[dict]:
        """Bilan par famille : objets lus = servis + écartés avec une raison. Un objet sans raison
        d'être écarté (« attendu ») et absent des faits publiés bloque la publication."""
        membre = ("EXISTS (SELECT 1 FROM _ctl_lm m WHERE m.acteur = x.acteur "
                  "AND x.date_ref BETWEEN m.debut AND m.fin)")
        legs = [int(f.split("/")[1]) for f in self.fiches if f.startswith("legislature/")]
        legs_sql = ", ".join(map(str, legs)) or "NULL"
        # Paragraphe publié sans texte (interruption notée sans paroles) : rien à servir.
        sans_texte = ("""WHEN NOT EXISTS (SELECT 1 FROM an_comptes_rendus__intervention i
                                          WHERE i.compte_rendu = x.compte_rendu AND i.id_syceron = x.id_syceron
                                            AND coalesce(i.texte, '') <> '') THEN 'paragraphe_sans_texte'"""
                      if self._a("an_comptes_rendus__intervention") else "")
        familles = [
            ("scrutins", ("an_scrutins__scrutin", "an_scrutins__decompte_groupe"),
             """SELECT DISTINCT uid AS id FROM an_scrutins__scrutin""",
             """CASE WHEN x.id LIKE 'VTCG%' THEN 'congres'
                     WHEN NOT EXISTS (SELECT 1 FROM an_scrutins__decompte_groupe d
                                      WHERE d.scrutin = x.id AND d.organe IN (SELECT organe FROM _ctl_lm))
                          THEN 'aucun_decompte_d_un_groupe_avec_fiche' END""",
             "SELECT DISTINCT id_scrutin FROM _ctl_fp"),
            ("amendements", ("amendement_canonique",),
             "SELECT amendement AS id, acteur, date_depot AS date_ref FROM amendement_canonique",
             f"""CASE WHEN x.acteur IN (SELECT acteur FROM _ctl_cand) THEN NULL
                      WHEN NOT {membre} THEN 'auteur_hors_groupe_a_la_date' END""",
             "SELECT DISTINCT id_amendement FROM _ctl_fp"),
            ("prises_de_parole", ("intervention_attribuee",),
             """SELECT compte_rendu || '#' || id_syceron AS id, acteur, date AS date_ref, compte_rendu,
                       id_syceron FROM intervention_attribuee""",
             f"""CASE WHEN x.acteur IS NULL THEN 'orateur_non_attribue'
                      {sans_texte}
                      WHEN x.acteur IN (SELECT acteur FROM _ctl_cand) THEN NULL
                      WHEN {"EXISTS (SELECT 1 FROM parole_gouvernement p WHERE p.compte_rendu = x.compte_rendu AND p.id_syceron = x.id_syceron AND p.gouvernement IN (SELECT organe FROM _ctl_gouv))" if self._a("parole_gouvernement") else "false"} THEN NULL
                      WHEN NOT {membre} THEN 'orateur_hors_groupe_a_la_date' END""",
             """SELECT DISTINCT id_compte_rendu || '#' || id_autre FROM _ctl_fp
                WHERE id_compte_rendu IS NOT NULL AND id_autre IS NOT NULL"""),
            ("actes_jo", ("acte_rattache",),
             "SELECT acte AS id, gouvernement, dans_periode_couverte FROM acte_rattache",
             """CASE WHEN x.gouvernement IS NULL THEN 'sans_gouvernement_a_la_date'
                     WHEN x.gouvernement NOT IN (SELECT organe FROM _ctl_gouv) THEN 'gouvernement_sans_fiche'
                     WHEN NOT coalesce(x.dans_periode_couverte, false) THEN 'hors_periode_couverte' END""",
             "SELECT DISTINCT id_acte FROM _ctl_fp"),
            ("dossiers", ("an_dossiers__dossier", "an_dossiers__acte"),
             "SELECT DISTINCT uid AS id, TRY_CAST(legislature AS INTEGER) AS legislature FROM an_dossiers__dossier",
             f"""CASE WHEN x.legislature IS NULL OR x.legislature NOT IN ({legs_sql}) THEN 'legislature_sans_fiche'
                      WHEN x.id NOT IN (SELECT dossier FROM an_dossiers__acte WHERE type_acte = 'DepotInitiative_Type')
                           THEN 'sans_texte_depose' END""",
             "SELECT DISTINCT id_dossier FROM _ctl_fp"),
            ("questions", ("an_questions__question", "question_personne"),
             "SELECT DISTINCT uid AS id FROM an_questions__question",
             """CASE WHEN NOT EXISTS (SELECT 1 FROM question_personne q WHERE q.question = x.id
                                      AND q.acteur IN (SELECT acteur FROM _ctl_cand))
                     THEN 'auteur_sans_fiche_candidat' END""",
             "SELECT DISTINCT id_question FROM _ctl_fp"),
        ]
        bilans, fautifs = [], []
        for nom, tables, lus, raison, servis in familles:
            if not self._a(*tables):
                bilans.append({"famille": nom, "statut": "non_evalue", "tables_absentes":
                               sorted(set(tables) - self._vues)})
                continue
            self._x(f"""CREATE OR REPLACE TEMP TABLE _ctl_c3 AS
                SELECT x.id, {raison} AS raison, coalesce(x.id IN ({servis}), false) AS servi FROM ({lus}) x""")
            n, sv = self._x("SELECT count(*), count(*) FILTER (servi) FROM _ctl_c3")[0]
            ec = dict(self._x("""SELECT raison, count(*) FROM _ctl_c3 WHERE NOT servi AND raison IS NOT NULL
                                 GROUP BY 1 ORDER BY 1"""))
            nx = [r[0] for r in self._x("SELECT id FROM _ctl_c3 WHERE NOT servi AND raison IS NULL ORDER BY id")]
            bilans.append({"famille": nom, "statut": "evalue", "lus": n, "servis": sv, "ecartes": ec,
                           "non_expliques": len(nx), "exemples": nx[:10]})
            fautifs += [f"{nom}: {i}" for i in nx]
        self._x("DROP TABLE IF EXISTS _ctl_c3")
        if fautifs:
            self._signaler("C3", "Données laissées de côté sans raison", fautifs,
                           detail={b["famille"]: b.get("non_expliques") for b in bilans})
        self.bilan_c3 = bilans
        return bilans

    # -- C7 : personne attendue écartée en silence -----------------------------------------
    def c7_personnes(self):
        if not self._a("population"):
            return
        nom = ("(SELECT any_value(c.nom) FROM candidat c WHERE c.per = p.per)" if self._a("candidat") else "NULL")
        manquants = self._x(f"""
            SELECT p.population, coalesce(p.per, p.acteur) || coalesce(' ' || {nom}, ''),
                   coalesce(p.fiche_attendue, '(aucune adresse)'), p.detail
            FROM population p
            WHERE p.raison_sortie IS NULL AND p.population <> 'depute_ni'
              -- Sans adresse, la fiche attendue est vide : la personne est absente (jamais « inconnu »).
              AND NOT coalesce(CASE WHEN p.population = 'candidat'
                            THEN p.fiche_attendue IN (SELECT fiche FROM _ctl_fiches)
                            ELSE EXISTS (SELECT 1 FROM _ctl_fp f WHERE f.fiche = p.fiche_attendue
                                         AND f.section = p.section_attendue AND f.id_acteur = p.acteur) END, false)
            ORDER BY 1, 2""")
        if manquants:
            self._signaler("C7", "Personnes attendues absentes, sans raison établie",
                           [f"{pop} {qui} → {fiche}" + (f" ({d})" if d else "") for pop, qui, fiche, d in manquants])

    # -- avertissements ---------------------------------------------------------------------
    def _avertir(self, code, titre, objets, detail=None):
        if objets:
            self._signaler(code, titre, objets, bloquant=False, detail=detail)

    def a1_hors_modele(self, decisions: list[dict]):
        self._avertir("A1", "Fiches hors modèle (décision)",
                      [f"{d.get('objet') or d.get('fiche')} : {d.get('motif')} ({d.get('fichier')})" for d in decisions])

    def a2_verification_croisee(self, generation: int, recuperer, nb_scrutins=20):
        from .verification import verifier
        if not self._a("an_scrutins__scrutin", "an_scrutins__position_vote"):
            return None
        r = verifier(self.con, generation, recuperer, nb_scrutins)
        self.bilan_a2 = {k: (v if not isinstance(v, list) else len(v)) for k, v in r.items()}
        self._avertir("A2", "Écarts avec les pages publiques de l'Assemblée", r["ecarts"],
                      detail=self.bilan_a2)
        if r["faits"] and len(r["non_verifies"]) == r["faits"]:
            self._avertir("A2", "Vérification croisée impossible : aucune page lue", r["non_verifies"][:5],
                          detail=self.bilan_a2)
        return r

    # Fenêtre d'une transition (A3) : entrées et sorties du groupe à moins de tant de jours du scrutin.
    A3_FENETRE_TRANSITION = 7

    def a3_totaux(self):
        """Effectif de chaque groupe à chaque scrutin (nos appartenances à la date) contre le
        nombre de membres publié par le scrutin ; lois promulguées sans dossier rattaché.

        Un écart d'effectif est **expliqué**, et seulement compté dans le détail (décision de la
        propriétaire du 13/11/2026, issue #9), quand :
        - `organe_hors_dates` : l'Assemblée rattache le décompte à un organe de groupe hors de ses
          dates (groupe socialiste de la XVIe : ancien organe clos le 18/10/2023, employé jusqu'au
          14/03/2024) ;
        - `transition` : au moins autant de membres sont entrés dans le groupe ou en sont sortis
          à moins de `A3_FENETRE_TRANSITION` jours du scrutin que l'écart en compte (remplacement des
          ministres par leurs suppléants, création d'un groupe : les deux sources ne datent pas le
          changement du même jour).
        Seuls les écarts inexpliqués sont nommés. Mesuré sur la génération 10 : 2 187 écarts sur
        193 821 décomptes, 1 592 de transition, 595 hors dates, aucun inexpliqué."""
        objets = []
        if self._a("an_scrutins__decompte_groupe", "an_scrutins__scrutin"):
            dates_groupe = ("(SELECT organe, debut, coalesce(fin, '9999-12-31') AS fin FROM groupe)"
                            if self._a("groupe") else
                            "(SELECT NULL::VARCHAR AS organe, NULL::VARCHAR AS debut, NULL::VARCHAR AS fin)")
            k = int(self.A3_FENETRE_TRANSITION)
            ecarts = self._x(f"""
                WITH d AS (SELECT d.scrutin, d.organe, any_value(d.nombre_membres) AS publie,
                                  any_value(s.date) AS date
                           FROM an_scrutins__decompte_groupe d JOIN an_scrutins__scrutin s ON s.uid = d.scrutin
                           WHERE d.organe IN (SELECT organe FROM _ctl_lm) GROUP BY 1, 2),
                c AS (SELECT d.scrutin, d.organe, d.publie, d.date,
                             (SELECT count(DISTINCT m.acteur) FROM _ctl_lm m WHERE m.organe = d.organe
                               AND d.date BETWEEN m.debut AND m.fin) AS nous
                      FROM d)
                SELECT c.scrutin, c.organe, c.publie, c.nous,
                       CASE WHEN c.publie IS NULL OR c.publie = c.nous THEN NULL
                            WHEN EXISTS (SELECT 1 FROM {dates_groupe} g WHERE g.organe = c.organe
                                         AND (c.date < g.debut OR c.date > g.fin)) THEN 'organe_hors_dates'
                            WHEN (SELECT count(*) FROM _ctl_lm m WHERE m.organe = c.organe
                                  AND (abs(datediff('day', TRY_CAST(m.debut AS DATE), TRY_CAST(c.date AS DATE))) <= {k}
                                       OR (m.fin <> '9999-12-31'
                                           AND abs(datediff('day', TRY_CAST(m.fin AS DATE), TRY_CAST(c.date AS DATE))) <= {k})))
                                 >= abs(c.publie - c.nous) THEN 'transition'
                            ELSE 'inexplique' END AS explication
                FROM c""")
            diff = [e for e in ecarts if e[4] is not None]
            if diff:
                par = {x: sum(1 for e in diff if e[4] == x) for x in ("transition", "organe_hors_dates", "inexplique")}
                self.bilan_a3 = {"decomptes_compares": len(ecarts), "ecarts": len(diff),
                                 "expliques_transition": par["transition"],
                                 "expliques_organe_hors_dates": par["organe_hors_dates"],
                                 "inexpliques": par["inexplique"]}
                objets += [f"{s} {o} : publié {p}, nos appartenances {n}"
                           for s, o, p, n, x in sorted(diff) if x == "inexplique"]
        if self._a("loi"):
            objets += [f"loi {n} ({d}) sans dossier rattaché" for n, d in self._x(
                "SELECT numero_loi, date_promulgation FROM loi WHERE dossier IS NULL AND legislature = 17 ORDER BY 1")]
        self._avertir("A3", "Totaux différents d'une autre source", objets,
                      detail=getattr(self, "bilan_a3", None))

    def a4_double_affichage(self):
        objets = [f"{f} / {s} : {n} lignes identiques" for f, s, n in self._x("""
            SELECT fiche, section, count(*) - count(DISTINCT hash(valeur)) FROM _ctl_fp GROUP BY 1, 2
            HAVING count(*) > count(DISTINCT hash(valeur)) ORDER BY 1, 2""")]
        if self._a("amendement_canonique"):
            objets += [f"amendement {a} servi alors qu'il est une copie de {c}" for a, c in self._x("""
                SELECT DISTINCT f.id_amendement, a.amendement FROM _ctl_fp f
                JOIN (SELECT amendement, unnest(alias) AS copie FROM amendement_canonique WHERE alias IS NOT NULL) a
                  ON a.copie = f.id_amendement AND a.copie <> a.amendement ORDER BY 1""")]
        self._avertir("A4", "Même objet affiché deux fois", objets)

    def a5_famille_a_zero(self):
        import re as _re
        par: dict[tuple, list] = {}
        for f in self.manifeste_fiches:
            for nom, info in (f.get("sections") or {}).items():
                base = _re.sub(r"-\d{4}(-s\d)?(-\d+)?$|-\d{3}$", "", nom)
                par.setdefault((f["type"], base), []).append(info.get("lignes"))
        objets = [f"{t} / {b} : vide sur les {len(v)} fiches" for (t, b), v in sorted(par.items())
                  if len(v) >= 2 and all(x == 0 for x in v)]
        self._avertir("A5", "Section vide pour toutes les fiches d'un type", objets)

    def a6_couverture(self):
        objets = []
        if self._a("population"):
            objets += [f"candidat {q} sans fiche : {r}" for q, r in self._x("""
                SELECT coalesce(per, acteur), raison_sortie FROM population
                WHERE population = 'candidat' AND raison_sortie IS NOT NULL ORDER BY 1""")]
        if self._a("parole_personne"):
            from .perimetre import LEGISLATURES_PAROLES, nom_legislature
            bornes = dict((n, (d, f)) for n, d, f in self._x("SELECT numero, debut, fin FROM legislature")) \
                if self._a("legislature") else {}
            for leg in LEGISLATURES_PAROLES:
                d0, d1 = bornes.get(leg, (None, None))
                n, tot = self._x("""
                    WITH m AS (SELECT DISTINCT acteur FROM _ctl_lm WHERE legislature = ?)
                    SELECT count(*) FILTER (NOT EXISTS (
                               SELECT 1 FROM _ctl_fp f WHERE f.id_acteur = m.acteur
                               AND f.section LIKE 'paroles-textes%'
                               AND (f.date IS NULL OR f.date BETWEEN coalesce(?, '0000') AND coalesce(?, '9999')))),
                           count(*) FROM m""", [leg, d0, d1])[0]
                if n:
                    # Un décompte, jamais une liste de noms : ce serait un indice individuel.
                    objets.append(f"{n} membres de groupes de la {nom_legislature(leg)} sur {tot} "
                                  "sans prise de parole servie pendant cette législature")
        self._avertir("A6", "Couverture insuffisante", objets)

    def a7_non_resolues(self, decisions: dict):
        objets = []
        for t, col_a, col_b in (("filiation", "maillon_avant", "maillon_apres"),
                                ("continuite_groupe", "organe_avant", "organe_apres")):
            if self._a(t):
                objets += [f"{t} à trancher : {a} → {b}" for a, b in self._x(
                    f"SELECT {col_a}, {col_b} FROM {t} WHERE verdict = 'a_trancher' ORDER BY 1, 2")]
                paires = {(a, b) for a, b in self._x(f"SELECT {col_a}, {col_b} FROM {t}")}
                objets += [f"décision {d.get('fichier')} sans objet : {d.get('avant')} → {d.get('apres')}"
                           for d in decisions.get(t, []) if (d.get("avant"), d.get("apres")) not in paires]
        # Bornage d'un mandat (Q23) : sans objet si la source a fermé le mandat, ou ne le publie plus.
        bornes = decisions.get("borne_mandat", [])
        if bornes and self._a("an_acteurs__mandat__source"):
            ouverts = {m for (m,) in self._x(
                "SELECT uid FROM an_acteurs__mandat__source WHERE date_fin IS NULL AND uid IN (SELECT unnest(?::VARCHAR[]))",
                [[d.get("mandat") for d in bornes]])}
            objets += [f"décision {d.get('fichier')} sans objet : le mandat {d.get('mandat')} n'est plus ouvert à la source"
                       for d in bornes if d.get("mandat") not in ouverts]
        if self._a("population"):
            pers = {r[0] for r in self._x("SELECT DISTINCT coalesce(per, '') FROM population")} | \
                   {r[0] for r in self._x("SELECT DISTINCT coalesce(acteur, '') FROM population")}
            objets += [f"décision {d.get('fichier')} sans objet : {d.get('personne')}"
                       for d in decisions.get("perimetre", []) if d.get("personne") not in pers]
        empreintes = {a["empreinte"] for a in self.anomalies}
        objets += [f"levée {l.get('fichier')} sans objet cette nuit : {e}" for e, l in sorted(self.levees.items())
                   if e not in empreintes]
        if self._a("legislature"):
            objets += [f"législature {n} en cours sans fiche" for (n,) in self._x(
                "SELECT numero FROM legislature WHERE fin IS NULL ORDER BY 1")
                if f"legislature/{n}" not in self.fiches]
        if self._a("conclusion_non_classee"):
            # Codes de conclusion non classés (R-ETAPE) : le sort de ces dossiers reste « non connu »
            # au lieu d'être deviné ; la liste dit lesquels (issue #45).
            objets += [f"conclusion {c} (« {l} ») non classée : {n} décisions, {d} dossiers "
                       f"({k} dont c'est la dernière décision), dont {', '.join(ex)}"
                       for c, l, n, d, ex, k in self._x(
                           "SELECT conclusion_code, conclusion_libelle, decisions, dossiers, exemples, "
                           "dossiers_dont_c_est_la_derniere_decision FROM conclusion_non_classee ORDER BY 1")]
        self._avertir("A7", "Entrées non résolues", objets)

    def a9_liste_des_candidats(self):
        """Écarts entre la liste des candidats (décision) et Wikipédia, et fiches de candidat
        retirées cette nuit : des noms de candidats et des statuts, jamais un indice."""
        objets = []
        if self._a("candidature_ecart_wikipedia"):
            libelle = {"declare_par_wikipedia_absent_de_la_liste":
                           "déclaré selon Wikipédia, absent de la liste en vigueur",
                       "declare_selon_wikipedia_retire_dans_la_liste":
                           "déclaré selon Wikipédia, retiré dans la liste en vigueur",
                       "retire_selon_wikipedia_declare_dans_la_liste":
                           "retiré selon Wikipédia, déclaré dans la liste en vigueur"}
            objets += [f"{nom}" + (f" ([[{art}]])" if art else "") + f" : {libelle.get(e, e)}"
                       for e, nom, art in self._x("""SELECT ecart, nom, article_frwiki
                                                     FROM candidature_ecart_wikipedia ORDER BY 1, 2""")]
        objets += [f"fiche {f} retirée cette nuit : {r}"
                   for f, r in sorted(getattr(self, "fiches_retirees_cette_nuit", {}).items())]
        self._avertir("A9", "Liste des candidats : écarts avec Wikipédia et fiches retirées", objets,
                      detail="La liste des candidats est une décision (`decisions/candidature/`), "
                             "recopiée de franceinfo ; Wikipédia ne sert qu'à signaler un écart. "
                             "Un écart se règle par une nouvelle décision, jamais d'office.")

    def a8_mandats_ouverts(self):
        if self._a("mandat_ouvert_organe_clos"):
            self._avertir("A8", "Mandats ouverts dans un organe clos", [
                f"{m} ({a}) dans {o}, clos le {f}" for m, a, o, f in self._x(
                    "SELECT mandat, acteur, organe, organe_fin FROM mandat_ouvert_organe_clos ORDER BY organe, mandat")])

    def bilan(self) -> dict:
        bloquantes = [a for a in self.anomalies if a["bloquant"]]
        return {"publication_autorisee": not bloquantes, "anomalies": self.anomalies,
                "bloquantes": [a["empreinte"] for a in bloquantes],
                "avertissements": [a["empreinte"] for a in self.anomalies if a["controle"].startswith("A")],
                "c3": getattr(self, "bilan_c3", None), "a2": getattr(self, "bilan_a2", None)}


def _touche(valeur_json: str, uids: set[str]) -> bool:
    return any(u in valeur_json for u in uids)


def _cles(obj, prefixe=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from _cles(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _cles(v)
    if isinstance(obj, dict) and isinstance(obj.get("colonnes"), list):
        yield from obj["colonnes"]


def _liens(obj):
    """Les liens vers d'autres fiches s'écrivent {"lien": "legislature/17"} dans les fichiers servis."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "lien" and isinstance(v, str):
                yield v
            else:
                yield from _liens(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _liens(v)
    if isinstance(obj, dict) and isinstance(obj.get("colonnes"), list) and "lien" in obj["colonnes"]:
        i = obj["colonnes"].index("lien")
        for l in obj.get("lignes", []):
            if isinstance(l[i], str):
                yield l[i]
