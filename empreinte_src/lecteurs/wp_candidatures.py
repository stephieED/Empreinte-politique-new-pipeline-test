"""Wikipédia : l'article « Candidatures à l'élection présidentielle française de 2027 »
(mesures `autres-sources.md`, § 5 ; licence CC BY-SA 4.0, la révision lue est gardée).

Le membre est la réponse JSON de l'API MediaWiki `action=parse` (`parse.revid`,
`parse.wikitext`, en `formatversion=2` ; la forme 1, `wikitext: {"*": …}`, est aussi lue). La
réponse peut porter la page entière ou une seule section (`section=1`, extrait de test) ; une
liste `parse.links` avec `exists`, si elle est là, dit si l'article lié existe.

Sections lues (titres de niveau 2, cherchés par leur texte) :
- « Candidats déclarés » : un tableau, une ligne par candidat ; le **nom est dans la cellule
  d'en-tête de ligne** (`!`), avant le premier `<br>`, sous quatre formes rencontrées :
  `! {{TriNom|Prénom|Nom}}`, `!{{TriNom|…}}` (sans espace), `{{TriNom|…|nolink=oui}}` (sans
  article), `![[Titre]]` ou `![[Titre|Nom affiché]]` (lien direct) ;
- « Candidatures retirées », si elle existe : une liste à puces, `* [[Nom]] ([[Parti]]), …`
  (ou `{{TriNom|…}}`, ou nom en clair avant la parenthèse).

Un nom qui ne prend aucune de ces formes **n'est pas deviné** : la ligne est comptée dans
`candidature_lecture` (`non_extraits`, avec l'en-tête tel qu'écrit dans `exemples`), qui donne
aussi le contrôle « candidats extraits = lignes du tableau ».

Pour chaque candidat : nom tel qu'écrit (prénom et nom d'un TriNom réunis par une espace),
article lié s'il y en a un (`None` avec `nolink=oui`), statut (`declaree`/`retiree`), date de
déclaration **si la ligne en donne une** dans une phrase qui dit la candidature (« annonce sa
candidature le {{date|…}} », « se déclare candidat le … », « est désigné candidat… le … »,
« annonce se présenter… le … ») : la date telle qu'écrite (`date_declaration_texte`), en ISO
quand elle est complète, et la phrase source ; sinon `None` et « non connue ». Les références
citées (`<ref>…</ref>`) sont restituées par leur adresse (`url=`, `lire en ligne=`, ou lien
nu) ; une référence réutilisée (`<ref name="x"/>`) n'a pas d'adresse dans la ligne : elle est
comptée dans `nb_references`, son nom gardé dans `references_nommees`.

Deux listes de références, à ne pas confondre (issue #72) :
- `references` : toutes celles de la **ligne** du tableau, qui sourcent aussi le parti, les
  soutiens (note « Candidature soutenue par »), les fonctions… (22 pour Jean-Luc Mélenchon le
  24/11/2026, dont 19 pour ses soutiens) ;
- `references_declaration` : celles qui établissent la date, c'est-à-dire celles de la **phrase
  qui date la déclaration** (y compris une référence placée juste après son point) ; si elle
  n'en porte aucune, celles de son **paragraphe** (texte de la cellule entre deux sauts de ligne
  ou `----`), car les contributeurs les placent souvent en fin de paragraphe, après une autre
  phrase (David Lisnard : « Il déclare sa candidature pour la présidentielle le {{date|31 mars
  2026}} […]. Il maintient sa volonté d'une primaire de la droite<ref>…</ref>. »). `references_declaration_portee` dit lequel (`phrase`,
  `paragraphe`, vide sans référence). Une référence réutilisée (`<ref name="x"/>`) est
  retrouvée par son nom dans tout l'article ; `nb_references_declaration` compte toutes celles
  retenues, retrouvées ou non.

Ce lecteur dépend de conventions de rédaction que tout contributeur peut changer : ses tests
couvrent les formes rencontrées, et l'écart entre lignes et candidats extraits est mesuré à
chaque lecture.
"""
from __future__ import annotations

import re
from urllib.parse import quote

import orjson
import pyarrow as pa

NOM = "wp_candidatures"
VERSION = 2
TYPES = ("candidatures",)
ELECTION = "presidentielle-2027"

S = pa.string()
TABLES = {
    "candidature": pa.schema([
        ("election", S), ("statut", S), ("rang", pa.int32()), ("personne_source", S),
        ("nom", S), ("prenom", S), ("nom_famille", S), ("forme_nom", S), ("article", S),
        ("article_existe", pa.bool_()),
        ("date_declaration", S), ("date_declaration_texte", S),
        ("date_declaration_raison", S), ("date_declaration_phrase", S),
        ("references", pa.list_(S)), ("references_nommees", pa.list_(S)),
        ("nb_references", pa.int32()),
        ("references_declaration", pa.list_(S)), ("nb_references_declaration", pa.int32()),
        ("references_declaration_portee", S),
        ("revision", pa.int64()), ("page", S),
    ]),
    "candidature_lecture": pa.schema([
        ("election", S), ("revision", pa.int64()), ("page", S), ("section", S),
        ("section_trouvee", pa.bool_()), ("lignes", pa.int32()), ("extraits", pa.int32()),
        ("non_extraits", pa.int32()), ("exemples", pa.list_(S)),
    ]),
}

SECTIONS = {"declaree": "Candidats déclarés", "retiree": "Candidatures retirées"}
MOIS = {m: i for i, m in enumerate(
    ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre",
     "octobre", "novembre", "décembre"], 1)}
MOIS["fevrier"], MOIS["aout"], MOIS["decembre"], MOIS["1er"] = 2, 8, 12, 1

_TITRE = re.compile(r"^(={2,6})\s*(.*?)\s*\1\s*$", re.M)
_TRINOM = re.compile(r"^\{\{\s*[Tt]ri[Nn]om\s*\|([^{}]*)\}\}")
_LIEN = re.compile(r"^\[\[([^\[\]|]+)(?:\|([^\[\]]+))?\]\]")
_REF = re.compile(r"<ref(\s[^>]*?)?(?:/>|>(.*?)</ref\s*>)", re.S | re.I)
_REF_NOM = re.compile(r"""name\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s/>]+))""", re.I)
_URL = re.compile(r"(?:\burl|lire en ligne|archive-url)\s*=\s*([^|}\s]+)", re.I)
_URL_NUE = re.compile(r"\[?(https?://[^\s|\]}<]+)")
# Une référence remplacée par un jeton (caractères d'usage privé) : paragraphes et phrases sont
# découpés sans couper dans une référence, et chacun garde les siennes ; une référence placée
# juste après la ponctuation finale appartient à la phrase qu'elle clôt.
_JETON = re.compile("\ue000(\\d+)\ue001")
_FIN_PHRASE = re.compile("[.!?]((?:\\s*\ue000\\d+\ue001)*)\\s+")
_DATE_MODELE = re.compile(r"\{\{\s*[Dd]ate\s*\|([^{}]*)\}\}")
_DATE_CLAIRE = re.compile(r"\b(1er|\d{1,2})\s+(" + "|".join(sorted(MOIS, key=len, reverse=True))
                          + r")\s+(\d{4})\b", re.I)
_MOIS_ANNEE = re.compile(r"\b((?:" + "|".join(m for m in MOIS if m != "1er") + r")\s+\d{4})\b", re.I)
_PHRASE_CANDIDATURE = re.compile(
    r"(annon\w*|déclar\w*|présent\w*|officialis\w*|dépos\w*)\s+(?:\S+\s+){0,2}?sa candidature"
    r"|se\s+(?:déclare|présente)\s+candidat"
    r"|désignée?\s+candidat"
    r"|annonce\s+(?:vouloir\s+)?se\s+présenter"
    r"|annonc\w*\b.{0,40}?\bêtre\s+candidat", re.I)


def _texte_wiki(o) -> tuple[int | None, str, str | None, dict]:
    p = o.get("parse")
    if not isinstance(p, dict):
        raise ValueError("réponse sans `parse` (erreur de l'API ?)")
    w = p.get("wikitext")
    if isinstance(w, dict):
        w = w.get("*")
    if not isinstance(w, str):
        raise ValueError("réponse sans wikitexte")
    existe = {l.get("title"): l.get("exists") for l in p.get("links") or [] if isinstance(l, dict)}
    rev = p.get("revid")
    return (int(rev) if rev is not None else None), w, p.get("title"), existe


def section(wiki: str, titre: str) -> str | None:
    """Texte d'une section de niveau 2 (jusqu'au titre suivant de niveau 2 ou moins)."""
    titres = list(_TITRE.finditer(wiki))
    for k, t in enumerate(titres):
        if len(t.group(1)) == 2 and t.group(2).strip().lower() == titre.lower():
            fin = len(wiki)
            for u in titres[k + 1:]:
                if len(u.group(1)) <= 2:
                    fin = u.start()
                    break
            return wiki[t.end():fin]
    return None


def nom_ecrit(cellule: str) -> dict | None:
    """Nom d'un candidat au début d'une cellule ; None si la forme n'est pas reconnue."""
    c = cellule.strip()
    m = _TRINOM.match(c)
    if m:
        pos, nommes = [], {}
        for a in m.group(1).split("|"):
            if "=" in a:
                k, v = a.split("=", 1)
                nommes[k.strip().lower()] = v.strip()
            else:
                pos.append(a.strip())
        if len(pos) < 2 or not pos[0] or not pos[1] or set(nommes) - {"nolink", "lien"}:
            return None
        nom = f"{pos[0]} {pos[1]}"
        if nommes.get("nolink", "").lower() in ("oui", "1", "yes"):
            article, forme = None, "TriNom nolink"
        else:
            article, forme = nommes.get("lien") or nom, "TriNom"
        return {"nom": nom, "prenom": pos[0], "nom_famille": pos[1], "article": article,
                "forme_nom": forme}
    m = _LIEN.match(c)
    if m:
        cible = m.group(1).strip()
        if ":" in cible:                          # Fichier:, Catégorie:… : pas un nom
            return None
        return {"nom": (m.group(2) or cible).strip(), "prenom": None, "nom_famille": None,
                "article": cible, "forme_nom": "lien"}
    return None


def _ref(m) -> tuple[str | None, str | None]:
    """(adresse, nom) d'une référence trouvée par `_REF` ; l'un ou l'autre peut manquer."""
    attrs, corps = m.group(1) or "", m.group(2)
    nm = _REF_NOM.search(attrs)
    nom = next((g for g in nm.groups() if g), None) if nm else None
    u = (_URL.search(corps) or _URL_NUE.search(corps)) if corps is not None else None
    return (u.group(1).strip() if u else None), nom


def adresses_nommees(wiki: str) -> dict[str, str]:
    """Nom -> adresse des références nommées de tout l'article (la première définition)."""
    out = {}
    for m in _REF.finditer(wiki):
        u, nom = _ref(m)
        if u and nom:
            out.setdefault(nom, u)
    return out


def _refs(texte: str):
    urls, noms, n = [], [], 0
    for m in _REF.finditer(texte):
        n += 1
        u, nom = _ref(m)
        if u:
            if u not in urls:
                urls.append(u)
        elif nom:
            noms.append(nom)
    return urls, noms, n


def _date_iso(texte_date: str) -> str | None:
    """`8 décembre 2025`, `23/08/2026`, `2|10|2026` -> ISO ; sinon None."""
    t = texte_date.strip()
    m = re.fullmatch(r"(\d{1,2})\s*[|/]\s*(\d{1,2})\s*[|/]\s*(\d{4})", t)
    if m:
        j, mo, a = int(m.group(1)), int(m.group(2)), int(m.group(3))
    else:
        m = re.fullmatch(r"(1er|\d{1,2})\s*[| ]\s*([^\s|]+)\s*[| ]\s*(\d{4})", t, re.I)
        if not m or m.group(2).lower() not in MOIS:
            return None
        j = 1 if m.group(1).lower() == "1er" else int(m.group(1))
        mo, a = MOIS[m.group(2).lower()], int(m.group(3))
    if not (1 <= mo <= 12 and 1 <= j <= 31):
        return None
    return f"{a:04d}-{mo:02d}-{j:02d}"


def _dates(phrase: str) -> list[tuple[int, str]]:
    """(position, date telle qu'écrite) : modèle {{date|…}}, date en clair, mois et année."""
    out = [(m.start(), m.group(1)) for m in _DATE_MODELE.finditer(phrase)]
    pris = [(m.start(), m.end()) for m in _DATE_MODELE.finditer(phrase)]
    for m in _DATE_CLAIRE.finditer(phrase):
        if not any(a <= m.start() < b for a, b in pris):
            out.append((m.start(), m.group(0)))
            pris.append((m.start(), m.end()))
    for m in _MOIS_ANNEE.finditer(phrase):
        if not any(a <= m.start() < b for a, b in pris):
            out.append((m.start(), m.group(1)))
    return sorted(out)


def _phrases(texte: str):
    """(phrase sans références, références de la phrase, références de son paragraphe). Les
    paragraphes sont séparés par un saut de ligne ou `----`, les phrases par une ponctuation
    finale suivie d'un blanc, comme dans le texte sans références."""
    refs = []

    def jeton(m):
        refs.append(m)
        return f"\ue000{len(refs) - 1}\ue001"
    for par in re.split(r"\n+|----", _REF.sub(jeton, texte)):
        du_paragraphe = [refs[int(i)] for i in _JETON.findall(par)]
        debut, morceaux = 0, []
        for m in _FIN_PHRASE.finditer(par):
            morceaux.append(par[debut:m.end(1)])
            debut = m.end()
        morceaux.append(par[debut:])
        for x in morceaux:
            yield _JETON.sub("", x), [refs[int(i)] for i in _JETON.findall(x)], du_paragraphe


def date_declaration(texte: str, nommees: dict[str, str] | None = None) -> dict:
    """Première phrase qui dit la candidature et porte une date ; la date retenue est la
    première qui suit l'expression (« … officialise sa candidature le … »), à défaut la
    dernière qui la précède (« Le {{date|…}}, elle annonce sa candidature »). Rend aussi les
    adresses des références de cette phrase, à défaut de son paragraphe
    (`references_declaration`, `references_declaration_portee`) ; une référence
    réutilisée (`<ref name="x"/>`) est retrouvée dans `nommees` (nom -> adresse, tout l'article)."""
    for phrase, de_la_phrase, du_paragraphe in _phrases(texte):
        m = _PHRASE_CANDIDATURE.search(phrase)
        if not m:
            continue
        dates = _dates(phrase)
        if not dates:
            continue
        apres = [d for d in dates if d[0] >= m.start()]
        brut = apres[0][1] if apres else dates[-1][1]
        lisible = brut.replace("|", "/") if re.fullmatch(r"[\d|]+", brut) else brut.replace("|", " ")
        iso = _date_iso(brut)
        portee, refs = (("phrase", de_la_phrase) if de_la_phrase
                        else ("paragraphe", du_paragraphe) if du_paragraphe else (None, []))
        urls = []
        for r in refs:
            u, nom = _ref(r)
            u = u or (nommees or {}).get(nom)
            if u and u not in urls:
                urls.append(u)
        return {"date_declaration": iso, "date_declaration_texte": " ".join(lisible.split()),
                "date_declaration_raison": None if iso else "date incomplète",
                "date_declaration_phrase": " ".join(phrase.split()).lstrip("|! ")[:500],
                "references_declaration": urls, "nb_references_declaration": len(refs),
                "references_declaration_portee": portee}
    return {"date_declaration": None, "date_declaration_texte": None,
            "date_declaration_raison": "non connue", "date_declaration_phrase": None,
            "references_declaration": [], "nb_references_declaration": 0,
            "references_declaration_portee": None}


def _lignes_tableau(sec: str) -> list[tuple[str, str]]:
    """(en-tête de ligne, texte de la ligne) pour chaque ligne du premier tableau de la section."""
    debut = sec.find("{|")
    if debut < 0:
        return []
    corps = sec[debut:]
    out = []
    for bloc in re.split(r"^\|-.*$", corps, flags=re.M)[1:]:
        lignes = bloc.strip("\n").split("\n")
        tete = next((l for l in lignes if l.startswith("!")), None)
        if tete is None or "scope=\"col\"" in tete or "scope=col" in tete:
            continue
        out.append((tete[1:], bloc))
    return out


def _lignes_liste(sec: str) -> list[tuple[str, str]]:
    return [(l.lstrip("*").strip(), l) for l in sec.split("\n") if l.startswith("*")]


def _nom_clair(entete: str) -> dict | None:
    """Liste des candidatures retirées : nom en clair avant « ( » ou « , »."""
    m = re.match(r"^([A-ZÀ-Ý][\w'’.\- ]+?)\s*[(,]", entete)
    if not m or "[[" in m.group(1) or "{{" in m.group(1):
        return None
    return {"nom": m.group(1).strip(), "prenom": None, "nom_famille": None, "article": None,
            "forme_nom": "texte"}


def lire(m):
    """Lit une réponse de l'API MediaWiki (`m`, un `MembreLu`) et rend
    `{"candidature": [lignes], "candidature_lecture": [lignes]}`.

    Pour chaque section de `SECTIONS` (candidats déclarés, puis candidatures retirées), chaque
    ligne dont le nom est reconnu donne une candidature (statut, rang, nom, article lié et son
    existence, date de déclaration, références, révision, adresse) ; une ligne de
    `candidature_lecture` par section compte les lignes lues, extraites et non extraites, avec
    jusqu'à cinq exemples non extraits. Lève `ValueError` si la section « Candidats déclarés » est
    introuvable."""
    rev, wiki, titre, existe = _texte_wiki(orjson.loads(m.octets))
    page = f"https://fr.wikipedia.org/w/index.php?title={quote((titre or '').replace(' ', '_'))}"
    candidatures, bilans = [], []
    nommees = adresses_nommees(wiki)
    for statut, nom_section in SECTIONS.items():
        sec = section(wiki, nom_section)
        lignes = [] if sec is None else (
            _lignes_tableau(sec) if statut == "declaree" else _lignes_liste(sec))
        extraits, exemples = 0, []
        for entete, texte in lignes:
            tete = re.split(r"<br\s*/?>", entete, maxsplit=1)[0]
            n = nom_ecrit(tete) or (_nom_clair(tete) if statut == "retiree" else None)
            if n is None:
                if len(exemples) < 5:
                    exemples.append(tete.strip()[:200])
                continue
            urls, noms, nb = _refs(texte)
            ancre = quote(nom_section.replace(" ", "_"))
            candidatures.append({
                "election": ELECTION, "statut": statut, "rang": extraits,
                "personne_source": n["article"] or n["nom"], **n,
                "article_existe": existe.get(n["article"]) if n["article"] else None,
                **date_declaration(texte, nommees),
                "references": urls, "references_nommees": noms, "nb_references": nb,
                "revision": rev, "page": titre,
                "prov_url": f"{page}&oldid={rev}#{ancre}" if rev else f"{page}#{ancre}",
            })
            extraits += 1
        bilans.append({
            "election": ELECTION, "revision": rev, "page": titre, "section": nom_section,
            "section_trouvee": sec is not None, "lignes": len(lignes), "extraits": extraits,
            "non_extraits": len(lignes) - extraits, "exemples": exemples,
            "prov_url": f"{page}&oldid={rev}" if rev else page,
        })
    if not bilans[0]["section_trouvee"]:
        raise ValueError("section « Candidats déclarés » introuvable")
    return {"candidature": candidatures, "candidature_lecture": bilans}


EXPORT = {
    "candidature": {"type": "candidature", "cle": ["election", "statut", "personne_source"],
                    "ids": {"autre": "personne_source"}, "date": "date_declaration"},
}
