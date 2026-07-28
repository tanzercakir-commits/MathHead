"""
API reference freshness (ROADMAP Phase 8 [S]) — `docs/api-reference.md` must
always stay in sync with the tools registered with MCP. If a new tool is added
without regenerating the doc, this test breaks (`python scripts/gen_api_reference.py`).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import gen_api_reference


def test_api_reference_up_to_date():
    generated = gen_api_reference.generate()
    on_disk = gen_api_reference._OUT.read_text(encoding="utf-8")
    assert on_disk == generated, (
        "docs/api-reference.md is out of date — "
        "run `python scripts/gen_api_reference.py` and commit."
    )
