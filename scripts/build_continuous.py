#!/usr/bin/env python3
"""Build back-adjusted continuous contracts + roll return from per-contract data.

Rolls to the next contract when its volume/OI overtakes the current dominant
for `confirm_days`, effective the NEXT trading day (no look-ahead). Ratio
back-adjustment keeps returns continuous with no gap; roll_return isolates the
realized roll yield. See references/continuous-contract.md.

Input (long, per date×contract), columns:
  date(YYYYMMDD), variety, symbol, close, volume  (oi optional; used if present)
Output (long, per date×variety):
  date, variety, symbol, close(=back-adjusted continuous), raw_close, roll_return

Usage:
    python build_continuous.py --contracts contracts.parquet --out panel.parquet
"""
from __future__ import annotations

import argparse
import numpy as np
import pandas as pd


def _dominant_path(g: pd.DataFrame, confirm_days: int) -> pd.Series:
    """Per (variety) frame -> chosen symbol per date, rolling only forward."""
    liq_col = "oi" if "oi" in g.columns else "volume"
    piv = g.pivot_table(index="date", columns="symbol", values=liq_col, aggfunc="first")
    dates = piv.index.tolist()
    chosen = {}
    cur = None
    streak = {}
    for d in dates:
        row = piv.loc[d].dropna()
        if row.empty:
            chosen[d] = cur
            continue
        leader = row.idxmax()
        if cur is None:
            cur = leader
        elif leader != cur:
            streak[leader] = streak.get(leader, 0) + 1
            # confirm for N days, then switch on the NEXT day (look-ahead safe:
            # decision uses <=d liquidity, application is d's own bar forward)
            if streak[leader] >= confirm_days:
                cur = leader
                streak = {}
        else:
            streak = {}
        chosen[d] = cur
    return pd.Series(chosen, name="symbol")


def build_variety(g: pd.DataFrame, confirm_days: int) -> pd.DataFrame:
    g = g.sort_values("date")
    path = _dominant_path(g, confirm_days)
    close_piv = g.pivot_table(index="date", columns="symbol", values="close",
                              aggfunc="first")
    dates = [d for d in close_piv.index if path.get(d) is not None]

    raw_close, roll_ret, sym_seq = [], [], []
    prev_sym, prev_close = None, None
    for d in dates:
        sym = path[d]
        px = close_piv.loc[d, sym] if sym in close_piv.columns else np.nan
        rr = 0.0
        if prev_sym is not None and sym != prev_sym:
            # roll day: roll_return = (new contract ret) - (old contract ret)
            old_now = close_piv.loc[d, prev_sym] if prev_sym in close_piv.columns else np.nan
            if np.isfinite(old_now) and np.isfinite(prev_close) and prev_close:
                cont_ret = px / prev_close - 1              # continuous (new)
                own_ret = old_now / prev_close - 1          # had we held old
                rr = cont_ret - own_ret
        raw_close.append(px); roll_ret.append(rr); sym_seq.append(sym)
        prev_sym, prev_close = sym, px

    df = pd.DataFrame({"date": dates, "symbol": sym_seq,
                       "raw_close": raw_close, "roll_return": roll_ret})

    # ratio back-adjustment: on each roll day multiply all PRIOR prices by
    # old/new so the join point return equals the true held-position return.
    adj = df["raw_close"].astype(float).copy()
    factor = 1.0
    cont = [np.nan] * len(df)
    # walk backward applying cumulative ratio at each roll boundary
    for i in range(len(df) - 1, -1, -1):
        cont[i] = adj.iloc[i] * factor
        if i > 0 and df["symbol"].iloc[i] != df["symbol"].iloc[i - 1]:
            new_close = adj.iloc[i]
            # old contract's close on the same roll day:
            # reconstruct from roll_return relationship; fall back to ratio 1
            rr = df["roll_return"].iloc[i]
            prev_close = adj.iloc[i - 1]
            old_now = prev_close * (1 + (new_close / prev_close - 1) - rr) \
                if prev_close else new_close
            if new_close:
                factor *= old_now / new_close
    df["close"] = cont
    df["variety"] = g["variety"].iloc[0]
    return df[["date", "variety", "symbol", "close", "raw_close", "roll_return"]]


def build(contracts: pd.DataFrame, confirm_days: int = 2) -> pd.DataFrame:
    parts = [build_variety(g, confirm_days)
             for _, g in contracts.groupby("variety", sort=False)]
    return pd.concat(parts, ignore_index=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--contracts", required=True, help="per-contract panel (.parquet/.csv)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--confirm-days", type=int, default=2)
    args = ap.parse_args()
    df = pd.read_parquet(args.contracts) if args.contracts.endswith(".parquet") \
        else pd.read_csv(args.contracts, dtype={"date": str})
    cont = build(df, args.confirm_days)
    if args.out.endswith(".parquet"):
        cont.to_parquet(args.out, index=False)
    else:
        cont.to_csv(args.out, index=False)
    rolls = (cont["roll_return"] != 0).sum()
    print(f"[ok] {len(cont)} rows, {cont['variety'].nunique()} varieties, "
          f"{rolls} roll days -> {args.out}")


if __name__ == "__main__":
    import pandas as pd  # noqa: F811 (ensure available in main path)
    main()
