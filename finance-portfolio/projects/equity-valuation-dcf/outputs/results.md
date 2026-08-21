# MRDN valuation - generated output

_Every figure below is produced by `python analysis.py`. Meridian Beverage Group is a fictional company; see `data/README.md`._

## 1. Cost of capital

| Input | Value | Source |
| :--- | ---: | ---: |
| Risk-free rate | 4.10% | 10-year government yield |
| Equity risk premium | 5.00% | mature-market implied ERP |
| Unlevered beta | 0.72 | bottom-up, beverages |
| Levered beta | 0.89 | Hamada at current D/E |
| Size premium | 0.50% | mid-cap adjustment |
| Cost of equity | 9.03% | CAPM |
| Pre-tax cost of debt | 6.14% | FY24 interest expense / average debt |
| After-tax cost of debt | 4.68% | at 23.90% tax |
| Weight of equity / debt | 76.8% / 23.2% | market values |
| **WACC** | **8.02%** |  |

## 2. Free cash flow forecast (USD m)

| FY | Revenue | EBIT % | EBIT | NOPAT | D&A | Capex | ΔNWC | FCFF | DF | PV |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2025 | 3,387 | 10.9% | 369 | 281 | 169 | -176 | -23 | 251 | 0.962 | 242 |
| 2026 | 3,543 | 11.3% | 400 | 305 | 174 | -181 | -22 | 276 | 0.891 | 245 |
| 2027 | 3,692 | 11.6% | 428 | 326 | 177 | -181 | -21 | 301 | 0.825 | 248 |
| 2028 | 3,832 | 11.8% | 452 | 344 | 184 | -180 | -20 | 328 | 0.763 | 250 |
| 2029 | 3,966 | 11.9% | 472 | 359 | 186 | -182 | -19 | 344 | 0.707 | 243 |

## 3. Value bridge

| Component | Gordon growth | Exit multiple |
| :--- | ---: | ---: |
| PV of explicit forecast | 1,229 | 1,229 |
| PV of terminal value | 4,312 | 4,421 |
| Terminal share of EV | 77.8% | 78.2% |
| Enterprise value | 5,541 | 5,650 |
| Less net debt | -1,030 | -1,030 |
| Equity value | 4,511 | 4,620 |
| Diluted shares (m) | 141.0 | 141.0 |
| **Value per share** | **$31.99** | **$32.76** |
| Cross-check | implies 9.3x exit EBITDA | implies 2.38% terminal growth |

## 4. Scenarios

| Scenario | Revenue growth shift | EBIT margin shift | Terminal g | Value / share | vs price | Probability |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| Bear | -2.2% | -1.7% | 1.50% | $21.23 | -23.1% | 25% |
| Base | +0.0% | +0.0% | 2.25% | $31.99 | +15.9% | 50% |
| Bull | +1.8% | +1.4% | 2.75% | $42.99 | +55.7% | 25% |

Probability-weighted value **$32.05** against a market price of $27.60 (+16.1%).

## 5. Sensitivity

### Value per share: WACC x terminal growth

| WACC \ g | 1.25% | 1.75% | 2.25% | 2.75% | 3.25% |
| :--- | ---: | ---: | ---: | ---: | ---: |
| 7.02% | $33.19 | $36.36 | $40.19 | $44.92 | $50.91 |
| 7.52% | $29.97 | $32.59 | $35.70 | $39.47 | $44.13 |
| 8.02% | $27.22 | $29.42 | $31.99 | $35.06 | $38.77 |
| 8.52% | $24.85 | $26.71 | $28.87 | $31.41 | $34.43 |
| 9.02% | $22.79 | $24.38 | $26.22 | $28.34 | $30.84 |

### Value per share: FY25 EBIT margin x parallel growth shift

| Margin \ growth | -2.0% | -1.0% | +0.0% | +1.0% | +2.0% |
| :--- | ---: | ---: | ---: | ---: | ---: |
| 9.90% | $26.60 | $27.54 | $28.49 | $29.46 | $30.44 |
| 10.90% | $29.81 | $30.89 | $31.99 | $33.12 | $34.26 |
| 11.90% | $33.02 | $34.24 | $35.49 | $36.77 | $38.08 |
| 12.90% | $36.23 | $37.60 | $39.00 | $40.43 | $41.89 |

## 6. Reverse DCF

Holding the base-case margin path, working capital intensity and a 2.25% terminal growth rate, the market price of $27.60 is consistent with uniform revenue growth of **0.45%** a year through FY29, against a base case averaging 4.22%.

## 7. Monte Carlo (20,000 trials)

| Statistic | Value per share |
| :--- | ---: |
| 5th percentile | $23.11 |
| 25th percentile | $28.01 |
| Median | $31.98 |
| 75th percentile | $36.41 |
| 95th percentile | $44.16 |
| Mean | $32.55 |
| P(value > market price) | 77.4% |

## 8. Trading comparables

| Company | Mkt cap | EV | EV/Sales | EV/EBITDA | EV/EBIT | P/E | FCF yield | Rev growth | EBIT margin | Net debt/EBITDA |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| MRDN Meridian Beverage Group | 3,892 | 4,922 | 1.53x | 10.2x | 14.5x | 19.1x | 6.2% | 4.7% | 10.5% | 2.1x |
| CALD Calder & Company | 33,329 | 35,037 | 3.16x | 14.6x | 17.7x | 23.0x | 4.4% | 4.1% | 17.9% | 0.7x |
| VSSL Vessel Drinks | 1,693 | 1,841 | 1.43x | 158.9x | n/m | n/m | -6.5% | 14.2% | -2.8% | 12.7x |

| Peer median multiple | Level | Peers used | Implied MRDN value / share |
| :--- | ---: | ---: | ---: |
| EV/EBITDA | 14.6x | 1 | $42.91 |
| EV/Sales | 2.30x | 2 | $45.20 |
| P/E | 23.0x | 1 | $33.22 |

Excluded as not meaningful (denominator too close to zero): VSSL. With only two peers, a median that survives one exclusion is a single observation wearing a statistic's clothes - the comps here are a sanity check on the DCF, not an independent valuation.
