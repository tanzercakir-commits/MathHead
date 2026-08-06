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


# --------------------------------------------------------------------------- #
# The BACKWARD checker (drat-trim's marking idea): forward agreement, marking
# savings, honest DRAT semantics, deletion reversal, budget, error paths
# --------------------------------------------------------------------------- #
def test_backward_agrees_with_forward_on_real_proofs():
    from mathhead.discovery.rup_check import check_drup_backward
    for n, s, t in ((6, 3, 3), (9, 3, 4)):
        clauses, proof = _glucose_proof(n, s, t)
        fwd = check_drup_lines(clauses, proof)
        bwd = check_drup_backward(clauses, proof)
        assert fwd.ok and bwd.ok, (n, s, t, fwd.status, bwd.status)
        assert bwd.checked_lemmas <= bwd.total_lemmas and bwd.total_lemmas > 0
        assert "backward" in bwd.message and bwd.visits > 0


def test_backward_checks_only_the_derivation_cone():
    """Marking skips lemmas outside ⊥'s cone — the entire speed-up. The flip side is honest
    drat-trim semantics: a junk lemma the derivation never uses does not undermine `verified`
    (the claim is exactly '⊥ follows from the input by the RUP chain over MARKED clauses'),
    while the forward checker, which checks EVERY lemma, refutes the same proof."""
    from mathhead.discovery.rup_check import check_drup_backward
    clauses = [[1, 2], [1, -2], [-1, 2], [-1, -2], [5, 6]]
    proof = ["5 7 0", "1 0", "-1 0", "0"]                    # "5 7" is junk: NOT RUP, never used
    fwd = check_drup_lines(clauses, proof)
    bwd = check_drup_backward(clauses, proof)
    assert fwd.status == "refuted"                           # forward checks every lemma
    assert bwd.status == "verified"                          # backward: ⊥'s cone is {1, -1}
    assert bwd.checked_lemmas < bwd.total_lemmas == 4        # the junk lemma was never checked
    # and on a REAL proof the cone is measurably smaller than the whole (the savings claim)
    from mathhead.discovery.ramsey_sat import _degree_lemmas
    from pysat.solvers import Glucose3
    ev, clauses44 = ramsey_cnf(18, 4, 4)
    extra, _lemmas, _top = _degree_lemmas(18, 4, 4, ev, max(ev.values()))
    clauses44 = clauses44 + extra
    with Glucose3(bootstrap_with=clauses44, with_proof=True) as solver:
        assert not solver.solve()
        proof44 = solver.get_proof()
    res = check_drup_backward(clauses44, proof44)
    assert res.ok and 0 < res.checked_lemmas < res.total_lemmas


def test_backward_tampered_cone_is_still_rejected():
    """Tampering INSIDE the derivation cone must refute — marking never excuses the root."""
    from mathhead.discovery.rup_check import check_drup_backward
    clauses, proof = _glucose_proof(6, 3, 3)
    forged = ["1 0", *proof]                                 # a unit out of nowhere, then the rest
    assert check_drup_backward(clauses, forged).status == "refuted"
    adds = [ln for ln in proof if not ln.startswith("d ")]
    assert check_drup_backward(clauses, adds[:2]).status == "refuted"   # no ⊥, no final conflict
    assert check_drup_backward(clauses, []).status == "refuted"
    _, sat_clauses = ramsey_cnf(5, 3, 3)                     # SATISFIABLE: no refutation exists
    assert check_drup_backward(sat_clauses, proof).status == "refuted"


def test_backward_drat_mode_reports_not_rup_checkable_never_refuted():
    """A marked lemma failing RUP under proof_format='drat' may be a genuine RAT step — the
    RUP-only checker reports `not_rup_checkable` (honestly undecided), NEVER `refuted`;
    the same input under 'drup' (documented RUP-only solver output) IS a refutation."""
    from mathhead.discovery.rup_check import check_drup_backward
    clauses = [[1, 2], [1, -2], [-1, 2], [-1, -2]]
    proof = ["3 0", "-3 0", "0"]                             # "3" is in ⊥'s cone but not RUP
    drat = check_drup_backward(clauses, proof, proof_format="drat")
    assert drat.status == "not_rup_checkable" and not drat.ok
    assert "RAT" in drat.message and "UNDECIDED" in drat.message
    drup = check_drup_backward(clauses, proof, proof_format="drup")
    assert drup.status == "refuted" and "not RUP" in drup.message


def test_backward_is_deletion_blind_by_design():
    """`d` lines are parsed and counted but deliberately NOT applied — sound for RUP (ignoring
    a deletion only ADDS clauses, and unit propagation is monotone in the clause set), and
    measured necessary at scale: solver deletion info is over-eager (54% of checks on a
    1.7M-lemma Glucose42 proof needed the deleted clauses back). An over-eager deletion of a
    clause a later lemma still needs therefore costs nothing here."""
    from mathhead.discovery.rup_check import check_drup_backward
    clauses = [[1, 2], [1, -2], [-1, 2], [-1, -2]]
    res = check_drup_backward(clauses, ["1 0", "d 1 2 0", "-1 0", "0"])
    assert res.ok and res.deletions_applied == 1             # recognized, skipped, counted
    # over-eager: [-1, 2] deleted though the lemma "-1" still needs it — blind mode is immune
    res = check_drup_backward(clauses, ["1 0", "d -1 2 0", "-1 0", "0"])
    assert res.ok and res.deletions_applied == 1
    assert "deletion-blind" in res.message


def test_backward_budget_and_error_paths():
    from mathhead.discovery.rup_check import check_drup_backward
    clauses, proof = _glucose_proof(6, 3, 3)
    res = check_drup_backward(clauses, proof, visit_budget=1)
    assert res.status == "budget_exceeded" and not res.ok and "no verdict" in res.message
    assert check_drup_backward(clauses, None).status == "error"
    assert check_drup_backward(None, proof).status == "error"
    assert check_drup_backward(clauses, "1 0").status == "error"      # a str is not a line list
    assert check_drup_backward(clauses, [42]).status == "error"
    assert check_drup_backward(clauses, ["1 y 0"]).status == "error"
    assert check_drup_backward(clauses, ["1 0 2"]).status == "error"  # interior zero
    assert check_drup_backward(clauses, proof, proof_format="lrat").status == "error"
    assert check_drup_backward([[1], [-1], []], ["0"]).status == "verified"   # empty input clause


def test_backward_accepts_a_lazily_read_proof_stream():
    """Multi-hundred-MB solver proofs are checked from disk, never held as a list — the
    backward checker takes any iterable of lines."""
    from mathhead.discovery.rup_check import check_drup_backward
    clauses, proof = _glucose_proof(6, 3, 3)
    res = check_drup_backward(clauses, (line for line in proof))
    assert res.ok


def test_backward_differential_against_forward_on_random_cnfs():
    """Deterministic differential fuzz: forward-verified ⟹ backward-verified (a proof whose
    EVERY lemma is RUP has every MARKED lemma RUP), and backward-refuted ⟹ forward-refuted.
    Tampered proofs may honestly diverge the other way (junk outside the cone)."""
    import random

    from mathhead.discovery.rup_check import check_drup_backward
    from mathhead.drat import refute
    rng = random.Random(11)
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
            lines = [" ".join(map(str, cl)) + " 0" for cl in candidate]
            fwd = check_drup_proof(cnf, [("a", tuple(cl)) for cl in candidate])
            bwd = check_drup_backward(cnf, lines)
            if fwd.ok:
                assert bwd.ok, (cnf, candidate, bwd.status)
            if bwd.status == "refuted":
                assert not fwd.ok, (cnf, candidate, fwd.status)
