"""Description du traitement, tirée du code (issue #95) : la page « Le traitement, étape par
étape » de la documentation (module `documentation.traitement`, écrit par `pages_doc`).

Une page en Markdown, lisible sans lire le code, écrite à chaque déploiement de Pages à partir de
ce que le code déclare déjà :

- les étapes E0 à E8 et les zones de données : la docstring du paquet ;
- le périmètre : `perimetre` (sa docstring et ses constantes) ;
- les lecteurs : `lecture.lecteurs()` (NOM, VERSION, TYPES, TABLES, début de la docstring), avec
  les points d'accès de leurs types dans `config/points_acces.yaml` ;
- les règles de liaison, dans leur ordre d'application : `liaison.regles()` (NOM, VERSION,
  DEPEND, DEPEND_FACULTATIF, SORTIES, DESCRIPTION) ;
- les contrôles bloquants et les avertissements : `controles`, lu avec `ast` (les appels
  `_signaler` et `_avertir`, la docstring de la méthode qui les fait, le résumé de la docstring
  du module).

Rien n'est recopié à la main : un lecteur, une règle ou un contrôle ajouté apparaît au prochain
déploiement. Les modules sont importés pour lire leurs constantes, rien n'est exécuté. pdoc rend
le Markdown, avec le menu, la recherche et le sommaire du reste de la documentation.
"""
from __future__ import annotations

import ast
import html
import inspect
import os
import re

import pyarrow as pa
import yaml

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(RACINE, "config", "points_acces.yaml")


def _cellules(ligne: str) -> list[str]:
    return [c.strip() for c in ligne.strip().strip("|").split("|")]


def premier_paragraphe(texte: str | None) -> str:
    """Rend le premier paragraphe de `texte` (une docstring), indentation commune retirée ; une
    chaîne vide pour `None`."""
    return re.split(r"\n\s*\n", inspect.cleandoc(texte or ""))[0].strip()


# -- ce que le code déclare ---------------------------------------------------------------------

def etapes() -> list[dict]:
    """Le tableau des étapes de la docstring du paquet : [{etape, quoi, modules}]."""
    import empreinte_src
    out = []
    for l in (empreinte_src.__doc__ or "").splitlines():
        c = _cellules(l) if l.startswith("| E") else None
        if c and len(c) >= 3:
            out.append({"etape": c[0], "quoi": c[1], "modules": re.findall(r"`([^`]+)`", c[2])})
    return out


def zones() -> str:
    """La section « Les zones de données » de la docstring du paquet (Markdown)."""
    import empreinte_src
    m = re.search(r"## Les zones de données\n(.*?)(?=\n## |\Z)", empreinte_src.__doc__ or "", re.S)
    return m.group(1).strip() if m else ""


def _type(t: pa.DataType) -> str:
    if pa.types.is_string(t) or pa.types.is_large_string(t):
        return "texte"
    if pa.types.is_boolean(t):
        return "booléen"
    if pa.types.is_integer(t):
        return "entier"
    if pa.types.is_floating(t) or pa.types.is_decimal(t):
        return "nombre"
    if pa.types.is_date(t) or pa.types.is_timestamp(t):
        return "date"
    if pa.types.is_list(t) or pa.types.is_large_list(t):
        return f"liste de {_type(t.value_type)}"
    if pa.types.is_struct(t):
        return "structure (" + ", ".join(t.field(i).name for i in range(t.num_fields)) + ")"
    return str(t)


def lecteurs(config: str | None = CONFIG) -> list[dict]:
    """Rend, pour chaque lecteur (`lecture.lecteurs()`), son nom, sa version, ses types, son
    module, le premier paragraphe de sa docstring, les colonnes et types de ses tables, et les
    points d'accès de ses types lus dans le fichier `config` (aucun si le fichier n'existe pas)."""
    from . import lecture
    points = []
    if config and os.path.exists(config):
        with open(config, encoding="utf-8") as f:
            points = (yaml.safe_load(f) or {}).get("points_acces") or []
    out = []
    for m in lecture.lecteurs():
        out.append({
            "nom": m.NOM, "version": m.VERSION, "types": tuple(m.TYPES), "module": m.__name__,
            "resume": premier_paragraphe(m.__doc__),
            "tables": {t: [(f.name, _type(f.type)) for f in s] for t, s in m.TABLES.items()},
            "points": [p for p in points if p.get("type") in m.TYPES],
        })
    return out


def colonnes_provenance() -> list[str]:
    """Rend les noms des colonnes de provenance que le cadre de lecture ajoute à chaque ligne
    (`lecture.COLONNES_PROVENANCE`)."""
    from .lecture import COLONNES_PROVENANCE
    return [n for n, _ in COLONNES_PROVENANCE]


def regles() -> list[dict]:
    """Les règles dans leur ordre d'application (`liaison.regles()`), et qui lit leurs sorties."""
    from . import liaison
    mods = liaison.regles()
    lue_par: dict[str, list[str]] = {}
    for m in mods:
        for d in tuple(m.DEPEND) + tuple(getattr(m, "DEPEND_FACULTATIF", ())):
            lue_par.setdefault(d, []).append(m.NOM)
    return [{"nom": m.NOM, "version": m.VERSION, "module": m.__name__,
             "depend": tuple(m.DEPEND), "facultatif": tuple(getattr(m, "DEPEND_FACULTATIF", ())),
             "sorties": tuple(m.SORTIES), "description": getattr(m, "DESCRIPTION", None),
             "lue_par": lue_par.get(m.NOM, [])} for m in mods]


def _cle_code(code: str):
    return [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", code)]


def _commentaire_au_dessus(lignes: list[str], ligne: int, borne: int) -> str | None:
    """Le bloc de commentaires le plus proche au-dessus de la ligne `ligne` (numérotée à partir de
    1), sans remonter au-delà de la ligne `borne` ; les intertitres `# --` ne comptent pas."""
    i = ligne - 2
    while i >= borne and not lignes[i].strip().startswith("#"):
        i -= 1
    bloc = []
    while i >= borne and lignes[i].strip().startswith("#") and not lignes[i].strip().startswith("# --"):
        bloc.insert(0, lignes[i].strip().lstrip("#").strip())
        i -= 1
    return " ".join(bloc) or None


def controles(chemin: str | None = None) -> list[dict]:
    """Les contrôles, lus dans le source de `controles` sans l'exécuter : chaque appel
    `self._signaler(code, titre, …)` (bloquant, sauf `bloquant=False`) ou `self._avertir(code,
    titre, …)` (avertissement) dont le code et le titre sont écrits en clair, avec la méthode qui
    le fait ; et le résumé de chaque code dans la docstring du module.

    Ce que le contrôle vérifie : la docstring de la méthode quand elle ne signale qu'un code ;
    quand elle en signale plusieurs (C1, C6 et « C1-C6 » dans `c1_c6_comparer`), le commentaire
    le plus proche au-dessus de l'appel, après l'appel précédent."""
    chemin = chemin or os.path.join(os.path.dirname(os.path.abspath(__file__)), "controles.py")
    with open(chemin, encoding="utf-8") as f:
        source = f.read()
    arbre, lignes = ast.parse(source), source.splitlines()
    doc_module = " ".join((ast.get_docstring(arbre) or "").split())
    bref = dict(re.findall(r"\b(C\d+) \(([^)]+)\)", doc_module))
    for code, texte in re.findall(r"\b(A\d+) (.+?)(?=, A\d+ |\.(?:\s|$))", doc_module):
        bref.setdefault(code, texte)
    par_cle: dict[tuple, dict] = {}
    for classe in (n for n in arbre.body if isinstance(n, ast.ClassDef)):
        for meth in (n for n in classe.body if isinstance(n, ast.FunctionDef)):
            appels = sorted((a for a in ast.walk(meth)
                             if isinstance(a, ast.Call) and isinstance(a.func, ast.Attribute)
                             and a.func.attr in ("_signaler", "_avertir") and len(a.args) >= 2
                             and all(isinstance(x, ast.Constant) and isinstance(x.value, str)
                                     for x in a.args[:2])), key=lambda a: a.lineno)
            codes = {a.args[0].value for a in appels}
            doc_meth = ast.get_docstring(meth)
            precedent = meth.body[0].end_lineno if doc_meth else meth.lineno
            for appel in appels:
                bloquant = appel.func.attr == "_signaler" and not any(
                    k.arg == "bloquant" and isinstance(k.value, ast.Constant) and k.value.value is False
                    for k in appel.keywords)
                code, titre = appel.args[0].value, appel.args[1].value
                c = par_cle.setdefault((code, bloquant), {
                    "code": code, "bloquant": bloquant, "bref": bref.get(code),
                    "titres": [], "methodes": [], "explications": []})
                if titre not in c["titres"]:
                    c["titres"].append(titre)
                if meth.name not in c["methodes"]:
                    c["methodes"].append(meth.name)
                    if len(codes) == 1 and doc_meth:
                        c["explications"].append(doc_meth)
                if len(codes) > 1:
                    x = _commentaire_au_dessus(lignes, appel.lineno, precedent)
                    if x and x not in c["explications"]:
                        c["explications"].append(x)
                precedent = appel.end_lineno
    return sorted(par_cle.values(), key=lambda c: (not c["bloquant"], _cle_code(c["code"])))


def perimetre() -> dict:
    """Rend la docstring du module `perimetre` (`doc`) et les plages de législatures des fiches
    (`legislatures`), des prises de parole (`paroles`) et des gouvernements (`gouvernements`)."""
    from . import perimetre as p
    return {"doc": p.__doc__ or "",
            "legislatures": p.plage(p.LEGISLATURES), "paroles": p.plage(p.LEGISLATURES_PAROLES),
            "gouvernements": p.plage(p.LEGISLATURES_GOUVERNEMENTS)}


def donnees(config: str | None = CONFIG) -> dict:
    """Rend tout ce que la page décrit : `etapes`, `zones`, `perimetre`, `lecteurs` (avec les
    points d'accès de `config`), `provenance`, `regles` et `controles`."""
    return {"etapes": etapes(), "zones": zones(), "perimetre": perimetre(),
            "lecteurs": lecteurs(config), "provenance": colonnes_provenance(),
            "regles": regles(), "controles": controles()}


# -- la page ------------------------------------------------------------------------------------

def ancre(titre: str) -> str:
    """L'ancre que pdoc donne au titre Markdown `titre` (voir `pages_doc.ancre`)."""
    from .pages_doc import ancre as a
    return a(titre)


def _cellule(texte: str) -> str:
    """Du Markdown d'une ligne, sûr dans une cellule de tableau."""
    return " ".join((texte or "").split()).replace("|", "\\|")


def _encart(doc: str) -> str:
    """Une docstring reprise dans la page : indentation commune retirée, ses titres descendus sous
    ceux de la page."""
    return re.sub(r"^(#{1,6}) ", lambda m: "#" * min(6, len(m.group(1)) + 4) + " ",
                  inspect.cleandoc(doc or ""), flags=re.M)


def _premiere_majuscule(t: str) -> str:
    return t[:1].upper() + t[1:]


def _titres(d: dict) -> dict[str, str]:
    """Les titres des sections et des sous-sections, d'où viennent les ancres des liens internes."""
    t = {"etapes": "1. Les étapes", "perimetre": "2. Le périmètre",
         "lecteurs": "3. Les sources et leurs lecteurs (étape E3)",
         "regles": "4. Les règles de liaison (étape E4)", "controles": "5. Les contrôles (étape E6)"}
    for l in d["lecteurs"]:
        t["lecteur:" + l["nom"]] = f"`{l['nom']}`"
    for i, r in enumerate(d["regles"], 1):
        t["regle:" + r["nom"]] = f"{i}. `{r['nom']}`"
    for c in d["controles"]:
        mot = "bloquant" if c["bloquant"] else "avertissement"
        intitule = c["bref"] or " ; ".join(c["titres"])
        t[f"controle:{c['code']}:{mot}"] = f"`{c['code']}` {_premiere_majuscule(intitule)} ({mot})"
    return t


def rendre(d: dict, commit: str | None = None, depot: str | None = None,
           de: str = "documentation.traitement") -> str:
    """Rend la page du traitement en Markdown à partir de `d` (voir `donnees`) : étapes et zones,
    périmètre, lecteurs avec leurs points d'accès et leurs tables, règles dans leur ordre
    d'application, contrôles bloquants puis avertissements. Les liens vers le code mènent aux
    pages pdoc des modules, vues depuis celle du module `de`. Avec `commit`, la page dit de quel
    commit elle vient (avec un lien si `depot`, l'adresse du dépôt, est donné)."""
    e = html.escape
    racine = "../" * de.count(".")
    t = _titres(d)

    def doc(module: str, a: str = "") -> str:
        return racine + module.replace(".", "/") + ".html" + (f"#{a}" if a else "")

    def vers(cle: str) -> str:
        return "#" + ancre(t[cle])

    def regles(noms) -> str:
        return ", ".join(f"[`{n}`]({vers('regle:' + n)})" for n in noms) or "aucune"

    def codes(noms) -> str:
        return ", ".join(f"`{n}`" for n in noms) or "aucune"

    p: list[str] = []
    w = p.append
    w("# Le traitement, étape par étape\n")
    origine = ""
    if commit:
        origine = (f" (commit [`{commit[:12]}`]({depot}/commit/{commit}))" if depot
                   else f" (commit `{commit[:12]}`)")
    nb_bl = sum(1 for c in d["controles"] if c["bloquant"])
    w(f"Cette page est écrite à partir du code du traitement{origine}, à chaque déploiement : ce "
      "qu'elle décrit est ce que le code déclare. Les choix et leurs raisons sont dans les "
      f"[documents de conception]({racine}documentation.html) ; "
      f"le code lui-même est décrit dans la [documentation du code]({doc('empreinte_src')}).\n")
    w(f"Dans cette page : [les étapes]({vers('etapes')}), [le périmètre]({vers('perimetre')}), "
      f"[les sources et leurs lecteurs]({vers('lecteurs')}) ({len(d['lecteurs'])}), "
      f"[les règles de liaison]({vers('regles')}) ({len(d['regles'])}), "
      f"[les contrôles]({vers('controles')}) ({nb_bl} bloquants, "
      f"{len(d['controles']) - nb_bl} avertissements).\n")

    # Étapes
    w(f"## {t['etapes']}\n")
    w("Chaque nuit, le traitement passe par ces étapes, dans cet ordre.\n")
    renvoi = {"E3": "lecteurs", "E4": "regles", "E6": "controles"}
    w("| Étape | Ce qu'elle fait | Code |\n| --- | --- | --- |")
    for x in d["etapes"]:
        num = x["etape"].split()[0]
        quoi = _cellule(x["quoi"])
        if num in renvoi:
            quoi += f" — [détail plus bas]({vers(renvoi[num])})"
        mods = ", ".join(f"[`{m}`]({doc('empreinte_src.' + m)})" for m in x["modules"])
        w(f"| {_cellule(x['etape'])} | {quoi} | {mods} |")
    w("")
    if d["zones"]:
        w("### Les zones de données\n")
        w(_encart(d["zones"]) + "\n")

    # Périmètre
    pe = d["perimetre"]
    w(f"## {t['perimetre']}\n")
    w(_encart(pe["doc"]) + "\n")
    w(f"- Législatures publiées (`LEGISLATURES`) : de la {pe['legislatures']}.\n"
      f"- Prises de parole en séance (`LEGISLATURES_PAROLES`) : de la {pe['paroles']}.\n"
      f"- Gouvernements (`LEGISLATURES_GOUVERNEMENTS`) : ceux qui traversent les législatures de "
      f"la {pe['gouvernements']}.\n")
    w(f"*Tiré de [`perimetre`]({doc('empreinte_src.perimetre')}).*\n")

    # Lecteurs
    w(f"## {t['lecteurs']}\n")
    w("Un **lecteur** transforme chaque fichier reçu d'une source en lignes de faits, rangées dans "
      "des tables. Il lit les points d'accès d'un ou de plusieurs types. Le traitement ajoute à "
      f"chaque ligne sa provenance : {codes(d['provenance'])}. Dans les règles, une table "
      "s'appelle `lecteur__table`.\n")
    w("| Lecteur | Ce qu'il lit | Tables |\n| --- | --- | ---: |")
    for l in d["lecteurs"]:
        w(f"| [`{l['nom']}`]({vers('lecteur:' + l['nom'])}) | {_cellule(l['resume'])} | {len(l['tables'])} |")
    w("")
    for l in d["lecteurs"]:
        w(f"### {t['lecteur:' + l['nom']]}\n")
        w(f"*version {l['version']} · types lus : {codes(l['types'])} · "
          f"[code]({doc(l['module'])})*\n")
        if l["resume"]:
            w(_encart(l["resume"]) + "\n")
        blocs = []
        if l["points"]:
            lignes = []
            for pt in l["points"]:
                etat = " (relevé, pas encore lu)" if pt.get("lire") is False else ""
                url = pt.get("url") or ""
                lien = f'<a href="{e(url)}">fichier</a>' if url.startswith("https://") else e(url)
                lignes.append(
                    f"<tr><td><code>{e(str(pt.get('id')))}</code>{etat}</td>"
                    f"<td>{e(str(pt.get('source', '')))}</td>"
                    f"<td>{e(str(pt.get('legislature', '') or ''))}</td>"
                    f"<td>{e(str(pt.get('licence', '') or ''))}</td><td>{lien}</td></tr>")
            blocs.append(f"<details><summary>Points d'accès lus ({len(l['points'])})</summary>"
                         "<table><thead><tr><th>Point d'accès</th><th>Source</th><th>Législature</th>"
                         "<th>Licence</th><th>Adresse</th></tr></thead><tbody>"
                         + "".join(lignes) + "</tbody></table></details>")
        for nom_t, cols in l["tables"].items():
            blocs.append(f"<details><summary>Table <code>{e(l['nom'])}__{e(nom_t)}</code> "
                         f"({len(cols)} colonnes)</summary><table><thead><tr><th>Colonne</th>"
                         "<th>Type</th></tr></thead><tbody>"
                         + "".join(f"<tr><td><code>{e(c)}</code></td><td>{e(ty)}</td></tr>"
                                   for c, ty in cols)
                         + "</tbody></table></details>")
        if blocs:
            w('<div class="details-traitement">' + "".join(blocs) + "</div>\n")

    # Règles
    w(f"## {t['regles']}\n")
    w("Une **règle** relie les faits lus : elle lit des tables de faits et les sorties d'autres "
      "règles, et écrit ses propres tables. Elles sont appliquées dans l'ordre ci-dessous : une "
      "règle passe après celles dont elle dépend, et sinon dans l'ordre alphabétique. Chaque "
      "ligne écrite porte le nom et la version de sa règle (`R-COMPOSITION@1`) ; une règle qui ne "
      "conclut pas écrit « non établi » et sa raison.\n")
    w("\n".join(f"{i}. [`{r['nom']}`]({vers('regle:' + r['nom'])})"
                for i, r in enumerate(d["regles"], 1)) + "\n")
    for r in d["regles"]:
        w(f"### {t['regle:' + r['nom']]}\n")
        w(f"*version {r['version']} · [code]({doc(r['module'])})*\n")
        w(" ".join(r["description"].split()) + "\n" if r["description"] else "*Pas de description.*\n")
        dep = f"- Dépend de : {regles(r['depend'])}"
        if r["facultatif"]:
            dep += f" ; lit aussi, si elles existent : {regles(r['facultatif'])}"
        w(dep + f"\n- Écrit : {codes(r['sorties'])}\n- Lue par : {regles(r['lue_par'])}\n")

    # Contrôles
    w(f"## {t['controles']}\n")
    w("Avant toute publication, des contrôles relisent le résultat. Un contrôle **bloquant** qui "
      "trouve une anomalie empêche la publication, sauf levée explicite par une décision de la "
      "propriétaire, valable pour cette anomalie seulement. Un **avertissement** laisse publier et "
      "ouvre une issue. Les avertissements donnent des décomptes et des identifiants, jamais un "
      "indice individuel.\n")
    for bloquant, titre in ((True, "Contrôles bloquants"), (False, "Avertissements")):
        w(f"### {titre}\n")
        for c in (c for c in d["controles"] if c["bloquant"] is bloquant):
            mot = "bloquant" if bloquant else "avertissement"
            cle = f"controle:{c['code']}:{mot}"
            w(f"#### {t[cle]}\n")
            w("\n".join(f"- Signale : « {' '.join(x.split())} »" for x in c["titres"]) + "\n")
            for x in c["explications"]:
                w(_encart(x) + "\n")
            w("*Méthode : " + ", ".join(
                f"[`{m}`]({doc('empreinte_src.controles', 'Controles.' + m)})"
                for m in c["methodes"]) + "*\n")
    return "\n".join(p).rstrip() + "\n"
