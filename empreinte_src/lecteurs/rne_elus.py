"""Répertoire national des élus (data.gouv.fr, Licence Ouverte 2.0 ; cahier 3.9) : les mandats
locaux, fichier par fichier (points `rne-*`, décisions du 13/11/2026, Q34 et Q35).

Un membre = un fichier CSV (séparateur `;`, parfois entre guillemets), reconnu par son uid :
`elus-cm` (conseillers municipaux), `elus-maires`, `elus-epci` (conseillers communautaires),
`elus-cd` (départementaux), `elus-cr` (régionaux), `elus-ca` (d'arrondissement), `elus-ma`
(membres d'une assemblée de collectivité à statut particulier), `elus-consfde` et `elus-afe`
(Français de l'étranger), et `elus-sortants-cm`, `elus-sortants-maires` (sortants des municipales
de 2026 : mandats 2020-2026, jeu figé du 27/02/2026).

Une ligne de `mandat_local` par ligne du fichier, telle que publiée : **aucun identifiant de
personne, aucune date de fin** (la source n'en a pas). Les colonnes varient d'un fichier à
l'autre : elles sont lues par leur nom. Les dates du fichier des sortants sont écrites
`JJ/MM/AA` : l'année de naissance à deux chiffres est lue au XXe siècle au-delà de `08` (un élu a
au moins 18 ans), au XXIe sinon ; la date telle qu'écrite est gardée (`naissance_publiee`). Une
date de naissance aberrante (le répertoire publie `1072-03-05` et `1900-01-01`) est gardée telle
quelle : la règle de rattachement exige une concordance exacte avec une autre source.
"""
import csv
import io
import re

import pyarrow as pa

NOM = "rne_elus"
VERSION = 1
TYPES = ("elus_rne",)
S = pa.string()
TABLES = {"mandat_local": pa.schema([
    ("fichier", S), ("niveau", S), ("sortant", pa.bool_()), ("fonction", S), ("collectivite", S),
    ("code_collectivite", S), ("departement", S), ("nom", S), ("prenom", S), ("sexe", S),
    ("naissance", S), ("naissance_publiee", S), ("debut_mandat", S), ("debut_fonction", S),
    ("categorie_socio_professionnelle", S), ("ligne", pa.int32())])}

# uid → (niveau, fonction par défaut, sortant, colonnes du libellé de la collectivité, du code)
FICHIERS = {
    "elus-cm": ("municipal", "Conseiller municipal", False, ["Libellé de la commune"], ["Code de la commune"]),
    "elus-maires": ("municipal", "Maire", False, ["Libellé de la commune"], ["Code de la commune"]),
    "elus-epci": ("intercommunal", "Conseiller communautaire", False, ["Libellé de l'EPCI"], ["N° SIREN"]),
    "elus-cd": ("departemental", "Conseiller départemental", False,
                ["Libellé du canton", "Libellé du département"], ["Code du canton"]),
    "elus-cr": ("regional", "Conseiller régional", False, ["Libellé de la région"], ["Code de la région"]),
    "elus-ca": ("arrondissement", "Conseiller d'arrondissement", False,
                ["Libellé du secteur", "Libellé de la commune"], ["Code de la commune"]),
    "elus-ma": ("collectivite_statut_particulier", "Membre de l'assemblée", False,
                ["Libellé de la collectivité à statut particulier", "Libellé de la région"],
                ["Code de la collectivité à statut particulier", "Code de la région"]),
    "elus-consfde": ("francais_etranger", "Conseiller des Français de l'étranger", False,
                     ["Libellé de la circonscription consulaire"], ["Code de la circonscription consulaire"]),
    "elus-afe": ("francais_etranger", "Membre de l'Assemblée des Français de l'étranger", False,
                 ["Libellé la circ. AFE"], ["Code de la circ. AFE"]),
    "elus-sortants-cm": ("municipal", "Conseiller municipal", True, ["Libellé de la commune"], ["Code de la commune"]),
    "elus-sortants-maires": ("municipal", "Maire", True, ["Libellé de la commune"], ["Code de la commune"]),
}
PAGE = {False: "https://www.data.gouv.fr/fr/datasets/repertoire-national-des-elus-1/",
        True: "https://www.data.gouv.fr/fr/datasets/69a233819c17f13feedbc2cc/"}
_JJMMAA = re.compile(r"^(\d{2})/(\d{2})/(\d{2})$")
LOT = 50_000


def date_iso(v: str | None, naissance: bool) -> str | None:
    """`AAAA-MM-JJ` tel quel ; `JJ/MM/AA` (sortants) avec le siècle établi comme dit plus haut."""
    v = (v or "").strip()
    if not v:
        return None
    m = _JJMMAA.match(v)
    if not m:
        return v
    j, mo, a = m.groups()
    siecle = (19 if int(a) > 8 else 20) if naissance else 20
    return f"{siecle}{a}-{mo}-{j}"


def _col(ligne: dict, noms: list[str]) -> str | None:
    vals = [(ligne.get(n) or "").strip() for n in noms]
    vals = [v for v in vals if v]
    return " · ".join(vals) if vals else None


def lire(m):
    if m.uid not in FICHIERS:
        return {"mandat_local": []}
    niveau, fonction_defaut, sortant, libelles, codes = FICHIERS[m.uid]
    texte = m.octets.decode("utf-8-sig", errors="replace")
    lecteur = csv.DictReader(io.StringIO(texte), delimiter=";")
    lecteur.fieldnames = [re.sub(r"\s+", " ", (c or "").strip()) for c in lecteur.fieldnames or []]
    lot = []
    for k, l in enumerate(lecteur, 1):
        n_pub = (l.get("Date de naissance") or "").strip() or None
        lot.append({
            "fichier": m.uid[len("elus-"):], "niveau": niveau, "sortant": sortant,
            "fonction": (l.get("Libellé de la fonction") or "").strip() or fonction_defaut,
            "collectivite": _col(l, libelles), "code_collectivite": _col(l, codes),
            "departement": (l.get("Libellé du département") or "").strip() or None,
            "nom": (l.get("Nom de l'élu") or "").strip() or None,
            "prenom": (l.get("Prénom de l'élu") or "").strip() or None,
            "sexe": (l.get("Code sexe") or "").strip() or None,
            "naissance": date_iso(n_pub, True), "naissance_publiee": n_pub,
            "debut_mandat": date_iso(l.get("Date de début du mandat"), False),
            "debut_fonction": date_iso(l.get("Date de début de la fonction"), False),
            "categorie_socio_professionnelle": (l.get("Libellé de la catégorie socio-professionnelle") or "").strip() or None,
            "ligne": k, "prov_url": PAGE[sortant]})
        if len(lot) >= LOT:
            yield {"mandat_local": lot}
            lot = []
    if lot:
        yield {"mandat_local": lot}


EXPORT = {
    # Clé du doc. 1 (1.4, G), plus la date de début de la fonction : une même fonction peut être
    # attribuée deux fois dans un mandat (23 adjoints et maires délégués dans les sortants de 2026).
    # Pas le numéro de ligne, qui se décale d'une publication à l'autre.
    "mandat_local": {"type": "mandat_local",
                     "cle": ["fichier", "nom", "prenom", "naissance_publiee", "code_collectivite",
                             "fonction", "debut_mandat", "debut_fonction"],
                     "ids": {"autre": "fichier"}, "date": "debut_mandat"},
}
