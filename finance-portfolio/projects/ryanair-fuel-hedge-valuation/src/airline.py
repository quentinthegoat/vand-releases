"""Ryanair: fuel-driven valuation model.

The thesis this model exists to test
------------------------------------
Ryanair earned a record EUR 2,459m of pre-exceptional operating profit in FY26
on a fuel bill of EUR 5,419m.  Fuel is 41% of the cost base, so a 45% rise in
the fuel bill erases every euro of operating profit.  At the reporting date the
issuer disclosed that jet-fuel spot had spiked above USD 150/bbl, while 80% of
FY27 fuel is hedged at approximately USD 67/bbl - but only to April 2027.

So the equity is not really a bet on traffic or ancillary revenue.  It is a bet
on two numbers:

    S      the jet-fuel price once the hedge rolls off
    theta  the share of a fuel cost increase recovered through higher fares

This module models exactly those two, and leaves everything else deliberately
simple.  A model that is elaborate everywhere hides which assumption is doing
the work.

The load-bearing assumption, stated plainly
-------------------------------------------
The FY26 release does not disclose the realised fuel price or fuel volume in
barrels, so the FY26 fuel bill cannot be decomposed into price x quantity from
this document alone.  The model therefore treats the FY26 realised fuel cost as
having been struck at approximately the FY27 hedge level of USD 67/bbl, and
scales from there.

That assumption is the weakest link in the whole analysis.  It is named here,
surfaced in the output, and sensitivity-tested in `analysis.py` rather than
buried.  Anyone with the annual report's fuel note should replace it.
"""

from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class FuelPath:
    """Effective fuel price exposure through the forecast.

    Year 1 (FY27) is `hedge_pct` hedged at `hedge_price`; the balance prices at
    spot.  From year 2 the hedge has expired and the airline is fully exposed to
    `long_run_price`, which is the scenario variable that matters.
    """
    baseline_price: float          # USD/bbl the FY26 bill is assumed struck at
    hedge_pct: float               # share of FY27 fuel hedged
    hedge_price: float             # USD/bbl of that hedge
    spot_price: float              # USD/bbl spot at the reporting date
    long_run_price: float          # USD/bbl once the hedge rolls off

    def effective_price(self, year_index: int) -> float:
        """Effective USD/bbl in forecast year `year_index` (1 = FY27)."""
        if year_index <= 1:
            return self.hedge_pct * self.hedge_price + (1 - self.hedge_pct) * self.spot_price
        return self.long_run_price

    def cost_factor(self, year_index: int) -> float:
        """Fuel cost per passenger relative to FY26."""
        return self.effective_price(year_index) / self.baseline_price


@dataclass(frozen=True)
class Drivers:
    years: tuple[int, ...]
    traffic_growth: tuple[float, ...]       # passenger growth
    non_fuel_cost_inflation: tuple[float, ...]
    ancillary_growth_per_pax: tuple[float, ...]
    pass_through: float                     # theta: share of fuel rise recovered in fares
    tax_rate: float
    capex_per_passenger: float              # EUR, fleet spend normalised to traffic
    depreciation_per_passenger: float       # EUR; tracks the fleet, not fuel prices
    nwc_per_passenger: float                # EUR, negative: passengers pay before flying

    def with_pass_through(self, theta: float) -> "Drivers":
        return replace(self, pass_through=theta)


@dataclass
class ForecastYear:
    year: int
    passengers: float
    fuel_price_usd: float
    revenue_per_pax: float
    fuel_cost_per_pax: float
    non_fuel_cost_per_pax: float
    revenue: float
    fuel_cost: float
    non_fuel_cost: float
    ebit: float
    ebit_margin: float
    nopat: float
    depreciation: float
    capex: float
    change_in_nwc: float
    fcff: float
    discount_factor: float = 0.0
    present_value: float = 0.0


@dataclass(frozen=True)
class Base:
    """FY26 actuals, per passenger, from the filing."""
    passengers: float
    revenue: float
    fuel_cost: float
    non_fuel_cost: float          # opex before exceptional, less fuel

    @property
    def revenue_per_pax(self) -> float:
        return self.revenue / self.passengers

    @property
    def fuel_per_pax(self) -> float:
        return self.fuel_cost / self.passengers

    @property
    def non_fuel_per_pax(self) -> float:
        return self.non_fuel_cost / self.passengers


def forecast(base: Base, drivers: Drivers, fuel: FuelPath) -> list[ForecastYear]:
    """Project FCFF with fuel price and fare pass-through as the live variables.

    Fares move only to the extent the airline recovers fuel:

        revenue/pax = FY26 revenue/pax
                    + theta x (fuel/pax increase versus FY26)
                    + ancillary growth

    Setting theta = 0 assumes fares are set entirely by competition and the
    whole fuel move lands on the margin.  theta = 1 assumes full recovery, which
    for a short-haul carrier with the lowest cost base in Europe is the bull
    case rather than the neutral one: Ryanair recovers when weaker competitors
    cut capacity, and that takes time.
    """
    out: list[ForecastYear] = []
    passengers = base.passengers
    prev_revenue = base.revenue
    nwc = base.passengers * drivers.nwc_per_passenger
    ancillary_uplift = 0.0
    non_fuel_per_pax = base.non_fuel_per_pax

    for k, year in enumerate(drivers.years, start=1):
        passengers *= 1.0 + drivers.traffic_growth[k - 1]
        non_fuel_per_pax *= 1.0 + drivers.non_fuel_cost_inflation[k - 1]
        ancillary_uplift += base.revenue_per_pax * drivers.ancillary_growth_per_pax[k - 1]

        fuel_per_pax = base.fuel_per_pax * fuel.cost_factor(k)
        fuel_increase_per_pax = fuel_per_pax - base.fuel_per_pax
        revenue_per_pax = (base.revenue_per_pax + ancillary_uplift
                           + drivers.pass_through * fuel_increase_per_pax)

        revenue = revenue_per_pax * passengers
        fuel_cost = fuel_per_pax * passengers
        non_fuel_cost = non_fuel_per_pax * passengers
        ebit = revenue - fuel_cost - non_fuel_cost

        nopat = ebit * (1.0 - drivers.tax_rate) if ebit > 0 else ebit
        # Depreciation and working capital are driven by the fleet and by
        # passenger volume, NOT by revenue. Scaling them off revenue lets a pure
        # fuel-price pass-through inflate the cash flow, which made the
        # full-pass-through column rise with the fuel price - an artefact, not a
        # result.
        depreciation = drivers.depreciation_per_passenger * passengers
        capex = drivers.capex_per_passenger * passengers
        new_nwc = passengers * drivers.nwc_per_passenger
        d_nwc = new_nwc - nwc
        nwc = new_nwc

        out.append(ForecastYear(
            year=year, passengers=passengers,
            fuel_price_usd=fuel.effective_price(k),
            revenue_per_pax=revenue_per_pax, fuel_cost_per_pax=fuel_per_pax,
            non_fuel_cost_per_pax=non_fuel_per_pax,
            revenue=revenue, fuel_cost=fuel_cost, non_fuel_cost=non_fuel_cost,
            ebit=ebit, ebit_margin=ebit / revenue, nopat=nopat,
            depreciation=depreciation, capex=capex, change_in_nwc=d_nwc,
            fcff=nopat + depreciation - capex - d_nwc))
        prev_revenue = revenue
    return out


def discount(rows: list[ForecastYear], wacc: float, mid_year: bool = True) -> list[ForecastYear]:
    for k, row in enumerate(rows, start=1):
        t = k - 0.5 if mid_year else k
        row.discount_factor = 1.0 / (1.0 + wacc) ** t
        row.present_value = row.fcff * row.discount_factor
    return rows


@dataclass
class Valuation:
    pv_explicit: float
    pv_terminal: float
    enterprise_value: float
    net_cash: float
    equity_value: float
    shares: float
    value_per_share: float
    terminal_share: float
    rows: list[ForecastYear]


def value(base: Base, drivers: Drivers, fuel: FuelPath, wacc: float,
          terminal_growth: float, net_cash: float, shares: float,
          mid_year: bool = True) -> Valuation:
    """Enterprise value to value per share.

    Note the sign convention: Ryanair holds net *cash*, so the bridge adds
    rather than subtracts.  Getting this backwards is worth EUR 4 per share and
    is one of the easiest mistakes to make on a debt-free balance sheet."""
    rows = discount(forecast(base, drivers, fuel), wacc, mid_year)
    last = rows[-1]

    if last.fcff <= 0:
        # A terminal value built off a negative cash flow is meaningless: the
        # Gordon formula would hand back a large positive number as the growth
        # rate rises. Report zero and let the explicit period speak.
        terminal = 0.0
    else:
        terminal = last.fcff * (1.0 + terminal_growth) / (wacc - terminal_growth)

    n = len(rows)
    t = (n - 0.5) if mid_year else n
    pv_terminal = terminal / (1.0 + wacc) ** t
    pv_explicit = sum(r.present_value for r in rows)
    ev = pv_explicit + pv_terminal
    equity = ev + net_cash
    return Valuation(pv_explicit, pv_terminal, ev, net_cash, equity, shares,
                     equity / shares, (pv_terminal / ev) if ev else 0.0, rows)


def breakeven_fuel_price(base: Base, drivers: Drivers, fuel: FuelPath,
                         lo: float = 40.0, hi: float = 400.0) -> float:
    """Long-run USD/bbl at which steady-state EBIT reaches zero.

    Bisection on the final forecast year's EBIT, which is monotonically
    decreasing in the fuel price for any pass-through below 1."""
    def ebit_at(price: float) -> float:
        rows = forecast(base, drivers, replace(fuel, long_run_price=price))
        return rows[-1].ebit

    if ebit_at(hi) > 0:
        return float("inf")
    for _ in range(200):
        mid = (lo + hi) / 2
        if ebit_at(mid) > 0:
            lo = mid
        else:
            hi = mid
        if hi - lo < 1e-6:
            break
    return (lo + hi) / 2


def implied_fuel_price(base: Base, drivers: Drivers, fuel: FuelPath, wacc: float,
                       terminal_growth: float, net_cash: float, shares: float,
                       target_price: float, lo: float = 40.0, hi: float = 400.0) -> float:
    """Reverse DCF: the long-run fuel price the market price implies.

    This is the number the whole report turns on. A DCF says what the shares are
    worth under your fuel view; this says what fuel view is already in the
    price."""
    def value_at(price: float) -> float:
        return value(base, drivers, replace(fuel, long_run_price=price), wacc,
                     terminal_growth, net_cash, shares).value_per_share

    for _ in range(200):
        mid = (lo + hi) / 2
        if value_at(mid) > target_price:
            lo = mid          # cheaper fuel -> higher value, so move the floor up
        else:
            hi = mid
        if hi - lo < 1e-6:
            break
    return (lo + hi) / 2
