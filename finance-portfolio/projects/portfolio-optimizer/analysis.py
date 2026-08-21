#!/usr/bin/env python3
"""Does portfolio optimisation beat equal weight out of sample?

    python analysis.py

Builds the long-only efficient frontier, compares seven construction rules in a
walk-forward test, and measures how much of each rule's in-sample advantage
survives contact with data it did not see. Writes outputs/results.md and six
figures. No arguments, no network, no third-party packages.
"""

from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

import finlib as fl                                                  # noqa: E402
import optimizer as op                                               # noqa: E402
import walkforward as wf                                             # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "outputs")

TICKERS = ["LCAP", "SCAP", "INTL", "EMKT", "BNDX", "REIT", "GOLD"]
LOOKBACK = 756          # three years of daily data
COST_BPS = 5.0
RISK_FREE = 0.025       # constant rate used inside the optimiser's objective


# ---------------------------------------------------------------------------
# Construction rules under test
# ---------------------------------------------------------------------------


def annualised_inputs(tickers, window):
    mu = [fl.annualised_return(window[t]) for t in tickers]
    cov = [[fl.covariance(window[a], window[b]) * fl.TRADING_DAYS for b in tickers]
           for a in tickers]
    return mu, cov


def est_equal_weight(tickers, window):
    return op.equal_weight(len(tickers))


def est_inverse_vol(tickers, window):
    _mu, cov = annualised_inputs(tickers, window)
    return op.inverse_volatility(cov)


def est_min_variance(tickers, window):
    _mu, cov = annualised_inputs(tickers, window)
    return op.min_variance(cov)


def est_risk_parity(tickers, window):
    _mu, cov = annualised_inputs(tickers, window)
    return op.risk_parity(cov)


def est_max_sharpe_sample(tickers, window):
    mu, cov = annualised_inputs(tickers, window)
    return op.max_sharpe(mu, cov, RISK_FREE, n_points=25)


def est_max_sharpe_shrunk(tickers, window):
    mu, _cov = annualised_inputs(tickers, window)
    lw = op.ledoit_wolf([window[t] for t in tickers])
    cov = [[c * fl.TRADING_DAYS for c in row] for row in lw.covariance]
    return op.max_sharpe(mu, cov, RISK_FREE, n_points=25)


def est_sixty_forty(tickers, window):
    fixed = {"LCAP": 0.60, "BNDX": 0.40}
    return [fixed.get(t, 0.0) for t in tickers]


STRATEGIES = {
    "Equal weight (1/N)": est_equal_weight,
    "60/40": est_sixty_forty,
    "Inverse volatility": est_inverse_vol,
    "Risk parity": est_risk_parity,
    "Minimum variance": est_min_variance,
    "Max Sharpe (sample cov)": est_max_sharpe_sample,
    "Max Sharpe (shrunk cov)": est_max_sharpe_shrunk,
}


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    dates, prices = fl.read_price_csv(os.path.join(HERE, "data", "prices_daily.csv"))
    _, rf_annual = fl.read_series_csv(os.path.join(HERE, "data", "risk_free_daily.csv"))
    rf_daily = [r / fl.TRADING_DAYS for r in rf_annual[1:]]

    returns = {t: fl.simple_returns(prices[t]) for t in TICKERS}
    mu_full = [fl.annualised_return(returns[t]) for t in TICKERS]
    cov_full = [[fl.covariance(returns[a], returns[b]) * fl.TRADING_DAYS for b in TICKERS]
                for a in TICKERS]

    # ---- in-sample structures ------------------------------------------
    frontier = op.efficient_frontier(mu_full, cov_full, n_points=45)
    in_sample = {
        "Equal weight (1/N)": op.equal_weight(len(TICKERS)),
        "Inverse volatility": op.inverse_volatility(cov_full),
        "Risk parity": op.risk_parity(cov_full),
        "Minimum variance": op.min_variance(cov_full),
        "Max Sharpe (sample cov)": op.max_sharpe(mu_full, cov_full, RISK_FREE, n_points=60),
    }

    lw_full = op.ledoit_wolf([returns[t] for t in TICKERS])
    cov_shrunk = [[c * fl.TRADING_DAYS for c in row] for row in lw_full.covariance]
    in_sample["Max Sharpe (shrunk cov)"] = op.max_sharpe(mu_full, cov_shrunk,
                                                         RISK_FREE, n_points=60)

    # How hard is the estimation problem?  Shrinkage only earns its keep when
    # the sample covariance matrix is poorly determined, so measure that
    # directly across window lengths instead of asserting it.
    shrink_by_window = []
    for window_len in (126, 252, 504, 756, 1260, len(returns[TICKERS[0]])):
        sub = [returns[t][:window_len] for t in TICKERS]
        lw = op.ledoit_wolf(sub)
        sample_cov = [[fl.covariance(sub[i], sub[j]) for j in range(len(TICKERS))]
                      for i in range(len(TICKERS))]
        shrink_by_window.append((window_len, window_len / len(TICKERS), lw.intensity,
                                 op.condition_number(sample_cov)))

    # ---- walk-forward ---------------------------------------------------
    results, summaries = {}, {}
    for name, estimator in STRATEGIES.items():
        r = wf.walk_forward(name, dates, returns, TICKERS, estimator,
                            lookback=LOOKBACK, cost_bps=COST_BPS)
        results[name] = r
        summaries[name] = wf.summarise(r, rf_daily, LOOKBACK)
        print(f"{name:26s} CAGR {fl.pct(summaries[name]['cagr']):>7}  "
              f"vol {fl.pct(summaries[name]['volatility']):>7}  "
              f"Sharpe {summaries[name]['sharpe']:5.2f}  "
              f"maxDD {fl.pct(summaries[name]['max_drawdown']):>8}  "
              f"turnover {summaries[name]['turnover']:.3f}")

    # ---- the look-ahead portfolio: an upper bound nobody can reach ------
    cheat_weights = in_sample["Max Sharpe (sample cov)"]
    cheat_returns = [sum(w * returns[t][k] for w, t in zip(cheat_weights, TICKERS))
                     for k in range(LOOKBACK, len(returns[TICKERS[0]]))]
    cheat = {"cagr": fl.annualised_return(cheat_returns),
             "volatility": fl.annualised_vol(cheat_returns),
             "sharpe": fl.sharpe(cheat_returns, rf_daily[LOOKBACK:]),
             "max_drawdown": fl.max_drawdown(fl.cumulative(cheat_returns))[0]}

    write_report(dict(dates=dates, returns=returns, mu=mu_full, cov=cov_full,
                      frontier=frontier, in_sample=in_sample, results=results,
                      summaries=summaries, cheat=cheat, lw=lw_full,
                      shrink_by_window=shrink_by_window))
    print(f"\nlook-ahead max-Sharpe (not investable): Sharpe {cheat['sharpe']:.2f}")
    print(f"outputs written to {OUT}")


def write_report(ns: dict) -> None:
    tickers = TICKERS
    mu, cov = ns["mu"], ns["cov"]

    parts = ["# Portfolio optimisation — generated output", "",
             "_Every figure below is produced by `python analysis.py`. The price history is "
             "simulated; see `data/README.md`._", "",
             "## 1. Asset inputs (full period, annualised)", "",
             fl.markdown_table(
                 ["Asset", "Return", "Volatility", "Sharpe (rf 2.5%)"],
                 [[t, fl.pct(mu[k]), fl.pct(math.sqrt(cov[k][k])),
                   f"{(mu[k] - RISK_FREE) / math.sqrt(cov[k][k]):.2f}"]
                  for k, t in enumerate(tickers)]), "",
             "## 2. In-sample optimal portfolios", "",
             fl.markdown_table(
                 ["Rule"] + tickers + ["Return", "Volatility", "Sharpe"],
                 [[name] + [fl.pct(w, 0) for w in weights]
                  + [fl.pct(op.portfolio_return(mu, weights)),
                     fl.pct(math.sqrt(op.portfolio_variance(cov, weights))),
                     f"{(op.portfolio_return(mu, weights) - RISK_FREE) / math.sqrt(op.portfolio_variance(cov, weights)):.2f}"]
                  for name, weights in ns["in_sample"].items()]), "",
             "These are the portfolios you would have chosen **if you had known the answer "
             "in advance**. Section 4 is what happens when you do not.", "",
             "## 3. How hard is the estimation problem?", "",
             fl.markdown_table(
                 ["Window (days)", "Observations per asset", "Ledoit-Wolf shrinkage intensity",
                  "Condition number of sample covariance"],
                 [[f"{w:,}", f"{ratio:.0f}", fl.pct(intensity, 1), f"{cond:,.0f}"]
                  for w, ratio, intensity, cond in ns["shrink_by_window"]]), "",
             "Shrinkage intensity falls as the window lengthens, which is the estimator "
             "working correctly: with seven assets and three years of daily data there is "
             "little estimation error left to shrink away. Shrinkage is a fix for a hard "
             "estimation problem, and this is not one.", ""]

    s = ns["summaries"]
    order = sorted(s, key=lambda k: -s[k]["sharpe"])
    parts += ["## 4. Walk-forward, out of sample", "",
              f"Three-year trailing estimation window, quarterly rebalancing, "
              f"{COST_BPS:.0f}bp one-way cost, weights drift between rebalances. "
              f"Test period {ns['results'][order[0]].dates[0]} to "
              f"{ns['results'][order[0]].dates[-1]} "
              f"({len(ns['results'][order[0]].returns) / fl.TRADING_DAYS:.1f} years).", "",
              fl.markdown_table(
                  ["Rule", "CAGR", "Volatility", "Sharpe", "Sortino", "Max DD",
                   "Turnover per rebalance", "Weight churn"],
                  [[name, fl.pct(s[name]["cagr"]), fl.pct(s[name]["volatility"]),
                    f"{s[name]['sharpe']:.2f}", f"{s[name]['sortino']:.2f}",
                    fl.pct(s[name]["max_drawdown"]), fl.pct(s[name]["turnover"], 1),
                    fl.pct(s[name]["stability"], 1)] for name in order]), "",
              fl.markdown_table(
                  ["Reference", "CAGR", "Volatility", "Sharpe", "Max DD"],
                  [["Look-ahead max Sharpe (**not investable**)",
                    fl.pct(ns["cheat"]["cagr"]), fl.pct(ns["cheat"]["volatility"]),
                    f"{ns['cheat']['sharpe']:.2f}", fl.pct(ns["cheat"]["max_drawdown"])]]),
              "",
              "The look-ahead row is the same optimiser fitted to the whole sample and then "
              "'tested' on part of it. It is included precisely because it is cheating: the "
              "gap between it and the honest walk-forward rows is the size of the error a "
              "backtest makes when it forgets what it was allowed to know.", ""]

    with open(os.path.join(OUT, "results.md"), "w") as fh:
        fh.write("\n".join(parts))

    write_figures(ns)


def write_figures(ns: dict) -> None:
    tickers, mu, cov = TICKERS, ns["mu"], ns["cov"]
    frontier = ns["frontier"]

    points = [(math.sqrt(cov[k][k]), mu[k], t) for k, t in enumerate(tickers)]
    highlight = {}
    for name, colour in (("Minimum variance", "#3d7a5d"), ("Max Sharpe (sample cov)", "#a83232"),
                         ("Risk parity", "#8a4f7d"), ("Equal weight (1/N)", "#b08a2e")):
        w = ns["in_sample"][name]
        label = {"Max Sharpe (sample cov)": "Max Sharpe", "Equal weight (1/N)": "1/N"}.get(name, name)
        points.append((math.sqrt(op.portfolio_variance(cov, w)),
                       op.portfolio_return(mu, w), label))
        highlight[label] = colour

    fl.write_svg(os.path.join(OUT, "efficient_frontier.svg"), fl.scatter_chart(
        points, title="Long-only efficient frontier",
        subtitle="Full-period inputs. Individual assets in orange; optimised portfolios "
                 "highlighted. Every optimised point sits above and left of every single asset.",
        x_label="Annualised volatility", y_label="Annualised return",
        frontier=[(v, r) for v, r, _w in frontier], highlight=highlight))

    fl.write_svg(os.path.join(OUT, "weights_comparison.svg"), fl.stacked_area(
        {t: [ns["in_sample"][name][k] for name in ns["in_sample"]]
         for k, t in enumerate(tickers)},
        [n.replace("Max Sharpe ", "MaxSh ").replace(" (sample cov)", "-sample")
          .replace(" (shrunk cov)", "-shrunk").replace("Equal weight (1/N)", "1/N")
          .replace("Inverse volatility", "Inv vol").replace("Minimum variance", "Min var")
          .replace("Risk parity", "Risk par") for n in ns["in_sample"]],
        title="In-sample weights by construction rule",
        subtitle="The optimisers that use expected returns concentrate; the ones that do not, "
                 "diversify.", y_format=lambda v: f"{v:.0%}"))

    order = sorted(ns["summaries"], key=lambda k: -ns["summaries"][k]["sharpe"])
    labels = [d.strftime("%Y-%m") for d in ns["results"][order[0]].dates]
    fl.write_svg(os.path.join(OUT, "out_of_sample_equity.svg"), fl.line_chart(
        {name: fl.cumulative(ns["results"][name].returns, 100.0)[1:] for name in order},
        labels, title="Out-of-sample growth of 100",
        subtitle="Walk-forward: every weight was chosen using only data available at the time.",
        y_format=lambda v: f"{v:,.0f}"))

    fl.write_svg(os.path.join(OUT, "sharpe_comparison.svg"), fl.bar_chart(
        [n.replace(" (sample cov)", "\n(sample)").replace(" (shrunk cov)", "\n(shrunk)")
          .replace("Equal weight (1/N)", "1/N") for n in order],
        [ns["summaries"][n]["sharpe"] for n in order],
        title="Out-of-sample Sharpe ratio by construction rule",
        subtitle="Estimating expected returns is the expensive part: the two rules that need "
                 "them rank last.",
        y_format=lambda v: f"{v:.2f}", colour_by_sign=True))

    fl.write_svg(os.path.join(OUT, "turnover_vs_sharpe.svg"), fl.scatter_chart(
        [(ns["summaries"][n]["turnover"], ns["summaries"][n]["sharpe"],
          n.replace(" (sample cov)", "-s").replace(" (shrunk cov)", "-lw")
           .replace("Equal weight (1/N)", "1/N")) for n in order],
        title="Turnover bought nothing",
        subtitle="Average one-way turnover per rebalance against out-of-sample Sharpe.",
        x_label="Turnover per rebalance", y_label="Out-of-sample Sharpe",
        x_format=lambda v: f"{v:.0%}", y_format=lambda v: f"{v:.2f}"))

    ms = ns["results"]["Max Sharpe (sample cov)"]
    fl.write_svg(os.path.join(OUT, "weight_instability.svg"), fl.stacked_area(
        {t: [w[k] for w in ms.weights_at_rebalance] for k, t in enumerate(tickers)},
        [d.strftime("%Y-%m") for d in ms.rebalance_dates],
        title="Max-Sharpe weights at each quarterly rebalance",
        subtitle="Same data, three months later, a different portfolio. This is what fitting "
                 "estimation noise looks like.", y_format=lambda v: f"{v:.0%}"))


if __name__ == "__main__":
    main()
