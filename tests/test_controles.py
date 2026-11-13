"""Contrôles bloquants (E6) : C1, C2, C4, C6 et la levée ciblée."""
import pyarrow as pa
import pyarrow.parquet as pq

from empreinte_src.composition import Ecrivain
from empreinte_src.controles import Controles


def _faits(p, lignes):
    pq.write_table(pa.Table.from_pylist(lignes), p)
    return str(p)


def _f(fiche, section, valeur):
    return {"fiche": fiche, "section": section, "type_fait": "t", "valeur": valeur}


def test_c1_perte_non_expliquee_puis_levee(tmp_path):
    avant = _faits(tmp_path / "a.parquet", [_f("legislature/17", "textes", '{"dossier":"DLR1"}'),
                                            _f("legislature/17", "textes", '{"dossier":"DLR2"}')])
    apres = _faits(tmp_path / "b.parquet", [_f("legislature/17", "textes", '{"dossier":"DLR1"}')])
    c = Controles(str(tmp_path))
    c.c1_c6_comparer(avant, apres)
    b = c.bilan()
    assert not b["publication_autorisee"] and b["anomalies"][0]["controle"] == "C1"
    # La source a modifié DLR2 cette nuit : la perte est expliquée.
    c = Controles(str(tmp_path))
    c.c1_c6_comparer(avant, apres, uids_changes_a_la_source={"DLR2"})
    assert c.bilan()["publication_autorisee"]
    # Levée par décision, pour cette anomalie précise.
    e = b["anomalies"][0]["empreinte"]
    c = Controles(str(tmp_path), levees=[{"empreinte": e, "fichier": "decisions/levee/x.yaml"}])
    c.c1_c6_comparer(avant, apres)
    assert c.bilan()["publication_autorisee"]
    assert c.bilan()["anomalies"][0]["levee_par"] == "decisions/levee/x.yaml"


def test_c6_effondrement(tmp_path):
    avant = _faits(tmp_path / "a.parquet", [_f("g/x", "actes", f'{{"i":{i}}}') for i in range(20)])
    apres = _faits(tmp_path / "b.parquet", [_f("g/x", "actes", f'{{"i":{i}}}') for i in range(5)])
    c = Controles(str(tmp_path))
    c.c1_c6_comparer(avant, apres, uids_changes_a_la_source=None)
    assert {a["controle"] for a in c.anomalies} == {"C1", "C6"}


def test_c2_et_c4_sur_les_fichiers_servis(tmp_path):
    ecr = Ecrivain(str(tmp_path), "p1")
    f = ecr.fiche("legislature", "17", "XVIIe législature")
    f.section("gouvernements", [{"nom": "Bayrou", "lien": "gouvernement/bayrou"}], type_fait="g")
    f.section("deputes", [{"acteur": "PA1", "taux_de_presence": 0.9}], type_fait="d")
    ecr.clore()
    c = Controles(ecr.racine)
    c.c2_liens({"legislature/17"})
    c.c4_interdits()
    assert {a["controle"] for a in c.anomalies} == {"C2", "C4"}
    assert not c.bilan()["publication_autorisee"]


def test_c5_section_complete_avec_source_en_panne(tmp_path):
    ecr = Ecrivain(str(tmp_path), "p1")
    f = ecr.fiche("legislature", "17", "XVIIe législature")
    f.section("textes", [{"dossier": "DLR1"}], type_fait="t",
              couverture={"statut": "complet", "points_acces": ["an-dossiers-l17"]})
    ecr.clore()
    c = Controles(ecr.racine)
    c.c5_couverture([{"point_acces": "an-dossiers-l17", "issue": "echec"}])
    assert [a["controle"] for a in c.anomalies] == ["C5"]   # section et en-tête : une seule anomalie
    c = Controles(ecr.racine)
    c.c5_couverture([{"point_acces": "an-dossiers-l17", "issue": "inchange"}])
    assert not c.anomalies


def test_source_en_panne_la_section_le_dit_et_la_publication_continue(tmp_path):
    """Scénario 2 de la commande : le Sénat ne répond plus ; la section « fonctions » qui en dépend
    passe en « panne », datée, et C5 ne bloque pas (constaté le 07/11/2026 : export du Sénat de
    444 octets, publication refusée faute de ce marquage)."""
    import gzip
    import json
    import os
    releve = {"point_acces": "senat-export", "issue": "suspect", "debut": "2026-11-07T06:55:26+00:00"}
    ecr = Ecrivain(str(tmp_path), "g000003", pannes={"senat-export": "2026-11-07T06:55:26+00:00"})
    f = ecr.fiche("candidat", "x", "X")
    f.section("fonctions", [{"a": 1}], "fonction",
              couverture={"famille": "fonctions", "statut": "complet", "detail": "Mandats.",
                          "points_acces": ["an-amo30-l17", "senat-export"]})
    f.section("votes", [{"a": 1}], "vote",
              couverture={"famille": "votes", "statut": "complet", "points_acces": ["an-scrutins-l17"]})
    ecr.clore()
    with gzip.open(os.path.join(ecr.racine, "candidats", "x", "fonctions.json.gz")) as fi:
        c = json.load(fi)["couverture"]
    assert (c["statut"], c["statut_sans_panne"], c["points_en_panne"]) == ("panne", "complet", ["senat-export"])
    assert c["panne_depuis"].startswith("2026-11-07") and "Source en panne depuis le 2026-11-07" in c["detail"]
    with gzip.open(os.path.join(ecr.racine, "candidats", "x", "fiche.json.gz")) as fi:
        entete = {x["section"]: x["statut"] for x in json.load(fi)["couverture"]}
    assert entete == {"fonctions": "panne", "votes": "complet"}
    ctrl = Controles(ecr.racine)
    ctrl.c5_couverture([releve])
    assert ctrl.bilan()["publication_autorisee"], ctrl.bilan()


def test_c1_reconnait_un_fait_a_son_identite_pas_a_sa_valeur(tmp_path):
    """08/11/2026 : les comptes datés (« au ») changeaient de valeur chaque nuit et passaient pour
    perdus. 11/11/2026 : des actes réellement disparus. Le premier n'est pas une perte, le second
    en est une."""
    def fait(fiche, section, type_fait, valeur, **ids):
        r = {"fiche": fiche, "section": section, "type_fait": type_fait, "valeur": valeur}
        r.update({f"id_{k}": v for k, v in ids.items()})
        return r
    avant = [fait("candidat/x", "entete", "compte_candidat", '{"famille":"mandats","valeur":3,"au":"2026-11-07"}',
                  acteur="PA1", autre="mandats"),
             fait("gouvernement/g", "actes-2026-10", "acte", '{"acte":"JORFTEXT1"}', acte="JORFTEXT1"),
             fait("gouvernement/g", "actes", "actes_compte", '{"nature":"DECRET","nb_actes":4,"au":"2026-11-07"}')]
    apres = [fait("candidat/x", "entete", "compte_candidat", '{"famille":"mandats","valeur":3,"au":"2026-11-08"}',
                  acteur="PA1", autre="mandats"),
             fait("gouvernement/g", "actes", "actes_compte", '{"nature":"DECRET","nb_actes":4,"au":"2026-11-08"}')]
    schema = pa.schema([(c, pa.string()) for c in ("fiche", "section", "type_fait", "valeur", "id_acteur",
                                                    "id_acte", "id_autre")])
    pa_ = str(tmp_path / "a.parquet")
    pb = str(tmp_path / "b.parquet")
    pq.write_table(pa.Table.from_pylist(avant, schema=schema), pa_)
    pq.write_table(pa.Table.from_pylist(apres, schema=schema), pb)
    c = Controles(str(tmp_path))
    c.c1_c6_comparer(pa_, pb)
    a = [x for x in c.anomalies if x["controle"] == "C1"]
    assert len(a) == 1 and a[0]["nb_objets"] == 1 and "JORFTEXT1" in a[0]["exemples"][0]


def test_c1_decompte_dont_la_case_se_vide_n_est_pas_une_perte(tmp_path):
    """13/11/2026 : des amendements de 2026 reçoivent leur commission à la source ; la ligne de
    décompte « commission non établie, 2026 » disparaît, ses nombres passent sur la commission.
    Les amendements eux-mêmes restent vérifiés un par un : leur perte, elle, bloque."""
    def fait(type_fait, valeur, **ids):
        r = {"fiche": "lignee/x", "section": "amendements", "type_fait": type_fait, "valeur": valeur}
        r.update({f"id_{k}": v for k, v in ids.items()})
        return r
    avant = [fait("amendements_compte_lignee", '{"commission":null,"annee":"2026","nb_amendements":122}', autre="2026"),
             fait("amendements_compte_lignee", '{"commission":"PO1","annee":"2026","nb_amendements":507}',
                  organe="PO1", autre="2026"),
             fait("amendement_lignee", '{"amendement":"AM1"}', amendement="AM1"),
             fait("amendement_lignee", '{"amendement":"AM2"}', amendement="AM2")]
    apres = [fait("amendements_compte_lignee", '{"commission":"PO1","annee":"2026","nb_amendements":629}',
                  organe="PO1", autre="2026"),
             fait("amendement_lignee", '{"amendement":"AM1"}', amendement="AM1")]
    schema = pa.schema([(c, pa.string()) for c in ("fiche", "section", "type_fait", "valeur", "id_organe",
                                                    "id_amendement", "id_autre")])
    pa_, pb = str(tmp_path / "a.parquet"), str(tmp_path / "b.parquet")
    pq.write_table(pa.Table.from_pylist(avant, schema=schema), pa_)
    pq.write_table(pa.Table.from_pylist(apres, schema=schema), pb)
    c = Controles(str(tmp_path))
    c.c1_c6_comparer(pa_, pb)
    a = [x for x in c.anomalies if x["controle"] == "C1"]
    assert len(a) == 1 and a[0]["nb_objets"] == 1 and "AM2" in a[0]["exemples"][0]


def test_faits_publies_ecrits_au_fil_de_l_eau(tmp_path):
    """Avec `chemin_faits`, l'Ecrivain ne garde en mémoire qu'un lot de faits : les autres sont déjà
    dans le Parquet, et le fichier final est le même qu'en une fois (mémoire : ≈ 2 millions de faits
    sur le périmètre complet)."""
    chemin = str(tmp_path / "export" / "faits-publies.parquet")
    ecr = Ecrivain(str(tmp_path / "site"), "p1", chemin_faits=chemin, lot_faits=2)
    f = ecr.fiche("legislature", "17", "XVIIe législature")
    lignes = [{"scrutin": f"VT{k}", "date": "2025-01-0" + str(k), "source_url": None} for k in range(1, 6)]
    f.section("votes", lignes, "vote", ids={"scrutin": "scrutin"}, date="date")
    assert len(ecr.faits) <= 2                                   # un lot au plus en mémoire
    ecr.clore()
    assert ecr.ecrire_faits_publies() == 5
    t = pq.read_table(chemin).to_pylist()
    assert [x["id_scrutin"] for x in t] == ["VT1", "VT2", "VT3", "VT4", "VT5"]
    # Même contenu que l'écriture en une fois.
    ecr2 = Ecrivain(str(tmp_path / "site2"), "p1")
    ecr2.fiche("legislature", "17", "XVIIe législature").section("votes", lignes, "vote",
                                                                ids={"scrutin": "scrutin"}, date="date")
    ecr2.clore()
    assert ecr2.ecrire_faits_publies(str(tmp_path / "une-fois.parquet")) == 5
    assert pq.read_table(str(tmp_path / "une-fois.parquet")).to_pylist() == t
