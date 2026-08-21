"""Unit tests for the valuation maths.

These check properties that must hold regardless of the assumptions - a
perpetuity identity, monotonicity, the terminal-method round trip - rather than
asserting today's output numbers.  Tests that only pin the current answer break
whenever an assumption is updated and prove nothing about the model.
"""

import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))

from dcf import (ForecastDrivers, WACCInputs, compute_wacc, discount,       # noqa: E402
                 forecast_fcff, implied_terminal_growth, monte_carlo,
                 percentile, reverse_dcf_growth, terminal_value_gordon,
                 value_with)


def drivers(growth=0.04, margin=0.11, n=5):
    return ForecastDrivers(
        years=tuple(2025 + k for k in range(n)),
        revenue_growth=tuple(growth for _ in range(n)),
        ebit_margin=tuple(margin for _ in range(n)),
        tax_rate=0.24,
        depreciation_pct_revenue=tuple(0.05 for _ in range(n)),
        capex_pct_revenue=tuple(0.05 for _ in range(n)),
        nwc_pct_revenue=0.10,
    )


class TestWACC(unittest.TestCase):
    def test_unlevered_equals_levered_without_debt(self):
        w = compute_wacc(WACCInputs(0.04, 0.05, 0.80, 0.06, 0.25, 1_000.0, 0.0))
        self.assertAlmostEqual(w.levered_beta, 0.80)
        self.assertAlmostEqual(w.wacc, w.cost_of_equity)

    def test_leverage_raises_beta_and_debt_lowers_wacc(self):
        no_debt = compute_wacc(WACCInputs(0.04, 0.05, 0.80, 0.06, 0.25, 1_000.0, 0.0))
        levered = compute_wacc(WACCInputs(0.04, 0.05, 0.80, 0.06, 0.25, 1_000.0, 500.0))
        self.assertGreater(levered.levered_beta, no_debt.levered_beta)
        # cheap after-tax debt in the mix pulls the blended rate down
        self.assertLess(levered.wacc, no_debt.wacc)

    def test_weights_sum_to_one(self):
        w = compute_wacc(WACCInputs(0.04, 0.05, 0.80, 0.06, 0.25, 1_200.0, 800.0))
        self.assertAlmostEqual(w.weight_equity + w.weight_debt, 1.0)


class TestForecast(unittest.TestCase):
    def test_fcff_identity(self):
        rows = forecast_fcff(1_000.0, drivers(), base_nwc=100.0)
        for r in rows:
            self.assertAlmostEqual(
                r.fcff, r.nopat + r.depreciation - r.capex - r.change_in_nwc, places=9)

    def test_working_capital_drag_scales_with_growth(self):
        slow = forecast_fcff(1_000.0, drivers(growth=0.01), base_nwc=100.0)
        fast = forecast_fcff(1_000.0, drivers(growth=0.10), base_nwc=100.0)
        self.assertGreater(fast[0].change_in_nwc, slow[0].change_in_nwc)

    def test_zero_growth_means_zero_working_capital_investment(self):
        rows = forecast_fcff(1_000.0, drivers(growth=0.0), base_nwc=100.0)
        for r in rows:
            self.assertAlmostEqual(r.change_in_nwc, 0.0, places=9)

    def test_mid_year_discounting_beats_year_end(self):
        rows_mid = discount(forecast_fcff(1_000.0, drivers(), 100.0), 0.09, mid_year=True)
        rows_end = discount(forecast_fcff(1_000.0, drivers(), 100.0), 0.09, mid_year=False)
        self.assertGreater(sum(r.present_value for r in rows_mid),
                           sum(r.present_value for r in rows_end))


class TestTerminalValue(unittest.TestCase):
    def test_gordon_perpetuity_identity(self):
        # A perpetuity growing at g, discounted at r, is worth FCFF*(1+g)/(r-g).
        self.assertAlmostEqual(terminal_value_gordon(100.0, 0.08, 0.02),
                               100.0 * 1.02 / 0.06)

    def test_growth_must_be_below_wacc(self):
        with self.assertRaises(ValueError):
            terminal_value_gordon(100.0, 0.05, 0.06)

    def test_implied_growth_inverts_gordon(self):
        tv = terminal_value_gordon(120.0, 0.085, 0.021)
        self.assertAlmostEqual(implied_terminal_growth(tv, 120.0, 0.085), 0.021, places=9)


class TestValuation(unittest.TestCase):
    def base(self, **kw):
        args = dict(base_revenue=1_000.0, base_nwc=100.0, drivers=drivers(),
                    wacc=0.085, net_debt=200.0, shares=100.0, terminal_growth=0.02)
        args.update(kw)
        return value_with(**args)

    def test_value_falls_as_wacc_rises(self):
        self.assertGreater(self.base(wacc=0.075).value_per_share,
                           self.base(wacc=0.095).value_per_share)

    def test_value_rises_with_growth_and_margin(self):
        self.assertGreater(self.base(drivers=drivers(growth=0.07)).value_per_share,
                           self.base(drivers=drivers(growth=0.02)).value_per_share)
        self.assertGreater(self.base(drivers=drivers(margin=0.14)).value_per_share,
                           self.base(drivers=drivers(margin=0.08)).value_per_share)

    def test_net_debt_reduces_equity_value_one_for_one(self):
        a = self.base(net_debt=0.0)
        b = self.base(net_debt=300.0)
        self.assertAlmostEqual(a.equity_value - b.equity_value, 300.0, places=6)

    def test_bridge_adds_up(self):
        v = self.base()
        self.assertAlmostEqual(v.enterprise_value, v.pv_explicit + v.pv_terminal, places=6)
        self.assertAlmostEqual(v.equity_value, v.enterprise_value - v.net_debt, places=6)
        self.assertAlmostEqual(v.value_per_share, v.equity_value / v.shares, places=9)

    def test_reverse_dcf_round_trip(self):
        """Solve for the growth implied by a price, then value at that growth:
        the result must come back to the price."""
        target = 14.0
        g = reverse_dcf_growth(target, 1_000.0, 100.0, drivers(), 0.085, 200.0, 100.0, 0.02)
        v = value_with(1_000.0, 100.0, drivers(growth=g), 0.085, 200.0, 100.0,
                       terminal_growth=0.02)
        self.assertAlmostEqual(v.value_per_share, target, places=4)


class TestMonteCarlo(unittest.TestCase):
    def test_deterministic_under_a_fixed_seed(self):
        kw = dict(base_revenue=1_000.0, base_nwc=100.0, drivers=drivers(),
                  wacc_mean=0.085, net_debt=200.0, shares=100.0,
                  terminal_growth_mean=0.02, trials=500, seed=42)
        self.assertEqual(monte_carlo(**kw), monte_carlo(**kw))

    def test_median_sits_near_the_deterministic_base_case(self):
        mc = monte_carlo(1_000.0, 100.0, drivers(), 0.085, 200.0, 100.0, 0.02,
                         trials=4_000, seed=1)
        base = value_with(1_000.0, 100.0, drivers(), 0.085, 200.0, 100.0,
                          terminal_growth=0.02).value_per_share
        self.assertLess(abs(percentile(mc, 0.5) / base - 1.0), 0.12)

    def test_percentiles_are_ordered(self):
        mc = monte_carlo(1_000.0, 100.0, drivers(), 0.085, 200.0, 100.0, 0.02,
                         trials=2_000, seed=3)
        self.assertLess(percentile(mc, 0.05), percentile(mc, 0.5))
        self.assertLess(percentile(mc, 0.5), percentile(mc, 0.95))


class TestSourceData(unittest.TestCase):
    def test_every_balance_sheet_ties(self):
        with open(os.path.join(HERE, "..", "data", "financials.json")) as fh:
            data = json.load(fh)
        for ticker, co in data.items():
            for y in co["years"]:
                b = y["balance_sheet"]
                self.assertAlmostEqual(
                    b["total_assets"], b["total_liabilities"] + b["total_equity"],
                    places=4, msg=f"{ticker} FY{y['year']} does not balance")

    def test_cash_flow_reconciles_to_the_balance_sheet(self):
        with open(os.path.join(HERE, "..", "data", "financials.json")) as fh:
            data = json.load(fh)
        for ticker, co in data.items():
            for y in co["years"]:
                c, b = y["cash_flow"], y["balance_sheet"]
                self.assertAlmostEqual(c["closing_cash"], b["cash"], places=4,
                                       msg=f"{ticker} FY{y['year']} cash mismatch")
                self.assertAlmostEqual(
                    c["opening_cash"] + c["net_change_in_cash"], c["closing_cash"],
                    places=4, msg=f"{ticker} FY{y['year']} cash flow does not foot")


if __name__ == "__main__":
    unittest.main()
