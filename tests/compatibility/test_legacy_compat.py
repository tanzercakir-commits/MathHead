from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from types import ModuleType
from typing import Any

import pytest


ROOT = Path(__file__).resolve().parents[2]
TOOL_PATH = ROOT / "tools/legacy_compat.py"
VALIDATOR_PATH = ROOT / "tools/validate_legacy_compat.py"
CORPUS_PATH = ROOT / "docs/reconstruction/legacy-compat-v1.json"


def _load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


compat = _load_module("legacy_compat_under_test", TOOL_PATH)


def _canonical(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False)
        + "\n"
    ).encode("utf-8")


def _corpus() -> dict[str, Any]:
    return json.loads(CORPUS_PATH.read_text(encoding="utf-8"))


def test_contract_binding_and_required_case_coverage() -> None:
    assert compat.CONTRACT_ID == "MH-C-LEGACY-COMPAT-001"
    assert compat.CONTRACT_SHA256 == hashlib.sha256(
        (ROOT / "docs/contracts/MH-C-LEGACY-COMPAT-001.json").read_bytes()
    ).hexdigest()
    assert len(compat.CASE_SPECS) == 10
    assert [case["id"] for case in compat.CASE_SPECS] == sorted(
        case["id"] for case in compat.CASE_SPECS
    )
    assert {case["category"] for case in compat.CASE_SPECS} == {
        "success", "refuted", "unsupported", "timeout", "error"
    }
    assert {case["invocation"]["surface"] for case in compat.CASE_SPECS} == {
        "router", "discovery"
    }


def test_committed_corpus_replays_all_legacy_cases() -> None:
    assert compat.main(["--check"]) == 0


def test_capture_is_deterministic_without_rewriting_source() -> None:
    rebuilt = compat._build_corpus()
    assert _canonical(rebuilt) == CORPUS_PATH.read_bytes()


def test_normalization_is_typed_path_specific_and_preserves_fields() -> None:
    raw = {
        "status": "ok",
        "meta": {"elapsed_ms": 1.25, "sympy_version": "1.14.0", "stable": 7},
    }
    normalized = compat._normalize(raw, ["meta.elapsed_ms", "meta.sympy_version"])
    assert raw["meta"]["elapsed_ms"] == 1.25
    assert normalized == {
        "status": "ok",
        "meta": {
            "elapsed_ms": "<normalized:number>",
            "sympy_version": "<normalized:string>",
            "stable": 7,
        },
    }
    with pytest.raises(compat.LegacyCompatError, match="exact sorted allowlist"):
        compat._normalize(raw, ["status"])
    with pytest.raises(compat.LegacyCompatError, match="type drift"):
        compat._normalize({"meta": {"elapsed_ms": "fast"}}, ["meta.elapsed_ms"])


def test_expected_timeout_is_a_result_not_a_watchdog_timeout() -> None:
    case = next(case for case in _corpus()["cases"] if case["category"] == "timeout")
    assert case["expected"]["status"] == "unknown"
    assert case["expected"]["reason_code"] == "SOLVER_TIMEOUT"
    assert case["expected"]["meta"]["timeout_ms"] == 1


class _HungProcess:
    def __init__(self) -> None:
        self.returncode: int | None = None
        self.calls = 0
        self.terminated = False
        self.killed = False

    def communicate(self, *, input: bytes | None = None, timeout: float | None = None):
        del input
        self.calls += 1
        if self.calls <= 2:
            raise subprocess.TimeoutExpired("legacy-case", timeout or 0)
        self.returncode = -9
        return b"", b""

    def terminate(self) -> None:
        self.terminated = True

    def kill(self) -> None:
        self.killed = True


def test_watchdog_terminates_kills_waits_and_reports_distinctly(monkeypatch) -> None:
    process = _HungProcess()
    monkeypatch.setattr(compat.subprocess, "Popen", lambda *args, **kwargs: process)
    with pytest.raises(compat.LegacyCompatError) as caught:
        compat._run_case(compat.CASE_SPECS[0])
    assert caught.value.kind == "watchdog-timeout"
    assert caught.value.exit_code == 4
    assert process.terminated and process.killed and process.calls == 3


def test_main_does_not_reclassify_process_control_exceptions(monkeypatch) -> None:
    monkeypatch.setattr(compat, "_check", lambda: (_ for _ in ()).throw(SystemExit(9)))
    with pytest.raises(SystemExit, match="9"):
        compat.main(["--check"])


def _mutation(base: dict[str, Any], name: str) -> None:
    if name == "input":
        base["cases"][0]["invocation"]["payload"]["expression"] = "x + 1"
    elif name == "category":
        base["cases"][0]["category"] = "success"
    elif name == "stable-output":
        base["cases"][0]["expected"]["reason_code"] = "OK"
        base["cases"][0]["expected_sha256"] = hashlib.sha256(
            _canonical(base["cases"][0]["expected"])
        ).hexdigest()
    elif name == "output-identity":
        base["cases"][0]["expected_sha256"] = "0" * 64
    elif name == "provenance":
        base["provenance"]["source_commit"] = "0" * 40
    elif name == "normalization":
        base["normalization"]["allowlist"].append("status")
    else:
        raise AssertionError(name)


@pytest.mark.parametrize(
    "mutation",
    ["input", "category", "stable-output", "output-identity", "provenance", "normalization"],
)
def test_independent_validator_rejects_semantic_mutations(tmp_path: Path, mutation: str) -> None:
    changed = copy.deepcopy(_corpus())
    _mutation(changed, mutation)
    path = tmp_path / f"{mutation}.json"
    path.write_bytes(_canonical(changed))
    result = subprocess.run(
        [sys.executable, str(VALIDATOR_PATH), "--corpus", str(path)],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=15,
        check=False,
    )
    assert result.returncode == 1
    assert b"legacy-compat-validator: FAIL" in result.stderr
