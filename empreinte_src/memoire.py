"""Réglage commun de DuckDB : mémoire bornée, débordement sur disque.

La limite se règle par la variable d'environnement EMPREINTE_DUCKDB_MEMOIRE (1 Go par
défaut) : la machine de développement a 7,8 Gio, celle de GitHub 16 Go (cahier 5.2)."""
import os
import tempfile


def regler_duckdb(con):
    """Règle la connexion DuckDB `con` : limite de mémoire (`EMPREINTE_DUCKDB_MEMOIRE`, 1 Go par
    défaut), dossier de débordement (`duckdb-empreinte` sous `EMPREINTE_DUCKDB_TMP`, ou le dossier
    temporaire du système), ordre d'insertion non conservé, nombre de fils
    (`EMPREINTE_DUCKDB_FILS`, 2 par défaut). Ne rend rien."""
    con.execute(f"SET memory_limit='{os.environ.get('EMPREINTE_DUCKDB_MEMOIRE', '1GB')}'")
    con.execute(f"SET temp_directory='{os.environ.get('EMPREINTE_DUCKDB_TMP', tempfile.gettempdir())}/duckdb-empreinte'")
    con.execute("SET preserve_insertion_order=false")   # l'ordre voulu est toujours explicite (ORDER BY)
    con.execute(f"SET threads={int(os.environ.get('EMPREINTE_DUCKDB_FILS', '2'))}")  # moins de fils, moins de mémoire
