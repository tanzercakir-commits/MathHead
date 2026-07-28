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
from itertools import combinations
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


# --------------------------------------------------------------------------- #
# ROADMAP J1 — new reductions. Every `sat` witness is INDEPENDENTLY verified in
# pure Python (meta.verified), the same certificate philosophy as Phase 10.
# --------------------------------------------------------------------------- #
def n_queens(n: int, *, timeout_ms: int = 10_000, seed: int = 42) -> ReasoningResult:
    """Place `n` non-attacking queens on an n×n board (the N-queens problem).

    Reduction: one Int per row (its queen's column); `Distinct` columns + distinct
    diagonals. `sat` → a placement (INDEPENDENTLY verified); `unsat` → impossible
    (n=2, n=3). Vertices/rows are 0-indexed.
    """
    t0 = time.perf_counter()
    if not isinstance(n, int) or n < 1 or n > 40:
        return ReasoningResult("error", "GUARDRAIL_VIOLATION", "n must be an integer in 1..40",
                               None, _meta(t0, seed, timeout_ms))
    col = [z3.Int(f"q_{i}") for i in range(n)]
    solver = solver_config(timeout_ms, seed)
    for i in range(n):
        solver.add(col[i] >= 0, col[i] < n)
    solver.add(z3.Distinct(col))
    for i in range(n):
        for j in range(i + 1, n):
            solver.add(col[i] - col[j] != i - j, col[i] - col[j] != j - i)  # diagonals
    extra = {"n": n}
    result = solver.check()
    if result == z3.sat:
        model = solver.model()
        pos = [model.eval(col[i], model_completion=True).as_long() for i in range(n)]
        ok = (len(set(pos)) == n
              and all(abs(pos[i] - pos[j]) != abs(i - j) for i in range(n) for j in range(i + 1, n)))
        if not ok:
            return ReasoningResult("error", "UNEXPECTED_SAT",
                                   "internal inconsistency: the placement failed independent verification",
                                   None, _meta(t0, seed, timeout_ms, extra))
        witness = {"columns": pos} if n <= 60 else {"note": f"{n} queens placed (summary)"}
        return ReasoningResult("sat", "MODEL_FOUND",
                               f"{n} non-attacking queens can be placed (independently verified).",
                               witness, _meta(t0, seed, timeout_ms, {**extra, "verified": True}))
    if result == z3.unsat:
        return ReasoningResult("unsat", "NO_MODEL",
                               f"{n} non-attacking queens cannot be placed on an {n}×{n} board.",
                               {"note": "impossibility proof"}, _meta(t0, seed, timeout_ms, extra))
    return _unknown(solver, t0, seed, timeout_ms, extra)


def latin_square(n: int, givens: list[list[int]] | None = None,
                 *, timeout_ms: int = 10_000, seed: int = 42) -> ReasoningResult:
    """Complete an n×n LATIN SQUARE (each symbol 1..n once per row and per column).

    `givens` (optional) is an n×n grid with 0 for blanks. `sat` → a completed square
    (INDEPENDENTLY verified); `unsat` → the givens cannot be completed.
    """
    t0 = time.perf_counter()
    if not isinstance(n, int) or n < 1 or n > 20:
        return ReasoningResult("error", "GUARDRAIL_VIOLATION", "n must be an integer in 1..20",
                               None, _meta(t0, seed, timeout_ms))
    if givens is not None and (not isinstance(givens, list) or len(givens) != n
                               or any(not isinstance(r, list) or len(r) != n for r in givens)):
        return ReasoningResult("error", "GUARDRAIL_VIOLATION", "givens must be an n×n grid (0 = blank)",
                               None, _meta(t0, seed, timeout_ms))
    cell = [[z3.Int(f"c_{r}_{c}") for c in range(n)] for r in range(n)]
    solver = solver_config(timeout_ms, seed)
    for r in range(n):
        for c in range(n):
            solver.add(cell[r][c] >= 1, cell[r][c] <= n)
    for r in range(n):
        solver.add(z3.Distinct(cell[r]))
    for c in range(n):
        solver.add(z3.Distinct([cell[r][c] for r in range(n)]))
    if givens is not None:
        for r in range(n):
            for c in range(n):
                if givens[r][c]:
                    if not (1 <= givens[r][c] <= n):
                        return ReasoningResult("error", "GUARDRAIL_VIOLATION",
                                               f"given at ({r},{c}) out of range 1..{n}",
                                               None, _meta(t0, seed, timeout_ms))
                    solver.add(cell[r][c] == givens[r][c])
    extra = {"n": n}
    result = solver.check()
    if result == z3.sat:
        model = solver.model()
        grid = [[model.eval(cell[r][c], model_completion=True).as_long() for c in range(n)]
                for r in range(n)]
        rows_ok = all(sorted(grid[r]) == list(range(1, n + 1)) for r in range(n))
        cols_ok = all(sorted(grid[r][c] for r in range(n)) == list(range(1, n + 1)) for c in range(n))
        given_ok = givens is None or all(not givens[r][c] or grid[r][c] == givens[r][c]
                                         for r in range(n) for c in range(n))
        if not (rows_ok and cols_ok and given_ok):
            return ReasoningResult("error", "UNEXPECTED_SAT",
                                   "internal inconsistency: the square failed independent verification",
                                   None, _meta(t0, seed, timeout_ms, extra))
        return ReasoningResult("sat", "MODEL_FOUND",
                               f"a {n}×{n} Latin square was found (independently verified).",
                               {"grid": grid}, _meta(t0, seed, timeout_ms, {**extra, "verified": True}))
    if result == z3.unsat:
        return ReasoningResult("unsat", "NO_MODEL",
                               "the givens cannot be completed to a Latin square.",
                               {"note": "impossibility proof"}, _meta(t0, seed, timeout_ms, extra))
    return _unknown(solver, t0, seed, timeout_ms, extra)


def sudoku_solve(givens: list[list[int]], *, timeout_ms: int = 20_000, seed: int = 42) -> ReasoningResult:
    """Solve a 9×9 SUDOKU. `givens` is a 9×9 grid with 0 for blanks.

    Reduction: Int per cell 1..9; each row, column, and 3×3 box `Distinct`; givens fixed.
    `sat` → the solution (INDEPENDENTLY verified: rows/cols/boxes are permutations of
    1..9 and the givens are respected); `unsat` → the puzzle has no solution.
    """
    t0 = time.perf_counter()
    if (not isinstance(givens, list) or len(givens) != 9
            or any(not isinstance(r, list) or len(r) != 9 for r in givens)
            or any(not isinstance(v, int) or not (0 <= v <= 9) for r in givens for v in r)):
        return ReasoningResult("error", "GUARDRAIL_VIOLATION",
                               "givens must be a 9×9 grid of integers 0..9 (0 = blank)",
                               None, _meta(t0, seed, timeout_ms))
    cell = [[z3.Int(f"s_{r}_{c}") for c in range(9)] for r in range(9)]
    solver = solver_config(timeout_ms, seed)
    for r in range(9):
        for c in range(9):
            solver.add(cell[r][c] >= 1, cell[r][c] <= 9)
            if givens[r][c]:
                solver.add(cell[r][c] == givens[r][c])
    for r in range(9):
        solver.add(z3.Distinct(cell[r]))
    for c in range(9):
        solver.add(z3.Distinct([cell[r][c] for r in range(9)]))
    for br in range(0, 9, 3):
        for bc in range(0, 9, 3):
            solver.add(z3.Distinct([cell[br + dr][bc + dc] for dr in range(3) for dc in range(3)]))
    extra = {"clues": sum(1 for r in givens for v in r if v)}
    result = solver.check()
    if result == z3.sat:
        model = solver.model()
        grid = [[model.eval(cell[r][c], model_completion=True).as_long() for c in range(9)]
                for r in range(9)]
        full = list(range(1, 10))
        ok = (all(sorted(grid[r]) == full for r in range(9))
              and all(sorted(grid[r][c] for r in range(9)) == full for c in range(9))
              and all(sorted(grid[br + dr][bc + dc] for dr in range(3) for dc in range(3)) == full
                      for br in range(0, 9, 3) for bc in range(0, 9, 3))
              and all(not givens[r][c] or grid[r][c] == givens[r][c] for r in range(9) for c in range(9)))
        if not ok:
            return ReasoningResult("error", "UNEXPECTED_SAT",
                                   "internal inconsistency: the solution failed independent verification",
                                   None, _meta(t0, seed, timeout_ms, extra))
        return ReasoningResult("sat", "MODEL_FOUND",
                               "the Sudoku has a solution (independently verified).",
                               {"grid": grid}, _meta(t0, seed, timeout_ms, {**extra, "verified": True}))
    if result == z3.unsat:
        return ReasoningResult("unsat", "NO_MODEL", "this Sudoku has no solution.",
                               {"note": "impossibility proof"}, _meta(t0, seed, timeout_ms, extra))
    return _unknown(solver, t0, seed, timeout_ms, extra)


def hamiltonian_path(edges: list[list[int]], n: int, cycle: bool = False,
                     *, timeout_ms: int = 15_000, seed: int = 42) -> ReasoningResult:
    """Is there a HAMILTONIAN path (or `cycle`) visiting every vertex exactly once?

    Vertices are 0-indexed `0..n-1`; `edges` is an undirected `[[u, v], ...]`. Reduction:
    an Int `position` per vertex (`Distinct`); consecutive positions must be adjacent.
    NP-complete. `sat` → the order (INDEPENDENTLY verified against the edge set);
    `unsat` → none exists.
    """
    t0 = time.perf_counter()
    if not isinstance(n, int) or n < 1 or n > 60 or not isinstance(edges, list):
        return ReasoningResult("error", "GUARDRAIL_VIOLATION",
                               "n must be an integer in 1..60 and edges a list", None, _meta(t0, seed, timeout_ms))
    eset: set[frozenset] = set()
    for e in edges:
        if not (isinstance(e, list) and len(e) == 2 and all(isinstance(v, int) and 0 <= v < n for v in e)) or e[0] == e[1]:
            return ReasoningResult("error", "GUARDRAIL_VIOLATION",
                                   "each edge must be [u, v] with 0≤u,v<n and u≠v", None, _meta(t0, seed, timeout_ms))
        eset.add(frozenset(e))
    pos = [z3.Int(f"p_{v}") for v in range(n)]
    solver = solver_config(timeout_ms, seed)
    for v in range(n):
        solver.add(pos[v] >= 0, pos[v] < n)
    solver.add(z3.Distinct(pos))
    for u in range(n):
        for v in range(n):
            if u != v and frozenset((u, v)) not in eset:
                solver.add(pos[v] != pos[u] + 1)                 # non-adjacent can't be consecutive
                if cycle:
                    solver.add(z3.Not(z3.And(pos[u] == n - 1, pos[v] == 0)))  # nor wrap-around
    extra = {"n": n, "edges": len(eset), "cycle": cycle}
    result = solver.check()
    if result == z3.sat:
        model = solver.model()
        order = sorted(range(n), key=lambda v: model.eval(pos[v], model_completion=True).as_long())
        seq = order + ([order[0]] if cycle else [])
        ok = (len(set(order)) == n
              and all(frozenset((seq[i], seq[i + 1])) in eset for i in range(len(seq) - 1)))
        if not ok and n > 1:
            return ReasoningResult("error", "UNEXPECTED_SAT",
                                   "internal inconsistency: the path failed independent verification",
                                   None, _meta(t0, seed, timeout_ms, extra))
        kind = "cycle" if cycle else "path"
        return ReasoningResult("sat", "MODEL_FOUND",
                               f"a Hamiltonian {kind} exists (independently verified).",
                               {"order": order}, _meta(t0, seed, timeout_ms, {**extra, "verified": True}))
    if result == z3.unsat:
        kind = "cycle" if cycle else "path"
        return ReasoningResult("unsat", "NO_MODEL", f"no Hamiltonian {kind} exists.",
                               {"note": "impossibility proof"}, _meta(t0, seed, timeout_ms, extra))
    return _unknown(solver, t0, seed, timeout_ms, extra)


def ramsey_coloring(n: int, s: int, t: int, *, timeout_ms: int = 20_000, seed: int = 42) -> ReasoningResult:
    """2-color the EDGES of the complete graph K_n avoiding a red K_s and a blue K_t.

    The Ramsey number R(s,t) = the least n where this becomes impossible. `sat` → a
    coloring exists (n < R(s,t)); `unsat` → impossible (n ≥ R(s,t), a proof). Known:
    R(3,3)=6, so n=5 is `sat` and n=6 is `unsat`. The coloring is INDEPENDENTLY verified.
    """
    t0 = time.perf_counter()
    if not all(isinstance(x, int) for x in (n, s, t)) or n < 1 or n > 12 or s < 2 or t < 2 or s > n + 1 or t > n + 1:
        return ReasoningResult("error", "GUARDRAIL_VIOLATION",
                               "need integers with 1≤n≤12, 2≤s,t≤n+1", None, _meta(t0, seed, timeout_ms))
    red = {frozenset(c): z3.Bool(f"e_{min(c)}_{max(c)}") for c in combinations(range(n), 2)}
    solver = solver_config(timeout_ms, seed)
    for clique in combinations(range(n), s):                      # no all-red K_s
        solver.add(z3.Or(*[z3.Not(red[frozenset(c)]) for c in combinations(clique, 2)]))
    for clique in combinations(range(n), t):                      # no all-blue K_t
        solver.add(z3.Or(*[red[frozenset(c)] for c in combinations(clique, 2)]))
    extra = {"n": n, "s": s, "t": t, "edges": len(red)}
    result = solver.check()
    if result == z3.sat:
        model = solver.model()
        color = {c: bool(z3.is_true(model.eval(red[frozenset(c)], model_completion=True)))
                 for c in (frozenset(x) for x in combinations(range(n), 2))}

        def mono(clique, want):
            return all(color[frozenset(c)] == want for c in combinations(clique, 2))
        ok = (not any(mono(cl, True) for cl in combinations(range(n), s))
              and not any(mono(cl, False) for cl in combinations(range(n), t)))
        if not ok:
            return ReasoningResult("error", "UNEXPECTED_SAT",
                                   "internal inconsistency: the coloring failed independent verification",
                                   None, _meta(t0, seed, timeout_ms, extra))
        red_edges = [list(c) for c in combinations(range(n), 2) if color[frozenset(c)]]
        return ReasoningResult("sat", "COLORING_FOUND",
                               f"K_{n}'s edges can be 2-colored with no red K_{s} and no blue K_{t} "
                               f"→ R({s},{t}) > {n} (independently verified).",
                               {"red_edges": red_edges}, _meta(t0, seed, timeout_ms, {**extra, "verified": True}))
    if result == z3.unsat:
        return ReasoningResult("unsat", "NO_COLORING",
                               f"K_{n} cannot avoid both a red K_{s} and a blue K_{t} → R({s},{t}) ≤ {n} "
                               f"(impossibility proved).",
                               {"note": "impossibility proof"}, _meta(t0, seed, timeout_ms, extra))
    return _unknown(solver, t0, seed, timeout_ms, extra)


def tsp_decision(distances: list[list[int]], budget: int,
                 *, timeout_ms: int = 20_000, seed: int = 42) -> ReasoningResult:
    """DECISION TSP: is there a tour visiting every city once with total length ≤ `budget`?

    `distances` is an n×n non-negative integer matrix. Reduction: directed arc booleans
    with in/out-degree 1 + MTZ subtour elimination + `Σ length ≤ budget`. `sat` → a tour
    (INDEPENDENTLY verified: a single Hamiltonian cycle whose cost ≤ budget); `unsat` → no
    tour meets the budget.
    """
    t0 = time.perf_counter()
    n = len(distances) if isinstance(distances, list) else 0
    if (n < 2 or n > 12 or any(not isinstance(row, list) or len(row) != n for row in distances)
            or any(not isinstance(d, int) or d < 0 for row in distances for d in row)):
        return ReasoningResult("error", "GUARDRAIL_VIOLATION",
                               "distances must be an n×n non-negative integer matrix, 2≤n≤12",
                               None, _meta(t0, seed, timeout_ms))
    if not isinstance(budget, int) or budget < 0:
        return ReasoningResult("error", "GUARDRAIL_VIOLATION", "budget must be a non-negative integer",
                               None, _meta(t0, seed, timeout_ms))
    y = {(i, j): z3.Bool(f"y_{i}_{j}") for i in range(n) for j in range(n) if i != j}
    u = [z3.Int(f"u_{i}") for i in range(n)]
    solver = solver_config(timeout_ms, seed)
    for i in range(n):
        solver.add(z3.Sum([z3.If(y[(i, j)], 1, 0) for j in range(n) if j != i]) == 1)  # out-degree 1
        solver.add(z3.Sum([z3.If(y[(j, i)], 1, 0) for j in range(n) if j != i]) == 1)  # in-degree 1
    solver.add(u[0] == 0)
    for i in range(1, n):
        solver.add(u[i] >= 1, u[i] <= n - 1)
    for i in range(1, n):
        for j in range(1, n):
            if i != j:
                solver.add(u[i] - u[j] + n * z3.If(y[(i, j)], 1, 0) <= n - 1)           # MTZ
    solver.add(z3.Sum([z3.If(y[(i, j)], distances[i][j], 0) for i in range(n) for j in range(n) if i != j]) <= budget)
    extra = {"n": n, "budget": budget}
    result = solver.check()
    if result == z3.sat:
        model = solver.model()
        succ = {i: next(j for j in range(n) if j != i and z3.is_true(model.eval(y[(i, j)], model_completion=True)))
                for i in range(n)}
        # independent check: follow successors → a single cycle over all cities, cost ≤ budget
        tour, cur = [0], 0
        for _ in range(n - 1):
            cur = succ[cur]
            tour.append(cur)
        cost = sum(distances[tour[k]][tour[(k + 1) % n]] for k in range(n))
        ok = sorted(tour) == list(range(n)) and cost <= budget
        if not ok:
            return ReasoningResult("error", "UNEXPECTED_SAT",
                                   "internal inconsistency: the tour failed independent verification",
                                   None, _meta(t0, seed, timeout_ms, extra))
        return ReasoningResult("sat", "MODEL_FOUND",
                               f"a tour of length {cost} ≤ {budget} exists (independently verified).",
                               {"tour": tour, "length": cost},
                               _meta(t0, seed, timeout_ms, {**extra, "verified": True}))
    if result == z3.unsat:
        return ReasoningResult("unsat", "NO_MODEL", f"no tour has total length ≤ {budget}.",
                               {"note": "impossibility proof"}, _meta(t0, seed, timeout_ms, extra))
    return _unknown(solver, t0, seed, timeout_ms, extra)
