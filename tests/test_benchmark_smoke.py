"""
Benchmark iskeleti duman testi (ROADMAP Aşama 5 [S]) — `scripts/benchmark.py`
çürümesin diye. Süre EŞİĞİ yok (ortama bağlı); yalnızca çalıştığını + her işin
anlamlı bir statü döndürdüğünü doğrular.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import benchmark  # noqa: E402


def test_bench_runs_and_reports():
    rows = benchmark.bench(n=1)
    assert len(rows) == len(benchmark.WORKLOAD)
    for r in rows:
        assert r["status"] not in (None, "error"), f"{r['label']}: {r['status']}"
        assert r["median_ms"] >= 0
