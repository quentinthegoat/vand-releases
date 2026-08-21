# Portfolio performance and risk — generated output

_Every figure below is produced by `python analysis.py`. The price history is simulated; see `data/README.md`._

## 1. Mandate

| Sleeve | Portfolio weight | Benchmark weight |
| :--- | ---: | ---: |
| LCAP | 35% | 60% |
| SCAP | 10% | 0% |
| INTL | 12% | 0% |
| EMKT | 8% | 0% |
| BNDX | 25% | 40% |
| REIT | 6% | 0% |
| GOLD | 4% | 0% |
| **Total** | 100% | 100% |

Rebalanced quarterly, with 5bp of one-way trading cost charged on turnover. Period: 2016-01-05 to 2025-12-31 (10.3 years, 2,607 trading days).

## 2. Headline performance

|  | CAGR | Volatility | Sharpe | Sortino | Max DD | VaR 95% | CVaR 95% | Skew | Excess kurtosis | Positive days |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Portfolio | 5.34% | 13.16% | 0.30 | 0.41 | -33.14% | 1.18% | 1.96% | -0.35 | +6.2 | 51.7% |
| Benchmark 60/40 | 5.02% | 11.72% | 0.29 | 0.41 | -29.56% | 1.06% | 1.75% | -0.40 | +6.4 | 52.1% |
| LCAP | 5.89% | 18.83% | 0.28 | 0.40 | -40.34% | 1.69% | 2.81% | -0.27 | +6.2 | 51.7% |
| SCAP | 6.15% | 22.84% | 0.28 | 0.40 | -52.38% | 2.13% | 3.32% | -0.16 | +4.7 | 51.3% |
| INTL | 3.59% | 16.89% | 0.16 | 0.23 | -35.33% | 1.60% | 2.50% | -0.21 | +4.4 | 50.7% |
| EMKT | 7.72% | 20.69% | 0.36 | 0.50 | -46.85% | 2.00% | 3.00% | -0.30 | +3.3 | 52.9% |
| BNDX | 2.54% | 6.31% | 0.08 | 0.12 | -18.28% | 0.63% | 0.86% | -0.17 | +1.5 | 51.3% |
| REIT | 6.30% | 16.71% | 0.32 | 0.45 | -36.37% | 1.54% | 2.44% | -0.25 | +5.1 | 51.7% |
| GOLD | 2.08% | 14.60% | 0.06 | 0.09 | -38.49% | 1.51% | 1.90% | -0.06 | -0.0 | 50.8% |

## 3. Versus the benchmark

| Measure | Value | Reading |
| :--- | ---: | :--- |
| Beta | 1.11 | sensitivity to benchmark excess returns |
| Annualised alpha | 0.11% | CAPM intercept against the 60/40 |
| R-squared | 0.977 | share of variance explained |
| Tracking error | 2.36% | volatility of the difference |
| Information ratio | 0.21 | active return per unit of tracking error |
| Up capture | 110% | of benchmark gains captured |
| Down capture | 110% | of benchmark losses taken |

## 4. Drawdown

|  | Worst drawdown | Peak | Trough | Recovered | Length (trading days) |
| :--- | ---: | ---: | ---: | ---: | ---: |
| Portfolio | -33.14% | 2020-11-24 | 2023-04-17 | not recovered | 1,331 |
| Benchmark | -29.56% | 2020-11-24 | 2023-04-17 | 2025-01-17 | 1,083 |

## 5. Calendar year returns

| Year | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Portfolio | 9.4% | 7.0% | 3.2% | 19.4% | 29.8% | -5.9% | -22.9% | 9.2% | 21.9% | -5.2% |
| Benchmark | 7.9% | 6.7% | 3.8% | 17.0% | 27.4% | -1.2% | -22.9% | 6.9% | 22.2% | -6.4% |
| Difference | +1.5pp | +0.3pp | -0.6pp | +2.4pp | +2.3pp | -4.7pp | +0.0pp | +2.3pp | -0.3pp | +1.2pp |

## 6. Attribution: where the return came from, and where the risk is

| Sleeve | Weight | Asset CAGR | Contribution to total return | Share of return | Share of portfolio risk | Risk ÷ weight |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| LCAP | 35% | 5.89% | 31.20% | 44% | 49% | 1.41x |
| SCAP | 10% | 6.15% | 10.11% | 14% | 16% | 1.63x |
| INTL | 12% | 3.59% | 6.55% | 9% | 14% | 1.21x |
| EMKT | 8% | 7.72% | 8.18% | 11% | 11% | 1.33x |
| BNDX | 25% | 2.54% | 8.98% | 13% | 2% | 0.08x |
| REIT | 6% | 6.30% | 5.22% | 7% | 7% | 1.21x |
| GOLD | 4% | 2.08% | 1.23% | 2% | -0% | -0.03x |

Diversification ratio: **1.20** (weighted average sleeve volatility ÷ portfolio volatility; 1.00 means diversification bought nothing).

## 7. Does rebalancing pay?

| Policy | CAGR | Volatility | Sharpe | Max DD | Rebalances | Total turnover | Cost drag p.a. |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| monthly | 5.36% | 13.13% | 0.30 | -32.90% | 119 | 1.25x | 0.012% |
| quarterly | 5.34% | 13.16% | 0.30 | -33.14% | 39 | 0.73x | 0.007% |
| annual | 5.20% | 13.06% | 0.29 | -33.07% | 9 | 0.28x | 0.003% |
| never | 4.96% | 14.03% | 0.26 | -35.79% | 0 | 0.00x | 0.000% |

## 8. Correlation matrix (daily returns, full period)

|  | LCAP | SCAP | INTL | EMKT | BNDX | REIT | GOLD |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| LCAP | 1.00 | 0.93 | 0.93 | 0.81 | 0.03 | 0.93 | -0.08 |
| SCAP | 0.93 | 1.00 | 0.86 | 0.75 | 0.04 | 0.87 | -0.07 |
| INTL | 0.93 | 0.86 | 1.00 | 0.78 | 0.04 | 0.86 | -0.07 |
| EMKT | 0.81 | 0.75 | 0.78 | 1.00 | 0.04 | 0.76 | -0.06 |
| BNDX | 0.03 | 0.04 | 0.04 | 0.04 | 1.00 | 0.22 | 0.03 |
| REIT | 0.93 | 0.87 | 0.86 | 0.76 | 0.22 | 1.00 | -0.06 |
| GOLD | -0.08 | -0.07 | -0.07 | -0.06 | 0.03 | -0.06 | 1.00 |
