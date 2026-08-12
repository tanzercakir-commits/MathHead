"""Deterministic, non-authoritative alternative-reading analysis for MH-041.

The boundary consumes only canonical accepted MH-040 result bytes.  It projects
the already-declared ProblemIR readings and checks their declared structural
differences.  It does not parse text, synthesize readings, choose a candidate,
normalize mathematical meaning, solve, or issue mathematical authority.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Final, NoReturn
import unicodedata

from mathhead.problem_intake import (
    CONTRACT_ID as INTAKE_CONTRACT_ID,
    CONTRACT_SHA256 as INTAKE_CONTRACT_SHA256,
    PROBLEM_IR_CONTRACT_SHA256,
    PROBLEM_IR_SCHEMA_SHA256,
    ProblemIntakeValidationError,
    canonical_problem_ir_bytes,
    parse_problem_intake_result,
    problem_intake_result_bytes,
)


CONTRACT_ID: Final = "MH-C-READING-ANALYSIS-002"
CONTRACT_SHA256: Final = \
    "0a3e2b077c2593af780c11adca12854bc82336911d852d99f251f56602df3d70"
RESULT_SCHEMA: Final = "mathhead.problem-readings-result.v2"
PROJECTION_SCHEMA: Final = "mathhead.reading-projection.v2"

MAX_INPUT_BYTES: Final = 67_108_864
MAX_OUTPUT_BYTES: Final = 201_326_592
MAX_CANDIDATES: Final = 100_000
MAX_ENTITIES: Final = 100_000
MAX_DELTAS: Final = 400_000
MAX_PATHS: Final = 400_000
MAX_DEPTH: Final = 512
MAX_STEPS: Final = 12_000_000
MAX_STRING_CODEPOINTS: Final = 1_048_576
MAX_AGGREGATE_STRING_CODEPOINTS: Final = 16_777_216
MAX_INTEGER: Final = 9_007_199_254_740_991
MAX_PATH_CODEPOINTS: Final = 4_096
MAX_DIAGNOSTICS: Final = 32
MAX_DIAGNOSTIC_CODEPOINTS: Final = 512

ENTITY_REGISTRIES: Final = (
    "source_documents",
    "source_spans",
    "domains",
    "variables",
    "expressions",
    "relations",
    "statements",
    "definitions",
    "assumptions",
    "goals",
)
SEMANTIC_REGISTRIES: Final = frozenset(ENTITY_REGISTRIES[2:])
REASON_CODES: Final = frozenset(
    {
        "ANALYZED",
        "BUDGET_EXHAUSTED",
        "INVALID_DIFFERENCE",
        "INVALID_INTAKE",
        "INVALID_READING_GRAPH",
        "INVALID_TYPE",
    }
)
DIFFERENCE_KINDS: Final = frozenset(
    {"domain", "quantifier", "scope", "notation", "parse", "reference", "other"}
)

_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_ID = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_PATH = re.compile(r"^\$(?:\.[a-z][a-z0-9_]*|\[[0-9]+\])*$")
_RESULT_TOKEN: Final = object()


class ReadingAnalysisValidationError(ValueError):
    """A strict analysis-result codec invariant failed."""

    __slots__ = ("kind", "path")

    def __init__(self, kind: str, path: str, detail: str) -> None:
        super().__init__(detail)
        self.kind = kind
        self.path = path


class _AnalysisError(ValueError):
    __slots__ = ("kind", "path", "detail")

    def __init__(self, kind: str, path: str, detail: str) -> None:
        super().__init__(detail)
        self.kind = kind
        self.path = path
        self.detail = detail


@dataclass(frozen=True, slots=True)
class ReadingAnalysisDiagnostic:
    code: str
    message: str
    path: str

    def __reduce__(self) -> NoReturn:
        raise TypeError("ReadingAnalysisDiagnostic cannot be pickled")

    def __copy__(self) -> ReadingAnalysisDiagnostic:
        return self

    def __deepcopy__(self, memo: dict[int, object]) -> ReadingAnalysisDiagnostic:
        del memo
        return self


@dataclass(frozen=True, slots=True)
class ReadingDelta:
    ordinal: int
    kind: str
    summary: str
    affected_ids: tuple[str, ...]
    span_ids: tuple[str, ...]
    removed_ids: tuple[str, ...]
    added_ids: tuple[str, ...]
    retained_ids: tuple[str, ...]
    paths: tuple[str, ...]
    before_sha256: str | None
    after_sha256: str | None

    def __reduce__(self) -> NoReturn:
        raise TypeError("ReadingDelta cannot be pickled")


@dataclass(frozen=True, slots=True)
class ReadingCandidate:
    reading_id: str
    difference_from: str | None
    projection_bytes: bytes
    projection_sha256: str
    deltas: tuple[ReadingDelta, ...]

    def __reduce__(self) -> NoReturn:
        raise TypeError("ReadingCandidate cannot be pickled")


@dataclass(frozen=True, slots=True)
class ReadingChoice:
    prompt: str
    candidate_reading_ids: tuple[str, ...]
    selection_required: bool

    def __reduce__(self) -> NoReturn:
        raise TypeError("ReadingChoice cannot be pickled")


@dataclass(frozen=True, slots=True, init=False)
class ReadingAnalysisResult:
    schema: str
    contract_id: str
    contract_sha256: str
    problem_intake_contract_id: str
    problem_intake_contract_sha256: str
    problem_ir_contract_id: str
    problem_ir_contract_sha256: str
    problem_ir_schema_sha256: str
    status: str
    reason_code: str
    input_result_sha256: str | None
    intake_result_bytes: bytes | None
    problem_ir_sha256: str | None
    ambiguity_status: str | None
    base_reading_id: str | None
    selected_reading_id: str | None
    required_choice: ReadingChoice | None
    candidates: tuple[ReadingCandidate, ...]
    diagnostics: tuple[ReadingAnalysisDiagnostic, ...]
    mathematical_authority: bool

    def __init__(
        self,
        *,
        schema: str = RESULT_SCHEMA,
        contract_id: str = CONTRACT_ID,
        contract_sha256: str = CONTRACT_SHA256,
        problem_intake_contract_id: str = INTAKE_CONTRACT_ID,
        problem_intake_contract_sha256: str = INTAKE_CONTRACT_SHA256,
        problem_ir_contract_id: str = "MH-C-PROBLEM-IR-002",
        problem_ir_contract_sha256: str = PROBLEM_IR_CONTRACT_SHA256,
        problem_ir_schema_sha256: str = PROBLEM_IR_SCHEMA_SHA256,
        status: str = "invalid",
        reason_code: str = "INVALID_INTAKE",
        input_result_sha256: str | None = None,
        intake_result_bytes: bytes | None = None,
        problem_ir_sha256: str | None = None,
        ambiguity_status: str | None = None,
        base_reading_id: str | None = None,
        selected_reading_id: str | None = None,
        required_choice: ReadingChoice | None = None,
        candidates: tuple[ReadingCandidate, ...] = (),
        diagnostics: tuple[ReadingAnalysisDiagnostic, ...] = (),
        mathematical_authority: bool = False,
        _token: object | None = None,
    ) -> None:
        if _token is not _RESULT_TOKEN:
            raise PermissionError("ReadingAnalysisResult is constructed by analyze_problem_readings")
        values = locals()
        for field in self.__slots__:
            object.__setattr__(self, field, values[field])

    def __init_subclass__(cls, **kwargs: object) -> NoReturn:
        del cls, kwargs
        raise TypeError("ReadingAnalysisResult is final")

    def __reduce__(self) -> NoReturn:
        raise TypeError("ReadingAnalysisResult cannot be pickled")

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del protocol
        raise TypeError("ReadingAnalysisResult cannot be pickled")

    def __copy__(self) -> ReadingAnalysisResult:
        return self

    def __deepcopy__(self, memo: dict[int, object]) -> ReadingAnalysisResult:
        del memo
        return self


def _fail(kind: str, path: str, detail: str) -> NoReturn:
    raise _AnalysisError(kind, path, detail)


def _step(steps: list[int], path: str, count: int = 1) -> None:
    steps[0] += count
    if steps[0] > MAX_STEPS:
        _fail("budget", path, "validation step budget exceeded")


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical_bytes(value: object, *, maximum: int = MAX_OUTPUT_BYTES) -> bytes:
    aggregate_strings = 0
    stack: list[tuple[object, int, str]] = [(value, 0, "$")]
    while stack:
        item, depth, path = stack.pop()
        if depth > MAX_DEPTH:
            _fail("budget", path, "canonical value nesting exceeds 512")
        if item is None or type(item) is bool:
            continue
        if type(item) is int:
            if abs(item) > MAX_INTEGER:
                _fail("canonical", path, "integer exceeds the portable exact range")
            continue
        if type(item) is str:
            if (
                len(item) > MAX_STRING_CODEPOINTS
                or "\x00" in item
                or unicodedata.normalize("NFC", item) != item
            ):
                _fail("canonical", path, "string is oversized, NUL-bearing, or non-NFC")
            aggregate_strings += len(item)
            if aggregate_strings > MAX_AGGREGATE_STRING_CODEPOINTS:
                _fail("budget", path, "aggregate string budget exceeded")
            continue
        if type(item) is list:
            stack.extend((child, depth + 1, f"{path}[{index}]") for index, child in enumerate(item))
            continue
        if type(item) is dict:
            for key, child in item.items():
                if type(key) is not str:
                    _fail("canonical", path, "object key is not an exact string")
                stack.append((key, depth + 1, path + ".<key>"))
                stack.append((child, depth + 1, path + "." + key))
            continue
        _fail("canonical", path, "floats, subclasses, and non-JSON values are forbidden")
    try:
        rendered = json.dumps(
            value,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError, RecursionError) as exc:
        _fail("canonical", "$", f"value is not canonical JSON: {exc}")
    payload = (rendered + "\n").encode("utf-8")
    if len(payload) > maximum:
        _fail("budget", "$", "canonical output byte budget exceeded")
    return payload


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ReadingAnalysisValidationError("schema", "$", f"duplicate JSON key {key!r}")
        value[key] = item
    return value


def _json_object(data: bytes, path: str) -> dict[str, Any]:
    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=_pairs)
    except ReadingAnalysisValidationError:
        raise
    except RecursionError as exc:
        raise ReadingAnalysisValidationError("budget", path, "JSON nesting budget exceeded") from exc
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ReadingAnalysisValidationError("schema", path, "invalid UTF-8 JSON") from exc
    if type(value) is not dict:
        raise ReadingAnalysisValidationError("schema", path, "expected a JSON object")
    return value


def _indexes(problem: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    registries: dict[str, dict[str, Any]] = {}
    owners: dict[str, str] = {}
    for registry in (*ENTITY_REGISTRIES, "readings"):
        index = {item["id"]: item for item in problem[registry]}
        registries[registry] = index
        for entity_id in index:
            owners[entity_id] = registry
    return registries, owners


def _dependencies(registry: str, record: dict[str, Any]) -> tuple[tuple[str, str], ...]:
    result: list[tuple[str, str]] = []

    def add(owner: str, value: str | None) -> None:
        if value is not None:
            result.append((owner, value))

    def extend(owner: str, values: list[str]) -> None:
        result.extend((owner, value) for value in values)

    if registry != "source_documents":
        extend("source_spans", record.get("span_ids", []))
    if registry == "source_spans":
        add("source_documents", record["source_id"])
    elif registry == "domains":
        kind = record["kind"]
        if kind == "finite":
            add("domains", record["element_domain_id"])
            extend("expressions", record["element_expr_ids"])
        elif kind == "interval":
            add("expressions", record["lower_expr_id"])
            add("expressions", record["upper_expr_id"])
        elif kind == "modular":
            add("expressions", record["modulus_expr_id"])
        elif kind == "collection":
            add("domains", record["element_domain_id"])
        elif kind == "product":
            extend("domains", record["factor_domain_ids"])
        elif kind == "function":
            extend("domains", record["parameter_domain_ids"])
            add("domains", record["result_domain_id"])
        elif kind == "structure":
            extend("domains", record["parameter_domain_ids"])
            extend("expressions", record["parameter_expr_ids"])
    elif registry == "variables":
        add("domains", record["domain_id"])
    elif registry == "expressions":
        add("domains", record["domain_id"])
        kind = record["kind"]
        if kind == "variable":
            add("variables", record["variable_id"])
        elif kind == "apply":
            extend("expressions", record["argument_expr_ids"])
        elif kind in {"tuple", "collection"}:
            extend("expressions", record["element_expr_ids"])
        elif kind == "conditional":
            add("statements", record["condition_statement_id"])
            add("expressions", record["then_expr_id"])
            add("expressions", record["else_expr_id"])
    elif registry == "relations":
        extend("expressions", record["operand_expr_ids"])
    elif registry == "statements":
        kind = record["kind"]
        if kind == "relation":
            add("relations", record["relation_id"])
        elif kind == "logical":
            extend("statements", record["operand_statement_ids"])
        elif kind == "quantified":
            extend("variables", record["variable_ids"])
            add("statements", record["body_statement_id"])
    elif registry == "definitions":
        extend("variables", record["parameter_variable_ids"])
        add("domains", record["result_domain_id"])
        body = record["body"]
        add("expressions" if body["kind"] == "expression" else "statements", body.get(
            "expression_id" if body["kind"] == "expression" else "statement_id"
        ))
    elif registry in {"assumptions", "goals"}:
        add("statements", record["statement_id"])
    return tuple(result)


def _projection(
    problem: dict[str, Any],
    reading: dict[str, Any],
    base_id: str,
    problem_ir_sha256: str,
    indexes: dict[str, dict[str, Any]],
    steps: list[int],
) -> tuple[dict[str, Any], bytes, frozenset[str]]:
    included: dict[str, set[str]] = {registry: set() for registry in ENTITY_REGISTRIES}
    pending: list[tuple[str, str, int]] = []
    pending.extend(("definitions", item, 0) for item in reading["definition_ids"])
    pending.extend(("assumptions", item, 0) for item in reading["assumption_ids"])
    pending.extend(("goals", item, 0) for item in reading["goal_ids"])
    pending.extend(("source_spans", item, 0) for item in reading["span_ids"])
    while pending:
        registry, entity_id, depth = pending.pop()
        _step(steps, f"$.problem.{registry}.{entity_id}")
        if depth > MAX_DEPTH:
            _fail("budget", "$.problem", "projection dependency depth exceeds 512")
        if entity_id in included[registry]:
            continue
        record = indexes[registry].get(entity_id)
        if record is None:
            _fail("reading", f"$.problem.{registry}", f"missing projection entity {entity_id!r}")
        included[registry].add(entity_id)
        if sum(len(values) for values in included.values()) > MAX_ENTITIES:
            _fail("budget", "$.problem", "projection entity budget exceeded")
        pending.extend((*dependency, depth + 1) for dependency in _dependencies(registry, record))

    entity_ids = tuple(sorted(entity_id for values in included.values() for entity_id in values))
    projection = {
        "schema": PROJECTION_SCHEMA,
        "problem_ir_sha256": problem_ir_sha256,
        "reading_id": reading["id"],
        "label": reading["label"],
        "base_reading_id": base_id,
        "is_base": reading["id"] == base_id,
        "definition_ids": list(reading["definition_ids"]),
        "assumption_ids": list(reading["assumption_ids"]),
        "goal_ids": list(reading["goal_ids"]),
        "reading_span_ids": list(reading["span_ids"]),
        "source_span_ids": sorted(included["source_spans"]),
        "entity_ids": list(entity_ids),
        "entities": {
            registry: [record for record in problem[registry] if record["id"] in included[registry]]
            for registry in ENTITY_REGISTRIES
        },
        "extensions": problem["extensions"],
    }
    payload = _canonical_bytes(projection)
    return projection, payload, frozenset(entity_ids)


def _root_positions(reading: dict[str, Any]) -> dict[str, tuple[str, int]]:
    positions: dict[str, tuple[str, int]] = {}
    for field in ("definition_ids", "assumption_ids", "goal_ids"):
        for index, entity_id in enumerate(reading[field]):
            positions[entity_id] = (field, index)
    return positions


def _fragment(
    ids: set[str],
    closure: frozenset[str],
    reading: dict[str, Any],
    indexes: dict[str, dict[str, Any]],
    owners: dict[str, str],
) -> bytes | None:
    present = sorted(ids & set(closure))
    if not present:
        return None
    positions = _root_positions(reading)
    value = []
    for entity_id in present:
        registry = owners[entity_id]
        item: dict[str, Any] = {
            "id": entity_id,
            "registry": registry,
            "record": indexes[registry][entity_id],
            "reading_span_ids": list(reading["span_ids"]),
        }
        if entity_id in positions:
            field, index = positions[entity_id]
            item["root"] = {"field": field, "index": index}
        value.append(item)
    return _canonical_bytes(value)


def _changed_ids(
    base_closure: frozenset[str],
    alternative_closure: frozenset[str],
    base: dict[str, Any],
    alternative: dict[str, Any],
    owners: dict[str, str],
) -> set[str]:
    changed = {
        entity_id
        for entity_id in base_closure ^ alternative_closure
        if owners[entity_id] in SEMANTIC_REGISTRIES
    }
    base_positions = _root_positions(base)
    alternative_positions = _root_positions(alternative)
    for entity_id in set(base_positions) & set(alternative_positions):
        if base_positions[entity_id] != alternative_positions[entity_id]:
            changed.add(entity_id)
    reading_span_changes = set(base["span_ids"]) ^ set(alternative["span_ids"])
    if reading_span_changes:
        for difference in alternative["differences"]:
            if (
                difference["kind"] in {"notation", "parse"}
                and set(difference["span_ids"]) & reading_span_changes
            ):
                changed.update(
                    entity_id
                    for entity_id in difference["affected_ids"]
                    if entity_id in base_closure
                    and entity_id in alternative_closure
                    and owners[entity_id] in SEMANTIC_REGISTRIES
                )
    return changed


def _kind_supported(
    kind: str,
    affected: set[str],
    removed: set[str],
    added: set[str],
    indexes: dict[str, dict[str, Any]],
    owners: dict[str, str],
    source_evidence: bool,
) -> bool:
    changed = removed | added | affected
    records = [(owners[item], indexes[owners[item]][item]) for item in changed]
    has_quantifier = any(
        registry == "statements" and record.get("kind") == "quantified"
        for registry, record in records
    )
    has_domain = any(registry == "domains" for registry, _record in records)
    has_scope = any(
        registry == "definitions"
        or (registry == "variables" and record.get("role") in {"bound", "parameter"})
        for registry, record in records
    )
    if kind == "quantifier":
        return has_quantifier and not has_domain
    if kind == "domain":
        return has_domain
    if kind == "scope":
        return has_scope and not has_quantifier and not has_domain
    if kind in {"notation", "parse"}:
        return source_evidence
    return bool(changed) and not has_quantifier and not has_domain and not has_scope


def _deltas(
    base: dict[str, Any],
    alternative: dict[str, Any],
    base_closure: frozenset[str],
    alternative_closure: frozenset[str],
    indexes: dict[str, dict[str, Any]],
    owners: dict[str, str],
    steps: list[int],
) -> tuple[ReadingDelta, ...]:
    declared = alternative["differences"]
    if not declared:
        _fail("difference", f"$.problem.readings.{alternative['id']}", "alternative has no differences")
    if len(declared) > MAX_DELTAS:
        _fail("budget", f"$.problem.readings.{alternative['id']}", "delta budget exceeded")
    changed = _changed_ids(base_closure, alternative_closure, base, alternative, owners)
    if not changed:
        _fail("difference", f"$.problem.readings.{alternative['id']}", "alternative has no structural change")
    claimed: set[str] = set()
    results: list[ReadingDelta] = []
    for ordinal, difference in enumerate(declared):
        path = f"$.problem.readings.{alternative['id']}.differences[{ordinal}]"
        _step(steps, path, len(difference["affected_ids"]) + len(difference["span_ids"]) + 1)
        affected = set(difference["affected_ids"])
        if not affected or not affected <= changed:
            _fail("difference", path, "affected IDs are empty, unchanged, or surplus")
        if claimed & affected:
            _fail("difference", path, "affected ID appears in more than one difference")
        claimed.update(affected)
        removed = affected & (set(base_closure) - set(alternative_closure))
        added = affected & (set(alternative_closure) - set(base_closure))
        retained = affected - removed - added
        spans = tuple(difference["span_ids"])
        reading_span_changes = set(base["span_ids"]) ^ set(alternative["span_ids"])
        source_evidence = bool(set(spans) & reading_span_changes)
        if difference["kind"] not in DIFFERENCE_KINDS or not _kind_supported(
            difference["kind"], affected, removed, added, indexes, owners, source_evidence
        ):
            _fail("difference", path + ".kind", "difference kind lacks structural evidence")
        base_fragment = _fragment(affected, base_closure, base, indexes, owners)
        alternative_fragment = _fragment(
            affected, alternative_closure, alternative, indexes, owners
        )
        paths: set[str] = set()
        base_positions = _root_positions(base)
        alternative_positions = _root_positions(alternative)
        for entity_id in sorted(affected):
            registry = owners[entity_id]
            if entity_id in removed:
                paths.add(f"$.base.entities.{registry}.{entity_id}")
            elif entity_id in added:
                paths.add(f"$.alternative.entities.{registry}.{entity_id}")
            else:
                if base_positions.get(entity_id) != alternative_positions.get(entity_id):
                    paths.add(f"$.goal_ids.{entity_id}")
                elif difference["kind"] in {"notation", "parse"} and source_evidence:
                    paths.add(f"$.reading_span_ids.{entity_id}")
                else:
                    _fail("difference", path, "retained affected ID has no changed structure")
        if len(paths) > MAX_PATHS or any(len(item) > MAX_PATH_CODEPOINTS for item in paths):
            _fail("budget", path, "delta path budget exceeded")
        results.append(
            ReadingDelta(
                ordinal=ordinal,
                kind=difference["kind"],
                summary=difference["summary"],
                affected_ids=tuple(sorted(affected)),
                span_ids=spans,
                removed_ids=tuple(sorted(removed)),
                added_ids=tuple(sorted(added)),
                retained_ids=tuple(sorted(retained)),
                paths=tuple(sorted(paths)),
                before_sha256=_sha(base_fragment) if base_fragment is not None else None,
                after_sha256=(
                    _sha(alternative_fragment) if alternative_fragment is not None else None
                ),
            )
        )
    if claimed != changed:
        missing = sorted(changed - claimed)
        _fail("difference", f"$.problem.readings.{alternative['id']}",
              f"structural changes omitted from differences: {missing[:4]!r}")
    return tuple(results)


def _diagnostic(error: _AnalysisError) -> ReadingAnalysisDiagnostic:
    code = {
        "budget": "BUDGET_EXHAUSTED",
        "difference": "INVALID_DIFFERENCE",
        "intake": "INVALID_INTAKE",
        "reading": "INVALID_READING_GRAPH",
        "type": "INVALID_TYPE",
    }.get(error.kind, "INVALID_READING_GRAPH")
    path = error.path if _PATH.fullmatch(error.path) is not None else "$"
    message = error.detail[:MAX_DIAGNOSTIC_CODEPOINTS] or "invalid reading analysis"
    return ReadingAnalysisDiagnostic(code=code, message=message, path=path)


def _new_result(**values: object) -> ReadingAnalysisResult:
    result = ReadingAnalysisResult(_token=_RESULT_TOKEN, **values)
    _validate_result_shape(result)
    return result


def analyze_problem_readings(intake_result: bytes) -> ReadingAnalysisResult:
    """Project and compare the readings in one canonical accepted intake result."""
    input_sha: str | None = None
    try:
        if type(intake_result) is not bytes:
            _fail("type", "$", "intake_result must be exact bytes")
        input_sha = _sha(intake_result)
        if len(intake_result) > MAX_INPUT_BYTES:
            _fail("budget", "$", "intake result byte budget exceeded")
        try:
            parsed = parse_problem_intake_result(intake_result)
        except ProblemIntakeValidationError as exc:
            _fail("intake", exc.path, str(exc))
        if parsed.status != "accepted":
            _fail("intake", "$.status", "only an accepted intake result can be analyzed")
        if problem_intake_result_bytes(parsed) != intake_result:
            _fail("intake", "$", "intake result round-trip drift")
        problem_bytes = canonical_problem_ir_bytes(parsed)
        problem_sha = _sha(problem_bytes)
        try:
            problem = json.loads(problem_bytes.decode("utf-8"), object_pairs_hook=_pairs)
        except ReadingAnalysisValidationError as exc:
            _fail("intake", exc.path, str(exc))
        assert type(problem) is dict
        indexes, owners = _indexes(problem)
        readings = indexes["readings"]
        if len(readings) > MAX_CANDIDATES:
            _fail("budget", "$.problem.readings", "candidate budget exceeded")
        bases = [item for item in problem["readings"] if item["difference_from"] is None]
        if len(bases) != 1:
            _fail("reading", "$.problem.readings", "exactly one base reading is required")
        base = bases[0]
        for reading in problem["readings"]:
            if reading is base:
                if reading["differences"]:
                    _fail("reading", f"$.problem.readings.{reading['id']}", "base has differences")
            elif reading["difference_from"] != base["id"]:
                _fail("reading", f"$.problem.readings.{reading['id']}.difference_from",
                      "every alternative must link directly to the base")

        steps = [0]
        projected: dict[str, tuple[dict[str, Any], bytes, frozenset[str]]] = {}
        for reading in problem["readings"]:
            projected[reading["id"]] = _projection(
                problem, reading, base["id"], problem_sha, indexes, steps
            )
        candidates: list[ReadingCandidate] = []
        base_closure = projected[base["id"]][2]
        for reading in sorted(problem["readings"], key=lambda item: item["id"]):
            _projection_value, projection_bytes, closure = projected[reading["id"]]
            deltas = () if reading is base else _deltas(
                base, reading, base_closure, closure, indexes, owners, steps
            )
            candidates.append(
                ReadingCandidate(
                    reading_id=reading["id"],
                    difference_from=reading["difference_from"],
                    projection_bytes=projection_bytes,
                    projection_sha256=_sha(projection_bytes),
                    deltas=deltas,
                )
            )
        ambiguity = problem["ambiguity"]
        choice = None
        if ambiguity["status"] == "unresolved":
            choice = ReadingChoice(
                prompt=ambiguity["required_choice"],
                candidate_reading_ids=tuple(ambiguity["candidate_reading_ids"]),
                selection_required=True,
            )
        result = _new_result(
            status="analyzed",
            reason_code="ANALYZED",
            input_result_sha256=input_sha,
            intake_result_bytes=intake_result,
            problem_ir_sha256=problem_sha,
            ambiguity_status=ambiguity["status"],
            base_reading_id=base["id"],
            selected_reading_id=ambiguity["selected_reading_id"],
            required_choice=choice,
            candidates=tuple(candidates),
            diagnostics=(),
        )
        if len(_result_bytes_unchecked(result)) > MAX_OUTPUT_BYTES:
            _fail("budget", "$", "analysis result byte budget exceeded")
        return result
    except _AnalysisError as error:
        diagnostic = _diagnostic(error)
        return _new_result(
            status="exhausted" if error.kind == "budget" else "invalid",
            reason_code=diagnostic.code,
            input_result_sha256=input_sha,
            diagnostics=(diagnostic,),
        )
    except RecursionError:
        return _new_result(
            status="exhausted",
            reason_code="BUDGET_EXHAUSTED",
            input_result_sha256=input_sha,
            diagnostics=(
                ReadingAnalysisDiagnostic(
                    code="BUDGET_EXHAUSTED",
                    path="$",
                    message="recursive analysis exceeded the structural budget",
                ),
            ),
        )


def _delta_mapping(delta: ReadingDelta) -> dict[str, Any]:
    return {
        "ordinal": delta.ordinal,
        "kind": delta.kind,
        "summary": delta.summary,
        "affected_ids": list(delta.affected_ids),
        "span_ids": list(delta.span_ids),
        "removed_ids": list(delta.removed_ids),
        "added_ids": list(delta.added_ids),
        "retained_ids": list(delta.retained_ids),
        "paths": list(delta.paths),
        "before_sha256": delta.before_sha256,
        "after_sha256": delta.after_sha256,
    }


def _result_mapping(result: ReadingAnalysisResult) -> dict[str, Any]:
    if result.intake_result_bytes is None:
        intake = None
    else:
        intake = _json_object(result.intake_result_bytes, "$.intake_result")
    candidates = []
    for candidate in result.candidates:
        projection = _json_object(candidate.projection_bytes, "$.candidates.projection")
        candidates.append(
            {
                "reading_id": candidate.reading_id,
                "difference_from": candidate.difference_from,
                "projection_sha256": candidate.projection_sha256,
                "projection": projection,
                "deltas": [_delta_mapping(delta) for delta in candidate.deltas],
            }
        )
    choice = result.required_choice
    return {
        "schema": result.schema,
        "contract_id": result.contract_id,
        "contract_sha256": result.contract_sha256,
        "problem_intake_contract_id": result.problem_intake_contract_id,
        "problem_intake_contract_sha256": result.problem_intake_contract_sha256,
        "problem_ir_contract_id": result.problem_ir_contract_id,
        "problem_ir_contract_sha256": result.problem_ir_contract_sha256,
        "problem_ir_schema_sha256": result.problem_ir_schema_sha256,
        "status": result.status,
        "reason_code": result.reason_code,
        "input_result_sha256": result.input_result_sha256,
        "intake_result": intake,
        "problem_ir_sha256": result.problem_ir_sha256,
        "ambiguity_status": result.ambiguity_status,
        "base_reading_id": result.base_reading_id,
        "selected_reading_id": result.selected_reading_id,
        "required_choice": None if choice is None else {
            "prompt": choice.prompt,
            "candidate_reading_ids": list(choice.candidate_reading_ids),
            "selection_required": choice.selection_required,
        },
        "candidates": candidates,
        "diagnostics": [
            {"code": item.code, "path": item.path, "message": item.message}
            for item in result.diagnostics
        ],
        "mathematical_authority": result.mathematical_authority,
    }


def _result_bytes_unchecked(result: ReadingAnalysisResult) -> bytes:
    return _canonical_bytes(_result_mapping(result))


def _validate_result_shape(result: object) -> None:
    if type(result) is not ReadingAnalysisResult:
        raise ReadingAnalysisValidationError("type", "$", "expected exact ReadingAnalysisResult")
    constants = {
        "schema": RESULT_SCHEMA,
        "contract_id": CONTRACT_ID,
        "contract_sha256": CONTRACT_SHA256,
        "problem_intake_contract_id": INTAKE_CONTRACT_ID,
        "problem_intake_contract_sha256": INTAKE_CONTRACT_SHA256,
        "problem_ir_contract_id": "MH-C-PROBLEM-IR-002",
        "problem_ir_contract_sha256": PROBLEM_IR_CONTRACT_SHA256,
        "problem_ir_schema_sha256": PROBLEM_IR_SCHEMA_SHA256,
        "mathematical_authority": False,
    }
    for field, expected in constants.items():
        actual = getattr(result, field, None)
        if type(actual) is not type(expected) or actual != expected:
            raise ReadingAnalysisValidationError("result", f"$.{field}", "result binding drift")
    if result.status not in {"analyzed", "invalid", "exhausted"}:
        raise ReadingAnalysisValidationError("result", "$.status", "unknown result status")
    if result.reason_code not in REASON_CODES:
        raise ReadingAnalysisValidationError("result", "$.reason_code", "unknown reason code")
    if result.input_result_sha256 is not None and (
        type(result.input_result_sha256) is not str
        or _DIGEST.fullmatch(result.input_result_sha256) is None
    ):
        raise ReadingAnalysisValidationError("result", "$.input_result_sha256", "invalid digest")
    if type(result.diagnostics) is not tuple or len(result.diagnostics) > MAX_DIAGNOSTICS:
        raise ReadingAnalysisValidationError("result", "$.diagnostics", "invalid diagnostics")
    for index, diagnostic in enumerate(result.diagnostics):
        path = f"$.diagnostics[{index}]"
        if type(diagnostic) is not ReadingAnalysisDiagnostic or diagnostic.code not in (
            REASON_CODES - {"ANALYZED"}
        ):
            raise ReadingAnalysisValidationError("result", path, "invalid diagnostic")
        if (
            type(diagnostic.message) is not str
            or not diagnostic.message
            or len(diagnostic.message) > MAX_DIAGNOSTIC_CODEPOINTS
            or "\x00" in diagnostic.message
            or unicodedata.normalize("NFC", diagnostic.message) != diagnostic.message
        ):
            raise ReadingAnalysisValidationError("result", path + ".message", "invalid message")
        if type(diagnostic.path) is not str or _PATH.fullmatch(diagnostic.path) is None:
            raise ReadingAnalysisValidationError("result", path + ".path", "invalid path")
    if result.status != "analyzed":
        empty = (
            result.intake_result_bytes is None
            and result.problem_ir_sha256 is None
            and result.ambiguity_status is None
            and result.base_reading_id is None
            and result.selected_reading_id is None
            and result.required_choice is None
            and result.candidates == ()
        )
        if not empty or not result.diagnostics or result.diagnostics[0].code != result.reason_code:
            raise ReadingAnalysisValidationError("result", "$", "failed result combination drift")
        if result.status == "exhausted" and result.reason_code != "BUDGET_EXHAUSTED":
            raise ReadingAnalysisValidationError("result", "$", "exhausted reason drift")
        if result.status == "invalid" and result.reason_code in {"ANALYZED", "BUDGET_EXHAUSTED"}:
            raise ReadingAnalysisValidationError("result", "$", "invalid reason drift")
        return
    if result.reason_code != "ANALYZED" or result.diagnostics:
        raise ReadingAnalysisValidationError("result", "$", "analyzed combination drift")
    if type(result.intake_result_bytes) is not bytes or len(result.intake_result_bytes) > MAX_INPUT_BYTES:
        raise ReadingAnalysisValidationError("result", "$.intake_result", "missing intake result")
    if _sha(result.intake_result_bytes) != result.input_result_sha256:
        raise ReadingAnalysisValidationError("identity", "$.input_result_sha256", "input digest drift")
    for field in ("problem_ir_sha256", "base_reading_id"):
        value = getattr(result, field)
        pattern = _DIGEST if field.endswith("sha256") else _ID
        if type(value) is not str or pattern.fullmatch(value) is None:
            raise ReadingAnalysisValidationError("result", f"$.{field}", "invalid analyzed field")
    if result.ambiguity_status not in {"unambiguous", "unresolved", "resolved"}:
        raise ReadingAnalysisValidationError("result", "$.ambiguity_status", "invalid state")
    if type(result.candidates) is not tuple or not result.candidates:
        raise ReadingAnalysisValidationError("result", "$.candidates", "missing candidates")
    ids = tuple(candidate.reading_id for candidate in result.candidates)
    if ids != tuple(sorted(ids)) or len(set(ids)) != len(ids):
        raise ReadingAnalysisValidationError("result", "$.candidates", "candidate order drift")
    if result.base_reading_id not in ids:
        raise ReadingAnalysisValidationError("result", "$.base_reading_id", "unknown base")
    for candidate in result.candidates:
        if type(candidate) is not ReadingCandidate:
            raise ReadingAnalysisValidationError("result", "$.candidates", "invalid candidate")
        if _sha(candidate.projection_bytes) != candidate.projection_sha256:
            raise ReadingAnalysisValidationError("identity", "$.candidates", "projection digest drift")
        if candidate.reading_id == result.base_reading_id:
            if candidate.difference_from is not None or candidate.deltas:
                raise ReadingAnalysisValidationError("result", "$.candidates", "base drift")
        elif candidate.difference_from != result.base_reading_id or not candidate.deltas:
            raise ReadingAnalysisValidationError("result", "$.candidates", "alternative drift")
    if result.ambiguity_status == "unresolved":
        if result.selected_reading_id is not None or type(result.required_choice) is not ReadingChoice:
            raise ReadingAnalysisValidationError("result", "$", "unresolved combination drift")
        if result.required_choice.candidate_reading_ids != ids:
            raise ReadingAnalysisValidationError("result", "$.required_choice", "choice candidates drift")
    elif result.required_choice is not None or result.selected_reading_id not in ids:
        raise ReadingAnalysisValidationError("result", "$", "resolved selection drift")


def validate_reading_analysis_result(result: object) -> None:
    """Recompute an analyzed in-memory result before it is consumed."""
    _validate_result_shape(result)
    assert type(result) is ReadingAnalysisResult
    if result.status == "analyzed":
        assert result.intake_result_bytes is not None
        expected = analyze_problem_readings(result.intake_result_bytes)
        if expected != result:
            raise ReadingAnalysisValidationError("result", "$", "analysis recomputation drift")


def reading_projection_bytes(candidate: ReadingCandidate) -> bytes:
    """Return exact canonical projection bytes after digest checks."""
    if type(candidate) is not ReadingCandidate:
        raise ReadingAnalysisValidationError("type", "$", "expected exact ReadingCandidate")
    if _sha(candidate.projection_bytes) != candidate.projection_sha256:
        raise ReadingAnalysisValidationError("identity", "$", "projection digest drift")
    value = _json_object(candidate.projection_bytes, "$")
    try:
        if _canonical_bytes(value) != candidate.projection_bytes:
            raise ReadingAnalysisValidationError("canonical", "$", "projection is noncanonical")
    except _AnalysisError as exc:
        raise ReadingAnalysisValidationError(exc.kind, exc.path, exc.detail) from exc
    return candidate.projection_bytes


def reading_analysis_result_bytes(result: ReadingAnalysisResult) -> bytes:
    """Serialize one closed result to canonical, replayable JSON bytes."""
    validate_reading_analysis_result(result)
    try:
        return _result_bytes_unchecked(result)
    except _AnalysisError as exc:
        raise ReadingAnalysisValidationError(exc.kind, exc.path, exc.detail) from exc


def reading_analysis_result_sha256(result: ReadingAnalysisResult) -> str:
    """Return the full SHA-256 identity of canonical analysis result bytes."""
    return _sha(reading_analysis_result_bytes(result))


def parse_reading_analysis_result(data: bytes) -> ReadingAnalysisResult:
    """Parse canonical result bytes and replay every analyzed projection and delta."""
    if type(data) is not bytes:
        raise ReadingAnalysisValidationError("type", "$", "result must be exact bytes")
    if len(data) > MAX_OUTPUT_BYTES:
        raise ReadingAnalysisValidationError("budget", "$", "result byte budget exceeded")
    value = _json_object(data, "$")
    try:
        if _canonical_bytes(value) != data:
            raise ReadingAnalysisValidationError("canonical", "$", "result bytes are noncanonical")
    except _AnalysisError as exc:
        raise ReadingAnalysisValidationError(exc.kind, exc.path, exc.detail) from exc
    fields = {
        "schema", "contract_id", "contract_sha256", "problem_intake_contract_id",
        "problem_intake_contract_sha256", "problem_ir_contract_id",
        "problem_ir_contract_sha256", "problem_ir_schema_sha256", "status",
        "reason_code", "input_result_sha256", "intake_result", "problem_ir_sha256",
        "ambiguity_status", "base_reading_id", "selected_reading_id", "required_choice",
        "candidates", "diagnostics", "mathematical_authority",
    }
    if set(value) != fields:
        raise ReadingAnalysisValidationError("schema", "$", "result field set drift")
    if value["status"] == "analyzed":
        if type(value["intake_result"]) is not dict:
            raise ReadingAnalysisValidationError("schema", "$.intake_result", "missing intake")
        try:
            intake_bytes = _canonical_bytes(value["intake_result"], maximum=MAX_INPUT_BYTES)
        except _AnalysisError as exc:
            raise ReadingAnalysisValidationError(exc.kind, exc.path, exc.detail) from exc
        expected = analyze_problem_readings(intake_bytes)
        if expected.status != "analyzed" or _result_mapping(expected) != value:
            raise ReadingAnalysisValidationError("result", "$", "historical analysis replay drift")
        if _result_bytes_unchecked(expected) != data:
            raise ReadingAnalysisValidationError("canonical", "$", "analysis round-trip drift")
        return expected
    raw_diagnostics = value["diagnostics"]
    if type(raw_diagnostics) is not list:
        raise ReadingAnalysisValidationError("schema", "$.diagnostics", "expected array")
    diagnostics: list[ReadingAnalysisDiagnostic] = []
    for index, raw in enumerate(raw_diagnostics):
        if type(raw) is not dict or set(raw) != {"code", "path", "message"}:
            raise ReadingAnalysisValidationError(
                "schema", f"$.diagnostics[{index}]", "diagnostic field drift"
            )
        diagnostics.append(ReadingAnalysisDiagnostic(**raw))
    result = ReadingAnalysisResult(
        schema=value["schema"],
        contract_id=value["contract_id"],
        contract_sha256=value["contract_sha256"],
        problem_intake_contract_id=value["problem_intake_contract_id"],
        problem_intake_contract_sha256=value["problem_intake_contract_sha256"],
        problem_ir_contract_id=value["problem_ir_contract_id"],
        problem_ir_contract_sha256=value["problem_ir_contract_sha256"],
        problem_ir_schema_sha256=value["problem_ir_schema_sha256"],
        status=value["status"],
        reason_code=value["reason_code"],
        input_result_sha256=value["input_result_sha256"],
        intake_result_bytes=None,
        problem_ir_sha256=value["problem_ir_sha256"],
        ambiguity_status=value["ambiguity_status"],
        base_reading_id=value["base_reading_id"],
        selected_reading_id=value["selected_reading_id"],
        required_choice=None,
        candidates=(),
        diagnostics=tuple(diagnostics),
        mathematical_authority=value["mathematical_authority"],
        _token=_RESULT_TOKEN,
    )
    _validate_result_shape(result)
    if _result_bytes_unchecked(result) != data:
        raise ReadingAnalysisValidationError("canonical", "$", "failed result round-trip drift")
    return result
