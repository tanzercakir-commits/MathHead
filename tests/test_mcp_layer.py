"""
MCP katmanı sözleşme testi (ROADMAP Aşama 8 [S]) — her `@mcp.tool()` aracı
gerçekten çağrılır ve geçerli bir statü döndürür. Ayrıca kayıtlı araç kümesi ile
bu testin kapsadığı küme SENKRON tutulur (yeni araç buraya eklenmezse kırılır).

Bu, MCP arayüzünün router'a doğru bağlandığını uçtan uca (in-process) doğrular
ve server katmanının test kapsamını tamamlar. Canlı stdio testi: Aşama 11.
"""
import asyncio

import pytest

from mathhead.server import mcp_server as m

_VALID_STATUS = {
    "valid", "invalid", "sat", "unsat", "unknown", "error", "ok",
    "tautology", "contradiction", "contingent", "equivalent", "not_equivalent",
    "optimal", "unbounded",
}

# Her araç için temsili argümanlar (MCP imzasına göre kwargs).
ARGS = {
    # mantık
    "entailment": {"premises": ["p", "implies(p,q)"], "conclusion": "q"},
    "consistency": {"statements": ["x>2", "x<5"]},
    "model": {"statements": ["x>2"]},
    "prove": {"premises": ["p", "implies(p,q)"], "conclusion": "q"},
    "equivalent": {"a": "p", "b": "p"},
    "classify": {"formula": "p or not(p)"},
    "enumerate_models": {"statements": ["p or q"], "limit": 5},
    "optimize": {"constraints": ["x>=0", "x<=10"], "objective": "x", "sense": "max"},
    "max_satisfy": {"hard": ["p"], "soft": ["not(p)"], "weights": None},
    # hesap
    "simplify": {"expression": "x + x"},
    "solve": {"equation": "x**2 == 4", "symbol": "x"},
    "differentiate": {"expression": "x**3", "symbol": "x", "order": 1},
    "integrate": {"expression": "2*x", "symbol": "x"},
    "limit": {"expression": "sin(x)/x", "symbol": "x", "point": "0", "direction": "both"},
    "series": {"expression": "exp(x)", "symbol": "x", "point": "0", "order": 5},
    "solve_system": {"equations": ["x+y==10", "x-y==2"], "symbols": ["x", "y"]},
    # lineer cebir
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
    # sayı teorisi
    "gcd": {"a": "48", "b": "36"},
    "lcm": {"a": "4", "b": "6"},
    "is_prime": {"n": "97"},
    "factorize": {"n": "360"},
    "modular_inverse": {"a": "3", "m": "11"},
    "chinese_remainder": {"moduli": ["3", "5", "7"], "residues": ["2", "3", "2"]},
    "linear_diophantine": {"a": "3", "b": "6", "c": "9"},
    # kombinatorik
    "permutations": {"n": "10", "k": "3"},
    "combinations": {"n": "10", "k": "3"},
    "factorial": {"n": "6"},
    "partition_count": {"n": "10"},
    "solve_recurrence": {"recurrence": "y(n)=2*y(n-1)", "func": "y", "var": "n",
                         "initial": {"0": "1"}},
    # çok değişkenli
    "gradient": {"expression": "x**2*y", "variables": ["x", "y"]},
    "jacobian": {"expressions": ["x*y", "x+y"], "variables": ["x", "y"]},
    "hessian": {"expression": "x**2*y", "variables": ["x", "y"]},
    "definite_integral": {"expression": "x**2", "symbol": "x", "lower": "0", "upper": "3"},
    "summation": {"expression": "i", "index": "i", "lower": "1", "upper": "n"},
    "product": {"expression": "i", "index": "i", "lower": "1", "upper": "5"},
    "solve_ode": {"equation": "y' = y", "func": "y", "var": "x"},
    # olasılık & istatistik
    "mean": {"data": ["2", "4", "6"]},
    "variance": {"data": ["2", "4", "6"], "sample": False},
    "standard_deviation": {"data": ["2", "4", "6"], "sample": False},
    "median": {"data": ["3", "1", "2"]},
    "distribution": {"name": "poisson", "params": ["2"], "at": None},
    # Track B (küçük ölçek, hızlı)
    "pythagorean_coloring": {"n": 10},
    "pigeonhole": {"n": 4},
    "van_der_waerden": {"n": 8, "k": 3, "colors": 2},
    "schur_number": {"n": 4, "colors": 2},
}


def _registered_names():
    return {t.name for t in asyncio.run(m.mcp.list_tools())}


def test_args_cover_all_registered_tools():
    # Kayıtlı her araç burada temsil edilmeli (yeni araç eklenince test uyarır).
    registered = _registered_names()
    covered = set(ARGS)
    assert registered == covered, (
        f"eksik: {registered - covered}  |  fazla: {covered - registered}"
    )


@pytest.mark.parametrize("name", sorted(ARGS), ids=sorted(ARGS))
def test_mcp_tool_callable_and_valid(name):
    fn = getattr(m, name)
    result = fn(**ARGS[name])
    assert isinstance(result, dict)
    assert result.get("status") in _VALID_STATUS, f"{name}: {result.get('status')!r}"
