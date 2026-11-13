"""Avertissement A2 — vérification croisée sur les pages publiques de l'Assemblée (doc. 2, 2.8.2 ;
cahier 3.1.9).

Chaque nuit, des scrutins **servis** sont tirés au sort (tirage reproductible : il dépend de la
génération) ; pour chacun, la page publique `/dyn/<législature>/scrutins/<numéro>` est relue et deux faits
sont comparés à nos données : les totaux du scrutin (votants, pour, contre, abstention) et la
position nominative d'un député tiré au sort. 20 scrutins font 40 faits (Q14).

La page est lue par trois motifs, dans l'ordre où ils apparaissent : le groupe
(`data-organe-id`), la position (`<span class="h6 …">Pour</span>`), le député
(`data-acteur-id="PA… - PM…"`) ; les totaux par « Nombre de votants : <b>41</b> »,
« Pour l'adoption : <b>26</b> », « Contre : <b>14</b> », « Abstention : <b>1</b> » (relevé le
06/11/2026 sur le scrutin 1000). Une page illisible ou injoignable n'est **pas** un écart : le
fait est compté « non vérifié », et l'avertissement le dit. A2 ne bloque jamais la publication.
"""
from __future__ import annotations

import hashlib
import re

URL_SCRUTIN = "https://www.assemblee-nationale.fr/dyn/{leg}/scrutins/{numero}"
_TOTAUX = {"nombre_votants": r"Nombre de votants\s*:\s*<b>(\d+)</b>",
           "pour": r"Pour l'adoption\s*:\s*<b>(\d+)</b>",
           "contre": r"Contre\s*:\s*<b>(\d+)</b>",
           "abstentions": r"Abstentions?\s*:\s*<b>(\d+)</b>"}
_JETONS = re.compile(r'data-organe-id="(PO\d+)"|<span class="h6[^"]*">\s*([^<]+?)\s*</span>|'
                     r'data-acteur-id="(PA\d+)')
POSITIONS = {"pour": "pour", "contre": "contre", "abstention": "abstention", "abstentions": "abstention",
             "non-votant": "non_votant", "non-votants": "non_votant", "non votant": "non_votant",
             "non votants": "non_votant"}


def lire_page(html: str) -> dict:
    """Totaux et positions nominatives d'une page de scrutin : {"totaux": {...}, "positions": {PA: pos}}."""
    totaux = {}
    for k, motif in _TOTAUX.items():
        m = re.search(motif, html)
        totaux[k] = int(m.group(1)) if m else None
    positions, pos = {}, None
    for organe, libelle, acteur in _JETONS.findall(html):
        if organe:
            pos = None
        elif libelle:
            pos = POSITIONS.get(libelle.strip().lower())      # autre intitulé : contexte inconnu
        elif acteur and pos:
            positions[acteur] = pos
    return {"totaux": totaux, "positions": positions}


def _rang(*cles) -> str:
    return hashlib.sha256("|".join(map(str, cles)).encode()).hexdigest()


def verifier(con, generation: int, recuperer, nb_scrutins: int = 20, legislature: int = 17) -> dict:
    """`recuperer(url) -> str | None` lit une page (None : injoignable). Rend le bilan et les écarts."""
    servis = [r[0] for r in con.execute("SELECT DISTINCT id_scrutin FROM _ctl_fp WHERE id_scrutin IS NOT NULL").fetchall()]
    servis.sort(key=lambda s: _rang(generation, s))
    tires = servis[:nb_scrutins]
    ecarts, non_verifies, verifies = [], [], 0
    for uid in tires:
        s = con.execute("""SELECT legislature, numero, nombre_votants, pour, contre, abstentions
                           FROM an_scrutins__scrutin WHERE uid = ? LIMIT 1""", [uid]).fetchall()
        if not s:
            non_verifies.append(f"{uid} : absent des faits lus")
            continue
        leg, numero, *nos = s[0]
        # La page du scrutin est celle de sa législature (XIVe à XVIIe), jamais celle de la XVIIe.
        url = URL_SCRUTIN.format(leg=leg or legislature, numero=numero)
        try:
            html = recuperer(url)
        except Exception as e:                      # injoignable : non vérifié, jamais un écart
            html, err = None, type(e).__name__
        else:
            err = "page vide ou refusée"
        if not html:
            non_verifies += [f"{uid} totaux ({err}) {url}", f"{uid} position ({err}) {url}"]
            continue
        page = lire_page(html)
        lus = [page["totaux"][k] for k in ("nombre_votants", "pour", "contre", "abstentions")]
        if None in lus:
            non_verifies.append(f"{uid} totaux (motif absent de la page) {url}")
        elif [int(x) if x is not None else None for x in nos] != lus:
            ecarts.append(f"{uid} totaux : nous {nos}, page {lus} — {url}")
        else:
            verifies += 1
        pv = con.execute("SELECT acteur, position FROM an_scrutins__position_vote WHERE scrutin = ?", [uid]).fetchall()
        if not pv:
            non_verifies.append(f"{uid} position (aucune position nominative lue) {url}")
            continue
        acteur, position = min(pv, key=lambda r: _rang(generation, uid, r[0]))
        sur_la_page = page["positions"].get(acteur)
        if sur_la_page is None:
            non_verifies.append(f"{uid} position de {acteur} (absent de la page lue) {url}")
        elif sur_la_page != position:
            ecarts.append(f"{uid} {acteur} : nous « {position} », page « {sur_la_page} » — {url}")
        else:
            verifies += 1
    return {"tires": len(tires), "faits": 2 * len(tires), "verifies": verifies, "ecarts": ecarts,
            "non_verifies": non_verifies}


def recuperateur(user_agent: str, delai_s: float = 20.0):
    """Rend une fonction `recuperer(url)` qui lit une page avec une session HTTP (en-tête
    `User-Agent` donné, délai d'attente de `delai_s` secondes)."""
    import requests
    session = requests.Session()
    session.headers["User-Agent"] = user_agent

    def recuperer(url):
        """Rend le texte de la page `url`, ou `None` si la réponse n'est pas un 200 ou est vide."""
        r = session.get(url, timeout=delai_s)
        return r.text if r.status_code == 200 and r.text else None
    return recuperer
