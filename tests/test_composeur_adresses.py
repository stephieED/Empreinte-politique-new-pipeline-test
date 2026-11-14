"""Adresses de fiches citées par des articles publiés (issue #86) : servies dans le catalogue."""
import gzip
import json
import os

import yaml

from empreinte_src.composeurs import adresses
from empreinte_src.composition import Ecrivain
from empreinte_src.controles import Controles
from empreinte_src.liaison import Contexte


def _contexte(tmp_path, decisions):
    d = tmp_path / "decisions" / "adresse_citee"
    d.mkdir(parents=True)
    (d / "articles.yaml").write_text(yaml.safe_dump(
        {"type": "adresse_citee", "date": "2026-11-14", "decisions": decisions}))
    (tmp_path / "z2").mkdir()
    ctx = Contexte(str(tmp_path / "z2"), str(tmp_path / "z3"), str(tmp_path / "decisions"))
    x = ctx.con.execute
    x("""CREATE VIEW lignee AS SELECT * FROM (VALUES ('lig:000002', 'socialistes-et-apparentes'),
                                                     ('lig:000009', 'ensemble-pour-la-republique'))
         t(lignee, adresse)""")
    # lig:000020 a été fusionnée dans lig:000009 : son adresse est devenue une redirection
    x("""CREATE VIEW lignee_adresse AS SELECT * FROM (VALUES
           ('socialistes-et-apparentes', 'lig:000002', 'lig:000002', 'active'),
           ('ensemble-pour-la-republique', 'lig:000009', 'lig:000009', 'active'),
           ('renaissance', 'lig:000020', 'lig:000009', 'redirection'))
         t(adresse, lignee_inscrite, lignee, statut)""")
    x("""CREATE VIEW gouvernement AS SELECT * FROM (VALUES ('PO873634', 'lecornu-ii'),
                                                          ('PO1', 'fillon-1')) t(organe, adresse)""")
    return ctx


def test_adresses_citees_menent_a_leur_fiche(tmp_path):
    ctx = _contexte(tmp_path, [
        {"adresse": "/groupes/AN-SOC", "type_fiche": "lignee", "objet": "lig:000002"},
        {"adresse": "/groupes/AN-REN", "type_fiche": "lignee", "objet": "lig:000020"},
        {"adresse": "/gouvernements/LECORNU_II", "type_fiche": "gouvernement", "objet": "PO873634"},
        {"adresse": "/gouvernements/FILLON_1", "type_fiche": "gouvernement", "objet": "PO1"},
        {"adresse": "/groupes/AN-XX", "type_fiche": "lignee", "objet": "lig:999999"}])
    ecr = Ecrivain(str(tmp_path / "site"), "g000001")
    for t, a in (("lignee", "socialistes-et-apparentes"), ("lignee", "ensemble-pour-la-republique"),
                 ("gouvernement", "lecornu-ii")):
        ecr.fiche(t, a, a).entete({})
    adresses.composer(ctx, ecr)
    ecr.clore()
    with gzip.open(os.path.join(ecr.racine, "catalogue.json.gz")) as f:
        cat = json.load(f)
    t = cat["adresses_citees"]
    assert t["colonnes"] == ["adresse", "lien", "raison", "decision"]
    r = {l[0]: l for l in t["lignes"]}
    assert r["/groupes/AN-SOC"][1:3] == ["lignee/socialistes-et-apparentes", None]
    # une lignée fusionnée mène à celle qui l'a reçue
    assert r["/groupes/AN-REN"][1] == "lignee/ensemble-pour-la-republique"
    assert r["/gouvernements/LECORNU_II"][1] == "gouvernement/lecornu-ii"
    assert r["/gouvernements/LECORNU_II"][3] == "adresse_citee/articles.yaml#2"
    # fiche non publiée, objet inconnu : jamais de lien, la raison est dite
    assert r["/gouvernements/FILLON_1"][1:3] == [None, "la fiche gouvernement/fillon-1 n'est pas publiée"]
    assert r["/groupes/AN-XX"][1] is None and "introuvable" in r["/groupes/AN-XX"][2]
    # C2 vérifie les liens servis ; A7 nomme les adresses sans fiche
    faits = str(tmp_path / "faits.parquet")
    ecr.ecrire_faits_publies(faits)
    c = Controles(ecr.racine)
    c.c2_liens({f["fiche"] for f in ecr.fiches})
    c.preparer(ctx.con, faits, {f["fiche"] for f in ecr.fiches})
    c.a7_non_resolues({})
    assert not [a for a in c.anomalies if a["bloquant"]]
    (a7,) = [a for a in c.anomalies if a["controle"] == "A7"]
    assert sum("adresse citée" in o for o in a7["exemples"]) == 2


def test_sans_decision_le_catalogue_ne_change_pas(tmp_path):
    ctx = _contexte(tmp_path, [])
    ecr = Ecrivain(str(tmp_path / "site"), "g000001")
    adresses.composer(ctx, ecr)
    ecr.clore()
    with gzip.open(os.path.join(ecr.racine, "catalogue.json.gz")) as f:
        assert "adresses_citees" not in json.load(f)
