# Discovery Engine — Progress log

> WHAT we did, WHEN, WHY — append-only, newest on top. The subproject that follows
> `docs/IDEAL-ENGINE-ROADMAP.md`. Rationale of design choices goes to
> `docs/discovery/DECISIONS.md`.

---

## 2026-07-29 — Factorizations that EXPLAIN the divisibilities (third kernel judgment: PolyIdentity)

A genuinely mathematical increment — the engine now explains WHY, not just THAT. Kernel gained a third
judgment `PolyIdentity` (p(n) = q(n) ∀n, via the `Identity` rule: p − q ≡ 0 — sound & complete). New
`identities.py` factors each polynomial and INDEPENDENTLY certifies the factorization with the kernel
(expand(p) must equal expand(factored) — it does not trust sympy.factor; a wrong factorization fails
the check).

The payoff is explanatory and ties threads together: when the factors are CONSECUTIVE integers, the
product is divisible by k!. So the engine reports `n³ − n = n(n−1)(n+1)` explains `6 | n³−n` (three
consecutive integers ⇒ divisible by 3! = 6) — the algebraic STRUCTURE explaining the modular NUMBER
found separately in arithmetic.py. Both kernel-checked. Report gains an EXPLANATIONS section and the
factorization identities enter PROVED (certainty `kernel_identity`); POLY_IDENTITY joins the axiom
manifest.

9 tests (6 identities + 2 kernel + 1 report; discovery suite 190); full suite **1479 green**, ruff
clean. ADR-D0029. Roadmap: algebraic-identity surface + M1 (third judgment).

**Next:** more explanatory links (why a bound is tight; why a law holds structurally), or a new domain,
or external-corpus novelty (X1/W2).

---

## 2026-07-29 — Impact analysis (Track X3): load-bearing axioms, hubs, the open frontier

New `impact.py` runs structural "so what?" analysis over the knowledge graph — all exact graph
computations, no guessing. `load_bearing_axioms` ranks inference rules by how many theorems depend on
them (RESIDUE(m=2) supports 6 proofs, CRT 5 — the leverage points: break one and many results move);
`most_connected` finds the hubs; `open_frontier` ranks OPEN conjectures by how entangled
(`related_to`) they are with known results — the highest-impact statements to settle next. The report
header now shows the most load-bearing axiom; `meta.impact` carries the full picture.

Honest scope: this is impact WITHIN the engine's own knowledge — descriptive centrality/leverage.
Saying "this settles conjecture C from the literature" needs external open-problem ingestion (X1/W2),
still open. 4 tests (discovery suite 181); full suite **1470 green**, ruff clean. ADR-D0028. Roadmap X3.

**Next:** ingest an external corpus for real novelty checks (X1/W2), or wire failure-memory into the
loop, or push a new domain surface.

---

## 2026-07-29 — Knowledge graph (Track X0): findings become a typed semantic graph

Findings stopped being a flat list. New `knowledge_graph.py`: a typed graph where nodes are
theorems / laws / conjectures / counterexamples / axioms and edges are typed relations. `from_report`
populates it, asserting only edges the engine can be CERTAIN of — `depends_on` (theorem → the kernel
axioms it rests on), `refuted_by` (conjecture → its counterexample witness), and symmetric
`related_to` (two statements sharing an invariant). On the report: ~48 nodes, ~123 edges (11
theorems, 7 axioms, 6 laws, 20 conjectures, 4 counterexamples).

Deliberately NOT fabricated: `generalizes`/`equivalent_to` edges — those need real entailment checks
(a judged pass, later X3), so the schema reserves the relations but the populator doesn't guess them
(tested). Ships a deterministic Mermaid export for visualization. The report header now shows the
graph summary; `meta.knowledge_graph` carries the counts.

9 tests (8 knowledge_graph + 1 report; discovery suite 177); full suite **1466 green**, ruff clean.
ADR-D0027. Roadmap X0. This is the substrate X3 (impact analysis) and W2 (novelty-vs-literature) run
over.

**Next:** impact analysis (X3 — which open problem would a result touch), or wire failure-memory into
the refute loop, or a new domain surface (AE — generate a genuinely new small lemma).

---

## 2026-07-29 — Interestingness ranking (Track W1): rank findings, transparently

The engine can now RANK what it found, not just list it. New `interestingness.py` scores each finding
by the document's components — novelty · generality · surprise · usefulness · compression ·
connectivity − triviality — each a named, deterministic proxy computed from the finding and its peers,
combined with documented (hand-set) weights into a [0,1] score that carries its full per-component
breakdown, so a ranking is always explainable.

On the real report it behaves sensibly: strong universal facts (composite modulus, kernel-verified —
n³−n mod 6, n⁵−n mod 30) top the list; the handshake lemma ranks high; the textbook-trivial χ≤n bound
sinks to 0.0 (low novelty + triviality penalty). The report gained a MOST INTERESTING section (top 5)
and `meta.most_interesting`.

HONEST framing, in the module and the report header: this is a HEURISTIC, not a learned or
ground-truth measure — a learned interestingness model with human feedback is Track W3 and stays OPEN.
It ranks and explains; it never decides what is true.

9 tests (8 interestingness + 1 report; discovery suite 169); full suite **1457 green**, ruff clean.
ADR-D0026. Roadmap W1.

**Next:** the knowledge-graph schema (X0 — store findings + relations: generalizes/refutes/equivalent),
or wire failure-memory `seen` into the refute loop, or a new domain surface.

---

## 2026-07-29 — Negative knowledge (Track Y): the engine remembers its dead ends

A discovery engine that forgets its failures re-walks them. New `failure_memory.py`: every closed
branch — a refuted conjecture, a timeout, a useless lemma, a dead-end transform (Y0) — is recorded
under a canonical FINGERPRINT (Y1: whitespace-normalized, kind-aware content hash), so `seen(...)`
lets the loop skip a dead end it already walked, and `record` is idempotent. `lessons()` distills
REUSABLE lessons (Y2): it clusters refuted conjectures by the WITNESS that killed them — a witness
that refutes many conjectures is a high-value probe to try FIRST on new look-alikes.

Wired into the report: the refutations feed a `FailureMemory`; the header now shows
`negative knowledge: N dead end(s) recorded` (and the top witness when it refutes more than one).
`populate_from_refutations` accepts both dict and dataclass refutation results and returns how many
NEW dead ends were learned (repeats skipped — the whole point). Pure/deterministic; not part of the
trust base (it's an efficiency-and-memory layer beside the judge).

8 tests (7 failure_memory + 1 report; discovery suite 160); full suite **1448 green**, ruff clean.
ADR-D0025. Roadmap Y0/Y1/Y2.

**Next:** interestingness scoring (Track W1 — rank findings by novelty/generality/surprise/…), or the
knowledge-graph schema (X0), or wire failure-memory `seen` into the refute loop to actually skip.

---

## 2026-07-29 — Kernel fragment widened: a second judgment (SUM identities), sequences now kernel-verified

The kernel grew from one judgment to two. `Theorem` now carries a `kind`: `Divides` (RESIDUE/CRT, as
before, with `modulus`/`poly` kept as backward-compatible accessors) and the new `SumIdentity`
(∀n≥1, Σf(i)=g(n)). New rule `SumInduction`: verify base g(1)=f(1) AND that the telescoping step
g(n)−g(n−1)−f(n) is the ZERO polynomial — sound and complete for polynomial sums. It needed RATIONAL
polynomial arithmetic (Fraction), since closed forms like n(n+1)/2 aren't integer — added exact
`_norm_q`/`_poly_sub_q`/`_poly_shift_back_q` and a `poly_from_sympy_q` bridge; the Divides fragment
stays integer (RESIDUE is only sound over ℤ).

Wired into `sequences.py`: all four polynomial sum identities (Σi=n(n+1)/2, Σi², Σi³, Σ(2i−1)=n²) are
now BOTH independently verified AND `kernel_verified` (axiom SUM_INDUCTION, with proof hash); the
non-polynomial Σ2^i stays refuted (no kernel proof). The report surfaces them the same way —
SAMPLE-REPORT.md now has 11 kernel-verified facts (7 modular + 4 sums) and SUM_INDUCTION in the axiom
manifest. The two judgments don't mix: CRT rejects a SumIdentity premise (tested).

11 tests (5 kernel + 1 sequences new; discovery suite 152); full suite **1440 green**, ruff clean.
ADR-D0024. Roadmap M1 (fragment widened).

**Next:** widen further (derive RESIDUE from ring/induction primitives — the deeper kernel), or open a
new track: AC1 (wire the full 16-step loop) or a fresh domain surface.

---

## 2026-07-29 — Proof provenance, hashing & replay (M4/M5): every theorem shows its axioms

The kernel proofs became auditable artifacts. New `provenance.py`: `axioms_used(term)` lists the
EXACT rules/primitives a theorem rests on (M5 — e.g. n⁵−n mod 30 → {CRT, RESIDUE(m=2), RESIDUE(m=3),
RESIDUE(m=5)}); `proof_hash(term)` is a deterministic, order-independent, kernel-versioned content
hash (M4 — same proof ⇒ same hash across processes, a version bump invalidates it); `replay(term)`
re-runs the kernel for byte-for-byte reproducibility.

Wired through: each `ArithmeticFinding` now carries `proof_hash` + `axioms`; the report prints
`⊢ kernel-verified [<hash>]` per fact and a kernel-axiom manifest in the header (`kernel v1.0 ·
axioms: CRT, RESIDUE(m=2), …, RESIDUE(m=8)`). Honest touch: n(n+1)(n+2)(n+3) mod 24 openly shows it
leaned on RESIDUE(m=8) (24 = 8·3) — nothing about the derivation is hidden. SAMPLE-REPORT.md
regenerated (7 hashed, axiom-listed proofs).

9 tests (7 provenance + 2 arithmetic; discovery suite 146); full suite **1434 green**, ruff clean.
ADR-D0023. Roadmap M4/M5.

**Next:** widen the kernel fragment (a rule class for the sum identities, or derive RESIDUE from more
primitive steps), or open a new track — the closed-loop connector (AC1), or the next domain surface.

---

## 2026-07-29 — Kernel wired into the arithmetic pipeline: every modular proof is `kernel_verified`

The kernel stopped being standalone. `discover_and_prove` now, for every proved modular finding,
converts the polynomial (`kernel.poly_from_sympy` — the optional sympy bridge, kept out of the
stdlib core), emits a proof TERM via `prove_divides`, and lets the LCF kernel mint the Theorem —
recording `kernel_verified` on the finding. All 7 family laws (n(n+1)…, n³−n mod 6, n⁵−n mod 30,
n⁷−n mod 42) are now BOTH `independently_verified` (checker.py, the M3 second checker) AND
`kernel_verified` (M1/M2). The report surfaces `⊢ kernel-verified` beside `✓ independently verified`;
SAMPLE-REPORT.md regenerated (7 kernel-verified facts).

Why this is stronger than the old flag: `kernel_verified` is proof-CARRYING — a false claim would
raise inside the kernel (the residue sweep fails, the guarded constructor blocks fabrication), so the
Theorem's mere existence is the evidence. Two independent confirmations now stand behind each modular
fact: the orthogonal residue re-check AND the kernel's rule-checked term.

2 net new tests (discovery suite 137); full suite **1426 green**, ruff clean. Extends ADR-D0022.

**Next:** widen the kernel fragment (e.g. derive RESIDUE from more primitive rules, or add a rule
class for the sum identities), or push into a new track — proof replay / axiom-provenance (M4/M5),
or the next domain surface.

---

## 2026-07-29 — A real PROOF KERNEL (M1/M2): theorems exist only if a proof term checks

The deepest step yet toward the "ideal engine" thesis (§1, the trustworthy kernel). New `kernel.py`
is a minimal LCF-style proof kernel: a `Theorem` can be created ONLY by the kernel's inference rules
— its constructor is guarded (`Theorem(...)` raises; only the module-private `_mint` builds one), so
every Theorem in the system is, by construction, the output of a checked rule.

Fragment (honest scope): judgments `Divides(m, p)` = "∀n∈ℤ, m | p(n)" for integer polynomials p, two
rules — RESIDUE (exhaust residues 0..m−1; a complete, sound decision procedure for the atomic
judgment) and CRT (compose pairwise-coprime moduli about the same p). A separate, UNTRUSTED prover
(`prove_divides`) factors m into prime powers, builds the term, and hands it to the kernel — the
Theorem is only as good as the kernel check.

What the tests pin down: valid proofs mint theorems (6|n³−n, 30|n⁵−n); a FALSE claim is rejected and
no theorem escapes (4∤n²+1); theorems can't be forged (`Theorem()` raises); CRT enforces its
side-conditions (rejects non-coprime moduli and mismatched polynomials); non-integer coefficients and
unknown terms are rejected; the kernel is order-independent.

TRUST BASE stated plainly in the module: sound IF the residue sweep and the CRT rule are sound (a few
auditable lines). RESIDUE is the trusted primitive — NOT yet derived from ring/induction axioms
(later M-track). Stdlib-only core, like the independent checker.

10 tests (discovery suite 135); full suite green, ruff clean. ADR-D0022. Roadmap M1/M2.

**Next:** bridge the kernel into the arithmetic pipeline — proved modular findings emit a
kernel-checked proof term and earn a new `kernel_verified` status (stronger than
`independently_verified`), with `checker.py` as the independent second checker (M3) cross-checking
the kernel.

---

## 2026-07-29 — Certificates surfaced in the report (OPEN coloring laws now show "certified")

Closed the loop from the previous increment: the report's OPEN coloring laws now carry their
constructive-certificate status. `report._frontier_laws` runs `certify_frontier_laws(...,
solver_confirm=False)` (structural fast path — keeps the report deterministic and solver-call-free)
and annotates the three certified laws (χ≤Δ+1, χ≤n, ω≤χ) with "constructively certified over the
sample (constructive_bounded)" plus a `certified=True` flag. Hamiltonicity implications (no
certificate) stay unmarked. Certified still means OPEN — never PROVED. `solver_confirm` threaded
through `certify_frontier_laws` so module tests keep the MathHead double-check while the report skips
it. 1 net new report test (discovery suite 125); full suite **1414 green**, ruff clean. Extends
ADR-D0020/D0021.

---

## 2026-07-29 — First step from "discover + refute" to "discover + PROVE" (graph domain)

The surviving coloring laws were OPEN — "the inequality held on the sample," nothing more. New
`graph_proofs.py` upgrades three of them from *observed* to *constructively certified*: the engine
now CONSTRUCTS an explicit witness realizing each bound and an independent checker re-validates it on
every graph (156 certificates up to n≤6, 0 check failures):

- `χ ≤ Δ+1` — a GREEDY (first-fit) proper coloring, re-checked proper AND ≤ Δ+1 colors (never
  exceeded Δ+1 on any graph).
- `χ ≤ n`   — the identity (all-distinct) coloring, trivially proper.
- `ω ≤ χ`   — a maximum CLIQUE, its lower bound DOUBLE-confirmed by MathHead (the clique K_ω is not
  (ω−1)-colorable → `graph_coloring` unsat). Two authorities again.

The independent checker rejects fakes (tested): a monochromatic "coloring" of K4 and a fake K4 inside
P4 both fail the re-check — M-spirit, don't trust the constructor.

HONEST STATUS — deliberately NOT overclaimed. Each certificate is `constructive_bounded`: an
explicit, re-checked witness over graphs up to the bound — strictly stronger than `bounded_check`,
but NOT a universal ∀G proof. The universal argument (greedy always fits; a clique forces its size)
is RECORDED on each certificate, but machine-verifying it needs the logic/proof-term kernel (Track
M1/M2, 🟡, unstarted). So these stay OPEN epistemically; what's new is that we now hold the
constructive certificate, not just the observation. No fake PROVED.

9 tests (discovery suite 124); full suite **1413 green**, ruff clean. ADR-D0021. Roadmap R1 (first
slice: constructive graph certificates).

**Next:** wire the certificates into the report (annotate the OPEN coloring laws "constructively
certified over the sample"), or push toward the kernel (M1) that would let a universal step be
checked — the real bridge OPEN → PROVED for graphs.

---

## 2026-07-29 — Frontier work folded into the flagship report (χ + Hamiltonicity now visible)

Two increments added frontier modules (χ, Hamiltonicity) that the run report didn't show — the
flagship artifact had drifted behind the engine's real reach. Closed that gap. `report.py` now:

- mines the frontier LAWS (coloring bounds + Hamiltonicity implications) into the honest epistemic
  buckets — survivors (ω≤χ≤Δ+1, Dirac, the necessary conditions) → OPEN (`bounded_check`), the
  killed ones (χ≤Δ, connected⟹Hamiltonian) → REFUTED with their counterexamples;
- adds a new FRONTIER section exercising the two-authority check IN the report: representative
  NP-hard invariant VALUES — χ(K4)=4, χ(K3)=3, Hamiltonicity of C5 / P4 — each independently
  confirmed by MathHead's solver (`solver_verified`), distinct from the bounded_check laws.

Kept the epistemic taxonomy pure: the frontier LAWS take their honest status (OPEN/REFUTED); only
the invariant VALUES are `solver_verified`. Honest placement of Dirac: OPEN, not PROVED — the engine
rediscovered the STATEMENT and failed to refute it on n≤5, but has NOT proven it. SAMPLE-REPORT.md
regenerated (now carries the FRONTIER section).

2 net new report tests (discovery suite 115); full suite **1404 green**, ruff clean. ADR-D0020.

**Next:** a third frontier invariant, or start proving the surviving frontier laws (lift Dirac /
the sandwich from OPEN toward PROVED with a real argument).

---

## 2026-07-29 — Second frontier invariant: Hamiltonian cycles + Dirac's theorem rediscovered

The graph→frontier bridge widened to a second NP-complete invariant. New `hamiltonicity.py`:
`is_hamiltonian(g)` (Hamiltonian cycle?) is decided locally by backtracking, then INDEPENDENTLY
CONFIRMED by MathHead's `hamiltonian_path(cycle=True)` — `sat` ⟺ Hamiltonian. All 53 graphs up to
n≤5 agree between the two engines (0 mismatches); n<3 is a convention edge case handled locally.

The engine mined the Hamiltonicity implications and REDISCOVERED **Dirac's theorem** from data
(`n≥3 ∧ δ ≥ n/2 ⟹ Hamiltonian`, survives, support 7) alongside the necessary conditions
(`Hamiltonian ⟹ connected`, `⟹ δ≥2`). It REFUTED `connected ⟹ Hamiltonian` with the minimal
STRUCTURAL witness — the 3-path P₃ (connected, no cycle). I scoped that claim to n≥3 on purpose so
the witness is structural, not the n<3 convention artifact — a deliberate honesty call (contrast the
coloring increment, where the degenerate K1 witness WAS the honest minimal one).

Bridge note: `hamiltonian_path` is 0-indexed (unlike `graph_coloring`), so no vertex shift here.

8 new tests (discovery suite 113); full suite **1402 green**, ruff clean. ADR-D0019. Roadmap O1.

**Next:** a third frontier invariant, or fold the frontier confirmations (χ, Hamiltonicity) into the
run report as first-class `solver_verified` provenance.

---

## 2026-07-29 — Graph domain reaches the SAT/UNSAT FRONTIER: chromatic number, two authorities

The graph domain crossed from exact-arithmetic invariants into the NP-hard frontier — and did it
with a double check. New `coloring.py`: χ(g) is computed exactly by backtracking (an ordinary
invariant, `chromatic_number` / `clique_number` now in the registry), then INDEPENDENTLY CONFIRMED
by MathHead's `graph_coloring` frontier tool — `sat` at χ colors AND `unsat` at χ−1 (an
impossibility proof). Our backtracking and MathHead's Z3 reduction are orthogonal authorities; both
agreeing is the "don't trust one prover" principle applied to a genuinely NP-hard invariant. Every
graph up to n≤5 has its χ confirmed this way; χ≤1 (edgeless) is trivial and skips the solver.

It also mines the classic coloring sandwich `ω ≤ χ ≤ Δ+1` (all survive the sample) and REFUTES
`χ ≤ Δ`. Honest surprise: refute-first reports the MINIMAL witness — not the textbook triangle
(χ=3 vs Δ=2) but the single vertex (χ=1 vs Δ=0), which breaks it more minimally. The engine found
a smaller counterexample than the human default; the test now records that (exact `bounded_check`,
not proven-for-all). Bridge quirk handled: `graph_coloring` is 1-indexed, so vertices shift +1 and
`n` is passed explicitly (isolated vertices counted).

9 new tests (discovery suite 105); full suite **1394 green**, ruff clean. ADR-D0018. Roadmap: O1
frontier-bridge slice + coloring invariants.

**Next:** more frontier invariants (independence number via `subset`/SAT, Hamiltonicity), or fold
`verify_chromatic_number` provenance into the report.

---

## 2026-07-29 — Independent verification extended to the sum-identity proofs

Closed the gap: now EVERY proved fact in the report is independently verified, not just the modular
ones. New `checker.check_sum_identity` re-verifies a sum identity Σf(i)=g(n) independently of the
MathHead proof — the base case plus the step g(n)−g(n−1)=f(n) as a COMPLETE polynomial-identity
check (evaluate at deg+2 points; a degree-D polynomial vanishing at D+1 points is identically zero).

`Σi = n(n+1)/2`, `Σi² = …`, `Σi³ = (n(n+1)/2)²`, `Σ(2i−1) = n²` are all now
`independently_verified=True`; the refuted `Σ2^i` is `False`. The report shows `✓ independently
verified` on every proved item across both proof families. 1 test (discovery suite 96); full suite
1385 green, ruff clean. Extends ADR-D0016/D0017.

---

## 2026-07-29 — Independent verification is now first-class: every proof is re-checked

The checker isn't optional anymore. `discover_and_prove` now runs `check_proof(proof_tree(finding),
fn)` on every proved fact and records `independently_verified` on the finding; the report surfaces
it (`✓ independently verified`).

So every proved arithmetic fact in the engine is confirmed by a checker independent of the prover —
the CRT reasoning is structurally re-checked, the claims re-verified by the complete residue method.
Trust shifted from "the strategy said so" to "an independent checker confirmed it", visible in the
report. A proof the checker couldn't confirm would ship as `independently_verified=False` (loud),
never silently. 2 tests; full suite 1384 green, ruff clean. ADR-D0017.

**Next:** extend independent verification to the sum-identity proofs, or more surface — the pipeline
absorbs it.

---

## 2026-07-29 — Independent proof checker (M spirit): don't trust the prover, check the proof

The document's #1 principle, in a tractable form. New `checker.py` re-verifies a proof tree by an
orthogonal, minimal, stdlib-only method — and rejects anything it can't confirm.

- A modular claim `p(n) ≡ 0 (mod m)` is re-checked at every residue mod m — COMPLETE, and
  independent of HOW the proof was found (even an induction/Z3 proof is re-verified this way).
- A CRT node is checked for its REASONING too: prime-power moduli pairwise coprime, product = m,
  every lemma checks out.

It confirms the real proofs (n³−n mod 6 via CRT structure + residues; n⁵−n mod 30 via residues) and
REJECTS both a false claim (n²+1 ≡ 0 mod 4) and broken CRT reasoning (children mod 2·3 but goal mod
12). A buggy prover can no longer pass off a wrong theorem — the strongest honest status
(`independently_verified`). Scoped to the modular class where the check is complete. 5 new tests
(discovery suite 93); full suite 1382 green, ruff clean. ADR-D0016 (M1–M3 spirit).

---

## 2026-07-29 — Proof-dependency trees (T3 slice): make a proof's lemmas explicit

A small, budget-measured step into lemma discovery. New `proof_tree.py`: reconstruct a proved
finding's dependency tree from the winning strategy — no extra solver calls, deterministic.

```
(n**3 - n) % 6 == 0   [CRT, formal_proof]  — coprime prime-power lemmas combined by CRT
    (n**3 - n) % 2 == 0   [induction, formal_proof]
    (n**3 - n) % 3 == 0   [induction, formal_proof]

(n**5 - n) % 30 == 0  [residue-exhaustion, exhaustive_residue_proof]  — all 30 residues checked
```

So a proof is now legible as a tree of the lemmas it rests on. Honest scope: this does NOT invent
lemmas (the 🔴 open part of T) — it surfaces the ones an existing proof already uses, checkably.
Deliberately small (one module, no new solver load) to stay inside the weekly budget. 4 new tests
(discovery suite 88); full suite 1377 green, ruff clean. ADR-D0015. Roadmap T3.

---

## 2026-07-29 — Proof portfolio (S1) with a COMPLETE fallback: residue exhaustion

Turned the modular prover into a small portfolio, and gave it a complete fallback so it stops
leaving true facts as `unknown`.

**Done — `strategy.py::prove_by_residues`:** a COMPLETE decision procedure for `p(n) ≡ 0 (mod m)`
over all integers — for an integer-coefficient polynomial, p(n) mod m depends only on n mod m, so
checking all m residues is a rigorous finite case-split (a real proof). The arithmetic loop now
tries the elegant MathHead proofs first (induction → factoring+CRT) and falls back to residue
exhaustion, recording the winning method.

**Result — every modular law now PROVED, each by the right strategy:**
- `induction`: n(n+1) ≡ 0 mod 2, n²−n ≡ 0 mod 2
- `modulus-factoring` (CRT): n(n+1)(n+2) ≡ 0 mod 6, n³−n ≡ 0 mod 6
- `residue-exhaustion` (complete): n(n+1)(n+2)(n+3) ≡ 0 mod 24, n⁵−n ≡ 0 mod 30, n⁷−n ≡ 0 mod 42

Honest note: the earlier `unknown`s were a weakness of one method, not a real wall — this class is
decidable and the engine now decides it (certainty `exhaustive_residue_proof` for the case-split,
`formal_proof` for the induction/CRT proofs). The genuine walls remain (graph laws →
`not_applicable`, truly open problems → `unknown`). 2 tests updated + residue-completeness test;
full suite 1373 green, ruff clean. ADR-D0014. Roadmap S1 (portfolio).

**Next:** a heavier track (lemma discovery T / a real proof kernel M), or more discovery surface —
the portfolio and the four report buckets absorb it.

---

## 2026-07-29 — Spectral bounds (numerical) + a more robust modular prover

Extended the spectral thread to real-valued BOUNDS, and hardened the modular prover.

**Done — new `spectral_bounds.py`:** the spectral radius (largest eigenvalue, from MathHead)
evaluated numerically; candidate bounds checked counterexample-first and labeled honestly
`certainty="numerical_check"` (not a proof). The engine found the classic sandwich
**average_degree ≤ spectral_radius ≤ max_degree** (survives) and REFUTED the plausible
`spectral_radius ≤ average_degree` — a single edge on 3 vertices breaks it (λ=1 > ⅔). Exact
symbolic eigenvalue comparison was unreliable (SymPy's complex-radical forms won't order), so we
went numeric — and kept it OUT of the default report (per-graph eigenvalue cost).

**Robustness fix:** the modular prover was unified — `discover_and_prove` now always routes
through `prove_modular_divisibility` (prime m = one induction; composite = factor + CRT) with a
reliable 2500 ms budget, removing a flaky direct-then-fallback race that occasionally dropped
`n³−n mod 6` back to unknown under load. Run ~10 s, verdicts stable. ADR-D0013.

3 new tests (discovery suite 82); full suite 1372 green, ruff clean.

**Next:** more surface into the four buckets, or start a heavier track (lemma discovery T / a real
proof kernel M) — the pipeline stays orderly either way.

---

## 2026-07-29 — Interestingness (W0): keep subclass-specific laws, drop restricted-universals

A first filter against the "a machine can emit a million trivially-true statements" problem. New
`novelty.py`: a subclass law is INTERESTING only if it is specific to that subclass — i.e. its
claim FAILS somewhere in the full sample — not a universal law merely restricted to it.

**What it cleaned up:**
- Dropped `trees: 2*num_edges = sum_degrees` and the forests version — these are just the Handshake
  Lemma seen on a subclass (they hold on EVERY graph), no discovery about trees/forests.
- Kept the genuine characterizations: `trees: num_edges = num_vertices − 1`, `trees: triangle-free`,
  `forests: num_vertices = num_edges + num_components`.

Wired into `run_report`, so the DISCOVERED section is now higher-signal. 2 new tests (discovery
suite 79); full suite 1369 green, ruff clean. ADR-D0012. A tractable first step on the
interestingness problem the document flags as central — without pretending it is "solved".

**Next:** more interestingness (dedup equivalent laws, flag trivial bounds) or more discovery
surface — all into the same four report buckets.

---

## 2026-07-29 — Proof strategy (S): factor the modulus → prove parts → CRT — proving what one induction couldn't

The judge now has more than one route. New `strategy.py`: `prove_modular_divisibility` factors m
(MathHead `factorize`), proves each prime power by induction, and combines coprime successes by CRT.
The arithmetic loop tries a single induction first, then falls back to this strategy.

**What it upgraded (real new proofs):**
- `n³ − n ≡ 0 (mod 6)` and `n(n+1)(n+2) ≡ 0 (mod 6)` — each `unknown` under one induction — are now
  **PROVED** via 2·3 + CRT (`certainty=formal_proof`, `method=modulus-factoring`). The report's
  PROVED arithmetic facts went 2 → 4.
- The still-hard ones (`n⁵−n mod 30`, `n⁷−n mod 42`, the mod-24 case) stay honestly `unknown` — now
  the strategy NAMES the blocking prime power (e.g. the mod-3 step of n⁵−n) instead of a bare wall.

Timing kept safe (judge budget 1500 ms, memoized run ~14 s). 4 new tests (discovery suite 77);
full suite 1367 green, ruff clean. ADR-D0011. First step of the proof-strategy orchestrator (S).

**Next:** more routes in the portfolio (e.g. prove a product-of-consecutives fact by the "one of k
consecutive is divisible by k" argument) or more surface — all into the same four report buckets.

---

## 2026-07-29 — Sum identities: discover the formula from data, prove it by induction (2nd arithmetic generator)

A second arithmetic generator, and a richer discover→prove loop: the engine finds a SUM's closed
form from data and MathHead proves it.

**Done — new `sequences.py`:** for a term f(i), compute partial sums, **fit** a closed-form
polynomial g(n) by interpolation (P4 "guess the formula"), **refute** counterexample-first over a
larger range, then **prove** by induction — base case + MathHead verifying the step
g(n) − g(n−1) = f(n).

**What it found and proved, autonomously:**
- `Σ i = n(n+1)/2`, `Σ i² = n(2n²+3n+1)/6`, `Σ i³ = (n(n+1)/2)²`, `Σ (2i−1) = n²`
  — all **proved** (`solver_verified`, MathHead did the algebraic step).
- `Σ 2^i` (not polynomial): the fit matches the sample but diverges beyond it → **refuted**, not
  forced. The engine doesn't invent a formula where none exists.

Wired into `run_report` — the new generator feeds the same four honest buckets (PROVED / REFUTED /
DISCOVERED / OPEN) without reshaping the pipeline, exactly as claimed. 4 new tests (discovery
suite 73); full suite 1363 green, ruff clean. ADR-D0010. Roadmap P4 done.

**Next:** more of the same into the same buckets — spectral bounds, or mining relations among
named sequences (Fibonacci/Catalan) — the pipeline absorbs it.

---

## 2026-07-29 — Spectral invariants: the graph domain's first bridge to MathHead

The graph domain now flows through MathHead's compute spine for the first time — spectral graph
theory, discovered from data and confirmed by MathHead's eigenvalues.

**Done — new `spectral.py` + spectral moments in `invariants.py`:**
- Spectral moments Σλ², Σλ³ as fast exact invariants (= trace(A²), trace(A³) by integer matmul),
  registered but kept OUT of the default `NUMERIC_INVARIANTS` so existing miners are undisturbed.
- The actual spectrum via **MathHead's `eigenvalues`** tool (memoized per graph) → `spectrum`,
  `num_distinct_eigenvalues`, and `spectrum_confirms_moments` (MathHead as independent authority).

**What the engine discovered (real spectral graph theory, from data):**
- **Σλ² = 2·num_edges** and **Σλ³ = 6·num_triangles** (`discover_spectral_laws`).
- MathHead's actual eigenvalues independently CONFIRM those moments on every graph n≤5 — the
  cross-check the whole product is built for (three ways agree: matmul trace, MathHead spectrum,
  structural count).

**Fix on the way:** symbolic `simplify` of Σλ³ (irrational cubes) blew the 30 s test timeout;
switched to a 40-digit numeric evaluation + round (the sum is provably an integer = trace), and
took Re() to drop numerical noise. Spectral test ~1.5 s. 5 new tests (discovery suite 69); full
suite 1359 green, ruff clean. ADR-D0009. Roadmap O1 (spectral) done.

**Next:** more surface into the same four report buckets — a second arithmetic generator, or
spectral bounds (e.g. spectral radius vs max degree) — without reshaping the pipeline.

---

## 2026-07-29 — AC2: one honest run report — consolidation, not sprawl

Tied the two domains into a single organized artifact. New `report.py`: `run_report()` runs the
whole pipeline (graphs + arithmetic) and assembles a `DiscoveryReport` with four honest sections,
and `render()` emits Markdown with provenance (version/seed/bounds/determinism). Deterministic.

The current run (graphs n≤6) at a glance:
- **PROVED (2):** `n(n+1) ≡ 0 mod 2`, `n²−n ≡ 0 mod 2` (formal_proof).
- **REFUTED (1):** `num_triangles ≤ num_edges` (minimal counterexample T=16 > E=14, n=6).
- **DISCOVERED (8, empirical):** the Handshake Lemma + the tree/forest laws.
- **OPEN (15):** graph bounds that survived + arithmetic facts the judge left `unknown`
  (`n³−n ≡ 0 mod 6`, `n⁵−n ≡ 0 mod 30`, …) — discovered, unproven, honestly labeled.

Every item sits in exactly one bucket by its true status; nothing blurred. This is the
consolidation that keeps growth ORDERLY — future domains feed the same four honest buckets rather
than scattering. A rendered sample lives at `docs/discovery/SAMPLE-REPORT.md`. 5 new tests
(discovery suite 64); full suite 1354 green, ruff clean. ADR-D0008.

**Next:** more surface into the same buckets — widen the arithmetic family or add a spectral graph
invariant routed through MathHead — the report absorbs it without reshaping.

---

## 2026-07-29 — Arithmetic domain: the loop CLOSES — generate → refute → PROVE, autonomously

The first fully autonomous loop with a real proof at the end. New `arithmetic.py`: for a family
of polynomials p(n) the engine discovers the modulus from data (`m = gcd(p(1),p(2),…)`), refutes
counterexample-first, then hands the survivor to MathHead's induction judge.

**What the engine found and did, on its own:**
- Discovered the moduli from data: n(n+1)→2, n(n+1)(n+2)→6, ×4→24, n²−n→2, **n³−n→6** (stronger
  than the textbook "mod 3"), **n⁵−n→30** (stronger than Fermat's mod 5), n⁷−n→42.
- PROVED by induction the ones MathHead can decide: `n(n+1) ≡ 0 (mod 2)`, `n²−n ≡ 0 (mod 2)` →
  `certainty=formal_proof`.
- Honest `unknown` (never faked) on the higher-degree steps beyond Z3's reach.
- Killed overshoot claims (e.g. n(n+1) ≡ 0 mod 4) with a minimal counterexample before the judge.

**Speed/honesty:** the induction proof runs under a small `timeout_ms` budget (a smaller budget
just yields `unknown` sooner — the bound is a budget, not a lie); the full run is memoized. The
test file dropped from ~102 s to ~11 s. 6 new tests (discovery suite 59); full suite 1349 green,
ruff clean. ADR-D0007.

**This is the thesis, end to end:** discover, try to kill, prove what can be proved, and say
`unknown` out loud for the rest.

**Next:** widen the arithmetic family / add a second generator (e.g. mine relations among integer
sequences), or return to graphs and add a spectral invariant routed through MathHead — either way,
more surface for the same honest loop.

---

## 2026-07-29 — R: the judge bridge — MathHead actually proves/refutes (first real judge use)

The survivors from Q were `no_counterexample_within_bound` — not proven. Now the judge reaches
real verdicts.

**Done — new `judge.py`:** bridges the discovery layer to `mathhead.router.route`, mapping a
MathHead result to a `Verdict` (proved | refuted | unknown | not_applicable) that carries
MathHead's own `certainty`. Semantic helpers: `judge_induction`, `judge_inequality`,
`judge_identity`, `judge_entailment`, `judge_task`; plus `judge(conjecture)` that uses an
optional `mathhead` task on a Conjecture. ADR-D0006.

**The judge genuinely works:**
- `n(n+1)` even and `n³ − n ≡ 0 (mod 3)` → **proved by induction**, `certainty=formal_proof`.
- AM-GM `x² + y² ≥ 2xy` → **proved**, `certainty=solver_verified` (Z3).
- `x² ≥ x` (false over the reals) → **refuted**, with MathHead's witness `x = 0.5`.
- a graph law (`min_degree ≤ max_degree`, no `mathhead` task) → **`not_applicable`** — honest, not
  a fabricated verdict.

So `empirical → proved / refuted` happens only where MathHead's grammar truly reaches; the
combinatorial laws stay honestly out of scope. 6 new tests (discovery suite 53); full suite
green, ruff clean. The bridge is ready.

**Next:** an arithmetic / integer-sequence object domain — so the discovery loop AUTO-GENERATES
conjectures the judge can prove, closing generate → refute-first → PROVE end to end in a domain
where MathHead is the native judge.

---

## 2026-07-29 — P0 + Q0: conjecture generation + counterexample-first — the engine's character

The engine now GENERATES candidate laws and, by default, tries to KILL them before believing —
the "counterexample-first" stance. This is where discovery stops being bookkeeping.

**Done — new `conjectures.py` (P0) + `refute.py` (Q0):**
- **`subclass_laws`** — mine O2 laws on a predicate-defined subclass. On **trees** the engine
  rediscovers classic theorems from data: `num_triangles = 0`, `num_edges = num_vertices - 1`;
  on **forests** the correct weaker `num_vertices = num_edges + num_components` (NOT E=V-1). Added
  structural `is_forest`/`is_tree` invariants (cycle detection, not the E=V-C formula — no
  circularity).
- **`bound_conjectures`** — propose non-trivial inequalities `A <= B` holding on the sample.
- **`refute`** (counterexample-first, Q0 + minimal-CE Q4): bounded scan returning the MINIMAL
  counterexample or an honest `no_counterexample_within_bound` — never "proved".

**The character moment (the milestone):** from graphs with n<=5 the engine proposes 11 plausible
bounds (all true on <=5 vertices); a bounded attack up to n=6 then **kills exactly one** —
`num_triangles <= num_edges`, with the minimal counterexample **T=16 > E=14** on 6 vertices (K6
minus an edge) — while the other 10 survive as bounded-honest. True theorems (`trees: E=V-1`,
`trees: triangle-free`) survive.

**Fixes on the way (recorded honestly):** the refute loop was regenerating the n<=6 graph set
per conjecture (~38 s > the 30 s test timeout; the timeout's traceback even crashed pytest's
renderer). Fixed by **memoizing generation by n** (deterministic) + switching stored predicates
from lambdas to named closures. Full loop now ~3.6 s.

**Honesty (ADR-D0005):** survivors are `no_counterexample_within_bound`, the handoff to the judge
(R). The judge (MathHead) is deliberately NOT wired for graph theorems — it isn't the right tool
there; it enters for the algebraically-reducible survivors. 8 new tests (discovery suite 47);
full suite 1337 green, ruff clean.

**Next:** R — take a survivor that IS expressible in MathHead's grammar (or move a sub-demo to a
number-theory domain) and let the judge actually PROVE it — the first real use of MathHead as the
discovery engine's judge.

---

## 2026-07-29 — O2: automatic relation discovery — the engine rediscovers the Handshake Lemma

First real *discovery*: the engine finds a true theorem from data (not hardcoded).

**Done — new `relations.py` (Track O2):**
- **`discover_linear_laws`** — builds the affine feature matrix over the numeric invariants and
  reports the exact linear laws (integer null space, sympy rationals) holding across the whole
  sample. Each is a `DiscoveredLaw` with **`status="empirical"`** (a conjecture, not a theorem)
  + `holds_over` / `support`. ADR-D0004.
- **`discover_constants`** — invariants constant across a sample (e.g. `num_vertices=4` over all
  graphs on 4 vertices).
- Added `sum_degrees` as a numeric invariant + `NUMERIC_INVARIANTS` (the miner's columns) —
  deliberately NOT hardcoding `sum_degrees = 2E`; the engine must find it.

**Milestone (the O2 gate):** over all graphs with n ≤ 5 (53 objects) AND n ≤ 6 (209 objects),
the miner returns **exactly one** universal law — `2*num_edges = sum_degrees`, the **Handshake
Lemma** — with no spurious relations. As A000088 pinned generation, this pins discovery.

**Honesty:** the law ships as `empirical` (holds over the sample), never as "proved". That is
the handoff to the next tracks: a conjecture for the counterexample-first track (Q) to attack,
then the judge (R) to prove. 6 new tests; discovery suite now 39; full suite green, ruff clean.

**Next on the critical path:** P0/P1 — conjecture generation (bounds/inequalities, subclass laws
via mutation) → then **Q**, where MathHead becomes the judge that attacks each conjecture.

---

## 2026-07-29 — First stone: N0 + N2 + N1 + O0/O1 (the "matter" layer)

Kicked off the discovery engine — the layer that will (later) generate conjectures and hunt
counterexamples, using MathHead as its judge. Started exactly on the roadmap's v0.1 domain
(finite graphs) and its critical path, small but real, fully tested.

**Done — new `mathhead.discovery` package (`src/mathhead/discovery/`):**
- **N0 `objects.py`** — typed object model behind a minimal `MathObject` base; first type is the
  immutable, hashable finite simple `Graph` (explicit `n` so isolated vertices survive).
- **N2 `canonical.py`** — isomorphism elimination via a degree-refined permutation-minimum
  canonical key (correct, not just degree sequence — distinguishes C6 from 2·C3). ADR-D0002.
- **N1 `generate.py`** — canonical non-isomorphic generation, honest-bounded at n ≤ 7 (no silent
  cap), pinned to **OEIS A000088**. ADR-D0003.
- **O0/O1 `invariants.py`** — exact, deterministic graph invariants (edges, degree sequence,
  triangles, components, connectivity...) + a named registry and feature-vector accessor (O3-lite).

**Verification (the correctness gate):**
- `count_non_isomorphic(n)` reproduces **A000088 exactly for n = 0..6: 1, 1, 2, 4, 11, 34, 156**
  (n=6 in ~3.2 s) — an independent oracle for both generation and canonical labeling.
- Hard iso case handled: **C6 vs 2·C3** (same degree sequence, non-isomorphic) correctly
  separated — proves the canonical form goes beyond the degree sequence.
- **33 discovery tests green, ruff clean.** No MathHead code touched (additive subpackage).

**Deliberately NOT done yet (honest):** the judge (MathHead verify/counterexample/certificate)
is not wired in — it belongs at the refutation/proof tracks (Q/R), not the object layer.
Orderly/McKay generation (to pass n=7) and nauty-style canonicalization are logged as planned
N1/N2 optimizations, not needed for correctness now.

**Next on the critical path:** O2 (automatic invariant discovery) → P0/P1 (conjecture generation
from the invariant feature tables) → Q (counterexample-first, where MathHead becomes the judge).
