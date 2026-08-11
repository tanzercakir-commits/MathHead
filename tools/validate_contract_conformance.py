#!/usr/bin/env python3
"""Validate the active P2 contract closure and emit one deterministic report."""

from __future__ import annotations

import argparse
import copy
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
from typing import Any, Callable, NoReturn, Sequence

try:
    from jsonschema import Draft202012Validator
    from jsonschema.exceptions import SchemaError
except ImportError:  # Reported as a conformance dependency failure by the CLI.
    Draft202012Validator = None  # type: ignore[assignment,misc]
    SchemaError = Exception  # type: ignore[assignment,misc]


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import contract_artifacts as artifacts  # noqa: E402
from tools import validate_engine_result_contract as engine_result  # noqa: E402
from tools import validate_evidence_certificate_contracts as evidence_certificate  # noqa: E402
from tools import validate_problem_ir_contract as problem_ir  # noqa: E402
from tools import validate_resource_budget_contract as resource_budget  # noqa: E402
from tools import validate_theory_context_contract as theory_context  # noqa: E402
from tools import validate_theory_plugin_contract as theory_plugin  # noqa: E402


REPORT_SCHEMA = "mathhead.foundation-conformance.v1"
WORKFLOW_ID = "MH-C-WORKFLOW-001"
WORKFLOW_PATH = Path("docs/contracts/PYTHON_CONTRACT_FIRST_WORKFLOW_V1.md")
WORKFLOW_SHA256 = "99cfdf17371938af65c4203c02cbaac0bf73470e9fab59f7a6d62360fc0b7cca"
MANIFEST_PATH = Path("docs/contracts/manifest.toml")
IMPLEMENTATION_MARKER = re.compile(
    rb'(?m)^(?P<name>[A-Z][A-Z0-9_]*_IMPLEMENTATION_SHA256) = "'
    rb'(?P<digest>[0-9a-f]{64})"$'
)


@dataclass(frozen=True)
class SchemaSpec:
    path: str
    sha256: str


@dataclass(frozen=True)
class ContractSpec:
    contract_id: str
    sha256: str
    target: str
    primary_validator: str
    schema: SchemaSpec | None = None
    supersedes: str | None = None
    explicit_dependencies: tuple[tuple[str, str], ...] = ()
    source_hash_when_implemented: bool = True


CONTRACTS = (
    ContractSpec(
        "MH-C-CONTRACT-ARTIFACTS-002",
        "602845fedb167d06ce3999f6c245d590a43f184b3f271180cae1b8154fe7b750",
        "tools.contract_artifacts:main",
        "python tools/contract_artifacts.py verify --all --check-report "
        "docs/contracts/reports/verification-v1.json",
        supersedes="MH-C-CONTRACT-ARTIFACTS-001",
        source_hash_when_implemented=False,
    ),
    ContractSpec(
        "MH-C-PROBLEM-IR-002",
        "6d657195869a5746c5a41492c334b32ee5edd2ca84eb7facfade44f53334c286",
        "mathhead.ir:ProblemIR",
        "python tools/validate_problem_ir_contract.py",
        SchemaSpec(
            "docs/contracts/schemas/problem-ir-v1.schema.json",
            "dcf871f15ebbae06b0eca285a115f2545defc00cb0befc23e3cc574d8523df2c",
        ),
        supersedes="MH-C-PROBLEM-IR-001",
    ),
    ContractSpec(
        "MH-C-THEORY-CONTEXT-001",
        "d2cb0e61c33327a6c2d5887872278179b5e11e42b6358b1661b60386e60e888d",
        "mathhead.context:TheoryContext",
        "python tools/validate_theory_context_contract.py",
        SchemaSpec(
            "docs/contracts/schemas/theory-context-v1.schema.json",
            "6a6e40070ba0a3209f5bfcfa0cc912d1ec08359a178611a40d61ffadda5819ec",
        ),
    ),
    ContractSpec(
        "MH-C-RESOURCE-BUDGET-001",
        "eef46d8e6d37ada50fb9af1ab6a1db5665070896f83c5d9155fc6ee2777f5045",
        "mathhead.budget:ResourceBudget",
        "python tools/validate_resource_budget_contract.py",
        SchemaSpec(
            "docs/contracts/schemas/resource-budget-v1.schema.json",
            "e735dee47394bf50c10ac571dfc8923fd1da851e258b1d9f42e1a66bb9d85e78",
        ),
    ),
    ContractSpec(
        "MH-C-ENGINE-RESULT-001",
        "6c57ba36c78a2e15b27d3e464342b890f71b2d298f6395c7f4b0cd5aa5a09370",
        "mathhead.results:EngineResult",
        "python tools/validate_engine_result_contract.py",
        SchemaSpec(
            "docs/contracts/schemas/engine-result-v1.schema.json",
            "4cd26ad69c6528a7553a429d06f224c79ae6b01b7d9cc0fa41ccb7c4d20cc948",
        ),
    ),
    ContractSpec(
        "MH-C-EVIDENCE-001",
        "c68c20ca599cfdd7aabe9b85f2817c6c3f1a121289334136ff048768ee20c3b3",
        "mathhead.evidence:Evidence",
        "python tools/validate_evidence_certificate_contracts.py",
        SchemaSpec(
            "docs/contracts/schemas/evidence-v1.schema.json",
            "4f1d0a4438812bdd7b204d0d0fe0098ff06cc274eb2e4ed7fa66a3f3a76b426f",
        ),
    ),
    ContractSpec(
        "MH-C-CERTIFICATE-001",
        "0a21aca8058fb5fc9900decb6dcd14e179c7a5171f7653ea965b5d34edd59740",
        "mathhead.certificates:Certificate",
        "python tools/validate_evidence_certificate_contracts.py",
        SchemaSpec(
            "docs/contracts/schemas/certificate-v1.schema.json",
            "cbc8f68469593e1d2b34588b49eaa16e37d597c863457945dd5b9ce5ae138760",
        ),
        explicit_dependencies=(
            (
                "MH-C-EVIDENCE-001",
                "c68c20ca599cfdd7aabe9b85f2817c6c3f1a121289334136ff048768ee20c3b3",
            ),
        ),
    ),
    ContractSpec(
        "MH-C-THEORY-PLUGIN-001",
        "2226973b172a3b2ce489aae3baae7820c3b7b57ab76cff089927f68a2759a8e8",
        "mathhead.plugins:TheoryPlugin",
        "python tools/validate_theory_plugin_contract.py",
        SchemaSpec(
            "docs/contracts/schemas/theory-plugin-v1.schema.json",
            "c3d234f725e2c3f0e6fa02507be83190bde71f8ddae6f5a08cd6395065d77142",
        ),
        explicit_dependencies=(
            (
                "MH-C-CERTIFICATE-001",
                "0a21aca8058fb5fc9900decb6dcd14e179c7a5171f7653ea965b5d34edd59740",
            ),
            (
                "MH-C-ENGINE-RESULT-001",
                "6c57ba36c78a2e15b27d3e464342b890f71b2d298f6395c7f4b0cd5aa5a09370",
            ),
            (
                "MH-C-EVIDENCE-001",
                "c68c20ca599cfdd7aabe9b85f2817c6c3f1a121289334136ff048768ee20c3b3",
            ),
            (
                "MH-C-PROBLEM-IR-002",
                "6d657195869a5746c5a41492c334b32ee5edd2ca84eb7facfade44f53334c286",
            ),
            (
                "MH-C-RESOURCE-BUDGET-001",
                "eef46d8e6d37ada50fb9af1ab6a1db5665070896f83c5d9155fc6ee2777f5045",
            ),
            (
                "MH-C-THEORY-CONTEXT-001",
                "d2cb0e61c33327a6c2d5887872278179b5e11e42b6358b1661b60386e60e888d",
            ),
        ),
    ),
)
CONTRACT_BY_ID = {spec.contract_id: spec for spec in CONTRACTS}


class ConformanceError(RuntimeError):
    """A classified closure, schema, validator, or binding failure."""

    def __init__(self, kind: str, path: str, detail: str) -> None:
        super().__init__(f"{path}: {detail}")
        self.kind = kind
        self.path = path
        self.detail = detail


def _fail(kind: str, path: str, detail: str) -> NoReturn:
    raise ConformanceError(kind, path, detail)


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical_bytes(value: Any) -> bytes:
    try:
        rendered = json.dumps(
            value,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        _fail("canonical", "$", f"value is not canonical JSON: {exc}")
    return (rendered + "\n").encode("utf-8")


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _fail("duplicate-key", "$", f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path, *, canonical: bool = False) -> tuple[dict[str, Any], bytes]:
    try:
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs)
    except ConformanceError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        _fail("json", str(path), f"invalid JSON: {exc}")
    if not isinstance(value, dict):
        _fail("json", str(path), "JSON root must be an object")
    if canonical and raw != canonical_bytes(value):
        _fail("canonical", str(path), "JSON bytes are not canonical")
    return value, raw


def _translate(path: str, action: Callable[[], Any]) -> Any:
    try:
        return action()
    except artifacts.ContractArtifactError as exc:
        _fail(exc.kind, path, str(exc))


def _validator_references(root: Path, command: str) -> list[str]:
    try:
        return artifacts._validator_references(root, command)  # noqa: SLF001
    except artifacts.ContractArtifactError as exc:
        _fail("validator", command, str(exc))


def validate_contract_payload(data: dict[str, Any], spec: ContractSpec, root: Path) -> None:
    _translate(
        spec.contract_id, lambda: artifacts.validate_contract(data, expected_id=spec.contract_id)
    )
    _translate(spec.contract_id, lambda: artifacts._assert_decidable_consistency(data))  # noqa: SLF001
    if data["target"] != spec.target:
        _fail("target", spec.contract_id, "accepted target drift")
    if data["supersedes"] != spec.supersedes:
        _fail("supersession", spec.contract_id, "supersession identity drift")
    if spec.primary_validator not in data["validators"]:
        _fail("validator", spec.contract_id, "primary validator is missing")
    for command in data["validators"]:
        _validator_references(root, command)
    rendered = canonical_bytes(data).decode("ascii")
    for dependency_id, dependency_sha256 in spec.explicit_dependencies:
        if f"{dependency_id}={dependency_sha256}" not in rendered:
            _fail("dependency", spec.contract_id, f"dependency binding missing: {dependency_id}")
    if spec.schema is not None:
        binding = f"{spec.schema.path}={spec.schema.sha256}"
        if binding not in rendered:
            _fail("schema", spec.contract_id, "normative schema identity is not bound")


def _validate_report_identity(value: dict[str, Any], path: str) -> None:
    _translate(path, lambda: artifacts._validate_report(value))  # noqa: SLF001


def _validate_acceptance_reports(root: Path, spec: ContractSpec) -> None:
    base = root / "docs/contracts/reports"
    prescreen_path = base / f"{spec.contract_id}.prescreen.json"
    acceptance_path = base / f"{spec.contract_id}.acceptance.json"
    prescreen, prescreen_raw = load_json(prescreen_path, canonical=True)
    acceptance, acceptance_raw = load_json(acceptance_path, canonical=True)
    _validate_report_identity(prescreen, str(prescreen_path))
    _validate_report_identity(acceptance, str(acceptance_path))
    prescreen_contract = prescreen.get("contract")
    acceptance_contract = acceptance.get("contract")
    if (
        prescreen.get("operation") != "prescreen"
        or prescreen.get("status") != "passed"
        or prescreen.get("acceptance") != "not_granted"
        or not isinstance(prescreen_contract, dict)
        or prescreen_contract.get("id") != spec.contract_id
        or prescreen_contract.get("sha256") != spec.sha256
    ):
        _fail("prescreen", spec.contract_id, "pre-screen report binding drift")
    if (
        acceptance.get("operation") != "accept"
        or acceptance.get("status") != "accepted"
        or acceptance_contract != {"id": spec.contract_id, "sha256": spec.sha256}
        or acceptance.get("proposal") != f"docs/contracts/proposed/{spec.contract_id}.json"
        or acceptance.get("accepted_artifact") != f"docs/contracts/{spec.contract_id}.json"
    ):
        _fail("acceptance", spec.contract_id, "acceptance report binding drift")
    report_ref = acceptance.get("prescreen_report")
    if not isinstance(report_ref, dict) or (
        report_ref.get("path") != f"docs/contracts/reports/{spec.contract_id}.prescreen.json"
        or report_ref.get("sha256") != _sha(prescreen_raw)
        or report_ref.get("report_sha256") != prescreen.get("report_sha256")
    ):
        _fail("acceptance", spec.contract_id, "accepted pre-screen reference drift")
    if _sha(acceptance_raw) == _sha(prescreen_raw):
        _fail("acceptance", spec.contract_id, "acceptance and pre-screen reports alias")


def _schema_child(value: Any, path: str) -> None:
    if isinstance(value, bool):
        return
    if not isinstance(value, dict):
        _fail("schema-meta", path, "schema node must be an object or boolean")
    _validate_schema_keywords(value, path)


def _schema_map(value: Any, path: str) -> None:
    if not isinstance(value, dict):
        _fail("schema-meta", path, "keyword must be an object")
    for key, child in value.items():
        if not isinstance(key, str):
            _fail("schema-meta", path, "schema map key must be a string")
        _schema_child(child, f"{path}.{key}")


def _schema_array(value: Any, path: str) -> None:
    if not isinstance(value, list) or not value:
        _fail("schema-meta", path, "keyword must be a nonempty schema array")
    for index, child in enumerate(value):
        _schema_child(child, f"{path}[{index}]")


def _nonnegative_integer(value: Any, path: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        _fail("schema-meta", path, "keyword must be a nonnegative integer")
    return value


def _validate_schema_keywords(schema: dict[str, Any], path: str) -> None:
    allowed_types = {"array", "boolean", "integer", "null", "number", "object", "string"}
    type_value = schema.get("type")
    if type_value is not None:
        types = [type_value] if isinstance(type_value, str) else type_value
        if (
            not isinstance(types, list)
            or not types
            or any(not isinstance(item, str) or item not in allowed_types for item in types)
            or len(types) != len(set(types))
        ):
            _fail("schema-meta", f"{path}.type", "invalid JSON Schema type declaration")
    for keyword in ("$defs", "properties", "patternProperties", "dependentSchemas"):
        if keyword in schema:
            _schema_map(schema[keyword], f"{path}.{keyword}")
    for keyword in (
        "additionalProperties",
        "contains",
        "contentSchema",
        "else",
        "if",
        "items",
        "not",
        "propertyNames",
        "then",
        "unevaluatedItems",
        "unevaluatedProperties",
    ):
        if keyword in schema:
            _schema_child(schema[keyword], f"{path}.{keyword}")
    for keyword in ("allOf", "anyOf", "oneOf", "prefixItems"):
        if keyword in schema:
            _schema_array(schema[keyword], f"{path}.{keyword}")
    if "required" in schema:
        required = schema["required"]
        if (
            not isinstance(required, list)
            or any(not isinstance(item, str) for item in required)
            or len(required) != len(set(required))
        ):
            _fail("schema-meta", f"{path}.required", "required must be unique strings")
    if "dependentRequired" in schema:
        dependent = schema["dependentRequired"]
        if not isinstance(dependent, dict):
            _fail("schema-meta", f"{path}.dependentRequired", "keyword must be an object")
        for key, names in dependent.items():
            if (
                not isinstance(key, str)
                or not isinstance(names, list)
                or any(not isinstance(item, str) for item in names)
                or len(names) != len(set(names))
            ):
                _fail("schema-meta", f"{path}.dependentRequired", "invalid dependency names")
    if "enum" in schema:
        enum = schema["enum"]
        if not isinstance(enum, list) or not enum:
            _fail("schema-meta", f"{path}.enum", "enum must be a nonempty array")
        encoded = [canonical_bytes(item) for item in enum]
        if len(encoded) != len(set(encoded)):
            _fail("schema-meta", f"{path}.enum", "enum values must be unique")
    for keyword in (
        "maxContains",
        "maxItems",
        "maxLength",
        "maxProperties",
        "minContains",
        "minItems",
        "minLength",
        "minProperties",
    ):
        if keyword in schema:
            _nonnegative_integer(schema[keyword], f"{path}.{keyword}")
    for minimum, maximum in (
        ("minContains", "maxContains"),
        ("minItems", "maxItems"),
        ("minLength", "maxLength"),
        ("minProperties", "maxProperties"),
    ):
        if minimum in schema and maximum in schema and schema[minimum] > schema[maximum]:
            _fail("schema-meta", path, f"{minimum} exceeds {maximum}")
    if "multipleOf" in schema and (
        isinstance(schema["multipleOf"], bool)
        or not isinstance(schema["multipleOf"], (int, float))
        or schema["multipleOf"] <= 0
    ):
        _fail("schema-meta", f"{path}.multipleOf", "multipleOf must be positive")
    for keyword in ("maximum", "minimum", "exclusiveMaximum", "exclusiveMinimum"):
        if keyword in schema and (
            isinstance(schema[keyword], bool) or not isinstance(schema[keyword], (int, float))
        ):
            _fail("schema-meta", f"{path}.{keyword}", "numeric bound must be a number")
    for keyword in ("pattern",):
        if keyword in schema:
            if not isinstance(schema[keyword], str):
                _fail("schema-meta", f"{path}.{keyword}", "pattern must be a string")
            try:
                re.compile(schema[keyword])
            except re.error as exc:
                _fail("schema-meta", f"{path}.{keyword}", f"invalid regular expression: {exc}")
    for keyword in ("$anchor", "$comment", "$id", "$ref", "$schema", "description", "title"):
        if keyword in schema and not isinstance(schema[keyword], str):
            _fail("schema-meta", f"{path}.{keyword}", "keyword must be a string")


def _validate_schema_document(root: Path, spec: ContractSpec) -> dict[str, Any]:
    assert spec.schema is not None
    path = root / spec.schema.path
    schema, raw = load_json(path)
    if _sha(raw) != spec.schema.sha256:
        _fail("schema-hash", spec.schema.path, "normative schema hash drift")
    if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        _fail("schema-meta", spec.schema.path, "schema dialect is not Draft 2020-12")
    if schema.get("type") != "object" or schema.get("additionalProperties") is not False:
        _fail("schema-closure", spec.schema.path, "root object is not closed")
    _validate_schema_keywords(schema, "$")
    if Draft202012Validator is not None:
        try:
            Draft202012Validator.check_schema(schema)
        except SchemaError as exc:
            _fail("schema-meta", spec.schema.path, str(exc))
    return schema


def _expect_validation_failure(label: str, action: Callable[[], Any]) -> None:
    try:
        action()
    except (
        problem_ir.ProblemIRValidationError,
        theory_context.TheoryContextValidationError,
        resource_budget.ResourceBudgetValidationError,
        engine_result.EngineResultValidationError,
        evidence_certificate.EvidenceCertificateValidationError,
        theory_plugin.TheoryPluginValidationError,
    ):
        return
    _fail("negative-probe", label, "mutation was accepted")


def _validate_schema_instance(root: Path, spec: ContractSpec, schema: dict[str, Any]) -> None:
    if spec.contract_id == "MH-C-CERTIFICATE-001":
        evidence = evidence_certificate.minimal_evidence()
        evidence_schema, _ = load_json(
            root / CONTRACT_BY_ID["MH-C-EVIDENCE-001"].schema.path  # type: ignore[union-attr]
        )
        evidence_certificate.validate_evidence(evidence, evidence_schema)
        value = evidence_certificate.minimal_certificate(evidence)

        def validate(item: dict[str, Any]) -> None:
            evidence_certificate.validate_certificate(
                item,
                schema,
                evidence=evidence,
                evidence_schema=evidence_schema,
            )

    else:
        adapters: dict[
            str,
            tuple[
                Callable[[], dict[str, Any]],
                Callable[[dict[str, Any], dict[str, Any]], None],
            ],
        ] = {
            "MH-C-PROBLEM-IR-002": (
                problem_ir.minimal_problem_ir,
                problem_ir.validate_problem_ir,
            ),
            "MH-C-THEORY-CONTEXT-001": (
                theory_context.minimal_theory_context,
                theory_context.validate_theory_context,
            ),
            "MH-C-RESOURCE-BUDGET-001": (
                resource_budget.minimal_resource_budget,
                resource_budget.validate_resource_budget,
            ),
            "MH-C-ENGINE-RESULT-001": (
                engine_result.minimal_engine_result,
                engine_result.validate_engine_result,
            ),
            "MH-C-EVIDENCE-001": (
                evidence_certificate.minimal_evidence,
                evidence_certificate.validate_evidence,
            ),
            "MH-C-THEORY-PLUGIN-001": (
                theory_plugin.minimal_theory_plugin,
                theory_plugin.validate_theory_plugin,
            ),
        }
        try:
            builder, instance_validator = adapters[spec.contract_id]
        except KeyError:
            _fail("schema-instance", spec.contract_id, "no representative instance adapter")
        value = builder()

        def validate(item: dict[str, Any]) -> None:
            instance_validator(item, schema)

    validate(copy.deepcopy(value))
    unknown = copy.deepcopy(value)
    unknown["unexpected"] = None
    _expect_validation_failure(f"{spec.contract_id}:unknown-field", lambda: validate(unknown))
    missing = copy.deepcopy(value)
    del missing["schema"]
    _expect_validation_failure(f"{spec.contract_id}:missing-field", lambda: validate(missing))


def implementation_basis_sha256(raw: bytes) -> tuple[str, str]:
    matches = list(IMPLEMENTATION_MARKER.finditer(raw))
    if len(matches) != 1:
        _fail("implementation-hash", "source", "exactly one implementation hash marker required")
    match = matches[0]
    declared = match.group("digest").decode("ascii")
    start, end = match.span("digest")
    basis = raw[:start] + (b"0" * 64) + raw[end:]
    return declared, _sha(basis)


def verify_implementation_binding(
    root: Path,
    data: dict[str, Any],
    contract_sha256: str,
    *,
    required: bool,
    require_source_hash: bool,
) -> dict[str, Any]:
    binding = _translate(
        data["contract_id"],
        lambda: artifacts._binding(root, data, contract_sha256, required=required),  # noqa: SLF001
    )
    if binding["status"] != "passed" or not require_source_hash:
        return binding
    source_path = root / binding["source"]
    try:
        declared, actual = implementation_basis_sha256(source_path.read_bytes())
    except OSError as exc:
        _fail("implementation-hash", str(source_path), str(exc))
    if declared != actual:
        _fail("implementation-hash", binding["source"], "implementation source basis drift")
    return {**binding, "implementation_basis_sha256": actual}


def _synthetic_contract() -> dict[str, Any]:
    value = copy.deepcopy(load_json(ROOT / "docs/contracts/MH-C-PROBLEM-IR-002.json")[0])
    value.update(
        {
            "contract_id": "MH-C-SYNTHETIC-001",
            "target": "mathhead.synthetic:Surface",
            "signature": "Surface(*, value: str) -> None",
            "supersedes": None,
        }
    )
    return value


def _synthetic_source(contract_sha256: str) -> bytes:
    template = (
        'SYNTHETIC_CONTRACT_ID = "MH-C-SYNTHETIC-001"\n'
        f'SYNTHETIC_CONTRACT_SHA256 = "{contract_sha256}"\n'
        'SYNTHETIC_IMPLEMENTATION_SHA256 = "{implementation_sha256}"\n\n'
        "class Surface:\n"
        "    def __init__(self, *, value: str) -> None:\n"
        "        self.value = value\n"
    )
    basis = template.format(implementation_sha256="0" * 64).encode("utf-8")
    return template.format(implementation_sha256=_sha(basis)).encode("utf-8")


def _expect_conformance_failure(kind: str, label: str, action: Callable[[], Any]) -> None:
    try:
        action()
    except ConformanceError as exc:
        if exc.kind != kind:
            _fail("negative-probe", label, f"expected {kind}, observed {exc.kind}")
        return
    _fail("negative-probe", label, "mutation was accepted")


def _run_negative_probes(root: Path) -> list[dict[str, Any]]:
    sample_spec = CONTRACT_BY_ID["MH-C-PROBLEM-IR-002"]
    sample, _ = load_json(root / f"docs/contracts/{sample_spec.contract_id}.json")

    unknown = copy.deepcopy(sample)
    unknown["unexpected"] = True
    _expect_conformance_failure(
        "schema",
        "contract-unknown-field",
        lambda: _translate("unknown", lambda: artifacts.validate_contract(unknown)),
    )
    missing = copy.deepcopy(sample)
    del missing["ensures"]
    _expect_conformance_failure(
        "schema",
        "contract-missing-field",
        lambda: _translate("missing", lambda: artifacts.validate_contract(missing)),
    )
    contradiction = copy.deepcopy(sample)
    contradiction["requires"].extend(["synthetic condition", "NOT: synthetic condition"])
    _expect_conformance_failure(
        "unsatisfiable",
        "contract-contradiction",
        lambda: _translate(
            "contradiction",
            lambda: artifacts._assert_decidable_consistency(contradiction),  # noqa: SLF001
        ),
    )
    missing_validator = copy.deepcopy(sample)
    missing_validator["validators"].remove(sample_spec.primary_validator)
    _expect_conformance_failure(
        "validator",
        "primary-validator-missing",
        lambda: validate_contract_payload(missing_validator, sample_spec, root),
    )
    shell_validator = copy.deepcopy(sample)
    shell_validator["validators"][0] = "python tools/validate_problem_ir_contract.py && python -V"
    _expect_conformance_failure(
        "validator",
        "validator-shell-syntax",
        lambda: validate_contract_payload(shell_validator, sample_spec, root),
    )

    try:
        json.loads('{"schema":1,"schema":2}', object_pairs_hook=_pairs)
    except ConformanceError as exc:
        if exc.kind != "duplicate-key":
            raise
    else:
        _fail("negative-probe", "duplicate-json-key", "duplicate key was accepted")

    synthetic = _synthetic_contract()
    synthetic_sha256 = _sha(canonical_bytes(synthetic))
    with tempfile.TemporaryDirectory(prefix="mathhead-conformance-") as directory:
        synthetic_root = Path(directory)
        source_path = synthetic_root / "src/mathhead/synthetic.py"
        source_path.parent.mkdir(parents=True)
        source = _synthetic_source(synthetic_sha256)
        source_path.write_bytes(source)
        binding = verify_implementation_binding(
            synthetic_root,
            synthetic,
            synthetic_sha256,
            required=True,
            require_source_hash=True,
        )
        if binding["status"] != "passed":
            _fail("negative-probe", "synthetic-binding", "exact binding did not pass")

        signature_drift = source.replace(
            b"def __init__(self, *, value: str) -> None:",
            b"def __init__(self, *, value: bytes) -> None:",
        )
        source_path.write_bytes(signature_drift)
        _expect_conformance_failure(
            "binding",
            "implementation-signature-drift",
            lambda: verify_implementation_binding(
                synthetic_root,
                synthetic,
                synthetic_sha256,
                required=True,
                require_source_hash=True,
            ),
        )

        contract_hash_drift = source.replace(synthetic_sha256.encode(), b"f" * 64)
        source_path.write_bytes(contract_hash_drift)
        _expect_conformance_failure(
            "binding",
            "implementation-contract-hash-drift",
            lambda: verify_implementation_binding(
                synthetic_root,
                synthetic,
                synthetic_sha256,
                required=True,
                require_source_hash=True,
            ),
        )

        source_drift = source.replace(b"self.value = value\n", b"self.value = value.strip()\n")
        source_path.write_bytes(source_drift)
        _expect_conformance_failure(
            "implementation-hash",
            "implementation-source-drift",
            lambda: verify_implementation_binding(
                synthetic_root,
                synthetic,
                synthetic_sha256,
                required=True,
                require_source_hash=True,
            ),
        )

    return [
        {"id": probe, "status": "passed"}
        for probe in (
            "contract-unknown-field",
            "contract-missing-field",
            "contract-contradiction",
            "primary-validator-missing",
            "validator-shell-syntax",
            "duplicate-json-key",
            "synthetic-binding",
            "implementation-signature-drift",
            "implementation-contract-hash-drift",
            "implementation-source-drift",
        )
    ]


def _run_primary_validators(root: Path, commands: Sequence[str]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for command in dict.fromkeys(commands):
        _validator_references(root, command)
        argv = shlex.split(command, posix=True)
        argv[0] = sys.executable
        try:
            completed = subprocess.run(
                argv,
                cwd=root,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=120,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            _fail("validator", command, str(exc))
        if completed.returncode != 0:
            detail = completed.stderr.decode("utf-8", errors="replace")[-1000:]
            _fail("validator", command, f"exit {completed.returncode}: {detail}")
        results.append({"command": command, "status": "passed", "exit_code": 0})
    return results


def build_report(root: Path = ROOT, *, run_validators: bool = True) -> dict[str, Any]:
    root = root.resolve()
    try:
        workflow_raw = (root / WORKFLOW_PATH).read_bytes()
    except OSError as exc:
        _fail("workflow", str(WORKFLOW_PATH), str(exc))
    if _sha(workflow_raw) != WORKFLOW_SHA256:
        _fail("workflow", str(WORKFLOW_PATH), "accepted workflow hash drift")
    if (
        artifacts.WORKFLOW_ID != WORKFLOW_ID
        or artifacts.WORKFLOW_SHA256 != WORKFLOW_SHA256
        or artifacts.CONTRACT_ARTIFACTS_CONTRACT_ID != CONTRACTS[0].contract_id
        or artifacts.CONTRACT_ARTIFACTS_CONTRACT_SHA256 != CONTRACTS[0].sha256
    ):
        _fail("workflow", "tools/contract_artifacts.py", "workflow/tool identity drift")

    records, _manifest_raw = _translate(
        str(MANIFEST_PATH),
        lambda: artifacts._manifest(root),  # noqa: SLF001
    )
    by_id = {record["id"]: record for record in records}
    try:
        p2_cutoff = next(
            index
            for index, record in enumerate(records)
            if record["id"] == CONTRACTS[-1].contract_id
        )
    except StopIteration:
        _fail("manifest", CONTRACTS[-1].contract_id, "P2 manifest cutoff is missing")
    # The conformance report is immutable P2 evidence. Later phase contracts are
    # append-only manifest records and must not rewrite MH-027 or the MH-028 bundle
    # that binds it. Any insertion, removal, or drift inside the P2 prefix still
    # changes this projection and fails byte-exact report comparison.
    manifest_raw = artifacts._render_manifest(records[: p2_cutoff + 1])  # noqa: SLF001
    entries: list[dict[str, Any]] = []
    schema_probes: list[dict[str, Any]] = []
    for spec in CONTRACTS:
        record = by_id.get(spec.contract_id)
        expected_record = {
            "id": spec.contract_id,
            "path": f"docs/contracts/{spec.contract_id}.json",
            "sha256": spec.sha256,
            "state": "accepted",
        }
        if record != expected_record:
            _fail("manifest", spec.contract_id, "active P2 manifest binding drift")
        accepted_path = root / expected_record["path"]
        proposed_path = root / f"docs/contracts/proposed/{spec.contract_id}.json"
        accepted, accepted_raw = load_json(accepted_path, canonical=True)
        proposed, proposed_raw = load_json(proposed_path, canonical=True)
        if accepted_raw != proposed_raw or _sha(accepted_raw) != spec.sha256:
            _fail("proposal", spec.contract_id, "accepted/proposed/hash identity drift")
        if proposed != accepted:
            _fail("proposal", spec.contract_id, "accepted/proposed semantic drift")
        validate_contract_payload(accepted, spec, root)
        _validate_acceptance_reports(root, spec)

        schema_entry: dict[str, Any] | None = None
        if spec.schema is not None:
            schema = _validate_schema_document(root, spec)
            _validate_schema_instance(root, spec, schema)
            schema_entry = {"path": spec.schema.path, "sha256": spec.schema.sha256}
            schema_probes.append(
                {
                    "contract_id": spec.contract_id,
                    "positive_instance": "passed",
                    "unknown_field_rejection": "passed",
                    "missing_field_rejection": "passed",
                }
            )

        binding = verify_implementation_binding(
            root,
            accepted,
            spec.sha256,
            required=False,
            require_source_hash=spec.source_hash_when_implemented,
        )
        entry = {
            "contract_id": spec.contract_id,
            "sha256": spec.sha256,
            "target": spec.target,
            "supersedes": spec.supersedes,
            "schema": schema_entry,
            "primary_validator": spec.primary_validator,
            "binding": binding,
            "explicit_dependencies": [
                {"contract_id": dependency_id, "sha256": dependency_sha256}
                for dependency_id, dependency_sha256 in spec.explicit_dependencies
            ],
        }
        entries.append(entry)

    validator_results = (
        _run_primary_validators(root, [spec.primary_validator for spec in CONTRACTS])
        if run_validators
        else [
            {"command": command, "status": "not_run"}
            for command in dict.fromkeys(spec.primary_validator for spec in CONTRACTS)
        ]
    )
    negative_probes = _run_negative_probes(root)
    body = {
        "schema": REPORT_SCHEMA,
        "status": "passed",
        "workflow": {
            "contract_id": WORKFLOW_ID,
            "path": WORKFLOW_PATH.as_posix(),
            "sha256": WORKFLOW_SHA256,
        },
        "manifest": {"path": MANIFEST_PATH.as_posix(), "sha256": _sha(manifest_raw)},
        "contract_count": len(entries),
        "contracts": entries,
        "schema_probes": schema_probes,
        "negative_probes": negative_probes,
        "validators": validator_results,
        "authority": "conformance only; no mathematical truth or verification authority",
    }
    return {**body, "report_sha256": _sha(canonical_bytes(body))}


def validate_report(value: dict[str, Any]) -> None:
    digest = value.get("report_sha256")
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        _fail("report", "$.report_sha256", "report identity missing")
    body = {key: item for key, item in value.items() if key != "report_sha256"}
    if _sha(canonical_bytes(body)) != digest:
        _fail("report", "$.report_sha256", "report identity drift")
    if value.get("schema") != REPORT_SCHEMA or value.get("status") != "passed":
        _fail("report", "$", "report status or schema drift")


def _write_report(path: Path, value: dict[str, Any]) -> None:
    payload = canonical_bytes(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    _translate(str(path), lambda: artifacts._atomic_write(path, payload))  # noqa: SLF001


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    output = parser.add_mutually_exclusive_group()
    output.add_argument("--report", type=Path)
    output.add_argument("--check-report", type=Path)
    parser.add_argument("--skip-validator-execution", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = build_report(args.root, run_validators=not args.skip_validator_execution)
        validate_report(report)
        payload = canonical_bytes(report)
        if args.report is not None:
            path = args.report if args.report.is_absolute() else args.root / args.report
            _write_report(path, report)
            print(f"contract-conformance: report updated: {path}")
        elif args.check_report is not None:
            path = (
                args.check_report
                if args.check_report.is_absolute()
                else args.root / args.check_report
            )
            if path.read_bytes() != payload:
                _fail("report", str(path), "deterministic report drift")
            print(f"contract-conformance: report current: {path}")
    except (ConformanceError, OSError) as exc:
        kind = exc.kind if isinstance(exc, ConformanceError) else "filesystem"
        print(f"contract-conformance: FAIL [{kind}] {exc}", file=sys.stderr)
        return 1
    print(
        "contract-conformance: PASS "
        f"(contracts={report['contract_count']}, schemas={len(report['schema_probes'])}, "
        f"negative={len(report['negative_probes'])}, validators={len(report['validators'])})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
