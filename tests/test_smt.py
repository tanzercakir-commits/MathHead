"""
Extra SMT theories (ROADMAP H2) — bit-vectors, EUF, arrays, strings.

Unified shape: check_<theory>(assumptions, goal=None). goal → entailment
(valid/invalid + witness); goal=None → consistency (sat/unsat). Best-case (real
theory theorems), honesty (counterexamples + grammar rejection), determinism.
"""
from mathhead.core.smt import (
    check_arrays,
    check_bitvector,
    check_strings,
    check_uninterpreted,
)
from mathhead.router import route


# ------------------------------ bit-vectors -------------------------------- #
def test_bv_xor_cancellation_valid():
    r = check_bitvector([], "x ^ y ^ y == x", 8)
    assert r.status == "valid" and r.reason_code == "ENTAILED"


def test_bv_or_is_not_add_counterexample():
    r = check_bitvector([], "(x | y) == (x + y)", 8)
    assert r.status == "invalid"
    assert r.witness is not None and set(r.witness) == {"x", "y"}


def test_bv_shift_is_double():
    r = check_bitvector([], "implies(True, (x << 1) == x + x)", 8)
    assert r.status == "valid"


def test_bv_power_of_two_consistency():
    r = check_bitvector(["(x & (x - 1)) == 0", "x != 0"], None, 8)
    assert r.status == "sat"
    # the witness is a genuine power of two
    v = r.witness["x"]
    assert v != 0 and (v & (v - 1)) == 0


def test_bv_signed_negative():
    r = check_bitvector(["x < 0"], None, 8, signed=True)
    assert r.status == "sat" and r.witness["x"] < 0


def test_bv_unsupported_operator_rejected():
    assert check_bitvector([], "x / y == 1", 8).status == "error"


def test_bv_bad_width_rejected():
    r = check_bitvector([], "x == x", 0)
    assert r.status == "error" and r.reason_code == "GUARDRAIL_VIOLATION"


# --------------------------- uninterpreted (EUF) --------------------------- #
def test_euf_congruence():
    r = check_uninterpreted(["a == b"], "f(a) == f(b)")
    assert r.status == "valid" and r.reason_code == "ENTAILED"


def test_euf_chain_entailment():
    r = check_uninterpreted(["f(f(a)) == a", "f(a) == b"], "f(b) == a")
    assert r.status == "valid"


def test_euf_independent_functions_not_entailed():
    r = check_uninterpreted(["a == b"], "f(a) == g(b)")
    assert r.status == "invalid"


def test_euf_predicate_consistency():
    r = check_uninterpreted(["P(a)", "implies(P(a), Q(a))"], None)
    assert r.status == "sat"


def test_euf_symbol_kind_clash_rejected():
    # 'a' used as a constant and as a function -> honest rejection (no silent guess)
    r = check_uninterpreted(["a == b", "a(b) == b"], None)
    assert r.status == "error" and r.reason_code == "PARSE_ERROR"


# ------------------------------- arrays ------------------------------------ #
def test_array_read_over_write_same():
    r = check_arrays([], "select(store(a, i, v), i) == v")
    assert r.status == "valid"


def test_array_read_over_write_different():
    r = check_arrays(["i != j"], "select(store(a, i, v), j) == select(a, j)")
    assert r.status == "valid"


def test_array_write_mismatch_invalid():
    r = check_arrays([], "select(store(a, i, v), j) == v")
    assert r.status == "invalid"


def test_array_consistency():
    r = check_arrays(["select(a, 0) == 5", "select(a, 1) == 7"], None)
    assert r.status == "sat"


# ------------------------------- strings ----------------------------------- #
def test_string_length_of_concat():
    r = check_strings([], "length(x + y) == length(x) + length(y)")
    assert r.status == "valid"


def test_string_concat_solve():
    r = check_strings(['x + "b" == "ab"'], None)
    assert r.status == "sat" and r.witness["x"] == "a"


def test_string_contains_entailment():
    r = check_strings(['x == "hello"'], 'contains(x, "ell")')
    assert r.status == "valid"


def test_string_prefix_false_is_invalid():
    r = check_strings([], 'prefixof("b", "ab")')
    assert r.status == "invalid"


def test_string_order_comparison_rejected():
    assert check_strings([], "x < y").status == "error"


# --------------------------- routing / determinism ------------------------- #
def test_router_wiring_all_four():
    assert route("check_bitvector", {"assumptions": [], "goal": "x ^ x == 0", "width": 8}).status == "valid"
    assert route("check_uninterpreted", {"assumptions": ["a == b"], "goal": "f(a) == f(b)"}).status == "valid"
    assert route("check_arrays", {"assumptions": [], "goal": "select(store(a, i, v), i) == v"}).status == "valid"
    assert route("check_strings", {"assumptions": [], "goal": "contains(x + y, x)"}).status == "valid"


def test_guardrail_assumptions_must_be_list():
    r = check_bitvector("not a list", None, 8)
    assert r.status == "error" and r.reason_code == "GUARDRAIL_VIOLATION"


def test_determinism():
    # ADR-0019: the VERDICT is deterministic; a counterexample witness is an *example*
    # (equally-valid witnesses may differ), so we assert the verdict is stable.
    assert [check_bitvector([], "(x | y) == (x + y)", 8).status for _ in range(5)] == ["invalid"] * 5
    assert [check_uninterpreted(["a == b"], "f(a) == f(b)").status for _ in range(5)] == ["valid"] * 5
    assert [check_arrays([], "select(store(a, i, v), i) == v").status for _ in range(3)] == ["valid"] * 3
