"""
Independent certificate checker (ROADMAP Track C2) — check_certificate.

Distinguishing feature: a result PRODUCED by MathHead can be re-verified with a
stdlib-only checker, INDEPENDENT of the engine (Z3/SymPy) that produced it.
Most critical test: proving (via subprocess) that the module does NOT ACTUALLY load z3/sympy.
"""
import subprocess
import sys

from mathhead.certificate import check_certificate as cc
from mathhead.frontier import subset_sum


# ----------------------- INDEPENDENCE (killer proof) ----------------------- #
def test_checker_is_engine_independent():
    # When mathhead.certificate is imported, z3/sympy must NOT ENTER sys.modules.
    code = (
        "import sys, mathhead.certificate; "
        "bad=[m for m in ('z3','sympy') if m in sys.modules]; "
        "sys.exit(1 if bad else 0)"
    )
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert r.returncode == 0, f"checker is not independent, loaded: {r.stdout} {r.stderr}"


# --------------------------- end-to-end loop ------------------------------ #
def test_end_to_end_subset_sum_then_independent_check():
    # 1) Engine (Z3) solves subset_sum  2) give witness to independent checker  3) must hold
    res = subset_sum([3, 34, 4, 12, 5, 2], 9)
    assert res.status == "sat"
    cert = {"kind": "subset_sum", "numbers": [3, 34, 4, 12, 5, 2],
            "target": 9, "indices": res.witness["indices"]}
    out = cc(cert)
    assert out.status == "verified"
    assert out.verified is True


# ------------------------------ kinds ------------------------------------ #
def test_subset_sum_refuted():
    r = cc({"kind": "subset_sum", "numbers": [3, 4, 2], "target": 9, "indices": [0, 1]})
    assert r.status == "refuted"


def test_graph_coloring_verified_and_refuted():
    assert cc({"kind": "graph_coloring", "edges": [[1, 2], [2, 3], [1, 3]],
               "colors": 3, "coloring": {"1": 0, "2": 1, "3": 2}}).status == "verified"
    assert cc({"kind": "graph_coloring", "edges": [[1, 2]], "colors": 2,
               "coloring": {"1": 0, "2": 0}}).status == "refuted"


def test_solution_exact_verified_and_refuted():
    ok = cc({"kind": "solution", "expression": "x**2 - 4", "symbol": "x", "value": "2"})
    assert ok.status == "verified" and ok.exact is True
    bad = cc({"kind": "solution", "expression": "x**2 - 4", "symbol": "x", "value": "3"})
    assert bad.status == "refuted"


def test_solution_rational_exact():
    # root 1/2: 2x - 1 = 0  ->  exact (Fraction) verified
    r = cc({"kind": "solution", "expression": "2*x - 1", "symbol": "x", "value": "1/2"})
    assert r.status == "verified" and r.exact is True


def test_not_equal_counterexample_check():
    # valid counterexample: 2x ≠ 3x @ x=1
    assert cc({"kind": "not_equal", "left": "2*x", "right": "3*x",
               "point": {"x": "1"}}).status == "verified"
    # invalid counterexample: x+x = 2x everywhere -> refuted
    assert cc({"kind": "not_equal", "left": "x+x", "right": "2*x",
               "point": {"x": "5"}}).status == "refuted"


def test_inequality_counterexample_exact():
    # x²-x @ 1/2 = -1/4 < 0  ->  counterexample to the 'x²-x >= 0' claim (exact)
    r = cc({"kind": "inequality_counterexample", "expression": "x**2 - x",
            "point": {"x": "1/2"}, "relation": ">="})
    assert r.status == "verified" and r.exact is True


def test_transcendental_is_numerical_not_exact():
    r = cc({"kind": "solution", "expression": "sin(x)", "symbol": "x", "value": "0"})
    assert r.status == "verified" and r.exact is False   # honest: numerical


# ------------------------------ safety ---------------------------------- #
def test_malicious_expression_rejected():
    assert cc({"kind": "solution", "expression": "__import__('os')",
               "symbol": "x", "value": "0"}).status == "error"


def test_unknown_kind_rejected():
    assert cc({"kind": "quantum"}).status == "error"


def test_determinism():
    for _ in range(5):
        assert cc({"kind": "solution", "expression": "x**2 - 4",
                   "symbol": "x", "value": "2"}).verified is True


# ----------------- I4: matrix / number-theory / probability --------------- #
def test_matrix_product_verified_and_refuted():
    ok = cc({"kind": "matrix_product", "a": [["1", "2"], ["3", "4"]],
             "b": [["5", "6"], ["7", "8"]], "product": [["19", "22"], ["43", "50"]]})
    assert ok.status == "verified" and ok.exact is True
    bad = cc({"kind": "matrix_product", "a": [["1", "2"], ["3", "4"]],
              "b": [["5", "6"], ["7", "8"]], "product": [["19", "22"], ["43", "51"]]})
    assert bad.status == "refuted"


def test_matrix_inverse_rational_exact():
    # A=[[4,3],[6,3]], inverse=[[-1/2,1/2],[1,-2/3]]  -> A·inv == I exactly
    r = cc({"kind": "matrix_inverse", "matrix": [["4", "3"], ["6", "3"]],
            "inverse": [["-1/2", "1/2"], ["1", "-2/3"]]})
    assert r.status == "verified" and r.exact is True
    assert cc({"kind": "matrix_inverse", "matrix": [["4", "3"], ["6", "3"]],
               "inverse": [["1", "0"], ["0", "1"]]}).status == "refuted"


def test_matrix_inverse_non_square_rejected():
    assert cc({"kind": "matrix_inverse", "matrix": [["1", "2", "3"]],
               "inverse": [["1"]]}).status == "error"


def test_linear_system_verified_and_refuted():
    ok = cc({"kind": "linear_system", "matrix": [["1", "1"], ["1", "-1"]],
             "rhs": ["10", "2"], "solution": ["6", "4"]})
    assert ok.status == "verified"
    bad = cc({"kind": "linear_system", "matrix": [["1", "1"], ["1", "-1"]],
              "rhs": ["10", "2"], "solution": ["5", "5"]})
    assert bad.status == "refuted"


def test_factorization_verified_composite_and_wrong():
    assert cc({"kind": "factorization", "n": "360",
               "factors": [["2", "3"], ["3", "2"], ["5", "1"]]}).status == "verified"
    # 6 is not prime -> not a prime factorization
    assert cc({"kind": "factorization", "n": "360",
               "factors": [["6", "1"], ["60", "1"]]}).status == "refuted"
    # product mismatch
    assert cc({"kind": "factorization", "n": "360",
               "factors": [["2", "3"], ["3", "2"]]}).status == "refuted"


def test_bezout_gcd_verified_and_refuted():
    # gcd(48,36)=12 = 48*1 + 36*(-1)
    assert cc({"kind": "bezout_gcd", "a": "48", "b": "36", "g": "12",
               "x": "1", "y": "-1"}).status == "verified"
    # wrong g (Bézout combination doesn't equal it)
    assert cc({"kind": "bezout_gcd", "a": "48", "b": "36", "g": "6",
               "x": "1", "y": "-1"}).status == "refuted"


def test_modular_inverse_verified_and_refuted():
    assert cc({"kind": "modular_inverse", "a": "3", "m": "11",
               "inverse": "4"}).status == "verified"      # 3*4=12≡1 (mod 11)
    assert cc({"kind": "modular_inverse", "a": "3", "m": "11",
               "inverse": "5"}).status == "refuted"


def test_chinese_remainder_verified_and_refuted():
    assert cc({"kind": "chinese_remainder", "moduli": ["3", "5", "7"],
               "residues": ["2", "3", "2"], "x": "23"}).status == "verified"
    assert cc({"kind": "chinese_remainder", "moduli": ["3", "5", "7"],
               "residues": ["2", "3", "2"], "x": "24"}).status == "refuted"


def test_expectation_exact_and_bad_distribution():
    # fair die: E = 7/2, exact via Fraction
    ok = cc({"kind": "expectation", "values": ["1", "2", "3", "4", "5", "6"],
             "probabilities": ["1/6", "1/6", "1/6", "1/6", "1/6", "1/6"], "expectation": "7/2"})
    assert ok.status == "verified" and ok.exact is True
    # probabilities don't sum to 1
    assert cc({"kind": "expectation", "values": ["1", "2"],
               "probabilities": ["1/2", "1/3"], "expectation": "1"}).status == "refuted"
    # wrong expectation
    assert cc({"kind": "expectation", "values": ["1", "2", "3", "4", "5", "6"],
               "probabilities": ["1/6", "1/6", "1/6", "1/6", "1/6", "1/6"],
               "expectation": "4"}).status == "refuted"


def test_i4_certificates_stay_engine_independent():
    # The new kinds must not pull in z3/sympy either (stdlib-only invariant holds).
    code = (
        "import sys, mathhead.certificate as c; "
        "c.check_certificate({'kind':'matrix_product','a':[['1']],'b':[['1']],'product':[['1']]}); "
        "c.check_certificate({'kind':'factorization','n':'6','factors':[['2','1'],['3','1']]}); "
        "bad=[m for m in ('z3','sympy') if m in sys.modules]; sys.exit(1 if bad else 0)"
    )
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert r.returncode == 0, f"I4 kinds broke independence: {r.stdout} {r.stderr}"


def test_i4_end_to_end_matrix_inverse_then_independent_check():
    # 1) Engine (SymPy) inverts a matrix  2) hand the inverse to the stdlib checker  3) must hold
    from mathhead.compute import matrix_inverse
    res = matrix_inverse([["4", "3"], ["6", "3"]])
    assert res.status == "ok"
    out = cc({"kind": "matrix_inverse", "matrix": [["4", "3"], ["6", "3"]],
              "inverse": res.result})
    assert out.status == "verified" and out.verified is True
