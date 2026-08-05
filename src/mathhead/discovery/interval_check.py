"""
mathhead.discovery.interval_check — the interval-arithmetic verification path (v1 Q3 slice).

A SECOND rigorous route to the A–H verdicts, fully independent of the integer-Sylvester certificates:
mpmath's interval arithmetic (`mpmath.iv`, directed rounding) evaluates the CLOSED-FORM double-star
slack — λ₁(D(a,b)) = √((a+b+1+√((a+b+1)²−4ab))/2), slack = λ₁ + 2 − (√(n−1)+1) — as a certified
ENCLOSURE [lo, hi]. Then, honestly three-valued:

    hi < 0  ⟹  interval-certified VIOLATION      (the whole enclosure is negative)
    lo > 0  ⟹  interval-certified non-violation  (the whole enclosure is positive)
    else    ⟹  UNDECIDED — the enclosure straddles 0; no claim (exactly what happens at the
               D(12,12) equality, where the truth IS zero — the honest boundary answer)

Two independent rigorous methods (integer Sylvester vs interval enclosure) agreeing on every witness is
the engine's cross-check culture applied to its own newest certificates. The closed form used here is
itself validated against the graph-side power iteration in tests, so the formula and the matrix agree.
"""
from __future__ import annotations

from dataclasses import dataclass

from mpmath import iv


@dataclass
class IntervalVerdict:
    a: int
    b: int
    n: int
    lo: str                     # certified enclosure endpoints (decimal strings)
    hi: str
    verdict: str                # "violation_certified" | "no_violation_certified" | "undecided"


def double_star_slack_interval(a: int, b: int, dps: int = 40) -> IntervalVerdict:
    """Certified enclosure of slack(D(a,b)) = λ₁ + μ − (√(n−1)+1), μ=2, via interval arithmetic."""
    iv.dps = dps
    A, B = iv.mpf(a), iv.mpf(b)
    s = A + B + 1
    disc = s * s - 4 * A * B
    lam1 = iv.sqrt((s + iv.sqrt(disc)) / 2)
    n = a + b + 2
    slack = lam1 + 2 - (iv.sqrt(iv.mpf(n - 1)) + 1)
    lo, hi = slack.a, slack.b
    if hi < 0:
        verdict = "violation_certified"
    elif lo > 0:
        verdict = "no_violation_certified"
    else:
        verdict = "undecided"
    return IntervalVerdict(a, b, n, str(lo), str(hi), verdict)


def cross_check_certifiers(pairs) -> dict:
    """Run BOTH rigorous routes (interval enclosure vs integer Sylvester) on plain double stars and
    demand consistency: interval 'violation' ⟹ integer certificate EXISTS; interval 'no violation' ⟹
    integer certificate ABSENT. Any disagreement is returned loudly (it would mean a certifier bug)."""
    from .adaptive_search import double_star
    from .conjecture_db import AH_SPECTRAL_MATCHING as AH
    agree, disagree = [], []
    for a, b in pairs:
        ivd = double_star_slack_interval(a, b)
        cert = AH.certify(double_star(a, b))
        consistent = ((ivd.verdict == "violation_certified" and cert is not None)
                      or (ivd.verdict == "no_violation_certified" and cert is None)
                      or ivd.verdict == "undecided")
        (agree if consistent else disagree).append((a, b, ivd.verdict, cert is not None))
    return {"agree": agree, "disagree": disagree, "consistent": not disagree}
