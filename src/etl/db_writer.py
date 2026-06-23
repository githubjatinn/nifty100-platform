"""SQLite database initialisation and insertion helpers for nifty100.db."""

from __future__ import annotations

import sqlite3

import pandas as pd


def init_database(db_path: str, schema_path: str) -> None:
    """Create all 10 tables in the SQLite database by applying schema.sql."""
    with open(schema_path, "r") as f:
        schema_sql = f.read()
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(schema_sql)
        conn.commit()
    finally:
        conn.close()


def insert_dataframe(table_name: str, df: pd.DataFrame, db_path: str) -> int:
    """Insert a normalised DataFrame into its matching SQLite table."""
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys = OFF")
        placeholders = ", ".join(["?"] * len(df.columns))
        cols = ", ".join(df.columns)
        sql = f"INSERT OR REPLACE INTO {table_name} ({cols}) VALUES ({placeholders})"
        conn.executemany(sql, df.values.tolist())
        conn.commit()
    except Exception as exc:
        conn.rollback()
        raise
    finally:
        conn.close()
    return len(df)


def table_row_count(table_name: str, db_path: str) -> int:
    """Return the current row count for a table (used for audit)."""
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.execute(f"SELECT COUNT(*) FROM {table_name}")
        return cursor.fetchone()[0]
    finally:
        conn.close()