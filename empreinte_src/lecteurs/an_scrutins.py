"""Scrutins de l'Assemblée (cahier 3.1.2 ; mesures `an-scrutins-dossiers.md`, section 2).

Un membre est, selon la législature :
- XVe-XVIIe : un JSON par scrutin, `{"scrutin": {...}}` ;
- XIVe : un seul fichier pour toute la législature, `{"scrutins": {"scrutin": [...]}}`.

Ce que le lecteur restitue, champ par champ, sans rien déduire :
- `scrutin` : l'en-tête, les totaux officiels et le mode de publication des votes ;
- `position_vote` : une ligne par votant **nommé** dans `decompteNominatif`. En mode
  `DecompteDissidentsPositionGroupe` (710 scrutins de la XIVe), seuls les dissidents sont
  nommés : les autres membres n'ont pas de ligne, leur position n'est jamais déduite de celle
  du groupe (règle R-NOMINATIF, tranche suivante) ;
- `mise_au_point` : les positions déclarées après coup, gardées à part (elles ne remplacent
  pas la position), y compris le sous-bloc `dysfonctionnement` ;
- `decompte_groupe` : par ligne de groupe, les décomptes et la position majoritaire publiés.

Pièges traités :
- trois jeux de clés pour les listes nominatives : `pour`/`contre`/`abstentions`/`nonVotants`
  (XIVe), `pours`/`contres`/`abstentions`/`nonVotants` (XVe-XVIIe), `pour`/`contre`/
  `abstention`/`nonVotant` (Congrès XVIe), et les mêmes variantes dans `decompteVoix` et
  `miseAuPoint` ; une clé inconnue qui porte des votants fait échouer la lecture (rien n'est
  perdu en silence) ;
- un votant seul est un dictionnaire, plusieurs une liste ;
- XIVe : `nonVotants` vaut la chaîne `"0"` quand il n'y a personne ;
- `miseAuPoint` : `null` (XIVe), ou présent sur tous les scrutins (XVe-XVIIe) avec des listes
  de deux éléments souvent `[null, null]` ; « bloc présent » n'est pas « mise au point » ;
- groupe `PO0` (14 scrutins XVIIe) : plusieurs lignes de groupe portent le même organe
  `PO0` dans un scrutin ; elles sont gardées telles quelles et distinguées par `occurrence` ;
- `parDelegation` est une chaîne `"true"`/`"false"` (absente en XIVe : `None`) ;
- identifiant de personne rétabli avec son préfixe `PA` s'il manquait ;
- le type se lit par son **code** (`codeTypeVote`) ; le libellé est gardé tel quel.

Adresse publique : `https://www.assemblee-nationale.fr/dyn/{leg}/scrutins/{numero}` pour les
scrutins de l'Assemblée (`VTAN…`) ; aucune pour le Congrès (`VTCG…`), dont le numéro est
celui d'une autre série.
"""
import orjson
import pyarrow as pa

from ..lecture import est_nil, liste, pa_id, val

NOM = "an_scrutins"
VERSION = 1
TYPES = ("scrutins",)

TABLES = {
    "scrutin": pa.schema([
        ("uid", pa.string()), ("legislature", pa.int32()), ("numero", pa.int32()),
        ("date", pa.string()), ("seance", pa.string()), ("session", pa.string()),
        ("organe", pa.string()), ("quantieme_jour_seance", pa.int32()), ("lieu_vote", pa.string()),
        ("code_type", pa.string()), ("libelle_type", pa.string()), ("type_majorite", pa.string()),
        ("titre", pa.string()), ("objet", pa.string()), ("demandeur", pa.string()),
        ("sort_code", pa.string()), ("sort_libelle", pa.string()), ("annonce", pa.string()),
        ("mode_publication", pa.string()),
        ("nombre_votants", pa.int32()), ("suffrages_exprimes", pa.int32()),
        ("suffrages_requis", pa.int32()),
        ("pour", pa.int32()), ("contre", pa.int32()), ("abstentions", pa.int32()),
        ("non_votants", pa.int32()), ("non_votants_volontaires", pa.int32()),
        ("dossier_ref", pa.string()), ("dossier_libelle", pa.string()),
        ("reference_legislative", pa.string()),
    ]),
    "position_vote": pa.schema([
        ("scrutin", pa.string()), ("acteur", pa.string()), ("mandat", pa.string()),
        ("groupe", pa.string()), ("position", pa.string()), ("par_delegation", pa.bool_()),
        ("cause", pa.string()), ("num_place", pa.string()), ("cle_source", pa.string()),
    ]),
    "mise_au_point": pa.schema([
        ("scrutin", pa.string()), ("acteur", pa.string()), ("mandat", pa.string()),
        ("position", pa.string()), ("dysfonctionnement", pa.bool_()),
        ("par_delegation", pa.bool_()), ("num_place", pa.string()), ("cle_source", pa.string()),
        ("element", pa.int32()),
    ]),
    "decompte_groupe": pa.schema([
        ("scrutin", pa.string()), ("organe", pa.string()), ("occurrence", pa.int32()),
        ("rang", pa.int32()), ("nombre_membres", pa.int32()),
        ("position_majoritaire", pa.string()),
        ("pour", pa.int32()), ("contre", pa.int32()), ("abstentions", pa.int32()),
        ("non_votants", pa.int32()), ("non_votants_volontaires", pa.int32()),
    ]),
}

# Toutes les clés de liste rencontrées (XIVe, XVe-XVIIe, Congrès XVIe) -> position lue.
POSITIONS = {
    "pours": "pour", "pour": "pour",
    "contres": "contre", "contre": "contre",
    "abstentions": "abstention", "abstention": "abstention",
    "nonVotants": "non_votant", "nonVotant": "non_votant",
    "nonVotantsVolontaires": "non_votant_volontaire", "nonVotantVolontaire": "non_votant_volontaire",
}


def adresse(uid: str, legislature, numero) -> str | None:
    if not uid.startswith("VTAN") or legislature is None or numero is None:
        return None
    return f"https://www.assemblee-nationale.fr/dyn/{legislature}/scrutins/{numero}"


def entier(x) -> int | None:
    """Nombre écrit en chaîne par la source ; None si absent. Une valeur non numérique lève."""
    x = val(x)
    if x is None or x == "":
        return None
    return int(x)


def booleen(x) -> bool | None:
    x = val(x)
    if x is None:
        return None
    if isinstance(x, bool):
        return x
    if x in ("true", "false"):
        return x == "true"
    raise ValueError(f"booléen inattendu : {x!r}")


def premiere(d: dict, *cles):
    """Valeur de la première clé présente (variantes singulier/pluriel)."""
    for k in cles:
        if k in d:
            return d[k]
    return None


def votants(bloc) -> list[dict]:
    """Votants d'un bloc de liste nominative. Un bloc vide est `null`, `{"@xsi:nil"}`, ou un
    compte en chaîne (`"0"` en XIVe) : aucun votant nommé."""
    if bloc is None or est_nil(bloc):
        return []
    if isinstance(bloc, str):
        if bloc.strip().isdigit():
            return []
        raise ValueError(f"bloc nominatif inattendu : {bloc!r}")
    if isinstance(bloc, list):
        out = []
        for b in bloc:
            out.extend(votants(b))
        return out
    if isinstance(bloc, dict):
        inconnues = set(bloc) - {"votant"}
        if inconnues:
            raise ValueError(f"clés inattendues dans un bloc nominatif : {sorted(inconnues)}")
        return [v for v in liste(bloc.get("votant")) if v is not None]
    raise ValueError(f"bloc nominatif inattendu : {type(bloc).__name__}")


def position_de(cle: str, bloc) -> str | None:
    """Position lue pour une clé de liste ; une clé inconnue qui porte des votants lève."""
    if cle in POSITIONS:
        return POSITIONS[cle]
    if votants(bloc):
        raise ValueError(f"clé de liste nominative inconnue : {cle!r}")
    return None


def scrutins_du_membre(octets: bytes) -> list[dict]:
    d = orjson.loads(octets)
    if "scrutin" in d:                              # XVe-XVIIe : un scrutin par fichier
        return [d["scrutin"]]
    if "scrutins" in d:                             # XIVe : toute la législature
        return liste((d["scrutins"] or {}).get("scrutin"))
    raise ValueError(f"forme de membre inconnue : clés {sorted(d)[:5]}")


def lire_scrutin(s: dict, out: dict):
    uid = val(s["uid"])
    leg = entier(s.get("legislature"))
    numero = entier(s.get("numero"))
    url = adresse(uid, leg, numero)
    tv = s.get("typeVote") or {}
    sort = s.get("sort") or {}
    sv = s.get("syntheseVote") or {}
    dc = sv.get("decompte") or {}
    obj = s.get("objet") or {}
    dl = obj.get("dossierLegislatif") or {}
    if est_nil(dl):
        dl = {}
    dem = s.get("demandeur") or {}
    ref_leg = val(obj.get("referenceLegislative")) or val(dem.get("referenceLegislative"))
    out["scrutin"].append({
        "uid": uid, "legislature": leg, "numero": numero,
        "date": val(s.get("dateScrutin")), "seance": val(s.get("seanceRef")),
        "session": val(s.get("sessionRef")), "organe": val(s.get("organeRef")),
        "quantieme_jour_seance": entier(s.get("quantiemeJourSeance")),
        "lieu_vote": val(s.get("lieuVote")),
        "code_type": val(tv.get("codeTypeVote")), "libelle_type": val(tv.get("libelleTypeVote")),
        "type_majorite": val(tv.get("typeMajorite")),
        "titre": val(s.get("titre")), "objet": val(obj.get("libelle")),
        "demandeur": val(dem.get("texte")),
        "sort_code": val(sort.get("code")), "sort_libelle": val(sort.get("libelle")),
        "annonce": val(sv.get("annonce")),
        "mode_publication": val(s.get("modePublicationDesVotes")),
        "nombre_votants": entier(sv.get("nombreVotants")),
        "suffrages_exprimes": entier(sv.get("suffragesExprimes")),
        "suffrages_requis": entier(sv.get("nbrSuffragesRequis")),
        "pour": entier(premiere(dc, "pour", "pours")),
        "contre": entier(premiere(dc, "contre", "contres")),
        "abstentions": entier(premiere(dc, "abstentions", "abstention")),
        "non_votants": entier(premiere(dc, "nonVotants", "nonVotant")),
        "non_votants_volontaires": entier(premiere(dc, "nonVotantsVolontaires", "nonVotantVolontaire")),
        "dossier_ref": val(dl.get("dossierRef")), "dossier_libelle": val(dl.get("libelle")),
        "reference_legislative": ref_leg if isinstance(ref_leg, str) else
        (orjson.dumps(ref_leg).decode() if ref_leg is not None else None),
        "prov_url": url,
    })

    # Groupes : décomptes publiés et listes nominatives.
    ventil = (s.get("ventilationVotes") or {}).get("organe") or {}
    groupes = liste((ventil.get("groupes") or {}).get("groupe"))
    vus: dict[str, int] = {}
    for rang, g in enumerate(groupes):
        organe = val(g.get("organeRef"))
        occ = vus.get(organe, 0)
        vus[organe] = occ + 1
        vote = g.get("vote") or {}
        dv = vote.get("decompteVoix") or {}
        out["decompte_groupe"].append({
            "scrutin": uid, "organe": organe, "occurrence": occ, "rang": rang,
            "nombre_membres": entier(g.get("nombreMembresGroupe")),
            "position_majoritaire": val(vote.get("positionMajoritaire")),
            "pour": entier(premiere(dv, "pour", "pours")),
            "contre": entier(premiere(dv, "contre", "contres")),
            "abstentions": entier(premiere(dv, "abstentions", "abstention")),
            "non_votants": entier(premiere(dv, "nonVotants", "nonVotant")),
            "non_votants_volontaires": entier(premiere(dv, "nonVotantsVolontaires",
                                                       "nonVotantVolontaire")),
            "prov_url": url,
        })
        dn = vote.get("decompteNominatif") or {}
        if est_nil(dn):
            dn = {}
        for cle, bloc in dn.items():
            pos = position_de(cle, bloc)
            for v in votants(bloc):
                out["position_vote"].append({
                    "scrutin": uid, "acteur": pa_id(v.get("acteurRef")),
                    "mandat": val(v.get("mandatRef")), "groupe": organe, "position": pos,
                    "par_delegation": booleen(v.get("parDelegation")),
                    "cause": val(v.get("causePositionVote")),
                    "num_place": val(v.get("numPlace")), "cle_source": cle, "prov_url": url,
                })

    # Mises au point (et dysfonctionnements), gardées à part.
    map_ = s.get("miseAuPoint")
    if map_ is None or est_nil(map_):
        return
    for cle, bloc in map_.items():
        if cle == "dysfonctionnement":
            sous = bloc if isinstance(bloc, dict) and not est_nil(bloc) else {}
            paires = [(k2, b2, True) for k2, b2 in sous.items()]
        else:
            paires = [(cle, bloc, False)]
        for k, b, dysf in paires:
            pos = position_de(k, b)
            # XVe-XVIIe : certains blocs sont des listes de deux éléments (souvent
            # [null, null]) ; le rang de l'élément est gardé, son sens n'est pas documenté.
            elements = list(enumerate(b)) if isinstance(b, list) else [(None, b)]
            for e, be in elements:
                for v in votants(be):
                    out["mise_au_point"].append({
                        "scrutin": uid, "acteur": pa_id(v.get("acteurRef")),
                        "mandat": val(v.get("mandatRef")), "position": pos,
                        "dysfonctionnement": dysf,
                        "par_delegation": booleen(v.get("parDelegation")),
                        "num_place": val(v.get("numPlace")), "cle_source": k, "element": e,
                        "prov_url": url,
                    })


def lire(m):
    out = {t: [] for t in TABLES}
    for s in scrutins_du_membre(m.octets):
        lire_scrutin(s, out)
    return out


EXPORT = {
    "scrutin": {"type": "scrutin", "cle": ["uid"],
                "ids": {"scrutin": "uid", "organe": "organe", "reunion": "seance",
                        "dossier": "dossier_ref"},
                "date": "date"},
    "position_vote": {"type": "position_vote", "cle": ["scrutin", "acteur"],
                      "ids": {"scrutin": "scrutin", "acteur": "acteur", "mandat": "mandat",
                              "organe": "groupe"},
                      "date": None},
    "mise_au_point": {"type": "mise_au_point",
                      "cle": ["scrutin", "acteur", "dysfonctionnement", "position"],
                      "ids": {"scrutin": "scrutin", "acteur": "acteur", "mandat": "mandat"},
                      "date": None},
    "decompte_groupe": {"type": "decompte_groupe", "cle": ["scrutin", "organe", "occurrence"],
                        "ids": {"scrutin": "scrutin", "organe": "organe"}, "date": None},
}
