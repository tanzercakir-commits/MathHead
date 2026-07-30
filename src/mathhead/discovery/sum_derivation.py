"""
mathhead.discovery.sum_derivation — make the induction STEP explicit and DERIVE the sum rule from the
kernel's own PolyIdentity judgment (roadmap M: shrink the trusted base).

The kernel's `SumInduction` rule proves `Σ_{i=1}^n f(i) = g(n)` by checking a base case and a
telescoping step. Like RESIDUE before `congruence.py`, it reads as its own TRUSTED PRIMITIVE. This
module removes that: it re-expresses the induction step as an explicit polynomial identity and hands
it to the kernel's OWN `PolyIdentity` (`Identity`) rule — no new trusted machinery.

The derivation, for a claim `Σ_{i=1}^n f(i) = g(n)` (∀ n ≥ 1). Let S(n) = Σ_{i=1}^n f(i):
  * BASE: S(1) = f(1), so the claim at n=1 is exactly `g(1) = f(1)` — an evaluation, not an axiom.
  * STEP: assume S(n−1) = g(n−1). Then S(n) = S(n−1) + f(n) = g(n−1) + f(n). The claim S(n) = g(n)
    therefore holds at n iff `g(n) = g(n−1) + f(n)` — a UNIVERSAL polynomial identity in n, verified
    EXACTLY as a kernel `PolyIdentity`. This is the induction step, made explicit and machine-checked.
  * By the principle of induction over n ≥ 1, base ∧ step ⇒ S(n) = g(n) for all n ≥ 1.

Trust base after this: `PolyIdentity` (exact rational polynomial arithmetic, already in the kernel),
evaluation at n=1, and the principle of mathematical induction over ℕ. `SumInduction` is no longer a
black box — its step is a THEOREM about `PolyIdentity`. An independent checker re-verifies the whole
derivation (base + step) without the kernel.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

from .kernel import (
    Identity,
    KernelError,
    _norm_q,
    _poly_eval_q,
    _poly_shift_back_q,
    _poly_sub_q,
    check,
)


def _poly_add_q(a: tuple, b: tuple) -> tuple:
    """Exact rational polynomial sum a + b."""
    n = max(len(a), len(b))
    aa = [Fraction(c) for c in a] + [Fraction(0)] * (n - len(a))
    bb = [Fraction(c) for c in b] + [Fraction(0)] * (n - len(b))
    return _norm_q(tuple(aa[i] + bb[i] for i in range(n)))


@dataclass
class SumDerivation:
    f_poly: tuple                    # f(i), the summand
    g_poly: tuple                    # g(n), the claimed closed form
    base_g: Fraction = Fraction(0)   # g(1)
    base_f: Fraction = Fraction(0)   # f(1)
    base_ok: bool = False            # g(1) == f(1)
    step_lhs: tuple = ()             # g(n)               — the explicit induction-step identity…
    step_rhs: tuple = ()             # g(n−1) + f(n)      — …LHS ≡ RHS
    step_kernel_verified: bool = False   # the PolyIdentity g(n) = g(n−1)+f(n) was kernel-checked
    verified: bool = False
    trust_base: str = "PolyIdentity (exact rational polynomial arithmetic) + evaluation + induction over ℕ"


def derive_sum_identity(f_poly: tuple, g_poly: tuple) -> SumDerivation:
    """Derive `Σ_{i=1}^n f(i) = g(n)` from the kernel's PolyIdentity rule. The base case is an
    evaluation at n=1; the induction step is the explicit polynomial identity `g(n) = g(n−1) + f(n)`
    handed to the kernel. `verified` iff the base holds AND the step identity kernel-checks."""
    f = _norm_q(f_poly)
    g = _norm_q(g_poly)
    base_g, base_f = _poly_eval_q(g, 1), _poly_eval_q(f, 1)
    base_ok = base_g == base_f
    step_lhs = g                              # g(n)
    step_rhs = _poly_add_q(_poly_shift_back_q(g), f)   # g(n−1) + f(n)
    try:
        check(Identity(step_lhs, step_rhs))   # the induction step, via the kernel's OWN rule
        step_kv = True
    except KernelError:
        step_kv = False
    return SumDerivation(
        f, g, base_g, base_f, base_ok, step_lhs, step_rhs, step_kv,
        verified=base_ok and step_kv,
    )


def check_sum_derivation(d: SumDerivation) -> bool:
    """INDEPENDENT re-check (no kernel): re-evaluate the base at n=1 and re-verify the induction step
    `g(n) − g(n−1) − f(n) ≡ 0` by exact rational polynomial reconstruction. Returns True iff the
    derivation genuinely establishes `Σ_{i=1}^n f(i) = g(n)` for all n ≥ 1."""
    f = _norm_q(d.f_poly)
    g = _norm_q(d.g_poly)
    if _poly_eval_q(g, 1) != _poly_eval_q(f, 1):          # base case
        return False
    # step: g(n) − (g(n−1) + f(n)) must be identically zero
    residual = _poly_sub_q(g, _poly_add_q(_poly_shift_back_q(g), f))
    return residual == (Fraction(0),)


def sum_induction_is_derivable(f_poly: tuple, g_poly: tuple) -> bool:
    """True iff `Σ_{i=1}^n f(i) = g(n)` is derivable from PolyIdentity (explicit induction step) AND
    the independent checker agrees."""
    d = derive_sum_identity(f_poly, g_poly)
    return d.verified and check_sum_derivation(d)
