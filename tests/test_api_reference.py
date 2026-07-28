"""
API referansı güncelliği (ROADMAP Aşama 8 [S]) — `docs/api-reference.md` daima
MCP'ye kayıtlı araçlarla senkron olmalı. Yeni araç eklenip doküman
üretilmezse bu test kırılır (`python scripts/gen_api_reference.py`).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import gen_api_reference


def test_api_reference_up_to_date():
    generated = gen_api_reference.generate()
    on_disk = gen_api_reference._OUT.read_text(encoding="utf-8")
    assert on_disk == generated, (
        "docs/api-reference.md güncel değil — "
        "`python scripts/gen_api_reference.py` çalıştır ve işle."
    )
