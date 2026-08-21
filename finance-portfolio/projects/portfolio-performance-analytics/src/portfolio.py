"""Portfolio construction, rebalancing and performance/risk attribution.

The engine is deliberately explicit about three things that portfolio
analytics usually leaves implicit:

* **Rebalancing is simulated, not assumed.**  Most tutorial code computes
  `sum(w_i * r_i)` every day, which silently assumes continuous, costless
  rebalancing back to target.  Nobody does that.  Here the weights drift with
  performance and are reset on an explicit calendar, turnover is measured, and
  a cost can be charged against it.
* **Risk contribution is separated from capital allocation.**  A 40% weight in
  bonds is not 40% of the risk, and the gap between those two numbers is
  usually the most important fact about a balanced portfolio.
* **Drawdowns are reported with their recovery, not just their depth.**  A 30%
  drawdown that recovers in eight months and a 30% drawdown that takes four
  years are not the same risk, and one number cannot tell them apart.
"""

from __future__ import annotations

import datetime as dt
import math
from dataclasses import dataclass
from typing import Sequence

import finlib as fl


# ---------------------------------------------------------------------------
# Rebalancing
# ---------------------------------------------------------------------------

REBALANCE_RULES = {
    "monthly": lambda prev, cur: (prev.year, prev.month) != (cur.year, cur.month),
    "quarterly": lambda prev, cur: (prev.year, (prev.month - 1) // 3)
                                   != (cur.year, (cur.month - 1) // 3),
    "annual": lambda prev, cur: prev.year != cur.year,
    "never": lambda prev, cur: False,
}


@dataclass
class BacktestResult:
    dates: list[dt.date]
    returns: list[float]
    weights_history: dict[str, list[float]]
    turnover: list[float]
    total_turnover: float
    rebalance_count: int
    cost_drag_annual: float


def backtest(dates: Sequence[dt.date], asset_returns: dict[str, list[float]],
             target: dict[str, float], frequency: str = "quarterly",
             cost_bps: float = 0.0) -> BacktestResult:
    """Run a drift-and-rebalance backtest.

    `asset_returns` are period returns aligned to `dates[1:]` (one fewer than
    the price series).  `cost_bps` is charged on one-way turnover at each
    rebalance, which is the convention that makes the number comparable to a
    quoted spread plus commission.
    """
    if frequency not in REBALANCE_RULES:
        raise ValueError(f"unknown rebalance frequency: {frequency}")
    should_rebalance = REBALANCE_RULES[frequency]

    tickers = list(target)
    total_w = sum(target.values())
    weights = {t: target[t] / total_w for t in tickers}

    port_returns, turnover, history = [], [], {t: [] for t in tickers}
    n = len(asset_returns[tickers[0]])

    for k in range(n):
        # Record the weight the portfolio actually enters the period with, so
        # that contribution analysis later uses the weight that earned the
        # return rather than the one left behind after it.
        for t in tickers:
            history[t].append(weights[t])

        # --- one period of drift ------------------------------------------
        gross = {t: weights[t] * (1.0 + asset_returns[t][k]) for t in tickers}
        total = sum(gross.values())
        period_return = total - 1.0
        weights = {t: gross[t] / total for t in tickers}

        # --- rebalance if the calendar says the next period starts a new
        #     month / quarter / year -----------------------------------------
        traded = 0.0
        this_date = dates[k + 1]
        next_date = dates[k + 2] if k + 2 < len(dates) else None
        if next_date is not None and should_rebalance(this_date, next_date):
            # One-way turnover: half the sum of absolute weight changes.
            traded = sum(abs(weights[t] - target[t] / total_w) for t in tickers) / 2.0
            weights = {t: target[t] / total_w for t in tickers}
            period_return -= traded * 2.0 * cost_bps / 10_000.0

        port_returns.append(period_return)
        turnover.append(traded)

    years = n / fl.TRADING_DAYS
    total_turn = sum(turnover)
    return BacktestResult(
        dates=list(dates[1:]), returns=port_returns, weights_history=history,
        turnover=turnover, total_turnover=total_turn,
        rebalance_count=sum(1 for t in turnover if t > 0),
        cost_drag_annual=total_turn * 2.0 * cost_bps / 10_000.0 / years,
    )


# ---------------------------------------------------------------------------
# Performance summary
# ---------------------------------------------------------------------------


@dataclass
class Performance:
    cagr: float
    total_return: float
    volatility: float
    sharpe: float
    sortino: float
    max_drawdown: float
    drawdown_peak: dt.date
    drawdown_trough: dt.date
    drawdown_recovery: dt.date | None
    drawdown_length_days: int
    var_95: float
    cvar_95: float
    skew: float
    excess_kurtosis: float
    best_day: float
    worst_day: float
    positive_days: float
    beta: float | None = None
    alpha_annual: float | None = None
    r_squared: float | None = None
    tracking_error: float | None = None
    information_ratio: float | None = None
    up_capture: float | None = None
    down_capture: float | None = None


def summarise(dates: Sequence[dt.date], returns: Sequence[float],
              rf_daily: Sequence[float], benchmark: Sequence[float] | None = None) -> Performance:
    equity = fl.cumulative(returns)
    dd, peak_i, trough_i, rec_i = fl.max_drawdown(equity)
    # equity has one extra leading point (the starting 1.0), so indices shift
    idx = lambda i: dates[max(0, min(i - 1, len(dates) - 1))]        # noqa: E731

    perf = Performance(
        cagr=fl.annualised_return(returns),
        total_return=equity[-1] / equity[0] - 1.0,
        volatility=fl.annualised_vol(returns),
        sharpe=fl.sharpe(returns, rf_daily),
        sortino=fl.sortino(returns, rf_daily),
        max_drawdown=dd,
        drawdown_peak=idx(peak_i), drawdown_trough=idx(trough_i),
        drawdown_recovery=idx(rec_i) if rec_i is not None else None,
        drawdown_length_days=((rec_i if rec_i is not None else len(equity) - 1) - peak_i),
        var_95=fl.historical_var(returns, 0.95),
        cvar_95=fl.historical_cvar(returns, 0.95),
        skew=fl.skewness(returns),
        excess_kurtosis=fl.excess_kurtosis(returns),
        best_day=max(returns), worst_day=min(returns),
        positive_days=sum(1 for r in returns if r > 0) / len(returns),
    )

    if benchmark is not None:
        excess = [r - f for r, f in zip(returns, rf_daily)]
        bench_excess = [b - f for b, f in zip(benchmark, rf_daily)]
        reg = fl.ols(excess, {"benchmark": bench_excess})
        perf.beta = reg.get("benchmark")
        perf.alpha_annual = reg.get("alpha") * fl.TRADING_DAYS
        perf.r_squared = reg.r2
        perf.tracking_error = fl.tracking_error(returns, benchmark)
        perf.information_ratio = fl.information_ratio(returns, benchmark)
        perf.up_capture, perf.down_capture = fl.capture_ratios(returns, benchmark)
    return perf


# ---------------------------------------------------------------------------
# Attribution
# ---------------------------------------------------------------------------


def return_contributions(asset_returns: dict[str, list[float]],
                         weights_history: dict[str, list[float]]) -> dict[str, float]:
    """Each holding's contribution to the portfolio's total compounded return.

    Contributions are accumulated on the *actual* drifting weights, so they sum
    to the portfolio return rather than to a plausible-looking approximation of
    it.  The usual shortcut - target weight times asset total return - does not
    add up once weights drift, and the residual quietly lands nowhere.
    """
    tickers = list(asset_returns)
    n = len(asset_returns[tickers[0]])
    contrib = {t: 0.0 for t in tickers}
    level = 1.0
    for k in range(n):
        period = 0.0
        for t in tickers:
            w = weights_history[t][k]           # weight entering the period
            contrib[t] += level * w * asset_returns[t][k]
            period += w * asset_returns[t][k]
        level *= 1.0 + period
    return contrib


def risk_contributions(cov: list[list[float]], weights: Sequence[float]) -> list[float]:
    """Percentage contribution to portfolio variance.

        MCR_i = w_i * (Sigma w)_i / sigma_p        (marginal contribution)
        PCR_i = MCR_i / sigma_p                    (share of total risk)

    These sum to 1 by Euler's theorem, because portfolio volatility is
    homogeneous of degree one in the weights.
    """
    sigma_w = fl.matvec(cov, weights)
    port_var = sum(w * s for w, s in zip(weights, sigma_w))
    if port_var <= 0:
        return [0.0] * len(weights)
    return [w * s / port_var for w, s in zip(weights, sigma_w)]


def diversification_ratio(cov: list[list[float]], weights: Sequence[float]) -> float:
    """Weighted average asset volatility divided by portfolio volatility.

    1.0 means diversification bought nothing; higher is better.  It is a
    cleaner headline than an average pairwise correlation, which hides how much
    of the portfolio each correlation applies to."""
    vols = [math.sqrt(cov[i][i]) for i in range(len(weights))]
    weighted_vol = sum(w * v for w, v in zip(weights, vols))
    port_vol = math.sqrt(sum(w * s for w, s in zip(weights, fl.matvec(cov, weights))))
    return weighted_vol / port_vol if port_vol else float("nan")


# ---------------------------------------------------------------------------
# Calendar aggregation
# ---------------------------------------------------------------------------


def calendar_year_returns(dates: Sequence[dt.date],
                          returns: Sequence[float]) -> dict[int, float]:
    out: dict[int, float] = {}
    for d, r in zip(dates, returns):
        out[d.year] = (1.0 + out.get(d.year, 0.0)) * (1.0 + r) - 1.0
    return out


def monthly_returns(dates: Sequence[dt.date],
                    returns: Sequence[float]) -> tuple[list[str], list[float]]:
    labels, values = [], []
    for d, r in zip(dates, returns):
        key = f"{d.year}-{d.month:02d}"
        if not labels or labels[-1] != key:
            labels.append(key)
            values.append(r)
        else:
            values[-1] = (1.0 + values[-1]) * (1.0 + r) - 1.0
    return labels, values
