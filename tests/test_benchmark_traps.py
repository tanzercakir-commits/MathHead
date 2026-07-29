"""
LLM-trap benchmark regression fence (ROADMAP Track C4).

Runs the `benchmarks/run.py` harness and enforces that EVERY trap is correctly
adjudicated (caught) by MathHead. This is a fence against the engine's "audits
the AI's work" value proposition silently breaking in the future.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "benchmarks"))

import run as bench  # noqa: E402

_ROWS = bench.run()


def test_trap_suite_nonempty():
    assert len(_ROWS) >= 20        # ROADMAP L5: a ≥20-error catch-rate benchmark


@pytest.mark.parametrize("row", _ROWS, ids=[r["id"] for r in _ROWS])
def test_each_trap_is_caught(row):
    assert row["caught"], (
        f"{row['id']} MISSED — expected {row['expect']}, got {row['got']}"
    )


def test_full_catch_rate():
    caught = sum(r["caught"] for r in _ROWS)
    assert caught == len(_ROWS), f"catch rate {caught}/{len(_ROWS)} — must be 100%"
