"""
Golden senaryo testleri (ROADMAP Aşama 5 [S]) — veri-güdümlü regresyon çiti.

`tests/fixtures/golden.json` içindeki her senaryoyu `route(task, payload)` ile
çalıştırır ve `expect`'teki alanları birebir doğrular (yalnız verilen alanlar).
Bilinen doğru çıktıların ileride sessizce bozulmasını engeller.
"""
import json
from pathlib import Path

import pytest

from dataclasses import asdict

from mathhead.router import route

_FIXTURE = Path(__file__).parent / "fixtures" / "golden.json"
_CASES = json.loads(_FIXTURE.read_text(encoding="utf-8"))["cases"]


@pytest.mark.parametrize("case", _CASES, ids=[c["name"] for c in _CASES])
def test_golden(case):
    result = asdict(route(case["task"], case["payload"]))
    for key, want in case["expect"].items():
        assert result.get(key) == want, \
            f"{case['name']}: {key} beklenen {want!r}, gelen {result.get(key)!r}"
