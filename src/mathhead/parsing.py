"""Portable, side-effect-free parsing for untrusted expression strings.

CPython versions have not always raised the same exception type for every
rejected ``ast.parse`` input.  This module owns that compatibility boundary so
public MathHead surfaces can preserve their own result and error envelopes.
"""
from __future__ import annotations

import ast


AST_PARSE_CONTRACT_ID = "MH-C-AST-PARSE-001"
AST_PARSE_CONTRACT_SHA256 = \
    "69884d482ed38e34ea0b1cd1c6d3349d2dca389704ddbd385d8e493b30886965"


class ExpressionSyntaxError(ValueError):
    """An untrusted expression could not be parsed into an eval-mode AST."""


def parse_expression(source: str) -> ast.Expression:
    """Return one eval-mode expression AST or raise ``ExpressionSyntaxError``.

    This boundary only normalizes parser input rejection.  It deliberately
    leaves grammar whitelisting, resource limits, and semantic interpretation
    to its callers.
    """
    if not isinstance(source, str):
        raise ExpressionSyntaxError("expression must be a string")
    if "\0" in source:
        raise ExpressionSyntaxError("expression contains NUL")
    try:
        return ast.parse(source, mode="eval")
    except SyntaxError as exc:
        raise ExpressionSyntaxError(exc.msg) from exc
    except (ValueError, TypeError) as exc:
        raise ExpressionSyntaxError("expression rejected by parser") from exc
