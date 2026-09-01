from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = ROOT / "docs/contracts/schemas"
VALIDATOR_PATH = ROOT / "tools/validate_execution_disposition.py"
CONTRACT_ID = "MH-C-EXECUTION-DISPOSITION-001"
CONTRACT_CANDIDATES = (
    ROOT / "docs/contracts" / f"{CONTRACT_ID}.json",
    ROOT / "docs/contracts/proposed" / f"{CONTRACT_ID}.json",
    ROOT / "docs/contracts" / f"{CONTRACT_ID}.input.json",
)
SCHEMA_NAMES = (
    "cancellation-intent-v1.schema.json",
    "execution-disposition-request-v1.schema.json",
    "execution-disposition-classification-v1.schema.json",
    "execution-disposition-diagnostic-v1.schema.json",
    "execution-disposition-result-v1.schema.json",
)


def _schema(name: str) -> dict[str, object]:
    return json.loads((SCHEMA_DIR / name).read_bytes())


def _contract_path() -> Path:
    for path in CONTRACT_CANDIDATES:
        if path.is_file():
            return path
    raise AssertionError(f"missing contract artifact for {CONTRACT_ID}")


def _literal_assignment(path: Path, name: str) -> object:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if any(isinstance(target, ast.Name) and target.id == name for target in targets):
            return ast.literal_eval(node.value)
    raise AssertionError(f"missing literal assignment {name!r} in {path}")


def _freeze(value: object) -> object:
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, dict):
        return tuple(sorted((key, _freeze(item)) for key, item in value.items()))
    return value


def _values(constraint: dict[str, object]) -> frozenset[object]:
    if "const" in constraint:
        return frozenset({_freeze(constraint["const"])})
    if "enum" in constraint:
        return frozenset(_freeze(value) for value in constraint["enum"])
    raise AssertionError(f"expected const or enum, got {constraint!r}")


def _flat_property_constraints(
    value: dict[str, object], prefix: tuple[str, ...] = ()
) -> dict[tuple[str, ...], frozenset[object]]:
    result: dict[tuple[str, ...], frozenset[object]] = {}
    for name, child in value.get("properties", {}).items():
        path = prefix + (name,)
        if "const" in child or "enum" in child:
            result[path] = _values(child)
        result.update(_flat_property_constraints(child, path))
        if "items" in child:
            result.update(
                _flat_property_constraints(child["items"], path + ("items",))
            )
    return result


def _merge_constraints(
    left: dict[tuple[str, ...], frozenset[object]],
    right: dict[tuple[str, ...], frozenset[object]],
) -> dict[tuple[str, ...], frozenset[object]]:
    result = dict(left)
    for path, values in right.items():
        if path in result:
            values = result[path] & values
            if not values:
                raise AssertionError(f"contradictory schema constraints at {path!r}")
        result[path] = values
    return result


def _constraint_alternatives(
    value: dict[str, object],
) -> list[dict[tuple[str, ...], frozenset[object]]]:
    alternatives = [_flat_property_constraints(value)]
    for child in value.get("allOf", []):
        alternatives = [
            _merge_constraints(left, right)
            for left in alternatives
            for right in _constraint_alternatives(child)
        ]
    if "oneOf" in value:
        choices = [
            choice
            for child in value["oneOf"]
            for choice in _constraint_alternatives(child)
        ]
        alternatives = [
            _merge_constraints(left, right)
            for left in alternatives
            for right in choices
        ]
    return alternatives


def _definition_refs(value: object) -> frozenset[str]:
    result: set[str] = set()
    if isinstance(value, dict):
        reference = value.get("$ref")
        if isinstance(reference, str) and reference.startswith("#/$defs/"):
            result.add(reference.rsplit("/", 1)[-1])
        for child in value.values():
            result.update(_definition_refs(child))
    elif isinstance(value, list):
        for child in value:
            result.update(_definition_refs(child))
    return frozenset(result)


def _named_values(value: object, name: str) -> frozenset[object]:
    result: set[object] = set()
    if isinstance(value, dict):
        properties = value.get("properties")
        if isinstance(properties, dict):
            constraint = properties.get(name)
            if isinstance(constraint, dict) and (
                "const" in constraint or "enum" in constraint
            ):
                result.update(_values(constraint))
        for child in value.values():
            result.update(_named_values(child, name))
    elif isinstance(value, list):
        for child in value:
            result.update(_named_values(child, name))
    return frozenset(result)


def _classification_rows(
    schema: dict[str, object],
) -> set[tuple[str, str, str, int, frozenset[object], int | None, int | None]]:
    rows = set()
    for branch in schema["allOf"][0]["oneOf"]:
        properties = branch["properties"]
        for cause in _values(properties["cause"]):
            rows.add(
                (
                    cause,
                    next(iter(_values(properties["disposition"]))),
                    next(iter(_values(properties["precedence_row"]))),
                    next(iter(_values(properties["precedence_rank"]))),
                    _values(properties["phase"]),
                    properties["resource_dimensions"].get("minItems"),
                    properties["resource_dimensions"].get("maxItems"),
                )
            )
    return rows


class ContractBootstrapTests(unittest.TestCase):
    def test_five_normative_schemas_are_closed(self) -> None:
        for name in SCHEMA_NAMES:
            with self.subTest(schema=name):
                value = _schema(name)
                self.assertEqual(
                    value["$schema"],
                    "https://json-schema.org/draft/2020-12/schema",
                )
                self.assertEqual(value["type"], "object")
                self.assertIs(value["additionalProperties"], False)
                self.assertEqual(set(value["required"]), set(value["properties"]))

    def test_schema_hashes_bind_validator_and_contract_constants(self) -> None:
        validator_hashes = _literal_assignment(VALIDATOR_PATH, "SCHEMAS")
        self.assertEqual(set(validator_hashes), set(SCHEMA_NAMES))
        contract_raw = _contract_path().read_bytes()
        self.assertEqual(
            _literal_assignment(VALIDATOR_PATH, "CONTRACT_SHA256"),
            hashlib.sha256(contract_raw).hexdigest(),
        )
        contract_strings = "\n".join(
            value
            for section in json.loads(_contract_path().read_bytes()).values()
            for value in (
                section
                if isinstance(section, list)
                else section.values()
                if isinstance(section, dict)
                else [section]
            )
            if isinstance(value, str)
        )
        for name in SCHEMA_NAMES:
            raw = (SCHEMA_DIR / name).read_bytes()
            observed = hashlib.sha256(raw).hexdigest()
            expected = validator_hashes[name]
            identity = name.removesuffix(".schema.json")
            contract_hashes = set(
                re.findall(rf"{re.escape(identity)}=([0-9a-f]{{64}})", contract_strings)
            )
            with self.subTest(schema=name):
                self.assertEqual(observed, expected)
                self.assertEqual(contract_hashes, {expected})

    def test_armed_request_requires_a_nonnull_base_budget(self) -> None:
        request = _schema("execution-disposition-request-v1.schema.json")
        branches = request["allOf"][0]["oneOf"]
        by_armed = {
            next(iter(_values(branch["properties"]["cancellation_armed"]))): branch[
                "properties"
            ]
            for branch in branches
        }
        self.assertEqual(set(by_armed), {False, True})
        self.assertEqual(
            set(by_armed[False]), {"cancellation_armed", "cancellation_intent"}
        )
        self.assertEqual(by_armed[False]["cancellation_intent"], {"type": "null"})
        self.assertEqual(
            set(by_armed[True]),
            {
                "base_parent_budget_sha256",
                "cancellation_armed",
                "cancellation_intent",
            },
        )
        self.assertEqual(
            by_armed[True]["base_parent_budget_sha256"],
            {"$ref": "#/$defs/sha256"},
        )
        self.assertEqual(
            by_armed[True]["cancellation_intent"],
            {"$ref": "cancellation-intent-v1.schema.json"},
        )

    def test_classification_matrix_is_exact(self) -> None:
        schema = _schema("execution-disposition-classification-v1.schema.json")
        expected = {
            ("checked_proof", "completed", "30_checked_terminal", 30, frozenset({"completed"}), None, 0),
            ("checked_refutation", "completed", "30_checked_terminal", 30, frozenset({"completed"}), None, 0),
            ("ambiguity", "inconclusive", "20_early_route_planner", 20, frozenset({"routing"}), None, 0),
            ("ambiguity", "inconclusive", "80_semantic_terminal", 80, frozenset({"producer"}), None, 0),
            ("user_cancellation", "cancelled", "40_observed_cancellation", 40, frozenset({"producer", "checker"}), None, 0),
            ("parent_cancellation", "cancelled", "40_observed_cancellation", 40, frozenset({"producer", "checker"}), None, 0),
            ("supervisor_cancellation", "cancelled", "40_observed_cancellation", 40, frozenset({"producer", "checker"}), None, 0),
            ("cancellation_origin_unproven", "cancelled", "40_observed_cancellation", 40, frozenset({"producer", "checker"}), None, 0),
            ("budget_exhaustion", "exhausted", "20_early_route_planner", 20, frozenset({"routing", "planning"}), None, 0),
            ("budget_exhaustion", "exhausted", "50_ledger_exhaustion", 50, frozenset({"producer", "checker"}), 1, None),
            ("unsupported_input", "refused", "20_early_route_planner", 20, frozenset({"routing"}), None, 0),
            ("unsupported_execution_environment", "refused", "20_early_route_planner", 20, frozenset({"routing"}), None, 0),
            ("unsupported_execution_environment", "refused", "60_environment_refusal", 60, frozenset({"producer", "checker"}), None, 0),
            ("producer_refusal", "refused", "70_component_refusal", 70, frozenset({"producer"}), None, 0),
            ("verifier_refusal", "refused", "70_component_refusal", 70, frozenset({"checker"}), None, 0),
            ("truncation", "inconclusive", "80_semantic_terminal", 80, frozenset({"producer", "checker"}), None, 0),
            ("inconclusive_execution", "inconclusive", "80_semantic_terminal", 80, frozenset({"checker"}), None, 0),
            ("checker_disagreement", "inconclusive", "80_semantic_terminal", 80, frozenset({"checker"}), None, 0),
            ("invalid_evidence", "inconclusive", "80_semantic_terminal", 80, frozenset({"producer", "checker"}), None, 0),
            ("producer_failure", "failed", "90_phase_failure", 90, frozenset({"producer"}), None, 0),
            ("verifier_failure", "failed", "90_phase_failure", 90, frozenset({"checker"}), None, 0),
            ("invalid_request", "invalid", "10_prelaunch_invalid", 10, frozenset({"request", "routing", "planning", "coordinator"}), None, 0),
            ("internal_error", "failed", "00_internal_invariant", 0, frozenset({"cleanup", "audit", "replay", "coordinator"}), None, 0),
        }
        self.assertEqual(_classification_rows(schema), expected)
        self.assertEqual(
            set(schema["properties"]["cause"]["enum"]),
            {row[0] for row in expected},
        )

        cancellation_origins = {
            "user_cancellation": "user",
            "parent_cancellation": "parent",
            "supervisor_cancellation": "supervisor",
            "cancellation_origin_unproven": None,
        }
        observed_origins = {}
        for branch in schema["allOf"][0]["oneOf"]:
            properties = branch["properties"]
            causes = _values(properties["cause"])
            if len(causes) != 1 or next(iter(causes)) not in cancellation_origins:
                continue
            cause = next(iter(causes))
            origin = properties["origin_source"]
            observed_origins[cause] = origin.get("const")
            if cause == "cancellation_origin_unproven":
                self.assertEqual(origin, {"type": "null"})
            self.assertEqual(properties["observer_source"], {"const": "supervisor"})
            self.assertEqual(properties["observer_cancellation_id"], {"type": "null"})
            self.assertEqual(
                properties["observer_basis"],
                {"const": "replayed_worker_status_plus_accepted_contract"},
            )
        self.assertEqual(observed_origins, cancellation_origins)

        cancellation_guard = schema["allOf"][1]
        self.assertEqual(
            set(cancellation_guard["if"]["properties"]["cause"]["enum"]),
            set(cancellation_origins),
        )
        self.assertEqual(
            cancellation_guard["else"]["properties"],
            {
                "origin_source": {"type": "null"},
                "observer_source": {"type": "null"},
                "observer_cancellation_id": {"type": "null"},
                "observer_basis": {"type": "null"},
            },
        )

    def test_diagnostic_code_phase_matrix_is_exact(self) -> None:
        schema = _schema("execution-disposition-diagnostic-v1.schema.json")
        expected = {
            "REQUEST_INVALID": ("request",),
            "INTENT_EVENT_MISMATCH": ("request",),
            "RESERVED_EXTENSION_COLLISION": ("coordinator",),
            "ROUTE_INPUT_INVALID": ("routing",),
            "PLANNING_INPUT_INVALID": ("planning",),
            "BINDING_INPUT_INVALID": ("request", "planning"),
            "ARTIFACT_INPUT_INVALID": ("request", "planning"),
            "EXECUTION_INPUT_INVALID": ("coordinator",),
            "BUDGET_ANCHOR_INVALID": ("coordinator",),
            "PORTFOLIO_REQUEST_INVALID": ("coordinator",),
            "AUDITED_EXECUTION_INVALID": ("audit",),
            "AUDIT_REPLAY_INVALID": ("replay",),
            "AUDIT_REPLAY_EXHAUSTED": ("replay",),
            "AUDIT_RELATION_INVALID": ("audit",),
            "CLEANUP_INVARIANT": ("cleanup",),
            "SUPERVISOR_INVARIANT": ("coordinator",),
            "WORKER_REQUEST_INVARIANT": ("coordinator",),
            "WORKER_PLAN_INVARIANT": ("coordinator",),
            "WORKER_STRATEGY_INVARIANT": ("coordinator",),
            "WORKER_BUDGET_INVARIANT": ("coordinator",),
            "WORKER_EXECUTABLE_INVARIANT": ("coordinator",),
            "PORTFOLIO_INPUT_INVARIANT": ("coordinator",),
            "PORTFOLIO_EXECUTION_INVARIANT": ("coordinator",),
            "COORDINATOR_LIMIT_EXHAUSTED": ("coordinator",),
        }
        self.assertEqual(schema["properties"]["severity"], {"const": "error"})
        self.assertEqual(schema["properties"]["subject_sha256"], {"type": "null"})
        self.assertEqual(
            schema["properties"]["related_sha256s"],
            {
                "type": "array",
                "maxItems": 0,
                "items": {"$ref": "#/$defs/sha256"},
            },
        )
        self.assertEqual(
            tuple(schema["properties"]["code"]["enum"]), tuple(expected)
        )

        observed: dict[str, list[str]] = {}
        observed_pairs: set[tuple[str, str]] = set()
        for branch in schema["allOf"][0]["oneOf"]:
            properties = branch["properties"]
            code = next(iter(_values(properties["code"])))
            phase = next(iter(_values(properties["phase"])))
            pair = (code, phase)
            self.assertNotIn(pair, observed_pairs)
            observed_pairs.add(pair)
            observed.setdefault(code, []).append(phase)

            diagnostic_id = f"execution_disposition.{phase}.{code.lower()}"
            preimage = {
                "schema": "mathhead.execution-disposition-diagnostic.v1",
                "diagnostic_id": diagnostic_id,
                "severity": "error",
                "code": code,
                "phase": phase,
                "subject_sha256": None,
                "related_sha256s": [],
                "diagnostic_sha256": None,
                "mathematical_authority": False,
            }
            canonical = (
                json.dumps(
                    preimage,
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=True,
                )
                + "\n"
            ).encode("ascii")
            self.assertEqual(properties["diagnostic_id"], {"const": diagnostic_id})
            self.assertEqual(
                properties["diagnostic_sha256"],
                {"const": hashlib.sha256(canonical).hexdigest()},
            )
        self.assertEqual(
            {code: tuple(phases) for code, phases in observed.items()}, expected
        )

    def test_result_variants_and_reason_ownership_are_exact(self) -> None:
        classification = _schema(
            "execution-disposition-classification-v1.schema.json"
        )
        result = _schema("execution-disposition-result-v1.schema.json")
        class_rows = _classification_rows(classification)
        terminal_branches = result["allOf"][4]["oneOf"]
        normal_branches = terminal_branches[:-2]

        observed = set()
        for branch in normal_branches:
            variant = branch["allOf"][0]["$ref"].removeprefix("#/$defs/")
            for constraints in _constraint_alternatives(branch["allOf"][1]):
                causes = constraints[("classification", "cause")]
                row_filter = constraints.get(("classification", "precedence_row"))
                phase_filter = constraints.get(("classification", "phase"))
                for cause in causes:
                    matching_rows = [row for row in class_rows if row[0] == cause]
                    for class_row in matching_rows:
                        precedence = class_row[2]
                        phases = class_row[4]
                        if row_filter is not None and precedence not in row_filter:
                            continue
                        if phase_filter is not None:
                            phases &= phase_filter
                            if not phases:
                                continue
                        observed.add(
                            (
                                variant,
                                cause,
                                precedence,
                                phases,
                                constraints.get(("route_status",)),
                                constraints.get(("route_reason_code",)),
                                constraints.get(("planning_status",)),
                                constraints.get(("planning_reason_code",)),
                                constraints.get(("portfolio_status",)),
                                constraints.get(("portfolio_reason_code",)),
                                constraints.get(
                                    ("classification", "resource_dimensions")
                                ),
                            )
                        )

        def one(value: str) -> frozenset[str]:
            return frozenset({value})
        none = None

        def row(
            variant: str,
            cause: str,
            precedence: str,
            phases: set[str],
            *,
            route_status: frozenset[object] | None = none,
            route_reason: frozenset[object] | None = none,
            planning_status: frozenset[object] | None = none,
            planning_reason: frozenset[object] | None = none,
            portfolio_status: frozenset[object] | None = none,
            portfolio_reason: frozenset[object] | None = none,
            dimensions: frozenset[object] | None = none,
        ) -> tuple[object, ...]:
            return (
                variant,
                cause,
                precedence,
                frozenset(phases),
                route_status,
                route_reason,
                planning_status,
                planning_reason,
                portfolio_status,
                portfolio_reason,
                dimensions,
            )

        expected = {
            row("audited_normal_result", "checked_proof", "30_checked_terminal", {"completed"}, portfolio_status=one("succeeded"), portfolio_reason=one("CHECKED_PROOF")),
            row("audited_normal_result", "checked_refutation", "30_checked_terminal", {"completed"}, portfolio_status=one("succeeded"), portfolio_reason=one("CHECKED_REFUTATION")),
            row("early_normal_result", "ambiguity", "20_early_route_planner", {"routing"}, route_status=one("ambiguous"), route_reason=frozenset({"NON_UNIQUE_SELECTION", "READING_AMBIGUOUS"}), planning_status=one("ambiguous"), planning_reason=one("ROUTE_AMBIGUOUS")),
            row("audited_normal_result", "ambiguity", "80_semantic_terminal", {"producer"}, portfolio_status=one("ambiguous"), portfolio_reason=one("EVIDENCE_INCOMPLETE")),
            row("early_normal_result", "budget_exhaustion", "20_early_route_planner", {"routing"}, route_status=one("exhausted"), route_reason=one("BUDGET_EXHAUSTED"), planning_status=one("exhausted"), planning_reason=one("ROUTE_EXHAUSTED")),
            row("early_normal_result", "budget_exhaustion", "20_early_route_planner", {"planning"}, route_status=one("routed"), route_reason=one("ROUTED"), planning_status=one("exhausted"), planning_reason=one("PLANNING_EXHAUSTED")),
            row("early_normal_result", "unsupported_input", "20_early_route_planner", {"routing"}, route_status=one("unsupported"), route_reason=one("NO_COMPATIBLE_CAPABILITY"), planning_status=one("unsupported"), planning_reason=one("ROUTE_UNSUPPORTED")),
            row("early_normal_result", "unsupported_execution_environment", "20_early_route_planner", {"routing"}, route_status=one("unsupported"), route_reason=one("NO_COMPATIBLE_CAPABILITY"), planning_status=one("unsupported"), planning_reason=one("ROUTE_UNSUPPORTED")),
            row("audited_normal_result", "unsupported_execution_environment", "60_environment_refusal", {"producer"}, portfolio_status=one("unsupported"), portfolio_reason=one("ISOLATION_UNSUPPORTED")),
            row("audited_normal_result", "unsupported_execution_environment", "60_environment_refusal", {"checker"}, portfolio_status=one("inconclusive"), portfolio_reason=one("ISOLATION_UNSUPPORTED")),
            row("audited_normal_result", "truncation", "80_semantic_terminal", {"producer"}, portfolio_status=one("truncated"), portfolio_reason=one("EVIDENCE_TRUNCATED")),
            row("audited_normal_result", "truncation", "80_semantic_terminal", {"checker"}, portfolio_status=one("truncated"), portfolio_reason=one("CHECKER_TRUNCATED")),
            row("audited_normal_result", "inconclusive_execution", "80_semantic_terminal", {"checker"}, portfolio_status=one("inconclusive"), portfolio_reason=one("CHECKER_INCONCLUSIVE")),
            row("audited_normal_result", "checker_disagreement", "80_semantic_terminal", {"checker"}, portfolio_status=one("disagreement"), portfolio_reason=frozenset({"CHECKER_REJECTED", "CHECKER_DISAGREED"})),
            row("audited_normal_result", "invalid_evidence", "80_semantic_terminal", {"producer"}, portfolio_status=one("invalid_evidence"), portfolio_reason=frozenset({"EVIDENCE_INVALID", "EVIDENCE_PROTOCOL_LIMIT"})),
            row("audited_normal_result", "invalid_evidence", "80_semantic_terminal", {"checker"}, portfolio_status=one("invalid_evidence"), portfolio_reason=one("CERTIFICATE_INVALID")),
            row("audited_normal_result", "producer_failure", "90_phase_failure", {"producer"}, portfolio_status=one("failed"), portfolio_reason=frozenset({"LAUNCH_FAILED", "EXIT_FAILED", "PROTOCOL_FAILED", "EVIDENCE_ERROR"})),
            row("audited_normal_result", "verifier_failure", "90_phase_failure", {"checker"}, portfolio_status=one("verifier_failed"), portfolio_reason=frozenset({"LAUNCH_FAILED", "EXIT_FAILED", "PROTOCOL_FAILED", "CERTIFICATE_INVALID"})),
        }
        for cause in (
            "user_cancellation",
            "parent_cancellation",
            "supervisor_cancellation",
        ):
            expected.add(
                row(
                    "audited_normal_result",
                    cause,
                    "40_observed_cancellation",
                    {"producer", "checker"},
                    portfolio_status=one("cancelled"),
                    portfolio_reason=one("CANCELLED"),
                )
            )
        for reason, dimensions in (
            ("BUDGET_INSUFFICIENT", none),
            ("WALL_TIME_EXHAUSTED", one(("wall_time_us",))),
            ("CPU_TIME_EXHAUSTED", one(("cpu_time_us",))),
            ("MEMORY_EXHAUSTED", one(("memory_bytes",))),
            ("OUTPUT_EXHAUSTED", one(("output_bytes",))),
            ("DIAGNOSTIC_EXHAUSTED", one(("diagnostic_bytes",))),
        ):
            expected.add(
                row(
                    "audited_normal_result",
                    "budget_exhaustion",
                    "50_ledger_exhaustion",
                    {"producer", "checker"},
                    portfolio_status=one("exhausted"),
                    portfolio_reason=one(reason),
                    dimensions=dimensions,
                )
            )
        for status, reason in (
            ("unsupported", "EVIDENCE_UNSUPPORTED"),
            ("exhausted", "EVIDENCE_EXHAUSTED"),
            ("cancelled", "EVIDENCE_CANCELLED"),
            ("failed", "EXECUTABLE_INVALID"),
        ):
            expected.add(
                row(
                    "audited_normal_result",
                    "producer_refusal",
                    "70_component_refusal",
                    {"producer"},
                    portfolio_status=one(status),
                    portfolio_reason=one(reason),
                )
            )
        for status, reason in (
            ("inconclusive", "CHECKER_INCONCLUSIVE"),
            ("exhausted", "CHECKER_EXHAUSTED"),
            ("cancelled", "CHECKER_CANCELLED"),
            ("verifier_failed", "EXECUTABLE_INVALID"),
        ):
            expected.add(
                row(
                    "audited_normal_result",
                    "verifier_refusal",
                    "70_component_refusal",
                    {"checker"},
                    portfolio_status=one(status),
                    portfolio_reason=one(reason),
                )
            )
        self.assertEqual(observed, expected)

        variants = {
            branch["properties"]["execution_state"]["const"]: branch["properties"]
            for branch in result["allOf"][0]["oneOf"]
        }
        self.assertEqual(
            set(variants),
            {
                "not_started",
                "attempted_no_bundle",
                "bundle_replay_failed",
                "replayed_complete",
            },
        )
        sha = {"$ref": "#/$defs/sha256"}
        null = {"type": "null"}
        started = {
            "disposition_request_sha256": sha,
            "invocation_sha256": sha,
            "anchored_parent_budget_sha256": sha,
            "base_parent_budget_sha256": sha,
            "planning_result_sha256": sha,
            "portfolio_request_sha256": sha,
            "route_status": {"const": "routed"},
            "route_reason_code": {"const": "ROUTED"},
            "planning_status": {"const": "planned"},
            "planning_reason_code": {"const": "PLANNED"},
        }
        no_report = {
            "logical_report_sha256": null,
            "portfolio_result_sha256": null,
            "execution_provenance_sha256": null,
            "portfolio_status": null,
            "portfolio_reason_code": null,
        }
        self.assertEqual(
            variants["not_started"],
            {
                "execution_state": {"const": "not_started"},
                "portfolio_relation": {"const": "not_available"},
                "audit_manifest_sha256": null,
                "logical_report_sha256": null,
                "replay_result_sha256": null,
                "portfolio_result_sha256": null,
                "execution_provenance_sha256": null,
                "portfolio_status": null,
                "portfolio_reason_code": null,
                "replay_status": null,
                "replay_reason_code": null,
            },
        )
        self.assertEqual(
            variants["attempted_no_bundle"],
            {
                "execution_state": {"const": "attempted_no_bundle"},
                "portfolio_relation": {"const": "not_available"},
                **started,
                "audit_manifest_sha256": null,
                **no_report,
                "replay_result_sha256": null,
                "replay_status": null,
                "replay_reason_code": null,
            },
        )
        self.assertEqual(
            variants["bundle_replay_failed"],
            {
                "execution_state": {"const": "bundle_replay_failed"},
                "portfolio_relation": {"const": "not_available"},
                **started,
                "audit_manifest_sha256": sha,
                **no_report,
                "replay_result_sha256": sha,
                "replay_status": {"enum": ["invalid", "exhausted"]},
                "replay_reason_code": {"$ref": "#/$defs/reason"},
            },
        )
        self.assertEqual(
            variants["replayed_complete"],
            {
                "execution_state": {"const": "replayed_complete"},
                "portfolio_relation": {"enum": ["exact", "invalid"]},
                **started,
                "audit_manifest_sha256": sha,
                "logical_report_sha256": sha,
                "replay_result_sha256": sha,
                "portfolio_result_sha256": sha,
                "execution_provenance_sha256": sha,
                "portfolio_status": {"not": {"type": "null"}},
                "portfolio_reason_code": {"$ref": "#/$defs/reason"},
                "replay_status": {"const": "complete"},
                "replay_reason_code": {"const": "REPLAY_COMPLETE"},
            },
        )

        replay_failure = next(
            branch
            for branch in result["allOf"][0]["oneOf"]
            if branch["properties"]["execution_state"]
            == {"const": "bundle_replay_failed"}
        )
        self.assertEqual(
            {
                (
                    next(iter(_values(branch["properties"]["replay_status"]))),
                    next(iter(_values(branch["properties"]["replay_reason_code"]))),
                )
                for branch in replay_failure["oneOf"]
            },
            {
                ("invalid", "REPLAY_INVALID"),
                ("exhausted", "REPLAY_BUDGET_EXHAUSTED"),
            },
        )

    def test_portfolio_pair_outcome_and_selection_matrices_are_exact(self) -> None:
        result = _schema("execution-disposition-result-v1.schema.json")
        expected_pairs = {
            "succeeded": frozenset({"CHECKED_PROOF", "CHECKED_REFUTATION"}),
            "unsupported": frozenset(
                {"ISOLATION_UNSUPPORTED", "EVIDENCE_UNSUPPORTED"}
            ),
            "exhausted": frozenset(
                {
                    "BUDGET_INSUFFICIENT",
                    "WALL_TIME_EXHAUSTED",
                    "CPU_TIME_EXHAUSTED",
                    "MEMORY_EXHAUSTED",
                    "OUTPUT_EXHAUSTED",
                    "DIAGNOSTIC_EXHAUSTED",
                    "EVIDENCE_EXHAUSTED",
                    "CHECKER_EXHAUSTED",
                }
            ),
            "cancelled": frozenset(
                {"CANCELLED", "EVIDENCE_CANCELLED", "CHECKER_CANCELLED"}
            ),
            "failed": frozenset(
                {
                    "REQUEST_INVALID",
                    "PLAN_INVALID",
                    "STRATEGY_MISMATCH",
                    "BUDGET_INVALID",
                    "EXECUTABLE_INVALID",
                    "LAUNCH_FAILED",
                    "EXIT_FAILED",
                    "PROTOCOL_FAILED",
                    "TREE_CLEANUP_FAILED",
                    "SUPERVISOR_FAILED",
                    "EVIDENCE_ERROR",
                }
            ),
            "ambiguous": frozenset({"EVIDENCE_INCOMPLETE"}),
            "truncated": frozenset(
                {"EVIDENCE_TRUNCATED", "CHECKER_TRUNCATED"}
            ),
            "inconclusive": frozenset(
                {"ISOLATION_UNSUPPORTED", "CHECKER_INCONCLUSIVE"}
            ),
            "disagreement": frozenset(
                {"CHECKER_REJECTED", "CHECKER_DISAGREED"}
            ),
            "verifier_failed": frozenset(
                {
                    "REQUEST_INVALID",
                    "PLAN_INVALID",
                    "STRATEGY_MISMATCH",
                    "BUDGET_INVALID",
                    "EXECUTABLE_INVALID",
                    "LAUNCH_FAILED",
                    "EXIT_FAILED",
                    "PROTOCOL_FAILED",
                    "TREE_CLEANUP_FAILED",
                    "SUPERVISOR_FAILED",
                    "CERTIFICATE_INVALID",
                }
            ),
            "invalid_evidence": frozenset(
                {
                    "EVIDENCE_INVALID",
                    "EVIDENCE_PROTOCOL_LIMIT",
                    "CERTIFICATE_INVALID",
                }
            ),
            "invalid": frozenset(
                {"PORTFOLIO_INPUT_INVALID", "PORTFOLIO_EXECUTION_INVALID"}
            ),
        }
        observed_pairs: dict[str, frozenset[object]] = {}
        pair_branches = result["$defs"]["portfolio_pair"]["oneOf"]
        for branch in pair_branches:
            properties = branch["properties"]
            statuses = _values(properties["portfolio_status"])
            self.assertEqual(len(statuses), 1)
            status = next(iter(statuses))
            self.assertNotIn(status, observed_pairs)
            observed_pairs[status] = _values(properties["portfolio_reason_code"])
        self.assertEqual(observed_pairs, expected_pairs)
        self.assertEqual(len(pair_branches), 12)
        self.assertEqual(sum(map(len, observed_pairs.values())), 49)

        outcome_gate = result["allOf"][2]["oneOf"]
        self.assertEqual(len(outcome_gate), 4)

        def discriminator(
            properties: dict[str, dict[str, object]],
        ) -> tuple[frozenset[object], ...]:
            return (
                _values(properties["portfolio_relation"]),
                _values(properties["portfolio_status"]),
                _values(properties["portfolio_reason_code"]),
                _values(properties["portfolio_outcome_kind"]),
            )

        self.assertEqual(
            {discriminator(branch["properties"]) for branch in outcome_gate[:3]},
            {
                (
                    frozenset({"exact"}),
                    frozenset({"failed", "verifier_failed"}),
                    frozenset({"LAUNCH_FAILED"}),
                    frozenset({"launch_refused"}),
                ),
                (
                    frozenset({"exact"}),
                    frozenset({"failed", "verifier_failed"}),
                    frozenset({"EXECUTABLE_INVALID"}),
                    frozenset({"executable_refused", "executable_invalid"}),
                ),
                (
                    frozenset({"exact"}),
                    frozenset({"inconclusive"}),
                    frozenset({"CHECKER_INCONCLUSIVE"}),
                    frozenset(
                        {"certificate_unsupported", "certificate_inconclusive"}
                    ),
                ),
            },
        )
        outcome_default = outcome_gate[3]
        self.assertEqual(
            outcome_default["properties"],
            {"portfolio_outcome_kind": {"type": "null"}},
        )
        self.assertEqual(
            {
                (
                    _values(properties["portfolio_relation"]),
                    _values(properties["portfolio_status"]),
                    _values(properties["portfolio_reason_code"]),
                )
                for guard in outcome_default["allOf"]
                for properties in (guard["not"]["properties"],)
            },
            {
                (
                    frozenset({"exact"}),
                    frozenset({"failed", "verifier_failed"}),
                    frozenset({"LAUNCH_FAILED"}),
                ),
                (
                    frozenset({"exact"}),
                    frozenset({"failed", "verifier_failed"}),
                    frozenset({"EXECUTABLE_INVALID"}),
                ),
                (
                    frozenset({"exact"}),
                    frozenset({"inconclusive"}),
                    frozenset({"CHECKER_INCONCLUSIVE"}),
                ),
            },
        )
        self.assertEqual(len(outcome_default["allOf"]), 3)

        sha = {"$ref": "#/$defs/sha256"}
        null = {"type": "null"}
        selected = (
            "selected_strategy_sha256",
            "selected_evidence_sha256",
            "selected_certificate_sha256",
            "selected_checker_decision_sha256",
        )
        selection = result["allOf"][3]
        self.assertEqual(
            selection["if"],
            {
                "properties": {
                    "classification": {
                        "properties": {
                            "cause": {
                                "enum": ["checked_proof", "checked_refutation"]
                            }
                        }
                    }
                }
            },
        )
        self.assertEqual(
            selection["then"]["properties"],
            {
                "execution_state": {"const": "replayed_complete"},
                **{name: sha for name in selected},
                "linked_authority_tier": {
                    "enum": [
                        "checker_attestation",
                        "external_proof_assistant",
                    ]
                },
            },
        )
        self.assertEqual(
            selection["else"]["properties"],
            {
                **{name: null for name in selected},
                "linked_authority_tier": {"const": "none"},
            },
        )
        self.assertEqual(result["properties"]["authority_ceiling"], {"const": "none"})

    def test_result_request_gate_and_prelaunch_milestones_are_exact(self) -> None:
        result = _schema("execution-disposition-result-v1.schema.json")
        sha = {"$ref": "#/$defs/sha256"}
        null = {"type": "null"}
        self.assertIn("cancellation_armed", result["required"])
        self.assertEqual(
            result["properties"]["cancellation_armed"],
            {"oneOf": [null, {"type": "boolean"}]},
        )
        self.assertEqual(
            result["properties"]["diagnostics"],
            {
                "type": "array",
                "maxItems": 1,
                "uniqueItems": True,
                "items": {
                    "$ref": "execution-disposition-diagnostic-v1.schema.json"
                },
            },
        )
        self.assertEqual(
            [branch["properties"] for branch in result["allOf"][1]["oneOf"]],
            [
                {
                    "disposition_request_sha256": null,
                    "invocation_sha256": null,
                    "cancellation_armed": null,
                    "cancellation_intent_sha256": null,
                },
                {
                    "disposition_request_sha256": sha,
                    "invocation_sha256": sha,
                    "cancellation_armed": {"const": False},
                    "cancellation_intent_sha256": null,
                },
                {
                    "disposition_request_sha256": sha,
                    "invocation_sha256": sha,
                    "cancellation_armed": {"const": True},
                    "cancellation_intent_sha256": sha,
                },
            ],
        )

        definitions = result["$defs"]
        self.assertEqual(
            definitions["valid_request_result"]["properties"],
            {
                "disposition_request_sha256": sha,
                "invocation_sha256": sha,
                "cancellation_armed": {"type": "boolean"},
            },
        )
        empty = {
            "disposition_request_sha256": null,
            "invocation_sha256": null,
            "cancellation_armed": null,
            "cancellation_intent_sha256": null,
            "base_parent_budget_sha256": null,
            "anchored_parent_budget_sha256": null,
            "planning_result_sha256": null,
            "portfolio_request_sha256": null,
            "route_status": null,
            "route_reason_code": null,
            "planning_status": null,
            "planning_reason_code": null,
        }
        self.assertEqual(definitions["empty_preflight_result"]["properties"], empty)
        common_null_budget = {
            "base_parent_budget_sha256": null,
            "anchored_parent_budget_sha256": null,
            "portfolio_request_sha256": null,
        }
        planned = {
            "route_status": {"const": "routed"},
            "route_reason_code": {"const": "ROUTED"},
            "planning_status": {"const": "planned"},
            "planning_reason_code": {"const": "PLANNED"},
        }
        expected_profiles = {
            "validated_pre_route_result": {
                **common_null_budget,
                "planning_result_sha256": null,
                "route_status": null,
                "route_reason_code": null,
                "planning_status": null,
                "planning_reason_code": null,
            },
            "invalid_route_result": {
                **common_null_budget,
                "planning_result_sha256": null,
                "route_status": {"const": "invalid"},
                "route_reason_code": {"const": "INVALID_INPUT"},
                "planning_status": null,
                "planning_reason_code": null,
            },
            "invalid_planning_result": {
                **common_null_budget,
                "planning_result_sha256": sha,
                "route_status": {"const": "routed"},
                "route_reason_code": {"const": "ROUTED"},
                "planning_status": {"const": "invalid"},
                "planning_reason_code": {"const": "INVALID_INPUT"},
            },
            "planned_no_budget_result": {
                **common_null_budget,
                "planning_result_sha256": sha,
                **planned,
            },
            "planned_unanchored_result": {
                "base_parent_budget_sha256": sha,
                "anchored_parent_budget_sha256": null,
                "planning_result_sha256": sha,
                "portfolio_request_sha256": null,
                **planned,
            },
            "planned_anchored_result": {
                "base_parent_budget_sha256": sha,
                "anchored_parent_budget_sha256": sha,
                "planning_result_sha256": sha,
                "portfolio_request_sha256": null,
                **planned,
            },
            "planned_portfolio_ready_result": {
                "base_parent_budget_sha256": sha,
                "anchored_parent_budget_sha256": sha,
                "planning_result_sha256": sha,
                "portfolio_request_sha256": sha,
                **planned,
            },
        }
        for name, properties in expected_profiles.items():
            with self.subTest(profile=name):
                self.assertEqual(definitions[name]["properties"], properties)
                self.assertEqual(
                    definitions[name]["allOf"],
                    [{"$ref": "#/$defs/valid_request_result"}],
                )

        invalid = result["allOf"][4]["oneOf"][-2]
        invalid_variants = {
            (
                _definition_refs(branch),
                _named_values(branch, "code"),
                _named_values(branch, "phase"),
            )
            for branch in invalid["oneOf"]
        }
        self.assertEqual(
            invalid_variants,
            {
                (frozenset({"empty_preflight_result"}), frozenset({"REQUEST_INVALID"}), frozenset({"request"})),
                (frozenset({"validated_pre_route_result"}), frozenset({"INTENT_EVENT_MISMATCH", "BINDING_INPUT_INVALID", "ARTIFACT_INPUT_INVALID"}), frozenset({"request"})),
                (frozenset({"validated_pre_route_result"}), frozenset({"ROUTE_INPUT_INVALID"}), frozenset({"routing"})),
                (frozenset({"invalid_route_result"}), frozenset({"ROUTE_INPUT_INVALID"}), frozenset({"routing"})),
                (frozenset({"invalid_planning_result"}), frozenset({"PLANNING_INPUT_INVALID", "ARTIFACT_INPUT_INVALID"}), frozenset({"planning"})),
                (frozenset({"planned_no_budget_result"}), frozenset({"BINDING_INPUT_INVALID"}), frozenset({"planning"})),
                (frozenset({"planned_no_budget_result"}), frozenset({"EXECUTION_INPUT_INVALID"}), frozenset({"coordinator"})),
                (frozenset({"planned_unanchored_result"}), frozenset({"RESERVED_EXTENSION_COLLISION"}), frozenset({"coordinator"})),
            },
        )
        internal = result["allOf"][4]["oneOf"][-1]
        coordinator = next(
            branch
            for branch in internal["oneOf"]
            if _named_values(branch, "phase") == frozenset({"coordinator"})
        )
        by_code = {
            next(iter(codes)): branch
            for branch in coordinator["oneOf"]
            if len(codes := _named_values(branch, "code")) == 1
        }
        self.assertEqual(
            set(by_code),
            {
                "BUDGET_ANCHOR_INVALID",
                "PORTFOLIO_REQUEST_INVALID",
                "SUPERVISOR_INVARIANT",
                "WORKER_REQUEST_INVARIANT",
                "WORKER_PLAN_INVARIANT",
                "WORKER_STRATEGY_INVARIANT",
                "WORKER_BUDGET_INVARIANT",
                "WORKER_EXECUTABLE_INVARIANT",
                "PORTFOLIO_INPUT_INVARIANT",
                "PORTFOLIO_EXECUTION_INVARIANT",
                "COORDINATOR_LIMIT_EXHAUSTED",
            },
        )

        def mapping(branch: dict[str, object]) -> tuple[object, ...]:
            return (
                _definition_refs(branch),
                _named_values(branch, "execution_state"),
                _named_values(branch, "portfolio_relation"),
                _named_values(branch, "portfolio_status"),
                _named_values(branch, "portfolio_reason_code"),
                _named_values(branch, "portfolio_outcome_kind"),
            )

        def values(*items: object) -> frozenset[object]:
            return frozenset(items)

        empty_values = frozenset()
        expected_coordinator = {
            "BUDGET_ANCHOR_INVALID": (
                values("planned_unanchored_result"),
                values("not_started"),
                empty_values,
                empty_values,
                empty_values,
                empty_values,
            ),
            "PORTFOLIO_REQUEST_INVALID": (
                values("planned_anchored_result"),
                values("not_started"),
                empty_values,
                empty_values,
                empty_values,
                empty_values,
            ),
            "COORDINATOR_LIMIT_EXHAUSTED": (
                values("empty_preflight_result"),
                values("not_started"),
                empty_values,
                empty_values,
                empty_values,
                empty_values,
            ),
            "WORKER_REQUEST_INVARIANT": (
                empty_values,
                values("replayed_complete"),
                values("exact"),
                values("failed", "verifier_failed"),
                values("REQUEST_INVALID"),
                empty_values,
            ),
            "WORKER_PLAN_INVARIANT": (
                empty_values,
                values("replayed_complete"),
                values("exact"),
                values("failed", "verifier_failed"),
                values("PLAN_INVALID"),
                empty_values,
            ),
            "WORKER_STRATEGY_INVARIANT": (
                empty_values,
                values("replayed_complete"),
                values("exact"),
                values("failed", "verifier_failed"),
                values("STRATEGY_MISMATCH"),
                empty_values,
            ),
            "WORKER_BUDGET_INVARIANT": (
                empty_values,
                values("replayed_complete"),
                values("exact"),
                values("failed", "verifier_failed"),
                values("BUDGET_INVALID"),
                empty_values,
            ),
            "WORKER_EXECUTABLE_INVARIANT": (
                empty_values,
                values("replayed_complete"),
                values("exact"),
                values("failed", "verifier_failed"),
                values("EXECUTABLE_INVALID"),
                values("executable_invalid"),
            ),
            "SUPERVISOR_INVARIANT": (
                empty_values,
                values("replayed_complete"),
                values("exact"),
                values("failed", "verifier_failed"),
                values("SUPERVISOR_FAILED"),
                empty_values,
            ),
            "PORTFOLIO_INPUT_INVARIANT": (
                empty_values,
                values("replayed_complete"),
                values("exact"),
                values("invalid"),
                values("PORTFOLIO_INPUT_INVALID"),
                empty_values,
            ),
            "PORTFOLIO_EXECUTION_INVARIANT": (
                empty_values,
                values("replayed_complete"),
                values("exact"),
                values("invalid"),
                values("PORTFOLIO_EXECUTION_INVALID"),
                empty_values,
            ),
        }
        self.assertEqual(
            {code: mapping(branch) for code, branch in by_code.items()},
            expected_coordinator,
        )

    def test_result_diagnostics_have_exact_cause_and_phase_ownership(self) -> None:
        diagnostic = _schema("execution-disposition-diagnostic-v1.schema.json")
        result = _schema("execution-disposition-result-v1.schema.json")
        terminal_branches = result["allOf"][4]["oneOf"]
        special = terminal_branches[-2:]
        for index, branch in enumerate(special):
            properties = branch["properties"]
            cause = next(
                iter(_values(properties["classification"]["properties"]["cause"]))
            )
            self.assertEqual(properties["diagnostics"]["minItems"], 1)
            self.assertEqual(
                properties["diagnostics"].get(
                    "maxItems", result["properties"]["diagnostics"]["maxItems"]
                ),
                1,
            )
            if index == 1:
                self.assertEqual(
                    properties["diagnostics"], {"minItems": 1, "maxItems": 1}
                )
            if cause == "invalid_request":
                self.assertEqual(properties["execution_state"], {"const": "not_started"})

        expected = {
            "REQUEST_INVALID": {("invalid_request", "request", "not_started", None)},
            "INTENT_EVENT_MISMATCH": {("invalid_request", "request", "not_started", None)},
            "RESERVED_EXTENSION_COLLISION": {("invalid_request", "coordinator", "not_started", None)},
            "ROUTE_INPUT_INVALID": {("invalid_request", "routing", "not_started", None)},
            "PLANNING_INPUT_INVALID": {("invalid_request", "planning", "not_started", None)},
            "BINDING_INPUT_INVALID": {
                ("invalid_request", "request", "not_started", None),
                ("invalid_request", "planning", "not_started", None),
            },
            "ARTIFACT_INPUT_INVALID": {
                ("invalid_request", "request", "not_started", None),
                ("invalid_request", "planning", "not_started", None),
            },
            "EXECUTION_INPUT_INVALID": {("invalid_request", "coordinator", "not_started", None)},
            "BUDGET_ANCHOR_INVALID": {("internal_error", "coordinator", "not_started", None)},
            "PORTFOLIO_REQUEST_INVALID": {("internal_error", "coordinator", "not_started", None)},
            "AUDITED_EXECUTION_INVALID": {("internal_error", "audit", "attempted_no_bundle", None)},
            "AUDIT_REPLAY_INVALID": {("internal_error", "replay", "bundle_replay_failed", "invalid")},
            "AUDIT_REPLAY_EXHAUSTED": {("internal_error", "replay", "bundle_replay_failed", "exhausted")},
            "AUDIT_RELATION_INVALID": {
                ("internal_error", "audit", "replayed_complete", None),
            },
            "CLEANUP_INVARIANT": {("internal_error", "cleanup", "replayed_complete", None)},
            "SUPERVISOR_INVARIANT": {
                ("internal_error", "coordinator", "replayed_complete", None),
            },
            "WORKER_REQUEST_INVARIANT": {
                ("internal_error", "coordinator", "replayed_complete", None)
            },
            "WORKER_PLAN_INVARIANT": {
                ("internal_error", "coordinator", "replayed_complete", None)
            },
            "WORKER_STRATEGY_INVARIANT": {
                ("internal_error", "coordinator", "replayed_complete", None)
            },
            "WORKER_BUDGET_INVARIANT": {
                ("internal_error", "coordinator", "replayed_complete", None)
            },
            "WORKER_EXECUTABLE_INVARIANT": {
                ("internal_error", "coordinator", "replayed_complete", None)
            },
            "PORTFOLIO_INPUT_INVARIANT": {
                ("internal_error", "coordinator", "replayed_complete", None)
            },
            "PORTFOLIO_EXECUTION_INVARIANT": {
                ("internal_error", "coordinator", "replayed_complete", None)
            },
            "COORDINATOR_LIMIT_EXHAUSTED": {
                ("internal_error", "coordinator", "not_started", None)
            },
        }
        observed: dict[str, set[tuple[str, str, str | None, str | None]]] = {}
        for branch in special:
            for constraints in _constraint_alternatives(branch):
                cause = next(iter(constraints[("classification", "cause")]))
                phase = next(iter(constraints[("classification", "phase")]))
                diagnostic_phase = next(
                    iter(constraints[("diagnostics", "items", "phase")])
                )
                self.assertEqual(diagnostic_phase, phase)
                execution_states = constraints.get(("execution_state",))
                replay_statuses = constraints.get(("replay_status",))
                execution_state = (
                    next(iter(execution_states)) if execution_states is not None else None
                )
                replay_status = (
                    next(iter(replay_statuses)) if replay_statuses is not None else None
                )
                codes = constraints[("diagnostics", "items", "code")]
                for code in codes:
                    observed.setdefault(code, set()).add(
                        (cause, phase, execution_state, replay_status)
                    )
        self.assertEqual(observed, expected)
        self.assertEqual(
            set(observed), set(diagnostic["properties"]["code"]["enum"])
        )

        internal = special[1]
        internal_by_phase = {
            next(
                iter(
                    _values(
                        branch["properties"]["classification"]["properties"][
                            "phase"
                        ]
                    )
                )
            ): branch
            for branch in internal["oneOf"]
        }
        self.assertEqual(
            set(internal_by_phase), {"cleanup", "audit", "replay", "coordinator"}
        )

        cleanup = internal_by_phase["cleanup"]
        self.assertEqual(
            (
                _named_values(cleanup, "execution_state"),
                _named_values(cleanup, "portfolio_relation"),
                _named_values(cleanup, "portfolio_status"),
                _named_values(cleanup, "portfolio_reason_code"),
                _named_values(cleanup, "code"),
            ),
            (
                frozenset({"replayed_complete"}),
                frozenset({"exact"}),
                frozenset({"failed", "verifier_failed"}),
                frozenset({"TREE_CLEANUP_FAILED"}),
                frozenset({"CLEANUP_INVARIANT"}),
            ),
        )

        audit = internal_by_phase["audit"]
        self.assertEqual(
            _values(audit["properties"]["execution_state"]),
            frozenset({"attempted_no_bundle", "replayed_complete"}),
        )
        audit_by_code = {
            next(iter(codes)): branch
            for branch in audit["oneOf"]
            if len(codes := _named_values(branch, "code")) == 1
        }
        self.assertEqual(set(audit_by_code), {"AUDITED_EXECUTION_INVALID", "AUDIT_RELATION_INVALID"})
        self.assertEqual(
            (
                _definition_refs(audit_by_code["AUDITED_EXECUTION_INVALID"]),
                _named_values(
                    audit_by_code["AUDITED_EXECUTION_INVALID"], "execution_state"
                ),
                _named_values(
                    audit_by_code["AUDITED_EXECUTION_INVALID"],
                    "portfolio_relation",
                ),
            ),
            (
                frozenset(),
                frozenset({"attempted_no_bundle"}),
                frozenset({"not_available"}),
            ),
        )
        self.assertEqual(
            (
                _definition_refs(audit_by_code["AUDIT_RELATION_INVALID"]),
                _named_values(
                    audit_by_code["AUDIT_RELATION_INVALID"], "execution_state"
                ),
                _named_values(
                    audit_by_code["AUDIT_RELATION_INVALID"], "portfolio_relation"
                ),
            ),
            (
                frozenset({"portfolio_pair"}),
                frozenset({"replayed_complete"}),
                frozenset({"invalid"}),
            ),
        )

        replay = internal_by_phase["replay"]
        self.assertEqual(
            (
                _values(replay["properties"]["execution_state"]),
                _values(replay["properties"]["portfolio_relation"]),
            ),
            (
                frozenset({"bundle_replay_failed"}),
                frozenset({"not_available"}),
            ),
        )
        self.assertEqual(
            {
                (
                    next(iter(_named_values(branch, "code"))),
                    next(iter(_named_values(branch, "execution_state"))),
                    next(iter(_named_values(branch, "replay_status"))),
                )
                for branch in replay["oneOf"]
            },
            {
                (
                    "AUDIT_REPLAY_INVALID",
                    "bundle_replay_failed",
                    "invalid",
                ),
                (
                    "AUDIT_REPLAY_EXHAUSTED",
                    "bundle_replay_failed",
                    "exhausted",
                ),
            },
        )
        self.assertEqual(
            result["$defs"]["early_normal_result"]["properties"]["diagnostics"],
            {"maxItems": 0},
        )
        self.assertEqual(
            result["$defs"]["audited_normal_result"]["properties"][
                "diagnostics"
            ],
            {"maxItems": 0},
        )

    def test_cancellation_origin_unproven_is_standalone_only(self) -> None:
        classification = _schema(
            "execution-disposition-classification-v1.schema.json"
        )
        result = _schema("execution-disposition-result-v1.schema.json")
        result_text = json.dumps(result, sort_keys=True)
        self.assertIn(
            "cancellation_origin_unproven",
            classification["properties"]["cause"]["enum"],
        )
        self.assertNotIn("cancellation_origin_unproven", result_text)

        result_causes = set()
        for branch in result["allOf"][4]["oneOf"]:
            for constraints in _constraint_alternatives(branch):
                result_causes.update(
                    constraints.get(("classification", "cause"), frozenset())
                )
        catalogue = set(classification["properties"]["cause"]["enum"])
        self.assertEqual(catalogue - result_causes, {"cancellation_origin_unproven"})
        contract_text = _contract_path().read_text(encoding="utf-8")
        self.assertIn(
            "cancellation_origin_unproven is a reserved closed catalogue member "
            "that the strict v1 coordinator validates but cannot emit",
            contract_text,
        )

    def test_budget_anchor_vector_changes_only_the_reserved_extension(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "_execution_disposition_bootstrap_validator", VALIDATOR_PATH
        )
        if spec is None or spec.loader is None:
            self.fail("could not load execution-disposition bootstrap validator")
        validator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(validator)

        self.assertEqual(
            validator.RESERVED_EXTENSION, "org.mathhead.execution-disposition"
        )
        base = validator._base_budget()
        base_mapping = json.loads(base)
        self.assertNotIn(
            validator.RESERVED_EXTENSION, base_mapping["extensions"]
        )
        request_sha256 = "a" * 64
        anchored_mapping = json.loads(base)
        anchored_mapping["extensions"][validator.RESERVED_EXTENSION] = {
            "disposition_request_sha256": request_sha256
        }
        anchored = validator._canonical(anchored_mapping)
        report = validator._anchor_check()
        self.assertEqual(
            report["base_parent_budget_sha256"], hashlib.sha256(base).hexdigest()
        )
        self.assertEqual(
            report["anchored_parent_budget_sha256"],
            hashlib.sha256(anchored).hexdigest(),
        )
        self.assertEqual(report["disposition_request_sha256"], request_sha256)
        self.assertEqual(
            {
                key
                for key in base_mapping
                if base_mapping[key] != anchored_mapping[key]
            },
            {"extensions"},
        )
        self.assertEqual(
            anchored_mapping["budget_id"], base_mapping["budget_id"]
        )
        stripped = json.loads(anchored)
        del stripped["extensions"][validator.RESERVED_EXTENSION]
        self.assertEqual(validator._canonical(stripped), base)
        self.assertEqual(
            stripped["extensions"], {"org.mathhead.fixture": {"preserved": True}}
        )
        self.assertEqual(
            json.loads(_contract_path().read_bytes())["determinism"]["anchor"],
            "the only base-to-anchored budget change is insertion of "
            "extensions.org.mathhead.execution-disposition."
            "disposition_request_sha256 equal to the complete request identity; "
            "deleting only that member and canonicalizing must reproduce the exact "
            "base bytes",
        )

    def test_result_request_projection_rejects_forged_identities(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "_execution_disposition_bootstrap_validator", VALIDATOR_PATH
        )
        if spec is None or spec.loader is None:
            self.fail("could not load execution-disposition bootstrap validator")
        validator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(validator)
        self.assertEqual(
            validator.RESULT_FIELDS,
            frozenset(
                _schema("execution-disposition-result-v1.schema.json")["required"]
            ),
        )
        digest_a = "a" * 64
        digest_b = "b" * 64
        artifact_bindings = [
            {"role": "problem", "sha256": digest_b, "byte_count": 7}
        ]
        invocation_projection = {
            "schema": "mathhead.execution-disposition-invocation.v1",
            "invocation_id": "invocation_fixture",
            "planning_request_sha256": digest_a,
            "route_result_sha256": digest_b,
            "planning_result_sha256": "c" * 64,
            "base_parent_budget_sha256": "d" * 64,
            "descriptor_sha256s": [digest_a],
            "binding_sha256s": [digest_b],
            "artifact_bindings": artifact_bindings,
            "cancellation_armed": True,
            "mathematical_authority": False,
        }
        invocation_sha256 = hashlib.sha256(
            validator._canonical(invocation_projection)
        ).hexdigest()
        intent = {
            "schema": "mathhead.cancellation-intent.v1",
            "intent_id": "intent_fixture",
            "origin_source": "user",
            "reason_code": "requested",
            "invocation_id": "invocation_fixture",
            "invocation_sha256": invocation_sha256,
            "base_parent_budget_sha256": "d" * 64,
            "policy_contract_id": CONTRACT_ID,
            "policy_contract_sha256": validator.CONTRACT_SHA256,
            "intent_sha256": None,
            "mathematical_authority": False,
        }
        intent_sha256 = hashlib.sha256(validator._canonical(intent)).hexdigest()
        intent["intent_sha256"] = intent_sha256
        request = {
            "schema": "mathhead.execution-disposition-request.v1",
            "contract_id": CONTRACT_ID,
            "contract_sha256": validator.CONTRACT_SHA256,
            "invocation_id": "invocation_fixture",
            "planning_request_sha256": digest_a,
            "route_result_sha256": digest_b,
            "planning_result_sha256": "c" * 64,
            "base_parent_budget_sha256": "d" * 64,
            "descriptor_sha256s": [digest_a],
            "binding_sha256s": [digest_b],
            "artifact_bindings": artifact_bindings,
            "cancellation_armed": True,
            "cancellation_intent": intent,
            "invocation_sha256": invocation_sha256,
            "request_sha256": None,
            "mathematical_authority": False,
        }
        request_sha256 = hashlib.sha256(validator._canonical(request)).hexdigest()
        request["request_sha256"] = request_sha256
        result = {
            "disposition_request_sha256": request_sha256,
            "invocation_sha256": invocation_sha256,
            "cancellation_armed": True,
            "cancellation_intent_sha256": intent_sha256,
        }
        validator._validate_result_request_projection(request, result)
        request_input = validator._canonical(request)
        full_result = {name: None for name in validator.RESULT_FIELDS}
        full_result.update(
            {
                "schema": "mathhead.execution-disposition-result.v1",
                "contract_id": CONTRACT_ID,
                "contract_sha256": validator.CONTRACT_SHA256,
                "request_input_sha256": hashlib.sha256(request_input).hexdigest(),
                **result,
                "diagnostics": [],
                "authority_ceiling": "none",
                "result_sha256": None,
                "mathematical_authority": False,
            }
        )
        full_result["result_sha256"] = hashlib.sha256(
            validator._canonical(full_result)
        ).hexdigest()
        validator._validate_result_request_projection(
            request, full_result, request_input=request_input
        )
        for field, replacement in (
            ("contract_sha256", "f" * 64),
            ("request_input_sha256", "f" * 64),
        ):
            with self.subTest(full_result_forgery=field):
                forged_full_result = dict(full_result)
                forged_full_result[field] = replacement
                forged_full_result["result_sha256"] = None
                forged_full_result["result_sha256"] = hashlib.sha256(
                    validator._canonical(forged_full_result)
                ).hexdigest()
                with self.assertRaises(
                    validator.ExecutionDispositionValidationFailure
                ):
                    validator._validate_result_request_projection(
                        request,
                        forged_full_result,
                        request_input=request_input,
                    )
        with self.subTest(full_result_forgery="result_sha256"):
            forged_full_result = dict(full_result)
            forged_full_result["result_sha256"] = "f" * 64
            with self.assertRaises(
                validator.ExecutionDispositionValidationFailure
            ):
                validator._validate_result_request_projection(
                    request, forged_full_result, request_input=request_input
                )
        with self.subTest(full_result_forgery="raw request bytes"):
            with self.assertRaises(
                validator.ExecutionDispositionValidationFailure
            ):
                validator._validate_result_request_projection(
                    request, full_result, request_input=b"{}\n"
                )
        transplanted_request_input = b"{}\n"
        transplanted_full_result = dict(full_result)
        transplanted_full_result["request_input_sha256"] = hashlib.sha256(
            transplanted_request_input
        ).hexdigest()
        transplanted_full_result["result_sha256"] = None
        transplanted_full_result["result_sha256"] = hashlib.sha256(
            validator._canonical(transplanted_full_result)
        ).hexdigest()
        with self.subTest(full_result_forgery="rehashed raw request transplant"):
            with self.assertRaisesRegex(
                validator.ExecutionDispositionValidationFailure,
                "retained request differs from the exact raw request bytes",
            ):
                validator._validate_result_request_projection(
                    request,
                    transplanted_full_result,
                    request_input=transplanted_request_input,
                )
        invalid_request_input = b'{"malformed":\n'
        invalid_full_result = {
            name: None for name in validator.RESULT_FIELDS
        }
        invalid_full_result.update(
            {
                "schema": "mathhead.execution-disposition-result.v1",
                "contract_id": CONTRACT_ID,
                "contract_sha256": validator.CONTRACT_SHA256,
                "request_input_sha256": hashlib.sha256(
                    invalid_request_input
                ).hexdigest(),
                "diagnostics": [],
                "authority_ceiling": "none",
                "result_sha256": None,
                "mathematical_authority": False,
            }
        )
        invalid_full_result["result_sha256"] = hashlib.sha256(
            validator._canonical(invalid_full_result)
        ).hexdigest()
        validator._validate_result_request_projection(
            None, invalid_full_result, request_input=invalid_request_input
        )
        with self.subTest(full_result_forgery="invalid raw request bytes"):
            with self.assertRaises(
                validator.ExecutionDispositionValidationFailure
            ):
                validator._validate_result_request_projection(
                    None,
                    invalid_full_result,
                    request_input=b'{"different":\n',
                )
        for field, replacement in (
            ("disposition_request_sha256", "d" * 64),
            ("invocation_sha256", "d" * 64),
            ("cancellation_armed", False),
            ("cancellation_armed", 1),
            ("cancellation_intent_sha256", "d" * 64),
            ("cancellation_intent_sha256", None),
        ):
            with self.subTest(field=field, replacement=replacement):
                forged = dict(result)
                forged[field] = replacement
                with self.assertRaises(
                    validator.ExecutionDispositionValidationFailure
                ):
                    validator._validate_result_request_projection(request, forged)

        def different_digest(value: str) -> str:
            return ("0" if value[0] != "0" else "1") + value[1:]

        forged_intent_request = json.loads(json.dumps(request))
        forged_intent_sha256 = different_digest(intent_sha256)
        forged_intent_request["cancellation_intent"]["intent_sha256"] = (
            forged_intent_sha256
        )
        forged_intent_preimage = dict(forged_intent_request)
        forged_intent_preimage["request_sha256"] = None
        forged_intent_request_sha256 = hashlib.sha256(
            validator._canonical(forged_intent_preimage)
        ).hexdigest()
        forged_intent_request["request_sha256"] = forged_intent_request_sha256
        forged_intent_result = {
            "disposition_request_sha256": forged_intent_request_sha256,
            "invocation_sha256": invocation_sha256,
            "cancellation_armed": True,
            "cancellation_intent_sha256": forged_intent_sha256,
        }
        with self.subTest(forgery="intent digest plus matching result"):
            with self.assertRaises(
                validator.ExecutionDispositionValidationFailure
            ):
                validator._validate_result_request_projection(
                    forged_intent_request, forged_intent_result
                )

        forged_request = json.loads(json.dumps(request))
        forged_request_sha256 = different_digest(request_sha256)
        forged_request["request_sha256"] = forged_request_sha256
        forged_request_result = dict(result)
        forged_request_result["disposition_request_sha256"] = (
            forged_request_sha256
        )
        with self.subTest(forgery="request digest plus matching result"):
            with self.assertRaises(
                validator.ExecutionDispositionValidationFailure
            ):
                validator._validate_result_request_projection(
                    forged_request, forged_request_result
                )

        forged_policy_request = json.loads(json.dumps(request))
        forged_policy_intent = forged_policy_request["cancellation_intent"]
        forged_policy_intent["policy_contract_sha256"] = "f" * 64
        forged_policy_intent["intent_sha256"] = None
        forged_policy_intent_sha256 = hashlib.sha256(
            validator._canonical(forged_policy_intent)
        ).hexdigest()
        forged_policy_intent["intent_sha256"] = forged_policy_intent_sha256
        forged_policy_request["contract_sha256"] = "f" * 64
        forged_policy_request["request_sha256"] = None
        forged_policy_request_sha256 = hashlib.sha256(
            validator._canonical(forged_policy_request)
        ).hexdigest()
        forged_policy_request["request_sha256"] = forged_policy_request_sha256
        with self.subTest(forgery="contract policy and repaired hash chain"):
            with self.assertRaisesRegex(
                validator.ExecutionDispositionValidationFailure,
                "retained request contract identity is not accepted",
            ):
                validator._validate_result_request_projection(
                    forged_policy_request,
                    {
                        "disposition_request_sha256": (
                            forged_policy_request_sha256
                        ),
                        "invocation_sha256": invocation_sha256,
                        "cancellation_armed": True,
                        "cancellation_intent_sha256": (
                            forged_policy_intent_sha256
                        ),
                    },
                )

        forged_intent_policy_request = json.loads(json.dumps(request))
        forged_intent_policy = forged_intent_policy_request[
            "cancellation_intent"
        ]
        forged_intent_policy["policy_contract_sha256"] = "f" * 64
        forged_intent_policy["intent_sha256"] = None
        forged_intent_policy_sha256 = hashlib.sha256(
            validator._canonical(forged_intent_policy)
        ).hexdigest()
        forged_intent_policy["intent_sha256"] = forged_intent_policy_sha256
        forged_intent_policy_request["request_sha256"] = None
        forged_intent_policy_request_sha256 = hashlib.sha256(
            validator._canonical(forged_intent_policy_request)
        ).hexdigest()
        forged_intent_policy_request["request_sha256"] = (
            forged_intent_policy_request_sha256
        )
        with self.subTest(forgery="intent policy and repaired hash chain"):
            with self.assertRaisesRegex(
                validator.ExecutionDispositionValidationFailure,
                "retained cancellation intent policy identity is not accepted",
            ):
                validator._validate_result_request_projection(
                    forged_intent_policy_request,
                    {
                        "disposition_request_sha256": (
                            forged_intent_policy_request_sha256
                        ),
                        "invocation_sha256": invocation_sha256,
                        "cancellation_armed": True,
                        "cancellation_intent_sha256": (
                            forged_intent_policy_sha256
                        ),
                    },
                )

        unarmed_request = json.loads(json.dumps(request))
        unarmed_request["cancellation_armed"] = False
        unarmed_projection = {
            name: unarmed_request[name] for name in validator.INVOCATION_FIELDS
        }
        unarmed_projection["schema"] = (
            "mathhead.execution-disposition-invocation.v1"
        )
        unarmed_invocation_sha256 = hashlib.sha256(
            validator._canonical(unarmed_projection)
        ).hexdigest()
        unarmed_request["invocation_sha256"] = unarmed_invocation_sha256
        unarmed_intent = unarmed_request["cancellation_intent"]
        unarmed_intent["invocation_sha256"] = unarmed_invocation_sha256
        unarmed_intent["intent_sha256"] = None
        unarmed_intent["intent_sha256"] = hashlib.sha256(
            validator._canonical(unarmed_intent)
        ).hexdigest()
        unarmed_request["request_sha256"] = None
        unarmed_request_sha256 = hashlib.sha256(
            validator._canonical(unarmed_request)
        ).hexdigest()
        unarmed_request["request_sha256"] = unarmed_request_sha256
        unarmed_result = {
            "disposition_request_sha256": unarmed_request_sha256,
            "invocation_sha256": unarmed_invocation_sha256,
            "cancellation_armed": False,
            "cancellation_intent_sha256": None,
        }
        with self.subTest(forgery="unarmed request retaining intent"):
            with self.assertRaises(
                validator.ExecutionDispositionValidationFailure
            ):
                validator._validate_result_request_projection(
                    unarmed_request, unarmed_result
                )

        valid_unarmed_request = json.loads(json.dumps(unarmed_request))
        valid_unarmed_request["cancellation_intent"] = None
        valid_unarmed_request["request_sha256"] = None
        valid_unarmed_request_sha256 = hashlib.sha256(
            validator._canonical(valid_unarmed_request)
        ).hexdigest()
        valid_unarmed_request["request_sha256"] = valid_unarmed_request_sha256
        valid_unarmed_result = {
            "disposition_request_sha256": valid_unarmed_request_sha256,
            "invocation_sha256": unarmed_invocation_sha256,
            "cancellation_armed": False,
            "cancellation_intent_sha256": None,
        }
        validator._validate_result_request_projection(
            valid_unarmed_request, valid_unarmed_result
        )
        with self.subTest(forgery="integer zero substituted for false"):
            forged_zero_result = dict(valid_unarmed_result)
            forged_zero_result["cancellation_armed"] = 0
            with self.assertRaises(
                validator.ExecutionDispositionValidationFailure
            ):
                validator._validate_result_request_projection(
                    valid_unarmed_request, forged_zero_result
                )


if __name__ == "__main__":
    unittest.main()
