"""
Frontier J1 — new reductions: N-queens, Latin squares, Sudoku, Hamiltonian
path/cycle, Ramsey, decision-TSP.

Each `sat` witness is INDEPENDENTLY verified in pure Python (meta.verified). Known
results are the acceptance test (n-queens unsat at 2/3; R(3,3)=6; a Hamiltonian cycle
needs the right graph). Best-case + honest unsat + independent certificate.
"""
from mathhead.frontier import (
    hamiltonian_path,
    latin_square,
    n_queens,
    ramsey_coloring,
    sudoku_solve,
    tsp_decision,
)
from mathhead.router import route

# canonical Sudoku with a unique solution
_PUZZLE = [
    [5, 3, 0, 0, 7, 0, 0, 0, 0],
    [6, 0, 0, 1, 9, 5, 0, 0, 0],
    [0, 9, 8, 0, 0, 0, 0, 6, 0],
    [8, 0, 0, 0, 6, 0, 0, 0, 3],
    [4, 0, 0, 8, 0, 3, 0, 0, 1],
    [7, 0, 0, 0, 2, 0, 0, 0, 6],
    [0, 6, 0, 0, 0, 0, 2, 8, 0],
    [0, 0, 0, 4, 1, 9, 0, 0, 5],
    [0, 0, 0, 0, 8, 0, 0, 7, 9],
]


# ------------------------------- N-queens ---------------------------------- #
def test_queens_eight_solved_and_verified():
    r = n_queens(8)
    assert r.status == "sat" and r.meta["verified"] is True
    cols = r.witness["columns"]
    assert sorted(cols) == list(range(8))  # a permutation = distinct columns


def test_queens_three_impossible():
    assert n_queens(3).status == "unsat"
    assert n_queens(2).status == "unsat"


def test_queens_guardrail():
    assert n_queens(0).status == "error"


# ----------------------------- Latin square -------------------------------- #
def test_latin_square_completed_and_verified():
    r = latin_square(4)
    assert r.status == "sat" and r.meta["verified"] is True
    grid = r.witness["grid"]
    for row in grid:
        assert sorted(row) == [1, 2, 3, 4]


def test_latin_square_impossible_givens():
    # a repeated symbol in a column cannot be a Latin square
    assert latin_square(2, [[1, 0], [1, 0]]).status == "unsat"


# ------------------------------- Sudoku ------------------------------------ #
def test_sudoku_solved_and_verified():
    r = sudoku_solve(_PUZZLE)
    assert r.status == "sat" and r.meta["verified"] is True
    grid = r.witness["grid"]
    assert all(sorted(row) == list(range(1, 10)) for row in grid)
    # clues respected
    assert all(_PUZZLE[i][j] == 0 or grid[i][j] == _PUZZLE[i][j] for i in range(9) for j in range(9))


def test_sudoku_contradictory_is_unsat():
    bad = [row[:] for row in _PUZZLE]
    bad[0][2] = 5  # duplicate 5 in row 0 → no solution
    assert sudoku_solve(bad).status == "unsat"


def test_sudoku_guardrail():
    assert sudoku_solve([[0] * 9] * 8).status == "error"  # wrong shape


# --------------------------- Hamiltonian ----------------------------------- #
def test_hamiltonian_path_exists():
    r = hamiltonian_path([[0, 1], [1, 2], [2, 3]], 4)
    assert r.status == "sat" and r.meta["verified"] is True


def test_no_hamiltonian_cycle_in_path_graph():
    assert hamiltonian_path([[0, 1], [1, 2], [2, 3]], 4, cycle=True).status == "unsat"


def test_hamiltonian_cycle_in_square():
    r = hamiltonian_path([[0, 1], [1, 2], [2, 3], [3, 0]], 4, cycle=True)
    assert r.status == "sat" and r.meta["verified"] is True


# ------------------------------- Ramsey ------------------------------------ #
def test_ramsey_r33_colorable_below_six():
    # R(3,3) = 6, so K_5 CAN be 2-colored with no monochromatic triangle
    r = ramsey_coloring(5, 3, 3)
    assert r.status == "sat" and r.meta["verified"] is True


def test_ramsey_r33_impossible_at_six():
    # K_6 cannot — the classic R(3,3)=6 impossibility
    assert ramsey_coloring(6, 3, 3).status == "unsat"


# ------------------------------- TSP --------------------------------------- #
_DIST = [[0, 1, 2, 1], [1, 0, 1, 2], [2, 1, 0, 1], [1, 2, 1, 0]]


def test_tsp_within_budget_verified():
    r = tsp_decision(_DIST, 4)
    assert r.status == "sat" and r.meta["verified"] is True
    assert r.witness["length"] <= 4
    assert sorted(r.witness["tour"]) == [0, 1, 2, 3]


def test_tsp_below_optimum_is_unsat():
    assert tsp_decision(_DIST, 3).status == "unsat"


# --------------------------- routing / determinism ------------------------- #
def test_router_wiring():
    assert route("n_queens", {"n": 6}).status == "sat"
    assert route("ramsey_coloring", {"n": 6, "s": 3, "t": 3}).status == "unsat"
    assert route("tsp_decision", {"distances": _DIST, "budget": 4}).status == "sat"


def test_determinism_of_verdicts():
    assert [n_queens(6).status for _ in range(3)] == ["sat"] * 3
    assert [ramsey_coloring(6, 3, 3).status for _ in range(3)] == ["unsat"] * 3
