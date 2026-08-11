#!/usr/bin/env python3
"""Validate the accepted reconstruction ADR index and immutable documents."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import re
import sys
try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10 compatibility in the pinned core profile.
    import tomli as tomllib


REQUIRED_TOPICS = {
    "preserve-rebuild-boundary",
    "package-ownership",
    "migration-strategy",
    "compatibility-policy",
    "trust-terminology",
}
ADR_FIELDS = {
    "id",
    "title",
    "path",
    "status",
    "accepted_on",
    "topics",
    "sha256",
    "supersedes",
}


class AdrIndexError(RuntimeError):
    """Raised when accepted reconstruction decisions are incomplete or stale."""


def _exact_file(root: Path, relative: str) -> Path:
    candidate = root
    for part in Path(relative).parts:
        try:
            names = {entry.name for entry in candidate.iterdir()}
        except OSError as exc:
            raise AdrIndexError(f"cannot inspect ADR path {relative}: {exc}") from exc
        if part not in names:
            aliases = sorted(name for name in names if name.casefold() == part.casefold())
            if aliases:
                raise AdrIndexError(
                    f"exact-case mismatch for ADR path {relative}: found {aliases[0]!r}"
                )
            raise AdrIndexError(f"ADR path does not exist: {relative}")
        candidate /= part
    resolved = candidate.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise AdrIndexError(f"ADR path escapes repository: {relative}") from exc
    if not resolved.is_file():
        raise AdrIndexError(f"ADR path is not a file: {relative}")
    return resolved


def validate(root: Path, index_path: Path | None = None) -> int:
    path = index_path or root / "docs" / "reconstruction" / "adrs" / "INDEX.toml"
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise AdrIndexError(f"cannot read ADR index: {exc}") from exc

    entries = data.get("adrs")
    topics = data.get("required_topics")
    if data.get("schema") != 1 or not isinstance(entries, list):
        raise AdrIndexError("ADR index must use schema 1 and [[adrs]] entries")
    if data.get("append_only") is not True:
        raise AdrIndexError("ADR index must declare append_only = true")
    if data.get("supersession_policy") != "new-adr-required":
        raise AdrIndexError("ADR supersession must require a new ADR")
    if not isinstance(topics, list) or set(topics) != REQUIRED_TOPICS:
        raise AdrIndexError("required ADR topic set is incomplete or contains extras")
    if len(topics) != len(set(topics)):
        raise AdrIndexError("required ADR topics contain duplicates")

    seen_ids: set[str] = set()
    seen_paths: set[str] = set()
    topic_owners: dict[str, str] = {}
    for number, entry in enumerate(entries, 1):
        if not isinstance(entry, dict) or set(entry) != ADR_FIELDS:
            raise AdrIndexError(f"ADR entry {number} has missing or unknown fields")
        adr_id = entry["id"]
        title = entry["title"]
        relative = entry["path"]
        entry_topics = entry["topics"]
        supersedes = entry["supersedes"]
        digest = entry["sha256"]
        if not isinstance(adr_id, str) or not re.fullmatch(r"MH-ADR-[0-9]{4}", adr_id):
            raise AdrIndexError(f"invalid ADR id in entry {number}")
        if adr_id in seen_ids:
            raise AdrIndexError(f"duplicate ADR id: {adr_id}")
        if not isinstance(title, str) or not title.strip():
            raise AdrIndexError(f"ADR {adr_id} has no title")
        if not isinstance(relative, str) or Path(relative).is_absolute():
            raise AdrIndexError(f"ADR {adr_id} has an invalid path")
        if relative in seen_paths:
            raise AdrIndexError(f"duplicate ADR path: {relative}")
        if entry["status"] != "accepted":
            raise AdrIndexError(f"ADR {adr_id} is not accepted")
        if not isinstance(entry["accepted_on"], str) or not re.fullmatch(
            r"[0-9]{4}-[0-9]{2}-[0-9]{2}", entry["accepted_on"]
        ):
            raise AdrIndexError(f"ADR {adr_id} has an invalid accepted_on date")
        if not isinstance(entry_topics, list) or not entry_topics:
            raise AdrIndexError(f"ADR {adr_id} owns no decision topic")
        if len(entry_topics) != len(set(entry_topics)):
            raise AdrIndexError(f"ADR {adr_id} repeats a decision topic")
        if not isinstance(supersedes, list) or not all(
            isinstance(item, str) for item in supersedes
        ):
            raise AdrIndexError(f"ADR {adr_id} has an invalid supersedes list")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise AdrIndexError(f"ADR {adr_id} has an invalid SHA-256")

        document = _exact_file(root, relative)
        text = document.read_text(encoding="utf-8")
        expected_heading = f"# {adr_id}: {title}"
        if not text.startswith(expected_heading + "\n"):
            raise AdrIndexError(f"ADR heading mismatch: {adr_id}")
        if "**Status:** Accepted" not in text:
            raise AdrIndexError(f"ADR document is not marked accepted: {adr_id}")
        actual = hashlib.sha256(document.read_bytes()).hexdigest()
        if actual != digest:
            raise AdrIndexError(f"accepted ADR hash mismatch: {adr_id}")

        for topic in entry_topics:
            if topic not in REQUIRED_TOPICS:
                raise AdrIndexError(f"ADR {adr_id} owns unknown topic: {topic}")
            if topic in topic_owners:
                raise AdrIndexError(
                    f"decision topic {topic} owned by both {topic_owners[topic]} and {adr_id}"
                )
            topic_owners[topic] = adr_id
        seen_ids.add(adr_id)
        seen_paths.add(relative)

    if set(topic_owners) != REQUIRED_TOPICS:
        missing = sorted(REQUIRED_TOPICS - set(topic_owners))
        raise AdrIndexError(f"required ADR topics have no owner: {', '.join(missing)}")
    for entry in entries:
        unknown = set(entry["supersedes"]) - seen_ids
        if unknown:
            raise AdrIndexError(
                f"ADR {entry['id']} supersedes unknown ids: {', '.join(sorted(unknown))}"
            )
        if entry["id"] in entry["supersedes"]:
            raise AdrIndexError(f"ADR {entry['id']} cannot supersede itself")
    return len(entries)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--index", type=Path)
    args = parser.parse_args(argv)
    try:
        count = validate(args.root.resolve(), args.index)
    except AdrIndexError as exc:
        print(f"reconstruction-adrs: FAIL: {exc}", file=sys.stderr)
        return 1
    print(f"reconstruction-adrs: PASS ({count} accepted decisions)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
