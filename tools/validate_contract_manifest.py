#!/usr/bin/env python3
"""Validate MathHead's accepted and proposed contract manifest fail-closed."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import tomllib


CONTRACT_ID = re.compile(r"^MH-C-[A-Z0-9-]+$")
PROPOSAL_FIELDS = {
    "schema",
    "contract_id",
    "target",
    "signature",
    "requires",
    "ensures",
    "raises",
    "effects",
    "determinism",
    "budget",
    "epistemics",
    "invariants",
    "validators",
    "supersedes",
}


class ContractManifestError(RuntimeError):
    """Raised when contract identity or acceptance evidence is invalid."""


def _exact_file(root: Path, relative: str) -> Path:
    if Path(relative).is_absolute():
        raise ContractManifestError(f"contract path must be relative: {relative}")
    current = root
    for part in Path(relative).parts:
        try:
            names = {entry.name for entry in current.iterdir()}
        except OSError as exc:
            raise ContractManifestError(f"cannot inspect contract path: {exc}") from exc
        if part not in names:
            aliases = sorted(name for name in names if name.casefold() == part.casefold())
            if aliases:
                raise ContractManifestError(
                    f"exact-case mismatch for {relative}: found {aliases[0]!r}"
                )
            raise ContractManifestError(f"contract path does not exist: {relative}")
        current /= part
    resolved = current.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ContractManifestError(f"contract path escapes repository: {relative}") from exc
    if not resolved.is_file():
        raise ContractManifestError(f"contract path is not a file: {relative}")
    return resolved


def _validate_proposal(path: Path, contract_id: str) -> None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ContractManifestError(f"invalid proposed JSON contract {contract_id}: {exc}") from exc
    if not isinstance(data, dict):
        raise ContractManifestError(f"proposed contract is not an object: {contract_id}")
    fields = set(data)
    if fields != PROPOSAL_FIELDS:
        missing = sorted(PROPOSAL_FIELDS - fields)
        unknown = sorted(fields - PROPOSAL_FIELDS)
        raise ContractManifestError(
            f"proposed contract fields differ for {contract_id}: "
            f"missing={missing}, unknown={unknown}"
        )
    if data["schema"] != "mathhead.function-contract.v1":
        raise ContractManifestError(f"unsupported proposal schema: {contract_id}")
    if data["contract_id"] != contract_id:
        raise ContractManifestError(f"proposal ID mismatch: {contract_id}")
    for key in ("requires", "ensures", "raises", "invariants", "validators"):
        value = data[key]
        if not isinstance(value, list) or not value or not all(
            isinstance(item, str) and item.strip() for item in value
        ):
            raise ContractManifestError(f"proposal {contract_id} has invalid {key}")
    for key in ("effects", "determinism", "budget", "epistemics"):
        if not isinstance(data[key], dict) or not data[key]:
            raise ContractManifestError(f"proposal {contract_id} has invalid {key}")


def validate(root: Path, manifest_path: Path | None = None) -> int:
    path = manifest_path or root / "docs" / "contracts" / "manifest.toml"
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise ContractManifestError(f"cannot read contract manifest: {exc}") from exc
    contracts = data.get("contracts")
    if data.get("schema") != 1 or not isinstance(contracts, list):
        raise ContractManifestError("manifest must use schema 1 and [[contracts]] entries")
    ids: set[str] = set()
    paths: set[str] = set()
    for number, record in enumerate(contracts, 1):
        if not isinstance(record, dict):
            raise ContractManifestError(f"contract {number} is not a table")
        contract_id = record.get("id")
        relative = record.get("path")
        expected = record.get("sha256")
        state = record.get("state")
        if not isinstance(contract_id, str) or not CONTRACT_ID.fullmatch(contract_id):
            raise ContractManifestError(f"invalid contract ID at entry {number}")
        if not isinstance(relative, str) or not relative:
            raise ContractManifestError(f"invalid path for {contract_id}")
        if contract_id in ids or relative in paths:
            raise ContractManifestError(f"duplicate contract ID or path: {contract_id}")
        if state not in {"accepted", "proposed"}:
            raise ContractManifestError(f"invalid state for {contract_id}: {state}")
        in_proposed = "/proposed/" in f"/{relative}"
        if (state == "proposed") != in_proposed:
            raise ContractManifestError(
                f"contract state and directory disagree: {contract_id}"
            )
        source = _exact_file(root, relative)
        actual = hashlib.sha256(source.read_bytes()).hexdigest()
        if not isinstance(expected, str) or expected != actual:
            raise ContractManifestError(f"contract hash mismatch: {contract_id}")
        if state == "proposed":
            _validate_proposal(source, contract_id)
        ids.add(contract_id)
        paths.add(relative)
    todo = (root / "docs" / "TODO.md").read_text(encoding="utf-8")
    referenced = set(re.findall(r"`(MH-C-[A-Z0-9-]+)`", todo))
    missing = sorted(referenced - ids)
    if missing:
        raise ContractManifestError(
            "TODO references contract(s) absent from manifest: " + ", ".join(missing)
        )
    return len(contracts)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args(argv)
    try:
        count = validate(args.root.resolve(), args.manifest)
    except ContractManifestError as exc:
        print(f"contract-manifest: FAIL: {exc}", file=sys.stderr)
        return 1
    print(f"contract-manifest: PASS ({count} contracts)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
