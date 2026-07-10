"""Loads NIFTY100 financial data (joined across financial_ratios, sectors, market_cap) and applies threshold filters."""

import sqlite3
import math
import yaml
import pandas as pd

DB_PATH = "data/nifty100.db"
CONFIG_PATH = "config/screener_config.yaml"


def load_config(config_path=CONFIG_PATH):
    """Reads screener_config.yaml and returns the parsed dict."""
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def load_screener_data(db_path=DB_PATH):
    """Pulls the most-populated year's financial_ratios joined with sectors and market_cap."""
    conn = sqlite3.connect(db_path)
    try:
        query = """
            SELECT c.id AS company_id, c.company_name, s.broad_sector, s.sub_sector,
                   fr.*, mc.pe_ratio, mc.pb_ratio, mc.dividend_yield_pct, mc.market_cap_crore
            FROM companies c
            JOIN financial_ratios fr ON c.id = fr.company_id
            LEFT JOIN sectors s ON c.id = s.company_id
            LEFT JOIN market_cap mc ON c.id = mc.company_id
                AND mc.year = CAST(SUBSTR(fr.year, 1, 4) AS INTEGER)
            WHERE fr.year = (
                SELECT year FROM financial_ratios
                GROUP BY year
                ORDER BY COUNT(*) DESC, year DESC
                LIMIT 1
            )
        """
        df = pd.read_sql_query(query, conn)
    finally:
        conn.close()
    df = df.loc[:, ~df.columns.duplicated()]
    return df


def _passes_de_filter(row, de_max, financials_label):
    """Returns True if D/E filter passes; Financials sector is exempt from this filter entirely."""
    if de_max is None:
        return True
    if row.get("broad_sector") == financials_label:
        return True
    de = row.get("debt_to_equity")
    if de is None or (isinstance(de, float) and math.isnan(de)):
        return False
    return de <= de_max


def _passes_icr_filter(row, icr_min):
    """Returns True if ICR filter passes; debt-free companies (total_debt_cr = 0) always pass."""
    if icr_min is None:
        return True
    if row.get("total_debt_cr") == 0:
        return True
    icr = row.get("interest_coverage")
    if icr is None or (isinstance(icr, float) and math.isnan(icr)):
        return False
    return icr >= icr_min


def _passes_simple_min(row, column, min_val):
    """Generic >= threshold check that tolerates missing/NaN values by failing closed."""
    if min_val is None:
        return True
    val = row.get(column)
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return False
    return val >= min_val


def _passes_simple_max(row, column, max_val):
    """Generic <= threshold check that tolerates missing/NaN values by failing closed."""
    if max_val is None:
        return True
    val = row.get(column)
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return False
    return val <= max_val


def apply_filters(df, config):
    """Applies all active threshold filters from config to the DataFrame and returns the filtered universe."""
    f = config["filters"]
    financials_label = config["sectors"]["financials_label"]

    mask = df.apply(
        lambda row: (
            _passes_simple_min(row, "return_on_equity_pct", f.get("roe_min"))
            and _passes_de_filter(row, f.get("de_max"), financials_label)
            and _passes_simple_min(row, "free_cash_flow_cr", f.get("fcf_min"))
            and _passes_simple_min(row, "revenue_cagr_5yr", f.get("revenue_cagr_5yr_min"))
            and _passes_simple_min(row, "pat_cagr_5yr", f.get("pat_cagr_5yr_min"))
            and _passes_simple_min(row, "operating_profit_margin_pct", f.get("opm_min"))
            and _passes_simple_max(row, "pe_ratio", f.get("pe_max"))
            and _passes_simple_max(row, "pb_ratio", f.get("pb_max"))
            and _passes_simple_min(row, "dividend_yield_pct", f.get("dividend_yield_min"))
            and _passes_icr_filter(row, f.get("icr_min"))
            and _passes_simple_min(row, "market_cap_crore", f.get("market_cap_min"))
        ),
        axis=1,
    )
    return df[mask].copy()


def run_screener(db_path=DB_PATH, config_path=CONFIG_PATH):
    """End-to-end entry point: load config, load data, filter, return DataFrame ready for composite scoring."""
    config = load_config(config_path)
    df = load_screener_data(db_path)
    filtered = apply_filters(df, config)
    filtered["composite_quality_score"] = None
    return filtered


if __name__ == "__main__":
    result = run_screener()
    print(f"{len(result)} companies passed the active filters.")