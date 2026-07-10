"""Generates an 8-axis radar chart per peer group (company vs peer average) and exports PNGs to reports/radar_charts/."""

import os
import math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

AXES = ["ROE", "ROCE", "NPM", "D/E", "FCF", "PAT CAGR 5yr", "Revenue CAGR 5yr", "Composite Score"]
AXIS_COLUMNS = {
    "ROE": "return_on_equity_pct",
    "ROCE": "return_on_capital_pct",
    "NPM": "net_profit_margin_pct",
    "D/E": "debt_to_equity",
    "FCF": "free_cash_flow_cr",
    "PAT CAGR 5yr": "pat_cagr_5yr",
    "Revenue CAGR 5yr": "revenue_cagr_5yr",
    "Composite Score": "composite_quality_score",
}
OUTPUT_DIR = "reports/radar_charts"


def _normalize_axis_values(df, column, invert=False):
    """Min-max normalizes a column to 0-100 across the group so all 8 axes share the same visual scale."""
    values = df[column].astype(float)
    min_v, max_v = values.min(), values.max()
    if max_v == min_v:
        return {idx: 50.0 for idx in df.index}
    normalized = (values - min_v) / (max_v - min_v) * 100
    if invert:
        normalized = 100 - normalized
    return normalized.to_dict()


def _company_radar_values(df, company_id):
    """Builds the 8 normalized axis values for a single company relative to its peer group."""
    result = []
    for axis in AXES:
        col = AXIS_COLUMNS[axis]
        if col not in df.columns:
            result.append(50.0)
            continue
        invert = axis == "D/E"
        norm_map = _normalize_axis_values(df, col, invert=invert)
        row = df[df["company_id"] == company_id]
        result.append(norm_map.get(row.index[0], 50.0) if not row.empty else 50.0)
    return result


def _peer_average_values(df):
    """Builds the 8 normalized axis values for the peer group average, used as the dashed overlay line."""
    result = []
    for axis in AXES:
        col = AXIS_COLUMNS[axis]
        if col not in df.columns:
            result.append(50.0)
            continue
        invert = axis == "D/E"
        norm_map = _normalize_axis_values(df, col, invert=invert)
        result.append(float(np.mean(list(norm_map.values()))))
    return result


def _plot_radar(company_name, company_values, peer_avg_values, output_path):
    """Draws a filled polygon for the company plus a dashed peer-average overlay, saves as PNG."""
    n = len(AXES)
    angles = [i / n * 2 * math.pi for i in range(n)]
    angles += angles[:1]
    company_values = company_values + company_values[:1]
    peer_avg_values = peer_avg_values + peer_avg_values[:1]

    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
    ax.plot(angles, company_values, linewidth=2, label=company_name)
    ax.fill(angles, company_values, alpha=0.25)
    ax.plot(angles, peer_avg_values, linewidth=1.5, linestyle="--", label="Peer Group Average")

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(AXES, fontsize=9)
    ax.set_ylim(0, 100)
    ax.set_title(company_name, fontsize=13, pad=20)
    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1))

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def generate_radar_for_peer_group(peer_group_df, peer_group_name, output_dir=OUTPUT_DIR):
    """Generates one radar PNG per company in the peer group."""
    for _, row in peer_group_df.iterrows():
        company_values = _company_radar_values(peer_group_df, row["company_id"])
        peer_avg_values = _peer_average_values(peer_group_df)
        safe_name = "_".join(str(row["company_name"]).split())
        output_path = os.path.join(output_dir, f"{safe_name}_radar.png")
        _plot_radar(row["company_name"], company_values, peer_avg_values, output_path)


def generate_standalone_chart(company_row, nifty100_avg_row, output_dir=OUTPUT_DIR):
    """For companies with no peer group: generates a single-metric bar-style chart vs Nifty 100 average."""
    fig, ax = plt.subplots(figsize=(5, 4))
    metrics = [AXIS_COLUMNS[a] for a in AXES if AXIS_COLUMNS[a] in company_row.index]
    company_vals = [company_row[m] for m in metrics]
    nifty_vals = [nifty100_avg_row.get(m, 0) for m in metrics]

    x = np.arange(len(metrics))
    ax.bar(x - 0.2, company_vals, width=0.4, label=company_row["company_name"])
    ax.bar(x + 0.2, nifty_vals, width=0.4, label="Nifty 100 Average")
    ax.set_xticks(x)
    ax.set_xticklabels(metrics, rotation=45, ha="right", fontsize=8)
    ax.legend()
    ax.set_title(f"{company_row['company_name']} vs Nifty 100 Average")

    safe_name = "_".join(str(row["company_name"]).split())
    os.makedirs(output_dir, exist_ok=True)
    fig.savefig(os.path.join(output_dir, f"{safe_name}_radar.png"), dpi=150, bbox_inches="tight")
    plt.close(fig)


def generate_all_radar_charts(df, output_dir=OUTPUT_DIR):
    """Iterates all peer groups (and unassigned companies) generating the full set of radar/standalone charts."""
    available_cols = [c for c in AXIS_COLUMNS.values() if c in df.columns]
    nifty100_avg = df[available_cols].mean()

    for group_name, group_df in df.groupby("peer_group_name", dropna=False):
        if group_name is None or len(group_df) < 3:
            for _, row in group_df.iterrows():
                generate_standalone_chart(row, nifty100_avg, output_dir)
        else:
            generate_radar_for_peer_group(group_df, group_name, output_dir)