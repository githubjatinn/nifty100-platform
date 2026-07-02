"""Ratio Engine — computes all KPIs for all 92 companies and writes to financial_ratios table."""

from __future__ import annotations

import logging
import os
import sqlite3
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "etl"))
sys.path.insert(0, os.path.dirname(__file__))

from ratios import (
    net_profit_margin, operating_profit_margin, return_on_equity,
    return_on_capital_employed, return_on_assets, ebit_margin,
    debt_to_equity, interest_coverage, asset_turnover,
    net_debt, net_debt_to_ebitda, fixed_asset_turnover,
    free_cash_flow, cfo_quality_score, capex_intensity,
    fcf_conversion, capital_allocation_pattern, cagr,
)

logger = logging.getLogger(__name__)

CAGR_WINDOWS = [3, 5, 10]
FINANCIAL_SECTORS = {"Financials"}


def _load_tables(db_path):
    """Load all required tables from SQLite into DataFrames."""
    conn = sqlite3.connect(db_path)
    try:
        tables = {}
        for name in ["companies", "profitandloss", "balancesheet", "cashflow", "sectors"]:
            tables[name] = pd.read_sql(f"SELECT * FROM {name}", conn)
        return tables
    finally:
        conn.close()


def _get_val(row, col):
    """Return None if value is NaN or missing, else float."""
    val = row.get(col)
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    return float(val)


def compute_ratios_for_company(company_id, pl, bs, cf, broad_sector):
    """Compute all KPIs for one company across all available years."""
    results = []

    pl_c = pl[pl["company_id"] == company_id].sort_values("year").reset_index(drop=True)
    bs_c = bs[bs["company_id"] == company_id].sort_values("year").reset_index(drop=True)
    cf_c = cf[cf["company_id"] == company_id].sort_values("year").reset_index(drop=True)

    if pl_c.empty:
        return results

    rev_series = pd.to_numeric(pl_c["sales"], errors="coerce")
    pat_series = pd.to_numeric(pl_c["net_profit"], errors="coerce")
    eps_series = pd.to_numeric(pl_c["eps"], errors="coerce") if "eps" in pl_c.columns else pd.Series(dtype=float)

    rev_cagr = {}
    pat_cagr = {}
    eps_cagr = {}
    n = len(pl_c)
    for w in CAGR_WINDOWS:
        if n > w:
            rv, rf = cagr(rev_series.iloc[-(w+1)], rev_series.iloc[-1], w)
            pv, pf = cagr(pat_series.iloc[-(w+1)], pat_series.iloc[-1], w)
            rev_cagr[w] = (rv, rf)
            pat_cagr[w] = (pv, pf)
            if not eps_series.empty and len(eps_series) > w:
                ev, ef = cagr(eps_series.iloc[-(w+1)], eps_series.iloc[-1], w)
                eps_cagr[w] = (ev, ef)
            else:
                eps_cagr[w] = (None, "INSUFFICIENT")
        else:
            rev_cagr[w] = (None, "INSUFFICIENT")
            pat_cagr[w] = (None, "INSUFFICIENT")
            eps_cagr[w] = (None, "INSUFFICIENT")

    is_financial = broad_sector in FINANCIAL_SECTORS

    for _, pl_row in pl_c.iterrows():
        year = pl_row["year"]

        bs_match = bs_c[bs_c["year"] == year]
        cf_match = cf_c[cf_c["year"] == year]
        bs_row = bs_match.iloc[0] if not bs_match.empty else pd.Series(dtype=float)
        cf_row = cf_match.iloc[0] if not cf_match.empty else pd.Series(dtype=float)

        sales = _get_val(pl_row, "sales")
        op = _get_val(pl_row, "operating_profit")
        other_inc = _get_val(pl_row, "other_income")
        interest = _get_val(pl_row, "interest")
        dep = _get_val(pl_row, "depreciation")
        net_prof = _get_val(pl_row, "net_profit")
        eps_val = _get_val(pl_row, "eps")
        div_payout = _get_val(pl_row, "dividend_payout")

        eq_cap = _get_val(bs_row, "equity_capital")
        reserves = _get_val(bs_row, "reserves")
        borr = _get_val(bs_row, "borrowings")
        fixed_ass = _get_val(bs_row, "fixed_assets")
        investments = _get_val(bs_row, "investments")
        total_assets = _get_val(bs_row, "total_assets")

        cfo = _get_val(cf_row, "operating_activity")
        cfi = _get_val(cf_row, "investing_activity")
        cff = _get_val(cf_row, "financing_activity")

        de_val = debt_to_equity(borr, eq_cap, reserves)
        de_flag = "HIGH_DE" if (not is_financial and de_val is not None and de_val > 2) else "OK"

        row = {
            "company_id": company_id,
            "year": year,
            "net_profit_margin_pct": net_profit_margin(net_prof, sales),
            "operating_profit_margin_pct": operating_profit_margin(op, sales),
            "ebit_margin_pct": ebit_margin(op, dep, sales),
            "return_on_equity_pct": return_on_equity(net_prof, eq_cap, reserves),
            "return_on_capital_pct": return_on_capital_employed(op, dep, eq_cap, reserves, borr),
            "return_on_assets_pct": return_on_assets(net_prof, total_assets),
            "earnings_per_share": eps_val,
            "dividend_payout_ratio_pct": div_payout,
            "debt_to_equity": de_val,
            "interest_coverage": interest_coverage(op, other_inc, interest),
            "net_debt_cr": net_debt(borr, investments),
            "net_debt_to_ebitda": net_debt_to_ebitda(borr, investments, op),
            "asset_turnover": asset_turnover(sales, total_assets),
            "fixed_asset_turnover": fixed_asset_turnover(sales, fixed_ass),
            "free_cash_flow_cr": free_cash_flow(cfo, cfi),
            "cfo_quality": cfo_quality_score(cfo, net_prof),
            "capex_intensity_pct": capex_intensity(cfi, sales),
            "fcf_conversion_pct": fcf_conversion(cfo, cfi, op),
            "cash_from_operations_cr": cfo,
            "capital_allocation_pattern": capital_allocation_pattern(cfo, cfi, cff),
            "total_debt_cr": borr,
            "revenue_cagr_3yr": rev_cagr[3][0],
            "revenue_cagr_5yr": rev_cagr[5][0],
            "revenue_cagr_10yr": rev_cagr[10][0],
            "pat_cagr_3yr": pat_cagr[3][0],
            "pat_cagr_5yr": pat_cagr[5][0],
            "eps_cagr_5yr": eps_cagr.get(5, (None, "INSUFFICIENT"))[0],
            "de_flag": de_flag,
            "revenue_cagr_5yr_flag": rev_cagr[5][1],
            "pat_cagr_5yr_flag": pat_cagr[5][1],
        }
        results.append(row)

    return results


def run_ratio_engine(db_path, edge_case_log_path):
    """Compute all KPIs for all 92 companies and write to financial_ratios table."""
    tables = _load_tables(db_path)
    companies = tables["companies"]
    pl = tables["profitandloss"]
    bs = tables["balancesheet"]
    cf = tables["cashflow"]
    sectors = tables["sectors"]

    sector_map = dict(zip(sectors["company_id"], sectors["broad_sector"]))

    all_rows = []
    edge_cases = []

    for company_id in companies["id"]:
        broad_sector = sector_map.get(company_id, "Unknown")
        rows = compute_ratios_for_company(company_id, pl, bs, cf, broad_sector)
        all_rows.extend(rows)

        for row in rows:
            if row.get("revenue_cagr_5yr_flag") not in ("OK", None):
                edge_cases.append({"company_id": company_id, "year": row["year"],
                                    "type": "revenue_cagr_5yr", "flag": row["revenue_cagr_5yr_flag"]})
            if row.get("pat_cagr_5yr_flag") not in ("OK", None):
                edge_cases.append({"company_id": company_id, "year": row["year"],
                                    "type": "pat_cagr_5yr", "flag": row["pat_cagr_5yr_flag"]})
            if row.get("de_flag") == "HIGH_DE":
                edge_cases.append({"company_id": company_id, "year": row["year"],
                                    "type": "high_de", "flag": f"D/E={row.get('debt_to_equity')}"})

    ratios_df = pd.DataFrame(all_rows)

    conn = sqlite3.connect(db_path)
    try:
        ratios_df.to_sql("financial_ratios", conn, if_exists="replace", index=False)
        conn.commit()
        logger.info("financial_ratios populated: %d rows", len(ratios_df))
    finally:
        conn.close()

    os.makedirs(os.path.dirname(edge_case_log_path), exist_ok=True)
    pd.DataFrame(edge_cases).to_csv(edge_case_log_path, index=False)
    logger.info("Edge cases: %d -> %s", len(edge_cases), edge_case_log_path)

    return ratios_df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    DB_PATH = os.path.join("data", "nifty100.db")
    LOG_PATH = os.path.join("output", "ratio_edge_cases.csv")
    df = run_ratio_engine(DB_PATH, LOG_PATH)
    print(f"\nRatio Engine complete: {len(df)} rows for {df['company_id'].nunique()} companies")
    print(df[["company_id", "year", "return_on_equity_pct", "debt_to_equity",
              "free_cash_flow_cr", "revenue_cagr_5yr"]].head(10).to_string(index=False))