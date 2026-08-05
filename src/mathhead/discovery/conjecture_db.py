"""
mathhead.discovery.conjecture_db — the curated conjecture database (v2B0, Real Discovery Program).

Formalization is the highest-risk step of the counterexample hunt: a subtly wrong statement makes a
"counterexample" worthless. Every entry here therefore carries FOUR defenses:

  1. the statement is recorded verbatim with its DOMAIN RESTRICTION (connected, n ≥ 3, …) — a witness
     outside the domain is rejected, never counted;
  2. `status` is honest: `refuted_in_literature` entries are CALIBRATION targets (re-finding a witness is
     REDISCOVERY of a known refutation, labelled as such), `open` entries are live targets;
  3. `small_n_guard` — the conjecture is exhaustively verified on all graphs of small n (via geng),
     where the literature says it HOLDS. If our formalization "finds" a small violation, the
     formalization itself is wrong and the test suite fails — the guard catches mis-statement;
  4. verdicts are never float: each entry's `certify(g)` produces an exact certificate (pure integer /
     exact invariants) or None. Search may use float scores; the VERDICT may not.

Entries:
  * AH_SPECTRAL_MATCHING — Aouchiche–Hansen: every CONNECTED graph on n ≥ 3 vertices satisfies
    λ₁ + μ ≥ √(n−1) + 1 (λ₁ = adjacency spectral radius, μ = matching number; equality at stars).
    REFUTED by A. Z. Wagner, "Constructions in combinatorics via neural networks" (arXiv:2104.14516,
    2021), who found a counterexample tree. Our hunt = calibration/rediscovery.
  * CHI_LE_DELTA — the naive strawman χ ≤ Δ on all graphs with n ≥ 2 (Brooks' theorem carves the real
    boundary; complete graphs and odd cycles violate the naive form). Machinery smoke-test tier.
  * CONN_HAMILTONIAN — "every connected graph on n ≥ 3 vertices is Hamiltonian" (folklore-false; P₃).
    Machinery smoke-test tier.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .invariants import chromatic_number, evaluate, is_hamiltonian, max_degree
from .objects import Graph
from .rich_invariants import matching_number
from .spectral_cert import certify_lambda1_plus_mu_below


def _connected(g: Graph) -> bool:
    return g.n > 0 and evaluate(g, "num_components") == 1


def lambda1_power(g: Graph, iters: int = 200) -> float:
    """Float ESTIMATE of λ₁ (search-side only, never the verdict). Power iteration on A + I — the +I
    shift makes the Perron eigenvalue strictly dominant even for bipartite graphs (trees!)."""
    if g.n == 0:
        return 0.0
    adj = [[0.0] * g.n for _ in range(g.n)]
    for (u, v) in g.edges:
        adj[u][v] = adj[v][u] = 1.0
    x = [1.0] * g.n
    for _ in range(iters):
        y = [x[i] + sum(adj[i][j] * x[j] for j in range(g.n)) for i in range(g.n)]   # (A+I)x
        norm = max(abs(v) for v in y) or 1.0
        x = [v / norm for v in y]
    ray_num = sum(x[i] * sum(adj[i][j] * x[j] for j in range(g.n)) for i in range(g.n))
    ray_den = sum(v * v for v in x) or 1.0
    return ray_num / ray_den                              # Rayleigh quotient of A itself


@dataclass
class Conjecture:
    id: str
    statement: str
    domain: str                                  # human-readable restriction
    status: str                                  # "refuted_in_literature" | "open"
    source: str
    in_domain: Callable                          # Graph -> bool (witnesses outside are REJECTED)
    score: Callable                              # Graph -> float; NEGATIVE ⇒ candidate violation (search)
    certify: Callable                            # Graph -> certificate | None  (EXACT verdict)
    small_n_guard: int = 6                       # exhaustively verified to hold for all n ≤ this
    notes: str = ""


# --- entry: Aouchiche–Hansen  λ₁ + μ ≥ √(n−1) + 1  (connected, n ≥ 3) ---------------------------
def _ah_score(g: Graph) -> float:
    """Slack λ₁ + μ − (√(n−1) + 1); negative ⇒ candidate violation. Float — search only."""
    return lambda1_power(g) + matching_number(g) - ((g.n - 1) ** 0.5 + 1.0)


def _ah_certify(g: Graph):
    if not (_connected(g) and g.n >= 3):
        return None                                        # outside the conjecture's domain
    return certify_lambda1_plus_mu_below(g, matching_number(g), lambda1_power(g))


AH_SPECTRAL_MATCHING = Conjecture(
    id="AH_SPECTRAL_MATCHING",
    statement="for every connected graph on n>=3 vertices: lambda1 + mu >= sqrt(n-1) + 1",
    domain="connected graphs, n >= 3",
    status="refuted_in_literature",
    source="Aouchiche & Hansen (conjectured); REFUTED by A. Z. Wagner, arXiv:2104.14516 (2021)",
    in_domain=lambda g: _connected(g) and g.n >= 3,
    score=_ah_score,
    certify=_ah_certify,
    small_n_guard=7,
    notes="equality at stars K_{1,n-1} AND (engine-certified) at D(12,12), n=26 (lambda1=4 exactly). "
          "TRANSCRIPTION CAVEAT: the statement is transcribed from memory of Wagner Conj. 2.1; a HUMAN "
          "must verify the wording against arXiv:2104.14516 before any external claim. Every witness "
          "here is a pure-integer certificate of the statement AS TRANSCRIBED, and a REDISCOVERY "
          "(status refuted_in_literature) — never a novelty claim.",
)


# --- entry: naive χ ≤ Δ (smoke tier) ------------------------------------------------------------
def _chi_certify(g: Graph):
    if g.n < 2:
        return None
    chi, delta = chromatic_number(g), max_degree(g)        # both EXACT integers
    if chi > delta:
        return {"witness": "chi > Delta", "chi": chi, "Delta": delta, "n": g.n,
                "certainty": "exact_integer_certificate"}
    return None


CHI_LE_DELTA = Conjecture(
    id="CHI_LE_DELTA",
    statement="for every graph on n>=2 vertices: chi <= Delta (NAIVE form)",
    domain="all graphs, n >= 2",
    status="refuted_in_literature",
    source="naive strawman; Brooks' theorem (1941) carves the true boundary (K_n, odd cycles violate)",
    in_domain=lambda g: g.n >= 2,
    score=lambda g: float(max_degree(g) - chromatic_number(g)),
    certify=_chi_certify,
    small_n_guard=0,                                       # violated already at tiny n — no guard range
    notes="calibration/smoke tier: the machinery must find K2/K3/odd cycles instantly.",
)


# --- entry: connected ⟹ Hamiltonian (smoke tier) -----------------------------------------------
def _ham_certify(g: Graph):
    if not (_connected(g) and g.n >= 3):
        return None
    if not is_hamiltonian(g):                              # exact backtracking + (elsewhere) solver-confirmed
        return {"witness": "connected but not Hamiltonian", "n": g.n,
                "certainty": "exact_integer_certificate"}
    return None


CONN_HAMILTONIAN = Conjecture(
    id="CONN_HAMILTONIAN",
    statement="every connected graph on n>=3 vertices is Hamiltonian",
    domain="connected graphs, n >= 3",
    status="refuted_in_literature",
    source="folklore-false; P3 is the minimal witness",
    in_domain=lambda g: _connected(g) and g.n >= 3,
    score=lambda g: 1.0 if is_hamiltonian(g) else -1.0,
    certify=_ham_certify,
    small_n_guard=0,
    notes="calibration/smoke tier.",
)


CONJECTURES: dict = {c.id: c for c in (AH_SPECTRAL_MATCHING, CHI_LE_DELTA, CONN_HAMILTONIAN)}


@dataclass
class GuardReport:
    conjecture_id: str
    checked_n: tuple = field(default_factory=tuple)
    graphs_checked: int = 0
    violations: int = 0

    @property
    def formalization_ok(self) -> bool:
        return self.violations == 0


def small_n_guard(conj: Conjecture, n_max: int | None = None) -> GuardReport:
    """FORMALIZATION GUARD: exhaustively verify the conjecture HOLDS on every in-domain graph up to
    n_max (default: the entry's literature-verified range). A violation here means OUR STATEMENT is
    wrong, not that we found a discovery — the test suite treats it as a failure."""
    from .nauty_scale import geng_available, geng_graphs
    from .generate import generate_graphs
    n_max = n_max if n_max is not None else conj.small_n_guard
    rep = GuardReport(conj.id)
    checked = []
    for n in range(3, n_max + 1):
        graphs = geng_graphs(n, connected=True) if geng_available() else \
            [g for g in generate_graphs(n) if _connected(g)]
        checked.append(n)
        for g in graphs:
            if not conj.in_domain(g):
                continue
            rep.graphs_checked += 1
            if conj.certify(g) is not None:
                rep.violations += 1
    rep.checked_n = tuple(checked)
    return rep
