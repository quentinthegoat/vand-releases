#!/usr/bin/env python3
"""Financial statement analysis of three beverage companies, run end to end.

    python analysis.py

Reads data/financials.json, writes outputs/results.md and six figures.
No arguments, no network, no third-party packages.
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

import finlib as fl                                              # noqa: E402
from ratios import (cagr, common_size_income, compute_history,   # noqa: E402
                    dupont_five, growth_rates)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "outputs")
TICKERS = ("MRDN", "CALD", "VSSL")
FOCUS = "MRDN"


def fmt(v, kind="pct", dp=1):
    if v is None:
        return "n/m"
    if kind == "pct":
        return fl.pct(v, dp)
    if kind == "x":
        return f"{v:.2f}x"
    if kind == "days":
        return f"{v:.0f}"
    return f"{v:,.{dp}f}"


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(HERE, "data", "financials.json")) as fh:
        data = json.load(fh)

    hist = {t: compute_history(data[t]) for t in TICKERS}
    years = [y["year"] for y in data[FOCUS]["years"]]
    parts = ["# Financial statement analysis — generated output", "",
             "_Every figure below is produced by `python analysis.py`. MRDN, CALD and VSSL "
             "are fictional companies; see `data/README.md`._", ""]

    # ---------------- 1. growth and scale -----------------------------------
    parts += ["## 1. Growth and scale", "",
              fl.markdown_table(
                  ["Company", "FY19 revenue", "FY24 revenue", "Revenue CAGR",
                   "FY24 EBIT margin", "FY19 EBIT margin", "FY24 EPS", "EPS CAGR"],
                  [[f"{t} {data[t]['name']}",
                    f"{data[t]['years'][0]['income_statement']['revenue']:,.0f}",
                    f"{data[t]['years'][-1]['income_statement']['revenue']:,.0f}",
                    fmt(cagr(data[t], "revenue")),
                    fmt(hist[t][-1].ebit_margin), fmt(hist[t][0].ebit_margin),
                    f"{data[t]['years'][-1]['income_statement']['eps']:.2f}",
                    fmt(cagr(data[t], "eps"))] for t in TICKERS]), ""]

    # ---------------- 2. common-size ----------------------------------------
    cs = common_size_income(data[FOCUS])
    parts += ["## 2. Common-size income statement — " + FOCUS, "",
              "Every line as a share of revenue. Reading across a row shows what moved; "
              "reading down a column shows how a dollar of sales was consumed.", "",
              fl.markdown_table(
                  ["% of revenue"] + [str(r["year"]) for r in cs],
                  [[label] + [fl.pct(r[key], 1) for r in cs] for label, key in [
                      ("Cost of goods sold", "cogs"),
                      ("**Gross profit**", "gross_profit"),
                      ("SG&A", "sga"),
                      ("R&D", "research_development"),
                      ("D&A", "depreciation_amortisation"),
                      ("**EBIT**", "ebit"),
                      ("Net interest", "net_interest"),
                      ("Tax", "tax"),
                      ("**Net income**", "net_income")]]), ""]

    # ---------------- 3. ratio suite ----------------------------------------
    for t in TICKERS:
        rows = hist[t]
        parts += [f"## 3.{TICKERS.index(t) + 1} Ratio suite — {t} {data[t]['name']}", "",
                  fl.markdown_table(
                      ["Ratio"] + [str(r.year) for r in rows],
                      [["Gross margin"] + [fmt(r.gross_margin) for r in rows],
                       ["EBITDA margin"] + [fmt(r.ebitda_margin) for r in rows],
                       ["EBIT margin"] + [fmt(r.ebit_margin) for r in rows],
                       ["Net margin"] + [fmt(r.net_margin) for r in rows],
                       ["ROE"] + [fmt(r.roe) for r in rows],
                       ["ROA"] + [fmt(r.roa) for r in rows],
                       ["ROIC"] + [fmt(r.roic) for r in rows],
                       ["Asset turnover"] + [fmt(r.asset_turnover, "x") for r in rows],
                       ["DSO (days)"] + [fmt(r.dso, "days") for r in rows],
                       ["DIO (days)"] + [fmt(r.dio, "days") for r in rows],
                       ["DPO (days)"] + [fmt(r.dpo, "days") for r in rows],
                       ["Cash conversion cycle"] + [fmt(r.cash_conversion_cycle, "days") for r in rows],
                       ["Current ratio"] + [fmt(r.current_ratio, "x") for r in rows],
                       ["Quick ratio"] + [fmt(r.quick_ratio, "x") for r in rows],
                       ["Interest coverage"] + [fmt(r.interest_coverage, "x") for r in rows],
                       ["Net debt / EBITDA"] + [fmt(r.net_debt_ebitda, "x") for r in rows],
                       ["Debt / equity"] + [fmt(r.debt_to_equity, "x") for r in rows],
                       ["CFO / EBITDA"] + [fmt(r.cfo_to_ebitda) for r in rows],
                       ["FCF / net income"] + [fmt(r.fcf_conversion) for r in rows],
                       ["Accrual ratio"] + [fmt(r.accrual_ratio) for r in rows],
                       ["Capex / D&A"] + [fmt(r.capex_to_depreciation, "x") for r in rows],
                       ["Altman Z"] + [fmt(r.altman_z, "n", 2) for r in rows],
                       ["Payout ratio"] + [fmt(r.payout_ratio) for r in rows],
                       ["Sustainable growth"] + [fmt(r.sustainable_growth) for r in rows]]), ""]

    # ---------------- 4. DuPont ---------------------------------------------
    parts += ["## 4. Five-step DuPont decomposition", "",
              "ROE = tax burden × interest burden × EBIT margin × asset turnover × leverage", ""]
    for t in TICKERS:
        rows = []
        for k, y in enumerate(data[t]["years"]):
            d = dupont_five(y, data[t]["years"][k - 1] if k else None)
            rows.append([str(y["year"]), fmt(d["tax_burden"], "x"),
                         fmt(d["interest_burden"], "x"), fmt(d["ebit_margin"]),
                         fmt(d["asset_turnover"], "x"), fmt(d["leverage"], "x"),
                         fmt(d["roe"]), fmt(d["reported_roe"])])
        parts += [f"**{t}**", "",
                  fl.markdown_table(
                      ["FY", "Tax burden", "Interest burden", "EBIT margin",
                       "Asset turnover", "Leverage", "DuPont ROE", "Reported ROE"], rows), ""]

    # ---------------- 5. leverage forensics ---------------------------------
    parts += ["## 5. Where the debt actually sits — " + FOCUS, "",
              "Headline term debt and total drawn debt are not the same story.", "",
              fl.markdown_table(
                  ["FY", "Term debt", "Revolver", "Total debt", "Cash", "Net debt",
                   "Net debt / EBITDA", "FCF", "Dividends + buybacks"],
                  [[str(y["year"]),
                    f"{y['balance_sheet']['debt_st'] + y['balance_sheet']['debt_lt']:,.0f}",
                    f"{y['balance_sheet']['revolver']:,.0f}",
                    f"{y['balance_sheet']['debt_st'] + y['balance_sheet']['debt_lt'] + y['balance_sheet']['revolver']:,.0f}",
                    f"{y['balance_sheet']['cash']:,.0f}",
                    f"{y['market']['net_debt']:,.0f}",
                    fmt(hist[FOCUS][k].net_debt_ebitda, "x"),
                    f"{y['cash_flow']['free_cash_flow']:,.0f}",
                    f"{-(y['cash_flow']['dividends'] + y['cash_flow']['buybacks']):,.0f}"]
                   for k, y in enumerate(data[FOCUS]["years"])]), ""]

    with open(os.path.join(OUT, "results.md"), "w") as fh:
        fh.write("\n".join(parts))

    write_figures(data, hist, years)

    print("Revenue CAGR FY19-24: " + ", ".join(
        f"{t} {fmt(cagr(data[t], 'revenue'))}" for t in TICKERS))
    print("FY24 ROIC:            " + ", ".join(
        f"{t} {fmt(hist[t][-1].roic)}" for t in TICKERS))
    print("FY24 Altman Z:        " + ", ".join(
        f"{t} {hist[t][-1].altman_z:.2f}" for t in TICKERS))
    print("FY24 CCC (days):      " + ", ".join(
        f"{t} {hist[t][-1].cash_conversion_cycle:.0f}" for t in TICKERS))
    print(f"outputs written to {OUT}")


def write_figures(data, hist, years) -> None:
    labels = [str(y) for y in years]

    fl.write_svg(os.path.join(OUT, "margins.svg"), fl.line_chart(
        {t: [r.ebit_margin for r in hist[t]] for t in TICKERS}, labels,
        title="EBIT margin, FY2019–FY2024",
        subtitle="The FY2022 input-cost spike hit all three; only Calder absorbed it without "
                 "losing half its margin.",
        y_format=lambda v: f"{v:.0%}", zero_line=True, x_tick_every=1))

    fl.write_svg(os.path.join(OUT, "roic_vs_wacc.svg"), fl.line_chart(
        dict({t: [r.roic if r.roic is not None else None for r in hist[t]] for t in TICKERS},
             **{"WACC ≈ 8%": [0.08] * len(years)}), labels,
        title="Return on invested capital versus cost of capital",
        subtitle="Value is created only above the horizontal line. NOPAT over average "
                 "invested capital, excess cash excluded.",
        y_format=lambda v: f"{v:.0%}", zero_line=True, x_tick_every=1))

    fl.write_svg(os.path.join(OUT, "cash_conversion_cycle.svg"), fl.line_chart(
        {t: [r.cash_conversion_cycle for r in hist[t]] for t in TICKERS}, labels,
        title="Cash conversion cycle (days)",
        subtitle="DSO + DIO − DPO. Rising means the business is funding its own growth "
                 "out of working capital.",
        y_format=lambda v: f"{v:.0f}", x_tick_every=1))

    fl.write_svg(os.path.join(OUT, "earnings_quality.svg"), fl.line_chart(
        {t: [r.fcf_conversion if r.fcf_conversion is not None else None for r in hist[t]]
         for t in TICKERS}, labels,
        title="Free cash flow as a multiple of reported net income",
        subtitle="Below 1.0x for years on end means reported profit is not turning into cash.",
        y_format=lambda v: f"{v:.1f}x", zero_line=True, x_tick_every=1))

    mrdn = data["MRDN"]["years"]
    fl.write_svg(os.path.join(OUT, "mrdn_leverage.svg"), fl.stacked_area(
        {"Term debt": [(y["balance_sheet"]["debt_st"] + y["balance_sheet"]["debt_lt"]) / 1400
                       for y in mrdn],
         "Revolver": [y["balance_sheet"]["revolver"] / 1400 for y in mrdn]},
        labels, title="MRDN debt mix — the revolver is doing the work",
        subtitle="Scaled to $1.4bn. Term debt falls every year after FY2022; total drawn debt "
                 "falls far less.",
        y_format=lambda v: f"{v * 1400:,.0f}"))

    fl.write_svg(os.path.join(OUT, "altman_z.svg"), fl.bar_chart(
        [f"{t} FY{y}" for t in TICKERS for y in (2022, 2024)],
        [hist[t][years.index(y)].altman_z for t in TICKERS for y in (2022, 2024)],
        title="Altman Z-score: FY2022 trough versus FY2024",
        subtitle="Below 1.81 is the distress zone; above 2.99 is the safe zone.",
        y_format=lambda v: f"{v:.1f}", colour_by_sign=False))


if __name__ == "__main__":
    main()
