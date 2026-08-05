"""Regression suite for ic_check's overlap-corrected significance.

Run from the repository root:
    python -B -m unittest discover -s tests -v

The bug this pins: daily ICs computed against an h-day forward return share
h-1 days of the same return window, so the iid formula t = IR*sqrt(N) treats
~N/h independent observations as N and overstates significance by roughly
sqrt(h). On pure random-walk input that produced |t| up to 4.6 at h=20 where
the same factors gave |t| <= 0.6 at h=1.
"""
from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import ic_check  # noqa: E402


def random_walk_panel(n_varieties=30, n_days=2000, seed=11):
    """Pure GBM: no cross-sectional predictability exists by construction."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2015-01-02", periods=n_days).strftime("%Y%m%d").tolist()
    rows = []
    for k in range(n_varieties):
        price = 1000 * np.exp(np.cumsum(rng.normal(0, 0.012, n_days)))
        for i, d in enumerate(dates):
            c = price[i]
            rows.append(dict(date=d, variety="V%02d" % k, close=c,
                             high=c * 1.004, low=c * 0.996, volume=1e5, oi=1e5))
    return pd.DataFrame(rows)


class NeweyWestKernel(unittest.TestCase):
    def test_lag_zero_reduces_exactly_to_the_iid_formula(self):
        rng = np.random.default_rng(3)
        ics = pd.Series(rng.normal(0.02, 0.4, 500))
        iid = ics.mean() / ics.std(ddof=1) * np.sqrt(len(ics))
        nw = ic_check._newey_west_t(ics, lag=0)
        # ddof differs by one observation out of 500; agreement to 1% is exact
        # enough to prove the kernel degenerates to the iid case.
        self.assertAlmostEqual(nw, iid, delta=abs(iid) * 0.01)

    def test_positively_autocorrelated_series_get_a_smaller_t(self):
        rng = np.random.default_rng(5)
        noise = rng.normal(0, 1, 3000)
        # AR(1) with rho=0.9 -- strong positive autocorrelation, like overlap
        ar = np.zeros(3000)
        for i in range(1, 3000):
            ar[i] = 0.9 * ar[i - 1] + noise[i]
        ics = pd.Series(ar + 0.15)
        naive = ics.mean() / ics.std(ddof=1) * np.sqrt(len(ics))
        corrected = ic_check._newey_west_t(ics, lag=19)
        self.assertLess(abs(corrected), abs(naive),
                        "HAC must shrink t on autocorrelated input")

    def test_degenerate_inputs_return_nan_not_a_number(self):
        self.assertTrue(np.isnan(ic_check._newey_west_t(pd.Series([0.1]), lag=0)))
        self.assertTrue(np.isnan(ic_check._newey_west_t(pd.Series([]), lag=5)))
        # zero variance -> no usable standard error
        self.assertTrue(np.isnan(
            ic_check._newey_west_t(pd.Series([0.2] * 50), lag=3)))

    def test_lag_is_clamped_to_the_sample_length(self):
        ics = pd.Series([0.1, -0.2, 0.3, -0.1, 0.2])
        self.assertTrue(np.isfinite(ic_check._newey_west_t(ics, lag=999)))


class NullHypothesisControl(unittest.TestCase):
    """On random-walk input every |t| must be small. This is the actual bug test."""

    @classmethod
    def setUpClass(cls):
        import compute_factors
        cls.panel = random_walk_panel()
        cls.factors = compute_factors.compute(cls.panel)

    def test_non_overlapping_horizon_is_already_clean(self):
        res = ic_check.run(self.factors, self.panel, [1])
        self.assertTrue((res["t_stat"].abs() < 3).all(),
                        "h=1 needs no correction and must show no false positives:\n%s"
                        % res[["factor", "t_stat"]].to_string())

    def test_overlapping_horizon_false_positives_are_removed(self):
        res = ic_check.run(self.factors, self.panel, [20])
        worst_naive = res["t_naive"].abs().max()
        worst_corrected = res["t_stat"].abs().max()
        # The uncorrected statistic manufactures significance on random data...
        self.assertGreater(worst_naive, 3.0,
                           "fixture no longer reproduces the inflation it pins")
        # ...and the corrected one must not.
        self.assertLess(worst_corrected, 3.0,
                        "HAC correction failed to remove the false positive:\n%s"
                        % res[["factor", "t_stat", "t_naive"]].to_string())
        self.assertLess(worst_corrected, worst_naive)

    def test_report_exposes_both_statistics_and_the_lag(self):
        res = ic_check.run(self.factors, self.panel, [20])
        for col in ("t_stat", "t_naive", "nw_lag"):
            self.assertIn(col, res.columns)
        self.assertTrue((res["nw_lag"] == 19).all())


if __name__ == "__main__":
    unittest.main()
