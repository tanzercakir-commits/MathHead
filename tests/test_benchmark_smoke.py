"""
Benchmark skeleton smoke test (ROADMAP Phase 5 [S]) — keeps `scripts/benchmark.py`
from rotting. No time THRESHOLD (environment-dependent); only verifies it runs +
each job returns a meaningful status.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import benchmark


def test_bench_runs_and_reports():
    rows = benchmark.bench(n=1)
    assert len(rows) == len(benchmark.WORKLOAD)
    for r in rows:
        assert r["status"] not in (None, "error"), f"{r['label']}: {r['status']}"
        assert r["median_ms"] >= 0


# Catastrophic slowdown fence: threshold DELIBERATELY generous (10 s) — normal ops
# <50ms; the goal is not timing jitter but catching disaster regressions like an
# accidentally added O(2^n)/infinite loop. For fine timing: scripts/benchmark.py.
_CEILING_MS = 10_000.0


def test_no_catastrophic_slowdown():
    for r in benchmark.bench(n=1):
        assert r["median_ms"] < _CEILING_MS, \
            f"{r['label']} too slow: {r['median_ms']} ms (ceiling {_CEILING_MS} ms)"
