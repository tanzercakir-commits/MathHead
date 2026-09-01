"""Legacy discovery adapter for the versioned dependency-minimal SAT checker.

The public result shape remains compatible with the Ramsey discovery pipeline,
but all mathematical authority comes from :mod:`mathhead.kernel.sat`.  Parsing
solver line collections and translating result labels do not grant authority.
"""

from __future__ import annotations

from dataclasses import dataclass

from mathhead.kernel.sat import (
    canonical_cnf_bytes,
    canonical_drup_bytes,
    check_sat_certificate,
)


_DEFAULT_VISIT_BUDGET = 500_000_000


@dataclass
class RupCheckResult:
    status: str
    message: str
    lemmas_checked: int = 0
    deletions_applied: int = 0
    visits: int = 0
    deletions_ignored_from: int | None = None

    @property
    def ok(self) -> bool:
        return self.status == "verified"


def parse_drup(lines: list[str]) -> list[tuple[str, tuple[int, ...]]]:
    """Parse PySAT-style DRUP lines into legacy add/delete steps."""
    steps: list[tuple[str, tuple[int, ...]]] = []
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("c"):
            continue
        operation = "a"
        if line == "d" or line.startswith("d "):
            operation, line = "d", line[1:].strip()
        try:
            numbers = [int(token) for token in line.split()]
        except ValueError as exc:
            raise ValueError(f"unparseable DRUP line: {raw!r}") from exc
        if numbers and numbers[-1] == 0:
            numbers = numbers[:-1]
        if any(value == 0 for value in numbers):
            raise ValueError(f"literal 0 inside a DRUP clause: {raw!r}")
        steps.append((operation, tuple(numbers)))
    return steps


def _key(clause: object) -> tuple[int, ...] | None:
    if not isinstance(clause, (list, tuple)):
        return None
    values: set[int] = set()
    for value in clause:
        if type(value) is not int or value == 0:
            return None
        if -value in values:
            return None
        values.add(value)
    return tuple(sorted(values, key=lambda value: (abs(value), 0 if value < 0 else 1)))


def _applied_deletions(clauses: object, steps: object, records: int) -> int:
    if not isinstance(clauses, (list, tuple)) or not isinstance(steps, (list, tuple)):
        return 0
    active: dict[tuple[int, ...], int] = {}
    for clause in clauses:
        key = _key(clause)
        if key is not None:
            active[key] = 1
    applied = 0
    for step in steps[:records]:
        if not isinstance(step, (list, tuple)) or len(step) != 2:
            continue
        key = _key(step[1])
        if key is None:
            continue
        if step[0] == "a":
            active[key] = active.get(key, 0) + 1
        elif step[0] == "d" and active.get(key, 0):
            active[key] -= 1
            applied += 1
    return applied


def check_drup_proof(
    clauses: list[list[int]],
    steps: list[tuple[str, tuple[int, ...]]],
    visit_budget: int = _DEFAULT_VISIT_BUDGET,
) -> RupCheckResult:
    """Translate and replay a legacy RUP-only DRUP proof through the kernel checker."""
    if not isinstance(clauses, (list, tuple)) or not isinstance(steps, (list, tuple)):
        return RupCheckResult(
            "error",
            "clauses and steps must be lists (got "
            f"{type(clauses).__name__}, {type(steps).__name__})",
        )
    if type(visit_budget) is not int or visit_budget < 0 or visit_budget > _DEFAULT_VISIT_BUDGET:
        return RupCheckResult("error", "visit_budget must be an integer from 0 through 500000000")
    try:
        cnf = canonical_cnf_bytes(clauses)
        certificate = canonical_drup_bytes(cnf, steps)
    except (TypeError, ValueError) as exc:
        return RupCheckResult("error", str(exc))
    replay = check_sat_certificate(cnf, certificate)
    visits = replay.stats.visits
    checked = replay.stats.additions
    if replay.verdict == "refuted" and checked:
        checked -= 1
    applied = _applied_deletions(clauses, steps, replay.stats.certificate_records)
    marker = "retained deleted clauses from proof addition "
    ignored = (
        int(replay.diagnostic.rsplit(marker, 1)[1])
        if marker in replay.diagnostic
        else None
    )
    if visits > visit_budget:
        return RupCheckResult(
            "budget_exceeded",
            f"RUP checking exceeded the visit budget ({visit_budget}) after {checked} lemmas — "
            "no verdict on the proof (honest: neither verified nor refuted)",
            checked,
            applied,
            visit_budget,
            ignored,
        )
    if replay.verdict == "verified":
        return RupCheckResult("verified", replay.diagnostic, checked, applied, visits, ignored)
    if replay.verdict == "refuted":
        return RupCheckResult("refuted", replay.diagnostic, checked, applied, visits, ignored)
    if replay.verdict == "exhausted":
        return RupCheckResult("budget_exceeded", replay.diagnostic, checked, applied, visits, ignored)
    return RupCheckResult("error", replay.diagnostic, checked, applied, visits, ignored)


def check_drup_lines(
    clauses: list[list[int]],
    lines: list[str],
    visit_budget: int = _DEFAULT_VISIT_BUDGET,
) -> RupCheckResult:
    """Parse PySAT proof lines, then replay them at the canonical kernel boundary."""
    if not isinstance(clauses, (list, tuple)):
        return RupCheckResult("error", f"clauses must be a list of clauses, got {type(clauses).__name__}")
    if not isinstance(lines, (list, tuple)) or any(not isinstance(line, str) for line in lines):
        detail = type(lines).__name__ if not isinstance(lines, (list, tuple)) else "non-string entries"
        return RupCheckResult("error", f"proof lines must be a list of strings, got {detail}")
    try:
        steps = parse_drup(lines)
    except ValueError as exc:
        return RupCheckResult("error", str(exc))
    return check_drup_proof(clauses, steps, visit_budget=visit_budget)


__all__ = ["RupCheckResult", "check_drup_lines", "check_drup_proof", "parse_drup"]
