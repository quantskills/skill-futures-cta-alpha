#!/usr/bin/env python3
"""Compute the CTA factor panel from a tidy futures panel.

Pure pandas — operates on a panel and is fully testable without Pandadata.
Every factor uses only data up to t (no look-ahead); forward returns are
aligned to t+1 downstream by factor-evaluate/backtest, not here.

Input panel (long, one row per date×variety), columns:
  required: date(YYYYMMDD str), variety, close
  optional: high, low, volume, oi, pn, pf, Dn, Df, basis, inventory,
            warehouse_receipt, spot_profit, broker_net, ls_ratio,
            virtual_ratio, roll_return
Factors whose inputs are absent are skipped (logged), not errored.

Output (long): date, variety, factor_name, value  ->  see output-schema.

Usage:
    python compute_factors.py --panel panel.parquet --out factors/all.parquet
"""
from __future__ import annotations

import argparse
import numpy as np
import pandas as pd

ANN = np.sqrt(252.0)

# expected IC sign (prior only — must be confirmed by ic-analysis downstream)
FACTOR_DIRECTION = {
    "tsmom_252": +1, "tsmom_252_21": +1, "tsmom_63": +1, "breakout_55": +1,
    "ema_xover_20_100": +1, "xsmom_252_21": +1, "xsmom_63": +1,
    "carry_ann": +1, "roll_return_63": +1, "basis_mom_20": +1,
    "vol_scaled_carry": +1, "ts_slope": -1, "ts_curvature": 0,
    "oi_price_confirm_20": +1, "broker_net_chg_5": +1, "ls_ratio_z": -1,
    "virtual_ratio_chg": 0, "inventory_mom_20": -1, "receipt_mom_20": -1,
    "spot_profit_z": -1, "lowvol": +1, "st_reversal_5": +1,
}


def _hv(logret: pd.Series, win: int = 20) -> pd.Series:
    return logret.rolling(win).std() * ANN


def _zscore(s: pd.Series, win: int = 60) -> pd.Series:
    m = s.rolling(win).mean()
    sd = s.rolling(win).std()
    return (s - m) / sd.replace(0, np.nan)


def _per_variety(g: pd.DataFrame) -> pd.DataFrame:
    """Time-series factors for one variety (g sorted by date)."""
    c = g["close"].astype(float)
    lr = np.log(c / c.shift(1))
    out = pd.DataFrame(index=g.index)

    # A. time-series momentum
    out["tsmom_252"] = c / c.shift(252) - 1
    out["tsmom_252_21"] = c.shift(21) / c.shift(252) - 1
    out["tsmom_63"] = c / c.shift(63) - 1
    if {"high", "low"} <= set(g.columns):
        hh = g["high"].rolling(55).max()
        ll = g["low"].rolling(55).min()
        mid = (hh + ll) / 2.0
        rng = 0.5 * (hh - ll)
        out["breakout_55"] = ((c - mid) / rng.replace(0, np.nan)).clip(-1, 1)
    hv20 = _hv(lr, 20)
    ema20 = c.ewm(span=20, adjust=False).mean()
    ema100 = c.ewm(span=100, adjust=False).mean()
    out["ema_xover_20_100"] = (ema20 - ema100) / (hv20 * c).replace(0, np.nan)

    # G. volatility / reversal
    out["lowvol"] = -hv20
    out["st_reversal_5"] = -(c / c.shift(5) - 1)

    # E. positioning (need oi / broker / ratios)
    if "oi" in g.columns:
        oi = g["oi"].astype(float)
        out["oi_price_confirm_20"] = np.sign(c - c.shift(20)) * np.log(
            (oi / oi.shift(20)).replace(0, np.nan))
        if "broker_net" in g.columns:
            out["broker_net_chg_5"] = (g["broker_net"] - g["broker_net"].shift(5)) \
                / oi.replace(0, np.nan)
    if "ls_ratio" in g.columns:
        out["ls_ratio_z"] = _zscore(g["ls_ratio"].astype(float))
    if "virtual_ratio" in g.columns:
        out["virtual_ratio_chg"] = g["virtual_ratio"].astype(float) \
            - g["virtual_ratio"].astype(float).shift(20)

    # C/D. carry & term structure (raw near/far contract prices)
    if {"pn", "pf", "Dn", "Df"} <= set(g.columns):
        pn, pf = g["pn"].astype(float), g["pf"].astype(float)
        dd = (g["Df"].astype(float) - g["Dn"].astype(float)).replace(0, np.nan)
        out["carry_ann"] = (pn / pf - 1) * (365.0 / dd)
        out["ts_slope"] = np.log((pf / pn).replace(0, np.nan)) / dd
        out["vol_scaled_carry"] = out["carry_ann"] / hv20.replace(0, np.nan)
    if {"p1", "p2", "p3"} <= set(g.columns):   # three-point term-structure convexity
        out["ts_curvature"] = g["p3"].astype(float) - 2 * g["p2"].astype(float) \
            + g["p1"].astype(float)
    if "basis" in g.columns:
        out["basis_mom_20"] = g["basis"].astype(float) - g["basis"].astype(float).shift(20)

    # F. inventory / receipt / spot profit
    if "inventory" in g.columns:
        iv = g["inventory"].astype(float)
        out["inventory_mom_20"] = np.log((iv / iv.shift(20)).replace(0, np.nan))
    if "warehouse_receipt" in g.columns:
        wr = g["warehouse_receipt"].astype(float)
        out["receipt_mom_20"] = np.log((wr / wr.shift(20)).replace(0, np.nan))
    if "spot_profit" in g.columns:
        out["spot_profit_z"] = _zscore(g["spot_profit"].astype(float))

    # realized roll return (needs continuous builder's roll_return column)
    if "roll_return" in g.columns:
        out["roll_return_63"] = g["roll_return"].astype(float).rolling(63).sum()

    out["date"] = g["date"].values
    out["variety"] = g["variety"].values
    return out


def _cross_sectional(long: pd.DataFrame) -> pd.DataFrame:
    """B. cross-sectional momentum = per-date z-score of the TS base returns."""
    base = long.pivot_table(index="date", columns="variety", values="value_ts",
                            aggfunc="first")
    return base


def compute(panel: pd.DataFrame) -> pd.DataFrame:
    panel = panel.sort_values(["variety", "date"]).reset_index(drop=True)
    parts = []
    for _, g in panel.groupby("variety", sort=False):
        parts.append(_per_variety(g))
    wide = pd.concat(parts, ignore_index=True)

    id_cols = ["date", "variety"]
    fac_cols = [c for c in wide.columns if c not in id_cols]
    long = wide.melt(id_vars=id_cols, value_vars=fac_cols,
                     var_name="factor_name", value_name="value")

    # B. cross-sectional momentum from the 12-1 and 3M base returns
    for name, src in [("xsmom_252_21", "tsmom_252_21"), ("xsmom_63", "tsmom_63")]:
        base = long[long.factor_name == src][["date", "variety", "value"]].copy()
        base["value"] = base.groupby("date")["value"].transform(
            lambda s: (s - s.mean()) / s.std() if s.std() else s * np.nan)
        base["factor_name"] = name
        long = pd.concat([long, base[["date", "variety", "factor_name", "value"]]],
                         ignore_index=True)

    long = long.dropna(subset=["value"])
    long = long[~long["value"].isin([np.inf, -np.inf])]
    return long.sort_values(["date", "variety", "factor_name"]).reset_index(drop=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--panel", required=True, help="tidy input panel (.parquet/.csv)")
    ap.add_argument("--out", required=True, help="output factor panel (.parquet/.csv)")
    args = ap.parse_args()
    panel = pd.read_parquet(args.panel) if args.panel.endswith(".parquet") \
        else pd.read_csv(args.panel, dtype={"date": str})
    long = compute(panel)
    if args.out.endswith(".parquet"):
        long.to_parquet(args.out, index=False)
    else:
        long.to_csv(args.out, index=False)
    n_fac = long["factor_name"].nunique()
    print(f"[ok] {len(long)} rows, {n_fac} factors, "
          f"{long['variety'].nunique()} varieties -> {args.out}")


if __name__ == "__main__":
    main()
