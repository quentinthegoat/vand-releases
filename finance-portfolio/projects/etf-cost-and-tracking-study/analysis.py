#!/usr/bin/env python3
"""Three funds, one index: which should you actually own?

    python analysis.py

Compares a 3bp core index fund, a 9bp total-market fund and a 35bp multifactor
fund against the index they are measured on, then asks what each costs to hold
over 10, 20 and 30 years. Writes outputs/results.md and six figures.
No arguments, no network, no third-party packages.
"""

from __future__ import annotations

import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

import etf                                                        # noqa: E402
import finlib as fl                                               # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "outputs")

INDEX = "IDXUS"
FUNDS = ["LCAP", "BRDX", "SMRT"]
LABELS = {"LCAP": "Core US Large-Cap", "BRDX": "Total US Market",
          "SMRT": "US Multifactor"}

# Assumed holdings, used only for the overlap calculation.  Real overlap comes
# from published holdings files; these stand in for them and the write-up says so.
ASSUMED_HOLDINGS = {
    "LCAP": {"mega_cap": 0.32, "large_cap": 0.58, "mid_cap": 0.10, "small_cap": 0.00},
    "BRDX": {"mega_cap": 0.28, "large_cap": 0.51, "mid_cap": 0.15, "small_cap": 0.06},
    "SMRT": {"mega_cap": 0.14, "large_cap": 0.44, "mid_cap": 0.28, "small_cap": 0.14},
}

INVESTMENT = 100_000.0
HORIZONS = (10, 20, 30)
GROSS_RETURN = 0.070      # assumed gross market return for the fee projections


def load_expense_ratios() -> dict[str, float]:
    with open(os.path.join(HERE, "data", "universe.csv")) as fh:
        return {r["ticker"]: float(r["annual_expense_ratio"]) for r in csv.DictReader(fh)}


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    dates, prices = fl.read_price_csv(os.path.join(HERE, "data", "prices_daily.csv"))
    _, rf_annual = fl.read_series_csv(os.path.join(HERE, "data", "risk_free_daily.csv"))
    rf_daily = [r / fl.TRADING_DAYS for r in rf_annual[1:]]
    expenses = load_expense_ratios()

    stats = {t: etf.analyse_tracking(t, prices[t], prices[INDEX], expenses[t])
             for t in FUNDS}

    write_report(dict(dates=dates, prices=prices, stats=stats, expenses=expenses,
                      rf_daily=rf_daily))

    for t in FUNDS:
        s = stats[t]
        print(f"{t} ({LABELS[t]:18s}) fee {fl.pct(s.expense_ratio, 2):>6}  "
              f"tracking difference {fl.pct(s.tracking_difference_annual, 2):>7}/yr  "
              f"tracking error {fl.pct(s.tracking_error_annual, 2):>6}  "
              f"unexplained {fl.pct(s.unexplained_annual, 2):>7}")
    gap = expenses["SMRT"] - expenses["LCAP"]
    cost = etf.fee_drag(INVESTMENT, GROSS_RETURN, expenses["SMRT"], 30)["cost"] \
        - etf.fee_drag(INVESTMENT, GROSS_RETURN, expenses["LCAP"], 30)["cost"]
    print(f"\n{fl.pct(gap, 2)} fee gap costs ${cost:,.0f} on ${INVESTMENT:,.0f} over 30 years")
    print(f"outputs written to {OUT}")


def write_report(ns: dict) -> None:
    stats, prices, expenses = ns["stats"], ns["prices"], ns["expenses"]
    money = lambda v: f"${v:,.0f}"                                     # noqa: E731

    parts = ["# ETF cost and tracking study — generated output", "",
             "_Every figure below is produced by `python analysis.py`. The price history is "
             "simulated; see `data/README.md`._", "",
             "## 1. The funds", "",
             fl.markdown_table(
                 ["Ticker", "Mandate", "Expense ratio", "10-year CAGR",
                  "Index CAGR", "Difference"],
                 [[t, LABELS[t], fl.pct(expenses[t], 2),
                   fl.pct(stats[t].fund_cagr), fl.pct(stats[t].index_cagr),
                   f"{stats[t].tracking_difference_annual * 100:+.2f}pp"]
                  for t in FUNDS]), "",
             "## 2. Tracking: level versus volatility", "",
             "Tracking **difference** is how much return the fund gave up. Tracking "
             "**error** is how reliably it gave up that amount. They answer different "
             "questions and a fund can be good at one and bad at the other.", "",
             fl.markdown_table(
                 ["Fund", "Expense ratio", "Tracking difference p.a.", "Tracking error p.a.",
                  "Unexplained", "Worst rolling year", "Best rolling year", "Beta", "R²"],
                 [[t, fl.pct(stats[t].expense_ratio, 2),
                   f"{stats[t].tracking_difference_annual * 100:+.2f}%",
                   fl.pct(stats[t].tracking_error_annual, 2),
                   f"{stats[t].unexplained_annual * 100:+.2f}%",
                   f"{stats[t].worst_rolling_year * 100:+.2f}%",
                   f"{stats[t].best_rolling_year * 100:+.2f}%",
                   f"{stats[t].beta_to_index:.3f}", f"{stats[t].r_squared:.4f}"]
                  for t in FUNDS]), "",
             "'Unexplained' is the tracking difference plus the expense ratio: what is left "
             "after fees have been accounted for. A well-run index fund should show a small "
             "number here. A large one means sampling error, cash drag, securities-lending "
             "revenue, or a portfolio that does not match the index it is quoted against.", ""]

    # ---- cost of ownership ------------------------------------------------
    parts += ["## 3. What the fee costs over a lifetime", "",
              f"${INVESTMENT:,.0f} invested at an assumed {fl.pct(GROSS_RETURN)} gross annual "
              f"return, with each fund's fee deducted. Same gross return for all three: a "
              f"fund gets no credit for outperformance it has not demonstrated.", ""]
    rows = []
    for t in FUNDS:
        row = [f"{t} ({fl.pct(expenses[t], 2)})"]
        for years in HORIZONS:
            d = etf.fee_drag(INVESTMENT, GROSS_RETURN, expenses[t], years)
            row.append(money(d["net_value"]))
        for years in HORIZONS:
            d = etf.fee_drag(INVESTMENT, GROSS_RETURN, expenses[t], years)
            row.append(money(d["cost"]))
        rows.append(row)
    parts += [fl.markdown_table(
        ["Fund", "Value 10y", "Value 20y", "Value 30y",
         "Fees paid 10y", "Fees paid 20y", "Fees paid 30y"], rows), ""]

    gap = expenses["SMRT"] - expenses["LCAP"]
    d30_smrt = etf.fee_drag(INVESTMENT, GROSS_RETURN, expenses["SMRT"], 30)
    d30_lcap = etf.fee_drag(INVESTMENT, GROSS_RETURN, expenses["LCAP"], 30)
    parts += [
        fl.markdown_table(
            ["Comparison", "Value"],
            [["Fee gap, SMRT over LCAP", fl.pct(gap, 2)],
             ["Extra cost over 30 years", money(d30_smrt["cost"] - d30_lcap["cost"])],
             ["As a share of the ending LCAP balance",
              fl.pct((d30_smrt["cost"] - d30_lcap["cost"]) / d30_lcap["net_value"], 1)],
             ["Gross outperformance SMRT needs each year, just to draw level",
              fl.pct(etf.breakeven_outperformance(gap), 2)],
             ["SMRT's actual annual difference to the index over the sample",
              f"{stats['SMRT'].tracking_difference_annual * 100:+.2f}%"]],
            align=["left", "right"]), ""]

    # ---- overlap ----------------------------------------------------------
    parts += ["## 4. How different are they really?", "",
              fl.markdown_table(
                  ["Pair", "Return correlation", "Assumed holdings overlap"],
                  [[f"{a} vs {b}",
                    f"{fl.correlation(fl.simple_returns(prices[a]), fl.simple_returns(prices[b])):.4f}",
                    fl.pct(etf.holding_overlap(ASSUMED_HOLDINGS[a], ASSUMED_HOLDINGS[b]), 0)]
                   for a, b in (("LCAP", "BRDX"), ("LCAP", "SMRT"), ("BRDX", "SMRT"))]), "",
              "Holdings overlap uses the stand-in capitalisation buckets in `analysis.py`, "
              "not real holdings files — it shows the calculation, not a fact about any "
              "fund. Return correlation is computed from the price data and is a fact about "
              "the sample.", ""]

    # ---- risk-adjusted ----------------------------------------------------
    parts += ["## 5. Risk and return of each fund", "",
              fl.markdown_table(
                  ["Fund", "CAGR", "Volatility", "Sharpe", "Max drawdown",
                   "Information ratio vs index"],
                  [[t, fl.pct(stats[t].fund_cagr),
                    fl.pct(fl.annualised_vol(fl.simple_returns(prices[t]))),
                    f"{fl.sharpe(fl.simple_returns(prices[t]), ns['rf_daily']):.2f}",
                    fl.pct(fl.max_drawdown(fl.cumulative(fl.simple_returns(prices[t])))[0]),
                    f"{stats[t].information_ratio:+.2f}"]
                   for t in FUNDS]
                  + [[f"{INDEX} (index, not investable)",
                      fl.pct(fl.annualised_return(fl.simple_returns(prices[INDEX]))),
                      fl.pct(fl.annualised_vol(fl.simple_returns(prices[INDEX]))),
                      f"{fl.sharpe(fl.simple_returns(prices[INDEX]), ns['rf_daily']):.2f}",
                      fl.pct(fl.max_drawdown(fl.cumulative(fl.simple_returns(prices[INDEX])))[0]),
                      "—"]]), ""]

    with open(os.path.join(OUT, "results.md"), "w") as fh:
        fh.write("\n".join(parts))

    write_figures(ns)


def write_figures(ns: dict) -> None:
    prices, stats, expenses = ns["prices"], ns["stats"], ns["expenses"]
    labels = [d.strftime("%Y-%m") for d in ns["dates"]]

    fl.write_svg(os.path.join(OUT, "cumulative_vs_index.svg"), fl.line_chart(
        dict({f"{INDEX} (index)": fl.rebase(prices[INDEX])},
             **{t: fl.rebase(prices[t]) for t in FUNDS}),
        labels, title="Growth of 100 against the index",
        subtitle="At this scale all four lines are the same line. That is the point: the "
                 "differences that matter are too small to see and too large to ignore.",
        y_format=lambda v: f"{v:,.0f}"))

    fl.write_svg(os.path.join(OUT, "rolling_tracking_difference.svg"), fl.line_chart(
        {t: etf.rolling_tracking_difference(prices[t], prices[INDEX]) for t in FUNDS},
        labels, title="Rolling one-year return difference versus the index",
        subtitle="The multifactor fund's spread against the index is two orders of magnitude "
                 "wider than the index funds'.",
        y_format=lambda v: f"{v:+.1%}", zero_line=True))

    fl.write_svg(os.path.join(OUT, "tracking_difference_bars.svg"), fl.bar_chart(
        [f"{t}\n({fl.pct(expenses[t], 2)} fee)" for t in FUNDS],
        [stats[t].tracking_difference_annual for t in FUNDS],
        title="Annual tracking difference against the index",
        subtitle="Negative means the fund lagged. For an index fund this should sit close to "
                 "minus the expense ratio.",
        y_format=lambda v: f"{v:+.2%}", colour_by_sign=True))

    fl.write_svg(os.path.join(OUT, "fee_drag.svg"), fl.line_chart(
        {f"{t} ({fl.pct(expenses[t], 2)})":
            etf.total_cost_of_ownership(INVESTMENT, GROSS_RETURN, expenses[t], 30)
         for t in FUNDS},
        [str(y) for y in range(31)],
        title=f"${INVESTMENT:,.0f} at {fl.pct(GROSS_RETURN)} gross, net of fees",
        subtitle="Identical gross return; the only difference between these three lines is "
                 "the expense ratio.",
        y_format=lambda v: f"${v / 1000:,.0f}k", x_tick_every=5))

    gaps = []
    for years in (5, 10, 20, 30, 40):
        d_hi = etf.fee_drag(INVESTMENT, GROSS_RETURN, expenses["SMRT"], years)
        d_lo = etf.fee_drag(INVESTMENT, GROSS_RETURN, expenses["LCAP"], years)
        gaps.append(d_hi["cost"] - d_lo["cost"])
    fl.write_svg(os.path.join(OUT, "fee_gap_by_horizon.svg"), fl.bar_chart(
        [f"{y} years" for y in (5, 10, 20, 30, 40)], gaps,
        title="Extra lifetime cost of the 0.32pp fee gap",
        subtitle=f"SMRT versus LCAP on a ${INVESTMENT:,.0f} investment. The cost is not "
                 f"linear in time, because the fee compounds against you.",
        y_format=lambda v: f"${v / 1000:,.1f}k"))

    fl.write_svg(os.path.join(OUT, "tracking_error_vs_fee.svg"), fl.scatter_chart(
        [(expenses[t], stats[t].tracking_error_annual, t) for t in FUNDS],
        title="Expense ratio against tracking error",
        subtitle="Two different costs of ownership. A fund can be cheap and unreliable, or "
                 "dear and precise — these three are neither.",
        x_label="Expense ratio", y_label="Annualised tracking error",
        x_format=lambda v: f"{v:.2%}", y_format=lambda v: f"{v:.1%}"))


if __name__ == "__main__":
    main()
