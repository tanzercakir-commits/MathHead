"""
mathhead.discovery.kernel — a minimal LCF-style PROOF KERNEL (roadmap Track M1/M2).

So far the engine proves a modular fact with a strategy and RE-CHECKS it (ADR-D0016/17). This goes
one level deeper: a theorem may be created ONLY by the kernel's inference rules, so a *proof* is a
TERM built out of those rules and nothing else. Forge-resistance is LCF-style — `Theorem` has a
guarded constructor (its `__init__` always raises; only the module-private `_mint` builds one), so
any `Theorem` value in the running system is, by construction, the output of a checked rule.

FRAGMENT (honest scope). A judgment is `Divides(m, p)` = "∀ integer n, m divides p(n)", where p is a
univariate integer polynomial (coefficients low→high, exact). Two inference rules:

  • RESIDUE (primitive) — if p(r) ≡ 0 (mod m) for every residue r ∈ {0,…,m−1}, then ⊢ Divides(m, p).
    SOUND: p has integer coefficients, so p(n) mod m depends only on n mod m; checking all residues
    is a COMPLETE decision procedure for the atomic judgment. The kernel runs the sweep itself.
  • CRT (composition) — from ⊢ Divides(m₁,p) … ⊢ Divides(m_k,p) with the mᵢ PAIRWISE COPRIME,
    conclude ⊢ Divides(∏mᵢ, p). The kernel checks coprimality and that every premise is a genuine
    Theorem about the SAME p.

TRUST BASE — stated plainly. The kernel is sound IF (a) the residue sweep is correct and (b) the CRT
rule is sound. Both are a few auditable lines. We do NOT derive RESIDUE from ring/induction axioms —
that deeper kernel is later M-track work; here residue-exhaustion is the trusted primitive. A false
claim cannot mint a Theorem: RESIDUE for Divides(4, n²+1) fails the sweep (n=1 → 2) and the kernel
RAISES; nothing downstream can fabricate the missing Theorem, because the constructor is guarded.

Stdlib only (like the independent checker) — no solver, no sympy in the core; the sympy bridge is a
separate, optional helper.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import gcd, prod


class KernelError(Exception):
    """Raised when a proof term is malformed or a rule is misapplied. No Theorem is produced."""


Poly = tuple  # coefficients low→high, e.g. (0, -1, 0, 1) == n³ − n


def _eval_mod(poly: Poly, n: int, m: int) -> int:
    """p(n) mod m by Horner — exact integer arithmetic."""
    acc = 0
    for c in reversed(poly):
        acc = (acc * n + c) % m
    return acc


def _poly_str(poly: Poly) -> str:
    terms = []
    for i, c in enumerate(poly):
        if c == 0:
            continue
        terms.append(str(c) if i == 0 else (f"{c}*n" if i == 1 else f"{c}*n^{i}"))
    return " + ".join(terms) if terms else "0"


def _norm(poly: Poly) -> Poly:
    """Canonical form: integer coeffs, trailing zeros trimmed (so 'same polynomial' is well-defined)."""
    p = list(poly)
    if any(int(c) != c for c in p):
        raise KernelError("kernel fragment requires INTEGER polynomial coefficients")
    p = [int(c) for c in p]
    while len(p) > 1 and p[-1] == 0:
        p.pop()
    return tuple(p)


# --- the guarded theorem type (LCF-style) -----------------------------------------------------

class Theorem:
    """⊢ Divides(modulus, poly). Cannot be constructed directly — only the kernel's rules mint one."""
    __slots__ = ("modulus", "poly")

    def __init__(self, *args, **kwargs):
        raise PermissionError(
            "Theorems are created only by the kernel's inference rules (check/residue/crt), "
            "never constructed directly")

    def __repr__(self) -> str:
        return f"⊢ Divides({self.modulus}, {_poly_str(self.poly)})"

    def __eq__(self, other) -> bool:
        return (isinstance(other, Theorem)
                and self.modulus == other.modulus and self.poly == other.poly)

    def __hash__(self) -> int:
        return hash((Theorem, self.modulus, self.poly))


def _mint(modulus: int, poly: Poly) -> Theorem:
    """Module-private theorem constructor. Every mint is preceded by a rule's verification."""
    t = object.__new__(Theorem)
    object.__setattr__(t, "modulus", int(modulus))
    object.__setattr__(t, "poly", _norm(poly))
    return t


# --- proof terms (an algebraic data type the kernel interprets) --------------------------------

@dataclass(frozen=True)
class Residue:
    """Leaf proof term: assert Divides(modulus, poly) by exhausting residues."""
    modulus: int
    poly: Poly


@dataclass(frozen=True)
class CRT:
    """Composition proof term: combine Divides(mᵢ, poly) over pairwise-coprime moduli."""
    parts: tuple            # tuple[ProofTerm, ...]


# --- the kernel: the ONLY way to turn a proof term into a Theorem -----------------------------

def check(term) -> Theorem:
    """Interpret a proof term, VERIFYING every rule application; return the Theorem it proves or
    raise KernelError. This is the whole trusted core."""
    if isinstance(term, Residue):
        m = int(term.modulus)
        if m < 1:
            raise KernelError(f"RESIDUE: modulus must be ≥ 1, got {m}")
        p = _norm(term.poly)
        bad = [r for r in range(m) if _eval_mod(p, r, m) != 0]
        if bad:
            raise KernelError(
                f"RESIDUE fails: Divides({m}, {_poly_str(p)}) — residue r={bad[0]} gives "
                f"{_eval_mod(p, bad[0], m)} ≠ 0 (mod {m})")
        return _mint(m, p)

    if isinstance(term, CRT):
        if not term.parts:
            raise KernelError("CRT: needs at least one premise")
        thms = [check(t) for t in term.parts]          # recursively verify every premise
        p0 = thms[0].poly
        for th in thms[1:]:
            if th.poly != p0:
                raise KernelError("CRT: all premises must be about the SAME polynomial")
        mods = [th.modulus for th in thms]
        for i in range(len(mods)):
            for j in range(i + 1, len(mods)):
                if gcd(mods[i], mods[j]) != 1:
                    raise KernelError(
                        f"CRT: moduli must be pairwise coprime — gcd({mods[i]},{mods[j]}) ≠ 1")
        return _mint(prod(mods), p0)

    raise KernelError(f"unknown proof term: {type(term).__name__}")


# --- a heuristic PROVER that emits proof terms (untrusted — the kernel checks its output) -------

def _factor_prime_powers(m: int) -> list:
    """m = ∏ pᵢ^aᵢ → [p₁^a₁, …] (pairwise coprime). Trial division — m is small here."""
    out, d, x = [], 2, m
    while d * d <= x:
        if x % d == 0:
            pk = 1
            while x % d == 0:
                pk *= d
                x //= d
            out.append(pk)
        d += 1
    if x > 1:
        out.append(x)
    return out or [1]


def prove_divides(m: int, poly: Poly):
    """Build a proof term for Divides(m, poly) — residue-prove each prime power, CRT-compose — then
    KERNEL-CHECK it. Returns (Theorem, proof_term). Raises KernelError if the claim is false (the
    residue sweep on some prime power fails). The prover is untrusted; the returned Theorem is only
    as good as the kernel check that produced it."""
    parts = tuple(Residue(pk, poly) for pk in _factor_prime_powers(m))
    term = parts[0] if len(parts) == 1 else CRT(parts)
    return check(term), term
