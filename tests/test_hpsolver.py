"""
High-performance CNF solving (ROADMAP J3) — solve_cnf.

A dedicated CDCL backend (CaDiCaL via the optional python-sat) for scale, with the
model INDEPENDENTLY verified in pure Python and the search conflict-bounded (honest
`unknown`, never a hang). The built-in stdlib fallback (always available) is tested
directly; the high-performance backend tests skip cleanly if python-sat is absent.
"""
from itertools import combinations

import pytest

from mathhead.hpsolver import pysat_available, solve_cnf
from mathhead.router import route


def _satisfies(clauses, model):
    truth = set(model)
    return all(any(lit in truth for lit in cl) for cl in clauses)


def _php(p):
    pigeons, holes = p + 1, p

    def var(i, j):
        return i * holes + j + 1

    cls = [[var(i, j) for j in range(holes)] for i in range(pigeons)]
    for j in range(holes):
        for a, b in combinations(range(pigeons), 2):
            cls.append([-var(a, j), -var(b, j)])
    return cls


# ------------------------- built-in fallback (no dep) ---------------------- #
def test_builtin_sat_model_verified():
    cnf = [[1, 2], [-1, 3], [-3]]
    r = solve_cnf(cnf, backend="builtin")
    assert r.status == "sat" and r.verified is True
    assert _satisfies(cnf, r.witness["model"])


def test_builtin_unsat_has_verified_proof():
    r = solve_cnf([[1], [-1]], backend="builtin")
    assert r.status == "unsat" and r.verified is True and r.proof is not None


def test_builtin_ceiling_is_honest_wall():
    big = [[i] for i in range(1, 25)]  # 24 vars > built-in ceiling
    r = solve_cnf(big, backend="builtin")
    assert r.status == "error" and r.reason_code == "BACKEND_UNAVAILABLE"


# ------------------------------ guardrails --------------------------------- #
def test_zero_literal_rejected():
    assert solve_cnf([[1, 0]]).status == "error"


def test_bad_backend_rejected():
    assert solve_cnf([[1]], backend="nope").reason_code == "GUARDRAIL_VIOLATION"


def test_bad_max_conflicts_rejected():
    assert solve_cnf([[1]], max_conflicts=0).reason_code == "GUARDRAIL_VIOLATION"


# --------------------- high-performance backend (optional) ----------------- #
_pysat = pytest.mark.skipif(not pysat_available(), reason="python-sat not installed")


@_pysat
def test_pysat_bad_solver_name_rejected():
    assert solve_cnf([[1]], solver="kissat").reason_code == "GUARDRAIL_VIOLATION"


@_pysat
def test_pysat_sat_model_independently_verified():
    cnf = [[1, 2], [-1, 3], [-3]]
    r = solve_cnf(cnf, backend="pysat")
    assert r.status == "sat" and r.verified is True
    assert "cadical" in r.meta["backend"]
    assert _satisfies(cnf, r.witness["model"])


@_pysat
def test_pysat_unsat():
    assert solve_cnf([[1], [-1]], backend="pysat").status == "unsat"


@_pysat
def test_pysat_scale_sat_verified():
    # a moderately large SAT instance the HP backend dispatches quickly; model verified
    n = 20

    def v(i, c):
        return i * n + c + 1

    cnf = []
    for i in range(n):
        cnf.append([v(i, c) for c in range(n)])
        for c1 in range(n):
            for c2 in range(c1 + 1, n):
                cnf.append([-v(i, c1), -v(i, c2)])
    for i in range(n - 1):
        for c in range(n):
            cnf.append([-v(i, c), -v(i + 1, c)])
    r = solve_cnf(cnf)
    assert r.status == "sat" and r.verified is True
    assert r.meta["variables"] == n * n and _satisfies(cnf, r.witness["model"])


@_pysat
def test_pysat_bounded_search_is_unknown_not_a_hang():
    # a hard instance under a tiny conflict budget → honest unknown (bounded, no hang)
    r = solve_cnf(_php(8), max_conflicts=1)
    assert r.status == "unknown" and r.reason_code == "BUDGET_EXCEEDED"


# --------------------------- routing / determinism ------------------------- #
def test_router_wiring():
    # small instance → works with or without the HP backend (auto falls back)
    assert route("solve_cnf", {"clauses": [[1, 2], [-1, 3], [-3]]}).status == "sat"


def test_verdict_determinism():
    assert [solve_cnf([[1], [-1]], backend="builtin").status for _ in range(3)] == ["unsat"] * 3
