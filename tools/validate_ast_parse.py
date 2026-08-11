#!/usr/bin/env python3
"""Validate the accepted MH-C-AST-PARSE-001 boundary fail-closed."""

from __future__ import annotations

import ast
import hashlib
import inspect
from pathlib import Path
import sys
from typing import get_type_hints


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

EXPECTED_CONTRACT_SHA256 = \
    "69884d482ed38e34ea0b1cd1c6d3349d2dca389704ddbd385d8e493b30886965"
FROZEN_BASELINE_SHA256 = \
    "b93f71ce676380574235ca422e8a23a8f4871ee45b2973195575ea397cefe19a"
FROZEN_OBSERVATIONS_SHA256 = \
    "69c90d4e71a9955c4211b5939be75bdde19a2d05457b1d272d900b74b11aa903"

CONSUMERS = (
    "mathhead/certificate.py",
    "mathhead/compute/__init__.py",
    "mathhead/core/induction.py",
    "mathhead/core/inequality.py",
    "mathhead/core/modal.py",
    "mathhead/core/smt.py",
    "mathhead/core/translate.py",
    "mathhead/guardrails/__init__.py",
)


class AstParseValidationError(RuntimeError):
    """Raised when the portable expression parser or a consumer drifts."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _validate_contract_files() -> None:
    accepted = ROOT / "docs/contracts/MH-C-AST-PARSE-001.json"
    proposed = ROOT / "docs/contracts/proposed/MH-C-AST-PARSE-001.json"
    for path in (accepted, proposed):
        if _sha256(path) != EXPECTED_CONTRACT_SHA256:
            raise AstParseValidationError(
                f"contract hash drift: {path.relative_to(ROOT)}"
            )
    if accepted.read_bytes() != proposed.read_bytes():
        raise AstParseValidationError("accepted contract differs from reviewed proposal")
    if _sha256(ROOT / "docs/reconstruction/legacy-baseline-v1.json") != \
            FROZEN_BASELINE_SHA256:
        raise AstParseValidationError("immutable baseline artifact drift")
    if _sha256(ROOT / "docs/reconstruction/legacy-observations-v1.json") != \
            FROZEN_OBSERVATIONS_SHA256:
        raise AstParseValidationError("immutable observation artifact drift")


def _validate_implementation() -> None:
    import mathhead.parsing as parsing

    if parsing.AST_PARSE_CONTRACT_ID != "MH-C-AST-PARSE-001" or \
            parsing.AST_PARSE_CONTRACT_SHA256 != EXPECTED_CONTRACT_SHA256:
        raise AstParseValidationError("implementation contract metadata drift")

    signature = inspect.signature(parsing.parse_expression)
    if list(signature.parameters) != ["source"]:
        raise AstParseValidationError("parse_expression parameter drift")
    source = signature.parameters["source"]
    if source.kind is not inspect.Parameter.POSITIONAL_OR_KEYWORD or \
            source.default is not inspect.Parameter.empty:
        raise AstParseValidationError("parse_expression signature drift")
    hints = get_type_hints(parsing.parse_expression)
    if hints != {"source": str, "return": ast.Expression}:
        raise AstParseValidationError("parse_expression type annotation drift")

    tree = parsing.parse_expression("1 + 2")
    if not isinstance(tree, ast.Expression) or not isinstance(tree.body, ast.BinOp):
        raise AstParseValidationError("valid expression behavior drift")
    cases = (("\0", "expression contains NUL"),
             ("x\0 + 1", "expression contains NUL"),
             (None, "expression must be a string"))
    for value, expected in cases:
        try:
            parsing.parse_expression(value)  # type: ignore[arg-type]
        except parsing.ExpressionSyntaxError as exc:
            if str(exc) != expected:
                raise AstParseValidationError(f"normalized message drift: {value!r}") from exc
        except (SyntaxError, ValueError, TypeError) as exc:
            raise AstParseValidationError(f"raw parser exception escaped: {type(exc).__name__}") \
                from exc
        else:
            raise AstParseValidationError(f"invalid parser input accepted: {value!r}")

    try:
        ast.parse("(", mode="eval")
    except SyntaxError as raw:
        expected_syntax = raw.msg
    else:  # pragma: no cover - every supported CPython rejects this expression
        raise AstParseValidationError("interpreter accepted malformed control expression")
    try:
        parsing.parse_expression("(")
    except parsing.ExpressionSyntaxError as exc:
        if str(exc) != expected_syntax:
            raise AstParseValidationError("SyntaxError.msg normalization drift") from exc
    else:
        raise AstParseValidationError("malformed syntax was accepted")

    original = parsing.ast.parse
    try:
        for raw_type in (ValueError, TypeError):
            def reject(*_args, _raw_type=raw_type, **_kwargs):
                raise _raw_type("interpreter-specific detail")

            parsing.ast.parse = reject
            try:
                parsing.parse_expression("x")
            except parsing.ExpressionSyntaxError as exc:
                if str(exc) != "expression rejected by parser":
                    raise AstParseValidationError("parser rejection message drift") from exc
            else:
                raise AstParseValidationError(f"{raw_type.__name__} was not normalized")
    finally:
        parsing.ast.parse = original


def _validate_single_parser_boundary() -> None:
    direct_calls: list[str] = []
    for path in sorted((SRC / "mathhead").rglob("*.py")):
        relative = path.relative_to(SRC).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        ast_aliases = {"ast"}
        parse_aliases: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "ast":
                        ast_aliases.add(alias.asname or alias.name)
            elif isinstance(node, ast.ImportFrom) and node.module == "ast":
                for alias in node.names:
                    if alias.name == "parse":
                        parse_aliases.add(alias.asname or alias.name)
            elif isinstance(node, ast.Call):
                function = node.func
                if isinstance(function, ast.Attribute) and function.attr == "parse" and \
                        isinstance(function.value, ast.Name) and \
                        function.value.id in ast_aliases:
                    direct_calls.append(f"{relative}:{node.lineno}")
                elif isinstance(function, ast.Name) and function.id in parse_aliases:
                    direct_calls.append(f"{relative}:{node.lineno}")
    if len(direct_calls) != 1 or not direct_calls[0].startswith("mathhead/parsing.py:"):
        raise AstParseValidationError(
            "ast.parse must occur exactly once at the shared boundary: " + ", ".join(direct_calls)
        )

    for relative in CONSUMERS:
        text = (SRC / relative).read_text(encoding="utf-8")
        if "from mathhead.parsing import" not in text or "parse_expression(" not in text:
            raise AstParseValidationError(f"expression consumer bypasses boundary: {relative}")


def validate() -> None:
    _validate_contract_files()
    _validate_single_parser_boundary()
    _validate_implementation()


def main() -> int:
    try:
        validate()
    except (AstParseValidationError, ImportError, OSError, SyntaxError) as exc:
        print(f"ast-parse-contract: FAIL: {exc}", file=sys.stderr)
        return 1
    print("ast-parse-contract: PASS (portable eval parser; 8 consumers)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
