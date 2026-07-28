"""
Duman testi (smoke test): iskelet import edilebilir mi ve dönüş sözleşmesi
(ReasoningResult contract) yerinde mi. Bunlar İSKELET aşamasında bile GEÇMELİDİR.
"""
import importlib.util

import pytest

from mathhead.core import ReasoningResult


def test_reasoning_result_contract():
    r = ReasoningResult(status="valid", reason_code="ENTAILED", explanation="x")
    assert r.is_conclusive() is True
    assert r.witness is None
    assert isinstance(r.meta, dict)

    unknown = ReasoningResult(status="unknown", reason_code="SOLVER_TIMEOUT", explanation="")
    assert unknown.is_conclusive() is False  # unknown/error kesin sonuç DEĞİL


def test_core_primitives_exist_and_callable():
    from mathhead.core import check_consistency, check_entailment, find_model

    for fn in (check_entailment, check_consistency, find_model):
        assert callable(fn)


@pytest.mark.skipif(
    importlib.util.find_spec("mcp") is None, reason="mcp SDK kurulu değil (opsiyonel)"
)
def test_server_module_imports():
    mod = importlib.import_module("mathhead.server.mcp_server")
    assert hasattr(mod, "mcp")
    assert hasattr(mod, "main")
