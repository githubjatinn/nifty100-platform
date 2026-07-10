"""End-to-end Sprint 3 pipeline: filter -> composite score -> peer percentiles -> radar charts -> Excel export."""

from src.screener.engine import load_config, load_screener_data, apply_filters
from src.screener.composite import compute_scores
from src.screener.presets import run_all_presets
from src.analytics.peer import load_peer_group_data, compute_peer_percentiles, save_peer_percentiles
from src.reports.radar_charts import generate_all_radar_charts
from src.reports.peer_comparison_export import build_peer_comparison_workbook
from src.reports.screener_export import build_screener_output_workbook


def main():
    """Runs the full Sprint 3 pipeline and prints a summary at each stage."""
    config = load_config()

    # Day 15: filter engine
    raw_df = load_screener_data()
    filtered_df = apply_filters(raw_df, config)
    print(f"Day 15 - Filter engine: {len(filtered_df)} of {len(raw_df)} companies passed.")

    # Day 17: composite + sector-relative scoring (run on the FULL universe, not just filtered)
    scored_df = compute_scores(raw_df, config)
    print(f"Day 17 - Composite scores computed for {len(scored_df)} companies.")

    # Day 17: screener_output.xlsx (one sheet per preset, threshold-coloured, sorted by composite score)
    preset_results = run_all_presets()
    preset_results = {
        name: df.merge(scored_df[["company_id", "composite_quality_score"]], on="company_id", how="left")
        for name, df in preset_results.items()
    }
    screener_output_path = build_screener_output_workbook(preset_results, config)
    print(f"Day 17 - Screener output workbook saved to {screener_output_path}")

    # Day 18: peer percentiles (uses its own loader since it needs peer_groups + is_benchmark)
    peer_df = load_peer_group_data()
    peer_df = peer_df.merge(
        scored_df[["company_id", "composite_quality_score"]], on="company_id", how="left"
    )
    percentiles = compute_peer_percentiles(peer_df, config)
    save_peer_percentiles(percentiles)
    unassigned = (percentiles["peer_group_name"] == "No peer group assigned").sum()
    print(f"Day 18 - Peer percentiles: {len(percentiles)} rows written, {unassigned} unassigned.")

    # Day 19: radar charts
    generate_all_radar_charts(peer_df)
    print("Day 19 - Radar charts generated in reports/radar_charts/")

    # Day 20: Excel export
    output_path = build_peer_comparison_workbook(peer_df, percentiles)
    print(f"Day 20 - Peer comparison workbook saved to {output_path}")


if __name__ == "__main__":
    main()