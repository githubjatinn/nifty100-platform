"""Unit tests for the 16 DQ rules in validator.py, using crafted violation records."""

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src", "etl"))

from validator import (
    check_dq01_company_pk_uniqueness,
    check_dq02_annual_pk_uniqueness,
    check_dq03_fk_integrity,
    check_dq04_balance_sheet_balance,
    check_dq06_positive_sales,
    check_dq07_year_format,
    check_dq09_net_cash_check,
    check_dq16_coverage,
    validate_all,
)


def test_dq01_duplicate_company_id_flagged():
    companies = pd.DataFrame({"id": ["TCS", "TCS", "INFY"]})
    violations = check_dq01_company_pk_uniqueness(companies)
    assert len(violations) == 1
    assert violations[0]["rule_id"] == "DQ-01"
    assert violations[0]["severity"] == "CRITICAL"


def test_dq01_no_duplicates_passes():
    companies = pd.DataFrame({"id": ["TCS", "INFY"]})
    assert check_dq01_company_pk_uniqueness(companies) == []


def test_dq02_duplicate_year_pair_flagged():
    df = pd.DataFrame({"company_id": ["TCS", "TCS"], "year": ["2023-03", "2023-03"]})
    violations = check_dq02_annual_pk_uniqueness("profitandloss", df)
    assert len(violations) == 2
    assert violations[0]["severity"] == "CRITICAL"


def test_dq03_orphan_company_id_flagged():
    df = pd.DataFrame({"company_id": ["TCS", "GHOST"], "year": ["2023-03", "2023-03"]})
    violations = check_dq03_fk_integrity("profitandloss", df, valid_ids={"TCS", "INFY"})
    assert len(violations) == 1
    assert violations[0]["company_id"] == "GHOST"


def test_dq04_bs_balance():
    df = pd.DataFrame({
        "company_id": ["TCS"], "year": ["2023-03"],
        "total_assets": [1000.0], "total_liabilities": [1020.0],
    })
    violations = check_dq04_balance_sheet_balance(df)
    assert len(violations) == 1
    assert violations[0]["severity"] == "WARNING"


def test_dq04_bs_within_tolerance_passes():
    df = pd.DataFrame({
        "company_id": ["TCS"], "year": ["2023-03"],
        "total_assets": [1000.0], "total_liabilities": [1005.0],
    })
    assert check_dq04_balance_sheet_balance(df) == []


def test_dq06_zero_sales():
    df = pd.DataFrame({"company_id": ["TCS"], "year": ["2023-03"], "sales": [0]})
    violations = check_dq06_positive_sales(df)
    assert len(violations) == 1
    assert violations[0]["severity"] == "WARNING"


def test_dq06_positive_sales_passes():
    df = pd.DataFrame({"company_id": ["TCS"], "year": ["2023-03"], "sales": [225458]})
    assert check_dq06_positive_sales(df) == []


def test_dq07_bad_year_format_flagged():
    df = pd.DataFrame({"company_id": ["TCS"], "year": ["FY23"]})
    violations = check_dq07_year_format("profitandloss", df)
    assert len(violations) == 1
    assert violations[0]["severity"] == "CRITICAL"


def test_dq07_good_year_format_passes():
    df = pd.DataFrame({"company_id": ["TCS"], "year": ["2023-03"]})
    assert check_dq07_year_format("profitandloss", df) == []


def test_dq09_net_cash_mismatch_flagged():
    df = pd.DataFrame({
        "company_id": ["TCS"], "year": ["2023-03"],
        "operating_activity": [100.0], "investing_activity": [-50.0],
        "financing_activity": [-20.0], "net_cash_flow": [100.0],
    })
    violations = check_dq09_net_cash_check(df)
    assert len(violations) == 1


def test_dq09_net_cash_match_passes():
    df = pd.DataFrame({
        "company_id": ["TCS"], "year": ["2023-03"],
        "operating_activity": [100.0], "investing_activity": [-50.0],
        "financing_activity": [-20.0], "net_cash_flow": [30.0],
    })
    assert check_dq09_net_cash_check(df) == []


def test_dq16_insufficient_history_flagged():
    companies = pd.DataFrame({"id": ["TCS"]})
    pl = pd.DataFrame({"company_id": ["TCS"] * 2, "year": ["2021-03", "2022-03"]})
    bs = pd.DataFrame({"company_id": ["TCS"] * 2, "year": ["2021-03", "2022-03"]})
    cf = pd.DataFrame({"company_id": ["TCS"] * 2, "year": ["2021-03", "2022-03"]})
    violations = check_dq16_coverage(companies, pl, bs, cf)
    assert len(violations) == 1
    assert violations[0]["severity"] == "WARNING"


def test_validate_all_returns_expected_columns():
    tables = {"companies": pd.DataFrame({"id": ["TCS"]})}
    result = validate_all(tables)
    assert list(result.columns) == ["rule_id", "severity", "table", "company_id", "year", "field", "issue"]