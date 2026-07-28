#!/usr/bin/env python3
"""
MathHead — performance benchmark skeleton (ROADMAP Phase 5 [S]).

Runs representative operations N times, tabulates median/mean time (ms). Goal:
keep a *baseline* and make large regressions visible.

Note: Time depends on the environment — this is NOT a test *gate* (no time threshold in CI);
it's only a measurement/observation tool. For a regression fence: `tests/test_golden.py`.

Usage:
    python scripts/benchmark.py            # default N
    python scripts/benchmark.py --n 50
"""
from __future__ import annotations

import argparse
import statistics
import time
from dataclasses import asdict

from mathhead.router import route

# (label, task, payload) — a fast but representative slice (each layer)
WORKLOAD = [
    ("logic/entailment", "entailment", {"premises": ["p", "implies(p,q)"], "conclusion": "q"}),
    ("logic/consistency", "consistency", {"statements": ["x>2", "x<5", "x<10"]}),
    ("logic/prove", "prove", {"premises": ["p", "implies(p,q)"], "conclusion": "q"}),
    ("logic/optimize", "optimize", {"constraints": ["x>=0", "x<=100"], "objective": "x", "sense": "max"}),
    ("compute/simplify", "simplify", {"expression": "(x**2 - 1)/(x - 1)"}),
    ("compute/integrate", "integrate", {"expression": "x**3 + sin(x)", "symbol": "x"}),
    ("compute/limit", "limit", {"expression": "sin(x)/x", "symbol": "x", "point": "0"}),
    ("linalg/eigenvalues", "eigenvalues", {"matrix": [["2", "1"], ["1", "2"]]}),
    ("linalg/matsolve", "matrix_solve", {"matrix": [["1", "1"], ["1", "-1"]], "rhs": ["10", "2"]}),
    ("numtheory/factorize", "factorize", {"n": "123456"}),
    ("numtheory/crt", "chinese_remainder", {"moduli": ["3", "5", "7"], "residues": ["2", "3", "2"]}),
    ("combin/recurrence", "solve_recurrence",
     {"recurrence": "y(n)=y(n-1)+y(n-2)", "func": "y", "var": "n", "initial": {"0": "0", "1": "1"}}),
    ("trackB/pigeonhole", "pigeonhole", {"n": 5}),
]


def bench(n: int = 20) -> list[dict]:
    """Runs each job n times; collects times (ms). n can be small for test/CI."""
    rows = []
    for label, task, payload in WORKLOAD:
        times = []
        status = None
        for _ in range(n):
            t0 = time.perf_counter()
            res = asdict(route(task, payload))
            times.append((time.perf_counter() - t0) * 1000.0)
            status = res.get("status")
        rows.append({
            "label": label,
            "status": status,
            "median_ms": round(statistics.median(times), 3),
            "mean_ms": round(statistics.fmean(times), 3),
            "min_ms": round(min(times), 3),
        })
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description="MathHead benchmark")
    ap.add_argument("--n", type=int, default=20, help="repetitions (default 20)")
    args = ap.parse_args()
    rows = bench(args.n)
    print(f"{'operation':24} {'status':14} {'median(ms)':>12} {'mean(ms)':>10} {'min(ms)':>10}")
    print("-" * 74)
    for r in rows:
        print(f"{r['label']:24} {r['status']:14} {r['median_ms']:>12} {r['mean_ms']:>10} {r['min_ms']:>10}")
    print("-" * 74)
    print(f"total median: {round(sum(r['median_ms'] for r in rows), 2)} ms  (N={args.n})")


if __name__ == "__main__":
    main()
