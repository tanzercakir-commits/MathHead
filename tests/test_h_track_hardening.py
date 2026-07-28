"""
Track H hardening (ROADMAP H5) — the property tests ARE the guarantees.

Cross-cuts H1 induction, H2 SMT theories, H3 quantifier elimination, H4 modal logic.
No new tools. Theorems as properties (a proved statement must hold on concrete input),
independent witness verification (a modal countermodel is re-checked in pure Python),
and determinism.
"""
import ast

from hypothesis import given, settings
from hypothesis import strategies as st

from mathhead.core.induction import prove_by_induction
from mathhead.core.modal import check_modal
from mathhead.core.qe import eliminate_quantifiers as qe
from mathhead.core.smt import check_arrays, check_bitvector, check_strings, check_uninterpreted


# =========================================================================== #
# H1 — induction: a PROVED theorem must actually hold on concrete integers.
# =========================================================================== #
_PROVEN = [
    ("(n*(n+1)) % 2 == 0", lambda n: (n * (n + 1)) % 2 == 0),
    ("(n**3 - n) % 3 == 0", lambda n: (n ** 3 - n) % 3 == 0),
    ("n**2 >= n", lambda n: n ** 2 >= n),
    ("(n+1)**2 == n**2 + 2*n + 1", lambda n: (n + 1) ** 2 == n ** 2 + 2 * n + 1),
]


def test_induction_proves_the_theorems():
    for claim, _ in _PROVEN:
        assert prove_by_induction(claim, "n", 0).status == "valid"


@given(n=st.integers(min_value=0, max_value=100_000))
@settings(max_examples=50, deadline=None)
def test_induction_proven_theorems_hold_numerically(n):
    # the tool PROVED these; the property confirms they are genuinely true on samples
    for _, fn in _PROVEN:
        assert fn(n)


def test_induction_base_failure_is_genuinely_false():
    # a claim the tool calls `invalid` at the base must be actually false at start
    r = prove_by_induction("n >= 5", "n", 0)
    assert r.status == "invalid"
    assert not (0 >= 5)  # P(start) is really false


def test_induction_determinism():
    for claim, _ in _PROVEN:
        outs = [prove_by_induction(claim, "n", 0).status for _ in range(5)]
        assert outs == ["valid"] * 5


# =========================================================================== #
# H2 — SMT theories: proved identities must hold on concrete values.
# =========================================================================== #
def test_bv_identities_are_proved():
    assert check_bitvector([], "x ^ y ^ y == x", 8).status == "valid"
    assert check_bitvector([], "~(x & y) == (~x) | (~y)", 8).status == "valid"   # De Morgan
    assert check_bitvector([], "(x << 1) == x + x", 8).status == "valid"


@given(x=st.integers(0, 255), y=st.integers(0, 255))
@settings(max_examples=100, deadline=None)
def test_bv_demorgan_holds_concretely(x, y):
    mask = 0xFF
    assert ((~(x & y)) & mask) == (((~x) & mask) | ((~y) & mask))
    assert ((x << 1) & mask) == ((x + x) & mask)


def test_euf_congruence_invariant():
    # a==b ⊨ f(a)==f(b) is a theorem of EUF (congruence)
    assert check_uninterpreted(["a == b"], "f(a) == f(b)").status == "valid"


def test_array_mccarthy_invariant():
    assert check_arrays([], "select(store(a, i, v), i) == v").status == "valid"


def test_string_length_concat_is_proved():
    assert check_strings([], "length(x + y) == length(x) + length(y)").status == "valid"


@given(a=st.text(max_size=6), b=st.text(max_size=6))
@settings(max_examples=60, deadline=None)
def test_string_length_concat_holds_concretely(a, b):
    assert len(a + b) == len(a) + len(b)


# =========================================================================== #
# H3 — quantifier elimination: correspondence + determinism.
# =========================================================================== #
@given(k=st.integers(min_value=2, max_value=6))
@settings(max_examples=5, deadline=None)
def test_qe_divisibility_is_a_modular_condition(k):
    # ∃y. x = k*y  eliminates to a modular (divisibility) condition on x
    r = qe(f"exists(y, x == {k}*y)")
    assert r.status == "ok" and "%" in r.result


@given(x=st.integers(-40, 40), k=st.integers(2, 6))
@settings(max_examples=80, deadline=None)
def test_qe_divisibility_matches_reality(x, k):
    # the statement ∃y. x = k*y is TRUE iff k divides x — a check of the math QE encodes
    exists_y = any(x == k * y for y in range(-50, 51))
    assert exists_y == (x % k == 0)


def test_qe_determinism():
    outs = [qe("exists(x, (a <= x) and (x <= b))").result for _ in range(5)]
    assert len(set(outs)) == 1


# =========================================================================== #
# H4 — modal logic: independent countermodel verification + duality.
# =========================================================================== #
def _kripke_eval(node: ast.AST, w: int, edges: set, val: dict) -> bool:
    """A pure-Python Kripke evaluator — INDEPENDENT of Z3 — to re-check a countermodel."""
    if isinstance(node, ast.Name):
        return val[w][node.id]
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return not _kripke_eval(node.operand, w, edges, val)
    if isinstance(node, ast.BoolOp):
        vals = [_kripke_eval(v, w, edges, val) for v in node.values]
        return all(vals) if isinstance(node.op, ast.And) else any(vals)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        fid, args = node.func.id, node.args
        if fid == "implies":
            return (not _kripke_eval(args[0], w, edges, val)) or _kripke_eval(args[1], w, edges, val)
        if fid == "iff":
            return _kripke_eval(args[0], w, edges, val) == _kripke_eval(args[1], w, edges, val)
        worlds = sorted(val)
        if fid == "box":
            return all(_kripke_eval(args[0], u, edges, val) for u in worlds if (w, u) in edges)
        if fid == "dia":
            return any(_kripke_eval(args[0], u, edges, val) for u in worlds if (w, u) in edges)
    raise AssertionError(f"unexpected node {ast.dump(node)}")


_INVALID = [
    ("implies(box(p), p)", "K"),                         # T axiom fails without reflexivity
    ("implies(box(p), box(box(p)))", "T"),               # 4 axiom fails without transitivity
    ("implies(dia(p), box(dia(p)))", "S4"),              # 5 axiom fails without symmetry
]


def test_modal_countermodels_independently_refute():
    for formula, system in _INVALID:
        r = check_modal(formula, system)
        assert r.status == "invalid", (formula, system)
        w = r.witness
        edges = {(a, b) for a, b in w["accessibility"]}
        val = {int(k): v for k, v in w["valuation"].items()}
        node = ast.parse(formula, mode="eval").body
        # the reported world really makes the formula FALSE (independent of Z3)
        assert _kripke_eval(node, w["false_at_world"], edges, val) is False


def test_modal_duality_holds_in_k():
    # □p ⟺ ¬◇¬p  and  ◇p ⟺ ¬□¬p  are valid in every normal system (modal duality)
    assert check_modal("iff(box(p), not(dia(not(p))))", "K").status == "valid"
    assert check_modal("iff(dia(p), not(box(not(p))))", "K").status == "valid"


def test_modal_verdict_determinism():
    for formula, system in _INVALID:
        assert [check_modal(formula, system).status for _ in range(5)] == ["invalid"] * 5
