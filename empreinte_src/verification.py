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

**Signataires d'amendement** (issue #63, 15/11/2026) : des amendements servis, signés par au moins un
député, sont tirés au sort de même ; leur page publique est relue et la liste des signataires
comparée à la nôtre (`amendement_auteur`, R-AMENDEMENT) : l'auteur (le premier nommé) et
l'ensemble des cosignataires. Deux formes de page (relevé du 15/11/2026) :
- XVe à XVIIe : `/dyn/<législature>/amendements/<uid>` redirige vers la page de l'amendement ; le
  bloc « Déposé par » nomme les signataires dans l'ordre, chacun avec un lien
  `/dyn/deputes/PA…` (auteur en premier) ;
- XIVe : l'adresse `/dyn/14/…` répond 404 ; la page de l'ancien site (`document_uri` de la
  source, `.pdf` → `.asp`) porte `<meta name="AUTEUR_ID">` et `<meta name="COSIGNATAIRES_ID">`
  (numéros sans le préfixe `PA`, séparés par `;`). Un amendement de commission y a pour auteur la
  commission : seuls ses cosignataires sont comparés. Un amendement retiré n'y est pas publié
  (404) : non vérifié.
Un amendement du gouvernement n'a pas de signataire député : il n'est pas tiré.

**Périodes de mandat de député** (issue #63, 23/11/2026) : `verifier_mandats`. Pas de page lue en
plus : la fiche Sycomore de chaque candidat (point `sycomore-fiches`, page publique de l'Assemblée,
base historique distincte de l'archive des acteurs) est déjà relue chaque nuit par la collecte, qui
en garde les faits (`sycomore__mandat_sycomore`). Toutes les périodes servies sont donc comparées,
sans tirage : chaque mandat de député en fonction servi dans une carrière (faits `periode_carriere`,
`institution = 'assemblee'`, depuis le 19/06/2002), début et fin, contre la ligne de Sycomore de la
même personne qui le recouvre ; et chaque mandat de Sycomore depuis le 19/06/2002 d'un candidat
publié doit avoir sa période servie. Sycomore ne publie pas les suspensions (entrée au
gouvernement) : elles ne sont pas comparées, mais leurs bornes sont la fin et la reprise de mandats
comparés. Les périodes d'avant 2002 viennent de Sycomore même : comptées, jamais comparées.
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


_META = lambda nom: re.compile(r'<meta name="' + nom + r'" content="([^"]*)"')


def lire_signataires(html: str) -> dict | None:
    """Signataires députés d'une page d'amendement : `{"auteur": PA… ou None, "cosignataires":
    [PA…]}` dans l'ordre de la page, sans doublon ; `None` si la page ne porte aucun des deux
    motifs connus. Sur l'ancien site (XIVe), l'amendement d'une commission porte pour auteur le
    numéro de la commission (`AUTEUR_ID` = 59051, `GROUPE_ID` vide, « M. Denaja, rapporteur pour
    avis… ») : l'auteur n'est pas donné par un identifiant, `auteur` vaut None."""
    auteur = _META("AUTEUR_ID").search(html)
    if auteur:                                          # ancien site (XIVe)
        cosig = _META("COSIGNATAIRES_ID").search(html)
        groupe = _META("GROUPE_ID").search(html)
        ids = [x.strip() for x in (cosig.group(1).split(";") if cosig else [])]
        cosignataires = list(dict.fromkeys("PA" + x for x in ids if x.isdigit()))
        commission = groupe is not None and not groupe.group(1).strip()
        a = auteur.group(1).strip()
        a = None if commission or not a.isdigit() else "PA" + a
        return {"auteur": a, "cosignataires": [c for c in cosignataires if c != a]}
    i = html.find("Déposé par")
    if i < 0:
        return None
    fin = html.find("amendement-section-body", i)
    ids = list(dict.fromkeys(re.findall(r'href="/dyn/deputes/(PA\d+)"', html[i: fin if fin > 0 else len(html)])))
    if not ids:
        return None
    return {"auteur": ids[0], "cosignataires": ids[1:]}


def adresse_amendement(uid: str, document_uri: str | None) -> str | None:
    """Page publique d'un amendement : `/dyn/<législature>/amendements/<uid>` à partir de la XVe ;
    l'ancien site pour la XIVe (`document_uri`, `.pdf` → `.asp`)."""
    m = re.search(r"R5L(\d+)", uid)
    if not m:
        return None
    if int(m.group(1)) >= 15:
        return f"https://www.assemblee-nationale.fr/dyn/{m.group(1)}/amendements/{uid}"
    if document_uri and document_uri.endswith(".pdf"):
        return "https://www.assemblee-nationale.fr" + document_uri[:-4] + ".asp"
    return None


def verifier_signataires(con, generation: int, recuperer, nb_amendements: int = 20) -> dict:
    """Signataires de `nb_amendements` amendements servis, tirés au sort, contre leur page publique
    (`recuperer(url) -> str | None`). Rend le bilan, les écarts et les faits non vérifiés."""
    servis = [r[0] for r in con.execute("""
        SELECT DISTINCT f.id_amendement FROM _ctl_fp f
        WHERE f.id_amendement IS NOT NULL
          AND EXISTS (SELECT 1 FROM amendement_auteur a WHERE a.amendement = f.id_amendement)""").fetchall()]
    servis.sort(key=lambda s: _rang(generation, "amendement", s))
    tires = servis[:nb_amendements]
    ecarts, non_verifies, verifies = [], [], 0
    for uid in tires:
        nos = con.execute("SELECT acteur, role FROM amendement_auteur WHERE amendement = ? ORDER BY rang",
                          [uid]).fetchall()
        doc = con.execute("SELECT any_value(document_uri) FROM amendement_canonique WHERE amendement = ?",
                          [uid]).fetchall()
        url = adresse_amendement(uid, doc[0][0] if doc else None)
        if url is None:
            non_verifies.append(f"{uid} signataires (adresse de la page inconnue)")
            continue
        try:
            html = recuperer(url)
        except Exception as e:                      # injoignable : non vérifié, jamais un écart
            html, err = None, type(e).__name__
        else:
            err = "page vide ou refusée"
        if not html:
            non_verifies.append(f"{uid} signataires ({err}) {url}")
            continue
        page = lire_signataires(html)
        if not page:
            non_verifies.append(f"{uid} signataires (motif absent de la page) {url}")
            continue
        auteur = next((a for a, r in nos if r == "auteur"), None)
        cosig = {a for a, r in nos if r != "auteur"}
        p_auteur, p_cosig = page["auteur"], set(page["cosignataires"])
        if p_auteur is None and not p_cosig:
            non_verifies.append(f"{uid} signataires (auteur nommé par sa commission, sans cosignataire) {url}")
            continue
        diff = []
        if p_auteur is not None and auteur != p_auteur:
            diff.append(f"auteur : nous {auteur}, page {p_auteur}")
        if cosig != p_cosig:
            manque, en_trop = sorted(p_cosig - cosig), sorted(cosig - p_cosig)
            diff.append("cosignataires : " + " ; ".join(
                x for x in (f"{len(manque)} sur la page seulement ({', '.join(manque[:5])})" if manque else "",
                            f"{len(en_trop)} chez nous seulement ({', '.join(en_trop[:5])})" if en_trop else "")
                if x))
        if diff:
            ecarts.append(f"{uid} " + " ; ".join(diff) + f" — {url}")
        else:
            verifies += 1
    return {"tires": len(tires), "faits": len(tires), "verifies": verifies, "ecarts": ecarts,
            "non_verifies": non_verifies}


def _rang(*cles) -> str:
    return hashlib.sha256("|".join(map(str, cles)).encode()).hexdigest()


def verifier(con, generation: int, recuperer, nb_scrutins: int = 20, legislature: int = 17) -> dict:
    """`recuperer(url) -> str | None` lit une page (None : injoignable). Rend le bilan et les écarts."""
    # Scrutins de l'Assemblée seulement : les votes du Parlement européen servis (`MTG-PL…`, `pt-…` :
    # 27 000 sur 47 000 en g14) n'ont pas de page à l'Assemblée ; tirés, ils étaient comptés « non
    # vérifiés » (10 des 20 tirés à l'essai du 15/11/2026).
    servis = [r[0] for r in con.execute("SELECT DISTINCT id_scrutin FROM _ctl_fp WHERE id_scrutin IN "
                                        "(SELECT uid FROM an_scrutins__scrutin)").fetchall()]
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


# Périodes de mandat de député contre Sycomore (issue #63). Avant cette date, la carrière lit
# Sycomore même (R-CARRIERE) : la comparaison n'aurait pas d'autre route.
DEBUT_ARCHIVE_ACTEURS = "2002-06-19"
FICHE_SYCOMORE = "https://www2.assemblee-nationale.fr/sycomore/fiche?num_dept="


def verifier_mandats(con, avec_identifiants: bool = True) -> dict:
    """Périodes de mandat de député servies (début, fin) contre les fiches Sycomore relevées la
    même nuit. Lit `_ctl_fp`, `_ctl_fiches`, `candidat` (`per`, `adresse`, `sycomore`,
    `element_wikidata`), `sycomore__mandat_sycomore` et, si `avec_identifiants`,
    `sycomore__identifiant_sycomore` (identifiant Sycomore de l'élément, comme R-CARRIERE).

    Rend `faits` (périodes servies comparables), `verifies`, `ecarts` (nommés : bornes différentes,
    période absente de Sycomore, mandat de Sycomore absent de la carrière servie),
    `non_verifies` (pas d'identifiant Sycomore, fiche non relevée) et les expliqués comptés :
    `suspensions_non_comparees`, `avant_2002_lues_dans_sycomore`."""
    syc_el = ("(SELECT min(i.identifiant) FROM sycomore__identifiant_sycomore i "
              "WHERE i.element = c.element_wikidata)") if avec_identifiants else "NULL"
    candidats = con.execute(f"""
        SELECT c.per, 'candidat/' || c.adresse, coalesce(c.sycomore, {syc_el})
        FROM candidat c JOIN _ctl_fiches f ON f.fiche = 'candidat/' || c.adresse
        ORDER BY 2""").fetchall()
    periodes = con.execute("""
        WITH p AS (SELECT f.fiche, f.id_mandat AS mandat,
                          json_extract_string(f.valeur, '$.institution') AS institution,
                          json_extract_string(f.valeur, '$.etat') AS etat,
                          json_extract_string(f.valeur, '$.legislature') AS legislature,
                          json_extract_string(f.valeur, '$.debut') AS debut,
                          json_extract_string(f.valeur, '$.fin') AS fin
                   FROM _ctl_fp f WHERE f.type_fait = 'periode_carriere')
        SELECT fiche, mandat, etat, institution, any_value(legislature), min(debut),
               CASE WHEN bool_or(fin IS NULL) THEN NULL ELSE max(fin) END
        FROM p WHERE institution IN ('assemblee', 'assemblee_avant_2002')
        GROUP BY fiche, mandat, etat, institution ORDER BY fiche, 6""").fetchall()
    syc = {}                                    # fiche relevée → ses mandats de député
    for ident, chambre, d, f, leg in con.execute("""
            SELECT DISTINCT identifiant, chambre, debut, fin, legislature FROM sycomore__mandat_sycomore
            ORDER BY 1, 3""").fetchall():
        lignes = syc.setdefault(ident, [])
        if chambre == "assemblee":
            lignes.append((d, f, leg))
    servies = {}
    suspensions = avant_2002 = 0
    for fiche, mandat, etat, inst, leg, d, f in periodes:
        if inst == "assemblee_avant_2002":
            avant_2002 += 1
        elif etat == "suspendu":
            suspensions += 1
        elif etat == "en_fonction" and d:
            servies.setdefault(fiche, []).append((mandat, leg, d, f))
    ecarts, non_verifies, verifies, faits = [], [], 0, 0
    fin_ = lambda x: x or "en cours"
    for per, fiche, ident in candidats:
        nos = servies.get(fiche, [])
        faits += len(nos)
        if not ident:
            non_verifies += [f"{fiche} {m} (pas d'identifiant Sycomore déclaré par Wikidata)" for m, *_ in nos]
            continue
        url = FICHE_SYCOMORE + ident
        if ident not in syc:
            non_verifies += [f"{fiche} {m} (fiche Sycomore {ident} non relevée)" for m, *_ in nos]
            continue
        restes = [s for s in syc[ident] if s[0] and s[0] >= DEBUT_ARCHIVE_ACTEURS]
        for mandat, leg, d, f in nos:
            recouvre = [s for s in restes if s[0] <= (f or "9999-12-31") and (s[1] or "9999-12-31") >= d]
            if not recouvre:
                ecarts.append(f"{fiche} {mandat} ({leg}e législature, du {d} au {fin_(f)}) : "
                              f"aucun mandat de Sycomore sur cette période — {url}")
                continue
            s = next((s for s in recouvre if s[0] == d), recouvre[0])
            restes.remove(s)
            diff = [x for x in (f"début : nous {d}, Sycomore {s[0]}" if s[0] != d else "",
                                f"fin : nous {fin_(f)}, Sycomore {fin_(s[1])}" if s[1] != f else "") if x]
            if diff:
                ecarts.append(f"{fiche} {mandat} ({leg}e législature) " + " ; ".join(diff) + f" — {url}")
            else:
                verifies += 1
        ecarts += [f"{fiche} : mandat de Sycomore du {d} au {fin_(f)} ({leg}), absent de la carrière "
                   f"servie — {url}" for d, f, leg in restes]
    return {"faits": faits, "verifies": verifies, "ecarts": ecarts, "non_verifies": non_verifies,
            "suspensions_non_comparees": suspensions, "avant_2002_lues_dans_sycomore": avant_2002}
