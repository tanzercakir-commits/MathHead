"""
mathhead.discovery.sequences — a second arithmetic generator: discover-and-prove SUM identities.

For a term f(i) the engine computes the partial sums S(n) = Σ_{i=1}^n f(i), FITS a closed-form
polynomial g(n) (interpolation — the "guess the formula" step), REFUTES counterexample-first over
a larger range, and PROVES the survivor by induction with MathHead: it checks the base case and
lets MathHead verify the inductive step g(n) − g(n−1) = f(n) (`solver_verified`). Base + verified
step ⇒ the identity holds for all n.

If the sequence is not polynomial (e.g. Σ 2^i), the fitted polynomial matches the fit points but
DIVERGES beyond them, so the extended counterexample-first check refutes it — the engine does not
force a formula onto a sequence that has none.
"""
from __future__ import annotations

from dataclasses import dataclass

import sympy

from .judge import judge_identity

_n = sympy.Symbol("n")


def _power(p: int):
    def f(i: int) -> int:
        return i**p
    return f


def _odd(i: int) -> int:
    return 2 * i - 1


def _pow2(i: int) -> int:
    return 2**i


# (f(i) as an expression, f(n) as an expression, the callable)
FAMILY = [
    ("i", "n", _power(1)),
    ("i**2", "n**2", _power(2)),
    ("i**3", "n**3", _power(3)),
    ("2*i - 1", "2*n - 1", _odd),
    ("2**i", "2**n", _pow2),            # non-polynomial trap -> should be refuted
]


@dataclass
class SumIdentityFinding:
    term: str                # f(i)
    closed_form: str         # discovered g(n)
    refute_status: str       # "no_counterexample_within_bound" | "refuted"
    verdict: str             # "proved" | "refuted" | "unknown"
    certainty: str
    checked_upto: int


def partial_sum(f, k: int) -> int:
    return sum(f(i) for i in range(1, k + 1))


def discover_closed_form(f, n_points: int = 8):
    """Fit a closed-form polynomial to the partial sums (interpolation)."""
    pts = [(k, partial_sum(f, k)) for k in range(1, n_points + 1)]
    return sympy.simplify(sympy.interpolate(pts, _n))


def _first_mismatch(f, g, upto: int):
    for k in range(1, upto + 1):
        if partial_sum(f, k) != g.subs(_n, k):
            return k
    return None


def discover_and_prove_sum(term_i: str, term_n: str, f, n_points: int = 8, check_upto: int = 16):
    """Discover the closed form, refute counterexample-first, then prove the survivor by induction
    (base case + MathHead-verified step)."""
    g = discover_closed_form(f, n_points)
    if _first_mismatch(f, g, check_upto) is not None:
        return SumIdentityFinding(term_i, str(g), "refuted", "refuted", "unknown", check_upto)
    base_ok = g.subs(_n, 1) == f(1)
    step = judge_identity(f"({g}) - ({sympy.expand(g.subs(_n, _n - 1))})", term_n)
    verdict = "proved" if (base_ok and step.status == "proved") else step.status
    return SumIdentityFinding(
        term_i, str(g), "no_counterexample_within_bound", verdict, step.certainty, check_upto)


_RUN_CACHE: dict = {}


def run_sequence_discovery(check_upto: int = 16) -> list:
    """Run discover → refute → prove over the term family. Memoized (deterministic)."""
    if check_upto not in _RUN_CACHE:
        _RUN_CACHE[check_upto] = [
            discover_and_prove_sum(ti, tn, f, check_upto=check_upto) for ti, tn, f in FAMILY
        ]
    return list(_RUN_CACHE[check_upto])
