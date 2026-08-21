"""Out-of-sample testing for portfolio construction rules.

The entire point of this module is that an optimiser evaluated on the data it
was fitted to is not being evaluated at all.  A mean-variance portfolio built
from ten years of returns and then measured over those same ten years will
always look excellent, because it was told the answer.

So: at each rebalance date the estimator sees only the trailing window, the
resulting weights are held forward through the next period, and the returns
recorded are the ones an investor would actually have received.  Weights drift
within the holding period rather than being reset daily.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import Callable, Sequence

import finlib as fl

Estimator = Callable[[list[str], dict[str, list[float]]], list[float]]


@dataclass
class WalkForwardResult:
    name: str
    dates: list[dt.date]
    returns: list[float]
    rebalance_dates: list[dt.date] = field(default_factory=list)
    weights_at_rebalance: list[list[float]] = field(default_factory=list)
    turnover: list[float] = field(default_factory=list)

    @property
    def average_turnover_per_rebalance(self) -> float:
        return sum(self.turnover) / len(self.turnover) if self.turnover else 0.0


def quarter_starts(dates: Sequence[dt.date], first_index: int) -> list[int]:
    """Indices where a new calendar quarter begins, at or after first_index."""
    out = [first_index]
    for k in range(first_index + 1, len(dates)):
        prev, cur = dates[k - 1], dates[k]
        if (prev.year, (prev.month - 1) // 3) != (cur.year, (cur.month - 1) // 3):
            out.append(k)
    return out


def walk_forward(name: str, dates: Sequence[dt.date], returns: dict[str, list[float]],
                 tickers: Sequence[str], estimator: Estimator,
                 lookback: int = 756, cost_bps: float = 5.0) -> WalkForwardResult:
    """Run one construction rule out of sample.

    `returns` are daily returns aligned to `dates[1:]`.  `estimator` receives the
    trailing window and returns weights; it never sees anything after the
    rebalance date.
    """
    n_obs = len(returns[tickers[0]])
    ret_dates = list(dates[1:])
    rebalance_points = quarter_starts(ret_dates, lookback)

    weights = [1.0 / len(tickers)] * len(tickers)
    out_returns: list[float] = []
    result = WalkForwardResult(name=name, dates=ret_dates[lookback:], returns=out_returns)

    next_reb = set(rebalance_points)
    for k in range(lookback, n_obs):
        if k in next_reb:
            window = {t: returns[t][k - lookback:k] for t in tickers}
            target = estimator(list(tickers), window)
            total = sum(target)
            target = [w / total for w in target]
            traded = sum(abs(a - b) for a, b in zip(weights, target)) / 2.0
            weights = target
            result.rebalance_dates.append(ret_dates[k])
            result.weights_at_rebalance.append(list(weights))
            result.turnover.append(traded)
            cost = traded * 2.0 * cost_bps / 10_000.0
        else:
            cost = 0.0

        gross = [w * (1.0 + returns[t][k]) for w, t in zip(weights, tickers)]
        total = sum(gross)
        out_returns.append(total - 1.0 - cost)
        weights = [g / total for g in gross]

    return result


def weight_stability(result: WalkForwardResult) -> float:
    """Mean absolute weight change between consecutive rebalances.

    A rule whose weights lurch every quarter is telling you it is fitting noise,
    and it will pay for that instability in trading costs before it pays for it
    in performance."""
    if len(result.weights_at_rebalance) < 2:
        return 0.0
    diffs = []
    for a, b in zip(result.weights_at_rebalance, result.weights_at_rebalance[1:]):
        diffs.append(sum(abs(x - y) for x, y in zip(a, b)) / 2.0)
    return sum(diffs) / len(diffs)


def summarise(result: WalkForwardResult, rf_daily: Sequence[float],
              offset: int) -> dict[str, float]:
    """Headline statistics for one out-of-sample track record."""
    rf = rf_daily[offset:offset + len(result.returns)]
    equity = fl.cumulative(result.returns)
    dd, _peak, _trough, _rec = fl.max_drawdown(equity)
    return {
        "cagr": fl.annualised_return(result.returns),
        "volatility": fl.annualised_vol(result.returns),
        "sharpe": fl.sharpe(result.returns, rf),
        "sortino": fl.sortino(result.returns, rf),
        "max_drawdown": dd,
        "turnover": result.average_turnover_per_rebalance,
        "stability": weight_stability(result),
        "total_return": equity[-1] - 1.0,
    }
