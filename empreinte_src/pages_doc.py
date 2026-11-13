"""Toute la documentation de Pages au format pdoc (décision de la propriétaire du 13/11/2026 :
« peut-on avoir toute la doc sur ce format »), rangée par usage (décision du 13/11/2026).

pdoc documente des modules Python : pour que les documents de conception (`livrables/`) et la
description du traitement aient le même menu, la même recherche et le même sommaire latéral que
le code, ce module écrit, à chaque déploiement, un paquet Python `documentation` dont chaque module
porte un document dans sa docstring (dans un dossier temporaire), puis le fait documenter par
pdoc dans le même appel que `empreinte_src` (Markdown, diagrammes Mermaid, gabarits de
`pages/gabarits-pdoc`) :

    python -m empreinte_src.pages_doc livrables sortie-pages/doc [--commit SHA] [--depot URL]

Le paquet ne suit pas les dossiers de `livrables/` (les fichiers n'y bougent pas) : il range les
documents par usage, une rubrique par paquet, dans l'ordre du menu.

| Module | Contenu |
| --- | --- |
| `documentation` | la page d'entrée : les rubriques et leurs documents, avec les liens |
| `documentation.comprendre` | la présentation (`0-LISEZMOI.md`) et le traitement, étape par étape (`methodologie`) |
| `documentation.conception` | les documents 1, 2, 3 et 8 |
| `documentation.decisions` | le cadrage, les questions ouvertes, les corrections P1 à P3 |
| `documentation.mise_en_oeuvre` | le journal des changements, le rapport de mesures, la migration |
| `documentation.annexes.mesures` | l'analyse préliminaire des sources (`annexes/mesures/`) |
| `documentation.annexes.archives` | les documents remplacés (4, 6 et 7) |

Une seule table, `DOCUMENTS`, dit la rubrique de chaque fichier (et son titre dans le menu quand
un titre plus court est plus clair) ; `module` en tire le nom du module, et les liens entre
documents suivent. Un fichier absent de la table est rangé par défaut (`PAR_DEFAUT`), sans liste
à tenir : un nouveau fichier de `etape-2/` va dans la mise en œuvre, de `annexes/` dans les annexes, de la
racine dans la conception, après les documents listés, dans l'ordre naturel de leur nom. Le
dossier `annexes/scripts/` n'est pas publié. Le menu et la page d'entrée citent aussi la
documentation du code (`empreinte_src`), qui n'est pas dans le paquet.

Le texte des documents n'est pas modifié, à une exception : les liens relatifs. Un lien vers un
`.md` publié mène à sa page pdoc, et son ancre (écrite à la manière de GitHub, accents compris) à
l'ancre que pdoc donne au même titre ; un lien vers un dossier publié mène à la page de sa
rubrique ; un lien vers ce qui n'est pas publié (scripts, fichiers de mesures, code) garde son
texte, sans lien. Le reste du Markdown (tableaux, blocs de code, diagrammes Mermaid) est rendu par
pdoc.

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
EN_TETE = "# Écrit par empreinte_src.pages_doc à chaque déploiement de Pages : ne pas modifier.\n"
TRAITEMENT = "(traitement)"  # la page du traitement (`methodologie`) dans `DOCUMENTS` : pas un fichier

# Les rubriques, dans l'ordre du menu : (paquet sous `documentation`, titre, introduction). Une
# sous-rubrique (`annexes.mesures`) vient dans sa rubrique, après les documents listés de celle-ci.
# Les liens de l'introduction sont écrits comme dans `livrables/` (depuis sa racine).
RUBRIQUES = (
    ("comprendre", "Comprendre",
     "Pour commencer : ce que propose le projet, et ce que fait le traitement, étape par étape."),
    ("conception", "Conception",
     "La conception du modèle de données et du processus de collecte et de publication, les "
     "raisons de chaque choix et la recette, critère par critère."),
    ("decisions", "Décisions",
     "Ce que la propriétaire a fixé, les questions encore ouvertes et les corrections P1 à P3."),
    ("mise_en_oeuvre", "Mise en œuvre",
     "Les documents de la réalisation du traitement : ce qui a changé dans les documents de "
     "conception, ce que le traitement a mesuré chaque nuit, et ce qu'il restera à faire pour "
     "passer au vrai dépôt."),
    ("annexes", "Annexes et archives",
     "L'analyse préliminaire des sources, sur laquelle reposent les choix, et les documents "
     "remplacés, gardés pour mémoire."),
    ("annexes.mesures", "Analyse préliminaire des sources (réalisée le 04/11/2026)",
     "L'analyse de chaque source faite avant la réalisation, le 04/11/2026, sur les archives "
     "relevées le 03/11/2026 : ce qu'elle contient, ses formats, ses délais, ses défauts et ses "
     "limites. Les choix du traitement s'y réfèrent. Certains chiffres ont été dépassés depuis : "
     "les mesures à jour sont dans le [rapport de mesures](etape-2/3-rapport-de-mesures.md)."),
    ("annexes.archives", "Archives : documents remplacés",
     "Des documents remplacés, gardés pour mémoire : les estimations chiffrées (document 4), "
     "remplacées par le [rapport de mesures](etape-2/3-rapport-de-mesures.md), et les documents 6 "
     "et 7, fusionnés dans le [document 2](2-processus-collecte-publication.md) et le "
     "[document 1](1-modele-de-donnees.md)."),
)
# La rubrique de chaque fichier de `livrables/`, dans l'ordre du menu : (fichier, rubrique, titre
# dans le menu ou None pour le titre du document, sa première ligne `# …`).
DOCUMENTS = (
    ("0-LISEZMOI.md", "comprendre", "Présentation"),
    (TRAITEMENT, "comprendre", "Le traitement, étape par étape"),
    ("1-modele-de-donnees.md", "conception", None),
    ("2-processus-collecte-publication.md", "conception", None),
    ("3-justifications.md", "conception", None),
    ("8-recette.md", "conception", None),
    ("etape-2/0-cadrage-et-decisions.md", "decisions", "Cadrage et décisions de la propriétaire"),
    ("5-questions-ouvertes.md", "decisions", None),
    ("etape-2/1-corrections-P1-P3.md", "decisions", "Corrections P1 à P3"),
    ("etape-2/journal-des-changements.md", "mise_en_oeuvre", "Journal des changements"),
    ("etape-2/3-rapport-de-mesures.md", "mise_en_oeuvre", "Rapport de mesures"),
    ("etape-2/migration-vers-le-vrai-depot.md", "mise_en_oeuvre", "Migration vers le vrai dépôt"),
    ("annexes/mesures/0-brief-commun.md", "annexes.mesures", None),
    ("annexes/mesures/an-acteurs.md", "annexes.mesures",
     "Assemblée nationale : acteurs, organes, mandats, agenda, questions"),
    ("annexes/mesures/an-amendements-cr.md", "annexes.mesures",
     "Assemblée nationale : amendements et comptes rendus de séance"),
    ("annexes/mesures/an-scrutins-dossiers.md", "annexes.mesures",
     "Assemblée nationale : scrutins et dossiers législatifs"),
    ("annexes/mesures/autres-sources.md", "annexes.mesures",
     "Sources hors Assemblée nationale, et limites de GitHub"),
    ("4-estimations.md", "annexes.archives", None),
    ("6-doc-processus.md", "annexes.archives", None),
    ("7-doc-modele.md", "annexes.archives", None),
)
# La rubrique d'un fichier absent de `DOCUMENTS` : celle du premier préfixe de son chemin.
PAR_DEFAUT = (("etape-2/", "mise_en_oeuvre"), ("annexes/mesures/", "annexes.mesures"),
              ("annexes/", "annexes"), ("", "conception"))
CODE_AVANT = "annexes"  # la documentation du code vient, dans la page d'entrée, avant cette rubrique


# -- rangement et noms ---------------------------------------------------------------------------

def _cle_naturelle(nom: str):
    return [int(x) if x.isdigit() else x.lower() for x in re.split(r"(\d+)", nom)]


def rubrique(chemin: str) -> str:
    """Rend la rubrique d'un fichier de `livrables/` (ou de `TRAITEMENT`) : celle de `DOCUMENTS`,
    sinon celle de `PAR_DEFAUT`. Pour un dossier (`etape-2/`), celle qu'y prend un fichier
    nouveau."""
    for c, r, _ in DOCUMENTS:
        if c == chemin:
            return r
    return next(r for p, r in PAR_DEFAUT if chemin.startswith(p))


def _cle_menu(chemin: str):
    """L'ordre du menu : la rubrique (dans l'ordre de `RUBRIQUES`), puis les documents listés dans l'ordre de `DOCUMENTS`, puis
    les autres dans l'ordre naturel de leur chemin."""
    rangs = {r: i for i, (r, _, _) in enumerate(RUBRIQUES)}
    listes = [c for c, _, _ in DOCUMENTS]
    rang = listes.index(chemin) if chemin in listes else len(listes)
    return rangs[rubrique(chemin)], rang, _cle_naturelle(chemin)


def documents(source: str) -> list[str]:
    """Rend les `.md` publiés de `source`, en chemins relatifs (séparateur `/`), rubrique par
    rubrique dans l'ordre de `RUBRIQUES` puis dans l'ordre du menu (`_cle_menu`) ; rien de
    `EXCLUS`."""
    out = []
    for dossier, sous, fichiers in os.walk(source):
        rel = posixpath.relpath(dossier.replace(os.sep, "/"), source.replace(os.sep, "/"))
        rel = "" if rel == "." else rel
        sous[:] = [n for n in sous if not any(f"{rel}/{n}".strip("/").startswith(x) for x in EXCLUS)]
        out += [f"{rel}/{n}".strip("/") for n in fichiers if n.endswith(".md")]
    return sorted(out, key=_cle_menu)


def identifiant(nom: str) -> str:
    """Un nom de fichier ou de dossier en nom de module : minuscules sans accents, `_` pour le
    reste, préfixe `d` (document) s'il commence par un chiffre (`0-LISEZMOI` → `d0_lisezmoi`)."""
    t = unicodedata.normalize("NFKD", nom).encode("ascii", "ignore").decode().lower()
    t = re.sub(r"[^a-z0-9]+", "_", t).strip("_") or "x"
    if t[0].isdigit():
        t = "d" + t
    return t + "_" if keyword.iskeyword(t) else t


def module(chemin: str) -> str:
    """Rend le nom du module pdoc d'un document de `livrables/`, rangé dans sa rubrique
    (`etape-2/1-corrections-P1-P3.md` → `documentation.decisions.d1_corrections_p1_p3`), de la
    page du traitement (`TRAITEMENT` → `documentation.comprendre.traitement`), ou d'un dossier :
    la rubrique où vont ses fichiers nouveaux (`annexes/mesures` → `documentation.annexes.mesures`,
    `etape-2` → `documentation.mise_en_oeuvre`, la racine → `documentation`)."""
    chemin = chemin.strip("/")
    if chemin in ("", "."):
        return PAQUET
    if chemin == TRAITEMENT:
        return f"{PAQUET}.{rubrique(chemin)}.traitement"
    if not chemin.endswith(".md"):
        return f"{PAQUET}.{rubrique(chemin + '/')}"
    return f"{PAQUET}.{rubrique(chemin)}.{identifiant(posixpath.basename(chemin)[:-3])}"


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


def relier(texte: str, chemin: str, publies: dict[str, dict[str, str]], de: str | None = None
           ) -> tuple[str, list[str]]:
    """Réécrit les liens relatifs du document `chemin` (voir la docstring du module) ; `publies`
    donne, pour chaque document publié, ses ancres (`ancres`). Les adresses sont relatives à la
    page du module `de` (par défaut, celui du document). Rend le texte et la liste des liens
    retirés ou dont l'ancre est inconnue (pour le journal)."""
    de = de or module(chemin)
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


def _lire(source: str) -> dict[str, str]:
    """Le texte de chaque document publié de `source`, dans l'ordre du menu."""
    textes = {}
    for c in documents(source):
        with open(os.path.join(source, c), encoding="utf-8") as f:
            textes[c] = f.read()
    return textes


def titres_menu(textes: dict[str, str]) -> dict[str, str]:
    """Rend le titre de chaque module du paquet dans le menu : celui de `DOCUMENTS` s'il y en a
    un, sinon la première ligne `# …` du document ; celui de `RUBRIQUES` pour une rubrique."""
    courts = {c: t for c, _, t in DOCUMENTS if t}
    out = {PAQUET: "Documentation", module(TRAITEMENT): courts[TRAITEMENT]}
    out.update({f"{PAQUET}.{r}": t for r, t, _ in RUBRIQUES})
    for c, t in textes.items():
        out[module(c)] = courts.get(c) or titre(t, posixpath.basename(c))
    return out


def ecrire(source: str, sortie: str, commit: str | None = None, depot: str | None = None
           ) -> tuple[list[str], list[str]]:
    """Écrit le paquet `documentation` dans le dossier `sortie` (créé au besoin) : un module par
    document de `source` (`livrables/`) et le module du traitement, chacun dans sa rubrique ; un
    paquet par rubrique non vide, qui présente et liste ses documents ; la page d'entrée. Rend les
    noms des modules écrits et les remarques sur les liens (`relier`). Sans dossier `source`,
    seuls la page d'entrée, la rubrique « Comprendre » et le traitement sont écrits."""
    from . import methodologie
    textes = _lire(source)
    publies = {c: ancres(t) for c, t in textes.items()}
    entrees = sorted([*textes, TRAITEMENT], key=_cle_menu)
    chemins = {module(c): c for c in entrees}
    rubriques = {f"{PAQUET}.{r}": (r, t, i) for r, t, i in RUBRIQUES}
    noms = [module(c) for c in entrees] + list(rubriques)
    if len(set(noms)) != len(noms):
        raise ValueError(f"deux documents de {source} auraient le même nom de module : {noms}")
    titres_m = titres_menu(textes)
    listes = {c for c, _, _ in DOCUMENTS}

    ecrits, remarques = [], []
    for c in textes:
        corps, r = relier(textes[c], c, publies)
        remarques += r
        corps = corps.rstrip() + f"\n\n---\n\n*Repris tel quel de `livrables/{c}`.*\n"
        _ecrire_module(sortie, module(c), corps)
        ecrits.append(module(c))
    traitement = module(TRAITEMENT)
    _ecrire_module(sortie, traitement, methodologie.rendre(
        methodologie.donnees(), commit=commit, depot=depot, de=traitement))
    ecrits.append(traitement)

    def contenu(r: str) -> list[str]:
        """Les modules d'une rubrique (`""` : le paquet) dans l'ordre du menu : ses documents
        listés, ses sous-rubriques non vides, puis ses documents rangés par défaut."""
        siens = [c for c in entrees if r and rubrique(c) == r]
        sous = [f"{PAQUET}.{x}" for x, _, _ in RUBRIQUES if x.rpartition(".")[0] == r]
        return ([module(c) for c in siens if c in listes]
                + [m for m in sous if contenu(rubriques[m][0])]
                + [module(c) for c in siens if c not in listes])

    def introduction(m: str, de: str) -> str:
        r, _, intro = rubriques[m]
        texte, rem = relier(intro, f"(introduction de la rubrique {r})", publies, de=de)
        remarques.extend(x for x in rem if x not in remarques)
        return texte

    def arbre(de: str, r: str, retrait: str = "") -> list[str]:
        lignes = []
        for m in contenu(r):
            lignes.append(f"{retrait}- [{titres_m[m]}]({lien(de, m)})")
            if m in rubriques:
                lignes += arbre(de, rubriques[m][0], retrait + "    ")
            elif chemins[m] == TRAITEMENT:
                lignes[-1] += " — tiré du code à chaque déploiement"
            else:
                lignes[-1] += f" — `livrables/{chemins[m]}`"
        return lignes

    for m, (r, t, _) in rubriques.items():
        if not contenu(r):
            continue
        doc = f"# {t}\n\n{introduction(m, m)}\n\n" + "\n".join(arbre(m, r)) + "\n"
        _ecrire_module(sortie, m, doc, paquet=True, sous=[x.rsplit(".", 1)[1] for x in contenu(r)])
        ecrits.append(m)

    origine = f" (commit `{commit[:12]}`)" if commit else ""
    code = ["## Le code", "",
            "[`empreinte_src`](empreinte_src.html) : la documentation du code, tirée des "
            "docstrings.", ""]
    accueil = [
        "# Documentation du projet", "",
        "Empreinte politique, dépôt d'essai du traitement de collecte. Toute la "
        "documentation est ici, rangée par usage, avec le même menu et la même recherche : les "
        "documents de conception (le dossier `livrables/` du dépôt, repris tels quels), la "
        f"description du traitement tirée du code{origine} et la documentation du code lui-même. "
        "La recherche, en haut du menu, porte sur l'ensemble.", "",
    ]
    if not textes:
        accueil += ["*Aucun document : le dossier `livrables/` est absent.*", ""]
    for m in contenu(""):
        if m == f"{PAQUET}.{CODE_AVANT}":
            accueil += code
            code = []
        accueil += [f"## {titres_m[m]}", "", introduction(m, PAQUET), "", *arbre(PAQUET, rubriques[m][0]), ""]
    accueil += code
    _ecrire_module(sortie, PAQUET, "\n".join(accueil), paquet=True,
                   sous=[x.rsplit(".", 1)[1] for x in contenu("")])
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


def _index_par_section(make_index, titres_m: dict[str, str]):
    """Enveloppe `pdoc.search.make_index` : les documents du paquet `documentation` sont indexés
    section par section (`sections`), sous leur titre dans le menu (`titres_m`) ; le code ne
    change pas."""
    def index(all_modules, is_public, docformat):
        out = []
        for item in make_index(all_modules, is_public, docformat):
            m = all_modules.get(item.get("modulename", ""))
            if (item.get("kind") == "module" and m is not None
                    and (m.modulename == PAQUET or m.modulename.startswith(PAQUET + "."))):
                out += sections(item, titres_m.get(m.modulename) or titre(m.docstring, m.modulename))
            else:
                out.append(item)
        return out
    return index


def construire(source: str, sortie: str, commit: str | None = None, depot: str | None = None
               ) -> list[str]:
    """Écrit toute la documentation dans `sortie` : le paquet `documentation` (`ecrire`, dans un
    dossier temporaire) et `empreinte_src`, documentés par pdoc dans le même appel (Markdown,
    Mermaid, gabarits de `pages/gabarits-pdoc`, recherche par section). Les gabarits reçoivent
    les titres du menu (`titres_menu`), le module du traitement et la rubrique avant laquelle
    vient la documentation du code. Rend les remarques sur les liens."""
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
        titres_m = titres_menu(_lire(source))
        pdoc.render.env.globals.update(titres_menu=titres_m, doc_traitement=module(TRAITEMENT),
                                       doc_code_avant=f"{PAQUET}.{CODE_AVANT}")
        origine = pdoc.render.make_index
        pdoc.render.make_index = _index_par_section(origine, titres_m)
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
