"""Verdict test: the circular block bootstrap over consecutive scored days (review finding 2)."""
import unittest
from unittest import mock

import numpy as np
import pandas as pd

from cloud import summarize
from cloud.summarize import BOOTSTRAP, block_indices, bootstrap_diff, stats


def daily(diffs, start="2026-09-01", n=4):
    """`n` scored rows per day; WeatherNext's error is Yr's (1.0) plus that day's difference."""
    rows = []
    for day, dd in zip(pd.date_range(start, periods=len(diffs)).strftime("%Y-%m-%d"), diffs):
        for i in range(n):
            rows.append({"day": day, "e_yr": 1.0, "e_wn": 1.0 + dd})
    return pd.DataFrame(rows)


def regimes(n_days=60, run=6, seed=3):
    """Daily differences that stay in one regime for `run` days at a time (strongly autocorrelated)."""
    rng = np.random.default_rng(seed)
    levels = rng.normal(0.0, 0.3, size=-(-n_days // run))
    return np.repeat(levels, run)[:n_days] + rng.normal(0.0, 0.02, size=n_days)


class BlockIndices(unittest.TestCase):
    def test_shape_and_range(self):
        idx = block_indices(30, np.random.default_rng(1), block=4)
        self.assertEqual(idx.shape, (BOOTSTRAP, 30))
        self.assertTrue(((idx >= 0) & (idx < 30)).all())

    def test_blocks_are_consecutive_days_wrapping_at_the_end(self):
        idx = block_indices(10, np.random.default_rng(2), block=4)
        # Positions 0-3, 4-7 and 8-9 are blocks: each step inside a block is the next day (mod 10).
        for a, b in ((0, 4), (4, 8), (8, 10)):
            steps = (idx[:, a + 1:b] - idx[:, a:b - 1]) % 10
            self.assertTrue((steps == 1).all())
        # Some block wraps from the last day to the first.
        self.assertTrue(((idx[:, 1:4] == 0) & (idx[:, 0:3] == 9)).any())

    def test_every_day_equally_likely(self):
        """Wrapping keeps the first and last days as likely as the middle ones."""
        idx = block_indices(20, np.random.default_rng(3), block=4)
        share = np.bincount(idx.ravel(), minlength=20) / idx.size
        self.assertTrue(np.allclose(share, 1 / 20, atol=0.006))

    def test_block_one_is_the_old_day_bootstrap(self):
        old = np.random.default_rng(1).integers(0, 15, size=(BOOTSTRAP, 15))
        self.assertTrue((block_indices(15, np.random.default_rng(1), block=1) == old).all())

    def test_default_is_the_fixed_block_length(self):
        self.assertEqual(summarize.BLOCK_DAYS, 4)
        a = block_indices(25, np.random.default_rng(5))
        b = block_indices(25, np.random.default_rng(5), block=4)
        self.assertTrue((a == b).all())


class BootstrapDiff(unittest.TestCase):
    def test_too_few_days(self):
        self.assertEqual(bootstrap_diff(daily([0.1] * 6)), (None, None))

    def test_reproducible(self):
        d = daily(regimes())
        self.assertEqual(bootstrap_diff(d), bootstrap_diff(d))

    def test_row_order_does_not_matter(self):
        """Days are put in date order before blocks are drawn."""
        d = daily(regimes())
        shuffled = d.sample(frac=1, random_state=7)
        self.assertEqual(bootstrap_diff(d), bootstrap_diff(shuffled))

    def test_wider_interval_when_neighbouring_days_are_alike(self):
        """Weather regimes make neighbouring days alike; blocks see that, single days don't."""
        d = daily(regimes())
        lo1, hi1 = bootstrap_diff(d, block=1)
        lo4, hi4 = bootstrap_diff(d, block=4)
        self.assertGreater(hi4 - lo4, 1.2 * (hi1 - lo1))

    def test_independent_days_give_a_similar_interval(self):
        d = daily(np.random.default_rng(11).normal(0.0, 0.3, size=90))
        w1 = np.subtract(*bootstrap_diff(d, block=1)[::-1])
        w4 = np.subtract(*bootstrap_diff(d, block=4)[::-1])
        self.assertLess(abs(w4 / w1 - 1), 0.2)

    def test_clear_winner_is_still_called(self):
        lo, hi = bootstrap_diff(daily(0.5 + regimes() * 0.1))
        self.assertGreater(lo, 0)
        self.assertEqual(summarize.verdict(lo, hi), "yr")

    def test_regime_driven_lead_becomes_too_close(self):
        """A lead that rests on a few week-long regimes is no longer called a win."""
        levels = np.array([0.55, -0.2, 0.5, -0.15, 0.45, -0.25])  # Yr ahead in three weeks of six
        diffs = np.repeat(levels, 7) + np.random.default_rng(8).normal(0.0, 0.02, size=42)
        d = daily(diffs)
        old, new = bootstrap_diff(d, block=1), bootstrap_diff(d, block=4)
        self.assertEqual(summarize.verdict(*old), "yr")
        self.assertEqual(summarize.verdict(*new), "too_close")


class StatsUnchanged(unittest.TestCase):
    def test_only_the_interval_changes(self):
        """Scores, the difference and the blend gain do not depend on the block length."""
        d = daily(regimes()).assign(e_avg=lambda x: (x.e_yr + x.e_wn) / 2)
        with mock.patch.object(summarize, "BLOCK_DAYS", 1):
            old = stats(d, with_base=False)
        new = stats(d, with_base=False)
        for key in ("n", "days", "mae_yr", "mae_wn", "diff", "avg_gain", "avg_gain_lo",
                    "avg_gain_hi", "verdict_avg"):
            self.assertEqual(old.get(key), new.get(key), key)
        self.assertNotEqual((old["ci_lo"], old["ci_hi"]), (new["ci_lo"], new["ci_hi"]))


if __name__ == "__main__":
    unittest.main()
