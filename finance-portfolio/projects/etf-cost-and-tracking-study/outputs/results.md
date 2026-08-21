# ETF cost and tracking study — generated output

_Every figure below is produced by `python analysis.py`. The price history is simulated; see `data/README.md`._

## 1. The funds

| Ticker | Mandate | Expense ratio | 10-year CAGR | Index CAGR | Difference |
| :--- | ---: | ---: | ---: | ---: | ---: |
| LCAP | Core US Large-Cap | 0.03% | 5.89% | 5.87% | +0.02pp |
| BRDX | Total US Market | 0.09% | 5.59% | 5.87% | -0.29pp |
| SMRT | US Multifactor | 0.35% | 5.23% | 5.87% | -0.65pp |

## 2. Tracking: level versus volatility

Tracking **difference** is how much return the fund gave up. Tracking **error** is how reliably it gave up that amount. They answer different questions and a fund can be good at one and bad at the other.

| Fund | Expense ratio | Tracking difference p.a. | Tracking error p.a. | Unexplained | Worst rolling year | Best rolling year | Beta | R² |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| LCAP | 0.03% | +0.02% | 0.12% | +0.05% | -0.31% | +0.24% | 1.000 | 1.0000 |
| BRDX | 0.09% | -0.29% | 1.17% | -0.20% | -4.16% | +3.22% | 0.980 | 0.9964 |
| SMRT | 0.35% | -0.65% | 4.45% | -0.30% | -19.77% | +12.19% | 0.917 | 0.9449 |

'Unexplained' is the tracking difference plus the expense ratio: what is left after fees have been accounted for. A well-run index fund should show a small number here. A large one means sampling error, cash drag, securities-lending revenue, or a portfolio that does not match the index it is quoted against.

## 3. What the fee costs over a lifetime

$100,000 invested at an assumed 7.00% gross annual return, with each fund's fee deducted. Same gross return for all three: a fund gets no credit for outperformance it has not demonstrated.

| Fund | Value 10y | Value 20y | Value 30y | Fees paid 10y | Fees paid 20y | Fees paid 30y |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| LCAP (0.03%) | $196,164 | $384,804 | $754,849 | $551 | $2,164 | $6,377 |
| BRDX (0.09%) | $195,067 | $380,510 | $742,249 | $1,648 | $6,458 | $18,976 |
| SMRT (0.35%) | $190,374 | $362,424 | $689,963 | $6,341 | $24,544 | $71,263 |

| Comparison | Value |
| :--- | ---: |
| Fee gap, SMRT over LCAP | 0.32% |
| Extra cost over 30 years | $64,886 |
| As a share of the ending LCAP balance | 8.6% |
| Gross outperformance SMRT needs each year, just to draw level | 0.32% |
| SMRT's actual annual difference to the index over the sample | -0.65% |

## 4. How different are they really?

| Pair | Return correlation | Assumed holdings overlap |
| :--- | ---: | ---: |
| LCAP vs BRDX | 0.9982 | 89% |
| LCAP vs SMRT | 0.9720 | 68% |
| BRDX vs SMRT | 0.9764 | 79% |

Holdings overlap uses the stand-in capitalisation buckets in `analysis.py`, not real holdings files — it shows the calculation, not a fact about any fund. Return correlation is computed from the price data and is a fact about the sample.

## 5. Risk and return of each fund

| Fund | CAGR | Volatility | Sharpe | Max drawdown | Information ratio vs index |
| :--- | ---: | ---: | ---: | ---: | ---: |
| LCAP | 5.89% | 18.83% | 0.28 | -40.34% | +0.17 |
| BRDX | 5.59% | 18.49% | 0.27 | -41.32% | -0.28 |
| SMRT | 5.23% | 17.76% | 0.25 | -37.93% | -0.18 |
| IDXUS (index, not investable) | 5.87% | 18.83% | 0.28 | -40.34% | — |
