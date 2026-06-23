"""Day 5: full pipeline -- load all 12 source files into nifty100.db and write load_audit.csv."""

from __future__ import annotations

import logging
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join("src", "etl"))

from normaliser import normalize_ticker, normalize_year
from loader import load_all_core_tables
from db_writer import init_database, insert_dataframe

logger = logging.getLogger(__name__)

SUPP_FILES = {
    "sectors": "sectors.xlsx",
    "stock_prices": "stock_prices.xlsx",
    "market_cap": "market_cap.xlsx",
    "financial_ratios": "financial_ratios.xlsx",
    "peer_groups": "peer_groups.xlsx",
}

SUPP_YEAR_COLUMN = {"financial_ratios": "year"}


def load_supplementary_table(table_name: str, source_dir: str):
    """Load and normalise one supplementary table (header=0)."""
    path = os.path.join(source_dir, SUPP_FILES[table_name])
    df = pd.read_excel(path, header=0)
    rows_in = len(df)
    rejected = 0

    if "company_id" in df.columns:
        cleaned = []
        for value in df["company_id"]:
            try:
                cleaned.append(normalize_ticker(value))
            except ValueError:
                cleaned.append(None)
                rejected += 1
        df = df.copy()
        df["company_id"] = cleaned
        df = df[df["company_id"].notna()].reset_index(drop=True)

    year_col = SUPP_YEAR_COLUMN.get(table_name)
    if year_col:
        cleaned = []
        for value in df[year_col]:
            try:
                cleaned.append(normalize_year(value))
            except ValueError:
                cleaned.append(None)
                rejected += 1
        df = df.copy()
        df[year_col] = cleaned
        df = df[df[year_col].notna()].reset_index(drop=True)

    return df, rows_in, rejected


def run_full_load(raw_dir, supp_dir, db_path, schema_path, audit_path):
    """Load all 12 source files into nifty100.db and write the per-table load audit CSV."""
    if os.path.exists(db_path):
        os.remove(db_path)
    init_database(db_path, schema_path)
    audit_rows = []

    core_order = ["companies", "profitandloss", "balancesheet", "cashflow",
                  "analysis", "documents", "prosandcons"]
    loaded = load_all_core_tables(raw_dir)
    for name in core_order:
        result = loaded.get(name)
        if result is None:
            audit_rows.append({"table": name, "rows_in": 0, "rows_out": 0,
                                "rejected": 0, "status": "FILE NOT FOUND"})
            continue
        try:
            insert_dataframe(name, result.df, db_path)
            audit_rows.append({"table": name, "rows_in": result.rows_in,
                                "rows_out": result.rows_out, "rejected": result.rejected,
                                "status": "OK"})
        except Exception as exc:
            audit_rows.append({"table": name, "rows_in": result.rows_in,
                                "rows_out": result.rows_out, "rejected": result.rejected,
                                "status": f"INSERT FAILED: {exc}"})

    for name in ["sectors", "stock_prices", "market_cap", "financial_ratios", "peer_groups"]:
        try:
            df, rows_in, rejected = load_supplementary_table(name, supp_dir)
            insert_dataframe(name, df, db_path)
            audit_rows.append({"table": name, "rows_in": rows_in, "rows_out": len(df),
                                "rejected": rejected, "status": "OK"})
        except Exception as exc:
            audit_rows.append({"table": name, "rows_in": 0, "rows_out": 0,
                                "rejected": 0, "status": f"FAILED: {exc}"})

    pd.DataFrame(audit_rows).to_csv(audit_path, index=False)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    RAW_DIR = os.path.join("data", "raw")
    SUPP_DIR = os.path.join("data", "supporting")
    DB_PATH = os.path.join("data", "nifty100.db")
    SCHEMA_PATH = os.path.join("src", "etl", "schema.sql")
    AUDIT_PATH = os.path.join("output", "load_audit.csv")

    os.makedirs(os.path.dirname(AUDIT_PATH), exist_ok=True)
    run_full_load(RAW_DIR, SUPP_DIR, DB_PATH, SCHEMA_PATH, AUDIT_PATH)

    print(f"\nLoad complete. Audit written to {AUDIT_PATH}")
    print(pd.read_csv(AUDIT_PATH).to_string(index=False))