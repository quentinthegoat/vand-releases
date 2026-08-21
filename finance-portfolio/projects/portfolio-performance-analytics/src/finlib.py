"""finlib - a small, dependency-free quantitative finance toolkit.

Everything here is standard-library Python 3.9+.  No numpy, no pandas, no
plotting library.  That is a deliberate constraint: every project in this
portfolio has to run with `python analysis.py` on a clean machine, and a
reviewer should be able to read the maths rather than trust a library call.

Contents
--------
IO          read_price_csv, read_series_csv
Returns     simple_returns, log_returns, cumulative, rebase
Statistics  mean, stdev, covariance, correlation, corr_matrix, cov_matrix
Risk        annualised_return, annualised_vol, sharpe, sortino, max_drawdown,
            drawdown_series, historical_var, historical_cvar, downside_deviation
Regression  ols  (multivariate least squares with t-statistics and R-squared)
Linear alg  transpose, matmul, solve, inverse
Charting    line_chart, bar_chart, scatter_chart, heatmap, stacked_area
Formatting  pct, num, markdown_table
"""

from __future__ import annotations

import csv
import datetime as dt
import math
from typing import Callable, Iterable, Sequence

TRADING_DAYS = 252

# ---------------------------------------------------------------------------
# IO
# ---------------------------------------------------------------------------


def read_price_csv(path: str) -> tuple[list[dt.date], dict[str, list[float]]]:
    """Read a wide price file: first column `date`, one column per ticker."""
    with open(path, newline="") as fh:
        rows = list(csv.reader(fh))
    header, body = rows[0], rows[1:]
    tickers = header[1:]
    dates = [dt.date.fromisoformat(r[0]) for r in body]
    data = {t: [float(r[i + 1]) for r in body] for i, t in enumerate(tickers)}
    return dates, data


def read_series_csv(path: str, column: int = 1) -> tuple[list[dt.date], list[float]]:
    """Read a two-column date/value file."""
    with open(path, newline="") as fh:
        rows = list(csv.reader(fh))
    body = rows[1:]
    return ([dt.date.fromisoformat(r[0]) for r in body],
            [float(r[column]) for r in body])


# ---------------------------------------------------------------------------
# Returns
# ---------------------------------------------------------------------------


def simple_returns(prices: Sequence[float]) -> list[float]:
    return [prices[i] / prices[i - 1] - 1.0 for i in range(1, len(prices))]


def log_returns(prices: Sequence[float]) -> list[float]:
    return [math.log(prices[i] / prices[i - 1]) for i in range(1, len(prices))]


def cumulative(returns: Sequence[float], start: float = 1.0) -> list[float]:
    """Compounded equity curve, including the starting point."""
    out = [start]
    for r in returns:
        out.append(out[-1] * (1.0 + r))
    return out


def rebase(prices: Sequence[float], base: float = 100.0) -> list[float]:
    return [p / prices[0] * base for p in prices]


def portfolio_returns(asset_returns: dict[str, list[float]],
                      weights: dict[str, float]) -> list[float]:
    """Return series of a portfolio rebalanced every period to `weights`."""
    n = len(next(iter(asset_returns.values())))
    return [sum(w * asset_returns[t][i] for t, w in weights.items()) for i in range(n)]


def buy_and_hold_returns(asset_returns: dict[str, list[float]],
                         weights: dict[str, float]) -> list[float]:
    """Return series with no rebalancing: weights drift with performance."""
    holdings = dict(weights)
    out = []
    for i in range(len(next(iter(asset_returns.values())))):
        gross = {t: h * (1.0 + asset_returns[t][i]) for t, h in holdings.items()}
        total = sum(gross.values())
        out.append(total / sum(holdings.values()) - 1.0)
        holdings = gross
    return out


# ---------------------------------------------------------------------------
# Descriptive statistics
# ---------------------------------------------------------------------------


def mean(xs: Sequence[float]) -> float:
    return sum(xs) / len(xs)


def stdev(xs: Sequence[float], sample: bool = True) -> float:
    m = mean(xs)
    denom = len(xs) - 1 if sample else len(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / denom)


def covariance(xs: Sequence[float], ys: Sequence[float], sample: bool = True) -> float:
    mx, my = mean(xs), mean(ys)
    denom = len(xs) - 1 if sample else len(xs)
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / denom


def correlation(xs: Sequence[float], ys: Sequence[float]) -> float:
    sx, sy = stdev(xs), stdev(ys)
    return covariance(xs, ys) / (sx * sy) if sx and sy else 0.0


def skewness(xs: Sequence[float]) -> float:
    m, s, n = mean(xs), stdev(xs), len(xs)
    return sum((x - m) ** 3 for x in xs) / n / s ** 3 if s else 0.0


def excess_kurtosis(xs: Sequence[float]) -> float:
    m, s, n = mean(xs), stdev(xs), len(xs)
    return sum((x - m) ** 4 for x in xs) / n / s ** 4 - 3.0 if s else 0.0


def cov_matrix(returns: dict[str, list[float]], tickers: Sequence[str]) -> list[list[float]]:
    return [[covariance(returns[a], returns[b]) for b in tickers] for a in tickers]


def corr_matrix(returns: dict[str, list[float]], tickers: Sequence[str]) -> list[list[float]]:
    return [[correlation(returns[a], returns[b]) for b in tickers] for a in tickers]


# ---------------------------------------------------------------------------
# Risk and performance
# ---------------------------------------------------------------------------


def annualised_return(returns: Sequence[float], periods: int = TRADING_DAYS) -> float:
    """Geometric (compound) annual growth rate implied by a return series."""
    total = 1.0
    for r in returns:
        total *= 1.0 + r
    years = len(returns) / periods
    return total ** (1.0 / years) - 1.0 if years > 0 else 0.0


def annualised_vol(returns: Sequence[float], periods: int = TRADING_DAYS) -> float:
    return stdev(returns) * math.sqrt(periods)


def downside_deviation(returns: Sequence[float], mar: float = 0.0,
                       periods: int = TRADING_DAYS) -> float:
    """Root-mean-square of shortfalls below the minimum acceptable return.

    Note the denominator is the *full* sample length, not just the losing days:
    that is the Sortino convention, and using only losing days silently
    inflates the ratio."""
    bad = [min(0.0, r - mar) ** 2 for r in returns]
    return math.sqrt(sum(bad) / len(bad)) * math.sqrt(periods)


def sharpe(returns: Sequence[float], rf_daily: Sequence[float] | float = 0.0,
           periods: int = TRADING_DAYS) -> float:
    if isinstance(rf_daily, (int, float)):
        rf_daily = [float(rf_daily)] * len(returns)
    excess = [r - f for r, f in zip(returns, rf_daily)]
    s = stdev(excess)
    return mean(excess) / s * math.sqrt(periods) if s else 0.0


def sortino(returns: Sequence[float], rf_daily: Sequence[float] | float = 0.0,
            periods: int = TRADING_DAYS) -> float:
    if isinstance(rf_daily, (int, float)):
        rf_daily = [float(rf_daily)] * len(returns)
    excess = [r - f for r, f in zip(returns, rf_daily)]
    dd = downside_deviation(excess, 0.0, periods)
    return mean(excess) * periods / dd if dd else 0.0


def drawdown_series(equity: Sequence[float]) -> list[float]:
    peak, out = equity[0], []
    for v in equity:
        peak = max(peak, v)
        out.append(v / peak - 1.0)
    return out


def max_drawdown(equity: Sequence[float]) -> tuple[float, int, int, int | None]:
    """Return (worst drawdown, peak index, trough index, recovery index)."""
    peak = equity[0]
    peak_i = worst_peak = worst_trough = 0
    worst = 0.0
    for i, v in enumerate(equity):
        if v > peak:
            peak, peak_i = v, i
        dd = v / peak - 1.0
        if dd < worst:
            worst, worst_peak, worst_trough = dd, peak_i, i
    recovery = None
    for i in range(worst_trough, len(equity)):
        if equity[i] >= equity[worst_peak]:
            recovery = i
            break
    return worst, worst_peak, worst_trough, recovery


def historical_var(returns: Sequence[float], level: float = 0.95) -> float:
    """Historical value at risk, reported as a positive loss fraction."""
    s = sorted(returns)
    idx = max(0, min(len(s) - 1, int(math.floor((1.0 - level) * len(s)))))
    return -s[idx]


def historical_cvar(returns: Sequence[float], level: float = 0.95) -> float:
    """Expected shortfall: mean loss in the tail beyond VaR."""
    s = sorted(returns)
    cutoff = max(1, int(math.floor((1.0 - level) * len(s))))
    return -mean(s[:cutoff])


def rolling(values: Sequence[float], window: int,
            fn: Callable[[Sequence[float]], float]) -> list[float | None]:
    out: list[float | None] = [None] * (window - 1)
    for i in range(window - 1, len(values)):
        out.append(fn(values[i - window + 1:i + 1]))
    return out


def capture_ratios(portfolio: Sequence[float], benchmark: Sequence[float]) -> tuple[float, float]:
    """Up-capture and down-capture versus a benchmark, in ratio terms."""
    up_p = [p for p, b in zip(portfolio, benchmark) if b > 0]
    up_b = [b for b in benchmark if b > 0]
    dn_p = [p for p, b in zip(portfolio, benchmark) if b < 0]
    dn_b = [b for b in benchmark if b < 0]
    up = (mean(up_p) / mean(up_b)) if up_b else float("nan")
    dn = (mean(dn_p) / mean(dn_b)) if dn_b else float("nan")
    return up, dn


def tracking_error(portfolio: Sequence[float], benchmark: Sequence[float],
                   periods: int = TRADING_DAYS) -> float:
    return stdev([p - b for p, b in zip(portfolio, benchmark)]) * math.sqrt(periods)


def information_ratio(portfolio: Sequence[float], benchmark: Sequence[float],
                      periods: int = TRADING_DAYS) -> float:
    diff = [p - b for p, b in zip(portfolio, benchmark)]
    te = stdev(diff)
    return mean(diff) / te * math.sqrt(periods) if te else 0.0


# ---------------------------------------------------------------------------
# Linear algebra
# ---------------------------------------------------------------------------


def transpose(m: list[list[float]]) -> list[list[float]]:
    return [list(col) for col in zip(*m)]


def matmul(a: list[list[float]], b: list[list[float]]) -> list[list[float]]:
    bt = transpose(b)
    return [[sum(x * y for x, y in zip(row, col)) for col in bt] for row in a]


def matvec(a: list[list[float]], v: Sequence[float]) -> list[float]:
    return [sum(x * y for x, y in zip(row, v)) for row in a]


def solve(a: list[list[float]], b: Sequence[float]) -> list[float]:
    """Solve A x = b by Gaussian elimination with partial pivoting."""
    n = len(a)
    m = [row[:] + [b[i]] for i, row in enumerate(a)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(m[r][col]))
        if abs(m[pivot][col]) < 1e-14:
            raise ValueError("matrix is singular to working precision")
        m[col], m[pivot] = m[pivot], m[col]
        pv = m[col][col]
        for r in range(n):
            if r == col:
                continue
            factor = m[r][col] / pv
            if factor:
                for c in range(col, n + 1):
                    m[r][c] -= factor * m[col][c]
    return [m[i][n] / m[i][i] for i in range(n)]


def inverse(a: list[list[float]]) -> list[list[float]]:
    n = len(a)
    cols = []
    for i in range(n):
        e = [1.0 if j == i else 0.0 for j in range(n)]
        cols.append(solve(a, e))
    return transpose(cols)


# ---------------------------------------------------------------------------
# Regression
# ---------------------------------------------------------------------------


class OLSResult:
    """Ordinary least squares fit with the diagnostics worth quoting."""

    def __init__(self, names, coefficients, stderrs, tstats, r2, adj_r2, n, residuals):
        self.names = names
        self.coefficients = coefficients
        self.stderrs = stderrs
        self.tstats = tstats
        self.r2 = r2
        self.adj_r2 = adj_r2
        self.n = n
        self.residuals = residuals

    def get(self, name: str) -> float:
        return self.coefficients[self.names.index(name)]

    def tstat(self, name: str) -> float:
        return self.tstats[self.names.index(name)]

    def __repr__(self) -> str:
        parts = ", ".join(f"{n}={c:+.4f}(t={t:+.2f})"
                          for n, c, t in zip(self.names, self.coefficients, self.tstats))
        return f"OLS(n={self.n}, R2={self.r2:.3f}, {parts})"


def ols(y: Sequence[float], regressors: dict[str, Sequence[float]],
        intercept: bool = True) -> OLSResult:
    """Least squares via the normal equations (X'X)b = X'y.

    Fine for the handful of well-conditioned regressors used here; a QR or SVD
    solve would be the right call for wide or collinear design matrices."""
    names = list(regressors)
    X = []
    for i in range(len(y)):
        row = [1.0] if intercept else []
        row += [regressors[k][i] for k in names]
        X.append(row)
    labels = (["alpha"] if intercept else []) + names

    xtx = matmul(transpose(X), X)
    xty = matvec(transpose(X), y)
    beta = solve(xtx, xty)

    fitted = [sum(b * xi for b, xi in zip(beta, row)) for row in X]
    resid = [yi - f for yi, f in zip(y, fitted)]
    ybar = mean(y)
    ss_res = sum(r * r for r in resid)
    ss_tot = sum((yi - ybar) ** 2 for yi in y)
    n, k = len(y), len(beta)
    r2 = 1.0 - ss_res / ss_tot if ss_tot else 0.0
    adj = 1.0 - (1.0 - r2) * (n - 1) / (n - k) if n > k else 0.0

    sigma2 = ss_res / (n - k) if n > k else 0.0
    xtx_inv = inverse(xtx)
    stderrs = [math.sqrt(max(sigma2 * xtx_inv[i][i], 0.0)) for i in range(k)]
    tstats = [b / s if s else 0.0 for b, s in zip(beta, stderrs)]
    return OLSResult(labels, beta, stderrs, tstats, r2, adj, n, resid)


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------


def pct(x: float | None, dp: int = 2) -> str:
    return "n/a" if x is None else f"{x * 100:.{dp}f}%"


def num(x: float | None, dp: int = 2) -> str:
    return "n/a" if x is None else f"{x:,.{dp}f}"


def markdown_table(headers: Sequence[str], rows: Iterable[Sequence[str]],
                   align: Sequence[str] | None = None) -> str:
    rows = [list(map(str, r)) for r in rows]
    align = align or ["left"] + ["right"] * (len(headers) - 1)
    sep = {"left": ":---", "right": "---:", "center": ":---:"}
    out = ["| " + " | ".join(headers) + " |",
           "| " + " | ".join(sep[a] for a in align) + " |"]
    out += ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join(out)


# ---------------------------------------------------------------------------
# SVG charting
#
# Charts are emitted as standalone SVG with an explicit light background, so
# they render identically in a GitHub README under either colour theme.
# ---------------------------------------------------------------------------

PALETTE = ["#2f5d8a", "#c4622d", "#3d7a5d", "#8a4f7d", "#b08a2e",
           "#6b7280", "#7a3b3b", "#4a6fa5"]
INK = "#1f2937"
MUTED = "#6b7280"
GRID = "#e5e7eb"
BG = "#ffffff"


def _esc(s: str) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _nice_ticks(lo: float, hi: float, count: int = 5) -> list[float]:
    if hi <= lo:
        return [lo]
    raw = (hi - lo) / count
    mag = 10 ** math.floor(math.log10(raw))
    for mult in (1, 2, 2.5, 5, 10):
        if raw / mag <= mult:
            step = mult * mag
            break
    else:
        step = 10 * mag
    start = math.floor(lo / step) * step
    ticks, v = [], start
    while v <= hi + step * 0.5:
        if v >= lo - step * 0.001:
            ticks.append(round(v, 10))
        v += step
    return ticks


class _Canvas:
    def __init__(self, width, height, title=None, subtitle=None,
                 pad_left=64, pad_right=24, pad_top=48, pad_bottom=46):
        self.w, self.h = width, height
        self.pl, self.pr, self.pt, self.pb = pad_left, pad_right, pad_top, pad_bottom
        if title:
            self.pt = max(self.pt, 56 if not subtitle else 74)
        self.parts = []
        self.title, self.subtitle = title, subtitle

    @property
    def plot_w(self):
        return self.w - self.pl - self.pr

    @property
    def plot_h(self):
        return self.h - self.pt - self.pb

    def add(self, s):
        self.parts.append(s)

    def text(self, x, y, s, size=11, fill=INK, anchor="start", weight="normal"):
        self.add(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" '
                 f'text-anchor="{anchor}" font-weight="{weight}" '
                 f'font-family="Inter, Segoe UI, Helvetica, Arial, sans-serif">{_esc(s)}</text>')

    def render(self) -> str:
        head = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
                f'viewBox="0 0 {self.w} {self.h}" role="img">',
                f'<rect width="{self.w}" height="{self.h}" fill="{BG}"/>']
        if self.title:
            head.append(f'<text x="{self.pl}" y="26" font-size="15" font-weight="600" fill="{INK}" '
                        f'font-family="Inter, Segoe UI, Helvetica, Arial, sans-serif">'
                        f'{_esc(self.title)}</text>')
        if self.subtitle:
            head.append(f'<text x="{self.pl}" y="45" font-size="11.5" fill="{MUTED}" '
                        f'font-family="Inter, Segoe UI, Helvetica, Arial, sans-serif">'
                        f'{_esc(self.subtitle)}</text>')
        return "\n".join(head + self.parts + ["</svg>"])


def _axes(c: _Canvas, xticks, xlabels, yticks, yfmt, ylo, yhi):
    def ypx(v):
        return c.pt + c.plot_h * (1.0 - (v - ylo) / (yhi - ylo))
    for t in yticks:
        y = ypx(t)
        c.add(f'<line x1="{c.pl}" y1="{y:.1f}" x2="{c.pl + c.plot_w}" y2="{y:.1f}" '
              f'stroke="{GRID}" stroke-width="1"/>')
        c.text(c.pl - 8, y + 3.5, yfmt(t), size=10.5, fill=MUTED, anchor="end")
    for x, lab in zip(xticks, xlabels):
        c.text(x, c.pt + c.plot_h + 18, lab, size=10.5, fill=MUTED, anchor="middle")
    c.add(f'<line x1="{c.pl}" y1="{c.pt + c.plot_h}" x2="{c.pl + c.plot_w}" '
          f'y2="{c.pt + c.plot_h}" stroke="{MUTED}" stroke-width="1"/>')


def _legend(c: _Canvas, labels, colours, y=None):
    y = y if y is not None else c.h - 12
    x = c.pl
    for lab, col in zip(labels, colours):
        c.add(f'<rect x="{x}" y="{y - 8}" width="10" height="10" rx="2" fill="{col}"/>')
        c.text(x + 15, y + 1, lab, size=11, fill=INK)
        x += 22 + 6.4 * len(str(lab))


def line_chart(series: dict[str, Sequence[float]], x_labels: Sequence[str],
               title="", subtitle="", y_format=lambda v: f"{v:,.0f}",
               width=880, height=380, colours=None, zero_line=False,
               fill_first=False, x_tick_every=None) -> str:
    """Multi-series line chart.  `x_labels` is one label per observation; only
    a handful are drawn."""
    c = _Canvas(width, height, title, subtitle)
    names = list(series)
    colours = colours or PALETTE
    n = len(next(iter(series.values())))
    allv = [v for s in series.values() for v in s if v is not None]
    lo, hi = min(allv), max(allv)
    if zero_line:
        lo, hi = min(lo, 0.0), max(hi, 0.0)
    span = (hi - lo) or 1.0
    lo, hi = lo - span * 0.06, hi + span * 0.10
    ticks = _nice_ticks(lo, hi)
    lo, hi = min(lo, ticks[0]), max(hi, ticks[-1])

    def xpx(i):
        return c.pl + c.plot_w * (i / max(n - 1, 1))

    def ypx(v):
        return c.pt + c.plot_h * (1.0 - (v - lo) / (hi - lo))

    step = x_tick_every or max(1, n // 8)
    idxs = list(range(0, n, step))
    _axes(c, [xpx(i) for i in idxs], [x_labels[i] for i in idxs], ticks, y_format, lo, hi)
    if zero_line and lo < 0 < hi:
        c.add(f'<line x1="{c.pl}" y1="{ypx(0):.1f}" x2="{c.pl + c.plot_w}" y2="{ypx(0):.1f}" '
              f'stroke="{MUTED}" stroke-width="1" stroke-dasharray="3 3"/>')

    for k, name in enumerate(names):
        vals = series[name]
        pts = [(xpx(i), ypx(v)) for i, v in enumerate(vals) if v is not None]
        col = colours[k % len(colours)]
        if fill_first and k == 0:
            area = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
            c.add(f'<polygon points="{c.pl},{ypx(min(max(0,lo),hi)):.1f} {area} '
                  f'{pts[-1][0]:.1f},{ypx(min(max(0,lo),hi)):.1f}" fill="{col}" opacity="0.13"/>')
        d = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        c.add(f'<polyline points="{d}" fill="none" stroke="{col}" stroke-width="1.9" '
              f'stroke-linejoin="round" stroke-linecap="round"/>')
    if len(names) > 1 or names[0]:
        _legend(c, names, [colours[i % len(colours)] for i in range(len(names))])
    return c.render()


def bar_chart(labels: Sequence[str], values: Sequence[float], title="", subtitle="",
              y_format=lambda v: f"{v:,.0f}", width=880, height=360,
              colour_by_sign=False, colour=None, value_labels=True) -> str:
    c = _Canvas(width, height, title, subtitle, pad_bottom=64)
    lo, hi = min(min(values), 0.0), max(max(values), 0.0)
    span = (hi - lo) or 1.0
    lo, hi = lo - span * 0.10, hi + span * 0.14
    ticks = _nice_ticks(lo, hi)

    def ypx(v):
        return c.pt + c.plot_h * (1.0 - (v - lo) / (hi - lo))

    for t in ticks:
        y = ypx(t)
        c.add(f'<line x1="{c.pl}" y1="{y:.1f}" x2="{c.pl + c.plot_w}" y2="{y:.1f}" '
              f'stroke="{GRID}"/>')
        c.text(c.pl - 8, y + 3.5, y_format(t), size=10.5, fill=MUTED, anchor="end")

    n = len(values)
    slot = c.plot_w / n
    bw = slot * 0.62
    zero = ypx(0.0)
    for i, (lab, v) in enumerate(zip(labels, values)):
        x = c.pl + slot * i + (slot - bw) / 2
        y = ypx(v)
        col = colour or PALETTE[0]
        if colour_by_sign:
            col = "#3d7a5d" if v >= 0 else "#a83232"
        c.add(f'<rect x="{x:.1f}" y="{min(y, zero):.1f}" width="{bw:.1f}" '
              f'height="{abs(zero - y):.1f}" rx="2" fill="{col}"/>')
        c.text(x + bw / 2, c.pt + c.plot_h + 18, lab, size=10.5, fill=MUTED, anchor="middle")
        if value_labels:
            c.text(x + bw / 2, (y - 6) if v >= 0 else (y + 14), y_format(v),
                   size=10, fill=INK, anchor="middle")
    c.add(f'<line x1="{c.pl}" y1="{zero:.1f}" x2="{c.pl + c.plot_w}" y2="{zero:.1f}" '
          f'stroke="{MUTED}"/>')
    return c.render()


def scatter_chart(points: list[tuple[float, float, str]], title="", subtitle="",
                  x_label="", y_label="", x_format=lambda v: f"{v:.0%}",
                  y_format=lambda v: f"{v:.0%}", width=760, height=460,
                  frontier: list[tuple[float, float]] | None = None,
                  highlight: dict[str, str] | None = None) -> str:
    """Risk/return style scatter with optional frontier curve and point labels."""
    c = _Canvas(width, height, title, subtitle, pad_bottom=58)
    highlight = highlight or {}
    xs = [p[0] for p in points] + [f[0] for f in (frontier or [])]
    ys = [p[1] for p in points] + [f[1] for f in (frontier or [])]
    xlo, xhi = min(xs), max(xs)
    ylo, yhi = min(ys), max(ys)
    xpad, ypad = (xhi - xlo or 1) * 0.14, (yhi - ylo or 1) * 0.16
    xlo, xhi, ylo, yhi = xlo - xpad, xhi + xpad, ylo - ypad, yhi + ypad
    xt, yt = _nice_ticks(xlo, xhi), _nice_ticks(ylo, yhi)

    def xpx(v):
        return c.pl + c.plot_w * (v - xlo) / (xhi - xlo)

    def ypx(v):
        return c.pt + c.plot_h * (1.0 - (v - ylo) / (yhi - ylo))

    for t in yt:
        y = ypx(t)
        c.add(f'<line x1="{c.pl}" y1="{y:.1f}" x2="{c.pl + c.plot_w}" y2="{y:.1f}" stroke="{GRID}"/>')
        c.text(c.pl - 8, y + 3.5, y_format(t), size=10.5, fill=MUTED, anchor="end")
    for t in xt:
        x = xpx(t)
        c.add(f'<line x1="{x:.1f}" y1="{c.pt}" x2="{x:.1f}" y2="{c.pt + c.plot_h}" stroke="{GRID}"/>')
        c.text(x, c.pt + c.plot_h + 18, x_format(t), size=10.5, fill=MUTED, anchor="middle")
    c.text(c.pl + c.plot_w / 2, c.h - 12, x_label, size=11.5, fill=INK, anchor="middle")
    c.add(f'<text x="16" y="{c.pt + c.plot_h / 2:.1f}" font-size="11.5" fill="{INK}" '
          f'text-anchor="middle" transform="rotate(-90 16 {c.pt + c.plot_h / 2:.1f})" '
          f'font-family="Inter, Segoe UI, Helvetica, Arial, sans-serif">{_esc(y_label)}</text>')

    if frontier:
        d = " ".join(f"{xpx(x):.1f},{ypx(y):.1f}" for x, y in frontier)
        c.add(f'<polyline points="{d}" fill="none" stroke="{PALETTE[0]}" stroke-width="2.2"/>')

    for x, y, lab in points:
        col = highlight.get(lab, PALETTE[1])
        r = 6.5 if lab in highlight else 4.6
        c.add(f'<circle cx="{xpx(x):.1f}" cy="{ypx(y):.1f}" r="{r}" fill="{col}" '
              f'stroke="{BG}" stroke-width="1.4"/>')
        if lab:
            c.text(xpx(x) + 9, ypx(y) + 3.6, lab, size=10.5, fill=INK)
    return c.render()


def heatmap(labels: Sequence[str], matrix: list[list[float]], title="", subtitle="",
            width=680, cell=46, fmt=lambda v: f"{v:.2f}",
            low="#c9dbea", high="#2f5d8a", mid="#ffffff",
            vmin=-1.0, vmax=1.0) -> str:
    n = len(labels)
    left, top = 74, 78 if subtitle else 60
    w = left + n * cell + 20
    h = top + n * cell + 24
    c = _Canvas(w, h, title, subtitle)

    def blend(a, b, t):
        aa = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
        bb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
        return "#" + "".join(f"{int(x + (y - x) * t):02x}" for x, y in zip(aa, bb))

    for i in range(n):
        c.text(left - 8, top + cell * i + cell / 2 + 4, labels[i], size=11, anchor="end")
        c.text(left + cell * i + cell / 2, top - 8, labels[i], size=11, anchor="middle")
        for j in range(n):
            v = matrix[i][j]
            t = (v - vmin) / (vmax - vmin) if vmax > vmin else 0.5
            col = blend(low, mid, t * 2) if t < 0.5 else blend(mid, high, (t - 0.5) * 2)
            c.add(f'<rect x="{left + cell * j}" y="{top + cell * i}" width="{cell - 2}" '
                  f'height="{cell - 2}" rx="3" fill="{col}"/>')
            c.text(left + cell * j + cell / 2 - 1, top + cell * i + cell / 2 + 4,
                   fmt(v), size=10, anchor="middle",
                   fill="#ffffff" if t > 0.82 else INK)
    return c.render()


def stacked_area(series: dict[str, Sequence[float]], x_labels: Sequence[str],
                 title="", subtitle="", width=880, height=360,
                 y_format=lambda v: f"{v:.0%}") -> str:
    """Stacked composition chart, used for portfolio weights through time."""
    c = _Canvas(width, height, title, subtitle)
    names = list(series)
    n = len(next(iter(series.values())))

    def xpx(i):
        return c.pl + c.plot_w * (i / max(n - 1, 1))

    def ypx(v):
        return c.pt + c.plot_h * (1.0 - v)

    for t in [0, 0.25, 0.5, 0.75, 1.0]:
        c.add(f'<line x1="{c.pl}" y1="{ypx(t):.1f}" x2="{c.pl + c.plot_w}" y2="{ypx(t):.1f}" '
              f'stroke="{GRID}"/>')
        c.text(c.pl - 8, ypx(t) + 3.5, y_format(t), size=10.5, fill=MUTED, anchor="end")
    step = max(1, n // 8)
    for i in range(0, n, step):
        c.text(xpx(i), c.pt + c.plot_h + 18, x_labels[i], size=10.5, fill=MUTED, anchor="middle")

    base = [0.0] * n
    for k, name in enumerate(names):
        top = [base[i] + series[name][i] for i in range(n)]
        up = " ".join(f"{xpx(i):.1f},{ypx(top[i]):.1f}" for i in range(n))
        dn = " ".join(f"{xpx(i):.1f},{ypx(base[i]):.1f}" for i in range(n - 1, -1, -1))
        c.add(f'<polygon points="{up} {dn}" fill="{PALETTE[k % len(PALETTE)]}" opacity="0.88"/>')
        base = top
    _legend(c, names, [PALETTE[i % len(PALETTE)] for i in range(len(names))])
    return c.render()


def write_svg(path: str, svg: str) -> None:
    with open(path, "w") as fh:
        fh.write(svg)


def range_chart(rows: list[tuple[str, float, float, float | None]], title="", subtitle="",
                width=880, row_height=42, x_format=lambda v: f"{v:,.0f}",
                reference: float | None = None, reference_label: str = "",
                x_label: str = "") -> str:
    """Horizontal floating-bar chart - the 'football field' of a valuation deck.

    Each row is (label, low, high, marker) where `marker` is an optional point
    estimate drawn inside the range."""
    left, top = 210, 74 if subtitle else 58
    h = top + row_height * len(rows) + 54
    c = _Canvas(width, h, title, subtitle, pad_left=left, pad_right=32)
    plot_w = width - left - 32
    lo = min(r[1] for r in rows)
    hi = max(r[2] for r in rows)
    if reference is not None:
        lo, hi = min(lo, reference), max(hi, reference)
    pad = (hi - lo) * 0.12 or 1.0
    lo, hi = lo - pad, hi + pad
    ticks = _nice_ticks(lo, hi, 6)

    def xpx(v):
        return left + plot_w * (v - lo) / (hi - lo)

    bottom = top + row_height * len(rows)
    for t in ticks:
        c.add(f'<line x1="{xpx(t):.1f}" y1="{top - 10}" x2="{xpx(t):.1f}" y2="{bottom}" '
              f'stroke="{GRID}"/>')
        c.text(xpx(t), bottom + 18, x_format(t), size=10.5, fill=MUTED, anchor="middle")
    if reference is not None:
        c.add(f'<line x1="{xpx(reference):.1f}" y1="{top - 14}" x2="{xpx(reference):.1f}" '
              f'y2="{bottom + 2}" stroke="#a83232" stroke-width="1.6" stroke-dasharray="5 4"/>')
        c.text(xpx(reference), top - 20, reference_label, size=10.5,
               fill="#a83232", anchor="middle", weight="600")

    for i, (label, low, high, marker) in enumerate(rows):
        y = top + row_height * i + row_height / 2
        c.text(left - 12, y + 4, label, size=11.5, anchor="end")
        x0, x1 = xpx(low), xpx(high)
        c.add(f'<rect x="{x0:.1f}" y="{y - 11:.1f}" width="{max(x1 - x0, 2):.1f}" height="22" '
              f'rx="4" fill="{PALETTE[0]}" opacity="0.72"/>')
        c.text(x0 - 6, y + 4, x_format(low), size=10, fill=MUTED, anchor="end")
        c.text(x1 + 6, y + 4, x_format(high), size=10, fill=MUTED)
        if marker is not None:
            c.add(f'<line x1="{xpx(marker):.1f}" y1="{y - 13:.1f}" x2="{xpx(marker):.1f}" '
                  f'y2="{y + 13:.1f}" stroke="{INK}" stroke-width="2"/>')
    if x_label:
        c.text(left + plot_w / 2, h - 10, x_label, size=11.5, anchor="middle")
    return c.render()


def histogram(values: Sequence[float], bins: int = 40, title="", subtitle="",
              width=880, height=360, x_format=lambda v: f"{v:,.0f}",
              markers: dict[str, float] | None = None) -> str:
    """Frequency histogram with optional labelled vertical markers."""
    lo, hi = min(values), max(values)
    span = (hi - lo) or 1.0
    edges = [lo + span * i / bins for i in range(bins + 1)]
    counts = [0] * bins
    for v in values:
        k = min(bins - 1, int((v - lo) / span * bins))
        counts[k] += 1

    c = _Canvas(width, height, title, subtitle, pad_bottom=54)
    top_count = max(counts) * 1.12

    def xpx(v):
        return c.pl + c.plot_w * (v - lo) / span

    def ypx(n):
        return c.pt + c.plot_h * (1.0 - n / top_count)

    for t in _nice_ticks(0, top_count, 4):
        c.add(f'<line x1="{c.pl}" y1="{ypx(t):.1f}" x2="{c.pl + c.plot_w}" y2="{ypx(t):.1f}" '
              f'stroke="{GRID}"/>')
        c.text(c.pl - 8, ypx(t) + 3.5, f"{t:,.0f}", size=10.5, fill=MUTED, anchor="end")
    for i, n in enumerate(counts):
        x0, x1 = xpx(edges[i]), xpx(edges[i + 1])
        c.add(f'<rect x="{x0:.1f}" y="{ypx(n):.1f}" width="{max(x1 - x0 - 1, 1):.1f}" '
              f'height="{c.pt + c.plot_h - ypx(n):.1f}" fill="{PALETTE[0]}" opacity="0.82"/>')
    for t in _nice_ticks(lo, hi, 6):
        if lo <= t <= hi:
            c.text(xpx(t), c.pt + c.plot_h + 18, x_format(t), size=10.5, fill=MUTED,
                   anchor="middle")
    cols = ["#a83232", "#3d7a5d", "#8a4f7d", "#b08a2e"]
    for k, (lab, v) in enumerate((markers or {}).items()):
        if lo <= v <= hi:
            c.add(f'<line x1="{xpx(v):.1f}" y1="{c.pt}" x2="{xpx(v):.1f}" '
                  f'y2="{c.pt + c.plot_h}" stroke="{cols[k % len(cols)]}" stroke-width="1.8" '
                  f'stroke-dasharray="5 4"/>')
            c.text(xpx(v) + 5, c.pt + 14 + 15 * k, lab, size=10.5, fill=cols[k % len(cols)],
                   weight="600")
    c.add(f'<line x1="{c.pl}" y1="{c.pt + c.plot_h}" x2="{c.pl + c.plot_w}" '
          f'y2="{c.pt + c.plot_h}" stroke="{MUTED}"/>')
    return c.render()
