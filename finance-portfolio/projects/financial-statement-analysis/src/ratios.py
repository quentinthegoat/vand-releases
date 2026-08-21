"""Ratio analysis over an articulated three-statement history.

Design notes that matter more than the formulas:

* **Balance-sheet items are averaged.** Every ratio that divides a flow (a year
  of revenue, a year of profit) by a stock (assets, equity, invested capital)
  uses the average of opening and closing balances.  Using the closing balance
  flatters any company that grew its balance sheet during the year, and
  Meridian's FY2022 acquisition would make that error large and one-sided.
* **Ratios return None rather than a number when the denominator is
  meaningless.** A ROE computed on negative equity, or an interest-coverage
  ratio on a company with no debt, is not a small number - it is not a number.
  Printing "n/m" is the honest output, and it keeps a nonsense value out of any
  average or chart downstream.
"""

from __future__ import annotations

from dataclasses import dataclass

DAYS = 365


def safe_div(a: float, b: float, positive_denominator: bool = True) -> float | None:
    if b == 0 or (positive_denominator and b < 0):
        return None
    return a / b


def avg(open_value: float, close_value: float) -> float:
    return (open_value + close_value) / 2.0


@dataclass
class YearRatios:
    year: int

    # --- profitability -----------------------------------------------------
    gross_margin: float
    ebitda_margin: float
    ebit_margin: float
    net_margin: float
    roe: float | None
    roa: float | None
    roic: float | None
    roce: float | None

    # --- efficiency --------------------------------------------------------
    asset_turnover: float
    fixed_asset_turnover: float
    dso: float
    dio: float
    dpo: float
    cash_conversion_cycle: float

    # --- liquidity and solvency -------------------------------------------
    current_ratio: float
    quick_ratio: float
    interest_coverage: float | None
    net_debt_ebitda: float | None
    debt_to_equity: float | None
    equity_multiplier: float | None

    # --- cash and earnings quality ----------------------------------------
    cfo_to_ebitda: float | None
    fcf_conversion: float | None
    accrual_ratio: float
    capex_to_depreciation: float

    # --- DuPont ------------------------------------------------------------
    tax_burden: float | None
    interest_burden: float | None
    dupont_check: float | None

    # --- distress and growth ----------------------------------------------
    altman_z: float
    sustainable_growth: float | None
    payout_ratio: float | None


def compute_year(current: dict, previous: dict | None) -> YearRatios:
    """All ratios for one fiscal year.  `previous` supplies opening balances;
    for the first year in the file, closing balances are used and the reader is
    told so in the write-up."""
    i, b, c, m = (current["income_statement"], current["balance_sheet"],
                  current["cash_flow"], current["market"])
    pb = previous["balance_sheet"] if previous else b

    revenue = i["revenue"]
    ebitda, ebit, ni = i["ebitda"], i["ebit"], i["net_income"]
    total_debt = b["debt_st"] + b["debt_lt"] + b["revolver"]
    prev_debt = pb["debt_st"] + pb["debt_lt"] + pb["revolver"]

    avg_assets = avg(pb["total_assets"], b["total_assets"])
    avg_equity = avg(pb["total_equity"], b["total_equity"])
    avg_receivables = avg(pb["receivables"], b["receivables"])
    avg_inventory = avg(pb["inventory"], b["inventory"])
    avg_payables = avg(pb["payables"], b["payables"])
    avg_ppe = avg(pb["ppe_net"], b["ppe_net"])

    # Invested capital: the capital the operating business actually uses.
    # Excess cash is stripped out on both sides, otherwise a cash-rich company
    # looks like a poor allocator of capital it has not deployed.
    invested = total_debt + b["total_equity"] - b["cash"]
    prev_invested = prev_debt + pb["total_equity"] - pb["cash"]
    avg_invested = avg(prev_invested, invested)

    effective_tax = i["tax"] / i["pretax_income"] if i["pretax_income"] > 0 else 0.0
    nopat = ebit * (1.0 - effective_tax)

    current_assets = b["cash"] + b["receivables"] + b["inventory"] + b["prepaid"]
    current_liabilities = b["payables"] + b["accrued"] + b["debt_st"] + b["revolver"]

    dso = avg_receivables / revenue * DAYS
    dio = avg_inventory / i["cogs"] * DAYS
    dpo = avg_payables / i["cogs"] * DAYS

    working_capital = current_assets - current_liabilities
    total_liabilities = b["total_liabilities"]

    # Altman Z for public manufacturers.  Below 1.81 is the distress zone,
    # above 2.99 the safe zone; between them is the "grey zone" the model's
    # author himself described as unreliable.
    z = (1.2 * working_capital / b["total_assets"]
         + 1.4 * b["retained_earnings"] / b["total_assets"]
         + 3.3 * ebit / b["total_assets"]
         + 0.6 * m["market_cap"] / total_liabilities
         + 1.0 * revenue / b["total_assets"])

    payout = safe_div(i["dividends_paid"], ni)
    roe = safe_div(ni, avg_equity)

    return YearRatios(
        year=current["year"],
        gross_margin=i["gross_profit"] / revenue,
        ebitda_margin=ebitda / revenue,
        ebit_margin=ebit / revenue,
        net_margin=ni / revenue,
        roe=roe,
        roa=safe_div(ni, avg_assets),
        roic=safe_div(nopat, avg_invested),
        roce=safe_div(ebit, avg_assets - (b["payables"] + b["accrued"])),
        asset_turnover=revenue / avg_assets,
        fixed_asset_turnover=revenue / avg_ppe,
        dso=dso, dio=dio, dpo=dpo,
        cash_conversion_cycle=dso + dio - dpo,
        current_ratio=current_assets / current_liabilities,
        quick_ratio=(current_assets - b["inventory"]) / current_liabilities,
        interest_coverage=safe_div(ebit, i["interest_expense"]),
        net_debt_ebitda=safe_div(m["net_debt"], ebitda),
        debt_to_equity=safe_div(total_debt, b["total_equity"]),
        equity_multiplier=safe_div(avg_assets, avg_equity),
        cfo_to_ebitda=safe_div(c["cash_from_operations"], ebitda),
        fcf_conversion=safe_div(c["free_cash_flow"], ni),
        # Sloan's accrual ratio: the share of earnings that is accounting rather
        # than cash.  Persistently high positive values are the single most
        # studied predictor of disappointing future returns.
        accrual_ratio=(ni - c["cash_from_operations"]) / avg_assets,
        capex_to_depreciation=-c["capital_expenditure"] / c["depreciation_amortisation"],
        tax_burden=safe_div(ni, i["pretax_income"]),
        interest_burden=safe_div(i["pretax_income"], ebit),
        dupont_check=roe,
        altman_z=z,
        sustainable_growth=(roe * (1 - payout)) if (roe is not None and payout is not None) else None,
        payout_ratio=payout,
    )


def compute_history(company: dict) -> list[YearRatios]:
    years = company["years"]
    return [compute_year(y, years[k - 1] if k else None) for k, y in enumerate(years)]


def dupont_five(current: dict, previous: dict | None) -> dict[str, float | None]:
    """ROE = tax burden x interest burden x EBIT margin x asset turnover x leverage.

    The five-step version is worth the extra arithmetic because it separates
    three things the three-step version blends: how much of operating profit
    survives interest, how much survives tax, and how much of the return is
    simply borrowed."""
    i, b = current["income_statement"], current["balance_sheet"]
    pb = previous["balance_sheet"] if previous else b
    avg_assets = avg(pb["total_assets"], b["total_assets"])
    avg_equity = avg(pb["total_equity"], b["total_equity"])

    tax_burden = safe_div(i["net_income"], i["pretax_income"])
    interest_burden = safe_div(i["pretax_income"], i["ebit"])
    ebit_margin = i["ebit"] / i["revenue"]
    turnover = i["revenue"] / avg_assets
    leverage = safe_div(avg_assets, avg_equity)

    product = None
    if None not in (tax_burden, interest_burden, leverage):
        product = tax_burden * interest_burden * ebit_margin * turnover * leverage

    return {"tax_burden": tax_burden, "interest_burden": interest_burden,
            "ebit_margin": ebit_margin, "asset_turnover": turnover,
            "leverage": leverage, "roe": product,
            "reported_roe": safe_div(i["net_income"], avg_equity)}


def common_size_income(company: dict) -> list[dict[str, float]]:
    """Every income-statement line as a share of revenue."""
    out = []
    for y in company["years"]:
        i = y["income_statement"]
        r = i["revenue"]
        out.append({
            "year": y["year"],
            "revenue": 1.0,
            "cogs": -i["cogs"] / r,
            "gross_profit": i["gross_profit"] / r,
            "sga": -i["sga"] / r,
            "research_development": -i["research_development"] / r,
            "depreciation_amortisation": -(i["depreciation"] + i["amortisation"]) / r,
            "ebit": i["ebit"] / r,
            "net_interest": -(i["interest_expense"] - i["interest_income"]) / r,
            "tax": -i["tax"] / r,
            "net_income": i["net_income"] / r,
        })
    return out


def growth_rates(company: dict, field: str, block: str = "income_statement") -> list[float | None]:
    values = [y[block][field] for y in company["years"]]
    out: list[float | None] = [None]
    for k in range(1, len(values)):
        prev = values[k - 1]
        out.append((values[k] / prev - 1.0) if prev > 0 else None)
    return out


def cagr(company: dict, field: str, block: str = "income_statement") -> float | None:
    values = [y[block][field] for y in company["years"]]
    if values[0] <= 0 or values[-1] <= 0:
        return None
    n = len(values) - 1
    return (values[-1] / values[0]) ** (1.0 / n) - 1.0
