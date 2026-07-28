"""
Benchmark iskeleti duman testi (ROADMAP Aşama 5 [S]) — `scripts/benchmark.py`
çürümesin diye. Süre EŞİĞİ yok (ortama bağlı); yalnızca çalıştığını + her işin
anlamlı bir statü döndürdüğünü doğrular.
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


# Katastrofik yavaşlama çiti: eşik BİLEREK cömert (10 sn) — normal işlemler
# <50ms; amaç zamanlama titrekliği değil, kazayla eklenen O(2^n)/sonsuz döngü gibi
# felaket regresyonları yakalamak. İnce zamanlama için: scripts/benchmark.py.
_CEILING_MS = 10_000.0


def test_no_catastrophic_slowdown():
    for r in benchmark.bench(n=1):
        assert r["median_ms"] < _CEILING_MS, \
            f"{r['label']} çok yavaş: {r['median_ms']} ms (çit {_CEILING_MS} ms)"
