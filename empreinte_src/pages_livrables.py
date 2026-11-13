"""Les documents de conception (`livrables/`) en HTML pour Pages (issue #95, décision de la
propriétaire du 13/11/2026).

Chaque fichier `.md` de `livrables/` devient une page HTML au même chemin dans le dossier de
sortie (`1-modele-de-donnees.md` → `1-modele-de-donnees.html`), convertie par `markdown2`
(extras `tables`, `fenced-code-blocks`, `header-ids`), avec le style de la page du traitement.
Une page `index.html` les liste avec leur titre (leur première ligne `# …`).

Liens relatifs : vers un `.md` publié, ils mènent à sa page `.html` (ancre gardée) ; vers un
dossier publié, à l'index ; vers ce qui n'est pas publié (scripts, fichiers de mesures), le lien
est retiré et son texte gardé, pour ne pas servir de lien mort. Rien n'est publié
d'`annexes/scripts/`.

Sans dossier `livrables/`, rien n'est écrit.

    python -m empreinte_src.pages_livrables livrables sortie-pages/livrables
"""
from __future__ import annotations

import argparse
import html
import os
import posixpath
import re

from .methodologie import STYLE

EXTRAS = ["tables", "fenced-code-blocks", "header-ids"]
EXCLUS = ("annexes/scripts",)


def documents(source: str) -> list[str]:
    """Les `.md` publiés, en chemins relatifs à `source` (séparateur `/`), triés."""
    out = []
    for racine, dossiers, noms in os.walk(source):
        rel = os.path.relpath(racine, source).replace(os.sep, "/")
        rel = "" if rel == "." else rel
        dossiers[:] = sorted(d for d in dossiers
                             if not any(f"{rel}/{d}".strip("/").startswith(x) for x in EXCLUS))
        out += [f"{rel}/{n}".strip("/") for n in noms if n.endswith(".md")]
    return sorted(out, key=lambda p: (p.count("/"), p))


def titre(texte: str, defaut: str) -> str:
    for l in texte.splitlines():
        if l.startswith("# "):
            return l[2:].strip()
    return defaut


def _relier(corps: str, chemin: str, publies: set[str]) -> str:
    """Réécrit les liens relatifs d'une page issue de `chemin` (voir la docstring du module)."""
    dossier = posixpath.dirname(chemin)
    profondeur = chemin.count("/")
    vers_index = "../" * profondeur + "index.html"
    dossiers_publies = {posixpath.dirname(p) for p in publies}
    dossiers_publies |= {"/".join(d.split("/")[:i]) for d in dossiers_publies
                         for i in range(1, d.count("/") + 1)}

    def lien(m):
        avant, cible, apres, texte = m.group(1) or " ", m.group(2), m.group(3), m.group(4)
        brut = html.unescape(cible)
        if re.match(r"^[a-z][a-z0-9+.-]*:", brut, re.I) or brut.startswith(("#", "/")):
            return m.group(0)
        chem, _, ancre = brut.partition("#")
        cible_rel = posixpath.normpath(posixpath.join(dossier, chem)) if chem else chemin
        if cible_rel in publies:
            nouveau = chem[:-3] + ".html" + (f"#{ancre}" if ancre else "")
        elif cible_rel in dossiers_publies or cible_rel == ".":
            nouveau = vers_index
        else:
            return texte
        return f'<a{avant}href="{html.escape(nouveau)}"{apres}>{texte}</a>'
    return re.sub(r'<a(\s[^>]*?)?href="([^"]*)"([^>]*)>(.*?)</a>', lien, corps, flags=re.S)


def _page(titre_page: str, corps: str, retour: str, accueil: str, origine: str) -> str:
    e = html.escape
    return ('<!doctype html>\n<html lang="fr">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            f"<title>{e(titre_page)}</title>\n<style>{STYLE}</style>\n</head>\n<body>\n"
            f'<p class="doux"><a href="{e(accueil)}">Empreinte politique — dépôt d\'essai</a>'
            + (f' · <a href="{e(retour)}">Documents de conception</a>' if retour else "")
            + "</p>\n" + corps
            + (f'\n<p class="meta">Converti de <code>{e(origine)}</code>.</p>' if origine else "")
            + "\n</body>\n</html>\n")


def convertir(source: str, sortie: str) -> list[str]:
    """Écrit les pages et l'index ; rend les chemins écrits (vide sans dossier source)."""
    if not os.path.isdir(source):
        return []
    import markdown2
    docs = documents(source)
    if not docs:
        return []
    publies = set(docs)
    ecrits, titres = [], {}
    for chemin in docs:
        with open(os.path.join(source, chemin), encoding="utf-8") as f:
            texte = f.read()
        titres[chemin] = titre(texte, posixpath.basename(chemin))
        corps = _relier(markdown2.markdown(texte, extras=EXTRAS), chemin, publies)
        # Un tableau large défile dans son cadre, pas la page (largeur mobile).
        corps = re.sub(r"<table\b", '<div class="defile"><table', corps).replace("</table>", "</table></div>")
        haut = "../" * chemin.count("/")
        cible = os.path.join(sortie, chemin[:-3] + ".html")
        os.makedirs(os.path.dirname(cible), exist_ok=True)
        with open(cible, "w", encoding="utf-8") as f:
            f.write(_page(titres[chemin], corps, haut + "index.html", haut + "../index.html",
                          f"livrables/{chemin}"))
        ecrits.append(cible)
    # Index : les documents de chaque dossier, la racine d'abord.
    e = html.escape
    corps = ["<h1>Documents de conception</h1>",
             '<p class="doux">Les documents du dossier <code>livrables/</code> du dépôt, convertis '
             "tels quels à chaque déploiement. La description du traitement tirée du code est "
             'dans <a href="../traitement/index.html">Le traitement, étape par étape</a>.</p>']
    par_dossier: dict[str, list[str]] = {}
    for c in docs:
        par_dossier.setdefault(posixpath.dirname(c), []).append(c)
    for d in sorted(par_dossier, key=lambda d: (d != "", d)):
        corps.append(f'<h2 id="{e(d or "racine")}"><code>livrables/{e(d + "/" if d else "")}</code></h2>')
        corps.append("<ul>" + "".join(
            f'<li><a href="{e(c[:-3])}.html">{e(titres[c])}</a> <span class="meta">'
            f"<code>{e(posixpath.basename(c))}</code></span></li>" for c in par_dossier[d]) + "</ul>")
    index = os.path.join(sortie, "index.html")
    with open(index, "w", encoding="utf-8") as f:
        f.write(_page("Documents de conception", "\n".join(corps), "", "../index.html", ""))
    return ecrits + [index]


def main(argv=None):
    ap = argparse.ArgumentParser(description="Convertit livrables/ en pages HTML (Pages).")
    ap.add_argument("source")
    ap.add_argument("sortie")
    a = ap.parse_args(argv)
    ecrits = convertir(a.source, a.sortie)
    print(f"{len(ecrits)} pages écrites dans {a.sortie}" if ecrits
          else f"Pas de dossier {a.source} : rien à publier.")


if __name__ == "__main__":
    main()
