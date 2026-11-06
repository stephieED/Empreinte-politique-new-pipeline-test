"""Règles R-CONTINUITE-GROUPE, R-FILIATION et R-LIGNEE (cahier 4.3 ; doc. 1, 1.5.2 et 1.6).

Sur de petites tables écrites ici, à la forme exacte des sorties de R-APPARTENANCE et R-DEPUTES,
qui reproduisent les cas mesurés dans l'archive du 06/11/2026 : un groupe qui change de sigle en
cours de législature (SRC → SER), un groupe dissident (R-UMP), et les deux exemples chiffrés du
cahier (Nouvelle Gauche : 51 % et 100 % ; Les Républicains après R-UMP : 100 % et 30 %)."""
import os
import types

import pyarrow as pa
import yaml

from empreinte_src.identites import RegistreIdentites
from empreinte_src.liaison import Contexte, ordonner, relier
from empreinte_src.regles import r_continuite_groupe, r_filiation, r_lignee


def _amont(groupes, appartenances, deputes):
    """Fausses règles amont : écrivent `groupe`, `appartenance`, `depute` telles quelles."""
    def _ga(ctx):
        ctx.con.register("_t_g", pa.Table.from_pylist(groupes))
        ctx.con.register("_t_a", pa.Table.from_pylist(appartenances))
        ctx.ecrire("groupe", "SELECT * FROM _t_g")
        ctx.ecrire("appartenance", "SELECT * FROM _t_a")
        return {}

    def _dep(ctx):
        ctx.con.register("_t_d", pa.Table.from_pylist(deputes))
        ctx.ecrire("depute", "SELECT * FROM _t_d")
        return {}
    return [types.SimpleNamespace(NOM="R-APPARTENANCE", VERSION=0, DEPEND=(), SORTIES=("groupe", "appartenance"),
                                  appliquer=_ga),
            types.SimpleNamespace(NOM="R-DEPUTES", VERSION=0, DEPEND=(), SORTIES=("depute",), appliquer=_dep)]


def _g(organe, leg, sigle, debut, fin, libelle=None, position="non_declaree"):
    return {"organe": organe, "legislature": leg, "sigle": sigle, "libelle": libelle or sigle, "debut": debut,
            "fin": fin, "position_declaree": position, "source_url": None}


def _a(acteur, groupe, debut, fin, leg):
    return {"acteur": acteur, "groupe": groupe, "legislature": leg, "debut": debut, "fin": fin}


def _d(acteur, leg):
    return {"acteur": acteur, "legislature": leg, "mandat": f"PM-{acteur}-{leg}"}


DEB = {13: ("2007-06-26", "2012-06-19"), 14: ("2012-06-26", "2017-06-20"), 15: ("2017-06-27", "2022-06-21")}


def scenario():
    """XIIIe : S13 (40 membres). XIVe : SRC → SER (même groupe, autre sigle), UMP, R-UMP
    (dissident de l'UMP en cours de législature). XVe : NG, LR."""
    g, a, d = [], [], []
    g.append(_g("PO13S", 13, "S.R.C.", *DEB[13]))
    for k in range(40):
        a.append(_a(f"S{k}", "PO13S", DEB[13][0], DEB[13][1], 13))
        d.append(_d(f"S{k}", 13))
    # XIVe : SRC puis SER, le lendemain, avec les mêmes 60 membres (dont 30 réélus de S13).
    g.append(_g("PO14A", 14, "SRC", "2012-06-26", "2016-05-24", "Socialiste, républicain et citoyen", "majoritaire"))
    g.append(_g("PO14B", 14, "SER", "2016-05-25", "2017-06-20", "Socialiste, écologiste et républicain", "majoritaire"))
    soc14 = [f"S{k}" for k in range(30)] + [f"T{k}" for k in range(30)]
    for p in soc14:
        a.append(_a(p, "PO14A", "2012-06-26", "2016-05-24", 14))
        a.append(_a(p, "PO14B", "2016-05-25", "2017-06-20", 14))
        d.append(_d(p, 14))
    # UMP (80 membres) ; R-UMP : 17 d'entre eux partent en cours de législature, puis reviennent.
    g.append(_g("PO14U", 14, "UMP", "2012-06-26", "2017-06-20"))
    g.append(_g("PO14R", 14, "R-UMP", "2012-11-27", "2013-01-15"))
    for k in range(80):
        p = f"U{k}"
        d.append(_d(p, 14))
        if k < 17:
            a += [_a(p, "PO14U", "2012-06-26", "2012-11-26", 14), _a(p, "PO14R", "2012-11-27", "2013-01-15", 14),
                  _a(p, "PO14U", "2013-01-16", "2017-06-20", 14)]
        else:
            a.append(_a(p, "PO14U", "2012-06-26", "2017-06-20", 14))
    # XVe. NG : 28 anciens députés, tous venus du groupe socialiste ; 55 socialistes réélus en tout
    # (28 en NG, 27 ailleurs). LR : 56 anciens députés, dont les 17 réélus de R-UMP (tous en LR).
    g.append(_g("PO15N", 15, "NG", *DEB[15]))
    g.append(_g("PO15L", 15, "LR", *DEB[15]))
    g.append(_g("PO15X", 15, "LAREM", *DEB[15]))
    for k, p in enumerate(soc14[:55]):
        d.append(_d(p, 15))
        a.append(_a(p, "PO15N" if k < 28 else "PO15X", *DEB[15], 15))
    for k in range(56):
        p = f"U{k}"
        d.append(_d(p, 15))
        a.append(_a(p, "PO15L", *DEB[15], 15))
    # LAREM accueille aussi 24 anciens UMP : les 27 socialistes n'y sont pas la majorité des
    # anciens députés (27 sur 51), et LAREM ne prend la suite de personne (comme en 2017).
    for k in range(56, 80):
        p = f"U{k}"
        d.append(_d(p, 15))
        a.append(_a(p, "PO15X", *DEB[15], 15))
    for k in range(10):                       # nouveaux députés de NG
        d.append(_d(f"N{k}", 15))
        a.append(_a(f"N{k}", "PO15N", *DEB[15], 15))
    return g, a, d


def _relier(tmp_path, tables, generation=1, registre="reg", decisions=None, nom="z3"):
    g, a, d = tables
    ctx = Contexte(str(tmp_path / "z2"), str(tmp_path / nom), dossier_decisions=decisions and str(decisions),
                   generation=generation, registre=RegistreIdentites(str(tmp_path / registre)))
    os.makedirs(tmp_path / "z2", exist_ok=True)
    bilan = relier(ctx, ordonner(_amont(g, a, d) + [r_continuite_groupe, r_filiation, r_lignee]))
    ctx.registre.sauver()
    return ctx, {b["regle"].split("@")[0]: b for b in bilan}


def _lignes(ctx, sql, params=None):
    r = ctx.con.execute(sql, params or [])
    cols = [x[0] for x in r.description]
    return [dict(zip(cols, x)) for x in r.fetchall()]


def test_continuite_malgre_le_changement_de_sigle(tmp_path):
    ctx, b = _relier(tmp_path, scenario())
    c = {(x["organe_avant"], x["organe_apres"]): x for x in _lignes(ctx, "SELECT * FROM continuite_groupe")}
    x = c[("PO14A", "PO14B")]
    assert (x["membres_avant"], x["membres_apres"], x["communs"], x["verdict"]) == (60, 60, 60, "continuite")
    m = {x["organe"]: x for x in _lignes(ctx, "SELECT * FROM maillon")}
    assert m["PO14A"]["maillon"] == m["PO14B"]["maillon"] == "grp:14:PO14A"
    assert [m["PO14A"]["rang"], m["PO14B"]["rang"]] == [1, 2]
    assert m["PO14A"]["position_maillon"] == "majoritaire"


def test_groupe_dissident_n_est_pas_une_continuite(tmp_path):
    ctx, _ = _relier(tmp_path, scenario())
    # R-UMP commence pendant que l'UMP existe : ce n'est pas une suite d'organe (critère de dates).
    assert not _lignes(ctx, "SELECT * FROM continuite_groupe WHERE organe_apres = 'PO14R'")
    m = {x["organe"]: x["maillon"] for x in _lignes(ctx, "SELECT * FROM maillon")}
    assert m["PO14R"] == "grp:14:PO14R" and m["PO14U"] == "grp:14:PO14U"


def test_position_divergente_dans_un_maillon(tmp_path):
    g, a, d = scenario()
    g = [dict(x, position_declaree="opposition") if x["organe"] == "PO14B" else x for x in g]
    ctx, _ = _relier(tmp_path, (g, a, d))
    m = {x["organe"]: x for x in _lignes(ctx, "SELECT * FROM maillon")}
    assert m["PO14A"]["position_maillon"] == m["PO14B"]["position_maillon"] == "divergente"
    assert (m["PO14A"]["position_declaree"], m["PO14B"]["position_declaree"]) == ("majoritaire", "opposition")


def test_filiation_exemples_du_cahier(tmp_path):
    ctx, b = _relier(tmp_path, scenario())
    f = {(x["maillon_avant"], x["maillon_apres"]): x for x in _lignes(ctx, "SELECT * FROM filiation")}
    ng = f[("grp:14:PO14A", "grp:15:PO15N")]        # 51 % et 100 % : combinées 67 %, suite
    assert (ng["reelus"], ng["anciens_deputes"], ng["communs"], ng["verdict"]) == (55, 28, 28, "suite")
    lr = f[("grp:14:PO14R", "grp:15:PO15L")]        # 100 % et 30 % : combinées 47 %, pas la suite
    assert (lr["reelus"], lr["anciens_deputes"], lr["communs"], lr["verdict"]) == (17, 56, 17, "pas_suite")
    assert lr["raison"] == "sous_le_seuil"
    assert f[("grp:14:PO14U", "grp:15:PO15L")]["verdict"] == "suite"
    assert f[("grp:13:PO13S", "grp:14:PO14A")]["verdict"] == "suite"
    # Aucun ratio n'est écrit : seulement des décomptes.
    cols = {x[0] for x in ctx.con.execute("DESCRIBE filiation").fetchall()}
    assert not any(c.startswith(("part", "ratio", "taux", "moyenne")) for c in cols)


def _deux_groupes(communs, reelus_hors, nouveaux_anciens, nouveaux_purs=0):
    """Un groupe G14 ; un groupe G15 qui reçoit `communs` de ses membres. `reelus_hors` autres
    membres de G14 sont réélus ailleurs ; `nouveaux_anciens` membres de G15 étaient députés en XIVe
    dans un autre groupe."""
    g = [_g("PO14G", 14, "G", *DEB[14]), _g("PO14H", 14, "H", *DEB[14]),
         _g("PO15G", 15, "G2", *DEB[15]), _g("PO15Z", 15, "Z", *DEB[15])]
    a, d = [], []
    for k in range(communs + reelus_hors):
        p = f"G{k}"
        a.append(_a(p, "PO14G", *DEB[14], 14))
        d += [_d(p, 14), _d(p, 15)]
        a.append(_a(p, "PO15G" if k < communs else "PO15Z", *DEB[15], 15))
    for k in range(nouveaux_anciens):
        p = f"H{k}"
        a += [_a(p, "PO14H", *DEB[14], 14), _a(p, "PO15G", *DEB[15], 15)]
        d += [_d(p, 14), _d(p, 15)]
    for k in range(nouveaux_purs):
        a.append(_a(f"N{k}", "PO15G", *DEB[15], 15))
        d.append(_d(f"N{k}", 15))
    return g, a, d


def test_seuil_exact_en_nombres_entiers(tmp_path):
    # 6 communs, 10 réélus, 10 anciens députés : 60 % et 60 %, moyenne harmonique 60 % pile → suite.
    ctx, _ = _relier(tmp_path, _deux_groupes(6, 4, 4))
    f = _lignes(ctx, "SELECT * FROM filiation WHERE maillon_avant = 'grp:14:PO14G' AND maillon_apres = 'grp:15:PO15G'")[0]
    assert (f["reelus"], f["anciens_deputes"], f["communs"], f["verdict"]) == (10, 10, 6, "suite")
    # Un réélu de plus parti ailleurs : 6 / 11 et 6 / 10, combinées 57 % → pas la suite.
    ctx, _ = _relier(tmp_path, _deux_groupes(6, 5, 4), nom="z3b")
    f = _lignes(ctx, "SELECT * FROM filiation WHERE maillon_avant = 'grp:14:PO14G' AND maillon_apres = 'grp:15:PO15G'")[0]
    assert f["verdict"] == "pas_suite"
    # Les nouveaux sans mandat antérieur ne comptent pas parmi les anciens députés.
    ctx, _ = _relier(tmp_path, _deux_groupes(6, 4, 4, nouveaux_purs=30), nom="z3c")
    f = _lignes(ctx, "SELECT * FROM filiation WHERE maillon_avant = 'grp:14:PO14G' AND maillon_apres = 'grp:15:PO15G'")[0]
    assert (f["anciens_deputes"], f["verdict"]) == (10, "suite")


def test_moins_de_cinq_communs(tmp_path):
    ctx, _ = _relier(tmp_path, _deux_groupes(4, 0, 0))        # 100 % et 100 %, mais 4 communs
    f = _lignes(ctx, "SELECT * FROM filiation WHERE maillon_apres = 'grp:15:PO15G' AND maillon_avant = 'grp:14:PO14G'")[0]
    assert (f["verdict"], f["raison"]) == ("pas_suite", "moins_de_5_communs")


def _scission():
    """G14 (20 membres réélus) se partage à parts égales entre A15 et B15 : les deux passent le seuil."""
    g = [_g("PO14G", 14, "G", *DEB[14]), _g("PO15A", 15, "A", *DEB[15]), _g("PO15B", 15, "B", *DEB[15])]
    a, d = [], []
    for k in range(20):
        p = f"G{k}"
        a += [_a(p, "PO14G", *DEB[14], 14), _a(p, "PO15A" if k < 10 else "PO15B", *DEB[15], 15)]
        d += [_d(p, 14), _d(p, 15)]
    return g, a, d


def test_deux_suites_a_trancher_puis_decision(tmp_path):
    ctx, b = _relier(tmp_path, _scission())
    f = {x["maillon_apres"]: x for x in _lignes(ctx, "SELECT * FROM filiation")}
    assert {x["verdict"] for x in f.values()} == {"a_trancher"}
    assert b["R-FILIATION"]["couverture"]["paires_tranchees"] == [0, 2]
    # En attendant : chaque groupe forme sa propre lignée (Q22), et la table le dit.
    lm = {x["maillon"]: x for x in _lignes(ctx, "SELECT * FROM lignee_maillon")}
    assert len({x["lignee"] for x in lm.values()}) == 3
    assert list(lm["grp:15:PO15A"]["filiation_a_trancher"]) == ["grp:14:PO14G"]
    # Décision : A15 prend la suite.
    dec = tmp_path / "decisions" / "filiation"
    os.makedirs(dec)
    with open(dec / "a15.yaml", "w") as fi:
        yaml.safe_dump({"type": "filiation", "date": "2026-11-07", "avant": "grp:14:PO14G",
                        "apres": "grp:15:PO15A", "verdict": "suite", "motif": "test"}, fi)
    with open(dec / "b15.yaml", "w") as fi:
        yaml.safe_dump({"type": "filiation", "date": "2026-11-07", "avant": "grp:14:PO14G",
                        "apres": "grp:15:PO15B", "verdict": "pas_suite", "motif": "test"}, fi)
    ctx, _ = _relier(tmp_path, _scission(), generation=2, decisions=tmp_path / "decisions", nom="z3d")
    f = {x["maillon_apres"]: x for x in _lignes(ctx, "SELECT * FROM filiation")}
    assert (f["grp:15:PO15A"]["verdict"], f["grp:15:PO15A"]["raison"]) == ("suite", "decision")
    assert f["grp:15:PO15A"]["decision"] == "filiation/a15.yaml"
    lm = {x["maillon"]: x["lignee"] for x in _lignes(ctx, "SELECT * FROM lignee_maillon")}
    assert lm["grp:15:PO15A"] == lm["grp:14:PO14G"] != lm["grp:15:PO15B"]


def test_numero_et_adresse_acquis(tmp_path):
    ctx, b = _relier(tmp_path, scenario())
    l1 = {x["maillon_racine"]: x for x in _lignes(ctx, "SELECT * FROM lignee")}
    soc = l1["grp:13:PO13S"]
    assert soc["adresse"] == "ng" and soc["publiee"] and soc["premiere_legislature"] == 13
    assert soc["debut_affiche"] == "2012-06-26"           # XIIIe calculée, pas affichée
    # Nuit suivante : le groupe change de nom ; le numéro et l'adresse restent.
    g, a, d = scenario()
    g = [dict(x, libelle="Socialistes et apparentés", sigle="SOC") if x["organe"] == "PO15N" else x for x in g]
    ctx, _ = _relier(tmp_path, (g, a, d), generation=2, nom="z3b")
    l2 = {x["maillon_racine"]: x for x in _lignes(ctx, "SELECT * FROM lignee")}
    assert {r: (x["lignee"], x["adresse"]) for r, x in l2.items()} == \
        {r: (x["lignee"], x["adresse"]) for r, x in l1.items()}
    assert l2["grp:13:PO13S"]["nom"] == "Socialistes et apparentés"
    # Un groupe nouveau d'une législature suivante qui prend la suite rejoint la lignée.
    g.append(_g("PO16N", 16, "SOC", "2022-06-28", None, "Socialistes"))
    for k in range(20):
        p = f"N{k % 10}" if k < 10 else f"S{k}"
        d.append(_d(p, 16))
        a.append(_a(p, "PO16N", "2022-06-28", None, 16))
    ctx, _ = _relier(tmp_path, (g, a, d), generation=3, nom="z3c")
    l3 = {x["lignee"]: x for x in _lignes(ctx, "SELECT * FROM lignee")}
    assert l3[soc["lignee"]]["derniere_legislature"] == 16 and l3[soc["lignee"]]["adresse"] == "ng"


def test_lignee_ancienne_non_publiee(tmp_path):
    g, a, d = scenario()
    ctx, _ = _relier(tmp_path, (g, a, d))
    # Les 10 socialistes de la XIIIe non réélus n'ont pas de groupe après : rien ne commence en XIIIe
    # seul ; une lignée réduite à la XIIIe n'aurait pas de fiche.
    g2 = g + [_g("PO13Z", 13, "Z", *DEB[13])]
    a2 = a + [_a(f"Z{k}", "PO13Z", *DEB[13], 13) for k in range(6)]
    ctx, _ = _relier(tmp_path, (g2, a2, d), generation=2, nom="z3b")
    z = _lignes(ctx, "SELECT * FROM lignee WHERE maillon_racine = 'grp:13:PO13Z'")[0]
    assert (z["publiee"], z["raison_non_publiee"]) == (False, "aucun_groupe_depuis_la_xive")


def test_fusion_garde_le_plus_ancien_numero_et_redirige(tmp_path):
    ctx, _ = _relier(tmp_path, _scission())       # trois lignées, numérotées
    av = {x["maillon_racine"]: x for x in _lignes(ctx, "SELECT * FROM lignee")}
    dec = tmp_path / "decisions" / "filiation"
    os.makedirs(dec)
    for apres in ("PO15A", "PO15B"):               # les deux deviennent la suite de G14 : fusion
        with open(dec / f"{apres}.yaml", "w") as fi:
            yaml.safe_dump({"type": "filiation", "date": "2026-11-07", "avant": "grp:14:PO14G",
                            "apres": f"grp:15:{apres}", "verdict": "suite", "motif": "test"}, fi)
    ctx, b = _relier(tmp_path, _scission(), generation=2, decisions=tmp_path / "decisions", nom="z3b")
    ap = _lignes(ctx, "SELECT * FROM lignee")
    assert len(ap) == 1 and ap[0]["lignee"] == av["grp:14:PO14G"]["lignee"]
    adr = {x["adresse"]: x for x in _lignes(ctx, "SELECT * FROM lignee_adresse")}
    assert adr[av["grp:14:PO14G"]["adresse"]]["statut"] == "active"
    for r in ("grp:15:PO15A", "grp:15:PO15B"):
        x = adr[av[r]["adresse"]]
        assert x["statut"] == "redirection" and x["lignee"] == ap[0]["lignee"]
    # Le registre n'a fait que croître.
    reg = RegistreIdentites(str(tmp_path / "reg")).lignees
    assert len(reg.fusions) == 2 and len(reg.adresses) == 3


def test_sans_registre_la_regle_echoue(tmp_path):
    import pytest
    g, a, d = scenario()
    os.makedirs(tmp_path / "z2", exist_ok=True)
    ctx = Contexte(str(tmp_path / "z2"), str(tmp_path / "z3"), generation=1)
    with pytest.raises(RuntimeError, match="registre"):
        relier(ctx, ordonner(_amont(g, a, d) + [r_continuite_groupe, r_filiation, r_lignee]))
