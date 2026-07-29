"""Discovery Track R — the judge bridge: MathHead actually proves/refutes discovery conjectures."""
from mathhead.discovery import (
    Conjecture,
    judge,
    judge_identity,
    judge_induction,
    judge_inequality,
)


def test_judge_proves_by_induction():
    v = judge_induction("(n*(n+1)) % 2 == 0")          # n(n+1) is always even
    assert v.status == "proved" and v.certainty == "formal_proof"

    v3 = judge_induction("(n**3 - n) % 3 == 0")         # n^3 - n divisible by 3
    assert v3.status == "proved" and v3.certainty == "formal_proof"


def test_judge_proves_inequality_via_solver():
    v = judge_inequality("x**2 + y**2 >= 2*x*y")        # AM-GM
    assert v.status == "proved" and v.certainty == "solver_verified"


def test_judge_refutes_with_a_counterexample():
    v = judge_inequality("x**2 >= x")                   # false over the reals (0 < x < 1)
    assert v.status == "refuted"
    assert "counterexample" in v.detail                 # MathHead hands back a witness


def test_judge_proves_identity():
    v = judge_identity("(x+1)**2", "x**2 + 2*x + 1")
    assert v.status == "proved"


def test_judge_is_honest_not_applicable_for_combinatorial_conjectures():
    # a graph law (no `mathhead` task) is NOT expressible in the algebraic judge's grammar
    graph_conj = Conjecture(
        kind="inequality", statement="min_degree <= max_degree",
        scope=lambda g: True, claim=lambda g: True,
    )
    v = judge(graph_conj)
    assert v.status == "not_applicable"                 # honest, not a fabricated verdict


def test_judge_dispatches_a_conjecture_with_a_mathhead_task():
    # a conjecture annotated with how MathHead judges it gets a real verdict
    conj = Conjecture(
        kind="arithmetic", statement="n(n+1) even",
        scope=lambda g: True, claim=lambda g: True,
        mathhead={"task": "prove_by_induction",
                  "payload": {"claim": "(n*(n+1)) % 2 == 0", "var": "n", "start": 0}},
    )
    v = judge(conj)
    assert v.status == "proved" and v.certainty == "formal_proof"
