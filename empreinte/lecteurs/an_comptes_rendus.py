"""Comptes rendus de séance de l'Assemblée, Syceron (cahier 3.1.5) : compte rendu et paragraphes.

Un membre de l'archive = un compte rendu XML (`xml/compteRendu/{uid}.xml`, 1,2 Mo au plus en
XVIIe). Il est lu en entier par lxml (sans entités externes ni réseau), un membre à la fois :
la mémoire reste bornée par le plus gros compte rendu.

Une ligne d'`intervention` par élément `<paragraphe>`, identifiée par `id_syceron` (unique dans
toute l'archive, et ancre de la page publique). Le lecteur **lit, il n'attribue pas** :
- l'orateur est restitué tel que la source l'écrit : `orateur` = l'attribut `id_acteur` (déjà
  préfixé `PA` par la source), y compris `PA0`, les identifiants négatifs (`PA-125869`) et
  l'identifiant de repli ; `orateurs` = tous les `<orateur>` du paragraphe (id avec son `PA`
  rétabli, nom affiché, qualité), même quand le nom affiché ne correspond pas à l'identifiant ;
- la présidence n'est pas déduite : `roledebat` est restitué tel quel (il manque sur une partie
  des paragraphes de présidence) ; la règle R-ORATEUR décide ;
- le point d'ordre du jour : `valeur_ptsodj` du paragraphe, et `points`, la chaîne des
  `<point nivpoint>` reconstituée dans l'ordre du document (les points sont surtout des frères
  successifs : un point de niveau n remplace les points de niveau ≥ n déjà ouverts). Les
  suspensions (`nivpoint="99"`) sont des points comme les autres pour la source : elles sont
  gardées, avec leur `code_grammaire` ;
- `ordre_absolu_seance` est restitué, mais la republication le renumérote : ce n'est pas une clé.

Le texte est celui des nœuds texte du `<texte>` : les espaces de mise en forme du XML sont
réduits à un seul, `<br/>` devient un saut de ligne, les balises d'italique et d'exposant sont
ôtées (leur texte reste). Les espaces insécables de la source sont gardés.
"""
import re

import pyarrow as pa
from lxml import etree

from ..lecture import pa_id

NOM = "an_comptes_rendus"
VERSION = 1
TYPES = ("comptes_rendus",)

ORATEUR = pa.struct([("id", pa.string()), ("nom", pa.string()), ("qualite", pa.string())])
POINT = pa.struct([("niv", pa.int32()), ("nivpoint", pa.string()), ("id_syceron", pa.string()),
                   ("code_grammaire", pa.string()), ("valeur_ptsodj", pa.string()),
                   ("titre", pa.string())])
TABLES = {
    "compte_rendu": pa.schema([
        ("uid", pa.string()), ("seance", pa.string()), ("session", pa.string()),
        ("date_seance", pa.string()), ("date", pa.string()), ("date_seance_jour", pa.string()),
        ("num_seance", pa.string()), ("num_seance_jour", pa.string()),
        ("type_assemblee", pa.string()), ("legislature", pa.string()),
        ("statut", pa.string()), ("validite", pa.string()), ("diffusion", pa.string()),
        ("version", pa.string()), ("heure_generation", pa.string()),
        ("nom_fichier_jo", pa.string()), ("president_seance", pa.string()),
        ("nb_paragraphes", pa.int32()),
    ]),
    "intervention": pa.schema([
        ("compte_rendu", pa.string()), ("seance", pa.string()), ("date", pa.string()),
        ("id_syceron", pa.string()), ("ordre_absolu_seance", pa.int32()),
        ("id_preparation", pa.string()), ("ordinal_prise", pa.string()),
        ("orateur", pa.string()), ("orateur_nom", pa.string()), ("qualite", pa.string()),
        ("orateurs", pa.list_(ORATEUR)), ("id_mandat", pa.string()),
        ("id_nomination_oe", pa.string()), ("id_nomination_op", pa.string()),
        ("roledebat", pa.string()), ("code_grammaire", pa.string()), ("code_style", pa.string()),
        ("type_debat", pa.string()),
        ("extraction_orateur", pa.string()), ("extraction_nom", pa.string()),
        ("art", pa.string()), ("adt", pa.string()), ("ssadt", pa.string()),
        ("uid_adt", pa.string()), ("decision", pa.string()),
        ("valeur_ptsodj", pa.string()), ("points", pa.list_(POINT)),
        ("stime", pa.string()), ("texte", pa.string()),
    ]),
}

NS = "{http://schemas.assemblee-nationale.fr/referentiel}"
_PARSEUR = etree.XMLParser(resolve_entities=False, no_network=True, huge_tree=True,
                           load_dtd=False)
_ESPACES = re.compile(r"[ \t\r\n]+")     # pas \s : l'espace insécable de la source reste
URL = "https://www.assemblee-nationale.fr/dyn/{leg}/comptes-rendus/seance/{uid}"


def _t(el, tag):
    """Texte d'un enfant simple, None s'il manque ou s'il est vide."""
    if el is None:
        return None
    x = el.find(NS + tag)
    if x is None:
        return None
    s = "".join(x.itertext()).strip()
    return s or None


def _texte(el):
    """Texte d'un élément `<texte>` : espaces de mise en forme réduits, `<br/>` → saut de ligne."""
    if el is None:
        return None
    morceaux = []

    def parcourir(e):
        if e.text:
            morceaux.append(_ESPACES.sub(" ", e.text))
        for c in e:
            if isinstance(c.tag, str):
                if c.tag == NS + "br":
                    morceaux.append("\n")
                else:
                    parcourir(c)
            if c.tail:
                morceaux.append(_ESPACES.sub(" ", c.tail))

    parcourir(el)
    s = "\n".join(ligne.strip(" ") for ligne in "".join(morceaux).split("\n")).strip()
    return s or None


def _int(x):
    try:
        return int(x)
    except (TypeError, ValueError):
        return None


def _date_iso(d):
    """`AAAAMMJJHHMMSSmmm` → `AAAA-MM-JJ` (forme seulement)."""
    if d and len(d) >= 8 and d[:8].isdigit():
        return f"{d[:4]}-{d[4:6]}-{d[6:8]}"
    return None


def lire(m):
    racine = etree.fromstring(m.octets, _PARSEUR)
    uid = _t(racine, "uid")
    seance = _t(racine, "seanceRef")
    md = racine.find(NS + "metadonnees")
    leg = _t(md, "legislature")
    date_seance = _t(md, "dateSeance")
    date = _date_iso(date_seance)
    sommaire = md.find(NS + "sommaire") if md is not None else None
    url = URL.format(leg=leg, uid=uid) if leg and uid else None

    interventions = []
    contenu = racine.find(NS + "contenu")
    ouverts: dict[int, dict] = {}       # points ouverts, par niveau
    if contenu is not None:
        for el in contenu.iter(NS + "point", NS + "paragraphe"):
            a = el.attrib
            if el.tag == NS + "point":
                niv = _int(a.get("nivpoint"))
                n = niv if niv is not None else 0
                ouverts = {k: v for k, v in ouverts.items() if k < n}
                ouverts[n] = {"niv": niv, "nivpoint": a.get("nivpoint"),
                              "id_syceron": a.get("id_syceron"),
                              "code_grammaire": a.get("code_grammaire"),
                              "valeur_ptsodj": a.get("valeur_ptsodj"),
                              "titre": _texte(el.find(NS + "texte"))}
                continue
            orateurs = [{"id": pa_id(_t(o, "id")), "nom": _t(o, "nom"), "qualite": _t(o, "qualite")}
                        for o in el.findall(NS + "orateurs/" + NS + "orateur")]
            parent = el.getparent()
            extraction = parent if parent is not None and parent.tag == NS + "interExtraction" else None
            texte_el = el.find(NS + "texte")
            ids = a.get("id_syceron")
            interventions.append({
                "compte_rendu": uid, "seance": seance, "date": date,
                "id_syceron": ids, "ordre_absolu_seance": _int(a.get("ordre_absolu_seance")),
                "id_preparation": a.get("id_preparation"), "ordinal_prise": a.get("ordinal_prise"),
                "orateur": a.get("id_acteur") or None,
                "orateur_nom": orateurs[0]["nom"] if orateurs else None,
                "qualite": orateurs[0]["qualite"] if orateurs else None,
                "orateurs": orateurs, "id_mandat": a.get("id_mandat") or None,
                "id_nomination_oe": a.get("id_nomination_oe"),
                "id_nomination_op": a.get("id_nomination_op"),
                "roledebat": a.get("roledebat") or None,
                "code_grammaire": a.get("code_grammaire"), "code_style": a.get("code_style"),
                "type_debat": a.get("type_debat") or None,
                "extraction_orateur": extraction.get("id_acteur") if extraction is not None else None,
                "extraction_nom": extraction.get("nom_orateur") if extraction is not None else None,
                "art": a.get("art") or None, "adt": a.get("adt") or None,
                "ssadt": a.get("ssadt") or None, "uid_adt": a.get("uid_adt") or None,
                "decision": a.get("decision") or None,
                "valeur_ptsodj": a.get("valeur_ptsodj"),
                "points": [ouverts[k] for k in sorted(ouverts)],
                "stime": texte_el.get("stime") if texte_el is not None else None,
                "texte": _texte(texte_el),
                "prov_url": f"{url}#{ids}" if url and ids else None,
            })
    compte_rendu = {
        "uid": uid, "seance": seance, "session": _t(racine, "sessionRef"),
        "date_seance": date_seance, "date": date, "date_seance_jour": _t(md, "dateSeanceJour"),
        "num_seance": _t(md, "numSeance"), "num_seance_jour": _t(md, "numSeanceJour"),
        "type_assemblee": _t(md, "typeAssemblee"), "legislature": leg,
        "statut": _t(md, "etat"), "validite": _t(md, "validite"), "diffusion": _t(md, "diffusion"),
        "version": _t(md, "version"), "heure_generation": _t(md, "heureGeneration"),
        "nom_fichier_jo": _t(md, "nomFichierJo"),
        "president_seance": _t(sommaire, "presidentSeance"),
        "nb_paragraphes": len(interventions),
        "prov_url": url,
    }
    return {"compte_rendu": [compte_rendu], "intervention": interventions}


EXPORT = {
    "compte_rendu": {"type": "compte_rendu", "cle": ["uid"],
                     "ids": {"compte_rendu": "uid", "reunion": "seance"}, "date": "date"},
    # Clé du modèle (1.2.2) : an:<uid du compte rendu>#<id_syceron>.
    "intervention": {"type": "intervention", "cle": ["compte_rendu", "id_syceron"],
                     "ids": {"compte_rendu": "compte_rendu", "reunion": "seance",
                             "acteur": "orateur", "autre": "id_syceron"},
                     "date": "date"},
}
