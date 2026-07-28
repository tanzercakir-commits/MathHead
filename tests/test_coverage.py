"""
Targeted guardrail / error-branch coverage (ROADMAP K2). Complements the fuzzers:
each case here asserts a SPECIFIC rejection path returns a clean `error` (never a
crash), exercising the fences across every layer. Doubles as coverage and as a
guarantee that malformed input is refused, not guessed (Wall #2).
"""
import pytest

from mathhead.cache import memoize, reset_cache
from mathhead.guardrails import GuardrailError, validate_input
from mathhead.router import route

# (task, payload) pairs that MUST return status == "error"
_ERRORS = [
    # compute / CAS
    ("determinant", {"matrix": [["1", "2"], ["3"]]}),         # ragged matrix
    ("eigenvalues", {"matrix": [["a", "b"]]}),                # non-square
    ("matrix_inverse", {"matrix": [["@@"]]}),                 # bad cell
    ("gradient", {"expression": "x*/", "variables": ["x"]}),  # parse error
    ("laplace_transform", {"expression": "))("}),
    ("distribution", {"name": "nonesuch", "params": {}}),     # unknown distribution
    ("t_test", {"sample1": []}),                              # empty sample
    ("linear_regression", {"x": [1], "y": [1, 2]}),           # length mismatch
    ("solve_recurrence", {"recurrence": "@@@"}),
    ("factorize", {"n": "not-a-number"}),
    ("modular_inverse", {"a": 2, "m": 4}),                    # no inverse (gcd≠1)
    # inequality (Z3 NRA)
    ("prove_inequality", {"goal": "x + 1", "assumptions": None}),   # not a comparison
    ("prove_nonnegative", {"expression": ""}),
    # induction
    ("prove_by_induction", {"claim": "n >= 1.5", "var": "n", "start": 0}),  # float
    ("prove_by_induction", {"claim": "n >= 0", "var": "1bad", "start": 0}),  # bad var
    # SMT theories
    ("check_bitvector", {"assumptions": [], "goal": "x / y == 1", "width": 8}),   # unsupported op
    ("check_bitvector", {"assumptions": [], "goal": "x == x", "width": 0}),        # bad width
    ("check_uninterpreted", {"assumptions": ["a == b", "a(b) == b"], "goal": None}),  # kind clash
    ("check_arrays", {"assumptions": [], "goal": "x", "index_sort": "Foo"}),        # bad sort
    ("check_strings", {"assumptions": [], "goal": "x < y"}),                        # order on strings
    ("check_strings", {"assumptions": [], "goal": "implies(p)"}),                   # bad arity
    # quantifier elimination
    ("eliminate_quantifiers", {"formula": "x*y > 0"}),        # nonlinear
    # modal
    ("check_modal", {"formula": "p", "system": "Q9"}),        # bad system
    ("check_modal", {"formula": "p", "system": "K", "max_worlds": 99}),  # too many worlds
    ("check_modal", {"formula": "nec(p)", "system": "K"}),    # unknown operator
    # frontier J1
    ("n_queens", {"n": 0}),
    ("latin_square", {"n": 3, "givens": [[1, 2]]}),           # wrong shape
    ("sudoku_solve", {"givens": [[0] * 9] * 3}),              # wrong shape
    ("hamiltonian_path", {"edges": [[0, 0]], "n": 2}),        # self-loop
    ("ramsey_coloring", {"n": 20, "s": 3, "t": 3}),           # n too big
    ("tsp_decision", {"distances": [[0, 1], [1]], "budget": 5}),  # ragged
    ("tsp_decision", {"distances": [[0, 1], [1, 0]], "budget": -1}),  # bad budget
    # DRUP / CNF
    ("prove_unsat", {"clauses": []}),
    ("prove_unsat", {"clauses": [[1, 0]]}),                   # zero literal
    ("check_unsat_proof", {"clauses": [[1]], "proof": [[0]]}),  # zero in proof
    ("solve_cnf", {"clauses": [[1, 0]], "backend": "builtin"}),
    ("solve_cnf", {"clauses": [[1]], "solver": "kissat", "backend": "pysat"}),  # bad solver
    # verification layer
    ("verify_solution", {"equation": "@@", "symbol": "x", "claimed": ["1"]}),
    ("cross_check", {"left": "))(", "right": "x"}),
    # batch (K1)
    ("entail_batch", {"premises": ["p"], "conclusions": []}),
]


@pytest.mark.parametrize("task,payload", _ERRORS, ids=[t for t, _ in _ERRORS])
def test_guardrails_reject_cleanly(task, payload):
    r = route(task, payload)
    assert r.status == "error", f"{task}: expected error, got {r.status}"


# Malformed inputs across the wider compute surface (transforms, complex, ODE, graphs,
# linear algebra III, statistics) — each must be a clean error, exercising those branches.
_BAD = "))("          # a guaranteed parse error
_RAGGED = [["1", "2"], ["3"]]
_COMPUTE_ERRORS = [
    ("laplace_transform", {"expression": _BAD}),
    ("inverse_laplace_transform", {"expression": _BAD}),
    ("fourier_transform", {"expression": _BAD}),
    ("z_transform", {"expression": _BAD}),
    ("residue", {"expression": _BAD, "symbol": "x", "point": "0"}),
    ("contour_integral", {"expression": _BAD, "symbol": "x", "poles": ["0"]}),
    ("laurent_series", {"expression": _BAD, "symbol": "x"}),
    ("complex_parts", {"expression": _BAD}),
    ("solve_ode", {"equation": _BAD}),
    ("solve_ode_system", {"equations": [_BAD], "functions": ["y"]}),
    ("classify_ode", {"equation": _BAD}),
    ("solve_pde", {"equation": _BAD, "variables": ["x", "t"]}),
    ("singular_values", {"matrix": _RAGGED}),
    ("qr_decomposition", {"matrix": _RAGGED}),
    ("cholesky_decomposition", {"matrix": _RAGGED}),
    ("pseudoinverse", {"matrix": _RAGGED}),
    ("matrix_exponential", {"matrix": _RAGGED}),
    ("jordan_form", {"matrix": _RAGGED}),
    ("characteristic_polynomial", {"matrix": _RAGGED}),
    ("gradient", {"expression": _BAD, "variables": ["x"]}),
    ("jacobian", {"expressions": [_BAD], "variables": ["x"]}),
    ("hessian", {"expression": _BAD, "variables": ["x"]}),
    ("divergence", {"field": [_BAD], "variables": ["x"]}),
    ("curl", {"field": [_BAD, _BAD, _BAD], "variables": ["x", "y", "z"]}),
    ("definite_integral", {"expression": _BAD, "symbol": "x", "lower": "0", "upper": "1"}),
    ("summation", {"expression": _BAD, "index": "k", "lower": "1", "upper": "n"}),
    ("critical_points", {"expression": _BAD, "variables": ["x"]}),
    ("check_convexity", {"expression": _BAD, "variables": ["x"]}),
    ("chi_square_test", {"observed": [1, 2], "expected": [1]}),           # length mismatch
    ("confidence_interval", {"data": []}),                                # empty
    ("runge_kutta", {"rhs": _BAD, "x0": 0, "y0": 1, "x_end": 1}),
    ("find_root_newton", {"expression": _BAD, "symbol": "x", "x0": 1}),
    ("numerical_integrate", {"expression": _BAD, "symbol": "x", "lower": 0, "upper": 1}),
]


@pytest.mark.parametrize("task,payload", _COMPUTE_ERRORS, ids=[t for t, _ in _COMPUTE_ERRORS])
def test_compute_error_branches(task, payload):
    r = route(task, payload)
    assert r.status == "error", f"{task}: expected error, got {r.status}"


# -------------------------- guardrail unit edges --------------------------- #
def test_validate_input_edges():
    with pytest.raises(GuardrailError):
        validate_input("not a list")
    with pytest.raises(GuardrailError):
        validate_input([])
    with pytest.raises(GuardrailError):
        validate_input(["  "])                 # empty/whitespace statement
    with pytest.raises(GuardrailError):
        validate_input(["x" * 5000])           # over the length limit
    with pytest.raises(GuardrailError):
        validate_input(["((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((x" + ")" * 68])


# ------------------------------ cache eviction ----------------------------- #
def test_cache_lru_eviction():
    reset_cache()
    calls = {"n": 0}

    @memoize
    def f(x):
        calls["n"] += 1
        return x * x

    for i in range(1100):                      # exceed the 1024 capacity → LRU eviction
        f(i)
    from mathhead.cache import cache_stats
    assert cache_stats()["evictions"] > 0
    assert cache_stats()["size"] <= cache_stats()["capacity"]
