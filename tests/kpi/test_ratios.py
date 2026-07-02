"""20 KPI formula tests for ratios.py covering all edge cases from the project spec."""

import sys
import os
import math

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src", "analytics"))

import pytest
from ratios import (
    net_profit_margin, operating_profit_margin, return_on_equity,
    return_on_capital_employed, return_on_assets, debt_to_equity,
    interest_coverage, asset_turnover, free_cash_flow, cfo_quality_score,
    capex_intensity, fcf_conversion, capital_allocation_pattern, cagr,
)


def test_npm_normal():
    assert abs(net_profit_margin(34990, 225458) - 15.52) < 0.1

def test_npm_zero_sales():
    assert net_profit_margin(100, 0) is None

def test_npm_none_sales():
    assert net_profit_margin(100, None) is None

def test_npm_negative_profit():
    result = net_profit_margin(-500, 10000)
    assert result < 0

def test_roe_positive_equity():
    result = return_on_equity(100, 500, 0)
    assert abs(result - 20.0) < 0.01

def test_roe_negative_equity():
    assert return_on_equity(100, -500, 0) is None

def test_roe_zero_equity():
    assert return_on_equity(100, 0, 0) is None

def test_roce_normal():
    result = return_on_capital_employed(48534, 5800, 366, 80000, 0)
    assert result is not None and result > 0

def test_roa_normal():
    assert abs(return_on_assets(100, 1000) - 10.0) < 0.01

def test_de_debt_free():
    assert debt_to_equity(0, 500, 100) == 0.0

def test_de_normal():
    result = debt_to_equity(500, 300, 200)
    assert abs(result - 1.0) < 0.01

def test_icr_debt_free():
    assert interest_coverage(50000, 3800, 0) is None

def test_icr_normal():
    result = interest_coverage(48534, 3800, 9000)
    assert result is not None and result > 1

def test_asset_turnover_normal():
    result = asset_turnover(225458, 100366)
    assert result is not None and result > 1

def test_cagr_normal():
    val, flag = cagr(100, 161, 5)
    assert flag == "OK"
    assert abs(val - 10.0) < 0.5

def test_cagr_turnaround():
    val, flag = cagr(-100, 200, 5)
    assert flag == "TURNAROUND"
    assert val is None

def test_cagr_decline_to_loss():
    val, flag = cagr(100, -50, 5)
    assert flag == "DECLINE_TO_LOSS"
    assert val is None

def test_cagr_insufficient():
    val, flag = cagr(100, 200, 2)
    assert flag == "INSUFFICIENT"

def test_fcf_normal():
    assert free_cash_flow(38000, -8000) == 30000

def test_capital_allocation_reinvestor():
    assert capital_allocation_pattern(38000, -8000, -25000) == "Reinvestor"

def test_capital_allocation_distress():
    assert capital_allocation_pattern(-5000, -2000, 10000) == "Distress"