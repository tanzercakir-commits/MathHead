"""v4F0 — UNSAT verdicts rest on independently RUP-checked DRUP proofs, not the solver's word.

The heavy anchors (R(3,4)<=9 base and strengthened) are asserted where they already run:
tests/test_discovery_ramsey_sat.py. This file covers the checker itself — including the
negative paths: a tampered proof, a proof for the wrong formula, and an exhausted budget
must NEVER yield the upgraded tier.
"""
import pytest

from mathhead.discovery.ramsey_sat import ramsey_cnf, ramsey_decide
from mathhead.discovery.rup_check import (
    RupCheckResult,
    check_drup_lines,
    check_drup_proof,
    parse_drup,
)

pytest.importorskip("pysat.solvers", reason="pysat not installed")


def _glucose_proof(n: int, s: int, t: int):
    """The real solver-emitted DRUP proof for an UNSAT Ramsey instance."""
    from pysat.solvers import Glucose3
    _, clauses = ramsey_cnf(n, s, t)
    with Glucose3(bootstrap_with=clauses, with_proof=True) as solver:
        assert not solver.solve()
        return clauses, solver.get_proof()


# --------------------------------------------------------------------------- #
# The verdict carries the new tier
# --------------------------------------------------------------------------- #
def test_r33_unsat_carries_independently_checked_rup_proof():
    v = ramsey_decide(6, 3, 3)                              # R(3,3) <= 6, the classic
    assert not v.satisfiable
    assert v.certainty == "independently_verified_unsat_proof"
    assert v.unsat_proof_checked and v.unsat_proof_lemmas > 0
    assert "RUP" in v.unsat_proof_note and "base encoding" in v.unsat_proof_note


def test_certify_opt_out_is_backward_compatible():
    v = ramsey_decide(6, 3, 3, certify_unsat=False)
    assert not v.satisfiable and v.certainty == "solver_verified"
    assert not v.unsat_proof_checked and v.unsat_proof_lemmas == 0
    assert "not requested" in v.unsat_proof_note


def test_sat_path_is_unchanged():
    v = ramsey_decide(5, 3, 3)
    assert v.satisfiable and v.certainty == "independently_verified_witness"
    assert v.red_edges and not v.unsat_proof_checked and v.unsat_proof_note == ""


def test_failed_check_falls_back_honestly_never_upgrading(monkeypatch):
    import mathhead.discovery.rup_check as rc
    monkeypatch.setattr(rc, "check_drup_lines",
                        lambda clauses, lines, **kw: RupCheckResult(
                            "budget_exceeded", "simulated exhausted budget"))
    v = ramsey_decide(6, 3, 3)
    assert not v.satisfiable and v.certainty == "solver_verified"    # NEVER the upgraded tier
    assert not v.unsat_proof_checked
    assert "budget_exceeded" in v.unsat_proof_note


# --------------------------------------------------------------------------- #
# The checker verifies real proofs — and rejects fake ones
# --------------------------------------------------------------------------- #
def test_real_glucose_proof_verifies_and_deletions_are_parsed():
    clauses, proof = _glucose_proof(6, 3, 3)
    assert any(line.startswith("d ") for line in proof)      # solver proofs interleave deletions
    res = check_drup_lines(clauses, proof)
    assert res.ok and res.status == "verified" and res.lemmas_checked > 0


def test_tampered_proof_is_rejected():
    clauses, proof = _glucose_proof(6, 3, 3)
    # inject a lemma that is NOT a consequence: a bare unit clause out of nowhere
    forged = ["1 0", *proof]
    res = check_drup_lines(clauses, forged)
    assert res.status == "refuted" and not res.ok and "not RUP" in res.message


def test_truncated_proof_is_rejected():
    clauses, proof = _glucose_proof(6, 3, 3)
    adds = [ln for ln in proof if not ln.startswith("d ")]
    res = check_drup_lines(clauses, adds[:2])                # cut before the empty clause
    assert res.status == "refuted" and "empty clause" in res.message
    assert check_drup_lines(clauses, []).status == "refuted"  # the empty proof proves nothing


def test_proof_for_the_wrong_formula_is_rejected():
    _, proof = _glucose_proof(6, 3, 3)
    _, sat_clauses = ramsey_cnf(5, 3, 3)                     # SATISFIABLE — no refutation exists
    assert not check_drup_lines(sat_clauses, proof).ok


def test_exhausted_budget_is_neither_verified_nor_refuted():
    clauses, proof = _glucose_proof(6, 3, 3)
    res = check_drup_lines(clauses, proof, visit_budget=1)
    assert res.status == "budget_exceeded" and not res.ok


# --------------------------------------------------------------------------- #
# Checker semantics on hand-built proofs
# --------------------------------------------------------------------------- #
def test_hand_built_proof_with_deletion_verifies():
    clauses = [[1, 2], [1, -2], [-1, 2], [-1, -2]]
    res = check_drup_lines(clauses, ["1 0", "d 1 2 0", "-1 0", "0"])
    assert res.ok and res.deletions_applied == 1


def test_input_unit_clauses_propagate():
    res = check_drup_proof([[1], [-1, 2], [-2]], [("a", ())])
    assert res.ok                                            # units alone already conflict


def test_parse_drup_rejects_garbage():
    with pytest.raises(ValueError):
        parse_drup(["1 x 0"])
    assert check_drup_lines([[1], [-1]], ["1 y 0"]).status == "error"
    assert parse_drup(["c comment", "", "d 1 2 0", "-3 0", "0"]) == [
        ("d", (1, 2)), ("a", (-3,)), ("a", ())]


def test_malformed_input_is_an_error_result_never_a_crash():
    assert check_drup_lines([[1], [-1]], None).status == "error"
    assert check_drup_lines(None, ["0"]).status == "error"
    assert check_drup_lines([[1], [-1]], "1 0").status == "error"     # a str is not a line list
    assert check_drup_lines([[1], [-1]], [42]).status == "error"      # non-string entries
    assert check_drup_proof(None, []).status == "error"
    assert check_drup_proof([[1], [-1]], None).status == "error"


def test_proof_truncated_just_before_the_empty_clause_still_verifies():
    """The final-formula conflict rule: F ∪ RUP-lemmas propagating to a conflict proves F
    UNSAT (each lemma is entailed by F) — a proof missing only the trailing ⊥ verifies."""
    res = check_drup_lines([[1, 2], [1, -2], [-1, 2], [-1, -2]], ["1 0", "-1 0"])
    assert res.ok and "final formula" in res.message
    clauses, proof = _glucose_proof(6, 3, 3)                 # the real thing, ⊥ line dropped
    assert proof[-1].strip() == "0"
    res = check_drup_lines(clauses, proof[:-1])
    assert res.ok and "final formula" in res.message


def test_differential_agreement_with_the_j2_checker_on_random_cnfs():
    """The fast watched-literal checker and the naive J2 checker must agree — on valid DPLL
    refutations AND on tampered ones (deterministic differential fuzz)."""
    import random

    from mathhead.drat import refute, rup_check as j2_rup_check
    rng = random.Random(7)
    tested = 0
    while tested < 25:
        nv, nc = rng.randint(3, 7), rng.randint(5, 25)
        cnf = [[rng.choice([1, -1]) * rng.randint(1, nv) for _ in range(3)] for _ in range(nc)]
        status, proof = refute(cnf)
        if status != "unsat":
            continue
        tested += 1
        variants = [proof]
        if len(proof) > 1:
            variants.append(proof[:-1] + [[rng.choice([1, -1]) * rng.randint(1, nv)]])
            variants.append(proof[1:])
        for candidate in variants:
            fast = check_drup_proof(cnf, [("a", tuple(cl)) for cl in candidate])
            naive_ok, _ = j2_rup_check(cnf, candidate)
            assert fast.ok == naive_ok, (cnf, candidate, fast.status)


def test_cross_checked_by_the_j2_drat_checker():
    """The v4F0 checker and the J2 `mathhead.drat` checker agree on a real solver proof
    (deletions filtered for the J2 checker, which predates them — sound, since ignoring
    deletions only adds clauses and clauses only help propagation)."""
    from mathhead.drat import rup_check as j2_rup_check
    clauses, proof = _glucose_proof(6, 3, 3)
    adds = [step for op, step in parse_drup(proof) if op == "a"]
    ok, msg = j2_rup_check(clauses, [list(step) for step in adds])
    assert ok, msg
