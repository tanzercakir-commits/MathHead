"""
mathhead.discovery.arithmetic — a domain where the loop closes END TO END (generate → refute →
PROVE), because MathHead is the native judge here (roadmap: the discovery loop, arithmetic domain).

For a family of polynomials p(n), the engine:
  1. DISCOVERS the modulus from data — m = gcd of the sampled values p(1), p(2), … (the largest m
     dividing every sample; i.e. the counterexample-first-optimal claim "p(n) ≡ 0 (mod m)").
  2. REFUTES counterexample-first over a larger range — a survivor is only
     `no_counterexample_within_bound`.
  3. Hands the survivor to the JUDGE (MathHead `prove_by_induction`) for a real verdict.

The result is honest by construction. The engine discovers true, sometimes-surprising facts
(n³−n ≡ 0 mod 6, stronger than mod 3; n⁵−n ≡ 0 mod 30), PROVES the ones whose induction step
MathHead can decide (`certainty=formal_proof`), and returns an honest `unknown` on the ones whose
step is beyond Z3's reach — never a fabricated proof. Overshoot moduli are killed with a minimal
counterexample before they ever reach the judge.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import reduce
from math import gcd

from .checker import check_proof
from .congruence import crt_chain_is_derivable, residue_is_derivable
from .kernel import KernelError, _factor_prime_powers, poly_from_sympy, prove_divides
from .proof_tree import proof_tree
from .provenance import axioms_used, proof_hash
from .strategy import prove_by_residues, prove_modular_divisibility


# ------------------------------ polynomial family -------------------------- #
def _consec(k: int):
    """Product of k consecutive integers starting at n: n(n+1)…(n+k-1)."""
    def f(n: int) -> int:
        r = 1
        for i in range(k):
            r *= n + i
        return r
    return f


def _pow_minus_n(p: int):
    """n**p - n."""
    def f(n: int) -> int:
        return n**p - n
    return f


def _consec_expr(k: int) -> str:
    return "*".join(["n"] + [f"(n+{i})" for i in range(1, k)])


POLY_FAMILY = [
    (_consec_expr(2), _consec(2)),
    (_consec_expr(3), _consec(3)),
    (_consec_expr(4), _consec(4)),
    ("n**2 - n", _pow_minus_n(2)),
    ("n**3 - n", _pow_minus_n(3)),
    ("n**5 - n", _pow_minus_n(5)),
    ("n**7 - n", _pow_minus_n(7)),
]


@dataclass
class ArithmeticFinding:
    expression: str
    modulus: int                  # discovered from data (gcd of samples)
    claim: str                    # the MathHead claim, e.g. "(n**3 - n) % 6 == 0"
    refute_status: str            # "no_counterexample_within_bound" | "refuted"
    verdict: str                  # "proved" | "unknown" | "refuted"  (from the judge)
    certainty: str                # judge certainty (formal_proof / unknown / ...)
    checked_upto: int
    method: str = "induction"     # "induction" | "modulus-factoring" | "residue-exhaustion"
    independently_verified: bool = False   # re-checked by the independent checker (not the prover)
    kernel_verified: bool = False          # a kernel proof TERM (RESIDUE/CRT) was checked (M1/M2)
    proof_hash: str = ""                   # deterministic kernel proof-artifact hash (M4)
    axioms: tuple = ()                     # the rules/primitives the kernel proof rests on (M5)
    residue_derivable: bool = False        # RESIDUE derivable from the factor theorem (M-floor)
    crt_derivable: bool = False            # CRT composition derivable from Bézout (M-floor)


def discovered_modulus(fn, sample=range(1, 20)) -> int:
    """The largest m dividing every sampled value (gcd of the non-zero samples)."""
    vals = [abs(fn(n)) for n in sample if fn(n) != 0]
    return reduce(gcd, vals) if vals else 0


def first_counterexample(fn, m: int, upto: int):
    """First n in 0..upto with fn(n) not divisible by m (else None)."""
    return next((n for n in range(upto + 1) if m and fn(n) % m != 0), None)


def discover_and_prove(expr: str, fn, check_upto: int = 60, judge_timeout_ms: int = 2500):
    """Discover the modulus, refute counterexample-first, then let MathHead judge the survivor via
    the modulus-factoring strategy (a prime modulus reduces to a single induction; a composite one
    factors + CRT). `judge_timeout_ms` bounds each induction — generous enough that the provable
    prime parts prove reliably, and the unprovable ones return an honest `unknown`."""
    m = discovered_modulus(fn)
    ce = first_counterexample(fn, m, check_upto)
    claim = f"({expr}) % {m} == 0"
    if ce is not None:                                  # (shouldn't happen for a gcd modulus)
        return ArithmeticFinding(expr, m, claim, "refuted", "refuted", "unknown", check_upto)
    v = prove_modular_divisibility(expr, m, timeout_ms=judge_timeout_ms)
    method = "modulus-factoring" if len(v.detail.get("prime_powers", [m])) > 1 else "induction"
    if v.status != "proved":                            # complete fallback: exhaustive residue proof
        v, method = prove_by_residues(fn, m), "residue-exhaustion"
    finding = ArithmeticFinding(
        expr, m, claim, "no_counterexample_within_bound", v.status, v.certainty, check_upto, method)
    if v.status == "proved":                            # don't trust the prover — check the proof
        finding.independently_verified = check_proof(proof_tree(finding), fn)[0]
        finding.kernel_verified, finding.proof_hash, finding.axioms = _kernel_check(expr, m)
        try:                                            # RESIDUE derivable from the factor theorem?
            finding.residue_derivable = residue_is_derivable(poly_from_sympy(expr), m)
        except KernelError:
            finding.residue_derivable = False
        finding.crt_derivable = crt_chain_is_derivable(_factor_prime_powers(m))  # CRT via Bézout
    return finding


def _kernel_check(expr: str, m: int):
    """Emit a kernel proof TERM for Divides(m, p), let the LCF kernel mint the Theorem (M1/M2), and
    derive its provenance (proof hash M4, axiom list M5). Returns (verified, hash, axioms). A false
    claim raises inside the kernel — genuine proof-carrying verification, not a trust-the-prover flag."""
    try:
        thm, term = prove_divides(m, poly_from_sympy(expr))
        if thm.modulus != m:
            return False, "", ()
        return True, proof_hash(term), tuple(sorted(axioms_used(term)))
    except KernelError:
        return False, "", ()


# The full run is deterministic; memoize it (each call otherwise re-runs the judge over the whole
# family, and the unprovable cases each spend the induction budget).
_RUN_CACHE: dict = {}


def run_arithmetic_discovery(check_upto: int = 60, judge_timeout_ms: int = 2500) -> list:
    """Run the full generate → refute → prove loop over the polynomial family."""
    key = (check_upto, judge_timeout_ms)
    if key not in _RUN_CACHE:
        _RUN_CACHE[key] = [
            discover_and_prove(expr, fn, check_upto, judge_timeout_ms) for expr, fn in POLY_FAMILY
        ]
    return list(_RUN_CACHE[key])
