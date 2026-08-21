"""Build the fictional three-statement history used by the fundamentals projects.

Why fictional?
--------------
Two projects here work off company accounts: a DCF valuation and a
financial-statement analysis.  Reproducing a real issuer's 10-K line items from
memory would be a fabrication risk (a number typed slightly wrong is worse than
no number at all), and redistributing a vendor's standardised fundamentals is a
licensing problem.  So the companies are invented, clearly labelled as invented,
and generated from explicit operating drivers.

What makes it worth reading anyway
----------------------------------
The statements are not hand-typed numbers that happen to look plausible.  They
are *articulated*: the income statement, balance sheet and cash flow statement
are all derived from one set of drivers, cash is the cash-flow-statement plug,
retained earnings roll forward, and the module refuses to emit anything unless

    assets - liabilities - equity == 0        (to the cent, every year)
    closing cash (BS) == closing cash (CFS)   (to the cent, every year)

which is exactly the discipline a real model needs.  Swapping in a real
company means replacing `data/drivers.py` with figures read off the filings;
none of the analysis code changes.

Companies
---------
MRDN  Meridian Beverage Group   mid-cap premium soft drinks; margin squeeze in
                                FY2022, debt-funded acquisition, then deleveraging
CALD  Calder & Company          larger, slower, higher margin, low leverage
VSSL  Vessel Drinks             small, fast-growing, thin margins, cash-hungry

Usage
-----
    python build_statements.py --out ../shared-data/fundamentals
"""

from __future__ import annotations

import argparse
import csv
import json
import os

YEARS = [2019, 2020, 2021, 2022, 2023, 2024]

# ---------------------------------------------------------------------------
# Operating drivers.  Everything downstream is derived from these.
# All monetary amounts are in millions of USD.
# ---------------------------------------------------------------------------

DRIVERS = {
    "MRDN": {
        "name": "Meridian Beverage Group",
        "sector": "Non-alcoholic beverages",
        "opening": {
            "revenue": 2_180.0, "ppe_net": 928.0, "goodwill": 402.0,
            "intangibles": 175.0, "cash": 214.0, "debt_lt": 640.0, "debt_st": 60.0,
            "share_capital": 520.0, "retained_earnings": 690.0, "treasury": 0.0,
            "other_assets": 96.0, "other_liabilities": 132.0, "deferred_tax": 88.0,
            "shares_out": 148.0, "min_cash_pct_revenue": 0.045, "revolver_spread": 0.010,
        },
        "by_year": {
            #        growth  gross%  sga%   rd%   dep%ppe capex%rev  DSO  DIO  DPO  tax%  int%  divPS  buyback  acq   debt_issue debt_repay
            2019: dict(growth=0.052, gross=0.412, sga=0.238, rd=0.011, dep=0.098, capex=0.052, dso=41, dio=62, dpo=58, tax=0.235, intrate=0.041, divps=0.62, buyback=40.0, acq=0.0, issue=0.0, repay=60.0),
            2020: dict(growth=0.018, gross=0.404, sga=0.244, rd=0.012, dep=0.099, capex=0.045, dso=44, dio=71, dpo=63, tax=0.232, intrate=0.036, divps=0.64, buyback=0.0, acq=0.0, issue=150.0, repay=40.0),
            2021: dict(growth=0.094, gross=0.418, sga=0.231, rd=0.012, dep=0.097, capex=0.058, dso=42, dio=66, dpo=60, tax=0.238, intrate=0.034, divps=0.68, buyback=85.0, acq=0.0, issue=0.0, repay=90.0),
            2022: dict(growth=0.081, gross=0.361, sga=0.243, rd=0.013, dep=0.101, capex=0.071, dso=46, dio=84, dpo=57, tax=0.244, intrate=0.049, divps=0.72, buyback=0.0, acq=430.0, issue=480.0, repay=45.0),
            2023: dict(growth=0.116, gross=0.379, sga=0.239, rd=0.013, dep=0.104, capex=0.061, dso=45, dio=76, dpo=59, tax=0.241, intrate=0.061, divps=0.76, buyback=0.0, acq=0.0, issue=0.0, repay=110.0),
            2024: dict(growth=0.047, gross=0.398, sga=0.234, rd=0.014, dep=0.103, capex=0.049, dso=43, dio=69, dpo=61, tax=0.239, intrate=0.058, divps=0.80, buyback=70.0, acq=0.0, issue=0.0, repay=140.0),
        },
    },
    "CALD": {
        "name": "Calder & Company",
        "sector": "Non-alcoholic beverages",
        "opening": {
            "revenue": 8_640.0, "ppe_net": 3_180.0, "goodwill": 2_740.0,
            "intangibles": 1_150.0, "cash": 1_420.0, "debt_lt": 2_900.0, "debt_st": 220.0,
            "share_capital": 1_900.0, "retained_earnings": 3_980.0, "treasury": 340.0,
            "other_assets": 410.0, "other_liabilities": 620.0, "deferred_tax": 395.0,
            "shares_out": 410.0, "min_cash_pct_revenue": 0.060, "revolver_spread": 0.008,
        },
        "by_year": {
            2019: dict(growth=0.031, gross=0.512, sga=0.286, rd=0.009, dep=0.089, capex=0.041, dso=38, dio=54, dpo=71, tax=0.222, intrate=0.036, divps=1.42, buyback=520.0, acq=0.0, issue=200.0, repay=180.0),
            2020: dict(growth=-0.014, gross=0.505, sga=0.291, rd=0.009, dep=0.090, capex=0.036, dso=40, dio=58, dpo=74, tax=0.219, intrate=0.031, divps=1.46, buyback=340.0, acq=0.0, issue=400.0, repay=210.0),
            2021: dict(growth=0.068, gross=0.518, sga=0.281, rd=0.010, dep=0.088, capex=0.043, dso=37, dio=55, dpo=72, tax=0.224, intrate=0.029, divps=1.52, buyback=610.0, acq=180.0, issue=150.0, repay=300.0),
            2022: dict(growth=0.059, gross=0.487, sga=0.288, rd=0.010, dep=0.091, capex=0.048, dso=39, dio=63, dpo=69, tax=0.228, intrate=0.038, divps=1.60, buyback=480.0, acq=0.0, issue=250.0, repay=260.0),
            2023: dict(growth=0.072, gross=0.499, sga=0.284, rd=0.010, dep=0.092, capex=0.046, dso=38, dio=59, dpo=70, tax=0.226, intrate=0.045, divps=1.68, buyback=560.0, acq=0.0, issue=100.0, repay=340.0),
            2024: dict(growth=0.041, gross=0.508, sga=0.281, rd=0.011, dep=0.091, capex=0.042, dso=37, dio=56, dpo=71, tax=0.225, intrate=0.043, divps=1.76, buyback=640.0, acq=0.0, issue=150.0, repay=290.0),
        },
    },
    "VSSL": {
        "name": "Vessel Drinks",
        "sector": "Non-alcoholic beverages",
        "opening": {
            "revenue": 386.0, "ppe_net": 121.0, "goodwill": 24.0,
            "intangibles": 31.0, "cash": 88.0, "debt_lt": 45.0, "debt_st": 12.0,
            "share_capital": 240.0, "retained_earnings": -46.0, "treasury": 0.0,
            "other_assets": 18.0, "other_liabilities": 27.0, "deferred_tax": 4.0,
            "shares_out": 62.0, "min_cash_pct_revenue": 0.055, "revolver_spread": 0.020,
        },
        "by_year": {
            2019: dict(growth=0.284, gross=0.352, sga=0.331, rd=0.021, dep=0.112, capex=0.094, dso=52, dio=88, dpo=51, tax=0.000, intrate=0.058, divps=0.0, equity_issue=70.0, buyback=0.0, acq=0.0, issue=30.0, repay=8.0),
            2020: dict(growth=0.176, gross=0.341, sga=0.338, rd=0.023, dep=0.115, capex=0.081, dso=56, dio=97, dpo=54, tax=0.000, intrate=0.052, divps=0.0, equity_issue=95.0, buyback=0.0, acq=0.0, issue=45.0, repay=10.0),
            2021: dict(growth=0.312, gross=0.358, sga=0.322, rd=0.022, dep=0.113, capex=0.102, dso=54, dio=92, dpo=52, tax=0.000, intrate=0.049, divps=0.0, equity_issue=150.0, buyback=0.0, acq=0.0, issue=60.0, repay=12.0),
            2022: dict(growth=0.241, gross=0.318, sga=0.334, rd=0.024, dep=0.118, capex=0.115, dso=59, dio=113, dpo=49, tax=0.000, intrate=0.071, divps=0.0, equity_issue=60.0, buyback=0.0, acq=0.0, issue=95.0, repay=14.0),
            2023: dict(growth=0.188, gross=0.336, sga=0.327, rd=0.023, dep=0.121, capex=0.088, dso=57, dio=104, dpo=51, tax=0.000, intrate=0.084, divps=0.0, equity_issue=190.0, buyback=0.0, acq=0.0, issue=55.0, repay=18.0),
            2024: dict(growth=0.142, gross=0.349, sga=0.318, rd=0.022, dep=0.119, capex=0.072, dso=55, dio=96, dpo=53, tax=0.060, intrate=0.079, divps=0.0, equity_issue=45.0, buyback=0.0, acq=0.0, issue=25.0, repay=22.0),
        },
    },
}

# Share prices at each fiscal year end (fictional, used for market-based ratios).
# Share prices at each fiscal year end (fictional).  These are not free
# parameters: they are set so that each company trades on a multiple its own
# fundamentals can support, because a valuation exercise run against an
# arbitrary price teaches nothing.  MRDN sits on a mid-teens to low-20s P/E, the
# larger and steadier CALD on a premium to it, and loss-making VSSL on EV/Sales.
YEAR_END_PRICE = {
    "MRDN": {2019: 22.40, 2020: 23.60, 2021: 31.80, 2022: 21.50, 2023: 24.80, 2024: 27.60},
    "CALD": {2019: 60.50, 2020: 61.70, 2021: 79.00, 2022: 63.00, 2023: 77.00, 2024: 91.00},
    "VSSL": {2019: 14.00, 2020: 19.50, 2021: 31.00, 2022: 11.00, 2023: 14.50, 2024: 17.30},
}

CASH_YIELD = 0.012          # interest earned on average cash balances
PREPAID_PCT = 0.018         # prepaid expenses as a share of revenue
ACCRUED_PCT = 0.061         # accrued liabilities as a share of cash operating costs
DEFERRED_TAX_DRIFT = 0.03   # deferred tax liability grows with the asset base


def _balance_opening(bs: dict) -> float:
    """Force the opening balance sheet to tie, and report the plug used."""
    assets = (bs["cash"] + bs["receivables"] + bs["inventory"] + bs["prepaid"]
              + bs["ppe_net"] + bs["goodwill"] + bs["intangibles"] + bs["other_assets"])
    liabilities = (bs["payables"] + bs["accrued"] + bs["debt_st"] + bs["debt_lt"]
                   + bs.get("revolver", 0.0) + bs["deferred_tax"] + bs["other_liabilities"])
    equity = bs["share_capital"] + bs["retained_earnings"] - bs["treasury"]
    gap = assets - liabilities - equity
    if gap < 0:
        bs["other_assets"] += -gap
    else:
        bs["other_liabilities"] += gap
    return gap


def build_company(ticker: str) -> dict:
    spec = DRIVERS[ticker]
    o = spec["opening"]

    rev_prev = o["revenue"]
    bs = {
        "cash": o["cash"], "ppe_net": o["ppe_net"], "goodwill": o["goodwill"],
        "intangibles": o["intangibles"], "other_assets": o["other_assets"],
        "other_liabilities": o["other_liabilities"], "deferred_tax": o["deferred_tax"],
        "debt_lt": o["debt_lt"], "debt_st": o["debt_st"],
        "share_capital": o["share_capital"], "retained_earnings": o["retained_earnings"],
        "treasury": o["treasury"],
    }
    bs["revolver"] = 0.0
    min_cash_pct = o.get("min_cash_pct_revenue", 0.05)
    revolver_spread = o.get("revolver_spread", 0.01)

    # Opening working capital, consistent with the first year's day counts.
    d0 = spec["by_year"][YEARS[0]]
    cogs_prev = rev_prev * (1 - d0["gross"])
    bs["receivables"] = d0["dso"] / 365 * rev_prev
    bs["inventory"] = d0["dio"] / 365 * cogs_prev
    bs["prepaid"] = PREPAID_PCT * rev_prev
    bs["payables"] = d0["dpo"] / 365 * cogs_prev
    bs["accrued"] = ACCRUED_PCT * (rev_prev * (d0["sga"] + d0["rd"]))
    shares = o["shares_out"]

    # The drivers pin down every opening line except one, so the opening
    # balance sheet needs a plug before it can be rolled forward.  Anything
    # else quietly pushes the imbalance into every later year.  The plug is
    # returned with the results rather than hidden.
    opening_plug = _balance_opening(bs)

    years_out = []
    for year in YEARS:
        d = spec["by_year"][year]
        open_bs = dict(bs)

        # ---------------- income statement --------------------------------
        revenue = rev_prev * (1 + d["growth"])
        cogs = revenue * (1 - d["gross"])
        gross_profit = revenue - cogs
        sga = revenue * d["sga"]
        rnd = revenue * d["rd"]
        depreciation = open_bs["ppe_net"] * d["dep"]
        amortisation = open_bs["intangibles"] * 0.11
        ebit = gross_profit - sga - rnd - depreciation - amortisation
        ebitda = ebit + depreciation + amortisation

        capex = revenue * d["capex"]
        debt_open = open_bs["debt_lt"] + open_bs["debt_st"]
        debt_close = debt_open + d["issue"] - d["repay"]
        term_interest = d["intrate"] * (debt_open + debt_close) / 2
        equity_issue = d.get("equity_issue", 0.0)
        min_cash = revenue * min_cash_pct

        # ---------------- working capital ---------------------------------
        receivables = d["dso"] / 365 * revenue
        inventory = d["dio"] / 365 * cogs
        prepaid = PREPAID_PCT * revenue
        payables = d["dpo"] / 365 * cogs
        accrued = ACCRUED_PCT * (sga + rnd)

        delta_wc = ((receivables - open_bs["receivables"])
                    + (inventory - open_bs["inventory"])
                    + (prepaid - open_bs["prepaid"])
                    - (payables - open_bs["payables"])
                    - (accrued - open_bs["accrued"]))

        # Interest income depends on the closing cash balance, which depends on
        # interest income.  One fixed-point pass removes the circularity to
        # well inside a cent; a real model would use an iterative calculation
        # switch for exactly this reason.
        # There is a second circularity on top of interest: if the year does not
        # fund itself the company draws its revolver, which costs interest,
        # which changes the cash it has to fund.  Both are resolved in the same
        # fixed-point pass.
        cash_close = open_bs["cash"]
        revolver_open = open_bs["revolver"]
        revolver_close = revolver_open
        for _ in range(60):
            interest_income = CASH_YIELD * (open_bs["cash"] + cash_close) / 2
            revolver_interest = ((d["intrate"] + revolver_spread)
                                 * (revolver_open + revolver_close) / 2)
            interest_expense = term_interest + revolver_interest
            pretax = ebit - interest_expense + interest_income
            tax = max(pretax, 0.0) * d["tax"]
            net_income = pretax - tax

            dividends = d["divps"] * shares
            cfo = (net_income + depreciation + amortisation - delta_wc
                   + (open_bs["deferred_tax"] * DEFERRED_TAX_DRIFT))
            cfi = -capex - d["acq"]
            cff_ex_revolver = (d["issue"] - d["repay"] + equity_issue
                               - dividends - d["buyback"])
            cash_before_revolver = open_bs["cash"] + cfo + cfi + cff_ex_revolver

            if cash_before_revolver < min_cash:
                revolver_draw = min_cash - cash_before_revolver
            else:
                revolver_draw = -min(revolver_open, cash_before_revolver - min_cash)
            new_revolver = revolver_open + revolver_draw
            new_cash = cash_before_revolver + revolver_draw
            converged = (abs(new_cash - cash_close) < 1e-10
                         and abs(new_revolver - revolver_close) < 1e-10)
            cash_close, revolver_close = new_cash, new_revolver
            if converged:
                break
        cff = cff_ex_revolver + (revolver_close - revolver_open)

        # ---------------- roll the balance sheet forward ------------------
        ppe_net = open_bs["ppe_net"] + capex - depreciation
        # An acquisition is split 70/30 goodwill/intangibles, a common outcome
        # for a brand-led deal in this sector.
        goodwill = open_bs["goodwill"] + d["acq"] * 0.70
        intangibles = open_bs["intangibles"] + d["acq"] * 0.30 - amortisation
        deferred_tax = open_bs["deferred_tax"] * (1 + DEFERRED_TAX_DRIFT)
        retained_earnings = open_bs["retained_earnings"] + net_income - dividends
        treasury = open_bs["treasury"] + d["buyback"]
        share_capital = open_bs["share_capital"] + equity_issue
        if d["buyback"]:
            shares -= d["buyback"] / YEAR_END_PRICE[ticker][year]
        if equity_issue:
            # Issued at the year-end price: the dilution shows up in EPS.
            shares += equity_issue / YEAR_END_PRICE[ticker][year]

        # Long-term / short-term split: keep 8% of closing debt current.
        debt_st = debt_close * 0.08
        debt_lt = debt_close - debt_st

        bs = {
            "cash": cash_close, "receivables": receivables, "inventory": inventory,
            "prepaid": prepaid, "ppe_net": ppe_net, "goodwill": goodwill,
            "intangibles": intangibles, "other_assets": open_bs["other_assets"],
            "payables": payables, "accrued": accrued, "debt_st": debt_st,
            "debt_lt": debt_lt, "deferred_tax": deferred_tax,
            "other_liabilities": open_bs["other_liabilities"],
            "revolver": revolver_close,
            "share_capital": share_capital,
            "retained_earnings": retained_earnings, "treasury": treasury,
        }

        assets = (bs["cash"] + bs["receivables"] + bs["inventory"] + bs["prepaid"]
                  + bs["ppe_net"] + bs["goodwill"] + bs["intangibles"] + bs["other_assets"])
        liabilities = (bs["payables"] + bs["accrued"] + bs["debt_st"] + bs["debt_lt"]
                       + bs["revolver"] + bs["deferred_tax"] + bs["other_liabilities"])
        equity = bs["share_capital"] + bs["retained_earnings"] - bs["treasury"]

        # The articulation check.  If this ever trips the model is wrong, and a
        # wrong model must not be allowed to emit numbers.
        if abs(assets - liabilities - equity) > 1e-6:
            raise AssertionError(
                f"{ticker} FY{year}: balance sheet out by {assets - liabilities - equity:,.6f}")

        price = YEAR_END_PRICE[ticker][year]
        years_out.append({
            "year": year,
            "income_statement": {
                "revenue": revenue, "cogs": cogs, "gross_profit": gross_profit,
                "sga": sga, "research_development": rnd,
                "depreciation": depreciation, "amortisation": amortisation,
                "ebitda": ebitda, "ebit": ebit,
                "interest_expense": interest_expense, "interest_income": interest_income,
                "pretax_income": pretax, "tax": tax, "net_income": net_income,
                "diluted_shares": shares, "eps": net_income / shares,
                "dividends_paid": dividends, "dividend_per_share": d["divps"],
            },
            "balance_sheet": dict(bs, total_assets=assets,
                                  total_liabilities=liabilities, total_equity=equity),
            "cash_flow": {
                "net_income": net_income,
                "depreciation_amortisation": depreciation + amortisation,
                "change_in_working_capital": -delta_wc,
                "deferred_tax_and_other": open_bs["deferred_tax"] * DEFERRED_TAX_DRIFT,
                "cash_from_operations": cfo,
                "capital_expenditure": -capex,
                "acquisitions": -d["acq"],
                "cash_from_investing": cfi,
                "debt_issued": d["issue"], "debt_repaid": -d["repay"],
                "revolver_movement": revolver_close - revolver_open,
                "equity_issued": equity_issue,
                "dividends": -dividends, "buybacks": -d["buyback"],
                "cash_from_financing": cff,
                "net_change_in_cash": cfo + cfi + cff,
                "opening_cash": open_bs["cash"], "closing_cash": cash_close,
                "free_cash_flow": cfo - capex,
            },
            "market": {
                "share_price": price,
                "market_cap": price * shares,
                "net_debt": bs["debt_st"] + bs["debt_lt"] + bs["revolver"] - bs["cash"],
                "enterprise_value": (price * shares + bs["debt_st"] + bs["debt_lt"]
                                     + bs["revolver"] - bs["cash"]),
            },
        })
        rev_prev = revenue

    return {"ticker": ticker, "name": spec["name"], "sector": spec["sector"],
            "currency": "USD millions (except per-share data)",
            "disclaimer": "Fictional company. Figures generated by build_statements.py.",
            "opening_balance_plug": round(opening_plug, 4),
            "years": years_out}


def flatten_to_csv(companies: dict, path: str) -> None:
    rows = []
    for tk, co in companies.items():
        for y in co["years"]:
            row = {"ticker": tk, "year": y["year"]}
            for block in ("income_statement", "balance_sheet", "cash_flow", "market"):
                for k, v in y[block].items():
                    row[k] = round(v, 4)
            rows.append(row)
    fields = list(rows[0])
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="../shared-data/fundamentals")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    companies = {tk: build_company(tk) for tk in DRIVERS}
    with open(os.path.join(args.out, "financials.json"), "w") as fh:
        json.dump(companies, fh, indent=2)
    flatten_to_csv(companies, os.path.join(args.out, "financials.csv"))

    print(f"wrote {len(companies)} companies x {len(YEARS)} years -> {args.out}")
    for tk, co in companies.items():
        last = co["years"][-1]
        i, b, c = last["income_statement"], last["balance_sheet"], last["cash_flow"]
        print(f"  {tk} FY{last['year']}: revenue {i['revenue']:>9,.0f}  "
              f"EBIT margin {i['ebit'] / i['revenue']:>6.1%}  "
              f"EPS {i['eps']:>6.2f}  FCF {c['free_cash_flow']:>8,.0f}  "
              f"net debt/EBITDA {last['market']['net_debt'] / i['ebitda']:>5.2f}x  "
              f"BS check {b['total_assets'] - b['total_liabilities'] - b['total_equity']:+.2e}")


if __name__ == "__main__":
    main()
