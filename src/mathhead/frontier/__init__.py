"""
mathhead.frontier — Track B seed.

**Idea (Plan.md §2, Track B):** reduce hard/open problems to a **satisfiability**
question and solve them with Z3. SMT/SAT solvers have actually settled
decades-old open problems this way (Boolean Pythagorean Triples 2016, Keller
dimension 7 in 2020, Schur 5 in 2017).

**HONESTY boundary:** the small examples here are not the famous results
*themselves* — they are the **same reduction method**. The n=7825 bound of the
Boolean Pythagorean problem required a ~200 TB proof; we solve small n instantly.
*Same method, different scale.* This module's purpose is to show the method
concretely and working.

This layer uses NOT the user's input language but the problem's **programmatic
encoding** (the encoding logic lives here, safely). The output is again the
shared `ReasoningResult`.
"""
from __future__ import annotations

import math
import time
from typing import Any

import z3

from mathhead.core.logic import ReasoningResult
from mathhead.guardrails import solver_config


def _meta(t0: float, seed: int, timeout_ms: int, extra: dict | None = None) -> dict[str, Any]:
    meta = {
        "engine": "z3",
        "z3_version": z3.get_version_string(),
        "elapsed_ms": round((time.perf_counter() - t0) * 1000, 3),
        "seed": seed,
        "timeout_ms": timeout_ms,
    }
    if extra:
        meta.update(extra)
    return meta


def _unknown(solver: z3.Solver, t0: float, seed: int, timeout_ms: int, extra: dict) -> ReasoningResult:
    reason = solver.reason_unknown()
    code = "SOLVER_TIMEOUT" if reason == "timeout" else "SOLVER_UNKNOWN"
    return ReasoningResult(
        "unknown", code,
        f"The solver could not decide at this scale ({reason}). The method is correct; the scale is large.",
        None, _meta(t0, seed, timeout_ms, extra),
    )


def _break_color_symmetry(solver: z3.Solver, cmap: dict, n: int, colors: int) -> None:
    """Breaks the color-permutation symmetry.

    Since colors are interchangeable, every coloring has (colors!) equivalent
    copies. Eliminating them does NOT change the `sat`/`unsat` result (if a
    solution exists, a symmetric one does too) but shrinks the search space → faster.

    * 2-color: the first element's color is fixed (factor 2).
    * r-color: colors are forced to be used in "first-seen order" 0,1,2,…
      (lex-leader; factor r!).
    """
    if n < 1:
        return
    if colors == 2:
        solver.add(cmap[1])  # first element = color A
        return
    solver.add(cmap[1] == 0)
    prev_max = z3.IntVal(0)
    for i in range(2, n + 1):
        solver.add(cmap[i] <= prev_max + 1)   # a new color can only be the next index
        mi = z3.Int(f"__cmax_{i}")
        solver.add(mi == z3.If(cmap[i] > prev_max, cmap[i], prev_max))
        prev_max = mi


def pythagorean_triples(n: int) -> list[tuple[int, int, int]]:
    """Returns all Pythagorean triples (a² + b² = c², a≤b) within {1..n}."""
    triples = []
    for a in range(1, n + 1):
        for b in range(a, n + 1):
            s = a * a + b * b
            c = math.isqrt(s)
            if c * c == s and c <= n:
                triples.append((a, b, c))
    return triples


def boolean_pythagorean_coloring(n: int, *, timeout_ms: int = 10_000, seed: int = 42) -> ReasoningResult:
    """Can the numbers {1..n} be 2-colored **with no monochromatic Pythagorean triple**?

    Reduction: a Boolean `c_i` for each i (True=red). For every (a,b,c) triple,
    the constraints "not all red" and "not all blue". SAT -> a coloring exists;
    UNSAT -> impossible (a proof).

    (This is the *same* encoding as the ~200 TB proof that showed in 2016 that
    n=7825 cannot be colored; we solve small n.)
    """
    t0 = time.perf_counter()
    if not isinstance(n, int) or n < 1 or n > 3000:
        return ReasoningResult(
            "error", "GUARDRAIL_VIOLATION", "n must be an integer in 1..3000",
            None, _meta(t0, seed, timeout_ms),
        )
    triples = pythagorean_triples(n)
    color = {i: z3.Bool(f"c_{i}") for i in range(1, n + 1)}
    solver = solver_config(timeout_ms, seed)
    for a, b, c in triples:
        solver.add(z3.Or(z3.Not(color[a]), z3.Not(color[b]), z3.Not(color[c])))  # not all red
        solver.add(z3.Or(color[a], color[b], color[c]))                          # not all blue

    extra = {"n": n, "pythagorean_triples": len(triples)}
    result = solver.check()
    if result == z3.sat:
        model = solver.model()
        reds = [i for i in range(1, n + 1) if z3.is_true(model.eval(color[i], model_completion=True))]
        if n <= 60:
            coloring = {i: ("red" if i in set(reds) else "blue") for i in range(1, n + 1)}
            witness: dict[str, Any] = {"coloring": coloring}
        else:
            witness = {"red_count": len(reds), "blue_count": n - len(reds),
                       "note": "coloring too long; summarized"}
        return ReasoningResult(
            "sat", "COLORING_FOUND",
            f"{{1..{n}}} can be 2-colored with no monochromatic Pythagorean triple "
            f"({len(triples)} triple constraints satisfied).",
            witness, _meta(t0, seed, timeout_ms, extra),
        )
    if result == z3.unsat:
        return ReasoningResult(
            "unsat", "NO_COLORING",
            f"{{1..{n}}} CANNOT be colored this way — a monochromatic Pythagorean triple is unavoidable "
            f"(impossibility proved).",
            {"note": "this is an impossibility proof"}, _meta(t0, seed, timeout_ms, extra),
        )
    return _unknown(solver, t0, seed, timeout_ms, extra)


def pigeonhole(n: int, *, timeout_ms: int = 10_000, seed: int = 42) -> ReasoningResult:
    """Can `n+1` pigeons be placed into `n` holes without collision? (pigeonhole)

    Expected: **unsat** — i.e. the engine *proves* the pigeonhole principle. An
    example of proving a classic theorem by reduction. (Note: PHP is exponentially
    hard for CDCL; large n may time out — this honestly returns `unknown`.)
    """
    t0 = time.perf_counter()
    if not isinstance(n, int) or n < 1 or n > 10:
        return ReasoningResult(
            "error", "GUARDRAIL_VIOLATION",
            "n must be an integer in 1..10 (PHP is exponentially hard for the solver)",
            None, _meta(t0, seed, timeout_ms),
        )
    pigeons, holes = n + 1, n
    p = [[z3.Bool(f"p_{i}_{j}") for j in range(holes)] for i in range(pigeons)]
    solver = solver_config(timeout_ms, seed)
    for i in range(pigeons):                        # each pigeon in at least one hole
        solver.add(z3.Or(*p[i]))
    for j in range(holes):                          # no hole has two pigeons
        for i1 in range(pigeons):
            for i2 in range(i1 + 1, pigeons):
                solver.add(z3.Or(z3.Not(p[i1][j]), z3.Not(p[i2][j])))

    extra = {"pigeons": pigeons, "holes": holes}
    result = solver.check()
    if result == z3.unsat:
        return ReasoningResult(
            "unsat", "PROVEN_IMPOSSIBLE",
            f"{pigeons} pigeons CANNOT be placed into {holes} holes without collision — "
            f"the pigeonhole principle is proved.",
            {"note": "impossibility proof (theorem)"}, _meta(t0, seed, timeout_ms, extra),
        )
    if result == z3.sat:
        return ReasoningResult(
            "sat", "UNEXPECTED_SAT",
            "Unexpected: a placement was found (by the principle it should not exist).",
            None, _meta(t0, seed, timeout_ms, extra),
        )
    return _unknown(solver, t0, seed, timeout_ms, extra)


def arithmetic_progressions(n: int, k: int) -> list[tuple[int, ...]]:
    """Returns all k-term arithmetic progressions within {1..n}."""
    aps: list[tuple[int, ...]] = []
    for a in range(1, n + 1):
        max_d = (n - a) // (k - 1) if k > 1 else 0
        for d in range(1, max_d + 1):
            aps.append(tuple(a + i * d for i in range(k)))
    return aps


def van_der_waerden_coloring(
    n: int, k: int, colors: int = 2, *, timeout_ms: int = 20_000, seed: int = 42,
    symmetry_break: bool = False,
) -> ReasoningResult:
    """Can {1..n} be `colors`-colored **with no monochromatic k-term arithmetic progression**?

    This is the core of computing the van der Waerden number W(colors, k) via SAT:
    W(r,k) = the smallest n at which the coloring becomes impossible. `sat` -> a
    coloring exists (n < W); `unsat` -> impossible (n ≥ W, a proof); `unknown` ->
    the scale exceeded the solver.

    HONESTY: known W values were computed with THIS METHOD (same code). Large/open
    values (e.g. W(2,7)) demand enormous computation; there the engine honestly
    returns `unknown`.
    """
    t0 = time.perf_counter()
    if not all(isinstance(x, int) for x in (n, k, colors)):
        return ReasoningResult("error", "GUARDRAIL_VIOLATION", "n, k, colors must be integers",
                               None, _meta(t0, seed, timeout_ms))
    if k < 2 or colors < 2 or colors > 6 or n < 1 or n > 5000:
        return ReasoningResult("error", "GUARDRAIL_VIOLATION",
                               "must have k≥2, colors 2..6, 1≤n≤5000",
                               None, _meta(t0, seed, timeout_ms))

    aps = arithmetic_progressions(n, k)
    solver = solver_config(timeout_ms, seed)
    if colors == 2:
        c = {i: z3.Bool(f"c_{i}") for i in range(1, n + 1)}
        for ap in aps:
            solver.add(z3.Or(*[z3.Not(c[i]) for i in ap]))  # not all color-A
            solver.add(z3.Or(*[c[i] for i in ap]))          # not all color-B
    else:
        c = {i: z3.Int(f"c_{i}") for i in range(1, n + 1)}
        for i in range(1, n + 1):
            solver.add(c[i] >= 0, c[i] < colors)
        for ap in aps:
            solver.add(z3.Or(*[c[ap[j]] != c[ap[j + 1]] for j in range(len(ap) - 1)]))

    if symmetry_break:
        _break_color_symmetry(solver, c, n, colors)
    extra = {"n": n, "k": k, "colors": colors, "arithmetic_progressions": len(aps),
             "symmetry_break": symmetry_break}
    result = solver.check()
    if result == z3.sat:
        model = solver.model()
        if colors == 2:
            coloring = {i: ("A" if z3.is_true(model.eval(c[i], model_completion=True)) else "B")
                        for i in range(1, n + 1)}
        else:
            coloring = {i: model.eval(c[i], model_completion=True).as_long()
                        for i in range(1, n + 1)}
        witness = {"coloring": coloring} if n <= 60 else {"note": f"{n} numbers colored (summary hidden)"}
        return ReasoningResult(
            "sat", "COLORING_FOUND",
            f"{{1..{n}}} can be {colors}-colored with no monochromatic {k}-term arithmetic progression "
            f"→ W({colors},{k}) > {n}.",
            witness, _meta(t0, seed, timeout_ms, extra),
        )
    if result == z3.unsat:
        return ReasoningResult(
            "unsat", "NO_COLORING",
            f"{{1..{n}}} CANNOT be colored this way — a monochromatic {k}-term arithmetic progression is unavoidable "
            f"→ W({colors},{k}) ≤ {n} (impossibility proved).",
            {"note": "impossibility proof"}, _meta(t0, seed, timeout_ms, extra),
        )
    return _unknown(solver, t0, seed, timeout_ms, extra)


def schur_number_coloring(
    n: int, colors: int, *, timeout_ms: int = 20_000, seed: int = 42,
    symmetry_break: bool = False,
) -> ReasoningResult:
    """Can {1..n} be `colors`-colored so that no color class contains `x + y = z`
    (same color)? (i.e. is every color class **sum-free**; x=y is allowed).

    The Schur number S(r) = the largest n colorable this way. `n ≤ S(r)` -> `sat`;
    `n = S(r)+1` -> `unsat` (a proof). Known: S(2)=4, S(3)=13, S(4)=44, S(5)=160.
    **S(6) is OPEN.** Known values were computed with this method; large scale is enormous.
    """
    t0 = time.perf_counter()
    if not all(isinstance(x, int) for x in (n, colors)):
        return ReasoningResult("error", "GUARDRAIL_VIOLATION", "n, colors must be integers",
                               None, _meta(t0, seed, timeout_ms))
    if colors < 2 or colors > 6 or n < 1 or n > 500:
        return ReasoningResult("error", "GUARDRAIL_VIOLATION",
                               "must have colors 2..6, 1≤n≤500", None, _meta(t0, seed, timeout_ms))

    solver = solver_config(timeout_ms, seed)
    triples = 0
    if colors == 2:
        c = {i: z3.Bool(f"c_{i}") for i in range(1, n + 1)}
        for x in range(1, n + 1):
            for y in range(x, n + 1):
                z = x + y
                if z > n:
                    break
                solver.add(z3.Or(z3.Not(c[x]), z3.Not(c[y]), z3.Not(c[z])))
                solver.add(z3.Or(c[x], c[y], c[z]))
                triples += 1
    else:
        c = {i: z3.Int(f"c_{i}") for i in range(1, n + 1)}
        for i in range(1, n + 1):
            solver.add(c[i] >= 0, c[i] < colors)
        for x in range(1, n + 1):
            for y in range(x, n + 1):
                z = x + y
                if z > n:
                    break
                solver.add(z3.Or(c[x] != c[y], c[y] != c[z]))
                triples += 1

    if symmetry_break:
        _break_color_symmetry(solver, c, n, colors)
    extra = {"n": n, "colors": colors, "sum_triples": triples, "symmetry_break": symmetry_break}
    result = solver.check()
    if result == z3.sat:
        model = solver.model()
        if colors == 2:
            coloring = {i: (0 if z3.is_true(model.eval(c[i], model_completion=True)) else 1)
                        for i in range(1, n + 1)}
        else:
            coloring = {i: model.eval(c[i], model_completion=True).as_long()
                        for i in range(1, n + 1)}
        witness = {"coloring": coloring} if n <= 60 else {"note": f"{n} numbers partitioned (summary)"}
        return ReasoningResult(
            "sat", "COLORING_FOUND",
            f"{{1..{n}}} can be partitioned into {colors} sum-free colors → S({colors}) ≥ {n}.",
            witness, _meta(t0, seed, timeout_ms, extra),
        )
    if result == z3.unsat:
        return ReasoningResult(
            "unsat", "NO_COLORING",
            f"{{1..{n}}} CANNOT be partitioned into {colors} sum-free colors → S({colors}) < {n} "
            f"(impossibility proved).",
            {"note": "impossibility proof"}, _meta(t0, seed, timeout_ms, extra),
        )
    return _unknown(solver, t0, seed, timeout_ms, extra)


# --------------------------------------------------------------------------- #
# Phase 10 — new reductions + VERIFIABLE CERTIFICATE.
#
# Certificate philosophy: in the `sat` case the witness IS A CERTIFICATE. We
# re-check it INDEPENDENTLY of Z3, in pure Python (`verified: true`). Thus even
# an encoding/translation error is caught, and the positive proof becomes
# independently verifiable of the solver (a polynomial-time check).
#
# HONEST asymmetry: producing an independently-checkable DRAT/LRAT certificate
# for `unsat` requires a DIMACS-level SAT pipeline; this is documented plainly
# as a WALL (the Z3 decision is preserved, and the output notes this honestly).
# --------------------------------------------------------------------------- #
def graph_coloring(
    edges: list[list[int]], colors: int, n: int | None = None,
    *, timeout_ms: int = 10_000, seed: int = 42,
) -> ReasoningResult:
    """Colors a graph with `colors` colors so that adjacent vertices differ.

    A classic NP-complete problem (graph k-coloring). `sat` → a coloring was found
    (and INDEPENDENTLY verified); `unsat` → chromatic number > colors (not colorable).
    Vertices are 1-indexed.
    """
    t0 = time.perf_counter()
    if not isinstance(colors, int) or not isinstance(edges, list) or (n is not None and not isinstance(n, int)):
        return ReasoningResult("error", "GUARDRAIL_VIOLATION",
                               "edges must be a list, colors/n must be integers", None, _meta(t0, seed, timeout_ms))
    verts: set[int] = set()
    for e in edges:
        if not (isinstance(e, list) and len(e) == 2 and all(isinstance(v, int) for v in e)):
            return ReasoningResult("error", "GUARDRAIL_VIOLATION",
                                   "each edge must be [u, v] (integers)", None, _meta(t0, seed, timeout_ms))
        verts.update(e)
    maxv = max(verts) if verts else 0
    N = n if n is not None else maxv
    if colors < 1 or N < 1 or N > 300 or maxv > N or (verts and min(verts) < 1):
        return ReasoningResult("error", "GUARDRAIL_VIOLATION",
                               "must have 1≤vertex≤n≤300 and colors≥1", None, _meta(t0, seed, timeout_ms))

    solver = solver_config(timeout_ms, seed)
    col = {v: z3.Int(f"col_{v}") for v in range(1, N + 1)}
    for v in range(1, N + 1):
        solver.add(col[v] >= 0, col[v] < colors)
    for u, w in edges:
        solver.add(col[u] != col[w])
    extra = {"vertices": N, "edges": len(edges), "colors": colors}
    result = solver.check()
    if result == z3.sat:
        model = solver.model()
        coloring = {v: model.eval(col[v], model_completion=True).as_long() for v in range(1, N + 1)}
        # INDEPENDENT verification (without Z3): each edge's endpoints differ in color + color range
        ok = all(coloring[u] != coloring[w] for u, w in edges) and \
            all(0 <= coloring[v] < colors for v in coloring)
        if not ok:
            return ReasoningResult("error", "UNEXPECTED_SAT",
                                   "internal inconsistency: the witness failed independent verification",
                                   None, _meta(t0, seed, timeout_ms, extra))
        witness = {"coloring": coloring} if N <= 60 else {"note": f"{N} vertices colored (summary)"}
        return ReasoningResult("sat", "COLORING_FOUND",
                               f"the graph can be {colors}-colored (independently verified).",
                               witness, _meta(t0, seed, timeout_ms, {**extra, "verified": True}))
    if result == z3.unsat:
        return ReasoningResult("unsat", "NO_COLORING",
                               f"the graph CANNOT be {colors}-colored (chromatic number > {colors}).",
                               {"note": "impossibility proof (DRAT certificate: a wall, see docs)"},
                               _meta(t0, seed, timeout_ms, extra))
    return _unknown(solver, t0, seed, timeout_ms, extra)


def subset_sum(
    numbers: list[int], target: int, *, timeout_ms: int = 10_000, seed: int = 42,
) -> ReasoningResult:
    """Does a subset of `numbers` sum to `target`? (NP-complete subset-sum).

    `sat` → the summing subset (an INDEPENDENTLY verified certificate); `unsat` → none.
    """
    t0 = time.perf_counter()
    if not isinstance(numbers, list) or not numbers or not all(isinstance(x, int) for x in numbers):
        return ReasoningResult("error", "GUARDRAIL_VIOLATION",
                               "numbers must be a non-empty list of integers", None, _meta(t0, seed, timeout_ms))
    if not isinstance(target, int) or len(numbers) > 200:
        return ReasoningResult("error", "GUARDRAIL_VIOLATION",
                               "target must be an integer, |numbers|≤200", None, _meta(t0, seed, timeout_ms))

    solver = solver_config(timeout_ms, seed)
    xs = [z3.Bool(f"x_{i}") for i in range(len(numbers))]
    solver.add(z3.Sum([z3.If(xs[i], numbers[i], 0) for i in range(len(numbers))]) == target)
    extra = {"count": len(numbers), "target": target}
    result = solver.check()
    if result == z3.sat:
        model = solver.model()
        idx = [i for i in range(len(numbers)) if z3.is_true(model.eval(xs[i], model_completion=True))]
        subset = [numbers[i] for i in idx]
        # INDEPENDENT verification (without Z3): do the selected numbers really sum to target
        if sum(subset) != target:
            return ReasoningResult("error", "UNEXPECTED_SAT",
                                   "internal inconsistency: the witness failed independent verification",
                                   None, _meta(t0, seed, timeout_ms, extra))
        witness = {"subset": subset, "indices": idx}
        return ReasoningResult("sat", "MODEL_FOUND",
                               f"a subset sums to {target}: {subset} (independently verified).",
                               witness, _meta(t0, seed, timeout_ms, {**extra, "verified": True}))
    if result == z3.unsat:
        return ReasoningResult("unsat", "NO_MODEL",
                               f"no subset sums to {target}.",
                               {"note": "impossibility (DRAT certificate: a wall, see docs)"},
                               _meta(t0, seed, timeout_ms, extra))
    return _unknown(solver, t0, seed, timeout_ms, extra)
