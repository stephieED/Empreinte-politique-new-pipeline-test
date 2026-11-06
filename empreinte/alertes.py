"""Alertes (étape E8) : une issue par sujet, mise à jour seulement quand son contenu change,
fermée quand le sujet disparaît (doc. 2, 2.10). Seule la tâche `alerter` appelle ce module,
avec le seul droit `issues: write` (correction P3)."""
from __future__ import annotations

import hashlib
import json
import subprocess

ETIQUETTE = "alerte"
PREFIXE = "[alerte] "


def sujets_du_rapport(rapport: dict) -> dict[str, str]:
    """Rend {clé de sujet: texte}. Une clé stable par sujet."""
    sujets = {}
    for r in rapport.get("releves", []):
        if r["issue"] in ("echec", "suspect"):
            cle = f"panne:{r['point_acces']}"
            depuis = r.get("panne_depuis") or r.get("debut")
            sujets[cle] = (f"Le point d'accès `{r['point_acces']}` n'a pas pu être relevé "
                           f"({r['issue']}) depuis le {depuis}.\n\nDernier message : "
                           f"`{(r.get('message') or '').splitlines()[0][:300] if r.get('message') else '—'}`\n\n"
                           f"Adresse : {r.get('url')}\n\nRien n'a été retiré : les données restent "
                           "celles du dernier relevé complet.")
    for a in rapport.get("anomalies", []):
        sujets[a["cle"]] = a["texte"]
    if rapport.get("echec_ecriture"):
        sujets["ecriture"] = f"L'écriture dans l'entrepôt a échoué : {rapport['echec_ecriture']}"
    return sujets


def _gh(*args):
    return subprocess.run(["gh", *args], capture_output=True, text=True, check=True).stdout


def synchroniser(depot: str, sujets: dict[str, str]) -> dict:
    subprocess.run(["gh", "label", "create", ETIQUETTE, "-R", depot, "--force", "--color", "B60205",
                    "--description", "Alerte du traitement nocturne"], capture_output=True, text=True)
    ouvertes = json.loads(_gh("issue", "list", "-R", depot, "--label", ETIQUETTE, "--state", "open",
                              "--limit", "200", "--json", "number,title,body"))
    par_cle = {i["title"][len(PREFIXE):]: i for i in ouvertes if i["title"].startswith(PREFIXE)}
    bilan = {"creees": [], "mises_a_jour": [], "fermees": [], "inchangees": []}
    for cle, texte in sorted(sujets.items()):
        marque = hashlib.sha256(texte.encode()).hexdigest()[:16]
        corps = f"{texte}\n\n<!-- empreinte-alerte:{marque} -->"
        i = par_cle.get(cle)
        if i is None:
            _gh("issue", "create", "-R", depot, "--title", PREFIXE + cle, "--body", corps,
                "--label", ETIQUETTE)
            bilan["creees"].append(cle)
        elif f"empreinte-alerte:{marque}" not in (i.get("body") or ""):
            _gh("issue", "edit", str(i["number"]), "-R", depot, "--body", corps)
            bilan["mises_a_jour"].append(cle)
        else:
            bilan["inchangees"].append(cle)
    for cle, i in par_cle.items():
        if cle not in sujets:
            _gh("issue", "close", str(i["number"]), "-R", depot, "--comment",
                "Sujet disparu à la dernière mise à jour.")
            bilan["fermees"].append(cle)
    return bilan
