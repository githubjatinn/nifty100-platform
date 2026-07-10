"""Unit tests for Sprint 3: filter engine, presets, composite score, and peer percentile ranking."""

import math
import pandas as pd
import pytest

from src.screener.engine import apply_filters, _passes_de_filter, _passes_icr_filter
from src.screener.composite import compute_composite_score, compute_sector_relative_score
from src.analytics.peer import compute_peer_percentiles, NO_PEER_GROUP_MSG


@pytest.fixture
def sample_config():
    """Minimal config mirroring screener_config.yaml structure for isolated unit testing."""
    return {
        "filters": {
            "roe_min": 15.0,
            "de_max": 1.0,
            "fcf_min": 0.0,
            "revenue_cagr_5yr_min": None,
            "pat_cagr_5yr_min": None,
            "opm_min": None,
            "pe_max": None,
            "pb_max": None,
            "dividend_yield_min": None,
            "icr_min": 3.0,
            "market_cap_min": None,
        },
        "sectors": {"financials_label": "Financials"},
        "composite_score": {"winsorize_pct": [0.10, 0.90]},
        "peer_percentiles": {
            "metrics": ["roe", "de"],
            "min_peer_group_size": 3,
        },
    }


@pytest.fixture
def sample_df():
    """5-company sample universe covering Financials exemption and debt-free (infinite ICR) cases."""
    return pd.DataFrame(
        [
            {"company_id": 1, "name": "A", "sector": "IT", "roe": 20, "de": 0.5, "fcf": 100, "interest_coverage_ratio": 5},
            {"company_id": 2, "name": "B", "sector": "IT", "roe": 10, "de": 0.5, "fcf": 100, "interest_coverage_ratio": 5},
            {"company_id": 3, "name": "C", "sector": "Financials", "roe": 18, "de": 5.0, "fcf": 50, "interest_coverage_ratio": 4},
            {"company_id": 4, "name": "D", "sector": "FMCG", "roe": 25, "de": 0.0, "fcf": 200, "interest_coverage_ratio": float("inf")},
            {"company_id": 5, "name": "E", "sector": "FMCG", "roe": 22, "de": 0.2, "fcf": -10, "interest_coverage_ratio": 2},
        ]
    )


def test_de_filter_skips_financials(sample_df, sample_config):
    """Financials-sector company with D/E > threshold should still pass the D/E component."""
    row = sample_df.iloc[2]
    assert _passes_de_filter(row, 1.0, "Financials") is True


def test_de_filter_fails_non_financials_high_de(sample_df, sample_config):
    """Non-Financials company with D/E above threshold should fail the D/E component."""
    high_de_row = pd.Series({"sector": "IT", "de": 2.0})
    assert _passes_de_filter(high_de_row, 1.0, "Financials") is False


def test_icr_infinite_always_passes(sample_config):
    """Debt-free company with ICR = infinity should always pass regardless of threshold."""
    row = pd.Series({"interest_coverage_ratio": float("inf")})
    assert _passes_icr_filter(row, 10.0) is True


def test_icr_below_threshold_fails(sample_config):
    """Company with finite ICR below threshold should fail."""
    row = pd.Series({"interest_coverage_ratio": 1.5})
    assert bool(_passes_icr_filter(row, 3.0)) is False


def test_apply_filters_quality_compounder(sample_df, sample_config):
    """Base filters (ROE>=15, D/E<=1 unless Financials, FCF>=0, ICR>=3) should keep companies A, C, D."""
    result = apply_filters(sample_df, sample_config)
    assert set(result["company_id"]) == {1, 3, 4}


def test_apply_filters_excludes_negative_fcf(sample_df, sample_config):
    """Company E has negative FCF and should be excluded even though ROE and D/E pass."""
    result = apply_filters(sample_df, sample_config)
    assert 5 not in set(result["company_id"])


def test_composite_score_range(sample_df, sample_config):
    """Composite quality score should be bounded between 0 and 100 after winsorization/scaling."""
    scored = compute_composite_score(sample_df, sample_config)
    assert scored["composite_quality_score"].between(0, 100).all()


def test_sector_relative_score_present(sample_df, sample_config):
    """Sector-relative score column should exist and be bounded 0-100 within each sector group."""
    scored = compute_composite_score(sample_df, sample_config)
    scored = compute_sector_relative_score(scored)
    assert "sector_relative_score" in scored.columns
    assert scored["sector_relative_score"].between(0, 100).all()


def test_peer_percentile_highest_roe_gets_top_rank(sample_config):
    """Within a peer group, the company with the highest ROE should receive the highest ROE percentile."""
    df = pd.DataFrame(
        [
            {"company_id": 1, "peer_group_name": "IT Services", "roe": 30, "de": 0.5},
            {"company_id": 2, "peer_group_name": "IT Services", "roe": 15, "de": 0.5},
            {"company_id": 3, "peer_group_name": "IT Services", "roe": 20, "de": 0.5},
        ]
    )
    result = compute_peer_percentiles(df, sample_config)
    top_roe_row = result[(result["company_id"] == 1) & (result["metric"] == "roe")].iloc[0]
    assert top_roe_row["percentile_rank"] == 100.0


def test_peer_percentile_no_group_below_min_size(sample_config):
    """Peer groups smaller than min_peer_group_size should be labelled NO_PEER_GROUP_MSG with null percentile."""
    df = pd.DataFrame(
        [
            {"company_id": 10, "peer_group_name": "Tiny Group", "roe": 20, "de": 0.5},
            {"company_id": 11, "peer_group_name": "Tiny Group", "roe": 15, "de": 0.5},
        ]
    )
    result = compute_peer_percentiles(df, sample_config)
    assert (result["peer_group_name"] == NO_PEER_GROUP_MSG).all()
    assert result["percentile_rank"].isna().all()


def test_de_percentile_inverted(sample_config):
    """D/E is inverted: the company with the LOWEST D/E should get the HIGHEST percentile rank."""
    df = pd.DataFrame(
        [
            {"company_id": 1, "peer_group_name": "Auto", "roe": 20, "de": 0.2},
            {"company_id": 2, "peer_group_name": "Auto", "roe": 20, "de": 1.5},
            {"company_id": 3, "peer_group_name": "Auto", "roe": 20, "de": 0.8},
        ]
    )
    result = compute_peer_percentiles(df, sample_config)
    lowest_de_row = result[(result["company_id"] == 1) & (result["metric"] == "de")].iloc[0]
    assert lowest_de_row["percentile_rank"] == 100.0


def test_no_raised_errors_on_missing_metric_column(sample_config):
    """compute_peer_percentiles should not raise even if a configured metric column is absent from the data."""
    df = pd.DataFrame(
        [
            {"company_id": 1, "peer_group_name": "Auto", "roe": 20},
            {"company_id": 2, "peer_group_name": "Auto", "roe": 18},
            {"company_id": 3, "peer_group_name": "Auto", "roe": 22},
        ]
    )
    result = compute_peer_percentiles(df, sample_config)  # "de" column missing entirely
    assert not result.empty


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
