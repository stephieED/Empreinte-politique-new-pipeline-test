"""Archives successives de l'Assemblée (liaison, ARCHIVES_SUCCESSIVES ; décision Q4) : un objet que
plusieurs archives portent n'est lu qu'une fois, dans la plus récente."""
import pyarrow as pa
import pyarrow.parquet as pq

from empreinte_src.liaison import Contexte


def _table(z2, nom, lignes):
    rows = [{**r, "prov_uid": r.get("prov_uid", r.get("uid")), "prov_version": 1, "prov_etat": "present"}
            for r in lignes]
    pq.write_table(pa.Table.from_pylist(rows), str(z2 / f"{nom}.parquet"))


def test_acteurs_archive_courante_seule_et_objets_par_archive_la_plus_recente(tmp_path):
    z2 = tmp_path / "z2"
    z2.mkdir()
    _table(z2, "an_acteurs__mandat", [
        # Republié par chaque archive des acteurs : seule la courante (XVIIe) est lue.
        {"uid": "PM1", "acteur": "PA1", "date_fin": "2022-06-21", "prov_point": "an-amo30-l15"},
        {"uid": "PM1", "acteur": "PA1", "date_fin": "2022-06-21", "prov_point": "an-amo30-l16"},
        {"uid": "PM1", "acteur": "PA1", "date_fin": "2022-06-21", "prov_point": "an-amo30-l17"},
        # Effacé de la courante (Q4 : retiré ou corrigé à la source) : n'est plus lu.
        {"uid": "PM9", "acteur": "PA9", "date_fin": None, "prov_point": "an-amo30-l16"},
        # Point hors suite d'archives : toujours lu.
        {"uid": "PM5", "acteur": "PA5", "date_fin": None, "prov_point": "test"}])
    _table(z2, "an_dossiers__dossier", [
        # Ouvert en XVIe, poursuivi en XVIIe : l'archive de la XVIIe fait foi.
        {"uid": "DL1", "titre": "ancien titre", "prov_point": "an-dossiers-l16"},
        {"uid": "DL1", "titre": "titre à jour", "prov_point": "an-dossiers-l17"},
        # Propre à la XVe (législature close) : gardé.
        {"uid": "DL2", "titre": "texte de la XVe", "prov_point": "an-dossiers-l15"}])
    _table(z2, "an_dossiers__acte", [
        # Chaque archive renumérote les actes du dossier (L16-… → L17-…) : ceux de la XVIIe font foi.
        {"uid": "L16-A1", "dossier": "DL1", "prov_point": "an-dossiers-l16", "prov_uid": "DL1"},
        {"uid": "L17-A1", "dossier": "DL1", "prov_point": "an-dossiers-l17", "prov_uid": "DL1"},
        {"uid": "L17-A2", "dossier": "DL1", "prov_point": "an-dossiers-l17", "prov_uid": "DL1"},
        {"uid": "L15-A3", "dossier": "DL2", "prov_point": "an-dossiers-l15", "prov_uid": "DL2"}])
    _table(z2, "an_dossiers__document", [
        {"uid": "DOC1", "dossier": "DLR5L14N1", "prov_point": "an-dossiers-l14", "prov_uid": "XIV"},
        {"uid": "DOC1", "dossier": "DLR5L15N1", "prov_point": "an-dossiers-l15", "prov_uid": "DLR5L15N1"}])
    _table(z2, "an_scrutins__scrutin", [
        {"uid": "VT1", "prov_point": "an-scrutins-l16"}, {"uid": "VT2", "prov_point": "an-scrutins-l17"}])
    ctx = Contexte(str(z2), str(tmp_path / "z3"))
    assert ctx.x("SELECT uid, prov_point FROM an_acteurs__mandat ORDER BY 1") == [
        ("PM1", "an-amo30-l17"), ("PM5", "test")]
    assert ctx.x("SELECT count(*) FROM an_acteurs__mandat__archives")[0][0] == 5
    assert ctx.x("SELECT uid, titre FROM an_dossiers__dossier ORDER BY 1") == [
        ("DL1", "titre à jour"), ("DL2", "texte de la XVe")]
    # Les actes suivent l'archive qui fait foi pour leur dossier.
    assert ctx.x("SELECT uid FROM an_dossiers__acte ORDER BY 1") == [("L15-A3",), ("L17-A1",), ("L17-A2",)]
    # Un document d'un texte qui continue d'une législature à l'autre change de dossier
    # (DLR5L14N1 → DLR5L15N1) : il n'est lu qu'une fois, sous le dossier le plus récent.
    assert ctx.x("SELECT uid, dossier FROM an_dossiers__document") == [("DOC1", "DLR5L15N1")]
    # Famille sans recouvrement entre archives : tout est lu.
    assert ctx.x("SELECT count(*) FROM an_scrutins__scrutin")[0][0] == 2
