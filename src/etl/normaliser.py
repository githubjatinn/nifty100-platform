"""Year and ticker normalisation helpers for the NIFTY100 ETL pipeline."""

from __future__ import annotations

import re
from typing import Any

_MONTH_NUM = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}
_ALREADY_NORMALISED_RE = re.compile(r"^(\d{4})-(\d{1,2})$")
_FY_RE = re.compile(r"^fy[\s\-]?(\d{2,4})$", re.IGNORECASE)
_MONTH_YEAR_RE = re.compile(r"^([A-Za-z]+)\.?[\s\-]+(\d{2,4})$")
_PLAIN_4DIGIT_RE = re.compile(r"^(\d{4})$")
_FISCAL_RANGE_RE = re.compile(r"^(\d{4})-(\d{2})$")
_TICKER_SUFFIX_RE = re.compile(r"\.(NS|BO|NSE|BSE)$", re.IGNORECASE)


def _expand_2digit_year(yy: int) -> int:
    """Pivot 2-digit years: 00-49 -> 2000s, 50-99 -> 1900s."""
    return 2000 + yy if yy <= 49 else 1900 + yy


def normalize_year(value: Any) -> str:
    """Normalise a fiscal-year label (e.g. 'Mar-23', 'FY24', 'Dec-22', '2023-24') to 'YYYY-MM'."""
    if value is None or isinstance(value, bool):
        raise ValueError(f"normalize_year: invalid value {value!r}")

    if isinstance(value, (int, float)):
        year = int(value)
        if 1900 <= year <= 2100:
            return f"{year}-03"
        raise ValueError(f"normalize_year: year {year} out of range")

    if not isinstance(value, str):
        raise ValueError(f"normalize_year: unsupported type {type(value)!r}")

    text = value.strip()
    if not text:
        raise ValueError("normalize_year: empty string")

    m = _ALREADY_NORMALISED_RE.match(text)
    if m:
        year_str, month_str = m.group(1), m.group(2)
        month = int(month_str)
        if 1 <= month <= 12:
            return f"{year_str}-{month:02d}"

    m = _FISCAL_RANGE_RE.match(text)
    if m:
        base_year = int(m.group(1))
        end_yy = int(m.group(2))
        end_year = _expand_2digit_year(end_yy)
        if end_year == base_year + 1:
            return f"{end_year}-03"

    m = _FY_RE.match(text)
    if m:
        year_str = m.group(1)
        year = int(year_str) if len(year_str) == 4 else _expand_2digit_year(int(year_str))
        return f"{year}-03"

    m = _MONTH_YEAR_RE.match(text)
    if m:
        month_token, year_str = m.group(1).lower(), m.group(2)
        month_num = _MONTH_NUM.get(month_token[:3])
        if month_num is not None:
            year = int(year_str) if len(year_str) == 4 else _expand_2digit_year(int(year_str))
            return f"{year}-{month_num:02d}"

    m = _PLAIN_4DIGIT_RE.match(text)
    if m:
        return f"{m.group(1)}-03"

    raise ValueError(f"normalize_year: unrecognised format {value!r}")


def normalize_ticker(value: Any) -> str:
    """Normalise an NSE ticker to canonical uppercase, stripping exchange prefixes/suffixes."""
    if value is None or not isinstance(value, str):
        raise ValueError(f"normalize_ticker: invalid value {value!r}")

    text = value.strip()
    if not text:
        raise ValueError("normalize_ticker: empty/whitespace-only string")

    text = re.sub(r"\s+", "", text)
    if ":" in text:
        text = text.split(":")[-1]
    text = _TICKER_SUFFIX_RE.sub("", text)

    if not text:
        raise ValueError(f"normalize_ticker: nothing left after cleaning {value!r}")

    return text.upper()