# Portfolio optimisation — generated output

_Every figure below is produced by `python analysis.py`. The price history is simulated; see `data/README.md`._

## 1. Asset inputs (full period, annualised)

| Asset | Return | Volatility | Sharpe (rf 2.5%) |
| :--- | ---: | ---: | ---: |
| LCAP | 5.89% | 18.83% | 0.18 |
| SCAP | 6.15% | 22.84% | 0.16 |
| INTL | 3.59% | 16.89% | 0.06 |
| EMKT | 7.72% | 20.69% | 0.25 |
| BNDX | 2.54% | 6.31% | 0.01 |
| REIT | 6.30% | 16.71% | 0.23 |
| GOLD | 2.08% | 14.60% | -0.03 |

## 2. In-sample optimal portfolios

| Rule | LCAP | SCAP | INTL | EMKT | BNDX | REIT | GOLD | Return | Volatility | Sharpe |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Equal weight (1/N) | 14% | 14% | 14% | 14% | 14% | 14% | 14% | 4.90% | 12.95% | 0.19 |
| Inverse volatility | 11% | 9% | 12% | 10% | 32% | 12% | 14% | 4.26% | 9.99% | 0.18 |
| Risk parity | 7% | 6% | 8% | 7% | 42% | 8% | 21% | 3.66% | 7.71% | 0.15 |
| Minimum variance | 0% | 0% | 10% | 0% | 75% | 0% | 14% | 2.60% | 5.54% | 0.02 |
| Max Sharpe (sample cov) | 0% | 0% | 0% | 62% | 0% | 38% | 0% | 7.18% | 18.09% | 0.26 |
| Max Sharpe (shrunk cov) | 0% | 0% | 0% | 62% | 0% | 38% | 0% | 7.18% | 18.12% | 0.26 |

These are the portfolios you would have chosen **if you had known the answer in advance**. Section 4 is what happens when you do not.

## 3. How hard is the estimation problem?

| Window (days) | Observations per asset | Ledoit-Wolf shrinkage intensity | Condition number of sample covariance |
| :--- | ---: | ---: | ---: |
| 126 | 18 | 4.1% | 77 |
| 252 | 36 | 4.4% | 101 |
| 504 | 72 | 1.8% | 103 |
| 756 | 108 | 1.1% | 107 |
| 1,260 | 180 | 1.2% | 151 |
| 2,607 | 372 | 0.4% | 170 |

Shrinkage intensity falls as the window lengthens, which is the estimator working correctly: with seven assets and three years of daily data there is little estimation error left to shrink away. Shrinkage is a fix for a hard estimation problem, and this is not one.

## 4. Walk-forward, out of sample

Three-year trailing estimation window, quarterly rebalancing, 5bp one-way cost, weights drift between rebalances. Test period 2018-11-28 to 2025-12-31 (7.3 years).

| Rule | CAGR | Volatility | Sharpe | Sortino | Max DD | Turnover per rebalance | Weight churn |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 60/40 | 4.12% | 12.73% | 0.17 | 0.24 | -29.56% | 4.3% | 0.0% |
| Equal weight (1/N) | 4.15% | 14.04% | 0.17 | 0.24 | -33.56% | 2.2% | 0.0% |
| Inverse volatility | 3.57% | 10.89% | 0.13 | 0.19 | -27.26% | 3.1% | 1.1% |
| Risk parity | 2.81% | 8.39% | 0.06 | 0.08 | -22.57% | 4.0% | 1.6% |
| Max Sharpe (shrunk cov) | 1.81% | 12.73% | -0.00 | -0.00 | -37.95% | 28.0% | 28.1% |
| Max Sharpe (sample cov) | 1.81% | 12.68% | -0.00 | -0.00 | -37.73% | 28.7% | 28.8% |
| Minimum variance | 1.71% | 5.88% | -0.13 | -0.18 | -16.83% | 4.6% | 1.9% |

| Reference | CAGR | Volatility | Sharpe | Max DD |
| :--- | ---: | ---: | ---: | ---: |
| Look-ahead max Sharpe (**not investable**) | 4.51% | 19.37% | 0.19 | -39.21% |

The look-ahead row is the same optimiser fitted to the whole sample and then 'tested' on part of it. It is included precisely because it is cheating: the gap between it and the honest walk-forward rows is the size of the error a backtest makes when it forgets what it was allowed to know.
