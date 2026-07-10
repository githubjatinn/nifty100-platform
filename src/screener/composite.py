"""Computes the 0-100 composite quality score (profitability, cash quality, growth, leverage) with winsorization."""

import pandas as pd
import numpy as np

# Sub-metric weights within each pillar, using your real financial_ratios column names
PILLAR_METRICS = {
    "profitability": {"return_on_equity_pct": 0.15, "return_on_capital_pct": 0.10, "net_profit_margin_pct": 0.10},
    "cash_quality": {"fcf_conversion_pct": 0.15, "cfo_quality": 0.10, "free_cash_flow_cr": 0.05},
    "growth": {"revenue_cagr_5yr": 0.10, "pat_cagr_5yr": 0.10},
    "leverage": {"debt_to_equity": 0.10, "interest_coverage": 0.05},  # debt_to_equity inverted (lower is better)
}

INVERTED_METRICS = {"debt_to_equity"}


def _winsorize(series, lower_pct, upper_pct):
    """Caps outliers at the given percentile bounds before scaling."""
    lower = series.quantile(lower_pct)
    upper = series.quantile(upper_pct)
    return series.clip(lower=lower, upper=upper)


def _scale_0_100(series, invert=False):
    """Min-max scales a winsorized series to 0-100; inverts direction for metrics where lower is better."""
    min_v, max_v = series.min(), series.max()
    if max_v == min_v:
        return pd.Series(50.0, index=series.index)
    scaled = (series - min_v) / (max_v - min_v) * 100
    return 100 - scaled if invert else scaled


def compute_composite_score(df, config):
    """Adds a 'composite_quality_score' column (0-100) using winsorized, weighted, normalized metrics."""
    winsor_bounds = config["composite_score"]["winsorize_pct"]
    scored = df.copy()
    total_weighted = pd.Series(0.0, index=scored.index)

    for pillar, metrics in PILLAR_METRICS.items():
        for metric, weight in metrics.items():
            if metric not in scored.columns:
                continue
            raw = pd.to_numeric(scored[metric], errors="coerce")
            winsorized = _winsorize(raw.fillna(raw.median()), winsor_bounds[0], winsor_bounds[1])
            metric_score = _scale_0_100(winsorized, invert=(metric in INVERTED_METRICS))
            total_weighted += metric_score * weight

    scored["composite_quality_score"] = total_weighted.round(2)
    return scored


def compute_sector_relative_score(df, sector_column="broad_sector"):
    """Normalizes composite_quality_score within each sector so scores reflect performance vs sector peers."""
    scored = df.copy()

    def _rescale_group(group):
        min_v, max_v = group.min(), group.max()
        if max_v == min_v:
            return pd.Series(50.0, index=group.index)
        return (group - min_v) / (max_v - min_v) * 100

    scored["sector_relative_score"] = (
        scored.groupby(sector_column)["composite_quality_score"]
        .transform(_rescale_group)
        .round(2)
    )
    return scored


def compute_scores(df, config):
    """Runs composite scoring followed by sector-relative normalization; returns the enriched DataFrame."""
    with_composite = compute_composite_score(df, config)
    return compute_sector_relative_score(with_composite)