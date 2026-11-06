"""Dossiers législatifs et documents de l'Assemblée (cahier 3.1.4 ; mesures
`an-scrutins-dossiers.md`, section 4).

Un membre est, selon la législature :
- XVe-XVIIe : un JSON par objet, `{"dossierParlementaire": {...}}` (sous
  `json/dossierParlementaire/`) ou `{"document": {...}}` (sous `json/document/`) ;
- XIVe : un seul fichier `{"export": {"textesLegislatifs": {"document": [...]},
  "dossiersLegislatifs": {"dossier": [{"dossierParlementaire": {...}}, ...]}}}`.

Tables :
- `dossier` : titre, chemins, procédure, initiateurs (acteurs, mandats, organes), fusion ;
- `document` : un texte déposé ou un rapport, et ses **divisions** (tomes, volumes), aplaties
  avec leur parent ; la nature est lue dans le **préfixe de l'uid** (`PRJL`, `PION`, `PNRE`,
  `RAPP`…), jamais dans le titre ; auteurs (acteurs et qualités, organes) ;
- `cosignature` : les cosignataires d'un document, avec date de cosignature et de retrait ;
- `acte` : l'arbre des actes, aplati (parent, rang, profondeur), champ par champ. La
  conclusion (`statutConclusion`), la décision du Conseil constitutionnel (`decision`) et le
  type de déclaration (`typeDeclaration`, dont `fam_code = "Art.49.3"`) sont lus **tels
  quels** : le lecteur ne déduit ni état, ni étape, ni sort.

Pièges traités :
- un acte, un votant, un rapporteur, un texte associé seul est un dictionnaire, plusieurs une
  liste ; `actesLegislatifs` vaut `null` sur les feuilles ;
- un même acte (même uid) peut figurer dans **deux dossiers** (examen commun : 43 uid dans
  l'archive XVIIe du 03/11/2026, 49.3 et motions de censure des lois financières) : la clé
  d'un acte est (dossier, uid) ;
- les scrutins cités (`voteRefs`) peuvent être ceux du **Sénat** (`VTSN…`) : gardés tels quels ;
- le NOR est dans `infoJO.referenceNOR` (XVe-XVIIe) ou **au niveau de l'acte**
  (`referenceNOR`, XIVe) ; de même `urlLegifrance` ;
- les rectificatifs au JO (`infoJORect`, dictionnaire ou liste) sont gardés à part ;
- l'archive XIVe contient des documents d'autres législatures ; `legislature` est lu tel quel
  (souvent `null` pour les documents du Sénat) ;
- identifiants de personne rétablis avec leur préfixe `PA`.

Adresses publiques : dossier `https://www.assemblee-nationale.fr/dyn/{leg}/dossiers/{titreChemin}` ;
document de l'Assemblée (XVe et suivantes) `https://www.assemblee-nationale.fr/dyn/opendata/{uid}.html`
(cahier 3.1.8 ; 404 sur toute la XIVe) ; acte : l'adresse que la source donne (Légifrance pour une
promulgation, Conseil constitutionnel pour une décision), sinon celle du dossier.
"""
import re

import orjson
import pyarrow as pa

from ..lecture import est_nil, liste, pa_id, val

NOM = "an_dossiers"
VERSION = 1
TYPES = ("dossiers",)

L = pa.list_(pa.string())

TABLES = {
    "dossier": pa.schema([
        ("uid", pa.string()), ("legislature", pa.string()), ("type_dossier", pa.string()),
        ("titre", pa.string()), ("titre_chemin", pa.string()), ("senat_chemin", pa.string()),
        ("procedure_code", pa.string()), ("procedure_libelle", pa.string()),
        ("initiateurs_acteurs", L), ("initiateurs_mandats", L), ("initiateurs_organes", L),
        ("fusion_cause", pa.string()), ("fusion_dossier_absorbant", pa.string()),
        ("themes", L), ("nb_actes", pa.int32()),
    ]),
    "document": pa.schema([
        ("uid", pa.string()), ("parent", pa.string()), ("profondeur", pa.int32()),
        ("dossier", pa.string()), ("legislature", pa.string()), ("nature", pa.string()),
        ("chambre", pa.string()), ("type_document", pa.string()),
        ("denomination_structurelle", pa.string()),
        ("titre", pa.string()), ("titre_court", pa.string()),
        ("type_code", pa.string()), ("type_libelle", pa.string()),
        ("sous_type_code", pa.string()), ("sous_type_libelle", pa.string()),
        ("famille_depot_code", pa.string()), ("famille_classe_code", pa.string()),
        ("famille_espece_code", pa.string()), ("statut_adoption", pa.string()),
        ("provenance", pa.string()),
        ("date_creation", pa.string()), ("date_depot", pa.string()),
        ("date_publication", pa.string()), ("date_publication_web", pa.string()),
        ("date_suppression", pa.string()),
        ("num_notice", pa.string()), ("formule_notice", pa.string()),
        ("adoption_conforme", pa.string()), ("rapport_publie", pa.string()),
        ("auteurs_acteurs", L), ("auteurs_qualites", L), ("auteurs_organes", L),
        ("organes_referents", L), ("correction_type", pa.string()),
        ("correction_niveau", pa.string()),
    ]),
    "cosignature": pa.schema([
        ("document", pa.string()), ("rang", pa.int32()), ("acteur", pa.string()),
        ("organe", pa.string()), ("et_apparentes", pa.string()),
        ("date_cosignature", pa.string()), ("date_retrait", pa.string()), ("edite", pa.string()),
    ]),
    "acte": pa.schema([
        ("dossier", pa.string()), ("uid", pa.string()), ("parent", pa.string()),
        ("rang", pa.int32()), ("profondeur", pa.int32()), ("type_acte", pa.string()),
        ("code", pa.string()), ("libelle", pa.string()), ("libelle_court", pa.string()),
        ("date", pa.string()), ("organe", pa.string()), ("reunion", pa.string()),
        ("odj", pa.string()), ("provenance", pa.string()),
        ("conclusion_code", pa.string()), ("conclusion_libelle", pa.string()),
        ("decision_code", pa.string()), ("decision_libelle", pa.string()),
        ("num_decision", pa.string()), ("annee_decision", pa.string()),
        ("url_conclusion", pa.string()), ("formule_decision", pa.string()),
        ("cas_saisine_code", pa.string()), ("cas_saisine_libelle", pa.string()),
        ("motif", pa.string()),
        ("type_declaration_code", pa.string()), ("type_declaration_libelle", pa.string()),
        ("type_motion_code", pa.string()), ("type_motion_libelle", pa.string()),
        ("type_motion_censure_code", pa.string()), ("type_motion_censure_libelle", pa.string()),
        ("auteur_motion", pa.string()), ("auteurs", L),
        ("scrutins", L),
        ("texte_associe", pa.string()), ("textes_associes", L), ("textes_associes_types", L),
        ("texte_adopte", pa.string()), ("texte_loi", pa.string()),
        ("depot_initial_lecture_definitive", pa.string()),
        ("rapporteurs", L), ("rapporteurs_types", L), ("rapporteurs_etude_plf", L),
        ("initiateurs_acteurs", L), ("initiateurs_mandats", L), ("initiateurs_organes", L),
        ("code_loi", pa.string()), ("titre_loi", pa.string()),
        ("reference_nor", pa.string()), ("type_jo", pa.string()), ("date_jo", pa.string()),
        ("num_jo", pa.string()), ("page_jo", pa.string()), ("url_legifrance", pa.string()),
        ("rectificatifs_jo", L), ("url_echeancier_loi", pa.string()),
        ("date_retrait", pa.string()),
        ("contribution_ouverture", pa.string()), ("contribution_fermeture", pa.string()),
        ("statut_adoption_code", pa.string()), ("statut_adoption_libelle", pa.string()),
        ("texte_europeen_type", pa.string()), ("texte_europeen_titre", pa.string()),
        ("date_joce", pa.string()), ("ref_joce", pa.string()),
        ("texte_externe", pa.string()),
    ]),
}

PREFIXE = re.compile(r"^([A-Z]{4})(AN|SN|CG)?")
LEG_AN = re.compile(r"ANR5L(\d+)")


def g(d, *ks):
    """Descente dans des dictionnaires imbriqués ; None dès qu'un niveau manque ou est vide."""
    for k in ks:
        if not isinstance(d, dict) or est_nil(d):
            return None
        d = d.get(k)
    return val(d)


def chaines(xs) -> list[str]:
    return [str(x) for x in (val(x) for x in xs) if x is not None]


def json_ou_none(x) -> str | None:
    """Champ composite rare gardé tel quel, en JSON compact."""
    if x is None or est_nil(x):
        return None
    return orjson.dumps(x, option=orjson.OPT_SORT_KEYS).decode()


def url_dossier(leg, chemin) -> str | None:
    if not leg or not chemin:
        return None
    return f"https://www.assemblee-nationale.fr/dyn/{leg}/dossiers/{chemin}"


def url_document(uid: str) -> str | None:
    m = LEG_AN.search(uid or "")
    if not m or int(m.group(1)) < 15:
        return None
    return f"https://www.assemblee-nationale.fr/dyn/opendata/{uid}.html"


# -- dossiers ------------------------------------------------------------------------------

def initiateurs(x) -> tuple[list, list, list]:
    """`initiateur` (dossier, RenvoiCMP) ou `initiateurs` (saisine, création d'organe)."""
    if x is None or est_nil(x):
        return [], [], []
    acteurs, mandats, organes = [], [], []
    for a in liste(g(x, "acteurs") and x["acteurs"].get("acteur")):
        acteurs.append(pa_id(a.get("acteurRef")))
        mandats.append(val(a.get("mandatRef")))
    for o in liste(g(x, "organes") and x["organes"].get("organe")):
        ref = o.get("organeRef")
        organes.append(val(ref.get("uid")) if isinstance(ref, dict) else val(ref))
    for a in liste(x.get("acteurRef")):
        acteurs.append(pa_id(a))
    for o in liste(x.get("organeRef")):
        organes.append(val(o))
    return ([a for a in acteurs if a], [m for m in mandats if m], [o for o in organes if o])


def lire_dossier(d: dict, out: dict):
    uid = val(d["uid"])
    leg = val(d.get("legislature"))
    td = d.get("titreDossier") or {}
    url = url_dossier(leg, g(td, "titreChemin"))
    ia, im, io = initiateurs(d.get("initiateur"))
    fus = d.get("fusionDossier")
    themes = [g(t, "libelleTheme") for t in
              liste(g(d, "indexation", "themes") and d["indexation"]["themes"].get("theme"))]
    actes = lire_actes(uid, d, url, out)
    out["dossier"].append({
        "uid": uid, "legislature": leg, "type_dossier": val(d.get("@xsi:type")),
        "titre": g(td, "titre"), "titre_chemin": g(td, "titreChemin"),
        "senat_chemin": g(td, "senatChemin"),
        "procedure_code": g(d, "procedureParlementaire", "code"),
        "procedure_libelle": g(d, "procedureParlementaire", "libelle"),
        "initiateurs_acteurs": ia, "initiateurs_mandats": im, "initiateurs_organes": io,
        "fusion_cause": g(fus, "cause"), "fusion_dossier_absorbant": g(fus, "dossierAbsorbantRef"),
        "themes": [t for t in themes if t], "nb_actes": actes, "prov_url": url,
    })


def lire_actes(dossier: str, d: dict, url_dos, out: dict) -> int:
    """Parcours en profondeur de l'arbre ; rend le nombre d'actes lus."""
    racine = liste((d.get("actesLegislatifs") or {}).get("acteLegislatif"))
    pile = [(0, None, k, a) for k, a in reversed(list(enumerate(racine)))]
    n = 0
    while pile:
        prof, parent, rang, a = pile.pop()
        if a is None or est_nil(a):
            continue
        n += 1
        out["acte"].append(ligne_acte(dossier, parent, rang, prof, a, url_dos))
        enfants = liste((a.get("actesLegislatifs") or {}).get("acteLegislatif"))
        for k, f in reversed(list(enumerate(enfants))):
            pile.append((prof + 1, val(a.get("uid")), k, f))
    return n


def ligne_acte(dossier, parent, rang, prof, a: dict, url_dos) -> dict:
    info = a.get("infoJO") or {}
    if est_nil(info):
        info = {}
    tas = liste(g(a, "textesAssocies") and a["textesAssocies"].get("texteAssocie"))
    raps = liste(g(a, "rapporteurs") and a["rapporteurs"].get("rapporteur"))
    ia, im, io = initiateurs(a.get("initiateur") if "initiateur" in a else a.get("initiateurs"))
    auteurs = a.get("auteurs")
    nor = g(info, "referenceNOR") or val(a.get("referenceNOR"))
    url_lf = g(info, "urlLegifrance") or val(a.get("urlLegifrance"))
    ta = a.get("texteAssocie")
    ce = a.get("contributionInternaute") or {}
    joce = a.get("infoJOCE") or {}
    return {
        "dossier": dossier, "uid": val(a.get("uid")), "parent": parent, "rang": rang,
        "profondeur": prof, "type_acte": val(a.get("@xsi:type")),
        "code": val(a.get("codeActe")),
        "libelle": g(a, "libelleActe", "nomCanonique"),
        "libelle_court": g(a, "libelleActe", "libelleCourt"),
        "date": val(a.get("dateActe")), "organe": val(a.get("organeRef")),
        "reunion": val(a.get("reunionRef")), "odj": val(a.get("odjRef")),
        "provenance": val(a.get("provenance")),
        "conclusion_code": g(a, "statutConclusion", "fam_code"),
        "conclusion_libelle": g(a, "statutConclusion", "libelle"),
        "decision_code": g(a, "decision", "fam_code"),
        "decision_libelle": g(a, "decision", "libelle"),
        "num_decision": val(a.get("numDecision")), "annee_decision": val(a.get("anneeDecision")),
        "url_conclusion": val(a.get("urlConclusion")),
        "formule_decision": val(a.get("formuleDecision")),
        "cas_saisine_code": g(a, "casSaisine", "fam_code"),
        "cas_saisine_libelle": g(a, "casSaisine", "libelle"),
        "motif": val(a.get("motif")),
        "type_declaration_code": g(a, "typeDeclaration", "fam_code"),
        "type_declaration_libelle": g(a, "typeDeclaration", "libelle"),
        "type_motion_code": g(a, "typeMotion", "fam_code"),
        "type_motion_libelle": g(a, "typeMotion", "libelle"),
        "type_motion_censure_code": g(a, "typeMotionCensure", "fam_code"),
        "type_motion_censure_libelle": g(a, "typeMotionCensure", "libelle"),
        "auteur_motion": pa_id(a.get("auteurMotion")),
        "auteurs": [x for x in (pa_id(v) for v in liste(
            auteurs.get("acteurRef") if isinstance(auteurs, dict) and not est_nil(auteurs) else None)) if x],
        "scrutins": chaines(liste(g(a, "voteRefs") and a["voteRefs"].get("voteRef"))),
        "texte_associe": val(ta) if not isinstance(ta, (dict, list)) else json_ou_none(ta),
        "textes_associes": chaines(t.get("refTexteAssocie") for t in tas if isinstance(t, dict)),
        "textes_associes_types": chaines(t.get("typeTexte") for t in tas if isinstance(t, dict)),
        "texte_adopte": val(a.get("texteAdopte")), "texte_loi": val(a.get("texteLoiRef")),
        "depot_initial_lecture_definitive": val(a.get("depotInitialLectureDefinitiveRef")),
        "rapporteurs": [pa_id(r.get("acteurRef")) for r in raps],
        "rapporteurs_types": [val(r.get("typeRapporteur")) for r in raps],
        "rapporteurs_etude_plf": [val(r.get("etudePLFRef")) for r in raps],
        "initiateurs_acteurs": ia, "initiateurs_mandats": im, "initiateurs_organes": io,
        "code_loi": val(a.get("codeLoi")), "titre_loi": val(a.get("titreLoi")),
        "reference_nor": nor, "type_jo": g(info, "typeJO"), "date_jo": g(info, "dateJO"),
        "num_jo": g(info, "numJO"), "page_jo": g(info, "pageJO"), "url_legifrance": url_lf,
        "rectificatifs_jo": [json_ou_none(r) for r in liste(a.get("infoJORect"))],
        "url_echeancier_loi": val(a.get("urlEcheancierLoi")),
        "date_retrait": val(a.get("dateRetrait")),
        "contribution_ouverture": g(ce, "dateOuverture"),
        "contribution_fermeture": g(ce, "dateFermeture"),
        "statut_adoption_code": g(a, "statutAdoption", "fam_code"),
        "statut_adoption_libelle": g(a, "statutAdoption", "libelle"),
        "texte_europeen_type": g(a, "texteEuropeen", "typeTexteEuropeen"),
        "texte_europeen_titre": g(a, "texteEuropeen", "titreTexteEuropeen"),
        "date_joce": g(joce, "dateJOCE"), "ref_joce": g(joce, "refJOCE"),
        "texte_externe": json_ou_none(a.get("texteExterneAssocie")),
        "prov_url": url_lf or val(a.get("urlConclusion")) or url_dos,
    }


# -- documents -----------------------------------------------------------------------------

def lire_document(doc: dict, out: dict, parent=None, prof=0, url_parent=None):
    uid = val(doc["uid"])
    m = PREFIXE.match(uid or "")
    cl = doc.get("classification") or {}
    ch = g(doc, "cycleDeVie") and (doc["cycleDeVie"].get("chrono") or {})
    acteurs, qualites, organes = [], [], []
    for au in liste(g(doc, "auteurs") and doc["auteurs"].get("auteur")):
        if not isinstance(au, dict):
            continue
        if isinstance(au.get("acteur"), dict):
            acteurs.append(pa_id(au["acteur"].get("acteurRef")))
            qualites.append(val(au["acteur"].get("qualite")))
        if isinstance(au.get("organe"), dict):
            organes.append(val(au["organe"].get("organeRef")))
    ref = doc.get("organesReferents")
    supprime = g(doc, "metadatas", "dateSuppression")
    # Une division (tome, volume) n'a pas de page à elle : l'adresse est celle du document
    # parent ; un document supprimé à la source n'en a plus.
    url = None if supprime else (url_parent if parent else url_document(uid))
    out["document"].append({
        "uid": uid, "parent": parent, "profondeur": prof,
        "dossier": val(doc.get("dossierRef")), "legislature": val(doc.get("legislature")),
        "nature": m.group(1) if m else None, "chambre": m.group(2) if m else None,
        "type_document": val(doc.get("@xsi:type")),
        "denomination_structurelle": val(doc.get("denominationStructurelle")),
        "titre": g(doc, "titres", "titrePrincipal"),
        "titre_court": g(doc, "titres", "titrePrincipalCourt"),
        "type_code": g(cl, "type", "code"), "type_libelle": g(cl, "type", "libelle"),
        "sous_type_code": g(cl, "sousType", "code"), "sous_type_libelle": g(cl, "sousType", "libelle"),
        "famille_depot_code": g(cl, "famille", "depot", "code"),
        "famille_classe_code": g(cl, "famille", "classe", "code"),
        "famille_espece_code": g(cl, "famille", "espece", "code"),
        "statut_adoption": g(cl, "statutAdoption"),
        "provenance": val(doc.get("provenance")),
        "date_creation": g(ch, "dateCreation"), "date_depot": g(ch, "dateDepot"),
        "date_publication": g(ch, "datePublication"),
        "date_publication_web": g(ch, "datePublicationWeb"),
        "date_suppression": supprime,
        "num_notice": g(doc, "notice", "numNotice"), "formule_notice": g(doc, "notice", "formule"),
        "adoption_conforme": g(doc, "notice", "adoptionConforme"),
        "rapport_publie": val(doc.get("rapportPublie")),
        "auteurs_acteurs": acteurs, "auteurs_qualites": qualites, "auteurs_organes": organes,
        "organes_referents": chaines(liste(ref.get("organeRef")) if isinstance(ref, dict) else []),
        "correction_type": g(doc, "correction", "typeCorrection"),
        "correction_niveau": g(doc, "correction", "niveauCorrection"),
        "prov_url": url,
    })
    for k, c in enumerate(liste(g(doc, "coSignataires") and doc["coSignataires"].get("coSignataire"))):
        org = c.get("organe") if isinstance(c.get("organe"), dict) else {}
        out["cosignature"].append({
            "document": uid, "rang": k,
            "acteur": pa_id(g(c, "acteur", "acteurRef")), "organe": val(org.get("organeRef")),
            "et_apparentes": val(org.get("etApparentes")),
            "date_cosignature": val(c.get("dateCosignature")),
            "date_retrait": val(c.get("dateRetraitCosignature")), "edite": val(c.get("edite")),
            "prov_url": url,
        })
    for div in liste(g(doc, "divisions") and doc["divisions"].get("division")):
        if isinstance(div, dict) and not est_nil(div):
            lire_document(div, out, parent=uid, prof=prof + 1, url_parent=url)


# -- membre --------------------------------------------------------------------------------

def lire(m):
    d = orjson.loads(m.octets)
    out = {t: [] for t in TABLES}
    if "dossierParlementaire" in d:
        lire_dossier(d["dossierParlementaire"], out)
    elif "document" in d:
        lire_document(d["document"], out)
    elif "export" in d:                               # XIVe : un seul fichier
        e = d["export"] or {}
        for doc in liste((e.get("textesLegislatifs") or {}).get("document")):
            lire_document(doc, out)
        for dos in liste((e.get("dossiersLegislatifs") or {}).get("dossier")):
            lire_dossier(dos.get("dossierParlementaire", dos), out)
    else:
        raise ValueError(f"forme de membre inconnue : clés {sorted(d)[:5]}")
    return out


EXPORT = {
    "dossier": {"type": "dossier", "cle": ["uid"], "ids": {"dossier": "uid"}, "date": None},
    "document": {"type": "document", "cle": ["uid"],
                 "ids": {"document": "uid", "dossier": "dossier"}, "date": "date_depot"},
    "cosignature": {"type": "cosignature", "cle": ["document", "rang"],
                    "ids": {"document": "document", "acteur": "acteur", "organe": "organe"},
                    "date": "date_cosignature"},
    "acte": {"type": "acte", "cle": ["dossier", "uid"],
             "ids": {"acte": "uid", "dossier": "dossier", "organe": "organe",
                     "reunion": "reunion"},
             "date": "date"},
}
