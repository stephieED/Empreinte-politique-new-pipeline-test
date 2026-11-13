"""Rapport de mesures (commande de réalisation, section 5) : les chiffres de chaque nuit.

Relit le rapport que chaque mise à jour qui écrit dépose dans l'artefact `rapport` (gardé 90 jours) et
les durées des tâches que GitHub Actions publie pour l'exécution, puis rend un tableau par mesure, une
ligne par nuit. Rien n'est estimé : une mesure absente d'un rapport reste vide.

Le pic de mémoire d'une tâche est le **maximum des pics de ses étapes** (`pic_memoire_mo` des
mesures du rapport). Le `Maximum resident set size` de `time -v`, imprimé dans le journal de la
tâche, ne vaut que pour la dernière étape : `mesures.Mesures.etape` remet à zéro le pic du processus
au début de chaque étape, et `time -v` lit ce même compteur à la fin (constaté le 13/11/2026).

    empreinte rapport-mesures --depot <propriétaire/dépôt> --cache <dossier> --sortie <fichier.md>
"""
from __future__ import annotations

import json
import os
import re
import statistics
from collections import defaultdict
from datetime import datetime, timezone

from . import distant

ARTEFACT = "rapport"
SOURCES = ("an", "senat", "dila", "wikidata", "wikipedia")
ETAPES_CALCUL = ("E3", "export", "E4", "E5", "E6")
TACHES = ("preparer", "collecter", "calculer", "ecrire", "alerter")
# Première génération de la série des sept nuits (commande, section 1) : celle de la première nuit
# sur le périmètre de validation complet en production. `None` tant qu'il ne l'est pas.
DEBUT_SERIE: int | None = None


# --- Récupération (GitHub) -------------------------------------------------------------------

def _api(chemin: str):
    return json.loads(distant._gh("api", chemin).stdout)


def recuperer(depot: str, cache: str) -> list[dict]:
    """Télécharge dans `cache/<exécution>/` le rapport de chaque nuit encore disponible, et les
    informations de son exécution (`execution.json`). Ce qui est déjà dans le cache n'est pas
    redemandé : le cache garde les nuits dont l'artefact a expiré depuis."""
    lignes = distant._gh("api", "--paginate", f"repos/{depot}/actions/artifacts?name={ARTEFACT}&per_page=100",
                         "--jq", '.artifacts[] | select(.expired | not) | .workflow_run.id').stdout.split()
    for run in sorted(set(lignes)):
        d = os.path.join(cache, run)
        if not os.path.exists(os.path.join(d, "rapport.json")):
            os.makedirs(d, exist_ok=True)
            distant._gh("run", "download", run, "-R", depot, "-n", ARTEFACT, "-D", d)
        if not os.path.exists(os.path.join(d, "execution.json")):
            ex = _api(f"repos/{depot}/actions/runs/{run}")
            jobs = _api(f"repos/{depot}/actions/runs/{run}/jobs?per_page=100")["jobs"]
            with open(os.path.join(d, "execution.json"), "w") as f:
                json.dump({"id": int(run), "evenement": ex.get("event"), "branche": ex.get("head_branch"),
                           "commit": (ex.get("head_sha") or "")[:7], "cree_le": ex.get("created_at"),
                           "taches": [{"nom": j["name"], "debut": j.get("started_at"), "fin": j.get("completed_at"),
                                       "conclusion": j.get("conclusion")} for j in jobs]}, f, indent=1)
    return charger(cache)


def charger(cache: str) -> list[dict]:
    """Les nuits du cache, dans l'ordre des générations."""
    nuits = []
    for run in os.listdir(cache):
        d = os.path.join(cache, run)
        try:
            with open(os.path.join(d, "rapport.json")) as f:
                rapport = json.load(f)
        except (OSError, ValueError):
            continue
        execution = {}
        if os.path.exists(os.path.join(d, "execution.json")):
            with open(os.path.join(d, "execution.json")) as f:
                execution = json.load(f)
        nuits.append({"rapport": rapport, "execution": execution})
    return sorted(nuits, key=lambda n: (n["rapport"].get("generation") or 0, n["rapport"].get("debut") or ""))


# --- Mesures d'une nuit ------------------------------------------------------------------------

def famille(point: str) -> str:
    """Famille d'un point d'accès : le point sans sa législature (`an-amendements-l17` →
    `an-amendements`) ; les acteurs (AMO20 de la XIVe, AMO30 ensuite) forment une famille."""
    f = re.sub(r"-l\d+$", "", point)
    return "an-acteurs" if re.fullmatch(r"an-amo\d+", f) else f


def _secondes(debut, fin):
    if not (debut and fin):
        return None
    lire = lambda s: datetime.fromisoformat(s.replace("Z", "+00:00"))
    return (lire(fin) - lire(debut)).total_seconds()


def _pic(mesures):
    pics = [(m.get("pic_memoire_mo"), m) for m in mesures if m.get("pic_memoire_mo") is not None]
    return max(pics, key=lambda x: x[0]) if pics else (None, None)


def mesurer(nuit: dict, points_deja_releves: set) -> dict:
    """Les mesures d'une nuit. `points_deja_releves` : les points relevés avec succès une nuit
    précédente ; un point relevé pour la première fois compte dans le premier remplissage, pas dans
    les objets nouveaux de la nuit. L'ensemble est complété par cette nuit."""
    r, ex = nuit["rapport"], nuit.get("execution") or {}
    c = r.get("calcul") or {}
    m = {"generation": r.get("generation"), "debut": r.get("debut"), "mode": r.get("mode"),
         "code": r.get("code"), "evenement": ex.get("evenement"), "branche": ex.get("branche"),
         "execution": ex.get("id")}

    # Durées des tâches (GitHub) et de toute la mise à jour.
    taches = {t["nom"]: _secondes(t.get("debut"), t.get("fin")) for t in ex.get("taches", [])
              if t.get("conclusion") not in ("skipped", None)}
    m["taches"] = taches
    debuts = [t["debut"] for t in ex.get("taches", []) if t.get("debut") and t.get("conclusion") != "skipped"]
    fins = [t["fin"] for t in ex.get("taches", []) if t.get("fin") and t.get("conclusion") != "skipped"]
    m["duree_totale"] = _secondes(min(debuts), max(fins)) if debuts and fins else None

    # Pics de mémoire : maximum des étapes, par tâche.
    pic, etape = _pic(r.get("mesures", []))
    m["pic_collecte"] = pic
    m["pic_collecte_etape"] = (etape or {}).get("point_acces") or (etape or {}).get("etape")
    pic, etape = _pic(c.get("mesures", []))
    m["pic_calcul"], m["pic_calcul_etape"] = pic, (etape or {}).get("etape")
    etapes = {}
    for e in ETAPES_CALCUL:
        ms = [x for x in c.get("mesures", []) if x.get("etape") == e]
        if ms:
            etapes[e] = {"duree_s": sum(x.get("duree_s") or 0 for x in ms), "pic": _pic(ms)[0]}
    m["etapes_calcul"] = etapes

    # Contrôles et publication.
    ctrl = c.get("controles") or {}
    m["publication_autorisee"] = ctrl.get("publication_autorisee")
    pub = c.get("publication") or {}
    fiches = pub.get("fiches") or []
    m["fiches"] = len(fiches) if pub else None
    m["faits_publies"] = pub.get("faits_publies")
    m["fichiers_servis"] = sum(1 + len(f.get("sections") or {}) for f in fiches) if pub else None

    # Octets reçus et durée de relevé par source ; objets nouveaux ou modifiés par famille ; premier
    # remplissage. Un point peut avoir plusieurs relevés dans une nuit (une livraison du JO chacun).
    # Durée d'un point : mesure E1-E2 (téléchargement, vérification, découpage) ; le `duree_s` d'un
    # relevé ne compte que le téléchargement.
    duree_point = defaultdict(float)
    for x in r.get("mesures", []):
        if x.get("etape") == "E1-E2" and x.get("point_acces"):
            duree_point[x["point_acces"]] += x.get("duree_s") or 0
    source_point = {}
    octets, duree_source = defaultdict(int), defaultdict(float)
    objets, retraits = defaultdict(int), defaultdict(int)
    premiers, pannes = {}, set()
    for rel in r.get("releves", []):
        pa = rel.get("point_acces")
        source_point[pa] = rel.get("source") or "?"
        octets[source_point[pa]] += rel.get("octets_recus") or 0
        reussi = rel.get("issue") in ("nouveau", "inchange") and rel.get("complet", True)
        if rel.get("issue") in ("echec", "suspect"):
            pannes.add(pa)
        if reussi and pa not in points_deja_releves:
            p = premiers.setdefault(pa, {"point": pa, "octets": 0, "duree_s": duree_point.get(pa),
                                         "membres": 0, "releves": 0})
            p["octets"] += rel.get("octets_recus") or 0
            p["membres"] += rel.get("nb_membres") or 0
            p["releves"] += 1
            continue
        objets[famille(pa)] += rel.get("nb_nouvelles_versions") or 0
        retraits[famille(pa)] += rel.get("nb_retraits") or 0
    for pa, d in duree_point.items():
        duree_source[source_point.get(pa, "?")] += d
    points_deja_releves.update(premiers)
    premiers = list(premiers.values())
    m["octets_par_source"], m["duree_par_source"] = dict(octets), dict(duree_source)
    m["duree_pannes"] = sum(duree_point.get(pa, 0) for pa in pannes)
    m["objets_par_famille"], m["retraits_par_famille"] = dict(objets), dict(retraits)
    m["premier_remplissage"], m["pannes"] = premiers, sorted(pannes)
    m["entrepot_octets"] = r.get("entrepot_octets")

    # Écritures dans les releases.
    envois = [e for e in ((r.get("ecriture") or {}).get("envois") or []) + (r.get("ecriture_export") or [])
              + (r.get("ecriture_site") or []) if not e.get("retire")]
    par_release = {}
    for e in envois:
        # Avant le 06/11/2026 au soir, tout allait dans `entrepot` (défaut corrigé, test_distant).
        p = par_release.setdefault(e.get("release") or "entrepot", {"envois": 0, "octets": 0, "duree_s": 0.0,
                                                               "duree_max_s": 0.0, "reessais": 0, "echecs": 0})
        p["envois"] += 1
        p["octets"] += e.get("octets") or 0
        p["duree_s"] += e.get("duree_s") or 0
        p["duree_max_s"] = max(p["duree_max_s"], e.get("duree_s") or 0)
        p["reessais"] += max(0, (e.get("essais") or 1) - 1)
        p["echecs"] += 0 if e.get("reussi", True) else 1
    m["ecritures"] = par_release

    # Poids téléchargé par fiche de candidat (octets compressés, comme les sert le site).
    poids = []
    for f in fiches:
        if f.get("type") != "candidat":
            continue
        initial = (f.get("entete") or {}).get("gz") or 0
        total = initial + sum((s or {}).get("gz") or 0 for s in (f.get("sections") or {}).values())
        poids.append({"fiche": f.get("fiche"), "initial": initial, "total": total})
    m["poids_candidats"] = poids
    return m


def mesurer_toutes(nuits: list[dict]) -> list[dict]:
    """Rend les mesures de chaque nuit (`mesurer`), dans l'ordre de `nuits` : les points déjà relevés
    s'accumulent d'une nuit à la suivante."""
    vus: set = set()
    return [mesurer(n, vus) for n in nuits]


# --- Rendu -------------------------------------------------------------------------------------

def _n(x):
    return "—" if x is None else f"{int(round(x)):,}".replace(",", " ")


def _mo(octets):
    if octets is None:
        return "—"
    return f"{octets / 1e6:,.1f}".replace(",", " ").replace(".", ",")


def _go_pic(mo):
    return "—" if mo is None else f"{mo / 1024:.1f}".replace(".", ",")


def _duree(s):
    if s is None:
        return "—"
    s = int(round(s))
    if s < 60:
        return f"{s} s"
    if s < 3600:
        return f"{s // 60} min {s % 60:02d} s"
    return f"{s // 3600} h {(s % 3600) // 60:02d} min"


def _nuit(m):
    return f"g{m['generation']}"


def _date(m):
    d = m.get("debut") or ""
    return f"{d[8:10]}/{d[5:7]} {d[11:16]}" if len(d) >= 16 else "—"


def _declenchement(m):
    return {"schedule": "nuit", "workflow_dispatch": "à la main"}.get(m.get("evenement"), m.get("evenement") or "—")


def _table(entetes, lignes):
    out = ["| " + " | ".join(entetes) + " |",
           "| " + " | ".join("---" if i == 0 else "---:" for i in range(len(entetes))) + " |"]
    out += ["| " + " | ".join(str(x) for x in l) + " |" for l in lignes]
    return "\n".join(out)


def rendre(mesures: list[dict], depot: str, genere_le: str | None = None) -> str:
    """Rend le rapport de mesures en markdown : un en-tête qui dit la méthode et la population, puis
    un tableau par mesure (durées et pics par mise à jour et par étape du calcul, octets et durées
    par source, objets nouveaux par famille, taille de l'entrepôt, écritures dans les releases,
    poids des fiches de candidat, premier remplissage, déploiement). `genere_le` vaut la date
    courante par défaut."""
    genere_le = genere_le or datetime.now(timezone.utc).strftime("%d/%m/%Y à %H h %M UTC")
    calc = [m for m in mesures if m.get("etapes_calcul")]
    serie = ("**Aucune de ces nuits ne compte encore dans la série des sept nuits** : le périmètre de "
             "validation n'est pas complet en production." if DEBUT_SERIE is None else
             f"**La série des sept nuits commence à g{DEBUT_SERIE}** ; les nuits d'avant ne comptent pas.")
    s = [f"""# Rapport de mesures (commande de réalisation, section 5)

Généré le {genere_le} par `empreinte rapport-mesures` à partir du rapport de chaque mise à jour qui
écrit (artefact `rapport` des exécutions de `{depot}`), et des durées de tâches publiées par GitHub
Actions. Toutes les mesures sont prises **sur GitHub Actions** (machine `ubuntu-latest` d'un dépôt
public), aucune sur une connexion domestique. Une case vide (« — ») est une mesure absente du rapport
de cette nuit, jamais un zéro.

**Population.** Chaque ligne est une génération de l'entrepôt (`gN`) : une mise à jour en mode
`quotidien` (« nuit » : déclenchement planifié ; « à la main » : lancée à la main). Les essais
(`mode=essai`) n'écrivent rien et ne sont pas comptés. Le périmètre a changé pendant la période
(journal des changements) : XVIIe seule jusqu'à g8, archives closes XIVe–XVIe à partir de g9,
gouvernements et fiches de législature XIVe–XVIIe à partir de g10 ; voir le journal pour la suite.
{serie}

**Pic de mémoire.** Maximum des pics des étapes d'une tâche (`VmHWM` du processus, remis à zéro au
début de chaque étape). Le `Maximum resident set size` de `time -v` du journal des tâches ne vaut
que pour la dernière étape et n'est pas repris ici.
"""]

    s.append("## Durée et pic de mémoire de chaque mise à jour\n\n"
             "Méthode : durées des tâches selon GitHub (du début à la fin de chaque tâche) ; mise à jour "
             "entière : du début de la première tâche à la fin de la dernière. Pics en Go (1 Go = 1 024 Mo).\n")
    s.append(_table(["Nuit", "Début (UTC)", "Déclenchement", "Code", "Collecte", "Calcul", "Écriture",
                     "Mise à jour entière", "Pic collecte", "Pic calcul (étape)", "Publication",
                     "Fiches", "Faits publiés"],
                    [[_nuit(m), _date(m), _declenchement(m), f"`{(m.get('code') or '')[:7]}`",
                      _duree(m["taches"].get("collecter")), _duree(m["taches"].get("calculer")),
                      _duree(m["taches"].get("ecrire")), _duree(m.get("duree_totale")),
                      _go_pic(m.get("pic_collecte")),
                      f"{_go_pic(m.get('pic_calcul'))} ({m['pic_calcul_etape']})" if m.get("pic_calcul") else "—",
                      {True: "autorisée", False: "**refusée**"}.get(m.get("publication_autorisee"), "—"),
                      _n(m.get("fiches")), _n(m.get("faits_publies"))] for m in mesures]))

    s.append("\n## Durée et pic de mémoire de chaque étape du calcul\n\n"
             "Méthode : mesures du traitement (`mesures.Mesures`) ; E3 additionne les lecteurs, son pic est "
             "le plus haut d'entre eux. E3 lecture, export de tous les faits lus, E4 règles, E5 fiches, "
             "E6 contrôles. Durée, puis pic en Go.\n")
    s.append(_table(["Nuit"] + [e for e in ETAPES_CALCUL],
                    [[_nuit(m)] + [f"{_duree(m['etapes_calcul'][e]['duree_s'])} · {_go_pic(m['etapes_calcul'][e]['pic'])}"
                                   if e in m["etapes_calcul"] else "—" for e in ETAPES_CALCUL] for m in calc]))

    s.append("\n## Octets téléchargés et durée de relevé par source\n\n"
             "Méthode : somme des octets reçus par les relevés de la nuit (`octets_recus`), en Mo "
             "(10⁶ octets) ; durée des relevés de la source (mesure E1-E2 de chaque point : téléchargement, "
             "vérification, découpage ; les points d'une source sont relevés l'un après l'autre). Une "
             "requête conditionnelle qui répond « inchangé » ne reçoit rien.\n")
    s.append(_table(["Nuit"] + list(SOURCES) + ["Total", "Points en panne"],
                    [[_nuit(m)] + [f"{_mo(m['octets_par_source'].get(x, 0))} · {_duree(m['duree_par_source'].get(x))}"
                                   for x in SOURCES]
                     + [_mo(sum(m["octets_par_source"].values())), ", ".join(f"`{p}`" for p in m["pannes"]) or "—"]
                     for m in mesures]))

    familles = sorted({f for m in mesures for f in m["objets_par_famille"]})
    s.append("\n## Objets nouveaux ou modifiés par nuit, par famille\n\n"
             "Méthode : nouvelles versions de fichiers de la source rangées dans l'entrepôt "
             "(`nb_nouvelles_versions` des relevés : un fichier nouveau ou dont les octets ont changé), "
             "par famille de points d'accès, toutes législatures confondues. Le premier relevé d'un point "
             "n'est pas compté ici (tableau du premier remplissage). Entre parenthèses : fichiers retirés "
             "à la source, quand il y en a.\n")
    s.append(_table(["Famille"] + [_nuit(m) for m in mesures],
                    [[f"`{f}`"] + [(_n(m["objets_par_famille"].get(f)) if f in m["objets_par_famille"] else "—")
                                   + (f" ({_n(m['retraits_par_famille'][f])})" if m["retraits_par_famille"].get(f) else "")
                                   for m in mesures] for f in familles]))

    s.append("\n## Taille de l'entrepôt et croissance par nuit\n\n"
             "Méthode : somme des octets des fichiers de l'entrepôt après l'écriture de la nuit "
             "(`entrepot_octets`, release `entrepot`, archives brutes comprises si elles y sont), en Mo.\n")
    lignes, avant = [], None
    for m in mesures:
        t = m.get("entrepot_octets")
        lignes.append([_nuit(m), _mo(t), "—" if (t is None or avant is None) else ("+" if t >= avant else "") + _mo(t - avant)])
        avant = t if t is not None else avant
    s.append(_table(["Nuit", "Entrepôt (Mo)", "Croissance (Mo)"], lignes))

    s.append("\n## Écritures dans les releases\n\n"
             "Méthode : chaque envoi d'un fichier par la tâche `ecrire` (`gh release upload`), avec sa "
             "durée, son nombre d'essais et sa réussite. Une nuit refusée n'écrit que l'entrepôt.\n")
    lignes = []
    for m in mesures:
        for rel, p in sorted(m["ecritures"].items()):
            lignes.append([_nuit(m), f"`{rel}`", _n(p["envois"]), _mo(p["octets"]), _duree(p["duree_s"]),
                           _duree(p["duree_max_s"]), _n(p["reessais"]), _n(p["echecs"])])
    s.append(_table(["Nuit", "Release", "Envois", "Mo", "Durée totale", "Plus long", "Réessais", "Échecs"], lignes))

    s.append("\n## Poids téléchargé par fiche de candidat\n\n"
             "Méthode : octets compressés (gzip) servis, comme les compte la page de contrôle : "
             "chargement initial = l'en-tête `fiche.json` ; toutes sections ouvertes = en-tête et toutes "
             "les sections. Population : les fiches de candidat composées cette nuit-là (publiées si la "
             "publication est autorisée). En Ko (10³ octets).\n")
    ko = lambda x: f"{x / 1e3:,.1f}".replace(",", " ").replace(".", ",")
    lignes = []
    for m in calc:
        p = m["poids_candidats"]
        if not p:
            continue
        ini, tot = [x["initial"] for x in p], [x["total"] for x in p]
        lignes.append([_nuit(m), _n(len(p)), ko(statistics.median(ini)), ko(max(ini)),
                       ko(statistics.median(tot)), ko(max(tot)), ko(sum(tot))])
    s.append(_table(["Nuit", "Fiches", "Initial, médiane", "Initial, max", "Ouvertes, médiane",
                     "Ouvertes, max", "Ouvertes, toutes fiches"], lignes))
    dern = next((m for m in reversed(calc) if m["poids_candidats"]), None)
    if dern:
        s.append(f"\nDétail de la dernière nuit ({_nuit(dern)}), du plus lourd au plus léger :\n")
        s.append(_table(["Fiche", "Initial (Ko)", "Toutes sections ouvertes (Ko)"],
                        [[f"`{x['fiche']}`", ko(x["initial"]), ko(x["total"])]
                         for x in sorted(dern["poids_candidats"], key=lambda x: -x["total"])]))

    s.append("\n## Premier remplissage\n\n"
             "Méthode : premier relevé réussi de chaque point d'accès dans la période (les nuits suivantes ne "
             "rapportent que ce qui change). Durée du relevé (téléchargement, vérification, découpage), "
             "octets reçus, fichiers découpés.\n")
    lignes = [[_nuit(m), f"`{p['point']}`" + (f" ({p['releves']} livraisons)" if p["releves"] > 1 else ""),
               _mo(p["octets"]), _duree(p["duree_s"]), _n(p["membres"])]
              for m in mesures for p in m["premier_remplissage"]]
    s.append(_table(["Nuit", "Point d'accès", "Mo reçus", "Durée", "Fichiers"], lignes))
    for m in mesures:
        if len(m["premier_remplissage"]) >= 5:
            p = m["premier_remplissage"]
            s.append(f"\n{_nuit(m)} : {len(p)} points relevés pour la première fois, {_mo(sum(x['octets'] for x in p))} Mo, "
                     f"{_duree(sum(x['duree_s'] or 0 for x in p))} de relevé ; relevés en échec "
                     f"{_duree(m['duree_pannes'])} ; collecte entière {_duree(m['taches'].get('collecter'))}.")

    s.append("\n## Déploiement Pages\n\nSans objet dans le dépôt d'essai : aucun déploiement (décision du "
             "06/11/2026, « tu peux faire un html minimal mais pas besoin de déployer »). Ce qui serait "
             "déployé est mesuré à la place : nombre de fichiers servis (un en-tête et une section par "
             "fichier) et taille de l'archive du site (release `publication`).\n")
    s.append(_table(["Nuit", "Fichiers servis", "Archive du site (Mo)"],
                    [[_nuit(m), _n(m.get("fichiers_servis")),
                      _mo((m["ecritures"].get("publication") or {}).get("octets"))] for m in calc]))
    return "\n".join(s) + "\n"
