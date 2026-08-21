"""Unit tests for the portfolio engine.

The important ones here are the additivity tests.  Attribution that does not
sum to the thing it decomposes is worse than no attribution, because it looks
like an answer.
"""

import datetime as dt
import math
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))

import finlib as fl                                                     # noqa: E402
import portfolio as pf                                                  # noqa: E402

PRICES = os.path.join(HERE, "..", "data", "prices_daily.csv")
WEIGHTS = {"LCAP": 0.35, "SCAP": 0.10, "INTL": 0.12, "EMKT": 0.08,
           "BNDX": 0.25, "REIT": 0.06, "GOLD": 0.04}


def load():
    dates, prices = fl.read_price_csv(PRICES)
    return dates, {t: fl.simple_returns(px) for t, px in prices.items()}


class TestBacktest(unittest.TestCase):
    def setUp(self):
        self.dates, self.returns = load()
        self.sub = {t: self.returns[t] for t in WEIGHTS}

    def test_single_asset_portfolio_equals_the_asset(self):
        r = pf.backtest(self.dates, {"LCAP": self.returns["LCAP"]}, {"LCAP": 1.0}, "monthly")
        for a, b in zip(r.returns, self.returns["LCAP"]):
            self.assertAlmostEqual(a, b, places=12)

    def test_weights_always_sum_to_one(self):
        r = pf.backtest(self.dates, self.sub, WEIGHTS, "quarterly")
        for k in range(len(r.returns)):
            total = sum(r.weights_history[t][k] for t in WEIGHTS)
            self.assertAlmostEqual(total, 1.0, places=10)

    def test_never_rebalancing_does_no_trading(self):
        r = pf.backtest(self.dates, self.sub, WEIGHTS, "never", cost_bps=25.0)
        self.assertEqual(r.rebalance_count, 0)
        self.assertAlmostEqual(r.total_turnover, 0.0)
        self.assertAlmostEqual(r.cost_drag_annual, 0.0)

    def test_more_frequent_rebalancing_means_more_turnover(self):
        turns = {f: pf.backtest(self.dates, self.sub, WEIGHTS, f).total_turnover
                 for f in ("monthly", "quarterly", "annual")}
        self.assertGreater(turns["monthly"], turns["quarterly"])
        self.assertGreater(turns["quarterly"], turns["annual"])

    def test_trading_costs_reduce_returns(self):
        free = pf.backtest(self.dates, self.sub, WEIGHTS, "monthly", cost_bps=0.0)
        dear = pf.backtest(self.dates, self.sub, WEIGHTS, "monthly", cost_bps=50.0)
        self.assertGreater(fl.annualised_return(free.returns),
                           fl.annualised_return(dear.returns))

    def test_weights_are_normalised_if_they_do_not_sum_to_one(self):
        a = pf.backtest(self.dates, self.sub, WEIGHTS, "quarterly")
        doubled = {t: w * 2 for t, w in WEIGHTS.items()}
        b = pf.backtest(self.dates, self.sub, doubled, "quarterly")
        for x, y in zip(a.returns, b.returns):
            self.assertAlmostEqual(x, y, places=12)

    def test_unknown_frequency_is_rejected(self):
        with self.assertRaises(ValueError):
            pf.backtest(self.dates, self.sub, WEIGHTS, "fortnightly")


class TestAttribution(unittest.TestCase):
    def setUp(self):
        self.dates, self.returns = load()
        self.sub = {t: self.returns[t] for t in WEIGHTS}
        self.bt = pf.backtest(self.dates, self.sub, WEIGHTS, "quarterly")

    def test_return_contributions_sum_to_total_return(self):
        contrib = pf.return_contributions(self.sub, self.bt.weights_history)
        total = fl.cumulative(self.bt.returns)[-1] - 1.0
        self.assertAlmostEqual(sum(contrib.values()), total, places=9)

    def test_risk_contributions_sum_to_one(self):
        """Euler's theorem: portfolio volatility is homogeneous of degree one."""
        tickers = list(WEIGHTS)
        cov = fl.cov_matrix(self.returns, tickers)
        pcr = pf.risk_contributions(cov, [WEIGHTS[t] for t in tickers])
        self.assertAlmostEqual(sum(pcr), 1.0, places=10)

    def test_single_asset_takes_all_the_risk(self):
        cov = fl.cov_matrix(self.returns, ["LCAP"])
        self.assertAlmostEqual(pf.risk_contributions(cov, [1.0])[0], 1.0, places=10)

    def test_diversification_ratio_is_one_for_a_single_asset(self):
        cov = fl.cov_matrix(self.returns, ["LCAP"])
        self.assertAlmostEqual(pf.diversification_ratio(cov, [1.0]), 1.0, places=10)

    def test_diversification_ratio_exceeds_one_when_correlations_are_below_one(self):
        tickers = list(WEIGHTS)
        cov = fl.cov_matrix(self.returns, tickers)
        self.assertGreater(pf.diversification_ratio(cov, [WEIGHTS[t] for t in tickers]), 1.0)


class TestStatistics(unittest.TestCase):
    def test_max_drawdown_on_a_known_path(self):
        equity = [100.0, 120.0, 60.0, 90.0, 130.0]
        dd, peak, trough, recovery = fl.max_drawdown(equity)
        self.assertAlmostEqual(dd, -0.5)
        self.assertEqual((peak, trough, recovery), (1, 2, 4))

    def test_max_drawdown_reports_no_recovery_when_there_is_none(self):
        dd, _peak, _trough, recovery = fl.max_drawdown([100.0, 120.0, 60.0, 90.0])
        self.assertAlmostEqual(dd, -0.5)
        self.assertIsNone(recovery)

    def test_monotonic_series_has_no_drawdown(self):
        self.assertAlmostEqual(fl.max_drawdown([1.0, 2.0, 3.0, 4.0])[0], 0.0)

    def test_cagr_matches_compounding(self):
        r = [0.10] * 252
        self.assertAlmostEqual(fl.annualised_return(r), 1.10 ** 252 - 1.0, places=6)

    def test_sharpe_is_zero_when_excess_return_is_zero(self):
        rets = [0.001, -0.002, 0.003, -0.001] * 60
        self.assertAlmostEqual(fl.sharpe(rets, fl.mean(rets)), 0.0, places=12)

    def test_cvar_is_never_smaller_than_var(self):
        _dates, returns = load()
        for t, r in returns.items():
            self.assertGreaterEqual(fl.historical_cvar(r), fl.historical_var(r), t)

    def test_calendar_years_compound_to_the_total(self):
        dates, returns = load()
        bt = pf.backtest(dates, {t: returns[t] for t in WEIGHTS}, WEIGHTS, "quarterly")
        cal = pf.calendar_year_returns(bt.dates, bt.returns)
        product = 1.0
        for y in sorted(cal):
            product *= 1.0 + cal[y]
        self.assertAlmostEqual(product, fl.cumulative(bt.returns)[-1], places=9)

    def test_ols_recovers_a_known_relationship(self):
        x = [0.01 * math.sin(i) for i in range(500)]
        y = [0.5 * xi + 0.0002 for xi in x]
        fit = fl.ols(y, {"x": x})
        self.assertAlmostEqual(fit.get("x"), 0.5, places=8)
        self.assertAlmostEqual(fit.get("alpha"), 0.0002, places=8)
        self.assertAlmostEqual(fit.r2, 1.0, places=8)


if __name__ == "__main__":
    unittest.main()
