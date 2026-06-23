"""35 unit tests for normalize_year() and normalize_ticker()."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src", "etl"))

import pytest
from normaliser import normalize_year, normalize_ticker


class TestNormalizeYear:

    def test_year_mar23(self):
        assert normalize_year("Mar-23") == "2023-03"

    def test_year_fy24(self):
        assert normalize_year("FY24") == "2024-03"

    def test_year_dec22(self):
        assert normalize_year("Dec-22") == "2022-12"

    def test_year_garbage(self):
        with pytest.raises(ValueError):
            normalize_year("xyz")

    def test_mar_space_2digit(self):
        assert normalize_year("Mar 23") == "2023-03"

    def test_full_month_name_hyphen(self):
        assert normalize_year("March-2023") == "2023-03"

    def test_mar_dash_4digit_year(self):
        assert normalize_year("Mar-2023") == "2023-03"

    def test_jun_year_end_bank(self):
        assert normalize_year("Jun-23") == "2023-06"

    def test_plain_4digit_string_assumes_march(self):
        assert normalize_year("2023") == "2023-03"

    def test_plain_int_assumes_march(self):
        assert normalize_year(2023) == "2023-03"

    def test_plain_float_assumes_march(self):
        assert normalize_year(2023.0) == "2023-03"

    def test_fy_prefix_removal_4digit(self):
        assert normalize_year("FY2023") == "2023-03"

    def test_fy_with_space_2digit(self):
        assert normalize_year("FY 23") == "2023-03"

    def test_fy_with_space_4digit(self):
        assert normalize_year("FY 2023") == "2023-03"

    def test_already_normalised_passthrough(self):
        assert normalize_year("2023-03") == "2023-03"

    def test_non_padded_month_gets_padded(self):
        assert normalize_year("2023-3") == "2023-03"

    def test_whitespace_padding_is_stripped(self):
        assert normalize_year("  Mar-23  ") == "2023-03"

    def test_2digit_pivot_to_1900s(self):
        assert normalize_year("Mar-95") == "1995-03"

    def test_2digit_pivot_to_2000s(self):
        assert normalize_year("Mar-05") == "2005-03"

    def test_none_raises(self):
        with pytest.raises(ValueError):
            normalize_year(None)

    def test_empty_string_raises(self):
        with pytest.raises(ValueError):
            normalize_year("")

    def test_fiscal_range_label_raises(self):
        with pytest.raises(ValueError):
            normalize_year("2022-23")


class TestNormalizeTicker:

    def test_ticker_strip(self):
        assert normalize_ticker("TCS") == "TCS"

    def test_ticker_lower(self):
        assert normalize_ticker("tcs") == "TCS"

    def test_ticker_strips_edge_whitespace(self):
        assert normalize_ticker("  TCS  ") == "TCS"

    def test_ticker_preserves_hyphen(self):
        assert normalize_ticker("BAJAJ-AUTO") == "BAJAJ-AUTO"

    def test_ticker_preserves_ampersand(self):
        assert normalize_ticker("M&M") == "M&M"

    def test_ticker_lowercase_with_hyphen(self):
        assert normalize_ticker("bajaj-auto") == "BAJAJ-AUTO"

    def test_ticker_strips_ns_suffix(self):
        assert normalize_ticker("RELIANCE.NS") == "RELIANCE"

    def test_ticker_strips_bo_suffix(self):
        assert normalize_ticker("RELIANCE.BO") == "RELIANCE"

    def test_ticker_strips_nse_suffix_lowercase(self):
        assert normalize_ticker("tcs.ns") == "TCS"

    def test_ticker_strips_nse_colon_prefix(self):
        assert normalize_ticker("NSE:INFY") == "INFY"

    def test_ticker_strips_bse_colon_prefix(self):
        assert normalize_ticker("BSE:TCS") == "TCS"

    def test_ticker_idempotent_on_canonical_value(self):
        assert normalize_ticker("INFY") == "INFY"

    def test_ticker_combined_lowercase_suffix_whitespace(self):
        assert normalize_ticker("  tcs.ns ") == "TCS"

    def test_ticker_raises_on_none(self):
        with pytest.raises(ValueError):
            normalize_ticker(None)

    def test_ticker_raises_on_empty_string(self):
        with pytest.raises(ValueError):
            normalize_ticker("")