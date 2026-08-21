# Publishing these as separate repositories

This directory holds the whole portfolio in one place so the projects can share a data lab
and a toolkit. For a public portfolio, **each project should be its own repository** — a
recruiter opening a link should land on that project's README, not three directories above
it.

## Why separate repositories

- Each project's README becomes the repository landing page.
- Each can be pinned individually on your GitHub profile (you get six pins).
- The repository name is the first thing anyone reads. `equity-valuation-dcf` describes
  itself; `finance-stuff` does not.

## The split

Each project is already self-contained — it has its own `src/finlib.py`, its own `data/`,
and no imports outside its own directory. Copying the directory out is the entire migration.

```bash
# for each project
mkdir ~/repos/equity-valuation-dcf
cp -r projects/equity-valuation-dcf/* ~/repos/equity-valuation-dcf/
cd ~/repos/equity-valuation-dcf

git init
git add .
git commit -m "Discounted cash flow valuation model with scenario and Monte Carlo analysis"
git branch -M main
git remote add origin git@github.com:<username>/equity-valuation-dcf.git
git push -u origin main
```

Verify each one still runs standalone before pushing:

```bash
python analysis.py && python -m unittest discover tests
```

## Suggested repository names and descriptions

GitHub shows the description under the repository name in search results and on your
profile. Write it as a sentence about what the project finds, not what it contains.

| Repository | Description field |
| :--- | :--- |
| `equity-valuation-dcf` | FCFF discounted cash flow with bottom-up WACC, reverse DCF, scenario and Monte Carlo analysis. Pure Python, no dependencies. |
| `financial-statement-analysis` | Six-year ratio analysis, five-step DuPont decomposition and earnings-quality forensics across three companies. |
| `portfolio-performance-analytics` | Portfolio backtesting with Euler risk decomposition and exact return attribution. Shows where the risk actually is. |
| `portfolio-optimizer` | Long-only mean-variance optimiser with Ledoit–Wolf shrinkage and risk parity, tested walk-forward against equal weight. |
| `etf-cost-and-tracking-study` | Tracking difference versus tracking error, and what an expense ratio costs over thirty years. |

Add topics to each repository — `finance`, `python`, `valuation`, `portfolio-management`,
`quantitative-finance` — since GitHub search uses them.

## The shared toolkit

`src/finlib.py` is copied into each project rather than shared as a package. That is
deliberate: a project that needs a `pip install` before it runs is a project most reviewers
will not run. The cost is that a fix to `finlib.py` has to be copied to five places. If you
prefer, publish it once as `finlib` and add a `requirements.txt` — but then say so in each
README, because "no dependencies" stops being true.

The `data-lab/` generators do not need to travel with the projects: each project has its
generated data committed. Keep the lab in one repository (this one, or a
`finance-data-lab`) and link to it from the project data READMEs, which already reference it.

## Before publishing anything

- [ ] `python analysis.py` runs from a clean clone of the split-out repository
- [ ] `python -m unittest discover tests` passes
- [ ] Every `TODO` placeholder is filled in or deleted
- [ ] The data notice is on the README's front page (it already is — do not remove it)
- [ ] Nothing in `outputs/` is stale relative to the README's numbers — rerun `analysis.py`
      and check the tables still match
- [ ] Copy `LICENSE` and `.gitignore` from this directory into each split-out repository
      root, and check the copyright name on the licence is right
