"""Lecteur `senat_export` : extrait réel du dump `export_sens.sql` du 04/11/2026, quatre
sénateurs (fiche `tests/extraits/senat_export.md`)."""
import os
import zipfile

import pytest

from empreinte_src.depaquetage import depaqueter
from empreinte_src.entrepot import Entrepot
from empreinte_src.export import exporter
from empreinte_src.lecture import Lecture, MembreLu
from empreinte_src.lecteurs import senat_export

EXTRAIT = os.path.join(os.path.dirname(__file__), "extraits", "senat_export_extrait.zip")
PA_SENAT = {"id": "senat-export", "source": "senat", "type": "export_sens", "format": "zip",
            "url": "http://exemple.invalid/export_sens.zip"}
CFG = {"points_acces": [{"id": "senat-export", "licence": "etalab-2.0"}]}


@pytest.fixture(scope="module")
def lu():
    with zipfile.ZipFile(EXTRAIT) as z:
        octets = z.read("export_sens.sql")
    return senat_export.lire(MembreLu("senat-export", "senat", "export_sens", "export_sens",
                                      "export_sens.sql", 1, "e", octets, "etalab-2.0"))


def _par_uid(lu, table):
    return {r["uid"]: r for r in lu[table]}


def test_identite(lu):
    i = _par_uid(lu, "identite_source")
    assert set(i) == {"senat:86039K", "senat:04033B", "senat:11027H", "senat:86034E"}
    m = i["senat:86039K"]
    assert (m["civilite"], m["prenom"], m["nom"]) == ("M.", "Jean-Luc", "Mélenchon")
    assert (m["date_naissance"], m["date_deces"], m["etat"]) == ("1951-08-19", None, "ANCIEN")
    assert m["feminin"] is False and m["profession"] == "Cadre administratif"
    c = i["senat:11027H"]
    assert c["feminin"] is True and c["nom_technique"] == "CONWAY_MOURET_HELENE"
    assert c["etat"] == "ACTIF" and c["uri_hatvp"].startswith("http://www.hatvp.fr/")
    assert "senema" not in c and "email" not in c        # courriel jamais lu


def test_mandats_de_senateur(lu):
    m = _par_uid(lu, "mandat")
    x = m["senat:elusen:399"]
    assert (x["acteur"], x["nature"], x["type_mandat"]) == ("senat:86039K", "mandat", "SENAT")
    assert (x["date_debut"], x["date_election"], x["date_fin"]) == ("1995-10-02", "1995-09-24", "2000-04-27")
    assert (x["cause_debut_code"], x["cause_fin_code"]) == ("REN1", "CESMEMGVT")
    assert x["cause_fin"] == "Devenu membre du Gouvernement"
    assert (x["circonscription_code"], x["circonscription"]) == ("265", "Essonne")
    assert m["senat:elusen:10907"]["evenement"] == "Elu député européen"


def test_groupe_politique_avec_libelle_a_la_date(lu):
    m = _par_uid(lu, "mandat")
    crc = m["senat:memgrppol:2081"]
    assert (crc["organe"], crc["qualite_code"], crc["qualite"]) == ("senat:grppol:CRC", "N", "Membre")
    assert (crc["date_debut"], crc["date_fin"]) == ("2008-11-28", "2010-01-07")
    # Le libellé est celui de 2008 (CRC-SPG), pas l'actuel (CRCE - Kanaky).
    assert (crc["libelle_organe"], crc["libelle_organe_court"]) == ("Groupe CRC-SPG", "CRC-SPG")
    assert crc["date_libelle"] == "2008-11-28"
    o = _par_uid(lu, "organe")["senat:grppol:CRC"]
    assert o["libelle"] == "Groupe CRCE - Kanaky" and o["type_organe"] == "GRPPOL"
    # Sans date de début, le libellé est lu à la date de fin, et la colonne le dit.
    soc = m["senat:memgrppol:67"]
    assert soc["date_debut"] is None and soc["date_libelle"] == "2000-04-27"
    assert soc["libelle_organe"] == "Groupe socialiste"
    # La fonction dans le groupe est une ligne à part, rattachée à son appartenance.
    f = m["senat:fonmemgrppol:2354"]
    assert (f["nature"], f["appartenance"], f["acteur"], f["qualite"]) == (
        "fonction", "senat:memgrppol:2081", "senat:86039K", "Membre")
    libs = [l for l in lu["organe_libelle"] if l["organe"] == "senat:grppol:CRC"]
    assert len(libs) >= 3


def test_commissions_et_bureau(lu):
    m = _par_uid(lu, "mandat")
    com = [x for x in m.values() if x["acteur"] == "senat:86039K" and x["nature"] == "appartenance"
           and x["organe"] == "senat:com:SOCI"]
    assert [(x["date_debut"], x["date_fin"], x["type_organe"]) for x in com] == [
        ("1986-10-06", "1988-06-29", "COM")]
    assert com[0]["libelle_organe"] == "Affaires sociales"
    larcher = [x for x in m.values() if x["acteur"] == "senat:86034E" and x["type_organe"] == "BUREAU"]
    assert "PDTSEN" in {x["qualite_code"] for x in larcher}
    assert {x["qualite"] for x in larcher if x["qualite_code"] == "PDTSEN"} == {"Président"}
    pres = [x for x in m.values() if x["nature"] == "fonction" and x["qualite_code"] == "PDTCOM"]
    assert all(x["appartenance"] and x["organe"].startswith("senat:com:") for x in pres)
    o = _par_uid(lu, "organe")["senat:com:SOCI"]
    assert o["type_organe"] == "COM" and o["libelle_long"] == "COMMISSION DES AFFAIRES SOCIALES"


def test_libelles_resserres_et_vides(lu):
    f = [x for x in lu["mandat"] if x["qualite_code"] == "MEMBRECOM"]
    assert f and all(x["qualite"] == "Membre" for x in f)     # foncomlib fait d'espaces : non lu
    assert all(v is None or v == v.strip() for r in lu["organe"] for v in r.values()
               if isinstance(v, str))


def test_tables_hors_liste_blanche_sautees():
    """Une table hors liste blanche (ici `typorg`, réelle) et une table de présence (bloc
    fictif, aucune donnée de personne) ne sont jamais rendues."""
    with zipfile.ZipFile(EXTRAIT) as z:
        octets = z.read("export_sens.sql")
    assert b"COPY typorg " in octets
    fictif = (b"COPY activite_participant (actparid, senmat) FROM stdin;\n1\tFICTIF\n\\.\n")
    t = senat_export.tables_du_dump(octets + fictif)
    assert "typorg" not in t and "activite_participant" not in t
    assert "activite_participant" in senat_export.JAMAIS and not senat_export.LUES & senat_export.JAMAIS


def test_echappements_copy():
    assert senat_export._desechapper(r"a\tb\\c\nd\101") == "a\tb\\c\ndA"
    t = senat_export.tables_du_dump(b"COPY dpt (dptnum, dptlib) FROM stdin;\n1\t\\N\n2\tx\\ty\n\\.\n")
    assert t["dpt"] == [{"dptnum": "1", "dptlib": None}, {"dptnum": "2", "dptlib": "x\ty"}]


def test_dump_tronque_illisible():
    with pytest.raises(ValueError):
        senat_export.tables_du_dump(b"COPY sen (senmat) FROM stdin;\n86039K\n")


def test_entrepot_lecture_et_export(tmp_path):
    e = Entrepot(str(tmp_path / "e"))
    e.versionner(PA_SENAT, "R1", depaqueter(EXTRAIT, "zip"), complet=True)
    e.clore("test")
    e = Entrepot(str(tmp_path / "e"))
    b = Lecture(e, str(tmp_path / "z2"), CFG).executer(senat_export)
    assert b["lues"] == 1 and b["illisibles"] == 0 and b["lignes"]["identite_source"] == 4
    sortie = exporter(str(tmp_path / "z2"), [senat_export], str(tmp_path / "export"))
    assert sortie["cles_en_double"] == 0 and sortie["faits_par_type"]["identite_source"] == 4
