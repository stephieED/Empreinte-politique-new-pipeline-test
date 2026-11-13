"""R-DERNIERE-LECTURE version 2 (issue #34, décision « Garder, signalé » du 13/11/2026).

Cas réel de la g10 : `DLR5L15N35986` (ordonnances « dialogue social ») ; sa première lecture
`VTANR5L15V314` (28/11/2017) est reliée ; le vote sur le texte de CMP, `VTANR5L15V386`
(06/02/2018), ne l'est pas : sa séance porte aussi `DLR5L15N36220` (séance ambiguë). Le vote
retenu reste `V314`, et `V386` est nommé."""
import types

import pyarrow as pa
import pyarrow.parquet as pq

from empreinte_src.lecteurs import an_dossiers
from empreinte_src.liaison import Contexte, ordonner, relier
from empreinte_src.regles import r_derniere_lecture

from .test_regles_c import ecrire_table

SEANCE = "RUANR5L15S2018IDS20897"


def _subst(z3, nom, sorties, tables):
    def appliquer(ctx):
        for t in sorties:
            ctx.ecrire(t, f"SELECT * FROM read_parquet('{z3 / ('_' + t + '.parquet')}')")
        return {}
    for t, tab in tables.items():
        pq.write_table(tab, z3 / f"_{t}.parquet")
    return types.SimpleNamespace(NOM=nom, VERSION=0, DEPEND=(), SORTIES=sorties, appliquer=appliquer)


def test_vote_posterieur_non_relie_nomme(tmp_path):
    z2, z3 = tmp_path / "z2", tmp_path / "z3"
    z2.mkdir()
    z3.mkdir()
    ecrire_table(z2, an_dossiers, "acte", [
        {"dossier": "DLR5L15N35986", "uid": "L15-A1", "reunion": SEANCE, "type_acte": "Decision_Type",
         "code": "CMP-DEBATS-AN-DEC"},
        {"dossier": "DLR5L15N36220", "uid": "L15-A2", "reunion": SEANCE,
         "type_acte": "DiscussionSeancePublique_Type", "code": "AN1-DEBATS-SEANCE"},
        {"dossier": "DLR5L15N99999", "uid": "L15-A3", "reunion": SEANCE, "type_acte": "DepotRapport_Type"}])
    scr = ["VTANR5L15V314", "VTANR5L15V386", "VTANR5L15V200"]
    classe = pa.table({
        "scrutin": scr, "date": ["2017-11-28", "2018-02-06", "2017-10-01"], "numero": [314, 386, 200],
        "legislature": [15, 15, 15], "nature": ["ensemble"] * 3, "lecture": ["premiere", "cmp", "premiere"],
        "sort": ["adopte"] * 3, "origine": ["projet"] * 3, "type_texte": ["PRJL"] * 3,
        "source_url": [None] * 3, "seance": ["S1", SEANCE, "S0"]}, schema=pa.schema([
            ("scrutin", pa.string()), ("date", pa.string()), ("numero", pa.int64()), ("legislature", pa.int64()),
            ("nature", pa.string()), ("lecture", pa.string()), ("sort", pa.string()), ("origine", pa.string()),
            ("type_texte", pa.string()), ("source_url", pa.string()), ("seance", pa.string())]))
    lien = pa.table({"scrutin": ["VTANR5L15V314", "VTANR5L15V200"],
                     "dossier": ["DLR5L15N35986", "DLR5L15N36220"], "nb_dossiers": [1, 1]})
    non_relie = pa.table({"scrutin": ["VTANR5L15V386"], "raison": ["seance_ambigue"],
                          "candidats": pa.array([None], pa.list_(pa.string()))})
    mods = [_subst(z3, "R-LIEN-SCRUTIN-DOSSIER", ("lien_scrutin_dossier", "scrutin_non_relie"),
                   {"lien_scrutin_dossier": lien, "scrutin_non_relie": non_relie}),
            _subst(z3, "R-ORIGINE", ("scrutin_classe",), {"scrutin_classe": classe}),
            r_derniere_lecture]
    ctx = Contexte(str(z2), str(z3))
    bilan = {b["regle"].split("@")[0]: b for b in relier(ctx, ordonner(mods))}
    dl = {d: (s, list(v)) for d, s, v in ctx.x(
        "SELECT dossier, scrutin, votes_posterieurs_non_relies FROM derniere_lecture")}
    # Le vote retenu est gardé ; le vote de CMP non relié, plus récent, est nommé pour les deux
    # dossiers de sa séance (discussion ou décision), pas pour un simple dépôt de rapport.
    assert dl == {"DLR5L15N35986": ("VTANR5L15V314", ["VTANR5L15V386"]),
                  "DLR5L15N36220": ("VTANR5L15V200", ["VTANR5L15V386"])}
    assert bilan["R-DERNIERE-LECTURE"]["couverture"]["derniere_lecture_sans_vote_posterieur_non_relie"] == [0, 2]
