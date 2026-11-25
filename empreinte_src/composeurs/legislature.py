"""Composeur de la fiche d'une législature (cahier 4.5 ; doc. 1, 1.7.2).

Fichiers de `legislatures/<numero>/` :

| fichier | ce que voit le lecteur | règles lues |
| --- | --- | --- |
| `fiche.json.gz` | en-tête (nom, période, mode de fin), en bref (gouvernements, comptes datés), limites | R-LEGISLATURES, R-GOUVERNEMENTS, R-DEPUTES, R-LOIS, R-LOI-ADOPTION, R-NATURE-SCRUTIN, R-49-3, R-SORT-FINAL |
| `hemicycle.json.gz` | qui siège : un siège par député en fonction au jour de constat | R-HEMICYCLE |
| `groupes.json.gz` | qui siège : effectif de chaque groupe, position déclarée | R-APPARTENANCE, R-HEMICYCLE |
| `ordre-du-jour-<annee>.json.gz` | le calendrier des séances et leurs points | R-ORDRE-DU-JOUR, R-MATIERE |
| `textes.json.gz` | les textes : matière, étape, sort, initiateur, législature d'adoption de la loi | R-ETAPE, R-SORT-FINAL, R-MATIERE, R-LOI-ADOPTION |
| `commissions.json.gz` | dossiers par commission saisie au fond et par étape (décomptes) | R-MATIERE, R-ETAPE |

Ce que le composeur ne fait pas : il ne déduit rien que les règles ne disent pas. Deux exceptions,
déclarées dans les fichiers : l'**initiateur** d'un texte est lu dans l'identifiant du texte
déposé (`PRJL` = gouvernement ; `PION`/`PNRE` déposé à l'Assemblée = députés, au Sénat =
sénateurs), faute de règle R-INITIATEUR ; la **date de dépôt** est celle du premier acte de
dépôt du dossier. Pas de place médiane d'un groupe : aucune règle ne la donne
(voir `LIMITES`). Le **terme légal** (date à laquelle le mandat devait finir, hors dissolution)
vient de R-LEGISLATURES (code électoral, L.O. 121) et est servi dans l'en-tête.

Le compte des **lois** est celui des numéros de loi des actes de promulgation (R-LOIS) dont la date
tombe dans la législature, quelle que soit la législature d'ouverture du dossier ; une loi publiée
par deux identifiants de dossier n'est comptée qu'une fois (décision du 25/11/2026, doc. 5, Q68 :
2017-1338, la XVe passe de 335 à 334 sur la g24). La capture du site actuel
dit 141 ; ce compte donne 150 au 06/11/2026 (dont 37 dossiers ouverts sous une législature
antérieure, 9 de procédure « loi organique ») : l'écart n'est pas expliqué, le détail est servi
avec le compte.

À côté (issue #83), le compte des **lois par adoption** (`lois_par_adoption`, R-LOI-ADOPTION) :
les lois que l'Assemblée a adoptées en dernier pendant la législature, puis promulguées, même
après sa fin, même quand le Sénat a voté en dernier (doc. 5, Q65 et Q66). Il est `partiel` quand
des lois qui ont pu l'être n'ont pas de législature d'adoption établie (raisons servies : dossier
absent des archives, suite absente) ; une loi adoptée par l'Assemblée avant la XIVe est hors du
périmètre (Q67) : elle est comptée parmi les lois adoptées sous une autre législature
(`dont_adoptees_avant_le_perimetre`), jamais comme incertaine. Chaque texte promulgué porte la législature d'adoption de sa
loi (`legislature_adoption_loi`, sa preuve ou sa raison).
"""
from __future__ import annotations

import datetime as dt
import re
from collections import Counter, defaultdict

from ..perimetre import LEGISLATURES, LEGISLATURES_GOUVERNEMENTS
from ..regles.r_loi_adoption import HORS_PERIMETRE

NOM = "legislature"
VERSION = 1
DEPEND = ("R-LEGISLATURES", "R-GOUVERNEMENTS", "R-DEPUTES", "R-APPARTENANCE", "R-HEMICYCLE",
          "R-LOIS", "R-49-3", "R-NATURE-SCRUTIN", "R-ORDRE-DU-JOUR", "R-MATIERE", "R-ETAPE",
          "R-SORT-FINAL", "R-LOI-ADOPTION")

# Législatures publiées : XIVe à XVIIe (cahier 4.1 ; module `perimetre`).
PERIMETRE = LEGISLATURES

COLS_HEMICYCLE = ["siege", "acteur", "prenom", "nom", "groupe", "groupe_sigle", "groupe_libelle",
                  "rattachement", "raison_rattachement", "raison_siege", "mandat", "date",
                  "date_origine", "source_url", "source_point", "licence"]
COLS_ODJ = ["date", "reunion", "statut_seance", "a_venir", "compte_rendu", "rang", "point", "objet",
            "type_point", "statut_point", "lien_dossier", "dossier", "dossiers", "titre_dossier",
            "commission", "commission_libelle", "matiere_statut", "source_url", "source_point",
            "licence"]
COLS_TEXTES = ["dossier", "titre", "date_depot", "texte_depose", "chambre_depot", "initiateur",
               "procedure_code", "procedure_libelle", "legislature_dossier", "matiere_statut",
               "commission", "commission_libelle", "type_commission", "raison_matiere", "etape",
               "date_etape", "raison_etape", "sort", "date_sort", "raison_sort",
               "sort_pendant_la_legislature", "par_49_3", "adopte_par_49_3", "numero_loi",
               "date_promulgation", "url_loi",
               # #83 : législature où l'Assemblée a adopté la loi en dernier (R-LOI-ADOPTION), sa
               # preuve, ou la raison qui l'empêche.
               "legislature_adoption_loi", "preuve_adoption_loi", "raison_adoption_loi",
               # #71 : vote solennel dans la législature (R-NATURE-SCRUTIN, R-LIEN-SCRUTIN-DOSSIER) ;
               # initiateur nominatif : premier auteur du texte déposé (R-TEXTE-PORTE), son groupe à
               # la date du dépôt (R-APPARTENANCE) ; un projet de loi : le gouvernement, jamais un
               # acte personnel du ministre (cahier 4.6), rôle `initiative_gouvernementale`.
               "vote_solennel", "scrutins_solennels", "initiateur_role", "initiateur_acteur",
               "initiateur_nom", "initiateur_groupe", "initiateur_groupe_sigle",
               "initiateur_gouvernement", "nb_auteurs",
               "source_url", "source_point", "licence"]

ETAPES = ("depot", "examen_commission", "seance", "adopte", "promulgue", "non_etablie")

# Ce que la fiche ne peut pas montrer, et pourquoi (section « Ce qu'on n'a pas pu lire »).
LIMITES = [
    {"sujet": "senat", "statut": "hors_perimetre",
     "detail": "Seule l'Assemblée nationale est lue. Un texte déposé au Sénat et jamais transmis "
               "à l'Assemblée n'apparaît pas ; les séances, débats et votes du Sénat ne sont pas "
               "couverts."},
    {"sujet": "commissions", "statut": "non_collecte",
     "detail": "Les comptes rendus des commissions, leurs auditions et leurs réunions ne sont pas "
               "lus : « le travail des commissions » compte les seuls dossiers saisis au fond, par "
               "étape atteinte."},
    {"sujet": "missions_d_information", "statut": "non_collecte",
     "detail": "Les rapports d'information, missions d'information et commissions d'enquête sont "
               "des dossiers sans texte déposé : ils sont écartés des textes de la législature "
               "(leur nombre est donné avec la section), et leur rattachement à une commission "
               "n'est pas lu."},
    {"sujet": "place_mediane", "statut": "non_collecte",
     "detail": "La place médiane d'un groupe dans l'hémicycle n'est donnée par aucune règle : seuls "
               "les sièges sont servis."},
    {"sujet": "hemicycle_legislature_close", "statut": "trou_source",
     "detail": "Le siège d'un député n'est publié, pour une législature close, que par l'archive "
               "figée de cette législature ; celle-ci n'en a pas d'utilisable : ni l'hémicycle ni "
               "la place des groupes ne sont servis."},
    {"sujet": "articles_de_la_periode", "statut": "hors_perimetre",
     "detail": "Les articles du site sur la période ne sont pas composés dans cette tranche."},
]


# --------------------------------------------------------------------------- outils

def _romain(n: int) -> str:
    vals = [(10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]
    out = ""
    for v, s in vals:
        while n >= v:
            out, n = out + s, n - v
    return out


def _nom(numero: int) -> str:
    return f"{_romain(numero)}{'re' if numero == 1 else 'e'} législature"


def _lignes(ctx, sql: str, params=None) -> list[dict]:
    r = ctx.con.execute(sql, params or [])
    cols = [d[0] for d in r.description]
    return [dict(zip(cols, row)) for row in r.fetchall()]


def _manquantes(ctx, *vues) -> list[str]:
    return [v for v in vues if not ctx.existe(v)]


def _points(ctx, *tables) -> list[str]:
    """Points d'accès dont viennent les faits lus de ces tables (pour C5)."""
    out = set()
    for t in tables:
        if ctx.existe(t):
            out |= {r[0] for r in ctx.x(f"SELECT DISTINCT prov_point FROM {t}") if r[0]}
    return sorted(out)


def _licences(ctx, *tables) -> dict:
    out = {}
    for t in tables:
        if ctx.existe(t):
            for p, l in ctx.x(f"SELECT DISTINCT prov_point, licence FROM {t}"):
                if p and l:
                    out[p] = l
    return out


def _regle(ctx, vue: str) -> str | None:
    if not ctx.existe(vue):
        return None
    return ctx.un(f"SELECT any_value(regle) FROM {vue}")


def _couv(n, d, phrase: str, points: list[str], sinon: str = "trou_source", **autres) -> dict:
    """Couverture d'une section : `complet` quand tout est établi, sinon le statut donné."""
    statut = "complet" if d is not None and n == d else sinon
    return {"statut": statut, "numerateur": n, "denominateur": d, "detail": phrase,
            "points_acces": points, **autres}


def _absente(manque: list[str], points: list[str]) -> dict:
    return {"statut": "non_relu", "numerateur": None, "denominateur": None,
            "detail": "Matière non établie : sortie de règle absente (" + ", ".join(manque) + ").",
            "points_acces": points}


def _date_reference(ctx) -> str:
    return ctx.date_reference or dt.date.today().isoformat()


def _fr(n) -> str:
    return f"{n:,}".replace(",", " ") if isinstance(n, int) else str(n)


def _date_fr(d: str | None) -> str:
    if not d:
        return "?"
    a, m, j = d[:10].split("-")
    return f"{j}/{m}/{a}"


# --------------------------------------------------------------------------- composeur

def composer(ctx, ecr):
    """Compose une fiche par législature du périmètre (`PERIMETRE`), avec l'écrivain `ecr`, en
    lisant les sorties des règles dans `ctx` ; ne fait rien si la sortie `legislature` manque. Ne
    rend rien."""
    if _manquantes(ctx, "legislature"):
        return
    for leg in _lignes(ctx, "SELECT * FROM legislature ORDER BY numero"):
        if leg["numero"] in PERIMETRE:
            composer_legislature(ctx, ecr, leg)


def composer_legislature(ctx, ecr, leg: dict):
    """Compose la fiche de la législature `leg` (une ligne de la sortie `legislature`) : un en-tête
    (la législature et sa source, ses gouvernements, ses compteurs, ses limites, la couverture des
    règles), dont les gouvernements et les compteurs sont inscrits comme faits publiés, puis les
    sections hémicycle, groupes, ordre du jour, textes et commissions. Les comptes d'une
    législature close sont arrêtés à sa date de fin. Ne rend rien."""
    numero = leg["numero"]
    ref = _date_reference(ctx)
    # `au` : date des comptes. Législature close : sa date de fin (jamais l'état actuel).
    au = ref if leg["en_cours"] or not leg["fin"] else min(leg["fin"], ref)
    lic = _licences(ctx, "an_acteurs__organe", "an_acteurs__mandat", "an_dossiers__dossier",
                    "an_dossiers__acte", "an_agenda__reunion", "an_scrutins__scrutin")
    f = ecr.fiche("legislature", str(numero), titre=_nom(numero))

    p_amo = _points(ctx, "an_acteurs__organe")
    leg_src = _lignes(ctx, "SELECT prov_point, prov_uid FROM an_acteurs__organe WHERE uid = ?",
                      [leg["organe"]])
    leg_src = leg_src[0] if leg_src else {"prov_point": None, "prov_uid": None}
    entete = {
        "legislature": {
            "numero": numero, "nom": _nom(numero), "organe": leg["organe"],
            "debut": leg["debut"], "fin": leg["fin"], "en_cours": leg["en_cours"],
            "mode_fin": leg["mode_fin"], "regle": leg.get("regle"),
            # terme légal (code électoral, L.O. 121), que la source ne publie pas : R-LEGISLATURES v2
            "terme_legal": leg.get("terme_legal"), "raison_terme_legal": leg.get("raison_terme_legal"),
            "source_terme_legal": leg.get("source_terme_legal"),
            "source_url": leg.get("source_url"), "source_point": leg_src["prov_point"],
            "source_uid": leg_src["prov_uid"], "licence": lic.get(leg_src["prov_point"])},
        "au": au,
        "date_reference": ref,
    }
    if leg_src["prov_point"] in lic:
        f.licences.add(lic[leg_src["prov_point"]])

    gouvs = _gouvernements(ctx, numero, au, lic)
    entete["gouvernements"] = {
        "colonnes": ["gouvernement", "nom", "lien", "raison_lien", "debut", "fin", "debut_gouvernement",
                     "fin_gouvernement", "duree_jours", "au", "en_cours", "source_point",
                     "source_uid", "licence"],
        "ordre": "chronologique",
        "lignes": None}
    entete["gouvernements"]["lignes"] = [[g.get(c) for c in entete["gouvernements"]["colonnes"]]
                                         for g in gouvs]
    comptes = _compteurs(ctx, leg, au, lic, gouvs)
    entete["compteurs"] = comptes
    avec_sieges = bool(ctx.existe("hemicycle") and
                       ctx.un("SELECT count(*) FROM hemicycle WHERE legislature = ?", [numero]))
    entete["limites"] = [x for x in LIMITES
                         if not ((leg["en_cours"] or avec_sieges) and x["sujet"] == "hemicycle_legislature_close")]
    f.entete(entete)
    # Les lignes de l'en-tête sont affichées : elles sont des faits publiés comme les autres.
    for g in gouvs:
        ecr.fait_publie(f, "entete", "gouvernement_de_la_legislature", g,
                        {"organe": "gouvernement"}, "debut", "source_url")
        if g.get("licence"):
            f.licences.add(g["licence"])
    for c in comptes:
        ecr.fait_publie(f, "entete", "compte_legislature", c, {"autre": "famille"}, "au",
                        "source_url")
        for l in c.get("licences") or []:
            f.licences.add(l)

    _section_hemicycle(ctx, f, leg, au, lic)
    _section_groupes(ctx, f, leg, au, lic)
    _section_ordre_du_jour(ctx, f, leg, au, lic)
    textes = _section_textes(ctx, f, leg, au, lic)
    _section_commissions(ctx, f, leg, au, lic, textes)
    _section_mots_titres(ctx, f, leg, au, lic, textes)
    f.entete({"couverture_regles": _couverture_regles(ctx)})


# --------------------------------------------------------------------------- en-tête

def _gouvernements(ctx, numero, au, lic) -> list[dict]:
    if _manquantes(ctx, "gouvernement", "gouvernement_legislature"):
        return []
    # Lien seulement vers un gouvernement qui a sa fiche (module `perimetre`, C2).
    gouv = ", ".join(str(n) for n in LEGISLATURES_GOUVERNEMENTS)
    rows = _lignes(ctx, f"""
        SELECT g.organe AS gouvernement, g.nom,
               CASE WHEN g.organe IN (SELECT gouvernement FROM gouvernement_legislature
                                      WHERE legislature IN ({gouv}))
                    THEN 'gouvernement/' || g.adresse END AS lien,
               gl.debut, gl.fin, g.debut AS debut_gouvernement, g.fin AS fin_gouvernement,
               date_diff('day', gl.debut::DATE, least(coalesce(gl.fin, ?), ?)::DATE) AS duree_jours,
               ? AS au, g.en_cours, o.prov_point AS source_point, o.prov_uid AS source_uid,
               g.source_url
        FROM gouvernement_legislature gl JOIN gouvernement g ON g.organe = gl.gouvernement
        LEFT JOIN an_acteurs__organe o ON o.uid = g.organe
        WHERE gl.legislature = ? AND gl.debut <= ?
        ORDER BY gl.debut""", [au, au, au, numero, au])
    for r in rows:
        r["licence"] = lic.get(r["source_point"])
        r["raison_lien"] = None if r["lien"] else "gouvernement sans fiche publiée"
    return rows


def _compte(famille, valeur, au, regle, definition, statut="complet", detail=None,
            numerateur=None, denominateur=None, points=None, licences=None, **autres):
    return {"famille": famille, "valeur": valeur, "au": au, "regle": regle,
            "definition": definition, "statut": statut, "detail": detail,
            "numerateur": numerateur, "denominateur": denominateur,
            "points_acces": points or [], "licences": licences or [], "source_url": None,
            **autres}


def _compteurs(ctx, leg, au, lic, gouvs) -> list[dict]:
    numero, debut = leg["numero"], leg["debut"]
    out = []
    lic_an = sorted(set(lic.values()))

    # Gouvernements.
    out.append(_compte(
        "gouvernements", len(gouvs) if ctx.existe("gouvernement_legislature") else None, au,
        _regle(ctx, "gouvernement_legislature"),
        "Gouvernements en fonction au moins un jour pendant la législature.",
        points=_points(ctx, "an_acteurs__organe"), licences=lic_an,
        statut="complet" if ctx.existe("gouvernement_legislature") else "non_relu"))

    # Députés : en fonction au jour `au` (l'hémicycle) et personnes ayant exercé un mandat.
    if ctx.existe("depute"):
        en_fonction, ayant, mandats = ctx.x("""
            SELECT count(DISTINCT acteur) FILTER (debut <= ? AND coalesce(fin, '9999-12-31') >= ?),
                   count(DISTINCT acteur), count(*)
            FROM depute WHERE legislature = ? AND debut <= ?""", [au, au, numero, au])[0]
        suspendus = ctx.un("""SELECT count(DISTINCT acteur) FROM depute WHERE legislature = ?
                              AND suspendu_du <= ? AND coalesce(suspendu_au, '9999-12-31') >= ?""",
                           [numero, au, au])
        out.append(_compte(
            "deputes_en_fonction", en_fonction, au, _regle(ctx, "depute"),
            f"Députés dont le mandat est en cours le {_date_fr(au)} (ceux qui sont au "
            "gouvernement n'y sont pas : leur suppléant siège).",
            detail=f"{_fr(suspendus)} mandats suspendus ce jour-là pour entrée au gouvernement.",
            points=_points(ctx, "an_acteurs__mandat"), licences=lic_an))
        out.append(_compte(
            "deputes_ayant_siege", ayant, au, _regle(ctx, "depute"),
            "Personnes ayant exercé un mandat de député pendant la législature (suppléants et "
            "élus partiels compris).",
            detail=f"{_fr(mandats)} mandats.", points=_points(ctx, "an_acteurs__mandat"),
            licences=lic_an))

    # Lois promulguées.
    if ctx.existe("loi"):
        # Q68 (25/11/2026, option 1) : des numéros de loi distincts. Une loi peut avoir deux actes de
        # promulgation, un par identifiant de dossier (2017-1338 : DLR5L14N35824 et DLR5L15N35824) ;
        # elle est rangée sous la plus ancienne législature de ses dossiers.
        n = ctx.un("SELECT count(DISTINCT numero_loi) FROM loi WHERE legislature = ? AND date_promulgation <= ?",
                   [numero, au])
        par_leg = ctx.x("""SELECT l, count(*) FROM (
                               SELECT loi.numero_loi, min(TRY_CAST(d.legislature AS INTEGER)) AS l FROM loi
                               LEFT JOIN an_dossiers__dossier d ON d.uid = loi.dossier
                               WHERE loi.legislature = ? AND loi.date_promulgation <= ? GROUP BY 1)
                           GROUP BY 1 ORDER BY 1""", [numero, au])
        organiques = ctx.un("""SELECT count(DISTINCT loi.numero_loi) FROM loi
                               JOIN an_dossiers__dossier d ON d.uid = loi.dossier
                               WHERE loi.legislature = ? AND loi.date_promulgation <= ?
                                 AND d.procedure_libelle ILIKE '%organique%'""", [numero, au])
        anterieurs = sum(c for l, c in par_leg if l is not None and l < numero)
        sans_leg = ctx.un("SELECT count(DISTINCT numero_loi) FROM loi WHERE legislature IS NULL")
        out.append(_compte(
            "lois", n, au, _regle(ctx, "loi"),
            "Lois promulguées pendant la législature : numéros de loi des actes de promulgation "
            "des dossiers législatifs dont la date tombe dans la législature, quelle que soit la "
            "législature où le dossier a été ouvert.",
            detail=(f"Dont {_fr(anterieurs)} issues d'un dossier ouvert sous une législature "
                    f"antérieure et {_fr(organiques)} de procédure « loi organique ». "
                    f"{_fr(sans_leg)} promulgation(s) du corpus hors de toute législature."),
            points=_points(ctx, "an_dossiers__acte"), licences=lic_an,
            par_legislature_du_dossier=[{"legislature": l, "lois": c} for l, c in par_leg],
            dont_procedure_organique=organiques))

    # Lois par adoption (issue #83) : à côté du compte par promulgation, qui ne change pas.
    if ctx.existe("loi_adoption"):
        out.append(_compte_lois_par_adoption(ctx, numero, au, lic_an))

    # Votes solennels.
    if ctx.existe("scrutin_nature"):
        rows = ctx.x("""SELECT nature, count(*) FROM scrutin_nature
                        WHERE legislature = ? AND solennel AND date <= ? GROUP BY 1 ORDER BY 1""",
                     [numero, au])
        dernier = ctx.un("SELECT max(date) FROM scrutin_nature WHERE legislature = ? AND date <= ?",
                         [numero, au])
        # Trous de l'archive (R-CONTINUITE-SCRUTINS) : le compte porte sur ce que l'archive contient.
        from ..regles.r_continuite_scrutins import date_des_donnees, marquer, trous
        ts = trous(ctx, numero)
        out.append(marquer(_compte(
            "votes_solennels", sum(c for _, c in rows), au, _regle(ctx, "scrutin_nature"),
            "Scrutins publics solennels (type lu dans le code du scrutin, jamais dans son libellé).",
            detail=f"Dernier scrutin publié le {_date_fr(dernier)}.",
            points=_points(ctx, "an_scrutins__scrutin"), licences=lic_an,
            par_nature=[{"nature": k, "scrutins": c} for k, c in rows],
            dernier_scrutin_publie=dernier), ts))
        out[-1]["au"] = date_des_donnees(out[-1]["au"], ts)

    # 49.3 : textes adoptés sans vote ; engagements distincts. Jamais une position de vote.
    if not _manquantes(ctx, "engagement_49_3", "etat_dossier"):
        fin = au
        textes, engagements = ctx.x("""
            WITH e AS (SELECT * FROM engagement_49_3 WHERE date >= ? AND date <= ?)
            SELECT (SELECT count(DISTINCT s.dossier) FROM etat_dossier s
                    WHERE s.adopte_par_49_3 AND coalesce(s.procedure_code, '') <> '13'
                      AND s.dossier IN (SELECT dossier FROM e)),
                   (SELECT count(DISTINCT acte) FROM e)""", [debut, fin])[0]
        out.append(_compte(
            "textes_adoptes_49_3", textes, au, _regle(ctx, "etat_dossier"),
            "Textes sur lesquels le gouvernement a engagé sa responsabilité (article 49, alinéa 3) "
            "pendant la législature et qui ont été adoptés ou promulgués. C'est un fait de "
            "procédure : le texte est adopté sans vote sur son ensemble.",
            detail=f"{_fr(engagements)} engagements de responsabilité distincts sur la période.",
            points=_points(ctx, "an_dossiers__acte"), licences=lic_an,
            engagements_distincts=engagements))

    # Motions de censure mises aux voix.
    if ctx.existe("scrutin_nature"):
        n, adoptees = ctx.x("""SELECT count(*), count(*) FILTER (sort = 'adopte') FROM scrutin_nature
                               WHERE legislature = ? AND motion_censure AND date <= ?""",
                            [numero, au])[0]
        out.append(_compte(
            "motions_censure", n, au, _regle(ctx, "scrutin_nature"),
            "Motions de censure mises aux voix (scrutins de type « motion de censure »).",
            detail=f"Dont {_fr(adoptees)} adoptée(s).", points=_points(ctx, "an_scrutins__scrutin"),
            licences=lic_an, adoptees=adoptees))
    return out


def _compte_lois_par_adoption(ctx, numero, au, lic_an) -> dict:
    """Lois adoptées en dernier par l'Assemblée pendant la législature, puis promulguées
    (R-LOI-ADOPTION). Daté comme les autres comptes (`au` : fin d'une législature close, toutes
    ses adoptions sont antérieures) ; les promulgations sont lues à la date de référence
    (`promulgations_lues_au`), car une loi adoptée avant la fin peut être promulguée après. Statut
    `partiel` quand des lois qui ont pu être adoptées pendant la législature (promulguées, votées
    par l'Assemblée, closes ou discutées en séance pendant celle-ci) n'ont pas de législature
    d'adoption établie : leur nombre et leurs raisons sont servis."""
    ref = _date_reference(ctx)
    # Une loi adoptée par l'Assemblée avant le périmètre (Q67) a été adoptée sous une autre
    # législature : elle est comptée comme telle, jamais comme incertaine.
    n, apres, avant, hors = ctx.x("""
        SELECT count(*) FILTER (legislature_adoption = $1),
               count(*) FILTER (legislature_adoption = $1 AND legislature_promulgation IS DISTINCT FROM $1),
               count(*) FILTER (legislature_promulgation = $1
                                AND (legislature_adoption <> $1 OR raison_adoption = $3)),
               count(*) FILTER (legislature_promulgation = $1 AND raison_adoption = $3)
        FROM loi_adoption WHERE date_promulgation <= $2""", [numero, ref, HORS_PERIMETRE])[0]
    incertaines = ctx.x("""
        SELECT raison_adoption, count(*) FROM loi_adoption
        WHERE legislature_adoption IS NULL AND date_promulgation <= $2 AND raison_adoption <> $3
          AND $1 IN (legislature_promulgation, legislature_dernier_vote_an, legislature_cloture,
                     legislature_derniere_seance_an)
        GROUP BY 1 ORDER BY 2 DESC, 1""", [numero, ref, HORS_PERIMETRE])
    nb_incertaines = sum(c for _, c in incertaines)
    par_promulgation = ctx.x("""
        SELECT legislature_promulgation, count(*) FROM loi_adoption
        WHERE legislature_adoption = ? AND date_promulgation <= ? GROUP BY 1 ORDER BY 1 NULLS LAST""",
                             [numero, ref])
    return _compte(
        "lois_par_adoption", n, au, _regle(ctx, "loi_adoption"),
        "Lois adoptées en dernier par l'Assemblée pendant la législature, puis promulguées, même "
        "après sa fin : date de la dernière décision enregistrée de l'Assemblée qui adopte le "
        "texte, même quand le Sénat vote en dernier, sous la même législature ou la suivante. Le "
        "compte des lois promulguées pendant la législature est servi à côté.",
        statut="complet" if nb_incertaines == 0 else "partiel",
        detail=(f"Dont {_fr(apres)} promulguée(s) après la fin de la législature ou entre deux "
                f"législatures. {_fr(avant)} loi(s) promulguée(s) pendant la législature, adoptée(s) "
                f"sous une autre"
                + (f", dont {_fr(hors)} avant la XIVe (hors périmètre)" if hors else "")
                + f". {_fr(nb_incertaines)} loi(s) qui ont pu être adoptées pendant la "
                "législature sans législature d'adoption établie"
                + (" (" + ", ".join(f"{r} : {_fr(c)}" for r, c in incertaines) + ")."
                   if incertaines else ".")),
        points=_points(ctx, "an_dossiers__acte", "jo_actes__acte_reglementaire"), licences=lic_an,
        promulgations_lues_au=ref, promulguees_hors_de_la_legislature=apres,
        promulguees_pendant_et_adoptees_sous_une_autre=avant,
        dont_adoptees_avant_le_perimetre=hors,
        par_legislature_de_promulgation=[{"legislature": l, "lois": c} for l, c in par_promulgation],
        sans_legislature_d_adoption=[{"raison": r, "lois": c} for r, c in incertaines])


# --------------------------------------------------------------------------- qui siège

def _section_hemicycle(ctx, f, leg, au, lic):
    points = _points(ctx, "an_acteurs__mandat")
    manque = _manquantes(ctx, "hemicycle")
    if manque:
        f.section("hemicycle", [], "siege_hemicycle", couverture=_absente(manque, points))
        return
    lignes = _lignes(ctx, """
        WITH ident AS (SELECT uid, any_value(prenom) AS prenom, any_value(nom) AS nom,
                              any_value(nom_alpha) AS nom_alpha
                       FROM an_acteurs__identite_source GROUP BY 1)
        SELECT h.siege, h.acteur, i.prenom, i.nom, h.groupe, g.sigle AS groupe_sigle,
               g.libelle AS groupe_libelle, h.rattachement, h.raison_rattachement, h.raison_siege,
               h.mandat, h.date, h.date_origine, h.source_url, m.prov_point AS source_point
        FROM hemicycle h LEFT JOIN ident i ON i.uid = h.acteur
        LEFT JOIN groupe g ON g.organe = h.groupe
        LEFT JOIN (SELECT uid, any_value(prov_point) AS prov_point FROM an_acteurs__mandat GROUP BY 1) m
               ON m.uid = h.mandat
        WHERE h.legislature = ?
        ORDER BY h.siege NULLS LAST, i.nom_alpha, h.acteur""", [leg["numero"]])
    for l in lignes:
        l["licence"] = lic.get(l["source_point"])
    n = len(lignes)
    siege = sum(1 for l in lignes if l["siege"] is not None)
    ratt = sum(1 for l in lignes if l["rattachement"] != "non_etabli")
    jour = lignes[0]["date"] if lignes else None
    if not leg["en_cours"] and not lignes:
        couv = {"statut": "borne_historique", "numerateur": 0, "denominateur": None,
                "detail": "Le siège n'est publié que dans l'archive figée d'une législature close, "
                          "et celle-ci n'en a pas d'utilisable (XIVe : pas d'archive figée au chemin "
                          "standard).",
                "points_acces": points}
    elif not leg["en_cours"]:
        couv = _couv(min(siege, ratt), n,
                     f"{_fr(siege)} sièges connus et {_fr(ratt)} groupes (ou non-inscrits) établis "
                     f"sur {_fr(n)} députés en fonction le {_date_fr(jour)}, d'après l'archive figée "
                     "de la législature : c'est l'état qu'elle publie à cette date.",
                     points, au=jour)
    else:
        couv = _couv(min(siege, ratt), n,
                     f"{_fr(siege)} sièges connus et {_fr(ratt)} groupes (ou non-inscrits) établis "
                     f"sur {_fr(n)} députés en fonction le {_date_fr(jour)}. Le siège n'est pas "
                     "daté par la source : c'est celui du jour de lecture.",
                     points, au=jour)
    f.section("hemicycle", lignes, "siege_hemicycle",
              ids={"acteur": "acteur", "mandat": "mandat", "organe": "groupe"}, date="date",
              couverture=couv, colonnes=COLS_HEMICYCLE,
              extra={"ordre": "hemicycle", "au": jour, "source_uid": "acteur"})


def _section_groupes(ctx, f, leg, au, lic):
    points = _points(ctx, "an_acteurs__mandat", "an_acteurs__organe")
    manque = _manquantes(ctx, "groupe", "effectif_groupe", "hemicycle")
    if manque:
        f.section("groupes", [], "effectif_groupe", couverture=_absente(manque, points))
        return
    numero = leg["numero"]
    # Jour de constat : celui de l'hémicycle (législature en cours) ; pour une législature close,
    # dont l'hémicycle n'est pas publié, le dernier jour de la législature.
    jour = ctx.un("SELECT any_value(date) FROM hemicycle WHERE legislature = ?", [numero]) or au
    avec_hemicycle = bool(ctx.un("SELECT count(*) FROM hemicycle WHERE legislature = ?", [numero]))
    lignes = _lignes(ctx, """
        SELECT g.organe AS groupe, g.sigle, g.libelle, g.debut, g.fin, g.position_declaree,
               CASE WHEN g.fin IS NULL OR g.fin >= ? THEN e.effectif END AS effectif,
               CASE WHEN g.fin IS NULL OR g.fin >= ? THEN ? END AS au,
               CASE WHEN g.fin < ? THEN ef.effectif END AS effectif_a_la_fin,
               CASE WHEN ? THEN (SELECT count(*) FROM hemicycle h WHERE h.groupe = g.organe
                                 AND h.legislature = ?) END AS sieges_dans_l_hemicycle,
               'groupe' AS rattachement, o.prov_point AS source_point, o.prov_uid AS source_uid
        FROM groupe g
        LEFT JOIN effectif_groupe e ON e.groupe = g.organe AND e.date = ?
        LEFT JOIN effectif_groupe ef ON ef.groupe = g.organe AND ef.date = g.fin
        LEFT JOIN an_acteurs__organe o ON o.uid = g.organe
        WHERE g.legislature = ? AND g.debut <= ?
        ORDER BY g.sigle, g.debut""", [jour, jour, jour, jour, avec_hemicycle, numero, jour, numero, au])
    # Non-inscrits et rattachement non établi : pas des groupes, comptés à part (s'il y en a).
    for ratt, libelle in (("non_inscrit", "Non-inscrits"), ("non_etabli", "Groupe non établi")):
        n = ctx.un("SELECT count(*) FROM hemicycle WHERE legislature = ? AND rattachement = ?",
                   [numero, ratt])
        if n:
            lignes.append({"groupe": None, "sigle": "NI" if ratt == "non_inscrit" else None,
                           "libelle": libelle, "debut": None, "fin": None,
                           "position_declaree": None, "effectif": n, "au": jour,
                           "effectif_a_la_fin": None, "sieges_dans_l_hemicycle": n,
                           "rattachement": ratt, "source_point": points[0] if points else None,
                           "source_uid": None})
    # Lien de chaque groupe vers la fiche de sa lignée (R-LIGNEE), quand elle est publiée.
    lignee_de = {}
    if not _manquantes(ctx, "lignee", "lignee_maillon"):
        lignee_de = {o: a for o, a in ctx.x("""
            SELECT unnest(m.organes), l.adresse FROM lignee_maillon m JOIN lignee l USING (lignee)
            WHERE l.publiee AND m.affiche""")}
    for l in lignes:
        l["licence"] = lic.get(l["source_point"])
        # Lien vers la lignée pour les groupes seulement : une ligne sans identifiant (non-inscrits)
        # est reconnue par C1 à sa valeur sans ses comptes (`CHAMPS_DE_COMPTE`), qui ne doit pas
        # changer.
        if l["groupe"]:
            ad = lignee_de.get(l["groupe"])
            l["lien"] = f"lignee/{ad}" if ad else None
    grp = [l for l in lignes if l["rattachement"] == "groupe"]
    declares = sum(1 for l in grp if l["position_declaree"] != "non_declaree")
    ecarts = [l["sigle"] for l in grp if l["effectif"] is not None and avec_hemicycle
              and l["effectif"] != l["sieges_dans_l_hemicycle"]]
    detail = (f"Effectif de chaque groupe le {_date_fr(jour)}, apparentés compris. Position "
              f"déclarée par {_fr(declares)} groupe(s) sur {_fr(len(grp))} : sans déclaration, "
              "« non déclarée », jamais déduite.")
    if not avec_hemicycle:
        detail += (" Les sièges de cette législature close ne sont pas publiés (pas d'archive figée "
                   "utilisable) : ils ne sont pas servis, et les non-inscrits ne sont pas comptés ici.")
    if ecarts:
        detail += " Effectif et sièges diffèrent pour : " + ", ".join(ecarts) + "."
    f.section("groupes", lignes, "effectif_groupe", ids={"organe": "groupe"}, date="au",
              couverture=_couv(len(grp) - len(ecarts), len(grp), detail, points,
                               sinon="en_cours", au=jour),
              extra={"ordre": "alphabetique", "au": jour})


# --------------------------------------------------------------------------- ordre du jour

def _section_ordre_du_jour(ctx, f, leg, au, lic):
    points = _points(ctx, "an_agenda__reunion", "an_agenda__point_odj")
    manque = _manquantes(ctx, "ordre_du_jour")
    if manque:
        f.section("ordre-du-jour", [], "point_ordre_du_jour", couverture=_absente(manque, points))
        return
    lignes = _lignes(ctx, """
        SELECT o.date, o.reunion, o.rang, o.objet, o.dossier, d.titre AS titre_dossier,
               CASE WHEN len(o.dossiers) > 1 THEN o.dossiers END AS dossiers,
               o.statut_seance, o.statut_point, o.lien_dossier, o.commission,
               o.commission_libelle, o.matiere_statut, o.type_point, o.compte_rendu,
               o.date > ? AS a_venir, o.point, o.source_url,
               r.prov_point AS source_point
        FROM ordre_du_jour o
        LEFT JOIN an_dossiers__dossier d ON d.uid = o.dossier
        LEFT JOIN (SELECT uid, any_value(prov_point) AS prov_point
                   FROM an_agenda__reunion GROUP BY 1) r ON r.uid = o.reunion
        WHERE o.legislature = ?
        ORDER BY o.date, o.reunion, o.rang NULLS FIRST""", [au, leg["numero"]])
    for l in lignes:
        l["licence"] = lic.get(l["source_point"])
        if l["dossiers"] is not None:
            l["dossiers"] = list(l["dossiers"])
    par_annee: dict[str, list] = {}
    for l in lignes:
        par_annee.setdefault((l["date"] or "sans-date")[:4], []).append(l)
    if not par_annee:
        # Aucune séance publique pour cette législature : la source ne la publie pas (l'archive
        # « Agenda XIV » ne contient que des réunions de groupes et de délégations, datées de
        # 2017-2018). Un trou de la source, jamais un « 0 séance » complet.
        f.section("ordre-du-jour-vide", [], "point_ordre_du_jour",
                  couverture={"statut": "trou_source", "numerateur": None, "denominateur": None,
                              "detail": f"L'agenda publié par l'Assemblée ne contient aucune séance "
                                        f"publique de la {_nom(leg['numero'])} : son ordre du jour "
                                        "n'est pas servi.", "points_acces": points},
                  colonnes=COLS_ODJ, extra={"ordre": "chronologique", "annee": None, "au": au})
        return
    for annee, ls in sorted(par_annee.items()):
        conf = [l for l in ls if l["rang"] is not None and l["statut_seance"] == "confirmee"
                and l["statut_point"] == "confirme"]
        lies = sum(1 for l in conf if l["lien_dossier"] in ("lie", "plusieurs_dossiers"))
        seances = len({l["reunion"] for l in ls})
        avenir = len({l["reunion"] for l in ls if l["a_venir"]})
        detail = (f"{_fr(seances)} séances publiques de l'Assemblée ({_fr(avenir)} à venir après le "
                  f"{_date_fr(au)}). {_fr(lies)} points confirmés sur {_fr(len(conf))} citent un "
                  "dossier ; les autres (questions, débats, déclarations) n'en citent aucun et sont "
                  "montrés comme non liés. Ni le Sénat ni les réunions de commission.")
        f.section(f"ordre-du-jour-{annee}", ls, "point_ordre_du_jour",
                  ids={"reunion": "reunion", "dossier": "dossier", "compte_rendu": "compte_rendu",
                       "organe": "commission", "autre": "point"},
                  date="date",
                  couverture={"statut": "complet", "numerateur": lies, "denominateur": len(conf),
                              "detail": detail, "points_acces": points},
                  colonnes=COLS_ODJ,
                  extra={"ordre": "chronologique", "annee": annee, "au": au,
                         "source_uid": "reunion", "aide_a_la_lecture": ["commission_libelle"]})


# --------------------------------------------------------------------------- textes

def _section_textes(ctx, f, leg, au, lic) -> list[dict]:
    points = _points(ctx, "an_dossiers__dossier", "an_dossiers__acte", "an_acteurs__organe")
    manque = _manquantes(ctx, "etat_dossier", "matiere")
    if manque:
        f.section("textes", [], "texte_legislature", couverture=_absente(manque, points))
        return []
    numero = leg["numero"]
    fin = leg["fin"] or au
    # Vote solennel (#71) : un scrutin solennel de la législature relié au dossier.
    if ctx.existe("lien_scrutin_dossier") and ctx.existe("scrutin_nature"):
        sol = f"""(SELECT l.dossier, list(DISTINCT l.scrutin ORDER BY l.scrutin) AS scrutins
                   FROM lien_scrutin_dossier l JOIN scrutin_nature n USING (scrutin)
                   WHERE n.solennel AND CAST(n.legislature AS INTEGER) = {int(numero)} GROUP BY 1)"""
    else:
        sol = "(SELECT NULL::VARCHAR AS dossier, NULL::VARCHAR[] AS scrutins WHERE false)"
    # Initiateur nominatif (#71) : premier auteur du texte déposé, ou initiative gouvernementale.
    if ctx.existe("texte_porte"):
        ini = """(SELECT document, count(*) FILTER (role = 'auteur') AS nb_auteurs,
                         arg_min(acteur, coalesce(rang, 999999)) AS acteur,
                         arg_min(role, coalesce(rang, 999999)) AS role,
                         any_value(gouvernement) FILTER (role = 'initiative_gouvernementale') AS gouvernement
                  FROM texte_porte WHERE role IN ('auteur', 'initiative_gouvernementale') GROUP BY 1)"""
    else:
        ini = ("(SELECT NULL::VARCHAR AS document, NULL::BIGINT AS nb_auteurs, NULL::VARCHAR AS acteur, "
               "NULL::VARCHAR AS role, NULL::VARCHAR AS gouvernement WHERE false)")
    # Législature d'adoption de la loi (#83, R-LOI-ADOPTION).
    adop = ("(SELECT numero_loi, legislature_adoption, preuve_adoption, raison_adoption FROM loi_adoption)"
            if ctx.existe("loi_adoption") else
            "(SELECT NULL::VARCHAR AS numero_loi, NULL::INTEGER AS legislature_adoption, "
            "NULL::VARCHAR AS preuve_adoption, NULL::VARCHAR AS raison_adoption WHERE false)")
    grp = ("""(SELECT a.acteur, a.groupe, a.debut, coalesce(a.fin, '9999-12-31') AS fin, g.sigle
               FROM appartenance a LEFT JOIN (SELECT organe, any_value(sigle) AS sigle FROM groupe GROUP BY 1) g
                    ON g.organe = a.groupe)""" if ctx.existe("appartenance") and ctx.existe("groupe")
           else "(SELECT NULL::VARCHAR AS acteur, NULL::VARCHAR AS groupe, NULL::VARCHAR AS debut, "
                "NULL::VARCHAR AS fin, NULL::VARCHAR AS sigle WHERE false)")
    lignes = _lignes(ctx, f"""
        WITH depot AS (
            SELECT dossier, arg_min(texte_associe, coalesce(date, '9999') || uid) AS texte_depose,
                   min(left(date, 10)) AS date_depot,
                   arg_min(CASE WHEN code LIKE 'AN%' THEN 'AN' WHEN code LIKE 'SN%' THEN 'SN' END,
                           coalesce(date, '9999') || uid) AS chambre_depot
            FROM an_dossiers__acte WHERE type_acte = 'DepotInitiative_Type' GROUP BY 1)
        SELECT e.dossier, e.titre, p.texte_depose,
               p.chambre_depot, p.date_depot,
               CASE WHEN left(p.texte_depose, 4) = 'PRJL' THEN 'gouvernement'
                    WHEN left(p.texte_depose, 4) IN ('PION', 'PNRE') AND p.chambre_depot = 'AN' THEN 'deputes'
                    WHEN left(p.texte_depose, 4) IN ('PION', 'PNRE') AND p.chambre_depot = 'SN' THEN 'senateurs'
                    ELSE 'non_etabli' END AS initiateur,
               e.procedure_code, d.procedure_libelle,
               TRY_CAST(d.legislature AS INTEGER) AS legislature_dossier,
               m.statut AS matiere_statut, m.commission,
               coalesce(o.libelle, m.libelle) AS commission_libelle, o.type_organe AS type_commission,
               m.raison AS raison_matiere,
               e.etape_atteinte AS etape, e.date_etape, e.raison_etape,
               e.sort, e.date_sort, e.raison_sort,
               CASE WHEN e.date_sort IS NULL THEN NULL
                    ELSE e.date_sort >= ? AND e.date_sort <= ? END AS sort_pendant_la_legislature,
               e.par_49_3, e.adopte_par_49_3, e.numero_loi, e.date_promulgation, e.url_loi,
               la.legislature_adoption AS legislature_adoption_loi, la.preuve_adoption AS preuve_adoption_loi,
               la.raison_adoption AS raison_adoption_loi,
               sol.scrutins IS NOT NULL AS vote_solennel, sol.scrutins AS scrutins_solennels,
               ini.role AS initiateur_role, ini.acteur AS initiateur_acteur,
               (SELECT any_value(g.groupe) FROM {grp} g WHERE g.acteur = ini.acteur AND ini.role = 'auteur'
                  AND g.debut <= p.date_depot AND g.fin >= p.date_depot) AS initiateur_groupe,
               (SELECT any_value(g.sigle) FROM {grp} g WHERE g.acteur = ini.acteur AND ini.role = 'auteur'
                  AND g.debut <= p.date_depot AND g.fin >= p.date_depot) AS initiateur_groupe_sigle,
               ini.gouvernement AS initiateur_gouvernement, ini.nb_auteurs,
               e.source_url, d.prov_point AS source_point
        FROM etat_dossier e
        JOIN depot p ON p.dossier = e.dossier
        LEFT JOIN {sol} sol ON sol.dossier = e.dossier
        LEFT JOIN {adop} la ON la.numero_loi = e.numero_loi
        LEFT JOIN {ini} ini ON ini.document = p.texte_depose
        LEFT JOIN an_dossiers__dossier d ON d.uid = e.dossier
        LEFT JOIN matiere m ON m.dossier = e.dossier
        LEFT JOIN an_acteurs__organe o ON o.uid = m.commission
        WHERE e.legislature = ?
        ORDER BY p.date_depot NULLS LAST, e.dossier""", [leg["debut"], fin, numero])
    # Nom de l'initiateur : prénom et nom de l'archive des acteurs (une ligne par acteur).
    noms = {}
    if ctx.existe("an_acteurs__identite_source") and any(l["initiateur_acteur"] for l in lignes):
        noms = {u: {"nom": " ".join(x for x in (pr, no) if x) or None} for u, pr, no in ctx.x(
            "SELECT uid, any_value(prenom), any_value(nom) FROM an_acteurs__identite_source "
            "WHERE uid IN (SELECT unnest(?::VARCHAR[])) GROUP BY uid",
            [sorted({l["initiateur_acteur"] for l in lignes if l["initiateur_acteur"]})])}
    for l in lignes:
        l["licence"] = lic.get(l["source_point"])
        l["initiateur_nom"] = (noms.get(l["initiateur_acteur"]) or {}).get("nom")
    ecartes = _lignes(ctx, """
        SELECT d.procedure_libelle, count(*) AS dossiers FROM etat_dossier e
        JOIN an_dossiers__dossier d ON d.uid = e.dossier
        WHERE e.legislature = ? AND e.dossier NOT IN
              (SELECT dossier FROM an_dossiers__acte WHERE type_acte = 'DepotInitiative_Type')
        GROUP BY 1 ORDER BY 1""", [numero])
    n = len(lignes)
    mat = sum(1 for l in lignes if l["matiere_statut"] in ("assemblee", "senat_seulement"))
    sen = sum(1 for l in lignes if l["matiere_statut"] == "senat_seulement")
    eta = sum(1 for l in lignes if l["etape"] != "non_etablie")
    ini = sum(1 for l in lignes if l["initiateur"] != "non_etabli")
    connu = sum(1 for l in lignes if l["sort"] != "non_connu")
    detail = (f"{_fr(n)} textes déposés et avancés pendant la législature. Matière établie pour "
              f"{_fr(mat)} (dont {_fr(sen)} « saisi au Sénat seulement ») ; les autres : « matière "
              f"non établie ». Étape établie pour {_fr(eta)}, initiateur pour {_fr(ini)}, sort "
              f"connu pour {_fr(connu)} (les autres : navette en cours ou texte non examiné). "
              f"{_fr(sum(e['dossiers'] for e in ecartes))} dossiers sans texte déposé (rapports, "
              "missions, engagements de responsabilité…) sont écartés. Les textes du seul Sénat ne "
              "sont pas lus.")
    # Poids (cahier 4.7) : les textes seulement déposés, au sort non connu (les trois quarts),
    # ne sont affichés qu'en décompte ; leur liste est à part, par année de dépôt.
    seulement_deposes = [l for l in lignes if l["etape"] == "depot" and l["sort"] == "non_connu"]
    avances = [l for l in lignes if not (l["etape"] == "depot" and l["sort"] == "non_connu")]
    par_annee: dict[str, list] = {}
    for l in seulement_deposes:
        # Année du dépôt dans la législature (un texte du Sénat est redéposé à chaque législature).
        par_annee.setdefault((l["date_etape"] or "sans-date")[:4], []).append(l)
    commun = {"ids": {"dossier": "dossier", "document": "texte_depose", "organe": "commission"},
              "date": "date_etape", "colonnes": COLS_TEXTES}
    extra = {"ordre": "chronologique", "au": au, "source_uid": "dossier",
             "initiateur_lu_dans": "identifiant du texte déposé (PRJL : gouvernement ; PION ou "
                                   "PNRE déposé à l'Assemblée : députés, au Sénat : sénateurs)",
             "aide_a_la_lecture": ["commission_libelle"]}
    ma = sum(1 for l in avances if l["matiere_statut"] in ("assemblee", "senat_seulement"))
    f.section("textes", avances, "texte_legislature", **commun,
              couverture=_couv(ma, len(avances), detail, points, matiere_etablie=[mat, n],
                               etape_etablie=[eta, n], initiateur_etabli=[ini, n],
                               sort_connu=[connu, n], textes=n,
                               dans_ce_fichier=len(avances)),
              extra={**extra, "dossiers_ecartes": ecartes,
                     "selection": "textes examinés au-delà du dépôt, ou dont le sort est connu ; "
                                  "les textes seulement déposés sont dans textes-deposes-<annee>",
                     "textes_deposes_par_annee": {a: len(v) for a, v in sorted(par_annee.items())}})
    for annee, ls in sorted(par_annee.items()):
        m = sum(1 for l in ls if l["matiere_statut"] in ("assemblee", "senat_seulement"))
        f.section(f"textes-deposes-{annee}", ls, "texte_legislature", **commun,
                  couverture=_couv(m, len(ls),
                                   f"{_fr(len(ls))} textes déposés dans la législature en {annee}, ni examinés en "
                                   f"commission ni discutés en séance au {_date_fr(au)} ; matière "
                                   f"établie pour {_fr(m)}.", points),
                  extra={**extra, "annee_de_depot_dans_la_legislature": annee})
    return lignes


def _section_commissions(ctx, f, leg, au, lic, textes: list[dict]):
    points = _points(ctx, "an_dossiers__acte", "an_acteurs__organe")
    if not textes:
        f.section("commissions", [], "decompte_commission_etape",
                  couverture=_absente(_manquantes(ctx, "etat_dossier", "matiere") or ["textes"],
                                      points))
        return
    cles: dict[tuple, dict] = {}
    for t in textes:
        k = (t["matiere_statut"], t["commission"], t["etape"])
        if k not in cles:
            libelle = t["commission_libelle"] if t["matiere_statut"] == "assemblee" else (
                "Saisi au Sénat seulement" if t["matiere_statut"] == "senat_seulement"
                else "Matière non établie")
            cles[k] = {"commission": t["commission"], "commission_libelle": libelle,
                       "type_commission": t["type_commission"], "matiere_statut": t["matiere_statut"],
                       "etape": t["etape"], "dossiers": 0, "au": au,
                       "source_point": t["source_point"], "licence": t["licence"]}
        cles[k]["dossiers"] += 1
    ordre_matiere = {"assemblee": 0, "senat_seulement": 1, "non_etablie": 2}
    lignes = sorted(cles.values(), key=lambda l: (ordre_matiere.get(l["matiere_statut"], 3),
                                                  l["commission_libelle"] or "",
                                                  ETAPES.index(l["etape"]) if l["etape"] in ETAPES else 9))
    n = len(textes)
    mat = sum(1 for t in textes if t["matiere_statut"] == "assemblee")
    detail = (f"Décomptes de dossiers par commission saisie au fond et par étape atteinte dans la "
              f"législature, au {_date_fr(au)} : {_fr(mat)} textes sur {_fr(n)} ont une commission de "
              "l'Assemblée saisie au fond. Chaque texte est compté une fois. Les travaux propres "
              "des commissions (réunions, auditions, rapports d'information) ne sont pas lus.")
    f.section("commissions", lignes, "decompte_commission_etape",
              ids={"organe": "commission", "autre": "etape"}, date="au", source=None,
              couverture=_couv(mat, n, detail, points, sinon="trou_source"),
              extra={"ordre": "alphabetique", "au": au, "etapes": list(ETAPES),
                     "aide_a_la_lecture": ["commission_libelle"]})


def _couverture_regles(ctx) -> list[dict]:
    """Les règles lues par la fiche et leur version (page de méthodologie)."""
    out = []
    for vue in ("legislature", "gouvernement_legislature", "depute", "hemicycle", "effectif_groupe",
                "loi", "loi_adoption", "scrutin_nature", "engagement_49_3", "ordre_du_jour", "matiere",
                "etape_dossier", "etat_dossier"):
        r = _regle(ctx, vue)
        out.append({"sortie": vue, "regle": r, "presente": r is not None})
    return out


# --------------------------------------------------------------------------- mots des titres

COLS_MOTS_TITRES = ["mot", "forme", "textes", "dossiers"]
NB_MOTS_TITRES = 100
_LETTRES = re.compile(r"[^\W\d_]+")


def _normalisation_titres(ctx) -> dict[str, list[str]]:
    """La normalisation déclarée (`references/mots_titres/`, issue #82) : `formule`, `mot_vide`,
    `verbe_intention`. Vide sans décision : le nuage n'est alors pas composé."""
    par: dict[str, list[str]] = defaultdict(list)
    for d in ctx.decisions.get("normalisation_titres", []):
        if d.get("genre") and d.get("texte"):
            par[d["genre"]].append(str(d["texte"]))
    return par


def _section_mots_titres(ctx, f, leg, au, lic, textes):
    """Nuage des mots des titres de la législature (#82) : pour chaque mot, les textes dont le titre
    le contient, après la normalisation déclarée. Les titres ne changent pas ; chaque mot renvoie
    aux dossiers qui le portent. Un décompte, jamais un classement de personnes."""
    from .candidat import VIDES, _norm
    points = _points(ctx, "an_dossiers__dossier")
    norm = _normalisation_titres(ctx)
    if not norm:
        f.section("mots-titres", [], "mot_titre_legislature",
                  couverture={"statut": "non_collecte", "detail": "Aucune normalisation des titres n'est "
                              "décidée (références `normalisation_titres`) : pas de nuage de mots.",
                              "points_acces": points},
                  colonnes=COLS_MOTS_TITRES)
        return
    # Formules : la plus longue d'abord (« proposition de loi organique » avant « proposition de loi »).
    formules = sorted({" " + " ".join(_LETTRES.findall(_norm(x))) + " " for x in norm.get("formule", [])},
                      key=len, reverse=True)
    ecartes = VIDES | {_norm(x) for k in ("mot_vide", "verbe_intention") for x in norm.get(k, [])}
    par_mot: dict[str, set] = defaultdict(set)
    formes: dict[str, Counter] = defaultdict(Counter)
    for t in textes:
        titre = t.get("titre") or ""
        brut = _LETTRES.findall(titre.lower())
        cle = " " + " ".join(_norm(w) for w in brut) + " "
        for fo in formules:
            cle = cle.replace(fo, " ")
        gardes = {w for w in cle.split() if len(w) >= 3 and w not in ecartes}
        for w in brut:
            n = _norm(w)
            if n in gardes:
                formes[n][w] += 1
        for n in gardes:
            par_mot[n].add(t["dossier"])
    lignes = [{"mot": m, "forme": formes[m].most_common(1)[0][0] if formes[m] else m,
               "textes": len(ds), "dossiers": sorted(ds)}
              for m, ds in par_mot.items()]
    lignes.sort(key=lambda r: (-r["textes"], r["mot"]))
    lignes = lignes[:NB_MOTS_TITRES]
    n_textes = len(textes)
    f.section("mots-titres", lignes, "mot_titre_legislature",
              ids={"autre": "mot"},
              couverture={"statut": "complet", "numerateur": len(lignes), "denominateur": len(par_mot),
                          "detail": f"Les {_fr(len(lignes))} mots les plus fréquents (sur {_fr(len(par_mot))}) "
                                    f"des titres des {_fr(n_textes)} textes de la législature, après la "
                                    "normalisation déclarée en méthodologie : formules de procédure, mots "
                                    "vides et verbes d'intention écartés. Chaque mot renvoie aux dossiers "
                                    "qui le portent.",
                          "points_acces": points},
              colonnes=COLS_MOTS_TITRES,
              extra={"ordre": "nombre de textes décroissant, puis mot", "au": au,
                     "normalisation": "references/mots_titres/normalisation.yaml"})

