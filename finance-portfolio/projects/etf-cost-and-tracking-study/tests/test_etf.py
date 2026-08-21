"""Unit tests for the fund analytics.

The fee arithmetic is exact, so it is tested against closed-form values rather
than against the current output.  The tracking statistics are tested against
constructed series whose answers are known by design - a fund that is exactly
the index minus a constant fee must show exactly that tracking difference and
zero tracking error, and if it does not, the estimator is wrong.
"""

import math
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))

import etf                                                            # noqa: E402
import finlib as fl                                                   # noqa: E402

PRICES = os.path.join(HERE, "..", "data", "prices_daily.csv")


def synthetic_pair(fee: float, n: int = 2_520, noise: float = 0.0, seed: int = 3):
    """An index path and a fund that is that index minus `fee` a year."""
    import random
    rng = random.Random(seed)
    index, fund = [100.0], [100.0]
    for _ in range(n):
        r = rng.gauss(0.0004, 0.01)
        index.append(index[-1] * (1.0 + r))
        drift = -fee / fl.TRADING_DAYS
        wobble = rng.gauss(0.0, noise) if noise else 0.0
        fund.append(fund[-1] * (1.0 + r + drift + wobble))
    return index, fund


class TestTracking(unittest.TestCase):
    def test_perfect_tracker_gives_up_slightly_more_than_its_fee(self):
        """A fund that is exactly the index minus f each day loses
        f x (1 + index CAGR) of compound annual return, not f - because the fee
        is taken from a balance that is itself compounding.  Asserting a flat
        -f here would be asserting a subtly wrong model of how fees work."""
        index, fund = synthetic_pair(fee=0.0030)
        s = etf.analyse_tracking("TEST", fund, index, 0.0030)
        expected = -0.0030 * (1.0 + s.index_cagr)
        # An approximation to second order, so a tolerance rather than places.
        self.assertAlmostEqual(s.tracking_difference_annual, expected, delta=2e-5)
        self.assertAlmostEqual(s.tracking_error_annual, 0.0, places=6)

    def test_zero_fee_tracker_has_zero_tracking_difference(self):
        index, fund = synthetic_pair(fee=0.0)
        s = etf.analyse_tracking("TEST", fund, index, 0.0)
        self.assertAlmostEqual(s.tracking_difference_annual, 0.0, places=6)

    def test_noise_creates_tracking_error_without_tracking_difference(self):
        """The distinction the whole project rests on, stated as a test."""
        index, fund = synthetic_pair(fee=0.0, noise=0.001)
        s = etf.analyse_tracking("TEST", fund, index, 0.0)
        # Large tracking error by construction...
        self.assertGreater(s.tracking_error_annual, 0.010)
        # ...but no systematic shortfall: the average difference is small
        # relative to its own volatility, which is the whole distinction.
        self.assertLess(abs(s.tracking_difference_annual), s.tracking_error_annual)

    def test_beta_and_r_squared_of_a_pure_tracker(self):
        index, fund = synthetic_pair(fee=0.0005)
        s = etf.analyse_tracking("TEST", fund, index, 0.0005)
        self.assertAlmostEqual(s.beta_to_index, 1.0, places=4)
        self.assertGreater(s.r_squared, 0.9999)

    def test_rolling_window_bounds_contain_the_average(self):
        _dates, prices = fl.read_price_csv(PRICES)
        s = etf.analyse_tracking("LCAP", prices["LCAP"], prices["IDXUS"], 0.0003)
        self.assertLessEqual(s.worst_rolling_year, s.tracking_difference_annual)
        self.assertGreaterEqual(s.best_rolling_year, s.tracking_difference_annual)

    def test_rolling_series_aligns_with_the_price_series(self):
        _dates, prices = fl.read_price_csv(PRICES)
        roll = etf.rolling_tracking_difference(prices["LCAP"], prices["IDXUS"])
        self.assertEqual(len(roll), len(prices["LCAP"]))
        self.assertIsNone(roll[0])
        self.assertIsNotNone(roll[-1])


class TestFeeArithmetic(unittest.TestCase):
    def test_fee_drag_matches_closed_form(self):
        d = etf.fee_drag(100_000.0, 0.07, 0.0035, 30)
        self.assertAlmostEqual(d["gross_value"], 100_000.0 * 1.07 ** 30, places=6)
        self.assertAlmostEqual(d["net_value"], 100_000.0 * (1.07 - 0.0035) ** 30, places=6)
        self.assertAlmostEqual(d["cost"], d["gross_value"] - d["net_value"], places=9)

    def test_zero_fee_costs_nothing(self):
        d = etf.fee_drag(100_000.0, 0.07, 0.0, 30)
        self.assertAlmostEqual(d["cost"], 0.0, places=8)

    def test_fee_cost_grows_faster_than_linearly_in_time(self):
        """Doubling the horizon more than doubles the cost, because the fee
        compounds against you."""
        ten = etf.fee_drag(100_000.0, 0.07, 0.0035, 10)["cost"]
        twenty = etf.fee_drag(100_000.0, 0.07, 0.0035, 20)["cost"]
        self.assertGreater(twenty, 2.0 * ten)

    def test_cost_path_length_and_monotonicity(self):
        path = etf.total_cost_of_ownership(100_000.0, 0.07, 0.0035, 30)
        self.assertEqual(len(path), 31)
        self.assertAlmostEqual(path[0], 100_000.0)
        for a, b in zip(path, path[1:]):
            self.assertGreater(b, a)

    def test_breakeven_equals_the_fee_gap(self):
        self.assertAlmostEqual(etf.breakeven_outperformance(0.0032), 0.0032)


class TestOverlap(unittest.TestCase):
    def test_identical_portfolios_overlap_completely(self):
        w = {"a": 0.5, "b": 0.3, "c": 0.2}
        self.assertAlmostEqual(etf.holding_overlap(w, w), 1.0)

    def test_disjoint_portfolios_do_not_overlap(self):
        self.assertAlmostEqual(
            etf.holding_overlap({"a": 1.0}, {"b": 1.0}), 0.0)

    def test_partial_overlap_is_the_sum_of_minimums(self):
        a = {"x": 0.6, "y": 0.4}
        b = {"x": 0.3, "y": 0.7}
        self.assertAlmostEqual(etf.holding_overlap(a, b), 0.3 + 0.4)

    def test_overlap_is_symmetric(self):
        a = {"x": 0.6, "y": 0.3, "z": 0.1}
        b = {"x": 0.2, "y": 0.5, "w": 0.3}
        self.assertAlmostEqual(etf.holding_overlap(a, b), etf.holding_overlap(b, a))


class TestRealPanel(unittest.TestCase):
    def test_index_fund_tracks_more_closely_than_the_factor_fund(self):
        _dates, prices = fl.read_price_csv(PRICES)
        core = etf.analyse_tracking("LCAP", prices["LCAP"], prices["IDXUS"], 0.0003)
        factor = etf.analyse_tracking("SMRT", prices["SMRT"], prices["IDXUS"], 0.0035)
        self.assertLess(core.tracking_error_annual, factor.tracking_error_annual)
        self.assertGreater(core.r_squared, factor.r_squared)

    def test_unexplained_is_small_for_a_true_index_fund(self):
        _dates, prices = fl.read_price_csv(PRICES)
        core = etf.analyse_tracking("LCAP", prices["LCAP"], prices["IDXUS"], 0.0003)
        self.assertLess(abs(core.unexplained_annual), 0.002)


if __name__ == "__main__":
    unittest.main()
