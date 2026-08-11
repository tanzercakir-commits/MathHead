#!/usr/bin/env python3
"""Validate the authority and preservation contract of the legacy index."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import re
import sys
import tomllib


ROLES = {
    "authoritative-plan",
    "authoritative-todo",
    "authoritative-progress",
    "historical-plan",
    "historical-todo",
    "historical-progress",
    "decision-ledger",
    "archive",
    "generated-output",
    "reference",
}
CLAIM_STATUSES = {"current", "mixed", "historical"}
AUTHORITIES = {
    "authoritative-plan": "docs/PLAN.md",
    "authoritative-todo": "docs/TODO.md",
    "authoritative-progress": "docs/PROGRESS.md",
}


class LegacyIndexError(RuntimeError):
    """Raised when the reconstruction index is ambiguous or stale."""


def _exact_path(root: Path, relative: str) -> Path:
    candidate = root
    for part in Path(relative).parts:
        try:
            names = {entry.name for entry in candidate.iterdir()}
        except OSError as exc:
            raise LegacyIndexError(f"cannot inspect {relative}: {exc}") from exc
        if part not in names:
            aliases = sorted(name for name in names if name.casefold() == part.casefold())
            if aliases:
                raise LegacyIndexError(
                    f"exact-case mismatch for {relative}: found {aliases[0]!r}"
                )
            raise LegacyIndexError(f"indexed source does not exist: {relative}")
        candidate /= part
    resolved = candidate.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise LegacyIndexError(f"indexed source escapes repository: {relative}") from exc
    if not resolved.is_file():
        raise LegacyIndexError(f"indexed source is not a file: {relative}")
    return resolved


def validate(root: Path, index_path: Path | None = None) -> int:
    path = index_path or root / "docs" / "reconstruction" / "LEGACY_INDEX.toml"
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise LegacyIndexError(f"cannot read index: {exc}") from exc
    records = data.get("records")
    if data.get("schema") != 1 or not isinstance(records, list):
        raise LegacyIndexError("index must use schema 1 and [[records]] entries")
    seen: set[str] = set()
    authorities: dict[str, str] = {}
    for number, record in enumerate(records, 1):
        if not isinstance(record, dict):
            raise LegacyIndexError(f"record {number} is not a table")
        relative = record.get("path")
        role = record.get("role")
        claim_status = record.get("claim_status")
        phase = record.get("phase")
        immutable = record.get("immutable")
        if not isinstance(relative, str) or not relative:
            raise LegacyIndexError(f"record {number} has no path")
        if Path(relative).is_absolute() or relative in seen:
            raise LegacyIndexError(f"duplicate or absolute indexed path: {relative}")
        if role not in ROLES or claim_status not in CLAIM_STATUSES:
            raise LegacyIndexError(f"invalid classification for {relative}")
        if not isinstance(phase, str) or not re.fullmatch(r"P(?:[0-9]|1[0-2])", phase):
            raise LegacyIndexError(f"invalid reconstruction phase for {relative}")
        if not isinstance(immutable, bool):
            raise LegacyIndexError(f"immutable must be boolean for {relative}")
        source = _exact_path(root, relative)
        seen.add(relative)
        if role in AUTHORITIES:
            authorities[role] = relative
        if immutable:
            expected = record.get("sha256")
            actual = hashlib.sha256(source.read_bytes()).hexdigest()
            if not isinstance(expected, str) or expected != actual:
                raise LegacyIndexError(f"immutable source hash mismatch: {relative}")
    if authorities != AUTHORITIES:
        raise LegacyIndexError(
            f"authority mapping mismatch: expected {AUTHORITIES}, found {authorities}"
        )
    return len(records)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--index", type=Path)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    try:
        count = validate(root, args.index)
    except LegacyIndexError as exc:
        print(f"legacy-index: FAIL: {exc}", file=sys.stderr)
        return 1
    print(f"legacy-index: PASS ({count} records)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
