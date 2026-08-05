# Futures CTA Alpha

[简体中文](README.md) | **English**

> Commodity-futures CTA factor library — a `date × variety × factor` panel for the
> QuantSkills factor toolchain.

Fills the ecosystem's largest structural gap: **ten equity factor libraries, zero for
futures.** Counterpart to `skill-factor-alpha191-alpha101` on the futures side.

## What it produces

A long factor panel (`date, variety, factor_name, value`) consumed directly by
`skill-factor-evaluate` / `skill-ic-analysis` / `skill-backtest`.

It emits **factor values only** — no human-readable research notes, no strategy code,
no investment advice. For qualitative futures research use
`skill-futures-deepview-analyst`; for strategy code use the `ssquant-*` skills.

## Quick start

```bash
pip install -r requirements.txt

# optional: splice per-contract data into a back-adjusted continuous series
python scripts/build_continuous.py --contracts contracts.csv --out panel.csv

# core: compute the factor panel (pure pandas, fully offline)
python scripts/compute_factors.py --panel panel.csv --out factors.csv
python scripts/validate_factors.py factors.csv

# optional self-check of predictive power
python scripts/ic_check.py --factors factors.csv --panel panel.csv --horizons 5 20
```

## Two data paths

| Path | Coverage | Needs |
| --- | --- | --- |
| **A. Pandadata** (`fetch_futures_panel.py`) | all ~22 factors incl. inventory / positioning / carry / basis | `skill-pandadata-api` + account |
| **B. Bring your own panel** (skip fetch) | whichever factors your columns support | nothing — any daily source works |

Price-based factors (momentum, volatility, reversal) plus carry need only daily bars.
Missing columns skip the dependent factors and are logged — they never raise.

## Factor families

Seven families, ~22 factors (formulas and priors in `references/factor-catalog.md`):
time-series momentum, cross-sectional momentum, carry/roll, term structure,
positioning/sentiment, inventory/warehouse/spot, volatility & reversal.

## Reading the evidence — two hard rules

`references/l3-evidence-ic.md` records IC measured on real data (2018–2026, 30 varieties).
Two findings matter more than any individual factor:

1. **Chinese commodities are a reversal market.** The global "momentum + long
   backwardation" prior fails broadly here; the tradeable signals are reversal and
   inverted carry (long contango).
2. **A significant IC is not a tradeable return.** `lowvol` had the library's strongest
   headline IC and a net Sharpe of ≈0.

> ⚠️ **The published t-statistics are uncorrected.** They were computed as
> `t = IR × √N`, which treats overlapping daily ICs as independent and inflates
> significance by roughly √h at horizon h. `ic_check.py` now reports a
> Newey-West(lag=h−1) `t_stat` alongside the old `t_naive`; a random-walk control
> confirms the old figure manufactured |t| up to 4.6 where the corrected one gives 1.5.
> **The tables in `references/l3-evidence-ic.md` have not yet been recomputed on the
> original panel** — see the correction notice at the top of that file, which flags
> which conclusions flip.

## No look-ahead

Every factor at date `t` uses only data up to `t`; `validate_factors.py` enforces this
along with coverage, NaN rate, constant columns and duplicate keys. Forward returns are
aligned downstream by `factor-evaluate`/`backtest`, never here.

## Validation

`python -B -m unittest discover -s tests -v` — includes a pure random-walk null control
that fails if the IC significance machinery starts manufacturing false positives again.

`runnable` is a community self-validation level, not official verification. Factor
direction priors are hypotheses and must be tested on your own data before use.

## License and disclaimer

GPL-3.0-only. Copyright (C) 2026 the QuantSkills contributors.

For quantitative research reference only. Factor directions require empirical
validation. **Nothing here is investment advice.**
