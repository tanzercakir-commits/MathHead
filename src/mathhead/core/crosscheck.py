"""
mathhead.core.crosscheck — CROSS-CHECK (Z3 ⋈ SymPy), ROADMAP Track C3.

**The differentiating idea:** verify the same claim with TWO INDEPENDENT engines;
consensus is required.
- SymPy (CAS, symbolic) and Z3 (SMT, real decision) run independently of each other.
- If both say "equal" → **consensus** (confidence a single-engine rival cannot give).
- If they conflict → **DISAGREEMENT**: often exposes a subtle issue (e.g. domain /
  domain trap) and raises a flag for a human (an honest 'unknown').

Example (the difference-maker): `(x²-1)/(x-1)` vs `x+1` — SymPy says symbolically
"equal"; with real division semantics Z3 diverges at `x=1` → **disagreement** →
the domain trap is caught.

Note: the Z3 side only checks polynomial/rational real expressions; for expressions
like `sin/exp/log` Z3 says "unsupported" and we fall back to the single-engine
(SymPy) decision.
"""
from __future__ import annotations

import time
from typing import Any

import sympy
import z3

from mathhead.compute import ComputeError, _meta, _parse
from mathhead.core.inequality import _IneqError, _translate
from mathhead.core.verify import VerifyResult, _equal_verdict
from mathhead.guardrails import solver_config

__all__ = ["cross_check"]


def _sympy_equal(left: str, right: str) -> str:
    """SymPy side (DETERMINISTIC): 'equal' | 'not_equal' | 'undecided' | 'error'.

    Shared deterministic helper `verify._equal_verdict` (simplify + fixed
    sample-point counterexample; NONE of `.equals()`'s randomness) — the cross-check
    is deterministic too.
    """
    syms: dict[str, Any] = {}
    try:
        le = _parse(left, syms)
        re = _parse(right, syms)
        if isinstance(le, sympy.Equality) or isinstance(re, sympy.Equality):
            return "error"
    except ComputeError:
        return "error"
    return _equal_verdict(le, re, syms)[0]


def _z3_equal(left: str, right: str) -> tuple[str, dict | None]:
    """Z3 side: ('equal'|'not_equal'|'undecided'|'unsupported', counterexample?)."""
    rvars: dict[str, Any] = {}
    try:
        lz = _translate(left, rvars)
        rz = _translate(right, rvars)
    except (_IneqError, SyntaxError, ValueError):
        return "unsupported", None
    if z3.is_bool(lz) or z3.is_bool(rz):     # not a comparison, an expression is expected
        return "unsupported", None
    solver = solver_config(5_000, 42)
    solver.add(z3.Not(lz == rz))
    res = solver.check()
    if res == z3.unsat:
        return "equal", None
    if res == z3.sat:
        model = solver.model()
        cx = {}
        for name, const in rvars.items():
            val = model.eval(const, model_completion=True)
            cx[name] = str(val)
        return "not_equal", cx
    return "undecided", None


def cross_check(left: str, right: str) -> VerifyResult:
    """INDEPENDENTLY verifies the claim `left` = `right` with Z3 and SymPy; seeks
    consensus.

    valid → both engines say 'equal' (CONSENSUS_EQUAL) or a single engine confirmed
    it (SINGLE_ENGINE). invalid → both engines say 'not equal'. unknown →
    **ENGINES_DISAGREE** (the engines conflict; subtle-issue/domain flag) or both are
    undecided (CROSS_UNDECIDED).
    """
    t0 = time.perf_counter()
    sym = _sympy_equal(left, right)
    if sym == "error":
        return VerifyResult("error", "PARSE_ERROR",
                            "cross_check: could not parse expression (or an equation was given).",
                            None, _meta(t0))
    z3v, cx = _z3_equal(left, right)
    details = {"sympy": sym, "z3": z3v}
    if cx:
        details["z3_counterexample"] = cx

    decisive = {"equal", "not_equal"}
    # both engines are decisive
    if sym in decisive and z3v in decisive:
        if sym == z3v:
            if sym == "equal":
                return VerifyResult("valid", "CONSENSUS_EQUAL",
                                    "two independent engines (Z3 + SymPy) say EQUAL (consensus).",
                                    details, _meta(t0))
            return VerifyResult("invalid", "CONSENSUS_NOT_EQUAL",
                                f"both engines say NOT EQUAL (consensus); counterexample: {cx}.",
                                details, _meta(t0))
        # conflict — subtle-issue flag (usually domain)
        return VerifyResult(
            "unknown", "ENGINES_DISAGREE",
            f"ENGINES CONFLICT — SymPy: {sym}, Z3: {z3v}. Usually a subtle issue "
            f"(domain, division, root branch). Human eyes needed. "
            f"Z3 counterexample: {cx}.",
            details, _meta(t0))
    # only one engine could decide
    if sym in decisive:
        status = "valid" if sym == "equal" else "invalid"
        return VerifyResult(status, "SINGLE_ENGINE",
                            f"only SymPy decided: {sym} (Z3: {z3v}). Single-engine, "
                            f"no cross-verification (lower confidence).", details, _meta(t0))
    if z3v in decisive:
        status = "valid" if z3v == "equal" else "invalid"
        return VerifyResult(status, "SINGLE_ENGINE",
                            f"only Z3 decided: {z3v} (SymPy: {sym}). Single-engine, "
                            f"no cross-verification (lower confidence).", details, _meta(t0))
    return VerifyResult("unknown", "CROSS_UNDECIDED",
                        f"no engine could decide (SymPy: {sym}, Z3: {z3v}).",
                        details, _meta(t0))
