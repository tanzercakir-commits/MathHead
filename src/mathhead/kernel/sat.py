"""Dependency-minimal SAT assignment and RUP-only DRUP replay.

The public checker accepts only exact, versioned, canonical bytes.  Collection
normalizers in this module are compatibility conveniences and carry no
authority: only :func:`check_sat_certificate` can issue ``checker_attestation``.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Iterator, NoReturn


SAT_REPLAY_CONTRACT_ID = "MH-C-SAT-REPLAY-001"
SAT_REPLAY_CONTRACT_SHA256 = "0bf4edbba9285070ef525ae584124ae4fab2762ce83a42f2434c18c8db6f2b50"
SAT_REPLAY_CHECKER_ID = "mathhead.kernel.sat-replay.v1"
SAT_REPLAY_RESULT_SCHEMA = "mathhead.sat-replay-result.v1"

MAX_CNF_BYTES = 67_108_864
MAX_CERTIFICATE_BYTES = 67_108_864
MAX_RESULT_BYTES = 65_536
MAX_RECORD_BYTES = 1_048_576
MAX_VARIABLES = 1_000_000
MAX_CLAUSES = 2_000_000
MAX_CERTIFICATE_RECORDS = 2_000_000
MAX_LITERALS = 16_000_000
MAX_CLAUSE_WIDTH = 1_000_000
MAX_ADDITIONS = 2_000_000
MAX_DELETIONS = 2_000_000
MAX_WATCH_OCCURRENCES = 4_000_000
MAX_ASSIGNMENTS = 500_000_000
MAX_PROPAGATIONS = 500_000_000
MAX_VISITS = 500_000_000
MAX_LOGICAL_STEPS = 1_000_000_000


class SATReplayValidationError(ValueError):
    """Classified failure at an explicitly requested result boundary."""

    def __init__(self, kind: str, detail: str) -> None:
        self.kind = kind
        self.detail = detail
        super().__init__(f"{kind}: {detail}")


class _ReplayValue:
    __slots__ = ()

    def __reduce__(self) -> NoReturn:
        raise TypeError("SAT replay values cannot be pickled")

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del protocol
        raise TypeError("SAT replay values cannot be pickled")

    def __copy__(self) -> _ReplayValue:
        return self

    def __deepcopy__(self, memo: dict[int, Any]) -> _ReplayValue:
        del memo
        return self


@dataclass(frozen=True, slots=True, init=False)
class SATReplayStats(_ReplayValue):
    additions: int
    assignments: int
    certificate_bytes: int
    certificate_records: int
    clauses: int
    cnf_bytes: int
    deletions: int
    literals: int
    logical_steps: int
    max_clause_width: int
    propagations: int
    variables: int
    visits: int
    watch_occurrences: int

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PermissionError("SAT replay statistics are checker-derived")

    def __init_subclass__(cls, **kwargs: object) -> NoReturn:
        del cls, kwargs
        raise TypeError("SATReplayStats is final")


@dataclass(frozen=True, slots=True, init=False)
class SATReplayResult(_ReplayValue):
    verdict: str
    reason_code: str
    diagnostic: str
    authority: str
    exact: bool
    claim: str | None
    certificate_format: str | None
    cnf_sha256: str | None
    certificate_sha256: str | None
    stats: SATReplayStats
    checker_id: str
    checker_contract_id: str
    checker_contract_sha256: str
    cnf: bytes | None
    certificate: bytes | None

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PermissionError("SAT replay results are created only by check_sat_certificate()")

    def __init_subclass__(cls, **kwargs: object) -> NoReturn:
        del cls, kwargs
        raise TypeError("SATReplayResult is final")

    @property
    def ok(self) -> bool:
        return self.verdict == "verified"


@dataclass(slots=True)
class _Counters:
    additions: int = 0
    assignments: int = 0
    certificate_bytes: int = 0
    certificate_records: int = 0
    clauses: int = 0
    cnf_bytes: int = 0
    deletions: int = 0
    literals: int = 0
    logical_steps: int = 0
    max_clause_width: int = 0
    propagations: int = 0
    variables: int = 0
    visits: int = 0
    watch_occurrences: int = 0

    def step(self, amount: int = 1) -> None:
        if type(amount) is not int or amount < 0:
            raise AssertionError("logical-step charge must be a nonnegative exact integer")
        if amount > MAX_LOGICAL_STEPS - self.logical_steps:
            self.logical_steps = MAX_LOGICAL_STEPS
            raise _Exhausted("logical-step budget exceeded")
        self.logical_steps += amount

    def bump(self, name: str, amount: int, maximum: int) -> None:
        if type(amount) is not int or amount < 0:
            raise AssertionError("counter charge must be a nonnegative exact integer")
        current = getattr(self, name)
        if amount > maximum - current:
            setattr(self, name, maximum)
            raise _Exhausted(f"{name.replace('_', '-')} budget exceeded")
        setattr(self, name, current + amount)
        self.step(amount)


class _Invalid(ValueError):
    def __init__(self, reason_code: str, diagnostic: str) -> None:
        self.reason_code = reason_code
        self.diagnostic = diagnostic
        super().__init__(diagnostic)


class _Unsupported(ValueError):
    def __init__(self, certificate_format: str, diagnostic: str) -> None:
        self.certificate_format = certificate_format
        self.diagnostic = diagnostic
        super().__init__(diagnostic)


class _Refuted(ValueError):
    pass


class _Exhausted(ValueError):
    pass


def _new_stats(counters: _Counters) -> SATReplayStats:
    value = object.__new__(SATReplayStats)
    for name in SATReplayStats.__dataclass_fields__:
        object.__setattr__(value, name, getattr(counters, name))
    return value


def _new_result(
    verdict: str,
    reason_code: str,
    diagnostic: str,
    *,
    counters: _Counters,
    cnf: bytes | None,
    certificate: bytes | None,
    claim: str | None,
    certificate_format: str | None,
    cnf_sha256: str | None,
    certificate_sha256: str | None,
) -> SATReplayResult:
    value = object.__new__(SATReplayResult)
    fields: dict[str, object] = {
        "verdict": verdict,
        "reason_code": reason_code,
        "diagnostic": diagnostic[:512],
        "authority": "checker_attestation" if verdict == "verified" else "none",
        "exact": True,
        "claim": claim,
        "certificate_format": certificate_format,
        "cnf_sha256": cnf_sha256,
        "certificate_sha256": certificate_sha256,
        "stats": _new_stats(counters),
        "checker_id": SAT_REPLAY_CHECKER_ID,
        "checker_contract_id": SAT_REPLAY_CONTRACT_ID,
        "checker_contract_sha256": SAT_REPLAY_CONTRACT_SHA256,
        "cnf": cnf,
        "certificate": certificate,
    }
    for name, item in fields.items():
        object.__setattr__(value, name, item)
    return value


def _fail(kind: str, detail: str) -> NoReturn:
    raise SATReplayValidationError(kind, detail)


def _lines(data: bytes, label: str, counters: _Counters) -> Iterator[tuple[int, bytes]]:
    if not data:
        raise _Invalid(
            "CNF_INVALID" if label == "CNF" else "CERTIFICATE_INVALID",
            f"{label} input is empty",
        )
    start = 0
    line_number = 0
    size = len(data)
    while start < size:
        search_stop = min(size, start + MAX_RECORD_BYTES + 1)
        end = data.find(b"\n", start, search_stop)
        if end < 0:
            if search_stop < size:
                raise _Exhausted(f"{label} record-byte budget exceeded")
            raise _Invalid(
                "CNF_INVALID" if label == "CNF" else "CERTIFICATE_INVALID",
                f"{label} record is not LF-terminated",
            )
        line_number += 1
        record_size = end - start
        if record_size > MAX_RECORD_BYTES:
            raise _Exhausted(f"{label} record-byte budget exceeded")
        line = data[start:end]
        if not line:
            raise _Invalid(
                "CNF_INVALID" if label == "CNF" else "CERTIFICATE_INVALID",
                f"{label} line {line_number} is blank",
            )
        if b"\r" in line or b"\t" in line:
            raise _Invalid(
                "CNF_INVALID" if label == "CNF" else "CERTIFICATE_INVALID",
                f"{label} line {line_number} contains forbidden whitespace",
            )
        if any(byte < 32 or byte > 126 for byte in line):
            raise _Invalid(
                "CNF_INVALID" if label == "CNF" else "CERTIFICATE_INVALID",
                f"{label} line {line_number} is not canonical ASCII",
            )
        counters.step(record_size + 1)
        yield line_number, line
        start = end + 1


def _uint(token: bytes, label: str, maximum: int) -> int:
    if not token or (len(token) > 1 and token[0] == 48) or any(byte < 48 or byte > 57 for byte in token):
        raise _Invalid("CERTIFICATE_INVALID" if label.startswith("certificate") else "CNF_INVALID",
                       f"{label} is not a canonical unsigned decimal")
    if len(token) > len(str(maximum)):
        raise _Exhausted(f"{label} exceeds its declared budget")
    value = int(token)
    if value > maximum:
        raise _Exhausted(f"{label} exceeds its declared budget")
    return value


def _literal(token: bytes, label: str) -> int:
    negative = token.startswith(b"-")
    digits = token[1:] if negative else token
    if (
        not digits
        or token.startswith(b"+")
        or digits == b"0"
        or (len(digits) > 1 and digits[0] == 48)
        or any(byte < 48 or byte > 57 for byte in digits)
    ):
        raise _Invalid("CERTIFICATE_INVALID" if label.startswith("certificate") else "CNF_INVALID",
                       f"{label} contains a noncanonical literal")
    if len(digits) > len(str(MAX_VARIABLES)):
        raise _Exhausted(f"{label} literal magnitude exceeds its declared budget")
    magnitude = int(digits)
    if magnitude > MAX_VARIABLES:
        raise _Exhausted(f"{label} literal magnitude exceeds its declared budget")
    return -magnitude if negative else magnitude


def _literal_key(value: int) -> tuple[int, int]:
    return (abs(value), 0 if value < 0 else 1)


def _clause(payload: bytes, label: str, counters: _Counters) -> tuple[int, ...]:
    tokens = payload.split(b" ")
    if not tokens or any(not token for token in tokens) or tokens[-1] != b"0":
        raise _Invalid("CERTIFICATE_INVALID" if label.startswith("certificate") else "CNF_INVALID",
                       f"{label} must use single spaces and one trailing zero")
    literal_tokens = tokens[:-1]
    if len(literal_tokens) > MAX_CLAUSE_WIDTH:
        raise _Exhausted(f"{label} clause-width budget exceeded")
    values = tuple(_literal(token, label) for token in literal_tokens)
    if values != tuple(sorted(values, key=_literal_key)):
        raise _Invalid("CERTIFICATE_INVALID" if label.startswith("certificate") else "CNF_INVALID",
                       f"{label} literals are not in canonical order")
    if len(set(values)) != len(values):
        raise _Invalid("CERTIFICATE_INVALID" if label.startswith("certificate") else "CNF_INVALID",
                       f"{label} contains a duplicate literal")
    present = set(values)
    if any(-value in present for value in values):
        raise _Invalid("CERTIFICATE_INVALID" if label.startswith("certificate") else "CNF_INVALID",
                       f"{label} contains complementary literals")
    counters.bump("literals", len(values), MAX_LITERALS)
    counters.max_clause_width = max(counters.max_clause_width, len(values))
    counters.step(len(values) + 1)
    return values


def _parse_cnf(data: bytes, counters: _Counters) -> tuple[int, list[tuple[int, ...]]]:
    iterator = _lines(data, "CNF", counters)
    try:
        _, header = next(iterator)
    except StopIteration:
        raise _Invalid("CNF_INVALID", "CNF header is missing") from None
    parts = header.split(b" ")
    if len(parts) != 5 or parts[:3] != [b"p", b"mathhead-cnf", b"1"]:
        raise _Invalid("CNF_INVALID", "CNF header must be 'p mathhead-cnf 1 <variables> <clauses>'")
    variables = _uint(parts[3], "CNF variable count", MAX_VARIABLES)
    declared_clauses = _uint(parts[4], "CNF clause count", MAX_CLAUSES)
    counters.variables = variables
    clauses: list[tuple[int, ...]] = []
    prior: tuple[int, ...] | None = None
    for line_number, line in iterator:
        if len(clauses) >= declared_clauses:
            raise _Invalid("CNF_INVALID", f"CNF has more clauses than declared at line {line_number}")
        item = _clause(line, f"CNF line {line_number}", counters)
        if prior is not None and item <= prior:
            detail = "duplicate" if item == prior else "not lexicographically ordered"
            raise _Invalid("CNF_INVALID", f"CNF clause at line {line_number} is {detail}")
        clauses.append(item)
        prior = item
    if len(clauses) != declared_clauses:
        raise _Invalid("CNF_INVALID", f"CNF declares {declared_clauses} clauses but contains {len(clauses)}")
    maximum = max((abs(literal) for clause in clauses for literal in clause), default=0)
    if variables != maximum:
        raise _Invalid("CNF_INVALID", f"CNF variable count {variables} differs from maximum literal {maximum}")
    counters.clauses = len(clauses)
    return variables, clauses


_UNSET, _TRUE, _FALSE = 0, 1, 2


class _Formula:
    def __init__(self, clauses: list[tuple[int, ...]], variables: int, counters: _Counters) -> None:
        self.clauses: list[tuple[int, ...]] = []
        self.deleted: list[bool] = []
        self.watchlist: dict[int, list[int]] = {}
        self.watched: list[list[int] | None] = []
        self.by_key: dict[tuple[int, ...], list[int]] = {}
        self.unit_indices: list[int] = []
        self.empty_indices: list[int] = []
        self.assign = bytearray(variables + 1)
        self.counters = counters
        for clause in clauses:
            self.add(clause)

    def ensure_capacity(self, variable: int) -> None:
        if variable >= len(self.assign):
            self.assign.extend(bytearray(variable + 1 - len(self.assign)))

    def add(self, clause: tuple[int, ...]) -> None:
        if len(clause) >= 2:
            self.counters.bump("watch_occurrences", 2, MAX_WATCH_OCCURRENCES)
        index = len(self.clauses)
        self.clauses.append(clause)
        self.deleted.append(False)
        self.by_key.setdefault(clause, []).append(index)
        if len(clause) >= 2:
            pair = [clause[0], clause[1]]
            self.watched.append(pair)
            self.watchlist.setdefault(pair[0], []).append(index)
            self.watchlist.setdefault(pair[1], []).append(index)
        else:
            self.watched.append(None)
            (self.unit_indices if clause else self.empty_indices).append(index)
        self.ensure_capacity(max((abs(value) for value in clause), default=0))
        self.counters.step(len(clause) + 1)

    def delete(self, clause: tuple[int, ...]) -> bool:
        self.counters.step()
        stack = self.by_key.get(clause, [])
        while stack:
            index = stack.pop()
            self.counters.step()
            if not self.deleted[index]:
                self.deleted[index] = True
                return True
        return False

    def conflict(self, assumed: tuple[int, ...], include_deleted: bool) -> bool:
        clauses = self.clauses
        deleted = self.deleted
        assign = self.assign
        trail: list[int] = []

        def set_literal(literal: int) -> bool:
            variable = abs(literal)
            wanted = _TRUE if literal > 0 else _FALSE
            current = assign[variable]
            self.counters.step()
            if current == _UNSET:
                self.counters.bump("assignments", 1, MAX_ASSIGNMENTS)
                assign[variable] = wanted
                trail.append(literal)
                return True
            return current == wanted

        try:
            for index in self.empty_indices:
                self.counters.step()
                if include_deleted or not deleted[index]:
                    return True
            for literal in assumed:
                if not set_literal(literal):
                    return True
            for index in self.unit_indices:
                self.counters.step()
                if (include_deleted or not deleted[index]) and not set_literal(clauses[index][0]):
                    return True
            head = 0
            while head < len(trail):
                literal = trail[head]
                head += 1
                self.counters.bump("propagations", 1, MAX_PROPAGATIONS)
                false_literal = -literal
                watched_here = self.watchlist.get(false_literal)
                if not watched_here:
                    continue
                offset = 0
                while offset < len(watched_here):
                    index = watched_here[offset]
                    if deleted[index] and not include_deleted:
                        offset += 1
                        continue
                    self.counters.bump("visits", 1, MAX_VISITS)
                    pair = self.watched[index]
                    if pair is None:
                        raise AssertionError("non-binary clause entered a watch list")
                    if pair[0] == false_literal:
                        false_position = 0
                        other = pair[1]
                    elif pair[1] == false_literal:
                        false_position = 1
                        other = pair[0]
                    else:
                        raise AssertionError("watch list and clause watch disagree")
                    other_value = assign[abs(other)]
                    if other_value != _UNSET and (other_value == _TRUE) == (other > 0):
                        offset += 1
                        continue
                    replacement = 0
                    for candidate in clauses[index]:
                        self.counters.step()
                        if candidate == other or candidate == false_literal:
                            continue
                        candidate_value = assign[abs(candidate)]
                        if candidate_value == _UNSET or (candidate_value == _TRUE) == (candidate > 0):
                            replacement = candidate
                            break
                    if replacement:
                        pair[false_position] = replacement
                        watched_here[offset] = watched_here[-1]
                        watched_here.pop()
                        self.watchlist.setdefault(replacement, []).append(index)
                        continue
                    if other_value == _UNSET:
                        if not set_literal(other):
                            return True
                        offset += 1
                        continue
                    return True
            return False
        finally:
            for literal in trail:
                assign[abs(literal)] = _UNSET


def _certificate_header(
    line: bytes, cnf_digest: str
) -> tuple[str, str, str]:
    parts = line.split(b" ")
    known = {b"mathhead-sat-assignment", b"mathhead-drup", b"mathhead-drat"}
    if len(parts) < 2 or parts[0] != b"p" or parts[1] not in known:
        raise _Unsupported("unknown", "certificate format or version is unsupported")
    name = parts[1]
    if len(parts) != 4 or parts[2] != b"1":
        raise _Unsupported("unknown", "certificate format or version is unsupported")
    if len(parts) == 4:
        try:
            digest = parts[3].decode("ascii")
        except UnicodeDecodeError:
            digest = ""
        if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
            raise _Invalid("CERTIFICATE_INVALID", "certificate header has a noncanonical CNF SHA-256")
        if digest != cnf_digest:
            raise _Invalid("CERTIFICATE_INVALID", "certificate CNF SHA-256 does not match the exact CNF bytes")
        if name == b"mathhead-sat-assignment":
            return "sat", "sat-assignment-v1", digest
        if name == b"mathhead-drup":
            return "unsat", "drup-v1", digest
        if name == b"mathhead-drat":
            raise _Unsupported("drat-v1", "DRAT/RAT certificates are recognized but unsupported")
    raise AssertionError("known certificate header dispatch is incomplete")


def _check_sat(
    iterator: Iterator[tuple[int, bytes]],
    variables: int,
    clauses: list[tuple[int, ...]],
    counters: _Counters,
) -> str:
    try:
        line_number, line = next(iterator)
    except StopIteration:
        raise _Invalid("CERTIFICATE_INVALID", "SAT certificate assignment record is missing") from None
    if not line.startswith(b"v "):
        raise _Invalid("CERTIFICATE_INVALID", f"certificate line {line_number} must be one v record")
    assignment = _clause(line[2:], f"certificate line {line_number}", counters)
    try:
        next(iterator)
    except StopIteration:
        pass
    else:
        raise _Invalid("CERTIFICATE_INVALID", "SAT certificate contains more than one assignment record")
    counters.certificate_records = 1
    if len(assignment) != variables or any(
        abs(value) != expected for expected, value in enumerate(assignment, 1)
    ):
        raise _Invalid("CERTIFICATE_INVALID", "SAT assignment must contain exactly one sign for every variable in order")
    truth = bytearray(variables + 1)
    for literal in assignment:
        counters.bump("assignments", 1, MAX_ASSIGNMENTS)
        truth[abs(literal)] = _TRUE if literal > 0 else _FALSE
    for index, clause in enumerate(clauses, 1):
        counters.bump("visits", 1, MAX_VISITS)
        satisfied = False
        for literal in clause:
            counters.step()
            if (truth[abs(literal)] == _TRUE) == (literal > 0):
                satisfied = True
                break
        if not satisfied:
            raise _Refuted(f"SAT assignment falsifies canonical CNF clause {index}")
    return "SAT assignment satisfies every canonical CNF clause"


def _check_drup(
    iterator: Iterator[tuple[int, bytes]],
    variables: int,
    clauses: list[tuple[int, ...]],
    counters: _Counters,
) -> str:
    formula = _Formula(clauses, variables, counters)
    include_deleted = False
    include_deleted_from: int | None = None
    applied_deletions = 0
    empty_derived = False
    for line_number, line in iterator:
        counters.bump("certificate_records", 1, MAX_CERTIFICATE_RECORDS)
        if line.startswith(b"a "):
            operation = "a"
        elif line.startswith(b"d "):
            operation = "d"
        else:
            raise _Invalid("CERTIFICATE_INVALID", f"certificate line {line_number} must begin with 'a ' or 'd '")
        clause = _clause(line[2:], f"certificate line {line_number}", counters)
        if operation == "d":
            counters.bump("deletions", 1, MAX_DELETIONS)
            if formula.delete(clause):
                applied_deletions += 1
            continue
        counters.bump("additions", 1, MAX_ADDITIONS)
        formula.ensure_capacity(max((abs(value) for value in clause), default=0))
        assumptions = tuple(-value for value in clause)
        conflict = formula.conflict(assumptions, include_deleted)
        if not conflict and not include_deleted:
            conflict = formula.conflict(assumptions, True)
            if conflict:
                include_deleted = True
                include_deleted_from = counters.additions
        if not conflict:
            raise _Refuted(f"proof addition {counters.additions} is not RUP with respect to the accumulated formula")
        formula.add(clause)
        if not clause:
            empty_derived = True
    if empty_derived:
        suffix = (
            f" with retained deleted clauses from proof addition {include_deleted_from}"
            if include_deleted
            else ""
        )
        return f"the empty clause was derived by reverse unit propagation{suffix}"
    if formula.conflict((), include_deleted):
        suffix = (
            f" with retained deleted clauses from proof addition {include_deleted_from}"
            if include_deleted
            else ""
        )
        return f"the final formula unit-propagates to a conflict{suffix}"
    if not include_deleted and applied_deletions and formula.conflict((), True):
        return "the final formula unit-propagates to a conflict with retained deleted clauses"
    raise _Refuted("the proof ends without deriving the empty clause or a final formula conflict")


def check_sat_certificate(cnf: bytes, certificate: bytes) -> SATReplayResult:
    """Replay one canonical SAT assignment or RUP-only DRUP refutation."""
    counters = _Counters()
    exact_cnf = cnf if type(cnf) is bytes else None
    exact_certificate = certificate if type(certificate) is bytes else None
    cnf_digest: str | None = None
    certificate_digest: str | None = None
    if type(cnf) is not bytes or type(certificate) is not bytes:
        return _new_result(
            "invalid", "INPUT_TYPE_INVALID", "cnf and certificate must be exact bytes",
            counters=counters, cnf=exact_cnf, certificate=exact_certificate,
            claim=None, certificate_format=None, cnf_sha256=cnf_digest,
            certificate_sha256=certificate_digest,
        )
    counters.cnf_bytes = min(len(cnf), MAX_CNF_BYTES)
    counters.certificate_bytes = min(len(certificate), MAX_CERTIFICATE_BYTES)
    claim: str | None = None
    certificate_format: str | None = None
    try:
        if len(cnf) > MAX_CNF_BYTES:
            raise _Exhausted("CNF byte budget exceeded")
        if len(certificate) > MAX_CERTIFICATE_BYTES:
            raise _Exhausted("certificate byte budget exceeded")
        cnf_digest = hashlib.sha256(cnf).hexdigest()
        certificate_digest = hashlib.sha256(certificate).hexdigest()
        variables, clauses = _parse_cnf(cnf, counters)
        iterator = _lines(certificate, "certificate", counters)
        try:
            _, header = next(iterator)
        except StopIteration:
            raise _Invalid("CERTIFICATE_INVALID", "certificate header is missing") from None
        claim, certificate_format, _ = _certificate_header(header, cnf_digest)
        if claim == "sat":
            diagnostic = _check_sat(iterator, variables, clauses, counters)
            reason = "SAT_VERIFIED"
        else:
            diagnostic = _check_drup(iterator, variables, clauses, counters)
            reason = "UNSAT_VERIFIED"
        return _new_result(
            "verified", reason, diagnostic, counters=counters, cnf=cnf, certificate=certificate,
            claim=claim, certificate_format=certificate_format, cnf_sha256=cnf_digest,
            certificate_sha256=certificate_digest,
        )
    except _Unsupported as exc:
        return _new_result(
            "unsupported", "FORMAT_UNSUPPORTED", exc.diagnostic,
            counters=counters, cnf=cnf, certificate=certificate, claim="unsat" if exc.certificate_format == "drat-v1" else None,
            certificate_format=exc.certificate_format, cnf_sha256=cnf_digest,
            certificate_sha256=certificate_digest,
        )
    except _Invalid as exc:
        return _new_result(
            "invalid", exc.reason_code, exc.diagnostic,
            counters=counters, cnf=cnf, certificate=certificate, claim=claim,
            certificate_format=certificate_format, cnf_sha256=cnf_digest,
            certificate_sha256=certificate_digest,
        )
    except _Refuted as exc:
        return _new_result(
            "refuted", "CLAIM_REFUTED", str(exc),
            counters=counters, cnf=cnf, certificate=certificate, claim=claim,
            certificate_format=certificate_format, cnf_sha256=cnf_digest,
            certificate_sha256=certificate_digest,
        )
    except _Exhausted as exc:
        return _new_result(
            "exhausted", "BUDGET_EXHAUSTED", str(exc),
            counters=counters, cnf=cnf, certificate=certificate, claim=claim,
            certificate_format=certificate_format, cnf_sha256=cnf_digest,
            certificate_sha256=certificate_digest,
        )


def _normalize_clause(value: object, label: str) -> tuple[int, ...] | None:
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{label} must be a list or tuple of literals")
    if len(value) > MAX_CLAUSE_WIDTH:
        raise ValueError(f"{label} exceeds the clause-width budget")
    literals: set[int] = set()
    for item in value:
        if type(item) is not int or item == 0 or abs(item) > MAX_VARIABLES:
            raise ValueError(f"{label} must contain bounded nonzero exact integers")
        if -item in literals:
            return None
        literals.add(item)
    return tuple(sorted(literals, key=_literal_key))


def canonical_cnf_bytes(clauses: object) -> bytes:
    """Normalize a legacy collection CNF into unique canonical checker bytes."""
    if not isinstance(clauses, (list, tuple)):
        raise ValueError("clauses must be a list or tuple")
    if len(clauses) > MAX_CLAUSES:
        raise ValueError("too many clauses")
    normalized: set[tuple[int, ...]] = set()
    for index, clause in enumerate(clauses, 1):
        item = _normalize_clause(clause, f"clause {index}")
        if item is not None:
            normalized.add(item)
    ordered = sorted(normalized)
    literal_count = sum(len(clause) for clause in ordered)
    if literal_count > MAX_LITERALS:
        raise ValueError("too many literals")
    variables = max((abs(value) for clause in ordered for value in clause), default=0)
    data = bytearray(f"p mathhead-cnf 1 {variables} {len(ordered)}\n".encode("ascii"))
    for clause in ordered:
        record = (" ".join([*(str(value) for value in clause), "0"]) + "\n").encode("ascii")
        if len(record) - 1 > MAX_RECORD_BYTES:
            raise ValueError("canonical CNF record exceeds the record-byte budget")
        if len(record) > MAX_CNF_BYTES - len(data):
            raise ValueError("canonical CNF exceeds the byte budget")
        data.extend(record)
    return bytes(data)


def canonical_drup_bytes(cnf: bytes, steps: object) -> bytes:
    """Normalize legacy add/delete collections into canonical RUP-only DRUP bytes."""
    if type(cnf) is not bytes:
        raise ValueError("cnf must be exact canonical bytes")
    if len(cnf) > MAX_CNF_BYTES:
        raise ValueError("cnf exceeds the byte budget")
    if not isinstance(steps, (list, tuple)):
        raise ValueError("steps must be a list or tuple")
    if len(steps) > MAX_CERTIFICATE_RECORDS:
        raise ValueError("too many proof records")
    data = bytearray(f"p mathhead-drup 1 {hashlib.sha256(cnf).hexdigest()}\n".encode("ascii"))
    literals = 0
    additions = 0
    deletions = 0
    for index, step in enumerate(steps, 1):
        if not isinstance(step, (list, tuple)) or len(step) != 2 or step[0] not in {"a", "d"}:
            raise ValueError(f"proof record {index} must be an ('a'|'d', clause) pair")
        clause = _normalize_clause(step[1], f"proof record {index}")
        if clause is None:
            raise ValueError(f"proof record {index} is tautological")
        literals += len(clause)
        additions += step[0] == "a"
        deletions += step[0] == "d"
        if literals > MAX_LITERALS or additions > MAX_ADDITIONS or deletions > MAX_DELETIONS:
            raise ValueError("canonical DRUP certificate exceeds its record or literal budget")
        record = (
            step[0] + " " + " ".join([*(str(value) for value in clause), "0"]) + "\n"
        ).encode("ascii")
        if len(record) - 1 > MAX_RECORD_BYTES:
            raise ValueError("canonical DRUP record exceeds the record-byte budget")
        if len(record) > MAX_CERTIFICATE_BYTES - len(data):
            raise ValueError("canonical DRUP certificate exceeds the byte budget")
        data.extend(record)
    return bytes(data)


def canonical_sat_assignment_bytes(cnf: bytes, assignment: object) -> bytes:
    """Normalize one signed-literal assignment into canonical certificate bytes."""
    if type(cnf) is not bytes:
        raise ValueError("cnf must be exact canonical bytes")
    if len(cnf) > MAX_CNF_BYTES:
        raise ValueError("cnf exceeds the byte budget")
    clause = _normalize_clause(assignment, "assignment")
    if clause is None:
        raise ValueError("assignment contains both signs of a variable")
    ordered = tuple(sorted(clause, key=lambda value: abs(value)))
    data = (
        f"p mathhead-sat-assignment 1 {hashlib.sha256(cnf).hexdigest()}\n"
        + "v " + " ".join([*(str(value) for value in ordered), "0"]) + "\n"
    ).encode("ascii")
    if len(data) > MAX_CERTIFICATE_BYTES or len(data.split(b"\n", 1)[1]) - 1 > MAX_RECORD_BYTES:
        raise ValueError("canonical SAT assignment exceeds the byte or record budget")
    return data


def _stats_object(stats: SATReplayStats) -> dict[str, int]:
    if type(stats) is not SATReplayStats:
        _fail("result", "stats has the wrong exact type")
    return {name: getattr(stats, name) for name in SATReplayStats.__dataclass_fields__}


def _result_object(result: SATReplayResult) -> dict[str, object]:
    return {
        "authority": result.authority,
        "certificate_format": result.certificate_format,
        "certificate_sha256": result.certificate_sha256,
        "checker": {
            "checker_id": result.checker_id,
            "contract_id": result.checker_contract_id,
            "contract_sha256": result.checker_contract_sha256,
        },
        "claim": result.claim,
        "cnf_sha256": result.cnf_sha256,
        "diagnostic": result.diagnostic,
        "exact": result.exact,
        "reason_code": result.reason_code,
        "stats": _stats_object(result.stats),
        "verdict": result.verdict,
    }


def _canonical_json_bytes(value: object) -> bytes:
    try:
        text = json.dumps(value, ensure_ascii=True, allow_nan=False, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError, OverflowError) as exc:
        _fail("canonical", f"canonical JSON encoding failed: {type(exc).__name__}")
    return (text + "\n").encode("ascii")


def validate_sat_replay_result(result: SATReplayResult) -> SATReplayResult:
    """Recompute an in-memory result from its retained exact inputs."""
    if type(result) is not SATReplayResult:
        _fail("type", "result must be an exact SATReplayResult")
    expected = check_sat_certificate(result.cnf, result.certificate)
    if result != expected:
        _fail("result", "SAT replay result differs from independent recomputation")
    return result


def sat_replay_result_sha256(result: SATReplayResult) -> str:
    validate_sat_replay_result(result)
    return hashlib.sha256(_canonical_json_bytes(_result_object(result))).hexdigest()


def sat_replay_result_to_bytes(result: SATReplayResult) -> bytes:
    validate_sat_replay_result(result)
    envelope = {
        "result": _result_object(result),
        "result_sha256": sat_replay_result_sha256(result),
        "schema": SAT_REPLAY_RESULT_SCHEMA,
    }
    data = _canonical_json_bytes(envelope)
    if len(data) > MAX_RESULT_BYTES:
        _fail("budget", "SAT replay result exceeds the output-byte budget")
    return data


class _DuplicateKey(ValueError):
    pass


def _pairs_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKey(key)
        result[key] = value
    return result


def _reject_number(value: str) -> NoReturn:
    del value
    raise ValueError("floating-point JSON numbers are forbidden")


def parse_sat_replay_result(data: bytes, cnf: bytes, certificate: bytes) -> SATReplayResult:
    """Parse canonical result bytes and replay them against the supplied exact inputs."""
    if type(data) is not bytes or type(cnf) is not bytes or type(certificate) is not bytes:
        _fail("type", "result, CNF, and certificate inputs must be exact bytes")
    if len(data) > MAX_RESULT_BYTES:
        _fail("budget", "SAT replay result exceeds the input-byte budget")
    try:
        raw = json.loads(
            data.decode("ascii"), object_pairs_hook=_pairs_object,
            parse_float=_reject_number, parse_constant=_reject_number,
        )
    except UnicodeDecodeError as exc:
        _fail("encoding", f"SAT replay result is not ASCII at byte {exc.start}")
    except _DuplicateKey as exc:
        _fail("duplicate", f"duplicate JSON key: {exc.args[0]}")
    except RecursionError:
        _fail("budget", "SAT replay result JSON nesting exceeds the parser budget")
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        _fail("schema", f"invalid SAT replay result JSON: {type(exc).__name__}")
    if type(raw) is not dict or set(raw) != {"result", "result_sha256", "schema"}:
        _fail("schema", "SAT replay result envelope fields differ")
    if raw["schema"] != SAT_REPLAY_RESULT_SCHEMA:
        _fail("schema", "SAT replay result schema differs")
    digest = raw["result_sha256"]
    if type(digest) is not str or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        _fail("schema", "result_sha256 is not lowercase SHA-256")
    expected = check_sat_certificate(cnf, certificate)
    item = _result_object(expected)
    if raw["result"] != item:
        _fail("result", "serialized SAT replay result differs from independent recomputation")
    actual = hashlib.sha256(_canonical_json_bytes(item)).hexdigest()
    if digest != actual:
        _fail("identity", "SAT replay result SHA-256 differs")
    if data != sat_replay_result_to_bytes(expected):
        _fail("canonical", "SAT replay result bytes are not canonical")
    return expected


__all__ = [
    "SATReplayResult",
    "SATReplayStats",
    "SATReplayValidationError",
    "SAT_REPLAY_CHECKER_ID",
    "SAT_REPLAY_CONTRACT_ID",
    "SAT_REPLAY_CONTRACT_SHA256",
    "SAT_REPLAY_RESULT_SCHEMA",
    "canonical_cnf_bytes",
    "canonical_drup_bytes",
    "canonical_sat_assignment_bytes",
    "check_sat_certificate",
    "parse_sat_replay_result",
    "sat_replay_result_sha256",
    "sat_replay_result_to_bytes",
    "validate_sat_replay_result",
]
