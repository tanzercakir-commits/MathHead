"""
MCP layer contract test (ROADMAP Phase 8 [S]) — every `@mcp.tool()` tool is
actually called and returns a valid status. Also, the registered tool set and
the set this test covers are kept IN SYNC (breaks if a new tool isn't added here).

This verifies end-to-end (in-process) that the MCP interface is wired correctly
to the router and completes the server layer's test coverage. Live stdio test: Phase 11.
"""
import asyncio

import pytest

from mathhead.server import mcp_server as m

_VALID_STATUS = {
    "valid", "invalid", "sat", "unsat", "unknown", "error", "ok",
    "tautology", "contradiction", "contingent", "equivalent", "not_equivalent",
    "optimal", "unbounded", "verified", "refuted",
}

# Representative arguments for each tool (kwargs per MCP signature).
ARGS = {
    # logic
    "entailment": {"premises": ["p", "implies(p,q)"], "conclusion": "q"},
    "consistency": {"statements": ["x>2", "x<5"]},
    "model": {"statements": ["x>2"]},
    "prove": {"premises": ["p", "implies(p,q)"], "conclusion": "q"},
    "equivalent": {"a": "p", "b": "p"},
    "classify": {"formula": "p or not(p)"},
    "enumerate_models": {"statements": ["p or q"], "limit": 5},
    "optimize": {"constraints": ["x>=0", "x<=10"], "objective": "x", "sense": "max"},
    "max_satisfy": {"hard": ["p"], "soft": ["not(p)"], "weights": None},
    # inequality & nonlinear (Z3 NRA)
    "prove_inequality": {"goal": "x**2 + y**2 >= 2*x*y", "assumptions": None},
    "prove_nonnegative": {"expression": "x**2 - 2*x + 1", "assumptions": None},
    "find_real_solution": {"constraints": ["x**2 + y**2 == 1", "x == y"]},
    # verification layer (Track C)
    "verify_equality": {"left": "sin(x)**2 + cos(x)**2", "right": "1"},
    "verify_solution": {"equation": "x**2==4", "symbol": "x", "claimed": ["2", "-2"]},
    "verify_steps": {"steps": ["(x+1)**2", "x**2 + 2*x + 1"]},
    "verify_derivation": {"steps": ["2*x + 3 == 7", "2*x == 4", "x == 2"],
                          "operations": [{"op": "subtract", "value": "3"},
                                         {"op": "divide", "value": "2"}]},
    "cross_check": {"left": "(x+1)**2", "right": "x**2 + 2*x + 1"},
    "verify_derivative": {"expression": "x**3", "symbol": "x", "claimed": "3*x**2", "order": 1},
    "verify_integral": {"expression": "2*x", "symbol": "x", "claimed": "x**2"},
    "verify_limit": {"expression": "sin(x)/x", "symbol": "x", "point": "0", "claimed": "1"},
    "verify_series": {"expression": "exp(x)", "symbol": "x", "point": "0", "order": 3,
                      "claimed": "x**2/2 + x + 1"},
    "verify_matrix_identity": {"left": [["1", "2"], ["3", "4"]], "right": [["1", "2"], ["3", "4"]]},
    "check_certificate": {"certificate": {"kind": "subset_sum", "numbers": [3, 4, 2],
                                          "target": 9, "indices": [0, 1, 2]}},
    "interpret_natural": {"text": "derivative of x**3 with respect to x"},
    # compute
    "simplify": {"expression": "x + x"},
    "solve": {"equation": "x**2 == 4", "symbol": "x"},
    "differentiate": {"expression": "x**3", "symbol": "x", "order": 1},
    "integrate": {"expression": "2*x", "symbol": "x"},
    "limit": {"expression": "sin(x)/x", "symbol": "x", "point": "0", "direction": "both"},
    "series": {"expression": "exp(x)", "symbol": "x", "point": "0", "order": 5},
    "solve_system": {"equations": ["x+y==10", "x-y==2"], "symbols": ["x", "y"]},
    # linear algebra
    "determinant": {"matrix": [["1", "2"], ["3", "4"]]},
    "matrix_inverse": {"matrix": [["1", "2"], ["3", "4"]]},
    "eigenvalues": {"matrix": [["2", "0"], ["0", "3"]]},
    "matrix_rank": {"matrix": [["1", "2"], ["2", "4"]]},
    "matrix_multiply": {"a": [["1", "2"], ["3", "4"]], "b": [["5", "6"], ["7", "8"]]},
    "matrix_solve": {"matrix": [["1", "1"], ["1", "-1"]], "rhs": ["10", "2"]},
    "eigenvectors": {"matrix": [["2", "0"], ["0", "3"]]},
    "rref": {"matrix": [["1", "2"], ["2", "4"]]},
    "nullspace": {"matrix": [["1", "2"], ["2", "4"]]},
    "lu_decomposition": {"matrix": [["4", "3"], ["6", "3"]]},
    # number theory
    "gcd": {"a": "48", "b": "36"},
    "lcm": {"a": "4", "b": "6"},
    "is_prime": {"n": "97"},
    "factorize": {"n": "360"},
    "modular_inverse": {"a": "3", "m": "11"},
    "chinese_remainder": {"moduli": ["3", "5", "7"], "residues": ["2", "3", "2"]},
    "linear_diophantine": {"a": "3", "b": "6", "c": "9"},
    # combinatorics
    "permutations": {"n": "10", "k": "3"},
    "combinations": {"n": "10", "k": "3"},
    "factorial": {"n": "6"},
    "partition_count": {"n": "10"},
    "solve_recurrence": {"recurrence": "y(n)=2*y(n-1)", "func": "y", "var": "n",
                         "initial": {"0": "1"}},
    # multivariable
    "gradient": {"expression": "x**2*y", "variables": ["x", "y"]},
    "jacobian": {"expressions": ["x*y", "x+y"], "variables": ["x", "y"]},
    "hessian": {"expression": "x**2*y", "variables": ["x", "y"]},
    "divergence": {"field": ["x**2", "y**2", "z**2"], "variables": ["x", "y", "z"]},
    "curl": {"field": ["-y", "x", "0"], "variables": ["x", "y", "z"]},
    "laplacian": {"expression": "x**2 + y**2 + z**2", "variables": ["x", "y", "z"]},
    "directional_derivative": {"expression": "x**2 + y**2", "variables": ["x", "y"],
                               "direction": ["3", "4"]},
    "line_integral": {"field": ["y", "x"], "variables": ["x", "y"],
                      "parametrization": ["t", "t**2"], "param": "t", "lower": "0", "upper": "1"},
    "definite_integral": {"expression": "x**2", "symbol": "x", "lower": "0", "upper": "3"},
    "summation": {"expression": "i", "index": "i", "lower": "1", "upper": "n"},
    "product": {"expression": "i", "index": "i", "lower": "1", "upper": "5"},
    "solve_ode": {"equation": "y' = y", "func": "y", "var": "x"},
    # probability & statistics
    "mean": {"data": ["2", "4", "6"]},
    "variance": {"data": ["2", "4", "6"], "sample": False},
    "standard_deviation": {"data": ["2", "4", "6"], "sample": False},
    "median": {"data": ["3", "1", "2"]},
    "distribution": {"name": "poisson", "params": ["2"], "at": None},
    # Track B (small scale, fast)
    "pythagorean_coloring": {"n": 10},
    "pigeonhole": {"n": 4},
    "van_der_waerden": {"n": 8, "k": 3, "colors": 2},
    "schur_number": {"n": 4, "colors": 2},
    "graph_coloring": {"edges": [[1, 2], [2, 3], [1, 3]], "colors": 3, "n": None},
    "subset_sum": {"numbers": [3, 34, 4, 12, 5, 2], "target": 9},
}


def _registered_names():
    return {t.name for t in asyncio.run(m.mcp.list_tools())}


def test_args_cover_all_registered_tools():
    # Every registered tool must be represented here (test warns when a new tool is added).
    registered = _registered_names()
    covered = set(ARGS)
    assert registered == covered, (
        f"missing: {registered - covered}  |  extra: {covered - registered}"
    )


@pytest.mark.parametrize("name", sorted(ARGS), ids=sorted(ARGS))
def test_mcp_tool_callable_and_valid(name):
    fn = getattr(m, name)
    result = fn(**ARGS[name])
    assert isinstance(result, dict)
    assert result.get("status") in _VALID_STATUS, f"{name}: {result.get('status')!r}"
