"""
v1 closure sweep C — PROOF tests for the V / Y / AB0 / AD / AE closure candidates.

Each test is the evidence behind a roadmap ✅: V0 recognize-or-refuse base, V1 seven-component
decomposition, V2 candidate formalizations A/B/C with machine-readable assumption deltas,
V3 formalization probes (known example / counterexample / boundary), Y2 reusable lessons,
AB0 complete axiom trace + replay, AD0 control surface (axiom ban / technique priority /
proof-style selection), AD1 auditable decision rationale, AD2 human-readable report + proof
rendering, AE1 the N/O/P/Q/R chain concretized in the graph domain, AE3 contract + provenance +
honest Lean export. (V4, AD3, AE2 stay open with one-line honest reasons in the roadmap —
no test pretends otherwise.)
"""
import importlib

import pytest

from mathhead.discovery.objects import Graph

N3_MINUS_N = (0, -1, 0, 1)          # n³ − n
N5_MINUS_N = (0, -1, 0, 0, 0, 1)    # n⁵ − n
N7_MINUS_N = (0, -1, 0, 0, 0, 0, 0, 1)  # n⁷ − n


# --- V0: the recognize-or-refuse base (interpret_natural) --------------------------------------

def test_v0_recognize_or_refuse_understands_restates_refuses_and_never_guesses():
    from mathhead.core.nl import interpret
    from mathhead.router import route

    # UNDERSTOOD: formal task + payload + round-trip restatement (confirm-then-trust)
    r = interpret("derivative of x**2 with respect to x")
    assert (r.status, r.reason_code) == ("ok", "UNDERSTOOD")
    assert r.interpretation["task"] == "differentiate"
    assert r.interpretation["payload"] == {"expression": "x**2", "symbol": "x", "order": 1}
    assert "derivative of 'x**2'" in r.interpretation["restatement"]

    # AMBIGUOUS: two distinct task readings → candidates surfaced, NO silent pick
    a = interpret("factorize 7 and is 7 prime")
    assert (a.status, a.reason_code) == ("unknown", "AMBIGUOUS")
    tasks = {c["task"] for c in a.interpretation["candidates"]}
    assert {"factorize", "is_prime"} <= tasks

    # UNRECOGNIZED: honest refusal, no interpretation fabricated
    bad = interpret("the meaning of life")
    assert (bad.status, bad.reason_code) == ("error", "UNRECOGNIZED")
    assert bad.interpretation is None
    assert (interpret("").status, interpret("").reason_code) == ("error", "PARSE_ERROR")

    # deterministic, and the SAME base is what the router task exposes (MathHead surface)
    r2 = interpret("derivative of x**2 with respect to x")
    assert (r2.status, r2.interpretation) == (r.status, r.interpretation)
    via_router = route("interpret_natural", {"text": "derivative of x**2 with respect to x"})
    assert via_router.interpretation == r.interpretation


# --- V1: seven-component decomposition, total over the engine's own corpus ---------------------

def test_v1_seven_components_are_total_and_honest_over_the_engine_corpus():
    from mathhead.discovery.conjecture_db import AH_SPECTRAL_MATCHING, CONJECTURES
    from mathhead.discovery.statement_parse import parse_statement

    for c in CONJECTURES.values():
        p = parse_statement(c.statement)
        assert p.quantifier == "universal"                       # niceleyici
        assert p.n_min in (2, 3)                                 # önkoşul (size precondition)
        assert p.basis == "finite graph theory"                  # temel
        assert p.implicit_assumptions == (                       # örtük-varsayım — made VISIBLE
            "finite", "simple (no loops / multi-edges)", "undirected")
        for _inv, ref in p.definitions:                          # tanım — resolvable, cannot drift
            mod, attr = ref.split(":")
            assert callable(getattr(importlib.import_module(mod), attr))

    # hedef — the claim triple splits ONLY at the unambiguous ':' separator …
    ah = parse_statement(AH_SPECTRAL_MATCHING.statement)
    assert ah.goal == ("lambda1 + mu", ">=", "sqrt(n-1) + 1")
    assert dict(ah.definitions)["matching number"] == \
        "mathhead.discovery.rich_invariants:matching_number"
    # … and refuses to split where a '>=' glyph sits in the PRECONDITION (n>=3), honestly
    ham = parse_statement("every connected graph on n>=3 vertices is Hamiltonian")
    assert ham.goal == ()

    # a bare relation (no quantifier prefix) splits losslessly: the triple reconstructs the text
    bare = parse_statement("num_triangles <= num_edges")
    assert bare.goal == ("num_triangles", "<=", "num_edges")
    assert " ".join(bare.goal) == bare.text

    # unrecognized input: all seven components stay empty/unknown and the input is REPORTED
    w = parse_statement("the weather tomorrow")
    assert w.unrecognized == ("the weather tomorrow",)
    assert (w.quantifier, w.domain, w.goal, w.basis) == ("unknown", "", (), "")
    assert w.definitions == () and w.implicit_assumptions == ()
    assert parse_statement(bare.text) == parse_statement(bare.text)   # deterministic


# --- V2: candidate formalizations A/B/C with machine-readable assumption deltas ----------------

def test_v2_candidate_formalizations_split_verdicts_and_list_assumption_deltas():
    from mathhead.discovery.formalize import candidate_formalizations, formalize

    # the quantifier ambiguity is REAL: the same relation text gets three honest verdicts
    r = formalize("num_vertices <= num_edges + 1", max_n=5, fixed_n=4)
    v = r["verdicts"]
    assert v["A"].verdict == "open"                       # true theorem on connected graphs
    assert v["A"].tier == "no_counterexample_within_bound"
    assert v["A"].structure == "graph_inequality"         # candidate A IS check()'s own envelope
    assert v["B"].verdict == "refuted"                    # drops connectivity → dies immediately
    assert v["B"].witness == {"n": 2, "edges": [], "num_vertices": 2, "num_edges": 0}
    assert not (2 <= 0 + 1)                               # independent recomputation of the witness
    assert v["C"].verdict == "refuted"                    # the empty graph of order 4 kills C too

    # the assumption difference is machine-readable: A adds exactly 'connected' over B
    d_ab = next(d for d in r["differences"] if d["pair"] == ("A", "B"))
    assert d_ab["only_first"] == ("connected",) and d_ab["only_second"] == ()
    d_ac = next(d for d in r["differences"] if d["pair"] == ("A", "C"))
    assert "connected" in d_ac["only_first"]
    assert d_ac["only_second"] == ("n == 4 (complete finite domain)",)

    # fixed-order C is genuinely DECIDABLE — and it carries its OWN honest tier (an exhaustion
    # proof over the complete finite domain, not a witness): triangles<=edges on order 4 …
    r2 = formalize("num_triangles <= num_edges", max_n=6, fixed_n=4)
    assert (r2["verdicts"]["C"].verdict, r2["verdicts"]["C"].tier) == \
        ("proved", "finite_domain_exhaustion")
    assert "exhaustion proof, not a witness" in r2["verdicts"]["C"].notes
    from mathhead.discovery.generate import generate_graphs
    from mathhead.discovery.invariants import evaluate
    order4 = generate_graphs(4)
    assert len(order4) == 11                              # OEIS A000088 — the domain is complete
    assert all(evaluate(g, "num_triangles") <= evaluate(g, "num_edges") for g in order4)
    # … while the unbounded readings are refuted (first witness at n=6) — same text, split verdict
    assert r2["verdicts"]["A"].verdict == "refuted" and r2["verdicts"]["A"].witness["n"] == 6

    # refusal, never guessing: non-graph text and unknown invariants raise
    with pytest.raises(ValueError):
        candidate_formalizations("the weather tomorrow")
    with pytest.raises(ValueError):
        candidate_formalizations("frobnitz <= num_edges")
    assert formalize("num_vertices <= num_edges + 1", max_n=5, fixed_n=4)["verdicts"]["B"].witness \
        == v["B"].witness                                  # deterministic


# --- V3: known example / counterexample / boundary probe each formalization correctly ----------

def test_v3_known_objects_correctly_refute_or_validate_each_formalization():
    from mathhead.discovery.formalize import candidate_formalizations, probe
    from mathhead.discovery.product import check

    a, b, c = candidate_formalizations("num_vertices <= num_edges + 1", max_n=5, fixed_n=4)
    e2 = Graph.from_edges(2, [])                     # KNOWN counterexample (two isolated vertices)
    p3 = Graph.from_edges(3, [(0, 1), (1, 2)])       # KNOWN example (a path)
    k2 = Graph.from_edges(2, [(0, 1)])               # BOUNDARY case (equality: 2 = 1 + 1)

    # the known counterexample refutes reading B — and is honestly OUT OF DOMAIN for reading A:
    # the recorded connectivity assumption shields A, which is exactly what V3 must surface
    assert probe(b, e2) == {"label": "B", "in_domain": True, "claim_holds": False}
    assert probe(a, e2) == {"label": "A", "in_domain": False, "claim_holds": None}
    # the known example validates both bounded readings
    assert probe(a, p3)["claim_holds"] is True and probe(b, p3)["claim_holds"] is True
    # the boundary case sits exactly on the bound (equality) and still validates
    assert probe(a, k2)["claim_holds"] is True
    assert k2.n == 2 and len(k2.edges) == 1          # 2 <= 1+1 — tight, recomputed independently
    # the fixed-order reading is only probed by objects of ITS order
    assert probe(c, e2)["in_domain"] is False and probe(c, p3)["in_domain"] is False

    # the same discipline at the product door: a known counterexample REFUTES (witness verified
    # outside the engine), a known example VALIDATES (kernel proof)
    bad = check("5 | n^3 - n")
    assert bad.verdict == "refuted" and bad.witness["n"] == 2
    assert (2 ** 3 - 2) % 5 == 1 != 0                # independent arithmetic: the witness is real
    good = check("6 | n^3 - n")
    assert (good.verdict, good.tier) == ("proved", "kernel_verified")


# --- Y2: reusable lessons from refuted conjectures — deterministic and honest ------------------

def test_y2_lessons_cluster_by_killing_witness_deterministically_and_honestly():
    from mathhead.discovery.failure_memory import FailureMemory

    w1 = {"n": 2, "edges": [(0, 1)]}
    w2 = {"n": 5, "edges": []}
    records = [
        ("num_edges <= num_triangles", {"counterexample": w1}),
        ("num_vertices <= num_edges", {"counterexample": w1}),      # same killer witness
        ("max_degree <= min_degree", {"counterexample": w2}),
    ]
    mem = FailureMemory()
    for stmt, detail in records:
        mem.record("refuted_conjecture", stmt, detail)
    mem.record("timeout", "R(3,6) <= 18", {"budget_s": 600})        # NOT a lesson source
    mem.record("dead_end", "induction on n for chi", {})            # NOT a lesson source

    lessons = mem.lessons()
    assert [le["refutes"] for le in lessons] == [2, 1]              # broadest refuter FIRST
    assert lessons[0]["statements"] == sorted(
        ["num_edges <= num_triangles", "num_vertices <= num_edges"])
    assert set(lessons[0]) == {"witness", "refutes", "statements"}  # no claim beyond the record
    assert all("R(3,6)" not in s for le in lessons for s in le["statements"])

    # order-independence: reversed insertion produces the IDENTICAL lesson list
    mem2 = FailureMemory()
    for stmt, detail in reversed(records):
        mem2.record("refuted_conjecture", stmt, detail)
    assert mem2.lessons() == lessons

    # idempotence: re-recording the same dead ends adds nothing and changes no lesson
    for stmt, detail in records:
        assert mem.seen("refuted_conjecture", stmt)
        mem.record("refuted_conjecture", stmt, detail)
    assert mem.lessons() == lessons


# --- AB0: the axiom trace is COMPLETE and replay-consistent ------------------------------------

def _expected_axioms(term):
    """Independent re-derivation of the axiom footprint (test-local walker, not provenance's)."""
    from mathhead.discovery.kernel import CRT, Residue
    if isinstance(term, Residue):
        return {f"RESIDUE(m={int(term.modulus)})"}
    if isinstance(term, CRT):
        out = {"CRT"}
        for part in term.parts:
            out |= _expected_axioms(part)
        return out
    raise AssertionError(f"unexpected term {term!r}")


def test_ab0_every_theorem_axiom_list_is_complete_and_replay_consistent():
    from mathhead.discovery.kernel import prove_divides
    from mathhead.discovery.provenance import axioms_used, proof_hash, replay

    battery = [(6, N3_MINUS_N), (30, N5_MINUS_N), (42, N7_MINUS_N), (2, (0, 1, 1))]
    for m, poly in battery:
        thm, term = prove_divides(m, poly)
        # completeness: the traced axiom set equals an INDEPENDENT walk of the proof term —
        # every RESIDUE leaf and every CRT composition, nothing hidden, nothing invented
        assert axioms_used(term) == frozenset(_expected_axioms(term))
        # replay: re-running the kernel mints the SAME theorem; the artifact hash is stable
        assert replay(term) == thm
        h = proof_hash(term)
        assert h == proof_hash(term) and len(h) == 16
        assert all(ch in "0123456789abcdef" for ch in h)

    # composite moduli really exercise the composed trace (CRT + one RESIDUE per prime power)
    _thm, term30 = prove_divides(30, N5_MINUS_N)
    assert axioms_used(term30) == frozenset(
        {"CRT", "RESIDUE(m=2)", "RESIDUE(m=3)", "RESIDUE(m=5)"})

    # and the pipeline carries the same trace: every kernel-verified arithmetic finding names
    # its axioms (M5 provenance), never an empty or foreign list
    from mathhead.discovery.arithmetic import run_arithmetic_discovery
    kernel_findings = [f for f in run_arithmetic_discovery() if f.kernel_verified]
    assert kernel_findings
    for f in kernel_findings:
        assert f.axioms and all(a == "CRT" or a.startswith("RESIDUE(m=") for a in f.axioms)


# --- AD0: the control surface — ban an axiom, prioritize, pick a proof style -------------------

def test_ad0_control_surface_bans_axioms_prioritizes_and_selects_proof_style():
    from mathhead.discovery.axiom_minimize import candidate_proofs, proof_avoiding
    from mathhead.discovery.portfolio import run_portfolio
    from mathhead.discovery.technique_map import suggest_techniques
    from mathhead.profiles import ALWAYS, PACKS

    # BAN an axiom: the surface honors the ban and NEVER fabricates an alternative
    assert proof_avoiding(6, N3_MINUS_N, {"CRT"}).axioms == ("RESIDUE(m=6)",)
    crt = proof_avoiding(6, N3_MINUS_N, {"RESIDUE(m=6)"})
    assert crt.strategy == "crt-prime-powers"
    assert crt.axioms == ("CRT", "RESIDUE(m=2)", "RESIDUE(m=3)")
    assert proof_avoiding(6, N3_MINUS_N, {"RESIDUE(m=6)", "CRT"}) is None
    assert proof_avoiding(5, N3_MINUS_N, set()) is None       # false claim: no ban mints a proof

    # SELECT a proof style: both kernel-checked styles are enumerable by name — the caller picks
    styles = {p.strategy for p in candidate_proofs(30, N5_MINUS_N)}
    assert styles == {"direct-residue", "crt-prime-powers"}

    # PRIORITIZE a technique: the map lists strongest-first; the budget steers the portfolio
    techs = suggest_techniques("6 | n^3 - n")
    assert techs and techs[0][1] == "kernel.prove_divides"     # strongest instrument first
    run = run_portfolio(30, N5_MINUS_N, budget=13)             # affords CRT (13), not direct (30)
    assert run.winner == "crt-prime-powers" and run.spent <= run.budget
    assert [o.outcome for o in run.outcomes if o.name == "direct-residue"] == ["skipped"]

    # the MathHead profile base (♻️): capability packs + always-on triage tools exist
    assert {"core", "logic", "symbolic", "numerical", "frontier", "observability"} <= set(PACKS)
    assert "recommend_tool" in ALWAYS


# --- AD1: the decision rationale is auditable — recomputable from its own inputs ---------------

def test_ad1_decision_rationale_is_auditable_and_recomputable():
    from mathhead.discovery.director import ResearchDirector
    from mathhead.discovery.lemma_ranking import RankedLemma

    d = ResearchDirector()
    pick = RankedLemma("c1", "num_triangles <= num_edges", 1.0, 0.25, 0.625)
    cases = [
        ([pick], {}, "settle"),
        ([], {"EMPIRICALLY_VALIDATED": 5, "FORMALLY_PROVED": 2}, "raise"),
        ([], {"EMPIRICALLY_VALIDATED": 2, "FORMALLY_PROVED": 5}, "widen"),
    ]
    for ranked, ladder, expected_branch in cases:
        goal, rat = d._decide(ranked, ladder)
        assert rat["branch"] == expected_branch
        # the rationale is RECOMPUTABLE: re-derive the branch from the recorded inputs alone
        ins = rat["inputs"]
        rederived = ("settle" if ins["open_goals_ranked"] > 0 else
                     "raise" if ins["empirically_validated"] > ins["formally_proved"] else "widen")
        assert rederived == rat["branch"]
        assert d._select_next_goal(ranked, ladder) == goal      # one policy, two views

    # settle branch: the priority arithmetic in the rationale is checkable to the digit
    _goal, rat = d._decide([pick], {})
    ins = rat["inputs"]
    assert abs(ins["top_priority"]
               - (0.5 * ins["top_importance"] + 0.5 * ins["top_likelihood"])) < 1e-3
    assert "0.5·importance(1.0)" in rat["because"] and "not learned" in rat["policy"]

    # live cycle: the recorded rationale explains the goal the director actually adopted
    live = ResearchDirector().run_cycle(max_n=3)
    assert live.rationale["branch"] in ("settle", "raise", "widen")
    prefix = {"settle": "settle open conjecture:", "raise": "raise validated laws",
              "widen": "widen the sample bound"}[live.rationale["branch"]]
    assert live.next_goal.startswith(prefix)

    # the portfolio's decision is equally auditable: the winner is justified by the cost ledger
    from mathhead.discovery.portfolio import run_portfolio
    run = run_portfolio(30, N5_MINUS_N, budget=100)
    proved = [o for o in run.outcomes if o.outcome == "proved"]
    assert run.winner == min(proved, key=lambda o: (o.cost, o.name)).name
    assert run.spent == sum(o.cost for o in run.outcomes if o.launched) <= run.budget


# --- AD2: human-readable proof + research report ------------------------------------------------

def test_ad2_report_and_proof_rendering_are_complete_and_deterministic():
    from mathhead.discovery.arithmetic import run_arithmetic_discovery
    from mathhead.discovery.report import render, render_rich_status, run_report

    rep = run_report(max_n=4)
    text = render(rep)
    for heading in ("# MathHead — Discovery Run Report", "## PROVED", "## REFUTED",
                    "## DISCOVERED", "## OPEN", "## FRONTIER", "## EXPLANATIONS",
                    "## HONEST SCORECARD"):
        assert heading in text
    # EVERY finding statement appears verbatim — the report hides nothing
    for bucket in (rep.proved, rep.refuted, rep.empirical_laws, rep.open_bounded):
        for item in bucket:
            assert item["statement"] in text
    assert render(rep) == text                                   # deterministic rendering

    # the human-readable PROOF view: labelled provenance lines for a kernel-proved finding
    finding = next(f for f in run_arithmetic_discovery() if f.kernel_verified)
    block = render_rich_status(finding)
    for label in ("STATUS:", "FOUNDATION:", "DEPENDENCIES:", "KERNEL:", "PROOF_HASH:",
                  "INDEPENDENT_CHECKER:"):
        assert label in block
    assert "theorem minted (LCF-checked proof term)" in block
    assert finding.proof_hash in block


# --- AE1: N/O/P/Q/R concretized in the graph domain — one chain, every track -------------------

def _raw_invariant(g, name):
    """RAW re-computation from (n, edges) alone — deliberately no engine call, so the Q-step
    witness check below is genuinely outside the engine."""
    from itertools import combinations
    edges = {tuple(sorted(e)) for e in g.edges}
    deg = {v: 0 for v in range(g.n)}
    for u, v in edges:
        deg[u] += 1
        deg[v] += 1
    if name == "num_vertices":
        return g.n
    if name == "num_edges":
        return len(edges)
    if name == "sum_degrees":
        return sum(deg.values())
    if name == "max_degree":
        return max(deg.values(), default=0)
    if name == "min_degree":
        return min(deg.values(), default=0)
    if name == "num_triangles":
        return sum(1 for a, b, c in combinations(range(g.n), 3)
                   if {(a, b), (b, c), (a, c)} <= edges)
    if name == "num_components":
        parent = list(range(g.n))

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        for u, v in edges:
            parent[find(u)] = find(v)
        return len({find(v) for v in range(g.n)})
    raise AssertionError(f"raw evaluator does not cover {name!r}")


def test_ae1_n_o_p_q_r_chain_is_concrete_in_the_graph_domain():
    # N — object generation: every isomorphism class, pinned to OEIS A000088
    from mathhead.discovery.families import cycle
    from mathhead.discovery.generate import generate_graphs
    sample = [g for n in range(4) for g in generate_graphs(n)]
    assert [len(generate_graphs(n)) for n in range(5)] == [1, 1, 2, 4, 11]
    c5 = cycle(5)

    # O — invariant evaluation, exact
    from mathhead.discovery.invariants import evaluate
    assert evaluate(c5, "num_edges") == 5 and evaluate(c5, "chromatic_number") == 3

    # P — conjecture generation from the sample (inequalities that hold on small graphs)
    from mathhead.discovery.conjectures import bound_conjectures
    conjectures = bound_conjectures(sample)
    assert conjectures and all(" <= " in c.statement for c in conjectures)

    # Q — counterexample-first refutation with a MINIMAL witness; EVERY witness re-verified by
    # the raw evaluator above (no engine call — genuinely outside the engine)
    from mathhead.discovery.refute import refute
    results = [(c, refute(c, max_n=5)) for c in conjectures]
    killed = [(c, r) for c, r in results if r.status == "refuted"]
    survivors = [r for _c, r in results if r.status == "no_counterexample_within_bound"]
    assert killed and survivors
    for c0, r0 in killed:
        a, b = c0.statement.split(" <= ")
        assert _raw_invariant(r0.counterexample, a) > _raw_invariant(r0.counterexample, b)

    # R — honest status + certificate: a survivor is NEVER proved, and a constructive
    # certificate is exhibited and re-checked outside the certifier
    assert all(r.status == "no_counterexample_within_bound" for r in survivors)
    from mathhead.discovery.graph_proofs import certify_chi_le_delta_plus_1
    cert = certify_chi_le_delta_plus_1(c5)
    assert cert.checked and cert.certainty == "constructive_bounded"
    coloring = cert.witness["coloring"]
    assert all(coloring[u] != coloring[v] for (u, v) in c5.edges)            # proper — recomputed
    assert cert.witness["colors_used"] <= _raw_invariant(c5, "max_degree") + 1


# --- AE3: output contract + provenance + Lean export (honestly pending-external) ---------------

def test_ae3_lean_export_is_written_deterministic_and_honestly_pending(tmp_path):
    from mathhead.discovery.arithmetic import run_arithmetic_discovery
    from mathhead.discovery.lean_export import export_kernel_theorems

    out = tmp_path / "MathheadKernel.lean"
    ex = export_kernel_theorems(str(out))
    assert out.exists()
    # the theorem count is exactly the kernel-proved arithmetic facts + the 2 identities
    proved = [f for f in run_arithmetic_discovery() if f.verdict == "proved"]
    assert ex.theorems == len(proved) + 2

    # HONESTY is the contract: the export NEVER claims verification before the external build
    assert ex.status == "export_written_pending_external_check"
    assert "No theorem is claimed Lean-verified" in ex.note
    text = out.read_text(encoding="utf-8")
    assert "TO VERIFY (external step, NOT yet run)" in text
    assert "export_written_pending_external_check" in text
    assert "decide" in text and "ZMod" in text                  # the RESIDUE ≡ decide bridge
    assert text.count("theorem mathhead_") == ex.theorems

    # deterministic: a second export is byte-identical (reproducible artifact contract)
    out2 = tmp_path / "Again.lean"
    ex2 = export_kernel_theorems(str(out2))
    assert ex2.theorems == ex.theorems
    assert out2.read_text(encoding="utf-8") == text

    # provenance contract carried by the findings the export is built from
    for f in proved:
        if f.kernel_verified:
            assert len(f.proof_hash) == 16 and f.axioms
