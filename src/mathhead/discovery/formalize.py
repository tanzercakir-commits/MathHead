"""
mathhead.discovery.formalize — candidate formalizations A/B/C + formalization probes (v1 V2/V3).

An informal graph-bound claim like "num_triangles <= num_edges" is AMBIGUOUS about its quantifier
domain: over CONNECTED graphs? over ALL graphs (disconnected included)? at one FIXED order n?
Track V2 asks the engine to make that ambiguity EXPLICIT instead of silently picking one reading:

  * `candidate_formalizations` produces the three deterministic candidates —
      A  universal over CONNECTED graphs, 2 <= n <= max_n   (exactly `check()`'s own semantics;
         candidate A is EVALUATED by delegating to the product single door);
      B  universal over ALL graphs incl. disconnected, 2 <= n <= max_n  (drops the connectivity
         assumption — the reading a careless formalizer silently adds);
      C  all graphs of one FIXED order n = fixed_n  (a COMPLETE finite domain: every isomorphism
         class of that order is enumerated, so the scan genuinely DECIDES this reading);
  * `differences` lists the assumption deltas between candidates MACHINE-READABLY (which
    assumption each candidate adds/removes — "A assumes connectivity, B does not");
  * `evaluate_candidate` runs each candidate honestly: A through `check()`, B and C through their
    own exhaustive scans, returning the same `CheckResult` envelope. The same relation text can
    honestly be OPEN under A, REFUTED under B, and DECIDED under C — that verdict split IS the
    formalization ambiguity, surfaced.

Track V3 — formalization probes: `probe(candidate, graph)` reports whether a KNOWN example /
counterexample / boundary object lies IN the candidate's domain and whether the claim HOLDS on it.
A known object that refutes candidate B while falling outside candidate A's domain is exactly the
formalization test the track asks for: the object separates the readings.

Deterministic and honest by construction: the grammar and the invariant registry are the product's
OWN, taken through its public helpers `graph_statement_grammar()` / `graph_invariant_registry()`
(one shared object — drift is structurally impossible), unknown invariant names or non-graph
statements raise ValueError (no guessing), no LLM anywhere. Tier discipline: an unbounded
universal survivor is only ever OPEN (`no_counterexample_within_bound`); only the FIXED-order
candidate C may say "proved", and it carries its own honest tier `finite_domain_exhaustion` —
a decision by complete enumeration of the finite fixed-n domain (one representative per
isomorphism class; the invariants are isomorphism-invariant), an exhaustion proof, NOT a witness.
"""
from __future__ import annotations

from dataclasses import dataclass

from .product import CheckResult, graph_invariant_registry, graph_statement_grammar

_MAX_ORDER = 7          # generate.generate_graphs' honest brute-force wall


@dataclass(frozen=True)
class CandidateFormalization:
    """One candidate reading of an ambiguous bound claim — assumptions machine-readable."""
    label: str                  # "A" | "B" | "C"
    statement: str              # the bare relation text, e.g. "num_triangles <= num_edges"
    domain: str                 # human-readable domain description
    assumptions: tuple          # machine-readable assumption atoms (compared by `differences`)
    lhs: str = ""
    rel: str = ""
    k: int = 1                  # right-side multiplier in `invA REL k*invB + c`
    rhs: str = ""
    c: int = 0                  # right-side additive constant
    max_n: int | None = None    # bounded-scan ceiling (candidates A and B)
    fixed_n: int | None = None  # the fixed order (candidate C)


def candidate_formalizations(statement: str, *, max_n: int = 6,
                             fixed_n: int = 4) -> tuple:
    """The three candidate readings of `invA <= / >= / == [k*]invB [+ c]` (V2). Deterministic;
    a statement outside the graph-bound grammar or with unknown invariants raises ValueError —
    the module refuses to guess, exactly like the product door."""
    if not 2 <= max_n <= _MAX_ORDER or not 1 <= fixed_n <= _MAX_ORDER:
        raise ValueError(f"bounds must satisfy 2 <= max_n <= {_MAX_ORDER} and "
                         f"1 <= fixed_n <= {_MAX_ORDER} (the honest generation wall)")
    m = graph_statement_grammar().match(statement.strip())
    if not m:
        raise ValueError(f"not a graph-bound statement ({statement!r}) — the candidate surface is "
                         "'invA <= / >= / == [k*]invB [+ c]'; the module refuses to guess")
    lhs, rel, k, rhs, c = (m.group(1), m.group(2), int(m.group(3) or 1),
                           m.group(4), int(m.group(5) or 0))
    rel = "==" if rel == "=" else rel
    invs = graph_invariant_registry()
    for name in (lhs, rhs):
        if name not in invs:
            raise ValueError(f"unknown invariant {name!r} — not in the shared registry; "
                             "the module refuses to guess")
    stmt = statement.strip()
    common = ("simple undirected graph", "invariants evaluated exactly (integers)")
    a = CandidateFormalization(
        "A", stmt, f"connected graphs, 2 <= n <= {max_n} (bounded scan)",
        common + ("connected", f"2 <= n <= {max_n} (bounded scan)"),
        lhs, rel, k, rhs, c, max_n=max_n)
    b = CandidateFormalization(
        "B", stmt, f"ALL graphs incl. disconnected, 2 <= n <= {max_n} (bounded scan)",
        common + (f"2 <= n <= {max_n} (bounded scan)",),
        lhs, rel, k, rhs, c, max_n=max_n)
    cc = CandidateFormalization(
        "C", stmt, f"all graphs of the FIXED order n = {fixed_n} (complete finite domain)",
        common + (f"n == {fixed_n} (complete finite domain)",),
        lhs, rel, k, rhs, c, fixed_n=fixed_n)
    return (a, b, cc)


def differences(candidates) -> list:
    """Pairwise assumption deltas, machine-readable (V2's "A assumes X, C only Y"). Each entry:
    {'pair': (label1, label2), 'only_first': (...), 'only_second': (...)}."""
    out = []
    for i in range(len(candidates)):
        for j in range(i + 1, len(candidates)):
            a, b = candidates[i], candidates[j]
            out.append({
                "pair": (a.label, b.label),
                "only_first": tuple(x for x in a.assumptions if x not in b.assumptions),
                "only_second": tuple(x for x in b.assumptions if x not in a.assumptions),
            })
    return out


def _holds(cand: CandidateFormalization, g) -> bool:
    """Does the bare relation hold on one graph? Exact integer arithmetic, shared registry."""
    invs = graph_invariant_registry()
    va, vb = invs[cand.lhs](g), invs[cand.rhs](g)
    op = {"<=": lambda x, y: x <= y, ">=": lambda x, y: x >= y,
          "==": lambda x, y: x == y}[cand.rel]
    return op(va, cand.k * vb + cand.c)


def _in_domain(cand: CandidateFormalization, g) -> bool:
    """Is the graph inside the candidate's quantifier domain? (V3 probe helper.)"""
    from .invariants import evaluate
    if cand.label == "C":
        return g.n == cand.fixed_n
    if not 2 <= g.n <= cand.max_n:
        return False
    return evaluate(g, "num_components") == 1 if cand.label == "A" else True


def probe(cand: CandidateFormalization, g) -> dict:
    """V3 — run one KNOWN object (example / counterexample / boundary case) against a candidate
    formalization. Returns {'label', 'in_domain', 'claim_holds'} — `claim_holds` is None when the
    object is OUTSIDE the domain (an out-of-domain object refutes NOTHING; that shielding is the
    whole point of recording the domain assumption)."""
    ind = _in_domain(cand, g)
    return {"label": cand.label, "in_domain": ind,
            "claim_holds": _holds(cand, g) if ind else None}


def _scan(cand: CandidateFormalization, graphs, complete_domain: bool) -> CheckResult:
    """Exhaustive counterexample-first scan for candidates B and C. Only a COMPLETE finite domain
    (candidate C) may turn a survivor into 'proved'; a bounded slice of an unbounded domain stays
    honestly OPEN."""
    structure = ("graph_bound_fixed_order" if cand.label == "C"
                 else "graph_bound_all_graphs")
    checked = 0
    for g in graphs:
        checked += 1
        if not _holds(cand, g):
            invs = graph_invariant_registry()
            return CheckResult(
                cand.statement, structure, "refuted", "exact_integer_certificate",
                witness={"n": g.n, "edges": sorted(g.edges),
                         cand.lhs: invs[cand.lhs](g), cand.rhs: invs[cand.rhs](g)},
                checked_up_to=f"first counterexample in candidate {cand.label}'s domain "
                              f"({cand.domain})",
                instruments=("formalize: counterexample-first scan",),
                notes=f"witness lies inside candidate {cand.label}'s domain; values exact — "
                      f"this reading of the statement is false")
    if complete_domain:
        return CheckResult(
            cand.statement, structure, "proved", "finite_domain_exhaustion",
            checked_up_to=f"ALL {checked} isomorphism classes of order n={cand.fixed_n} "
                          "(complete finite domain)",
            instruments=("formalize: exhaustive finite-domain scan",),
            notes="the fixed-order reading quantifies over a FINITE domain, enumerated "
                  "completely (one representative per isomorphism class; the invariants are "
                  "isomorphism-invariant) — an exhaustion proof, not a witness; decided, "
                  "not extrapolated")
    return CheckResult(
        cand.statement, structure, "open", "no_counterexample_within_bound",
        checked_up_to=f"ALL {checked} graphs (incl. disconnected) with 2 <= n <= {cand.max_n}",
        instruments=("formalize: counterexample-first scan",),
        notes="survived the bounded scan; the domain is unbounded, so a finite scan NEVER "
              "proves this reading — honestly open")


def evaluate_candidate(cand: CandidateFormalization) -> CheckResult:
    """Honest verdict envelope for one candidate. A is `check()`'s own semantics and is DELEGATED
    to the product door; B and C run their own exhaustive scans (same envelope, same tiers)."""
    if cand.label == "A":
        from .product import check
        return check(cand.statement, max_n=cand.max_n)
    from .generate import generate_graphs
    if cand.label == "B":
        graphs = [g for n in range(2, cand.max_n + 1) for g in generate_graphs(n)]
        return _scan(cand, graphs, complete_domain=False)
    return _scan(cand, generate_graphs(cand.fixed_n), complete_domain=True)


def formalize(statement: str, *, max_n: int = 6, fixed_n: int = 4) -> dict:
    """The V2 one-call surface: candidates + machine-readable differences + one honest verdict
    per candidate."""
    cands = candidate_formalizations(statement, max_n=max_n, fixed_n=fixed_n)
    return {
        "statement": statement.strip(),
        "candidates": cands,
        "differences": differences(cands),
        "verdicts": {c.label: evaluate_candidate(c) for c in cands},
    }
