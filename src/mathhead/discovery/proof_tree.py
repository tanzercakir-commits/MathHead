"""
mathhead.discovery.proof_tree — expose the STRUCTURE of a proof (roadmap T3, a tractable slice).

A proof is not a yes/no; it rests on lemmas. This module reconstructs the proof-dependency tree of
an arithmetic finding from the strategy that proved it — no extra solver calls, deterministic:

  * modulus-factoring → the goal rests on one `≡ 0 (mod pᵢ^{eᵢ})` lemma per prime power (each proved
    by induction), combined by CRT;
  * residue-exhaustion → a single complete finite case-split (leaf);
  * induction (prime modulus) → a single inductive proof (leaf).

This is the honest first step of intermediate-lemma discovery (T): it does not invent lemmas
(the open 🔴 part), it makes the lemmas an existing proof already uses explicit and checkable.

COVERAGE INVENTORY (v4F6). Not every proved/certified finding kind has a lemma tree, and that is a
STRUCTURAL fact, not an omission: a constructive bijection or a solver witness is a point-checked
certificate with no intermediate lemmas; a DRUP refutation is a linear clause derivation, not a
tree. `PROOF_TREE_COVERAGE` records, for every proved/certified certainty the engine emits — the
discovery report's proved/certified labels AND the instrument tiers (check() door, SAT/Ramsey,
spectral, interval) — either a resolvable tree builder ("module:callable", the X2/S0 no-drift
pattern) or the honest one-line reason why no tree exists. `tree_or_reason(certainty, kind=None)`
is the query API: (builder, None) or (None, reason) — never both, never neither. `formal_proof` is
legitimately emitted by TWO tree-covered kinds (modular and sum induction); pass `kind=` for the
exact builder.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from importlib import import_module

from .strategy import factor_prime_powers


@dataclass
class ProofNode:
    claim: str
    method: str                       # "CRT" | "induction" | "residue-exhaustion"
    certainty: str
    children: list = field(default_factory=list)
    note: str = ""


def proof_tree(finding) -> ProofNode:
    """Reconstruct the proof-dependency tree of a proved arithmetic finding."""
    goal = finding.claim
    if finding.verdict != "proved":
        return ProofNode(goal, finding.method, finding.certainty, note="not proved")
    if finding.method == "modulus-factoring":
        lemmas = [ProofNode(f"({finding.expression}) % {pp} == 0", "induction", "formal_proof")
                  for pp in factor_prime_powers(finding.modulus)]
        return ProofNode(goal, "CRT", "formal_proof", lemmas,
                         "coprime prime-power lemmas combined by the Chinese Remainder Theorem")
    if finding.method == "residue-exhaustion":
        return ProofNode(goal, "residue-exhaustion", "exhaustive_residue_proof",
                         note=f"finite case-split: all {finding.modulus} residues checked")
    return ProofNode(goal, "induction", "formal_proof")


def sum_proof_tree(f_poly, g_poly, statement: str | None = None) -> ProofNode:
    """Reconstruct the proof-dependency tree of a SUM identity `Σ_{i=1}^n f(i) = g(n)`. By the explicit
    derivation (`sum_derivation`), a SumInduction proof rests on TWO lemmas: a base case `g(1) = f(1)`
    (an evaluation) and an induction STEP `g(n) = g(n−1) + f(n)` (a kernel-checked PolyIdentity). This
    makes those lemmas explicit — the same honest T3 slice as the modular tree, now for sums."""
    from .sum_derivation import derive_sum_identity
    d = derive_sum_identity(f_poly, g_poly)
    goal = statement or "sum_(i=1..n) f(i) = g(n)"
    if not d.verified:
        return ProofNode(goal, "SumInduction", "unknown", note="not proved")
    base = ProofNode(f"g(1) = f(1)  [{d.base_g} = {d.base_f}]", "evaluation", "arithmetic_check",
                     note="base case at n=1")
    step = ProofNode("g(n) = g(n−1) + f(n)", "PolyIdentity", "kernel_verified",
                     note="the induction step, verified as a kernel polynomial identity")
    return ProofNode(goal, "SumInduction", "formal_proof", [base, step],
                     "base case + kernel-checked telescoping step ⇒ induction over n ≥ 1")


def identity_proof_tree(finding) -> ProofNode:
    """The proof tree of a kernel-certified IDENTITY `p(n) = factored` (an IdentityFinding). It is a
    genuine LEAF: the kernel's single POLY_IDENTITY rule checks expand(lhs) ≡ expand(rhs) — there are
    no intermediate lemmas, and the tree says so instead of inventing any."""
    claim = f"{finding.expression} = {finding.factored}"
    if not finding.kernel_verified:
        return ProofNode(claim, "kernel-identity", "unknown", note="not kernel-verified")
    return ProofNode(claim, "kernel-identity", "kernel_identity",
                     note="single kernel Identity rule: expand(lhs) ≡ expand(rhs) — "
                          "a one-rule leaf proof, no intermediate lemmas")


@dataclass(frozen=True)
class TreeCoverage:
    kind: str                    # the proved/certified finding kind
    certainties: tuple           # certainty labels that kind emits when proved/certified
    builder_ref: str | None      # "module:callable" that builds the ProofNode; None ⇒ no tree
    reason: str | None           # honest structural reason why NO tree is produced


PROOF_TREE_COVERAGE = (
    TreeCoverage("modular_divisibility", ("formal_proof", "exhaustive_residue_proof"),
                 "mathhead.discovery.proof_tree:proof_tree", None),
    TreeCoverage("sum_identity", ("formal_proof",),
                 "mathhead.discovery.proof_tree:sum_proof_tree", None),
    TreeCoverage("kernel_identity", ("kernel_identity",),
                 "mathhead.discovery.proof_tree:identity_proof_tree", None),
    TreeCoverage("kernel_theorem", ("kernel_verified",),
                 "mathhead.discovery.proof_tree:proof_tree", None),
    TreeCoverage("constructive_bijection", ("constructive_bijection",), None,
                 "the certificate is an explicit witness MAP re-checked point-by-point (injective + "
                 "onto) on the bounded sample; there are no intermediate lemmas to expose, and the "
                 "universal step is a recorded classical argument, not machine-checked — a lemma "
                 "tree would fabricate structure the certificate does not have"),
    TreeCoverage("constructive_bounded_certificate", ("constructive_bounded",), None,
                 "a constructed witness (greedy coloring / exhibited clique) independently "
                 "re-checked per instance; instance-level evidence, not a lemma-structured "
                 "universal deduction — no dependency tree exists to reconstruct"),
    TreeCoverage("solver_verified_value", ("solver_verified",), None,
                 "a two-authority instance decision (e.g. sat@χ ∧ unsat@χ−1 on one graph); the "
                 "justification is a pair of direct solver checks, not a chain of named lemmas"),
    TreeCoverage("exact_integer_certificate", ("exact_integer_certificate",), None,
                 "an exact integer comparison chain (Bareiss principal minors / one square "
                 "comparison) certifying a single instance; numeric witness steps, not lemmas"),
    TreeCoverage("solver_verified_with_derived_lemmas", ("solver_verified_with_derived_lemmas",),
                 None,
                 "a solver verdict shipped with the list of derived lemmas that strengthened the "
                 "encoding; the lemmas are NAMED on the verdict but the solver's internal "
                 "derivation is not exposed, so no dependency tree can honestly be reconstructed"),
    TreeCoverage("interval_certified", ("interval_certified",), None,
                 "a certified numeric enclosure computed with directed rounding; the certificate "
                 "is the interval evaluation itself — bound-propagation steps, not named lemmas"),
    TreeCoverage("sat_witness", ("independently_verified_witness",), None,
                 "an explicit combinatorial witness (e.g. a Ramsey coloring) re-checked directly by "
                 "an independent checker; verification is one check with no intermediate lemmas"),
    TreeCoverage("drup_unsat_proof", ("independently_verified_unsat_proof",
                                      "independently_verified_unsat_proof_of_strengthened_formula"),
                 None,
                 "the proof object is the DRUP lemma SEQUENCE itself, checked line-by-line by "
                 "reverse unit propagation; its natural shape is a linear derivation of thousands "
                 "of clauses — flattening it under one root would add no tree structure, so the "
                 "honest artifact is the checked derivation, not a tree"),
)


def resolve_builder(cov: TreeCoverage):
    """Import and return the tree builder a coverage entry points at (raises if it cannot — the
    reference is load-bearing, it must not drift)."""
    if cov.builder_ref is None:
        raise ValueError(f"kind '{cov.kind}' has no tree builder — honest reason: {cov.reason}")
    mod_name, fn_name = cov.builder_ref.split(":")
    fn = getattr(import_module(mod_name), fn_name)
    if not callable(fn):
        raise TypeError(f"builder_ref {cov.builder_ref!r} does not resolve to a callable")
    return fn


def coverage_for(certainty: str, kind: str | None = None) -> TreeCoverage | None:
    """The coverage entry for a proved/certified certainty label (None if the label is unknown —
    the inventory test turns that None into a failure for any label the engine actually emits).
    `formal_proof` is emitted by two tree-covered kinds (modular and sum induction); pass `kind=`
    ("modular_divisibility" / "sum_identity") for the exact entry."""
    if kind is not None:
        return next((c for c in PROOF_TREE_COVERAGE
                     if c.kind == kind and certainty in c.certainties), None)
    return next((c for c in PROOF_TREE_COVERAGE if certainty in c.certainties), None)


def tree_or_reason(certainty: str, kind: str | None = None) -> tuple:
    """T3 coverage query: (tree_builder, None) when a proof tree exists for this certainty,
    (None, honest_reason) when none structurally can. Raises KeyError on an unknown label (or a
    kind/certainty pair the inventory does not record) — an uncovered proved/certified kind must
    fail loudly, not silently pass. Without `kind`, a certainty shared by several tree-covered
    kinds (`formal_proof`: modular AND sum induction) returns the first entry's builder; pass
    `kind=` for the exact one."""
    cov = coverage_for(certainty, kind)
    if cov is None:
        raise KeyError(f"no proof-tree coverage recorded for certainty {certainty!r}"
                       + (f" with kind {kind!r}" if kind is not None else ""))
    if cov.builder_ref is not None:
        return resolve_builder(cov), None
    return None, cov.reason


def render_tree(node: ProofNode, indent: int = 0) -> str:
    """A readable ASCII proof tree."""
    pad = "    " * indent
    head = f"{pad}{node.claim}   [{node.method}, {node.certainty}]"
    if node.note:
        head += f"  — {node.note}"
    lines = [head] + [render_tree(c, indent + 1) for c in node.children]
    return "\n".join(lines)
