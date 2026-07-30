"""
mathhead.discovery.pslq_hunt — PSLQ constant-formula hunt (v2A3, Real Discovery Program Kademe 1).

The BBP formula for π was FOUND by an integer-relation search (PSLQ), not by a human derivation — the
canonical proof that machines find things in exponential haystacks that humans missed. This module is
that instrument, built on mpmath's exact arbitrary-precision engine (`mpmath.pslq` / `mpmath.findpoly`),
with the honesty protocol as the core design:

  * TWO-PRECISION PROTOCOL — a relation is DISCOVERED at working precision (default 60 digits) and then
    RE-VERIFIED from scratch at a much higher precision (default 220 digits). A numerical artifact that
    only "holds" at low precision dies at the second gate; only relations whose residual collapses to the
    high-precision floor survive.
  * NOISE REJECTION — with bounded coefficient height, PSLQ on unrelated constants (e, π) or on an
    arbitrary literal must return None. No low-height relation ⇒ we say NONE, we do not lower the bar.
  * HONEST STATUS — a surviving relation is a `numerical_conjecture`. PSLQ evidence is NOT proof; the
    kernel cannot check transcendental identities. We never label these proved. (ζ(2)=π²/6 happens to be
    a known theorem — the ATTRIBUTION says that; the instrument's own epistemic claim stays numerical.)

Rediscovery calibration (all verified at 220 digits): √2 → x²−2, φ → x²−x−1, 6ζ(2)=π², 90ζ(4)=π⁴.
Deterministic: fixed constant registry, fixed precisions, no randomness.
"""
from __future__ import annotations

from dataclasses import dataclass

import mpmath as mp

# name → zero-argument constructor evaluated at the CURRENT working precision
CONSTANTS: dict = {
    "pi": lambda: mp.pi,
    "e": lambda: mp.e,
    "gamma": lambda: mp.euler,
    "ln2": lambda: mp.ln(2),
    "catalan": lambda: mp.catalan,
    "zeta2": lambda: mp.zeta(2),
    "zeta3": lambda: mp.zeta(3),
    "zeta4": lambda: mp.zeta(4),
    "pi^2": lambda: mp.pi ** 2,
    "pi^4": lambda: mp.pi ** 4,
    "sqrt2": lambda: mp.sqrt(2),
    "phi": lambda: mp.phi,
    # a fixed arbitrary literal — the noise-control constant (no known low-height relations)
    "noise": lambda: mp.mpf("0.73916283565179862041350146073019284659103718652974102935861"),
}


@dataclass
class NumericalConjecture:
    kind: str                    # "algebraic_polynomial" | "integer_relation"
    statement: str
    names: tuple
    coefficients: tuple
    discovered_at_dps: int
    verified_at_dps: int
    residual_exponent: int       # residual ≈ 10^exponent at verification precision
    status: str = "numerical_conjecture"    # NEVER "proved" — PSLQ evidence is not proof


def _values(names, dps: int) -> list:
    with mp.workdps(dps):
        return [+CONSTANTS[nm]() for nm in names]        # unary + rounds to current precision


def _residual_exp(x) -> int:
    return int(mp.floor(mp.log10(abs(x)))) if x != 0 else -mp.inf


def find_relation(names, dps: int = 60, verify_dps: int = 220,
                  maxcoeff: int = 10 ** 6) -> NumericalConjecture | None:
    """Integer relation Σ aᵢ·cᵢ = 0 among the named constants, or None. Two-precision protocol: found at
    `dps`, re-verified from scratch at `verify_dps` (fails the second gate ⇒ rejected, None)."""
    with mp.workdps(dps):
        rel = mp.pslq(_values(names, dps), maxcoeff=maxcoeff, maxsteps=10 ** 5)
    if rel is None:
        return None
    with mp.workdps(verify_dps):
        vals = _values(names, verify_dps)
        residual = mp.fsum(a * v for a, v in zip(rel, vals))
        tol = mp.mpf(10) ** (-(verify_dps - 40))         # far below any coincidence, above the fp floor
        if abs(residual) > tol:
            return None                                   # numerical artifact — dies at the second gate
        rexp = _residual_exp(residual)
    stmt = " + ".join(f"{a}*{nm}" for a, nm in zip(rel, names) if a) + " = 0"
    return NumericalConjecture("integer_relation", stmt, tuple(names), tuple(int(a) for a in rel),
                               dps, verify_dps, rexp)


def find_algebraic(name: str, degree: int = 4, dps: int = 60, verify_dps: int = 220,
                   maxcoeff: int = 10 ** 6) -> NumericalConjecture | None:
    """Integer polynomial p (deg ≤ `degree`) with p(c) = 0 for the named constant, or None — same
    two-precision protocol. √2 → x²−2; π at bounded degree/height → honestly None."""
    with mp.workdps(dps):
        poly = mp.findpoly(CONSTANTS[name](), degree, maxcoeff=maxcoeff)
    if poly is None:
        return None
    with mp.workdps(verify_dps):
        residual = mp.polyval(poly, CONSTANTS[name]())
        tol = mp.mpf(10) ** (-(verify_dps - 40))
        if abs(residual) > tol:
            return None
        rexp = _residual_exp(residual)
    deg = len(poly) - 1
    terms = [f"{c}*x^{deg - i}" for i, c in enumerate(poly) if c]
    return NumericalConjecture("algebraic_polynomial", " + ".join(terms) + " = 0", (name,),
                               tuple(int(c) for c in poly), dps, verify_dps, rexp)


# the deterministic calibration sweep: known rediscoveries MUST land, unrelated pairs MUST yield None
_RELATION_TARGETS = [("zeta2", "pi^2"), ("zeta4", "pi^4"), ("e", "pi"), ("gamma", "ln2"),
                     ("noise", "pi")]
_ALGEBRAIC_TARGETS = ["sqrt2", "phi", "pi"]


def hunt_constants(dps: int = 60, verify_dps: int = 220) -> dict:
    """Run the calibration sweep. Returns {"found": [NumericalConjecture...], "none": [target...]} —
    the `none` list is a RESULT, not a failure (no low-height relation exists at this bound)."""
    found, none = [], []
    for pair in _RELATION_TARGETS:
        nc = find_relation(pair, dps, verify_dps)
        (found.append(nc) if nc else none.append(f"relation{pair}"))
    for name in _ALGEBRAIC_TARGETS:
        nc = find_algebraic(name, 4, dps, verify_dps)
        (found.append(nc) if nc else none.append(f"algebraic({name})"))
    return {"found": found, "none": none}
