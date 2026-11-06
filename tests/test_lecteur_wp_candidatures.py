"""Lecteur `wp_candidatures` : réponse réelle de l'API (section « Candidats déclarés », révision
240980797) et lignes de wikitexte recopiées de la révision 241073157 (fiche
`tests/extraits/wp_candidatures.md`). Ce lecteur dépend de conventions de rédaction : chaque
forme de nom rencontrée a son test, et une forme inconnue doit être comptée, pas devinée."""
import os

import orjson
import pytest

from empreinte.depaquetage import depaqueter
from empreinte.entrepot import Entrepot
from empreinte.export import exporter
from empreinte.lecture import Lecture, MembreLu
from empreinte.lecteurs import wp_candidatures as wp

EXTRAIT = os.path.join(os.path.dirname(__file__), "extraits", "wp_candidatures_section1.json")
PA_WP = {"id": "wp-candidatures-2027", "source": "wikipedia", "type": "candidatures",
         "format": "api_json", "url": "http://exemple.invalid/api.php"}
CFG = {"points_acces": [{"id": "wp-candidatures-2027", "licence": "cc-by-sa-4.0"}]}

# Lignes recopiées telles quelles de la révision 241073157 (entrepôt du 06/11/2026), références
# raccourcies à leur seule adresse.
RETIREES = (
    "== Candidatures retirées ==\n"
    "* [[Clémentine Autain]] ([[L'Après]]), députée de la {{Circonscription fr|11|Seine-Saint-Denis}}."
    " Après avoir annoncé sa candidature en mars 2025 à la [[Primaire de la gauche unitaire de 2026"
    "|primaire de la gauche unitaire]]<ref>{{Article |titre=x |lire en ligne=https://www.lemonde.fr/"
    "politique/article/2025/03/07/x.html}}</ref>, elle la retire le 11 juillet 2026.\n"
    "* [[Benjamin Lucas-Lundy]] ([[Génération.s|G·s]]), député de la {{Circonscription fr|8|Yvelines}}."
    " Après avoir annoncé le 15 mai 2026 être candidat à la primaire de la gauche unitaire<ref name=\"tf1\"/>,"
    " il la retire le 7 juillet.\n"
    "\n== Candidats pressentis ayant décliné ==\n"
)


def _lire(octets):
    return wp.lire(MembreLu("wp-candidatures-2027", "wikipedia", "candidatures",
                            "candidatures-2027", "releve", 1, "e", octets, "cc-by-sa-4.0"))


@pytest.fixture(scope="module")
def section1():
    with open(EXTRAIT, "rb") as f:
        return _lire(f.read())


def _reponse(wikitexte, revid=241073157, v1=False):
    w = {"*": wikitexte} if v1 else wikitexte
    return orjson.dumps({"parse": {"title": "Candidatures à l'élection présidentielle française de 2027",
                                   "pageid": 17573391, "revid": revid, "wikitext": w}})


def _section_declares(lignes_entete):
    """Petit tableau au gabarit de l'article ; chaque ligne reçoit un commentaire minimal."""
    corps = "".join(f"|-\n{e}\n| texte\n" for e in lignes_entete)
    return ("== Candidats déclarés ==\n{| class=\"wikitable sortable\"\n"
            "! colspan=\"3\" scope=\"col\" | Candidat\n" + corps + "|}\n")


def test_section1_29_candidats_tous_extraits(section1):
    (dec, ret) = section1["candidature_lecture"]
    assert (dec["revision"], dec["lignes"], dec["extraits"], dec["non_extraits"]) == (240980797, 29, 29, 0)
    assert ret["section_trouvee"] is False and ret["lignes"] == 0
    c = section1["candidature"]
    assert len(c) == 29 and {x["statut"] for x in c} == {"declaree"}
    assert sum(x["article"] is not None for x in c) == 24       # mesure du 04/11 : 24 articles


def test_formes_de_nom(section1):
    c = {x["nom"]: x for x in section1["candidature"]}
    a = c["Nathalie Arthaud"]                                   # ! {{TriNom|Nathalie|Arthaud}}
    assert (a["forme_nom"], a["prenom"], a["nom_famille"], a["article"], a["article_existe"]) == (
        "TriNom", "Nathalie", "Arthaud", "Nathalie Arthaud", True)
    assert c["Olivier Becht"]["forme_nom"] == "TriNom"          # !{{TriNom|…}} sans espace
    g = c["Raphaël Glucksmann"]                                 # ![[Raphaël Glucksmann]]
    assert (g["forme_nom"], g["article"], g["prenom"]) == ("lien", "Raphaël Glucksmann", None)
    sans = {n for n, x in c.items() if x["forme_nom"] == "TriNom nolink"}
    assert sans == {"Selma Labib", "Mira Markovic", "Benoît Mathieu", "Manolo Mlekuz", "Gilles Platret"}
    assert all(c[n]["article"] is None and c[n]["personne_source"] == n for n in sans)
    assert c["Marine Le Pen"]["nom_famille"] == "Le Pen"


def test_dates_de_declaration(section1):
    c = {x["nom"]: x for x in section1["candidature"]}
    assert (c["Nathalie Arthaud"]["date_declaration"], c["Nathalie Arthaud"]["date_declaration_texte"]) == (
        "2025-12-08", "8 décembre 2025")                       # Le {{date|8 décembre 2025}}, elle annonce…
    assert c["Sylvain Durif"]["date_declaration"] == "2026-08-23"          # {{date|23/08/2026}}
    assert c["Mira Markovic"]["date_declaration"] == "2026-10-02"          # {{date|2|10|2026}}
    assert c["François Ruffin"]["date_declaration"] == "2025-04-01"        # {{Date|01|04|2025}}
    assert c["Benoît Mathieu"]["date_declaration"] == "2026-03-30"         # date en clair
    assert c["Olivier Becht"]["date_declaration"] == "2026-09-24"          # « se déclare candidat »
    assert c["Bruno Retailleau"]["date_declaration"] == "2026-04-19"       # « est désigné candidat »
    # Deux dates dans la phrase : celle qui suit « officialise sa candidature ».
    assert c["Nicolas Dupont-Aignan"]["date_declaration"] == "2026-09-19"
    for n in ("Marine Le Pen", "Éric Zemmour", "Manolo Mlekuz"):           # rien de daté
        assert c[n]["date_declaration"] is None and c[n]["date_declaration_raison"] == "non connue"


def test_references_et_revision(section1):
    c = {x["nom"]: x for x in section1["candidature"]}
    a = c["Nathalie Arthaud"]
    assert a["nb_references"] == 3 and len(a["references"]) == 3
    assert a["references"][0].startswith("https://www.rtl.fr/")
    assert a["revision"] == 240980797
    assert a["prov_url"].endswith("&oldid=240980797#Candidats_d%C3%A9clar%C3%A9s")
    assert c["Jean-Luc Mélenchon"]["nb_references"] == 15


def test_page_entiere_avec_candidatures_retirees_forme_1():
    texte = "Intro.\n\n" + _section_declares(["! {{TriNom|Gabriel|Attal}}<br>(37 ans)"]) + RETIREES
    r = _lire(_reponse(texte, v1=True))                       # wikitext: {"*": …}
    dec, ret = r["candidature_lecture"]
    assert (dec["extraits"], ret["section_trouvee"], ret["lignes"], ret["extraits"]) == (1, True, 2, 2)
    c = {x["nom"]: x for x in r["candidature"]}
    au = c["Clémentine Autain"]
    assert (au["statut"], au["article"], au["forme_nom"]) == ("retiree", "Clémentine Autain", "lien")
    # « en mars 2025 » : date incomplète, pas la date du retrait qui suit.
    assert (au["date_declaration"], au["date_declaration_texte"], au["date_declaration_raison"]) == (
        None, "mars 2025", "date incomplète")
    assert au["references"] == ["https://www.lemonde.fr/politique/article/2025/03/07/x.html"]
    lu = c["Benjamin Lucas-Lundy"]
    assert lu["date_declaration"] == "2026-05-15"
    assert lu["references"] == [] and lu["references_nommees"] == ["tf1"] and lu["nb_references"] == 1
    assert lu["article_existe"] is None                         # pas de liste `links` dans la réponse


def test_formes_inconnues_comptees_pas_devinees():
    entetes = ["! {{TriNom|Gabriel|Attal}}<br>(37 ans)",
               "! {{TriNom|Jean|Dupont|lien=Jean Dupont (homme politique)}}<br>(50 ans)",
               "! Jean Martin<br>(50 ans)",                         # nom en clair : non extrait
               "! {{Nom|Paul|Durand}}<br>(40 ans)",                 # autre modèle : non extrait
               "! {{TriNom|Seul}}<br>",                             # TriNom incomplet : non extrait
               "! [[Fichier:Photo.jpg|80px]]"]                      # pas un nom
    r = _lire(_reponse(_section_declares(entetes)))
    (dec, _) = r["candidature_lecture"]
    assert (dec["lignes"], dec["extraits"], dec["non_extraits"]) == (6, 2, 4)
    assert dec["exemples"][0] == "Jean Martin"
    d = {x["nom"]: x for x in r["candidature"]}
    assert d["Jean Dupont"]["article"] == "Jean Dupont (homme politique)"
    assert d["Jean Dupont"]["personne_source"] == "Jean Dupont (homme politique)"


def test_section_absente_illisible():
    with pytest.raises(ValueError):
        _lire(_reponse("== Autre chose ==\ntexte\n"))
    with pytest.raises(ValueError):
        _lire(orjson.dumps({"error": {"code": "missingtitle"}}))


def test_entrepot_lecture_et_export(tmp_path):
    e = Entrepot(str(tmp_path / "e"))
    e.versionner(PA_WP, "R1", depaqueter(EXTRAIT, "api_json", uid_fixe="candidatures-2027"),
                 complet=True)
    e.clore("test")
    e = Entrepot(str(tmp_path / "e"))
    b = Lecture(e, str(tmp_path / "z2"), CFG).executer(wp)
    assert b["illisibles"] == 0 and b["lignes"]["candidature"] == 29
    sortie = exporter(str(tmp_path / "z2"), [wp], str(tmp_path / "export"))
    assert sortie["cles_en_double"] == 0 and sortie["faits_par_type"]["candidature"] == 29
