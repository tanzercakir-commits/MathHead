"""Contract and integration tests for the portable expression parser."""

from __future__ import annotations

import ast
import hashlib
import inspect
from pathlib import Path
from typing import get_type_hints

from hypothesis import given, settings
from hypothesis import strategies as st
import pytest

from mathhead import parsing
from mathhead.certificate import check_certificate
from mathhead.compute import simplify
from mathhead.core.induction import prove_by_induction
from mathhead.core.inequality import prove_inequality
from mathhead.core.logic import check_consistency
from mathhead.core.modal import check_modal
from mathhead.core.smt import check_bitvector
from mathhead.core.translate import ParseError, parse
from mathhead.guardrails import GuardrailError, validate_input


ROOT = Path(__file__).resolve().parents[2]
EXPECTED_SHA256 = "69884d482ed38e34ea0b1cd1c6d3349d2dca389704ddbd385d8e493b30886965"


def test_accepted_contract_is_exact_reviewed_proposal():
    accepted = ROOT / "docs/contracts/MH-C-AST-PARSE-001.json"
    proposed = ROOT / "docs/contracts/proposed/MH-C-AST-PARSE-001.json"
    assert hashlib.sha256(accepted.read_bytes()).hexdigest() == EXPECTED_SHA256
    assert accepted.read_bytes() == proposed.read_bytes()


def test_contract_binding_and_signature():
    signature = inspect.signature(parsing.parse_expression)
    assert list(signature.parameters) == ["source"]
    assert signature.parameters["source"].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert signature.parameters["source"].default is inspect.Parameter.empty
    assert get_type_hints(parsing.parse_expression) == {"source": str, "return": ast.Expression}
    assert parsing.AST_PARSE_CONTRACT_ID == "MH-C-AST-PARSE-001"
    assert parsing.AST_PARSE_CONTRACT_SHA256 == EXPECTED_SHA256


def test_valid_source_returns_an_unmodified_eval_ast():
    tree = parsing.parse_expression("x + 2")
    assert isinstance(tree, ast.Expression)
    assert ast.dump(tree, include_attributes=False) == \
        "Expression(body=BinOp(left=Name(id='x', ctx=Load()), op=Add(), " \
        "right=Constant(value=2)))"


@pytest.mark.parametrize("source", ["\0", "x\0", "\0 + x", "x + \0"])
def test_nul_rejection_is_exact_and_portable(source):
    with pytest.raises(parsing.ExpressionSyntaxError, match="^expression contains NUL$"):
        parsing.parse_expression(source)


@pytest.mark.parametrize("source", [None, 1, b"x", ["x"]])
def test_runtime_non_string_rejection_is_exact(source):
    with pytest.raises(parsing.ExpressionSyntaxError, match="^expression must be a string$"):
        parsing.parse_expression(source)


def test_malformed_syntax_uses_only_syntaxerror_message():
    with pytest.raises(SyntaxError) as raw:
        ast.parse("(", mode="eval")
    with pytest.raises(parsing.ExpressionSyntaxError) as normalized:
        parsing.parse_expression("(")
    assert str(normalized.value) == raw.value.msg
    assert normalized.value.__cause__ is raw.value.__class__ or \
        isinstance(normalized.value.__cause__, SyntaxError)
    assert "line" not in str(normalized.value)


@pytest.mark.parametrize("raw_type", [ValueError, TypeError])
def test_interpreter_parser_rejections_are_normalized(monkeypatch, raw_type):
    def reject(*_args, **_kwargs):
        raise raw_type("interpreter-specific detail")

    monkeypatch.setattr(parsing.ast, "parse", reject)
    with pytest.raises(parsing.ExpressionSyntaxError, match="^expression rejected by parser$"):
        parsing.parse_expression("x")


@pytest.mark.parametrize("raw_type", [MemoryError, KeyboardInterrupt, SystemExit])
def test_process_and_resource_exceptions_are_not_swallowed(monkeypatch, raw_type):
    def interrupt(*_args, **_kwargs):
        raise raw_type("stop")

    monkeypatch.setattr(parsing.ast, "parse", interrupt)
    with pytest.raises(raw_type, match="stop"):
        parsing.parse_expression("x")


@given(source=st.text(max_size=128))
@settings(max_examples=250, deadline=None)
def test_arbitrary_unicode_has_only_the_normalized_boundary_outcome(source):
    try:
        tree = parsing.parse_expression(source)
    except parsing.ExpressionSyntaxError:
        return
    assert isinstance(tree, ast.Expression)


def test_caller_specific_error_envelopes_are_preserved_for_nul():
    with pytest.raises(GuardrailError, match="syntax error: expression contains NUL"):
        validate_input(["\0"])
    with pytest.raises(ParseError, match="syntax error: expression contains NUL"):
        parse("\0")

    results = {
        "compute": simplify("\0"),
        "logic": check_consistency(["\0"]),
        "induction": prove_by_induction("\0"),
        "smt": check_bitvector(["\0"], width=8),
        "modal": check_modal("\0"),
        "inequality": prove_inequality("\0"),
        "certificate": check_certificate({
            "kind": "solution", "expression": "\0", "symbol": "x", "value": "0"
        }),
    }
    assert {name: result.status for name, result in results.items()} == {
        "compute": "error",
        "logic": "error",
        "induction": "error",
        "smt": "error",
        "modal": "error",
        "inequality": "error",
        "certificate": "error",
    }
    assert all("NUL" in result.explanation for result in results.values())
