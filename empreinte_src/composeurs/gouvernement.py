"""Composeur « gouvernement » : la fiche de chaque gouvernement de la XVIIe législature (cahier 4.4 ;
doc. 1, 1.7.2, `gouvernements/<adresse>/`).

Une fiche par gouvernement qui traverse la XVIIe (`gouvernement_legislature`, R-GOUVERNEMENTS) ;
son adresse est `gouvernement.adresse` (« lecornu-ii »). Fichiers servis :

| fichier | contenu | chargé |
| --- | --- | --- |
| `fiche.json.gz` | en-tête (nom, période, durée), en bref (frise, législatures, composition, majorité, projets de loi, 49.3, paroles, actes), limites, couverture de chaque section | tout de suite |
| `composition.json.gz` | membres par ministère, Premier ministre en tête, ministres délégués sous leur tutelle | à la demande |
| `paroles.json.gz` | sujets de parole (débats) : séances, prises de parole, membres intervenus, sans texte | à la demande |
| `paroles-textes-<nnn>.json.gz` | extraits (300 caractères) et lien du paragraphe, par paquets de sujets (≈ 300 Ko bruts) | au clic sur un sujet |
| `deposes.json.gz` | projets de loi : matière, sort, 49.3, date | à la demande |
| `procedure-49-3.json.gz` | engagements de responsabilité (fait de procédure, jamais un vote) | à la demande |
| `actes.json.gz` | actes du JO de la période couverte, comptés par ministère (tel que publié) et par nature | à la demande |
| `actes-<aaaa-mm>.json.gz`, `actes-nominatives-<aaaa-mm>.json.gz` | liste des actes d'un mois ; mesures nominatives à part | au clic |
| `actes-lois.json.gz` | lois citées dans le titre d'un acte | au clic |
| `budgets.json.gz` | vide : sources financières non collectées dans l'essai | à la demande |

Règles éditoriales appliquées ici (cahier, partie 2) : aucun score ni classement ; listes de
personnes dans un ordre neutre (protocolaire publié par la source, puis chronologique, puis
alphabétique) ; un 49.3 est un fait de procédure, servi à part ; une donnée manquante reste
`null` (un compte d'actes hors de la période couverte n'est jamais 0) ; le nombre d'actes dont
le **titre** cite une loi est servi, jamais une part d'actes qui « appliquent » une loi ; aucun
acte n'est rattaché à une personne ; chaque compte porte sa date (`au`).
"""
from __future__ import annotations

import datetime as dt
import json
import re
import unicodedata
from collections import defaultdict

from ..perimetre import LEGISLATURES, LEGISLATURES_GOUVERNEMENTS, PAROLES_DEPUIS

NOM = "gouvernement"
VERSION = 1
DEPEND = ("R-GOUVERNEMENTS", "R-LEGISLATURES", "R-COMPOSITION", "R-VAGUE", "R-APPARTENANCE",
          "R-DEPOT-GOUVERNEMENT", "R-MATIERE", "R-SORT-FINAL", "R-49-3",
          "R-PAROLES-GOUVERNEMENT", "R-RATTACHEMENT-ACTE", "R-LOI-CITEE")

LEGISLATURES_GOUV = LEGISLATURES_GOUVERNEMENTS   # gouvernements publiés (module `perimetre`)
# Fiches publiées par les composeurs de cette tranche : seules cibles possibles d'un lien (C2).
LEGISLATURES_PUBLIEES = set(LEGISLATURES)
LONGUEUR_EXTRAIT = 300
# Poids brut visé d'un fichier d'extraits : un clic sur un sujet ne charge que son paquet (≈ 60 Ko
# compressés) ; un sujet plus lourd (loi de finances) est réparti sur plusieurs paquets consécutifs.
# Un découpage par semestre (doc. 1, 1.7.2) faisait jusqu'à 0,8 Mo compressé par clic (Bayrou, 2025-S1).
PAQUET_EXTRAITS = 300_000
_ESPACES = re.compile(r"\s+")

# Points d'accès dont dépend chaque famille (contrôle C5), quand la table lue ne les dit pas.
PA_AMO, PA_DOSSIERS, PA_SYCERON, PA_JO = "an-amo30-l17", "an-dossiers-l17", "an-syceron-l17", "jo-livraisons"

ORDRE_MEMBRES = ("ministères dans l'ordre protocolaire publié par l'Assemblée (préséance), Premier "
                 "ministre en tête ; dans un ministère, le titulaire puis les portefeuilles rattachés, "
                 "par préséance, puis date de début, puis nom")


# -- outils ---------------------------------------------------------------------------------

def _lignes(ctx, sql: str, params=None) -> list[dict]:
    rel = ctx.con.execute(sql, params or [])
    noms = [d[0] for d in rel.description]
    return [dict(zip(noms, r)) for r in rel.fetchall()]


def _couv(famille, statut, detail, numerateur=None, denominateur=None, points=(), au=None, **extra):
    c = {"famille": famille, "statut": statut, "numerateur": numerateur,
         "denominateur": denominateur, "detail": detail, "points_acces": sorted(set(points))}
    if au:
        c["au"] = au
    c.update(extra)
    return c


def _avant(g, debut_lu, au) -> str:
    """Statut d'une section quand le gouvernement commence avant ce qui est lu : `partiel` s'il
    est en fonction aussi après (les chiffres portent sur la partie lue, le détail la dit),
    `hors_perimetre` s'il a fini avant."""
    return "hors_perimetre" if (g["fin"] or au) < debut_lu else "partiel"


def _compte(n, statut):
    """Un compte nul n'est servi que si la lecture est complète (cahier, règle 5 ; C5)."""
    return None if n == 0 and statut not in ("complet", "relu_aucun") else n


def _jours(debut: str, fin: str) -> int:
    return (dt.date.fromisoformat(fin) - dt.date.fromisoformat(debut)).days + 1


def _fr(d: str | None) -> str | None:
    return None if not d else f"{d[8:10]}/{d[5:7]}/{d[0:4]}"


def _sans_accents(x: str) -> str:
    """Clé de tri alphabétique : casse et accents ignorés."""
    return "".join(c for c in unicodedata.normalize("NFD", x.strip().lower())
                   if unicodedata.category(c) != "Mn")


def _vue(ctx, nom) -> bool:
    return ctx.existe(nom)


def _points(ctx, table, defaut) -> list[str]:
    if not _vue(ctx, table):
        return [defaut]
    pts = [r[0] for r in ctx.x(f"SELECT DISTINCT prov_point FROM {table} WHERE prov_point IS NOT NULL")]
    return sorted(pts) or [defaut]


def _licence_unique(ctx, table) -> str | None:
    if not _vue(ctx, table):
        return None
    ls = [r[0] for r in ctx.x(f"SELECT DISTINCT licence FROM {table} WHERE licence IS NOT NULL")]
    return ls[0] if len(ls) == 1 else None


def _identites(ctx) -> dict[str, dict]:
    """acteur -> nom affiché et clé de tri alphabétique (archive la plus récente)."""
    if not _vue(ctx, "an_acteurs__identite_source"):
        return {}
    out = {}
    for r in _lignes(ctx, """
            SELECT uid, prenom, nom, nom_alpha FROM an_acteurs__identite_source
            QUALIFY row_number() OVER (PARTITION BY uid ORDER BY prov_point DESC) = 1"""):
        nom = " ".join(x for x in (r["prenom"], r["nom"]) if x) or None
        out[r["uid"]] = {"nom": nom, "tri": _sans_accents(f"{r['nom_alpha'] or r['nom'] or ''} {r['prenom'] or ''}")}
    return out


# -- composer -------------------------------------------------------------------------------

def composer(ctx, ecr):
    au = ctx.date_reference or dt.date.today().isoformat()
    gouvs = _lignes(ctx, """
        SELECT organe, nom, adresse, debut, fin, en_cours, rang, source_url FROM gouvernement
        ORDER BY debut""")
    publies = {r[0] for r in ctx.x(
        "SELECT DISTINCT gouvernement FROM gouvernement_legislature WHERE legislature IN "
        "(SELECT unnest(?::INTEGER[]))", [list(LEGISLATURES_GOUV)])}
    adresses = {g["organe"]: g["adresse"] for g in gouvs if g["organe"] in publies}
    noms = _identites(ctx)
    commun = {"au": au, "noms": noms, "adresses": adresses, "gouvs": gouvs,
              "pa_amo": _points(ctx, "an_acteurs__mandat", PA_AMO),
              "lic_amo": _licence_unique(ctx, "an_acteurs__mandat")}
    for i, g in enumerate(gouvs):
        if g["organe"] not in publies:
            continue
        precedent = gouvs[i - 1] if i > 0 else None
        suivant = gouvs[i + 1] if i + 1 < len(gouvs) else None
        _composer_un(ctx, ecr, g, precedent, suivant, commun)


def _voisin(g, adresses):
    if g is None:
        return None
    v = {"organe": g["organe"], "nom": g["nom"], "debut": g["debut"], "fin": g["fin"]}
    if g["organe"] in adresses:
        v["lien"] = f"gouvernement/{adresses[g['organe']]}"
    return v


def _composer_un(ctx, ecr, g, precedent, suivant, commun):
    au, org = commun["au"], g["organe"]
    fin_effective = g["fin"] or au
    f = ecr.fiche("gouvernement", g["adresse"], titre=f"Gouvernement {g['nom']}")
    limites: list[dict] = []

    legislatures = []
    for r in _lignes(ctx, """SELECT legislature, debut, fin FROM gouvernement_legislature
                             WHERE gouvernement = ? ORDER BY debut""", [org]):
        x = {"numero": r["legislature"], "debut": r["debut"], "fin": r["fin"]}
        if r["legislature"] in LEGISLATURES_PUBLIEES:
            x["lien"] = f"legislature/{r['legislature']}"
        legislatures.append(x)
    # Début de ce qui est lu (cahier 4.1) : dossiers depuis la XIVe, comptes rendus depuis la XVe.
    debuts = dict(ctx.x("SELECT numero, debut FROM legislature")) if _vue(ctx, "legislature") else {}
    debut_dossiers = debuts.get(min(LEGISLATURES)) or g["debut"]
    debut_paroles = debuts.get(PAROLES_DEPUIS) or g["debut"]

    composition = _composition(ctx, f, g, commun, limites)
    paroles = _paroles(ctx, f, g, commun, composition["nb_membres"], debut_paroles, limites)
    projets, e493 = _deposes(ctx, f, g, commun, debut_dossiers)
    actes = _actes(ctx, f, g, commun)
    _budgets(f)

    majorite = _majorite(ctx, g, fin_effective, commun)
    if majorite["nb_groupes_declarant"] == 0:
        limites.append({"famille": "majorite", "statut": "relu_aucun",
                        "detail": "Aucun groupe de l'Assemblée ne déclare sa position (majoritaire, "
                                  "minoritaire, opposition) sur cette période : la majorité est « non "
                                  "déclarée ». Elle n'est jamais déduite des votes ni des nominations.",
                        "au": au})

    f.entete({
        "gouvernement": {
            "organe": org, "nom": g["nom"], "adresse": g["adresse"],
            "debut": g["debut"], "fin": g["fin"], "en_cours": bool(g["en_cours"]),
            "duree_jours": _jours(g["debut"], fin_effective),
            "duree_au": fin_effective,
            "source": {"point_acces": commun["pa_amo"], "uid": org, "url": g["source_url"]},
        },
        "en_bref": {
            "frise": {"precedent": _voisin(precedent, commun["adresses"]),
                      "suivant": _voisin(suivant, commun["adresses"])},
            "legislatures": legislatures,
            "composition": composition["entete"],
            "majorite": majorite,
            "projets_de_loi": projets,
            "procedure_49_3": e493,
            "paroles": paroles,
            "actes": actes,
        },
        "limites": limites,
        "regles": list(DEPEND),
    })


# -- qui le composait -----------------------------------------------------------------------

def _composition(ctx, f, g, commun, limites):
    org, au = g["organe"], commun["au"]
    fin_effective = g["fin"] or au
    licence = commun["lic_amo"]
    lignes = _lignes(ctx, """
        SELECT acteur, portefeuille, qualite, ministere, ministere_tutelle, tutelle_statut,
               raison_tutelle, debut, fin, premier_ministre, preseance, mandat, source_url
        FROM membre_gouvernement WHERE gouvernement = ?""", [org])
    par_ministere = defaultdict(list)
    for r in lignes:
        par_ministere[r["ministere"]].append(r)

    def racine(r, vus=()):
        """Ministère de plein exercice auquel le portefeuille se rattache (tutelle de tutelle suivie)."""
        if r["tutelle_statut"] in ("etabli", "decision") and r["ministere_tutelle"]:
            t = r["ministere_tutelle"]
            if t in vus:
                return t
            titulaires = par_ministere.get(t)
            return racine(titulaires[0], vus + (t,)) if titulaires else t
        if r["tutelle_statut"] == "sans_objet":
            return r["ministere"]
        return None

    def libelle(m):
        rs = par_ministere.get(m) or []
        return rs[0]["portefeuille"] if rs else None

    # Un ministère recréé sous le même libellé (remaniement : nouvel organe) reste un seul groupe.
    def cle_libelle(m):
        return None if m is None else _sans_accents(_ESPACES.sub(" ", (libelle(m) or m).replace("’", "'")))

    groupes = defaultdict(list)
    for r in lignes:
        r["_racine"] = racine(r)
        groupes[cle_libelle(r["_racine"])].append(r)

    def cle_groupe(k):
        rs = [r for r in groupes[k] if r["ministere"] == r["_racine"]] or groupes[k]
        pm = any(r["premier_ministre"] for r in rs)
        prec = min((r["preseance"] for r in rs if r["preseance"] is not None), default=10 ** 6)
        return (k is None, not pm, prec, min(r["debut"] or "" for r in rs), k or "")

    def tri_nom(a):
        return commun["noms"].get(a, {}).get("tri") or a

    sortie = []
    for k in sorted(groupes, key=cle_groupe):
        rs = sorted(groupes[k], key=lambda r: (
            k is not None and r["ministere"] != r["_racine"],
            r["preseance"] if r["preseance"] is not None else 10 ** 6,
            r["debut"] or "", tri_nom(r["acteur"]), r["mandat"]))
        for r in rs:
            m = r["_racine"]
            sortie.append({
                "ministere_groupe": m, "ministere_groupe_libelle": libelle(m) if m else None,
                "rattachement": ("non_etabli" if m is None else
                                 "titulaire" if r["ministere"] == m else "rattache"),
                "acteur": r["acteur"], "nom": commun["noms"].get(r["acteur"], {}).get("nom"),
                "portefeuille": r["portefeuille"], "qualite": r["qualite"],
                "ministere": r["ministere"], "premier_ministre": bool(r["premier_ministre"]),
                "ministere_tutelle": r["ministere_tutelle"],
                "ministere_tutelle_libelle": libelle(r["ministere_tutelle"]) if r["ministere_tutelle"] else None,
                "tutelle_statut": r["tutelle_statut"],
                "raison_tutelle": r["raison_tutelle"],
                "debut": r["debut"], "fin": r["fin"], "preseance": r["preseance"],
                "mandat": r["mandat"], "source_url": r["source_url"],
                "source_point": commun["pa_amo"][0], "licence": licence})

    a_ratt = [r for r in lignes if r["tutelle_statut"] != "sans_objet"]
    ratt = [r for r in a_ratt if r["tutelle_statut"] in ("etabli", "decision")]
    ouverts = []
    if _vue(ctx, "mandat_ouvert_organe_clos"):
        ouverts = [r[0] for r in ctx.x("""SELECT mandat FROM mandat_ouvert_organe_clos
                                           WHERE organe = ? ORDER BY mandat""", [org])]
    detail = (f"Composition lue dans les mandats « ministère » publiés par l'Assemblée. "
              f"{len(ratt)} portefeuilles sur {len(a_ratt)} à rattacher sont rattachés à leur ministère "
              f"de tutelle ; les autres sont dits « rattachement non établi » (le libellé ne désigne pas "
              f"un seul ministre du gouvernement en fonction à la même date).")
    if ouverts:
        detail += (f" {len(ouverts)} mandats « membre du gouvernement » restés ouverts alors que le "
                   f"gouvernement est clos, sans portefeuille, n'entrent pas dans la composition (signalés).")
        limites.append({"famille": "composition", "statut": "trou_source",
                        "detail": f"{len(ouverts)} mandats de membre du gouvernement sans date de fin "
                                  f"dans un gouvernement clos (source de l'Assemblée) : hors composition, "
                                  f"en attente de décision.", "mandats": ouverts, "au": au})
    couverture = _couv("composition", "complet", detail, len(ratt), len(a_ratt),
                       commun["pa_amo"], au=au)
    f.section("composition", sortie, type_fait="membre_gouvernement",
              ids={"acteur": "acteur", "mandat": "mandat", "organe": "ministere"},
              date="debut", couverture=couverture,
              colonnes=list(sortie[0].keys()) if sortie else None,
              extra={"ordre": ORDRE_MEMBRES})

    vagues = [{k: v for k, v in x.items() if k not in ("regle", "gouvernement")}
              for x in _lignes(ctx, "SELECT * FROM vague WHERE gouvernement = ? ORDER BY vague", [org])] \
        if _vue(ctx, "vague") else []
    formation = [v for v in vagues if v.get("nature") == "formation"]
    # L'effectif minimal se lit après la formation : avant, le Premier ministre est souvent seul.
    fin_formation = max((v["fin"] for v in formation), default=None)
    # Effectif jour par jour (personnes distinctes en fonction), du début à la fin (ou au jour).
    effectif = {"min": None, "max": None}
    if lignes and g["debut"] <= fin_effective:
        jours = ctx.x("""
            WITH j AS (SELECT unnest(range(?::DATE, ?::DATE + 1, INTERVAL 1 DAY))::DATE AS j)
            SELECT strftime(j.j, '%Y-%m-%d'), count(DISTINCT m.acteur)
            FROM j LEFT JOIN membre_gouvernement m
              ON m.gouvernement = ? AND j.j >= m.debut::DATE
             AND j.j <= coalesce(m.fin, '9999-12-31')::DATE
            GROUP BY 1 ORDER BY 1""", [g["debut"], fin_effective, org])
        for cle, choix in (("min", min), ("max", max)):
            serie = [(d, n) for d, n in jours if cle == "max" or not fin_formation or d >= fin_formation] or jours
            v = choix(n for _, n in serie)
            periodes, cour = [], None
            for d, n in serie:
                if n == v:
                    if cour and cour["au"] == _veille(d):
                        cour["au"] = d
                    else:
                        cour = {"du": d, "au": d}
                        periodes.append(cour)
            effectif[cle] = {"valeur": v, "periodes": periodes}

    entete = {
        "nb_membres": len({r["acteur"] for r in lignes}),
        "nb_portefeuilles": len(lignes),
        "effectif_minimal": effectif["min"], "effectif_maximal": effectif["max"],
        "effectif_definition": ("personnes distinctes en fonction le même jour ; le minimum est lu à "
                                "partir de la fin de la formation"
                                + (f" ({_fr(fin_formation)})" if fin_formation else "")),
        "vagues": vagues, "nb_vagues": len(vagues) if _vue(ctx, "vague") else None,
        "vague_definition": "nominations d'un même gouvernement séparées de moins de 8 jours",
        "remaniements": (sum(1 for v in vagues if v.get("nature") == "remaniement")
                         if vagues and all(v.get("nature") for v in vagues) else None),
        "remaniements_definition": ("vague, après la formation, où au moins un membre quitte le "
                                    "gouvernement ou change de portefeuille ; une vague qui ne fait "
                                    "qu'ajouter des membres est un complément (décision du 07/11/2026)"),
        "tutelle": {"etablie": len(ratt), "a_rattacher": len(a_ratt)},
        "au": g["fin"] or au,
    }
    return {"entete": entete, "nb_membres": entete["nb_membres"]}


def _veille(d: str) -> str:
    return (dt.date.fromisoformat(d) - dt.timedelta(days=1)).isoformat()


# -- majorité à l'Assemblée ---------------------------------------------------------------

def _majorite(ctx, g, fin_effective, commun):
    if not _vue(ctx, "groupe"):
        return {"statut": "non_etabli", "groupes": [], "nb_groupes": None, "nb_groupes_declarant": None,
                "au": fin_effective}
    groupes = _lignes(ctx, """
        SELECT organe, legislature, sigle, libelle, debut, fin, position_declaree
        FROM groupe WHERE debut <= ? AND coalesce(fin, '9999-12-31') >= ?""", [fin_effective, g["debut"]])
    groupes.sort(key=lambda x: (_sans_accents(x["libelle"] or x["sigle"] or ""), x["organe"]))
    declarant = [x for x in groupes if x["position_declaree"] != "non_declaree"]
    par_pos = defaultdict(list)
    for x in declarant:
        par_pos[x["position_declaree"]].append(x["sigle"] or x["libelle"])
    return {
        "statut": "declaree" if declarant else "non_declaree",
        "libelle": None if declarant else "non déclarée",
        "positions_declarees": dict(par_pos),
        "groupes": groupes,
        "nb_groupes": len(groupes), "nb_groupes_declarant": len(declarant),
        "regle": "position que chaque groupe déclare à l'Assemblée sur la période du gouvernement ; "
                 "jamais déduite",
        "source": {"point_acces": commun["pa_amo"]},
        "au": fin_effective,
    }


# -- sur quoi ils ont pris la parole --------------------------------------------------------

def _paroles(ctx, f, g, commun, nb_membres, debut_lu, limites):
    org, au = g["organe"], commun["au"]
    pts = _points(ctx, "an_comptes_rendus__intervention", PA_SYCERON)
    if not _vue(ctx, "parole_gouvernement"):
        c = _couv("paroles", "en_cours", "Paroles du gouvernement non établies (règle non appliquée).",
                  points=pts, au=au)
        f.section("paroles", [], type_fait="parole_sujet", couverture=c)
        return {"nb_sujets": None, "nb_prises_de_parole": None, "nb_membres_intervenus": None,
                "nb_membres": nb_membres, "au": au}
    texte = _vue(ctx, "an_comptes_rendus__intervention")
    jointure = ("LEFT JOIN an_comptes_rendus__intervention i USING (compte_rendu, id_syceron)"
                if texte else "")
    cols_texte = ("i.texte, i.licence" if texte else "NULL::VARCHAR AS texte, NULL::VARCHAR AS licence")
    rows = _lignes(ctx, f"""
        SELECT p.acteur, p.compte_rendu, p.id_syceron, p.date, p.sujet, p.dossier, p.statut_sujet,
               p.type_sujet, p.qualite_source, p.qualite_ecrite_libelle, p.interruption,
               p.source_url, {cols_texte}
        FROM parole_gouvernement p {jointure}
        WHERE p.gouvernement = ?
        ORDER BY p.date, p.compte_rendu, TRY_CAST(p.id_syceron AS BIGINT), p.id_syceron, p.acteur""",
        [org])
    noms = commun["noms"]

    def tri_nom(a):
        return noms.get(a, {}).get("tri") or a

    # Sujets : (type, intitulé) ; un paragraphe sans intitulé publié est compté à part.
    sujets: dict[tuple, dict] = {}
    for r in rows:
        k = (r["type_sujet"], r["sujet"])
        s = sujets.setdefault(k, {"type_sujet": r["type_sujet"], "sujet": r["sujet"],
                                  "statut_sujet": r["statut_sujet"], "dossiers": set(), "seances": set(),
                                  "membres": set(), "nb": 0, "nb_inter": 0, "premiere": r["date"],
                                  "derniere": r["date"], "fichiers": set(), "source_url": r["source_url"],
                                  "licence": r["licence"]})
        if r["dossier"]:
            s["dossiers"].add(r["dossier"])
        s["seances"].add(r["compte_rendu"])
        s["membres"].add(r["acteur"])
        s["nb"] += 1
        s["nb_inter"] += bool(r["interruption"])
        s["derniere"] = max(s["derniere"], r["date"])
    ordonnes = sorted(sujets.values(), key=lambda s: (s["premiere"], (s["sujet"] or "￿").lower(),
                                                       s["type_sujet"] or ""))
    ident = {(s["type_sujet"], s["sujet"]): n for n, s in enumerate(ordonnes, 1)}

    # Extraits, par paquets de sujets consécutifs (chargés au clic sur un sujet).
    extraits = defaultdict(list)
    for r in rows:
        t = _ESPACES.sub(" ", r["texte"] or "").strip() if r["texte"] is not None else None
        extraits[ident[(r["type_sujet"], r["sujet"])]].append({
            "sujet_id": ident[(r["type_sujet"], r["sujet"])], "date": r["date"], "acteur": r["acteur"],
            "compte_rendu": r["compte_rendu"], "id_syceron": r["id_syceron"],
            "extrait": None if t is None else t[:LONGUEUR_EXTRAIT],
            "extrait_tronque": None if t is None else len(t) > LONGUEUR_EXTRAIT,
            "interruption": bool(r["interruption"]), "qualite_source": r["qualite_source"],
            "qualite_ecrite": r["qualite_ecrite_libelle"], "dossier": r["dossier"],
            "source_url": r["source_url"], "licence": r["licence"]})
    paquets, poids = [[]], 0
    for n in range(1, len(ordonnes) + 1):
        for x in extraits[n]:
            taille = len(json.dumps(x, ensure_ascii=False)) - 40      # sans les noms de colonnes
            if poids + taille > PAQUET_EXTRAITS and paquets[-1]:
                paquets.append([])
                poids = 0
            paquets[-1].append(x)
            poids += taille
            ordonnes[n - 1]["fichiers"].add(len(paquets))
    if not paquets[-1]:
        paquets.pop()

    index = []
    for n, s in enumerate(ordonnes, 1):
        index.append({
            "sujet_id": n, "sujet": s["sujet"] if s["sujet"] is not None else None,
            "sujet_libelle": s["sujet"] if s["sujet"] is not None else "Intitulé non publié",
            "type_sujet": s["type_sujet"], "statut_sujet": s["statut_sujet"],
            "dossiers": sorted(s["dossiers"]),
            "nb_seances": len(s["seances"]), "nb_prises_de_parole": s["nb"],
            "dont_interruptions": s["nb_inter"],
            "nb_membres_intervenus": len(s["membres"]),
            "membres": sorted(s["membres"], key=tri_nom),
            "premiere_date": s["premiere"], "derniere_date": s["derniere"],
            "fichiers_extraits": [f"paroles-textes-{k:03d}.json.gz" for k in sorted(s["fichiers"])],
            "source_url": s["source_url"], "licence": s["licence"]})
    intervenus = sorted({r["acteur"] for r in rows}, key=tri_nom)
    personnes = {a: noms.get(a, {}).get("nom") for a in intervenus}

    # Couverture : comptes rendus lus à partir de la XVe (cahier 4.1) ; avant, hors périmètre.
    sans_intitule = sum(1 for r in rows if r["statut_sujet"] != "etabli")
    ecrite = sum(1 for r in rows if r["qualite_source"] == "compte_rendu")
    phrase_q = (f"Prises de parole des membres pendant leur fonction, en qualité de membre du "
                f"gouvernement ({ecrite} sur {len(rows)} avec une qualité écrite par le compte rendu, "
                f"les autres déduites de la fonction à la date). Les paroles tenues en « affaires "
                f"courantes » après la fin publiée du gouvernement ne sont pas rattachées.")
    if sans_intitule:
        phrase_q += (f" {sans_intitule} prises de parole sans intitulé publié sont comptées sous "
                     f"« Intitulé non publié ».")
    if g["debut"] < debut_lu:
        couv = _couv("paroles", _avant(g, debut_lu, au),
                     f"Comptes rendus lus à partir de la XVe législature (le {_fr(debut_lu)}, cahier "
                     f"4.1) ; ceux du {_fr(g['debut'])} au {_fr(_veille(debut_lu))} sont hors du "
                     "périmètre. " + phrase_q,
                     _jours(debut_lu, g["fin"] or au), _jours(g["debut"], g["fin"] or au), pts, au=au)
    else:
        couv = _couv("paroles", "complet", phrase_q, len(intervenus), nb_membres, pts, au=au)
    f.section("paroles", index, type_fait="parole_sujet",
              ids={"autre": "sujet_id"}, date="premiere_date",
              couverture=couv, colonnes=list(index[0].keys()) if index else None,
              extra={"personnes": personnes,
                     "ordre": "sujets par date de première prise de parole ; membres par ordre alphabétique"})

    for k, ls in enumerate(paquets, 1):
        pers = {a: noms.get(a, {}).get("nom") for a in sorted({x["acteur"] for x in ls}, key=tri_nom)}
        ids_s = sorted({x["sujet_id"] for x in ls})
        c = _couv("paroles", couv["statut"], f"Extraits des sujets {ids_s[0]} à {ids_s[-1]}.",
                  len(ls), len(ls), pts)
        f.section(f"paroles-textes-{k:03d}", ls, type_fait="parole_extrait",
                  ids={"acteur": "acteur", "compte_rendu": "compte_rendu", "dossier": "dossier",
                       "autre": "id_syceron"},
                  date="date", couverture=c, colonnes=list(ls[0].keys()), extra={"personnes": pers})
    st = couv["statut"]
    return {"nb_sujets": _compte(len(index), st), "nb_prises_de_parole": _compte(len(rows), st),
            "nb_membres_intervenus": _compte(len(intervenus), st), "nb_membres": nb_membres,
            "couverture": couv["statut"], "au": au}


# -- ce qu'il a fait déposer ----------------------------------------------------------------

def _deposes(ctx, f, g, commun, debut_lu):
    org, au = g["organe"], commun["au"]
    pts = _points(ctx, "an_dossiers__dossier", PA_DOSSIERS)
    lic = _licence_unique(ctx, "an_dossiers__dossier")
    matiere = _vue(ctx, "matiere")
    etat = _vue(ctx, "etat_dossier")
    sel_m = ("m.statut AS matiere_statut, m.libelle AS matiere, m.commission AS matiere_commission"
             if matiere else "NULL AS matiere_statut, NULL AS matiere, NULL AS matiere_commission")
    sel_e = ("""e.sort, e.date_sort, e.raison_sort, e.par_49_3, e.adopte_par_49_3, e.nb_engagements_49_3,
                e.numero_loi, e.date_promulgation, e.url_loi, e.etape_atteinte,
                e.legislature AS etape_legislature""" if etat else
             """NULL AS sort, NULL AS date_sort, NULL AS raison_sort, NULL AS par_49_3,
                NULL AS adopte_par_49_3, NULL AS nb_engagements_49_3, NULL AS numero_loi,
                NULL AS date_promulgation, NULL AS url_loi, NULL AS etape_atteinte,
                NULL AS etape_legislature""")
    j_m = "LEFT JOIN matiere m USING (dossier)" if matiere else ""
    j_e = ("""LEFT JOIN (SELECT * FROM etat_dossier QUALIFY row_number() OVER (
                  PARTITION BY dossier ORDER BY legislature DESC NULLS LAST) = 1) e USING (dossier)"""
           if etat else "")
    rows = _lignes(ctx, f"""
        SELECT p.dossier, p.document, p.titre_dossier, p.date_depot, p.chambre_depot,
               p.procedure_libelle, {sel_m}, {sel_e}, p.source_url
        FROM projet_gouvernement p {j_m} {j_e}
        WHERE p.gouvernement = ? ORDER BY p.date_depot, p.dossier""", [org])
    for r in rows:
        r["ministere_porteur"] = None
        r["licence"] = lic
    n = len(rows)
    adoptes = sum(1 for r in rows if r["sort"] in ("adopte", "promulgue")) if etat else None
    promulgues = sum(1 for r in rows if r["sort"] == "promulgue") if etat else None
    par_sort = defaultdict(int)
    for r in rows:
        par_sort[r["sort"] or "non_etabli"] += 1
    phrase = ("Projets de loi reconnus au texte du premier dépôt (PRJL), rattachés au gouvernement en "
              "fonction ce jour-là. La matière est la commission saisie au fond (aide à la lecture). "
              "Le ministère porteur n'est pas encore établi (règle à venir).")
    if g["debut"] < debut_lu:
        couv = _couv("textes", _avant(g, debut_lu, au),
                     f"Dossiers législatifs lus à partir de la XIVe législature (le {_fr(debut_lu)}, "
                     f"cahier 4.1) : les projets déposés du {_fr(g['debut'])} au "
                     f"{_fr(_veille(debut_lu))} n'y figurent que s'ils ont continué ensuite. " + phrase,
                     _jours(debut_lu, g["fin"] or au), _jours(g["debut"], g["fin"] or au), pts, au=au)
    else:
        couv = _couv("textes", "complet", phrase, n, n, pts, au=au)
    cols = ["dossier", "document", "titre_dossier", "date_depot", "chambre_depot", "procedure_libelle",
            "matiere", "matiere_statut", "matiere_commission", "sort", "date_sort", "raison_sort",
            "par_49_3", "adopte_par_49_3", "nb_engagements_49_3", "numero_loi", "date_promulgation",
            "url_loi", "etape_atteinte", "etape_legislature", "ministere_porteur", "source_url", "licence"]
    f.section("deposes", rows, type_fait="projet_de_loi",
              ids={"dossier": "dossier", "document": "document"}, date="date_depot",
              couverture=couv, colonnes=cols,
              extra={"aide_a_la_lecture": ["matiere"], "ordre": "date de dépôt",
                     "note_49_3": "par_49_3 : le gouvernement a engagé sa responsabilité sur le texte "
                                  "(fait de procédure, jamais une position de vote)"})
    st = couv["statut"]
    projets = {"deposes": _compte(n, st), "adoptes": None if adoptes is None else _compte(adoptes, st),
               "promulgues": None if promulgues is None else _compte(promulgues, st),
               "adoptes_definition": "adoptés définitivement, promulgués ou non, à la date du compte",
               "par_sort": dict(sorted(par_sort.items())), "couverture": couv["statut"], "au": au}

    # 49.3 : engagements du gouvernement à sa date (sur ses textes ou sur d'autres).
    e_rows = _lignes(ctx, """
        SELECT acte, date, etape, declaration, dossier, titre_dossier, procedure_code,
               procedure_libelle, source_url
        FROM engagement_49_3 WHERE gouvernement = ? ORDER BY date, acte, dossier""", [org]) \
        if _vue(ctx, "engagement_49_3") else []
    for r in e_rows:
        r["licence"] = lic
    nb_eng = len({r["acte"] for r in e_rows})
    nb_textes = len({r["dossier"] for r in e_rows if r["procedure_code"] != "13"})
    c49 = _couv("procedure_49_3", "complet" if g["debut"] >= debut_lu else _avant(g, debut_lu, au),
                "Engagements de responsabilité (article 49, alinéa 3) lus dans les dossiers législatifs, "
                "rattachés au gouvernement en fonction à leur date. Un même engagement figure dans le "
                "dossier du texte et dans le dossier « Engagement de la responsabilité du Gouvernement ». "
                "C'est un fait de procédure, jamais une position de vote.",
                nb_eng, nb_eng, pts, au=au)
    f.section("procedure-49-3", e_rows, type_fait="engagement_49_3",
              ids={"dossier": "dossier", "acte": "acte", "document": "declaration"}, date="date",
              couverture=c49, colonnes=["acte", "date", "etape", "declaration", "dossier", "titre_dossier",
                                        "procedure_code", "procedure_libelle", "source_url", "licence"])
    e493 = {"nb_engagements": _compte(nb_eng, c49["statut"]), "nb_textes": _compte(nb_textes, c49["statut"]),
            "nature": "fait de procédure, pas un vote", "couverture": c49["statut"], "au": au}
    return projets, e493


# -- ce qu'il a fait entrer en vigueur ------------------------------------------------------

def _actes(ctx, f, g, commun):
    org, au = g["organe"], commun["au"]
    pts = _points(ctx, "jo_actes__acte_reglementaire", PA_JO)
    lic = _licence_unique(ctx, "jo_actes__acte_reglementaire")
    cj = (_lignes(ctx, "SELECT * FROM couverture_jo_gouvernement WHERE gouvernement = ?", [org]) or [None])[0] \
        if _vue(ctx, "couverture_jo_gouvernement") else None
    periode = (_lignes(ctx, "SELECT premiere_publication, derniere_publication FROM couverture_jo") or [None])[0] \
        if _vue(ctx, "couverture_jo") else None
    statut_regle = cj["statut"] if cj else None
    duree = _jours(g["debut"], g["fin"] or au)
    du, a = (cj["couvert_du"], cj["couvert_au"]) if cj else (None, None)
    jours_couverts = _jours(du, a) if du and a else 0
    if periode and periode["premiere_publication"]:
        bornes = (f"Le Journal officiel est lu du {_fr(periode['premiere_publication'])} au "
                  f"{_fr(periode['derniere_publication'])} (livraisons reçues, numéros complets).")
    else:
        bornes = "Aucune livraison complète du Journal officiel n'est lue."
    commun_phrase = (" Un acte est rattaché au gouvernement par sa date de publication et au ministère "
                     "tel que l'acte le publie (la correspondance entre libellés de ministère n'est pas "
                     "établie sans décision), jamais à une personne. Les mesures nominatives sont "
                     "comptées à part. On compte les actes dont le titre cite une loi par son numéro ; un "
                     "titre qui n'en cite pas ne veut pas dire « sans loi ».")
    if statut_regle == "complet":
        statut, detail = "complet", bornes + commun_phrase
    elif statut_regle == "partiel":
        statut = "non_collecte"
        detail = (bornes + f" Pour ce gouvernement, seuls les actes publiés du {_fr(du)} au {_fr(a)} "
                  f"sont comptés ({jours_couverts} jours sur {duree}) ; avant, ils ne sont pas "
                  f"collectés." + commun_phrase)
    else:
        statut = "non_collecte"
        detail = (bornes + " Aucun acte publié pendant ce gouvernement n'est dans la période lue : les "
                  "actes ne sont pas collectés pour lui (aucun compte n'est donné, pas même zéro).")
    couv = _couv("actes", statut, detail, jours_couverts, duree, pts, au=au,
                 etendue=statut_regle or "non_etablie", periode_couverte={"du": du, "au": a})

    if statut_regle not in ("complet", "partiel") or not _vue(ctx, "acte_rattache"):
        f.section("actes", [], type_fait="actes_compte", couverture=couv)
        f.section("actes-lois", [], type_fait="loi_citee_titre", couverture=couv)
        return {"nb_actes": None, "nb_mesures_nominatives": None, "nb_titre_cite_une_loi": None,
                "periode_couverte": None, "couverture": statut, "etendue": couv["etendue"], "au": au}

    rows = _lignes(ctx, """
        SELECT acte, id_jorf, date_publication, nature, numero, nor, titre, ministere_libelle,
               ministere_statut, ministere_normalise, mesure_nominative, cite_une_loi, nb_lois_citees,
               est_rectificatif, rectificatif_de, num_jo, source_url
        FROM acte_rattache
        WHERE gouvernement = ? AND dans_periode_couverte
        ORDER BY date_publication, acte""", [org])
    lois_par_acte = defaultdict(list)
    lois = {}
    if _vue(ctx, "acte_loi_citee"):
        for r in _lignes(ctx, """
                SELECT l.acte, l.numero_loi, l.type_loi, l.loi_jorf, l.loi_identifiee_par,
                       l.loi_source_url
                FROM acte_loi_citee l JOIN acte_rattache a USING (acte)
                WHERE a.gouvernement = ? AND a.dans_periode_couverte
                ORDER BY l.acte, l.rang""", [org]):
            lois_par_acte[r["acte"]].append(r["numero_loi"])
            x = lois.setdefault(r["numero_loi"], {**{k: r[k] for k in (
                "numero_loi", "type_loi", "loi_jorf", "loi_identifiee_par")},
                "source_url": r["loi_source_url"] if r["loi_jorf"] else None, "actes": set()})
            x["actes"].add(r["acte"])

    # Comptes par ministère (tel que publié) et par nature.
    agr = {}
    for r in rows:
        k = (r["ministere_libelle"], r["nature"])
        x = agr.setdefault(k, {"ministere_libelle": r["ministere_libelle"],
                               "ministere_statut": r["ministere_statut"],
                               "ministere_normalise": r["ministere_normalise"], "nature": r["nature"],
                               "nb_actes": 0, "nb_mesures_nominatives": 0,
                               "nb_rubrique_non_lue": 0, "nb_titre_cite_une_loi": 0})
        x["nb_actes"] += 1
        x["nb_mesures_nominatives"] += r["mesure_nominative"] is True
        x["nb_rubrique_non_lue"] += r["mesure_nominative"] is None
        x["nb_titre_cite_une_loi"] += r["cite_une_loi"] is True
    agregats = sorted(agr.values(), key=lambda x: ((x["ministere_libelle"] is None),
                                                    (x["ministere_libelle"] or "").lower(),
                                                    x["nature"] or "￿"))
    for x in agregats:
        x.update({"du": du, "au": a, "source_url": None, "licence": lic})

    # Listes par mois ; mesures nominatives à part.
    mois = defaultdict(lambda: {"actes": [], "nominatives": []})
    for r in rows:
        r["lois_citees"] = lois_par_acte.get(r["acte"], [])
        r["licence"] = lic
        mois[r["date_publication"][:7]]["nominatives" if r["mesure_nominative"] else "actes"].append(r)
    cols = ["acte", "id_jorf", "date_publication", "nature", "numero", "nor", "titre", "ministere_libelle",
            "ministere_statut", "mesure_nominative", "cite_une_loi", "lois_citees", "est_rectificatif",
            "rectificatif_de", "num_jo", "source_url", "licence"]
    fichiers = []
    for m, parts in sorted(mois.items()):
        entree = {"mois": m}
        for genre, prefixe in (("actes", "actes"), ("nominatives", "actes-nominatives")):
            ls = parts[genre]
            entree[f"nb_{genre}"] = len(ls)
            if not ls:
                entree[f"fichier_{genre}"] = None
                continue
            c = _couv("actes", statut, f"Actes du Journal officiel publiés en {m} dans la période "
                      f"couverte ({'mesures nominatives' if genre == 'nominatives' else 'hors mesures nominatives'}).",
                      len(ls), len(ls), pts, au=au)
            f.section(f"{prefixe}-{m}", ls, type_fait="acte_jo", ids={"acte": "acte", "autre": "nor"},
                      date="date_publication", couverture=c, colonnes=cols)
            entree[f"fichier_{genre}"] = f"{prefixe}-{m}.json.gz"
        fichiers.append(entree)

    f.section("actes", agregats, type_fait="actes_compte", couverture=couv,
              colonnes=["ministere_libelle", "ministere_statut", "ministere_normalise", "nature",
                        "nb_actes", "nb_mesures_nominatives", "nb_rubrique_non_lue",
                        "nb_titre_cite_une_loi", "du", "au", "source_url", "licence"],
              extra={"mois": fichiers,
                     "ordre": "ministère tel que publié (alphabétique), puis nature",
                     "note": "nb_titre_cite_une_loi : actes dont le titre cite une loi par son numéro. "
                             "Le site ne calcule jamais la part des actes qui « appliquent » une loi."})
    liste_lois = []
    for x in sorted(lois.values(), key=lambda x: x["numero_loi"]):
        liste_lois.append({**{k: v for k, v in x.items() if k != "actes"},
                           "nb_actes": len(x["actes"]), "licence": lic})
    f.section("actes-lois", liste_lois, type_fait="loi_citee_titre",
              ids={"acte": "loi_jorf", "autre": "numero_loi"}, couverture=_couv(
                  "actes", statut, "Lois citées par leur numéro dans le titre d'au moins un acte de la "
                  "période couverte ; identifiées par un lien du Journal officiel ou par l'acte de la loi, "
                  "sinon « loi non identifiée ».", sum(1 for x in liste_lois if x["loi_jorf"]),
                  len(liste_lois), pts, au=au),
              colonnes=["numero_loi", "type_loi", "loi_jorf", "loi_identifiee_par", "nb_actes",
                        "source_url", "licence"])
    return {"nb_actes": len(rows),
            "nb_mesures_nominatives": sum(1 for r in rows if r["mesure_nominative"] is True),
            "nb_hors_mesures_nominatives": sum(1 for r in rows if r["mesure_nominative"] is False),
            "nb_rubrique_non_lue": sum(1 for r in rows if r["mesure_nominative"] is None),
            "nb_titre_cite_une_loi": sum(1 for r in rows if r["cite_une_loi"] is True),
            "nb_lois_citees": len(liste_lois),
            "nb_ministeres_publies": len({r["ministere_libelle"] for r in rows if r["ministere_libelle"]}),
            "periode_couverte": {"du": du, "au": a}, "couverture": statut, "etendue": statut_regle,
            "au": au}


# -- les budgets ----------------------------------------------------------------------------

def _budgets(f):
    f.section("budgets", [], type_fait="exercice_budgetaire", couverture=_couv(
        "budget", "non_collecte",
        "Les sources financières (lois de finances, exécution, comptes sociaux) ne sont pas collectées "
        "dans l'essai : les exercices rattachés à ce gouvernement ne sont pas servis.", None, None, ()))
