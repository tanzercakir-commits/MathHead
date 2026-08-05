"""
v4F3 hardening sweep A — PROOF tests for the M/Q/R/S/N/O closure candidates.

Each test is the evidence behind a roadmap ✅ (or documents the honest coverage behind a 🟢 that
stays partial): M0 judge↔kernel interface coherence, M1 closed proof-term language, M2 exhaustive
rule side-conditions, M3 independent-checker coverage of all three judgments (method wing),
M5 axiom manifest + dependency graph, M7 rich status block, S0 strategy ledger, S2 portfolio
ledger accounting, S3 the S→Y failure loop end-to-end.
"""
from fractions import Fraction

import pytest

from mathhead.discovery import checker, kernel
from mathhead.discovery.kernel import (
    CRT, Identity, KernelError, Residue, SumInduction, Theorem, check,
)

N3_MINUS_N = (0, -1, 0, 1)          # n³ − n
N5_MINUS_N = (0, -1, 0, 0, 0, 1)    # n⁵ − n


# --- M0: the judge envelope is the kernel interface — findings carry it coherently -------------

def test_m0_findings_carry_the_kernel_interface_coherently():
    from mathhead.discovery.arithmetic import run_arithmetic_discovery
    findings = run_arithmetic_discovery()
    assert findings, "the arithmetic pipeline must produce findings"
    for f in findings:
        if f.kernel_verified:                       # a minted theorem ⇒ full provenance, no gaps
            assert f.verdict == "proved"
            assert len(f.proof_hash) == 16 and all(c in "0123456789abcdef" for c in f.proof_hash)
            assert f.axioms and all(a.startswith(("RESIDUE", "CRT")) for a in f.axioms)
        if f.verdict != "proved":                   # no proof ⇒ no kernel claims leak through
            assert not f.kernel_verified and f.proof_hash == "" and f.axioms == ()


# --- M1: the proof-term language is CLOSED — exactly four terms, nothing else mints ------------

def test_m1_proof_term_language_is_closed():
    # the four designed terms each mint exactly their judgment kind
    assert check(Residue(6, N3_MINUS_N)).kind == "Divides"
    assert check(CRT((Residue(2, N3_MINUS_N), Residue(3, N3_MINUS_N)))).kind == "Divides"
    assert check(SumInduction((0, 1), (0, Fraction(1, 2), Fraction(1, 2)))).kind == "SumIdentity"
    assert check(Identity((1, 2, 1), (1, 2, 1, 0))).kind == "PolyIdentity"

    class Impostor:                                 # duck-typed fake with a Residue's attributes
        modulus, poly = 6, N3_MINUS_N

    for bad in (Impostor(), 42, "Residue(6, ...)", None):
        with pytest.raises(KernelError):
            check(bad)
    with pytest.raises(PermissionError):            # the LCF guard: no direct Theorem construction
        Theorem("Divides", (6, N3_MINUS_N))


# --- M2: every rule's side-condition is enforced — no malformed term mints a Theorem -----------

def test_m2_every_rule_side_condition_is_enforced():
    cases = [
        Residue(0, N3_MINUS_N),                          # modulus < 1
        Residue(2, (Fraction(1, 2),)),                   # non-integer coefficients
        Residue(4, (1, 0, 1)),                           # false claim: 4 ∤ n²+1 (residue sweep)
        CRT(()),                                         # no premises
        CRT((Residue(2, (0,)), Residue(4, (0,)))),       # non-coprime moduli (gcd 2)
        CRT((Residue(2, (0, 2)), Residue(3, (0, 3)))),   # premises about DIFFERENT polynomials
        CRT((SumInduction((0, 1), (0, Fraction(1, 2), Fraction(1, 2))),)),  # wrong judgment kind
        SumInduction((0, 1), (1, 0, Fraction(1, 2))),    # base case g(1)=3/2 ≠ f(1)=1
        SumInduction((0, 1), (0, 0, 1)),                 # step g(n)−g(n−1)−f(n) = n−1 ≢ 0
        Identity((0, 1), (0, 2)),                        # n ≠ 2n
        Residue(6, (float("nan"),)),                     # junk coefficient: NaN
        Residue("six", N3_MINUS_N),                      # junk modulus: a word, not an int
        SumInduction(("junk", 1), (0, 1)),               # junk coefficient: a string
        Identity((None,), (0,)),                         # junk coefficient: None
    ]
    for term in cases:
        with pytest.raises(KernelError):                 # total: junk wraps to KernelError,
            check(term)                                  # never a foreign TypeError/ValueError


# --- M3 (method wing): the independent checker covers all THREE kernel judgment kinds ----------

def test_m3_independent_checker_covers_all_three_judgments():
    import sympy
    n = sympy.Symbol("n")
    # Divides — complete residue re-check, orthogonal to the prover
    assert checker.independently_verify(lambda k: k**3 - k, 6)
    assert not checker.independently_verify(lambda k: k * k + 1, 4)
    # SumIdentity — base + step re-checked by exact evaluation
    assert checker.check_sum_identity(lambda k: k, n * (n + 1) / 2)
    assert not checker.check_sum_identity(lambda k: k, n**2)
    # PolyIdentity — point-evaluation (kernel subtracts coefficients; the checker evaluates)
    assert checker.check_poly_identity((1, 2, 1), (1, 2, 1, 0))
    assert not checker.check_poly_identity((1, 2, 1), (1, 2, 2))
    # agreement with the kernel on the same pairs (cross-validation, not shared code)
    kernel.prove_identity((1, 2, 1), (1, 2, 1, 0))
    with pytest.raises(KernelError):
        kernel.prove_identity((1, 2, 1), (1, 2, 2))


# --- M5: full axiom list + dependent-theorem graph --------------------------------------------

def test_m5_axiom_manifest_and_dependency_graph():
    from mathhead.discovery.provenance import axioms_used

    _, term = kernel.prove_divides(30, N5_MINUS_N)
    assert axioms_used(term) == frozenset(
        {"RESIDUE(m=2)", "RESIDUE(m=3)", "RESIDUE(m=5)", "CRT"})   # nothing hidden, nothing extra
    sum_term = SumInduction((0, 1), (0, Fraction(1, 2), Fraction(1, 2)))
    assert axioms_used(sum_term) == frozenset({"SUM_INDUCTION"})
    assert axioms_used(Identity((0, 1), (0, 1))) == frozenset({"POLY_IDENTITY"})

    # the dependent-theorem graph: a CRT-proved finding rests on one lemma per prime power
    from mathhead.discovery.arithmetic import run_arithmetic_discovery
    from mathhead.discovery.proof_tree import proof_tree
    crt_findings = [f for f in run_arithmetic_discovery()
                    if f.verdict == "proved" and f.method == "modulus-factoring"]
    assert crt_findings, "at least one CRT-proved finding expected"
    for f in crt_findings:
        tree = proof_tree(f)
        assert tree.method == "CRT" and len(tree.children) >= 2
        moduli = [int(c.claim.split("%")[1].split("==")[0]) for c in tree.children]
        prod = 1
        for m in moduli:
            prod *= m
        assert prod == f.modulus                    # the lemmas exactly compose the goal


# --- M7: the rich status block — all six fields, honest in both directions ---------------------

def test_m7_rich_status_has_all_six_fields_and_is_honest():
    from mathhead.discovery.arithmetic import ArithmeticFinding, run_arithmetic_discovery
    from mathhead.discovery.report import render_rich_status, rich_status

    proved = next(f for f in run_arithmetic_discovery()
                  if f.kernel_verified and f.method == "modulus-factoring")
    rs = rich_status(proved)
    assert list(rs) == ["STATUS", "FOUNDATION", "DEPENDENCIES", "KERNEL", "PROOF_HASH",
                        "INDEPENDENT_CHECKER"]
    assert rs["STATUS"] == "proved" and rs["PROOF_HASH"] == proved.proof_hash
    assert rs["FOUNDATION"] == list(proved.axioms)
    assert len(rs["DEPENDENCIES"]) >= 2              # one lemma claim per prime power
    leaf = next(f for f in run_arithmetic_discovery()
                if f.kernel_verified and f.method != "modulus-factoring")
    assert rich_status(leaf)["DEPENDENCIES"]         # a leaf proof still states what it rests on
    assert "theorem minted" in rs["KERNEL"] and "passed" in rs["INDEPENDENT_CHECKER"]
    text = render_rich_status(proved)
    for label in rs:
        assert f"{label}: " in text

    unproved = ArithmeticFinding("n**2 + 1", 4, "(n**2 + 1) % 4 == 0",
                                 "refuted", "refuted", "unknown", 60)
    ru = rich_status(unproved)
    assert ru["STATUS"] == "refuted" and ru["PROOF_HASH"] == "(none)"
    assert ru["FOUNDATION"] == ["(no kernel proof)"]
    assert "NOT kernel-verified" in ru["KERNEL"] and ru["INDEPENDENT_CHECKER"] == "not confirmed"


# --- S0: the strategy ledger resolves, and is honest about what is missing ---------------------

def test_s0_strategy_ledger_resolves_and_is_honest():
    from mathhead.discovery import strategy_registry as sr

    summary = sr.validate()                          # unique names + every implemented ref imports
    assert summary["implemented"] >= 12 and summary["missing"] >= 6
    names = {e.name for e in sr.REGISTRY}
    assert {"induction", "residue-exhaustion", "crt-factoring", "sat-encoding",
            "simulated-annealing", "interval-arithmetic"} <= {e.name for e in sr.implemented()}
    assert {"mcts", "resolution", "groebner-basis", "learned-guidance"} <= {
        e.name for e in sr.missing()}                # the ledger records absences, never inflates
    assert len(names) == len(sr.REGISTRY)
    assert callable(sr.resolve(next(e for e in sr.implemented() if e.name == "induction")))
    with pytest.raises(ValueError):
        sr.resolve(next(e for e in sr.missing()))


# --- S2: the portfolio ledger accounts for every strategy under every budget -------------------

def test_s2_portfolio_ledger_accounting_is_exact():
    from mathhead.discovery.portfolio import run_portfolio

    for budget in range(0, 50, 7):                  # true claim: 30 | n⁵−n
        run = run_portfolio(30, N5_MINUS_N, budget)
        launched_cost = sum(o.cost for o in run.outcomes if o.launched)
        assert run.spent == launched_cost <= run.budget == budget
        assert sorted(o.name for o in run.outcomes) == sorted(
            {o.name for o in run.outcomes})          # each strategy ledgered exactly once
        for o in run.outcomes:
            assert o.launched == (o.outcome != "skipped")
        if run.winner:
            assert run.status == "solved"
        elif any(o.launched for o in run.outcomes):
            assert run.status == "unsolved"
        else:
            assert run.status == "exhausted"
    assert run_portfolio(4, (1, 0, 1), 10).status == "unsolved"    # false claim: honest, not hidden
    assert run_portfolio(4, (1, 0, 1), 3).status == "exhausted"    # budget too small: says so
    with pytest.raises(ValueError):                                # negative budget: caller error,
        run_portfolio(30, N5_MINUS_N, -1)                          # never silently clamped


# --- S3: the S→Y loop end-to-end — failures accumulate, successes and repeats do not -----------

def test_s3_failure_loop_end_to_end():
    from mathhead.discovery.failure_memory import FailureMemory
    from mathhead.discovery.portfolio import run_portfolio
    from mathhead.discovery.strategy_log import log_and_diagnose

    memory = FailureMemory()
    runs = [run_portfolio(4, (1, 0, 1), 3),          # exhausted → timeout record
            run_portfolio(4, (1, 0, 1), 10),         # unsolved  → dead_end record
            run_portfolio(6, N3_MINUS_N, 100)]       # solved    → NOT recorded
    labels = ["4 | n^2+1 (tight)", "4 | n^2+1", "6 | n^3-n"]
    diag = log_and_diagnose(memory, runs, labels)
    assert (diag.runs, diag.solved, diag.unsolved, diag.exhausted) == (3, 1, 1, 1)
    kinds = sorted(r.kind for r in memory.records())
    assert kinds == ["dead_end", "timeout"]          # exactly the two failures, success excluded
    assert memory.seen("timeout", "portfolio failed on: 4 | n^2+1 (tight)")
    before = len(memory.records())
    log_and_diagnose(memory, runs, labels)           # re-logging the same dead ends
    assert len(memory.records()) == before           # …adds nothing (fingerprint dedup)
