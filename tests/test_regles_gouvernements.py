"""R-GOUVERNEMENTS : nom affiché et adresse d'un gouvernement (« Lecornu » / « Lecornu I »)."""
import os
import types

import pyarrow as pa

from empreinte_src.liaison import Contexte, ordonner, relier
from empreinte_src.regles import r_gouvernements


def _org(uid, abrege, debut, fin):
    return {"uid": uid, "type_organe": "GOUVERNEMENT", "libelle_abrege": abrege, "date_debut": debut,
            "date_fin": fin, "prov_url": None}


def test_premier_gouvernement_numerote_i_sans_changer_d_adresse(tmp_path):
    os.makedirs(tmp_path / "z2")
    ctx = Contexte(str(tmp_path / "z2"), str(tmp_path / "z3"))
    ctx.con.register("an_acteurs__organe", pa.Table.from_pylist([
        _org("PO855052", "BAYROU", "2024-12-14", "2025-09-09"),
        _org("PO873418", "LECORNU", "2025-09-10", "2025-10-10"),
        _org("PO873634", "LECORNU II", "2025-10-11", None)]))

    def leg(c):
        c.ecrire("legislature", "SELECT 17 AS numero, '2024-07-18' AS debut, NULL::VARCHAR AS fin")
        return {}
    relier(ctx, ordonner([types.SimpleNamespace(NOM="R-LEGISLATURES", VERSION=0, DEPEND=(),
                                                SORTIES=("legislature",), appliquer=leg), r_gouvernements]))
    g = {o: (n, a) for o, n, a in ctx.x("SELECT organe, nom, adresse FROM gouvernement")}
    assert g == {"PO855052": ("Bayrou", "bayrou"), "PO873418": ("Lecornu I", "lecornu"),
                 "PO873634": ("Lecornu II", "lecornu-ii")}
