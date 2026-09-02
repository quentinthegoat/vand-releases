# Data

## This project uses real data

Unlike the other five projects in this portfolio, the figures here are **real**, transcribed
by hand from a primary source:

> **Ryanair FY26 Results** — Condensed Consolidated Preliminary Financial Statements
> (unaudited), published 18 May 2026.
> https://investor.ryanair.com/wp-content/uploads/2026/05/FY26-Ryanair-Results.pdf

Two caveats the issuer itself states, which carry through to every number in this project:

1. The statements are **preliminary and unaudited**. The annual report may restate them.
2. FY26 operating profit includes an **€85m exceptional charge** (a provision for
   approximately 33% of an Italian AGCM fine). The model works off the pre-exceptional
   figure, and both are carried in the JSON so either can be used.

The share price of **€22.845** is the Euronext Dublin quote on 2 September 2026, supplied by
the repository owner and cross-checked against the Nasdaq ADR market capitalisation of
approximately $29bn — which implies €24.3bn at ~1.17 USD/EUR against 1,064.4m diluted shares,
consistent to within 2%.

## Transcription is the main risk, so it is tested

Hand-copying figures out of a PDF is the most likely defect in this project. `tests/` asserts
that the transcribed statements **foot**:

- scheduled + ancillary revenue = total revenue
- the seven operating cost lines = operating expenses before exceptional
- revenue − operating expenses = operating profit (both pre- and post-exceptional)
- operating profit + net finance income + FX = profit before tax
- profit before tax + tax = profit after tax
- profit after tax ÷ share count = reported EPS, basic and diluted
- non-current + current assets = total assets = liabilities + equity
- gross cash − debt − **lease liabilities** = the €2.1bn net cash the issuer reports

That last one is worth noting: excluding lease liabilities gives €2,230m, which is *not* what
the issuer reported. The test pins down the definition as well as the arithmetic.

## Known discrepancy in the source

The release quotes the FY27 fuel hedge two ways:

| Location | Quote | Implied $/bbl |
| :--- | :--- | ---: |
| Highlights | `FY27 jet-fuel 80% hedged @ $668 met. tn` | ~$84.6 |
| Narrative | `80% of FY27 jet-fuel is hedged at approx. $67bbl` | $67 |

At ~7.9 barrels per metric tonne these do not reconcile. The model works in $/bbl, because
spot is also quoted per barrel, and §4.4 of the write-up sensitivity-tests baselines spanning
both readings. **Resolve this against the annual report's fuel note before quoting a level.**

## Updating for the next filing

Replace the figures in `ryanair_fy26.json`, keeping the structure. Every field maps to a line
in the results release:

| JSON path | Source |
| :--- | :--- |
| `income_statement.*` | Condensed Consolidated Preliminary Income Statement |
| `balance_sheet.*` | Condensed Consolidated Preliminary Balance Sheet |
| `cash_flow.*` | Condensed Consolidated Preliminary Statement of Cash Flows |
| `operating_stats.*` | the traffic/load-factor table in the MD&A |
| `hedging_and_liquidity.*` | "Jet-Fuel Hedging" and "Balance Sheet, Liquidity & Returns" |
| `market_data.share_price_eur` | Euronext Dublin quote on the valuation date |

Then run `python analysis.py` and `python -m unittest discover tests`. The transcription
tests will catch most typing errors before they reach the write-up.

## Not investment advice

This is a student portfolio project. It is a demonstration of method, not a recommendation to
buy or sell anything.
