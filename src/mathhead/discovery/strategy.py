"""
mathhead.discovery.strategy — a proof-strategy orchestrator for modular claims (roadmap S).

A single induction often can't prove `p(n) ≡ 0 (mod m)` for composite m (Z3's inductive step is
too hard). But by the CRT, m = ∏ pᵢ^{eᵢ} with the parts pairwise coprime, so if MathHead proves
`p(n) ≡ 0 (mod pᵢ^{eᵢ})` for EVERY prime power, the composite claim follows. This strategy factors
the modulus (via MathHead's `factorize`) and proves each part by induction, then combines the
coprime successes.

Honest: it upgrades what one induction can't reach (e.g. n³−n ≡ 0 mod 6 = 2·3 — each part proved,
CRT gives mod 6), and when a prime part is itself beyond induction (e.g. the mod-3 step of n⁵−n)
it returns `unknown` and names WHICH part blocked — never a fabricated proof.
"""
from __future__ import annotations

from mathhead.router import route

from .judge import Verdict, judge_induction


def factor_prime_powers(m: int) -> list:
    """Prime-power factorization [p^e, …] of m, via MathHead's `factorize` tool."""
    r = route("factorize", {"n": str(m)})
    return [int(f["prime"]) ** int(f["exponent"]) for f in (getattr(r, "result", None) or [])]


def prove_modular_divisibility(expr: str, m: int, var: str = "n", start: int = 0,
                               timeout_ms: int = 1500) -> Verdict:
    """Prove `expr ≡ 0 (mod m)` by factoring m and proving each prime-power part by induction,
    combining coprime successes (CRT)."""
    parts = factor_prime_powers(m)
    if not parts:
        return Verdict("unknown", "unknown", "NO_FACTORS", {"modulus": m})
    results = {pp: judge_induction(f"({expr}) % {pp} == 0", var, start, timeout_ms) for pp in parts}
    blocked = [pp for pp, v in results.items() if v.status != "proved"]
    if not blocked:
        return Verdict("proved", "formal_proof", "PROVED_BY_CRT_FACTORING",
                       {"modulus": m, "prime_powers": parts, "method": "modulus-factoring+CRT"})
    return Verdict("unknown", "unknown", "PART_UNPROVEN",
                   {"modulus": m, "prime_powers": parts, "blocked_parts": blocked,
                    "method": "modulus-factoring+CRT"})
