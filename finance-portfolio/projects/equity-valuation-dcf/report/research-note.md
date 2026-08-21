# Meridian Beverage Group (MRDN)

### The market is pricing zero growth into a business that still grows

**Rating: Buy, small position · Price $27.60 · Value $32 · Upside 16%**
*Fictional company — see the data notice in the repository README.*

---

**In one paragraph.** Meridian trades at 19.1× trailing earnings and 10.2× EV/EBITDA, a
30% EBITDA-multiple discount to its larger peer. A reverse DCF says the price embeds
0.45% annual revenue growth through FY2029. The company grew 4.7% last year and 11.6%
the year before, and has recovered two-thirds of the gross margin it lost in the FY2022
input-cost spike. Our base case values the equity at $32, 16% above the current price.
The discount is not unearned — leverage is real and the deleveraging is partly
presentational — but 16% for a business this far through its repair is too wide.

## What happened

FY2022 was the break. Gross margin fell 570bp to 36.1% as input costs spiked, and EBIT
margin halved to 6.3%. In the same year management closed a $430m brand acquisition
funded with $480m of new debt. Net debt/EBITDA went from 0.9× to 3.7× against a
collapsing earnings base — the textbook worst sequencing of a good asset bought at a bad
moment.

Two years on, most of that has reversed. Gross margin is 39.8% (FY21: 41.8%), EBIT margin
10.5% (FY21: 13.2%), and net debt/EBITDA is 2.1×. Free cash flow has gone from −$137m in
FY2022 to +$239m in FY2024, comfortably covering the dividend.

## What the price says

This is the part that decides the recommendation. Solving the DCF backwards for the
growth rate that justifies $27.60 — holding our margin path, working-capital intensity
and a 2.25% terminal growth rate — gives **0.45% a year**.

For that to be the right number, Meridian has to be structurally ex-growth while
simultaneously holding a margin that the same price implicitly accepts. Those two
assumptions do not usually coexist: a business losing volume that badly loses pricing
power too. The market appears to be applying a leverage discount and calling it a growth
forecast.

## What we think it is worth

| | Value / share | vs price |
| :--- | ---: | ---: |
| DCF, Gordon growth 2.25% | $31.99 | +16% |
| DCF, exit multiple 9.5× | $32.76 | +19% |
| Probability-weighted scenarios | $32.05 | +16% |
| Monte Carlo median (20k trials) | $31.98 | +16% |
| Peer P/E 23.0× (unadjusted) | $33.22 | +20% |

Four methods that lean on different assumptions land within 3% of each other. The
Monte Carlo puts 77% of the distribution above the current price, with a 5th percentile
of $23.11 — the downside is a 16% loss, not a wipeout.

WACC of 8.02% is built bottom-up: a 0.72 sector unlevered beta relevered to 0.89 at
current leverage, a 9.03% cost of equity, and a 6.14% pre-tax cost of debt taken from
what Meridian actually pays rather than from a ratings grid.

## What would make us wrong

**The margin recovery stalls.** Our base case reaches 11.9% EBIT margin by FY2029, still
130bp below FY2021. If the FY22 damage was structural — mix shift toward the lower-margin
acquired brand rather than input costs — the bear case at $21.23 is the right number and
the stock is 23% overvalued, not 16% cheap. **The FY25 gross margin print is the test.**

**The revolver.** Term debt has fallen from $1,095m to $845m since the acquisition, which
reads as deleveraging. Over the same period the revolver went from zero to $330m. Total
debt is down far less than the headline suggests, and the revolver has grown in every
year that dividends plus buybacks exceeded free cash flow. Management repurchased $70m of
stock in FY2024 while drawing on the facility. We would rather they did not.

**Rates.** At 23% debt weighting, a 100bp rise in the cost of debt costs roughly $1.50 per
share through the WACC, before any effect on the multiple.

## Position

Buy, sized small. The upside is real but it is 16%, not 50%, and it sits on top of a
balance sheet that has not finished healing. This is a position to add to on evidence —
specifically on an FY25 gross margin above 40% with the revolver flat or lower — rather
than one to size up on the valuation gap alone.

---

*Methodology, code and full sensitivity tables: [`../README.md`](../README.md) and
[`../outputs/results.md`](../outputs/results.md). Every figure in this note is reproduced
by `python analysis.py`.*
