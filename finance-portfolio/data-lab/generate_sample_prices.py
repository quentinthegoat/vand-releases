"""Generate the synthetic daily price panel used by three portfolio projects.

Why synthetic data?
-------------------
The projects in this portfolio must run for anyone who clones them, with no API
key, no network access and no paid data licence.  Redistributing vendor price
history is also a licensing problem.  So the committed sample panel is
*simulated*, not real, and every project says so on its front page.

The simulation is not noise for the sake of noise: it is a small linear factor
model with the stylised facts that matter for the analytics being demonstrated
(volatility clustering, fat tails, a genuine bear market, correlated but not
identical assets, funds that track an index minus their fee).  That means the
Sharpe ratios, drawdowns, tracking errors and frontier shapes the projects
report are *mechanically* correct even though the tickers are fictional.

Every project also ships `fetch_real_prices.py`, which downloads the same CSV
layout from Stooq so the identical pipeline can be pointed at real history.

Model
-----
    r_i,t = alpha_i / 252
          + sum_k beta_i,k * f_k,t
          + idio_i * z_i,t
          - expense_i / 252

    f_EQ,t   equity factor with GARCH(1,1) volatility and Student-t shocks
    f_RATE,t rates/duration factor
    f_SIZE,t small-cap spread
    f_VAL,t  value spread
    f_FX,t   non-US currency factor
    f_EM,t   emerging-market spread
    f_GLD,t  gold factor

Usage
-----
    python generate_sample_prices.py --out ../shared-data

Deterministic: same seed in, byte-identical CSV out.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import math
import os
import random

SEED = 20240101
START = dt.date(2016, 1, 4)
END = dt.date(2025, 12, 31)
TRADING_DAYS = 252

# --------------------------------------------------------------------------
# Universe definition.  Tickers are fictional and deliberately look fictional.
# betas are exposures to (EQ, RATE, SIZE, VAL, FX, EM, GLD).
# alpha and idio are annualised; expense is the annual fund fee in decimals.
# --------------------------------------------------------------------------
FACTORS = ("EQ", "RATE", "SIZE", "VAL", "FX", "EM", "GLD")

UNIVERSE = {
    # ticker:  (label, betas,                                   alpha,  idio,  expense)
    "IDXUS": ("US Large-Cap Index (not investable)",
              dict(EQ=1.00), 0.0000, 0.000, 0.0000),
    "LCAP":  ("Core US Large-Cap ETF",
              dict(EQ=1.00), 0.0000, 0.0012, 0.0003),
    "BRDX":  ("Total US Market ETF",
              dict(EQ=0.98, SIZE=0.12), 0.0000, 0.0030, 0.0009),
    "SMRT":  ("US Multifactor 'Smart Beta' ETF",
              dict(EQ=0.92, VAL=0.38, SIZE=0.22), 0.0000, 0.020, 0.0035),
    "SCAP":  ("US Small-Cap ETF",
              dict(EQ=1.12, SIZE=0.85), 0.0000, 0.035, 0.0006),
    "INTL":  ("Developed ex-US Equity ETF",
              dict(EQ=0.82, FX=0.75), -0.005, 0.030, 0.0007),
    "EMKT":  ("Emerging Markets Equity ETF",
              dict(EQ=0.88, EM=0.90, FX=0.35), -0.010, 0.055, 0.0014),
    "BNDX":  ("Aggregate Bond ETF",
              dict(RATE=1.00, EQ=0.05), 0.0000, 0.012, 0.0005),
    "REIT":  ("Listed Real Estate ETF",
              dict(EQ=0.85, RATE=0.55, VAL=0.25), -0.008, 0.045, 0.0012),
    "GOLD":  ("Physical Gold ETC",
              dict(GLD=1.00, EQ=-0.05), 0.0000, 0.020, 0.0025),
}

# Annualised factor volatilities and drifts.
FACTOR_SPEC = {
    "EQ":   dict(vol=0.160, drift=0.075),
    "RATE": dict(vol=0.055, drift=0.022),
    "SIZE": dict(vol=0.090, drift=0.005),
    "VAL":  dict(vol=0.085, drift=0.010),
    "FX":   dict(vol=0.075, drift=-0.005),
    "EM":   dict(vol=0.110, drift=-0.010),
    "GLD":  dict(vol=0.145, drift=0.075),
}

# Regimes deliberately planted so the risk analytics have something to find.
# (start, end, equity drift override, equity vol multiplier)
REGIMES = [
    (dt.date(2018, 10, 1), dt.date(2018, 12, 24), -0.55, 1.6),   # Q4 growth scare
    (dt.date(2020, 2, 19), dt.date(2020, 3, 23), -2.30, 2.7),    # pandemic crash
    (dt.date(2020, 3, 24), dt.date(2020, 8, 31), 0.42, 1.4),     # V-shaped recovery
    (dt.date(2022, 1, 3), dt.date(2022, 10, 12), -0.22, 1.4),    # rate-shock bear
    (dt.date(2022, 10, 13), dt.date(2023, 12, 29), 0.26, 1.05),  # post-bear recovery
    (dt.date(2025, 2, 3), dt.date(2025, 4, 30), -0.38, 1.6),     # late correction
]

# Policy-rate path (annualised, decimal) used for the risk-free series.
RATE_PATH = {
    2016: 0.004, 2017: 0.010, 2018: 0.019, 2019: 0.021, 2020: 0.004,
    2021: 0.003, 2022: 0.020, 2023: 0.049, 2024: 0.049, 2025: 0.039,
}


def business_days(start: dt.date, end: dt.date) -> list[dt.date]:
    """Weekdays between two dates.  Exchange holidays are ignored on purpose:
    the sample panel is a simulation, and a fake holiday calendar would only
    invite the reader to believe it is real."""
    days, cur = [], start
    while cur <= end:
        if cur.weekday() < 5:
            days.append(cur)
        cur += dt.timedelta(days=1)
    return days


def student_t(rng: random.Random, df: float = 5.0) -> float:
    """Standardised Student-t draw (unit variance) via the normal/chi mixture."""
    z = rng.gauss(0.0, 1.0)
    chi = sum(rng.gauss(0.0, 1.0) ** 2 for _ in range(int(df)))
    return z / math.sqrt(chi / df) * math.sqrt((df - 2.0) / df)


def regime_for(day: dt.date):
    for start, end, drift, volmult in REGIMES:
        if start <= day <= end:
            return drift, volmult
    return None, 1.0


def simulate_factors(days: list[dt.date], rng: random.Random) -> dict[str, list[float]]:
    """Daily factor returns.  EQ carries a GARCH(1,1) variance process so that
    volatility clusters the way it does in real equity data."""
    out = {f: [] for f in FACTORS}

    eq_target_var = (FACTOR_SPEC["EQ"]["vol"] ** 2) / TRADING_DAYS
    omega, alpha, beta = eq_target_var * 0.06, 0.09, 0.85
    var = eq_target_var
    last_resid = 0.0          # base-scale residual: this is what drives the GARCH

    for day in days:
        drift_override, volmult = regime_for(day)

        # --- equity factor: GARCH variance, fat-tailed shock ---------------
        # The recursion is fed the *base-scale* residual.  Feeding it the
        # regime-scaled residual instead makes alpha * volmult**2 + beta > 1
        # inside the crash regime and the variance process detonates.
        var = omega + alpha * last_resid ** 2 + beta * var
        base_vol = math.sqrt(var)
        last_resid = base_vol * student_t(rng)
        vol = base_vol * volmult
        drift = FACTOR_SPEC["EQ"]["drift"] if drift_override is None else drift_override
        out["EQ"].append(drift / TRADING_DAYS + last_resid * volmult)

        # --- remaining factors: Gaussian, mildly linked to the equity state -
        for f in FACTORS[1:]:
            spec = FACTOR_SPEC[f]
            dvol = spec["vol"] / math.sqrt(TRADING_DAYS)
            shock = rng.gauss(0.0, 1.0)
            if f == "RATE":
                # duration rallies in equity stress, except in the 2022 rate shock
                stress = -0.25 if day < dt.date(2022, 1, 1) or day > dt.date(2022, 10, 12) else 0.45
                shock += stress * out["EQ"][-1] / max(vol, 1e-9)
                if dt.date(2022, 1, 1) <= day <= dt.date(2022, 10, 12):
                    dvol *= 1.8
            if f == "EM" and volmult > 1.2:
                dvol *= 1.4
            out[f].append(spec["drift"] / TRADING_DAYS + dvol * shock)

    return out


def simulate_prices(days, factors, rng) -> dict[str, list[float]]:
    prices = {t: [100.0] for t in UNIVERSE}
    for i, _day in enumerate(days):
        for ticker, (_label, betas, alpha, idio, expense) in UNIVERSE.items():
            r = (alpha - expense) / TRADING_DAYS
            for f, b in betas.items():
                r += b * factors[f][i]
            if idio:
                r += idio / math.sqrt(TRADING_DAYS) * rng.gauss(0.0, 1.0)
            prices[ticker].append(prices[ticker][-1] * (1.0 + r))
    for t in prices:
        prices[t] = prices[t][1:]   # drop the seed value
    return prices


def write_prices(path: str, days, prices) -> None:
    tickers = list(UNIVERSE)
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["date"] + tickers)
        for i, day in enumerate(days):
            w.writerow([day.isoformat()] + [f"{prices[t][i]:.4f}" for t in tickers])


def write_riskfree(path: str, days) -> None:
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["date", "annualised_rate"])
        for day in days:
            w.writerow([day.isoformat(), f"{RATE_PATH[day.year]:.4f}"])


def write_metadata(path: str) -> None:
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["ticker", "description", "factor_exposures", "annual_expense_ratio"])
        for t, (label, betas, _a, _i, exp) in UNIVERSE.items():
            expo = "; ".join(f"{k}={v:+.2f}" for k, v in betas.items())
            w.writerow([t, label, expo, f"{exp:.4f}"])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="../shared-data", help="output directory")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    rng = random.Random(SEED)
    days = business_days(START, END)
    factors = simulate_factors(days, rng)
    prices = simulate_prices(days, factors, rng)

    write_prices(os.path.join(args.out, "prices_daily.csv"), days, prices)
    write_riskfree(os.path.join(args.out, "risk_free_daily.csv"), days)
    write_metadata(os.path.join(args.out, "universe.csv"), )

    print(f"{len(days)} trading days, {len(UNIVERSE)} series -> {args.out}")
    for t in UNIVERSE:
        total = prices[t][-1] / prices[t][0] - 1.0
        yrs = len(days) / TRADING_DAYS
        cagr = (1.0 + total) ** (1.0 / yrs) - 1.0
        print(f"  {t:6s} total {total:+8.1%}   CAGR {cagr:+6.2%}")


if __name__ == "__main__":
    main()
