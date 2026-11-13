"""Toute la documentation de Pages au format pdoc (décision de la propriétaire du 13/11/2026 :
« peut-on avoir toute la doc sur ce format »).

pdoc documente des modules Python : pour que les documents de conception (`livrables/`) et la
description du traitement aient le même menu, la même recherche et le même sommaire latéral que
le code, ce module écrit, à chaque déploiement, un paquet Python `documentation` dont chaque module
porte un document dans sa docstring (dans un dossier temporaire), puis le fait documenter par
pdoc dans le même appel que `empreinte_src` (Markdown, diagrammes Mermaid, gabarits de
`pages/gabarits-pdoc`) :

    python -m empreinte_src.pages_doc livrables sortie-pages/doc [--commit SHA] [--depot URL]

Le paquet écrit :

| Module | Contenu |
| --- | --- |
| `documentation` | la page d'entrée : ce qu'il y a, avec les liens |
| `documentation.d0_lisezmoi` … | un module par `.md` de `livrables/`, repris tel quel |
| `documentation.traitement` | la description du traitement tirée du code (`methodologie`) |
| `documentation.etape_2`, `documentation.annexes.mesures` … | un paquet par dossier de `livrables/` |

Les documents sont découverts dans `livrables/` à chaque déploiement : un fichier ajouté a sa
page, sans liste à tenir. Le dossier `annexes/scripts/` n'est pas publié. Les documents de la
racine viennent dans l'ordre de leur numéro, puis le traitement, puis les dossiers (les annexes en
dernier).

Le texte des documents n'est pas modifié, à une exception : les liens relatifs. Un lien vers un
`.md` publié mène à sa page pdoc, et son ancre (écrite à la manière de GitHub, accents compris) à
l'ancre que pdoc donne au même titre ; un lien vers un dossier publié mène à la page de son
paquet ; un lien vers ce qui n'est pas publié (scripts, fichiers de mesures, code) garde son texte,
sans lien. Le reste du Markdown (tableaux, blocs de code, diagrammes Mermaid) est rendu par pdoc.

La recherche de pdoc indexe chaque docstring d'un bloc ; un long document y serait noyé. Les
documents du paquet sont donc indexés section par section (`sections`) : un mot mène à la section
qui le contient. Le code est indexé comme pdoc le fait.
"""
from __future__ import annotations

import argparse
import keyword
import os
import posixpath
import re
import sys
import unicodedata

PAQUET = "documentation"
RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXCLUS = ("annexes/scripts",)
TITRES_DOSSIERS = {"etape-2": "Étape 2", "annexes": "Annexes", "annexes/mesures": "Annexes : mesures"}
EN_TETE = "# Écrit par empreinte_src.pages_doc à chaque déploiement de Pages : ne pas modifier.\n"


# -- découverte et noms ------------------------------------------------------------------------

def _cle_naturelle(nom: str):
    return [int(x) if x.isdigit() else x.lower() for x in re.split(r"(\d+)", nom)]


def documents(source: str) -> list[str]:
    """Rend les `.md` publiés de `source`, en chemins relatifs (séparateur `/`), dans l'ordre du
    menu : ceux d'un dossier dans l'ordre de leur numéro, avant ses sous-dossiers ; les annexes
    après les autres dossiers ; rien de `EXCLUS`."""
    def parcourir(rel: str) -> list[str]:
        dossier = os.path.join(source, rel)
        noms = sorted(os.listdir(dossier), key=_cle_naturelle)
        out = [f"{rel}/{n}".strip("/") for n in noms
               if n.endswith(".md") and os.path.isfile(os.path.join(dossier, n))]
        sous = [n for n in noms if os.path.isdir(os.path.join(dossier, n))
                and not any(f"{rel}/{n}".strip("/").startswith(x) for x in EXCLUS)]
        for n in sorted(sous, key=lambda n: (n == "annexes", _cle_naturelle(n))):
            out += parcourir(f"{rel}/{n}".strip("/"))
        return out
    return parcourir("") if os.path.isdir(source) else []


def identifiant(nom: str) -> str:
    """Un nom de fichier ou de dossier en nom de module : minuscules sans accents, `_` pour le
    reste, préfixe `d` (document) s'il commence par un chiffre (`0-LISEZMOI` → `d0_lisezmoi`)."""
    t = unicodedata.normalize("NFKD", nom).encode("ascii", "ignore").decode().lower()
    t = re.sub(r"[^a-z0-9]+", "_", t).strip("_") or "x"
    if t[0].isdigit():
        t = "d" + t
    return t + "_" if keyword.iskeyword(t) else t


def module(chemin: str) -> str:
    """Rend le nom du module pdoc d'un document (`etape-2/0-cadrage.md` →
    `documentation.etape_2.d0_cadrage`) ou d'un dossier (`annexes/mesures` →
    `documentation.annexes.mesures`) de `livrables/`."""
    parties = [p for p in chemin.split("/") if p]
    if parties and parties[-1].endswith(".md"):
        parties[-1] = parties[-1][:-3]
    return ".".join([PAQUET] + [identifiant(p) for p in parties])


def page(nom_module: str) -> str:
    """Rend le chemin de la page pdoc d'un module, relatif au dossier de la documentation."""
    return nom_module.replace(".", "/") + ".html"


def lien(de: str, vers: str) -> str:
    """Rend l'adresse relative de la page du module `vers` vue depuis celle du module `de`."""
    return posixpath.relpath(page(vers), posixpath.dirname(page(de)) or ".")


def titre(texte: str, defaut: str) -> str:
    """Rend le texte de la première ligne `# …` d'un document Markdown, ou `defaut`."""
    for l in _hors_blocs(texte):
        if l.startswith("# "):
            return l[2:].strip()
    return defaut


# -- ancres --------------------------------------------------------------------------------------

def _hors_blocs(texte: str):
    """Les lignes de `texte` hors des blocs de code délimités (``` ou ~~~)."""
    clot = None
    for l in texte.splitlines():
        m = re.match(r"\s{0,3}(`{3,}|~{3,})", l)
        if m:
            if clot is None:
                clot = m.group(1)[0] * len(m.group(1))
                continue
            if l.strip().startswith(clot):
                clot = None
                continue
        if clot is None:
            yield l


def titres(texte: str) -> list[str]:
    """Rend le texte brut des titres d'un document Markdown (`# …` et soulignés `===`/`---`),
    dans l'ordre, hors des blocs de code."""
    out, precedente = [], ""
    for l in _hors_blocs(texte):
        m = re.match(r"\s{0,3}(#{1,6})\s+(.*?)\s*#*\s*$", l)
        if m:
            out.append(m.group(2))
        elif re.fullmatch(r"=+\s*|-+\s*", l) and precedente.strip() and not re.match(
                r"\s*([-*+]|\d+\.|\||>)\s", precedente):
            out.append(precedente.strip())
        precedente = l
    return out


def ancre(texte: str) -> str:
    """L'ancre que pdoc (markdown2, extra `header-ids`) donne à un titre : accents retirés, ce qui
    n'est ni lettre, ni chiffre, ni `_`, ni `-`, ni espace retiré, espaces et tirets regroupés en
    un `-`, en minuscules."""
    t = unicodedata.normalize("NFKD", texte)
    t = re.sub(r"[^\w\s-]", "", t).strip().lower()
    return re.sub(r"[-\s]+", "-", t)


def ancre_github(texte: str) -> str:
    """L'ancre que GitHub donne à un titre (celle qu'on écrit dans les liens entre livrables) :
    le texte affiché, en minuscules, sans ponctuation, accents gardés, chaque espace devenu `-`."""
    t = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", texte)
    t = re.sub(r"[`*]|(?<!\w)_|_(?!\w)", "", t).lower()
    t = re.sub(r"[^\w\- ]", "", t)
    return t.replace(" ", "-")


def ancres(texte: str) -> dict[str, str]:
    """Rend, pour un document, la correspondance des ancres : celle de GitHub (et celle de pdoc
    elle-même) → celle de pdoc, doublons numérotés à la manière de chacun (`-1`, `-2`… pour
    GitHub ; `-2`, `-3`… pour pdoc)."""
    vus_g: dict[str, int] = {}
    vus_p: dict[str, int] = {}
    out: dict[str, str] = {}
    for t in titres(texte):
        g, p = ancre_github(t), ancre(t)
        n_g, n_p = vus_g.get(g, 0), vus_p.get(p, 0) + 1
        vus_g[g], vus_p[p] = n_g + 1, n_p
        g = f"{g}-{n_g}" if n_g else g
        p = f"{p}-{n_p}" if n_p > 1 or not p else p
        out.setdefault(p, p)
        out.setdefault(g, p)
    return out


# -- liens -----------------------------------------------------------------------------------

_LIEN = re.compile(r"(?<!!)\[((?:[^\[\]]|\[[^\]]*\])*)\]\(\s*<?([^)\s>]*)>?(\s+\"[^\"]*\")?\s*\)")
_CODE = re.compile(r"(`+)(?:.+?)(?<!`)\1(?!`)", re.S)


def _hors_code(ligne: str, f) -> str:
    """Applique `f` aux morceaux de `ligne` hors des `code`."""
    out, i = [], 0
    for m in _CODE.finditer(ligne):
        out += [f(ligne[i:m.start()]), m.group(0)]
        i = m.end()
    return "".join(out + [f(ligne[i:])])


def relier(texte: str, chemin: str, publies: dict[str, dict[str, str]]) -> tuple[str, list[str]]:
    """Réécrit les liens relatifs du document `chemin` (voir la docstring du module) ; `publies`
    donne, pour chaque document publié, ses ancres (`ancres`). Rend le texte et la liste des liens
    retirés ou dont l'ancre est inconnue (pour le journal)."""
    de = module(chemin)
    dossier = posixpath.dirname(chemin)
    dossiers = {"/".join(p.split("/")[:i]) for p in publies for i in range(1, p.count("/") + 1)}
    remarques: list[str] = []

    def remplacer(m: re.Match) -> str:
        texte_lien, cible, titre_lien = m.group(1), m.group(2), m.group(3) or ""
        if not cible or re.match(r"^[a-z][a-z0-9+.-]*:", cible, re.I) or cible.startswith("/"):
            return m.group(0)
        chem, _, a = cible.partition("#")
        rel = posixpath.normpath(posixpath.join(dossier, chem)) if chem else chemin
        if rel in publies:
            adresse = lien(de, module(rel)) if rel != chemin else ""
            if a:
                nouvelle = publies[rel].get(a)
                if nouvelle is None:
                    remarques.append(f"{chemin} : ancre inconnue « {cible} »")
                    nouvelle = a
                adresse += "#" + nouvelle
            return f"[{texte_lien}]({adresse or '#'}{titre_lien})"
        if rel.rstrip("/") in dossiers or rel == ".":
            vers = module(rel) if rel != "." else PAQUET
            return f"[{texte_lien}]({lien(de, vers)}{titre_lien})"
        remarques.append(f"{chemin} : lien retiré (non publié) « {cible} »")
        return texte_lien

    lignes, clot = [], None
    for l in texte.split("\n"):
        m = re.match(r"\s{0,3}(`{3,}|~{3,})", l)
        if m and clot is None:
            clot = m.group(1)[0] * len(m.group(1))
        elif m and l.strip().startswith(clot):
            clot = None
        elif clot is None:
            l = _hors_code(l, lambda s: _LIEN.sub(remplacer, s))
        lignes.append(l)
    return "\n".join(lignes), remarques


# -- le paquet ---------------------------------------------------------------------------------

def _ecrire_module(racine: str, nom: str, doc: str, paquet: bool = False,
                   sous: list[str] | None = None) -> str:
    """Écrit le module `nom` (sa docstring : `doc`) sous `racine` ; un paquet a un `__init__.py`
    et, dans `__all__`, l'ordre de ses sous-modules dans le menu."""
    parties = nom.split(".")
    if paquet:
        chemin = os.path.join(racine, *parties, "__init__.py")
    else:
        chemin = os.path.join(racine, *parties[:-1], parties[-1] + ".py")
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    corps = EN_TETE + repr(doc) + "\n"
    if sous is not None:
        corps += f"__all__ = {sous!r}\n"
    with open(chemin, "w", encoding="utf-8") as f:
        f.write(corps)
    return chemin


def _liste(de: str, entrees: list[tuple[str, str, str]]) -> str:
    return "\n".join(f"- [{t}]({lien(de, m)}) — `livrables/{c}`" if c else f"- [{t}]({lien(de, m)})"
                     for m, t, c in entrees)


def ecrire(source: str, sortie: str, commit: str | None = None, depot: str | None = None
           ) -> tuple[list[str], list[str]]:
    """Écrit le paquet `documentation` dans le dossier `sortie` (créé au besoin) : un module par
    document de `source` (`livrables/`), un paquet par dossier, le module `traitement` et la page
    d'entrée. Rend les noms des modules écrits et les remarques sur les liens (`relier`). Sans
    dossier `source`, seuls la page d'entrée et le traitement sont écrits."""
    from . import methodologie
    docs = documents(source)
    textes = {}
    for c in docs:
        with open(os.path.join(source, c), encoding="utf-8") as f:
            textes[c] = f.read()
    publies = {c: ancres(t) for c, t in textes.items()}
    noms = [module(c) for c in docs] + [f"{PAQUET}.traitement"]
    if len(set(noms)) != len(noms):
        raise ValueError(f"deux documents de {source} auraient le même nom de module : {noms}")

    ecrits, remarques = [], []
    titres_docs = {c: titre(textes[c], posixpath.basename(c)) for c in docs}
    for c in docs:
        corps, r = relier(textes[c], c, publies)
        remarques += r
        corps = corps.rstrip() + f"\n\n---\n\n*Repris tel quel de `livrables/{c}`.*\n"
        _ecrire_module(sortie, module(c), corps)
        ecrits.append(module(c))

    traitement = f"{PAQUET}.traitement"
    _ecrire_module(sortie, traitement, methodologie.rendre(
        methodologie.donnees(), commit=commit, depot=depot, de=traitement))
    ecrits.append(traitement)

    # Les dossiers : un paquet chacun, qui liste ses documents et ses sous-dossiers.
    dossiers = sorted({"/".join(c.split("/")[:i]) for c in docs for i in range(1, c.count("/") + 1)},
                      key=lambda d: (-d.count("/"), d))
    def enfants(d: str) -> tuple[list[str], list[str]]:
        fichiers = [c for c in docs if posixpath.dirname(c) == d]
        sous_d = [x for x in dossiers if posixpath.dirname(x) == d]
        sous_d.sort(key=lambda x: (posixpath.basename(x) == "annexes", _cle_naturelle(x)))
        return fichiers, sous_d

    def titre_dossier(d: str) -> str:
        return TITRES_DOSSIERS.get(d, posixpath.basename(d).replace("-", " ").capitalize())

    for d in dossiers:
        fichiers, sous_d = enfants(d)
        nom = module(d)
        doc = (f"# {titre_dossier(d)}\n\nLes documents du dossier `livrables/{d}/` du dépôt, "
               "repris tels quels.\n\n"
               + _liste(nom, [(module(c), titres_docs[c], c) for c in fichiers]
                        + [(module(x), titre_dossier(x), "") for x in sous_d]) + "\n")
        _ecrire_module(sortie, nom, doc, paquet=True,
                       sous=[module(x).rsplit(".", 1)[1] for x in fichiers + sous_d])
        ecrits.append(nom)

    fichiers, sous_d = enfants("")
    origine = f" (commit `{commit[:12]}`)" if commit else ""
    accueil = [
        "# Documentation du projet", "",
        "Empreinte politique, dépôt d'essai de l'étape 2 : le traitement de collecte. Toute la "
        "documentation est ici, avec le même menu et la même recherche : les documents de "
        "conception (le dossier `livrables/` du dépôt, repris tels quels), la description du "
        f"traitement tirée du code{origine} et la documentation du code lui-même. La recherche, en "
        "haut du menu, porte sur l'ensemble.", "",
        "## Les documents de conception", "",
        _liste(PAQUET, [(module(c), titres_docs[c], c) for c in fichiers])
        or "*Aucun document : le dossier `livrables/` est absent.*", "",
        "## Le traitement, étape par étape", "",
        f"[Le traitement, étape par étape]({lien(PAQUET, traitement)}) : les étapes, le "
        "périmètre, les sources et leurs lecteurs, les règles de liaison et les contrôles, écrits "
        "à partir du code à chaque déploiement.", "",
    ]
    for x in sous_d:
        f_x, s_x = enfants(x)
        accueil += [f"## {titre_dossier(x)}", "",
                    _liste(PAQUET, [(module(c), titres_docs[c], c) for c in f_x]
                           + [(module(y), titre_dossier(y), "") for y in s_x]), ""]
    accueil += [
        "## Le code", "",
        "[`empreinte_src`](empreinte_src.html) : la documentation du code, tirée des docstrings.",
        "",
        "## La page minimale de contrôle", "",
        "[La page minimale de contrôle](../site/index.html) : les fiches et les fichiers servis de "
        "la dernière publication. Ce n'est pas le site : l'interface reste hors périmètre.", "",
    ]
    sous = ([module(c).rsplit(".", 1)[1] for c in fichiers] + ["traitement"]
            + [module(x).rsplit(".", 1)[1] for x in sous_d])
    _ecrire_module(sortie, PAQUET, "\n".join(accueil), paquet=True, sous=sous)
    ecrits.append(PAQUET)
    return ecrits, remarques


# -- pdoc ---------------------------------------------------------------------------------------

GABARITS = os.path.join(RACINE, "pages", "gabarits-pdoc")


def sections(item: dict, titre_doc: str) -> list[dict]:
    """Découpe l'entrée de recherche d'un document (son HTML entier) en une entrée par section
    (titres de niveau 2 et 3) : la recherche mène à la section, et un mot d'un long document n'est
    pas noyé dans sa longueur. L'entrée du document, intitulée par son titre, garde ce qui précède
    la première section."""
    morceaux = re.split(r'(<h[23] id="[^"]+">.*?</h[23]>)', item.get("doc", ""), flags=re.S)
    out = [dict(item, fullname=titre_doc, doc=morceaux[0])]
    for i in range(1, len(morceaux) - 1, 2):
        m = re.match(r'<h[23] id="([^"]+)">(.*?)</h[23]>', morceaux[i], re.S)
        intitule = " ".join(re.sub(r"<[^>]+>", "", m.group(2)).split())
        out.append({"fullname": f"{titre_doc} › {intitule}", "modulename": item["modulename"],
                    "qualname": m.group(1), "kind": "section", "doc": morceaux[i + 1]})
    return out


def _index_par_section(make_index):
    """Enveloppe `pdoc.search.make_index` : les documents du paquet `documentation` sont indexés
    section par section (`sections`) ; le code ne change pas."""
    def index(all_modules, is_public, docformat):
        out = []
        for item in make_index(all_modules, is_public, docformat):
            m = all_modules.get(item.get("modulename", ""))
            if (item.get("kind") == "module" and m is not None
                    and (m.modulename == PAQUET or m.modulename.startswith(PAQUET + "."))):
                out += sections(item, titre(m.docstring, m.modulename))
            else:
                out.append(item)
        return out
    return index


def construire(source: str, sortie: str, commit: str | None = None, depot: str | None = None
               ) -> list[str]:
    """Écrit toute la documentation dans `sortie` : le paquet `documentation` (`ecrire`, dans un
    dossier temporaire) et `empreinte_src`, documentés par pdoc dans le même appel (Markdown,
    Mermaid, gabarits de `pages/gabarits-pdoc`, recherche par section). Rend les remarques sur
    les liens."""
    import tempfile
    from pathlib import Path

    import pdoc
    import pdoc.render

    with tempfile.TemporaryDirectory() as tmp:
        _, remarques = ecrire(source, tmp, commit, depot)
        # Un paquet `documentation` déjà importé (un appel précédent) ne doit pas resservir.
        for nom in [n for n in sys.modules if n == PAQUET or n.startswith(PAQUET + ".")]:
            del sys.modules[nom]
        pdoc.render.configure(docformat="markdown", mermaid=True,
                              template_directory=Path(GABARITS))
        origine = pdoc.render.make_index
        pdoc.render.make_index = _index_par_section(origine)
        try:
            pdoc.pdoc(Path(RACINE, "empreinte_src"), Path(tmp, PAQUET), output_directory=Path(sortie))
        finally:
            pdoc.render.make_index = origine
    return remarques


def main(argv=None):
    """Point d'entrée : écrit toute la documentation (`construire`) et affiche les remarques sur
    les liens."""
    ap = argparse.ArgumentParser(description="Écrit la documentation de Pages (pdoc).")
    ap.add_argument("source", help="le dossier livrables/")
    ap.add_argument("sortie", help="le dossier de la documentation")
    ap.add_argument("--commit")
    ap.add_argument("--depot", help="adresse du dépôt, pour le lien vers le commit")
    a = ap.parse_args(argv)
    for r in construire(a.source, a.sortie, a.commit, a.depot):
        print(r)
    print(f"Documentation écrite dans {a.sortie}")


if __name__ == "__main__":
    main()
