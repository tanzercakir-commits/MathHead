"""
mathhead.discovery.adversarial — red-team the verifier (roadmap Q/verification hardening).

A verification engine is only worth its soundness. This module ATTACKS the kernel and the independent
checker with a large, systematic battery of FALSE claims and confirms every one is rejected — plus
positive controls (true claims that MUST be accepted, so we're not just rejecting everything).

It cannot prove the verifier complete, but it demonstrates soundness on a broad adversarial sweep:
every false modular claim, wrong sum closed form, bogus factorization, forged theorem, and illegal
rule application we can systematically generate is caught. A single BREACH (a false claim minted as a
theorem) would be a hard failure — the whole point of the engine.

Deterministic: the battery is an enumeration (small integer polynomials × small moduli), no
randomness.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from functools import partial
from itertools import product

from .checker import independently_verify
from .kernel import (
    CRT,
    Identity,
    KernelError,
    Residue,
    SumInduction,
    Theorem,
    check,
    prove_divides,
    prove_sum_identity,
)


def _eval_mod(poly, n, m):
    acc = 0
    for c in reversed(poly):
        acc = (acc * n + c) % m
    return acc


def _poly_value(poly, n: int) -> int:
    """Exact integer value p(n) (no modulus) — for feeding the independent checker."""
    v = 0
    for c in reversed(poly):
        v = v * n + c
    return v


def _small_polys(max_deg: int = 3, lo: int = -2, hi: int = 2):
    """All integer polynomials with degree ≤ max_deg and coeffs in [lo, hi] (trailing nonzero)."""
    rng = range(lo, hi + 1)
    for length in range(1, max_deg + 2):
        for coeffs in product(rng, repeat=length):
            if length > 1 and coeffs[-1] == 0:
                continue
            yield coeffs


def _false_divides_cases(moduli=range(2, 7)):
    """(m, poly) pairs where 'm | poly(n) for all n' is actually FALSE (some residue is nonzero)."""
    for poly in _small_polys():
        for m in moduli:
            if any(_eval_mod(poly, r, m) != 0 for r in range(m)):
                yield m, poly


@dataclass
class RobustnessReport:
    attempts: int = 0
    breaches: list = field(default_factory=list)   # (category, detail) for each false claim ACCEPTED
    positive_controls: int = 0
    positive_failures: list = field(default_factory=list)  # true claims wrongly REJECTED

    @property
    def sound(self) -> bool:
        return not self.breaches and not self.positive_failures


def attack_divides(limit: int = 600) -> list:
    """Feed false modular claims to the kernel; a breach is any that mints a theorem instead of raising."""
    breaches = []
    for i, (m, poly) in enumerate(_false_divides_cases()):
        if i >= limit:
            break
        try:
            prove_divides(m, poly)                 # must raise KernelError
            breaches.append(("Divides", f"m={m}, poly={poly}"))
        except KernelError:
            pass
    return breaches


def attack_sum_identities() -> list:
    """Feed wrong sum closed forms to the kernel."""
    breaches = []
    # Σi = n(n+1)/2 is the truth; every OTHER low-degree polynomial is a false closed form for f(i)=i
    f = (0, 1)
    wrong_gs = [(0, 1), (0, 0, 1), (1, 0, Fraction(1, 2)), (0, Fraction(1, 3), Fraction(1, 2))]
    for g in wrong_gs:
        try:
            prove_sum_identity(f, g)               # must raise (base or step fails)
            breaches.append(("SumIdentity", f"f={f}, g={g}"))
        except KernelError:
            pass
    return breaches


def attack_factorizations() -> list:
    """Feed bogus polynomial identities to the kernel."""
    breaches = []
    bogus = [((0, -1, 0, 1), (0, 1, -2, 1)),      # n³−n vs a wrong cubic
             ((1, 0, 1), (1, 0, -1)),              # n²+1 vs n²−1
             ((0, 0, 1), (0, 1))]                  # n² vs n
    for lhs, rhs in bogus:
        try:
            check(Identity(lhs, rhs))              # must raise
            breaches.append(("PolyIdentity", f"lhs={lhs}, rhs={rhs}"))
        except KernelError:
            pass
    return breaches


def attack_illegal_rules() -> list:
    """Illegal rule applications: non-coprime CRT, mismatched-poly CRT, forged theorems."""
    breaches = []
    n3 = (0, -1, 0, 1)
    fourn = (0, 4)
    attempts = [
        ("CRT non-coprime", lambda: check(CRT((Residue(2, fourn), Residue(4, fourn))))),
        ("CRT mismatched poly", lambda: check(CRT((Residue(2, n3), Residue(3, (0, 0, 1)))))),
        ("CRT of a SumIdentity", lambda: check(CRT((SumInduction((0, 1), (0, 1)), Residue(2, n3))))),
    ]
    for name, thunk in attempts:
        try:
            thunk()
            breaches.append(("IllegalRule", name))
        except KernelError:
            pass
    # forging a theorem must raise PermissionError (not KernelError)
    try:
        Theorem(6, n3)
        breaches.append(("Forgery", "Theorem() constructed directly"))
    except PermissionError:
        pass
    return breaches


def attack_checker() -> list:
    """The independent checker must also reject false modular claims."""
    breaches = []
    false_cases = [((1, 0, 1), 4), ((0, 0, 1), 3), ((1, 1), 2)]   # n²+1 mod4, n² mod3, n+1 mod2
    for poly, m in false_cases:
        fn = partial(_poly_value, poly)
        if independently_verify(fn, m):                          # must be False
            breaches.append(("Checker", f"poly={poly}, m={m}"))
    return breaches


def _positive_controls() -> tuple:
    """True claims the verifier MUST accept — guards against a verifier that rejects everything."""
    ok, failures = 0, []
    gauss = (0, Fraction(1, 2), Fraction(1, 2))               # n(n+1)/2
    truths = [
        ("6|n³−n", lambda: prove_divides(6, (0, -1, 0, 1))),
        ("30|n⁵−n", lambda: prove_divides(30, (0, -1, 0, 0, 0, 1))),
        ("Σi=n(n+1)/2", lambda: prove_sum_identity((0, 1), gauss)),
    ]
    for name, thunk in truths:
        try:
            thunk()
            ok += 1
        except Exception as e:                                   # noqa: BLE001 (control must pass)
            failures.append((name, str(e)))
    return ok, failures


def robustness_report(divides_limit: int = 600) -> RobustnessReport:
    """Run the full adversarial battery + positive controls."""
    breaches = (attack_divides(divides_limit) + attack_sum_identities()
                + attack_factorizations() + attack_illegal_rules() + attack_checker())
    attempts = min(divides_limit, sum(1 for _ in _false_divides_cases())) + 3 + 3 + 4 + 3
    ok, failures = _positive_controls()
    return RobustnessReport(attempts=attempts, breaches=breaches,
                            positive_controls=ok, positive_failures=failures)
