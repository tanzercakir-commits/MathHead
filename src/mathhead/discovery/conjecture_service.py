"""
mathhead.discovery.conjecture_service — the Graffiti-style conjecture service (v2C0, Kademe 3).

Fajtlowicz's Graffiti (1980s) generated invariant inequalities that mathematicians then proved — dozens
of papers came from a machine's conjecture feed. This is that instrument on the engine's rich invariants
(α, γ, ν, girth, diameter, radius + the classics), with the project's honesty built in:

  * counterexample-first — every candidate inequality (A ≤ B, A ≤ B + c, A ≤ 2B) is tested over ALL
    connected graphs in the sample; one violation kills it (exact invariants, no floats anywhere);
  * SHARPNESS — a surviving bound is interesting when equality is ATTAINED: each conjecture reports its
    equality witnesses (count + smallest example), Graffiti's hallmark ranking signal;
  * honest scope — survivors are `empirical` over the sample, never theorems; and the feed carries the
    AE2 lesson verbatim: most survivors are KNOWN results (γ ≤ α, radius ≤ diameter ≤ 2·radius …) — the
    feed is a list for HUMANS to attack, not a novelty claim.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .invariants import chromatic_number, clique_number, evaluate
from .rich_invariants import RICH_INVARIANTS

_CLASSIC = {
    "num_edges": lambda g: evaluate(g, "num_edges"),
    "max_degree": lambda g: evaluate(g, "max_degree"),
    "min_degree": lambda g: evaluate(g, "min_degree"),
    "chromatic_number": chromatic_number,
    "clique_number": clique_number,
}


def service_invariants() -> dict:
    """The feed's invariant registry: rich (α, γ, ν, girth, diameter, radius) + classics."""
    return {**RICH_INVARIANTS, **_CLASSIC}


@dataclass
class ServiceConjecture:
    statement: str               # e.g. "domination_number <= independence_number"
    form: str                    # "A<=B" | "A<=B+c" | "A<=2B"
    lhs: str
    rhs: str
    const: int = 0
    support: int = 0             # graphs it held on (all of them — survivors only)
    sharp_count: int = 0         # graphs attaining equality
    sharp_example: tuple = ()    # (n, sorted edge list) of the smallest equality witness
    status: str = "empirical"    # sample-true; NEVER a theorem
    caveat: str = ("survivor over the connected sample only; almost certainly a KNOWN result — "
                   "a feed item for humans to attack, not a novelty claim")


def _connected_sample(n_max: int) -> list:
    from .nauty_scale import geng_available, geng_graphs
    if geng_available():
        return [g for n in range(2, n_max + 1) for g in geng_graphs(n, connected=True)]
    from .generate import generate_graphs
    return [g for n in range(2, n_max + 1) for g in generate_graphs(n)
            if evaluate(g, "num_components") == 1]


@dataclass
class ConjectureFeed:
    n_max: int
    graphs: int = 0
    tested: int = 0
    survivors: list = field(default_factory=list)   # ServiceConjecture, sharpest-first


def run_service(n_max: int = 6, max_const: int = 1) -> ConjectureFeed:
    """Mine the feed: all ordered invariant pairs in the forms A ≤ B, A ≤ B + c (c ≤ max_const),
    A ≤ 2B — counterexample-first over every connected graph with 2 ≤ n ≤ n_max; survivors ranked by
    sharpness (most equality witnesses first), deterministically."""
    invs = service_invariants()
    graphs = _connected_sample(n_max)
    values = [{name: fn(g) for name, fn in invs.items()} for g in graphs]
    # diameter/radius sentinels (-1) never occur on connected graphs with n>=2; assert the contract
    assert all(v["diameter"] >= 0 and v["radius"] >= 0 for v in values)

    feed = ConjectureFeed(n_max, len(graphs))
    names = sorted(invs)
    candidates = []
    for a in names:
        for b in names:
            if a == b:
                continue
            candidates.append((f"{a} <= {b}", "A<=B", a, b, 0, lambda va, vb, c=0: va <= vb))
            for c in range(1, max_const + 1):
                candidates.append((f"{a} <= {b} + {c}", "A<=B+c", a, b, c,
                                   lambda va, vb, c=c: va <= vb + c))
            candidates.append((f"{a} <= 2*{b}", "A<=2B", a, b, 0, lambda va, vb, c=0: va <= 2 * vb))

    for stmt, form, a, b, c, pred in candidates:
        feed.tested += 1
        ok = True
        sharp, sharp_ex = 0, ()
        for g, v in zip(graphs, values):
            va, vb = v[a], v[b]
            if not pred(va, vb):
                ok = False
                break
            boundary = (va == vb + c) if form != "A<=2B" else (va == 2 * vb)
            if boundary:
                sharp += 1
                if not sharp_ex:
                    sharp_ex = (g.n, tuple(sorted(g.edges)))
        if ok:
            feed.survivors.append(ServiceConjecture(stmt, form, a, b, c,
                                                    len(graphs), sharp, sharp_ex))
    # sharpest-first; ties by simplicity (plain A<=B before offset/scaled forms), then lexicographic
    form_rank = {"A<=B": 0, "A<=2B": 1, "A<=B+c": 2}
    feed.survivors.sort(key=lambda s: (-s.sharp_count, form_rank[s.form], s.statement))
    # drop dominated duplicates: if A<=B survives, A<=B+c is implied noise — keep the tight form only
    tight = {(s.lhs, s.rhs) for s in feed.survivors if s.form == "A<=B"}
    feed.survivors = [s for s in feed.survivors
                      if not (s.form == "A<=B+c" and (s.lhs, s.rhs) in tight)]
    return feed
