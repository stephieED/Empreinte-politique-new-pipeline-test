"""Acteurs, organes, mandats et déports de l'Assemblée (archive AMO30, cahier 3.1.1).

Un fichier JSON par objet : `json/acteur/PA….json` (l'acteur et **tous** ses mandats),
`json/organe/PO….json`, `json/deport/DPTR….json`. Le lecteur restitue la source champ par
champ, sans règle ni liaison (doc. 1, 1.6) :

- l'état civil et la profession d'un acteur → `identite_source` ;
- chacun de ses mandats → `mandat` (une ligne par mandat ; les dates, la qualité, la cause de
  fin, la `datePriseFonction` et le siège sont ceux de la source, tels quels : la suspension
  et la reprise sont reconstruites par les règles, pas ici) ;
- un organe → `organe` (avec la position politique déclarée d'un groupe, `null` pour tous
  les groupes de la XVIIe à la date des mesures, et la succession `organePrecedentRef`) ;
- un déport → `deport`.

Pièges de forme gérés (mesures `an-acteurs.md`, 2.5) : un objet seul est un dictionnaire,
plusieurs sont une liste (`mandats.mandat`, `organes.organeRef` des missions auprès de deux
ministères, `suppleants.suppleant`, `listePays.paysRef`) ; le vide s'écrit `null`, chaîne vide
ou `{"@xsi:nil": "true"}` (date de décès, trigramme, lieu de naissance, profession…) et
devient toujours `None` ; l'uid d'un acteur est un objet (`uid.#text`), celui d'un organe une
chaîne ; un identifiant de personne sans `PA` reçoit son préfixe.

**Jamais lus** : les collaborateurs parlementaires (`mandat.collaborateurs`, règle 3), les
noms des secrétaires d'un organe (`organe.secretariat`) et les adresses de l'acteur
(postales, électroniques, réseaux) : données de personnes qui restent dans l'entrepôt.

Aucune adresse publique n'est donnée par l'archive ni vérifiée dans les données : `prov_url`
reste vide.
"""
import orjson
import pyarrow as pa

from ..lecture import liste, pa_id, val

NOM = "an_acteurs"
VERSION = 1
TYPES = ("acteurs_organes",)

_SUPPLEANT = pa.struct([("suppleant", pa.string()), ("date_debut", pa.string()),
                        ("date_fin", pa.string())])

TABLES = {
    "identite_source": pa.schema([
        ("uid", pa.string()), ("civilite", pa.string()), ("prenom", pa.string()),
        ("nom", pa.string()), ("nom_alpha", pa.string()), ("trigramme", pa.string()),
        ("date_naissance", pa.string()), ("ville_naissance", pa.string()),
        ("departement_naissance", pa.string()), ("pays_naissance", pa.string()),
        ("date_deces", pa.string()), ("profession", pa.string()),
        ("categorie_socio_pro", pa.string()), ("famille_socio_pro", pa.string()),
        ("uri_hatvp", pa.string()),
    ]),
    "organe": pa.schema([
        ("uid", pa.string()), ("type_organe", pa.string()), ("type_xsi", pa.string()),
        ("libelle", pa.string()), ("libelle_edition", pa.string()),
        ("libelle_abrege", pa.string()), ("sigle", pa.string()),
        ("date_debut", pa.string()), ("date_fin", pa.string()), ("date_agrement", pa.string()),
        ("legislature", pa.string()), ("regime", pa.string()), ("regime_juridique", pa.string()),
        ("organe_parent", pa.string()), ("organe_precedent", pa.string()),
        ("position_politique", pa.string()), ("preseance", pa.string()),
        ("numero", pa.string()), ("chambre", pa.string()), ("couleur", pa.string()),
        ("site_internet", pa.string()), ("nombre_reunions_annuelles", pa.string()),
        ("departement_code", pa.string()), ("departement_nature", pa.string()),
        ("departement", pa.string()), ("region", pa.string()), ("region_type", pa.string()),
        ("pays", pa.list_(pa.string())),
    ]),
    "mandat": pa.schema([
        ("uid", pa.string()), ("acteur", pa.string()), ("type_mandat", pa.string()),
        ("type_organe", pa.string()), ("organe", pa.string()),
        ("organes", pa.list_(pa.string())), ("legislature", pa.string()),
        ("qualite_code", pa.string()), ("qualite", pa.string()), ("qualite_sexe", pa.string()),
        ("date_debut", pa.string()), ("date_fin", pa.string()),
        ("date_publication", pa.string()), ("preseance", pa.string()),
        ("nomination_principale", pa.string()), ("libelle", pa.string()),
        ("chambre", pa.string()),
        ("mission_precedente", pa.string()), ("mission_suivante", pa.string()),
        # election (mandats parlementaires)
        ("cause_mandat", pa.string()), ("circonscription", pa.string()),
        ("region", pa.string()), ("region_type", pa.string()), ("departement", pa.string()),
        ("num_departement", pa.string()), ("num_circo", pa.string()),
        # mandature (mandats parlementaires)
        ("date_prise_fonction", pa.string()), ("cause_fin", pa.string()),
        ("premiere_election", pa.string()), ("place_hemicycle", pa.string()),
        ("mandat_remplace", pa.string()),
        ("suppleants", pa.list_(_SUPPLEANT)),
    ]),
    "deport": pa.schema([
        ("uid", pa.string()), ("acteur", pa.string()), ("legislature", pa.string()),
        ("chronotag", pa.string()), ("date_creation", pa.string()),
        ("date_publication", pa.string()),
        ("portee_code", pa.string()), ("portee", pa.string()),
        ("lecture_code", pa.string()), ("lecture", pa.string()),
        ("instance_code", pa.string()), ("instance", pa.string()),
        ("cible_type_code", pa.string()), ("cible_type", pa.string()),
        ("cible_reference_textuelle", pa.string()), ("cible_references", pa.string()),
        ("explication", pa.string()),
    ]),
}


def v(x):
    """Valeur simple ; les trois écritures du vide (null, "", xsi:nil) deviennent None."""
    x = val(x)
    if x is None or (isinstance(x, str) and x == ""):
        return None
    if isinstance(x, (dict, list)):
        raise ValueError(f"valeur simple attendue, reçu {type(x).__name__} : {str(x)[:80]}")
    return str(x)


def d(x) -> dict:
    """Sous-objet : {} pour un vide (null ou xsi:nil)."""
    x = val(x)
    if x is None:
        return {}
    if not isinstance(x, dict):
        raise ValueError(f"objet attendu, reçu {type(x).__name__} : {str(x)[:80]}")
    return x


def _acteur(a: dict) -> dict[str, list[dict]]:
    uid = pa_id(a.get("uid"))
    if uid is None:
        raise ValueError("acteur sans uid")
    ec = d(a.get("etatCivil"))
    ident, nais = d(ec.get("ident")), d(ec.get("infoNaissance"))
    prof = d(a.get("profession"))
    soc = d(prof.get("socProcINSEE"))
    mandats = [_mandat(m) for m in liste(d(a.get("mandats")).get("mandat"))]
    identite = {
        "uid": uid, "civilite": v(ident.get("civ")), "prenom": v(ident.get("prenom")),
        "nom": v(ident.get("nom")), "nom_alpha": v(ident.get("alpha")),
        "trigramme": v(ident.get("trigramme")),
        "date_naissance": v(nais.get("dateNais")), "ville_naissance": v(nais.get("villeNais")),
        "departement_naissance": v(nais.get("depNais")),
        "pays_naissance": v(nais.get("paysNais")), "date_deces": v(ec.get("dateDeces")),
        "profession": v(prof.get("libelleCourant")),
        "categorie_socio_pro": v(soc.get("catSocPro")),
        "famille_socio_pro": v(soc.get("famSocPro")),
        "uri_hatvp": v(a.get("uri_hatvp")), "prov_url": None,
    }
    return {"identite_source": [identite], "mandat": mandats}


def _mandat(m: dict) -> dict:
    # `collaborateurs` n'est jamais lu (règle 3).
    qual = d(m.get("infosQualite"))
    organes = [v(o) for o in liste(d(m.get("organes")).get("organeRef"))]
    organes = [o for o in organes if o]
    el = d(m.get("election"))
    lieu = d(el.get("lieu"))
    mt = d(m.get("mandature"))
    supp = [{"suppleant": pa_id(s.get("suppleantRef")), "date_debut": v(s.get("dateDebut")),
             "date_fin": v(s.get("dateFin"))}
            for s in liste(d(m.get("suppleants")).get("suppleant"))]
    uid = v(m.get("uid"))
    if uid is None:
        raise ValueError("mandat sans uid")
    return {
        "uid": uid, "acteur": pa_id(m.get("acteurRef")), "type_mandat": v(m.get("@xsi:type")),
        "type_organe": v(m.get("typeOrgane")), "organe": organes[0] if organes else None,
        "organes": organes, "legislature": v(m.get("legislature")),
        "qualite_code": v(qual.get("codeQualite")), "qualite": v(qual.get("libQualite")),
        "qualite_sexe": v(qual.get("libQualiteSex")),
        "date_debut": v(m.get("dateDebut")), "date_fin": v(m.get("dateFin")),
        "date_publication": v(m.get("datePublication")), "preseance": v(m.get("preseance")),
        "nomination_principale": v(m.get("nominPrincipale")), "libelle": v(m.get("libelle")),
        "chambre": v(m.get("chambre")),
        "mission_precedente": v(m.get("missionPrecedenteRef")),
        "mission_suivante": v(m.get("missionSuivanteRef")),
        "cause_mandat": v(el.get("causeMandat")), "circonscription": v(el.get("refCirconscription")),
        "region": v(lieu.get("region")), "region_type": v(lieu.get("regionType")),
        "departement": v(lieu.get("departement")), "num_departement": v(lieu.get("numDepartement")),
        "num_circo": v(lieu.get("numCirco")),
        "date_prise_fonction": v(mt.get("datePriseFonction")), "cause_fin": v(mt.get("causeFin")),
        "premiere_election": v(mt.get("premiereElection")),
        "place_hemicycle": v(mt.get("placeHemicycle")),
        "mandat_remplace": v(mt.get("mandatRemplaceRef")),
        "suppleants": supp, "prov_url": None,
    }


def _organe(o: dict) -> dict:
    # `secretariat` (noms des secrétaires) n'est pas lu.
    vi = d(o.get("viMoDe"))
    lieu = d(o.get("lieu"))
    dep, reg = d(lieu.get("departement")), d(lieu.get("region"))
    pays = [v(p) for p in liste(d(o.get("listePays")).get("paysRef"))]
    uid = v(o.get("uid"))
    if uid is None:
        raise ValueError("organe sans uid")
    return {
        "uid": uid, "type_organe": v(o.get("codeType")), "type_xsi": v(o.get("@xsi:type")),
        "libelle": v(o.get("libelle")), "libelle_edition": v(o.get("libelleEdition")),
        "libelle_abrege": v(o.get("libelleAbrege")), "sigle": v(o.get("libelleAbrev")),
        "date_debut": v(vi.get("dateDebut")), "date_fin": v(vi.get("dateFin")),
        "date_agrement": v(vi.get("dateAgrement")), "legislature": v(o.get("legislature")),
        "regime": v(o.get("regime")), "regime_juridique": v(o.get("regimeJuridique")),
        "organe_parent": v(o.get("organeParent")),
        "organe_precedent": v(o.get("organePrecedentRef")),
        "position_politique": v(o.get("positionPolitique")), "preseance": v(o.get("preseance")),
        "numero": v(o.get("numero")), "chambre": v(o.get("chambre")),
        "couleur": v(o.get("couleurAssociee")), "site_internet": v(o.get("siteInternet")),
        "nombre_reunions_annuelles": v(o.get("nombreReunionsAnnuelles")),
        "departement_code": v(dep.get("code")), "departement_nature": v(dep.get("codeNatureDep")),
        "departement": v(dep.get("libelle")), "region": v(reg.get("libelle")),
        "region_type": v(reg.get("type")), "pays": [p for p in pays if p],
        "prov_url": None,
    }


def _deport(x: dict) -> dict:
    cible = d(x.get("cible"))
    refs = val(cible.get("references"))
    uid = v(x.get("uid"))
    if uid is None:
        raise ValueError("déport sans uid")
    return {
        "uid": uid, "acteur": pa_id(x.get("refActeur")), "legislature": v(x.get("legislature")),
        "chronotag": v(x.get("chronotag")), "date_creation": v(x.get("dateCreation")),
        "date_publication": v(x.get("datePublication")),
        "portee_code": v(d(x.get("portee")).get("code")),
        "portee": v(d(x.get("portee")).get("libelle")),
        "lecture_code": v(d(x.get("lecture")).get("code")),
        "lecture": v(d(x.get("lecture")).get("libelle")),
        "instance_code": v(d(x.get("instance")).get("code")),
        "instance": v(d(x.get("instance")).get("libelle")),
        "cible_type_code": v(d(cible.get("type")).get("code")),
        "cible_type": v(d(cible.get("type")).get("libelle")),
        "cible_reference_textuelle": v(cible.get("referenceTextuelle")),
        # Toujours null dans les archives mesurées : forme inconnue, gardée telle quelle (JSON).
        "cible_references": None if refs is None else orjson.dumps(refs).decode(),
        "explication": v(x.get("explication")),  # HTML échappé, tel quel
        "prov_url": None,
    }


def lire(m):
    doc = orjson.loads(m.octets)
    vide = {t: [] for t in TABLES}
    # Archive AMO20 de la XIVe : tous les organes et acteurs dans un seul fichier.
    if isinstance(doc.get("export"), dict):
        ex = doc["export"]
        out = {t: [] for t in TABLES}
        for o in liste((ex.get("organes") or {}).get("organe")):
            out["organe"].append(_organe(o))
        for a in liste((ex.get("acteurs") or {}).get("acteur")):
            for t, ls in _acteur(a).items():
                out[t] += ls
        return out
    if "acteur" in doc:
        return {**vide, **_acteur(doc["acteur"])}
    if "organe" in doc:
        return {**vide, "organe": [_organe(doc["organe"])]}
    if "deport" in doc:
        return {**vide, "deport": [_deport(doc["deport"])]}
    raise ValueError(f"objet AMO inconnu : clés {sorted(doc)[:5]}")


EXPORT = {
    "identite_source": {"type": "identite_source", "cle": ["uid"], "ids": {"acteur": "uid"},
                        "date": None},
    "organe": {"type": "organe", "cle": ["uid"],
               "ids": {"organe": "uid"}, "date": "date_debut"},
    "mandat": {"type": "mandat", "cle": ["uid"],
               "ids": {"mandat": "uid", "acteur": "acteur", "organe": "organe"},
               "date": "date_debut"},
    "deport": {"type": "deport", "cle": ["uid"], "ids": {"acteur": "acteur", "autre": "uid"},
               "date": "date_creation"},
}
