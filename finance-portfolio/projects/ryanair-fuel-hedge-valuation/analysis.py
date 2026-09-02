#!/usr/bin/env python3
"""Ryanair (RYA.IR) - what fuel price is in the share price?

    python analysis.py

Reads data/ryanair_fy26.json (transcribed from the FY26 results release) and
writes outputs/results.md plus five figures. No network, no dependencies.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import replace

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

import finlib as fl                                                    # noqa: E402
from airline import (Base, Drivers, FuelPath, breakeven_fuel_price,    # noqa: E402
                     forecast, implied_fuel_price, value)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "outputs")

FORECAST_YEARS = (2027, 2028, 2029, 2030, 2031)

# --- Cost of capital -------------------------------------------------------
# Ryanair holds net cash, so the WACC collapses to the cost of equity. A euro
# risk-free rate and a mature-market ERP; beta above 1 because airline earnings
# are geared to fuel and the cycle, which is precisely what this model tests.
RISK_FREE = 0.028
EQUITY_RISK_PREMIUM = 0.050
BETA = 1.15
WACC = RISK_FREE + BETA * EQUITY_RISK_PREMIUM
TERMINAL_GROWTH = 0.020

# --- Scenario axes ---------------------------------------------------------
FUEL_SCENARIOS = {
    "Normalisation ($75)": 75.0,
    "Elevated ($110)": 110.0,
    "Spot persists ($150)": 150.0,
    "Escalation ($200)": 200.0,
}
PASS_THROUGH = [0.0, 0.40, 0.70, 1.00]
BASE_PASS_THROUGH = 0.40


def build_drivers(pass_through: float = BASE_PASS_THROUGH) -> Drivers:
    return Drivers(
        years=FORECAST_YEARS,
        # Ryanair's stated ambition is roughly 300m passengers by 2034; from
        # 208m that is about 4% a year, constrained by Boeing delivery slots.
        traffic_growth=(0.030, 0.040, 0.040, 0.035, 0.035),
        non_fuel_cost_inflation=(0.035, 0.030, 0.030, 0.028, 0.028),
        ancillary_growth_per_pax=(0.010, 0.010, 0.010, 0.010, 0.010),
        pass_through=pass_through,
        tax_rate=0.103,                 # FY26 effective rate, 249.6 / 2,423.3
        capex_per_passenger=9.50,       # FY26 was EUR 9.08; MAX-10 spend ahead
        depreciation_per_passenger=6.59,   # FY26: 1,373.4 / 208.4
        # The balance sheet implies working capital of about -45% of revenue,
        # because passengers pay before they fly. Extrapolating that in full
        # would make growth implausibly cash-generative, so the model applies a
        # deliberately conservative -20% and sensitivity-tests it.
        nwc_per_passenger=-14.92,       # -20% of FY26 revenue per passenger
    )


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(HERE, "data", "ryanair_fy26.json")) as fh:
        d = json.load(fh)

    fy26 = d["income_statement"]["FY26"]
    hedge = d["hedging_and_liquidity"]
    mkt = d["market_data"]

    base = Base(
        passengers=d["operating_stats"]["FY26"]["passengers_m"],
        revenue=fy26["total_revenue"],
        fuel_cost=fy26["fuel_and_oil"],
        non_fuel_cost=fy26["opex_before_exceptional"] - fy26["fuel_and_oil"],
    )
    shares = fy26["shares_diluted_m"]
    net_cash = hedge["net_cash"]
    price = mkt["share_price_eur"]

    fuel = FuelPath(
        baseline_price=hedge["fy27_hedge_price_usd_bbl"],
        hedge_pct=hedge["fy27_hedge_pct"],
        hedge_price=hedge["fy27_hedge_price_usd_bbl"],
        spot_price=hedge["spot_jet_fuel_usd_bbl_at_reporting"],
        long_run_price=hedge["spot_jet_fuel_usd_bbl_at_reporting"],
    )

    drivers = build_drivers()

    # --- the grid: fuel price x pass-through -------------------------------
    grid = {}
    for name, p in FUEL_SCENARIOS.items():
        row = []
        for theta in PASS_THROUGH:
            v = value(base, drivers.with_pass_through(theta),
                      replace(fuel, long_run_price=p), WACC, TERMINAL_GROWTH,
                      net_cash, shares)
            row.append(v)
        grid[name] = row

    # --- reverse DCF and breakevens ----------------------------------------
    implied = {theta: implied_fuel_price(base, drivers.with_pass_through(theta), fuel,
                                         WACC, TERMINAL_GROWTH, net_cash, shares, price)
               for theta in PASS_THROUGH}
    breakeven = {theta: breakeven_fuel_price(base, drivers.with_pass_through(theta), fuel)
                 for theta in PASS_THROUGH}

    base_case = value(base, drivers, replace(fuel, long_run_price=110.0), WACC,
                      TERMINAL_GROWTH, net_cash, shares)

    # The FY26 realised fuel price is not disclosed, and the whole model scales
    # off it. Rather than pick one and hope, solve the reverse DCF across a
    # range of baselines: the implied *level* moves, but the implied price
    # expressed as a ratio to the baseline barely does, and that ratio is the
    # finding that survives the assumption.
    baseline_test = []
    for bl in (67.0, 75.0, 85.0, 95.0):
        f = replace(fuel, baseline_price=bl)
        imp = implied_fuel_price(base, drivers, f, WACC, TERMINAL_GROWTH,
                                 net_cash, shares, price)
        v150 = value(base, drivers, replace(f, long_run_price=150.0), WACC,
                     TERMINAL_GROWTH, net_cash, shares)
        baseline_test.append((bl, imp, imp / bl, v150.value_per_share))

    ctx = dict(d=d, base=base, drivers=drivers, fuel=fuel, shares=shares,
               net_cash=net_cash, price=price, grid=grid, implied=implied,
               breakeven=breakeven, base_case=base_case, fy26=fy26,
               baseline_test=baseline_test)
    write_report(ctx)

    print(f"FY26 unit economics: revenue EUR{base.revenue_per_pax:.2f}/pax, "
          f"fuel EUR{base.fuel_per_pax:.2f}/pax ({base.fuel_cost / base.revenue:.1%} of revenue)")
    print(f"fuel rise that erases operating profit: "
          f"{(base.revenue - base.fuel_cost - base.non_fuel_cost) / base.fuel_cost:.1%}")
    print(f"WACC {WACC:.2%} (net cash, so WACC = cost of equity)\n")
    for name, row in grid.items():
        print(f"  {name:22s} " + "  ".join(
            f"θ={t:.0%}: €{v.value_per_share:7.2f}" for t, v in zip(PASS_THROUGH, row)))
    print(f"\nmarket price €{price:.2f}")
    print("implied long-run fuel price at each pass-through: " + ", ".join(
        f"θ={t:.0%} ${p:.0f}" for t, p in implied.items()))
    print("EBIT breakeven fuel price: " + ", ".join(
        f"θ={t:.0%} ${p:.0f}" for t, p in breakeven.items()))
    print(f"outputs written to {OUT}")


def write_report(ns: dict) -> None:
    base, price, shares = ns["base"], ns["price"], ns["shares"]
    fy26, d = ns["fy26"], ns["d"]
    src = d["source"]
    eur = lambda v: f"€{v:,.2f}"                                        # noqa: E731

    parts = [
        "# Ryanair — what fuel price is in the share price?", "",
        f"_Generated by `python analysis.py`. Financials transcribed from "
        f"[{src['document']}]({src['url']}), published {src['published']}, "
        f"which the issuer labels preliminary and unaudited. Share price "
        f"{eur(price)} on {d['market_data']['price_date']} "
        f"({d['market_data']['exchange']})._", "",
        "## 1. FY26 as reported", "",
        fl.markdown_table(
            ["€m", "FY26", "FY25", "Change"],
            [[k,
              f"{d['income_statement']['FY26'][f]:,.1f}",
              f"{d['income_statement']['FY25'][f]:,.1f}",
              f"{d['income_statement']['FY26'][f] / d['income_statement']['FY25'][f] - 1:+.1%}"]
             for k, f in [("Total revenue", "total_revenue"),
                          ("Fuel and oil", "fuel_and_oil"),
                          ("Operating profit (pre-exceptional)", "operating_profit_pre_exceptional"),
                          ("Profit after tax", "profit_after_tax"),
                          ("Diluted EPS (€)", "eps_diluted")]]), "",
        "## 2. Unit economics and the fuel gearing", "",
        fl.markdown_table(
            ["Per passenger (FY26)", "€"],
            [["Revenue", f"{base.revenue_per_pax:.2f}"],
             ["Fuel", f"{base.fuel_per_pax:.2f}"],
             ["All other operating cost", f"{base.non_fuel_per_pax:.2f}"],
             ["**Operating profit**", f"**{(base.revenue - base.fuel_cost - base.non_fuel_cost) / base.passengers:.2f}**"]],
            align=["left", "right"]),
        "",
        f"Fuel is **{base.fuel_cost / base.revenue:.1%} of revenue** and "
        f"**{base.fuel_cost / (base.fuel_cost + base.non_fuel_cost):.1%} of the cost base**. "
        f"Operating profit is €{base.revenue - base.fuel_cost - base.non_fuel_cost:,.0f}m against a "
        f"fuel bill of €{base.fuel_cost:,.0f}m, so a "
        f"**{(base.revenue - base.fuel_cost - base.non_fuel_cost) / base.fuel_cost:.1%} rise in the fuel "
        f"bill erases every euro of operating profit** if nothing is recovered in fares.", "",
        f"At the reporting date the issuer disclosed spot jet fuel above "
        f"**${d['hedging_and_liquidity']['spot_jet_fuel_usd_bbl_at_reporting']:.0f}/bbl** against an FY27 hedge of "
        f"**{d['hedging_and_liquidity']['fy27_hedge_pct']:.0%} at ~${d['hedging_and_liquidity']['fy27_hedge_price_usd_bbl']:.0f}/bbl**, "
        f"expiring {d['hedging_and_liquidity']['hedge_expiry']}.", "",
        "## 3. Value per share: fuel price × fare pass-through", "",
        "Rows are the long-run jet-fuel price once the hedge rolls off. Columns are θ, the "
        "share of the fuel cost increase recovered through higher fares.", "",
        fl.markdown_table(
            ["Long-run fuel"] + [f"θ = {t:.0%}" for t in PASS_THROUGH],
            [[name] + [eur(v.value_per_share) for v in row] for name, row in ns["grid"].items()]),
        "",
        f"Market price: **{eur(price)}**.", "",
        "## 4. Reverse DCF — what the price already assumes", "",
        fl.markdown_table(
            ["Pass-through θ", "Implied long-run fuel price", "EBIT breakeven fuel price"],
            [[f"{t:.0%}",
              ("no solution" if ns["implied"][t] > 399 else f"${ns['implied'][t]:.0f}/bbl"),
              ("never" if ns["breakeven"][t] == float("inf") else f"${ns['breakeven'][t]:.0f}/bbl")]
             for t in PASS_THROUGH]),
        "",
        "## 5. Is the answer just the assumption? — testing the baseline", "",
        "The FY26 realised fuel price is not disclosed, and every scenario scales off it. "
        "So the reverse DCF is re-solved across a range of baselines. The implied *level* "
        "moves with the assumption, as it must — but the implied price **as a ratio to the "
        "baseline** barely moves, and that ratio is the result that survives.", "",
        fl.markdown_table(
            ["Assumed FY26 fuel ($/bbl)", "Implied long-run price", "Implied ÷ baseline",
             "Value at $150 spot (θ=40%)"],
            [[f"${bl:.0f}", f"${imp:.0f}", f"{ratio:.2f}×", eur(v)]
             for bl, imp, ratio, v in ns["baseline_test"]]),
        "",
        "**The finding, stated so that it does not depend on the weak assumption: the market "
        "is pricing long-run fuel within about 3% of whatever FY26 was struck at** — that is, it "
        "assumes the spike is fully temporary and fuel reverts to where it has been. "
        "Spot at the reporting date was 124% above the FY27 hedge price.", "",
        "### A note on the source document", "",
        "The release quotes the FY27 hedge two ways: `80% hedged @ $668 met. tn` in the "
        "highlights, and `approx. $67bbl` in the narrative. At the standard ~7.9 barrels per "
        "metric tonne these imply **$85/bbl and $67/bbl** respectively, which do not "
        "reconcile. The model works in $/bbl because spot is also quoted per barrel, and the "
        "baseline test above spans both readings. Anyone taking this further should resolve "
        "the discrepancy against the annual report's fuel note before quoting a level.", "",
        "## 6. Assumptions", "",
        fl.markdown_table(
            ["Assumption", "Value", "Basis"],
            [["WACC", f"{WACC:.2%}", "net cash, so WACC = cost of equity (CAPM)"],
             ["Risk-free / ERP / beta", f"{RISK_FREE:.1%} / {EQUITY_RISK_PREMIUM:.1%} / {BETA:.2f}", "euro rates, mature-market ERP, airline beta"],
             ["Terminal growth", f"{TERMINAL_GROWTH:.1%}", "below long-run nominal GDP"],
             ["Effective tax rate", "10.3%", "FY26 actual: 249.6 / 2,423.3"],
             ["Traffic growth", "3.0–4.0%", "~300m passengers by 2034, Boeing-constrained"],
             ["Non-fuel cost inflation", "2.8–3.5%", "judgement"],
             ["Capex per passenger", "€9.50", "FY26 was €9.08; MAX-10 spend ahead"],
             ["Depreciation per passenger", "€6.59", "FY26: 1,373.4 / 208.4 — tracks the fleet, not fuel"],
             ["Working capital per passenger", "−€14.92", "−20% of FY26 revenue/pax; balance sheet implies ~−45%"],
             ["FY26 realised fuel price", "assumed ≈ $67/bbl", "**not disclosed in this release — the model's weakest link**"]],
            align=["left", "right", "left"]), ""]

    with open(os.path.join(OUT, "results.md"), "w") as fh:
        fh.write("\n".join(parts))
    write_figures(ns)


def write_figures(ns: dict) -> None:
    price, grid = ns["price"], ns["grid"]
    names = list(grid)

    fl.write_svg(os.path.join(OUT, "value_grid.svg"), fl.heatmap(
        [f"{t:.0%}" for t in PASS_THROUGH],
        [[v.value_per_share for v in row] for row in grid.values()],
        title="Value per share (€): fuel price × fare pass-through",
        subtitle="Rows top to bottom: " + ", ".join(names)
                 + f". Market price €{price:.2f}.",
        fmt=lambda v: f"{v:,.0f}", cell=62,
        vmin=min(v.value_per_share for r in grid.values() for v in r),
        vmax=max(v.value_per_share for r in grid.values() for v in r),
        low="#f4dcd8", mid="#ffffff", high="#2c6a4d"))

    prices = [75.0, 90.0, 110.0, 130.0, 150.0, 175.0, 200.0]
    series = {}
    for theta in PASS_THROUGH:
        vals = []
        for p in prices:
            v = value(ns["base"], ns["drivers"].with_pass_through(theta),
                      replace(ns["fuel"], long_run_price=p), WACC, TERMINAL_GROWTH,
                      ns["net_cash"], ns["shares"])
            vals.append(v.value_per_share)
        series[f"θ = {theta:.0%}"] = vals
    series["Market price"] = [price] * len(prices)
    fl.write_svg(os.path.join(OUT, "value_vs_fuel.svg"), fl.line_chart(
        series, [f"${p:.0f}" for p in prices],
        title="Value per share against long-run jet-fuel price",
        subtitle="Each line is a fare pass-through assumption. Where a line crosses the "
                 "market price is the fuel view that price implies.",
        y_format=lambda v: f"€{v:,.0f}", zero_line=True, x_tick_every=1))

    rows = forecast(ns["base"], ns["drivers"], replace(ns["fuel"], long_run_price=110.0))
    fl.write_svg(os.path.join(OUT, "ebit_bridge.svg"), fl.bar_chart(
        ["FY26a"] + [f"FY{r.year - 2000}" for r in rows],
        [ns["base"].revenue - ns["base"].fuel_cost - ns["base"].non_fuel_cost]
        + [r.ebit for r in rows],
        title="Operating profit under the base case (fuel $110, θ = 40%)",
        subtitle="€m. FY27 is protected by the hedge; the damage lands in FY28.",
        y_format=lambda v: f"{v:,.0f}", colour_by_sign=True))

    fl.write_svg(os.path.join(OUT, "fuel_cost_share.svg"), fl.bar_chart(
        ["Fuel", "Staff", "Airport &\nhandling", "Depreciation", "Route\ncharges",
         "Marketing\n& other", "Maintenance"],
        [ns["fy26"][k] for k in ("fuel_and_oil", "staff_costs", "airport_and_handling",
                                 "depreciation", "route_charges",
                                 "marketing_distribution_other",
                                 "maintenance_materials_repairs")],
        title="FY26 operating cost base (€m)",
        subtitle="Fuel is larger than the next three lines combined. That concentration "
                 "is the whole investment case.",
        y_format=lambda v: f"{v:,.0f}"))


if __name__ == "__main__":
    main()
