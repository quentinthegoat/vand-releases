#!/usr/bin/env python3
"""Meridian Beverage Group (MRDN) - intrinsic value, run end to end.

    python analysis.py

Writes every table and figure quoted in README.md and report/research-note.md
into outputs/.  No arguments, no network, no third-party packages: the point is
that a reader can reproduce every number in the write-up in one command.
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

import finlib as fl                                                    # noqa: E402
from comps import build_comp_row, implied_value_per_share, median, screen  # noqa: E402
from dcf import (ForecastDrivers, WACCInputs, compute_wacc, implied_exit_multiple,  # noqa: E402
                 implied_terminal_growth, monte_carlo, percentile,
                 reverse_dcf_growth, value_with)

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data", "financials.json")
OUT = os.path.join(HERE, "outputs")

TICKER = "MRDN"
BASE_YEAR = 2024
FORECAST_YEARS = (2025, 2026, 2027, 2028, 2029)

# ---------------------------------------------------------------------------
# Assumptions.  Every one of these is defended in README.md; nothing here is
# picked because it produced a convenient answer.
# ---------------------------------------------------------------------------

RISK_FREE = 0.041              # 10-year government yield
EQUITY_RISK_PREMIUM = 0.050    # mature-market implied ERP
UNLEVERED_BETA = 0.72          # bottom-up, staples/beverages
SIZE_PREMIUM = 0.005           # mid-cap illiquidity premium
TERMINAL_GROWTH = 0.0225       # below long-run nominal GDP
EXIT_MULTIPLE = 9.5            # cross-check terminal method
WEEK_52_RANGE = (21.90, 29.40)  # fictional, for the football field only

BASE_CASE = dict(
    revenue_growth=(0.050, 0.046, 0.042, 0.038, 0.035),
    ebit_margin=(0.109, 0.113, 0.116, 0.118, 0.119),
    depreciation_pct_revenue=(0.050, 0.049, 0.048, 0.048, 0.047),
    capex_pct_revenue=(0.052, 0.051, 0.049, 0.047, 0.046),
)

SCENARIOS = {
    #            growth shift, margin shift, terminal g, probability
    "Bear":  (-0.022, -0.017, 0.0150, 0.25),
    "Base":  (0.000, 0.000, TERMINAL_GROWTH, 0.50),
    "Bull":  (+0.018, +0.014, 0.0275, 0.25),
}


def load() -> dict:
    with open(DATA) as fh:
        return json.load(fh)


def historical_nwc_ratio(company: dict) -> float:
    """Net working capital as a share of revenue, averaged over history.

    Averaging matters here: FY2022 working capital was distorted by inventory
    build during the cost spike, and anchoring the forecast on that one year
    would bake a temporary problem into perpetuity."""
    ratios = []
    for y in company["years"]:
        b, i = y["balance_sheet"], y["income_statement"]
        nwc = (b["receivables"] + b["inventory"] + b["prepaid"]
               - b["payables"] - b["accrued"])
        ratios.append(nwc / i["revenue"])
    return sum(ratios) / len(ratios)


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    data = load()
    co = data[TICKER]
    base = next(y for y in co["years"] if y["year"] == BASE_YEAR)
    i, b, c, m = (base["income_statement"], base["balance_sheet"],
                  base["cash_flow"], base["market"])

    shares = i["diluted_shares"]
    price = m["share_price"]
    net_debt = m["net_debt"]
    gross_debt = b["debt_st"] + b["debt_lt"] + b["revolver"]
    nwc_ratio = historical_nwc_ratio(co)
    base_nwc = i["revenue"] * nwc_ratio

    # ---------------- cost of capital ---------------------------------------
    w = compute_wacc(WACCInputs(
        risk_free=RISK_FREE, equity_risk_premium=EQUITY_RISK_PREMIUM,
        unlevered_beta=UNLEVERED_BETA,
        pretax_cost_of_debt=i["interest_expense"] / ((gross_debt + 1_182.0) / 2),
        tax_rate=i["tax"] / i["pretax_income"],
        market_cap=price * shares, market_value_of_debt=gross_debt,
        size_premium=SIZE_PREMIUM))
    tax_rate = i["tax"] / i["pretax_income"]

    drivers = ForecastDrivers(years=FORECAST_YEARS, tax_rate=tax_rate,
                              nwc_pct_revenue=nwc_ratio, **BASE_CASE)

    # ---------------- base case, both terminal methods -----------------------
    gordon = value_with(i["revenue"], base_nwc, drivers, w.wacc, net_debt, shares,
                        terminal_growth=TERMINAL_GROWTH)
    exitm = value_with(i["revenue"], base_nwc, drivers, w.wacc, net_debt, shares,
                       exit_multiple=EXIT_MULTIPLE)
    last = gordon.rows[-1]
    final_ebitda = last.ebit + last.depreciation
    gordon_implied_multiple = implied_exit_multiple(
        gordon.pv_terminal * (1 + w.wacc) ** (len(gordon.rows) - 0.5), final_ebitda)
    exit_implied_growth = implied_terminal_growth(
        exitm.pv_terminal * (1 + w.wacc) ** (len(exitm.rows) - 0.5), last.fcff, w.wacc)

    # ---------------- scenarios ---------------------------------------------
    scenario_rows, weighted = [], 0.0
    for name, (dg, dm, tg, prob) in SCENARIOS.items():
        v = value_with(i["revenue"], base_nwc, drivers.scaled(dg, dm), w.wacc,
                       net_debt, shares, terminal_growth=tg)
        scenario_rows.append((name, v, prob, dg, dm, tg))
        weighted += prob * v.value_per_share

    # ---------------- sensitivity -------------------------------------------
    waccs = [round(w.wacc + d, 6) for d in (-0.010, -0.005, 0.0, 0.005, 0.010)]
    growths = [0.0125, 0.0175, 0.0225, 0.0275, 0.0325]
    grid = [[value_with(i["revenue"], base_nwc, drivers, ww, net_debt, shares,
                        terminal_growth=gg).value_per_share for gg in growths]
            for ww in waccs]

    margins = [0.099, 0.109, 0.119, 0.129]
    growth_shifts = [-0.02, -0.01, 0.0, 0.01, 0.02]
    grid2 = [[value_with(i["revenue"], base_nwc,
                         drivers.scaled(gs, mm - BASE_CASE["ebit_margin"][0]),
                         w.wacc, net_debt, shares,
                         terminal_growth=TERMINAL_GROWTH).value_per_share
              for gs in growth_shifts] for mm in margins]

    # ---------------- reverse DCF and Monte Carlo ---------------------------
    implied_growth = reverse_dcf_growth(price, i["revenue"], base_nwc, drivers,
                                        w.wacc, net_debt, shares, TERMINAL_GROWTH)
    mc = monte_carlo(i["revenue"], base_nwc, drivers, w.wacc, net_debt, shares,
                     TERMINAL_GROWTH, trials=20_000)
    p_above = sum(1 for v in mc if v > price) / len(mc)

    # ---------------- comparables -------------------------------------------
    comps = [build_comp_row(t, data[t]) for t in ("MRDN", "CALD", "VSSL")]
    peers = [r for r in comps if r.ticker != TICKER]
    subject = next(r for r in comps if r.ticker == TICKER)
    ebitda_mult, ebitda_dropped = screen(peers, "ev_ebitda")
    sales_mult, sales_dropped = screen(peers, "ev_sales")
    pe_mult, pe_dropped = screen(peers, "pe")
    med_ev_ebitda, med_ev_sales, med_pe = (median(ebitda_mult), median(sales_mult),
                                           median(pe_mult))
    dropped = sorted({t for lst in (ebitda_dropped, sales_dropped, pe_dropped) for t in lst})
    comp_values = {
        "EV/EBITDA": implied_value_per_share(med_ev_ebitda, i["ebitda"], net_debt, shares),
        "EV/Sales": implied_value_per_share(med_ev_sales, i["revenue"], net_debt, shares),
        "P/E": implied_value_per_share(med_pe, i["net_income"], net_debt, shares,
                                       equity_multiple=True),
    }

    write_outputs(dict(
        i=i, b=b, c=c, m=m, price=price, shares=shares, net_debt=net_debt,
        gross_debt=gross_debt, base_nwc=base_nwc, nwc_ratio=nwc_ratio,
        tax_rate=tax_rate, drivers=drivers, w=w, gordon=gordon, exitm=exitm,
        gordon_implied_multiple=gordon_implied_multiple,
        exit_implied_growth=exit_implied_growth, scenario_rows=scenario_rows,
        weighted=weighted, waccs=waccs, growths=growths, grid=grid,
        margins=margins, growth_shifts=growth_shifts, grid2=grid2,
        implied_growth=implied_growth, mc=mc, p_above=p_above, comps=comps,
        med_ev_ebitda=med_ev_ebitda, med_ev_sales=med_ev_sales, med_pe=med_pe,
        comp_values=comp_values, dropped=dropped,
        n_ebitda=len(ebitda_mult), n_sales=len(sales_mult), n_pe=len(pe_mult)))
    print(f"base case (Gordon)      {gordon.value_per_share:8.2f}")
    print(f"base case (exit mult.)  {exitm.value_per_share:8.2f}")
    print(f"probability weighted    {weighted:8.2f}")
    print(f"market price            {price:8.2f}   upside "
          f"{weighted / price - 1:+.1%}")
    print(f"WACC {w.wacc:.2%}  beta_L {w.levered_beta:.2f}  Ke {w.cost_of_equity:.2%}")
    print(f"reverse DCF implied growth {implied_growth:.2%}")
    print(f"P(value > price) = {p_above:.1%}")
    print(f"outputs written to {OUT}")


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def write_outputs(ns: dict) -> None:
    """Render every table and figure the write-up quotes."""
    g = ns["gordon"]; e = ns["exitm"]; w = ns["w"]; mc = ns["mc"]
    price = ns["price"]
    money = lambda v: f"{v:,.0f}"                                        # noqa: E731
    usd = lambda v: f"${v:,.2f}"                                         # noqa: E731

    parts = ["# MRDN valuation - generated output",
             "",
             "_Every figure below is produced by `python analysis.py`. "
             "Meridian Beverage Group is a fictional company; see `data/README.md`._",
             "", "## 1. Cost of capital", "",
             fl.markdown_table(
                 ["Input", "Value", "Source"],
                 [["Risk-free rate", fl.pct(RISK_FREE), "10-year government yield"],
                  ["Equity risk premium", fl.pct(EQUITY_RISK_PREMIUM), "mature-market implied ERP"],
                  ["Unlevered beta", f"{UNLEVERED_BETA:.2f}", "bottom-up, beverages"],
                  ["Levered beta", f"{w.levered_beta:.2f}", "Hamada at current D/E"],
                  ["Size premium", fl.pct(SIZE_PREMIUM), "mid-cap adjustment"],
                  ["Cost of equity", fl.pct(w.cost_of_equity), "CAPM"],
                  ["Pre-tax cost of debt", fl.pct(ns["i"]["interest_expense"] / ((ns["gross_debt"] + 1182.0) / 2)),
                   "FY24 interest expense / average debt"],
                  ["After-tax cost of debt", fl.pct(w.after_tax_cost_of_debt), f"at {fl.pct(ns['tax_rate'])} tax"],
                  ["Weight of equity / debt", f"{w.weight_equity:.1%} / {w.weight_debt:.1%}", "market values"],
                  ["**WACC**", f"**{fl.pct(w.wacc)}**", ""]]),
             "", "## 2. Free cash flow forecast (USD m)", ""]

    rows = [[str(r.year), money(r.revenue), fl.pct(r.ebit_margin, 1), money(r.ebit),
             money(r.nopat), money(r.depreciation), money(-r.capex),
             money(-r.change_in_nwc), money(r.fcff), f"{r.discount_factor:.3f}",
             money(r.present_value)] for r in g.rows]
    parts += [fl.markdown_table(
        ["FY", "Revenue", "EBIT %", "EBIT", "NOPAT", "D&A", "Capex", "ΔNWC", "FCFF",
         "DF", "PV"], rows), ""]

    parts += ["## 3. Value bridge", "",
              fl.markdown_table(
                  ["Component", "Gordon growth", "Exit multiple"],
                  [["PV of explicit forecast", money(g.pv_explicit), money(e.pv_explicit)],
                   ["PV of terminal value", money(g.pv_terminal), money(e.pv_terminal)],
                   ["Terminal share of EV", fl.pct(g.terminal_share_of_ev, 1),
                    fl.pct(e.terminal_share_of_ev, 1)],
                   ["Enterprise value", money(g.enterprise_value), money(e.enterprise_value)],
                   ["Less net debt", money(-g.net_debt), money(-e.net_debt)],
                   ["Equity value", money(g.equity_value), money(e.equity_value)],
                   ["Diluted shares (m)", f"{g.shares:,.1f}", f"{e.shares:,.1f}"],
                   ["**Value per share**", f"**{usd(g.value_per_share)}**",
                    f"**{usd(e.value_per_share)}**"],
                   ["Cross-check", f"implies {ns['gordon_implied_multiple']:.1f}x exit EBITDA",
                    f"implies {fl.pct(ns['exit_implied_growth'])} terminal growth"]]), ""]

    parts += ["## 4. Scenarios", "",
              fl.markdown_table(
                  ["Scenario", "Revenue growth shift", "EBIT margin shift", "Terminal g",
                   "Value / share", "vs price", "Probability"],
                  [[n, f"{dg:+.1%}", f"{dm:+.1%}", fl.pct(tg),
                    usd(v.value_per_share), f"{v.value_per_share / price - 1:+.1%}",
                    fl.pct(p, 0)] for n, v, p, dg, dm, tg in ns["scenario_rows"]]),
              "",
              f"Probability-weighted value **{usd(ns['weighted'])}** against a market price of "
              f"{usd(price)} ({ns['weighted'] / price - 1:+.1%}).", ""]

    parts += ["## 5. Sensitivity", "", "### Value per share: WACC x terminal growth", "",
              fl.markdown_table(
                  ["WACC \\ g"] + [fl.pct(x) for x in ns["growths"]],
                  [[fl.pct(ww)] + [usd(v) for v in row]
                   for ww, row in zip(ns["waccs"], ns["grid"])]), "",
              "### Value per share: FY25 EBIT margin x parallel growth shift", "",
              fl.markdown_table(
                  ["Margin \\ growth"] + [f"{x:+.1%}" for x in ns["growth_shifts"]],
                  [[fl.pct(mm)] + [usd(v) for v in row]
                   for mm, row in zip(ns["margins"], ns["grid2"])]), ""]

    parts += ["## 6. Reverse DCF", "",
              f"Holding the base-case margin path, working capital intensity and a "
              f"{fl.pct(TERMINAL_GROWTH)} terminal growth rate, the market price of "
              f"{usd(price)} is consistent with uniform revenue growth of "
              f"**{fl.pct(ns['implied_growth'])}** a year through FY29, against a base case "
              f"averaging {fl.pct(sum(BASE_CASE['revenue_growth']) / 5)}.", ""]

    parts += ["## 7. Monte Carlo (20,000 trials)", "",
              fl.markdown_table(
                  ["Statistic", "Value per share"],
                  [["5th percentile", usd(percentile(mc, 0.05))],
                   ["25th percentile", usd(percentile(mc, 0.25))],
                   ["Median", usd(percentile(mc, 0.50))],
                   ["75th percentile", usd(percentile(mc, 0.75))],
                   ["95th percentile", usd(percentile(mc, 0.95))],
                   ["Mean", usd(sum(mc) / len(mc))],
                   ["P(value > market price)", fl.pct(ns["p_above"], 1)]]), ""]

    parts += ["## 8. Trading comparables", "",
              fl.markdown_table(
                  ["Company", "Mkt cap", "EV", "EV/Sales", "EV/EBITDA", "EV/EBIT", "P/E",
                   "FCF yield", "Rev growth", "EBIT margin", "Net debt/EBITDA"],
                  [[f"{r.ticker} {r.name}", money(r.market_cap), money(r.enterprise_value),
                    f"{r.ev_sales:.2f}x",
                    f"{r.ev_ebitda:.1f}x" if r.ev_ebitda else "n/m",
                    f"{r.ev_ebit:.1f}x" if r.ev_ebit else "n/m",
                    f"{r.pe:.1f}x" if r.pe else "n/m",
                    fl.pct(r.fcf_yield, 1), fl.pct(r.revenue_growth, 1),
                    fl.pct(r.ebit_margin, 1),
                    f"{r.net_debt_ebitda:.1f}x" if r.net_debt_ebitda and r.net_debt_ebitda > 0 else "n/m"]
                   for r in ns["comps"]]),
              "",
              fl.markdown_table(
                  ["Peer median multiple", "Level", "Peers used", "Implied MRDN value / share"],
                  [["EV/EBITDA", f"{ns['med_ev_ebitda']:.1f}x", str(ns["n_ebitda"]),
                    usd(ns["comp_values"]["EV/EBITDA"])],
                   ["EV/Sales", f"{ns['med_ev_sales']:.2f}x", str(ns["n_sales"]),
                    usd(ns["comp_values"]["EV/Sales"])],
                   ["P/E", f"{ns['med_pe']:.1f}x", str(ns["n_pe"]),
                    usd(ns["comp_values"]["P/E"])]]),
              "",
              "Excluded as not meaningful (denominator too close to zero): "
              + (", ".join(ns["dropped"]) if ns["dropped"] else "none")
              + ". With only two peers, a median that survives one exclusion is a "
                "single observation wearing a statistic's clothes - the comps here are a "
                "sanity check on the DCF, not an independent valuation.", ""]

    with open(os.path.join(OUT, "results.md"), "w") as fh:
        fh.write("\n".join(parts))

    # ---------------- figures ------------------------------------------------
    fl.write_svg(os.path.join(OUT, "fcff_forecast.svg"), fl.bar_chart(
        [str(r.year) for r in g.rows] + ["TV (PV)"],
        [r.present_value for r in g.rows] + [g.pv_terminal],
        title="Present value of forecast cash flows, MRDN",
        subtitle=f"USD m, discounted at a {fl.pct(w.wacc)} WACC, mid-year convention. "
                 f"The terminal value is {fl.pct(g.terminal_share_of_ev, 0)} of enterprise value.",
        y_format=lambda v: f"{v:,.0f}"))

    field_rows = [
        ("DCF - Gordon growth",
         min(r[1].value_per_share for r in ns["scenario_rows"]),
         max(r[1].value_per_share for r in ns["scenario_rows"]),
         g.value_per_share),
        ("DCF - exit multiple 8.5-10.5x",
         value_with(ns["i"]["revenue"], ns["base_nwc"], ns["drivers"], w.wacc,
                    ns["net_debt"], ns["shares"], exit_multiple=8.5).value_per_share,
         value_with(ns["i"]["revenue"], ns["base_nwc"], ns["drivers"], w.wacc,
                    ns["net_debt"], ns["shares"], exit_multiple=10.5).value_per_share,
         e.value_per_share),
        ("Monte Carlo P5-P95", percentile(mc, 0.05), percentile(mc, 0.95),
         percentile(mc, 0.50)),
        ("Peer multiples", min(ns["comp_values"].values()),
         max(ns["comp_values"].values()), None),
        ("52-week range (fictional)", WEEK_52_RANGE[0], WEEK_52_RANGE[1], None),
    ]
    fl.write_svg(os.path.join(OUT, "football_field.svg"), fl.range_chart(
        field_rows, title="MRDN value per share by method",
        subtitle="Vertical rule marks each method's point estimate; dashed line is the market price.",
        reference=price, reference_label=f"market {usd(price)}",
        x_format=lambda v: f"${v:,.0f}", x_label="Value per share (USD)"))

    fl.write_svg(os.path.join(OUT, "monte_carlo.svg"), fl.histogram(
        mc, bins=48, title="Distribution of intrinsic value, 20,000 trials",
        subtitle="Parallel shifts to growth and margin, plus WACC and terminal-growth draws.",
        x_format=lambda v: f"${v:,.0f}",
        markers={f"market {usd(price)}": price,
                 f"median {usd(percentile(mc, 0.5))}": percentile(mc, 0.5)}))

    fl.write_svg(os.path.join(OUT, "sensitivity_heatmap.svg"), fl.heatmap(
        [fl.pct(x) for x in ns["growths"]], ns["grid"],
        title="Value per share: WACC (rows) x terminal growth (columns)",
        subtitle="Rows top to bottom: " + ", ".join(fl.pct(x) for x in ns["waccs"]),
        fmt=lambda v: f"{v:,.0f}", cell=62,
        vmin=min(min(r) for r in ns["grid"]), vmax=max(max(r) for r in ns["grid"]),
        low="#ffffff", mid="#c9dbea", high="#2f5d8a"))


if __name__ == "__main__":
    main()
