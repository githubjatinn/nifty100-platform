"""Computes percentile ranks for each company within its peer group across metrics and stores them in SQLite."""

import sqlite3
import math
import pandas as pd
import yaml

DB_PATH = "data/nifty100.db"
CONFIG_PATH = "config/screener_config.yaml"
NO_PEER_GROUP_MSG = "No peer group assigned"


def load_config(config_path=CONFIG_PATH):
    """Reads screener_config.yaml and returns the parsed dict."""
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def load_peer_group_data(db_path=DB_PATH):
    """Pulls the most-populated year's metrics plus peer_group assignment for all companies."""
    conn = sqlite3.connect(db_path)
    try:
        query = """
            SELECT c.id AS company_id, c.company_name, s.broad_sector,
                   pg.peer_group_name, pg.is_benchmark, fr.*
            FROM companies c
            JOIN financial_ratios fr ON c.id = fr.company_id
            LEFT JOIN sectors s ON c.id = s.company_id
            LEFT JOIN peer_groups pg ON c.id = pg.company_id
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


def _percentile_rank_series(series, invert=False):
    """Returns each value's percentile rank (0-100) within the series; infinity always ranks at 100."""
    finite = series.replace([float("inf"), float("-inf")], pd.NA).dropna()
    ranking_basis = -finite if invert else finite
    ranks = ranking_basis.rank(pct=True) * 100
    result = pd.Series(index=series.index, dtype="float64")
    result.loc[finite.index] = ranks
    inf_mask = series.apply(lambda v: isinstance(v, float) and math.isinf(v) and v > 0)
    result.loc[inf_mask] = 100.0
    return result.round(2)


def compute_peer_percentiles(df, config):
    """For each peer group and metric, computes percentile_rank; small or missing groups get NO_PEER_GROUP_MSG."""
    metrics = config["peer_percentiles"]["metrics"]
    min_group_size = config["peer_percentiles"]["min_peer_group_size"]
    invert_metrics = {"debt_to_equity"}

    records = []
    for group_name, group_df in df.groupby("peer_group_name", dropna=False):
        eligible = pd.notna(group_name) and len(group_df) >= min_group_size
        for metric in metrics:
            if metric not in group_df.columns:
                continue
            values = pd.to_numeric(group_df[metric], errors="coerce")
            if eligible:
                percentiles = _percentile_rank_series(values, invert=(metric in invert_metrics))
            else:
                percentiles = pd.Series(None, index=group_df.index)
            for company_id, value, pct in zip(group_df["company_id"], values, percentiles):
                records.append({
                    "company_id": company_id,
                    "peer_group_name": group_name if eligible else NO_PEER_GROUP_MSG,
                    "metric": metric,
                    "value": None if pd.isna(value) else float(value),
                    "percentile_rank": None if (not eligible or pd.isna(pct)) else float(pct),
                })
    return pd.DataFrame.from_records(records)


def save_peer_percentiles(percentiles_df, db_path=DB_PATH):
    """Writes the peer_percentiles table to SQLite, replacing any existing table; closes connection explicitly."""
    conn = sqlite3.connect(db_path)
    try:
        percentiles_df.to_sql("peer_percentiles", conn, if_exists="replace", index=False)
        conn.commit()
    finally:
        conn.close()


def run_peer_analysis(db_path=DB_PATH, config_path=CONFIG_PATH):
    """End-to-end: load data, compute percentiles, persist to SQLite, return the resulting DataFrame."""
    config = load_config(config_path)
    df = load_peer_group_data(db_path)
    percentiles = compute_peer_percentiles(df, config)
    save_peer_percentiles(percentiles, db_path)
    return percentiles


if __name__ == "__main__":
    result = run_peer_analysis()
    unassigned = (result["peer_group_name"] == NO_PEER_GROUP_MSG).sum()
    print(f"{len(result)} percentile rows written. {unassigned} rows with no peer group assigned.")