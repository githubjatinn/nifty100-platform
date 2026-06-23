"""Excel ingestion for the 7 core NIFTY100 datasets (header=1 layout)."""

from __future__ import annotations

import logging
import os
from typing import Dict

import pandas as pd

from normaliser import normalize_ticker, normalize_year

logger = logging.getLogger(__name__)

CORE_FILES = {
    "companies": "companies.xlsx",
    "profitandloss": "profitandloss.xlsx",
    "balancesheet": "balancesheet.xlsx",
    "cashflow": "cashflow.xlsx",
    "analysis": "analysis.xlsx",
    "documents": "documents.xlsx",
    "prosandcons": "prosandcons.xlsx",
}

TICKER_COLUMN = {
    "companies": "id",
    "profitandloss": "company_id",
    "balancesheet": "company_id",
    "cashflow": "company_id",
    "analysis": "company_id",
    "documents": "company_id",
    "prosandcons": "company_id",
}

# documents.xlsx has a plain calendar-year 'Year' column -- not fiscal, no normalize_year().
YEAR_COLUMN = {
    "profitandloss": "year",
    "balancesheet": "year",
    "cashflow": "year",
}


class LoadResult:
    """Holds a cleaned DataFrame plus per-table load/rejection counters."""

    def __init__(self, table_name: str, df: pd.DataFrame, rows_in: int,
                 ticker_rejects: int = 0, year_rejects: int = 0):
        self.table_name = table_name
        self.df = df
        self.rows_in = rows_in
        self.rows_out = len(df)
        self.ticker_rejects = ticker_rejects
        self.year_rejects = year_rejects

    @property
    def rejected(self) -> int:
        """Total rows rejected across ticker + year normalisation."""
        return self.ticker_rejects + self.year_rejects

    def as_audit_row(self) -> dict:
        """Return this result as a row dict for load_audit.csv."""
        return {
            "table": self.table_name,
            "rows_in": self.rows_in,
            "rows_out": self.rows_out,
            "rejected": self.rejected,
            "ticker_rejects": self.ticker_rejects,
            "year_rejects": self.year_rejects,
        }


def load_excel_file(filepath: str, header: int = 1) -> pd.DataFrame:
    """Read one Excel file; core files use header=1 since row 0 is metadata."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Source file not found: {filepath}")
    return pd.read_excel(filepath, header=header)


def _normalise_ticker_column(df: pd.DataFrame, column: str, table_name: str):
    """Apply normalize_ticker() to a column, dropping rows that fail."""
    cleaned, rejected = [], 0
    for value in df[column]:
        try:
            cleaned.append(normalize_ticker(value))
        except ValueError:
            cleaned.append(None)
            rejected += 1
    df = df.copy()
    df[column] = cleaned
    if rejected:
        logger.warning("%s: %d row(s) rejected on ticker normalisation", table_name, rejected)
    return df[df[column].notna()].reset_index(drop=True), rejected


def _normalise_year_column(df: pd.DataFrame, column: str, table_name: str):
    """Apply normalize_year() to a column, dropping rows that fail (PARSE_ERROR)."""
    cleaned, rejected = [], 0
    for value in df[column]:
        try:
            cleaned.append(normalize_year(value))
        except ValueError:
            cleaned.append(None)
            rejected += 1
    df = df.copy()
    df[column] = cleaned
    if rejected:
        logger.warning("%s: %d row(s) rejected on year normalisation", table_name, rejected)
    return df[df[column].notna()].reset_index(drop=True), rejected


def load_core_table(table_name: str, source_dir: str) -> LoadResult:
    """Load and normalise one of the 7 core tables by name."""
    if table_name not in CORE_FILES:
        raise ValueError(f"Unknown core table '{table_name}'")

    filepath = os.path.join(source_dir, CORE_FILES[table_name])
    df = load_excel_file(filepath, header=1)
    rows_in = len(df)

    ticker_rejects = year_rejects = 0

    ticker_col = TICKER_COLUMN.get(table_name)
    if ticker_col:
        df, ticker_rejects = _normalise_ticker_column(df, ticker_col, table_name)

    year_col = YEAR_COLUMN.get(table_name)
    if year_col:
        df, year_rejects = _normalise_year_column(df, year_col, table_name)

    return LoadResult(table_name, df, rows_in, ticker_rejects, year_rejects)


def load_all_core_tables(source_dir: str) -> Dict[str, LoadResult]:
    """Load and normalise all 7 core Excel files into a dict of LoadResults."""
    results: Dict[str, LoadResult] = {}
    for table_name in CORE_FILES:
        try:
            result = load_core_table(table_name, source_dir)
            results[table_name] = result
            logger.info(
                "%s: %d rows in -> %d rows out (%d rejected)",
                table_name, result.rows_in, result.rows_out, result.rejected,
            )
        except FileNotFoundError as exc:
            logger.error(str(exc))
    return results


def write_load_audit(results: Dict[str, LoadResult], output_path: str) -> None:
    """Write a per-table audit CSV: table, rows_in, rows_out, rejected, ..."""
    rows = [r.as_audit_row() for r in results.values()]
    pd.DataFrame(rows).to_csv(output_path, index=False)
    logger.info("Load audit written to %s", output_path)


if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(description="Load the 7 core NIFTY100 Excel files")
    parser.add_argument("--source-dir", default=os.path.join("..", "..", "data", "raw"))
    parser.add_argument("--audit-out", default=os.path.join("..", "..", "output", "load_audit.csv"))
    args = parser.parse_args()

    loaded = load_all_core_tables(args.source_dir)
    for name, result in loaded.items():
        print(f"{name}: {result.rows_out} rows ({result.rejected} rejected)")

    os.makedirs(os.path.dirname(args.audit_out), exist_ok=True)
    write_load_audit(loaded, args.audit_out)