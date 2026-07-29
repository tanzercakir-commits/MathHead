"""
Tool-selection accuracy fence (ROADMAP L5).

Runs `benchmarks/run_tool_selection.py` and fences the L3 triage quality:
`recommend_tool` must surface a correct tool often enough to be useful. The
thresholds are HONEST floors set BELOW the measured accuracy (top-3 ≈ 94%,
top-1 ≈ 78% at the time of writing) — they catch a regression without pretending
the keyword heuristic is perfect.
"""
import sys
from pathlib import Path

from mathhead.router import route

sys.path.insert(0, str(Path(__file__).parent.parent / "benchmarks"))

import run_tool_selection as ts  # noqa: E402

_ROWS = ts.run()
_SUMMARY = ts.summarize(_ROWS)


def test_case_set_is_substantial():
    assert len(_ROWS) >= 15


def test_expected_tools_are_real():
    # every "correct answer" must name a tool that actually exists in the catalog
    seen = set()
    for row in _ROWS:
        for name in row["expect"]:
            if name not in seen:
                assert route("describe_tool", {"name": name}).status == "ok", \
                    f"expected tool {name!r} is not a real tool"
                seen.add(name)


def test_top3_accuracy_floor():
    assert _SUMMARY["top3_rate"] >= 0.85, f"top-3 accuracy regressed: {_SUMMARY}"


def test_top1_accuracy_floor():
    assert _SUMMARY["top1_rate"] >= 0.70, f"top-1 accuracy regressed: {_SUMMARY}"
