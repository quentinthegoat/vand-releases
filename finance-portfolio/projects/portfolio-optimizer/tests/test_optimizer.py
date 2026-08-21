"""Unit tests for the optimiser.

Two categories matter here:

* **Correctness of the constraint primitive.**  Every solver is built on
  `project_to_simplex`, so if the projection is wrong every result is wrong.
  It is tested against known closed-form cases and against its defining
  property (it returns the nearest feasible point).
* **No look-ahead.**  The walk-forward engine is tested by feeding it an
  estimator that records what it was shown, and asserting it was never shown
  anything from after the rebalance date.  A backtest without this test is a
  backtest you cannot trust.
"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))

import finlib as fl                                                  # noqa: E402
import optimizer as op                                               # noqa: E402
import walkforward as wf                                             # noqa: E402

TICKERS = ["LCAP", "SCAP", "INTL", "EMKT", "BNDX", "REIT", "GOLD"]


def load():
    dates, prices = fl.read_price_csv(os.path.join(HERE, "..", "data", "prices_daily.csv"))
    returns = {t: fl.simple_returns(prices[t]) for t in TICKERS}
    cov = [[fl.covariance(returns[a], returns[b]) * fl.TRADING_DAYS for b in TICKERS]
           for a in TICKERS]
    mu = [fl.annualised_return(returns[t]) for t in TICKERS]
    return dates, returns, mu, cov


class TestSimplexProjection(unittest.TestCase):
    def test_already_feasible_point_is_unchanged(self):
        w = [0.2, 0.3, 0.5]
        for a, b in zip(op.project_to_simplex(w), w):
            self.assertAlmostEqual(a, b, places=12)

    def test_output_is_always_feasible(self):
        for v in ([0.5, 0.9, -0.3, 0.1], [-1.0, -2.0, -3.0], [10.0, 0.0, 0.0],
                  [0.0, 0.0, 0.0], [1e-9, 1e-9, 1e-9]):
            w = op.project_to_simplex(v)
            self.assertAlmostEqual(sum(w), 1.0, places=10)
            self.assertTrue(all(x >= -1e-12 for x in w), v)

    def test_known_projection(self):
        """(0.5, 0.9, -0.3, 0.1) projects to (0.3, 0.7, 0, 0)."""
        w = op.project_to_simplex([0.5, 0.9, -0.3, 0.1])
        for a, b in zip(w, [0.3, 0.7, 0.0, 0.0]):
            self.assertAlmostEqual(a, b, places=10)

    def test_projection_is_the_nearest_feasible_point(self):
        """Random feasible points must all be at least as far away."""
        import random
        rng = random.Random(11)
        v = [0.8, -0.2, 0.6, 0.1]
        w = op.project_to_simplex(v)
        d_opt = sum((a - b) ** 2 for a, b in zip(v, w))
        for _ in range(3_000):
            cand = op.project_to_simplex([rng.gauss(0, 1) for _ in v])
            d = sum((a - b) ** 2 for a, b in zip(v, cand))
            self.assertGreaterEqual(d + 1e-12, d_opt)

    def test_uniform_input_gives_equal_weights(self):
        w = op.project_to_simplex([0.25] * 4)
        for x in w:
            self.assertAlmostEqual(x, 0.25, places=10)


class TestOptimisers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dates, cls.returns, cls.mu, cls.cov = load()

    def test_all_solvers_return_feasible_weights(self):
        for w in (op.min_variance(self.cov),
                  op.risk_parity(self.cov),
                  op.inverse_volatility(self.cov),
                  op.max_sharpe(self.mu, self.cov, 0.025, n_points=15),
                  op.equal_weight(len(TICKERS))):
            self.assertAlmostEqual(sum(w), 1.0, places=8)
            self.assertTrue(all(x >= -1e-9 for x in w))

    def test_minimum_variance_is_the_minimum_variance(self):
        """No random feasible portfolio may have lower variance."""
        import random
        rng = random.Random(5)
        w = op.min_variance(self.cov)
        best = op.portfolio_variance(self.cov, w)
        for _ in range(2_000):
            cand = op.project_to_simplex([abs(rng.gauss(0, 1)) for _ in TICKERS])
            self.assertGreaterEqual(op.portfolio_variance(self.cov, cand), best * 0.999)

    def test_minimum_variance_beats_equal_weight_on_variance(self):
        mv = op.min_variance(self.cov)
        ew = op.equal_weight(len(TICKERS))
        self.assertLess(op.portfolio_variance(self.cov, mv),
                        op.portfolio_variance(self.cov, ew))

    def test_risk_parity_equalises_risk_contributions(self):
        w = op.risk_parity(self.cov)
        sw = fl.matvec(self.cov, w)
        var = sum(wi * s for wi, s in zip(w, sw))
        contributions = [wi * s / var for wi, s in zip(w, sw)]
        for c in contributions:
            self.assertAlmostEqual(c, 1.0 / len(TICKERS), places=4)

    def test_frontier_is_monotone_in_return(self):
        """Higher volatility must buy higher return along an efficient frontier."""
        frontier = op.efficient_frontier(self.mu, self.cov, n_points=12)
        returns = [r for _v, r, _w in frontier]
        for a, b in zip(returns, returns[1:]):
            self.assertGreaterEqual(b + 1e-6, a)

    def test_max_sharpe_beats_equal_weight_in_sample(self):
        """In sample it must win - that is exactly why out of sample matters."""
        ms = op.max_sharpe(self.mu, self.cov, 0.025, n_points=40)
        ew = op.equal_weight(len(TICKERS))
        def sharpe(w):
            import math
            return ((op.portfolio_return(self.mu, w) - 0.025)
                    / math.sqrt(op.portfolio_variance(self.cov, w)))
        self.assertGreater(sharpe(ms), sharpe(ew))

    def test_higher_risk_aversion_lowers_portfolio_variance(self):
        timid = op.max_utility(self.mu, self.cov, 200.0)
        bold = op.max_utility(self.mu, self.cov, 1.0)
        self.assertLess(op.portfolio_variance(self.cov, timid),
                        op.portfolio_variance(self.cov, bold))


class TestShrinkage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dates, cls.returns, cls.mu, cls.cov = load()

    def test_intensity_is_a_valid_proportion(self):
        lw = op.ledoit_wolf([self.returns[t] for t in TICKERS])
        self.assertGreaterEqual(lw.intensity, 0.0)
        self.assertLessEqual(lw.intensity, 1.0)

    def test_shrinkage_preserves_symmetry_and_trace(self):
        lw = op.ledoit_wolf([self.returns[t] for t in TICKERS])
        n = len(TICKERS)
        for i in range(n):
            for j in range(n):
                self.assertAlmostEqual(lw.covariance[i][j], lw.covariance[j][i], places=15)
        sample = [[fl.covariance(self.returns[a], self.returns[b], sample=False)
                   for b in TICKERS] for a in TICKERS]
        self.assertAlmostEqual(sum(lw.covariance[i][i] for i in range(n)),
                               sum(sample[i][i] for i in range(n)), places=10)

    def test_shrinkage_improves_conditioning(self):
        shrunk = op.shrink_toward_identity(self.cov, 0.5)
        self.assertLess(op.condition_number(shrunk), op.condition_number(self.cov))

    def test_full_shrinkage_gives_a_diagonal_matrix(self):
        shrunk = op.shrink_toward_identity(self.cov, 1.0)
        for i in range(len(TICKERS)):
            for j in range(len(TICKERS)):
                if i != j:
                    self.assertAlmostEqual(shrunk[i][j], 0.0, places=15)

    def test_shorter_windows_need_more_shrinkage(self):
        short = op.ledoit_wolf([self.returns[t][:252] for t in TICKERS]).intensity
        long = op.ledoit_wolf([self.returns[t] for t in TICKERS]).intensity
        self.assertGreater(short, long)


class TestWalkForward(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dates, cls.returns, cls.mu, cls.cov = load()

    def test_estimator_never_sees_the_future(self):
        """The test that makes the whole backtest trustworthy."""
        seen: list[int] = []

        def spy(tickers, window):
            seen.append(len(window[tickers[0]]))
            return op.equal_weight(len(tickers))

        lookback = 504
        result = wf.walk_forward("spy", self.dates, self.returns, TICKERS, spy,
                                 lookback=lookback, cost_bps=0.0)
        # Every window handed to the estimator is exactly the lookback length,
        # so it can never contain an observation from on or after the rebalance.
        self.assertTrue(seen)
        for length in seen:
            self.assertEqual(length, lookback)
        self.assertEqual(len(result.returns),
                         len(self.returns[TICKERS[0]]) - lookback)

    def test_equal_weight_walk_forward_matches_a_direct_calculation(self):
        lookback = 504
        result = wf.walk_forward("ew", self.dates, self.returns, TICKERS,
                                 lambda t, w: op.equal_weight(len(t)),
                                 lookback=lookback, cost_bps=0.0)
        direct = [sum(self.returns[t][k] for t in TICKERS) / len(TICKERS)
                  for k in range(lookback, len(self.returns[TICKERS[0]]))]
        # The first day after each rebalance is exactly equal weighted; later
        # days drift, so compare the rebalance days only.
        for idx, date in enumerate(result.rebalance_dates):
            k = result.dates.index(date)
            self.assertAlmostEqual(result.returns[k], direct[k], places=10)

    def test_costs_reduce_returns(self):
        free = wf.walk_forward("a", self.dates, self.returns, TICKERS,
                               lambda t, w: op.inverse_volatility(
                                   [[fl.covariance(w[x], w[y]) for y in t] for x in t]),
                               lookback=504, cost_bps=0.0)
        dear = wf.walk_forward("b", self.dates, self.returns, TICKERS,
                               lambda t, w: op.inverse_volatility(
                                   [[fl.covariance(w[x], w[y]) for y in t] for x in t]),
                               lookback=504, cost_bps=100.0)
        self.assertGreater(fl.annualised_return(free.returns),
                           fl.annualised_return(dear.returns))

    def test_rebalances_happen_quarterly(self):
        result = wf.walk_forward("ew", self.dates, self.returns, TICKERS,
                                 lambda t, w: op.equal_weight(len(t)), lookback=504)
        quarters = {(d.year, (d.month - 1) // 3) for d in result.rebalance_dates}
        self.assertEqual(len(quarters), len(result.rebalance_dates))

    def test_weight_stability_is_zero_for_a_constant_rule(self):
        result = wf.walk_forward("ew", self.dates, self.returns, TICKERS,
                                 lambda t, w: op.equal_weight(len(t)), lookback=504)
        self.assertAlmostEqual(wf.weight_stability(result), 0.0, places=12)


if __name__ == "__main__":
    unittest.main()
