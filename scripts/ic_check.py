#!/usr/bin/env python3
"""Lightweight IC self-check for the factor panel — L2->L3 evidence.

Cross-sectional rank IC: for each date, Spearman(factor(t,·), fwd_ret(t→t+h,·))
across varieties; then mean IC, IC-IR (mean/std), and a Newey-West(lag=h-1)
t-stat that corrects for the overlap between consecutive ICs, plus share>0.
Compares realized IC sign to each factor's prior in factor-catalog.md.

For h>1 the uncorrected t = IR*sqrt(N) is inflated by roughly sqrt(h); it is
still reported as `t_naive` so the gap stays visible, but significance must be
judged on `t_stat`. See tests/test_ic_check.py for the random-walk control.

This is a quick self-check; full factor attribution is `skill-ic-analysis`.
Forward returns use the price panel's continuous `close`.

Usage:
    python ic_check.py --factors factors.csv --panel panel.csv --horizons 5 10 20
"""
from __future__ import annotations

import argparse
import numpy as np
import pandas as pd

PRIOR = {
    "tsmom_252": +1, "tsmom_252_21": +1, "tsmom_63": +1, "breakout_55": +1,
    "ema_xover_20_100": +1, "xsmom_252_21": +1, "xsmom_63": +1,
    "carry_ann": +1, "roll_return_63": +1, "basis_mom_20": +1,
    "vol_scaled_carry": +1, "ts_slope": -1, "oi_price_confirm_20": +1,
    "broker_net_chg_5": +1, "ls_ratio_z": -1, "inventory_mom_20": -1,
    "receipt_mom_20": -1, "spot_profit_z": -1, "lowvol": +1, "st_reversal_5": +1,
}


def _fwd_ret(panel: pd.DataFrame, h: int) -> pd.DataFrame:
    """Long fwd return per date×variety over the next h trading days."""
    p = panel.sort_values(["variety", "date"]).copy()
    p["fwd"] = p.groupby("variety")["close"].transform(lambda s: s.shift(-h) / s - 1)
    return p[["date", "variety", "fwd"]]


def _rank_ic(sub: pd.DataFrame) -> float:
    """Spearman = Pearson on cross-sectional ranks (no scipy dependency)."""
    x = sub["value"].rank()
    y = sub["fwd"].rank()
    if len(sub) < 5 or x.std() == 0 or y.std() == 0:
        return np.nan
    return float(np.corrcoef(x, y)[0, 1])


def _newey_west_t(ics: pd.Series, lag: int) -> float:
    """t-stat for mean(ics) with a Bartlett-kernel HAC standard error.

    Daily ICs computed against an h-day forward return are NOT independent:
    consecutive ICs share h-1 days of the same return window. The naive
    t = IR*sqrt(N) treats them as iid and overstates significance by roughly
    sqrt(h) -- on pure random-walk input, h=20 produced |t| up to 4.6 where the
    same factors gave |t| <= 0.6 at h=1.

    lag = h-1 is the overlap length, so h=1 gives lag=0 and reduces exactly to
    the iid formula. The Bartlett weights keep the variance estimate
    positive semi-definite.
    """
    values = ics.to_numpy(dtype=float)
    values = values[np.isfinite(values)]
    n = len(values)
    if n < 2:
        return np.nan
    mean = values.mean()
    resid = values - mean
    # np.sum rather than `@`: matmul emits spurious FP warnings on some
    # numpy builds, and the explicit form reads as the autocovariance it is.
    gamma0 = float(np.sum(resid * resid)) / n
    variance = gamma0
    for k in range(1, min(lag, n - 1) + 1):
        gamma_k = float(np.sum(resid[k:] * resid[:-k])) / n
        variance += 2.0 * (1.0 - k / (lag + 1.0)) * gamma_k
    if not np.isfinite(variance) or variance <= 0:
        return np.nan
    # A constant series does not subtract to exactly zero in floating point, so
    # `variance > 0` alone would let float noise become the denominator and
    # report an absurd t (~1e17) for a series carrying no information at all.
    # Require the dispersion to be meaningful relative to the series level.
    if np.sqrt(variance) <= 1e-12 * max(abs(mean), 1.0):
        return np.nan
    return float(mean / np.sqrt(variance / n))


def run(factors: pd.DataFrame, panel: pd.DataFrame, horizons) -> pd.DataFrame:
    out = []
    for h in horizons:
        fwd = _fwd_ret(panel, h)
        merged = factors.merge(fwd, on=["date", "variety"], how="inner").dropna(
            subset=["value", "fwd"])
        for fac, g in merged.groupby("factor_name"):
            ics = g.groupby("date")[["value", "fwd"]].apply(_rank_ic).dropna()
            if len(ics) < 20:
                continue
            mean_ic = ics.mean()
            ir = mean_ic / ics.std() if ics.std() else np.nan
            # t_stat is HAC-corrected for the h-day overlap; t_naive is the old
            # iid figure, kept only so the inflation stays visible in --out.
            t = _newey_west_t(ics, lag=h - 1)
            t_naive = ir * np.sqrt(len(ics)) if ir == ir else np.nan
            prior = PRIOR.get(fac, 0)
            agree = "✓" if prior and np.sign(mean_ic) == np.sign(prior) else \
                    ("✗" if prior else "·")
            out.append(dict(factor=fac, h=h, n_days=len(ics),
                            mean_ic=mean_ic, ic_ir=ir, t_stat=t,
                            t_naive=t_naive, nw_lag=h - 1,
                            pos_rate=(ics > 0).mean(), prior=prior, agree=agree))
    return pd.DataFrame(out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--factors", required=True)
    ap.add_argument("--panel", required=True, help="price panel with close")
    ap.add_argument("--horizons", nargs="+", type=int, default=[5, 10, 20])
    ap.add_argument("--out")
    args = ap.parse_args()
    fac = pd.read_csv(args.factors, dtype={"date": str}) if args.factors.endswith(".csv") \
        else pd.read_parquet(args.factors)
    pan = pd.read_csv(args.panel, dtype={"date": str}) if args.panel.endswith(".csv") \
        else pd.read_parquet(args.panel)
    res = run(fac, pan, args.horizons)
    if args.out:
        res.to_csv(args.out, index=False)
    for h in args.horizons:
        sub = res[res.h == h].sort_values("mean_ic")
        if not len(sub):
            continue
        overlap = " · t is Newey-West(lag=%d) corrected for overlap" % (h - 1) \
            if h > 1 else " · non-overlapping, t needs no correction"
        print(f"\n=== IC @ T+{h} (rank IC, {sub['n_days'].max()} days){overlap} ===")
        print(f"{'factor':<20}{'meanIC':>8}{'IC_IR':>7}{'t_NW':>7}{'t_iid':>7}"
              f"{'pos%':>7}  prior agree")
        for _, r in sub.iterrows():
            print(f"{r.factor:<20}{r.mean_ic*100:>7.2f}%{r.ic_ir:>7.2f}{r.t_stat:>7.1f}"
                  f"{r.t_naive:>7.1f}{r.pos_rate*100:>6.0f}%  {r.prior:>+d}     {r.agree}")
        if h > 1:
            print("  t_iid is the uncorrected figure and is inflated ~sqrt(h); "
                  "judge significance on t_NW.")


if __name__ == "__main__":
    main()
