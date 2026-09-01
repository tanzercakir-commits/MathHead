#!/usr/bin/env python3
"""Validate the accepted MH-C-ENCODING-001 boundary fail-closed."""

from __future__ import annotations

import ast
import hashlib
import importlib
import inspect
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

EXPECTED_CONTRACT_SHA256 = \
    "b47e07c259a8357000d57cde4238b61ea11a872113d713165515dc86a54cf210"
FROZEN_BASELINE_SHA256 = \
    "b93f71ce676380574235ca422e8a23a8f4871ee45b2973195575ea397cefe19a"
FROZEN_OBSERVATIONS_SHA256 = \
    "69c90d4e71a9955c4211b5939be75bdde19a2d05457b1d272d900b74b11aa903"


class CommandEncodingValidationError(RuntimeError):
    """Raised when the accepted output boundary or one of its consumers drifts."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate() -> None:
    accepted = ROOT / "docs/contracts/MH-C-ENCODING-001.json"
    proposed = ROOT / "docs/contracts/proposed/MH-C-ENCODING-001.json"
    for path in (accepted, proposed):
        if _sha256(path) != EXPECTED_CONTRACT_SHA256:
            raise CommandEncodingValidationError(
                f"contract hash drift: {path.relative_to(ROOT)}"
            )
    if accepted.read_bytes() != proposed.read_bytes():
        raise CommandEncodingValidationError("accepted contract differs from reviewed proposal")
    if _sha256(ROOT / "docs/reconstruction/legacy-baseline-v1.json") != FROZEN_BASELINE_SHA256:
        raise CommandEncodingValidationError("immutable baseline artifact drift")
    if _sha256(ROOT / "docs/reconstruction/legacy-observations-v1.json") != \
            FROZEN_OBSERVATIONS_SHA256:
        raise CommandEncodingValidationError("immutable observation artifact drift")

    output = importlib.import_module("mathhead.output")
    if output.ENCODING_CONTRACT_ID != "MH-C-ENCODING-001" or \
            output.ENCODING_CONTRACT_SHA256 != EXPECTED_CONTRACT_SHA256:
        raise CommandEncodingValidationError("implementation contract metadata drift")
    if list(inspect.signature(output.safe_text).parameters) != ["text", "encoding"]:
        raise CommandEncodingValidationError("safe_text signature drift")

    cases = {
        ("Türkçe", "cp1254"): "Türkçe",
        ("Türkçe →", "cp1254"): "Türkçe \\u2192",
        ("é—", "ascii"): "\\xe9\\u2014",
        ("é—", "cp1252"): "é—",
        ("π", None): "π",
        ("π", "utf_8"): "π",
    }
    for arguments, expected in cases.items():
        actual = output.safe_text(*arguments)
        if actual != expected or output.safe_text(actual, arguments[1]) != actual:
            raise CommandEncodingValidationError(f"safe_text behavior drift: {arguments!r}")
    try:
        output.safe_text("x", "not-a-real-codec")
    except LookupError:
        pass
    else:
        raise CommandEncodingValidationError("unknown codec was hidden")

    consumers = {
        SRC / "mathhead/cli.py": True,
        SRC / "mathhead/discovery/cli.py": True,
        SRC / "mathhead/server/mcp_server.py": False,
        ROOT / "tools/dev.py": True,
    }
    for path, emits_json in consumers.items():
        text = path.read_text(encoding="utf-8")
        if "from mathhead.output import safe_print as print" not in text:
            raise CommandEncodingValidationError(
                f"command surface bypasses safe_print: {path.relative_to(ROOT)}"
            )
        if emits_json and "ensure_ascii=False" in text:
            raise CommandEncodingValidationError(
                f"command JSON is locale-sensitive: {path.relative_to(ROOT)}"
            )
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr == "reconfigure":
                raise CommandEncodingValidationError(
                    f"global stream reconfiguration found: {path.relative_to(ROOT)}"
                )
            if isinstance(node, ast.Attribute) and node.attr == "setlocale":
                raise CommandEncodingValidationError(
                    f"global locale mutation found: {path.relative_to(ROOT)}"
                )


def main() -> int:
    try:
        validate()
    except (CommandEncodingValidationError, OSError, SyntaxError) as exc:
        print(f"command-encoding: FAIL: {exc}", file=sys.stderr)
        return 1
    print("command-encoding: PASS (ascii/cp1252/cp1254/utf/redirected)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
