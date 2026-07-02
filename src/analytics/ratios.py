"""Financial Ratio Engine — computes 50+ KPIs for all 92 NIFTY100 companies."""

from __future__ import annotations

import math
from typing import Optional

import pandas as pd


def _safe_div(numerator, denominator):
    """Return numerator/denominator or None if either is None/zero."""
    if numerator is None or denominator is None:
        return None
    if denominator == 0:
        return None
    return numerator / denominator


def _pct(numerator, denominator):
    """Return numerator/denominator * 100 or None."""
    result = _safe_div(numerator, denominator)
    return result * 100 if result is not None else None


def net_profit_margin(net_profit, sales):
    """Net Profit Margin = net_profit / sales * 100."""
    return _pct(net_profit, sales)


def operating_profit_margin(operating_profit, sales):
    """Operating Profit Margin = operating_profit / sales * 100."""
    return _pct(operating_profit, sales)


def return_on_equity(net_profit, equity_capital, reserves):
    """ROE = net_profit / (equity_capital + reserves) * 100. None if equity <= 0."""
    if equity_capital is None or reserves is None:
        return None
    total_equity = equity_capital + reserves
    if total_equity <= 0:
        return None
    return _pct(net_profit, total_equity)


def ebit(operating_profit, depreciation):
    """EBIT = operating_profit - depreciation."""
    if operating_profit is None:
        return None
    dep = depreciation or 0
    return operating_profit - dep


def return_on_capital_employed(operating_profit, depreciation, equity_capital, reserves, borrowings):
    """ROCE = EBIT / (equity + reserves + borrowings) * 100."""
    ebit_val = ebit(operating_profit, depreciation)
    if ebit_val is None or equity_capital is None or reserves is None:
        return None
    borr = borrowings or 0
    capital_employed = equity_capital + reserves + borr
    if capital_employed <= 0:
        return None
    return _pct(ebit_val, capital_employed)


def return_on_assets(net_profit, total_assets):
    """ROA = net_profit / total_assets * 100."""
    return _pct(net_profit, total_assets)


def ebit_margin(operating_profit, depreciation, sales):
    """EBIT Margin = EBIT / sales * 100."""
    ebit_val = ebit(operating_profit, depreciation)
    return _pct(ebit_val, sales)


def debt_to_equity(borrowings, equity_capital, reserves):
    """D/E = borrowings / (equity + reserves). Returns 0 if debt-free."""
    if borrowings is None or equity_capital is None or reserves is None:
        return None
    total_equity = equity_capital + reserves
    if total_equity <= 0:
        return None
    borr = borrowings or 0
    return borr / total_equity


def interest_coverage(operating_profit, other_income, interest):
    """ICR = (operating_profit + other_income) / interest. None if interest = 0."""
    if operating_profit is None:
        return None
    if not interest:
        return None
    oi = other_income or 0
    return (operating_profit + oi) / interest


def asset_turnover(sales, total_assets):
    """Asset Turnover = sales / total_assets."""
    return _safe_div(sales, total_assets)


def net_debt(borrowings, investments):
    """Net Debt = borrowings - investments."""
    if borrowings is None:
        return None
    borr = borrowings or 0
    inv = investments or 0
    return borr - inv


def net_debt_to_ebitda(borrowings, investments, operating_profit):
    """Net Debt / EBITDA. None if EBITDA <= 0."""
    nd = net_debt(borrowings, investments)
    if nd is None or operating_profit is None or operating_profit <= 0:
        return None
    return nd / operating_profit


def fixed_asset_turnover(sales, fixed_assets):
    """Fixed Asset Turnover = sales / fixed_assets."""
    return _safe_div(sales, fixed_assets)


def free_cash_flow(operating_activity, investing_activity):
    """FCF = CFO + CFI."""
    if operating_activity is None:
        return None
    inv = investing_activity or 0
    return operating_activity + inv


def cfo_quality_score(operating_activity, net_profit):
    """CFO / PAT ratio. None if net_profit = 0."""
    return _safe_div(operating_activity, net_profit)


def capex_intensity(investing_activity, sales):
    """CapEx Intensity = abs(investing_activity) / sales * 100."""
    if investing_activity is None:
        return None
    return _pct(abs(investing_activity), sales)


def fcf_conversion(operating_activity, investing_activity, operating_profit):
    """FCF Conversion = FCF / EBITDA * 100."""
    fcf = free_cash_flow(operating_activity, investing_activity)
    return _pct(fcf, operating_profit)


def capital_allocation_pattern(operating_activity, investing_activity, financing_activity):
    """Classify into 8 CFO/CFI/CFF sign patterns."""
    def sign(v):
        if v is None or v == 0:
            return "0"
        return "+" if v > 0 else "-"
    pattern = f"{sign(operating_activity)}{sign(investing_activity)}{sign(financing_activity)}"
    labels = {
        "+-+": "Distress",
        "+--": "Reinvestor",
        "+-0": "Reinvestor",
        "+++": "Aggressive Growth",
        "+0-": "Shareholder Returns",
        "++-": "Expansion",
        "--+": "Distress",
        "---": "Contraction",
    }
    return labels.get(pattern, f"Other({pattern})")


def cagr(start_value, end_value, years):
    """Compute CAGR. Returns (value, flag)."""
    if years < 3:
        return None, "INSUFFICIENT"
    if start_value is None or end_value is None:
        return None, "INSUFFICIENT"
    if start_value == 0:
        return None, "ZERO_BASE"
    if start_value < 0 and end_value > 0:
        return None, "TURNAROUND"
    if start_value > 0 and end_value < 0:
        return None, "DECLINE_TO_LOSS"
    if start_value < 0 and end_value < 0:
        return None, "BOTH_NEGATIVE"
    result = (math.pow(end_value / start_value, 1 / years) - 1) * 100
    return result, "OK"


def _winsorise(series):
    """Winsorise at P10/P90."""
    p10 = series.quantile(0.10)
    p90 = series.quantile(0.90)
    return series.clip(lower=p10, upper=p90)


def _scale_0_100(series):
    """Min-max scale to 0-100 after winsorisation."""
    ws = _winsorise(series)
    rng = ws.max() - ws.min()
    if rng == 0:
        return pd.Series(50.0, index=series.index)
    return (ws - ws.min()) / rng * 100


def composite_quality_score(ratios_df):
    """Composite Quality Score = weighted combination of KPIs, scaled 0-100."""
    score = pd.Series(0.0, index=ratios_df.index)
    if "return_on_equity_pct" in ratios_df.columns:
        score += 0.15 * _scale_0_100(ratios_df["return_on_equity_pct"].fillna(0))
    if "return_on_capital_pct" in ratios_df.columns:
        score += 0.10 * _scale_0_100(ratios_df["return_on_capital_pct"].fillna(0))
    if "net_profit_margin_pct" in ratios_df.columns:
        score += 0.10 * _scale_0_100(ratios_df["net_profit_margin_pct"].fillna(0))
    if "cfo_quality" in ratios_df.columns:
        score += 0.10 * _scale_0_100(ratios_df["cfo_quality"].fillna(0))
    if "revenue_cagr_5yr" in ratios_df.columns:
        score += 0.10 * _scale_0_100(ratios_df["revenue_cagr_5yr"].fillna(0))
    if "pat_cagr_5yr" in ratios_df.columns:
        score += 0.10 * _scale_0_100(ratios_df["pat_cagr_5yr"].fillna(0))
    if "debt_to_equity" in ratios_df.columns:
        score += 0.15 * (100 - _scale_0_100(ratios_df["debt_to_equity"].fillna(5)))
    return score.clip(0, 100)