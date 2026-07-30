"""
mathhead.discovery.generalize — reverse-engineer a specific finding into the GENERAL principle it is an
instance of (roadmap P2: "interesting result → search for the more general principle that explains it").

`identities.py` EXPLAINS a single finding — `6 | n³−n` holds because `n³−n = (n−1)n(n+1)` is a product
of 3 consecutive integers, so `3! = 6` divides it. P2 goes one step further: it LIFTS that explanation
over a PARAMETER. From "3 consecutive ints ⇒ divisible by 3!" it proposes the general law

    for every k ≥ 1, the product of k consecutive integers is divisible by k!

then KERNEL-verifies the law for k = 1..K (each `k! | ∏_{i=0}^{k−1}(n+i)` is universal in n and checked
by the kernel's RESIDUE rule), and reports the specific finding as one instance of it.

HONEST status: every tested instance is kernel_verified (universal in n, via residue exhaustion); the
∀k statement itself is the classical binomial-coefficient integrality theorem — `C(n,k) = ∏/k! ∈ ℤ` —
a structural_argument (cited), NOT machine-proved for unboundedly many k. We generalize the pattern and
verify a finite window; we do not overclaim the unbounded quantifier.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from math import factorial

from .identities import discover_factorization
from .kernel import KernelError, prove_divides
from .provenance import axioms_used, proof_hash

_CITATION = "product of k consecutive integers ≡ k!·C(n,k); C(n,k) ∈ ℤ (binomial integrality)"


def _poly_mul(a: tuple, b: tuple) -> tuple:
    """Exact integer polynomial product (coeffs low→high)."""
    out = [0] * (len(a) + len(b) - 1)
    for i, ca in enumerate(a):
        for j, cb in enumerate(b):
            out[i + j] += ca * cb
    return tuple(out)


def consecutive_product(k: int) -> tuple:
    """The polynomial ∏_{i=0}^{k−1}(n+i) — a product of k consecutive integers — as an integer tuple."""
    poly = (1,)
    for i in range(k):
        poly = _poly_mul(poly, (i, 1))          # ×(n + i)
    return poly


@dataclass
class GeneralInstance:
    k: int
    modulus: int                # k!
    poly: tuple                 # ∏_{i=0}^{k−1}(n+i)
    kernel_verified: bool       # the kernel proved k! | poly (universal in n)
    proof_hash: str = ""
    axioms: tuple = ()


@dataclass
class Generalization:
    specific: str                       # the finding we started from, e.g. "n**3 - n"
    specific_modulus: int               # e.g. 6
    run_length: int                     # k detected in the specific finding (0 ⇒ no generalization)
    principle: str = ""
    parameter: str = "k = number of consecutive integer factors"
    instances: list = field(default_factory=list)
    instance_status: str = "kernel_verified"      # per-k, universal in n
    universal_status: str = "structural_argument"  # the ∀k claim (cited, not machine-proved)
    citation: str = _CITATION
    generalized: bool = False


def _instance(k: int) -> GeneralInstance:
    poly = consecutive_product(k)
    m = factorial(k)
    try:
        _thm, term = prove_divides(m, poly)      # kernel proves k! | ∏(n+i), universal in n
        return GeneralInstance(k, m, poly, True, proof_hash(term), tuple(sorted(axioms_used(term))))
    except KernelError:
        return GeneralInstance(k, m, poly, False)


def general_principle(k_max: int = 5) -> list:
    """Kernel-verified evidence for the general law, one entry per k in 1..k_max: `k! | ∏(n+i)`."""
    return [_instance(k) for k in range(1, k_max + 1)]


def generalize(expr: str, m: int, k_max: int = 6) -> Generalization:
    """Reverse-engineer `m | p(n)` into the consecutive-product principle, if it is an instance of one.

    Uses `identities` to detect that p(n) is a product of a consecutive run of length k with m = k!;
    if so, returns the general law plus kernel-verified instances for k = 1..k_max. Otherwise returns a
    Generalization with `generalized=False` (honest: no consecutive-product generalization was found)."""
    finding = discover_factorization(expr)
    k = finding.consecutive_run
    if not k or finding.divisibility_explained != m:
        return Generalization(expr, m, 0, generalized=False)
    principle = ("for every k ≥ 1, the product of k consecutive integers ∏_{i=0}^{k−1}(n+i) "
                 "is divisible by k!")
    instances = general_principle(max(k, k_max))
    return Generalization(
        specific=expr,
        specific_modulus=m,
        run_length=k,
        principle=principle,
        instances=instances,
        generalized=all(inst.kernel_verified for inst in instances),
    )
