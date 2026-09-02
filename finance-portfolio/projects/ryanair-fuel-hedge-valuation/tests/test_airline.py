"""Tests for the Ryanair fuel model and the transcribed financials.

Two things are being tested, and the second matters as much as the first:

1. **The model's invariants.** Above all, that full fare pass-through makes
   value independent of the fuel price. If that ever fails, depreciation or
   working capital has been wired to revenue instead of to passengers, and
   every number in the grid is wrong.

2. **The transcription.** These figures were typed by hand out of a PDF. The
   statements must foot: revenue components sum to total revenue, cost lines sum
   to total operating expenses, and the profit build works down to EPS. A
   transcription error is the most likely defect in this project, so it is the
   one most heavily tested.
"""

import json
import os
import sys
import unittest
from dataclasses import replace

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))

from airline import (Base, Drivers, FuelPath, breakeven_fuel_price,   # noqa: E402
                     forecast, implied_fuel_price, value)

with open(os.path.join(HERE, "..", "data", "ryanair_fy26.json")) as fh:
    D = json.load(fh)

FY26 = D["income_statement"]["FY26"]
FY25 = D["income_statement"]["FY25"]
HEDGE = D["hedging_and_liquidity"]


def base_case():
    return Base(passengers=D["operating_stats"]["FY26"]["passengers_m"],
                revenue=FY26["total_revenue"], fuel_cost=FY26["fuel_and_oil"],
                non_fuel_cost=FY26["opex_before_exceptional"] - FY26["fuel_and_oil"])


def drivers(theta=0.40):
    return Drivers(years=(2027, 2028, 2029, 2030, 2031),
                   traffic_growth=(0.030, 0.040, 0.040, 0.035, 0.035),
                   non_fuel_cost_inflation=(0.035, 0.030, 0.030, 0.028, 0.028),
                   ancillary_growth_per_pax=(0.01,) * 5,
                   pass_through=theta, tax_rate=0.103, capex_per_passenger=9.50,
                   depreciation_per_passenger=6.59, nwc_per_passenger=-14.92)


def fuel(long_run=110.0, baseline=67.0):
    return FuelPath(baseline_price=baseline, hedge_pct=HEDGE["fy27_hedge_pct"],
                    hedge_price=HEDGE["fy27_hedge_price_usd_bbl"],
                    spot_price=HEDGE["spot_jet_fuel_usd_bbl_at_reporting"],
                    long_run_price=long_run)


def val(theta=0.40, long_run=110.0, baseline=67.0):
    return value(base_case(), drivers(theta), fuel(long_run, baseline),
                 wacc=0.0855, terminal_growth=0.020,
                 net_cash=HEDGE["net_cash"], shares=FY26["shares_diluted_m"])


class TestTranscription(unittest.TestCase):
    """The filing must foot. If it does not, it was typed in wrong."""

    def test_revenue_components_sum(self):
        for y in (FY26, FY25):
            self.assertAlmostEqual(y["scheduled_revenue"] + y["ancillary_revenue"],
                                   y["total_revenue"], places=1)

    def test_operating_cost_lines_sum(self):
        for y in (FY26, FY25):
            lines = ("fuel_and_oil", "staff_costs", "airport_and_handling", "depreciation",
                     "route_charges", "marketing_distribution_other",
                     "maintenance_materials_repairs")
            self.assertAlmostEqual(sum(y[k] for k in lines), y["opex_before_exceptional"],
                                   places=1)

    def test_total_opex_includes_the_exceptional_charge(self):
        for y in (FY26, FY25):
            self.assertAlmostEqual(y["opex_before_exceptional"] + y["exceptional_charge"],
                                   y["total_opex"], places=1)

    def test_operating_profit_builds_from_revenue_less_costs(self):
        for y in (FY26, FY25):
            self.assertAlmostEqual(y["total_revenue"] - y["total_opex"],
                                   y["operating_profit"], places=1)
            self.assertAlmostEqual(y["total_revenue"] - y["opex_before_exceptional"],
                                   y["operating_profit_pre_exceptional"], places=1)

    def test_profit_before_tax_builds(self):
        for y in (FY26, FY25):
            self.assertAlmostEqual(
                y["operating_profit"] + y["net_finance_and_other_income"]
                + y["foreign_exchange"], y["profit_before_tax"], places=1)

    def test_profit_after_tax_builds(self):
        for y in (FY26, FY25):
            self.assertAlmostEqual(y["profit_before_tax"] + y["tax_expense"],
                                   y["profit_after_tax"], places=1)

    def test_eps_reconciles_to_profit_and_share_count(self):
        for y in (FY26, FY25):
            self.assertAlmostEqual(y["profit_after_tax"] / y["shares_basic_m"],
                                   y["eps_basic"], places=3)
            self.assertAlmostEqual(y["profit_after_tax"] / y["shares_diluted_m"],
                                   y["eps_diluted"], places=3)

    def test_balance_sheet_balances(self):
        for k in ("FY26", "FY25"):
            b = D["balance_sheet"][k]
            self.assertAlmostEqual(
                b["total_non_current_assets"] + b["total_current_assets"],
                b["total_assets"], places=1)
            self.assertAlmostEqual(
                b["total_current_liabilities"] + b["total_non_current_liabilities"]
                + b["shareholders_equity"], b["total_assets"], places=1)

    def test_net_cash_matches_the_issuer_statement(self):
        """Gross cash less debt AND lease liabilities gives the stated EUR 2.1bn.

        Excluding leases gives EUR 2,230m, which is not what the issuer reported
        — so this test also pins down the definition being used."""
        b = D["balance_sheet"]["FY26"]
        gross = (b["cash_and_equivalents"] + b["financial_assets_cash_over_3m"]
                 + b["restricted_cash"])
        net = gross - (b["current_maturities_of_debt"] + b["non_current_maturities_of_debt"]
                       + b["current_lease_liability"] + b["non_current_lease_liability"])
        self.assertAlmostEqual(gross, HEDGE["gross_cash"], places=1)
        self.assertAlmostEqual(net, HEDGE["net_cash"], places=1)
        self.assertAlmostEqual(net / 1000.0, 2.1, places=1)


class TestBaseUnitEconomics(unittest.TestCase):
    def test_ebit_per_the_model_matches_the_filing(self):
        b = base_case()
        self.assertAlmostEqual(b.revenue - b.fuel_cost - b.non_fuel_cost,
                               FY26["operating_profit_pre_exceptional"], places=1)

    def test_fuel_share_of_revenue(self):
        b = base_case()
        self.assertAlmostEqual(b.fuel_cost / b.revenue, 0.3486, places=3)

    def test_fuel_rise_that_erases_operating_profit(self):
        b = base_case()
        ebit = b.revenue - b.fuel_cost - b.non_fuel_cost
        self.assertAlmostEqual(ebit / b.fuel_cost, 0.454, places=3)


class TestFuelPath(unittest.TestCase):
    def test_year_one_blends_hedge_and_spot(self):
        f = fuel()
        self.assertAlmostEqual(f.effective_price(1), 0.8 * 67.0 + 0.2 * 150.0, places=6)

    def test_later_years_are_fully_exposed(self):
        f = fuel(long_run=123.0)
        for y in (2, 3, 4, 5):
            self.assertAlmostEqual(f.effective_price(y), 123.0, places=9)

    def test_cost_factor_is_relative_to_the_baseline(self):
        self.assertAlmostEqual(fuel(long_run=134.0).cost_factor(2), 2.0, places=9)


class TestModelInvariants(unittest.TestCase):
    def test_full_pass_through_makes_value_independent_of_fuel(self):
        """The invariant the whole model rests on.

        If every euro of fuel is recovered in fares, the fuel price cannot
        change value. A failure here means depreciation or working capital has
        been wired to revenue instead of to passengers."""
        values = [val(theta=1.0, long_run=p).value_per_share
                  for p in (75.0, 110.0, 150.0, 200.0, 300.0)]
        for v in values[1:]:
            self.assertAlmostEqual(v, values[0], places=6)

    def test_value_falls_as_fuel_rises_when_pass_through_is_partial(self):
        for theta in (0.0, 0.4, 0.7):
            vs = [val(theta=theta, long_run=p).value_per_share
                  for p in (75.0, 110.0, 150.0, 200.0)]
            for a, b in zip(vs, vs[1:]):
                self.assertGreater(a, b, f"theta={theta}")

    def test_value_rises_with_pass_through(self):
        vs = [val(theta=t, long_run=150.0).value_per_share for t in (0.0, 0.4, 0.7, 1.0)]
        for a, b in zip(vs, vs[1:]):
            self.assertLess(a, b)

    def test_net_cash_is_added_not_subtracted(self):
        v = val()
        self.assertAlmostEqual(v.equity_value, v.enterprise_value + v.net_cash, places=6)
        self.assertGreater(v.equity_value, v.enterprise_value)

    def test_bridge_adds_up(self):
        v = val()
        self.assertAlmostEqual(v.enterprise_value, v.pv_explicit + v.pv_terminal, places=6)
        self.assertAlmostEqual(v.value_per_share, v.equity_value / v.shares, places=9)

    def test_fy27_is_protected_by_the_hedge(self):
        """Even at extreme spot, FY27 margin holds up: that is what the hedge buys."""
        rows = forecast(base_case(), drivers(0.0), fuel(long_run=300.0))
        self.assertGreater(rows[0].ebit, 0.0)
        self.assertLess(rows[1].ebit, rows[0].ebit)

    def test_terminal_value_is_zero_on_negative_final_cash_flow(self):
        """A Gordon terminal value on a negative cash flow is meaningless and
        would grow more positive as the growth rate rises."""
        v = val(theta=0.0, long_run=300.0)
        self.assertLessEqual(v.rows[-1].fcff, 0.0)
        self.assertEqual(v.pv_terminal, 0.0)


class TestSolvers(unittest.TestCase):
    def test_reverse_dcf_round_trip(self):
        target = 22.845
        p = implied_fuel_price(base_case(), drivers(0.40), fuel(), 0.0855, 0.020,
                               HEDGE["net_cash"], FY26["shares_diluted_m"], target)
        v = val(theta=0.40, long_run=p).value_per_share
        self.assertAlmostEqual(v, target, places=3)

    def test_breakeven_price_produces_zero_ebit(self):
        for theta in (0.0, 0.4):
            p = breakeven_fuel_price(base_case(), drivers(theta), fuel())
            rows = forecast(base_case(), drivers(theta), fuel(long_run=p))
            self.assertAlmostEqual(rows[-1].ebit, 0.0, delta=1.0)

    def test_higher_pass_through_raises_the_breakeven_price(self):
        prices = [breakeven_fuel_price(base_case(), drivers(t), fuel())
                  for t in (0.0, 0.4, 0.7)]
        for a, b in zip(prices, prices[1:]):
            self.assertGreater(b, a)

    def test_full_pass_through_never_breaks_even(self):
        self.assertEqual(breakeven_fuel_price(base_case(), drivers(1.0), fuel()),
                         float("inf"))

    def test_implied_price_scales_with_the_baseline_assumption(self):
        """The ratio is stable even though the level is not — the finding in
        section 4.4 of the write-up."""
        ratios = []
        for bl in (67.0, 75.0, 85.0, 95.0):
            p = implied_fuel_price(base_case(), drivers(0.40), fuel(baseline=bl),
                                   0.0855, 0.020, HEDGE["net_cash"],
                                   FY26["shares_diluted_m"], 22.845)
            ratios.append(p / bl)
        self.assertLess(max(ratios) - min(ratios), 0.05)


if __name__ == "__main__":
    unittest.main()
