"""
mathhead.discovery.frankl — the LIVE hunt on a genuinely open conjecture (v2B3): Frankl's union-closed
sets conjecture (1979).

STATEMENT (transcription-certain): every finite union-closed family of sets, other than {∅}, has an
element that belongs to at least half of the sets. A VIOLATION is a union-closed family F ≠ {∅}, F ≠ ∅,
in which EVERY element x satisfies 2·freq(x) < |F| (strict, pure integers) — a self-verifying witness.

STATUS: OPEN. Known partial results (as recorded, not re-proved here): Gilmer (2022) proved a constant
fraction; follow-ups reached (3−√5)/2 ≈ 0.381966, with examples showing that technique cannot pass that
constant; the full 1/2 remains open. Literature reports exhaustive verification for small universes —
we do NOT rely on that: our own FORMALIZATION GUARD exhaustively verifies the conjecture on every
union-closed family over universes m ≤ 3 (256 candidate families) and, on demand, m = 4 (65 536).

HONEST EXPECTATION, stated up front: a witness would refute a 45-year conjecture; the overwhelmingly
likely outcome of any bounded hunt is `not_found_within_budget`, and that is what we report. The value
is the INSTRUMENT: the engine now hunts on a live open problem with exact-integer verdicts.

Representation: sets are int BITMASKS over universe [m]; a family is a frozenset of masks; union = OR.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

FRANKL_INFO = {
    "id": "FRANKL_UNION_CLOSED",
    "statement": "every finite union-closed family F != {emptyset} has an element in >= |F|/2 sets",
    "status": "open",
    "source": "P. Frankl, 1979; Gilmer 2022 (constant fraction) and follow-ups to (3-sqrt(5))/2; "
              "full 1/2 OPEN as recorded at engine-build time",
    "violation_form": "F union-closed, F != {0}, |F| > 0, and for EVERY element x: 2*freq(x) < |F|",
}


def union_closure(gens, cap: int = 4096):
    """The union-closure of generator masks (BFS under OR). Returns None if it would exceed cap —
    an explicit refusal, never a silent truncation."""
    fam = set(gens)
    frontier = list(fam)
    while frontier:
        nxt = []
        for a in frontier:
            for b in list(fam):
                u = a | b
                if u not in fam:
                    fam.add(u)
                    nxt.append(u)
                    if len(fam) > cap:
                        return None
        frontier = nxt
    return frozenset(fam)


def is_union_closed(fam) -> bool:
    fs = set(fam)
    return all((a | b) in fs for a in fs for b in fs)


def frequencies(fam, m: int) -> list:
    """freq[x] = number of sets containing element x — exact integers."""
    return [sum(1 for a in fam if a >> x & 1) for x in range(m)]


def certify_violation(fam, m: int):
    """EXACT verdict: a pure-integer certificate that `fam` violates Frankl, or None. Checks the FULL
    definition — union-closure included — so a bogus state can never certify."""
    fam = frozenset(fam)
    if not fam or fam == frozenset({0}) or not is_union_closed(fam):
        return None
    size = len(fam)
    freqs = frequencies(fam, m)
    union_all = 0
    for a in fam:
        union_all |= a
    if union_all == 0:
        return None                                        # fam == {∅} case, already excluded
    if all(2 * freqs[x] < size for x in range(m) if union_all >> x & 1):
        return {"family_size": size, "universe": m,
                "max_2freq": max(2 * freqs[x] for x in range(m) if union_all >> x & 1),
                "frequencies": freqs, "certainty": "exact_integer_certificate",
                "meaning": "REFUTES Frankl's union-closed conjecture — every element in < half the sets"}
    return None


@dataclass
class FranklGuard:
    universe: int
    families_checked: int = 0
    union_closed: int = 0
    violations: int = 0

    @property
    def formalization_ok(self) -> bool:
        return self.violations == 0


def guard_exhaustive(m: int) -> FranklGuard:
    """FORMALIZATION GUARD: enumerate EVERY family over subsets of [m] (2^(2^m) of them — m ≤ 4 only),
    and verify the conjecture holds on every union-closed one. A violation here would mean our
    formalization is wrong (or history is), and the test suite fails."""
    if m > 4:
        raise ValueError("exhaustive guard is honest only for m <= 4 (2^(2^m) families)")
    n_masks = 1 << m
    rep = FranklGuard(m)
    for code in range(1, 1 << n_masks):                    # nonempty families
        fam = frozenset(i for i in range(n_masks) if code >> i & 1)
        rep.families_checked += 1
        if not is_union_closed(fam):
            continue
        rep.union_closed += 1
        if certify_violation(fam, m) is not None:
            rep.violations += 1
    return rep


@dataclass
class FranklHunt:
    universe: int
    seed: int
    steps: int
    status: str                  # "certified_counterexample" | "not_found_within_budget"
    best_score: int              # max_x(2·freq) − |F| over the best state (≤ −1 would be a violation)
    best_family_size: int = 0
    certificate: dict | None = None
    history: list = field(default_factory=list)


def _score(fam, m: int) -> int:
    """max over live elements of 2·freq(x) − |F| — integer; ≤ −1 ⟺ violation. Minimize."""
    size = len(fam)
    union_all = 0
    for a in fam:
        union_all |= a
    if union_all == 0:
        return 10 ** 9
    return max(2 * f - size for x, f in enumerate(frequencies(fam, m)) if union_all >> x & 1)


def hunt_frankl(m: int = 7, seed: int = 0, steps: int = 4000, n_gens: int = 8,
                cap: int = 2000) -> FranklHunt:
    """Seeded SA over GENERATOR sets (the family = union-closure of the generators, size-capped with
    explicit refusal). Deterministic per (m, seed, steps). The verdict is `certify_violation` — exact."""
    rng = random.Random(seed)
    full = (1 << m) - 1
    gens = [rng.randrange(1, full + 1) for _ in range(n_gens)]
    fam = union_closure(gens, cap) or frozenset(gens)
    cur = _score(fam, m)
    best, best_fam = cur, fam
    history = []
    temp = 2.0
    for step in range(steps):
        cand_gens = list(gens)
        move = rng.random()
        if move < 0.45 or len(cand_gens) <= 2:
            cand_gens.append(rng.randrange(1, full + 1))            # add a generator
        elif move < 0.9:
            cand_gens[rng.randrange(len(cand_gens))] = rng.randrange(1, full + 1)   # replace one
        else:
            cand_gens.pop(rng.randrange(len(cand_gens)))            # drop one
        cand_fam = union_closure(cand_gens, cap)
        if cand_fam is None or len(cand_fam) < 2:
            continue
        sc = _score(cand_fam, m)
        if sc <= cur or rng.random() < pow(2.718281828, -(sc - cur) / max(temp, 1e-9)):
            gens, fam, cur = cand_gens, cand_fam, sc
            if cur < best:
                best, best_fam = cur, fam
                history.append((step, best))
                if best <= -1:
                    cert = certify_violation(best_fam, m)           # the EXACT gate
                    if cert is not None:
                        return FranklHunt(m, seed, step + 1, "certified_counterexample",
                                          best, len(best_fam), cert, history)
        temp *= 0.999
    return FranklHunt(m, seed, steps, "not_found_within_budget", best, len(best_fam), None, history)
