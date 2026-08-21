"""Mean-variance optimisation, covariance shrinkage and risk parity.

Everything is long-only and fully invested (weights on the simplex), because
that is the constraint set an actual mandate has and because the unconstrained
solution is where mean-variance optimisation earns its nickname of
"error maximiser": with no constraints it happily takes a 400% long in whichever
asset has the highest estimated mean and funds it by shorting the rest.

Three solvers, all built on one primitive - Euclidean projection onto the
simplex - so the constraint handling is identical everywhere and can be tested
once:

    max_utility(mu, Sigma, lambda)   maximise  w'mu - (lambda/2) w'Sigma w
    min_variance(Sigma)              minimise  w'Sigma w
    risk_parity(Sigma)               equalise  each asset's contribution to risk

The efficient frontier is traced by sweeping lambda rather than by solving a
constrained problem per target return.  The two are equivalent, and the sweep
never has to handle an infeasible target.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

import finlib as fl


# ---------------------------------------------------------------------------
# The constraint primitive
# ---------------------------------------------------------------------------


def project_to_simplex(v: Sequence[float]) -> list[float]:
    """Euclidean projection onto {w : sum(w) = 1, w >= 0}.

    Duchi et al. (2008): sort descending, find the largest rho whose partial
    average keeps the shifted value positive, subtract that threshold, clip at
    zero.  O(n log n) and exact - not a heuristic clip-and-renormalise, which
    is not a projection and can move a solution off the true optimum.
    """
    n = len(v)
    u = sorted(v, reverse=True)
    css = 0.0
    rho, theta = 0, 0.0
    for i in range(n):
        css += u[i]
        t = (css - 1.0) / (i + 1)
        if u[i] - t > 0:
            rho, theta = i + 1, t
    if rho == 0:
        return [1.0 / n] * n
    return [max(x - theta, 0.0) for x in v]


def largest_eigenvalue(matrix: list[list[float]], iterations: int = 200) -> float:
    """Dominant eigenvalue by power iteration.

    Used to set the gradient step size.  A step of 1/L, where L is the Lipschitz
    constant of the gradient, is the standard guarantee for projected gradient
    descent on a smooth convex objective - and picking the step by feel instead
    is how an optimiser silently returns a point that is not the optimum.
    """
    n = len(matrix)
    v = [1.0 / math.sqrt(n)] * n
    value = 0.0
    for _ in range(iterations):
        mv = fl.matvec(matrix, v)
        norm = math.sqrt(sum(x * x for x in mv))
        if norm == 0:
            return 0.0
        v = [x / norm for x in mv]
        value = norm
    return value


def _projected_gradient(grad_fn, n: int, step_size: float, steps: int = 4_000,
                        tolerance: float = 1e-12,
                        start: Sequence[float] | None = None) -> list[float]:
    """Projected gradient descent on the simplex.

    Convex objective, convex feasible set and a step of 1/L: this converges to
    the global optimum.  It stops early once the iterate stops moving, so the
    step budget is a ceiling rather than a cost.
    """
    w = list(start) if start is not None else [1.0 / n] * n
    for _ in range(steps):
        g = grad_fn(w)
        nxt = project_to_simplex([wi - step_size * gi for wi, gi in zip(w, g)])
        if max(abs(a - b) for a, b in zip(nxt, w)) < tolerance:
            return nxt
        w = nxt
    return w


# ---------------------------------------------------------------------------
# Optimisers
# ---------------------------------------------------------------------------


def portfolio_variance(cov: list[list[float]], w: Sequence[float]) -> float:
    return sum(wi * s for wi, s in zip(w, fl.matvec(cov, w)))


def portfolio_return(mu: Sequence[float], w: Sequence[float]) -> float:
    return sum(wi * m for wi, m in zip(w, mu))


def min_variance(cov: list[list[float]], **kw) -> list[float]:
    """Minimum-variance portfolio.  Needs no expected returns at all, which is
    exactly why it survives out of sample: expected returns are the input we
    estimate worst."""
    n = len(cov)
    lipschitz = 2.0 * largest_eigenvalue(cov)
    step = 1.0 / lipschitz if lipschitz > 0 else 1.0
    return _projected_gradient(lambda w: [2.0 * x for x in fl.matvec(cov, w)],
                               n, step, **kw)


def max_utility(mu: Sequence[float], cov: list[list[float]],
                risk_aversion: float, **kw) -> list[float]:
    """Maximise w'mu - (lambda/2) w'Sigma w."""
    n = len(mu)
    lipschitz = risk_aversion * largest_eigenvalue(cov)
    step = 1.0 / lipschitz if lipschitz > 0 else 1.0

    def grad(w):
        sw = fl.matvec(cov, w)
        return [-m + risk_aversion * s for m, s in zip(mu, sw)]

    return _projected_gradient(grad, n, step, **kw)


def efficient_frontier(mu: Sequence[float], cov: list[list[float]],
                       n_points: int = 40,
                       lam_lo: float = 0.4, lam_hi: float = 240.0
                       ) -> list[tuple[float, float, list[float]]]:
    """Trace the long-only frontier by sweeping risk aversion.

    Returns (volatility, return, weights) sorted by volatility.  Lambda is swept
    geometrically because the interesting part of the frontier is compressed at
    the low-risk end."""
    out = []
    for k in range(n_points):
        lam = lam_lo * (lam_hi / lam_lo) ** (k / max(n_points - 1, 1))
        w = max_utility(mu, cov, lam, steps=3_000)
        out.append((math.sqrt(portfolio_variance(cov, w)), portfolio_return(mu, w), w))
    return sorted(out)


def max_sharpe(mu: Sequence[float], cov: list[list[float]], rf: float = 0.0,
               n_points: int = 60) -> list[float]:
    """Tangency portfolio, found as the frontier point with the highest Sharpe.

    The closed-form tangency solution requires inverting the covariance matrix
    and permits shorts; on a long-only mandate it is simply the wrong answer.
    Searching the constrained frontier gives the right one, and cannot blow up
    on a near-singular covariance matrix."""
    best, best_sharpe = None, -1e18
    for vol, ret, w in efficient_frontier(mu, cov, n_points=n_points):
        if vol <= 0:
            continue
        s = (ret - rf) / vol
        if s > best_sharpe:
            best, best_sharpe = w, s
    return best or [1.0 / len(mu)] * len(mu)


def risk_parity(cov: list[list[float]], iterations: int = 600,
                tolerance: float = 1e-12) -> list[float]:
    """Equal risk contribution portfolio.

    Fixed-point iteration: scale each weight by the ratio of its target risk
    share to its actual one, renormalise, repeat.  Converges monotonically for
    a positive-definite covariance matrix and needs no expected returns."""
    n = len(cov)
    w = [1.0 / n] * n
    target = 1.0 / n
    for _ in range(iterations):
        sw = fl.matvec(cov, w)
        var = sum(wi * s for wi, s in zip(w, sw))
        if var <= 0:
            break
        rc = [wi * s / var for wi, s in zip(w, sw)]
        new = [wi * (target / r) ** 0.5 if r > 0 else wi for wi, r in zip(w, rc)]
        total = sum(new)
        new = [x / total for x in new]
        if max(abs(a - b) for a, b in zip(new, w)) < tolerance:
            w = new
            break
        w = new
    return w


def equal_weight(n: int) -> list[float]:
    return [1.0 / n] * n


def inverse_volatility(cov: list[list[float]]) -> list[float]:
    """Naive risk weighting: 1/sigma, normalised.  Risk parity with all
    correlations assumed equal - useful as a control that isolates how much of
    risk parity's benefit comes from the correlation structure."""
    inv = [1.0 / math.sqrt(cov[i][i]) for i in range(len(cov))]
    total = sum(inv)
    return [x / total for x in inv]


# ---------------------------------------------------------------------------
# Covariance estimation
# ---------------------------------------------------------------------------


@dataclass
class Shrinkage:
    covariance: list[list[float]]
    intensity: float
    target_variance: float


def ledoit_wolf(returns: list[list[float]]) -> Shrinkage:
    """Ledoit-Wolf (2004) shrinkage toward a scaled identity target.

    `returns` is n_assets x n_observations.

        F      = (trace(S)/n) I                       the target
        delta2 = ||S - F||_F^2 / n                    dispersion of S from F
        beta2  = (1/T^2) sum_t ||x_t x_t' - S||_F^2 / n     estimation error in S
        rho    = min(beta2 / delta2, 1)               shrinkage intensity
        Sigma  = rho F + (1 - rho) S

    The intuition is the whole reason this project uses it: the sample
    covariance matrix is unbiased but noisy, and mean-variance optimisation
    concentrates weight on exactly the smallest eigenvalues, which are the
    noisiest part of it.  Pulling the estimate toward a structured target
    trades a little bias for a large reduction in variance, and the optimal
    trade-off is estimable from the data rather than guessed.
    """
    n = len(returns)
    T = len(returns[0])
    means = [fl.mean(r) for r in returns]
    x = [[r[t] - means[i] for t in range(T)] for i, r in enumerate(returns)]

    S = [[sum(x[i][t] * x[j][t] for t in range(T)) / T for j in range(n)] for i in range(n)]

    mu_hat = sum(S[i][i] for i in range(n)) / n
    F = [[mu_hat if i == j else 0.0 for j in range(n)] for i in range(n)]

    delta2 = sum((S[i][j] - F[i][j]) ** 2 for i in range(n) for j in range(n)) / n

    beta_sum = 0.0
    for t in range(T):
        for i in range(n):
            xi = x[i][t]
            for j in range(n):
                beta_sum += (xi * x[j][t] - S[i][j]) ** 2
    beta2 = beta_sum / (T * T) / n

    rho = 0.0 if delta2 <= 0 else min(max(beta2 / delta2, 0.0), 1.0)
    shrunk = [[rho * F[i][j] + (1.0 - rho) * S[i][j] for j in range(n)] for i in range(n)]
    return Shrinkage(shrunk, rho, mu_hat)


def shrink_toward_identity(cov: list[list[float]], intensity: float) -> list[list[float]]:
    """Manual shrinkage at a chosen intensity, for the sensitivity analysis."""
    n = len(cov)
    mu_hat = sum(cov[i][i] for i in range(n)) / n
    return [[intensity * (mu_hat if i == j else 0.0) + (1.0 - intensity) * cov[i][j]
             for j in range(n)] for i in range(n)]


def condition_number(cov: list[list[float]], iterations: int = 400) -> float:
    """Ratio of largest to smallest eigenvalue, via power iteration on the
    matrix and on its inverse.  A large condition number is the quantitative
    statement of "this covariance matrix cannot be trusted to be inverted"."""
    largest = largest_eigenvalue(cov, iterations)
    try:
        smallest_inverse = largest_eigenvalue(fl.inverse(cov), iterations)
    except (ValueError, ZeroDivisionError):
        return float("inf")
    if smallest_inverse <= 0:
        return float("inf")
    return largest * smallest_inverse
