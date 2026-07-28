"""
Verifiable UNSAT certificates (ROADMAP J2) — prove_unsat / check_unsat_proof.

Closes the Phase-10 wall: an UNSAT result becomes a DRUP proof re-checked by an
INDEPENDENT, pure-Python reverse-unit-propagation checker (no z3/sympy, no external
SAT binary). Round-trip (produce → independently verify), honest rejection of a
bad/incomplete proof, engine independence, and determinism.
"""
import subprocess
import sys
from itertools import combinations

from mathhead.drat import check_unsat_proof, prove_unsat
from mathhead.router import route


def _php(p):
    """Pigeonhole CNF: p+1 pigeons into p holes (UNSAT)."""
    pigeons, holes = p + 1, p

    def var(i, j):
        return i * holes + j + 1

    cls = [[var(i, j) for j in range(holes)] for i in range(pigeons)]
    for j in range(holes):
        for a, b in combinations(range(pigeons), 2):
            cls.append([-var(a, j), -var(b, j)])
    return cls


# ------------------------------ prove_unsat -------------------------------- #
def test_prove_unsat_simple():
    r = prove_unsat([[1], [-1]])
    assert r.status == "unsat" and r.reason_code == "UNSAT_CERTIFIED" and r.verified is True


def test_prove_unsat_pigeonhole_certified():
    r = prove_unsat(_php(3))
    assert r.status == "unsat" and r.verified is True
    assert r.proof_length >= 1


def test_prove_unsat_satisfiable_is_honest():
    r = prove_unsat([[1, 2], [-1, 3], [-3]])
    assert r.status == "sat" and r.verified is None and r.witness is not None


def test_produced_proof_passes_independent_check():
    # round-trip: the proof produced is verified by the INDEPENDENT checker
    r = prove_unsat(_php(2))
    assert r.status == "unsat"
    again = check_unsat_proof(_php(2), r.proof)
    assert again.status == "verified" and again.verified is True


# --------------------------- check_unsat_proof ----------------------------- #
def test_empty_proof_ok_when_directly_rup():
    # (x) ∧ (¬x): the empty clause is reached by pure unit propagation → empty proof verifies
    r = check_unsat_proof([[1], [-1]], [])
    assert r.status == "verified"


def test_incomplete_proof_is_refuted():
    # an empty proof cannot certify a non-trivial UNSAT (this is exactly why a naive
    # solver-emitted empty proof must be rejected, not trusted)
    r = check_unsat_proof(_php(3), [])
    assert r.status == "refuted" and r.verified is False


def test_bogus_proof_is_refuted():
    # a wrong first lemma on a non-trivially-UNSAT formula: [1] is not RUP from PHP(3)
    r = check_unsat_proof(_php(3), [[1]])
    assert r.status == "refuted" and r.verified is False


# ------------------------------ guardrails --------------------------------- #
def test_zero_literal_rejected():
    assert prove_unsat([[1, 0]]).status == "error"


def test_empty_clause_list_rejected():
    assert prove_unsat([]).status == "error"


def test_too_many_variables_rejected():
    big = [[i] for i in range(1, 25)]  # 24 distinct vars > prove_unsat bound
    r = prove_unsat(big)
    assert r.status == "error" and r.reason_code == "GUARDRAIL_VIOLATION"


# ----------------------- engine independence ------------------------------- #
def test_checker_is_engine_independent():
    # Importing mathhead.drat must NOT pull z3 or sympy into sys.modules —
    # "don't trust us, run the checker."
    code = (
        "import sys, mathhead.drat; "
        "bad=[m for m in ('z3', 'sympy') if m in sys.modules]; "
        "sys.exit(1 if bad else 0)"
    )
    proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert proc.returncode == 0, f"drat is not independent, loaded: {proc.stdout} {proc.stderr}"


# --------------------------- routing / determinism ------------------------- #
def test_router_wiring():
    assert route("prove_unsat", {"clauses": [[1], [-1]]}).status == "unsat"
    assert route("check_unsat_proof", {"clauses": [[1], [-1]], "proof": []}).status == "verified"


def test_determinism():
    a = prove_unsat(_php(3))
    b = prove_unsat(_php(3))
    assert a.status == b.status == "unsat"
    assert a.proof == b.proof  # the producer is deterministic
