#!/usr/bin/env python3
"""Generate and fail-closed validate the MH-028 foundation fixture bundle."""

from __future__ import annotations

import argparse
import copy
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any, NoReturn


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = Path("docs/fixtures/foundation-v1")
MANIFEST_PATH = FIXTURE_DIR / "manifest.json"
SCHEMA_PATH = FIXTURE_DIR / "manifest.schema.json"
CONFORMANCE_REPORT_PATH = Path("docs/contracts/reports/foundation-conformance-v1.json")
OBJECT_DIR = FIXTURE_DIR / "objects"
ZERO_SHA256 = "0" * 64
SHA256_RE = re.compile(r"[0-9a-f]{64}")

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import validate_engine_result_contract as engine_result  # noqa: E402
from tools import validate_evidence_certificate_contracts as evidence_certificate  # noqa: E402
from tools import validate_problem_ir_contract as problem_ir  # noqa: E402
from tools import validate_resource_budget_contract as resource_budget  # noqa: E402
from tools import validate_theory_context_contract as theory_context  # noqa: E402
from tools import validate_theory_plugin_contract as theory_plugin  # noqa: E402


BUNDLE_ID = "mathhead.foundation-reference-fixtures.v1"
MANIFEST_SCHEMA_ID = "mathhead.foundation-reference-fixture-manifest.v1"
SCENARIO_ORDER = (
    "proof",
    "refutation",
    "ambiguity",
    "unsupported",
    "timeout",
    "backend-disagreement",
    "invalid-certificate",
    "replay-mismatch",
)
ROLE_ORDER = (
    "problem_ir",
    "theory_context",
    "resource_budget",
    "theory_plugin",
    "evidence",
    "certificate",
    "engine_result",
)
ROLE_CONTRACTS = {
    "problem_ir": (
        problem_ir.CONTRACT_ID,
        problem_ir.EXPECTED_CONTRACT_SHA256,
        "mathhead.problem-ir.v1",
    ),
    "theory_context": (
        theory_context.CONTRACT_ID,
        theory_context.EXPECTED_CONTRACT_SHA256,
        "mathhead.theory-context.v1",
    ),
    "resource_budget": (
        resource_budget.CONTRACT_ID,
        resource_budget.EXPECTED_CONTRACT_SHA256,
        "mathhead.resource-budget.v1",
    ),
    "theory_plugin": (
        theory_plugin.CONTRACT_ID,
        theory_plugin.EXPECTED_CONTRACT_SHA256,
        "mathhead.theory-plugin.v1",
    ),
    "evidence": (
        evidence_certificate.EVIDENCE_CONTRACT_ID,
        evidence_certificate.EVIDENCE_CONTRACT_SHA256,
        "mathhead.evidence.v1",
    ),
    "certificate": (
        evidence_certificate.CERTIFICATE_CONTRACT_ID,
        evidence_certificate.CERTIFICATE_CONTRACT_SHA256,
        "mathhead.certificate.v1",
    ),
    "engine_result": (
        engine_result.CONTRACT_ID,
        engine_result.EXPECTED_CONTRACT_SHA256,
        "mathhead.engine-result.v1",
    ),
}
GOVERNANCE_CONTRACTS = (
    {
        "contract_id": "MH-C-WORKFLOW-001",
        "sha256": "99cfdf17371938af65c4203c02cbaac0bf73470e9fab59f7a6d62360fc0b7cca",
        "path": "docs/contracts/PYTHON_CONTRACT_FIRST_WORKFLOW_V1.md",
        "artifact_kind": "workflow",
        "governed_schema": None,
    },
    {
        "contract_id": "MH-C-CONTRACT-ARTIFACTS-002",
        "sha256": "602845fedb167d06ce3999f6c245d590a43f184b3f271180cae1b8154fe7b750",
        "path": "docs/contracts/MH-C-CONTRACT-ARTIFACTS-002.json",
        "artifact_kind": "function_contract",
        "governed_schema": "mathhead.function-contract.v1",
    },
)
CONTRACT_CLOSURE = tuple(
    sorted(
        [
            *GOVERNANCE_CONTRACTS,
            *(
                {
                    "contract_id": identifier,
                    "sha256": sha256,
                    "path": f"docs/contracts/{identifier}.json",
                    "artifact_kind": "function_contract",
                    "governed_schema": schema,
                }
                for identifier, sha256, schema in ROLE_CONTRACTS.values()
            ),
        ],
        key=lambda item: item["contract_id"],
    )
)


class ReferenceFixtureError(RuntimeError):
    """A classified fixture shape, identity, semantic, or replay failure."""

    def __init__(self, kind: str, path: str, detail: str) -> None:
        super().__init__(f"{path}: {detail}")
        self.kind = kind
        self.path = path
        self.detail = detail


def _fail(kind: str, path: str, detail: str) -> NoReturn:
    raise ReferenceFixtureError(kind, path, detail)


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


def canonical_sha256(value: Any) -> str:
    return _sha(canonical_bytes(value))


def _pairs(path: Path):
    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                _fail("duplicate-key", str(path), f"duplicate JSON key {key!r}")
            result[key] = value
        return result

    return reject_duplicates


def load_json(path: Path, *, canonical: bool = False) -> tuple[dict[str, Any], bytes]:
    try:
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs(path))
    except ReferenceFixtureError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        _fail("json", str(path), f"invalid UTF-8 JSON: {exc}")
    if not isinstance(value, dict):
        _fail("shape", str(path), "JSON root must be an object")
    if canonical and raw != canonical_bytes(value):
        _fail("canonical", str(path), "JSON bytes are not canonical")
    return value, raw


def _safe_path(root: Path, relative: str) -> Path:
    if not relative or Path(relative).is_absolute() or "\\" in relative:
        _fail("path", relative, "fixture path must be a nonempty POSIX relative path")
    candidate = (root / relative).resolve()
    resolved_root = root.resolve()
    if candidate != resolved_root and resolved_root not in candidate.parents:
        _fail("path", relative, "fixture path escapes the repository root")
    return candidate


def _slug(scenario_id: str) -> str:
    return scenario_id.replace("-", "_")


def _opaque(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _normal_problem() -> dict[str, Any]:
    value = copy.deepcopy(problem_ir.minimal_problem_ir())
    value["variables"][0]["role"] = "free"
    value["statements"] = [value["statements"][0]]
    value["goals"][0]["statement_id"] = "statement_body"
    value["readings"][0]["label"] = "The integer variable x equals itself."
    return value


def _ambiguous_problem() -> dict[str, Any]:
    value = _normal_problem()
    value["goals"].append(
        {
            "id": "goal_alternative",
            "statement_id": "statement_body",
            "mode": "refute",
            "span_ids": [],
        }
    )
    value["goals"].sort(key=lambda item: item["id"])
    base = value["readings"][0]
    base["id"] = "reading_base"
    base["label"] = "Identity claim reading"
    alternative = {
        "id": "reading_other",
        "label": "Refutation request reading",
        "definition_ids": [],
        "assumption_ids": [],
        "goal_ids": ["goal_alternative"],
        "difference_from": "reading_base",
        "differences": [
            {
                "kind": "other",
                "summary": "The source does not choose proof or refutation mode.",
                "affected_ids": ["goal_alternative"],
                "span_ids": [],
            }
        ],
        "span_ids": [],
    }
    value["readings"] = [base, alternative]
    value["ambiguity"] = {
        "status": "unresolved",
        "candidate_reading_ids": ["reading_base", "reading_other"],
        "selected_reading_id": None,
        "required_choice": "Choose proof or refutation mode.",
    }
    return value


def _context(problem_sha256: str, *, ambiguous: bool) -> dict[str, Any]:
    value: dict[str, Any] = {
        "schema": "mathhead.theory-context.v1",
        "context_id": "context_ambiguous" if ambiguous else "context_identity",
        "namespace": "org.mathhead.fixtures",
        "revision": {
            "number": 0,
            "mode": "root",
            "parent": None,
            "retired_declaration_ids": [],
        },
        "scope": {"kind": "theory", "id": None, "parent_theory_sha256": None},
        "artifacts": [
            {
                "id": "artifact_problem",
                "kind": "problem_ir",
                "schema": "mathhead.problem-ir.v1",
                "sha256": problem_sha256,
            }
        ],
        "imports": [],
        "direct_import_ids": [],
        "declarations": [],
        "consistency": {
            "status": "unchecked",
            "basis_sha256": ZERO_SHA256,
            "reason": "The fixture does not promote an unchecked context to consistency.",
        },
        "extensions": {},
    }
    value["consistency"]["basis_sha256"] = theory_context.consistency_basis_sha256(value)
    return value


def _completed_budget() -> dict[str, Any]:
    value = copy.deepcopy(resource_budget.minimal_resource_budget())
    value["budget_id"] = "budget_completed"
    return value


def _timeout_budget() -> dict[str, Any]:
    value = copy.deepcopy(resource_budget.minimal_resource_budget())
    value["budget_id"] = "budget_timeout"
    value["limits"]["wall_time_us"] = 100
    sample = next(event for event in value["events"] if event["kind"] == "sample")
    sample = copy.deepcopy(sample)
    sample["event_id"] = "event_sample_overrun"
    sample["sequence"] = 0
    sample["observation"]["wall_time_us"] = 101
    request = resource_budget.zero_limit_vector()
    request["wall_time_us"] = 1
    value["events"] = [
        sample,
        {
            "event_id": "event_exhaust",
            "sequence": 1,
            "kind": "exhaust",
            "exhaustion_id": "exhaustion_wall",
            "dimensions": ["wall_time_us"],
            "requested": request,
            "reason": "deadline reached",
            "extensions": {},
        },
    ]
    value["outcome"] = {
        "status": "exhausted",
        "exhaustion_id": "exhaustion_wall",
    }
    return value


@dataclass
class ObjectStore:
    values: dict[str, bytes]

    def add(self, value: dict[str, Any]) -> tuple[str, int]:
        raw = canonical_bytes(value)
        digest = _sha(raw)
        previous = self.values.setdefault(digest, raw)
        if previous != raw:
            _fail("identity", digest, "SHA-256 collision in generated object store")
        return digest, len(raw)

    def records(self) -> list[dict[str, Any]]:
        return [
            {
                "sha256": digest,
                "path": f"{OBJECT_DIR.as_posix()}/{digest}.json",
                "byte_count": len(raw),
                "media_type": "application/json",
            }
            for digest, raw in sorted(self.values.items())
        ]


def _attachment(
    store: ObjectStore,
    *,
    attachment_id: str,
    kind: str,
    schema: str,
    producer_component_id: str,
    value: dict[str, Any],
) -> dict[str, Any]:
    digest, byte_count = store.add(value)
    return {
        "attachment_id": attachment_id,
        "kind": kind,
        "schema": schema,
        "sha256": digest,
        "byte_count": byte_count,
        "producer_component_id": producer_component_id,
    }


def _evidence(
    scenario_id: str,
    *,
    problem: dict[str, Any],
    problem_sha256: str,
    context_sha256: str,
    budget_sha256: str,
    plugin: dict[str, Any],
    payload: dict[str, Any],
    payload_kind: str,
) -> dict[str, Any]:
    slug = _slug(scenario_id)
    value = copy.deepcopy(evidence_certificate.minimal_evidence())
    value["evidence_id"] = f"evidence_{slug}"
    value["subject"] = {
        "kind": "goal",
        "subject_id": "goal_reflexive",
        "statement_sha256": canonical_sha256(problem["statements"][0]),
        "problem_ir_sha256": problem_sha256,
        "theory_context_sha256": context_sha256,
        "reading_id": "reading_only",
        "assumption_sha256s": [],
        "obligation_sha256s": [],
    }
    format_id = f"org.mathhead.{payload_kind}"
    value["format"].update(
        {
            "kind": payload_kind,
            "format_id": format_id,
            "schema_sha256": _opaque(f"{format_id}.schema.v1"),
        }
    )
    producer = plugin["components"]["producer"]
    value["producer"] = {
        **copy.deepcopy(producer),
        "role": "solver",
        "environment_contract_sha256": plugin["implementation"]["environment_contract_sha256"],
    }
    payload_id = f"payload_{slug}"
    value["payloads"] = [
        {
            "payload_id": payload_id,
            "role": "primary",
            "media_type": "application/json",
            "sha256": payload["sha256"],
            "byte_count": payload["byte_count"],
            "encoding": "utf-8",
            "compression": "none",
            "extensions": {},
        }
    ]
    value["primary_payload_id"] = payload_id
    value["outcome"] = {
        "status": "produced",
        "payload_ids": [payload_id],
        "diagnostic_ids": [],
    }
    value["generation"].update(
        {
            "algorithm_id": f"org.mathhead.fixture.{scenario_id}",
            "configuration_sha256": producer["configuration_sha256"],
            "input_sha256": canonical_sha256(value["subject"]),
            "basis_sha256": ZERO_SHA256,
        }
    )
    value["budget"] = {
        "initial_sha256": budget_sha256,
        "final_sha256": budget_sha256,
        "outcome": "completed",
    }
    value["generation"]["basis_sha256"] = evidence_certificate.evidence_generation_basis_sha256(
        value
    )
    return value


def _certificate(
    scenario_id: str,
    *,
    evidence: dict[str, Any],
    plugin: dict[str, Any],
    budget_sha256: str,
    checker_result: dict[str, Any],
    replay_log: dict[str, Any],
    observed_payload_sha256: str,
    verdict_status: str,
) -> dict[str, Any]:
    slug = _slug(scenario_id)
    value = copy.deepcopy(evidence_certificate.minimal_certificate(evidence))
    checker = copy.deepcopy(plugin["components"]["checker"])
    checker["environment_contract_sha256"] = plugin["implementation"]["environment_contract_sha256"]
    value["certificate_id"] = f"certificate_{slug}"
    value["checker"] = checker
    value["replay"].update(
        {
            "attempt_id": f"attempt_{slug}",
            "algorithm_id": f"org.mathhead.fixture.check.{scenario_id}",
            "configuration_sha256": checker["configuration_sha256"],
            "input_evidence_sha256": value["evidence"]["evidence_sha256"],
            "expected_payload_sha256": value["evidence"]["primary_payload_sha256"],
            "observed_payload_sha256": observed_payload_sha256,
            "basis_sha256": ZERO_SHA256,
        }
    )
    value["verification_artifacts"] = [
        {
            "artifact_id": "artifact_checker_result",
            "kind": "checker_result",
            "sha256": checker_result["sha256"],
            "byte_count": checker_result["byte_count"],
            "producer_component_id": checker["component_id"],
            "extensions": {},
        },
        {
            "artifact_id": "artifact_replay_log",
            "kind": "replay_log",
            "sha256": replay_log["sha256"],
            "byte_count": replay_log["byte_count"],
            "producer_component_id": checker["component_id"],
            "extensions": {},
        },
    ]
    value["budget"] = {
        "initial_sha256": budget_sha256,
        "final_sha256": budget_sha256,
        "outcome": "completed",
    }
    if verdict_status == "verified":
        value["verdict"] = {
            "status": "verified",
            "authority": "checker_attested",
            "checker_result_artifact_id": "artifact_checker_result",
            "supporting_artifact_ids": [
                "artifact_checker_result",
                "artifact_replay_log",
            ],
            "diagnostic_ids": [],
        }
        value["diagnostics"] = []
    else:
        if verdict_status == "disagreement":
            verdict: dict[str, Any] = {
                "status": "disagreement",
                "conflicting_artifact_ids": [
                    "artifact_checker_result",
                    "artifact_replay_log",
                ],
                "reason": "checker observations conflict",
                "diagnostic_ids": ["diagnostic_certificate"],
            }
            severity = "error"
        else:
            reason_code = (
                "replay_mismatch" if scenario_id == "replay-mismatch" else "semantic_failure"
            )
            verdict = {
                "status": "invalid",
                "reason_code": reason_code,
                "checker_result_artifact_id": "artifact_checker_result",
                "reason": (
                    "replayed payload differs"
                    if reason_code == "replay_mismatch"
                    else "checker rejected the mathematical claim"
                ),
                "diagnostic_ids": ["diagnostic_certificate"],
            }
            severity = "warning"
        value["verdict"] = verdict
        value["diagnostics"] = [
            {
                "diagnostic_id": "diagnostic_certificate",
                "severity": severity,
                "code": f"org.mathhead.fixture.{scenario_id}",
                "message": "certificate did not establish a verified claim",
                "related_artifact_ids": ["artifact_checker_result"],
                "details": {},
            }
        ]
    value["trust_dependencies"] = sorted(
        [
            {
                "kind": "checker_configuration",
                "identifier": checker["component_id"],
                "sha256": checker["configuration_sha256"],
            },
            {
                "kind": "checker_contract",
                "identifier": checker["contract_id"],
                "sha256": checker["contract_sha256"],
            },
            {
                "kind": "checker_implementation",
                "identifier": checker["component_id"],
                "sha256": checker["implementation_sha256"],
            },
            {
                "kind": "environment_contract",
                "identifier": "MH-C-ENV-002",
                "sha256": checker["environment_contract_sha256"],
            },
            {
                "kind": "evidence",
                "identifier": evidence["evidence_id"],
                "sha256": value["evidence"]["evidence_sha256"],
            },
            {
                "kind": "problem_ir",
                "identifier": "ProblemIR",
                "sha256": evidence["subject"]["problem_ir_sha256"],
            },
            {
                "kind": "theory_context",
                "identifier": "TheoryContext",
                "sha256": evidence["subject"]["theory_context_sha256"],
            },
        ],
        key=lambda item: (item["kind"], item["identifier"]),
    )
    value["replay"]["basis_sha256"] = evidence_certificate.certificate_replay_basis_sha256(value)
    return value


def _diagnostic(scenario_id: str, *, severity: str) -> dict[str, Any]:
    return {
        "diagnostic_id": "diagnostic_result",
        "severity": severity,
        "code": f"org.mathhead.fixture.{scenario_id}",
        "message": "fixture execution did not establish a completed verified outcome",
        "related_artifact_ids": [],
        "details": {},
    }


def _result_artifact(
    *,
    artifact_id: str,
    kind: str,
    schema: str,
    binding: dict[str, Any],
    producer_component_id: str,
) -> dict[str, Any]:
    return {
        "artifact_id": artifact_id,
        "kind": kind,
        "schema": schema,
        "sha256": binding["sha256"],
        "byte_count": binding["byte_count"],
        "producer_component_id": producer_component_id,
        "extensions": {},
    }


def _engine_result(
    scenario_id: str,
    *,
    problem: dict[str, Any],
    problem_binding: dict[str, Any],
    context_binding: dict[str, Any],
    budget_binding: dict[str, Any],
    plugin: dict[str, Any],
    plugin_binding: dict[str, Any],
    evidence_binding: dict[str, Any] | None,
    certificate_binding: dict[str, Any] | None,
    checker_result: dict[str, Any] | None,
    backend_inputs: list[dict[str, Any]],
) -> dict[str, Any]:
    slug = _slug(scenario_id)
    value = copy.deepcopy(engine_result.minimal_engine_result())
    producer = copy.deepcopy(plugin["components"]["producer"])
    checker = copy.deepcopy(plugin["components"]["checker"])
    value["result_id"] = f"result_{slug}"
    value["provenance"] = {
        "producer": producer,
        "components": [checker],
        "environment_contract_sha256": plugin["implementation"]["environment_contract_sha256"],
    }
    ambiguous = scenario_id == "ambiguity"
    if ambiguous:
        candidates = ["reading_base", "reading_other"]
        selected = None
        goals = ["goal_alternative", "goal_reflexive"]
    else:
        candidates = ["reading_only"]
        selected = "reading_only"
        goals = ["goal_reflexive"]
    value["request"] = {
        "request_id": f"request_{slug}",
        "problem_ir_sha256": problem_binding["sha256"],
        "theory_context_sha256": context_binding["sha256"],
        "initial_budget_sha256": budget_binding["sha256"],
        "candidate_reading_ids": candidates,
        "selected_reading_id": selected,
        "goal_ids": goals,
    }
    value["replay"].update(
        {
            "replay_id": f"replay_{slug}",
            "algorithm_id": f"org.mathhead.fixture.solve.{scenario_id}",
            "configuration_sha256": producer["configuration_sha256"],
            "plan_sha256": _opaque(f"fixture-plan:{scenario_id}:{plugin_binding['sha256']}"),
            "basis_sha256": ZERO_SHA256,
        }
    )
    artifacts: list[dict[str, Any]] = []
    primary_id = "artifact_primary_evidence"
    certificate_id = "artifact_certificate"
    if evidence_binding is not None:
        primary_kind = "counterexample" if scenario_id == "refutation" else "proof"
        if scenario_id not in {"proof", "refutation"}:
            primary_kind = "evidence"
        artifacts.append(
            _result_artifact(
                artifact_id=primary_id,
                kind=primary_kind,
                schema="mathhead.evidence.v1",
                binding=evidence_binding,
                producer_component_id=producer["component_id"],
            )
        )
    if certificate_binding is not None:
        artifacts.append(
            _result_artifact(
                artifact_id=certificate_id,
                kind="certificate",
                schema="mathhead.certificate.v1",
                binding=certificate_binding,
                producer_component_id=checker["component_id"],
            )
        )
    if checker_result is not None:
        artifacts.append(
            _result_artifact(
                artifact_id="artifact_checker_result",
                kind="checker_result",
                schema=checker_result["schema"],
                binding=checker_result,
                producer_component_id=checker["component_id"],
            )
        )
    for backend in backend_inputs:
        artifacts.append(
            _result_artifact(
                artifact_id=backend["attachment_id"],
                kind="disagreement_input",
                schema=backend["schema"],
                binding=backend,
                producer_component_id=backend["producer_component_id"],
            )
        )
    value["artifacts"] = sorted(artifacts, key=lambda item: item["artifact_id"])
    value["diagnostics"] = []
    verification = {
        "checker_component_id": checker["component_id"],
        "checker_contract_id": checker["contract_id"],
        "checker_contract_sha256": checker["contract_sha256"],
        "checker_result_artifact_id": "artifact_checker_result",
        "evidence_artifact_ids": [certificate_id],
        "trust_dependency_sha256": sorted(
            {
                checker["contract_sha256"],
                checker["implementation_sha256"],
                problem_binding["sha256"],
                context_binding["sha256"],
            }
        ),
    }
    assessment_base = {
        "assessment_id": "assessment_main",
        "goal_id": "goal_reflexive",
        "reading_id": "reading_only",
        "assumption_refs": [],
        "discharged_obligations": [],
        "extensions": {},
    }
    if scenario_id in {"proof", "refutation"}:
        support = sorted(["artifact_checker_result", certificate_id, primary_id])
        verdict: dict[str, Any] = {
            "status": "proved" if scenario_id == "proof" else "refuted",
            "epistemic_tier": "checker_attested",
            "support_artifact_ids": support,
            "verification": verification,
        }
        if scenario_id == "refutation":
            verdict["counterexample_artifact_ids"] = [primary_id]
        assessment = copy.deepcopy(assessment_base)
        assessment["verdict"] = verdict
        assessment["discharged_obligations"] = [
            {
                "obligation_id": "obligation_fixture",
                "evidence_artifact_ids": [certificate_id],
            }
        ]
        value["assessments"] = [assessment]
        value["execution"] = {"status": "completed", "diagnostic_ids": []}
    elif scenario_id == "unsupported":
        assessment = copy.deepcopy(assessment_base)
        assessment["verdict"] = {
            "status": "unsupported",
            "epistemic_tier": "producer_reported",
            "feature_codes": ["org.mathhead.transcendental"],
        }
        value["assessments"] = [assessment]
        value["execution"] = {
            "status": "unsupported",
            "feature_codes": ["org.mathhead.transcendental"],
            "reason": "input feature is outside the supported fragment",
            "diagnostic_ids": ["diagnostic_result"],
        }
        value["diagnostics"] = [_diagnostic(scenario_id, severity="warning")]
    elif scenario_id == "ambiguity":
        value["assessments"] = []
        value["execution"] = {
            "status": "ambiguous",
            "reading_ids": candidates,
            "reason": "multiple readings require an explicit choice",
            "diagnostic_ids": ["diagnostic_result"],
        }
        value["diagnostics"] = [_diagnostic(scenario_id, severity="warning")]
    elif scenario_id == "timeout":
        value["assessments"] = []
        value["execution"] = {
            "status": "exhausted",
            "exhaustion_id": "exhaustion_wall",
            "dimensions": ["wall_time_us"],
            "reason": "deadline reached",
            "diagnostic_ids": ["diagnostic_result"],
        }
        value["diagnostics"] = [_diagnostic(scenario_id, severity="warning")]
    else:
        reason = (
            "backend_disagreement" if scenario_id == "backend-disagreement" else "verifier_failure"
        )
        assessment = copy.deepcopy(assessment_base)
        assessment["verdict"] = {
            "status": "unknown",
            "epistemic_tier": "producer_reported",
            "reason": reason,
            "support_artifact_ids": sorted([certificate_id, primary_id]),
        }
        value["assessments"] = [assessment]
        if scenario_id == "backend-disagreement":
            value["execution"] = {
                "status": "disagreement",
                "backend_artifact_ids": sorted(item["attachment_id"] for item in backend_inputs),
                "reason": "backends returned incompatible claims",
                "diagnostic_ids": ["diagnostic_result"],
            }
        else:
            value["execution"] = {
                "status": "verifier_failed",
                "checker_result_artifact_ids": ["artifact_checker_result"],
                "reason": "certificate did not verify producer evidence",
                "diagnostic_ids": ["diagnostic_result"],
            }
        value["diagnostics"] = [_diagnostic(scenario_id, severity="error")]
    budget_outcome = "exhausted" if scenario_id == "timeout" else "completed"
    value["budget"] = {
        "budget_id": f"budget_snapshot_{slug}",
        "initial_budget_sha256": budget_binding["sha256"],
        "final_budget_sha256": budget_binding["sha256"],
        "outcome": budget_outcome,
        "usage": engine_result._usage(),  # noqa: SLF001
    }
    value["replay"]["basis_sha256"] = engine_result.replay_basis_sha256(value)
    return value


def _present_binding(
    role: str,
    digest: str,
    byte_count: int,
    dependencies: list[str],
) -> dict[str, Any]:
    contract_id, contract_sha256, schema = ROLE_CONTRACTS[role]
    return {
        "role": role,
        "state": "present",
        "contract_id": contract_id,
        "contract_sha256": contract_sha256,
        "schema": schema,
        "sha256": digest,
        "byte_count": byte_count,
        "depends_on_sha256": sorted(set(dependencies)),
    }


def _absent_binding(role: str, reason: str) -> dict[str, Any]:
    return {"role": role, "state": "absent", "reason": reason}


def _scenario_expectation(scenario_id: str) -> dict[str, str]:
    values = {
        "proof": ("supported", "completed", "proved", "produced", "verified", "completed"),
        "refutation": (
            "supported",
            "completed",
            "refuted",
            "produced",
            "verified",
            "completed",
        ),
        "ambiguity": ("unsupported", "ambiguous", "none", "absent", "absent", "completed"),
        "unsupported": (
            "unsupported",
            "unsupported",
            "unsupported",
            "absent",
            "absent",
            "completed",
        ),
        "timeout": ("supported", "exhausted", "none", "absent", "absent", "exhausted"),
        "backend-disagreement": (
            "supported",
            "disagreement",
            "unknown",
            "produced",
            "disagreement",
            "completed",
        ),
        "invalid-certificate": (
            "supported",
            "verifier_failed",
            "unknown",
            "produced",
            "invalid",
            "completed",
        ),
        "replay-mismatch": (
            "supported",
            "verifier_failed",
            "unknown",
            "produced",
            "invalid",
            "completed",
        ),
    }
    route, execution, mathematical, evidence, certificate, budget = values[scenario_id]
    return {
        "route_status": route,
        "execution_status": execution,
        "mathematical_status": mathematical,
        "evidence_status": evidence,
        "certificate_status": certificate,
        "budget_outcome": budget,
        "authority": "checker_attested" if certificate == "verified" else "none",
    }


def _fragment(scenario_id: str) -> dict[str, Any]:
    value = copy.deepcopy(theory_plugin.minimal_fragment())
    if scenario_id == "ambiguity":
        value["ambiguous"] = True
    if scenario_id == "unsupported":
        value["expression_kinds"] = ["org.mathhead.expression.transcendental"]
    return value


def _role_dependencies(bindings: dict[str, dict[str, Any]]) -> dict[str, list[str]]:
    required = {
        "problem_ir": [],
        "theory_context": ["problem_ir"],
        "resource_budget": [],
        "theory_plugin": [],
        "evidence": ["problem_ir", "theory_context", "resource_budget", "theory_plugin"],
        "certificate": [
            "problem_ir",
            "theory_context",
            "resource_budget",
            "theory_plugin",
            "evidence",
        ],
        "engine_result": ["problem_ir", "theory_context", "resource_budget", "theory_plugin"],
    }
    if bindings.get("evidence", {}).get("state") == "present":
        required["engine_result"].append("evidence")
    if bindings.get("certificate", {}).get("state") == "present":
        required["engine_result"].append("certificate")
    return {
        role: [bindings[item]["sha256"] for item in dependencies]
        for role, dependencies in required.items()
        if bindings.get(role, {}).get("state") == "present"
    }


def build_bundle(root: Path) -> tuple[dict[str, Any], dict[str, bytes]]:
    schema_path = root / SCHEMA_PATH
    report_path = root / CONFORMANCE_REPORT_PATH
    try:
        schema_raw = schema_path.read_bytes()
        report_raw = report_path.read_bytes()
    except OSError as exc:
        _fail("dependency", str(exc.filename), str(exc))
    store = ObjectStore({})
    plugin = copy.deepcopy(theory_plugin.minimal_theory_plugin())
    plugin_sha, plugin_size = store.add(plugin)
    normal_problem = _normal_problem()
    ambiguous_problem = _ambiguous_problem()
    problem_values = {False: normal_problem, True: ambiguous_problem}
    problem_bindings: dict[bool, dict[str, Any]] = {}
    context_values: dict[bool, dict[str, Any]] = {}
    context_bindings: dict[bool, dict[str, Any]] = {}
    for ambiguous, value in problem_values.items():
        digest, size = store.add(value)
        problem_bindings[ambiguous] = {"sha256": digest, "byte_count": size}
        context = _context(digest, ambiguous=ambiguous)
        context_values[ambiguous] = context
        context_digest, context_size = store.add(context)
        context_bindings[ambiguous] = {
            "sha256": context_digest,
            "byte_count": context_size,
        }
    completed_budget = _completed_budget()
    timeout_budget = _timeout_budget()
    budget_values = {False: completed_budget, True: timeout_budget}
    budget_bindings: dict[bool, dict[str, Any]] = {}
    for timeout, value in budget_values.items():
        digest, size = store.add(value)
        budget_bindings[timeout] = {"sha256": digest, "byte_count": size}
    scenarios: list[dict[str, Any]] = []
    for scenario_id in SCENARIO_ORDER:
        ambiguous = scenario_id == "ambiguity"
        timeout = scenario_id == "timeout"
        problem = problem_values[ambiguous]
        problem_binding = problem_bindings[ambiguous]
        context_binding = context_bindings[ambiguous]
        budget_binding = budget_bindings[timeout]
        plugin_binding = {"sha256": plugin_sha, "byte_count": plugin_size}
        attachments: list[dict[str, Any]] = []
        evidence_value: dict[str, Any] | None = None
        certificate_value: dict[str, Any] | None = None
        evidence_binding: dict[str, Any] | None = None
        certificate_binding: dict[str, Any] | None = None
        checker_result: dict[str, Any] | None = None
        backend_inputs: list[dict[str, Any]] = []
        has_evidence = scenario_id not in {"ambiguity", "unsupported", "timeout"}
        if has_evidence:
            payload_kind = "counterexample" if scenario_id == "refutation" else "proof"
            payload = _attachment(
                store,
                attachment_id=f"payload_{_slug(scenario_id)}",
                kind=payload_kind,
                schema=f"org.mathhead.fixture.{payload_kind}.v1",
                producer_component_id=plugin["components"]["producer"]["component_id"],
                value={
                    "kind": payload_kind,
                    "scenario_id": scenario_id,
                    "statement_sha256": canonical_sha256(problem["statements"][0]),
                },
            )
            attachments.append(payload)
            evidence_value = _evidence(
                scenario_id,
                problem=problem,
                problem_sha256=problem_binding["sha256"],
                context_sha256=context_binding["sha256"],
                budget_sha256=budget_binding["sha256"],
                plugin=plugin,
                payload=payload,
                payload_kind=payload_kind,
            )
            evidence_sha, evidence_size = store.add(evidence_value)
            evidence_binding = {"sha256": evidence_sha, "byte_count": evidence_size}
            observed = payload["sha256"]
            if scenario_id == "replay-mismatch":
                replayed = _attachment(
                    store,
                    attachment_id="payload_replayed",
                    kind="proof",
                    schema="org.mathhead.fixture.proof.v1",
                    producer_component_id=plugin["components"]["checker"]["component_id"],
                    value={
                        "kind": "proof",
                        "scenario_id": scenario_id,
                        "statement_sha256": _opaque("mismatched-statement"),
                    },
                )
                attachments.append(replayed)
                observed = replayed["sha256"]
            certificate_status = _scenario_expectation(scenario_id)["certificate_status"]
            checker_result = _attachment(
                store,
                attachment_id="artifact_checker_result",
                kind="checker_result",
                schema="org.mathhead.fixture.checker-result.v1",
                producer_component_id=plugin["components"]["checker"]["component_id"],
                value={
                    "observed_payload_sha256": observed,
                    "scenario_id": scenario_id,
                    "status": certificate_status,
                },
            )
            attachments.append(checker_result)
            replay_log = _attachment(
                store,
                attachment_id="artifact_replay_log",
                kind="replay_log",
                schema="org.mathhead.fixture.replay-log.v1",
                producer_component_id=plugin["components"]["checker"]["component_id"],
                value={
                    "expected_payload_sha256": payload["sha256"],
                    "observed_payload_sha256": observed,
                    "scenario_id": scenario_id,
                },
            )
            attachments.append(replay_log)
            certificate_value = _certificate(
                scenario_id,
                evidence=evidence_value,
                plugin=plugin,
                budget_sha256=budget_binding["sha256"],
                checker_result=checker_result,
                replay_log=replay_log,
                observed_payload_sha256=observed,
                verdict_status=certificate_status,
            )
            certificate_sha, certificate_size = store.add(certificate_value)
            certificate_binding = {
                "sha256": certificate_sha,
                "byte_count": certificate_size,
            }
        if scenario_id == "backend-disagreement":
            for suffix, component in (
                ("checker", plugin["components"]["checker"]),
                ("producer", plugin["components"]["producer"]),
            ):
                backend = _attachment(
                    store,
                    attachment_id=f"artifact_backend_{suffix}",
                    kind="disagreement_input",
                    schema="org.mathhead.fixture.backend-result.v1",
                    producer_component_id=component["component_id"],
                    value={
                        "claim": "proved" if suffix == "producer" else "refuted",
                        "scenario_id": scenario_id,
                    },
                )
                attachments.append(backend)
                backend_inputs.append(backend)
        result = _engine_result(
            scenario_id,
            problem=problem,
            problem_binding=problem_binding,
            context_binding=context_binding,
            budget_binding=budget_binding,
            plugin=plugin,
            plugin_binding=plugin_binding,
            evidence_binding=evidence_binding,
            certificate_binding=certificate_binding,
            checker_result=checker_result,
            backend_inputs=backend_inputs,
        )
        result_sha, result_size = store.add(result)
        bindings: dict[str, dict[str, Any]] = {
            "problem_ir": _present_binding(
                "problem_ir", problem_binding["sha256"], problem_binding["byte_count"], []
            ),
            "theory_context": _present_binding(
                "theory_context",
                context_binding["sha256"],
                context_binding["byte_count"],
                [problem_binding["sha256"]],
            ),
            "resource_budget": _present_binding(
                "resource_budget", budget_binding["sha256"], budget_binding["byte_count"], []
            ),
            "theory_plugin": _present_binding("theory_plugin", plugin_sha, plugin_size, []),
        }
        if evidence_binding is None:
            bindings["evidence"] = _absent_binding(
                "evidence", "execution stopped before a producer Evidence envelope existed"
            )
            bindings["certificate"] = _absent_binding(
                "certificate", "no Evidence bytes existed for independent checking"
            )
        else:
            bindings["evidence"] = _present_binding(
                "evidence", evidence_binding["sha256"], evidence_binding["byte_count"], []
            )
            assert certificate_binding is not None
            bindings["certificate"] = _present_binding(
                "certificate",
                certificate_binding["sha256"],
                certificate_binding["byte_count"],
                [],
            )
        bindings["engine_result"] = _present_binding("engine_result", result_sha, result_size, [])
        dependencies = _role_dependencies(bindings)
        for role, digests in dependencies.items():
            bindings[role]["depends_on_sha256"] = sorted(digests)
        fragment = _fragment(scenario_id)
        route = theory_plugin.route_fragment(plugin, fragment, kind="decision")
        scenarios.append(
            {
                "scenario_id": scenario_id,
                "description": {
                    "proof": "A checked proof establishes the requested goal.",
                    "refutation": "A checked counterexample refutes the requested goal.",
                    "ambiguity": "Two complete readings remain unresolved and no output is promoted.",
                    "unsupported": "The plugin rejects a fragment outside its declared capability.",
                    "timeout": "The wall-time budget is exhausted before evidence exists.",
                    "backend-disagreement": "Producer and checker backend claims conflict.",
                    "invalid-certificate": "The checker rejects produced evidence semantically.",
                    "replay-mismatch": "Replay observes bytes different from the expected payload.",
                }[scenario_id],
                "routing": {"fragment": fragment, **route},
                "expected": _scenario_expectation(scenario_id),
                "artifacts": [bindings[role] for role in ROLE_ORDER],
                "attachments": sorted(attachments, key=lambda item: item["attachment_id"]),
            }
        )
    manifest: dict[str, Any] = {
        "schema": MANIFEST_SCHEMA_ID,
        "bundle_id": BUNDLE_ID,
        "bundle_sha256": ZERO_SHA256,
        "manifest_schema_sha256": _sha(schema_raw),
        "conformance_report_sha256": _sha(report_raw),
        "contracts": list(CONTRACT_CLOSURE),
        "scenario_order": list(SCENARIO_ORDER),
        "scenarios": scenarios,
        "objects": store.records(),
        "extensions": {},
    }
    manifest["bundle_sha256"] = bundle_basis_sha256(manifest)
    return manifest, store.values


def bundle_basis_sha256(manifest: dict[str, Any]) -> str:
    basis = copy.deepcopy(manifest)
    basis["bundle_sha256"] = ZERO_SHA256
    return canonical_sha256(basis)


def _exact_fields(value: dict[str, Any], expected: set[str], path: str) -> None:
    if set(value) != expected:
        _fail("shape", path, f"field set must be {sorted(expected)}")


def _require_string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value:
        _fail("shape", path, "must be a nonempty string")
    return value


def _validate_manifest_shape(manifest: dict[str, Any]) -> None:
    _exact_fields(
        manifest,
        {
            "schema",
            "bundle_id",
            "bundle_sha256",
            "manifest_schema_sha256",
            "conformance_report_sha256",
            "contracts",
            "scenario_order",
            "scenarios",
            "objects",
            "extensions",
        },
        "$",
    )
    if manifest["schema"] != MANIFEST_SCHEMA_ID or manifest["bundle_id"] != BUNDLE_ID:
        _fail("identity", "$", "bundle or schema identity drift")
    for field in ("bundle_sha256", "manifest_schema_sha256", "conformance_report_sha256"):
        if not isinstance(manifest[field], str) or SHA256_RE.fullmatch(manifest[field]) is None:
            _fail("shape", f"$.{field}", "must be lowercase SHA-256")
    if manifest["extensions"] != {}:
        _fail("shape", "$.extensions", "v1 extensions must be empty")
    if manifest["scenario_order"] != list(SCENARIO_ORDER):
        _fail("scenario-order", "$.scenario_order", "scenario order drift")
    scenarios = manifest["scenarios"]
    if not isinstance(scenarios, list) or [item.get("scenario_id") for item in scenarios] != list(
        SCENARIO_ORDER
    ):
        _fail("scenario-order", "$.scenarios", "exact scenario inventory or order drift")
    if manifest["contracts"] != list(CONTRACT_CLOSURE):
        _fail("contract", "$.contracts", "accepted contract closure drift")
    objects = manifest["objects"]
    if not isinstance(objects, list):
        _fail("shape", "$.objects", "must be an array")
    object_hashes: list[str] = []
    for index, item in enumerate(objects):
        path = f"$.objects[{index}]"
        if not isinstance(item, dict):
            _fail("shape", path, "must be an object")
        _exact_fields(item, {"sha256", "path", "byte_count", "media_type"}, path)
        digest = _require_string(item["sha256"], f"{path}.sha256")
        if SHA256_RE.fullmatch(digest) is None:
            _fail("shape", f"{path}.sha256", "must be lowercase SHA-256")
        if item["path"] != f"{OBJECT_DIR.as_posix()}/{digest}.json":
            _fail("path", f"{path}.path", "content-addressed object path drift")
        if (
            isinstance(item["byte_count"], bool)
            or not isinstance(item["byte_count"], int)
            or item["byte_count"] <= 0
        ):
            _fail("empty", f"{path}.byte_count", "present objects cannot be empty")
        if item["media_type"] != "application/json":
            _fail("shape", f"{path}.media_type", "object media type drift")
        object_hashes.append(digest)
    if object_hashes != sorted(set(object_hashes)):
        _fail("order", "$.objects", "objects must be sorted and unique by SHA-256")
    for scenario_index, scenario in enumerate(scenarios):
        path = f"$.scenarios[{scenario_index}]"
        if not isinstance(scenario, dict):
            _fail("shape", path, "must be an object")
        _exact_fields(
            scenario,
            {
                "scenario_id",
                "description",
                "routing",
                "expected",
                "artifacts",
                "attachments",
            },
            path,
        )
        _require_string(scenario["description"], f"{path}.description")
        bindings = scenario["artifacts"]
        if not isinstance(bindings, list) or [item.get("role") for item in bindings] != list(
            ROLE_ORDER
        ):
            _fail("order", f"{path}.artifacts", "artifact role order drift")
        for offset, binding in enumerate(bindings):
            binding_path = f"{path}.artifacts[{offset}]"
            if not isinstance(binding, dict):
                _fail("shape", binding_path, "must be an object")
            state = binding.get("state")
            if state == "present":
                _exact_fields(
                    binding,
                    {
                        "role",
                        "state",
                        "contract_id",
                        "contract_sha256",
                        "schema",
                        "sha256",
                        "byte_count",
                        "depends_on_sha256",
                    },
                    binding_path,
                )
                if binding["sha256"] not in object_hashes:
                    _fail("reference", f"{binding_path}.sha256", "object is undeclared")
                if not isinstance(binding["byte_count"], int) or binding["byte_count"] <= 0:
                    _fail("empty", f"{binding_path}.byte_count", "present artifact is empty")
                dependencies = binding["depends_on_sha256"]
                if not isinstance(dependencies, list) or dependencies != sorted(set(dependencies)):
                    _fail("order", f"{binding_path}.depends_on_sha256", "dependencies drift")
            elif state == "absent":
                _exact_fields(binding, {"role", "state", "reason"}, binding_path)
                _require_string(binding["reason"], f"{binding_path}.reason")
            else:
                _fail("shape", f"{binding_path}.state", "unknown artifact presence state")
        attachments = scenario["attachments"]
        if not isinstance(attachments, list):
            _fail("shape", f"{path}.attachments", "must be an array")
        ids: list[str] = []
        for offset, attachment in enumerate(attachments):
            attachment_path = f"{path}.attachments[{offset}]"
            if not isinstance(attachment, dict):
                _fail("shape", attachment_path, "must be an object")
            _exact_fields(
                attachment,
                {
                    "attachment_id",
                    "kind",
                    "schema",
                    "sha256",
                    "byte_count",
                    "producer_component_id",
                },
                attachment_path,
            )
            ids.append(_require_string(attachment["attachment_id"], attachment_path))
            if attachment["sha256"] not in object_hashes:
                _fail("reference", f"{attachment_path}.sha256", "attachment object undeclared")
            if not isinstance(attachment["byte_count"], int) or attachment["byte_count"] <= 0:
                _fail("empty", f"{attachment_path}.byte_count", "attachment is empty")
        if ids != sorted(set(ids)):
            _fail("order", f"{path}.attachments", "attachment IDs must sort and deduplicate")


def _validate_schema(root: Path, manifest: dict[str, Any]) -> None:
    schema, raw = load_json(root / SCHEMA_PATH, canonical=True)
    if _sha(raw) != manifest["manifest_schema_sha256"]:
        _fail("schema-hash", str(SCHEMA_PATH), "manifest schema hash drift")
    if (
        schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema"
        or schema.get("$id") != MANIFEST_SCHEMA_ID
        or schema.get("type") != "object"
        or schema.get("additionalProperties") is not False
    ):
        _fail("schema", str(SCHEMA_PATH), "schema dialect, identity, or closure drift")
    try:
        import jsonschema
    except ImportError:
        return
    try:
        jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.Draft202012Validator(schema).validate(manifest)
    except jsonschema.exceptions.SchemaError as exc:
        _fail("schema-meta", str(SCHEMA_PATH), str(exc))
    except jsonschema.exceptions.ValidationError as exc:
        _fail("shape", "$.manifest", str(exc))


def _load_objects(root: Path, manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    objects: dict[str, dict[str, Any]] = {}
    declared_paths: set[Path] = set()
    for record in manifest["objects"]:
        path = _safe_path(root, record["path"])
        value, raw = load_json(path, canonical=True)
        digest = _sha(raw)
        if digest != record["sha256"]:
            _fail("object-hash", record["path"], "object SHA-256 does not match bytes")
        if len(raw) != record["byte_count"]:
            _fail("byte-count", record["path"], "object byte count does not match bytes")
        objects[digest] = value
        declared_paths.add(path)
    object_dir = _safe_path(root, OBJECT_DIR.as_posix())
    actual_paths = set(object_dir.glob("*.json")) if object_dir.is_dir() else set()
    if actual_paths != declared_paths:
        _fail("object-inventory", str(OBJECT_DIR), "undeclared, missing, or stale object file")
    return objects


def _schema_documents(root: Path) -> dict[str, dict[str, Any]]:
    paths = {
        "problem_ir": problem_ir.SCHEMA_PATH,
        "theory_context": theory_context.SCHEMA_PATH,
        "resource_budget": resource_budget.SCHEMA_PATH,
        "theory_plugin": theory_plugin.SCHEMA_PATH,
        "engine_result": engine_result.SCHEMA_PATH,
        "evidence": evidence_certificate.EVIDENCE_SCHEMA_PATH,
        "certificate": evidence_certificate.CERTIFICATE_SCHEMA_PATH,
    }
    return {role: load_json(root / path)[0] for role, path in paths.items()}


def _translate_validation(role: str, action: Any) -> None:
    try:
        action()
    except ReferenceFixtureError:
        raise
    except Exception as exc:
        kind = getattr(exc, "kind", "semantic")
        _fail(f"artifact-{kind}", role, str(exc))


def _artifact_map(scenario: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {binding["role"]: binding for binding in scenario["artifacts"]}


def _attachment_map(scenario: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["attachment_id"]: item for item in scenario["attachments"]}


def _validate_dag(scenario: dict[str, Any]) -> None:
    present = {
        binding["sha256"]: binding
        for binding in scenario["artifacts"]
        if binding["state"] == "present"
    }
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(digest: str) -> None:
        if digest in visited:
            return
        if digest in visiting:
            _fail("dependency-cycle", scenario["scenario_id"], "artifact dependency cycle")
        visiting.add(digest)
        for dependency in present[digest]["depends_on_sha256"]:
            if dependency not in present:
                _fail("dependency", scenario["scenario_id"], "dependency is absent or foreign")
            visit(dependency)
        visiting.remove(digest)
        visited.add(digest)

    for digest in present:
        visit(digest)


def _validate_scenario(
    scenario: dict[str, Any],
    objects: dict[str, dict[str, Any]],
    schemas: dict[str, dict[str, Any]],
) -> None:
    scenario_id = scenario["scenario_id"]
    bindings = _artifact_map(scenario)
    attachments = _attachment_map(scenario)
    _validate_dag(scenario)
    for role, binding in bindings.items():
        if binding["state"] == "absent":
            continue
        expected_contract = ROLE_CONTRACTS[role]
        if (
            binding["contract_id"],
            binding["contract_sha256"],
            binding["schema"],
        ) != expected_contract:
            _fail("contract", f"{scenario_id}.{role}", "role contract binding drift")
        object_record = objects[binding["sha256"]]
        if len(canonical_bytes(object_record)) != binding["byte_count"]:
            _fail("byte-count", f"{scenario_id}.{role}", "artifact byte count drift")
    problem = objects[bindings["problem_ir"]["sha256"]]
    context = objects[bindings["theory_context"]["sha256"]]
    budget = objects[bindings["resource_budget"]["sha256"]]
    plugin = objects[bindings["theory_plugin"]["sha256"]]
    result = objects[bindings["engine_result"]["sha256"]]
    _translate_validation(
        "problem_ir", lambda: problem_ir.validate_problem_ir(problem, schemas["problem_ir"])
    )
    _translate_validation(
        "theory_context",
        lambda: theory_context.validate_theory_context(context, schemas["theory_context"]),
    )
    _translate_validation(
        "resource_budget",
        lambda: resource_budget.validate_resource_budget(budget, schemas["resource_budget"]),
    )
    _translate_validation(
        "theory_plugin",
        lambda: theory_plugin.validate_theory_plugin(plugin, schemas["theory_plugin"]),
    )
    _translate_validation(
        "engine_result",
        lambda: engine_result.validate_engine_result(result, schemas["engine_result"]),
    )
    if context["artifacts"] != [
        {
            "id": "artifact_problem",
            "kind": "problem_ir",
            "schema": "mathhead.problem-ir.v1",
            "sha256": bindings["problem_ir"]["sha256"],
        }
    ]:
        _fail("cross-link", f"{scenario_id}.theory_context", "ProblemIR binding drift")
    request = result["request"]
    if request["problem_ir_sha256"] != bindings["problem_ir"]["sha256"]:
        _fail("cross-link", f"{scenario_id}.engine_result", "ProblemIR request binding drift")
    if request["theory_context_sha256"] != bindings["theory_context"]["sha256"]:
        _fail("cross-link", f"{scenario_id}.engine_result", "TheoryContext binding drift")
    if request["initial_budget_sha256"] != bindings["resource_budget"]["sha256"]:
        _fail("cross-link", f"{scenario_id}.engine_result", "ResourceBudget binding drift")
    producer = plugin["components"]["producer"]
    checker = plugin["components"]["checker"]
    if result["provenance"]["producer"] != producer or result["provenance"]["components"] != [
        checker
    ]:
        _fail("provenance", f"{scenario_id}.engine_result", "TheoryPlugin provenance drift")
    route = theory_plugin.route_fragment(plugin, scenario["routing"]["fragment"], kind="decision")
    if scenario["routing"] != {"fragment": scenario["routing"]["fragment"], **route}:
        _fail("routing", scenario_id, "recorded plugin route drift")
    expectation = scenario["expected"]
    if expectation != _scenario_expectation(scenario_id):
        _fail("expectation", scenario_id, "scenario expectation drift")
    if route["status"] != expectation["route_status"]:
        _fail("routing", scenario_id, "route does not match expected status")
    if result["execution"]["status"] != expectation["execution_status"]:
        _fail("outcome", scenario_id, "EngineResult execution status drift")
    if budget["outcome"]["status"] != expectation["budget_outcome"]:
        _fail("budget", scenario_id, "ResourceBudget outcome drift")
    verdicts = [item["verdict"]["status"] for item in result["assessments"]]
    expected_math = expectation["mathematical_status"]
    if expected_math == "none":
        if verdicts:
            _fail("authority", scenario_id, "failure state promoted a mathematical verdict")
    elif verdicts != [expected_math]:
        _fail("outcome", scenario_id, "mathematical verdict drift")
    evidence_binding = bindings["evidence"]
    certificate_binding = bindings["certificate"]
    if expectation["evidence_status"] == "absent":
        if evidence_binding["state"] != "absent" or certificate_binding["state"] != "absent":
            _fail("presence", scenario_id, "absent evidence or certificate became present")
        if attachments:
            _fail("presence", scenario_id, "pre-evidence scenario has attachments")
        if any(
            artifact["kind"] in {"proof", "counterexample", "evidence", "certificate"}
            for artifact in result["artifacts"]
        ):
            _fail("authority", scenario_id, "absent output is represented as an artifact")
        return
    if evidence_binding["state"] != "present" or certificate_binding["state"] != "present":
        _fail("presence", scenario_id, "required evidence or certificate is absent")
    evidence = objects[evidence_binding["sha256"]]
    certificate = objects[certificate_binding["sha256"]]
    _translate_validation(
        "evidence",
        lambda: evidence_certificate.validate_evidence(evidence, schemas["evidence"]),
    )
    _translate_validation(
        "certificate",
        lambda: evidence_certificate.validate_certificate(
            certificate,
            schemas["certificate"],
            evidence=evidence,
            evidence_schema=schemas["evidence"],
        ),
    )
    if evidence["subject"]["problem_ir_sha256"] != bindings["problem_ir"]["sha256"]:
        _fail("cross-link", f"{scenario_id}.evidence", "ProblemIR subject binding drift")
    if evidence["subject"]["theory_context_sha256"] != bindings["theory_context"]["sha256"]:
        _fail("cross-link", f"{scenario_id}.evidence", "TheoryContext subject binding drift")
    if evidence["budget"] != {
        "initial_sha256": bindings["resource_budget"]["sha256"],
        "final_sha256": bindings["resource_budget"]["sha256"],
        "outcome": "completed",
    }:
        _fail("budget", f"{scenario_id}.evidence", "Evidence budget binding drift")
    primary = next(
        item
        for item in evidence["payloads"]
        if item["payload_id"] == evidence["primary_payload_id"]
    )
    payload_attachment = attachments.get(primary["payload_id"])
    if payload_attachment is None or (
        payload_attachment["sha256"],
        payload_attachment["byte_count"],
    ) != (primary["sha256"], primary["byte_count"]):
        _fail("payload", scenario_id, "Evidence primary payload bytes are unresolved")
    certificate_status = certificate["verdict"]["status"]
    if certificate_status != expectation["certificate_status"]:
        _fail("outcome", scenario_id, "Certificate verdict drift")
    if certificate_status != "verified" and certificate["verdict"].get("authority") is not None:
        _fail("authority", scenario_id, "non-verified certificate carries authority")
    if expectation["authority"] == "none" and any(
        verdict in {"proved", "refuted", "bounded"} for verdict in verdicts
    ):
        _fail("authority", scenario_id, "non-verified certificate promoted mathematical truth")
    artifact_map = {item["artifact_id"]: item for item in result["artifacts"]}
    for artifact_id, role in (
        ("artifact_primary_evidence", "evidence"),
        ("artifact_certificate", "certificate"),
    ):
        artifact = artifact_map.get(artifact_id)
        if artifact is None or artifact["sha256"] != bindings[role]["sha256"]:
            _fail("cross-link", f"{scenario_id}.engine_result", f"{role} artifact drift")
    for artifact in certificate["verification_artifacts"]:
        attachment = attachments.get(artifact["artifact_id"])
        if attachment is None or (attachment["sha256"], attachment["byte_count"]) != (
            artifact["sha256"],
            artifact["byte_count"],
        ):
            _fail("attachment", scenario_id, "certificate verification bytes unresolved")
    if scenario_id == "replay-mismatch":
        replay = certificate["replay"]
        if (
            replay["observed_payload_sha256"] == replay["expected_payload_sha256"]
            or certificate["verdict"].get("reason_code") != "replay_mismatch"
        ):
            _fail("replay", scenario_id, "replay mismatch was hidden")
    if (
        scenario_id == "invalid-certificate"
        and certificate["verdict"].get("reason_code") != "semantic_failure"
    ):
        _fail("outcome", scenario_id, "semantic certificate invalidity drift")
    if scenario_id == "backend-disagreement":
        backend_ids = result["execution"]["backend_artifact_ids"]
        backend_producers = {artifact_map[item]["producer_component_id"] for item in backend_ids}
        if backend_producers != {producer["component_id"], checker["component_id"]}:
            _fail("disagreement", scenario_id, "backend disagreement lacks independent inputs")


def validate_bundle(root: Path = ROOT) -> dict[str, Any]:
    manifest, manifest_raw = load_json(root / MANIFEST_PATH, canonical=True)
    _validate_manifest_shape(manifest)
    _validate_schema(root, manifest)
    for contract in manifest["contracts"]:
        contract_path = _safe_path(root, contract["path"])
        try:
            contract_raw = contract_path.read_bytes()
        except OSError as exc:
            _fail("contract", contract["path"], str(exc))
        if _sha(contract_raw) != contract["sha256"]:
            _fail("contract", contract["path"], "governing contract byte identity drift")
        if contract_path.suffix == ".json":
            load_json(contract_path, canonical=True)
    report_raw = (root / CONFORMANCE_REPORT_PATH).read_bytes()
    if _sha(report_raw) != manifest["conformance_report_sha256"]:
        _fail("conformance", str(CONFORMANCE_REPORT_PATH), "P2 conformance report drift")
    if bundle_basis_sha256(manifest) != manifest["bundle_sha256"]:
        _fail("bundle-hash", str(MANIFEST_PATH), "bundle basis SHA-256 drift")
    objects = _load_objects(root, manifest)
    schemas = _schema_documents(root)
    for scenario in manifest["scenarios"]:
        _validate_scenario(scenario, objects, schemas)
    expected_manifest, expected_objects = build_bundle(root)
    if manifest != expected_manifest or manifest_raw != canonical_bytes(expected_manifest):
        _fail("regeneration", str(MANIFEST_PATH), "manifest is not byte-identical on replay")
    actual_objects = {
        record["sha256"]: (root / record["path"]).read_bytes() for record in manifest["objects"]
    }
    if actual_objects != expected_objects:
        _fail("regeneration", str(OBJECT_DIR), "object bytes are not byte-identical on replay")
    return {
        "bundle_sha256": manifest["bundle_sha256"],
        "scenario_count": len(manifest["scenarios"]),
        "object_count": len(manifest["objects"]),
        "attachment_count": sum(len(item["attachments"]) for item in manifest["scenarios"]),
        "contract_count": len(manifest["contracts"]),
    }


def write_bundle(root: Path = ROOT) -> dict[str, Any]:
    manifest, objects = build_bundle(root)
    object_dir = root / OBJECT_DIR
    object_dir.mkdir(parents=True, exist_ok=True)
    expected_names = {f"{digest}.json" for digest in objects}
    stale_paths = [
        path
        for path in object_dir.glob("*.json")
        if path.name not in expected_names
        and re.fullmatch(r"[0-9a-f]{64}\.json", path.name) is not None
    ]
    for path in stale_paths:
        path.unlink()
    for digest, raw in objects.items():
        (object_dir / f"{digest}.json").write_bytes(raw)
    (root / MANIFEST_PATH).write_bytes(canonical_bytes(manifest))
    return manifest


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--write", action="store_true", help="write canonical generated fixtures")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = args.root.resolve()
    try:
        if args.write:
            manifest = write_bundle(root)
            print(
                "reference-fixtures: wrote "
                f"{len(manifest['scenarios'])} scenarios, {len(manifest['objects'])} objects"
            )
        report = validate_bundle(root)
    except ReferenceFixtureError as exc:
        print(
            f"reference-fixtures: FAIL [{exc.kind}] {exc.path}: {exc.detail}",
            file=sys.stderr,
        )
        return 1
    print(
        "reference-fixtures: PASS "
        f"(scenarios={report['scenario_count']}, objects={report['object_count']}, "
        f"attachments={report['attachment_count']}, "
        f"bundle={report['bundle_sha256'][:12]})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
