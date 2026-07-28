"""
Sözleşme denetimi (ROADMAP Aşama 11 [S]) — HER aracın ortak çıktı sözleşmesine
uyduğunu doğrular: `status` + `reason_code` + `explanation` + `meta` (elapsed_ms
ile). Bu, "net protokol & API" prensibinin makine-denetimidir; bir araç
sözleşmeyi bozarsa (ör. meta'sız döner) test kırılır.

Kapsanan araç kümesi `test_mcp_layer.ARGS`'tan gelir (tek kaynak) — böylece yeni
araç eklenince hem çağrılabilirlik hem sözleşme birlikte zorlanır.
"""
from dataclasses import asdict

import pytest

from mathhead.router import route
from tests.test_mcp_layer import ARGS

# route() task adları MCP araç adlarından birkaç yerde ayrışır (enumerate_models
# -> enumerate, model -> find_model, vb.). MCP adı -> router task eşlemesi:
_TASK = {
    "model": "find_model",
    "enumerate_models": "enumerate",
    "max_satisfy": "maxsat",
    "van_der_waerden": "van_der_waerden",
}


@pytest.mark.parametrize("tool", sorted(ARGS), ids=sorted(ARGS))
def test_tool_output_contract(tool):
    task = _TASK.get(tool, tool)
    result = asdict(route(task, ARGS[tool]))
    # Evrensel sözleşme: dört alan daima var
    for key in ("status", "reason_code", "explanation", "meta"):
        assert key in result, f"{tool}: sözleşme ihlali — '{key}' yok"
    assert isinstance(result["status"], str) and result["status"]
    assert isinstance(result["explanation"], str)
    assert isinstance(result["meta"], dict)
    # meta ölçüm taşımalı (her katman)
    assert "elapsed_ms" in result["meta"], f"{tool}: meta.elapsed_ms yok"
    assert isinstance(result["meta"]["elapsed_ms"], (int, float))
