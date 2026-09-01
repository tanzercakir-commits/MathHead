"""Portable strategy-selection contract for the canonical discovery report."""

from __future__ import annotations

import hashlib
import inspect
from pathlib import Path
from typing import Callable, get_type_hints

import pytest

from mathhead.discovery import arithmetic
from mathhead.discovery.arithmetic import ArithmeticFinding


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_SHA256 = "247534720fe49f89a9961196701cc12a954f5e95e12bd7b8b8c5a07318b3bf7b"
EXPECTED_METHODS = (
    "induction",
    "modulus-factoring",
    "residue-exhaustion",
    "induction",
    "modulus-factoring",
    "residue-exhaustion",
    "residue-exhaustion",
)


def test_accepted_contract_is_exact_reviewed_proposal():
    accepted = ROOT / "docs/contracts/MH-C-DISCOVERY-PORTFOLIO-002.json"
    proposed = ROOT / "docs/contracts/proposed/MH-C-DISCOVERY-PORTFOLIO-002.json"
    assert hashlib.sha256(accepted.read_bytes()).hexdigest() == EXPECTED_SHA256
    assert accepted.read_bytes() == proposed.read_bytes()


def test_contract_binding_and_signature():
    signature = inspect.signature(arithmetic.discover_and_prove)
    assert list(signature.parameters) == ["expr", "fn", "check_upto", "judge_timeout_ms"]
    assert signature.parameters["check_upto"].default == 60
    assert signature.parameters["judge_timeout_ms"].default == 2500
    assert get_type_hints(arithmetic.discover_and_prove) == {
        "expr": str,
        "fn": Callable[[int], int],
        "check_upto": int,
        "judge_timeout_ms": int,
        "return": ArithmeticFinding,
    }
    assert arithmetic.DISCOVERY_PORTFOLIO_CONTRACT_ID == \
        "MH-C-DISCOVERY-PORTFOLIO-002"
    assert arithmetic.DISCOVERY_PORTFOLIO_CONTRACT_SHA256 == EXPECTED_SHA256


@pytest.mark.parametrize("expr,fn", arithmetic.POLY_FAMILY[2:3] + arithmetic.POLY_FAMILY[5:])
def test_high_degree_uses_residues_before_any_solver_call(monkeypatch, expr, fn):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("timing-sensitive induction was called")

    monkeypatch.setattr(arithmetic, "prove_modular_divisibility", forbidden)
    finding = arithmetic.discover_and_prove(expr, fn, judge_timeout_ms=1)
    assert (finding.verdict, finding.certainty, finding.method) == (
        "proved", "exhaustive_residue_proof", "residue-exhaustion"
    )
    assert finding.independently_verified and finding.kernel_verified


def test_canonical_family_methods_are_platform_independent():
    arithmetic._RUN_CACHE.clear()
    findings = arithmetic.run_arithmetic_discovery()
    assert tuple(finding.method for finding in findings) == EXPECTED_METHODS
    assert all(finding.verdict == "proved" for finding in findings)
    assert all(finding.independently_verified and finding.kernel_verified for finding in findings)


def test_high_degree_budget_cannot_change_the_result():
    expr, fn = arithmetic.POLY_FAMILY[2]
    fast_timeout = arithmetic.discover_and_prove(expr, fn, judge_timeout_ms=1)
    large_timeout = arithmetic.discover_and_prove(expr, fn, judge_timeout_ms=1_000_000)
    fields = ("verdict", "certainty", "method", "proof_hash", "axioms")
    assert tuple(getattr(fast_timeout, field) for field in fields) == \
        tuple(getattr(large_timeout, field) for field in fields)


def test_committed_sample_report_is_current():
    from mathhead.discovery import render, run_report

    expected = (ROOT / "docs/discovery/SAMPLE-REPORT.md").read_text(encoding="utf-8")
    assert render(run_report(max_n=6)) + "\n" == expected
