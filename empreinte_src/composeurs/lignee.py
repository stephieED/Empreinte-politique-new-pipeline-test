"""Composeur « lignee » : la fiche de chaque lignée de groupe publiée (cahier 4.3 ; doc. 1, 1.2.2,
1.5.2 et 1.7.2).

Une fiche `lignee/<adresse>` par lignée publiée (R-LIGNEE : au moins un groupe de la XIVe à la
XVIIe). L'adresse est acquise (registre des lignées) : elle ne change pas quand le groupe change de
nom. Un groupe d'une législature (« maillon », `grp:17:PO…`) n'a pas de fiche propre : la fiche de
sa lignée l'affiche, et l'en-tête donne pour chaque maillon ses organes, pour qu'une ancienne
adresse de groupe redirige vers la lignée ouverte sur cette législature.

Fichiers de `lignees/<adresse>/` :

| fichier | ce que voit le lecteur | chargé |
| --- | --- | --- |
| `fiche.json.gz` | en-tête : nom, suite des noms, période ; frise des maillons (organes, dates, position déclarée — `divergente` si deux organes d'un maillon en déclarent deux différentes —, membres, effectif, lien vers la législature quand sa fiche existe) ; filiations (les décomptes qui relient chaque maillon à son prédécesseur, ou qui montrent pourquoi la lignée commence là) ; couverture | tout de suite |
| `effectifs.json.gz` | effectif jour par jour de chaque maillon, écrit aux seuls jours où il change | à la demande |
| `membres.json.gz` | un point par personne et par maillon : arrivée, départ, périodes, d'où elle vient (au départ, déjà là au groupe précédent, revenue d'un groupe plus ancien, nouvelle), si elle reste au maillon suivant ; lien vers sa fiche quand elle est candidate | à la demande |
| `paroles.json.gz` | XVe à XVIIe : débats (sujets) avec leurs prises de parole et leurs orateurs distincts, prises de parole par nature et par orateur, index léger | à la demande |
| `paroles-textes-<aaaa>-s<n>[-<k>].json.gz` | extraits (300 caractères) et lien au paragraphe | au clic, ou pour un filtre |
| `proposes.json.gz` | XIVe à XVIIe : textes portés par les membres pendant leur appartenance (rôle, étape, matière) | à la demande |
| `amendements.json.gz` | XIVe à XVIIe : amendements distincts déposés par les membres pendant leur appartenance, par commission et par année ; irrecevables et signatures à part | à la demande |
| `amendements-<annee>[-<k>].json.gz` | liste de l'année | au clic |
| `votes-<législature>.json.gz` | un fichier par législature du groupe : décompte publié de chaque scrutin pour le groupe (pour, contre, abstention, non-votants, membres), position majoritaire publiée et si elle est établie (Q30), partage du groupe | à la demande |
| `avec-qui-<législature>.json.gz` | les autres groupes de la législature, dans l'ordre de l'hémicycle (législature en cours, ou close avec une archive figée : XVe, XVIe) ou des sigles (XIVe) : scrutins où les deux positions sont établies et ceux où elles coïncident, par nature de scrutin | à la demande |
| `mots/<xx>.json.gz` | index de mots | au filtre par mot |

Règles éditoriales (cahier, partie 2) : aucun score, aucun classement, aucun ratio — la fiche sert
des **décomptes** (membres, communs, voix, scrutins), jamais une part, un taux ni une cohésion ;
une position majoritaire n'est servie que publiée par l'Assemblée et concordante avec son
décompte (Q30) ; les listes déclarent leur ordre (alphabétique, chronologique, hémicycle) ;
chaque compte porte sa date (`au`), celle de la fin du maillon quand il est clos.

Périmètre (cahier 4.1, module `perimetre`) : textes, amendements et votes de la XIVe à la XVIIe ;
prises de parole de la XVe à la XVIIe — pour un maillon de la XIVe, la section le dit
(`hors_perimetre`).
"""
from __future__ import annotations

import datetime as dt
from collections import defaultdict

from ..perimetre import LEGISLATURES, LEGISLATURES_PAROLES, PAROLES_DEPUIS, points
from .candidat import points_de_l_annee
from .candidat import (LONGUEUR_EXTRAIT, IndexMots, _couv, _decouper, _ecrire_mots, _fr, _lignes,
                       _semestre, _taille, _vue)
from .gouvernement import _identites
from ..regles.r_continuite_scrutins import date_des_donnees, marquer as marquer_trous

NOM = "lignee"
VERSION = 1
DEPEND = ("R-LIGNEE", "R-FILIATION", "R-CONTINUITE-GROUPE", "R-APPARTENANCE", "R-HEMICYCLE",
          "R-LEGISLATURES", "R-NATURE-SCRUTIN", "R-DERNIERE-LECTURE", "R-LIEN-SCRUTIN-DOSSIER",
          "R-PAROLE-PERSONNE", "R-TEXTE-PORTE", "R-AMENDEMENT", "R-IDENTITE")

# Licence des données de l'Assemblée (la même pour toutes ses archives) : lue sur l'archive courante.
PA_AMO, PA_SCRUTINS, PA_DOSSIERS = "an-amo30-l17", "an-scrutins-l17", "an-dossiers-l17"
PA_AMENDEMENTS, PA_SYCERON = "an-amendements-l17", "an-syceron-l17"
POSITIONS = ("pour", "contre", "abstention")

LIMITES = [
    "Textes, amendements et votes de la XIVe à la XVIIe législature ; prises de parole en séance à "
    "partir de la XVe (cahier 4.1) : un groupe de la XIVe n'a pas de prises de parole servies.",
    "Le siège d'une législature close vient de son archive figée (XVe, XVIe) ; la XIVe n'en a pas "
    "d'utilisable : ses groupes sont rangés par sigle, sans place médiane.",
    "Les groupes de la XIIe et de la XIIIe servent au calcul des filiations ; ils ne sont pas affichés.",
    "Effectifs et membres d'après les mandats de groupe publiés par l'Assemblée (apparentés compris).",
]


def _au(fin, au):
    """Date d'un compte : la fin du maillon s'il est clos, sinon la date de référence."""
    return min(fin, au) if fin else au


def _hors_perimetre(famille, maillon, points, au) -> dict:
    return _couv(famille, "hors_perimetre", f"Prises de parole de la {_romain(maillon['legislature'])} "
                 f"législature hors du périmètre : elles sont publiées à partir de la {_romain(PAROLES_DEPUIS)} "
                 "(cahier 4.1).", points=points, au=au, maillon=maillon["maillon"],
                 raison="paroles_avant_la_xve")


def _romain(n: int) -> str:
    v = [(10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]
    s, x = "", int(n)
    for k, r in v:
        while x >= k:
            s, x = s + r, x - k
    return s + "e"


# -- composer -------------------------------------------------------------------------------

def composer(ctx, ecr):
    if not (_vue(ctx, "lignee") and _vue(ctx, "lignee_maillon") and _vue(ctx, "appartenance")):
        return
    au = ctx.date_reference or dt.date.today().isoformat()
    commun = _commun(ctx, au)
    for l in _lignes(ctx, "SELECT * FROM lignee WHERE publiee ORDER BY adresse"):
        _composer_une(ctx, ecr, l, commun)
    ctx.x("DROP TABLE IF EXISTS _lm")
    ctx.x("DROP TABLE IF EXISTS _lg_pos")


def _commun(ctx, au) -> dict:
    lic = {}
    for t in ("an_acteurs__mandat", "an_scrutins__scrutin", "an_dossiers__dossier",
              "an_amendements__amendement", "an_comptes_rendus__intervention"):
        if _vue(ctx, t):
            for p, l in ctx.x(f"SELECT DISTINCT prov_point, licence FROM {t} WHERE prov_point IS NOT NULL"):
                if l:
                    lic[p] = l
    # Périodes d'appartenance aux maillons affichés des lignées publiées.
    ctx.x("""CREATE OR REPLACE TEMP TABLE _lm AS
        WITH o AS (SELECT lm.lignee, lm.maillon, lm.legislature, unnest(lm.organes) AS organe
                   FROM lignee_maillon lm JOIN lignee l USING (lignee) WHERE l.publiee AND lm.affiche)
        SELECT o.lignee, o.maillon, o.legislature, a.acteur, a.groupe AS organe, a.debut, a.fin
        FROM o JOIN appartenance a ON a.groupe = o.organe""")
    legs = {r["numero"]: r for r in _lignes(ctx, "SELECT numero, debut, fin FROM legislature")} \
        if _vue(ctx, "legislature") else {}
    candidats = {}
    if _vue(ctx, "candidat"):
        candidats = {a: ad for a, ad in ctx.x("""SELECT acteur, adresse FROM candidat
                                                 WHERE publie AND adresse IS NOT NULL AND acteur IS NOT NULL""")}
    titres = {}
    if _vue(ctx, "an_dossiers__dossier"):
        titres = {u: t for u, t in ctx.x("SELECT uid, any_value(titre) FROM an_dossiers__dossier GROUP BY 1")}
    adresses = {lig: ad for lig, ad in ctx.x("SELECT lignee, adresse FROM lignee WHERE publiee")}
    maillon_de = {}
    for m, lig, org in ctx.x("SELECT maillon, lignee, unnest(organes) FROM lignee_maillon"):
        maillon_de[org] = (m, lig)
    # Effectif par maillon et par jour (somme de ses organes, qui ne se chevauchent pas).
    effectif = defaultdict(list)
    if _vue(ctx, "effectif_groupe"):
        for m, d, n in ctx.x("""SELECT lm.maillon, e.date, sum(e.effectif)
                                FROM (SELECT maillon, unnest(organes) AS organe FROM lignee_maillon
                                      WHERE affiche) lm
                                JOIN effectif_groupe e ON e.groupe = lm.organe
                                GROUP BY 1, 2 ORDER BY 1, 2"""):
            effectif[m].append((d, int(n)))
    return {"au": au, "lic": lic, "legs": legs, "candidats": candidats, "titres": titres,
            "identites": _identites(ctx), "adresses": adresses, "maillon_de": maillon_de,
            "effectif": effectif}


def _composer_une(ctx, ecr, l, commun):
    au = commun["au"]
    f = ecr.fiche("lignee", l["adresse"], titre=l["nom"] or l["sigle"] or l["adresse"])
    maillons = _lignes(ctx, """SELECT * FROM lignee_maillon WHERE lignee = ? AND affiche
                               ORDER BY rang_dans_lignee""", [l["lignee"]])
    idx = IndexMots()
    membres = _membres(ctx, f, l, maillons, commun)
    effectifs = _effectifs(f, maillons, commun)
    frise = _frise(ctx, l, maillons, membres, effectifs, commun)
    filiations = _filiations(ctx, l, maillons, commun)
    actifs = [m for m in maillons if m["legislature"] in LEGISLATURES]
    parole = [m for m in actifs if m["legislature"] in LEGISLATURES_PAROLES]
    _paroles(ctx, f, l, parole, [m for m in actifs if m not in parole], commun, idx)
    _proposes(ctx, f, l, actifs, [], commun, idx)
    _amendements(ctx, f, l, actifs, [], commun)
    for leg in sorted({m["legislature"] for m in actifs}):
        ms = [m for m in actifs if m["legislature"] == leg]
        _votes(ctx, f, l, ms, leg, commun, idx)
        _avec_qui(ctx, f, l, ms, leg, commun)
    noms = []
    for m in maillons:
        for lib in m["libelles"]:
            if lib and lib not in noms:
                noms.append(lib)
    entete = {
        "lignee": {"lignee": l["lignee"], "adresse": l["adresse"], "nom": l["nom"], "sigle": l["sigle"],
                   "noms_successifs": noms, "debut": l["debut_affiche"], "fin": l["fin"],
                   "en_cours": l["en_cours"], "regle": l["regle"],
                   "premiere_legislature_calculee": l["premiere_legislature"]},
        "maillons": {"colonnes": COLS_FRISE, "ordre": "chronologique",
                     "lignes": [[x.get(c) for c in COLS_FRISE] for x in frise]},
        "filiations": {"colonnes": COLS_FILIATION, "ordre": "chronologique",
                       "lignes": [[x.get(c) for c in COLS_FILIATION] for x in filiations],
                       "regle": ("Suite quand 2 × communs ≥ 0,6 × (réélus + anciens députés), avec au moins "
                                 "5 communs : la moyenne harmonique des deux parts atteint 60 %. Les "
                                 "nombres sont servis ; aucune part n'est écrite.")},
        "au": au, "date_reference": au, "limites": LIMITES,
    }
    for x in frise:
        ecr.fait_publie(f, "entete", "maillon_lignee", x, {"organe": "premier_organe", "autre": "maillon"},
                        "debut", "source_url")
        if x.get("licence"):
            f.licences.add(x["licence"])
    for x in filiations:
        ecr.fait_publie(f, "entete", "filiation_groupe", x, {"autre": "maillon"}, "au", None)
    entete["mots"] = _mots(ecr, f, idx, au)
    f.entete(entete)


# -- frise, effectifs, filiations -----------------------------------------------------------

COLS_FRISE = ["maillon", "legislature", "sigle", "libelle", "debut", "fin", "position_maillon",
              "organes", "sigles", "libelles", "positions_organes", "premier_organe", "membres",
              "effectif", "effectif_au", "lien", "raison_lien", "source_url", "licence"]


def _frise(ctx, l, maillons, membres, effectifs, commun):
    au = commun["au"]
    pos = {o: (p, u) for o, p, u in ctx.x("""SELECT organe, position_declaree, source_url FROM maillon
                                            WHERE maillon IN (SELECT unnest(?::VARCHAR[]))""",
                                         [[m["maillon"] for m in maillons]])}
    out = []
    for m in maillons:
        quand = _au(m["fin"], au)
        serie = effectifs.get(m["maillon"]) or []
        n = None
        for d, e in serie:
            if d <= quand:
                n = e
        leg = m["legislature"]
        lien = f"legislature/{leg}" if leg in LEGISLATURES and leg in commun["legs"] else None
        out.append({"maillon": m["maillon"], "legislature": leg, "sigle": m["sigle"], "libelle": m["libelle"],
                    "debut": m["debut"], "fin": m["fin"], "position_maillon": m["position_maillon"],
                    "organes": list(m["organes"]), "sigles": list(m["sigles"]), "libelles": list(m["libelles"]),
                    "positions_organes": [pos.get(o, (None, None))[0] for o in m["organes"]],
                    "premier_organe": m["organes"][0],
                    "membres": len(membres.get(m["maillon"], ())),
                    "effectif": n, "effectif_au": quand if n is not None else None,
                    "lien": lien, "raison_lien": None if lien else "législature sans fiche publiée",
                    "source_url": pos.get(m["organes"][-1], (None, None))[1],
                    "licence": commun["lic"].get(PA_AMO)})
    return out


def _effectifs(f, maillons, commun):
    au = commun["au"]
    lignes, series = [], {}
    for m in maillons:
        serie, prec = [], None
        brut = commun["effectif"].get(m["maillon"], [])
        for k, (d, n) in enumerate(brut):
            if n != prec or k == len(brut) - 1:
                serie.append((d, n))
                prec = n
        series[m["maillon"]] = serie
        for d, n in serie:
            lignes.append({"maillon": m["maillon"], "legislature": m["legislature"], "date": d, "effectif": n,
                           "source_url": None, "licence": commun["lic"].get(PA_AMO)})
    tous = sum(1 for m in maillons if commun["effectif"].get(m["maillon"]))
    f.section("effectifs", lignes, "effectif_lignee", ids={"autre": "maillon"}, date="date",
              couverture=_couv("effectifs", "complet" if tous == len(maillons) else "trou_source",
                               "Effectif de chaque groupe jour par jour, d'après les périodes d'appartenance "
                               "publiées (apparentés compris) ; une ligne aux seuls jours où il change, et le "
                               "dernier jour connu.", tous, len(maillons), [PA_AMO], au=au),
              colonnes=["maillon", "legislature", "date", "effectif", "source_url", "licence"],
              extra={"ordre": "chronologique",
                     "lecture": "l'effectif d'un jour est celui de la dernière ligne antérieure ou égale"})
    return series


COLS_FILIATION = ["maillon", "maillon_avant", "legislature_avant", "sigle_avant", "libelle_avant",
                  "lignee_avant", "lien", "reelus", "anciens_deputes", "communs", "verdict", "raison",
                  "decision", "au"]


def _filiations(ctx, l, maillons, commun):
    """Pour chaque maillon : les filiations retenues (ou à trancher) ; pour le premier maillon de
    la lignée, la comparaison la plus proche, pour dire pourquoi la lignée commence là."""
    ids = [m["maillon"] for m in maillons]
    if not ids or not _vue(ctx, "filiation"):
        return []
    rows = _lignes(ctx, """
        WITH f AS (SELECT f.*, row_number() OVER (PARTITION BY maillon_apres ORDER BY communs DESC,
                                                   maillon_avant) AS proche
                   FROM filiation f WHERE maillon_apres IN (SELECT unnest(?::VARCHAR[])))
        SELECT f.*, a.sigle AS sigle_avant, a.libelle AS libelle_avant, a.fin AS fin_avant,
               lm.lignee AS lignee_avant
        FROM f LEFT JOIN (SELECT maillon, arg_max(sigle, rang) AS sigle, arg_max(libelle, rang) AS libelle,
                                 any_value(fin_maillon) AS fin FROM maillon GROUP BY 1) a ON a.maillon = f.maillon_avant
        LEFT JOIN lignee_maillon lm ON lm.maillon = f.maillon_avant
        WHERE f.verdict IN ('suite', 'a_trancher') OR (f.proche = 1 AND f.maillon_apres = ?)
        ORDER BY f.legislature_apres, f.maillon_apres, f.maillon_avant""", [ids, l["maillon_racine"]])
    out = []
    for r in rows:
        ad = commun["adresses"].get(r["lignee_avant"])
        lien = f"lignee/{ad}" if ad and r["lignee_avant"] != l["lignee"] else None
        out.append({"maillon": r["maillon_apres"], "maillon_avant": r["maillon_avant"],
                    "legislature_avant": r["legislature_avant"], "sigle_avant": r["sigle_avant"],
                    "libelle_avant": r["libelle_avant"], "lignee_avant": r["lignee_avant"], "lien": lien,
                    "reelus": r["reelus"], "anciens_deputes": r["anciens_deputes"], "communs": r["communs"],
                    "verdict": r["verdict"], "raison": r["raison"], "decision": r["decision"],
                    "au": r["fin_avant"]})
    return out


# -- membres --------------------------------------------------------------------------------

COLS_MEMBRES = ["acteur", "nom", "maillon", "legislature", "arrivee", "depart", "periodes", "provenance",
                "reste_au_maillon_suivant", "candidat", "lien", "source_url", "licence"]


def _fusion(periodes):
    out = []
    for d0, d1 in sorted(periodes, key=lambda p: p[0]):
        if out and out[-1][1] is not None and d0 <= (dt.date.fromisoformat(out[-1][1]) +
                                                     dt.timedelta(days=1)).isoformat():
            out[-1][1] = None if d1 is None else max(out[-1][1], d1)
        elif out and out[-1][1] is None:
            continue
        else:
            out.append([d0, d1])
    return out


def _membres(ctx, f, l, maillons, commun):
    au = commun["au"]
    par: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    for m, a, d0, d1 in ctx.x("SELECT maillon, acteur, debut, fin FROM _lm WHERE lignee = ?", [l["lignee"]]):
        par[m][a].append((d0, d1))
    legs = sorted({m["legislature"] for m in maillons})
    par_leg: dict[int, set] = defaultdict(set)
    for m in maillons:
        par_leg[m["legislature"]] |= set(par[m["maillon"]])
    ident = commun["identites"]
    lignes = []
    for m in maillons:
        leg = m["legislature"]
        avant = par_leg.get(leg - 1, set())
        plus_anciens = set().union(*(par_leg[x] for x in legs if x < leg - 1)) if legs else set()
        suivant = par_leg.get(leg + 1) if leg + 1 in par_leg else None
        for a, ps in par[m["maillon"]].items():
            per = _fusion(ps)
            if leg == legs[0]:
                prov = "au_depart"
            elif a in avant:
                prov = "deja_la"
            elif a in plus_anciens:
                prov = "revenu"
            else:
                prov = "nouveau"
            cand = commun["candidats"].get(a)
            lignes.append({"acteur": a, "nom": (ident.get(a) or {}).get("nom"), "_tri": (ident.get(a) or {}).get("tri") or a,
                           "maillon": m["maillon"], "legislature": leg, "arrivee": per[0][0],
                           "depart": per[-1][1], "periodes": per, "provenance": prov,
                           "reste_au_maillon_suivant": None if suivant is None else a in suivant,
                           "candidat": cand is not None, "lien": f"candidat/{cand}" if cand else None,
                           "source_url": None, "licence": commun["lic"].get(PA_AMO)})
    lignes.sort(key=lambda x: (x["legislature"], x["_tri"], x["acteur"]))
    for x in lignes:
        x.pop("_tri")
    sans_nom = sum(1 for x in lignes if not x["nom"])
    f.section("membres", lignes, "membre_lignee", ids={"acteur": "acteur", "autre": "maillon"},
              date="arrivee",
              couverture=_couv("membres", "complet", f"Une ligne par personne et par groupe : périodes "
                               f"d'appartenance publiées par l'Assemblée (départs et retours compris). Nom "
                               f"connu pour {len(lignes) - sans_nom} lignes sur {len(lignes)}.",
                               len(lignes) - sans_nom, len(lignes), [PA_AMO], au=au),
              colonnes=COLS_MEMBRES,
              extra={"ordre": "législature, puis alphabétique",
                     "provenances": {"au_depart": "premier groupe affiché de la lignée",
                                     "deja_la": "membre du groupe de la lignée à la législature précédente",
                                     "revenu": "membre d'un groupe plus ancien de la lignée, pas du précédent",
                                     "nouveau": "jamais membre d'un groupe affiché de la lignée"},
                     "au": au})
    return {m: set(v) for m, v in par.items()}


# -- activité de la XVIIe -------------------------------------------------------------------

def _absente(famille, points, au, manque):
    return _couv(famille, "non_relu", "Section non établie : sortie de règle absente (" + ", ".join(manque)
                 + ").", points=points, au=au, raison="regle_absente")


def _couv_anciens(anciens, famille, points, au):
    return [_hors_perimetre(famille, m, points, au) for m in anciens]


def _jointure(table, col_date, l, ms, a="x"):
    """Lignes de `table` (alias `a`) d'un membre d'un des maillons `ms` à une date de son appartenance.
    Les identifiants viennent des tables de règles (`lig:…`, `grp:…`), jamais d'une source libre."""
    liste = ", ".join(f"'{m['maillon']}'" for m in ms)
    return (f"""FROM {table} {a} JOIN _lm m{a} ON m{a}.acteur = {a}.acteur AND m{a}.lignee = '{l["lignee"]}'
                AND m{a}.maillon IN ({liste})
                AND {a}.{col_date} BETWEEN m{a}.debut AND coalesce(m{a}.fin, '9999-12-31')""")


def _legs(ms) -> list[int]:
    return sorted({m["legislature"] for m in ms})


def _au_maillons(ms, au):
    """Date des comptes de maillons : la fin du dernier s'ils sont tous clos, sinon la référence."""
    if any(not m["fin"] for m in ms):
        return au
    return _au(max(m["fin"] for m in ms), au)


def _trous_votes(ctx, ms, leg) -> list[dict]:
    """Trous de l'archive des scrutins de la législature qui tombent pendant l'un des maillons
    (R-CONTINUITE-SCRUTINS)."""
    from ..regles.r_continuite_scrutins import couvre, trous
    return [t for t in trous(ctx, leg) if any(couvre(t, m["debut"], m["fin"]) for m in ms)]


def _garder(rows, cols):
    """Les seules colonnes servies : un fait publié ne porte que ce que la fiche affiche."""
    return [{c: r.get(c) for c in cols} for r in rows]


COLS_PAROLES = ["n", "date", "acteur", "preside", "sujet_id", "fichier", "ligne", "compte_rendu",
                "id_syceron", "source_url", "licence"]
COLS_EXTRAITS = ["n", "date", "acteur", "nom", "compte_rendu", "id_syceron", "extrait", "extrait_tronque",
                 "qualite", "preside", "sujet_id", "dossier", "source_url", "licence"]
COLS_SUJETS = ["sujet_id", "sujet", "sujet_libelle", "type_sujet", "dossier", "titre_dossier",
               "prises_de_parole", "orateurs_distincts", "premiere_date", "derniere_date"]


def _paroles(ctx, f, l, ms, anciens, commun, idx):
    au, pts = commun["au"], points("syceron", _legs(ms) or LEGISLATURES_PAROLES)
    lic = commun["lic"].get(PA_SYCERON)
    if not _vue(ctx, "parole_personne"):
        f.section("paroles", [], "parole_lignee", couverture=_absente("paroles", pts, au, ["parole_personne"]))
        return
    rows = _lignes(ctx, "SELECT x.* " + _jointure("parole_personne", "date", l, ms)
                   + " ORDER BY x.date, x.compte_rendu, x.ordre_absolu_seance, x.id_syceron") if ms else []
    ident = commun["identites"]
    sujets: dict[tuple, dict] = {}
    orateurs: dict[tuple, set] = defaultdict(set)
    for n, r in enumerate(rows, 1):
        k = (r["type_sujet"], r["sujet"], r["dossier"])
        if k not in sujets:
            sujets[k] = {"sujet_id": len(sujets) + 1, "sujet": r["sujet"],
                         "sujet_libelle": r["sujet"] or "Intitulé non publié", "type_sujet": r["type_sujet"],
                         "dossier": r["dossier"], "titre_dossier": commun["titres"].get(r["dossier"]),
                         "prises_de_parole": 0, "premiere_date": r["date"], "derniere_date": r["date"]}
        s = sujets[k]
        s["derniere_date"] = max(s["derniere_date"], r["date"])
        if not r["preside"]:
            s["prises_de_parole"] += 1
            orateurs[k].add(r["acteur"])
        r["sujet_id"], r["n"], r["licence"] = s["sujet_id"], n, lic
        r["nom"] = (ident.get(r["acteur"]) or {}).get("nom")
    for k, s in sujets.items():
        s["orateurs_distincts"] = len(orateurs[k])
    for nom, sem, ls in _decouper(rows, lambda r: _semestre(r["date"]), "paroles-textes",
                                  taille=lambda r: len(r["extrait"] or "") + 260):
        for k, r in enumerate(ls):
            r["fichier"], r["ligne"] = f"{nom}.json.gz", k
            idx.ajouter(nom, k, r["extrait"])
        f.section(nom, _garder(ls, COLS_EXTRAITS), "parole_extrait",
                  ids={"acteur": "acteur", "compte_rendu": "compte_rendu", "dossier": "dossier",
                       "autre": "id_syceron"}, date="date",
                  couverture=_couv("paroles", "complet", f"Extraits ({LONGUEUR_EXTRAIT} premiers caractères) "
                                   f"et lien au paragraphe, semestre {sem}.", len(ls), len(ls),
                                   points_de_l_annee(ctx, pts, str(sem)[:4]), au=au),
                  colonnes=COLS_EXTRAITS, extra={"semestre": sem, "ordre": "chronologique"})
    liste = sorted(sujets.values(), key=lambda s: s["sujet_id"])
    for s in liste:
        idx.ajouter("paroles:sujets", s["sujet_id"] - 1, s["sujet"], s["titre_dossier"])
    par_nature, par_orateur = defaultdict(int), defaultdict(lambda: [0, 0])
    for r in rows:
        if r["preside"]:
            par_orateur[r["acteur"]][1] += 1
        else:
            par_nature[r["type_sujet"] or "non_etabli"] += 1
            par_orateur[r["acteur"]][0] += 1
    orat = sorted(({"acteur": a, "nom": (ident.get(a) or {}).get("nom"),
                    "_tri": (ident.get(a) or {}).get("tri") or a, "prises_de_parole": v[0],
                    "paragraphes_de_presidence": v[1]} for a, v in par_orateur.items()),
                  key=lambda x: (x["_tri"], x["acteur"]))
    for x in orat:
        x.pop("_tri")
    debat = sum(1 for r in rows if not r["preside"])
    sans_s = sum(1 for r in rows if r["statut_sujet"] != "etabli")
    statut = "complet" if ms else "hors_perimetre"
    cv = _couv("paroles", statut, f"Paragraphes du compte rendu de séance attribués aux membres pendant leur "
               f"appartenance au groupe : {debat} prises de parole et {len(rows) - debat} paragraphes de "
               f"présidence de séance, comptés à part. {sans_s} sans intitulé publié. Commissions non lues.",
               len(rows) - sans_s, len(rows), pts, au=au)
    cv["maillons_hors_perimetre"] = _couv_anciens(anciens, "paroles", pts, au)
    # Index léger : chaque ligne renvoie à son extrait, déjà inscrit comme fait publié.
    f.section("paroles", _garder(rows, COLS_PAROLES), None,
              ids={"acteur": "acteur", "compte_rendu": "compte_rendu", "autre": "id_syceron"}, date="date",
              couverture=cv, colonnes=COLS_PAROLES,
              extra={"ordre": "chronologique", "maillons": [m["maillon"] for m in ms],
                     "sujets": {"colonnes": COLS_SUJETS, "ordre": "chronologique (première prise de parole)",
                                "lignes": [[s[c] for c in COLS_SUJETS] for s in liste]},
                     "par_nature": dict(sorted(par_nature.items())),
                     "orateurs": {"colonnes": ["acteur", "nom", "prises_de_parole", "paragraphes_de_presidence"],
                                  "ordre": "alphabetique",
                                  "lignes": [[x[c] for c in ("acteur", "nom", "prises_de_parole",
                                                             "paragraphes_de_presidence")] for x in orat]},
                     "lecture": "index sans texte ; l'extrait est dans `fichier`, au rang `ligne`", "au": au})


COLS_TEXTES = ["dossier", "document", "titre", "role", "qualite_rapporteur", "nature", "nature_code",
               "date", "etape_atteinte", "sort", "par_49_3", "adopte_par_49_3", "matiere", "matiere_statut",
               "matiere_libelle", "acteur", "nom", "source_url", "licence"]


def _proposes(ctx, f, l, ms, anciens, commun, idx):
    au, pts = commun["au"], points("dossiers", _legs(ms))
    if not _vue(ctx, "texte_porte"):
        f.section("proposes", [], "texte_porte_lignee", couverture=_absente("textes", pts, au, ["texte_porte"]))
        return
    rows = _lignes(ctx, """WITH x AS (SELECT *, coalesce(date_role, date_depot) AS date FROM texte_porte
                                      WHERE publiable AND role <> 'initiative_gouvernementale')
                           SELECT x.* """ + _jointure("x", "date", l, ms)
                   + " ORDER BY x.date, x.dossier, x.role, x.acteur") if ms else []
    ident = commun["identites"]
    for k, t in enumerate(rows):
        t["titre"] = t["titre"] or commun["titres"].get(t["dossier"])
        t["nom"] = (ident.get(t["acteur"]) or {}).get("nom")
        t["licence"] = commun["lic"].get(PA_DOSSIERS)
        idx.ajouter("proposes", k, t["titre"])
    # Décomptes de dossiers distincts par rôle, étape et matière (un texte porté par trois membres
    # compte une fois).
    agr: dict[tuple, set] = defaultdict(set)
    for t in rows:
        agr[(t["role"], t["etape_atteinte"], t["matiere"], t["matiere_libelle"])].add(t["dossier"])
    agregats = [{"role": r, "etape_atteinte": e, "matiere": m, "matiere_libelle": ml, "dossiers_distincts": len(s)}
                for (r, e, m, ml), s in sorted(agr.items(), key=lambda kv: tuple(str(x) for x in kv[0]))]
    mat = sum(1 for t in rows if t["matiere_statut"] in ("assemblee", "senat_seulement"))
    cv = _couv("textes", "complet" if ms else "non_collecte",
               f"Textes portés par les membres pendant leur appartenance (auteur, cosignataire, rapporteur), "
               f"publiés à partir de leur examen en commission : {len(rows)} rôles sur "
               f"{len({t['dossier'] for t in rows})} dossiers distincts. Matière établie pour {mat} sur {len(rows)}.",
               mat, len(rows), pts, au=au)
    cv["maillons_hors_perimetre"] = _couv_anciens(anciens, "textes", pts, au)
    f.section("proposes", _garder(rows, COLS_TEXTES), "texte_porte_lignee",
              ids={"acteur": "acteur", "dossier": "dossier", "document": "document", "organe": "matiere"},
              date="date", couverture=cv, colonnes=COLS_TEXTES,
              extra={"ordre": "chronologique", "aide_a_la_lecture": ["matiere_libelle"],
                     "agregats": {"colonnes": ["role", "etape_atteinte", "matiere", "matiere_libelle",
                                               "dossiers_distincts"],
                                  "lignes": [[a[c] for c in ("role", "etape_atteinte", "matiere",
                                                             "matiere_libelle", "dossiers_distincts")]
                                             for a in agregats]},
                     "note_49_3": "par_49_3 : fait de procédure, jamais une position de vote", "au": au})


COLS_AMENDEMENTS = ["amendement", "numero_long", "date_depot", "sort", "famille_sort", "commission",
                    "commission_libelle", "dossier", "titre_dossier", "document", "article_designation",
                    "acteur", "nom", "source_url", "licence"]
COLS_AGREGATS = ["commission", "commission_libelle", "annee", "nb_amendements", "nb_dossiers_distincts",
                 "nb_irrecevables_40", "nb_irrecevables_45", "nb_signatures_cosignataire", "au"]


def _amendements(ctx, f, l, ms, anciens, commun):
    au, pts = commun["au"], points("amendements", _legs(ms))
    lic = commun["lic"].get(PA_AMENDEMENTS)
    if not _vue(ctx, "amendement_canonique"):
        f.section("amendements", [], "amendements_lignee",
                  couverture=_absente("amendements", pts, au, ["amendement_canonique"]))
        return
    rows = _lignes(ctx, "SELECT x.* " + _jointure("amendement_canonique", "date_depot", l, ms)
                   + " ORDER BY x.date_depot, x.amendement") if ms else []
    # Signatures : amendements cosignés par un membre pendant son appartenance, dont l'auteur
    # principal n'est pas membre du groupe à cette date (sinon l'amendement est déjà compté).
    sig = _lignes(ctx, f"""SELECT DISTINCT x.amendement, x.date_depot, x.commission
                           {_jointure("amendement_auteur", "date_depot", l, ms)}
                           WHERE x.role = 'cosignataire' AND x.amendement NOT IN
                                 (SELECT y.amendement {_jointure("amendement_canonique", "date_depot", l, ms, "y")})""") \
        if ms and _vue(ctx, "amendement_auteur") else []
    ident = commun["identites"]
    lib = {}
    for r in rows:
        r["titre_dossier"] = commun["titres"].get(r["dossier"])
        r["nom"] = (ident.get(r["acteur"]) or {}).get("nom")
        r["licence"] = lic
        r["annee"] = (r["date_depot"] or "")[:4] or None
        lib[r["commission"]] = r["commission_libelle"]
    listes = {}
    for nom, annee, ls in _decouper(rows, lambda x: x["annee"] or "sans-date", "amendements",
                                    taille=lambda x: _taille([x.get(k) for k in COLS_AMENDEMENTS])):
        listes.setdefault(annee, []).append(f"{nom}.json.gz")
        f.section(nom, _garder(ls, COLS_AMENDEMENTS), "amendement_lignee",
                  ids={"acteur": "acteur", "amendement": "amendement", "dossier": "dossier",
                       "document": "document", "organe": "commission"}, date="date_depot",
                  couverture=_couv("amendements", "complet", f"Amendements déposés en {annee} par un membre, "
                                   "auteur principal, pendant son appartenance (copies dédoublonnées), avec "
                                   "l'adresse de sa page sur le site de l'Assemblée.", len(ls), len(ls),
                                   points_de_l_annee(ctx, pts, annee), au=au),
                  colonnes=COLS_AMENDEMENTS, extra={"annee": annee, "ordre": "chronologique",
                                                    "aide_a_la_lecture": ["commission_libelle"]})
    agr: dict[tuple, dict] = {}

    def cle(com, annee):
        k = (com, annee)
        if k not in agr:
            agr[k] = {"commission": com, "commission_libelle": lib.get(com) if com else "Commission non établie",
                      "annee": annee, "nb_amendements": 0, "_d": set(), "nb_irrecevables_40": 0,
                      "nb_irrecevables_45": 0, "nb_signatures_cosignataire": 0, "au": au}
        return agr[k]
    for r in rows:
        x = cle(r["commission"], r["annee"])
        if r["famille_sort"] == "irrecevable_40":
            x["nb_irrecevables_40"] += 1
        elif r["famille_sort"] == "irrecevable_45":
            x["nb_irrecevables_45"] += 1
        else:
            x["nb_amendements"] += 1
            if r["dossier"]:
                x["_d"].add(r["dossier"])
    for s in sig:
        cle(s["commission"], (s["date_depot"] or "")[:4] or None)["nb_signatures_cosignataire"] += 1
    agregats = []
    for x in sorted(agr.values(), key=lambda x: (x["commission"] is None, (x["commission_libelle"] or "").lower(),
                                                 x["annee"] or "")):
        x["nb_dossiers_distincts"] = len(x.pop("_d"))
        agregats.append(x)
    hors = sum(1 for r in rows if r["famille_sort"] not in ("irrecevable_40", "irrecevable_45"))
    com = sum(1 for r in rows if r["commission"])
    cv = _couv("amendements", "complet" if ms else "non_collecte",
               f"Amendements distincts dont un membre est l'auteur principal, déposés pendant son "
               f"appartenance : {hors}, plus {len(rows) - hors} irrecevables (articles 40 et 45) comptés à "
               f"part ; {len(sig)} amendements d'autres auteurs cosignés par des membres, comptés à part. "
               f"Commission établie pour {com} sur {len(rows)}. Aucun taux d'adoption.",
               com, len(rows), pts, au=au)
    cv["maillons_hors_perimetre"] = _couv_anciens(anciens, "amendements", pts, au)
    f.section("amendements", agregats, "amendements_compte_lignee", ids={"organe": "commission", "autre": "annee"},
              date="au", source=None, couverture=cv, colonnes=COLS_AGREGATS,
              extra={"ordre": "commission (alphabétique), puis année", "listes": listes,
                     "aide_a_la_lecture": ["commission_libelle"],
                     "definitions": {"nb_amendements": "amendements dont l'auteur principal est membre à la "
                                                       "date de dépôt, hors irrecevables 40 et 45",
                                     "nb_signatures_cosignataire": "amendements d'un auteur extérieur au "
                                                                   "groupe cosignés par au moins un membre"},
                     "au": au})


COLS_VOTES = ["scrutin", "numero", "date", "intitule", "nature", "lecture", "sort", "derniere_lecture",
              "votes_posterieurs_non_relies",
              "dossier", "titre_dossier", "groupe", "sigle", "position_publiee", "position_groupe",
              "raison_position_non_etablie", "pour", "contre", "abstentions", "non_votants", "membres",
              "partage", "source_url", "licence"]


def _positions_groupes(ctx):
    """Position de chaque organe à chaque scrutin, telle que publiée, et si elle est établie (Q30)."""
    ctx.x(f"""CREATE OR REPLACE TEMP TABLE _lg_pos AS
        WITH d AS (SELECT scrutin, organe,
                          CASE WHEN count(DISTINCT position_majoritaire) = 1 THEN any_value(position_majoritaire) END AS pub,
                          count(DISTINCT position_majoritaire) AS nb_pos,
                          any_value(pour) AS pour, any_value(contre) AS contre, any_value(abstentions) AS abst,
                          any_value(non_votants) AS nv, any_value(nombre_membres) AS membres
                   FROM an_scrutins__decompte_groupe WHERE organe <> 'PO0' GROUP BY 1, 2)
        SELECT *, CASE WHEN nb_pos > 1 THEN 'positions_publiees_discordantes'
                       WHEN coalesce(pour, 0) + coalesce(contre, 0) + coalesce(abst, 0) = 0 THEN 'aucun_membre_exprime'
                       WHEN pub NOT IN {POSITIONS} OR pub IS NULL THEN 'position_non_publiee'
                       WHEN CASE pub WHEN 'pour' THEN pour WHEN 'contre' THEN contre WHEN 'abstention' THEN abst END
                            < greatest(pour, contre, abst) THEN 'position_publiee_contredite_par_le_decompte'
                  END AS raison
        FROM d""")


def _votes(ctx, f, l, ms, leg, commun, idx):
    pts = points("scrutins", [leg])
    if not ms:
        return
    ts = _trous_votes(ctx, ms, leg)
    au = date_des_donnees(_au_maillons(ms, commun["au"]), ts)
    nom = f"votes-{leg}"
    if not (_vue(ctx, "an_scrutins__decompte_groupe") and _vue(ctx, "scrutin_classe")):
        f.section(nom, [], "vote_groupe", couverture=_absente("votes", pts, au, ["scrutin_classe"]))
        return
    if not commun.get("positions"):
        _positions_groupes(ctx)
        commun["positions"] = True
    dl = "EXISTS (SELECT 1 FROM derniere_lecture d WHERE d.scrutin = s.scrutin)" \
        if _vue(ctx, "derniere_lecture") else "false"
    dos = "(SELECT min(dossier) FROM lien_scrutin_dossier ld WHERE ld.scrutin = s.scrutin)" \
        if _vue(ctx, "lien_scrutin_dossier") else "NULL"
    # Un vote plus récent sur l'ensemble, relié à aucun texte, a pu être la dernière lecture (#34).
    tard = ("(SELECT CASE WHEN len(flatten(list(d.votes_posterieurs_non_relies))) > 0 "
            "THEN flatten(list(d.votes_posterieurs_non_relies)) END FROM derniere_lecture d "
            "WHERE d.scrutin = s.scrutin)") \
        if _vue(ctx, "derniere_lecture") and "votes_posterieurs_non_relies" in [c[0] for c in ctx.x("DESCRIBE derniere_lecture")] \
        else "NULL::VARCHAR[]"
    rows = _lignes(ctx, f"""
        SELECT s.scrutin, s.numero, s.date, s.titre AS intitule, s.nature, s.lecture, s.sort,
               {dl} AS derniere_lecture, {tard} AS votes_posterieurs_non_relies, {dos} AS dossier,
               p.organe AS groupe, g.sigle,
               p.pub AS position_publiee, CASE WHEN p.raison IS NULL THEN p.pub END AS position_groupe,
               p.raison AS raison_position_non_etablie, p.pour, p.contre, p.abst AS abstentions,
               p.nv AS non_votants, p.membres, s.source_url
        FROM _lg_pos p JOIN scrutin_classe s USING (scrutin) LEFT JOIN groupe g ON g.organe = p.organe
        WHERE p.organe IN (SELECT unnest(?::VARCHAR[])) AND s.legislature = ?
        ORDER BY s.date, s.numero, p.organe""", [[o for m in ms for o in m["organes"]], leg])
    for k, r in enumerate(rows):
        r["titre_dossier"] = commun["titres"].get(r["dossier"])
        r["licence"] = commun["lic"].get(PA_SCRUTINS)
        voix = [x for x in (r["pour"], r["contre"], r["abstentions"]) if x]
        r["partage"] = ("aucun_exprime" if not voix else "une_seule_voix" if len(voix) == 1
                        else "pour_et_contre" if r["pour"] and r["contre"] else "position_et_abstention")
        idx.ajouter(nom, k, r["intitule"], r["titre_dossier"])
    etab = sum(1 for r in rows if r["position_groupe"])
    n_scr = ctx.un("SELECT count(*) FROM scrutin_classe WHERE legislature = ?", [leg])
    f.section(nom, rows, "vote_groupe", ids={"scrutin": "scrutin", "organe": "groupe", "dossier": "dossier"},
              date="date",
              couverture=marquer_trous(_couv("votes", "complet", f"Décompte publié par l'Assemblée pour le groupe sur {len(rows)} "
                               f"scrutins de la législature (sur {n_scr} que contient l'archive) : pour, contre, abstention, non-votants, "
                               f"membres. Position majoritaire établie pour {etab} : publiée et concordante avec le "
                               "décompte (Q30) ; sinon « non établie », avec la raison. Aucun seuil de quorum "
                               "n'est appliqué ici : c'est un choix d'affichage.", etab, len(rows), pts, au=au,
                               scrutins_de_la_legislature=n_scr), ts),
              colonnes=COLS_VOTES,
              extra={"ordre": "chronologique ; `derniere_lecture` permet de mettre les dernières lectures en tête",
                     "partages": {"une_seule_voix": "toutes les voix exprimées du groupe dans le même sens",
                                  "position_et_abstention": "des voix dans un sens et des abstentions",
                                  "pour_et_contre": "des voix pour et des voix contre",
                                  "aucun_exprime": "aucun membre ne s'est exprimé"},
                     "au": au})


COLS_AVEC_QUI = ["maillon", "groupe_sigle", "groupe_libelle", "lien", "place_mediane", "nature",
                 "scrutins_compares", "scrutins_coincidents", "au"]


def _avec_qui(ctx, f, l, ms, leg, commun):
    pts = points("scrutins", [leg]) + [PA_AMO]
    if not ms:
        return
    ts = _trous_votes(ctx, ms, leg)
    au = date_des_donnees(_au_maillons(ms, commun["au"]), ts)
    nom = f"avec-qui-{leg}"
    if not (_vue(ctx, "an_scrutins__decompte_groupe") and _vue(ctx, "scrutin_classe")):
        f.section(nom, [], "avec_qui", couverture=_absente("votes", pts, au, ["scrutin_classe"]))
        return
    if not commun.get("positions"):
        _positions_groupes(ctx)
        commun["positions"] = True
    med = {}
    if _vue(ctx, "hemicycle"):
        med = {m: v for m, v in ctx.x("""
            SELECT lm.maillon, median(TRY_CAST(h.siege AS INTEGER))
            FROM hemicycle h JOIN (SELECT maillon, unnest(organes) AS organe FROM lignee_maillon) lm
              ON lm.organe = h.groupe WHERE h.legislature = ? GROUP BY 1""", [leg])}
    rows = _lignes(ctx, """
        WITH p AS (SELECT p.scrutin, lm.maillon, p.pub FROM _lg_pos p
                   JOIN (SELECT maillon, legislature, unnest(organes) AS organe FROM lignee_maillon) lm
                     ON lm.organe = p.organe
                   WHERE p.raison IS NULL AND lm.legislature = ?),
        moi AS (SELECT * FROM p WHERE maillon IN (SELECT unnest(?::VARCHAR[])))
        SELECT o.maillon, s.nature, count(*) AS scrutins_compares,
               count(*) FILTER (o.pub = moi.pub) AS scrutins_coincidents
        FROM moi JOIN p o ON o.scrutin = moi.scrutin AND o.maillon <> moi.maillon
        JOIN scrutin_classe s ON s.scrutin = moi.scrutin
        GROUP BY 1, 2""", [leg, [m["maillon"] for m in ms]])
    info = {m: (lig, s, lb) for m, lig, s, lb in ctx.x(
        "SELECT maillon, lignee, sigle, libelle FROM lignee_maillon WHERE legislature = ?", [leg])}
    for r in rows:
        lig, s, lb = info.get(r["maillon"], (None, None, None))
        ad = commun["adresses"].get(lig)
        r.update({"groupe_sigle": s, "groupe_libelle": lb, "lien": f"lignee/{ad}" if ad else None,
                  "place_mediane": med.get(r["maillon"]), "au": au})
    rows.sort(key=lambda r: (r["place_mediane"] is None, r["place_mediane"] or 0, r["groupe_sigle"] or "",
                             r["nature"] or ""))
    phrase = ("Pour chaque autre groupe de la législature et chaque nature de scrutin : nombre de scrutins "
              "où les positions majoritaires des deux groupes sont établies, et nombre de ceux où elles "
              "coïncident. Aucune part n'est calculée.")
    if med:
        couv = _couv("votes", "complet", phrase, sum(1 for r in rows if r["place_mediane"] is not None),
                     len(rows), pts, au=au)
        ordre = "hémicycle (place médiane des membres siégeant le jour de constat ; groupes clos à la fin)"
    else:
        # Législature close : l'Assemblée ne publie que l'hémicycle en cours. Rien n'est déduit.
        couv = _couv("votes", "complet", phrase + " Les sièges de cette législature ne sont pas publiés "
                     "(pas d'archive figée utilisable) : groupes rangés par sigle, sans place médiane.",
                     len(rows), len(rows), pts, au=au)
        ordre = "alphabétique (sigle) : sièges non publiés pour cette législature"
    f.section(nom, rows, "avec_qui", ids={"autre": "maillon"}, date="au", source=None,
              couverture=marquer_trous(couv, ts), colonnes=COLS_AVEC_QUI, extra={"ordre": ordre, "au": au})


def _mots(ecr, f, idx, au):
    m = _ecrire_mots(ecr, f, idx, au)
    m["porte_sur"] = ["extraits de parole", "sujets de parole", "titres des textes portés",
                      "intitulés des scrutins et titres de leurs dossiers"]
    return m
