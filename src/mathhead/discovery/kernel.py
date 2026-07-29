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
from fractions import Fraction
from math import comb, gcd, prod


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
        cs = _coeff_str(c)
        terms.append(cs if i == 0 else (f"{cs}*n" if i == 1 else f"{cs}*n^{i}"))
    return " + ".join(terms) if terms else "0"


def _norm(poly: Poly) -> Poly:
    """Canonical form: integer coeffs, trailing zeros trimmed (so 'same polynomial' is well-defined).
    Used by the Divides fragment, whose RESIDUE rule is sound only for INTEGER polynomials."""
    p = list(poly)
    if any(int(c) != c for c in p):
        raise KernelError("kernel fragment requires INTEGER polynomial coefficients")
    p = [int(c) for c in p]
    while len(p) > 1 and p[-1] == 0:
        p.pop()
    return tuple(p)


# --- rational polynomial arithmetic (for the SumIdentity fragment; e.g. Σi = n(n+1)/2) ---------

def _norm_q(poly: Poly) -> tuple:
    """Canonical RATIONAL polynomial (Fraction coeffs, trailing zeros trimmed)."""
    p = [Fraction(c) for c in poly]
    while len(p) > 1 and p[-1] == 0:
        p.pop()
    return tuple(p)


def _poly_sub_q(a: tuple, b: tuple) -> tuple:
    n = max(len(a), len(b))
    aa = [Fraction(c) for c in a] + [Fraction(0)] * (n - len(a))
    bb = [Fraction(c) for c in b] + [Fraction(0)] * (n - len(b))
    return _norm_q(tuple(aa[i] - bb[i] for i in range(n)))


def _poly_shift_back_q(g: tuple) -> tuple:
    """g(n−1) as a rational polynomial, by exact binomial expansion of (n−1)^k."""
    gg = [Fraction(c) for c in g]
    res = [Fraction(0)] * len(gg)
    for k, a in enumerate(gg):
        if a == 0:
            continue
        for j in range(k + 1):
            res[j] += a * comb(k, j) * ((-1) ** (k - j))
    return _norm_q(tuple(res))


def _poly_eval_q(poly: tuple, n: int) -> Fraction:
    acc = Fraction(0)
    for c in reversed(poly):
        acc = acc * n + Fraction(c)
    return acc


def _coeff_str(c) -> str:
    c = Fraction(c)
    return str(c.numerator) if c.denominator == 1 else f"{c.numerator}/{c.denominator}"


# --- the guarded theorem type (LCF-style) -----------------------------------------------------

class Theorem:
    """A kernel theorem, one of two judgment kinds:
      • Divides:     payload (modulus, poly)  — "∀n∈ℤ, modulus | poly(n)"
      • SumIdentity: payload (f_poly, g_poly) — "∀n≥1, Σ_{i=1}^n f(i) = g(n)"
    Cannot be constructed directly — only the kernel's rules mint one (LCF guard)."""
    __slots__ = ("kind", "payload")

    def __init__(self, *args, **kwargs):
        raise PermissionError(
            "Theorems are created only by the kernel's inference rules (check/residue/crt/sum), "
            "never constructed directly")

    # backward-compatible accessors for the Divides fragment
    @property
    def modulus(self) -> int:
        if self.kind != "Divides":
            raise AttributeError("modulus is defined only for Divides theorems")
        return self.payload[0]

    @property
    def poly(self) -> Poly:
        if self.kind != "Divides":
            raise AttributeError("poly is defined only for Divides theorems")
        return self.payload[1]

    def __repr__(self) -> str:
        if self.kind == "Divides":
            m, p = self.payload
            return f"⊢ Divides({m}, {_poly_str(p)})"
        if self.kind == "SumIdentity":
            f, g = self.payload
            return f"⊢ SumIdentity(Σ_(i=1..n) {_poly_str(f)} = {_poly_str(g)})"
        if self.kind == "PolyIdentity":
            p, q = self.payload
            return f"⊢ PolyIdentity({_poly_str(p)} = {_poly_str(q)})"
        return f"⊢ {self.kind}{self.payload}"

    def __eq__(self, other) -> bool:
        return (isinstance(other, Theorem)
                and self.kind == other.kind and self.payload == other.payload)

    def __hash__(self) -> int:
        return hash((Theorem, self.kind, self.payload))


def _mint(kind: str, payload: tuple) -> Theorem:
    """Module-private theorem constructor. Every mint is preceded by a rule's verification."""
    t = object.__new__(Theorem)
    object.__setattr__(t, "kind", kind)
    object.__setattr__(t, "payload", payload)
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


@dataclass(frozen=True)
class SumInduction:
    """Leaf proof term for a SUM identity: assert Σ_{i=1}^n f(i) = g(n) by base case + telescoping
    step. SOUND & COMPLETE for polynomial sums: g(1)=f(1) and the polynomial g(n)−g(n−1)−f(n) ≡ 0
    ⟹ (by induction on n) the identity holds for every n ≥ 1."""
    f_poly: Poly            # f(i), rational coefficients allowed
    g_poly: Poly            # g(n), the claimed closed form


@dataclass(frozen=True)
class Identity:
    """Leaf proof term for a polynomial IDENTITY p(n) = q(n) (∀n). SOUND & COMPLETE: p ≡ q iff the
    polynomial p − q is identically zero (all coefficients zero). Used to independently CERTIFY a
    factorization (p in expanded form, q in factored form) without trusting the factoring routine."""
    lhs: Poly
    rhs: Poly


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
        return _mint("Divides", (m, p))

    if isinstance(term, CRT):
        if not term.parts:
            raise KernelError("CRT: needs at least one premise")
        thms = [check(t) for t in term.parts]          # recursively verify every premise
        if any(th.kind != "Divides" for th in thms):
            raise KernelError("CRT: premises must be Divides theorems")
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
        return _mint("Divides", (prod(mods), p0))

    if isinstance(term, SumInduction):
        f = _norm_q(term.f_poly)
        g = _norm_q(term.g_poly)
        if _poly_eval_q(g, 1) != _poly_eval_q(f, 1):
            raise KernelError(
                f"SUM base case fails: g(1)={_poly_eval_q(g, 1)} ≠ f(1)={_poly_eval_q(f, 1)}")
        step = _poly_sub_q(_poly_sub_q(g, _poly_shift_back_q(g)), f)   # g(n) − g(n−1) − f(n)
        if step != (Fraction(0),):
            raise KernelError(
                f"SUM step fails: g(n)−g(n−1)−f(n) = {_poly_str(step)} ≢ 0")
        return _mint("SumIdentity", (f, g))

    if isinstance(term, Identity):
        p = _norm_q(term.lhs)
        q = _norm_q(term.rhs)
        if _poly_sub_q(p, q) != (Fraction(0),):
            raise KernelError(f"IDENTITY fails: {_poly_str(p)} ≠ {_poly_str(q)}")
        return _mint("PolyIdentity", (p, q))

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


def prove_sum_identity(f_poly: Poly, g_poly: Poly):
    """Build a SumInduction term for Σf(i)=g(n) and KERNEL-CHECK it. Returns (Theorem, proof_term);
    raises KernelError if the base case or the telescoping step fails."""
    term = SumInduction(f_poly, g_poly)
    return check(term), term


def prove_identity(lhs: Poly, rhs: Poly):
    """Build an Identity term for p(n)=q(n) and KERNEL-CHECK it. Returns (Theorem, proof_term);
    raises KernelError if p − q ≢ 0."""
    term = Identity(lhs, rhs)
    return check(term), term


# --- optional sympy bridge (NOT part of the stdlib-only trusted core) --------------------------

def poly_from_sympy(expr: str, var: str = "n") -> Poly:
    """Convert a polynomial expression string (e.g. "n**3 - n", "n*(n+1)*(n+2)") to the kernel's
    exact integer coefficient tuple (low→high). Raises KernelError on a non-integer-polynomial.
    This is a convenience bridge for the arithmetic pipeline — the kernel core stays sympy-free."""
    import sympy
    x = sympy.Symbol(var)
    poly = sympy.Poly(sympy.expand(sympy.sympify(expr)), x)
    coeffs_high_to_low = poly.all_coeffs()
    low_to_high = list(reversed(coeffs_high_to_low))
    return _norm(tuple(int(c) for c in low_to_high))


def poly_from_sympy_q(expr: str, var: str = "n") -> tuple:
    """Like `poly_from_sympy` but keeps RATIONAL coefficients (Fraction) — for sum closed forms such
    as n*(n+1)/2. Low→high, exact."""
    import sympy
    x = sympy.Symbol(var)
    poly = sympy.Poly(sympy.expand(sympy.sympify(expr)), x)
    low_to_high = list(reversed(poly.all_coeffs()))
    return _norm_q(tuple(Fraction(int(c.p), int(c.q)) if hasattr(c, "p") else Fraction(c)
                         for c in low_to_high))
