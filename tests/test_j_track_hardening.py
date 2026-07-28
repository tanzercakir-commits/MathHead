"""
Track J hardening (ROADMAP J4) — the property tests ARE the guarantees.

Cross-cuts J1 reductions, J2 verifiable UNSAT certificates, J3 the high-performance
solver. No new tools. The strongest checks: prove_unsat's verdict matches brute-force
truth AND its DRUP proof round-trips through the independent checker; the stdlib DPLL
(J2) and CaDiCaL (J3) AGREE on random CNFs (two independent solvers); and every
reduction witness is re-verified orthogonally to the tool's own check.
"""
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from mathhead.drat import check_unsat_proof, prove_unsat
from mathhead.frontier import hamiltonian_path, latin_square, n_queens, ramsey_coloring, tsp_decision
from mathhead.hpsolver import pysat_available, solve_cnf

_pysat = pytest.mark.skipif(not pysat_available(), reason="python-sat not installed")


@st.composite
def _cnf(draw, max_var=4, max_clauses=8):
    nv = draw(st.integers(min_value=2, max_value=max_var))
    n = draw(st.integers(min_value=1, max_value=max_clauses))
    clauses = []
    for _ in range(n):
        size = draw(st.integers(min_value=1, max_value=nv))
        vs = draw(st.lists(st.integers(1, nv), min_size=size, max_size=size, unique=True))
        clauses.append([v if draw(st.booleans()) else -v for v in vs])
    return clauses


def _brute_sat(clauses, nv):
    for bits in range(1 << nv):
        assign = {i + 1: bool(bits >> i & 1) for i in range(nv)}
        if all(any((lit > 0) == assign[abs(lit)] for lit in cl) for cl in clauses):
            return True
    return False


# ===================== J2 — soundness + round-trip ========================= #
@given(clauses=_cnf())
@settings(max_examples=150)
def test_prove_unsat_matches_bruteforce_and_certificate_round_trips(clauses):
    nv = max(abs(lit) for cl in clauses for lit in cl)
    r = prove_unsat(clauses)
    truth = _brute_sat(clauses, nv)
    if r.status == "sat":
        assert truth
    elif r.status == "unsat":
        assert not truth                                    # sound: never UNSAT on a SAT formula
        # the produced DRUP proof is independently re-verified
        assert check_unsat_proof(clauses, r.proof).status == "verified"


@given(clauses=_cnf())
@settings(max_examples=120)
def test_checker_never_certifies_a_satisfiable_formula(clauses):
    # soundness of the certificate layer: a SATISFIABLE CNF has NO UNSAT certificate,
    # so an empty proof must be refuted and prove_unsat must never claim `unsat`.
    nv = max(abs(lit) for cl in clauses for lit in cl)
    if _brute_sat(clauses, nv):
        assert check_unsat_proof(clauses, []).status == "refuted"
        assert prove_unsat(clauses).status != "unsat"


# ===================== J2 ⋈ J3 — independent-solver agreement =============== #
@_pysat
@given(clauses=_cnf())
@settings(max_examples=120)
def test_stdlib_dpll_and_cadical_agree(clauses):
    a = prove_unsat(clauses)                    # stdlib DPLL (J2)
    b = solve_cnf(clauses, backend="pysat")     # CaDiCaL (J3)
    if a.status in ("sat", "unsat") and b.status in ("sat", "unsat"):
        assert a.status == b.status             # two independent engines, same verdict


@given(clauses=_cnf())
@settings(max_examples=80)
def test_solver_sat_model_actually_satisfies(clauses):
    r = solve_cnf(clauses, backend="builtin")
    if r.status == "sat":
        truth = set(r.witness["model"])
        assert all(any(lit in truth for lit in cl) for cl in clauses)


# ===================== J1 — reduction witnesses re-verified ================= #
@given(n=st.integers(min_value=1, max_value=8))
@settings(max_examples=8)
def test_nqueens_witness_and_known_unsat(n):
    r = n_queens(n)
    if r.status == "sat":
        cols = r.witness["columns"]
        assert len(set(cols)) == n
        assert all(abs(cols[i] - cols[j]) != abs(i - j)
                   for i in range(n) for j in range(i + 1, n))
    else:
        assert n in (2, 3)                       # only n=2,3 are impossible in this range


@given(n=st.integers(min_value=1, max_value=6))
@settings(max_examples=6)
def test_latin_square_witness_valid(n):
    r = latin_square(n)
    assert r.status == "sat"
    grid = r.witness["grid"]
    full = list(range(1, n + 1))
    assert all(sorted(row) == full for row in grid)
    assert all(sorted(grid[r_][c] for r_ in range(n)) == full for c in range(n))


def test_hamiltonian_cycle_witness_valid_on_cycle_graphs():
    for n in range(3, 7):
        edges = [[i, (i + 1) % n] for i in range(n)]   # an n-cycle
        r = hamiltonian_path(edges, n, cycle=True)
        assert r.status == "sat"
        order = r.witness["order"]
        eset = {frozenset(e) for e in edges}
        seq = order + [order[0]]
        assert all(frozenset((seq[i], seq[i + 1])) in eset for i in range(n))


def test_tsp_tour_within_budget_verified():
    dist = [[0, 2, 9, 1], [2, 0, 3, 8], [9, 3, 0, 4], [1, 8, 4, 0]]
    r = tsp_decision(dist, 12)
    if r.status == "sat":
        tour = r.witness["tour"]
        n = len(dist)
        assert sorted(tour) == list(range(n))
        cost = sum(dist[tour[k]][tour[(k + 1) % n]] for k in range(n))
        assert cost == r.witness["length"] <= 12


def test_ramsey_r33_is_six():
    # the canonical R(3,3)=6: colorable below 6, impossible at 6
    assert ramsey_coloring(5, 3, 3).status == "sat"
    assert ramsey_coloring(6, 3, 3).status == "unsat"


# ------------------------------ determinism -------------------------------- #
def test_verdict_determinism_across_track():
    assert [n_queens(6).status for _ in range(3)] == ["sat"] * 3
    assert [prove_unsat([[1], [-1]]).proof for _ in range(3)].count([[]]) == 3
    assert [solve_cnf([[1], [-1]], backend="builtin").status for _ in range(3)] == ["unsat"] * 3
