"""
mathhead.discovery.hamiltonicity — a SECOND bridge to the SAT/UNSAT FRONTIER (roadmap O1):
Hamiltonian cycles.

`is_hamiltonian(g)` (does g have a Hamiltonian cycle?) is decided LOCALLY by backtracking, then
INDEPENDENTLY CONFIRMED through MathHead's `hamiltonian_path(cycle=True)` frontier tool: `sat` ⟺
Hamiltonian, `unsat` ⟺ not. Our search and MathHead's Z3 reduction are orthogonal authorities;
both agreeing is the "don't trust one prover" check applied to a second NP-complete invariant.

We also mine Hamiltonicity IMPLICATIONS over the sample:
  * Hamiltonian ⟹ connected                        (necessary)        — survives
  * Hamiltonian ⟹ min_degree ≥ 2                   (necessary)        — survives
  * Dirac: n≥3 ∧ min_degree ≥ n/2 ⟹ Hamiltonian    (sufficient)       — survives  ← a real theorem,
                                                                          rediscovered from data
  * connected ∧ n≥3 ⟹ Hamiltonian                  (plausible, FALSE) — REFUTED (a path P₃ breaks it)

Two honesty details. (1) MathHead's `hamiltonian_path` is 0-INDEXED (unlike `graph_coloring`), so
there is NO vertex shift here. (2) The n<3 "no cycle" convention is a definitional edge case, not a
structural fact — so it is handled locally (MathHead's reduction accepts a degenerate 2-cycle), and
the `connected ⟹ Hamiltonian` claim is scoped to n≥3 so its counterexample (P₃) is a genuine
STRUCTURAL witness, not a convention artifact.
"""
from __future__ import annotations

from dataclasses import dataclass

from mathhead.router import route

from .invariants import is_connected, is_hamiltonian, min_degree
from .objects import Graph


def _mathhead_status(g: Graph) -> str:
    """MathHead frontier verdict for 'does g have a Hamiltonian cycle?': 'sat' | 'unsat' | other."""
    return route(
        "hamiltonian_path",
        {"edges": [[u, v] for (u, v) in g.edges], "n": g.n, "cycle": True},
    ).status


@dataclass
class HamiltonicityVerification:
    n: int
    hamiltonian: bool
    confirmed: bool             # local backtracking and MathHead's reduction agree
    certainty: str              # "solver_verified" | "trivial"


def verify_hamiltonicity(g: Graph) -> HamiltonicityVerification:
    """Confirm the backtracking `is_hamiltonian(g)` against MathHead's frontier reduction.
    For n < 3 the answer is a convention (no cycle) and MathHead — whose reduction accepts a
    degenerate 2-cycle — is not invoked; for n ≥ 3 the two definitions coincide exactly."""
    ham = is_hamiltonian(g)
    if g.n < 3:
        return HamiltonicityVerification(g.n, ham, True, "trivial")
    agrees = (_mathhead_status(g) == "sat") == ham
    return HamiltonicityVerification(g.n, ham, agrees, "solver_verified")


def _hamiltonian(g: Graph) -> bool:
    return is_hamiltonian(g)


def _connected(g: Graph) -> bool:
    return is_connected(g)


def _min_deg_ge_2(g: Graph) -> bool:
    return min_degree(g) >= 2


def _dirac_premise(g: Graph) -> bool:
    """Dirac's sufficient condition: n ≥ 3 and every vertex has degree ≥ n/2."""
    return g.n >= 3 and 2 * min_degree(g) >= g.n


def _connected_n3(g: Graph) -> bool:
    """Connected AND n ≥ 3 — scoped past the n<3 convention so the witness is structural."""
    return g.n >= 3 and is_connected(g)


# (statement, premise, conclusion) — the claim is  premise(g) ⟹ conclusion(g)
_LAWS = [
    ("Hamiltonian => connected", _hamiltonian, _connected),                     # true (necessary)
    ("Hamiltonian => min_degree >= 2", _hamiltonian, _min_deg_ge_2),            # true (necessary)
    ("(n>=3 and min_degree >= n/2) => Hamiltonian [Dirac]", _dirac_premise, _hamiltonian),  # true
    ("(connected and n>=3) => Hamiltonian", _connected_n3, _hamiltonian),       # FALSE (P3)
]


@dataclass
class ImplicationFinding:
    statement: str
    status: str                    # "no_counterexample_within_bound" | "refuted"
    certainty: str = "bounded_check"
    counterexample: dict = None
    support: int = 0               # # of sample graphs that satisfied the premise (non-vacuous)


def hamiltonicity_laws(graphs) -> list:
    """Check each Hamiltonicity implication counterexample-first (ascending graph size ⇒ a MINIMAL
    counterexample). Boolean/integer invariants ⇒ each check is exact — `bounded_check` (exact over
    the finite sample), not proven for all n."""
    out = []
    for statement, premise, conclusion in _LAWS:
        ce, support = None, 0
        for g in graphs:
            if g.n == 0:
                continue
            if premise(g):
                support += 1
                if not conclusion(g):
                    ce = {"n": g.n, "edges": sorted(g.edges)}
                    break
        status = "refuted" if ce else "no_counterexample_within_bound"
        out.append(ImplicationFinding(statement, status, "bounded_check", ce, support))
    return out
