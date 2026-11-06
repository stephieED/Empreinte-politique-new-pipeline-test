"""Journal officiel : livraisons de la DILA (cahier 3.6 ; mesures `autres-sources.md`, § 1).

Chaque livraison `JORF_AAAAMMJJ-HHMMSS.tar.gz` est rangée membre par membre. Le chemin d'un
membre commence par l'horodatage de la livraison (`20261104-004428/jorf/global/…`) ; la nature
du membre se lit à **sa racine XML**, jamais à son uid :

- `TEXTE_VERSION` (`texte/version/…/JORFTEXT….xml`) : les métadonnées d'un acte et ses liens
  → `acte_reglementaire` et `lien_acte_loi` ;
- `TEXTELR` (`texte/struct/…/JORFTEXT….xml`) : le plan de l'acte et la liste de ses versions
  (version JORF d'origine, versions consolidées LEGI avec leur état `VIGUEUR`, `MODIFIE`,
  `ABROGE`…) → `version_acte` ;
- `JO` (`conteneur/…/JORFCONT….xml`) : le sommaire d'un numéro du JO, qui seul porte la
  **rubrique** d'un acte (« Mesures nominatives »… : R-MESURE-NOMINATIVE) → `sommaire_jo`.
  Le rapprochement acte ↔ rubrique est une liaison : il appartient aux règles ;
- `liste_suppression_jorf.dat` (texte, une ligne par chemin supprimé, sans extension :
  `jorf/global/article/…/JORFARTI…`, `null/JORFDOLE…`) : 7 livraisons sur 72 en portent une
  entre le 06/10 et le 05/11/2026, aucune des trois livraisons mesurées le 04/11 → `suppression_jo`,
  ligne à ligne, telle que publiée (le retrait des objets visés est une règle) ;
- `ARTICLE` (`JORFARTI`) et `SECTION_TA` (`JORFSCTA`) : **non lus** (aucune ligne). Le texte
  intégral n'est pas un besoin du site (doc. 1, 1.4 G ; cahier 3.1.8) ; le numéro, l'état et
  les dates des articles sont déjà dans le plan (`TEXTELR`), les métadonnées de l'acte dans
  `TEXTE_VERSION`, et le rattachement article → texte dans le chemin des liens. Ils restent
  dans l'entrepôt.

Pièges traités :
- **un même `JORFTEXT` deux fois par livraison** (struct et version) : l'entrepôt nomme le
  second `JORFTEXT…@<empreinte du chemin>`, et comme le chemin porte l'horodatage, chaque
  redélivraison d'un acte crée un **uid nouveau**. L'identifiant de l'acte est donc lu dans
  `META_COMMUN/ID`, et chaque ligne garde sa `livraison` (lue dans le chemin), qui entre dans
  la clé d'export : un acte redélivré donne une ligne par livraison, la règle « la dernière
  livraison d'un ID remplace la précédente » restant aux règles (voir le compte rendu) ;
- **redélivraison de textes anciens** (134 actes sur 169 dans la livraison du 02/11 soir) :
  lus comme les autres, avec leur date de publication, aucun filtre ici ;
- **date sentinelle `2999-01-01`** (signature, début et fin de version) : `None`, avec un
  indicateur `…_sentinelle` ; la valeur écrite reste dans `date_signature_source` ;
- **`SIGNATAIRES`** : bloc HTML libre, restitué tel quel (`signataires_html`) et en texte
  (`signataires`, sauts de ligne aux `<br/>`) ; aucun nom de personne n'en est tiré ;
- **ministère** en libellé libre, **NOR** et **numéro** souvent vides (les lois n'ont pas de
  ministère) : la chaîne vide devient `None` ;
- **lois en double** (loi 2025-391 : deux `JORFTEXT`) : deux actes, comme à la source.

Liens (`lien_acte_loi`) : on lit les liens dont le texte visé est de nature législative
(`NATURES_LIEES` : lois, lois organiques, ordonnances…), dans les deux sens, avec leur type
(`CITATION`, `APPLICATION`, `MODIFIE`…) tels que publiés. Les autres liens (arrêtés, décrets,
codes : 95 % des 125 860 liens de la livraison du 02/11 soir) ne servent pas au site : ils ne
sont pas lus, mais leur nombre est gardé dans l'acte (`nb_liens`, `nb_liens_lus`).

Adresse publique : `https://www.legifrance.gouv.fr/jorf/id/{JORFTEXT…}` (acte, liens, plan) ;
`ID_ELI` du sommaire pour un numéro du JO.
"""
from __future__ import annotations

import pyarrow as pa
from lxml import etree

NOM = "jo_actes"
VERSION = 1
TYPES = ("jorf",)

SENTINELLE = "2999-01-01"
NATURES_LIEES = frozenset({"LOI", "LOI_ORGANIQUE", "LOI_CONSTIT", "LOI_PROGRAMME", "ORDONNANCE",
                           "DECRET_LOI", "CONSTITUTION"})
URL_ACTE = "https://www.legifrance.gouv.fr/jorf/id/{}"

TABLES = {
    "acte_reglementaire": pa.schema([
        ("uid", pa.string()), ("id_jorf", pa.string()), ("livraison", pa.string()),
        ("cid", pa.string()), ("id_eli", pa.string()), ("nature", pa.string()),
        ("titre", pa.string()), ("titre_complet", pa.string()), ("numero", pa.string()),
        ("nor", pa.string()), ("num_parution", pa.string()), ("num_sequence", pa.string()),
        ("origine_publication", pa.string()), ("date_publication", pa.string()),
        ("date_publication_sentinelle", pa.bool_()),
        ("date_signature", pa.string()), ("date_signature_sentinelle", pa.bool_()),
        ("date_signature_source", pa.string()),
        ("page_debut", pa.string()), ("page_fin", pa.string()),
        ("ministere", pa.string()), ("autorite", pa.string()),
        ("signataires", pa.string()), ("signataires_html", pa.string()),
        ("rectificatif", pa.string()), ("nb_liens", pa.int32()), ("nb_liens_lus", pa.int32()),
    ]),
    "lien_acte_loi": pa.schema([
        ("acte", pa.string()), ("livraison", pa.string()), ("rang", pa.int32()),
        ("type_lien", pa.string()), ("sens", pa.string()), ("nature_cible", pa.string()),
        ("cible", pa.string()), ("cible_texte", pa.string()), ("cible_numero", pa.string()),
        ("cible_article", pa.string()), ("cible_nor", pa.string()),
        ("cible_date_signature", pa.string()), ("cible_date_signature_sentinelle", pa.bool_()),
        ("libelle", pa.string()),
    ]),
    "version_acte": pa.schema([
        ("acte", pa.string()), ("livraison", pa.string()), ("rang", pa.int32()),
        ("etat", pa.string()), ("id_version", pa.string()), ("numero", pa.string()),
        ("date_debut", pa.string()), ("date_debut_sentinelle", pa.bool_()),
        ("date_fin", pa.string()), ("date_fin_sentinelle", pa.bool_()),
        ("nb_articles", pa.int32()),
    ]),
    "sommaire_jo": pa.schema([
        ("conteneur", pa.string()), ("livraison", pa.string()), ("rang", pa.int32()),
        ("num_jo", pa.string()), ("titre_jo", pa.string()), ("date_publication", pa.string()),
        ("acte", pa.string()), ("id_jorf", pa.string()), ("titre_sommaire", pa.string()),
        ("rubrique", pa.list_(pa.string())), ("niveau", pa.int32()),
    ]),
    "suppression_jo": pa.schema([
        ("livraison", pa.string()), ("rang", pa.int32()), ("chemin", pa.string()),
        ("dossier", pa.string()), ("id_jorf", pa.string()), ("prefixe", pa.string()),
    ]),
}

NON_LUS = ("ARTICLE", "SECTION_TA")


# -- aides ---------------------------------------------------------------------------------

def _t(x) -> str | None:
    """Texte d'un élément ou d'un attribut ; vide -> None (jamais d'espaces seuls)."""
    if x is None:
        return None
    if not isinstance(x, str):
        x = x.text
    if x is None:
        return None
    x = x.strip()
    return x or None


def _date(x) -> tuple[str | None, bool]:
    """(date, sentinelle) : `2999-01-01` devient (None, True)."""
    x = _t(x)
    if x == SENTINELLE:
        return None, True
    return x, False


def _livraison(chemin: str) -> str | None:
    tete = chemin.split("/", 1)[0]
    return tete if len(tete) == 15 and tete[8] == "-" and tete.replace("-", "").isdigit() else None


def _jorf(id_: str | None) -> str | None:
    return f"jorf:{id_}" if id_ else None


def _texte_html(contenu) -> str | None:
    """Texte d'un bloc HTML de la DILA : un saut de ligne par `<br/>` ou paragraphe, espaces
    resserrés ligne par ligne, lignes vides ôtées."""
    if contenu is None:
        return None
    morceaux = []

    def parcourir(e):
        if e.text:
            morceaux.append(e.text)
        for f in e:
            if isinstance(f.tag, str):          # les commentaires XML ne sont pas du texte
                if f.tag in ("br", "p", "div"):
                    morceaux.append("\n")
                parcourir(f)
                if f.tag in ("p", "div"):
                    morceaux.append("\n")
            if f.tail:
                morceaux.append(f.tail)
    parcourir(contenu)
    lignes = (" ".join(l.split()) for l in "".join(morceaux).split("\n"))
    return "\n".join(l for l in lignes if l) or None


def _html(contenu) -> str | None:
    """Contenu HTML tel que publié (sans la balise `CONTENU` elle-même)."""
    if contenu is None:
        return None
    s = (contenu.text or "") + "".join(etree.tostring(e, encoding="unicode") for e in contenu)
    return s.strip() or None


def _chronicle(r):
    return r.find("META/META_SPEC/META_TEXTE_CHRONICLE")


# -- lecture des trois natures lues --------------------------------------------------------

def _texte_version(r, livraison):
    commun = r.find("META/META_COMMUN")
    ch = _chronicle(r)
    tv = r.find("META/META_SPEC/META_TEXTE_VERSION")
    id_ = _t(commun.find("ID"))
    if not id_:
        raise ValueError("TEXTE_VERSION sans ID")
    acte = _jorf(id_)
    url = URL_ACTE.format(id_)
    g = (lambda p: _t(ch.find(p))) if ch is not None else (lambda p: None)
    date_publi, publi_sent = _date(ch.find("DATE_PUBLI") if ch is not None else None)
    date_sign, sign_sent = _date(ch.find("DATE_TEXTE") if ch is not None else None)
    liens_xml = tv.findall("LIENS/LIEN") if tv is not None else []
    liens = []
    for k, l in enumerate(liens_xml):
        nature = _t(l.get("naturetexte"))
        if nature not in NATURES_LIEES:
            continue
        ds, ds_sent = _date(l.get("datesignatexte"))
        liens.append({
            "acte": acte, "livraison": livraison, "rang": k,
            "type_lien": _t(l.get("typelien")), "sens": _t(l.get("sens")),
            "nature_cible": nature, "cible": _t(l.get("id")),
            "cible_texte": _t(l.get("cidtexte")), "cible_numero": _t(l.get("numtexte")),
            "cible_article": _t(l.get("num")), "cible_nor": _t(l.get("nortexte")),
            "cible_date_signature": ds, "cible_date_signature_sentinelle": ds_sent,
            "libelle": _t("".join(l.itertext())), "prov_url": url,
        })
    gv = (lambda p: _t(tv.find(p))) if tv is not None else (lambda p: None)
    sig = r.find("SIGNATAIRES/CONTENU")
    acte_l = {
        "uid": acte, "id_jorf": id_, "livraison": livraison,
        "cid": g("CID"), "id_eli": _t(commun.find("ID_ELI")), "nature": _t(commun.find("NATURE")),
        "titre": gv("TITRE"), "titre_complet": gv("TITREFULL"), "numero": g("NUM"),
        "nor": g("NOR"), "num_parution": g("NUM_PARUTION"), "num_sequence": g("NUM_SEQUENCE"),
        "origine_publication": g("ORIGINE_PUBLI"),
        "date_publication": date_publi, "date_publication_sentinelle": publi_sent,
        "date_signature": date_sign, "date_signature_sentinelle": sign_sent,
        "date_signature_source": g("DATE_TEXTE"),
        "page_debut": g("PAGE_DEB_PUBLI"), "page_fin": g("PAGE_FIN_PUBLI"),
        "ministere": gv("MINISTERE"), "autorite": gv("AUTORITE"),
        "signataires": _texte_html(sig), "signataires_html": _html(sig),
        "rectificatif": _texte_html(r.find("RECT/CONTENU")),
        "nb_liens": len(liens_xml), "nb_liens_lus": len(liens), "prov_url": url,
    }
    return {"acte_reglementaire": [acte_l], "lien_acte_loi": liens}


def _texte_struct(r, livraison):
    id_ = _t(r.find("META/META_COMMUN/ID"))
    if not id_:
        raise ValueError("TEXTELR sans ID")
    nb_articles = len(r.findall("STRUCT//LIEN_ART"))
    out = []
    for k, v in enumerate(r.findall("VERSIONS/VERSION")):
        lt = v.find("LIEN_TXT")
        deb, deb_s = _date(lt.get("debut") if lt is not None else None)
        fin, fin_s = _date(lt.get("fin") if lt is not None else None)
        out.append({
            "acte": _jorf(id_), "livraison": livraison, "rang": k, "etat": _t(v.get("etat")),
            "id_version": _t(lt.get("id")) if lt is not None else None,
            "numero": _t(lt.get("num")) if lt is not None else None,
            "date_debut": deb, "date_debut_sentinelle": deb_s,
            "date_fin": fin, "date_fin_sentinelle": fin_s,
            "nb_articles": nb_articles, "prov_url": URL_ACTE.format(id_),
        })
    return {"version_acte": out}


def _sommaire(r, livraison):
    commun = r.find("META/META_COMMUN")
    mc = r.find("META/META_SPEC/META_CONTENEUR")
    id_ = _t(commun.find("ID"))
    if not id_:
        raise ValueError("JO sans ID")
    eli = _t(commun.find("ID_ELI"))
    num = _t(mc.find("NUM")) if mc is not None else None
    titre = _t(mc.find("TITRE")) if mc is not None else None
    date = _date(mc.find("DATE_PUBLI"))[0] if mc is not None else None
    out = []

    def parcourir(noeud, chemin):
        for e in noeud:
            if e.tag == "TM":
                parcourir(e, chemin + [_t(e.find("TITRE_TM"))])
            elif e.tag == "LIEN_TXT":
                idt = _t(e.get("idtxt"))
                out.append({
                    "conteneur": id_, "livraison": livraison, "rang": len(out),
                    "num_jo": num, "titre_jo": titre, "date_publication": date,
                    "acte": _jorf(idt), "id_jorf": idt, "titre_sommaire": _t(e.get("titretxt")),
                    "rubrique": [c for c in chemin if c], "niveau": len(chemin),
                    "prov_url": URL_ACTE.format(idt) if idt else eli,
                })
    st = r.find("STRUCTURE_TXT")
    if st is not None:
        parcourir(st, [])
    return {"sommaire_jo": out}


def _suppressions(octets, livraison):
    out = []
    for ligne in octets.decode("utf-8").splitlines():
        ligne = ligne.strip()
        if not ligne:
            continue
        dossier, _, id_ = ligne.rpartition("/")
        out.append({"livraison": livraison, "rang": len(out), "chemin": ligne,
                    "dossier": dossier or None, "id_jorf": id_ or None,
                    "prefixe": id_[:8] if id_.startswith("JORF") else None,
                    "prov_url": URL_ACTE.format(id_) if id_.startswith("JORFTEXT") else None})
    return {"suppression_jo": out}


def lire(m):
    livraison = _livraison(m.chemin)
    if m.chemin.endswith("liste_suppression_jorf.dat"):
        return _suppressions(m.octets, livraison)
    r = etree.fromstring(m.octets)
    if r.tag == "TEXTE_VERSION":
        return _texte_version(r, livraison)
    if r.tag == "TEXTELR":
        return _texte_struct(r, livraison)
    if r.tag == "JO":
        return _sommaire(r, livraison)
    if r.tag in NON_LUS:
        return {}
    raise ValueError(f"racine XML inattendue : {r.tag}")


EXPORT = {
    # Un texte redélivré est une nouvelle version du même membre : la dernière livraison fait foi.
    "acte_reglementaire": {"type": "acte_reglementaire", "cle": ["uid"],
                           "ids": {"acte": "uid"}, "date": "date_publication"},
    "lien_acte_loi": {"type": "lien_acte_loi", "cle": ["acte", "rang"],
                      "ids": {"acte": "acte", "autre": "cible_texte"}, "date": None},
    "version_acte": {"type": "version_acte", "cle": ["acte", "rang"],
                     "ids": {"acte": "acte", "autre": "id_version"}, "date": "date_debut"},
    "sommaire_jo": {"type": "sommaire_jo", "cle": ["conteneur", "rang"],
                    "ids": {"acte": "acte", "autre": "conteneur"}, "date": "date_publication"},
    # Chaque livraison a sa liste de suppressions : toutes sont des faits.
    "suppression_jo": {"type": "suppression_jo", "cle": ["livraison", "rang"],
                       "ids": {"autre": "id_jorf"}, "date": None, "toutes_versions": True},
}
