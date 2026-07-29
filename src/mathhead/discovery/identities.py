"""
mathhead.discovery.identities — discover polynomial FACTORIZATIONS and kernel-verify them, then use
them to EXPLAIN the modular divisibilities (roadmap: discover → prove, algebraic-identity surface).

For a polynomial p(n) the engine factors it (sympy), then INDEPENDENTLY certifies the factorization
with the kernel's `Identity` rule: expand(p) and expand(factored) must be the same polynomial (the
kernel does not trust the factoring routine — a wrong factorization fails the check and is dropped).

The payoff is explanatory. When the factorization is a run of CONSECUTIVE linear factors —
n³ − n = (n−1)·n·(n+1) — that is a product of k consecutive integers, which is ALWAYS divisible by
k!. So the engine can say WHY 6 | n³−n (three consecutive integers ⇒ divisible by 3! = 6), connecting
the algebraic identity to the modular fact discovered separately in `arithmetic.py`. Structure
explaining number, both kernel-checked.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import factorial

from .kernel import KernelError, poly_from_sympy_q, prove_identity
from .provenance import axioms_used, proof_hash

# polynomials worth factoring (the modular family + a couple of classics)
FAMILY = [
    "n**2 - 1",
    "n**2 - n",
    "n**3 - n",
    "n**3 - n**2",
    "n**2 - 4",
    "n*(n+1)*(n+2)",
]


@dataclass
class IdentityFinding:
    expression: str
    factored: str
    kernel_verified: bool = False
    proof_hash: str = ""
    axioms: tuple = ()
    consecutive_run: int = 0        # length of a consecutive-integer factor run (0 if none)
    divisibility_explained: int = 0  # the k! the run guarantees divisibility by (0 if none)


def _consecutive_linear_run(factored) -> int:
    """If the factored form is a product of DISTINCT linear factors (n + c) whose constants c form a
    run of consecutive integers, return the run length; else 0. That means a product of consecutive
    integers (⇒ divisible by run!)."""
    import sympy
    n = sympy.Symbol("n")
    factors = sympy.Mul.make_args(sympy.factor(factored))
    offsets = []
    for fac in factors:
        poly = sympy.Poly(fac, n) if fac.has(n) else None
        if poly is None or poly.degree() != 1:
            return 0
        a, b = poly.all_coeffs()          # a*n + b
        if a != 1:                        # only monic linear factors are "integer n + c"
            return 0
        offsets.append(int(b))
    offsets.sort()
    if len(offsets) >= 2 and offsets == list(range(offsets[0], offsets[0] + len(offsets))):
        return len(offsets)
    return 0


def discover_factorization(expr: str) -> IdentityFinding:
    """Factor p(n), kernel-verify expand(p) = expand(factored), and detect a consecutive-integer run
    that explains a k! divisibility."""
    import sympy
    e = sympy.sympify(expr)
    factored = sympy.factor(e)
    finding = IdentityFinding(expr, str(factored))
    try:
        lhs = poly_from_sympy_q(str(sympy.expand(e)))
        rhs = poly_from_sympy_q(str(sympy.expand(factored)))
        _thm, term = prove_identity(lhs, rhs)          # kernel certifies the factorization
        finding.kernel_verified = True
        finding.proof_hash = proof_hash(term)
        finding.axioms = tuple(sorted(axioms_used(term)))
    except KernelError:
        finding.kernel_verified = False
    run = _consecutive_linear_run(factored)
    if run:
        finding.consecutive_run = run
        finding.divisibility_explained = factorial(run)   # product of `run` consecutive ints | run!
    return finding


_RUN_CACHE: dict = {}


def run_identity_discovery() -> list:
    """Factor every family member, kernel-verify, and record the divisibility explanations. Memoized."""
    if "all" not in _RUN_CACHE:
        _RUN_CACHE["all"] = [discover_factorization(expr) for expr in FAMILY]
    return list(_RUN_CACHE["all"])
