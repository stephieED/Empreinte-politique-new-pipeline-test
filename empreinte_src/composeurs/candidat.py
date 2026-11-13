"""Composeur « candidat » : la fiche de chaque candidat publié (cahier 4.2 ; doc. 1, 1.7.2 et 1.7.3).

Une fiche `candidat/<adresse>` par candidat **publié** (`candidat.publie`, R-IDENTITE : déclaré
dans la liste des candidats, décision `candidature` recopiée de franceinfo, avec une adresse). Un candidat retiré, ou qui n'est plus listé, n'a
pas de fiche ; ses données restent dans les tables (cahier 4.1). Les tables d'activité (groupe
E2) sont calculées pour tous les députés : la fiche les filtre sur l'`acteur` du candidat, quand
il en a un (identifiant de l'Assemblée déclaré par Wikidata, jamais rapproché par le nom).

Fichiers de `candidats/<adresse>/` :

| fichier | ce que voit le lecteur | chargé |
| --- | --- | --- |
| `fiche.json.gz` | en-tête (nom, profession, groupe actuel, naissance, source), candidature, en bref (frise de carrière par institution, liens vers `legislature/<14 à 17>` et les gouvernements publiés ; compteurs par institution, datés), périodes de position, limites, couverture de chaque section, tranches de l'index de mots | tout de suite |
| `fonctions.json.gz` | fonctions par famille, avec leur durée | à la demande |
| `fonctions-periodes.json.gz` | détail : un mandat d'organe de la source par ligne | au clic |
| `proposes.json.gz` | textes portés publiables (rôle, nature, étape, sort, matière) | à la demande |
| `amendements.json.gz` | amendements dont la personne est l'auteur principal, décomptés par commission et par année ; irrecevables (articles 40 et 45) et signatures comptés à part | à la demande |
| `amendements-<annee>[-<k>].json.gz` | la liste des amendements de l'année (sans exposé) | au clic |
| `exposes-<annee>[-<k>].json.gz` | exposés sommaires, en texte, par paquets (≈ 300 Ko bruts) | au clic, ou pour les seuls résultats d'un filtre par mot |
| `votes.json.gz` | une position par texte (dernière lecture, vote sur l'ensemble), avec matière, origine, sort final, période | à la demande |
| `votes-motions.json.gz` | motions de censure, à part | à la demande |
| `divergences.json.gz` | bande : sa position et celle de son groupe, scrutin par scrutin (`diverge`) ; **aucun total** | à la demande |
| `paroles.json.gz` | index léger (date, qualité, présidence, sujet, période) et table des sujets, sans texte | à la demande |
| `paroles-textes-<aaaa>-s<n>[-<k>].json.gz` | extraits (300 caractères) et lien au paragraphe | au clic, ou pour les résultats d'un filtre |
| `questions.json.gz` | questions écrites, au gouvernement, orales sans débat | à la demande |
| `mots/<xx>.json.gz` | index de mots : mots qui commencent par « xx » → lignes des fichiers ci-dessus | au filtre par mot |

Les tranches de l'index de mots ne sont pas des sections (elles n'affichent rien) : elles sont
écrites hors de la liste des sections, pour garder l'en-tête léger ; l'en-tête liste les
tranches existantes.

Règles éditoriales appliquées ici (cahier, partie 2) : aucun score, aucun classement, aucun taux
(ni de présence, ni d'adoption) ; un 49.3 est un fait de procédure, jamais une position ; la
bande des divergences ne porte **aucun total** (règle 7) : une seule liste, chaque ligne dit
`diverge`, et aucun compte de divergences n'est servi ; une donnée manquante reste `null`
(un compte nul n'est servi que si la lecture est complète) ; chaque compte porte sa date (`au`).

Périmètre (cahier 4.1, module `perimetre`) : textes, amendements, votes et questions de la XIVe à
la XVIIe législature (depuis le 20/06/2012) ; prises de parole de la XVe à la XVIIe (depuis le
21/06/2017). Une activité antérieure est « hors périmètre », dite comme telle, et rien n'est
compté pour elle. Les mandats et fonctions viennent de l'archive des acteurs (depuis le
19/06/2002).
"""
from __future__ import annotations

import datetime as dt
import html
import json
import re
import unicodedata
from collections import defaultdict

from ..perimetre import LEGISLATURES, LEGISLATURES_GOUVERNEMENTS, PAROLES_DEPUIS, plage, point, points
from ..regles.r_continuite_scrutins import marquer as marquer_trous

NOM = "candidat"
VERSION = 1
DEPEND = ("R-CANDIDATURES", "R-IDENTITE", "R-CARRIERE", "R-FONCTIONS", "R-TEXTE-PORTE",
          "R-AMENDEMENT", "R-VOTE-PERSONNE", "R-PERIODE", "R-DIVERGENCE", "R-PAROLE-PERSONNE",
          "R-QUESTION-PERSONNE", "R-LEGISLATURES", "R-GOUVERNEMENTS", "R-APPARTENANCE", "R-VOTE-PE",
          "R-ACTIVITE-PE")

LEGISLATURES_PUBLIEES = set(LEGISLATURES)   # fiches de législature publiées (seules cibles de lien, C2)
LONGUEUR_EXTRAIT = 300
# Poids brut visé d'un fichier de textes (exposés, extraits) : un clic ne charge que son paquet.
PAQUET = 300_000
MOIS_FILTRE = (6, 12)

PA_AMO, PA_SCRUTINS, PA_DOSSIERS = "an-amo30-l17", "an-scrutins-l17", "an-dossiers-l17"
PA_AMENDEMENTS, PA_SYCERON = "an-amendements-l17", "an-syceron-l17"
PA_QUESTIONS = ("an-questions-ecrites-l17", "an-questions-gouvernement-l17", "an-questions-orales-l17")
PA_WP, PA_WD, PA_SENAT = "wp-candidatures-2027", "wd-identifiants-parlementaires", "senat-export"
PA_PE, PA_PE_VOTES, PA_PARLTRACK = "pe-eurodeputes", "pe-votes", "parltrack-votes"
PA_PARLTRACK_ACT = "parltrack-activites"
PA_RNE = "rne-cm"                  # répertoire national des élus (tous ses points : Licence Ouverte)
DEBUT_VOTES_PE = "2019-07-02"      # portail du PE : votes nominatifs à partir de la 9e législature (Q3)

# Statuts de couverture de R-CARRIERE → statuts servis (doc. 1, 1.5.5).
STATUT_CARRIERE = {"complet": "complet", "relu_aucun": "relu_aucun", "non_collecte": "non_collecte",
                   "partiel": "partiel",
                   "hors_source": "borne_historique", "aucun_identifiant": "hors_perimetre",
                   "identifiant_absent_de_la_source": "trou_source", "non_etabli": "non_relu"}
INSTITUTIONS = ("assemblee", "assemblee_avant_2002", "gouvernement", "senat", "parlement_europeen",
                "local")
LIBELLE_INSTITUTION = {"assemblee": "Assemblée nationale", "assemblee_avant_2002":
                       "Assemblée nationale avant le 19/06/2002", "gouvernement": "Gouvernement",
                       "senat": "Sénat", "parlement_europeen": "Parlement européen",
                       "local": "Mandats locaux"}

# Mots vides du filtre par mot (formes normalisées : minuscules, sans accents, 3 lettres et plus).
VIDES = set("""les des une est dans pour par sur que qui aux avec son ses sont pas plus cette ces
ont ete etre elle ils elles nous vous leur leurs mais comme ainsi tout tous toute toutes sans
sous entre dont fait faire peut doit tres aussi donc car quand meme cet cela celui celle ceux
deja encore alors avoir avait sera seront etait apres avant depuis lors puis sur afin notre
votre nos vos mes tes lui moi toi aux une uns par non oui car ces qu'il""".split())
_MOT = re.compile(r"[a-z0-9]+")
_BALISE = re.compile(r"<[^>]+>")
_ESPACES = re.compile(r"\s+")


# -- outils ---------------------------------------------------------------------------------

def _lignes(ctx, sql: str, params=None) -> list[dict]:
    rel = ctx.con.execute(sql, params or [])
    noms = [d[0] for d in rel.description]
    return [dict(zip(noms, r)) for r in rel.fetchall()]


def _vue(ctx, nom) -> bool:
    return ctx.existe(nom)


def _couv(famille, statut, detail, numerateur=None, denominateur=None, points=(), au=None, **extra):
    c = {"famille": famille, "statut": statut, "numerateur": numerateur,
         "denominateur": denominateur, "detail": detail, "points_acces": sorted(set(points))}
    if au:
        c["au"] = au
    c.update(extra)
    return c


def points_de_l_annee(ctx, pts: list[str], annee) -> list[str]:
    """Points d'accès d'une section limitée à une année : ceux des législatures qui recouvrent
    cette année (un point sans législature est gardé). Sans cela, la section « amendements de
    2026 » se disait en panne quand l'archive de la XVIe (close en 2024) ne venait pas (#33)."""
    import re as _re
    if not annee or not str(annee).isdigit() or not _vue(ctx, "legislature"):
        return pts
    if getattr(ctx, "_annees_legislatures", None) is None:
        ctx._annees_legislatures = {int(n): ((d or "")[:4], (f or "9999")[:4])
                                    for n, d, f in ctx.x("SELECT numero, debut, fin FROM legislature")}
    out = []
    for p in pts:
        m = _re.search(r"-l(\d+)$", p)
        per = ctx._annees_legislatures.get(int(m.group(1))) if m else None
        if per is None or per[0] <= str(annee) <= per[1]:
            out.append(p)
    return out


def _absente(famille, manque, points, au) -> dict:
    return _couv(famille, "non_relu", "Section non établie : sortie de règle absente ("
                 + ", ".join(manque) + ").", points=points, au=au, raison="regle_absente")


def _compte(n, statut):
    """Un compte nul n'est servi que si la lecture est complète (cahier, règle 5 ; C5)."""
    if n is None:
        return None
    return None if n == 0 and statut not in ("complet", "relu_aucun") else n


def _fr(d) -> str | None:
    d = None if d is None else str(d)
    return None if not d else f"{d[8:10]}/{d[5:7]}/{d[0:4]}"


def _jour(d) -> dt.date | None:
    return None if d is None else dt.date.fromisoformat(str(d)[:10])


def _jours_union(intervalles, depuis=None, jusqu_a=None) -> int:
    """Jours couverts par l'union d'intervalles fermés [d0, d1], bornés à [depuis, jusqu_a]."""
    xs = []
    for d0, d1 in intervalles:
        if depuis and d0 < depuis:
            d0 = depuis
        if jusqu_a and d1 > jusqu_a:
            d1 = jusqu_a
        if d1 >= d0:
            xs.append((d0, d1))
    total, cour = 0, None
    for d0, d1 in sorted(xs):
        if cour and d0 <= cour[1] + dt.timedelta(days=1):
            cour[1] = max(cour[1], d1)
        else:
            if cour:
                total += (cour[1] - cour[0]).days + 1
            cour = [d0, d1]
    if cour:
        total += (cour[1] - cour[0]).days + 1
    return total


def _norm(t: str) -> str:
    t = t.lower().replace("œ", "oe").replace("æ", "ae")
    return "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")


def mots(texte: str | None) -> set[str]:
    """Mots normalisés d'un texte (minuscules, sans accents, 3 caractères et plus, sans mots vides)."""
    if not texte:
        return set()
    return {m for m in _MOT.findall(_norm(texte)) if len(m) >= 3 and m not in VIDES}


def texte_brut(h: str | None) -> str | None:
    """Exposé publié en HTML → texte (balises retirées, entités décodées, espaces resserrés)."""
    if h is None:
        return None
    t = _ESPACES.sub(" ", html.unescape(_BALISE.sub(" ", h))).strip()
    return t or None


def _taille(x) -> int:
    return len(json.dumps(x, ensure_ascii=False, separators=(",", ":"), default=str))


def _semestre(d: str) -> str:
    return f"{d[:4]}-s{1 if int(d[5:7]) <= 6 else 2}"


def _decouper(lignes, cle, prefixe, taille=None, taille_max=PAQUET) -> list[tuple[str, str, list]]:
    """Groupe les lignes par `cle` (année, semestre), puis découpe chaque groupe en paquets
    d'au plus `taille_max` octets bruts. Rend [(nom de section, groupe, lignes)]."""
    groupes: dict[str, list] = defaultdict(list)
    for l in lignes:
        groupes[cle(l)].append(l)
    out = []
    for g in sorted(groupes):
        paquets, poids = [[]], 0
        for l in groupes[g]:
            t = (taille or _taille)(l)
            if paquets[-1] and poids + t > taille_max:
                paquets.append([])
                poids = 0
            paquets[-1].append(l)
            poids += t
        if len(paquets) == 1:
            out.append((f"{prefixe}-{g}", g, paquets[0]))
        else:
            out += [(f"{prefixe}-{g}-{k}", g, p) for k, p in enumerate(paquets, 1)]
    return out


class IndexMots:
    """Index de mots d'une fiche : mot normalisé → (fichier, rang de ligne)."""

    def __init__(self):
        self.renvois: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(list))
        self.textes = 0

    def ajouter(self, fichier: str, rang: int, *textes):
        vus = set()
        for t in textes:
            if isinstance(t, (list, tuple)):
                for x in t:
                    vus |= mots(x)
            else:
                vus |= mots(t)
        if vus:
            self.textes += 1
        for m in vus:
            self.renvois[m][fichier].append(rang)

    def tranches(self) -> dict[str, list]:
        par: dict[str, list] = defaultdict(list)
        for m in sorted(self.renvois):
            par[m[:2]].append(m)
        return par


# -- composer -------------------------------------------------------------------------------

def composer(ctx, ecr):
    if not _vue(ctx, "candidat"):
        return
    au = ctx.date_reference or dt.date.today().isoformat()
    commun = _commun(ctx, au)
    ident = {r["per"]: r for r in _lignes(ctx, "SELECT * FROM personne_identite")} \
        if _vue(ctx, "personne_identite") else {}
    for c in _lignes(ctx, "SELECT * FROM candidat WHERE publie AND adresse IS NOT NULL ORDER BY adresse"):
        _composer_un(ctx, ecr, c, ident.get(c["per"]), commun)


def _commun(ctx, au) -> dict:
    lic = {}
    for t in ("an_acteurs__mandat", "an_scrutins__scrutin", "an_dossiers__dossier",
              "an_amendements__amendement", "an_comptes_rendus__intervention", "an_questions__question",
              "senat_export__mandat", "wd_identifiants__identifiant_externe", "pe_eurodeputes__eurodepute", "pe_votes__vote_pe", "parltrack_votes__vote_pt",
              "parltrack_activites__activite_pt",
              "rne_elus__mandat_local",
              "wp_candidatures__candidature"):
        if _vue(ctx, t):
            for p, l in ctx.x(f"SELECT DISTINCT prov_point, licence FROM {t} WHERE prov_point IS NOT NULL"):
                if l:
                    lic[p] = l
    gouvs = {r["organe"]: r for r in _lignes(ctx, "SELECT organe, nom, adresse, debut, fin FROM gouvernement")} \
        if _vue(ctx, "gouvernement") else {}
    publies_g = set()
    if _vue(ctx, "gouvernement_legislature"):
        publies_g = {r[0] for r in ctx.x("SELECT DISTINCT gouvernement FROM gouvernement_legislature "
                                         "WHERE legislature IN (SELECT unnest(?::INTEGER[]))",
                                         [list(LEGISLATURES_GOUVERNEMENTS)])}
    legs = {r["numero"]: r for r in _lignes(ctx, "SELECT numero, debut, fin FROM legislature")} \
        if _vue(ctx, "legislature") else {}
    fiches = {f"legislature/{n}" for n in legs if n in LEGISLATURES_PUBLIEES}
    fiches |= {f"gouvernement/{gouvs[o]['adresse']}" for o in publies_g if o in gouvs}
    groupes = {r["organe"]: r for r in _lignes(ctx, "SELECT organe, sigle, libelle, legislature FROM groupe")} \
        if _vue(ctx, "groupe") else {}
    titres = {}
    if _vue(ctx, "an_dossiers__dossier"):
        titres = {u: t for u, t in ctx.x("SELECT uid, any_value(titre) FROM an_dossiers__dossier GROUP BY 1")}
    # Début de l'activité lue : la première législature du périmètre ; les paroles, à partir de la XVe.
    # (Si la source ne connaît pas l'une d'elles, la plus ancienne connue : le texte servi dit la date.)
    debut_activite = min((legs[n]["debut"] for n in LEGISLATURES if n in legs and legs[n]["debut"]),
                         default=None)
    debut_paroles = min((legs[n]["debut"] for n in LEGISLATURES if n >= PAROLES_DEPUIS and n in legs
                         and legs[n]["debut"]), default=None)
    # Exposés des amendements des candidats publiés (les seuls lus : 220 millions de caractères
    # pour toute l'archive).
    if not _vue(ctx, "amendement_canonique") or not _vue(ctx, "an_amendements__amendement"):
        ctx.x("""CREATE OR REPLACE TEMP TABLE _cand_exposes (amendement VARCHAR, expose VARCHAR,
                                                              a_dispositif BOOLEAN)""")
    else:
        ctx.x("""CREATE OR REPLACE TEMP TABLE _cand_exposes AS
            SELECT uid AS amendement, any_value(expose_sommaire) AS expose,
                   bool_or(dispositif IS NOT NULL) AS a_dispositif
            FROM an_amendements__amendement
            WHERE uid IN (SELECT amendement FROM amendement_canonique WHERE acteur IN
                          (SELECT acteur FROM candidat WHERE publie AND acteur IS NOT NULL))
            GROUP BY 1""")
    # Lignée publiée de chaque organe de groupe affiché (R-LIGNEE) : cible du lien « groupe actuel ».
    lignee_de = {}
    if _vue(ctx, "lignee_maillon") and _vue(ctx, "lignee"):
        lignee_de = {o: a for o, a in ctx.x("""
            SELECT unnest(m.organes), l.adresse FROM lignee_maillon m JOIN lignee l USING (lignee)
            WHERE l.publiee AND m.affiche""")}
    fiches |= {f"lignee/{a}" for a in lignee_de.values()}
    # Dernières lectures dont un vote plus récent sur l'ensemble n'a pu être relié (#34).
    posterieurs = {}
    if _vue(ctx, "derniere_lecture") and "votes_posterieurs_non_relies" in [c[0] for c in ctx.x("DESCRIBE derniere_lecture")]:
        posterieurs = {s: list(v) for s, v in ctx.x("""SELECT scrutin, flatten(list(votes_posterieurs_non_relies))
                                                         FROM derniere_lecture GROUP BY 1""") if v}
    return {"au": au, "lic": lic, "gouvs": gouvs, "publies_g": publies_g, "fiches": fiches,
            "groupes": groupes, "titres": titres, "debut_activite": debut_activite,
            "debut_paroles": debut_paroles, "legs": legs,
            "lignee_de": lignee_de, "posterieurs": posterieurs}


def _lien_gouv(organe, commun):
    g = commun["gouvs"].get(organe)
    if g and organe in commun["publies_g"]:
        return f"gouvernement/{g['adresse']}"
    return None


def _composer_un(ctx, ecr, c, ident, commun):
    au = commun["au"]
    nom = (" ".join(x for x in ((ident or {}).get("prenom"), (ident or {}).get("nom")) if x)
           if ident and ident.get("source_nom") not in ("wikipedia", "franceinfo") else None) or c["nom"]
    f = ecr.fiche("candidat", c["adresse"], titre=nom)
    acteur = c["acteur"] if c["acteur"] and c["acteur_connu_an"] else None
    perim = _perimetre(ctx, c, acteur, commun, commun["debut_activite"],
                       f"de la {plage()} législature")
    perim_paroles = _perimetre(ctx, c, acteur, commun, commun["debut_paroles"],
                               f"de la {plage(n for n in LEGISLATURES if n >= PAROLES_DEPUIS)} législature",
                               "Prises de parole en séance")
    idx = IndexMots()
    limites: list[dict] = []

    carriere, couv_car = _carriere(ctx, f, c, commun)
    periodes = _periodes(ctx, f, acteur, commun)
    fonctions = _fonctions(ctx, f, c, acteur, commun, couv_car)
    proposes = _proposes(ctx, f, acteur, perim, commun, idx)
    amend = _amendements(ctx, f, acteur, perim, commun, idx)
    votes = _votes(ctx, f, acteur, perim, commun, idx)
    div = _divergences(ctx, f, acteur, perim, commun)
    paroles = _paroles(ctx, f, acteur, perim_paroles, commun, idx)
    questions = _questions(ctx, f, acteur, perim, commun, idx)
    europe = _europe(ctx, f, c, carriere, commun)
    activite_pe = _activite_europe(ctx, f, c, carriere, commun)
    mots_info = _ecrire_mots(ecr, f, idx, au)

    # Limites de la fiche (section « Ce qu'on n'a pas pu lire »), en plus des couvertures.
    limites.append({"famille": "activite", "statut": perim["statut"], "detail": perim["detail"],
                    "raison": perim["raison"], "au": au})
    if perim_paroles["statut"] != perim["statut"]:
        limites.append({"famille": "paroles", "statut": perim_paroles["statut"],
                        "detail": perim_paroles["detail"], "raison": perim_paroles["raison"], "au": au})
    for inst in ("assemblee_avant_2002", "parlement_europeen", "local", "senat"):
        x = couv_car.get(inst)
        if inst == "senat" and not c["matricule_senat"]:
            continue
        if x and x["statut"] not in ("complet", "relu_aucun"):
            limites.append({"famille": f"carriere_{inst}", "statut": x["statut"], "detail": x["detail"],
                            "au": au})
    if c["matricule_senat"]:
        limites.append({"famille": "activite_senat", "statut": "non_collecte",
                        "detail": "L'activité au Sénat (votes, amendements, débats, questions) n'est "
                                  "pas collectée dans l'essai : seuls les mandats et fonctions de "
                                  "sénateur sont lus.", "au": au})
    dans = [p for p in periodes if p["legislature"] in LEGISLATURES]
    if dans and all(p["banc"] == "non_declaree" for p in dans):
        limites.append({"famille": "banc", "statut": "relu_aucun",
                        "detail": "Aucun des groupes de la personne ne déclare sa position (majorité, "
                                  "minorité, opposition) : le banc est « non déclaré », jamais déduit.",
                        "au": au})
    if europe:
        limites.append({"famille": "europe_votes", "statut": europe["statut"], "detail": europe["detail"],
                        "au": au})
        if activite_pe and activite_pe["statut"] not in ("complet", "relu_aucun"):
            limites.append({"famille": "europe_activite", "statut": activite_pe["statut"],
                            "detail": activite_pe["detail"], "au": au})

    compteurs = _compteurs(c, acteur, perim, carriere, couv_car, fonctions, proposes, amend, votes,
                           div, paroles, questions, au)
    for x in compteurs:
        ecr.fait_publie(f, "entete", "compte_candidat", x, {"acteur": "acteur", "autre": "famille"},
                        "au", None)

    personne = _personne(c, ident, commun)
    for l in personne.pop("_licences"):
        f.licences.add(l)
    # L'en-tête est un fait publié (issue #42, décision du 13/11/2026) : sa disparition est vue par
    # C1, et un champ qui se vide par l'avertissement A9. Reconnu à son numéro de personne (`per`),
    # jamais à sa valeur : un candidat sans identifiant parlementaire a aussi un `per`.
    ecr.fait_publie(f, "entete", "identite_personne", personne, {"autre": "per"}, None, None)
    f.entete({
        "personne": personne,
        "candidature": {
            "election": "presidentielle-2027", "statut": c["statut"],
            "parti": c["parti"],
            "date_declaration": c["date_declaration"],
            "date_declaration_texte": c["date_declaration_texte"],
            "raison_date_declaration": c["date_declaration_raison"],
            "date_declaration_source": "wikipedia" if c["date_declaration_source_url"] else None,
            "date_declaration_source_url": c["date_declaration_source_url"],
            "date_declaration_source_point": PA_WP if c["date_declaration_source_url"] else None,
            "revision_wikipedia": c["revision_wikipedia"],
            "article_frwiki": c["article_frwiki"], "article_url": c["article_url"],
            "element_wikidata": c["element_wikidata"], "element_url": c["element_url"],
            "rattachement": c["rattachement"], "raison_rattachement": c["raison_rattachement"],
            "rattachement_valide_par_decision": bool(c["rattachement_par_nom"]),
            "source": c["source_liste"], "source_url": c["source_url"], "source_titre": c["source_titre"],
            "source_lue_le": c["date_liste"], "decision": c["decision"],
            "note_licence": "liste recopiée de franceinfo (nom, statut, parti) et date reprise de "
                            "Wikipédia : des faits seulement, hors licence des données (cahier 2.2) ; "
                            "la page de franceinfo n'est pas collectée"},
        "groupe_actuel": _groupe_actuel(carriere, au, commun),
        "en_bref": {
            "carriere": {"colonnes": COLS_CARRIERE,
                         "lignes": [[l.get(k) for k in COLS_CARRIERE] for l in carriere],
                         "ordre": "chronologique", "au": au},
            "institutions": [couv_car[i] for i in INSTITUTIONS if i in couv_car],
            "compteurs": compteurs,
        },
        "periodes": {"colonnes": COLS_PERIODES, "lignes": [[p.get(k) for k in COLS_PERIODES] for p in periodes],
                     "ordre": "chronologique",
                     "definition": "une période change quand change le banc déclaré du groupe ou le "
                                   "gouvernement ; le banc n'est jamais déduit"},
        "perimetre_activite": perim,
        "filtres": {"mot": mots_info, "periode_mois": list(MOIS_FILTRE),
                    "periode_definition": "6 ou 12 derniers mois avant la date de référence, appliqués "
                                          "dans le navigateur sur les dates déjà chargées"},
        "limites": limites,
        "au": au, "date_reference": au,
        "regles": list(DEPEND),
    })


# -- en-tête : personne, carrière, groupe actuel -------------------------------------------

COLS_CARRIERE = ["institution", "debut", "fin", "libelle", "etat", "legislature", "gouvernement",
                 "gouvernement_nom", "qualite", "groupe", "groupe_sigle", "groupe_libelle",
                 "groupe_statut", "siege", "siege_date", "raison_siege", "lien", "raison_lien",
                 "circonscription", "cause_fin", "fin_raison", "mandat", "source", "source_url",
                 "licence"]
COLS_PERIODES = ["periode", "debut", "fin", "legislature", "banc", "raisons_banc", "gouvernement",
                 "gouvernement_nom", "lien", "dans_le_perimetre"]


def _personne(c, ident, commun) -> dict:
    lic = commun["lic"]
    licences = set()
    i = ident or {}
    src = {"an": PA_AMO, "senat": PA_SENAT, "wikidata": PA_WD, "wikipedia": PA_WP, "franceinfo": None}
    def champ(valeur, source, raison=None):
        if source in ("an", "senat", "wikidata") and lic.get(src[source]):
            licences.add(lic[src[source]])
        return {"valeur": valeur, "source": source, "source_point": src.get(source), "raison": raison}
    return {
        "per": c["per"], "nom": i.get("nom") or c["nom"], "prenom": i.get("prenom"),
        "nom_affiche": c["nom"], "civilite": i.get("civilite"),
        "profession": champ(i.get("profession"), i.get("source_profession"), i.get("raison_profession")),
        "naissance": {**champ(i.get("naissance"), i.get("source_naissance"), i.get("raison_naissance")),
                      "lieu": i.get("lieu_naissance"), "source_lieu": i.get("source_lieu_naissance"),
                      "raison_lieu": i.get("raison_lieu_naissance"),
                      "concordance": i.get("naissance_concordance")},
        "deces": i.get("deces"),
        "source_nom": i.get("source_nom") or "wikipedia",
        "source_url": i.get("source_url") or c["article_url"],
        "source_url_wikipedia": i.get("source_url_wikipedia") or c["article_url"],
        "source_url_wikidata": i.get("source_url_wikidata") or c["element_url"],
        "acteur": c["acteur"], "matricule_senat": c["matricule_senat"], "sycomore": c["sycomore"],
        "identifiants_source": "déclarés par Wikidata (P4123 Assemblée, P1808 Sénat), jamais rapprochés par le nom",
        "_licences": licences,
    }


def _carriere(ctx, f, c, commun):
    au = commun["au"]
    lic_an = commun["lic"].get(PA_AMO)
    lignes = _lignes(ctx, "SELECT * FROM carriere WHERE per = ? ORDER BY debut, institution",
                     [c["per"]]) if _vue(ctx, "carriere") else []
    for l in lignes:
        lien = l.get("lien")
        l["raison_lien"] = None
        if lien and lien not in commun["fiches"]:
            l["lien"], l["raison_lien"] = None, "fiche non publiée"
        elif not lien:
            l["raison_lien"] = ("législature sans fiche publiée dans l'essai" if l["institution"] == "assemblee"
                                else "gouvernement sans fiche publiée dans l'essai" if l["institution"] == "gouvernement"
                                else "pas de fiche pour cette institution dans l'essai")
        g = commun["gouvs"].get(l.get("gouvernement"))
        l["gouvernement_nom"] = g["nom"] if g else None
        l["licence"] = (lic_an if l.get("source") == "an" else commun["lic"].get(PA_PE)
                        if l.get("source") == "pe" else commun["lic"].get(PA_RNE)
                        if l.get("source") == "rne" else None
                        if l.get("source") == "sycomore" else commun["lic"].get(PA_SENAT))
        if l["licence"]:
            f.licences.add(l["licence"])
        ecr_ids = {"acteur": "acteur", "mandat": "mandat", "organe": "groupe"}
        f.ecr.fait_publie(f, "entete", "periode_carriere", l, ecr_ids, "debut", "source_url")
    couv = {}
    if _vue(ctx, "couverture_carriere"):
        for r in _lignes(ctx, "SELECT * FROM couverture_carriere WHERE per = ?", [c["per"]]):
            inst = r["institution"]
            pts = {"assemblee": [PA_AMO], "assemblee_avant_2002": [], "gouvernement": [PA_AMO],
                   "senat": [PA_SENAT]}.get(inst, [])
            ls = [l for l in lignes if l["institution"] == inst]
            couv[inst] = {"institution": inst, "libelle": LIBELLE_INSTITUTION.get(inst, inst),
                          "statut": STATUT_CARRIERE.get(r["statut"], "non_relu"),
                          "statut_regle": r["statut"], "detail": r["detail"], "depuis": r["depuis"],
                          "periodes": len(ls),
                          "premier_debut": min((l["debut"] for l in ls), default=None),
                          "derniere_fin": None if any(l["fin"] is None for l in ls)
                          else max((l["fin"] for l in ls), default=None),
                          "points_acces": pts, "au": au}
    return lignes, couv


def _groupe_actuel(carriere, au, commun=None) -> dict:
    cours = [l for l in carriere if l["institution"] in ("assemblee", "senat")
             and l["etat"] == "en_fonction" and l["fin"] is None]
    if not cours:
        return {"statut": "aucun_mandat_en_cours", "groupe": None, "sigle": None, "libelle": None,
                "detail": "Aucun mandat parlementaire en cours le " + _fr(au) + " dans nos sources.",
                "au": au}
    l = max(cours, key=lambda x: x["debut"])
    adresse = ((commun or {}).get("lignee_de") or {}).get(l["groupe"]) if l["institution"] == "assemblee" else None
    raison = (None if adresse else
              "groupe du Sénat : pas de fiche de groupe" if l["institution"] == "senat" else
              "aucun groupe à cette date (non-inscrit ou appartenance non établie)" if not l["groupe"] else
              "groupe sans lignée publiée")
    return {"statut": l["groupe_statut"], "groupe": l["groupe"], "sigle": l["groupe_sigle"],
            "libelle": l["groupe_libelle"], "institution": l["institution"], "depuis": l["debut"],
            "lien": f"lignee/{adresse}" if adresse else None, "raison_lien": raison,
            "source_url": l["source_url"], "au": au}


def _periodes(ctx, f, acteur, commun) -> list[dict]:
    if not acteur or not _vue(ctx, "periode_position"):
        return []
    out = []
    for p in _lignes(ctx, """SELECT periode, debut, fin, legislature, banc, raisons_banc, gouvernement
                             FROM periode_position WHERE acteur = ? ORDER BY debut""", [acteur]):
        g = commun["gouvs"].get(p["gouvernement"])
        p["gouvernement_nom"] = g["nom"] if g else None
        p["lien"] = _lien_gouv(p["gouvernement"], commun)
        p["dans_le_perimetre"] = p["legislature"] in LEGISLATURES
        p["raisons_banc"] = list(p["raisons_banc"] or [])
        p["acteur"] = acteur
        out.append(p)
        f.ecr.fait_publie(f, "entete", "periode_position", p, {"acteur": "acteur", "autre": "periode",
                                                              "organe": "gouvernement"}, "debut", None)
    return out


def _perimetre(ctx, c, acteur, commun, depuis, plage_txt, quoi="Activité") -> dict:
    """Couverture de l'activité de la personne lue depuis `depuis` (textes, amendements, votes,
    questions : début de la XIVe ; paroles : début de la XVe)."""
    au = commun["au"]
    pts = [PA_AMO]
    vide = {"jours_dans_le_perimetre": None, "jours_total": None, "points_acces": pts, "depuis": depuis}
    if not c["acteur"]:
        if c["matricule_senat"]:
            return {"statut": "hors_perimetre", "raison": "aucun_identifiant_assemblee",
                    "detail": "Aucun identifiant de l'Assemblée nationale n'est déclaré pour cette "
                              "personne : l'activité de l'Assemblée ne la concerne pas. Son activité "
                              "de sénateur n'est pas collectée.", **vide}
        detail = {
            "aucun_element": "La liste n'inscrit aucun élément Wikidata pour ce nom : aucun identifiant "
                             "parlementaire n'est connu, et rien n'est rattaché par le nom. Il n'y a "
                             "ni vote, ni amendement, ni prise de parole à publier.",
            "non_etabli": "Identité non établie (" + str(c["raison_rattachement"]) + ") : aucune "
                          "activité n'est rattachée.",
        }.get(c["rattachement"], "Nos sources ne connaissent aucun mandat parlementaire de cette "
                                 "personne : Wikidata ne lui déclare aucun identifiant de l'Assemblée "
                                 "nationale ni du Sénat. Il n'y a donc ni vote, ni amendement, ni prise "
                                 "de parole à publier.")
        return {"statut": "hors_perimetre", "raison": "aucun_identifiant_parlementaire",
                "detail": detail, **vide}
    if not acteur:
        return {"statut": "trou_source", "raison": "identifiant_absent_de_la_source",
                "detail": f"L'identifiant déclaré par Wikidata ({c['acteur']}) est absent de l'archive "
                          "de l'Assemblée : aucune activité n'est lue.", **vide}
    # Jours où la personne siège ou est au gouvernement (carrière), depuis 2002 et dans le périmètre.
    iv = []
    if _vue(ctx, "carriere"):
        for d0, d1 in ctx.x("""SELECT debut, fin FROM carriere WHERE per = ? AND etat = 'en_fonction'
                               AND institution IN ('assemblee', 'gouvernement')""", [c["per"]]):
            iv.append((_jour(d0), _jour(d1) if d1 else _jour(au)))
    fin = _jour(au)
    total = _jours_union(iv, jusqu_a=fin)
    dans = _jours_union(iv, depuis=_jour(depuis), jusqu_a=fin) if depuis else None
    anterieur = any(d0 < _jour(depuis) for d0, _ in iv) if depuis else False
    base = (f"{quoi} lue{'s' if quoi != 'Activité' else ''} {plage_txt} (depuis le {_fr(depuis)}), "
            "à l'Assemblée nationale.")
    if quoi == "Activité":
        base = (f"Activité lue {plage_txt} (depuis le {_fr(depuis)}) : votes, amendements, textes et "
                "questions de l'Assemblée nationale.")
    if anterieur:
        detail = (base + f" Mandats et fonctions antérieurs ({total - (dans or 0)} jours depuis le "
                  "19/06/2002) : leur activité est hors du périmètre, rien n'est compté pour eux.")
        if not dans:
            detail += f" Aucun mandat ni fonction depuis le {_fr(depuis)} : rien n'est compté."
        # Lue en partie (mandats avant et depuis le début du périmètre) : `partiel` ; rien depuis :
        # `hors_perimetre`.
        return {"statut": "partiel" if dans else "hors_perimetre",
                "raison": "activite_anterieure_au_perimetre", "detail": detail,
                "jours_dans_le_perimetre": dans, "jours_total": total, "points_acces": pts,
                "depuis": depuis, "statut_comptes": "complet" if dans else "hors_perimetre"}
    return {"statut": "complet", "raison": None, "detail": base, "jours_dans_le_perimetre": dans,
            "jours_total": total, "points_acces": pts, "depuis": depuis, "statut_comptes": "complet"}


def _st(perim) -> str:
    """Statut des comptes d'activité, pris sur le seul périmètre : complet si la personne a siégé ou
    été au gouvernement depuis son début ; sinon aucun compte (pas même 0)."""
    return perim.get("statut_comptes") or perim["statut"]


def _couv_activite(famille, perim, phrase, n, d, points, au, **extra):
    """Couverture d'une section d'activité : le statut est celui du périmètre de la personne
    (complet, hors périmètre pour une activité antérieure, aucun identifiant parlementaire…) ; la
    phrase et les chiffres disent ce qui est établi dans le périmètre."""
    statut = perim["statut"]
    detail = (perim["detail"] + " " + phrase).strip() if statut != "complet" else phrase
    return _couv(famille, statut, detail, n, d, points, au=au, perimetre=f"depuis le {_fr(perim.get('depuis'))}",
                 raison=perim["raison"], **extra)


# -- les fonctions exercées -----------------------------------------------------------------

COLS_FONCTIONS = ["famille", "libelle_famille", "rang_famille", "organe", "libelle", "qualite",
                  "qualite_distinctive", "debut", "fin", "en_cours", "duree_jours", "duree_calculee_au",
                  "raison_duree", "duree_organe_jours", "chambre", "legislature", "type_organe",
                  "nb_periodes_fusionnees", "plus_long_trou_fusionne_jours", "nb_mandats_source",
                  "acteur", "source_url", "licence"]
COLS_FONCTIONS_PERIODES = ["famille", "organe", "libelle", "qualite", "debut", "fin", "legislature",
                           "chambre", "type_organe", "mandat", "acteur", "source_url", "licence"]


def _fonctions(ctx, f, c, acteur, commun, couv_car) -> dict:
    au = commun["au"]
    pts = [PA_AMO] + ([PA_SENAT] if c["matricule_senat"] else [])
    if not _vue(ctx, "fonction_personne"):
        cv = _absente("fonctions", ["fonction_personne"], pts, au)
        f.section("fonctions", [], "fonction", couverture=cv, colonnes=COLS_FONCTIONS)
        return {"lignes": [], "statut": cv["statut"]}
    lignes = _lignes(ctx, """SELECT * FROM fonction_personne WHERE per = ?
                             ORDER BY rang_famille, famille, debut, organe, qualite""", [c["per"]])
    for l in lignes:
        l["licence"] = commun["lic"].get(PA_SENAT if l["chambre"] == "senat" else PA_AMO)
    duree = sum(1 for l in lignes if l["duree_jours"] is not None)
    an = couv_car.get("assemblee", {}).get("statut")
    sen = couv_car.get("senat", {}).get("statut")
    if not c["acteur"] and not c["matricule_senat"]:
        statut, detail = "hors_perimetre", ("Aucun identifiant parlementaire déclaré : nos sources ne "
                                             "connaissent aucune fonction au Parlement.")
    else:
        statut = "complet" if an in ("complet", "relu_aucun", None) else an
        detail = (f"Fonctions dans les organes de l'Assemblée depuis le 19/06/2002"
                  + (" et du Sénat" if c["matricule_senat"] else "") + " ; avant 2002 : hors source. "
                  f"Durée établie pour {duree} fonctions sur {len(lignes)} (une fonction ouverte "
                  "commencée avant le mandat en cours n'a pas de fin publiée). Les permutations de "
                  "commission de 3 jours au plus sont fusionnées ; le détail des mandats est à part.")
        if any((l["debut"] or "") <= "2002-06-19" for l in lignes):
            statut = "borne_historique"
        if sen == "non_collecte":
            detail += " Export du Sénat non collecté : fonctions de sénateur absentes."
    familles = defaultdict(lambda: {"organes": set(), "lignes": 0})
    for l in lignes:
        familles[(l["rang_famille"], l["famille"], l["libelle_famille"])]["organes"].add(l["organe"])
        familles[(l["rang_famille"], l["famille"], l["libelle_famille"])]["lignes"] += 1
    resume = [{"famille": k[1], "libelle_famille": k[2], "nb_intitules": len(v["organes"]),
               "nb_lignes": v["lignes"], "au": au} for k, v in sorted(familles.items())]
    cv = _couv("fonctions", statut, detail, duree, len(lignes), pts, au=au)
    f.section("fonctions", lignes, "fonction", ids={"acteur": "acteur", "organe": "organe"},
              date="debut", couverture=cv, colonnes=COLS_FONCTIONS,
              extra={"ordre": "famille (rang publié), puis chronologique", "familles": resume,
                     "detail_dans": "fonctions-periodes.json.gz"})
    det = _lignes(ctx, """SELECT * FROM fonction_periode WHERE per = ?
                          ORDER BY rang_famille, organe, debut, mandat""", [c["per"]]) \
        if _vue(ctx, "fonction_periode") else []
    for l in det:
        l["licence"] = commun["lic"].get(PA_SENAT if l["chambre"] == "senat" else PA_AMO)
    f.section("fonctions-periodes", det, "fonction_mandat_source",
              ids={"acteur": "acteur", "organe": "organe", "mandat": "mandat"}, date="debut",
              couverture=_couv("fonctions", statut, "Un mandat d'organe de la source par ligne, sans "
                               "fusion.", len(det), len(det), pts, au=au),
              colonnes=COLS_FONCTIONS_PERIODES, extra={"ordre": "famille, organe, chronologique"})
    return {"lignes": lignes, "statut": statut}


# -- ce qu'il a proposé ---------------------------------------------------------------------

COLS_TEXTES = ["dossier", "document", "titre", "role", "qualite_rapporteur", "nature", "nature_code",
               "date_depot", "date_role", "chambre", "etape_atteinte", "date_etape", "sort",
               "raison_sort", "par_49_3", "adopte_par_49_3", "matiere", "matiere_statut",
               "matiere_libelle", "gouvernement", "gouvernement_nom", "lien", "acteur", "source_url",
               "licence"]


def _proposes(ctx, f, acteur, perim, commun, idx) -> dict:
    au, d0 = commun["au"], commun["debut_activite"]
    pts = points("dossiers")
    if not _vue(ctx, "texte_porte"):
        f.section("proposes", [], "texte_porte", couverture=_absente("textes", ["texte_porte"], pts, au))
        return {"publies": None, "statut": "non_relu"}
    toutes = _lignes(ctx, "SELECT * FROM texte_porte WHERE acteur = ? ORDER BY date_depot, dossier, role",
                     [acteur]) if acteur else []
    avant = [t for t in toutes if (t["date_role"] or t["date_depot"] or "") < (d0 or "")]
    dans = [t for t in toutes if (t["date_role"] or t["date_depot"] or "") >= (d0 or "")]
    lignes = [t for t in dans if t["publiable"]]
    for t in lignes:
        t["licence"] = commun["lic"].get(PA_DOSSIERS)
        t["titre"] = t["titre"] or commun["titres"].get(t["dossier"])
        g = commun["gouvs"].get(t["gouvernement"])
        t["gouvernement_nom"] = g["nom"] if g else None
        t["lien"] = _lien_gouv(t["gouvernement"], commun)
    lignes.sort(key=lambda t: (t["date_depot"] or "", t["dossier"] or "", t["role"]))
    for k, t in enumerate(lignes):
        idx.ajouter("proposes", k, t["titre"])
    ecartes = defaultdict(int)
    for t in dans:
        if not t["publiable"]:
            ecartes[t["raison_non_publiable"] or "non_publiable"] += 1
    mat = sum(1 for t in lignes if t["matiere_statut"] in ("assemblee", "senat_seulement"))
    phrase = (f"Textes portés (auteur, cosignataire, rapporteur ; initiative gouvernementale pour un "
              f"projet de loi) publiés à partir de leur examen en commission : {len(lignes)}. "
              f"Écartés : {ecartes.get('pas_encore_examine_en_commission', 0)} pas encore examinés en "
              f"commission, {ecartes.get('cosignature_retiree', 0)} cosignatures retirées, "
              f"{ecartes.get('etape_non_etablie', 0)} à l'étape non établie. Matière établie pour "
              f"{mat} sur {len(lignes)}.")
    if avant:
        phrase += (f" {len(avant)} textes portés antérieurs au {_fr(d0)}, présents dans l'archive, "
                   "sont écartés (hors périmètre).")
    cv = _couv_activite("textes", perim, phrase, mat, len(lignes), pts, au,
                        selection={"publies": len(lignes), "ecartes": dict(sorted(ecartes.items())),
                                   "anterieurs_au_perimetre": len(avant)})
    f.section("proposes", lignes, "texte_porte",
              ids={"acteur": "acteur", "dossier": "dossier", "document": "document", "organe": "matiere"},
              date="date_depot", couverture=cv, colonnes=COLS_TEXTES,
              extra={"ordre": "chronologique (date de dépôt)", "aide_a_la_lecture": ["matiere_libelle"],
                     "roles": {"auteur": "auteur d'une proposition (loi ou résolution)",
                               "cosignataire": "cosignataire d'une proposition",
                               "rapporteur": "nommé rapporteur du texte",
                               "initiative_gouvernementale": "projet de loi déposé au nom du "
                               "gouvernement : jamais un acte personnel du ministre"},
                     "note_49_3": "par_49_3 : le gouvernement a engagé sa responsabilité sur le texte "
                                  "(fait de procédure, jamais une position de vote)", "au": au})
    st = _st(perim)
    par_role = defaultdict(int)
    for t in lignes:
        par_role[t["role"]] += 1
    return {"publies": _compte(len(lignes), st), "statut": st,
            "par_role": {r: _compte(par_role.get(r, 0), st) for r in
                         ("auteur", "rapporteur", "cosignataire", "initiative_gouvernementale")}}


COLS_AMENDEMENTS = ["amendement", "numero_long", "date_depot", "sort", "famille_sort", "sort_source",
                    "commission", "commission_libelle", "raison_commission", "dossier", "titre_dossier",
                    "document", "article_designation", "sous_amendement", "banc_au_depot",
                    "nb_cosignataires_liste", "expose_fichier", "expose_ligne", "raison_sans_expose",
                    "acteur", "source_url", "raison_source_url", "licence"]
COLS_AGREGATS = ["commission", "commission_libelle", "annee", "nb_amendements", "nb_dossiers_distincts",
                 "nb_irrecevables_40", "nb_irrecevables_45", "nb_signatures_cosignataire", "au",
                 "source_url", "licence"]


def _amendements(ctx, f, acteur, perim, commun, idx) -> dict:
    au = commun["au"]
    pts = points("amendements")
    lic = commun["lic"].get(PA_AMENDEMENTS)
    if not _vue(ctx, "amendement_canonique"):
        f.section("amendements", [], "amendements_compte",
                  couverture=_absente("amendements", ["amendement_canonique"], pts, au))
        return {"auteur": None, "statut": "non_relu"}
    lignes = _lignes(ctx, """
        SELECT a.*, e.expose AS _expose, e.a_dispositif AS _a_dispositif
        FROM amendement_canonique a LEFT JOIN _cand_exposes e USING (amendement)
        WHERE a.acteur = ? ORDER BY a.date_depot, a.amendement""", [acteur]) if acteur else []
    sig = _lignes(ctx, """SELECT amendement, date_depot, commission, dossier FROM amendement_auteur
                          WHERE acteur = ? AND role = 'cosignataire'""", [acteur]) \
        if acteur and _vue(ctx, "amendement_auteur") else []
    lib_com = {}
    for l in lignes:
        l["titre_dossier"] = commun["titres"].get(l["dossier"])
        l["licence"] = lic
        l["annee"] = (l["date_depot"] or "")[:4] or None
        lib_com[l["commission"]] = l["commission_libelle"]
    # Exposés : en texte, par année puis par paquets ; la liste renvoie à leur fichier et rang.
    exposes = []
    for l in lignes:
        t = texte_brut(l.pop("_expose"))
        a_disp = l.pop("_a_dispositif")
        l["raison_sans_expose"] = None if t else ("ni exposé ni dispositif publiés" if not a_disp
                                                   else "exposé non publié")
        if t:
            exposes.append({"amendement": l["amendement"], "date_depot": l["date_depot"],
                            "expose": t, "acteur": acteur, "source_url": None, "licence": lic, "_l": l})
    ecrits = _decouper(exposes, lambda x: (x["date_depot"] or "sans-date")[:4], "exposes",
                       taille=lambda x: len(x["expose"]) + 120)
    for nom, annee, ls in ecrits:
        for k, x in enumerate(ls):
            x["_l"]["expose_fichier"], x["_l"]["expose_ligne"] = f"{nom}.json.gz", k
            idx.ajouter(nom, k, x["expose"])
        lignes_s = [{k2: v for k2, v in x.items() if k2 != "_l"} for x in ls]
        f.section(nom, lignes_s, "expose_amendement", ids={"acteur": "acteur", "amendement": "amendement"},
                  date="date_depot",
                  couverture=_couv("amendements", "complet", f"Exposés sommaires des amendements de "
                                   f"{annee} dont la personne est l'auteur principal, en texte.",
                                   len(ls), len(ls), points_de_l_annee(ctx, pts, annee), au=au),
                  colonnes=["amendement", "date_depot", "expose", "acteur", "source_url", "licence"],
                  extra={"annee": annee})
    sans = sum(1 for l in lignes if l["raison_sans_expose"])
    # Listes par année (sans exposé), chargées au clic.
    fichiers_annee = {}
    for nom, annee, ls in _decouper(lignes, lambda x: x["annee"] or "sans-date", "amendements",
                                    taille=lambda x: _taille([x.get(k) for k in COLS_AMENDEMENTS])):
        fichiers_annee.setdefault(annee, []).append(f"{nom}.json.gz")
        titres = {l["dossier"]: l["titre_dossier"] for l in ls if l["dossier"]}
        f.section(nom, ls, "amendement",
                  ids={"acteur": "acteur", "amendement": "amendement", "dossier": "dossier",
                       "document": "document", "organe": "commission"},
                  date="date_depot",
                  couverture=_couv("amendements", "complet", f"Amendements déposés en {annee} dont la "
                                   "personne est l'auteur principal (copies dédoublonnées), avec l'adresse "
                                   "de sa page sur le site de l'Assemblée.", len(ls), len(ls),
                                   points_de_l_annee(ctx, pts, annee), au=au),
                  colonnes=COLS_AMENDEMENTS,
                  extra={"annee": annee, "dossiers": titres, "ordre": "chronologique",
                         "aide_a_la_lecture": ["commission_libelle"]})
    # Décomptes par commission et par année ; irrecevables 40 et 45 et signatures à part.
    agr: dict[tuple, dict] = {}

    def cle(com, annee):
        k = (com, annee)
        if k not in agr:
            agr[k] = {"commission": com, "commission_libelle": lib_com.get(com) if com else "Commission non établie",
                      "annee": annee, "nb_amendements": 0, "_dossiers": set(), "nb_irrecevables_40": 0,
                      "nb_irrecevables_45": 0, "nb_signatures_cosignataire": 0, "au": au,
                      "source_url": None, "licence": lic}
        return agr[k]
    for l in lignes:
        x = cle(l["commission"], l["annee"])
        if l["famille_sort"] == "irrecevable_40":
            x["nb_irrecevables_40"] += 1
        elif l["famille_sort"] == "irrecevable_45":
            x["nb_irrecevables_45"] += 1
        else:
            x["nb_amendements"] += 1
            if l["dossier"]:
                x["_dossiers"].add(l["dossier"])
    for s in sig:
        if s["commission"] not in lib_com:
            lib_com[s["commission"]] = None
        cle(s["commission"], (s["date_depot"] or "")[:4] or None)["nb_signatures_cosignataire"] += 1
    if _vue(ctx, "amendement_canonique") and any(v is None for k, v in lib_com.items() if k):
        manquants = [k for k, v in lib_com.items() if k and v is None]
        for k, v in ctx.x("""SELECT commission, any_value(commission_libelle) FROM amendement_canonique
                             WHERE commission IN (SELECT unnest(?::VARCHAR[])) GROUP BY 1""", [manquants]):
            lib_com[k] = v
        for x in agr.values():
            if x["commission"] and x["commission_libelle"] is None:
                x["commission_libelle"] = lib_com.get(x["commission"])
    agregats = []
    for x in sorted(agr.values(), key=lambda x: (x["commission"] is None, (x["commission_libelle"] or "").lower(),
                                                 x["annee"] or "")):
        x["nb_dossiers_distincts"] = len(x.pop("_dossiers"))
        agregats.append(x)
    hors_irr = [l for l in lignes if l["famille_sort"] not in ("irrecevable_40", "irrecevable_45")]
    i40 = sum(1 for l in lignes if l["famille_sort"] == "irrecevable_40")
    i45 = sum(1 for l in lignes if l["famille_sort"] == "irrecevable_45")
    com = sum(1 for l in lignes if l["commission"])
    phrase = (f"Amendements dont la personne est l'auteur principal, comptés une fois (copies B/BTC "
              f"dédoublonnées) : {len(hors_irr)}, plus {i40} irrecevables au titre de l'article 40 et "
              f"{i45} au titre de l'article 45, comptés à part. Signatures comme cosignataire comptées à "
              f"part : {len(sig)}. Commission établie pour {com} sur {len(lignes)}. Aucun taux "
              f"d'adoption n'est calculé. {sans} amendements sans exposé publié ne sont pas trouvables "
              "par le filtre par mot.")
    cv = _couv_activite("amendements", perim, phrase, com, len(lignes), pts, au,
                        distincts={"amendements": len(hors_irr),
                                   "dossiers": len({l["dossier"] for l in hors_irr if l["dossier"]})},
                        sans_expose=sans)
    f.section("amendements", agregats, "amendements_compte", ids={"organe": "commission", "autre": "annee"},
              date="au", source=None, couverture=cv, colonnes=COLS_AGREGATS,
              extra={"ordre": "commission (alphabétique), puis année", "listes": fichiers_annee,
                     "exposes": [f"{n}.json.gz" for n, _, _ in ecrits],
                     "aide_a_la_lecture": ["commission_libelle"],
                     "definitions": {
                         "nb_amendements": "amendements dont la personne est l'auteur principal, hors "
                                           "irrecevables des articles 40 et 45",
                         "nb_signatures_cosignataire": "amendements d'un autre auteur que la personne a "
                                                       "cosignés (signatures, pas des amendements à elle)"},
                     "au": au})
    st = _st(perim)
    return {"auteur": _compte(len(hors_irr), st), "irrecevables_40": _compte(i40, st),
            "irrecevables_45": _compte(i45, st), "signatures": _compte(len(sig), st), "statut": st}


# -- ce qu'il a voté ------------------------------------------------------------------------

def _trous_votes(ctx, acteur, depuis) -> list[dict]:
    """Trous de l'archive des scrutins (R-CONTINUITE-SCRUTINS) pendant un mandat de député de la
    personne, dans le périmètre lu : ses votes de ces jours-là manquent à la source."""
    if not acteur or not _vue(ctx, "carriere"):
        return []
    from ..regles.r_continuite_scrutins import couvre, trous
    iv = ctx.x("""SELECT debut, fin FROM carriere WHERE acteur = ? AND etat = 'en_fonction'
                  AND institution = 'assemblee'""", [acteur])
    return [t for t in trous(ctx)
            if any(couvre(t, max(d0 or "", depuis or ""), d1) for d0, d1 in iv)]


COLS_VOTES = ["scrutin", "numero", "date", "dossier", "titre_dossier", "intitule", "lecture", "position",
              "cause_non_votant", "par_delegation", "mise_au_point", "matiere", "matiere_statut",
              "matiere_libelle", "origine", "type_texte", "sort_final", "dossier_par_49_3", "groupe",
              "groupe_sigle", "periode", "gouvernement", "banc", "solennel", "votes_posterieurs_non_relies",
              "acteur", "source_url", "licence"]


def _votes(ctx, f, acteur, perim, commun, idx) -> dict:
    au = commun["au"]
    pts = points("scrutins") + points("dossiers")
    lic = commun["lic"].get(PA_SCRUTINS)
    if not _vue(ctx, "vote_personne"):
        cv = _absente("votes", ["vote_personne"], pts, au)
        f.section("votes", [], "position_texte", couverture=cv)
        f.section("votes-motions", [], "position_motion", couverture=cv)
        return {"positions": None, "motions": None, "statut": "non_relu"}
    rows = _lignes(ctx, """SELECT *, par_49_3 AS dossier_par_49_3 FROM vote_personne
                           WHERE acteur = ? AND date >= ? ORDER BY date, scrutin""",
                   [acteur, commun["debut_activite"] or ""]) if acteur else []
    for r in rows:
        r["licence"] = lic
        r["groupe_sigle"] = (commun["groupes"].get(r["groupe"]) or {}).get("sigle")
        r["titre_dossier"] = r["titre_dossier"] or commun["titres"].get(r["dossier"])
        r["votes_posterieurs_non_relies"] = commun["posterieurs"].get(r["scrutin"])
        r["dossiers"] = list(r["dossiers"]) if r.get("dossiers") is not None else None
    ens = [r for r in rows if r["nature"] == "ensemble"]
    mot = [r for r in rows if r["nature"] == "motion_censure"]
    for k, r in enumerate(ens):
        idx.ajouter("votes", k, r["titre_dossier"], r["intitule"])
    for k, r in enumerate(mot):
        idx.ajouter("votes-motions", k, r["intitule"])
    mat = sum(1 for r in ens if r["matiere_statut"] in ("assemblee", "senat_seulement"))
    sort = sum(1 for r in ens if r["sort_final"] not in (None, "non_connu"))
    per = sum(1 for r in ens if r["periode"])
    phrase = (f"Une position par texte : celle du dernier vote sur l'ensemble (dernière lecture, choisie "
              f"sur tous les scrutins du texte), telle que l'Assemblée la publie en nommant la personne "
              f"({len(ens)} textes). Matière établie pour {mat}, sort final connu pour {sort}, période "
              f"établie pour {per}. Une personne non nommée n'a pas de position, jamais déduite. Un 49.3 "
              "n'est jamais une position : le texte est seulement signalé (dossier_par_49_3).")
    ts = _trous_votes(ctx, acteur, commun["debut_activite"])
    cv = marquer_trous(_couv_activite("votes", perim, phrase, mat, len(ens), pts, au,
                                      sort_final_connu=[sort, len(ens)], periode_etablie=[per, len(ens)]), ts)
    extra = {"ordre": "chronologique ; regroupées par période (voir l'en-tête : periodes)",
             "aide_a_la_lecture": ["matiere_libelle"], "au": au,
             "note_49_3": "dossier_par_49_3 : le gouvernement a engagé sa responsabilité sur ce texte "
                          "(fait de procédure, jamais une position de vote)"}
    ids = {"acteur": "acteur", "scrutin": "scrutin", "dossier": "dossier", "organe": "groupe",
           "autre": "periode"}
    f.section("votes", ens, "position_texte", ids=ids, date="date", couverture=cv, colonnes=COLS_VOTES,
              extra=extra)
    cvm = marquer_trous(_couv_activite("votes", perim, f"Motions de censure mises aux voix ({len(mot)} positions "
                                       "nommées) : présentées à part, jamais comptées parmi les positions sur un texte.",
                                       len(mot), len(mot), points("scrutins"), au), ts)
    f.section("votes-motions", mot, "position_motion", ids=ids, date="date", couverture=cvm,
              colonnes=COLS_VOTES + ["dossiers"], extra={"ordre": "chronologique", "au": au})
    # Un trou de la source pendant un mandat : un compte nul n'est pas servi (règle 5).
    st = "trou_source" if ts and _st(perim) == "complet" else _st(perim)
    return {"positions": _compte(len(ens), st), "motions": _compte(len(mot), st), "statut": st}


COLS_DIVERGENCES = ["scrutin", "date", "dossier", "titre_dossier", "position", "position_groupe",
                    "diverge", "groupe", "sigle", "groupe_divise", "groupe_pour", "groupe_contre",
                    "groupe_abstentions", "groupe_non_votants", "groupe_membres",
                    "groupe_scrutin_different", "matiere", "matiere_libelle", "sort_final", "origine",
                    "periode", "votes_posterieurs_non_relies", "acteur", "source_url", "licence"]


def _exclusions(ctx, acteur, depuis) -> dict:
    """Positions en dernière lecture écartées de la comparaison, par raison (mêmes conditions que
    R-DIVERGENCE, qui ne sert que les comparaisons retenues)."""
    from ..regles.r_divergence import LEGISLATURES_AVEC_FICHE, POSITIONS
    if not _vue(ctx, "an_scrutins__decompte_groupe") or not _vue(ctx, "groupe"):
        return {}
    legs = ", ".join(str(x) for x in LEGISLATURES_AVEC_FICHE)
    # Même condition 5 que R-DIVERGENCE : le groupe appartient à une lignée publiée.
    avec_fiche = ("AND g.organe IN (SELECT unnest(m.organes) FROM lignee_maillon m "
                  "JOIN lignee l USING (lignee) WHERE l.publiee AND m.affiche)"
                  if _vue(ctx, "lignee_maillon") else "")
    rows = ctx.x(f"""
        WITH v AS (SELECT * FROM vote_personne WHERE acteur = ? AND nature = 'ensemble' AND date >= ?),
        dg AS (SELECT scrutin, organe AS groupe,
                      CASE WHEN count(DISTINCT position_majoritaire) = 1 THEN any_value(position_majoritaire) END AS pg,
                      any_value(pour) AS pour, any_value(contre) AS contre, any_value(abstentions) AS abst
               FROM an_scrutins__decompte_groupe
               WHERE organe <> 'PO0' AND scrutin IN (SELECT scrutin FROM v) GROUP BY 1, 2)
        SELECT CASE WHEN v.position NOT IN {POSITIONS} OR v.position IS NULL THEN 'position_personne_non_publiee'
                    WHEN NOT v.derniere_lecture THEN 'pas_la_derniere_lecture'
                    WHEN v.groupe IS NULL THEN 'sans_groupe_a_la_date'
                    WHEN g.organe IS NULL THEN 'groupe_sans_fiche'
                    WHEN dg.groupe IS NULL THEN 'groupe_absent_du_decompte'
                    WHEN dg.pg IS NULL THEN 'positions_du_groupe_discordantes'
                    WHEN coalesce(dg.pour, 0) + coalesce(dg.contre, 0) + coalesce(dg.abst, 0) = 0 THEN 'aucun_membre_exprime'
                    WHEN dg.pg NOT IN {POSITIONS} THEN 'position_du_groupe_non_publiee'
                    WHEN CASE dg.pg WHEN 'pour' THEN dg.pour WHEN 'contre' THEN dg.contre
                                    WHEN 'abstention' THEN dg.abst END < greatest(dg.pour, dg.contre, dg.abst)
                         THEN 'position_publiee_contredite_par_le_decompte'
               END AS raison, count(*)
        FROM v LEFT JOIN groupe g ON g.organe = v.groupe AND g.legislature IN ({legs}) {avec_fiche}
        LEFT JOIN dg ON dg.scrutin = v.scrutin AND dg.groupe = v.groupe
        GROUP BY 1""", [acteur, depuis or ""])
    return {r: n for r, n in rows if r is not None}


def _divergences(ctx, f, acteur, perim, commun) -> dict:
    au = commun["au"]
    pts = points("scrutins") + [PA_AMO]
    if not _vue(ctx, "divergence"):
        f.section("divergences", [], "comparaison_groupe",
                  couverture=_absente("divergences", ["divergence"], pts, au))
        return {"comparaisons": None, "statut": "non_relu"}
    rows = _lignes(ctx, """SELECT * FROM divergence WHERE acteur = ? AND date >= ?
                           ORDER BY date, scrutin""", [acteur, commun["debut_activite"] or ""]) if acteur else []
    for r in rows:
        r["licence"] = commun["lic"].get(PA_SCRUTINS)
        r["titre_dossier"] = r["titre_dossier"] or commun["titres"].get(r["dossier"])
        r["votes_posterieurs_non_relies"] = commun["posterieurs"].get(r["scrutin"])
    exclus = _exclusions(ctx, acteur, commun["debut_activite"]) if acteur else {}
    total = len(rows) + sum(exclus.values())
    contre = exclus.get("position_publiee_contredite_par_le_decompte", 0)
    groupe_non_etabli = sum(exclus.get(k, 0) for k in (
        "groupe_absent_du_decompte", "positions_du_groupe_discordantes", "aucun_membre_exprime",
        "position_du_groupe_non_publiee", "position_publiee_contredite_par_le_decompte"))
    phrase = (f"Sur {total} positions en dernière lecture, {len(rows)} sont comparées à la position "
              "majoritaire publiée de son groupe à la date (5 conditions : position de la personne "
              "publiée, position du groupe établie, dernière lecture, ensemble du texte, groupe ayant "
              f"une fiche). {groupe_non_etabli} sont écartées faute de position du groupe établie, dont "
              f"{contre} parce que la position publiée du groupe contredit son propre décompte : ces "
              "scrutins sont « non établis » (décision du 06/11/2026, Q30). Les divergences ne sont "
              "jamais comptées.")
    ts = _trous_votes(ctx, acteur, commun["debut_activite"])
    cv = _couv_activite("divergences", perim, phrase, len(rows), total, pts, au,
                        ecartes=[{"raison": k, "positions": v} for k, v in sorted(exclus.items())],
                        regle_de_selection="5 conditions du cahier 4.2 ; groupes ayant une fiche : "
                                           f"ceux des lignées publiées ({plage()} législature)")
    cv = marquer_trous(cv, ts)
    f.section("divergences", rows, "comparaison_groupe",
              ids={"acteur": "acteur", "scrutin": "scrutin", "dossier": "dossier", "organe": "groupe",
                   "autre": "periode"},
              date="date", couverture=cv, colonnes=COLS_DIVERGENCES,
              extra={"ordre": "chronologique",
                     "lecture": "une ligne par scrutin comparé ; `diverge` dit si les deux positions "
                                "diffèrent ; aucun total n'est servi (cahier, règle 7)",
                     "groupe_divise": "les membres du groupe n'ont pas tous voté de même (sans seuil)",
                     "au": au})
    st = "trou_source" if ts and _st(perim) == "complet" else _st(perim)
    return {"comparaisons": _compte(len(rows), st), "statut": st}


# -- ce qu'il a dit -------------------------------------------------------------------------

COLS_PAROLES = ["n", "date", "qualite", "qualite_source", "preside", "interruption", "sujet_id",
                "periode", "fichier", "ligne", "compte_rendu", "id_syceron", "acteur", "source_url",
                "licence"]
COLS_EXTRAITS = ["n", "date", "compte_rendu", "id_syceron", "extrait", "extrait_tronque", "longueur",
                 "qualite", "preside", "interruption", "sujet_id", "dossier", "acteur", "source_url",
                 "licence"]
COLS_SUJETS = ["sujet_id", "sujet", "sujet_libelle", "type_sujet", "creneau", "statut_sujet",
               "dossier", "titre_dossier", "premiere_date", "derniere_date"]


def _paroles(ctx, f, acteur, perim, commun, idx) -> dict:
    au = commun["au"]
    pts = points("syceron")
    lic = commun["lic"].get(PA_SYCERON)
    if not _vue(ctx, "parole_personne"):
        f.section("paroles", [], "parole_index", couverture=_absente("paroles", ["parole_personne"], pts, au))
        return {"paroles": None, "presidences": None, "statut": "non_relu"}
    rows = _lignes(ctx, """SELECT * FROM parole_personne WHERE acteur = ? AND date >= ?
                           ORDER BY date, compte_rendu, ordre_absolu_seance, id_syceron""",
                   [acteur, commun["debut_paroles"] or ""]) if acteur else []
    sujets: dict[tuple, dict] = {}
    for r in rows:
        k = (r["type_sujet"], r["sujet"], r["creneau"])
        if k not in sujets:
            sujets[k] = {"sujet_id": len(sujets) + 1, "sujet": r["sujet"],
                         "sujet_libelle": r["sujet"] or "Intitulé non publié", "type_sujet": r["type_sujet"],
                         "creneau": r["creneau"], "statut_sujet": r["statut_sujet"], "dossier": r["dossier"],
                         "titre_dossier": commun["titres"].get(r["dossier"]),
                         "premiere_date": r["date"], "derniere_date": r["date"]}
        s = sujets[k]
        s["derniere_date"] = max(s["derniere_date"], r["date"])
        r["sujet_id"] = s["sujet_id"]
        r["licence"] = lic
    for n, r in enumerate(rows, 1):
        r["n"] = n
    # Extraits par semestre, puis par paquets ; l'index renvoie au fichier et au rang.
    for nom, sem, ls in _decouper(rows, lambda r: _semestre(r["date"]), "paroles-textes",
                                  taille=lambda r: len(r["extrait"] or "") + 260):
        for k, r in enumerate(ls):
            r["fichier"], r["ligne"] = f"{nom}.json.gz", k
            idx.ajouter(nom, k, r["extrait"])
        f.section(nom, ls, "parole_extrait",
                  ids={"acteur": "acteur", "compte_rendu": "compte_rendu", "dossier": "dossier",
                       "autre": "id_syceron"},
                  date="date",
                  couverture=_couv("paroles", "complet", f"Extraits ({LONGUEUR_EXTRAIT} premiers "
                                   f"caractères) et lien au paragraphe, semestre {sem}.", len(ls), len(ls),
                                   points_de_l_annee(ctx, pts, str(sem)[:4]), au=au),
                  colonnes=COLS_EXTRAITS, extra={"semestre": sem, "ordre": "chronologique"})
    liste_sujets = sorted(sujets.values(), key=lambda s: s["sujet_id"])
    for s in liste_sujets:
        idx.ajouter("paroles:sujets", s["sujet_id"] - 1, s["sujet"], s["titre_dossier"])
    debat = [r for r in rows if not r["preside"]]
    pres = [r for r in rows if r["preside"]]
    ecrite = sum(1 for r in debat if r["qualite_source"] == "compte_rendu")
    sans_q = sum(1 for r in rows if r["qualite"] is None)
    sans_s = sum(1 for r in rows if r["statut_sujet"] != "etabli")
    phrase = (f"Paragraphes du compte rendu de séance attribués à la personne : {len(debat)} prises de "
              f"parole dans le débat et {len(pres)} paragraphes de présidence de séance, comptés à part "
              f"(présider n'est pas intervenir). Qualité écrite par le compte rendu pour {ecrite} prises "
              f"de parole sur {len(debat)}, les autres déduites des fonctions à la date ; {sans_q} sans "
              f"qualité établie ; {sans_s} sans intitulé publié. Commissions non lues.")
    cv = _couv_activite("paroles", perim, phrase, ecrite, len(debat), pts, au,
                        sujet_publie=[len(rows) - sans_s, len(rows)])
    par_q = defaultdict(int)
    for r in rows:
        par_q[("presidence_de_seance" if r["preside"] else r["qualite"] or "non_etablie")] += 1
    f.section("paroles", rows, "parole_index",
              ids={"acteur": "acteur", "compte_rendu": "compte_rendu", "autre": "id_syceron"},
              date="date", couverture=cv, colonnes=COLS_PAROLES,
              extra={"ordre": "chronologique",
                     "sujets": {"colonnes": COLS_SUJETS,
                                "lignes": [[s[k] for k in COLS_SUJETS] for s in liste_sujets]},
                     "par_qualite": dict(sorted(par_q.items())),
                     "lecture": "index sans texte ; l'extrait est dans `fichier`, au rang `ligne`",
                     "au": au})
    st = _st(perim)
    return {"paroles": _compte(len(debat), st), "presidences": _compte(len(pres), st), "statut": st}


FAMILLES_QUESTIONS = {"QE": "questions-ecrites", "QG": "questions-gouvernement",
                      "QOSD": "questions-orales"}


def _entier(x):
    try:
        return int(x)
    except (TypeError, ValueError):
        return None


COLS_QUESTIONS = ["question", "type", "type_code", "numero", "legislature", "date", "date_nature",
                  "ministere", "ministere_libelle", "ministere_attributaire_libelle", "rubrique",
                  "tete_analyse", "analyses", "date_reponse", "cloture", "date_cloture", "acteur",
                  "source_url", "raison_source_url", "source_point", "licence",
                  "statut_seance", "raison_seance", "date_seance", "lien_seance", "intervenants"]
# Séance d'une question au gouvernement ou orale sans débat (R-QAG) : `statut_seance` appariee /
# non_appariee (raison dans `raison_seance`), vide pour une question écrite.


def _questions(ctx, f, acteur, perim, commun, idx) -> dict:
    au = commun["au"]
    pts = [p for fam in FAMILLES_QUESTIONS.values() for p in points(fam)]
    if not _vue(ctx, "question_personne"):
        f.section("questions", [], "question", couverture=_absente("questions", ["question_personne"], pts, au))
        return {"par_type": None, "statut": "non_relu"}
    legs = ", ".join(str(n) for n in LEGISLATURES)
    qag = _vue(ctx, "question_reponse_parole")
    jointure = ("""LEFT JOIN (SELECT question, statut AS statut_seance, raison AS raison_seance,
                                    date_seance, source_url AS lien_seance, intervenants
                             FROM question_reponse_parole) s USING (question)""" if qag else "")
    rows = _lignes(ctx, f"""SELECT * FROM question_personne {jointure} WHERE acteur = ?
                            AND TRY_CAST(legislature AS INTEGER) IN ({legs})
                            ORDER BY date NULLS LAST, question""", [acteur]) if acteur else []
    for k, r in enumerate(rows):
        fam = FAMILLES_QUESTIONS.get(r["type_code"])
        leg = _entier(r["legislature"])
        r["source_point"] = point(fam, leg) if fam and leg else None
        r["licence"] = commun["lic"].get(r["source_point"])
        r["analyses"] = list(r["analyses"]) if r["analyses"] is not None else None
        r["intervenants"] = [dict(x) for x in r["intervenants"]] if r.get("intervenants") else None
        idx.ajouter("questions", k, r["tete_analyse"], r["analyses"], r["rubrique"])
    rep = sum(1 for r in rows if r["date_reponse"])
    orales = [r for r in rows if r["type_code"] in ("QG", "QOSD")]
    app = sum(1 for r in orales if r.get("statut_seance") == "appariee")
    seance = (f" Une question posée en séance (au gouvernement ou orale sans débat) est reliée au compte "
              f"rendu de sa séance quand l'auteur y prend la parole sous l'intitulé de la question, "
              f"dans les dix jours qui précèdent sa publication au Journal officiel : {app} sur "
              f"{len(orales)} ; les autres restent sans lien, la raison est dite." if qag else
              " Le lien entre une question posée en séance et le compte rendu n'est pas établi (règle "
              "R-QAG non appliquée).")
    phrase = (f"Questions écrites, au gouvernement et orales sans débat dont la personne est l'auteur "
              f"({len(rows)}), avec réponse publiée pour {rep}. Une question sans réponse n'a pas de date "
              "de réponse. Chaque question renvoie à sa page sur le site de l'Assemblée." + seance)
    cv = _couv_activite("questions", perim, phrase, rep, len(rows), pts, au)
    f.section("questions", rows, "question", ids={"acteur": "acteur", "question": "question",
                                                  "organe": "ministere"},
              date="date", couverture=cv, colonnes=COLS_QUESTIONS,
              extra={"ordre": "chronologique", "aide_a_la_lecture": ["rubrique"], "au": au})
    par = defaultdict(int)
    for r in rows:
        par[r["type"]] += 1
    st = _st(perim)
    par_type = {t: _compte(par.get(t, 0), st) for t in ("ecrite", "au_gouvernement", "orale_sans_debat")}
    return {"par_type": par_type, "statut": st}


# -- volet européen : votes nominatifs (R-VOTE-PE ; décisions Q3 et Q33) --------------------

COLS_VOTES_PE = ["date", "heure", "vote", "numero", "seance", "libelle", "document_ref", "objet",
                 "rubrique", "nature", "position", "raison_position", "intention", "resultat", "pour",
                 "contre", "abstention", "methode", "eurodepute", "source_url", "licence"]
# (la source de chaque ligne se lit dans `licence` et `source_url` : colonnes inchangées, pour que le
# schéma des fichiers servis, C4, reste celui des votes du portail)


def _europe(ctx, f, c, carriere, commun) -> dict | None:
    """Votes nominatifs au Parlement européen, un fichier par année (`europe-votes-<année>`), et
    un index `europe` (années, lignes, couverture). Deux sources raccordées au 02/07/2019
    (décision Q3) : Parltrack avant, le portail du PE ensuite ; la licence de chaque ligne suit sa
    source. Rien pour un candidat sans identifiant européen : sa frise le dit déjà."""
    if not c.get("eurodepute"):
        return None
    au = commun["au"]
    mandats = [l for l in carriere if l["institution"] == "parlement_europeen"]
    avant = any(l["debut"] and l["debut"] < DEBUT_VOTES_PE for l in mandats)
    apres = any(not l["fin"] or l["fin"] >= DEBUT_VOTES_PE for l in mandats)
    lu_avant = _vue(ctx, "parltrack_votes__vote_pt")
    lu_apres = _vue(ctx, "pe_votes__vote_pe")
    pts = ([PA_PARLTRACK] if avant else []) + ([PA_PE_VOTES] if apres else [])
    if not _vue(ctx, "vote_personne_pe"):
        f.section("europe", [], None, couverture=_absente("europe_votes", ["vote_personne_pe"], pts, au))
        return {"statut": "non_relu", "detail": "Votes au Parlement européen : règle absente."}
    rows = _lignes(ctx, "SELECT * FROM vote_personne_pe WHERE per = ? ORDER BY date, heure, numero",
                   [c["per"]])
    for r in rows:
        r["licence"] = commun["lic"].get(r.get("source_point"))
    n_ens = sum(1 for r in rows if r["nature"] == "ensemble")
    n_non = sum(1 for r in rows if r["nature"] == "non_etablie")
    sources = []
    if avant:
        sources.append(f"avant le {_fr(DEBUT_VOTES_PE)} : Parltrack (licence ODbL, figé depuis le 24/07/2026)"
                       if lu_avant else f"avant le {_fr(DEBUT_VOTES_PE)} : non collectés (Parltrack)")
    if apres:
        sources.append(f"depuis le {_fr(DEBUT_VOTES_PE)} : portail du Parlement européen"
                       if lu_apres else f"depuis le {_fr(DEBUT_VOTES_PE)} : non collectés (portail du PE)")
    lu = (f"Votes nominatifs publiés par le Parlement européen ({len(rows)}, dont {n_ens} sur l'ensemble "
          f"d'un texte ; nature non établie pour {n_non}) ; " + " ; ".join(sources) + ". Un vote où la "
          "personne ne figure pas n'est pas montré.")
    couverts = [x for x, besoin in ((lu_avant, avant), (lu_apres, apres)) if besoin]
    if not mandats:
        statut, detail = "non_etabli", "Aucun mandat de député européen lu : votes non rattachés."
    elif all(couverts):
        statut, detail = "complet", lu
    elif any(couverts):
        statut, detail = "partiel", lu
    else:
        statut, detail = "non_collecte", lu
    par_annee = defaultdict(list)
    for r in rows:
        par_annee[str(r["date"])[:4]].append(r)
    index = []
    for annee, lignes in sorted(par_annee.items()):
        p_an = sorted({r["source_point"] for r in lignes if r.get("source_point")}) or pts
        cv = _couv("europe_votes", statut, detail, len(lignes), None, p_an, au=au)
        f.section(f"europe-votes-{annee}", lignes, "position_vote_pe",
                  ids={"acteur": "eurodepute", "scrutin": "vote", "reunion": "seance"}, date="date",
                  couverture=cv, colonnes=COLS_VOTES_PE,
                  extra={"ordre": "chronologique", "au": au,
                         "lecture": "position : pour, contre, abstention, telle que publiée ; intention : "
                                    "correction déposée après le vote, qui ne remplace pas la position"})
        index.append({"annee": annee, "fichier": f"europe-votes-{annee}.json.gz", "lignes": len(lignes),
                      "eurodepute": c["eurodepute"]})
    f.section("europe", index, None, couverture=_couv("europe_votes", statut, detail, len(rows), None, pts, au=au),
              colonnes=["annee", "fichier", "lignes", "eurodepute"], extra={"au": au, "depuis": DEBUT_VOTES_PE})
    return {"statut": statut, "detail": detail, "n": _compte(len(rows), statut)}


# -- volet européen : activité hors votes (R-ACTIVITE-PE ; décision Q37) ----------------------

FAMILLES_ACTIVITE_PE = {"interventions": "Interventions en séance", "rapports": "Rapports et avis",
                        "resolutions": "Propositions de résolution", "questions": "Questions",
                        "explications": "Explications de vote", "autres": "Autres activités"}
COLS_ACTIVITE_PE = ["date", "annee", "legislature_pe", "date_raison", "titre", "reference", "role_pe", "type_source",
                    "commission", "dossiers", "extrait", "activite", "eurodepute", "source_url", "licence"]
FIN_PARLTRACK = "2026-07-24"


def _activite_europe(ctx, f, c, carriere, commun) -> dict | None:
    """Une section par famille d'activité (`europe-interventions`, `europe-rapports`…), chacune
    avec sa couverture. Parltrack est figé depuis le 24/07/2026 : pour un mandat qui court au-delà,
    la section est `partiel`."""
    if not c.get("eurodepute"):
        return None
    au = commun["au"]
    mandats = [l for l in carriere if l["institution"] == "parlement_europeen"]
    if not _vue(ctx, "activite_pe"):
        return {"statut": "non_relu", "detail": "Activité au Parlement européen : règle absente."}
    lu_pt = _vue(ctx, "parltrack_activites__activite_pt")
    lu_pe = _vue(ctx, "pe_eurodeputes__intervention_pe")
    apres_gel = any(not l["fin"] or l["fin"] > FIN_PARLTRACK for l in mandats)
    rows = _lignes(ctx, "SELECT * FROM activite_pe WHERE per = ? ORDER BY famille, coalesce(date, annee), activite",
                   [c["per"]])
    statuts = []
    for fam, titre in FAMILLES_ACTIVITE_PE.items():
        lignes = [r for r in rows if r["famille"] == fam]
        for r in lignes:
            r["licence"] = commun["lic"].get(r["source_point"])
        if fam == "interventions":
            pts = [PA_PARLTRACK_ACT, PA_PE]
            detail = ("Interventions en séance : Parltrack avant le 02/07/2019, portail du Parlement européen "
                      "ensuite ; le titre du débat et le lien vers le compte rendu, sans le texte.")
            statut = "complet" if (lu_pt and lu_pe) else ("partiel" if (lu_pt or lu_pe) else "non_collecte")
            # Trou de source : le portail ne publie les interventions de certains députés qu'à partir
            # d'une date plus tardive (mesuré : R. Glucksmann, pas avant le 06/07/2021, ni dans Parltrack).
            premiere = min((r["date"] for r in lignes if r["source"] == "pe" and r["date"]), default=None)
            debut_apres = min((l["debut"] for l in mandats if not l["fin"] or l["fin"] >= DEBUT_VOTES_PE), default=None)
            if statut == "complet" and premiere and debut_apres and premiere > max(debut_apres, DEBUT_VOTES_PE)[:10] \
                    and (dt.date.fromisoformat(premiere) - dt.date.fromisoformat(max(debut_apres, DEBUT_VOTES_PE)[:10])).days > 180:
                statut = "partiel"
                detail += (f" Aucune intervention publiée par le portail avant le {_fr(premiere)} (ni par Parltrack) "
                           "pour un mandat commencé plus tôt : trou de source probable.")
        else:
            pts = [PA_PARLTRACK_ACT]
            detail = (f"{titre} : Parltrack (licence ODbL), figé depuis le {_fr(FIN_PARLTRACK)}"
                      + (" ; les activités postérieures ne sont pas connues." if apres_gel else "."))
            statut = "non_collecte" if not lu_pt else ("partiel" if apres_gel else "complet")
        if statut == "complet" and not lignes:
            statut = "relu_aucun"
        sans_date = sum(1 for r in lignes if not r["date"])
        if sans_date:
            detail += (f" Date inconnue pour {sans_date} (republication du 22/11/2016) : seule l'année, "
                       "ou à défaut la législature européenne, est donnée.")
        statuts.append(statut)
        f.section(f"europe-{fam}", lignes, f"activite_pe_{fam}",
                  ids={"acteur": "eurodepute", "autre": "activite"}, date="date",
                  couverture=_couv(f"europe_{fam}", statut, detail, len(lignes), None, pts, au=au),
                  colonnes=COLS_ACTIVITE_PE, extra={"ordre": "chronologique", "au": au, "titre": titre})
    pire = next((x for x in ("non_collecte", "non_relu", "partiel") if x in statuts), "complet")
    return {"statut": pire, "detail": "Activité au Parlement européen hors votes : " + (
        "Parltrack est figé depuis le 24/07/2026, les activités postérieures ne sont pas connues."
        if pire == "partiel" else "voir chaque section.")}


# -- filtre par mot -------------------------------------------------------------------------

def _ecrire_mots(ecr, f, idx: IndexMots, au) -> dict:
    """Une tranche par deux premières lettres du mot : `mots/<xx>.json.gz`. Les mots sont des
    valeurs (colonne `mot`), jamais des clés : un mot ne peut pas passer pour un champ."""
    tranches = idx.tranches()
    poids = {}
    for xx, liste in sorted(tranches.items()):
        fichiers = sorted({fi for m in liste for fi in idx.renvois[m]})
        num = {fi: k for k, fi in enumerate(fichiers)}
        lignes = [[m, [[num[fi], rs] for fi, rs in sorted(idx.renvois[m].items())]] for m in liste]
        contenu = {"contrat": "1.0", "fiche": f.id, "tranche": xx,
                   "fichiers": [fi if ":" in fi else f"{fi}.json.gz" for fi in fichiers],
                   "colonnes": ["mot", "renvois"], "lignes": lignes,
                   "lecture": "renvois : [rang du fichier dans `fichiers`, [rangs des lignes]] ; "
                              "« paroles:sujets » renvoie à la table des sujets de paroles.json.gz"}
        info = ecr.ecrire(f"{f.dossier}/mots/{xx}.json.gz", contenu)
        poids[xx] = info["gz"]
    return {"tranches": sorted(tranches), "modele": "mots/{xx}.json.gz", "nb_mots": len(idx.renvois),
            "textes_indexes": idx.textes,
            "normalisation": "minuscules, sans accents, mots de 3 caractères et plus, mots vides retirés ; "
                             "tranche = deux premiers caractères du mot",
            "porte_sur": ["titres des textes portés", "titres et intitulés des textes votés",
                          "exposés des amendements", "extraits de parole", "sujets de parole",
                          "analyses et rubriques des questions"],
            "poids_gz_max_tranche": max(poids.values(), default=None), "au": au}


# -- compteurs ------------------------------------------------------------------------------

def _compteurs(c, acteur, perim, carriere, couv_car, fonctions, proposes, amend, votes, div, paroles,
               questions, au) -> list[dict]:
    out = []

    def ajouter(institution, famille, valeur, statut, definition, points, perimetre=None, **extra):
        out.append({"institution": institution, "famille": famille, "valeur": valeur, "au": au,
                    "statut": statut, "definition": definition, "perimetre": perimetre,
                    "points_acces": points, "acteur": acteur, **extra})

    for inst in ("assemblee", "gouvernement", "senat"):
        cc = couv_car.get(inst, {})
        st = cc.get("statut", "non_relu")
        ls = [l for l in carriere if l["institution"] == inst and l["etat"] == "en_fonction"]
        iv = [(_jour(l["debut"]), _jour(l["fin"]) if l["fin"] else _jour(au)) for l in ls]
        pts = [PA_SENAT] if inst == "senat" else [PA_AMO]
        n_mandats = len({l["mandat"] for l in ls})
        ajouter(inst, "mandats" if inst != "gouvernement" else "fonctions",
                _compte(n_mandats, st), st,
                {"assemblee": "mandats de député depuis le 19/06/2002",
                 "gouvernement": "fonctions gouvernementales depuis le 17/05/2007",
                 "senat": "mandats de sénateur (export du Sénat)"}[inst], pts)
        ajouter(inst, "jours_en_fonction", _compte(_jours_union(iv, jusqu_a=_jour(au)), st), st,
                "jours en fonction (périodes réunies, mandats suspendus exclus), jusqu'à la date du compte",
                pts)
        if inst == "assemblee":
            ajouter(inst, "legislatures", _compte(len({l["legislature"] for l in ls}), st), st,
                    "législatures où la personne a siégé", pts,
                    liste=sorted({l["legislature"] for l in ls if l["legislature"] is not None}))
    for inst in ("parlement_europeen", "local"):
        ajouter(inst, "mandats", None, "non_collecte", LIBELLE_INSTITUTION[inst] + " : non collecté dans l'essai",
                [])
    xv = f"{plage()} législature"
    xvp = f"{plage(n for n in LEGISLATURES if n >= PAROLES_DEPUIS)} législature"
    ajouter("assemblee", "textes_portes_publies", proposes.get("publies"), proposes["statut"],
            "textes portés publiés (à partir de l'examen en commission), tous rôles", points("dossiers"), xv,
            par_role=proposes.get("par_role"))
    ajouter("assemblee", "amendements_auteur_principal", amend.get("auteur"), amend["statut"],
            "amendements dont la personne est l'auteur principal, hors irrecevables 40 et 45 ; aucun taux "
            "d'adoption", points("amendements"), xv)
    ajouter("assemblee", "irrecevables_article_40", amend.get("irrecevables_40"), amend["statut"],
            "amendements de la personne irrecevables au titre de l'article 40 (comptés à part)",
            points("amendements"), xv)
    ajouter("assemblee", "irrecevables_article_45", amend.get("irrecevables_45"), amend["statut"],
            "amendements de la personne irrecevables au titre de l'article 45 (comptés à part)",
            points("amendements"), xv)
    ajouter("assemblee", "signatures_cosignataire", amend.get("signatures"), amend["statut"],
            "signatures comme cosignataire d'amendements d'autres auteurs", points("amendements"), xv)
    ajouter("assemblee", "positions_textes", votes.get("positions"), votes["statut"],
            "textes sur lesquels la position de la personne est publiée (dernière lecture, ensemble)",
            points("scrutins"), xv)
    ajouter("assemblee", "motions_de_censure", votes.get("motions"), votes["statut"],
            "motions de censure sur lesquelles la position de la personne est publiée", points("scrutins"), xv)
    ajouter("assemblee", "scrutins_compares_au_groupe", div.get("comparaisons"), div["statut"],
            "scrutins où sa position est placée à côté de celle de son groupe (jamais de total des "
            "divergences)", points("scrutins"), xv)
    ajouter("assemblee", "prises_de_parole", paroles.get("paroles"), paroles["statut"],
            "paragraphes de compte rendu de séance attribués, hors présidence de séance", points("syceron"), xvp)
    ajouter("assemblee", "presidence_de_seance", paroles.get("presidences"), paroles["statut"],
            "paragraphes prononcés en présidant la séance", points("syceron"), xvp)
    for t, lib in (("ecrite", "questions écrites"), ("au_gouvernement", "questions au gouvernement"),
                   ("orale_sans_debat", "questions orales sans débat")):
        ajouter("assemblee", f"questions_{t}", (questions.get("par_type") or {}).get(t), questions["statut"],
                lib, [p for fam in FAMILLES_QUESTIONS.values() for p in points(fam)], xv)
    return out
