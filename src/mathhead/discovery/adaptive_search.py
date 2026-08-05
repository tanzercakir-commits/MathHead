"""
mathhead.discovery.adaptive_search — the adaptive counterexample hunter (v2B1/B2).

Wagner (arXiv:2104.14516) showed that ADAPTIVE search — not exhaustive sweep — is how machines find
counterexamples humans missed: the haystack at n≈19 has ~2^171 graphs; nothing exhaustive gets there.
This is that instrument, kept deliberately simple and fully deterministic:

  * SEEDED simulated annealing over CONNECTED graphs on a fixed n — moves toggle a single edge (removals
    that would disconnect are rejected), temperature decays geometrically, every run reproducible from
    (seed, steps, n);
  * the OBJECTIVE is a Conjecture's `score` (float slack; negative ⇒ candidate violation) — floats are
    for STEERING only;
  * the VERDICT is the Conjecture's `certify` — exact integer arithmetic. `hunt` reports `certified`
    ONLY when the exact certificate exists; a negative float score alone proves nothing and is reported
    honestly as `float_candidate_uncertified` (near-boundary float noise dies at the exact gate).

An unsuccessful hunt returns `not_found_within_budget` — an honest outcome, never dressed up.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

from .objects import Graph


def _adj_from(edges: set, n: int) -> list:
    adj = [set() for _ in range(n)]
    for (u, v) in edges:
        adj[u].add(v)
        adj[v].add(u)
    return adj


def _connected_edges(edges: set, n: int) -> bool:
    if n == 0:
        return False
    adj = _adj_from(edges, n)
    seen, stack = {0}, [0]
    while stack:
        v = stack.pop()
        for u in adj[v]:
            if u not in seen:
                seen.add(u)
                stack.append(u)
    return len(seen) == n


def random_tree(n: int, rng: random.Random) -> set:
    """A uniform-ish random labelled tree (random Prüfer-style attachment) — the sparse starting point."""
    edges = set()
    for v in range(1, n):
        u = rng.randrange(v)
        edges.add((u, v))
    return edges


@dataclass
class HuntOutcome:
    conjecture_id: str
    n: int
    seed: int
    steps: int
    status: str                 # "certified_counterexample" | "float_candidate_uncertified" | "not_found_within_budget"
    best_score: float
    witness: Graph | None = None
    certificate: object = None
    history: list = field(default_factory=list)   # (step, best_score) checkpoints


def hunt(conj, n: int, seed: int = 0, steps: int = 20000, t0: float = 1.0,
         cooling: float = 0.999) -> HuntOutcome:
    """Simulated annealing on connected graphs of order n against `conj`. Deterministic per
    (n, seed, steps). Certified verdicts only — float candidates are re-judged by `conj.certify`."""
    rng = random.Random(seed)
    edges = random_tree(n, rng)
    cur = Graph(n, frozenset(edges))
    cur_score = conj.score(cur)
    best, best_score = cur, cur_score
    temp = t0
    history = []
    all_pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]

    for step in range(steps):
        u, v = all_pairs[rng.randrange(len(all_pairs))]
        e = (u, v)
        nxt = set(edges)
        if e in nxt:
            nxt.remove(e)
            if not _connected_edges(nxt, n):
                continue                                   # stay in the conjecture's domain
        else:
            nxt.add(e)
        cand = Graph(n, frozenset(nxt))
        cand_score = conj.score(cand)
        delta = cand_score - cur_score
        if delta <= 0 or rng.random() < pow(2.718281828, -delta / max(temp, 1e-9)):
            edges, cur, cur_score = nxt, cand, cand_score
            if cur_score < best_score:
                best, best_score = cur, cur_score
                history.append((step, round(best_score, 6)))
                if best_score < 0:
                    cert = conj.certify(best)              # the EXACT gate
                    if cert is not None:
                        return HuntOutcome(conj.id, n, seed, step + 1, "certified_counterexample",
                                           best_score, best, cert, history)
        temp *= cooling

    if best_score < 0:                                     # float said yes, exact gate said no
        cert = conj.certify(best)
        if cert is not None:
            return HuntOutcome(conj.id, n, seed, steps, "certified_counterexample",
                               best_score, best, cert, history)
        return HuntOutcome(conj.id, n, seed, steps, "float_candidate_uncertified",
                           best_score, best, None, history)
    return HuntOutcome(conj.id, n, seed, steps, "not_found_within_budget",
                       best_score, None, None, history)


def hunt_multi(conj, sizes, seeds, steps: int = 20000) -> list:
    """The calibration sweep: hunt across several orders and seeds; certified outcomes first."""
    outcomes = [hunt(conj, n, seed, steps) for n in sizes for seed in seeds]
    outcomes.sort(key=lambda o: (o.status != "certified_counterexample", o.best_score))
    return outcomes


# --- tree-space hunt (the A–H specialist) --------------------------------------------------------
def tree_matching_number(edges: set, n: int) -> int:
    """EXACT ν for a TREE, linear time: repeatedly match a leaf to its neighbour (classically optimal
    on trees). Cross-checked in tests against the general exact `matching_number`."""
    adj = _adj_from(edges, n)
    deg = [len(a) for a in adj]
    leaves = [v for v in range(n) if deg[v] == 1]
    dead = [False] * n
    nu = 0
    while leaves:
        v = leaves.pop()
        if dead[v] or deg[v] == 0:
            continue
        u = next(w for w in adj[v] if not dead[w])         # v's unique live neighbour
        nu += 1
        for x in (u, v):                                   # remove the matched pair
            dead[x] = True
        for w in adj[u]:
            if not dead[w]:
                deg[w] -= 1
                if deg[w] == 1:
                    leaves.append(w)
        adj[u].clear()
        adj[v].clear()
    return nu


def tree_hunt(conj, n: int, seed: int = 0, steps: int = 8000, t0: float = 0.15,
              cooling: float = 0.9995, power_iters: int = 60) -> HuntOutcome:
    """Simulated annealing restricted to TREE space (edge-rewire moves keep exactly n−1 edges and
    connectivity) — the heuristic informed by Wagner's witness being a tree. The verdict is still the
    conjecture's exact `certify`; the tree restriction is a SEARCH choice, not a completeness claim."""
    from .conjecture_db import lambda1_power
    rng = random.Random(seed)
    edges = random_tree(n, rng)
    target = (n - 1) ** 0.5 + 1.0

    def score(es: set) -> float:
        g = Graph(n, frozenset(es))
        return lambda1_power(g, power_iters) + tree_matching_number(es, n) - target

    cur_score = score(edges)
    best, best_score = set(edges), cur_score
    temp = t0
    history = []
    for step in range(steps):
        u, v = rng.sample(range(n), 2)
        e = (min(u, v), max(u, v))
        if e in edges:
            continue
        nxt = set(edges)
        nxt.add(e)                                         # adding (u,v) to a tree closes ONE cycle…
        cyc = _cycle_edges(nxt, n, e)
        drop = cyc[rng.randrange(len(cyc))]
        if drop == e:
            continue
        nxt.remove(drop)                                   # …removing any cycle edge restores a tree
        cand_score = score(nxt)
        delta = cand_score - cur_score
        if delta <= 0 or rng.random() < pow(2.718281828, -delta / max(temp, 1e-9)):
            edges, cur_score = nxt, cand_score
            if cur_score < best_score:
                best, best_score = set(nxt), cur_score
                history.append((step, round(best_score, 6)))
                if best_score < 0:
                    g = Graph(n, frozenset(best))
                    cert = conj.certify(g)
                    if cert is not None:
                        return HuntOutcome(conj.id, n, seed, step + 1, "certified_counterexample",
                                           best_score, g, cert, history)
        temp *= cooling

    g = Graph(n, frozenset(best))
    if best_score < 0.05:                                  # near-boundary: let the EXACT gate decide
        cert = conj.certify(g)
        if cert is not None:
            return HuntOutcome(conj.id, n, seed, steps, "certified_counterexample",
                               best_score, g, cert, history)
    status = "float_candidate_uncertified" if best_score < 0 else "not_found_within_budget"
    return HuntOutcome(conj.id, n, seed, steps, status, best_score,
                       g if best_score < 0 else None, None, history)


def _cycle_edges(edges: set, n: int, closing: tuple) -> list:
    """The edges of the unique cycle created in a tree by `closing` = (u, v): the u→v tree path + it."""
    adj = _adj_from(edges - {closing}, n)
    u, v = closing
    parent = {u: None}
    stack = [u]
    while stack:
        x = stack.pop()
        if x == v:
            break
        for w in adj[x]:
            if w not in parent:
                parent[w] = x
                stack.append(w)
    path = []
    x = v
    while parent[x] is not None:
        p = parent[x]
        path.append((min(p, x), max(p, x)))
        x = p
    return path + [closing]


# --- the A–H calibration instrument (v2B2) -------------------------------------------------------
def double_star(a: int, b: int, subdiv: int = 0) -> Graph:
    """Two star centers joined by a path with `subdiv` internal vertices; a and b leaves. The
    subdivided balanced form D(k,k,1) is exactly 'two balanced stars whose centers are joined by a
    path' — the shape of Wagner's RL-found witness."""
    edges = []
    path = [0] + list(range(2, 2 + subdiv)) + [1]
    for x, y in zip(path, path[1:]):
        edges.append((min(x, y), max(x, y)))
    nxt = 2 + subdiv
    for _ in range(a):
        edges.append((0, nxt)); nxt += 1
    for _ in range(b):
        edges.append((1, nxt)); nxt += 1
    return Graph.from_edges(nxt, edges)


def ah_calibration(n_cap: int = 30):
    """The v2B2 calibration sweep: scan the (subdivided) double-star families up to n_cap and return
    every EXACT-certified violation of the transcribed A–H statement, smallest n first. Deterministic;
    every verdict is a pure-integer certificate (never floats)."""
    from .conjecture_db import AH_SPECTRAL_MATCHING as AH
    found = []
    for subdiv in (0, 1, 2):
        for a in range(4, 16):
            for b in range(a, 17):
                g = double_star(a, b, subdiv)
                if g.n > n_cap or g.n < 3:
                    continue
                cert = AH.certify(g)
                if cert is not None:
                    found.append({"n": g.n, "a": a, "b": b, "subdiv": subdiv,
                                  "certificate": cert, "graph": g})
    found.sort(key=lambda w: (w["n"], w["subdiv"], w["a"], w["b"]))
    return found
