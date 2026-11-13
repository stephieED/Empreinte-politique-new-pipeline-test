"""R-QAG : question posée en séance ↔ prises de parole (décision Q38 du 13/11/2026).

Tables construites à la main, sur le modèle des cas mesurés le 13/11/2026 dans les données réelles
(questions de la XVIIe et de la XVe, comptes rendus de la XVe à la XVIIe) :

- QG390 (XVIIe) : publiée au JO le 12/02/2025, posée en séance le 11/02 : un jour d'écart ;
- XVe : date au format JJ/MM/AAAA, `analyses` vide, titre dans l'en-tête du bloc JO seulement ;
- QG1610 et QG1611 : deux députés sous un même intitulé, dans un même point ; un des deux
  interrompt l'autre ;
- cas sans lien : intitulé différent, auteur absent, séance non lue, deux comptes rendus à égalité.
"""
import os

import pyarrow as pa
import pyarrow.parquet as pq

from empreinte_src.liaison import Contexte, relier
from empreinte_src.regles import r_qag


def _bloc(titre):
    return (f'</p><p align="CENTER"> {titre} <a name=PG17></a> </p><br><strong>Mme la présidente . '
            '</strong>La parole est à…')


def _q(uid, auteur, date, titre_jo=None, analyse=None, type_="QG", leg="17"):
    return {"uid": uid, "type": type_, "legislature": leg, "auteur": auteur, "date_reponse": date,
            "analyses": [analyse] if analyse else [], "texte_reponse": _bloc(titre_jo) if titre_jo else None,
            "prov_point": "an-questions", "prov_uid": uid, "prov_version": 1, "prov_etat": "present"}


# (compte rendu, date, point, titre, [(id_syceron, ordre, acteur, preside, interruption, qualite)])
CR = [
    ("CR98", "2025-02-11", "P196", "Continuité territoriale pour les fonctionnaires et militaires ultramarins",
     [("196a", 1, "PA-PRES", True, False, None), ("197", 2, "PA721110", False, False, "depute"),
      ("198", 3, "PA267622", False, False, "membre_du_gouvernement")]),
    ("CR89", "2026-06-02", "P573", "Violences en marge de la finale de la Ligue des champions",
     [("10", 10, "PA-PRES", True, False, None), ("11", 11, "PA795912", False, False, "depute"),
      ("12", 12, "PA842311", False, True, "depute"),                 # interruption de l'autre auteur
      ("13", 13, "PA759834", False, False, "membre_du_gouvernement"),
      ("14", 14, "PA-PRES", True, False, None), ("15", 15, "PA842311", False, False, "depute"),
      ("16", 16, "PA759834", False, False, "membre_du_gouvernement")]),
    ("CR-XV", "2021-03-30", "P22", "Statut des infirmiers anesthésistes",
     [("22a", 1, "PA-DAVID", False, False, "depute"), ("22b", 2, "PA-VERAN", False, False, "membre_du_gouvernement")]),
    ("CR-A", "2026-01-20", "PA1", "Pesticides", [("a1", 1, "PA-X", False, False, "depute")]),
    ("CR-B", "2026-01-20", "PB1", "Pesticides", [("b1", 1, "PA-X", False, False, "depute")]),
    ("CR-C", "2026-02-03", "PC1", "Budget", [("c1", 1, "PA-Y", False, False, "depute")]),
    ("CR-D", "2026-02-10", "PD1", "Autre sujet", [("d1", 1, "PA-W", False, False, "depute")]),
]

QUESTIONS = [
    _q("QG390", "PA721110", "2025-02-12", "CONTINUITÉ TERRITORIALE POUR LES FONCTIONNAIRES ET MILITAIRES ULTRAMARINS",
       "Continuité territoriale pour les fonctionnaires et militaires ultramarins"),
    _q("QG1610", "PA795912", "2026-06-03", "VIOLENCES EN MARGE DE LA FINALE DE LA LIGUE DES CHAMPIONS"),
    _q("QG1611", "PA842311", "2026-06-03", "VIOLENCES EN MARGE DE LA FINALE DE LA LIGUE DES CHAMPIONS"),
    _q("QG-XV", "PA-DAVID", "31/03/2021", "STATUT DES INFIRMIERS ANESTHÉSISTES", leg="15"),
    _q("QG-AMB", "PA-X", "2026-01-21", "PESTICIDES"),
    _q("QG-DIFF", "PA-Y", "2026-02-04", "LOI DE FINANCES POUR 2026"),
    _q("QG-ABS", "PA-Z", "2026-02-11", "AUTRE SUJET"),
    _q("QG-LOIN", "PA-W", "2026-02-25", "AUTRE SUJET"),                 # séance 15 jours avant
    _q("QG-SANS", "PA-W", None, "AUTRE SUJET"),
    _q("QG-NOTITRE", "PA-W", "2026-02-11"),
    _q("QOSD7", "PA-DAVID", "2021-03-31", "STATUT DES INFIRMIERS ANESTHÉSISTES", type_="QOSD", leg="15"),
    _q("QE1", "PA-W", "2026-02-11", "AUTRE SUJET", type_="QE"),
]


def _ecrire(dossier, nom, rows):
    os.makedirs(dossier, exist_ok=True)
    pq.write_table(pa.Table.from_pylist(rows), os.path.join(dossier, f"{nom}.parquet"))


def _contexte(tmp_path, questions=QUESTIONS, qualite=True):
    z2, z3e = str(tmp_path / "z2"), str(tmp_path / "z3e")
    _ecrire(z2, "an_questions__question", questions)
    suj, att, inter, qual = [], [], [], []
    for cr, date, point, titre, pars in CR:
        for ids, ordre, acteur, preside, interruption, q in pars:
            url = f"https://www.assemblee-nationale.fr/dyn/17/comptes-rendus/seance/{cr}#{ids}"
            suj.append({"compte_rendu": cr, "id_syceron": ids, "seance": "RU" + cr, "date": date,
                        "type_sujet": "question", "point": point, "sujet_publie": titre, "source_url": url})
            att.append({"compte_rendu": cr, "id_syceron": ids, "acteur": acteur, "preside": preside,
                        "interruption": interruption})
            inter.append({"compte_rendu": cr, "id_syceron": ids, "ordre_absolu_seance": ordre,
                          "prov_point": "an-cr", "prov_uid": cr, "prov_version": 1, "prov_etat": "present"})
            qual.append({"compte_rendu": cr, "id_syceron": ids, "qualite": q})
    _ecrire(z2, "an_comptes_rendus__intervention", inter)
    _ecrire(z3e, "sujet_intervention", suj)
    _ecrire(z3e, "intervention_attribuee", att)
    if qualite:
        _ecrire(z3e, "qualite_orateur", qual)
    ctx = Contexte(z2, str(tmp_path / "z3"))
    for t in ("sujet_intervention", "intervention_attribuee") + (("qualite_orateur",) if qualite else ()):
        ctx.x(f"CREATE VIEW {t} AS SELECT * FROM read_parquet('{z3e}/{t}.parquet')")
    bilan = relier(ctx, [r_qag])
    rows = ctx.con.execute("SELECT * FROM question_reponse_parole").fetchall()
    cols = [d[0] for d in ctx.con.description]
    return {r[0]: dict(zip(cols, r)) for r in rows}, bilan[0]


def test_question_appariee_la_veille_de_sa_publication(tmp_path):
    q, _ = _contexte(tmp_path)
    r = q["QG390"]
    assert (r["statut"], r["raison"], r["date_jo"], r["date_seance"]) == ("appariee", None, "2025-02-12", "2025-02-11")
    assert (r["compte_rendu"], r["points"], r["type"]) == ("CR98", ["P196"], "au_gouvernement")
    assert r["interventions"] == ["196a", "197", "198"]
    assert r["intervenants"] == [{"acteur": "PA267622", "qualite": "membre_du_gouvernement"}]
    assert r["source_url"].endswith("CR98#197")                        # premier paragraphe de l'auteur
    assert r["titre_jo"] == "CONTINUITÉ TERRITORIALE POUR LES FONCTIONNAIRES ET MILITAIRES ULTRAMARINS"


def test_xve_date_jj_mm_aaaa_et_titre_du_seul_en_tete(tmp_path):
    q, _ = _contexte(tmp_path)
    assert (q["QG-XV"]["statut"], q["QG-XV"]["date_jo"], q["QG-XV"]["date_seance"]) == (
        "appariee", "2021-03-31", "2021-03-30")
    assert q["QOSD7"]["statut"] == "appariee" and q["QOSD7"]["type"] == "orale_sans_debat"


def test_point_partage_decoupe_par_auteur_et_interruption_ecartee(tmp_path):
    q, _ = _contexte(tmp_path)
    a, b = q["QG1610"], q["QG1611"]
    assert a["statut"] == b["statut"] == "appariee"
    # L'interruption de PA842311 (12) ne fait pas commencer sa question : elle reste dans celle de
    # PA795912 ; la question de PA842311 commence à sa vraie prise de parole (15).
    assert a["interventions"] == ["10", "11", "12", "13", "14"]
    assert b["interventions"] == ["15", "16"]
    assert a["intervenants"] == b["intervenants"] == [{"acteur": "PA759834", "qualite": "membre_du_gouvernement"}]
    assert b["source_url"].endswith("#15")


def test_raisons_de_non_appariement(tmp_path):
    q, b = _contexte(tmp_path)
    raisons = {k: v["raison"] for k, v in q.items() if v["statut"] == "non_appariee"}
    assert raisons == {"QG-AMB": "ambigu", "QG-DIFF": "intitule_different", "QG-ABS": "auteur_sans_parole",
                       "QG-LOIN": "seance_non_lue", "QG-SANS": "sans_date", "QG-NOTITRE": "titre_non_publie"}
    assert "QE1" not in q                                               # questions écrites hors règle
    assert all(v["compte_rendu"] is None and v["interventions"] is None
               for v in q.values() if v["statut"] == "non_appariee")
    c = b["couverture"]
    assert c["question_appariee_toutes"] == [5, 11]
    # Le dénominateur ne compte que les questions dont la fenêtre contient un compte rendu lu.
    assert c["question_appariee"] == [5, 8]
    assert c["appariee_orale_sans_debat"] == [1, 1]


def test_doublon_de_la_source_et_sans_r_qualite(tmp_path):
    q, _ = _contexte(tmp_path, QUESTIONS + [dict(QUESTIONS[0])], qualite=False)
    assert q["QG390"]["statut"] == "appariee"
    assert q["QG390"]["intervenants"] == [{"acteur": "PA267622", "qualite": None}]
