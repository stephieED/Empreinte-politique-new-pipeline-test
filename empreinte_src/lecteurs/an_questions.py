"""Questions de l'Assemblée : écrites, au gouvernement, orales sans débat (cahier 3.1.6).

Un fichier JSON par question (`json/QANR5L17QE5268.json`), même schéma pour les trois types en
XVIIe. Une ligne de `question` par question, champ par champ :

- auteur (`acteurRef`, `mandatRef`, groupe déclaré par la source) ;
- ministère interrogé (`minInt.organeRef`) et ministères attributaires successifs
  (`minAttribs.minAttrib`, un objet seul ou une liste, avec leur date de JO) ;
- rubrique, tête d'analyse, analyse ;
- texte de la question et sa publication au JO ; texte de la réponse et sa publication ;
  les errata (deuxième publication d'un texte, avec la clé `erratum`) sont gardés à part, la
  publication d'origine restant le texte principal ;
- signalement, renouvellements (un objet seul ou une liste), clôture.

Une question au gouvernement n'a **pas** de texte de question (`textesQuestion` toujours
null) : question et réponse forment un seul bloc HTML, gardé tel quel dans `texte_reponse`
(1 857 sur 1 857 en XVIIe) ; elle ne porte aucune référence de séance.

Le schéma de la XVe écrit les clés en capitales (cahier 3.1.6) : les clés sont cherchées sans
tenir compte de la casse, ce qui suffit si seuls les noms changent de casse. **Non vérifié** :
aucune archive de questions de la XVe n'est disponible localement.

Adresse publique : l'adresse `questions.assemblee-nationale.fr/q{leg}/{uid}.htm` du cahier
(3.1.9) n'apparaît dans aucune donnée relevée ; `prov_url` reste vide.
"""
import re

import orjson
import pyarrow as pa

from ..lecture import en_flux, est_nil, liste, pa_id, val

SEUIL_FLUX = 32 << 20     # au-delà, un fichier unique de questions est lu en flux

NOM = "an_questions"
VERSION = 2
TYPES = ("questions_ecrites", "questions_gouvernement", "questions_orales")

_ATTRIB = pa.struct([("organe", pa.string()), ("abrege", pa.string()),
                     ("libelle", pa.string()), ("date_jo", pa.string())])
_ERRATUM = pa.struct([("date_jo", pa.string()), ("num_jo", pa.string()),
                      ("page_jo", pa.string()), ("erratum", pa.string()),
                      ("texte", pa.string())])

TABLES = {
    "question": pa.schema([
        ("uid", pa.string()), ("type", pa.string()), ("type_xsi", pa.string()),
        ("legislature", pa.string()), ("numero", pa.string()), ("regime", pa.string()),
        ("auteur", pa.string()), ("auteur_mandat", pa.string()),
        ("auteur_groupe", pa.string()), ("auteur_groupe_abrege", pa.string()),
        ("auteur_groupe_libelle", pa.string()),
        ("ministere_interroge", pa.string()), ("ministere_interroge_abrege", pa.string()),
        ("ministere_interroge_libelle", pa.string()),
        ("ministeres_attributaires", pa.list_(_ATTRIB)),
        ("rubrique", pa.string()), ("tete_analyse", pa.string()),
        ("analyses", pa.list_(pa.string())),
        ("date_question", pa.string()), ("num_jo_question", pa.string()),
        ("page_jo_question", pa.string()), ("texte_question", pa.string()),
        ("errata_question", pa.list_(_ERRATUM)),
        ("date_reponse", pa.string()), ("num_jo_reponse", pa.string()),
        ("page_jo_reponse", pa.string()), ("type_jo_reponse", pa.string()),
        ("texte_reponse", pa.string()), ("errata_reponse", pa.list_(_ERRATUM)),
        ("date_depot_signalement", pa.string()), ("date_jo_signalement", pa.string()),
        ("dates_renouvellement", pa.list_(pa.string())),
        ("code_cloture", pa.string()), ("libelle_cloture", pa.string()),
        ("date_cloture", pa.string()), ("date_jo_cloture", pa.string()),
    ]),
}


def g(x, *chemin):
    """Descend dans les objets en cherchant chaque clé sans tenir compte de la casse
    (XVe : clés en capitales). Rend None dès qu'un maillon manque ou est vide."""
    for k in chemin:
        if not isinstance(x, dict) or est_nil(x):
            return None
        if k in x:
            x = x[k]
            continue
        bas = k.lower()
        x = next((w for c, w in x.items() if c.lower() == bas), None)
    return None if est_nil(x) else x


def v(x):
    """Valeur simple ; null, "" et xsi:nil deviennent None."""
    x = val(x)
    if x is None or x == "":
        return None
    if isinstance(x, (dict, list)):
        raise ValueError(f"valeur simple attendue, reçu {type(x).__name__} : {str(x)[:80]}")
    return str(x)


_JJ_MM_AAAA = re.compile(r"(\d{2})/(\d{2})/(\d{4})")


def d(x) -> str | None:
    """Une date de la source, en `AAAA-MM-JJ`. L'archive de la XVe les publie en `JJ/MM/AAAA`
    (toutes ses questions : écrites, orales, au gouvernement), les autres en `AAAA-MM-JJ`.
    Version 2 du lecteur (14/11/2026) : comparées comme du texte, `15/03/2019` passait avant
    `2012-06-20`, et les filtres par date écartaient des questions de la XVe."""
    x = v(x)
    m = _JJ_MM_AAAA.fullmatch(x) if x else None
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else x


def _textes(bloc, cle):
    """(texte principal, errata) d'un bloc `textesQuestion` / `textesReponse`.
    Le principal est la première publication sans `erratum` (à défaut la première)."""
    elems = [e for e in liste(g(bloc, cle)) if isinstance(e, dict)]
    if not elems:
        return None, []
    a_erratum = lambda e: any(c.lower() == "erratum" for c in e)
    principal = next((e for e in elems if not a_erratum(e)), elems[0])
    errata = [{"date_jo": d(g(e, "infoJO", "dateJO")), "num_jo": v(g(e, "infoJO", "numJO")),
               "page_jo": v(g(e, "infoJO", "pageJO")), "erratum": v(g(e, "erratum")),
               "texte": v(g(e, "texte"))}
              for e in elems if e is not principal]
    return principal, errata


def _question(q: dict) -> dict:
    uid = v(g(q, "uid"))
    if uid is None:
        raise ValueError("question sans uid")
    tq, errata_q = _textes(g(q, "textesQuestion"), "texteQuestion")
    tr, errata_r = _textes(g(q, "textesReponse"), "texteReponse")
    attribs = [{"organe": v(g(a, "denomination", "organeRef")),
                "abrege": v(g(a, "denomination", "abrege")),
                "libelle": v(g(a, "denomination", "developpe")),
                "date_jo": d(g(a, "infoJO", "dateJO"))}
               for a in liste(g(q, "minAttribs", "minAttrib")) if isinstance(a, dict)]
    analyses = [v(a) for a in liste(g(q, "indexationAN", "analyses", "analyse"))]
    renouv = [d(g(r, "infoJO", "dateJO"))
              for r in liste(g(q, "renouvellements", "renouvellement")) if isinstance(r, dict)]
    return {
        "uid": uid, "type": v(g(q, "type")), "type_xsi": v(g(q, "@xsi:type")),
        "legislature": v(g(q, "identifiant", "legislature")),
        "numero": v(g(q, "identifiant", "numero")), "regime": v(g(q, "identifiant", "regime")),
        "auteur": pa_id(v(g(q, "auteur", "identite", "acteurRef"))),
        "auteur_mandat": v(g(q, "auteur", "identite", "mandatRef")),
        "auteur_groupe": v(g(q, "auteur", "groupe", "organeRef")),
        "auteur_groupe_abrege": v(g(q, "auteur", "groupe", "abrege")),
        "auteur_groupe_libelle": v(g(q, "auteur", "groupe", "developpe")),
        "ministere_interroge": v(g(q, "minInt", "organeRef")),
        "ministere_interroge_abrege": v(g(q, "minInt", "abrege")),
        "ministere_interroge_libelle": v(g(q, "minInt", "developpe")),
        "ministeres_attributaires": attribs,
        "rubrique": v(g(q, "indexationAN", "rubrique")),
        "tete_analyse": v(g(q, "indexationAN", "teteAnalyse")),
        "analyses": [a for a in analyses if a],
        "date_question": d(g(tq, "infoJO", "dateJO")), "num_jo_question": v(g(tq, "infoJO", "numJO")),
        "page_jo_question": v(g(tq, "infoJO", "pageJO")), "texte_question": v(g(tq, "texte")),
        "errata_question": errata_q,
        "date_reponse": d(g(tr, "infoJO", "dateJO")), "num_jo_reponse": v(g(tr, "infoJO", "numJO")),
        "page_jo_reponse": v(g(tr, "infoJO", "pageJO")),
        "type_jo_reponse": v(g(tr, "infoJO", "typeJO")), "texte_reponse": v(g(tr, "texte")),
        "errata_reponse": errata_r,
        "date_depot_signalement": d(g(q, "signalement", "dateDepotSignal")),
        "date_jo_signalement": d(g(q, "signalement", "infoJO", "dateJO")),
        "dates_renouvellement": [r for r in renouv if r],
        "code_cloture": v(g(q, "cloture", "codeCloture")),
        "libelle_cloture": v(g(q, "cloture", "libelleCloture")),
        "date_cloture": d(g(q, "cloture", "dateCloture")),
        "date_jo_cloture": d(g(q, "cloture", "infoJO", "dateJO")),
        "prov_url": None,
    }


def lire(m):
    """Lit un membre de l'archive des questions (`m`, un `MembreLu`) et rend
    `{"question": [lignes]}`, une ligne par question.

    Un fichier unique de la XIVe plus gros que `SEUIL_FLUX` (et qui commence par `{"questions`) est
    lu en flux : on rend alors un générateur de tels dictionnaires, un par lot. Une question seule,
    une liste de questions ou une enveloppe à une seule clé qui contient `question` sont lues ;
    sans objet « question », lève `ValueError`."""
    # Archives de la XIVe : toutes les questions dans un seul fichier (questions écrites : 575 Mo,
    # relevé le 07/11/2026) ; lues en flux, par lots, pour borner la mémoire.
    tete = m.octets[:120].decode("utf-8", "replace")
    if len(m.octets) > SEUIL_FLUX and tete.lstrip().startswith('{"questions'):
        cle = tete.split('"')[1]
        return ({"question": [_question(x) for x in lot]}
                for lot in en_flux(m.octets, f"{cle}.question.item"))
    doc = orjson.loads(m.octets)
    q = g(doc, "question")
    # Archives de la XIVe : toutes les questions dans une enveloppe (`questionsGvt`,
    # `questionsEcrites`, `questionsOralesSansDebat`…) qui contient la liste `question`.
    if q is None and isinstance(doc, dict) and len(doc) == 1:
        env = next(iter(doc.values()))
        q = g(env, "question") if isinstance(env, dict) else None
    if q is None:
        raise ValueError(f"pas d'objet « question » : clés {sorted(doc)[:5] if isinstance(doc, dict) else type(doc).__name__}")
    # Un fichier par question en XVIIe ; une liste est tolérée (fichier unique d'une archive ancienne).
    return {"question": [_question(x) for x in liste(q)]}


EXPORT = {
    "question": {"type": "question", "cle": ["uid"],
                 "ids": {"question": "uid", "acteur": "auteur", "mandat": "auteur_mandat",
                         "organe": "ministere_interroge"},
                 "date": "date_question"},
}
