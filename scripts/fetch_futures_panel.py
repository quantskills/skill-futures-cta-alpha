#!/usr/bin/env python3
"""Assemble the futures factor-input panel from Pandadata.

This is the ONE place that depends on Pandadata. It joins daily OHLC/OI, term
structure, basis, inventory/receipt, positioning, and spot profit into a single
tidy panel (date×variety) that compute_factors.py consumes. Because it needs the
`pandadata-api` skill's runtime + credentials, it is a documented interface here;
downstream compute/validate are pure pandas and fully testable offline.

Contract: load the sibling `pandadata-api` skill, confirm each method's exact
signature/fields via its search script, then call — do NOT guess parameters.
Method routing is specified in references/data-map.md.

Usage (once pandadata-api is available):
    python fetch_futures_panel.py --varieties RB M CU --start 20220101 \
        --end 20241231 --out panel.parquet
"""
from __future__ import annotations

import argparse

# Panel columns produced (see references/data-map.md for the method per column):
PANEL_COLUMNS = [
    "date", "variety", "symbol",
    "close", "open", "high", "low", "volume", "oi",   # get_future_daily
    "pn", "pf", "Dn", "Df",                            # get_future_term_structure
    "basis",                                           # get_future_basis
    "inventory",                                       # get_future_inventory
    "warehouse_receipt",                               # get_future_warehouse_receipt
    "spot_profit",                                     # get_future_spot_profit
    "broker_net",                                      # get_broker_netmarg[_change]
    "ls_ratio",                                        # get_future_ls_ratio
    "virtual_ratio",                                   # get_future_virtual_ratio
]


def fetch(varieties, start, end):
    """Return a tidy panel DataFrame. Requires the pandadata-api skill.

    Implementation outline (fill against pandadata-api's confirmed contracts):
        1. get_future_dominant(variety, start, end)  -> dominant symbol per date
        2. get_future_daily(symbol/variety, start, end) -> OHLC/OI  (smoke-test first)
        3. get_future_term_structure(variety, date) -> pn/pf/Dn/Df  (same trade_date)
        4. get_future_basis / _inventory / _warehouse_receipt / _spot_profit
        5. get_broker_netmarg_change / get_future_ls_ratio / _virtual_ratio
        6. outer-join all on (date, variety); keep raw units; label data cutoff
    Return columns from PANEL_COLUMNS (missing optional columns are allowed —
    compute_factors.py skips factors whose inputs are absent).
    """
    raise SystemExit(
        "fetch_futures_panel requires the pandadata-api skill runtime.\n"
        "Load pandadata-api, implement the outlined joins (references/data-map.md),\n"
        "or supply your own panel.parquet directly to compute_factors.py."
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--varieties", nargs="+", required=True)
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    df = fetch(args.varieties, args.start, args.end)
    df.to_parquet(args.out, index=False) if args.out.endswith(".parquet") \
        else df.to_csv(args.out, index=False)


if __name__ == "__main__":
    main()
