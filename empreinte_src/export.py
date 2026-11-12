"""Export plat des faits (commande de réalisation, section 7).

Une ligne par fait, pour comparer deux versions fait par fait sans connaître le modèle
interne. Chaque lecteur déclare, pour chaque table, comment ses lignes deviennent des faits :

    EXPORT = {
        "reunion": {
            "type": "reunion",                    # type de fait
            "cle": ["uid"],                       # colonnes qui identifient le fait
            "ids": {"reunion": "uid", "organe": "organe"},   # identifiants de source exportés
            "date": "date_seance",                # date du fait (ou None)
            "toutes_versions": False,             # True : chaque version est un fait (listes livrées en delta)
        },
    }

Clés d'identifiants possibles (une colonne `id_<clé>` chacune dans l'export) : voir IDS.
Le fait exporté est celui de l'état courant : dernière version du membre, présente à la
source. La colonne `fiche` sera remplie quand les fiches seront composées (tranche 3).
"""
from __future__ import annotations

import os

import duckdb

IDS = ["acteur", "organe", "mandat", "scrutin", "amendement", "dossier", "document",
       "reunion", "compte_rendu", "question", "acte", "autre"]

COLONNES = (["cle_fait", "type_fait", "fiche"] + [f"id_{k}" for k in IDS]
            + ["valeur", "date", "source_url", "source", "licence", "prov_uid", "prov_version",
               "lecteur"])

EXCLUES_DE_LA_VALEUR = {"prov_source", "prov_point", "prov_uid", "prov_version", "prov_empreinte",
                        "prov_url", "prov_vu_du", "prov_vu_jusqu_au", "prov_etat", "lecteur", "licence"}


def requete_table(chemin: str, spec: dict, colonnes: list[str]) -> str:
    def q(c):
        return f'"{c}"'
    ids = spec.get("ids", {})
    inconnus = set(ids) - set(IDS)
    if inconnus:
        raise ValueError(f"clés d'identifiants inconnues : {inconnus}")
    valeur_cols = [c for c in colonnes if c not in EXCLUES_DE_LA_VALEUR]
    struct = ", ".join(f"{q(c)} := {q(c)}" for c in valeur_cols)
    cle = " || '|' || ".join(f"coalesce(CAST({q(c)} AS VARCHAR), '')" for c in spec["cle"])
    sel = [f"'{spec['type']}' || '|' || {cle} AS cle_fait", f"'{spec['type']}' AS type_fait",
           "CAST(NULL AS VARCHAR) AS fiche"]
    for k in IDS:
        sel.append(f"CAST({q(ids[k])} AS VARCHAR) AS id_{k}" if k in ids
                   else f"CAST(NULL AS VARCHAR) AS id_{k}")
    sel.append(f"CAST(to_json(struct_pack({struct})) AS VARCHAR) AS valeur")
    sel.append(f"CAST({q(spec['date'])} AS VARCHAR) AS date" if spec.get("date")
               else "CAST(NULL AS VARCHAR) AS date")
    sel += ["prov_url AS source_url", "prov_source AS source", "licence", "prov_uid",
            "prov_version", "lecteur"]
    if spec.get("toutes_versions"):
        return f"""SELECT {", ".join(sel)} FROM read_parquet('{chemin}') WHERE prov_etat = 'present'"""
    # Dernière version de chaque fichier source, calculée sur les seules colonnes d'identifiants
    # (mémoire bornée), puis jointe.
    return f"""
        SELECT {", ".join(sel)} FROM read_parquet('{chemin}') x
        SEMI JOIN (SELECT prov_point AS p, prov_uid AS u, max(prov_version) AS n
                   FROM read_parquet('{chemin}') GROUP BY 1, 2) d
          ON x.prov_point = d.p AND x.prov_uid = d.u AND x.prov_version = d.n
        WHERE x.prov_etat = 'present'"""


def exporter(dossier_z2: str, lecteurs, sortie: str) -> dict:
    """Écrit `faits.parquet` dans `sortie` (Parquet seul : le CSV, 1,25 Go par nuit sur le périmètre
    complet, est abandonné le 12/11/2026). Rend le nombre de faits par type.

    Table par table (mémoire bornée) : chaque table est exportée dans un fichier à part, puis
    les morceaux sont assemblés au fil de l'eau, groupés par type de fait. L'ordre des lignes
    dans un type n'est pas garanti : on compare en joignant sur `cle_fait`."""
    import shutil

    import pyarrow as pa
    import pyarrow.parquet as pq

    from .memoire import regler_duckdb
    os.makedirs(sortie, exist_ok=True)
    morceaux_dir = os.path.join(sortie, "morceaux")
    shutil.rmtree(morceaux_dir, ignore_errors=True)
    os.makedirs(morceaux_dir)
    con = duckdb.connect()
    regler_duckdb(con)
    parts = []
    for mod in lecteurs:
        for table, spec in getattr(mod, "EXPORT", {}).items():
            chemin = os.path.join(dossier_z2, f"{mod.NOM}__{table}.parquet")
            if not os.path.exists(chemin):
                continue
            cols = [r[0] for r in con.execute(f"DESCRIBE SELECT * FROM read_parquet('{chemin}')").fetchall()]
            part = os.path.join(morceaux_dir, f"{spec['type']}__{mod.NOM}.parquet")
            # Pas de tri (il coûte trop de mémoire sur les tables larges) : deux nuits se
            # comparent en joignant sur `cle_fait`, pas par l'ordre des lignes.
            con.execute(f"COPY ({requete_table(chemin, spec, cols)}) "
                        f"TO '{part}' (FORMAT parquet, COMPRESSION zstd, ROW_GROUP_SIZE 10000)")
            parts.append((spec["type"], mod.NOM, part))
    if not parts:
        con.close()
        return {}
    compte, doublons = {}, 0
    for t, _, part in parts:
        n, d = con.execute(f"SELECT count(*), count(*) - count(DISTINCT cle_fait) "
                           f"FROM read_parquet('{part}')").fetchone()
        compte[t] = compte.get(t, 0) + n
        doublons += d
    con.close()
    # Deux lecteurs qui exportent le même type (identités de l'Assemblée et du Sénat) ont des
    # clés de même forme : on vérifie aussi les clés en double entre leurs morceaux.
    par_type: dict[str, list] = {}
    for t, _, part in parts:
        par_type.setdefault(t, []).append(part)
    con = duckdb.connect()
    regler_duckdb(con)
    for t, ps in par_type.items():
        if len(ps) > 1:
            liste = ", ".join(f"'{p}'" for p in ps)
            doublons += con.execute(f"SELECT count(*) - count(DISTINCT cle_fait) "
                                    f"FROM read_parquet([{liste}])").fetchone()[0]
    con.close()
    pq_ = os.path.join(sortie, "faits.parquet")
    # Toutes les colonnes peuvent être vides d'un type de fait à l'autre (un identifiant absent).
    schema = pa.schema([f.with_nullable(True) for f in pq.read_schema(parts[0][2])])
    with pq.ParquetWriter(pq_, schema, compression="zstd") as w:
        for t, _, part in sorted(parts):
            for b in pq.ParquetFile(part).iter_batches(batch_size=50_000):
                w.write_table(pa.Table.from_batches([b]).cast(schema))
    shutil.rmtree(morceaux_dir, ignore_errors=True)
    return {"faits_par_type": dict(sorted(compte.items())), "total": sum(compte.values()),
            "cles_en_double": doublons}
