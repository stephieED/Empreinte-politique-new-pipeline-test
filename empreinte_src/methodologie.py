"""Description du traitement, tirée du code (issue #95) : la partie `traitement/` de Pages.

Une page HTML statique, lisible sans lire le code, écrite à chaque déploiement de Pages à partir
de ce que le code déclare déjà :

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
déploiement. Les modules sont importés pour lire leurs constantes, rien n'est exécuté ; aucune
dépendance, aucun script, aucune ressource externe dans la page.

    python -m empreinte_src.methodologie sortie-pages/traitement [--commit SHA] [--depot URL]
"""
from __future__ import annotations

import argparse
import ast
import html
import inspect
import os
import re

import pyarrow as pa
import yaml

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(RACINE, "config", "points_acces.yaml")
DOC = "../doc/"          # documentation du code (pdoc), servie à côté de `traitement/`


# -- un peu de Markdown (celui des docstrings), sans dépendance -------------------------------

def _inline(texte: str) -> str:
    t = html.escape(texte, quote=False)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    return re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)


def _cellules(ligne: str) -> list[str]:
    return [c.strip() for c in ligne.strip().strip("|").split("|")]


def markdown(texte: str) -> str:
    """Le Markdown des docstrings : paragraphes, listes à tirets, tableaux, titres, blocs indentés,
    `code` et **gras**. Tout le reste est rendu comme du texte (échappé)."""
    sortie = []
    blocs = re.split(r"\n\s*\n", inspect.cleandoc(texte or ""))
    for bloc in blocs:
        lignes = bloc.splitlines()
        if not lignes:
            continue
        if all(l.lstrip().startswith("|") for l in lignes):
            lignes_t = [_cellules(l) for l in lignes
                        if not re.fullmatch(r"[\s|:\-]+", l)]
            tete, corps = lignes_t[0], lignes_t[1:]
            sortie.append('<div class="defile"><table><thead><tr>'
                          + "".join(f"<th>{_inline(c)}</th>" for c in tete) + "</tr></thead><tbody>"
                          + "".join("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in r) + "</tr>"
                                    for r in corps)
                          + "</tbody></table></div>")
            continue
        if all(l.startswith("    ") for l in lignes):
            sortie.append("<pre>" + html.escape("\n".join(l[4:] for l in lignes)) + "</pre>")
            continue
        m = re.match(r"(#{1,6}) (.*)", lignes[0])
        if m and len(lignes) == 1:
            sortie.append(f"<h4>{_inline(m.group(2))}</h4>")
            continue
        # Paragraphe et liste peuvent se suivre sans ligne vide.
        para, items = [], []

        def vider():
            if para:
                sortie.append("<p>" + _inline(" ".join(para)) + "</p>")
                para.clear()
            if items:
                sortie.append("<ul>" + "".join(f"<li>{_inline(' '.join(i))}</li>" for i in items) + "</ul>")
                items.clear()
        for l in lignes:
            if l.startswith("- "):
                if para:
                    vider()
                items.append([l[2:].strip()])
            elif items and l.startswith(" "):
                items[-1].append(l.strip())
            else:
                if items:
                    vider()
                para.append(l.strip())
        vider()
    return "\n".join(sortie)


def premier_paragraphe(texte: str | None) -> str:
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
    from . import perimetre as p
    return {"doc": p.__doc__ or "",
            "legislatures": p.plage(p.LEGISLATURES), "paroles": p.plage(p.LEGISLATURES_PAROLES),
            "gouvernements": p.plage(p.LEGISLATURES_GOUVERNEMENTS)}


def donnees(config: str | None = CONFIG) -> dict:
    return {"etapes": etapes(), "zones": zones(), "perimetre": perimetre(),
            "lecteurs": lecteurs(config), "provenance": colonnes_provenance(),
            "regles": regles(), "controles": controles()}


# -- la page ------------------------------------------------------------------------------------

STYLE = """
:root { --texte: #1b1b1b; --fond: #fff; --doux: #555; --lien: #0b4f9c; --trait: #d6d6d6;
        --encart: #f4f4f4; --bloquant: #9b1c1c; --avert: #7a5300; }
@media (prefers-color-scheme: dark) {
  :root { --texte: #e6e6e6; --fond: #161616; --doux: #aaa; --lien: #8cb8ff; --trait: #3a3a3a;
          --encart: #222; --bloquant: #ff9b9b; --avert: #f0c674; }
}
* { box-sizing: border-box; }
body { font-family: system-ui, sans-serif; max-width: 52rem; margin: 2rem auto; padding: 0 1rem;
       line-height: 1.5; color: var(--texte); background: var(--fond); overflow-wrap: break-word; }
a { color: var(--lien); }
h2 { margin-top: 2.5rem; border-bottom: 1px solid var(--trait); padding-bottom: .2rem; }
h3 { margin: 1.8rem 0 .3rem; }
.doux, .meta { color: var(--doux); }
.meta { font-size: .92rem; margin: .2rem 0; }
code { background: var(--encart); padding: 0 .2em; border-radius: 3px; font-size: .92em; }
pre { background: var(--encart); padding: .6rem; overflow-x: auto; }
.defile { overflow-x: auto; }
table { border-collapse: collapse; margin: .5rem 0; font-size: .92rem; }
th, td { border: 1px solid var(--trait); padding: .25rem .5rem; text-align: left; vertical-align: top; }
details { margin: .4rem 0; }
summary { cursor: pointer; color: var(--lien); }
.etiquette { font-size: .8rem; font-weight: 600; padding: 0 .4em; border: 1px solid; border-radius: 3px; }
.bloquant { color: var(--bloquant); }
.avert { color: var(--avert); }
ol.sommaire li, ol.ordre li { margin: .1rem 0; }
h3 code, h4 code { font-size: 1em; }
"""


def _ancre(nom: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "-", nom)


def _doc(module: str, ancre: str = "") -> str:
    return DOC + module.replace(".", "/") + ".html" + (f"#{ancre}" if ancre else "")


def _liste(noms, prefixe="regle-") -> str:
    return ", ".join(f'<a href="#{prefixe}{_ancre(n)}"><code>{html.escape(n)}</code></a>' for n in noms) or "aucune"


def _codes(noms) -> str:
    return ", ".join(f"<code>{html.escape(n)}</code>" for n in noms) or "aucune"


def rendre(d: dict, commit: str | None = None, depot: str | None = None) -> str:
    e = html.escape
    p = []
    w = p.append
    w('<!doctype html>\n<html lang="fr">\n<head>\n<meta charset="utf-8">\n'
      '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
      "<title>Le traitement, étape par étape</title>\n"
      f"<style>{STYLE}</style>\n</head>\n<body>\n")
    w('<p class="doux"><a href="../index.html">Empreinte politique — dépôt d\'essai</a></p>\n')
    w("<h1>Le traitement, étape par étape</h1>\n")
    origine = ""
    if commit:
        court = e(commit[:12])
        origine = (f' (commit <a href="{e(depot)}/commit/{e(commit)}"><code>{court}</code></a>)'
                   if depot else f" (commit <code>{court}</code>)")
    w(f'<p class="doux">Cette page est écrite à partir du code du traitement{origine}, à chaque '
      "déploiement : ce qu'elle décrit est ce que le code déclare. Les choix et leurs raisons sont "
      'dans les <a href="../livrables/index.html">documents de conception</a> ; le code lui-même '
      f'est décrit dans la <a href="{DOC}empreinte_src.html">documentation du code</a>.</p>\n')
    nb_bl = sum(1 for c in d["controles"] if c["bloquant"])
    w('<ol class="sommaire">'
      '<li><a href="#etapes">Les étapes</a></li>'
      '<li><a href="#perimetre">Le périmètre</a></li>'
      f'<li><a href="#lecteurs">Les sources et leurs lecteurs</a> ({len(d["lecteurs"])})</li>'
      f'<li><a href="#regles">Les règles de liaison</a> ({len(d["regles"])})</li>'
      f'<li><a href="#controles">Les contrôles</a> ({nb_bl} bloquants, '
      f'{len(d["controles"]) - nb_bl} avertissements)</li></ol>\n')

    # Étapes
    w('<h2 id="etapes">1. Les étapes</h2>\n')
    w("<p>Chaque nuit, le traitement passe par ces étapes, dans cet ordre.</p>\n")
    renvoi = {"E3": "lecteurs", "E4": "regles", "E6": "controles"}
    w('<div class="defile"><table><thead><tr><th>Étape</th><th>Ce qu\'elle fait</th>'
      "<th>Code</th></tr></thead><tbody>\n")
    for x in d["etapes"]:
        num = x["etape"].split()[0]
        quoi = _inline(x["quoi"])
        if num in renvoi:
            quoi += f' — <a href="#{renvoi[num]}">détail plus bas</a>'
        mods = ", ".join(f'<a href="{_doc("empreinte_src." + m)}"><code>{e(m)}</code></a>' for m in x["modules"])
        w(f"<tr><td>{e(x['etape'])}</td><td>{quoi}</td><td>{mods}</td></tr>\n")
    w("</tbody></table></div>\n")
    if d["zones"]:
        w("<h3>Les zones de données</h3>\n" + markdown(d["zones"]) + "\n")

    # Périmètre
    pe = d["perimetre"]
    w('<h2 id="perimetre">2. Le périmètre</h2>\n')
    w(markdown(pe["doc"]) + "\n")
    w("<ul>"
      f"<li>Législatures publiées (<code>LEGISLATURES</code>) : de la {e(pe['legislatures'])}.</li>"
      f"<li>Prises de parole en séance (<code>LEGISLATURES_PAROLES</code>) : de la {e(pe['paroles'])}.</li>"
      f"<li>Gouvernements (<code>LEGISLATURES_GOUVERNEMENTS</code>) : ceux qui traversent les "
      f"législatures de la {e(pe['gouvernements'])}.</li></ul>\n")
    w(f'<p class="meta">Tiré de <a href="{_doc("empreinte_src.perimetre")}"><code>perimetre</code></a>.</p>\n')

    # Lecteurs
    w('<h2 id="lecteurs">3. Les sources et leurs lecteurs (étape E3)</h2>\n')
    w("<p>Un <strong>lecteur</strong> transforme chaque fichier reçu d'une source en lignes de "
      "faits, rangées dans des tables. Il lit les points d'accès d'un ou de plusieurs types. Le "
      "traitement ajoute à chaque ligne sa provenance : " + _codes(d["provenance"]) + ". Dans les "
      "règles, une table s'appelle <code>lecteur__table</code>.</p>\n")
    w('<div class="defile"><table><thead><tr><th>Lecteur</th><th>Ce qu\'il lit</th><th>Tables</th>'
      "</tr></thead><tbody>"
      + "".join(f'<tr><td><a href="#lecteur-{_ancre(l["nom"])}"><code>{e(l["nom"])}</code></a></td>'
                f'<td>{_inline(l["resume"])}</td><td>{len(l["tables"])}</td></tr>' for l in d["lecteurs"])
      + "</tbody></table></div>\n")
    for l in d["lecteurs"]:
        w(f'<h3 id="lecteur-{_ancre(l["nom"])}"><code>{e(l["nom"])}</code></h3>\n')
        w(f'<p class="meta">version {e(str(l["version"]))} · types lus : {_codes(l["types"])} · '
          f'<a href="{_doc(l["module"])}">code</a></p>\n')
        if l["resume"]:
            w(markdown(l["resume"]) + "\n")
        if l["points"]:
            w('<details><summary>Points d\'accès lus (' + str(len(l["points"])) + ")</summary>"
              '<div class="defile"><table><thead><tr><th>Point d\'accès</th><th>Source</th>'
              "<th>Législature</th><th>Licence</th><th>Adresse</th></tr></thead><tbody>")
            for pt in l["points"]:
                etat = " (relevé, pas encore lu)" if pt.get("lire") is False else ""
                url = pt.get("url") or ""
                lien = f'<a href="{e(url)}">fichier</a>' if url.startswith("https://") else e(url)
                w(f"<tr><td><code>{e(str(pt.get('id')))}</code>{etat}</td><td>{e(str(pt.get('source', '')))}</td>"
                  f"<td>{e(str(pt.get('legislature', '') or ''))}</td><td>{e(str(pt.get('licence', '') or ''))}</td>"
                  f"<td>{lien}</td></tr>")
            w("</tbody></table></div></details>\n")
        for t, cols in l["tables"].items():
            w(f"<details><summary>Table <code>{e(l['nom'])}__{e(t)}</code> ({len(cols)} colonnes)</summary>"
              '<div class="defile"><table><thead><tr><th>Colonne</th><th>Type</th></tr></thead><tbody>'
              + "".join(f"<tr><td><code>{e(c)}</code></td><td>{e(ty)}</td></tr>" for c, ty in cols)
              + "</tbody></table></div></details>\n")

    # Règles
    w('<h2 id="regles">4. Les règles de liaison (étape E4)</h2>\n')
    w("<p>Une <strong>règle</strong> relie les faits lus : elle lit des tables de faits et les "
      "sorties d'autres règles, et écrit ses propres tables. Elles sont appliquées dans l'ordre "
      "ci-dessous : une règle passe après celles dont elle dépend, et sinon dans l'ordre "
      "alphabétique. Chaque ligne écrite porte le nom et la version de sa règle "
      "(<code>R-COMPOSITION@1</code>) ; une règle qui ne conclut pas écrit « non établi » et sa "
      "raison.</p>\n")
    w('<ol class="ordre">' + "".join(f'<li><a href="#regle-{_ancre(r["nom"])}"><code>{e(r["nom"])}</code></a></li>'
                                     for r in d["regles"]) + "</ol>\n")
    for i, r in enumerate(d["regles"], 1):
        w(f'<h3 id="regle-{_ancre(r["nom"])}">{i}. <code>{e(r["nom"])}</code></h3>\n')
        w(f'<p class="meta">version {e(str(r["version"]))} · <a href="{_doc(r["module"])}">code</a></p>\n')
        w(f"<p>{_inline(r['description'])}</p>\n" if r["description"]
          else '<p class="doux">Pas de description.</p>\n')
        w("<ul>"
          f"<li>Dépend de : {_liste(r['depend'])}"
          + (f" ; lit aussi, si elles existent : {_liste(r['facultatif'])}" if r["facultatif"] else "")
          + "</li>"
          f"<li>Écrit : {_codes(r['sorties'])}</li>"
          f"<li>Lue par : {_liste(r['lue_par'])}</li></ul>\n")

    # Contrôles
    w('<h2 id="controles">5. Les contrôles (étape E6)</h2>\n')
    w("<p>Avant toute publication, des contrôles relisent le résultat. Un contrôle "
      '<strong class="bloquant">bloquant</strong> qui trouve une anomalie empêche la publication, '
      "sauf levée explicite par une décision de la propriétaire, valable pour cette anomalie "
      'seulement. Un <strong class="avert">avertissement</strong> laisse publier et ouvre une '
      "issue. Les avertissements donnent des décomptes et des identifiants, jamais un indice "
      "individuel.</p>\n")
    for bloquant, titre in ((True, "Contrôles bloquants"), (False, "Avertissements")):
        w(f"<h3>{titre}</h3>\n")
        for c in (c for c in d["controles"] if c["bloquant"] is bloquant):
            classe, mot = ("bloquant", "bloquant") if bloquant else ("avert", "avertissement")
            ancre = f"controle-{_ancre(c['code'])}-{mot}"
            intitule = c["bref"] or " ; ".join(c["titres"])
            w(f'<h4 id="{ancre}"><code>{e(c["code"])}</code> ' + _inline(intitule[0].upper() + intitule[1:])
              + f' <span class="etiquette {classe}">{mot}</span></h4>\n')
            w("<ul>" + "".join(f"<li>Signale : « {_inline(t)} »</li>" for t in c["titres"]) + "</ul>\n")
            for doc in c["explications"]:
                w(markdown(doc) + "\n")
            w('<p class="meta">Méthode : ' + ", ".join(
                f'<a href="{_doc("empreinte_src.controles", "Controles." + m)}"><code>{e(m)}</code></a>'
                for m in c["methodes"]) + "</p>\n")
    w("</body>\n</html>\n")
    return "".join(p)


def ecrire(dossier: str, config: str | None = CONFIG, commit: str | None = None,
           depot: str | None = None) -> str:
    os.makedirs(dossier, exist_ok=True)
    chemin = os.path.join(dossier, "index.html")
    with open(chemin, "w", encoding="utf-8") as f:
        f.write(rendre(donnees(config), commit=commit, depot=depot))
    return chemin


def main(argv=None):
    ap = argparse.ArgumentParser(description="Écrit la description du traitement (Pages, traitement/).")
    ap.add_argument("dossier")
    ap.add_argument("--config", default=CONFIG)
    ap.add_argument("--commit")
    ap.add_argument("--depot", help="adresse du dépôt, pour le lien vers le commit")
    a = ap.parse_args(argv)
    print(ecrire(a.dossier, a.config, a.commit, a.depot))


if __name__ == "__main__":
    main()
