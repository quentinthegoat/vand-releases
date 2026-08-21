#!/usr/bin/env python3
"""Performance and risk attribution for a multi-asset portfolio, run end to end.

    python analysis.py

Reads data/prices_daily.csv, writes outputs/results.md and seven figures.
No arguments, no network, no third-party packages.
"""

from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

import finlib as fl                                          # noqa: E402
import portfolio as pf                                       # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "outputs")

# The portfolio under review: a globally diversified balanced mandate.
PORTFOLIO = {
    "LCAP": 0.35,   # US large-cap core
    "SCAP": 0.10,   # US small-cap
    "INTL": 0.12,   # developed ex-US
    "EMKT": 0.08,   # emerging markets
    "BNDX": 0.25,   # aggregate bonds
    "REIT": 0.06,   # listed real estate
    "GOLD": 0.04,   # gold
}

# The benchmark it is measured against: the classic 60/40.
BENCHMARK = {"LCAP": 0.60, "BNDX": 0.40}

REBALANCE = "quarterly"
COST_BPS = 5.0          # one-way trading cost charged on turnover


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    dates, prices = fl.read_price_csv(os.path.join(HERE, "data", "prices_daily.csv"))
    _, rf_annual = fl.read_series_csv(os.path.join(HERE, "data", "risk_free_daily.csv"))
    rf_daily = [r / fl.TRADING_DAYS for r in rf_annual[1:]]

    asset_returns = {t: fl.simple_returns(px) for t, px in prices.items()}
    tickers = list(PORTFOLIO)

    port = pf.backtest(dates, {t: asset_returns[t] for t in tickers}, PORTFOLIO,
                       REBALANCE, COST_BPS)
    bench = pf.backtest(dates, {t: asset_returns[t] for t in BENCHMARK}, BENCHMARK,
                        REBALANCE, COST_BPS)

    p_perf = pf.summarise(port.dates, port.returns, rf_daily, bench.returns)
    b_perf = pf.summarise(bench.dates, bench.returns, rf_daily)

    cov = fl.cov_matrix(asset_returns, tickers)
    ann_cov = [[c * fl.TRADING_DAYS for c in row] for row in cov]
    weights = [PORTFOLIO[t] for t in tickers]
    pcr = pf.risk_contributions(ann_cov, weights)
    dratio = pf.diversification_ratio(ann_cov, weights)
    contrib = pf.return_contributions({t: asset_returns[t] for t in tickers},
                                      port.weights_history)

    reb = {}
    for freq in ("monthly", "quarterly", "annual", "never"):
        r = pf.backtest(dates, {t: asset_returns[t] for t in tickers}, PORTFOLIO,
                        freq, COST_BPS)
        reb[freq] = (r, pf.summarise(r.dates, r.returns, rf_daily, bench.returns))

    write_report(dict(dates=dates, prices=prices, asset_returns=asset_returns,
                      tickers=tickers, port=port, bench=bench, p=p_perf, b=b_perf,
                      rf_daily=rf_daily, pcr=pcr, dratio=dratio, contrib=contrib,
                      reb=reb, ann_cov=ann_cov))

    print(f"portfolio  CAGR {fl.pct(p_perf.cagr)}  vol {fl.pct(p_perf.volatility)}  "
          f"Sharpe {p_perf.sharpe:.2f}  maxDD {fl.pct(p_perf.max_drawdown)}")
    print(f"benchmark  CAGR {fl.pct(b_perf.cagr)}  vol {fl.pct(b_perf.volatility)}  "
          f"Sharpe {b_perf.sharpe:.2f}  maxDD {fl.pct(b_perf.max_drawdown)}")
    print(f"beta {p_perf.beta:.2f}  alpha {fl.pct(p_perf.alpha_annual)}  "
          f"TE {fl.pct(p_perf.tracking_error)}  IR {p_perf.information_ratio:.2f}")
    print("risk contribution: " + ", ".join(
        f"{t} {fl.pct(c, 0)}" for t, c in zip(tickers, pcr)))
    print(f"outputs written to {OUT}")


def perf_rows(name: str, p: pf.Performance) -> list[list[str]]:
    return [[name, fl.pct(p.cagr), fl.pct(p.volatility), f"{p.sharpe:.2f}",
             f"{p.sortino:.2f}", fl.pct(p.max_drawdown), fl.pct(p.var_95),
             fl.pct(p.cvar_95), f"{p.skew:+.2f}", f"{p.excess_kurtosis:+.1f}",
             fl.pct(p.positive_days, 1)]]


def write_report(ns: dict) -> None:
    p, b, port, bench = ns["p"], ns["b"], ns["port"], ns["bench"]
    tickers, ar = ns["tickers"], ns["asset_returns"]
    rf = ns["rf_daily"]

    parts = ["# Portfolio performance and risk — generated output", "",
             "_Every figure below is produced by `python analysis.py`. The price history is "
             "simulated; see `data/README.md`._", "",
             "## 1. Mandate", "",
             fl.markdown_table(
                 ["Sleeve", "Portfolio weight", "Benchmark weight"],
                 [[t, fl.pct(PORTFOLIO[t], 0), fl.pct(BENCHMARK.get(t, 0.0), 0)]
                  for t in tickers]
                 + [["**Total**", fl.pct(sum(PORTFOLIO.values()), 0),
                     fl.pct(sum(BENCHMARK.values()), 0)]]),
             "",
             f"Rebalanced {REBALANCE}, with {COST_BPS:.0f}bp of one-way trading cost charged "
             f"on turnover. Period: {port.dates[0]} to {port.dates[-1]} "
             f"({len(port.returns) / fl.TRADING_DAYS:.1f} years, {len(port.returns):,} trading days).",
             "", "## 2. Headline performance", "",
             fl.markdown_table(
                 ["", "CAGR", "Volatility", "Sharpe", "Sortino", "Max DD", "VaR 95%",
                  "CVaR 95%", "Skew", "Excess kurtosis", "Positive days"],
                 perf_rows("Portfolio", p) + perf_rows("Benchmark 60/40", b)
                 + [[t, fl.pct(fl.annualised_return(ar[t])),
                     fl.pct(fl.annualised_vol(ar[t])),
                     f"{fl.sharpe(ar[t], rf):.2f}",
                     f"{fl.sortino(ar[t], rf):.2f}",
                     fl.pct(fl.max_drawdown(fl.cumulative(ar[t]))[0]),
                     fl.pct(fl.historical_var(ar[t])), fl.pct(fl.historical_cvar(ar[t])),
                     f"{fl.skewness(ar[t]):+.2f}", f"{fl.excess_kurtosis(ar[t]):+.1f}",
                     fl.pct(sum(1 for x in ar[t] if x > 0) / len(ar[t]), 1)]
                    for t in tickers]),
             "", "## 3. Versus the benchmark", "",
             fl.markdown_table(
                 ["Measure", "Value", "Reading"],
                 [["Beta", f"{p.beta:.2f}", "sensitivity to benchmark excess returns"],
                  ["Annualised alpha", fl.pct(p.alpha_annual),
                   "CAPM intercept against the 60/40"],
                  ["R-squared", f"{p.r_squared:.3f}", "share of variance explained"],
                  ["Tracking error", fl.pct(p.tracking_error), "volatility of the difference"],
                  ["Information ratio", f"{p.information_ratio:.2f}",
                   "active return per unit of tracking error"],
                  ["Up capture", fl.pct(p.up_capture, 0), "of benchmark gains captured"],
                  ["Down capture", fl.pct(p.down_capture, 0), "of benchmark losses taken"]],
                 align=["left", "right", "left"]),
             ""]

    # ---- drawdown ---------------------------------------------------------
    parts += ["## 4. Drawdown", "",
              fl.markdown_table(
                  ["", "Worst drawdown", "Peak", "Trough", "Recovered", "Length (trading days)"],
                  [["Portfolio", fl.pct(p.max_drawdown), str(p.drawdown_peak),
                    str(p.drawdown_trough),
                    str(p.drawdown_recovery) if p.drawdown_recovery else "not recovered",
                    f"{p.drawdown_length_days:,}"],
                   ["Benchmark", fl.pct(b.max_drawdown), str(b.drawdown_peak),
                    str(b.drawdown_trough),
                    str(b.drawdown_recovery) if b.drawdown_recovery else "not recovered",
                    f"{b.drawdown_length_days:,}"]]), ""]

    # ---- calendar years ---------------------------------------------------
    cal_p = pf.calendar_year_returns(port.dates, port.returns)
    cal_b = pf.calendar_year_returns(bench.dates, bench.returns)
    years = sorted(cal_p)
    parts += ["## 5. Calendar year returns", "",
              fl.markdown_table(
                  ["Year"] + [str(y) for y in years],
                  [["Portfolio"] + [fl.pct(cal_p[y], 1) for y in years],
                   ["Benchmark"] + [fl.pct(cal_b[y], 1) for y in years],
                   ["Difference"] + [f"{(cal_p[y] - cal_b[y]) * 100:+.1f}pp" for y in years]]), ""]

    # ---- attribution ------------------------------------------------------
    total = sum(ns["contrib"].values())
    parts += ["## 6. Attribution: where the return came from, and where the risk is", "",
              fl.markdown_table(
                  ["Sleeve", "Weight", "Asset CAGR", "Contribution to total return",
                   "Share of return", "Share of portfolio risk", "Risk ÷ weight"],
                  [[t, fl.pct(PORTFOLIO[t], 0), fl.pct(fl.annualised_return(ar[t])),
                    fl.pct(ns["contrib"][t]), fl.pct(ns["contrib"][t] / total, 0),
                    fl.pct(ns["pcr"][k], 0),
                    f"{ns['pcr'][k] / PORTFOLIO[t]:.2f}x"]
                   for k, t in enumerate(tickers)]),
              "",
              f"Diversification ratio: **{ns['dratio']:.2f}** "
              f"(weighted average sleeve volatility ÷ portfolio volatility; 1.00 means "
              f"diversification bought nothing).", ""]

    # ---- rebalancing ------------------------------------------------------
    parts += ["## 7. Does rebalancing pay?", "",
              fl.markdown_table(
                  ["Policy", "CAGR", "Volatility", "Sharpe", "Max DD", "Rebalances",
                   "Total turnover", "Cost drag p.a."],
                  [[freq, fl.pct(s.cagr), fl.pct(s.volatility), f"{s.sharpe:.2f}",
                    fl.pct(s.max_drawdown), f"{r.rebalance_count:,}",
                    f"{r.total_turnover:.2f}x", fl.pct(r.cost_drag_annual, 3)]
                   for freq, (r, s) in ns["reb"].items()]), ""]

    # ---- correlations -----------------------------------------------------
    corr = fl.corr_matrix(ar, tickers)
    parts += ["## 8. Correlation matrix (daily returns, full period)", "",
              fl.markdown_table(
                  ["", *tickers],
                  [[tickers[i]] + [f"{corr[i][j]:.2f}" for j in range(len(tickers))]
                   for i in range(len(tickers))]), ""]

    with open(os.path.join(OUT, "results.md"), "w") as fh:
        fh.write("\n".join(parts))

    write_figures(ns, corr, cal_p, cal_b, years)


def write_figures(ns, corr, cal_p, cal_b, years) -> None:
    port, bench, tickers, ar = ns["port"], ns["bench"], ns["tickers"], ns["asset_returns"]
    labels = [d.strftime("%Y-%m") for d in port.dates]

    eq_p = fl.cumulative(port.returns, 100.0)[1:]
    eq_b = fl.cumulative(bench.returns, 100.0)[1:]
    fl.write_svg(os.path.join(OUT, "equity_curve.svg"), fl.line_chart(
        {"Portfolio": eq_p, "Benchmark 60/40": eq_b}, labels,
        title="Growth of 100, portfolio versus 60/40 benchmark",
        subtitle="Simulated price history, quarterly rebalancing, 5bp one-way costs.",
        y_format=lambda v: f"{v:,.0f}"))

    fl.write_svg(os.path.join(OUT, "drawdown.svg"), fl.line_chart(
        {"Portfolio": fl.drawdown_series(fl.cumulative(port.returns))[1:],
         "Benchmark 60/40": fl.drawdown_series(fl.cumulative(bench.returns))[1:]},
        labels, title="Drawdown from prior peak",
        subtitle="Depth is only half the story: the recovery date is in section 4 of results.md.",
        y_format=lambda v: f"{v:.0%}", zero_line=True, fill_first=True))

    fl.write_svg(os.path.join(OUT, "calendar_returns.svg"), fl.bar_chart(
        [str(y) for y in years], [cal_p[y] for y in years],
        title="Portfolio calendar-year returns",
        subtitle="Two negative years in ten, and one of them cost 21%.",
        y_format=lambda v: f"{v:.0%}", colour_by_sign=True))

    win = 252
    fl.write_svg(os.path.join(OUT, "rolling_volatility.svg"), fl.line_chart(
        {"Portfolio": [v * math.sqrt(fl.TRADING_DAYS) if v is not None else None
                       for v in fl.rolling(port.returns, win, fl.stdev)],
         "Benchmark 60/40": [v * math.sqrt(fl.TRADING_DAYS) if v is not None else None
                             for v in fl.rolling(bench.returns, win, fl.stdev)]},
        labels, title="Rolling 12-month annualised volatility",
        subtitle="Realised risk is not a constant, which is why a single full-period "
                 "volatility number understates what an investor lived through.",
        y_format=lambda v: f"{v:.0%}"))

    fl.write_svg(os.path.join(OUT, "risk_vs_weight.svg"), fl.bar_chart(
        [f"{t}" for t in tickers],
        [ns["pcr"][k] - PORTFOLIO[t] for k, t in enumerate(tickers)],
        title="Share of risk minus share of capital",
        subtitle="Positive means the sleeve consumes more risk budget than capital budget. "
                 "This is the gap a weights table cannot show you.",
        y_format=lambda v: f"{v:+.0%}", colour_by_sign=True))

    fl.write_svg(os.path.join(OUT, "correlation.svg"), fl.heatmap(
        tickers, corr, title="Correlation of daily returns",
        subtitle="Full period. Gold is the only sleeve with a genuinely low equity correlation.",
        fmt=lambda v: f"{v:.2f}"))

    fl.write_svg(os.path.join(OUT, "contribution.svg"), fl.bar_chart(
        tickers, [ns["contrib"][t] for t in tickers],
        title="Contribution to the portfolio's total return",
        subtitle="Accumulated on actual drifting weights, so the bars sum to the "
                 "portfolio's total return.",
        y_format=lambda v: f"{v:.0%}", colour_by_sign=True))


if __name__ == "__main__":
    main()
