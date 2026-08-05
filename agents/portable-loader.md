# Portable Loader Prompt

Use this prompt in agents that do not natively discover `SKILL.md` folders.

```text
You have access to a local skill named futures-cta-alpha at:
<FUTURES_CTA_SKILL_ROOT>

When the user asks for commodity-futures factors, CTA signals, momentum / carry / term-structure /
inventory / positioning factors, a factor panel for backtesting, or futures factor IC:

1. Read <FUTURES_CTA_SKILL_ROOT>/SKILL.md for the workflow and the boundary with
   skill-futures-deepview-analyst (that one writes research reports; this one emits a
   structured date x variety x factor panel for the factor toolchain).
2. Read <FUTURES_CTA_SKILL_ROOT>/references/factor-catalog.md for each factor's formula,
   data interface, and MEASURED direction (priors were recalibrated against real data).
3. Compute and check:
   python <FUTURES_CTA_SKILL_ROOT>/scripts/compute_factors.py --panel panel.csv --out factors.csv
   python <FUTURES_CTA_SKILL_ROOT>/scripts/validate_factors.py factors.csv
   python <FUTURES_CTA_SKILL_ROOT>/scripts/ic_check.py --factors factors.csv --panel panel.csv --horizons 5 10 20
   Pandadata is required only for fetch_futures_panel.py. Price + carry factors work off any
   daily source: feed your own panel (date, variety, close[, high, low, oi, pn, pf, Dn, Df, ...])
   straight to compute_factors.py. Missing columns simply skip their factors.
4. Two hard rules from the measured evidence (references/l3-evidence-ic.md):
   - China commodities are a REVERSAL market. 1-3 month momentum has IC -7% (t=-11): use it
     inverted. Carry is INVERTED vs global (contango outperforms, not backwardation).
   - Significant IC != tradeable. lowvol has the strongest IC (t=5.7) but ~0 net Sharpe.
     Confirm direction with ic_check.py; confirm tradeability with a cost-aware backtest.
5. Do not invent factors, Pandadata methods, or field names. This skill computes factor values
   only — no research reports, no strategy code, no investment advice.
```
