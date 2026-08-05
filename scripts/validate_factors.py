#!/usr/bin/env python3
"""Validate a CTA factor panel before it is published to the toolchain.

Checks: schema, no inf/duplicate keys, unknown factor names, per-factor nan
rate, and zero-variance (constant) factors. Exits non-zero on hard failures.

Usage:
    python validate_factors.py factors/all.parquet
"""
from __future__ import annotations

import argparse
import sys

REQUIRED = ["date", "variety", "factor_name", "value"]
KNOWN = {
    "tsmom_252", "tsmom_252_21", "tsmom_63", "breakout_55", "ema_xover_20_100",
    "xsmom_252_21", "xsmom_63", "carry_ann", "roll_return_63", "basis_mom_20",
    "vol_scaled_carry", "ts_slope", "ts_curvature", "oi_price_confirm_20",
    "broker_net_chg_5", "ls_ratio_z", "virtual_ratio_chg", "inventory_mom_20",
    "receipt_mom_20", "spot_profit_z", "lowvol", "st_reversal_5",
}
MAX_NAN_RATE = 0.98  # a factor with >98% missing is effectively empty


def validate(path: str) -> list[str]:
    import numpy as np
    import pandas as pd
    df = pd.read_parquet(path) if path.endswith(".parquet") \
        else pd.read_csv(path, dtype={"date": str})
    errors: list[str] = []

    miss = [c for c in REQUIRED if c not in df.columns]
    if miss:
        return [f"missing required columns: {miss}"]

    if df["value"].isin([np.inf, -np.inf]).any():
        errors.append("value contains inf/-inf")

    dup = df.duplicated(subset=["date", "variety", "factor_name"]).sum()
    if dup:
        errors.append(f"{dup} duplicate (date,variety,factor_name) keys")

    unknown = set(df["factor_name"]) - KNOWN
    if unknown:
        errors.append(f"unknown factor_name(s): {sorted(unknown)}")

    bad_date = df[~df["date"].astype(str).str.match(r"^\d{8}$")]
    if len(bad_date):
        errors.append(f"{len(bad_date)} rows with non-YYYYMMDD date")

    # per-factor coverage on the full date×variety grid
    n_cells = df["date"].nunique() * df["variety"].nunique()
    for fac, g in df.groupby("factor_name"):
        present = g["value"].notna().sum()
        nan_rate = 1 - present / n_cells if n_cells else 1.0
        if nan_rate > MAX_NAN_RATE:
            errors.append(f"[{fac}] {nan_rate*100:.1f}% missing (effectively empty)")
        if present and g["value"].std(skipna=True) == 0:
            errors.append(f"[{fac}] zero variance (constant factor)")

    return errors


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("path", help="factor panel (.parquet/.csv)")
    args = ap.parse_args()
    errs = validate(args.path)
    if errs:
        print(f"FAIL: {len(errs)} issue(s)")
        for e in errs[:100]:
            print("  -", e)
        sys.exit(1)
    print("OK: factor panel passed all checks")


if __name__ == "__main__":
    main()
