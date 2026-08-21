"""Fund analytics: tracking difference, tracking error, and the cost of holding.

The distinction this module is built around, and that most fund comparisons
blur:

* **Tracking difference** is the *level* of underperformance against the index -
  how much return the fund gave up.  It is what actually costs you money, and
  over long horizons it is dominated by the expense ratio.
* **Tracking error** is the *volatility* of that difference - how reliably the
  fund delivers whatever it delivers.  A fund can have zero tracking error and
  still lose 0.5% a year to fees, or a large tracking error and no average
  shortfall at all.

Quoting only tracking error - which fund factsheets often do - answers the
question nobody asked.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

import finlib as fl


@dataclass
class TrackingStats:
    ticker: str
    fund_cagr: float
    index_cagr: float
    tracking_difference_annual: float     # fund CAGR minus index CAGR
    tracking_error_annual: float          # stdev of the daily difference
    worst_rolling_year: float
    best_rolling_year: float
    correlation: float
    beta_to_index: float
    r_squared: float
    information_ratio: float
    expense_ratio: float
    unexplained_annual: float             # tracking difference not explained by fees


def analyse_tracking(ticker: str, fund: Sequence[float], index: Sequence[float],
                     expense_ratio: float) -> TrackingStats:
    """Compare one fund's daily return series to its benchmark index."""
    fund_r = fl.simple_returns(fund)
    index_r = fl.simple_returns(index)
    diff = [f - i for f, i in zip(fund_r, index_r)]

    fund_cagr = fl.annualised_return(fund_r)
    index_cagr = fl.annualised_return(index_r)

    # Tracking difference is measured as a difference of compound annual rates.
    # Worth knowing: a fund charging a fee f gives up slightly *more* than f of
    # CAGR, because the fee is deducted from a balance that is itself
    # compounding.  For a fund that is exactly the index minus f each day, the
    # realised CAGR gap is f x (1 + index CAGR) - so a 30bp fee costs about
    # 33bp of CAGR in a market compounding at 10%.  This is why 'unexplained'
    # below is a diagnostic to interpret, not a residual that should be zero to
    # the basis point.
    td = fund_cagr - index_cagr

    reg = fl.ols(fund_r, {"index": index_r})

    # Rolling one-year tracking difference: the range an investor could actually
    # have experienced, as opposed to the single full-period average.
    rolling = []
    window = fl.TRADING_DAYS
    for k in range(window, len(diff) + 1):
        chunk = diff[k - window:k]
        compounded_fund = 1.0
        compounded_index = 1.0
        for f, i in zip(fund_r[k - window:k], index_r[k - window:k]):
            compounded_fund *= 1.0 + f
            compounded_index *= 1.0 + i
        rolling.append(compounded_fund - compounded_index)

    return TrackingStats(
        ticker=ticker,
        fund_cagr=fund_cagr,
        index_cagr=index_cagr,
        tracking_difference_annual=td,
        tracking_error_annual=fl.stdev(diff) * math.sqrt(fl.TRADING_DAYS),
        worst_rolling_year=min(rolling) if rolling else float("nan"),
        best_rolling_year=max(rolling) if rolling else float("nan"),
        correlation=fl.correlation(fund_r, index_r),
        beta_to_index=reg.get("index"),
        r_squared=reg.r2,
        information_ratio=fl.information_ratio(fund_r, index_r),
        expense_ratio=expense_ratio,
        # A fund should lag its index by roughly its fee.  Anything else is
        # sampling, securities lending, cash drag, or a different portfolio
        # than the label implies - and it is worth naming as unexplained.
        unexplained_annual=td + expense_ratio,
    )


def total_cost_of_ownership(initial: float, gross_return: float, expense_ratio: float,
                            years: int, extra_annual_cost: float = 0.0) -> list[float]:
    """Value path net of fees, so the compounding is visible rather than asserted."""
    net = gross_return - expense_ratio - extra_annual_cost
    return [initial * (1.0 + net) ** y for y in range(years + 1)]


def fee_drag(initial: float, gross_return: float, expense_ratio: float,
             years: int, extra_annual_cost: float = 0.0) -> dict[str, float]:
    """What the fee costs by the end of the horizon, in money and in percent.

    The comparison is against the *same* gross return, which is the only honest
    way to isolate the fee: a fund is not entitled to credit for outperformance
    it has not demonstrated."""
    gross_path = initial * (1.0 + gross_return) ** years
    net_path = initial * (1.0 + gross_return - expense_ratio - extra_annual_cost) ** years
    return {"gross_value": gross_path, "net_value": net_path,
            "cost": gross_path - net_path,
            "cost_share_of_gross_gain": ((gross_path - net_path) / (gross_path - initial)
                                         if gross_path > initial else float("nan"))}


def breakeven_outperformance(expense_gap: float) -> float:
    """Gross outperformance a pricier fund must deliver just to draw level.

    Trivial arithmetic, and worth stating because it is the question a fee
    comparison is really asking: this much, every year, forever, before it has
    added anything at all."""
    return expense_gap


def holding_overlap(weights_a: dict[str, float], weights_b: dict[str, float]) -> float:
    """Portfolio overlap: sum of the minimum weight in each common holding.

    100% means identical portfolios; 0% means no shared exposure.  Two funds
    with 95% overlap are one fund with two fee schedules, whatever their
    marketing says."""
    return sum(min(weights_a.get(k, 0.0), weights_b.get(k, 0.0))
               for k in set(weights_a) | set(weights_b))


def rolling_tracking_difference(fund: Sequence[float], index: Sequence[float],
                                window: int = fl.TRADING_DAYS) -> list[float | None]:
    """Rolling `window`-day compounded return difference, aligned to the price series."""
    fund_r = fl.simple_returns(fund)
    index_r = fl.simple_returns(index)
    # One `None` per price observation that has no complete trailing window.
    # Returns are one shorter than prices, so the padding is `window`, not
    # `window - 1` - otherwise the series silently misaligns with its dates.
    out: list[float | None] = [None] * window
    for k in range(window, len(fund_r) + 1):
        cf = ci = 1.0
        for f, i in zip(fund_r[k - window:k], index_r[k - window:k]):
            cf *= 1.0 + f
            ci *= 1.0 + i
        out.append(cf - ci)
    return out
