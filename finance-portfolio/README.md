# Finance Portfolio

Five quantitative finance projects, written in pure standard-library Python. Every one runs
with a single command, on a clean machine, with no dependencies, no API key and no network
access — and reproduces every number and figure in its write-up.

```bash
cd projects/<project>
python analysis.py
python -m unittest discover tests -v
```

---

## The projects

### 1. [Equity Valuation — Discounted Cash Flow](projects/equity-valuation-dcf/)

**What is this company worth, and what does the market price already assume?**

FCFF discounted cash flow with a bottom-up WACC, two terminal-value methods cross-checking
each other, scenario and 20,000-trial Monte Carlo analysis, a **reverse DCF**, and a
trading-comparables sanity check with an explicit not-meaningful screen.

> *Headline finding:* the DCF values the equity at $32 against a $27.60 price — but the
> result that decides the recommendation is the reverse DCF, which shows the market pricing
> **0.45% annual revenue growth** into a business that grew 4.7% last year.

Also contains a two-page [research note](projects/equity-valuation-dcf/report/research-note.md)
of the kind a portfolio manager would actually read.

### 2. [Financial Statement Analysis](projects/financial-statement-analysis/)

**Three companies, one industry, one cost shock. Which is actually a good business?**

Six years of ratio analysis, five-step DuPont decomposition, common-size statements,
cash-conversion and earnings-quality forensics (accrual ratio, FCF conversion), and Altman
Z-scores.

> *Headline finding:* the fastest-growing company (21% revenue CAGR) is the worst business —
> negative ROIC and negative free cash flow in all six years, funded by a 58% increase in
> share count. And one company's reported deleveraging does not survive looking at the
> revolver: term debt fell $250m while **total drawn debt fell $23m**.

### 3. [Portfolio Performance & Risk Analytics](projects/portfolio-performance-analytics/)

**A seven-sleeve diversified portfolio beat the 60/40 by 32bp a year. Was it worth it?**

Drift-and-rebalance backtesting with measured turnover and costs, full performance
statistics, Euler risk decomposition, return attribution that sums exactly to the portfolio
return, and a rebalancing-frequency study.

> *Headline finding:* the portfolio holds 25% of its capital in bonds and gets **2% of its
> risk** from them. 65% in equities produces 90% of the risk. It is not a balanced
> portfolio; it is an equity portfolio with a bond sleeve attached.

### 4. [Portfolio Optimizer](projects/portfolio-optimizer/)

**Does mean-variance optimisation beat equal weight out of sample?**

A long-only optimiser built from scratch — exact simplex projection, Lipschitz-stepped
projected gradient descent, Ledoit–Wolf covariance shrinkage, risk parity — and a
walk-forward test that never lets an estimator see data it would not have had.

> *Headline finding:* equal weight won. The Sharpe-maximising optimiser delivered a Sharpe
> of **zero**, with 13× the turnover and the deepest drawdown in the study. And the
> look-ahead portfolio — the one that knew the future — beat 1/N by two basis points of
> Sharpe, which reframes the whole exercise: there was barely a prize to win.

### 5. [ETF Cost & Tracking Study](projects/etf-cost-and-tracking-study/)

**Three funds, one index, expense ratios of 0.03%, 0.09% and 0.35%.**

Tracking difference separated from tracking error, an "unexplained" residual after fees,
lifetime cost-of-ownership projections, breakeven analysis and holdings overlap.

> *Headline finding:* the 0.32pp fee gap costs **$64,886 over thirty years on $100,000** —
> 8.6% of the final balance. And a methodological one that matters more: two of the three
> funds cannot legitimately be judged against this index at all, because they do not track
> it. Mandate difference is routinely mislabelled as tracking failure.

---

## How to read these

Each project follows the same structure, and each one states its question before it states
its answer:

| | |
| :--- | :--- |
| `README.md` | question → methodology → results → **conclusion** → **limitations** |
| `analysis.py` | one command; regenerates every table and figure in the README |
| `src/` | the analytics, documented with the reasoning behind each choice |
| `data/` | the input data, with a `README.md` explaining its provenance |
| `outputs/` | generated results and SVG figures — safe to delete and rebuild |
| `tests/` | unit tests for the maths, runnable with `python -m unittest` |

The limitations sections are real, not decorative. Where a result is weak, unfavourable, or
undermines the thing the project set out to demonstrate — the shrinkage that did nothing,
the diversification that did not pay, the peer set that collapses to one company — it is
reported and explained rather than dropped.

## About the data

**The data in these projects is generated, not real, and every project says so on its front
page.** Two things drove that decision:

1. **Accuracy.** Reproducing a real issuer's filings from memory produces numbers that look
   authoritative and may be wrong. A wrong number presented as real is worse than an
   invented number presented as invented.
2. **Reproducibility and licensing.** Vendor price history and standardised fundamentals
   cannot be redistributed. A portfolio that stops reproducing when an API key expires is
   not a portfolio.

What was built instead is more work than downloading a CSV, and demonstrates more:

- **[`data-lab/generate_sample_prices.py`](data-lab/generate_sample_prices.py)** — a factor
  model with GARCH(1,1) volatility clustering, Student-t shocks, planted bear-market regimes,
  and a 2022 episode where bonds deliberately fail to hedge. Funds are modelled as index
  minus fee plus tracking noise. Fixed seed: same input, byte-identical output.
- **[`data-lab/build_statements.py`](data-lab/build_statements.py)** — a three-statement
  engine driven by operating assumptions, which **refuses to emit a company** unless the
  balance sheet ties to the cent and the cash flow statement reconciles to closing cash,
  every year. It models both circularities a real model has (interest on cash, revolver
  draws) with a fixed-point iteration.

Every project also ships `fetch_real_prices.py` or a documented mapping to 10-K line items,
so the identical pipeline runs on real data by replacing one file. The write-ups are
careful throughout to separate conclusions about **method** (which transfer) from
conclusions about **markets** (which do not).

## Why no pandas or numpy

Every project is standard-library Python 3.9+. `src/finlib.py` is a shared toolkit
containing the statistics, linear algebra (Gaussian elimination, matrix inversion, OLS with
t-statistics), and an SVG chart engine written for these projects — every figure in every
README is generated by it.

Three reasons this was worth the constraint:

1. **It always runs.** No environment, no version conflicts, no install step. Clone and
   execute.
2. **The maths is readable.** A reviewer can see the Euler risk decomposition, the simplex
   projection and the Ledoit–Wolf estimator written out, rather than trusting a library call.
3. **It surfaces real bugs.** Writing an optimiser by hand meant a unit test could catch
   the min-variance solver converging to a point that was not the minimum — a step-size
   bug a library would have hidden.

For production work, numpy and pandas are the right answer, and `finlib` is not a
replacement for them.

## Repository layout

```
projects/
  equity-valuation-dcf/                 DCF, scenarios, Monte Carlo, reverse DCF, comps
  financial-statement-analysis/         ratios, DuPont, earnings quality, Altman Z
  portfolio-performance-analytics/      backtest, attribution, Euler risk decomposition
  portfolio-optimizer/                  frontier, shrinkage, risk parity, walk-forward
  etf-cost-and-tracking-study/          tracking difference vs error, fee drag, overlap
lib/finlib.py                           shared toolkit (copied into each project's src/)
data-lab/                               the data generators, with their validation rules
shared-data/                            generated panels, copied into each project's data/
site/index.html                         a single-page portfolio site
github-profile/README.md                profile README for the GitHub profile repository
SPLITTING-INTO-REPOS.md                 how to publish each project as its own repository
```

## The site and the profile

[`site/index.html`](site/index.html) is a single-file portfolio site — no build step, no
dependencies, works from `file://` or any static host, and renders correctly in both light
and dark themes. [`github-profile/README.md`](github-profile/README.md) is a profile README
for a repository named after your GitHub username.

Both contain clearly-marked `TODO` placeholders for personal details, which are deliberately
loud rather than subtle: a page that ships with an invisible placeholder is worse than one
that ships with an obvious one. Fill them in or delete those lines before publishing.

## Reproducing the data

```bash
python data-lab/generate_sample_prices.py --out shared-data
python data-lab/build_statements.py --out shared-data/fundamentals
```

Both are deterministic. If either produces different output on your machine, that is a bug.
