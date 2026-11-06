"""Lecteur `jo_actes` : membres réels de trois livraisons de la DILA (fiche
`tests/extraits/jo_actes.md`)."""
import os
import tarfile

import pyarrow.parquet as pq

from empreinte.depaquetage import depaqueter
from empreinte.entrepot import Entrepot
from empreinte.export import exporter
from empreinte.lecture import Lecture, MembreLu
from empreinte.lecteurs import jo_actes

EXTRAITS = os.path.join(os.path.dirname(__file__), "extraits")
LIVRAISONS = ["20261102-213929", "20261103-214151", "20261104-004428"]
TARS = {l: os.path.join(EXTRAITS, f"jo_JORF_{l}_extrait.tar.gz") for l in LIVRAISONS}
PA_JO = {"id": "jo-livraisons", "source": "dila", "type": "jorf", "format": "liste_tar",
         "url": "http://exemple.invalid/JORF/",
         # même règle que config/points_acces.yaml : uid qualifié par son dossier, sans l'horodatage
         "qualifier_uid": r"^\d{8}-\d{6}/jorf/global/(?P<q>.+?)/JORF/"}
CFG = {"points_acces": [{"id": "jo-livraisons", "licence": "etalab-2.0"}]}


def _membre(livraison, dossier, id_):
    with tarfile.open(TARS[livraison], "r:gz") as t:
        for info in t:
            if f"/{dossier}/" in info.name and info.name.endswith(f"/{id_}.xml"):
                return info.name, t.extractfile(info).read()
    raise KeyError(id_)


def _lire(livraison, dossier, id_):
    chemin, octets = _membre(livraison, dossier, id_)
    return jo_actes.lire(MembreLu("jo-livraisons", "dila", "jorf", id_, chemin, 1, "e", octets,
                                  "etalab-2.0"))


def test_decret_signataires_ministere_et_liens_vers_des_lois():
    r = _lire("20261102-213929", "texte/version", "JORFTEXT000055037137")
    (a,) = r["acte_reglementaire"]
    assert a["uid"] == "jorf:JORFTEXT000055037137" and a["livraison"] == "20261102-213929"
    assert (a["nature"], a["numero"], a["nor"]) == ("DECRET", "2026-1013", "INTJ2624402D")
    assert (a["date_publication"], a["date_signature"]) == ("2026-10-31", "2026-10-28")
    assert a["date_signature_sentinelle"] is False
    assert a["ministere"] == "Ministère de l'intérieur" and a["autorite"] is None
    assert a["titre_complet"].startswith("Décret n° 2026-1013 du 28 octobre 2026 relatif")
    # SIGNATAIRES : texte libre tel quel, aucun nom n'en est tiré.
    assert a["signataires"].startswith("Fait le 28 octobre 2026.\nSébastien LECORNU")
    assert "Laurent NUNEZ" in a["signataires"] and a["signataires_html"].startswith("<")
    assert a["prov_url"] == "https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000055037137"
    # Seuls les liens vers des textes législatifs sont lus ; le total reste compté.
    liens = r["lien_acte_loi"]
    assert a["nb_liens"] == 22 and a["nb_liens_lus"] == len(liens) == 2
    assert {(l["type_lien"], l["sens"], l["nature_cible"], l["cible_numero"], l["cible_article"])
            for l in liens} == {("CITATION", "source", "LOI", "2015-991", None),
                                ("CITATION", "source", "LOI", "2015-991", "99")}
    assert {l["cible_texte"] for l in liens} == {"JORFTEXT000030985460"}
    assert liens[1]["cible"] == "JORFARTI000030986990"


def test_date_sentinelle_2999_et_signataires_vides():
    (a,) = _lire("20261104-004428", "texte/version", "JORFTEXT000055053883")["acte_reglementaire"]
    assert a["date_signature"] is None and a["date_signature_sentinelle"] is True
    assert a["date_signature_source"] == "2999-01-01" and a["date_publication"] == "2026-11-04"
    assert a["nature"] == "AVIS" and a["numero"] is None and a["signataires"] is None
    assert a["nb_liens"] == 0


def test_loi_sans_ministere():
    (a,) = _lire("20261103-214151", "texte/version", "JORFTEXT000055047268")["acte_reglementaire"]
    assert a["nature"] == "LOI" and a["numero"] == "2026-1015" and a["ministere"] is None


def test_lien_application_et_rectificatif():
    r = _lire("20261102-213929", "texte/version", "JORFTEXT000033703701")
    types = {(l["type_lien"], l["sens"]) for l in r["lien_acte_loi"]}
    assert ("APPLICATION", "source") in types or ("APPLICATION", "cible") in types
    (a,) = _lire("20261102-213929", "texte/version", "JORFTEXT000000721454")["acte_reglementaire"]
    assert a["rectificatif"].startswith("Rectificatif au JO du 27 mai 1992")
    assert a["date_publication"] < "2000"          # texte ancien redélivré : lu tel quel


def test_plan_versions_consolidees_et_sentinelles():
    v = _lire("20261102-213929", "texte/struct", "JORFTEXT000021262661")["version_acte"]
    assert [(x["rang"], x["etat"], x["id_version"]) for x in v] == [
        (0, None, "JORFTEXT000021262661"), (1, "VIGUEUR", "LEGITEXT000042981982"),
        (2, "MODIFIE", "LEGITEXT000021263604")]
    assert v[0]["date_debut"] is None and v[0]["date_debut_sentinelle"] is True
    assert (v[1]["date_debut"], v[1]["date_fin"], v[1]["date_fin_sentinelle"]) == ("2021-01-02", None, True)
    assert (v[2]["date_debut"], v[2]["date_fin"]) == ("2010-01-13", "2021-01-02")
    assert v[0]["nb_articles"] == 11 and v[0]["acte"] == "jorf:JORFTEXT000021262661"


def test_sommaire_rubrique_mesures_nominatives():
    s = _lire("20261104-004428", "conteneur", "JORFCONT000055053315")["sommaire_jo"]
    assert {x["conteneur"] for x in s} == {"JORFCONT000055053315"}
    assert s[0]["num_jo"] == "0258" and s[0]["date_publication"] == "2026-11-04"
    assert s[0]["acte"] == "jorf:JORFTEXT000055053320"
    assert s[0]["rubrique"] == ['Journal officiel "Lois et Décrets"', "Décrets, arrêtés, circulaires",
                                "Textes généraux", "Ministère de l'intérieur"]
    nomin = [x for x in s if "Mesures nominatives" in x["rubrique"]]
    assert nomin and all(x["acte"].startswith("jorf:JORFTEXT") for x in nomin)
    assert [x["rang"] for x in s] == list(range(len(s)))


def test_articles_et_sections_non_lus():
    assert _lire("20261104-004428", "article", "JORFARTI000055053487") == {}
    assert _lire("20261104-004428", "section_ta", "JORFSCTA000055053400") == {}


def test_entrepot_lecture_et_export_sans_cle_en_double(tmp_path):
    """Trois livraisons rangées comme par la collecte (point « delta »). La loi 2025-391
    (`JORFTEXT000051538879`) est redélivrée le 03/11 : l'entrepôt donne à son fichier
    `texte/version` un uid nouveau à chaque livraison ; la clé d'export porte la livraison."""
    e = Entrepot(str(tmp_path / "e"))
    for l in LIVRAISONS:
        e.versionner(PA_JO, f"R-{l}", depaqueter(TARS[l], "liste_tar"), complet=True, delta=True)
    e.clore("test")
    e = Entrepot(str(tmp_path / "e"))
    uids = {r["uid"] for r in e._index if r["uid"].startswith("JORFTEXT000051538879")}
    # Deux membres stables (le plan et la version du texte) ; chaque livraison en est une version.
    assert uids == {"JORFTEXT000051538879@texte-struct", "JORFTEXT000051538879@texte-version"}
    b = Lecture(e, str(tmp_path / "z2"), CFG).executer(jo_actes)
    assert b["illisibles"] == 0
    actes = pq.read_table(tmp_path / "z2" / "jo_actes__acte_reglementaire.parquet").to_pylist()
    # 5 + 2 + 1 fichiers `texte/version`, dont un redélivré à l'identique : même empreinte, pas de version nouvelle
    assert len(actes) == 7
    # Redélivré à l'identique le 03/11 : une seule version, datée de sa première livraison ;
    # la redélivraison prolonge seulement sa présence dans l'entrepôt.
    assert sorted(a["livraison"] for a in actes if a["id_jorf"] == "JORFTEXT000051538879") == [
        "20261102-213929"]
    # Loi 2025-391 en double à la source : deux JORFTEXT, gardés tous deux.
    assert {a["id_jorf"] for a in actes if a["numero"] == "2025-391"} == {
        "JORFTEXT000051538879", "JORFTEXT000051575460"}
    assert all(a["licence"] == "etalab-2.0" and a["prov_etat"] == "present" for a in actes)
    sortie = exporter(str(tmp_path / "z2"), [jo_actes], str(tmp_path / "export"))
    assert sortie["cles_en_double"] == 0
    # Un fait par acte : la dernière livraison d'un texte fait foi.
    assert sortie["faits_par_type"]["acte_reglementaire"] == len({a["id_jorf"] for a in actes})


def test_liste_de_suppressions():
    """Contenu recopié de la liste de la livraison `20261020-214622` (entrepôt du 06/11/2026 ;
    aucune des trois livraisons de `travail/sources/` n'en porte)."""
    octets = (b"jorf/global/section_ta/JORF/SCTA/00/00/00/90/33/JORFSCTA000000903358\n"
              b"jorf/global/section_ta/JORF/SCTA/00/00/00/90/33/JORFSCTA000000903359\n"
              b"jorf/global/section_ta/JORF/SCTA/00/00/00/90/33/JORFSCTA000000903360\n"
              b"jorf/global/article/JORF/ARTI/00/00/01/69/13/JORFARTI000001691372\n"
              b"null/JORFDOLE000055000812\n")
    s = jo_actes.lire(MembreLu("jo-livraisons", "dila", "jorf", "liste_suppression_jorf.dat",
                               "20261020-214622/liste_suppression_jorf.dat", 1, "e", octets,
                               "etalab-2.0"))["suppression_jo"]
    assert len(s) == 5 and {x["livraison"] for x in s} == {"20261020-214622"}
    assert (s[3]["dossier"], s[3]["id_jorf"], s[3]["prefixe"]) == (
        "jorf/global/article/JORF/ARTI/00/00/01/69/13", "JORFARTI000001691372", "JORFARTI")
    assert (s[4]["dossier"], s[4]["id_jorf"], s[4]["prefixe"]) == ("null", "JORFDOLE000055000812", "JORFDOLE")
