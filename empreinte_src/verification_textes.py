"""Avertissement A2 — stade atteint et dates des textes relus sur la page publique de leur dossier
(issue #63, troisième famille, 23/11/2026 ; voir `verification` pour les votes et les signataires).

Chaque nuit, des textes **servis** (faits `texte_legislature` des fiches de législature : un
dossier dans une législature) sont tirés au sort, comme les scrutins et les amendements (tirage
reproductible : il dépend de la génération). La page publique du dossier (`source_url` servie,
`/dyn/<législature>/dossiers/<chemin>`) est relue, et jusqu'à trois faits sont comparés :

| fait | servi | sur la page |
| --- | --- | --- |
| dépôt | `date_depot` | la date du premier acte de dépôt d'initiative (`DepotInitiative`) |
| étape | `etape`, `date_etape` dans la législature du fait | le plus haut palier des actes de cette législature datés au plus tard à la date de référence ; la date d'étape parmi les dates que la page affiche pour ce palier |
| loi (si servie) | `numero_loi`, `date_promulgation` | « Loi n°… du … » du bloc de promulgation |

La page (relevé du 23/11/2026) porte chaque acte comme `data-id="<uid> (<type> / <code>)"`,
suivi de la date de son en-tête (« Mardi 21 novembre 2023 ») quand la page en affiche une ; les
réunions de commission et les séances sont seulement nommées (« Acte(s) de réunion : <uid> -
<uid> »), sans date. La législature d'un acte est celle de son identifiant (`L16-…`), comme dans
R-ETAPE. Paliers, dans l'ordre de R-ETAPE (adoption définitive et séance réunies : la page ne
dit pas si une adoption est définitive) :

| palier | servi | actes de la page |
| --- | --- | --- |
| 1 | `depot` | dépôt d'initiative, de navette, d'accord international, de motion de censure |
| 2 | `examen_commission` | rapport déposé, décision hors séance (CMP), réunion nommée dans un bloc de commission |
| 3 | `seance`, `adopte` | bloc de discussion en séance daté, décision de séance, réunion nommée dans un bloc de séance |
| 4 | `promulgue` | promulgation |

La page est plus récente que l'archive relue : un acte daté après la date de référence de la
nuit n'est pas compté (un acte sans date propre prend celle de son bloc d'étape).

Seul l'inexpliqué est nommé (décision des 13 et 15/11/2026 pour A3). Sont **expliqués**, et
seulement comptés dans le bilan :
- `date_non_affichee` : l'étape est la même, mais la page ne date pas l'acte qui la prouve (une
  réunion n'a pas de date sur la page) et nomme au moins une réunion de ce palier ;
- `date_de_promulgation_du_jo` : la date servie est celle du JO (R-LOIS, `source_date_promulgation`)
  et la page donne celle de l'acte de l'Assemblée (`date_assemblee`), que A7 nomme déjà.
Une page illisible ou injoignable n'est pas un écart : ses faits sont comptés « non vérifiés »,
avec la raison ; de même une loi servie que la page ne nomme pas, quand la page ne montre pas de
promulgation (loi 2021-191, que l'Assemblée date mal, #128). A2 ne bloque jamais la publication.

Mesuré en local le 23/11/2026 sur les faits publiés de la g20 (date de référence 20/11/2026),
180 textes distincts (100 tirés parmi tous, 100 parmi ceux qui ont dépassé le dépôt) : 391 faits,
383 vérifiés (dépôt 180 sur 180, étape 173, loi 30), 6 expliqués (`date_non_affichee`), 1 non
vérifié (loi 2021-191), 1 écart (DLR5L14N35418 : l'archive de la XIVe range sous `L14-` un
rapport du Sénat du 17/01/2018, que la page range sous la XVe).
"""
from __future__ import annotations

import json
import re

from .verification import _rang

MOIS = {"janvier": 1, "février": 2, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6,
        "juillet": 7, "août": 8, "aout": 8, "septembre": 9, "octobre": 10, "novembre": 11,
        "décembre": 12, "decembre": 12}
_JOUR = r"(?:Lundi|Mardi|Mercredi|Jeudi|Vendredi|Samedi|Dimanche)"
_JETONS = re.compile(
    r'data-id="L(\d+)-([^"\s]+) \((\w+) / ([^)"]*)\)"'
    r'|<span>' + _JOUR + r' (\d{1,2})(?:er)? (\w+) (\d{4})</span>'
    r'|Acte\(s\) de réunion\s*:\s*([^<]+)'
    r'|Loi (?:organique |constitutionnelle )?n°\s*(\d{4}-\d+)\s+du\s+\w+\s+(\d{1,2})(?:er)?\s+(\w+)\s+(\d{4})')
DEPOTS = ("DepotInitiative", "DepotInitiativeNavette", "DepotAccordInternational", "DepotMotionCensure")
PALIER_SERVI = {"depot": 1, "examen_commission": 2, "seance": 3, "adopte": 3, "promulgue": 4}
NOM_PALIER = {1: "dépôt", 2: "examen en commission", 3: "séance", 4: "promulgation"}


def _date(j, mois, a) -> str | None:
    """Date `AAAA-MM-JJ` d'un jour, d'un mois en lettres et d'une année ; `None` si le mois est inconnu."""
    m = MOIS.get(mois.lower())
    return f"{int(a):04d}-{m:02d}-{int(j):02d}" if m else None


def palier_acte(type_acte: str, code: str) -> int | None:
    """Palier d'un acte de la page (voir l'en-tête), `None` s'il ne prouve aucune étape."""
    if type_acte == "Promulgation" or (type_acte == "Etape" and code == "PROM"):
        return 4
    if type_acte == "DecisionMotionCensure" or (type_acte == "Decision" and "DEBATS" in code) \
            or (type_acte == "Etape" and re.search(r"-DEBATS(-AN|-SN)?$", code)):
        return 3
    if type_acte == "DepotRapport" or type_acte == "Decision":
        return 2
    if type_acte in DEPOTS:
        return 1
    return None


def lire_dossier(html: str) -> dict | None:
    """Actes, réunions et lois d'une page de dossier : `{"actes": [{"uid", "leg", "type", "code",
    "date", "date_bloc", "palier"}], "reunions": [{"uid", "leg", "date_bloc", "palier"}], "lois": [(numero, date)]}` ;
    `None` si la page ne porte aucun acte. La date d'un acte est la première date d'en-tête qui le
    suit, avant l'acte suivant ; un acte nommé deux fois garde la première date lue. Un acte ou une
    réunion sans date propre porte aussi `date_bloc`, la date du dernier bloc d'étape daté qui le
    précède (pour savoir s'il est atteint à la date de référence, jamais pour comparer une date)."""
    actes, ordre, reunions, lois = {}, [], [], []
    courant, contexte, date_bloc = None, "", None
    for leg, reste, type_acte, code, j, mois, an, reu, num, lj, lmois, lan in _JETONS.findall(html):
        if type_acte:
            uid = f"L{leg}-{reste}"
            if uid not in actes:
                actes[uid] = {"uid": uid, "leg": int(leg), "type": type_acte, "code": code, "date": None,
                              "date_bloc": date_bloc, "palier": palier_acte(type_acte, code)}
                ordre.append(uid)
            courant = uid if actes[uid]["date"] is None else None
            if type_acte == "Etape" or "DEBATS" in code or "COM" in code:
                contexte = code
        elif j:
            if courant:
                actes[courant]["date"] = actes[courant]["date_bloc"] = _date(j, mois, an)
                if actes[courant]["type"] == "Etape":
                    date_bloc = actes[courant]["date"]
                courant = None
        elif reu:
            for u in re.findall(r"L(\d+)-([A-Z0-9-]+)", reu):
                if any(r["uid"] == f"L{u[0]}-{u[1]}" for r in reunions):
                    continue
                reunions.append({"uid": f"L{u[0]}-{u[1]}", "leg": int(u[0]), "date_bloc": date_bloc,
                                 "palier": 3 if "DEBATS" in contexte else 2})
        elif num:
            lois.append((num, _date(lj, lmois, lan)))
    if not actes:
        return None
    return {"actes": [actes[u] for u in ordre], "reunions": reunions, "lois": lois}


def comparer(servi: dict, legislature: int, page: dict, au: str, loi: dict | None = None) -> list[tuple]:
    """Compare un texte servi à sa page : une ligne `(fait, issue, texte)` par fait, `issue` valant
    `verifie`, `ecart`, `non_verifie` ou le nom d'une explication (voir l'en-tête). `loi` :
    `{"date_assemblee", "source_date_promulgation"}` de la loi servie, si connue."""
    out = []
    actes = page["actes"]
    # Dépôt : la date du premier dépôt d'initiative de la page.
    depots = sorted(a["date"] for a in actes if a["type"] == "DepotInitiative" and a["date"])
    if not servi.get("date_depot"):
        out.append(("depot", "non_verifie", "aucune date de dépôt servie"))
    elif not depots:
        out.append(("depot", "non_verifie", "aucun dépôt daté sur la page"))
    elif depots[0] != servi["date_depot"]:
        out.append(("depot", "ecart", f"dépôt : nous {servi['date_depot']}, page {depots[0]}"))
    else:
        out.append(("depot", "verifie", ""))
    # Étape dans la législature du fait.
    etape, date_etape = servi.get("etape"), servi.get("date_etape")
    p_servi = PALIER_SERVI.get(etape)
    dans_leg = [a for a in actes if a["leg"] == legislature and a["palier"]]
    reu = [r for r in page["reunions"] if r["leg"] == legislature]
    # Atteint à la date de référence : un acte sans date propre prend celle de son bloc.
    atteints = [a for a in dans_leg if (a["date_bloc"] or "") <= au]
    reu = [r for r in reu if (r["date_bloc"] or "") <= au]
    p_page = max([a["palier"] for a in atteints] + [r["palier"] for r in reu] + [0])
    if p_servi is None:
        out.append(("etape", "non_verifie", f"étape « {etape} » sans palier"))
    elif p_page == 0:
        out.append(("etape", "non_verifie", f"aucun acte de la législature {legislature} sur la page"))
    elif p_page < p_servi:
        out.append(("etape", "ecart", f"étape : nous « {etape} » ({date_etape}), page {NOM_PALIER[p_page]} "
                                      f"au plus (législature {legislature})"))
    elif p_page > p_servi:
        haut = sorted({a["uid"] + (f" du {a['date']}" if a["date"] else "")
                       for a in atteints if a["palier"] > p_servi}
                      | {r["uid"] for r in reu if r["palier"] > p_servi})
        out.append(("etape", "ecart", f"étape : nous « {etape} » ({date_etape}), page {NOM_PALIER[p_page]} "
                                      f"({', '.join(haut[:3])})"))
    else:
        dates = {a["date"] for a in dans_leg if a["palier"] == p_servi and a["date"]}
        if p_servi == 1:            # une navette est datée par le bloc de sa lecture
            dates |= {a["date"] for a in actes if a["leg"] == legislature and a["type"] == "Etape"
                      and a["date"] and re.fullmatch(r"(AN|SN)\w*|CMP", a["code"] or "")}
        if date_etape in dates:
            out.append(("etape", "verifie", ""))
        elif any(r["palier"] == p_servi for r in reu):
            out.append(("etape", "date_non_affichee", ""))
        else:
            out.append(("etape", "ecart", f"date d'étape « {etape} » : nous {date_etape}, page "
                                          f"{', '.join(sorted(dates)) or 'aucune date'}"))
    # Loi : numéro et date.
    if servi.get("numero_loi"):
        sur_page = dict(page["lois"])
        n, d = servi["numero_loi"], servi.get("date_promulgation")
        if not page["lois"]:
            # Page sans promulgation : rien à comparer ; avec une promulgation, la loi doit y être.
            promulguee = any(a["palier"] == 4 for a in actes)
            out.append(("loi", "ecart" if promulguee else "non_verifie",
                        f"loi {n} : aucune loi nommée sur la page"))
        elif n not in sur_page:
            out.append(("loi", "ecart", f"loi : nous {n}, page {', '.join(sorted(sur_page))}"))
        elif sur_page[n] != d:
            if loi and loi.get("source_date_promulgation") == "journal_officiel" \
                    and loi.get("date_assemblee") == sur_page[n]:
                out.append(("loi", "date_de_promulgation_du_jo", ""))
            else:
                out.append(("loi", "ecart", f"loi {n} : nous du {d}, page du {sur_page[n]}"))
        else:
            out.append(("loi", "verifie", ""))
    return out


def verifier_textes(con, generation: int, recuperer, au: str, nb_textes: int = 20) -> dict:
    """Stade et dates de `nb_textes` textes servis, tirés au sort, contre la page publique de leur
    dossier (`recuperer(url) -> str | None`). Rend le bilan, les écarts, les faits non vérifiés et
    les explications comptées."""
    servis = con.execute("""
        SELECT fiche, id_dossier, any_value(valeur), any_value(source_url) FROM _ctl_fp
        WHERE type_fait = 'texte_legislature' AND id_dossier IS NOT NULL GROUP BY 1, 2""").fetchall()
    servis.sort(key=lambda r: _rang(generation, "texte", r[0], r[1]))
    tires = servis[:nb_textes]
    lois = {}
    if {"loi"} <= {r[0] for r in con.execute("SELECT table_name FROM duckdb_tables() UNION ALL "
                                              "SELECT view_name FROM duckdb_views()").fetchall()}:
        cols = {r[0] for r in con.execute("DESCRIBE loi").fetchall()}
        if {"date_assemblee", "source_date_promulgation"} <= cols:
            lois = {n: {"date_assemblee": a, "source_date_promulgation": s} for n, a, s in con.execute(
                "SELECT numero_loi, any_value(date_assemblee), any_value(source_date_promulgation) "
                "FROM loi WHERE numero_loi IS NOT NULL GROUP BY 1").fetchall()}
    ecarts, non_verifies, expliques, verifies, faits = [], [], {}, 0, 0
    for fiche, dossier, valeur, url in tires:
        servi = json.loads(valeur)
        m = re.search(r"(\d+)$", fiche)
        leg = int(m.group(1)) if m else None
        url = url or servi.get("source_url")
        nb = 3 if servi.get("numero_loi") else 2
        faits += nb
        if not url or leg is None:
            non_verifies += [f"{dossier} ({fiche}) : adresse de la page inconnue"] * nb
            continue
        try:
            html = recuperer(url)
        except Exception as e:                      # injoignable : non vérifié, jamais un écart
            html, err = None, type(e).__name__
        else:
            err = "page vide ou refusée"
        if not html:
            non_verifies += [f"{dossier} ({fiche}) : {err} {url}"] * nb
            continue
        page = lire_dossier(html)
        if not page:
            non_verifies += [f"{dossier} ({fiche}) : aucun acte lisible sur la page {url}"] * nb
            continue
        for fait, issue, texte in comparer(servi, leg, page, au, lois.get(servi.get("numero_loi"))):
            if issue == "verifie":
                verifies += 1
            elif issue == "ecart":
                ecarts.append(f"{dossier} ({fiche}) {texte} — {url}")
            elif issue == "non_verifie":
                non_verifies.append(f"{dossier} ({fiche}) {fait} : {texte} {url}")
            else:
                expliques[issue] = expliques.get(issue, 0) + 1
    return {"tires": len(tires), "faits": faits, "verifies": verifies, "ecarts": ecarts,
            "non_verifies": non_verifies, "expliques": expliques}
