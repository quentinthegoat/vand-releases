#!/usr/bin/env python3
"""Download real daily price history from Stooq into this project's CSV layout.

The committed sample panel is simulated (see data/README.md).  This script
points the identical analysis pipeline at real market data:

    python fetch_real_prices.py --tickers spy,iwm,efa,eem,agg,vnq,gld \
                                --names LCAP,SCAP,INTL,EMKT,BNDX,REIT,GOLD \
                                --start 2016-01-04 --out data/prices_daily.csv

Stooq serves free end-of-day CSV with no API key.  US symbols take a `.us`
suffix, which this script adds when the symbol has no dot in it already.

Two things worth knowing before trusting the output:

* Stooq's free series are **not** dividend-adjusted for every instrument.  For
  total-return analysis on equity ETFs, verify against the fund's own factsheet
  before quoting a CAGR - a 2% dividend yield left out compounds into a very
  large error over ten years.
* Series are aligned on dates present in *every* file.  A ticker with a shorter
  history silently truncates the whole panel, so the script reports the final
  date range and row count and you should check it.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import sys
import urllib.request

STOOQ = "https://stooq.com/q/d/l/?s={symbol}&i=d"


def fetch_one(symbol: str, timeout: int = 30) -> dict[dt.date, float]:
    sym = symbol if "." in symbol else f"{symbol}.us"
    url = STOOQ.format(symbol=sym.lower())
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        body = resp.read().decode("utf-8", "replace")
    rows = list(csv.DictReader(io.StringIO(body)))
    if not rows or "Close" not in (rows[0] if rows else {}):
        raise SystemExit(f"no usable data returned for {sym} - check the symbol")
    return {dt.date.fromisoformat(r["Date"]): float(r["Close"])
            for r in rows if r.get("Close") not in (None, "", "N/D")}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tickers", required=True, help="comma-separated Stooq symbols")
    ap.add_argument("--names", help="comma-separated column names (default: the symbols)")
    ap.add_argument("--start", default="2016-01-04")
    ap.add_argument("--end", default=dt.date.today().isoformat())
    ap.add_argument("--out", default="data/prices_daily.csv")
    args = ap.parse_args()

    symbols = [s.strip() for s in args.tickers.split(",")]
    names = [n.strip() for n in args.names.split(",")] if args.names else symbols
    if len(names) != len(symbols):
        raise SystemExit("--names must have the same number of entries as --tickers")

    start, end = dt.date.fromisoformat(args.start), dt.date.fromisoformat(args.end)
    series = {}
    for sym, name in zip(symbols, names):
        print(f"fetching {sym} -> {name}", file=sys.stderr)
        series[name] = fetch_one(sym)

    # Intersect the dates so every row is complete.  Forward-filling instead
    # would invent prices on days a market was closed and understate volatility.
    common = sorted(set.intersection(*(set(s) for s in series.values())))
    common = [d for d in common if start <= d <= end]
    if not common:
        raise SystemExit("no overlapping dates across the requested tickers")

    with open(args.out, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["date"] + names)
        for d in common:
            w.writerow([d.isoformat()] + [f"{series[n][d]:.4f}" for n in names])

    print(f"wrote {len(common):,} rows, {common[0]} to {common[-1]}, "
          f"{len(names)} series -> {args.out}", file=sys.stderr)
    print("check that range before quoting any statistic from it.", file=sys.stderr)


if __name__ == "__main__":
    main()
