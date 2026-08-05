"""Discovery AA0/AA1/AA2 — the FunSearch skeleton: DSL, evolution, conjecture → kernel proof."""
from mathhead.discovery.program_search import (
    conjecture_and_prove,
    evaluate_program,
    evolve,
    fitness,
    render,
)


def test_dsl_evaluator_and_guards():
    assert evaluate_program(("*", "n", ("+", "n", 1)), 4) == 20
    assert evaluate_program(("//", 1, ("-", "n", "n")), 5) is None      # safe division: None, no crash
    assert render(("//", ("*", "n", ("+", "n", 1)), 2)) == "((n * (n + 1)) // 2)"


def test_exact_fitness_no_floats():
    tri = (1, 3, 6, 10, 15)
    assert fitness(("//", ("*", "n", ("+", "n", 1)), 2), tri, offset=1) == 5
    assert fitness("n", tri, offset=1) == 1                             # only n=1 matches


def test_evolution_rediscovers_squares_and_triangular():
    sq = tuple(n * n for n in range(1, 13))
    assert evolve(sq, "squares", seed=0, offset=1).status == "program_found_empirical"
    tri = tuple(n * (n + 1) // 2 for n in range(1, 13))
    f = evolve(tri, "triangular", seed=0, offset=1)
    assert f.status == "program_found_empirical" and f.matched == 12


def test_full_loop_program_to_kernel_proof():
    # AA1 finds a program for Σi; AA2 hands the closed form to the KERNEL — independent agreement
    cp = conjecture_and_prove((0, 1))                                   # summand f(i) = i
    assert cp.status == "kernel_verified" and cp.proof_hash             # SumInduction, hashed


def test_honest_not_found_is_reported():
    cp = conjecture_and_prove((0, 0, 1))                                # Σi² — beyond this budget/DSL
    assert cp.status in {"not_found_within_budget", "kernel_verified"}
    if cp.status == "not_found_within_budget":
        assert cp.proof_hash == ""                                      # no proof claimed


def test_evolution_is_deterministic():
    tri = tuple(n * (n + 1) // 2 for n in range(1, 13))
    a, b = evolve(tri, seed=3, offset=1), evolve(tri, seed=3, offset=1)
    assert (a.rendered, a.status, a.matched) == (b.rendered, b.status, b.matched)
