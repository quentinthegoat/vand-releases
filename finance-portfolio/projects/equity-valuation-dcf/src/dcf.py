"""Discounted cash flow engine: WACC, FCFF forecast, terminal value, bridge.

The model is unlevered (FCFF discounted at WACC) rather than levered (FCFE at
the cost of equity).  For a company whose capital structure is actively moving
- and Meridian's is, after a debt-funded acquisition and three years of
deleveraging - FCFF is the more stable of the two, because the financing
decision affects the discount rate rather than the cash flow being discounted.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field, replace


# ---------------------------------------------------------------------------
# Cost of capital
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WACCInputs:
    risk_free: float
    equity_risk_premium: float
    unlevered_beta: float          # bottom-up, from sector peers
    pretax_cost_of_debt: float
    tax_rate: float
    market_cap: float
    market_value_of_debt: float
    size_premium: float = 0.0      # applied to the cost of equity


@dataclass(frozen=True)
class WACC:
    levered_beta: float
    cost_of_equity: float
    after_tax_cost_of_debt: float
    weight_equity: float
    weight_debt: float
    wacc: float


def compute_wacc(i: WACCInputs) -> WACC:
    """CAPM cost of equity with a bottom-up beta, relevered at the target
    structure via Hamada.

    Why bottom-up rather than a regression beta on the company's own stock:
    a single-name regression beta carries a standard error wide enough to move
    the valuation by double digits, and it embeds whatever leverage the company
    happened to run over the estimation window.  A sector unlevered beta
    relevered at the *target* structure is both tighter and internally
    consistent with the capital structure assumed in the WACC weights.

        beta_L = beta_U * (1 + (1 - t) * D/E)
        Ke     = rf + beta_L * ERP + size premium
        Kd     = pretax cost of debt * (1 - t)
        WACC   = We * Ke + Wd * Kd
    """
    d_over_e = i.market_value_of_debt / i.market_cap
    levered_beta = i.unlevered_beta * (1.0 + (1.0 - i.tax_rate) * d_over_e)
    ke = i.risk_free + levered_beta * i.equity_risk_premium + i.size_premium
    kd = i.pretax_cost_of_debt * (1.0 - i.tax_rate)
    total = i.market_cap + i.market_value_of_debt
    we, wd = i.market_cap / total, i.market_value_of_debt / total
    return WACC(levered_beta, ke, kd, we, wd, we * ke + wd * kd)


# ---------------------------------------------------------------------------
# Free cash flow forecast
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ForecastDrivers:
    """One entry per forecast year.  Ratios are decimals of revenue."""
    years: tuple[int, ...]
    revenue_growth: tuple[float, ...]
    ebit_margin: tuple[float, ...]
    tax_rate: float
    depreciation_pct_revenue: tuple[float, ...]
    capex_pct_revenue: tuple[float, ...]
    nwc_pct_revenue: float          # working capital intensity, from history

    def scaled(self, growth_delta: float = 0.0, margin_delta: float = 0.0) -> "ForecastDrivers":
        """Return a copy with parallel shifts applied - used for scenarios."""
        return replace(
            self,
            revenue_growth=tuple(g + growth_delta for g in self.revenue_growth),
            ebit_margin=tuple(m + margin_delta for m in self.ebit_margin),
        )


@dataclass
class ForecastYear:
    year: int
    revenue: float
    ebit: float
    ebit_margin: float
    nopat: float
    depreciation: float
    capex: float
    change_in_nwc: float
    fcff: float
    discount_factor: float
    present_value: float


def forecast_fcff(base_revenue: float, drivers: ForecastDrivers,
                  base_nwc: float) -> list[ForecastYear]:
    """FCFF = EBIT x (1 - t) + D&A - capex - change in net working capital.

    Working capital is modelled as a constant share of revenue, so the cash
    absorbed each year is that share applied to *incremental* revenue.  A
    growing company therefore has a permanent working-capital drag, which is
    the point: a forecast that ignores it flatters every growth assumption.
    """
    out: list[ForecastYear] = []
    revenue = base_revenue
    nwc = base_nwc
    for k, year in enumerate(drivers.years):
        revenue = revenue * (1.0 + drivers.revenue_growth[k])
        ebit = revenue * drivers.ebit_margin[k]
        nopat = ebit * (1.0 - drivers.tax_rate)
        dep = revenue * drivers.depreciation_pct_revenue[k]
        capex = revenue * drivers.capex_pct_revenue[k]
        new_nwc = revenue * drivers.nwc_pct_revenue
        d_nwc = new_nwc - nwc
        nwc = new_nwc
        fcff = nopat + dep - capex - d_nwc
        out.append(ForecastYear(year, revenue, ebit, drivers.ebit_margin[k], nopat,
                                dep, capex, d_nwc, fcff, 0.0, 0.0))
    return out


def discount(rows: list[ForecastYear], wacc: float, mid_year: bool = True) -> list[ForecastYear]:
    """Discount the explicit forecast.

    Mid-year convention: cash arrives through the year rather than in a lump on
    31 December, so period t is discounted at t - 0.5.  It lifts the value by
    roughly WACC/2 versus year-end discounting and is the more honest default
    for an operating business.
    """
    for k, row in enumerate(rows, start=1):
        t = k - 0.5 if mid_year else k
        row.discount_factor = 1.0 / (1.0 + wacc) ** t
        row.present_value = row.fcff * row.discount_factor
    return rows


# ---------------------------------------------------------------------------
# Terminal value
# ---------------------------------------------------------------------------


def terminal_value_gordon(final_fcff: float, wacc: float, growth: float) -> float:
    if growth >= wacc:
        raise ValueError("terminal growth must be below WACC")
    return final_fcff * (1.0 + growth) / (wacc - growth)


def terminal_value_exit_multiple(final_ebitda: float, multiple: float) -> float:
    return final_ebitda * multiple


def implied_exit_multiple(tv: float, final_ebitda: float) -> float:
    return tv / final_ebitda


def implied_terminal_growth(tv: float, final_fcff: float, wacc: float) -> float:
    """Invert Gordon: g = (TV * WACC - FCFF) / (TV + FCFF)."""
    return (tv * wacc - final_fcff) / (tv + final_fcff)


# ---------------------------------------------------------------------------
# Enterprise value to per-share value
# ---------------------------------------------------------------------------


@dataclass
class Valuation:
    pv_explicit: float
    pv_terminal: float
    enterprise_value: float
    net_debt: float
    other_claims: float
    equity_value: float
    shares: float
    value_per_share: float
    terminal_share_of_ev: float
    method: str
    rows: list[ForecastYear] = field(default_factory=list)


def build_valuation(rows: list[ForecastYear], terminal: float, wacc: float,
                    net_debt: float, shares: float, method: str,
                    other_claims: float = 0.0, mid_year: bool = True) -> Valuation:
    n = len(rows)
    t = (n - 0.5) if mid_year else n
    pv_terminal = terminal / (1.0 + wacc) ** t
    pv_explicit = sum(r.present_value for r in rows)
    ev = pv_explicit + pv_terminal
    equity = ev - net_debt - other_claims
    return Valuation(pv_explicit, pv_terminal, ev, net_debt, other_claims,
                     equity, shares, equity / shares, pv_terminal / ev, method, rows)


def value_with(base_revenue: float, base_nwc: float, drivers: ForecastDrivers,
               wacc: float, net_debt: float, shares: float,
               terminal_growth: float | None = None,
               exit_multiple: float | None = None,
               mid_year: bool = True) -> Valuation:
    """One call from drivers to value per share, for either terminal method."""
    rows = discount(forecast_fcff(base_revenue, drivers, base_nwc), wacc, mid_year)
    last = rows[-1]
    if exit_multiple is not None:
        ebitda = last.ebit + last.depreciation
        tv = terminal_value_exit_multiple(ebitda, exit_multiple)
        method = f"exit multiple {exit_multiple:.1f}x EBITDA"
    else:
        tv = terminal_value_gordon(last.fcff, wacc, terminal_growth or 0.0)
        method = f"Gordon growth {(terminal_growth or 0.0):.2%}"
    return build_valuation(rows, tv, wacc, net_debt, shares, method, mid_year=mid_year)


# ---------------------------------------------------------------------------
# Sensitivity, scenarios, reverse DCF, Monte Carlo
# ---------------------------------------------------------------------------


def sensitivity_grid(fn, row_values: list[float], col_values: list[float]) -> list[list[float]]:
    return [[fn(r, c) for c in col_values] for r in row_values]


def reverse_dcf_growth(target_price: float, base_revenue: float, base_nwc: float,
                       drivers: ForecastDrivers, wacc: float, net_debt: float,
                       shares: float, terminal_growth: float,
                       lo: float = -0.15, hi: float = 0.35) -> float:
    """What uniform revenue growth rate does the market price imply?

    A DCF says what a set of assumptions is worth.  A reverse DCF says what the
    market's price already assumes, which is the more useful question when you
    are deciding whether your own forecast is differentiated or just consensus
    with extra steps.  Solved by bisection: value per share is monotonic in
    growth over any sane range.
    """
    def price_at(g: float) -> float:
        d = replace(drivers, revenue_growth=tuple(g for _ in drivers.years))
        return value_with(base_revenue, base_nwc, d, wacc, net_debt, shares,
                          terminal_growth=terminal_growth).value_per_share

    for _ in range(200):
        mid = (lo + hi) / 2
        if price_at(mid) < target_price:
            lo = mid
        else:
            hi = mid
        if hi - lo < 1e-7:
            break
    return (lo + hi) / 2


def monte_carlo(base_revenue: float, base_nwc: float, drivers: ForecastDrivers,
                wacc_mean: float, net_debt: float, shares: float,
                terminal_growth_mean: float, trials: int = 20_000,
                growth_sd: float = 0.015, margin_sd: float = 0.011,
                wacc_sd: float = 0.006, tg_sd: float = 0.0035,
                seed: int = 7) -> list[float]:
    """Draw correlated-ish assumption sets and return the value distribution.

    Growth and margin are shifted in parallel across all forecast years rather
    than independently by year: analysts are wrong about the *level* of a
    company's trajectory far more often than they are wrong about one year in
    isolation, and independent yearly draws would wash out through averaging
    and understate the real spread.
    """
    rng = random.Random(seed)
    out = []
    for _ in range(trials):
        g = rng.gauss(0.0, growth_sd)
        m = rng.gauss(0.0, margin_sd)
        w = max(0.03, rng.gauss(wacc_mean, wacc_sd))
        tg = rng.gauss(terminal_growth_mean, tg_sd)
        tg = min(tg, w - 0.01)            # keep Gordon well defined
        d = drivers.scaled(growth_delta=g, margin_delta=m)
        try:
            v = value_with(base_revenue, base_nwc, d, w, net_debt, shares,
                           terminal_growth=tg).value_per_share
        except ValueError:
            continue
        if math.isfinite(v):
            out.append(v)
    return sorted(out)


def percentile(sorted_values: list[float], p: float) -> float:
    if not sorted_values:
        return float("nan")
    k = (len(sorted_values) - 1) * p
    lo, hi = math.floor(k), math.ceil(k)
    if lo == hi:
        return sorted_values[int(k)]
    return sorted_values[lo] * (hi - k) + sorted_values[hi] * (k - lo)
