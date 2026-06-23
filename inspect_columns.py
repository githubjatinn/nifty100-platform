"""One-off inspection script: prints column headers and row counts for all 12 real source files."""

import os
import pandas as pd

RAW_DIR = os.path.join("data", "raw")
SUPP_DIR = os.path.join("data", "supporting")

CORE_FILES = ["companies.xlsx", "profitandloss.xlsx", "balancesheet.xlsx",
              "cashflow.xlsx", "analysis.xlsx", "documents.xlsx", "prosandcons.xlsx"]
SUPP_FILES = ["sectors.xlsx", "stock_prices.xlsx", "market_cap.xlsx",
              "financial_ratios.xlsx", "peer_groups.xlsx"]

print("=== CORE FILES (header=1) ===")
for fname in CORE_FILES:
    path = os.path.join(RAW_DIR, fname)
    df = pd.read_excel(path, header=1)
    print(f"\n{fname}: {len(df)} rows")
    print(list(df.columns))

print("\n=== SUPPLEMENTARY FILES (header=0) ===")
for fname in SUPP_FILES:
    path = os.path.join(SUPP_DIR, fname)
    df = pd.read_excel(path, header=0)
    print(f"\n{fname}: {len(df)} rows")
    print(list(df.columns))