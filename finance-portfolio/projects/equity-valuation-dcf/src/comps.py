"""Trading-comparables cross-check for the DCF.

A DCF and a comps table answer different questions.  The DCF asks what the
business is worth if the forecast is right; comps ask what the market is
currently paying for businesses that look similar.  Quoting only one of them is
how you end up defending a number nobody else can reach.

The peer set here is deliberately tiny and deliberately imperfect, and the
write-up says so: two peers is not a peer set, it is an anecdote with a median.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CompRow:
    ticker: str
    name: str
    market_cap: float
    enterprise_value: float
    revenue: float
    ebitda: float
    ebit: float
    net_income: float
    free_cash_flow: float
    net_debt: float
    revenue_growth: float
    ebit_margin: float

    @property
    def ev_sales(self) -> float:
        return self.enterprise_value / self.revenue

    @property
    def ev_ebitda(self) -> float | None:
        return self.enterprise_value / self.ebitda if self.ebitda > 0 else None

    @property
    def ev_ebit(self) -> float | None:
        return self.enterprise_value / self.ebit if self.ebit > 0 else None

    @property
    def pe(self) -> float | None:
        return self.market_cap / self.net_income if self.net_income > 0 else None

    @property
    def fcf_yield(self) -> float:
        return self.free_cash_flow / self.market_cap

    @property
    def net_debt_ebitda(self) -> float | None:
        return self.net_debt / self.ebitda if self.ebitda > 0 else None


def build_comp_row(ticker: str, company: dict, year_index: int = -1) -> CompRow:
    y = company["years"][year_index]
    prev = company["years"][year_index - 1]
    i, c, m = y["income_statement"], y["cash_flow"], y["market"]
    return CompRow(
        ticker=ticker, name=company["name"],
        market_cap=m["market_cap"], enterprise_value=m["enterprise_value"],
        revenue=i["revenue"], ebitda=i["ebitda"], ebit=i["ebit"],
        net_income=i["net_income"], free_cash_flow=c["free_cash_flow"],
        net_debt=m["net_debt"],
        revenue_growth=i["revenue"] / prev["income_statement"]["revenue"] - 1.0,
        ebit_margin=i["ebit"] / i["revenue"],
    )


# A multiple computed off a denominator close to zero is arithmetic, not
# information: VSSL's EBITDA is barely positive, so its EV/EBITDA prints at
# well over 100x and would drag any median it touched.  Screening those out is
# a judgement call, so the bands are explicit and the write-up reports what was
# excluded rather than quietly dropping it.
MEANINGFUL_BANDS = {"ev_ebitda": (2.0, 40.0), "ev_ebit": (2.0, 45.0),
                    "pe": (3.0, 60.0), "ev_sales": (0.1, 15.0)}


def screen(rows: list["CompRow"], attr: str) -> tuple[list[float], list[str]]:
    """Return (usable multiples, tickers excluded as not meaningful)."""
    lo, hi = MEANINGFUL_BANDS[attr]
    keep, dropped = [], []
    for r in rows:
        v = getattr(r, attr)
        if v is None or not (lo <= v <= hi):
            dropped.append(r.ticker)
        else:
            keep.append(v)
    return keep, dropped


def median(values: list[float]) -> float:
    vs = sorted(v for v in values if v is not None)
    if not vs:
        return float("nan")
    n = len(vs)
    return vs[n // 2] if n % 2 else (vs[n // 2 - 1] + vs[n // 2]) / 2


def implied_value_per_share(multiple: float, metric: float, net_debt: float,
                            shares: float, equity_multiple: bool = False) -> float:
    """Apply a peer multiple to the subject company's metric.

    `equity_multiple=True` for P/E-style multiples, where the multiple already
    values equity and no net-debt bridge is applied."""
    if equity_multiple:
        return multiple * metric / shares
    return (multiple * metric - net_debt) / shares
