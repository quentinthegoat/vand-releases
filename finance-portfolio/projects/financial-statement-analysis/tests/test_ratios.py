"""Unit tests for the ratio engine.

These assert identities and invariants - a DuPont product that must reconcile
to reported ROE, a cash conversion cycle that must equal its three components,
denominators that must be refused rather than divided by - rather than pinning
the current output numbers, which would break on any driver change and prove
nothing about correctness.
"""

import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))

from ratios import (avg, cagr, common_size_income, compute_history,   # noqa: E402
                    compute_year, dupont_five, safe_div)

with open(os.path.join(HERE, "..", "data", "financials.json")) as fh:
    DATA = json.load(fh)


class TestSafeDiv(unittest.TestCase):
    def test_zero_denominator_returns_none(self):
        self.assertIsNone(safe_div(10.0, 0.0))

    def test_negative_denominator_refused_by_default(self):
        """ROE on negative equity is not a small number, it is not a number."""
        self.assertIsNone(safe_div(10.0, -5.0))

    def test_negative_denominator_allowed_when_asked(self):
        self.assertAlmostEqual(safe_div(10.0, -5.0, positive_denominator=False), -2.0)

    def test_average_of_opening_and_closing(self):
        self.assertAlmostEqual(avg(100.0, 200.0), 150.0)


class TestIdentities(unittest.TestCase):
    def test_cash_conversion_cycle_equals_its_components(self):
        for ticker in DATA:
            for r in compute_history(DATA[ticker]):
                self.assertAlmostEqual(r.cash_conversion_cycle, r.dso + r.dio - r.dpo,
                                       places=9, msg=f"{ticker} FY{r.year}")

    def test_dupont_product_reconciles_to_reported_roe(self):
        """The whole point of a decomposition: the parts must multiply back."""
        for ticker in DATA:
            years = DATA[ticker]["years"]
            for k, y in enumerate(years):
                d = dupont_five(y, years[k - 1] if k else None)
                if d["roe"] is None or d["reported_roe"] is None:
                    continue
                self.assertAlmostEqual(d["roe"], d["reported_roe"], places=9,
                                       msg=f"{ticker} FY{y['year']} DuPont does not reconcile")

    def test_common_size_lines_sum_to_net_margin(self):
        for ticker in DATA:
            for row in common_size_income(DATA[ticker]):
                built = (row["gross_profit"] + row["sga"] + row["research_development"]
                         + row["depreciation_amortisation"])
                self.assertAlmostEqual(built, row["ebit"], places=9,
                                       msg=f"{ticker} FY{row['year']} EBIT build-up")
                self.assertAlmostEqual(row["ebit"] + row["net_interest"] + row["tax"],
                                       row["net_income"], places=9,
                                       msg=f"{ticker} FY{row['year']} net income build-up")

    def test_margins_are_ordered(self):
        """Gross >= EBITDA >= EBIT for every company-year in this dataset."""
        for ticker in DATA:
            for r in compute_history(DATA[ticker]):
                self.assertGreaterEqual(r.gross_margin, r.ebitda_margin, f"{ticker} {r.year}")
                self.assertGreaterEqual(r.ebitda_margin, r.ebit_margin, f"{ticker} {r.year}")


class TestBehaviour(unittest.TestCase):
    def test_loss_making_company_reports_negative_roic(self):
        vssl = compute_history(DATA["VSSL"])
        self.assertLess(vssl[-1].roic, 0.0)

    def test_quick_ratio_never_exceeds_current_ratio(self):
        for ticker in DATA:
            for r in compute_history(DATA[ticker]):
                self.assertLessEqual(r.quick_ratio, r.current_ratio)

    def test_accrual_ratio_sign_matches_cash_versus_profit(self):
        for ticker in DATA:
            years = DATA[ticker]["years"]
            for k, y in enumerate(years):
                r = compute_year(y, years[k - 1] if k else None)
                cash_beats_profit = (y["cash_flow"]["cash_from_operations"]
                                     > y["income_statement"]["net_income"])
                self.assertEqual(cash_beats_profit, r.accrual_ratio < 0,
                                 f"{ticker} FY{y['year']}")

    def test_cagr_matches_compounded_endpoints(self):
        g = cagr(DATA["MRDN"], "revenue")
        first = DATA["MRDN"]["years"][0]["income_statement"]["revenue"]
        last = DATA["MRDN"]["years"][-1]["income_statement"]["revenue"]
        n = len(DATA["MRDN"]["years"]) - 1
        self.assertAlmostEqual(first * (1 + g) ** n, last, places=6)

    def test_cagr_refuses_negative_endpoints(self):
        self.assertIsNone(cagr(DATA["VSSL"], "net_income"))


class TestSourceData(unittest.TestCase):
    def test_every_balance_sheet_ties(self):
        for ticker, co in DATA.items():
            for y in co["years"]:
                b = y["balance_sheet"]
                self.assertAlmostEqual(b["total_assets"],
                                       b["total_liabilities"] + b["total_equity"],
                                       places=4, msg=f"{ticker} FY{y['year']}")

    def test_cash_flow_foots_and_ties_to_the_balance_sheet(self):
        for ticker, co in DATA.items():
            for y in co["years"]:
                c, b = y["cash_flow"], y["balance_sheet"]
                self.assertAlmostEqual(c["cash_from_operations"] + c["cash_from_investing"]
                                       + c["cash_from_financing"], c["net_change_in_cash"],
                                       places=4, msg=f"{ticker} FY{y['year']} sections")
                self.assertAlmostEqual(c["closing_cash"], b["cash"], places=4,
                                       msg=f"{ticker} FY{y['year']} closing cash")

    def test_free_cash_flow_definition(self):
        for ticker, co in DATA.items():
            for y in co["years"]:
                c = y["cash_flow"]
                self.assertAlmostEqual(c["free_cash_flow"],
                                       c["cash_from_operations"] + c["capital_expenditure"],
                                       places=4, msg=f"{ticker} FY{y['year']}")


if __name__ == "__main__":
    unittest.main()
