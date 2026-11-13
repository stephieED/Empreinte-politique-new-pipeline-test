"""Rapport de mesures (commande, section 5) : chiffres tirés du rapport de chaque nuit."""
import json

from empreinte_src import rapport_mesures as rm


def _rapport(gen, releves, calcul=None, mesures=None, **autres):
    return {"generation": gen, "debut": f"2026-11-0{gen}T20:35:00+00:00", "mode": "quotidien",
            "code": "abc1234def", "releves": releves, "mesures": mesures or [], "calcul": calcul or {},
            "entrepot_octets": 1000 * gen, **autres}


def _rel(point, source="an", issue="nouveau", octets=10, versions=1, membres=5, retraits=0):
    return {"point_acces": point, "source": source, "issue": issue, "complet": issue != "echec",
            "octets_recus": octets, "nb_nouvelles_versions": versions, "nb_membres": membres,
            "nb_retraits": retraits, "duree_s": 0.1}


def test_famille_sans_legislature_et_acteurs_regroupes():
    assert rm.famille("an-amendements-l17") == "an-amendements"
    assert rm.famille("an-amo20-l14") == rm.famille("an-amo30-l17") == "an-acteurs"
    assert rm.famille("jo-livraisons") == "jo-livraisons"


def test_pic_du_calcul_est_le_maximum_des_etapes():
    """`time -v` ne voit que la dernière étape (pic remis à zéro à chaque étape) : constaté le
    13/11/2026, 4 813 Mo en E4 contre 2 683 Mo rapportés par `time -v` (E6)."""
    cal = {"mesures": [{"etape": "E3", "lecteur": "a", "duree_s": 2, "pic_memoire_mo": 1000},
                       {"etape": "E3", "lecteur": "b", "duree_s": 3, "pic_memoire_mo": 1500},
                       {"etape": "E4", "duree_s": 25, "pic_memoire_mo": 4813},
                       {"etape": "E6", "duree_s": 104, "pic_memoire_mo": 2683}]}
    m = rm.mesurer({"rapport": _rapport(1, [], calcul=cal)}, set())
    assert (m["pic_calcul"], m["pic_calcul_etape"]) == (4813, "E4")
    assert m["etapes_calcul"]["E3"] == {"duree_s": 5, "pic": 1500}


def test_premier_releve_compte_a_part_et_livraisons_regroupees():
    vus = set()
    n1 = rm.mesurer({"rapport": _rapport(1, [_rel("jo-livraisons", "dila", versions=7, membres=7),
                                              _rel("jo-livraisons", "dila", versions=3, membres=3),
                                              _rel("an-scrutins-l17", versions=9),
                                              _rel("an-amendements-l16", issue="echec", octets=0, versions=0)],
                                         mesures=[{"etape": "E1-E2", "point_acces": "jo-livraisons", "duree_s": 4},
                                                  {"etape": "E1-E2", "point_acces": "an-amendements-l16", "duree_s": 1800}])},
                    vus)
    assert n1["objets_par_famille"] == {"an-amendements": 0}
    jo = next(p for p in n1["premier_remplissage"] if p["point"] == "jo-livraisons")
    assert (jo["releves"], jo["membres"], jo["duree_s"]) == (2, 10, 4)
    assert n1["pannes"] == ["an-amendements-l16"] and n1["duree_pannes"] == 1800
    n2 = rm.mesurer({"rapport": _rapport(2, [_rel("jo-livraisons", "dila", versions=4),
                                              _rel("an-scrutins-l17", issue="inchange", versions=0, retraits=2)])}, vus)
    assert n2["objets_par_famille"] == {"jo-livraisons": 4, "an-scrutins": 0}
    assert n2["retraits_par_famille"]["an-scrutins"] == 2 and n2["premier_remplissage"] == []


def test_ecritures_poids_des_candidats_et_rendu():
    pub = {"id": "g000002", "faits_publies": 12,
           "fiches": [{"fiche": "candidat/a", "type": "candidat", "entete": {"gz": 5000},
                       "sections": {"votes": {"gz": 1000}, "amendements": {"gz": 500}}},
                      {"fiche": "lignee/x", "type": "lignee", "entete": {"gz": 9}, "sections": {}}]}
    r = _rapport(2, [_rel("an-scrutins-l17")], calcul={"publication": pub, "controles": {"publication_autorisee": False},
                                                         "mesures": [{"etape": "E5", "duree_s": 60, "pic_memoire_mo": 2048}]},
                 ecriture={"envois": [{"actif": "x", "octets": 100, "duree_s": 2, "essais": 2, "reussi": True}]},
                 ecriture_export=[{"actif": "f", "release": "export", "octets": 50, "duree_s": 1, "essais": 1, "reussi": False},
                                  {"actif": "vieux", "release": "export", "retire": True, "reussi": True}])
    m = rm.mesurer({"rapport": r, "execution": {"evenement": "schedule", "taches": [
        {"nom": "collecter", "debut": "2026-11-02T20:35:00Z", "fin": "2026-11-02T20:40:00Z", "conclusion": "success"},
        {"nom": "ecrire", "debut": "2026-11-02T20:50:00Z", "fin": "2026-11-02T20:51:00Z", "conclusion": "success"},
        {"nom": "alerter", "debut": None, "fin": None, "conclusion": "skipped"}]}}, set())
    assert m["ecritures"]["entrepot"]["reessais"] == 1        # sans release : avant le 06/11, tout allait dans `entrepot`
    assert m["ecritures"]["export"] == {"envois": 1, "octets": 50, "duree_s": 1, "duree_max_s": 1,
                                        "reessais": 0, "echecs": 1}
    assert m["poids_candidats"] == [{"fiche": "candidat/a", "initial": 5000, "total": 6500}]
    assert m["duree_totale"] == 16 * 60 and m["fichiers_servis"] == 4
    texte = rm.rendre([m], "o/d", genere_le="13/11/2026")
    assert "| g2 | 02/11 20:35 | nuit |" in texte and "**refusée**" in texte
    assert "`candidat/a` | 5,0 | 6,5 |" in texte


def test_charger_trie_par_generation(tmp_path):
    for run, gen in (("9", 3), ("10", 1)):
        (tmp_path / run).mkdir()
        (tmp_path / run / "rapport.json").write_text(json.dumps(_rapport(gen, [])))
    (tmp_path / "vide").mkdir()
    assert [n["rapport"]["generation"] for n in rm.charger(str(tmp_path))] == [1, 3]
