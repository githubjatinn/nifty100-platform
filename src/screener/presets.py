"""Applies the 6 preset filter combinations (Quality Compounder, Value Pick, etc.) on top of the base screener."""

from src.screener.engine import load_config, load_screener_data, apply_filters, _passes_simple_min, _passes_simple_max

def _merge_preset_into_filters(base_config, preset_name):
    """Builds a preset-only filter config: starts with ALL filters off, then applies just this preset's thresholds."""
    config = {k: dict(v) if isinstance(v, dict) else v for k, v in base_config.items()}
    preset = config["presets"].get(preset_name)
    if preset is None:
        raise ValueError(f"Unknown preset: {preset_name}")
    empty_filters = {key: None for key in config["filters"]}
    for key, value in preset.items():
        if key in empty_filters:
            empty_filters[key] = value
    config["filters"] = empty_filters
    return config


def quality_compounder(df, config):
    """ROE > 15%, D/E < 1.0, FCF > 0, Revenue CAGR 5yr > 10%."""
    merged = _merge_preset_into_filters(config, "quality_compounder")
    return apply_filters(df, merged)


def value_pick(df, config):
    """P/E < 20, P/B < 3.0, Dividend Yield > 2%."""
    merged = _merge_preset_into_filters(config, "value_pick")
    return apply_filters(df, merged)


def growth_accelerator(df, config):
    """Revenue CAGR 5yr > 20%, PAT CAGR 5yr > 15%, D/E < 2.0."""
    merged = _merge_preset_into_filters(config, "growth_accelerator")
    return apply_filters(df, merged)


def dividend_champion(df, config):
    """Dividend Yield > 3%, Dividend Payout between 40-80%, FCF > 0."""
    merged = _merge_preset_into_filters(config, "dividend_champion")
    base_pass = apply_filters(df, merged)
    payout_min = config["presets"]["dividend_champion"]["dividend_payout_min"]
    payout_max = config["presets"]["dividend_champion"]["dividend_payout_max"]
    return base_pass[
        base_pass.apply(
            lambda row: _passes_simple_min(row, "dividend_payout_ratio_pct", payout_min)
            and _passes_simple_max(row, "dividend_payout_ratio_pct", payout_max),
            axis=1,
        )
    ]


def debt_free_blue_chip(df, config):
    """D/E = 0, ROE > 12%, Revenue > 5000 Crore (uses market_cap_crore as proxy)."""
    merged = _merge_preset_into_filters(config, "debt_free_blue_chip")
    revenue_min = config["presets"]["debt_free_blue_chip"]["revenue_min_cr"]
    base_pass = apply_filters(df, merged)
    return base_pass[base_pass.apply(lambda row: _passes_simple_min(row, "market_cap_crore", revenue_min), axis=1)]


def turnaround_watch(df, config):
    """Revenue CAGR 5yr > 10%, FCF positive in latest year."""
    merged = _merge_preset_into_filters(config, "turnaround_watch")
    return apply_filters(df, merged)


PRESET_FUNCS = {
    "Quality Compounder": quality_compounder,
    "Value Pick": value_pick,
    "Growth Accelerator": growth_accelerator,
    "Dividend Champion": dividend_champion,
    "Debt-Free Blue Chip": debt_free_blue_chip,
    "Turnaround Watch": turnaround_watch,
}


def run_all_presets(db_path=None, config_path=None):
    """Runs the base screener plus all 6 presets and returns a dict of {preset_name: DataFrame}."""
    config = load_config(config_path) if config_path else load_config()
    df = load_screener_data(db_path) if db_path else load_screener_data()
    return {name: func(df, config) for name, func in PRESET_FUNCS.items()}


if __name__ == "__main__":
    results = run_all_presets()
    for name, out in results.items():
        print(f"{name}: {len(out)} companies")