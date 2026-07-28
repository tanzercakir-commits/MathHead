"""
Golden scenario tests (ROADMAP Phase 5 [S]) — data-driven regression fence.

Runs each scenario in `tests/fixtures/golden.json` via `route(task, payload)`
and verifies the fields in `expect` exactly (only the given fields).
Prevents known-correct outputs from silently breaking in the future.
"""
import json
from dataclasses import asdict
from pathlib import Path

import pytest

from mathhead.router import route

_FIXTURE = Path(__file__).parent / "fixtures" / "golden.json"
_CASES = json.loads(_FIXTURE.read_text(encoding="utf-8"))["cases"]


@pytest.mark.parametrize("case", _CASES, ids=[c["name"] for c in _CASES])
def test_golden(case):
    result = asdict(route(case["task"], case["payload"]))
    for key, want in case["expect"].items():
        assert result.get(key) == want, \
            f"{case['name']}: {key} beklenen {want!r}, gelen {result.get(key)!r}"
