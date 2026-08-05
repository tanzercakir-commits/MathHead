"""
mathhead.discovery.spectral_cert — EXACT spectral certification in pure integer arithmetic (v2B支撑).

The counterexample hunter needs to certify claims like `λ₁(G) + μ(G) < √(n−1) + 1` (λ₁ = adjacency
spectral radius). Floating point is fine for SEARCH but never for the VERDICT — near the boundary a
float error could manufacture a fake counterexample. This module decides the two needed comparisons
EXACTLY, using only Python integers:

  * `lambda1_below(g, r)` — is λ₁(G) < r for rational r = p/q?  λ₁ < p/q  ⟺  (p·I − q·A) is positive
    definite (A symmetric ⇒ Sylvester's criterion: every leading principal minor > 0). p·I − q·A is an
    INTEGER matrix; its minors are computed by fraction-free Bareiss elimination — exact, no rationals.
  * `sqrt_bound_above(s_num, s_den, m)` — is s = s_num/s_den < √m?  For s ≥ 0:  ⟺  s_num² < m · s_den²
    — one integer comparison.

`certify_lambda1_plus_mu_below(g, mu, float_hint)` combines them: find a rational r with
λ₁ < r  AND  r + μ < √(n−1) + 1 (the second via the integer square test). If such r exists the strict
inequality λ₁ + μ < √(n−1) + 1 is PROVED (a self-verifying witness); if the slack is zero (stars: λ₁ =
√(n−1), μ = 1) no such r exists and certification honestly returns None.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

from .objects import Graph


def _int_det_bareiss(mat: list) -> int:
    """Exact determinant of a square integer matrix (fraction-free Bareiss). Pure int arithmetic."""
    m = [row[:] for row in mat]
    n = len(m)
    if n == 0:
        return 1
    sign, prev = 1, 1
    for k in range(n - 1):
        if m[k][k] == 0:                                   # pivot: swap in a nonzero row
            for i in range(k + 1, n):
                if m[i][k] != 0:
                    m[k], m[i] = m[i], m[k]
                    sign = -sign
                    break
            else:
                return 0
        for i in range(k + 1, n):
            for j in range(k + 1, n):
                m[i][j] = (m[i][j] * m[k][k] - m[i][k] * m[k][j]) // prev
        prev = m[k][k]
    return sign * m[n - 1][n - 1]


def _shifted_matrix(g: Graph, p: int, q: int) -> list:
    """The integer matrix p·I − q·A for the adjacency matrix A of g."""
    mat = [[p if i == j else 0 for j in range(g.n)] for i in range(g.n)]
    for (u, v) in g.edges:
        mat[u][v] = mat[v][u] = -q
    return mat


def lambda1_below(g: Graph, r: Fraction) -> bool:
    """EXACT: is λ₁(G) < r?  (r > 0 required — λ₁ ≥ 0 for any graph with a vertex.)
    Sylvester on the integer matrix p·I − q·A: positive definite ⟺ all leading minors > 0."""
    r = Fraction(r)
    p, q = r.numerator, r.denominator
    if p <= 0:
        return False
    mat = _shifted_matrix(g, p, q)
    for k in range(1, g.n + 1):
        if _int_det_bareiss([row[:k] for row in mat[:k]]) <= 0:
            return False
    return True


def sqrt_bound_above(s: Fraction, m: int) -> bool:
    """EXACT: is s < √m (for s given as a rational)? Negative s is trivially below; else square test."""
    s = Fraction(s)
    if s < 0:
        return True
    return s.numerator ** 2 < m * s.denominator ** 2


@dataclass
class SpectralCertificate:
    """A self-verifying, pure-integer proof that λ₁(G) + μ < √(n−1) + 1 for the given graph."""
    n: int
    mu: int                     # exact matching number (integer)
    r: Fraction                 # the rational separator: λ₁ < r  AND  r + μ − 1 < √(n−1)
    statement: str
    method: str = "integer Sylvester (Bareiss minors) + integer square comparison"
    certainty: str = "exact_integer_certificate"


def certify_lambda1_plus_mu_below(g: Graph, mu: int, float_hint: float):
    """Try to PROVE λ₁(G) + μ < √(n−1) + 1 exactly. Returns a SpectralCertificate or None (None also
    covers the equality case — stars — where no separating rational exists)."""
    if g.n < 3:
        return None
    target_m = g.n - 1
    for eps in (1e-12, 1e-9, 1e-7, 1e-5, 1e-4, 1e-3, 1e-2):
        r = Fraction(float_hint + eps).limit_denominator(10 ** 9)
        if r <= 0:
            continue
        # (a) r + μ < √(n−1) + 1  ⟺  (r + μ − 1) < √(n−1)   [integer square test]
        if not sqrt_bound_above(r + mu - 1, target_m):
            continue                                       # r already too big — smaller eps won't help either
        # (b) λ₁ < r   [integer Sylvester]
        if lambda1_below(g, r):
            return SpectralCertificate(
                g.n, mu, r,
                f"lambda1 < {r} and {r} + {mu} - 1 < sqrt({target_m}); hence "
                f"lambda1 + mu < sqrt(n-1) + 1 on n={g.n}")
    return None
