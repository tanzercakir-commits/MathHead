"""
LLM-tuzak benchmark regresyon çiti (ROADMAP Track C4).

`benchmarks/run.py` harness'ını çalıştırır ve HER tuzağın MathHead tarafından
doğru adjuke edildiğini (yakalandığını) zorlar. Bu, motorun "AI'ın işini
denetler" değer önerisinin ileride sessizce bozulmasına karşı çittir.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "benchmarks"))

import run as bench  # noqa: E402

_ROWS = bench.run()


def test_trap_suite_nonempty():
    assert len(_ROWS) >= 12


@pytest.mark.parametrize("row", _ROWS, ids=[r["id"] for r in _ROWS])
def test_each_trap_is_caught(row):
    assert row["caught"], (
        f"{row['id']} KAÇIRILDI — beklenen {row['expect']}, gelen {row['got']}"
    )


def test_full_catch_rate():
    caught = sum(r["caught"] for r in _ROWS)
    assert caught == len(_ROWS), f"yakalama oranı {caught}/{len(_ROWS)} — %100 olmalı"
