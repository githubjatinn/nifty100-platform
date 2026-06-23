"""Schema / data-quality validator implementing the 16 DQ rules (DQ-01..DQ-16)."""

from __future__ import annotations

import os
import re
from typing import Dict, List

import pandas as pd

_YEAR_FORMAT_RE = re.compile(r"^\d{4}-\d{2}$")

VIOLATION_COLUMNS = ["rule_id", "severity", "table", "company_id", "year", "field", "issue"]

CHILD_TABLES = ["profitandloss", "balancesheet", "cashflow", "analysis", "documents", "prosandcons"]
TIME_SERIES_TABLES = ["profitandloss", "balancesheet", "cashflow"]


def check_dq01_company_pk_uniqueness(companies: pd.DataFrame) -> List[dict]:
    """DQ-01: every company id must be unique (CRITICAL)."""
    violations = []
    dupes = companies["id"][companies["id"].duplicated(keep=False)]
    for cid in dupes.unique():
        violations.append({"rule_id": "DQ-01", "severity": "CRITICAL", "table": "companies",
                            "company_id": cid, "year": None, "field": "id",
                            "issue": "duplicate company id"})
    return violations


def check_dq02_annual_pk_uniqueness(table_name: str, df: pd.DataFrame) -> List[dict]:
    """DQ-02: no duplicate (company_id, year) pairs in time-series tables (CRITICAL)."""
    violations = []
    dupe_mask = df.duplicated(subset=["company_id", "year"], keep=False)
    for _, row in df[dupe_mask].iterrows():
        violations.append({"rule_id": "DQ-02", "severity": "CRITICAL", "table": table_name,
                            "company_id": row["company_id"], "year": row["year"],
                            "field": "company_id,year", "issue": "duplicate (company_id, year) pair"})
    return violations


def check_dq03_fk_integrity(table_name: str, df: pd.DataFrame, valid_ids: set) -> List[dict]:
    """DQ-03: every company_id in a child table must exist in companies.id (CRITICAL)."""
    violations = []
    orphans = df[~df["company_id"].isin(valid_ids)]
    for _, row in orphans.iterrows():
        violations.append({"rule_id": "DQ-03", "severity": "CRITICAL", "table": table_name,
                            "company_id": row["company_id"], "year": row.get("year"),
                            "field": "company_id", "issue": "company_id not found in companies table"})
    return violations


def check_dq04_balance_sheet_balance(df: pd.DataFrame) -> List[dict]:
    """DQ-04: |total_assets - total_liabilities| / total_assets must be < 1% (WARNING)."""
    violations = []
    for _, row in df.iterrows():
        ta, tl = row.get("total_assets"), row.get("total_liabilities")
        if pd.notna(ta) and pd.notna(tl) and ta != 0:
            diff_pct = abs(ta - tl) / abs(ta)
            if diff_pct >= 0.01:
                violations.append({"rule_id": "DQ-04", "severity": "WARNING", "table": "balancesheet",
                                    "company_id": row["company_id"], "year": row["year"],
                                    "field": "total_assets,total_liabilities",
                                    "issue": f"balance sheet mismatch {diff_pct:.2%}"})
    return violations


def check_dq05_opm_cross_check(df: pd.DataFrame) -> List[dict]:
    """DQ-05: |opm_percentage - computed OPM| must be < 1.0 (WARNING)."""
    violations = []
    for _, row in df.iterrows():
        sales, op, opm = row.get("sales"), row.get("operating_profit"), row.get("opm_percentage")
        if pd.notna(sales) and pd.notna(op) and pd.notna(opm) and sales != 0:
            computed = op / sales * 100
            if abs(opm - computed) >= 1.0:
                violations.append({"rule_id": "DQ-05", "severity": "WARNING", "table": "profitandloss",
                                    "company_id": row["company_id"], "year": row["year"],
                                    "field": "opm_percentage",
                                    "issue": f"opm_percentage {opm} vs computed {computed:.2f}"})
    return violations


def check_dq06_positive_sales(df: pd.DataFrame) -> List[dict]:
    """DQ-06: sales must be > 0 for all non-bank companies (WARNING)."""
    violations = []
    for _, row in df.iterrows():
        sales = row.get("sales")
        if pd.notna(sales) and sales <= 0:
            violations.append({"rule_id": "DQ-06", "severity": "WARNING", "table": "profitandloss",
                                "company_id": row["company_id"], "year": row["year"],
                                "field": "sales", "issue": f"sales <= 0 ({sales})"})
    return violations


def check_dq07_year_format(table_name: str, df: pd.DataFrame) -> List[dict]:
    """DQ-07: normalised year values must match 'YYYY-MM' (CRITICAL)."""
    violations = []
    for _, row in df.iterrows():
        year = row.get("year")
        if pd.isna(year) or not _YEAR_FORMAT_RE.match(str(year)):
            violations.append({"rule_id": "DQ-07", "severity": "CRITICAL", "table": table_name,
                                "company_id": row.get("company_id"), "year": year,
                                "field": "year", "issue": f"year not in YYYY-MM format: {year!r}"})
    return violations


def check_dq08_ticker_format(table_name: str, df: pd.DataFrame, id_column: str) -> List[dict]:
    """DQ-08: company_id must be uppercase, stripped, 2-12 chars long (CRITICAL)."""
    violations = []
    for _, row in df.iterrows():
        cid = row.get(id_column)
        valid = pd.notna(cid) and 2 <= len(str(cid)) <= 12 and str(cid) == str(cid).strip().upper()
        if not valid:
            violations.append({"rule_id": "DQ-08", "severity": "CRITICAL", "table": table_name,
                                "company_id": cid, "year": row.get("year"),
                                "field": id_column, "issue": f"ticker format invalid: {cid!r}"})
    return violations


def check_dq09_net_cash_check(df: pd.DataFrame) -> List[dict]:
    """DQ-09: net_cash_flow must equal CFO+CFI+CFF within Rs 10 Cr tolerance (WARNING)."""
    violations = []
    for _, row in df.iterrows():
        cfo, cfi, cff = row.get("operating_activity"), row.get("investing_activity"), row.get("financing_activity")
        ncf = row.get("net_cash_flow")
        if pd.notna(ncf) and pd.notna(cfo) and pd.notna(cfi) and pd.notna(cff):
            if abs(ncf - (cfo + cfi + cff)) > 10:
                violations.append({"rule_id": "DQ-09", "severity": "WARNING", "table": "cashflow",
                                    "company_id": row["company_id"], "year": row["year"],
                                    "field": "net_cash_flow",
                                    "issue": f"net_cash_flow {ncf} vs computed {cfo + cfi + cff}"})
    return violations


def check_dq10_non_negative_fixed_assets(df: pd.DataFrame) -> List[dict]:
    """DQ-10: fixed_assets must be >= 0 (WARNING)."""
    violations = []
    for _, row in df.iterrows():
        fa = row.get("fixed_assets")
        if pd.notna(fa) and fa < 0:
            violations.append({"rule_id": "DQ-10", "severity": "WARNING", "table": "balancesheet",
                                "company_id": row["company_id"], "year": row["year"],
                                "field": "fixed_assets", "issue": f"negative fixed_assets: {fa}"})
    return violations


def check_dq11_tax_rate_range(df: pd.DataFrame) -> List[dict]:
    """DQ-11: tax_percentage must be within 0-60 (WARNING)."""
    violations = []
    for _, row in df.iterrows():
        tax = row.get("tax_percentage")
        if pd.notna(tax) and not (0 <= tax <= 60):
            violations.append({"rule_id": "DQ-11", "severity": "WARNING", "table": "profitandloss",
                                "company_id": row["company_id"], "year": row["year"],
                                "field": "tax_percentage", "issue": f"tax_percentage out of range: {tax}"})
    return violations


def check_dq12_dividend_payout_cap(df: pd.DataFrame) -> List[dict]:
    """DQ-12: dividend_payout must be <= 200 percent (WARNING)."""
    violations = []
    for _, row in df.iterrows():
        dp = row.get("dividend_payout")
        if pd.notna(dp) and dp > 200:
            violations.append({"rule_id": "DQ-12", "severity": "WARNING", "table": "profitandloss",
                                "company_id": row["company_id"], "year": row["year"],
                                "field": "dividend_payout", "issue": f"dividend_payout > 200%: {dp}"})
    return violations


def check_dq13_url_validity(df: pd.DataFrame, timeout: float = 5.0) -> List[dict]:
    """DQ-13: each Annual_Report URL should return HTTP 200 (WARNING, network call)."""
    import requests
    violations = []
    for _, row in df.iterrows():
        url = row.get("Annual_Report")
        if not url or pd.isna(url):
            continue
        try:
            resp = requests.head(url, timeout=timeout, allow_redirects=True)
            if resp.status_code != 200:
                violations.append({"rule_id": "DQ-13", "severity": "WARNING", "table": "documents",
                                    "company_id": row["company_id"], "year": row.get("Year"),
                                    "field": "Annual_Report", "issue": f"URL returned status {resp.status_code}"})
        except requests.RequestException as exc:
            violations.append({"rule_id": "DQ-13", "severity": "WARNING", "table": "documents",
                                "company_id": row["company_id"], "year": row.get("Year"),
                                "field": "Annual_Report", "issue": f"URL request failed: {exc}"})
    return violations


def check_dq14_eps_sign_consistency(df: pd.DataFrame) -> List[dict]:
    """DQ-14: eps must be > 0 whenever net_profit > 0 (WARNING)."""
    violations = []
    for _, row in df.iterrows():
        np_, eps = row.get("net_profit"), row.get("eps")
        if pd.notna(np_) and pd.notna(eps) and np_ > 0 and eps <= 0:
            violations.append({"rule_id": "DQ-14", "severity": "WARNING", "table": "profitandloss",
                                "company_id": row["company_id"], "year": row["year"],
                                "field": "eps", "issue": f"eps {eps} <= 0 but net_profit {np_} > 0"})
    return violations


def compute_dq15_strict_balance_count(df: pd.DataFrame) -> dict:
    """DQ-15: informational count of rows where total_assets == total_liabilities exactly (INFO)."""
    exact = (df["total_assets"] == df["total_liabilities"]).sum()
    return {"rule_id": "DQ-15", "severity": "INFO", "exact_balance_rows": int(exact), "total_rows": len(df)}


def check_dq16_coverage(companies: pd.DataFrame, pl: pd.DataFrame, bs: pd.DataFrame, cf: pd.DataFrame) -> List[dict]:
    """DQ-16: each company must have >= 5 years of P&L, BS, and CF records (WARNING)."""
    violations = []
    for cid in companies["id"]:
        pl_years = pl.loc[pl["company_id"] == cid, "year"].nunique()
        bs_years = bs.loc[bs["company_id"] == cid, "year"].nunique()
        cf_years = cf.loc[cf["company_id"] == cid, "year"].nunique()
        if min(pl_years, bs_years, cf_years) < 5:
            violations.append({"rule_id": "DQ-16", "severity": "WARNING", "table": "coverage",
                                "company_id": cid, "year": None, "field": "year_coverage",
                                "issue": f"insufficient history: PL={pl_years}, BS={bs_years}, CF={cf_years} yrs"})
    return violations


def validate_all(tables: Dict[str, pd.DataFrame], check_urls: bool = False) -> pd.DataFrame:
    """Run all 16 DQ rules against the loaded tables and return a violations DataFrame."""
    violations: List[dict] = []

    companies = tables.get("companies")
    valid_ids = set(companies["id"]) if companies is not None else set()
    if companies is not None:
        violations += check_dq01_company_pk_uniqueness(companies)
        violations += check_dq08_ticker_format("companies", companies, "id")

    for name in CHILD_TABLES:
        df = tables.get(name)
        if df is not None:
            violations += check_dq03_fk_integrity(name, df, valid_ids)
            violations += check_dq08_ticker_format(name, df, "company_id")

    for name in TIME_SERIES_TABLES:
        df = tables.get(name)
        if df is not None:
            violations += check_dq02_annual_pk_uniqueness(name, df)
            violations += check_dq07_year_format(name, df)

    pl = tables.get("profitandloss")
    if pl is not None:
        violations += check_dq05_opm_cross_check(pl)
        violations += check_dq06_positive_sales(pl)
        violations += check_dq11_tax_rate_range(pl)
        violations += check_dq12_dividend_payout_cap(pl)
        violations += check_dq14_eps_sign_consistency(pl)

    bs = tables.get("balancesheet")
    if bs is not None:
        violations += check_dq04_balance_sheet_balance(bs)
        violations += check_dq10_non_negative_fixed_assets(bs)

    cf = tables.get("cashflow")
    if cf is not None:
        violations += check_dq09_net_cash_check(cf)

    if companies is not None and pl is not None and bs is not None and cf is not None:
        violations += check_dq16_coverage(companies, pl, bs, cf)

    documents = tables.get("documents")
    if check_urls and documents is not None:
        violations += check_dq13_url_validity(documents)

    return pd.DataFrame(violations, columns=VIOLATION_COLUMNS)


def write_validation_failures(violations_df: pd.DataFrame, output_path: str) -> None:
    """Write the violations DataFrame to validation_failures.csv."""
    violations_df.to_csv(output_path, index=False)


if __name__ == "__main__":
    import argparse

    from loader import load_all_core_tables

    parser = argparse.ArgumentParser(description="Run the 16 DQ rules against the loaded core tables")
    parser.add_argument("--source-dir", default=os.path.join("..", "..", "data", "raw"))
    parser.add_argument("--output", default=os.path.join("..", "..", "output", "validation_failures.csv"))
    parser.add_argument("--check-urls", action="store_true")
    args = parser.parse_args()

    loaded = load_all_core_tables(args.source_dir)
    tables = {name: result.df for name, result in loaded.items()}
    violations_df = validate_all(tables, check_urls=args.check_urls)

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    write_validation_failures(violations_df, args.output)
    print(f"{len(violations_df)} DQ violation(s) found. Written to {args.output}")