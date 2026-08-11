"""
mathhead.drat — Verifiable UNSAT certificates (ROADMAP J2).

This compatibility module keeps the original J2 producer and result shapes. The
authoritative SAT/UNSAT replay boundary is now ``mathhead.kernel.sat`` under
``MH-C-SAT-REPLAY-001``; this module normalizes legacy collections into its exact
versioned bytes and translates the result without minting authority itself.

Two halves, both stdlib-only (this module imports NEITHER z3 NOR sympy — proven by a
subprocess test, the same "don't trust us, run the checker" guarantee as
`certificate.py`):

  * `rup_check(clauses, proof)` — a compatibility adapter to the dependency-minimal,
    content-addressed kernel checker.
  * `refute(clauses)` — a self-contained PRODUCER. A DPLL search that, on UNSAT,
    emits a resolution refutation as a DRUP proof (each resolvent is RUP by
    construction). No external SAT binary is required.

The tools (`prove_unsat`, `check_unsat_proof`) glue them: `prove_unsat` produces a
proof AND re-checks it with the independent checker before returning
(`verified: true`). Small-instance scope (CNF over a bounded number of variables); a
node budget keeps it terminating — exceeding it is an honest `unknown`, never a fake
certificate.

CNF format: a list of clauses; each clause is a list of nonzero ints (DIMACS
literals — `3` = variable 3 true, `-3` = false). `[]` (the empty clause) is an
immediate contradiction.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from mathhead.kernel.sat import (
    SATReplayResult,
    canonical_cnf_bytes,
    canonical_drup_bytes,
    check_sat_certificate,
)

_MAX_VARS_PROVE = 20        # 2^n worst case; the node budget is the real fence
_MAX_CLAUSES = 2_000
_MAX_NODES = 300_000
_MAX_PROOF = 200_000        # checker: cap the proof length we will validate


@dataclass
class DratResult:
    status: str                              # unsat | sat | verified | refuted | unknown | error
    reason_code: str
    explanation: str
    verified: bool | None = None             # UNSAT independently re-checked / proof valid
    proof: list[list[int]] | None = None     # the DRUP proof (list of lemma clauses)
    proof_length: int | None = None
    witness: dict[str, Any] | None = None     # a satisfying assignment (SAT case)
    meta: dict[str, Any] = field(default_factory=dict)


def _meta(t0: float, extra: dict | None = None) -> dict[str, Any]:
    m = {"engine": "drup-rup", "independent": True,
         "elapsed_ms": round((time.perf_counter() - t0) * 1000, 3)}
    if extra:
        m.update(extra)
    return m


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #
def _validate(clauses: Any) -> tuple[list[list[int]], set[int]]:
    if not isinstance(clauses, list) or not clauses:
        raise ValueError("clauses must be a non-empty list of clauses")
    if len(clauses) > _MAX_CLAUSES:
        raise ValueError(f"too many clauses (>{_MAX_CLAUSES})")
    out: list[list[int]] = []
    varset: set[int] = set()
    for cl in clauses:
        if not isinstance(cl, list) or any(not isinstance(x, int) or isinstance(x, bool) or x == 0 for x in cl):
            raise ValueError("each clause must be a list of nonzero integers (DIMACS literals)")
        out.append(list(cl))
        varset.update(abs(x) for x in cl)
    return out, varset


# --------------------------------------------------------------------------- #
# Compatibility adapter to the one authoritative SAT replay boundary
# --------------------------------------------------------------------------- #
def _replay_unsat(clauses: list[list[int]], proof: list[list[int]]) -> SATReplayResult:
    cnf = canonical_cnf_bytes(clauses)
    certificate = canonical_drup_bytes(cnf, [("a", clause) for clause in proof])
    return check_sat_certificate(cnf, certificate)


def rup_check(clauses: list[list[int]], proof: list[list[int]]) -> tuple[bool, str]:
    """Compatibility shape for the versioned ``mathhead.kernel.sat`` checker."""
    try:
        result = _replay_unsat(clauses, proof)
    except (TypeError, ValueError) as exc:
        return False, f"invalid legacy DRUP input: {exc}"
    return result.ok, result.diagnostic


# --------------------------------------------------------------------------- #
# DRUP producer (self-contained DPLL → resolution refutation)
# --------------------------------------------------------------------------- #
def refute(clauses: list[list[int]]) -> tuple[str, Any]:
    """DPLL refutation. Returns ('unsat', drup_proof) | ('sat', model) | ('unknown', None).

    On UNSAT the proof is a resolution refutation emitted as a DRUP proof (each
    resolvent is RUP by construction), ending with the empty clause.
    """
    formula = [frozenset(c) for c in clauses]
    proof: list[frozenset] = []
    nodes = [0]

    def solve(decisions: list[int]):
        nodes[0] += 1
        if nodes[0] > _MAX_NODES:
            raise TimeoutError
        assign: dict[int, bool] = {}
        reason: dict[int, frozenset | None] = {}

        def setl(lit: int, rcl):
            assign[abs(lit)] = lit > 0
            reason[abs(lit)] = rcl

        conflict = None
        for d in decisions:
            if abs(d) in assign and assign[abs(d)] != (d > 0):
                conflict = frozenset()          # contradictory decisions (defensive)
            else:
                setl(d, None)
        changed = True
        while changed and conflict is None:
            changed = False
            for cl in formula:
                unassigned: list[int] = []
                satisfied = False
                for lit in cl:
                    v = abs(lit)
                    if v in assign:
                        if assign[v] == (lit > 0):
                            satisfied = True
                            break
                    else:
                        unassigned.append(lit)
                if satisfied:
                    continue
                if not unassigned:
                    conflict = cl
                    break
                if len(unassigned) == 1:
                    setl(unassigned[0], cl)
                    changed = True
        if conflict is not None:
            # resolve the conflict clause against the reasons of propagated literals
            clause = frozenset(conflict)
            while True:
                propagated = [lit for lit in clause if reason.get(abs(lit)) is not None]
                if not propagated:
                    break
                lit = propagated[0]
                v = abs(lit)
                rcl = reason[v]
                clause = frozenset(x for x in clause if abs(x) != v) | \
                    frozenset(x for x in rcl if abs(x) != v)
                proof.append(clause)            # each resolvent is a RUP lemma
            return ("clause", clause)           # a clause falsified by `decisions`

        variables = {abs(lit) for cl in formula for lit in cl}
        unassigned_vars = [v for v in sorted(variables) if v not in assign]
        if not unassigned_vars:
            return ("sat", dict(assign))
        x = unassigned_vars[0]

        r1 = solve([*decisions, x])
        if r1[0] == "sat":
            return r1
        c1 = r1[1]
        if x not in c1 and -x not in c1:        # already falsified without x
            return ("clause", c1)

        r2 = solve([*decisions, -x])
        if r2[0] == "sat":
            return r2
        c2 = r2[1]
        if x not in c2 and -x not in c2:
            return ("clause", c2)

        resolvent = frozenset(lit for lit in c1 if abs(lit) != x) | \
            frozenset(lit for lit in c2 if abs(lit) != x)
        proof.append(resolvent)
        return ("clause", resolvent)

    try:
        status, data = solve([])
    except TimeoutError:
        return ("unknown", None)
    if status == "sat":
        return ("sat", data)
    ordered = [sorted(lemma, key=lambda t: (abs(t), t)) for lemma in proof]
    return ("unsat", ordered)


# --------------------------------------------------------------------------- #
# Tools
# --------------------------------------------------------------------------- #
def prove_unsat(clauses: list[list[int]]) -> DratResult:
    """Decide a CNF and, when UNSAT, return an INDEPENDENTLY-VERIFIED DRUP certificate.

    On `unsat` the produced DRUP proof is re-checked by the independent RUP checker
    before returning (`verified: true`) — the Phase-10 wall closed with no external SAT
    binary. `sat` → a satisfying assignment (no UNSAT certificate exists, reported
    honestly). `unknown` → the search exceeded its node budget.
    """
    t0 = time.perf_counter()
    try:
        cnf, varset = _validate(clauses)
    except ValueError as exc:
        return DratResult("error", "GUARDRAIL_VIOLATION", str(exc), meta=_meta(t0))
    if len(varset) > _MAX_VARS_PROVE:
        return DratResult("error", "GUARDRAIL_VIOLATION",
                          f"prove_unsat is bounded to {_MAX_VARS_PROVE} distinct variables "
                          f"(got {len(varset)}); use check_unsat_proof for larger proofs",
                          meta=_meta(t0))

    status, data = refute(cnf)
    extra = {"variables": len(varset), "clauses": len(cnf)}
    if status == "unknown":
        return DratResult("unknown", "BUDGET_EXCEEDED",
                          "The DPLL search exceeded its node budget; no certificate produced "
                          "(honest — the verdict is not fabricated).", meta=_meta(t0, extra))
    if status == "sat":
        model = {str(v): data.get(v, False) for v in sorted(varset)}
        return DratResult("sat", "SATISFIABLE",
                          "The CNF is satisfiable, so there is no UNSAT certificate.",
                          verified=None, witness=model, meta=_meta(t0, extra))
    # UNSAT — independently re-check the proof we just produced.
    ok, msg = rup_check(cnf, data)
    if not ok:
        return DratResult("error", "INTERNAL_INCONSISTENCY",
                          f"produced proof failed independent verification: {msg}", meta=_meta(t0, extra))
    return DratResult("unsat", "UNSAT_CERTIFIED",
                      f"UNSAT with an independently-verified DRUP certificate "
                      f"({len(data)} lemmas, checked by reverse unit propagation).",
                      verified=True, proof=data, proof_length=len(data),
                      meta=_meta(t0, {**extra, "verified": True}))


def check_unsat_proof(clauses: list[list[int]], proof: list[list[int]]) -> DratResult:
    """Independently verify a DRUP `proof` that `clauses` is UNSAT (bring-your-own proof
    from any solver). Pure-Python reverse-unit-propagation — no z3, no external binary.

    `verified` → the proof soundly derives the empty clause; `refuted` → it does not
    (a bad/incomplete proof is rejected, e.g. an empty proof for a non-trivial UNSAT).
    """
    t0 = time.perf_counter()
    try:
        cnf, _ = _validate(clauses)
    except ValueError as exc:
        return DratResult("error", "GUARDRAIL_VIOLATION", str(exc), meta=_meta(t0))
    if not isinstance(proof, list) or any(not isinstance(step, list) for step in proof):
        return DratResult("error", "GUARDRAIL_VIOLATION",
                          "proof must be a list of clauses (each a list of ints)", meta=_meta(t0))
    if len(proof) > _MAX_PROOF:
        return DratResult("error", "GUARDRAIL_VIOLATION", f"proof too long (>{_MAX_PROOF})", meta=_meta(t0))
    for step in proof:
        if any(not isinstance(x, int) or isinstance(x, bool) or x == 0 for x in step):
            return DratResult("error", "GUARDRAIL_VIOLATION",
                              "each proof step must be a list of nonzero integers", meta=_meta(t0))
    try:
        replay = _replay_unsat(cnf, proof)
    except (TypeError, ValueError) as exc:
        return DratResult("error", "GUARDRAIL_VIOLATION", str(exc), meta=_meta(t0))
    extra = {"proof_length": len(proof)}
    if replay.ok:
        return DratResult("verified", "PROOF_VERIFIED", replay.diagnostic, verified=True,
                          proof_length=len(proof), meta=_meta(t0, {**extra, "verified": True}))
    if replay.verdict == "exhausted":
        return DratResult("unknown", "BUDGET_EXCEEDED", replay.diagnostic, verified=None,
                          proof_length=len(proof), meta=_meta(t0, extra))
    if replay.verdict in {"invalid", "unsupported"}:
        return DratResult("error", "GUARDRAIL_VIOLATION", replay.diagnostic, verified=None,
                          proof_length=len(proof), meta=_meta(t0, extra))
    return DratResult("refuted", "PROOF_REFUTED", replay.diagnostic, verified=False,
                      proof_length=len(proof), meta=_meta(t0, extra))
