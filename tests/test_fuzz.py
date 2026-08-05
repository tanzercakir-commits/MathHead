"""
Parser fuzzing (ROADMAP K2). Throw malformed, random, and adversarial input at EVERY
parser-backed tool and assert the fence holds: the engine never raises an uncaught
exception — it always returns a well-formed result with a string `status` (a clean
error or a valid verdict). This exercises the guardrail/reject paths across the logic,
compute, induction, SMT-theory, quantifier-elimination, modal, and CNF parsers.
"""
from hypothesis import given, settings
from hypothesis import strategies as st

from mathhead.router import route

# a math-flavoured alphabet that stresses operators, keywords, and delimiters
_MATHY = st.text(
    alphabet="xyznpq01234()[]+-*/%.,<>=!~&|^ andornotimpliesiffforallexistsboxdiaselectstore",
    max_size=48,
)

# (router task, payload builder from a single fuzzed string)
_STRING_TASKS = [
    ("simplify", lambda s: {"expression": s}),
    ("solve", lambda s: {"equation": s, "symbol": "x"}),
    ("differentiate", lambda s: {"expression": s, "symbol": "x"}),
    ("integrate", lambda s: {"expression": s, "symbol": "x"}),
    ("limit", lambda s: {"expression": s, "symbol": "x"}),
    ("series", lambda s: {"expression": s, "symbol": "x"}),
    ("consistency", lambda s: {"statements": [s]}),
    ("entailment", lambda s: {"premises": [s], "conclusion": s}),
    ("equivalent", lambda s: {"a": s, "b": s}),
    ("classify", lambda s: {"formula": s}),
    ("prove", lambda s: {"premises": [s], "conclusion": s}),
    ("prove_inequality", lambda s: {"goal": s, "assumptions": None}),
    ("prove_by_induction", lambda s: {"claim": s, "var": "n", "start": 0}),
    ("eliminate_quantifiers", lambda s: {"formula": s}),
    ("check_modal", lambda s: {"formula": s, "system": "K", "max_worlds": 3}),
    ("check_bitvector", lambda s: {"assumptions": [s], "goal": None, "width": 8}),
    ("check_uninterpreted", lambda s: {"assumptions": [s], "goal": None}),
    ("check_arrays", lambda s: {"assumptions": [s], "goal": None}),
    ("check_strings", lambda s: {"assumptions": [s], "goal": None}),
    ("interpret_natural", lambda s: {"text": s}),
]


def _wellformed(result) -> bool:
    return isinstance(getattr(result, "status", None), str) and bool(result.status)


@given(s=_MATHY)
@settings(max_examples=250, deadline=None)
def test_string_parsers_never_crash_on_mathy_input(s):
    for task, make in _STRING_TASKS:
        assert _wellformed(route(task, make(s))), f"{task} crashed on {s!r}"


@given(s=st.text(max_size=64))
@settings(max_examples=120, deadline=None)
def test_string_parsers_never_crash_on_arbitrary_unicode(s):
    for task, make in _STRING_TASKS:
        assert _wellformed(route(task, make(s))), f"{task} crashed on {s!r}"


# a handful of classic parser landmines, checked exhaustively
_LANDMINES = [
    "", " ", "()", "(", ")", "((((((((((", "1/0", "x**", "**x", ",", "==", "and",
    "forall(", "exists(x)", "implies(p)", "box()", "select()", "x y", "0x1", "1e", "--", "+",
    # the third real bug this fuzzer caught (v4F0 follow-up): logical connectives over
    # non-boolean operands used to escape as z3.Z3Exception from the inequality, induction,
    # and bit-vector parsers
    "implies(0,0)", "iff(0,0)", "not(0)", "0 and x", "0 or x", "implies(x>0,1)",
    "implies(0,0) and x>1",
]


def test_landmine_strings_are_all_clean_errors_or_results():
    for s in _LANDMINES:
        for task, make in _STRING_TASKS:
            r = route(task, make(s))
            assert _wellformed(r), f"{task} mishandled {s!r}"


# ------------------------------ CNF fuzzing -------------------------------- #
_CNF = st.lists(st.lists(st.integers(min_value=-6, max_value=6), max_size=4), max_size=6)


@given(clauses=_CNF)
@settings(max_examples=200, deadline=None)
def test_cnf_tools_never_crash(clauses):
    # includes 0-literals (rejected), empty clauses, and empty CNF — none may crash
    assert _wellformed(route("prove_unsat", {"clauses": clauses}))
    assert _wellformed(route("check_unsat_proof", {"clauses": clauses, "proof": clauses}))
    assert _wellformed(route("solve_cnf", {"clauses": clauses, "backend": "builtin"}))
