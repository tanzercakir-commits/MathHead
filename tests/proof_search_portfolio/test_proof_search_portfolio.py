from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import pickle
import tempfile
from threading import Event
import sys
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


SCHEMAS = (
    "portfolio-execution-binding-v1.schema.json",
    "proof-search-portfolio-request-v1.schema.json",
    "portfolio-checker-decision-v1.schema.json",
    "portfolio-attempt-v1.schema.json",
    "portfolio-inconclusive-v1.schema.json",
    "proof-search-portfolio-result-v1.schema.json",
)


class ProofSearchPortfolioContractTests(unittest.TestCase):
    def test_schemas_are_closed_and_match_production_hashes(self) -> None:
        from mathhead import proof_search_portfolio as portfolio

        for name in SCHEMAS:
            raw = (ROOT / "docs/contracts/schemas" / name).read_bytes()
            schema = json.loads(raw)
            self.assertFalse(schema["additionalProperties"], name)
            self.assertEqual(
                hashlib.sha256(raw).hexdigest(),
                portfolio.SCHEMA_SHA256S[schema["properties"]["schema"]["const"]],
                name,
            )

    def test_contract_identity_is_bound_to_accepted_bytes(self) -> None:
        from mathhead import proof_search_portfolio as portfolio

        raw = (ROOT / "docs/contracts/MH-C-PROOF-SEARCH-PORTFOLIO-001.json").read_bytes()
        self.assertEqual(portfolio.PORTFOLIO_CONTRACT_ID, "MH-C-PROOF-SEARCH-PORTFOLIO-001")
        self.assertEqual(hashlib.sha256(raw).hexdigest(), portfolio.PORTFOLIO_CONTRACT_SHA256)

    def test_public_value_classes_are_constructor_and_subclass_closed(self) -> None:
        from mathhead import proof_search_portfolio as portfolio

        classes = (
            portfolio.PortfolioArtifactBinding,
            portfolio.PortfolioExecutionBinding,
            portfolio.ProofSearchPortfolioRequest,
            portfolio.PortfolioCheckerDecision,
            portfolio.PortfolioAttempt,
            portfolio.PortfolioInconclusive,
            portfolio.ProofSearchPortfolioResult,
        )
        for value_class in classes:
            with self.assertRaises(PermissionError):
                value_class()
            with self.assertRaises(TypeError):
                type("Forged", (value_class,), {})


class ProofSearchPortfolioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from tests.proof_search_portfolio.fixtures import PortfolioFixture

        cls.fixture = PortfolioFixture()

    def execute(self, fixture=None, *, cancel_event=None):
        from mathhead.isolated_worker import isolation_capability
        from mathhead.proof_search_portfolio import run_portfolio

        selected = self.fixture if fixture is None else fixture
        if not isolation_capability().supported:
            self.skipTest("host cannot enforce the complete isolated-worker capability")
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            return run_portfolio(
                selected.request,
                selected.plan_bytes,
                selected.parent,
                selected.descriptors if hasattr(selected, "descriptors") else (selected.descriptor,),
                selected.bindings if hasattr(selected, "bindings") else (selected.binding,),
                tuple(raw for _, raw in selected.input_pairs),
                selected.executable_paths,
                directory,
                cancel_event,
            )

    def require_isolation(self) -> None:
        from mathhead.isolated_worker import isolation_capability

        if not isolation_capability().supported:
            self.skipTest("host cannot enforce the complete isolated-worker capability")

    def replacement_binding(
        self,
        checker_output: bytes | None = None,
        *,
        producer_arguments: tuple[str, ...] | None = None,
        checker_arguments: tuple[str, ...] | None = None,
    ) -> tuple[bytes, bytes]:
        from mathhead.proof_search_portfolio import (
            make_portfolio_execution_binding,
            make_proof_search_portfolio_request,
            parse_portfolio_execution_binding,
        )
        from tests.proof_search_portfolio.fixtures import emit_script

        fixture = self.fixture
        value = parse_portfolio_execution_binding(fixture.binding)
        binding = make_portfolio_execution_binding(
            plan_order=value.plan_order,
            strategy_sha256=value.strategy_sha256,
            descriptor_sha256=value.descriptor_sha256,
            producer_component_id=value.producer_component_id,
            checker_component_id=value.checker_component_id,
            producer_family=value.producer_family,
            checker_family=value.checker_family,
            producer_executable=fixture.executable_bytes,
            checker_executable=fixture.executable_bytes,
            producer_arguments=value.producer_arguments if producer_arguments is None else producer_arguments,
            checker_arguments=(
                checker_arguments
                if checker_arguments is not None
                else value.checker_arguments
                if checker_output is None
                else ("-I", "-S", "-c", emit_script(checker_output))
            ),
            input_artifacts=fixture.input_pairs,
        )
        request = make_proof_search_portfolio_request(
            planning_result=fixture.plan_bytes,
            parent_budget=fixture.parent,
            descriptors=(fixture.descriptor,),
            bindings=(binding,),
            artifacts=fixture.input_pairs,
        )
        return binding, request

    def test_binding_and_request_are_closed_content_addressed_values(self) -> None:
        from mathhead.proof_search_portfolio import (
            ProofSearchPortfolioValidationError,
            make_portfolio_execution_binding,
            parse_portfolio_execution_binding,
            parse_proof_search_portfolio_request,
        )

        fixture = self.fixture
        binding = parse_portfolio_execution_binding(fixture.binding)
        request = parse_proof_search_portfolio_request(fixture.request)
        self.assertEqual(binding.strategy_sha256, fixture.strategy.strategy_sha256)
        self.assertEqual(request.binding_sha256s, (hashlib.sha256(fixture.binding).hexdigest(),))
        self.assertEqual(request.descriptor_sha256s, (hashlib.sha256(fixture.descriptor).hexdigest(),))
        self.assertFalse(binding.mathematical_authority)
        self.assertFalse(request.mathematical_authority)
        with self.assertRaises(ProofSearchPortfolioValidationError):
            parse_portfolio_execution_binding(fixture.binding.rstrip(b"\n"))
        duplicate = fixture.request.replace(b'{"artifact_bindings"', b'{"schema":"duplicate","artifact_bindings"', 1)
        with self.assertRaises(ProofSearchPortfolioValidationError):
            parse_proof_search_portfolio_request(duplicate)
        with self.assertRaises(ProofSearchPortfolioValidationError):
            make_portfolio_execution_binding(
                plan_order=True,
                strategy_sha256=binding.strategy_sha256,
                descriptor_sha256=binding.descriptor_sha256,
                producer_component_id=binding.producer_component_id,
                checker_component_id=binding.checker_component_id,
                producer_family=binding.producer_family,
                checker_family=binding.checker_family,
                producer_executable=fixture.executable_bytes,
                checker_executable=fixture.executable_bytes,
                producer_arguments=(),
                checker_arguments=(),
                input_artifacts=(),
            )
        for value in (binding, request):
            with self.assertRaises(TypeError):
                pickle.dumps(value)

    def test_public_codecs_reject_every_ambiguous_boundary_shape(self) -> None:
        from mathhead import proof_search_portfolio as portfolio
        from tests.proof_search_portfolio.fixtures import canonical, self_hash

        fixture = self.fixture
        binding = portfolio.parse_portfolio_execution_binding(fixture.binding)
        binding_arguments = {
            "plan_order": binding.plan_order,
            "strategy_sha256": binding.strategy_sha256,
            "descriptor_sha256": binding.descriptor_sha256,
            "producer_component_id": binding.producer_component_id,
            "checker_component_id": binding.checker_component_id,
            "producer_family": binding.producer_family,
            "checker_family": binding.checker_family,
            "producer_executable": fixture.executable_bytes,
            "checker_executable": fixture.executable_bytes,
            "producer_arguments": binding.producer_arguments,
            "checker_arguments": binding.checker_arguments,
            "input_artifacts": fixture.input_pairs,
        }

        nested: object = {}
        for _ in range(portfolio.MAX_DEPTH + 1):
            nested = {"nested": nested}
        malformed_bytes = (
            None,
            b"",
            b"\xff",
            b"[]\n",
            b'{"value":1.0}\n',
            f'{{"value":{portfolio.INTEGER_MAXIMUM + 1}}}\n'.encode(),
            b'{"value":"e\\u0301"}\n',
            canonical(nested),
        )
        for raw in malformed_bytes:
            with self.subTest(raw=repr(raw)[:80]):
                with self.assertRaises(portfolio.ProofSearchPortfolioValidationError):
                    portfolio.parse_portfolio_execution_binding(raw)  # type: ignore[arg-type]

        binding_mutations = (
            {"producer_executable": "python"},
            {"input_artifacts": (("input", bytearray(b"x")),)},
            {"producer_component_id": binding.checker_component_id},
            {"producer_family": "ambient"},
            {"producer_arguments": ("",)},
            {"producer_arguments": ("x",) * (portfolio.MAX_ARGUMENTS + 1)},
            {"input_artifacts": (("input", b"a"), ("input", b"b"))},
        )
        for mutation in binding_mutations:
            with self.subTest(binding_mutation=mutation.keys()):
                arguments = {**binding_arguments, **mutation}
                with self.assertRaises(portfolio.ProofSearchPortfolioValidationError):
                    portfolio.make_portfolio_execution_binding(**arguments)

        request_value = json.loads(fixture.request)
        repaired_constant = dict(request_value)
        repaired_constant["preference_policy"] = "majority_vote"
        self_hash(repaired_constant, "request_sha256")
        repaired_duplicate = dict(request_value)
        repaired_duplicate["descriptor_sha256s"] = [
            request_value["descriptor_sha256s"][0],
            request_value["descriptor_sha256s"][0],
        ]
        self_hash(repaired_duplicate, "request_sha256")
        stale_identity = dict(request_value)
        stale_identity["request_sha256"] = "0" * 64
        for raw in (
            canonical(repaired_constant),
            canonical(repaired_duplicate),
            canonical(stale_identity),
        ):
            with self.assertRaises(portfolio.ProofSearchPortfolioValidationError):
                portfolio.parse_proof_search_portfolio_request(raw)

        request_arguments = {
            "planning_result": fixture.plan_bytes,
            "parent_budget": fixture.parent,
            "descriptors": (fixture.descriptor,),
            "bindings": (fixture.binding,),
            "artifacts": fixture.input_pairs,
        }
        for mutation in (
            {"descriptors": [fixture.descriptor]},
            {"artifacts": (("input", bytearray(b"x")),)},
        ):
            with self.subTest(request_mutation=mutation.keys()):
                with self.assertRaises(portfolio.ProofSearchPortfolioValidationError):
                    portfolio.make_proof_search_portfolio_request(
                        **{**request_arguments, **mutation}
                    )

    def test_result_accessors_fail_closed_on_wrong_types_and_absent_artifacts(self) -> None:
        from mathhead import proof_search_portfolio as portfolio

        fixture = self.fixture
        invalid = portfolio.run_portfolio(
            b"",
            fixture.plan_bytes,
            fixture.parent,
            (fixture.descriptor,),
            (fixture.binding,),
            tuple(raw for _, raw in fixture.input_pairs),
            fixture.executable_paths,
            str(ROOT),
        )
        self.assertEqual(invalid.status, "invalid")
        for operation in (
            lambda: portfolio.validate_proof_search_portfolio_result(object()),
            lambda: portfolio.proof_search_portfolio_result_bytes(object()),
            lambda: portfolio.proof_search_portfolio_semantic_bytes(object()),
            lambda: portfolio.proof_search_portfolio_budget_bytes(object()),
            lambda: portfolio.proof_search_portfolio_selected_bytes(object(), "evidence"),
            lambda: portfolio.proof_search_portfolio_selected_bytes(invalid, "unknown"),
            lambda: portfolio.proof_search_portfolio_selected_bytes(invalid, "evidence"),
        ):
            with self.assertRaises(portfolio.ProofSearchPortfolioValidationError):
                operation()

    def test_evidence_codec_rejects_structural_semantic_and_resource_forgery(self) -> None:
        from mathhead import proof_search_portfolio as portfolio
        from tests.proof_search_portfolio.fixtures import (
            canonical,
            nonproduced_evidence_bytes,
        )

        fixture = self.fixture
        descriptor = portfolio._descriptor_inventory((fixture.descriptor,))[
            hashlib.sha256(fixture.descriptor).hexdigest()
        ]
        producer, _, environment, _ = portfolio._descriptor_strategy_parts(
            descriptor, fixture.strategy
        )
        base = json.loads(fixture.evidence)

        def changed(source, operation):
            value = copy.deepcopy(source)
            operation(value)
            return value

        diagnostic = {
            "diagnostic_id": "diagnostic_attack",
            "severity": "warning",
            "code": "org.mathhead.attack",
            "message": "adversarial fixture",
            "related_payload_ids": ["payload_proof"],
            "details": {},
        }
        incomplete = json.loads(
            nonproduced_evidence_bytes(
                fixture.strategy, fixture.descriptor, "incomplete"
            )
        )
        exhausted = json.loads(
            nonproduced_evidence_bytes(
                fixture.strategy, fixture.descriptor, "exhausted"
            )
        )
        truncated = json.loads(
            nonproduced_evidence_bytes(
                fixture.strategy, fixture.descriptor, "truncated"
            )
        )
        errored = json.loads(
            nonproduced_evidence_bytes(fixture.strategy, fixture.descriptor, "error")
        )
        dependencies = [
            {
                "evidence_id": "dependency_a",
                "evidence_sha256": "1" * 64,
                "relation": "premise",
                "depends_on_evidence_ids": ["dependency_b"],
            },
            {
                "evidence_id": "dependency_b",
                "evidence_sha256": "2" * 64,
                "relation": "support",
                "depends_on_evidence_ids": ["dependency_a"],
            },
        ]
        cases = (
            ("schema", changed(base, lambda value: value.update(schema="other"))),
            (
                "subject",
                changed(
                    base,
                    lambda value: value["subject"].update(statement_sha256="0" * 64),
                ),
            ),
            (
                "format version",
                changed(
                    base,
                    lambda value: value["format"].update(reader_minimum_minor=2),
                ),
            ),
            (
                "format binding",
                changed(
                    base,
                    lambda value: value["format"].update(format_id="org.mathhead.other"),
                ),
            ),
            (
                "producer substitution",
                changed(
                    base,
                    lambda value: value["producer"].update(component_id="producer_forged"),
                ),
            ),
            (
                "media type",
                changed(
                    base,
                    lambda value: value["payloads"][0].update(media_type="Application/JSON"),
                ),
            ),
            (
                "payload alias",
                changed(
                    base,
                    lambda value: value["payloads"].append(
                        {**value["payloads"][0], "payload_id": "payload_second"}
                    ),
                ),
            ),
            (
                "unbound primary",
                changed(base, lambda value: value.update(primary_payload_id=None)),
            ),
            (
                "wrong primary",
                changed(
                    base,
                    lambda value: value.update(primary_payload_id="payload_unknown"),
                ),
            ),
            (
                "duplicate dependency",
                changed(
                    base,
                    lambda value: value.update(
                        dependencies=[
                            {**dependencies[0], "depends_on_evidence_ids": []},
                            {**dependencies[0], "depends_on_evidence_ids": []},
                        ]
                    ),
                ),
            ),
            (
                "unresolved dependency",
                changed(
                    base,
                    lambda value: value.update(dependencies=[dependencies[0]]),
                ),
            ),
            (
                "dependency cycle",
                changed(base, lambda value: value.update(dependencies=dependencies)),
            ),
            (
                "seed policy",
                changed(
                    base,
                    lambda value: value["generation"].update(seed=7),
                ),
            ),
            (
                "generation identity",
                changed(
                    base,
                    lambda value: value["generation"].update(
                        configuration_sha256="0" * 64
                    ),
                ),
            ),
            (
                "unknown diagnostic payload",
                changed(
                    base,
                    lambda value: (
                        value.update(
                            diagnostics=[
                                {**diagnostic, "related_payload_ids": ["payload_unknown"]}
                            ]
                        ),
                        value["outcome"].update(
                            diagnostic_ids=["diagnostic_attack"]
                        ),
                    ),
                ),
            ),
            ("outcome shape", changed(base, lambda value: value.update(outcome=[]))),
            (
                "diagnostic inventory",
                changed(base, lambda value: value.update(diagnostics=[diagnostic])),
            ),
            (
                "payload inventory",
                changed(
                    base,
                    lambda value: value["outcome"].update(payload_ids=[]),
                ),
            ),
            (
                "hidden producer error",
                changed(
                    base,
                    lambda value: (
                        value.update(diagnostics=[{**diagnostic, "severity": "error"}]),
                        value["outcome"].update(
                            diagnostic_ids=["diagnostic_attack"]
                        ),
                    ),
                ),
            ),
            (
                "missing non-produced diagnostic",
                changed(
                    incomplete,
                    lambda value: (
                        value.update(diagnostics=[]),
                        value["outcome"].update(diagnostic_ids=[]),
                    ),
                ),
            ),
            (
                "empty exhaustion",
                changed(
                    exhausted,
                    lambda value: value["outcome"].update(dimensions=[]),
                ),
            ),
            (
                "unknown exhaustion dimension",
                changed(
                    exhausted,
                    lambda value: value["outcome"].update(dimensions=["ambient_time"]),
                ),
            ),
            (
                "empty truncation",
                changed(
                    truncated,
                    lambda value: value["outcome"].update(truncation_ids=[]),
                ),
            ),
            (
                "unknown retained payload",
                changed(
                    truncated,
                    lambda value: value["outcome"].update(
                        retained_payload_ids=["payload_unknown"]
                    ),
                ),
            ),
            (
                "non-error diagnostic",
                changed(
                    errored,
                    lambda value: value["diagnostics"][0].update(severity="warning"),
                ),
            ),
            (
                "hidden budget outcome",
                changed(
                    base,
                    lambda value: value["budget"].update(outcome="cancelled"),
                ),
            ),
            ("missing claim", changed(base, lambda value: value.update(extensions={}))),
            (
                "identity collision",
                changed(
                    base,
                    lambda value: (
                        value.update(
                            diagnostics=[
                                {**diagnostic, "diagnostic_id": value["evidence_id"]}
                            ]
                        ),
                        value["outcome"].update(
                            diagnostic_ids=[value["evidence_id"]]
                        ),
                    ),
                ),
            ),
            (
                "duplicate diagnostics",
                changed(
                    base,
                    lambda value: value.update(
                        diagnostics=[diagnostic, copy.deepcopy(diagnostic)]
                    ),
                ),
            ),
            (
                "unordered features",
                changed(
                    base,
                    lambda value: value["format"].update(
                        features=["org.mathhead.zeta", "org.mathhead.alpha"]
                    ),
                ),
            ),
            ("extension shape", changed(base, lambda value: value.update(extensions=[]))),
            ("payload shape", changed(base, lambda value: value.update(payloads={}))),
        )
        for label, value in cases:
            with self.subTest(label=label):
                with self.assertRaises(portfolio.ProofSearchPortfolioValidationError):
                    portfolio._validate_evidence(
                        canonical(value), fixture.strategy, producer, environment
                    )

    def test_finite_codec_guards_reject_non_json_and_oversized_collections(self) -> None:
        from mathhead import proof_search_portfolio as portfolio
        from tests.proof_search_portfolio.fixtures import canonical, self_hash

        guards = (
            lambda: portfolio._walk([None] * (portfolio.MAX_ITEMS + 1)),
            lambda: portfolio._walk({1: None}),
            lambda: portfolio._walk(object()),
            lambda: portfolio._canonical({"bounded": "value"}, maximum=1),
            lambda: portfolio._artifact_bindings({}, "artifacts"),
            lambda: portfolio._sha_tuple({}, "digests"),
        )
        for operation in guards:
            with self.assertRaises(portfolio.ProofSearchPortfolioValidationError):
                operation()

        forged = json.loads(self.fixture.binding)
        forged["protocol"] = "ambient_protocol"
        self_hash(forged, "binding_sha256")
        with self.assertRaises(portfolio.ProofSearchPortfolioValidationError):
            portfolio.parse_portfolio_execution_binding(canonical(forged))

    def test_certificate_codec_rejects_checker_replay_and_trust_forgery(self) -> None:
        from mathhead import proof_search_portfolio as portfolio
        from tests.proof_search_portfolio.fixtures import canonical, checker_envelope
        from tools.validate_evidence_certificate_contracts import (
            certificate_replay_basis_sha256,
        )

        fixture = self.fixture
        descriptor = portfolio._descriptor_inventory((fixture.descriptor,))[
            hashlib.sha256(fixture.descriptor).hexdigest()
        ]
        producer, checker, environment, formats = portfolio._descriptor_strategy_parts(
            descriptor, fixture.strategy
        )
        evidence, claim = portfolio._validate_evidence(
            fixture.evidence, fixture.strategy, producer, environment
        )
        self.assertEqual(claim, "proved")

        def certificate(status="verified"):
            return json.loads(
                checker_envelope(
                    fixture.strategy,
                    fixture.descriptor,
                    fixture.evidence,
                    "proved",
                    certificate_status=status,
                )
            )["certificate"]

        def changed(source, operation, *, repair_replay=False):
            value = copy.deepcopy(source)
            operation(value)
            if repair_replay:
                value["replay"]["basis_sha256"] = certificate_replay_basis_sha256(
                    value
                )
            return value

        base = certificate()
        diagnostic = {
            "diagnostic_id": "diagnostic_attack",
            "severity": "warning",
            "code": "org.mathhead.attack",
            "message": "adversarial fixture",
            "related_artifact_ids": ["artifact_checker_result"],
            "details": {},
        }
        cases = (
            ("schema", changed(base, lambda value: value.update(schema="other"))),
            (
                "subject",
                changed(
                    base,
                    lambda value: value["subject"].update(statement_sha256="0" * 64),
                ),
            ),
            (
                "format",
                changed(
                    base,
                    lambda value: value["format"].update(format_id="org.mathhead.other"),
                ),
            ),
            (
                "checker substitution",
                changed(
                    base,
                    lambda value: value["checker"].update(component_id="checker_forged"),
                ),
            ),
            (
                "evidence binding",
                changed(
                    base,
                    lambda value: value["evidence"].update(evidence_sha256="0" * 64),
                ),
            ),
            (
                "replay seed",
                changed(base, lambda value: value["replay"].update(seed=3)),
            ),
            (
                "observed digest",
                changed(
                    base,
                    lambda value: value["replay"].update(
                        observed_payload_sha256="not-a-digest"
                    ),
                ),
            ),
            (
                "replay identity",
                changed(
                    base,
                    lambda value: value["replay"].update(
                        configuration_sha256="0" * 64
                    ),
                ),
            ),
            (
                "artifact producer",
                changed(
                    base,
                    lambda value: value["verification_artifacts"][0].update(
                        producer_component_id="checker_forged"
                    ),
                ),
            ),
            (
                "artifact alias",
                changed(
                    base,
                    lambda value: value["verification_artifacts"].append(
                        {
                            **value["verification_artifacts"][0],
                            "artifact_id": "artifact_second",
                        }
                    ),
                ),
            ),
            (
                "trust alias",
                changed(
                    base,
                    lambda value: value["trust_dependencies"].append(
                        copy.deepcopy(value["trust_dependencies"][0])
                    ),
                ),
            ),
            (
                "diagnostic artifact",
                changed(
                    base,
                    lambda value: value.update(
                        diagnostics=[
                            {
                                **diagnostic,
                                "related_artifact_ids": ["artifact_unknown"],
                            }
                        ]
                    ),
                ),
            ),
            ("verdict shape", changed(base, lambda value: value.update(verdict=[]))),
            (
                "diagnostic inventory",
                changed(base, lambda value: value.update(diagnostics=[diagnostic])),
            ),
            (
                "authority mismatch",
                changed(
                    base,
                    lambda value: value["verdict"].update(authority="external_verified"),
                ),
            ),
            (
                "trust digest",
                changed(
                    base,
                    lambda value: value["trust_dependencies"][0].update(sha256="0" * 64),
                ),
            ),
            (
                "missing non-verified diagnostic",
                changed(
                    certificate("invalid"),
                    lambda value: (
                        value.update(diagnostics=[]),
                        value["verdict"].update(diagnostic_ids=[]),
                    ),
                ),
            ),
            (
                "soft verifier failure",
                changed(
                    certificate("verifier_failed"),
                    lambda value: value["diagnostics"][0].update(severity="warning"),
                ),
            ),
            (
                "invalid without checker result",
                changed(
                    certificate("invalid"),
                    lambda value: value["verdict"].update(
                        checker_result_artifact_id="artifact_unknown"
                    ),
                ),
            ),
            (
                "empty exhaustion",
                changed(
                    certificate("exhausted"),
                    lambda value: value["verdict"].update(dimensions=[]),
                ),
            ),
            (
                "empty truncation",
                changed(
                    certificate("truncated"),
                    lambda value: value["verdict"].update(truncation_ids=[]),
                ),
            ),
            (
                "unresolved disagreement",
                changed(
                    certificate("disagreement"),
                    lambda value: value["verdict"].update(
                        conflicting_artifact_ids=["artifact_checker_result"]
                    ),
                ),
            ),
            (
                "hidden budget outcome",
                changed(
                    certificate("exhausted"),
                    lambda value: value["budget"].update(outcome="completed"),
                ),
            ),
            (
                "namespace collision",
                changed(
                    base,
                    lambda value: value.update(
                        certificate_id="artifact_checker_result"
                    ),
                    repair_replay=True,
                ),
            ),
        )
        for label, value in cases:
            with self.subTest(label=label):
                with self.assertRaises(portfolio.ProofSearchPortfolioValidationError):
                    portfolio._validate_certificate(
                        canonical(value),
                        fixture.evidence,
                        evidence,
                        fixture.strategy,
                        checker,
                        environment,
                        formats,
                    )

    def test_checker_decision_codec_recomputes_all_authority_relations(self) -> None:
        from mathhead import proof_search_portfolio as portfolio
        from tests.proof_search_portfolio.fixtures import canonical, self_hash

        envelope = json.loads(self.fixture.envelope)
        base = envelope["decision"]
        certificate = canonical(envelope["certificate"])

        def changed(operation, *, repair=True):
            value = copy.deepcopy(base)
            operation(value)
            if repair:
                self_hash(value, "decision_sha256")
            return canonical(value)

        cases = (
            ("constants", changed(lambda value: value.update(schema="other"))),
            (
                "checker independence",
                changed(
                    lambda value: value.update(
                        producer_component_id=value["checker_component_id"]
                    )
                ),
            ),
            (
                "Evidence bytes",
                changed(lambda value: value.update(evidence_sha256=None)),
            ),
            (
                "Certificate bytes",
                changed(lambda value: value.update(certificate_sha256=None)),
            ),
            (
                "agreement reason",
                changed(lambda value: value.update(reason_code="CHECKER_REJECTED")),
            ),
            (
                "non-verified authority",
                changed(
                    lambda value: value.update(
                        certificate_verdict="invalid",
                        agreement=False,
                        reason_code="CHECKER_REJECTED",
                    )
                ),
            ),
            (
                "disagreement relation",
                changed(
                    lambda value: value.update(
                        certificate_verdict="unsupported",
                        certificate_authority="none",
                        agreement=False,
                        reason_code="CHECKER_DISAGREED",
                    )
                ),
            ),
            (
                "boolean type",
                changed(lambda value: value.update(agreement=1)),
            ),
            (
                "stale identity",
                changed(
                    lambda value: value.update(decision_sha256="0" * 64),
                    repair=False,
                ),
            ),
        )
        for label, raw in cases:
            with self.subTest(label=label):
                with self.assertRaises(portfolio.ProofSearchPortfolioValidationError):
                    portfolio.parse_portfolio_checker_decision(raw)
        with self.assertRaises(portfolio.ProofSearchPortfolioValidationError):
            portfolio.parse_portfolio_checker_decision(canonical(base), [certificate])
        with self.assertRaises(portfolio.ProofSearchPortfolioValidationError):
            portfolio.parse_portfolio_checker_decision(canonical(base), b"wrong")

    def test_result_codec_rejects_repaired_attempt_and_ledger_forgery(self) -> None:
        from mathhead import proof_search_portfolio as portfolio
        from tests.proof_search_portfolio.fixtures import (
            FallbackPortfolioFixture,
            canonical,
            self_hash,
        )

        result = self.execute()
        raw = json.loads(portfolio.proof_search_portfolio_result_bytes(result))
        final_parent = portfolio.proof_search_portfolio_budget_bytes(result)
        evidence = portfolio.proof_search_portfolio_selected_bytes(result, "evidence")
        certificate = portfolio.proof_search_portfolio_selected_bytes(
            result, "certificate"
        )

        def changed(operation, *, repair_attempt=True):
            value = copy.deepcopy(raw)
            operation(value)
            if repair_attempt:
                for attempt in value["attempts"]:
                    self_hash(attempt, "attempt_sha256")
            self_hash(value, "result_sha256")
            return canonical(value)

        cases = (
            (
                "contract",
                changed(
                    lambda value: value.update(contract_sha256="0" * 64)
                ),
            ),
            (
                "attempt constants",
                changed(lambda value: value["attempts"][0].update(schema="other")),
            ),
            (
                "attempt identity",
                changed(
                    lambda value: value["attempts"][0].update(
                        attempt_sha256="0" * 64
                    ),
                    repair_attempt=False,
                ),
            ),
            (
                "producer status",
                changed(
                    lambda value: value["attempts"][0].update(
                        producer_worker_result_sha256=None
                    )
                ),
            ),
            (
                "Evidence bytes",
                changed(
                    lambda value: value["attempts"][0].update(
                        evidence_sha256=None
                    )
                ),
            ),
            (
                "checker status",
                changed(
                    lambda value: value["attempts"][0].update(
                        checker_worker_result_sha256=None
                    )
                ),
            ),
            (
                "unstarted checker",
                changed(
                    lambda value: value["attempts"][0].update(
                        checker_status="not_started",
                        checker_worker_result_sha256=None,
                    )
                ),
            ),
            (
                "unchecked success",
                changed(
                    lambda value: value["attempts"][0].update(
                        evidence_sha256=None,
                        evidence_bytes=0,
                    )
                ),
            ),
            (
                "attempt order",
                changed(
                    lambda value: value["attempts"][0].update(attempt_order=1)
                ),
            ),
            (
                "missing selection",
                changed(lambda value: value.update(selected_strategy_sha256=None)),
            ),
            (
                "selected attempt",
                changed(
                    lambda value: value.update(selected_strategy_sha256="0" * 64)
                ),
            ),
            (
                "authority on failure",
                changed(
                    lambda value: value.update(
                        status="invalid", mathematical_verdict="none"
                    )
                ),
            ),
        )
        for label, forged in cases:
            with self.subTest(label=label):
                with self.assertRaises(portfolio.ProofSearchPortfolioValidationError):
                    portfolio.parse_proof_search_portfolio_result(
                        forged, final_parent, evidence, certificate
                    )

        with self.assertRaises(portfolio.ProofSearchPortfolioValidationError):
            portfolio.parse_proof_search_portfolio_result(canonical(raw))
        with self.assertRaises(portfolio.ProofSearchPortfolioValidationError):
            portfolio.parse_proof_search_portfolio_result(
                canonical(raw), final_parent + b"x", evidence, certificate
            )

        final_chain = copy.deepcopy(raw)
        final_chain["attempts"][-1]["parent_budget_after_sha256"] = "0" * 64
        self_hash(final_chain["attempts"][-1], "attempt_sha256")
        self_hash(final_chain, "result_sha256")
        with self.assertRaises(portfolio.ProofSearchPortfolioValidationError):
            portfolio.parse_proof_search_portfolio_result(
                canonical(final_chain), final_parent, evidence, certificate
            )

        fallback = self.execute(FallbackPortfolioFixture())
        fallback_raw = json.loads(
            portfolio.proof_search_portfolio_result_bytes(fallback)
        )
        fallback_parent = portfolio.proof_search_portfolio_budget_bytes(fallback)
        fallback_evidence = portfolio.proof_search_portfolio_selected_bytes(
            fallback, "evidence"
        )
        fallback_certificate = portfolio.proof_search_portfolio_selected_bytes(
            fallback, "certificate"
        )
        stale_result = copy.deepcopy(raw)
        stale_result["result_sha256"] = "0" * 64
        with self.assertRaises(portfolio.ProofSearchPortfolioValidationError):
            portfolio.parse_proof_search_portfolio_result(
                canonical(stale_result), final_parent, evidence, certificate
            )

        inconclusive_constants = copy.deepcopy(fallback_raw)
        inconclusive_constants["inconclusive_outcomes"][0]["schema"] = "other"
        self_hash(
            inconclusive_constants["inconclusive_outcomes"][0],
            "inconclusive_sha256",
        )
        self_hash(inconclusive_constants, "result_sha256")
        with self.assertRaises(portfolio.ProofSearchPortfolioValidationError):
            portfolio.parse_proof_search_portfolio_result(
                canonical(inconclusive_constants),
                fallback_parent,
                fallback_evidence,
                fallback_certificate,
            )

        stale_inconclusive = copy.deepcopy(fallback_raw)
        stale_inconclusive["inconclusive_outcomes"][0][
            "inconclusive_sha256"
        ] = "0" * 64
        self_hash(stale_inconclusive, "result_sha256")
        with self.assertRaises(portfolio.ProofSearchPortfolioValidationError):
            portfolio.parse_proof_search_portfolio_result(
                canonical(stale_inconclusive),
                fallback_parent,
                fallback_evidence,
                fallback_certificate,
            )

        fallback_raw["attempts"][0]["parent_budget_after_sha256"] = "0" * 64
        self_hash(fallback_raw["attempts"][0], "attempt_sha256")
        self_hash(fallback_raw, "result_sha256")
        with self.assertRaises(portfolio.ProofSearchPortfolioValidationError):
            portfolio.parse_proof_search_portfolio_result(
                canonical(fallback_raw),
                fallback_parent,
                fallback_evidence,
                fallback_certificate,
            )

    def test_checked_proof_uses_two_reconciled_isolated_leases(self) -> None:
        from mathhead.proof_search_portfolio import (
            parse_proof_search_portfolio_result,
            proof_search_portfolio_budget_bytes,
            proof_search_portfolio_result_bytes,
            proof_search_portfolio_selected_bytes,
            validate_proof_search_portfolio_result,
        )

        result = self.execute()
        self.assertEqual((result.status, result.mathematical_verdict), ("succeeded", "proved"))
        self.assertEqual(result.authority_tier, "checker_attestation")
        self.assertEqual(len(result.attempts), 1)
        attempt = result.attempts[0]
        self.assertEqual((attempt.producer_status, attempt.checker_status, attempt.outcome), ("completed", "completed", "success"))
        final_budget = proof_search_portfolio_budget_bytes(result)
        events = json.loads(final_budget)["events"]
        self.assertEqual([item["kind"] for item in events], ["reserve", "sample", "reconcile", "reserve", "sample", "reconcile"])
        self.assertNotEqual(events[0]["lease_id"], events[3]["lease_id"])
        self.assertEqual(proof_search_portfolio_selected_bytes(result, "evidence"), self.fixture.evidence)
        raw = proof_search_portfolio_result_bytes(result)
        rebuilt = parse_proof_search_portfolio_result(
            raw,
            final_budget,
            proof_search_portfolio_selected_bytes(result, "evidence"),
            proof_search_portfolio_selected_bytes(result, "certificate"),
        )
        self.assertEqual(rebuilt, result)
        validate_proof_search_portfolio_result(result)
        with self.assertRaises(TypeError):
            copy.copy(result)

    def test_repaired_result_selection_and_inconclusive_links_are_rejected(self) -> None:
        from mathhead.proof_search_portfolio import (
            ProofSearchPortfolioValidationError,
            parse_proof_search_portfolio_result,
            proof_search_portfolio_budget_bytes,
            proof_search_portfolio_result_bytes,
            proof_search_portfolio_selected_bytes,
        )
        from tests.proof_search_portfolio.fixtures import (
            FallbackPortfolioFixture,
            canonical,
            self_hash,
            sha,
        )

        result = self.execute()
        raw = proof_search_portfolio_result_bytes(result)
        final_parent = proof_search_portfolio_budget_bytes(result)
        evidence = proof_search_portfolio_selected_bytes(result, "evidence")
        certificate = proof_search_portfolio_selected_bytes(result, "certificate")

        repaired_selection = json.loads(raw)
        repaired_selection["selected_strategy_sha256"] = "0" * 64
        self_hash(repaired_selection, "result_sha256")
        with self.assertRaises(ProofSearchPortfolioValidationError):
            parse_proof_search_portfolio_result(
                canonical(repaired_selection),
                final_parent,
                evidence,
                certificate,
            )

        forged_evidence_value = json.loads(evidence)
        forged_evidence_value["extensions"]["org.mathhead.portfolio.claim"] = "refuted"
        forged_evidence = canonical(forged_evidence_value)
        repaired_chain = json.loads(raw)
        repaired_chain["selected_evidence_sha256"] = sha(forged_evidence)
        repaired_chain["attempts"][-1]["evidence_sha256"] = sha(forged_evidence)
        repaired_chain["attempts"][-1]["evidence_bytes"] = len(forged_evidence)
        self_hash(repaired_chain["attempts"][-1], "attempt_sha256")
        self_hash(repaired_chain, "result_sha256")
        with self.assertRaises(ProofSearchPortfolioValidationError):
            parse_proof_search_portfolio_result(
                canonical(repaired_chain),
                final_parent,
                forged_evidence,
                certificate,
            )

        fallback = self.execute(FallbackPortfolioFixture())
        fallback_raw = json.loads(proof_search_portfolio_result_bytes(fallback))
        fallback_raw["inconclusive_outcomes"][0]["producer_worker_result_sha256"] = "0" * 64
        self_hash(fallback_raw["inconclusive_outcomes"][0], "inconclusive_sha256")
        self_hash(fallback_raw, "result_sha256")
        with self.assertRaises(ProofSearchPortfolioValidationError):
            parse_proof_search_portfolio_result(
                canonical(fallback_raw),
                proof_search_portfolio_budget_bytes(fallback),
                proof_search_portfolio_selected_bytes(fallback, "evidence"),
                proof_search_portfolio_selected_bytes(fallback, "certificate"),
            )

    def test_invalid_evidence_falls_back_in_exact_plan_order_then_refutes(self) -> None:
        from tests.proof_search_portfolio.fixtures import FallbackPortfolioFixture

        result = self.execute(FallbackPortfolioFixture())
        self.assertEqual((result.status, result.mathematical_verdict), ("succeeded", "refuted"))
        self.assertEqual(tuple(item.outcome for item in result.attempts), ("invalid_evidence", "success"))
        self.assertEqual(result.attempts[0].checker_status, "not_started")
        self.assertEqual(len(result.inconclusive_outcomes), 1)
        self.assertEqual(result.inconclusive_outcomes[0].attempt_order, 0)

    def test_v1_preserves_planner_order_without_name_based_counterexample_preference(self) -> None:
        from tests.proof_search_portfolio.fixtures import FallbackPortfolioFixture

        result = self.execute(FallbackPortfolioFixture(first_claim="proved"))
        self.assertEqual((result.status, result.mathematical_verdict), ("succeeded", "proved"))
        self.assertEqual(result.preference_policy, "planner_order_no_sound_witness_declaration")
        self.assertEqual(len(result.attempts), 1)
        self.assertEqual(result.attempts[0].strategy_sha256, result.selected_strategy_sha256)
        self.assertEqual(result.inconclusive_outcomes, ())

    def test_checker_disagreement_is_non_authoritative(self) -> None:
        from tests.proof_search_portfolio.fixtures import PortfolioFixture

        result = self.execute(PortfolioFixture(agreement=False))
        self.assertEqual((result.status, result.mathematical_verdict), ("disagreement", "inconclusive"))
        self.assertEqual(result.authority_tier, "none")
        self.assertIsNone(result.selected_certificate_sha256)
        self.assertEqual(result.attempts[0].outcome, "checker_disagreement")
        self.assertEqual(len(result.inconclusive_outcomes), 1)

    def test_all_closed_certificate_outcomes_follow_exact_terminal_transitions(self) -> None:
        from tests.proof_search_portfolio.fixtures import PortfolioFixture

        expected = {
            "invalid": ("disagreement", "checker_disagreement"),
            "unsupported": ("inconclusive", "checker_inconclusive"),
            "inconclusive": ("inconclusive", "checker_inconclusive"),
            "cancelled": ("cancelled", "cancelled"),
            "exhausted": ("exhausted", "exhausted"),
            "truncated": ("truncated", "truncated"),
            "verifier_failed": ("verifier_failed", "verifier_failure"),
            "disagreement": ("disagreement", "checker_disagreement"),
        }
        for certificate_status, (terminal, outcome) in expected.items():
            with self.subTest(certificate_status=certificate_status):
                result = self.execute(PortfolioFixture(certificate_status=certificate_status))
                self.assertEqual(result.status, terminal)
                self.assertEqual(result.mathematical_verdict, "inconclusive")
                self.assertEqual(result.authority_tier, "none")
                self.assertEqual(result.attempts[0].outcome, outcome)
                self.assertIsNone(result.selected_certificate_sha256)

    def test_all_nonproduced_evidence_outcomes_remain_non_authoritative(self) -> None:
        from mathhead.proof_search_portfolio import run_portfolio
        from tests.proof_search_portfolio.fixtures import emit_script, nonproduced_evidence_bytes

        self.require_isolation()
        expected = {
            "unsupported": ("unsupported", "unsupported"),
            "incomplete": ("ambiguous", "ambiguous"),
            "cancelled": ("cancelled", "cancelled"),
            "exhausted": ("exhausted", "exhausted"),
            "truncated": ("truncated", "truncated"),
            "error": ("failed", "producer_error"),
        }
        for evidence_status, (terminal, outcome) in expected.items():
            with self.subTest(evidence_status=evidence_status):
                payload = nonproduced_evidence_bytes(
                    self.fixture.strategy,
                    self.fixture.descriptor,
                    evidence_status,
                )
                binding, request = self.replacement_binding(
                    producer_arguments=("-I", "-S", "-c", emit_script(payload))
                )
                with tempfile.TemporaryDirectory(dir=ROOT) as directory:
                    result = run_portfolio(
                        request,
                        self.fixture.plan_bytes,
                        self.fixture.parent,
                        (self.fixture.descriptor,),
                        (binding,),
                        tuple(raw for _, raw in self.fixture.input_pairs),
                        self.fixture.executable_paths,
                        directory,
                    )
                self.assertEqual((result.status, result.mathematical_verdict), (terminal, "inconclusive"))
                self.assertEqual(result.attempts[0].outcome, outcome)
                self.assertEqual(result.attempts[0].checker_status, "not_started")
                self.assertEqual(result.authority_tier, "none")

    def test_malformed_certificate_cannot_promote_producer_claim(self) -> None:
        self.require_isolation()
        binding, request = self.replacement_binding(b'{"certificate":{},"decision":{}}\n')
        fixture = self.fixture
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            from mathhead.proof_search_portfolio import run_portfolio

            result = run_portfolio(
                request,
                fixture.plan_bytes,
                fixture.parent,
                (fixture.descriptor,),
                (binding,),
                tuple(raw for _, raw in fixture.input_pairs),
                fixture.executable_paths,
                directory,
            )
        self.assertEqual((result.status, result.mathematical_verdict), ("invalid_evidence", "inconclusive"))
        self.assertIsNone(result.selected_evidence_sha256)
        self.assertEqual(result.attempts[0].outcome, "invalid_evidence")

    def test_evidence_larger_than_the_worker_argument_protocol_is_explicit(self) -> None:
        from mathhead.proof_search_portfolio import run_portfolio
        from tests.proof_search_portfolio.fixtures import canonical, emit_script
        from tools.validate_evidence_certificate_contracts import evidence_generation_basis_sha256

        self.require_isolation()
        evidence = json.loads(self.fixture.evidence)
        evidence["diagnostics"] = [
            {
                "diagnostic_id": "diagnostic_protocol_limit",
                "severity": "info",
                "code": "org.mathhead.protocol-limit",
                "message": "x" * 4096,
                "related_payload_ids": [],
                "details": {},
            }
        ]
        evidence["outcome"]["diagnostic_ids"] = ["diagnostic_protocol_limit"]
        evidence["generation"]["basis_sha256"] = evidence_generation_basis_sha256(evidence)
        oversized = canonical(evidence)
        self.assertGreater(len(oversized), 4096)
        binding, request = self.replacement_binding(
            producer_arguments=("-I", "-S", "-c", emit_script(oversized))
        )
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            result = run_portfolio(
                request,
                self.fixture.plan_bytes,
                self.fixture.parent,
                (self.fixture.descriptor,),
                (binding,),
                tuple(raw for _, raw in self.fixture.input_pairs),
                self.fixture.executable_paths,
                directory,
            )
        self.assertEqual((result.status, result.mathematical_verdict), ("invalid_evidence", "inconclusive"))
        self.assertEqual(result.attempts[0].outcome, "invalid_evidence")
        self.assertEqual(result.attempts[0].checker_status, "not_started")
        self.assertEqual(result.inconclusive_outcomes[0].reason_code, "EVIDENCE_PROTOCOL_LIMIT")

    def test_manifest_mismatch_fails_before_any_supervisor_call(self) -> None:
        from mathhead import proof_search_portfolio as portfolio

        fixture = self.fixture
        with mock.patch.object(portfolio, "supervise_worker") as supervisor:
            result = portfolio.run_portfolio(
                fixture.request,
                fixture.plan_bytes,
                fixture.parent,
                (fixture.descriptor,),
                (),
                tuple(raw for _, raw in fixture.input_pairs),
                fixture.executable_paths,
                str(ROOT),
            )
        supervisor.assert_not_called()
        self.assertEqual((result.status, result.reason_code), ("invalid", "PORTFOLIO_INPUT_INVALID"))
        self.assertEqual(result.attempts, ())

    def test_worker_crashes_are_distinct_producer_and_verifier_failures(self) -> None:
        from mathhead.proof_search_portfolio import run_portfolio

        self.require_isolation()
        fixture = self.fixture
        cases = (
            (
                {"producer_arguments": ("-I", "-S", "-c", "raise SystemExit(7)")},
                "failed",
                "producer_error",
                "not_started",
            ),
            (
                {"checker_arguments": ("-I", "-S", "-c", "raise SystemExit(9)")},
                "verifier_failed",
                "verifier_failure",
                "failed",
            ),
        )
        for replacement, terminal, outcome, checker_status in cases:
            with self.subTest(terminal=terminal):
                binding, request = self.replacement_binding(**replacement)
                with tempfile.TemporaryDirectory(dir=ROOT) as directory:
                    result = run_portfolio(
                        request,
                        fixture.plan_bytes,
                        fixture.parent,
                        (fixture.descriptor,),
                        (binding,),
                        tuple(raw for _, raw in fixture.input_pairs),
                        fixture.executable_paths,
                        directory,
                    )
                self.assertEqual(result.status, terminal)
                self.assertEqual(result.attempts[0].outcome, outcome)
                self.assertEqual(result.attempts[0].checker_status, checker_status)
                self.assertEqual(result.authority_tier, "none")

    def test_cleanup_failure_stops_before_fallback_can_promote(self) -> None:
        from mathhead import isolated_worker as worker
        from mathhead.proof_search_portfolio import run_portfolio
        from tests.proof_search_portfolio.fixtures import FallbackPortfolioFixture

        self.require_isolation()
        fixture = FallbackPortfolioFixture()
        original_rmtree = worker.shutil.rmtree
        calls = 0

        def fail_first_cleanup(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise OSError("cleanup denied")
            return original_rmtree(*args, **kwargs)

        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            with mock.patch.object(worker.shutil, "rmtree", side_effect=fail_first_cleanup):
                result = run_portfolio(
                    fixture.request,
                    fixture.plan_bytes,
                    fixture.parent,
                    fixture.descriptors,
                    fixture.bindings,
                    tuple(raw for _, raw in fixture.input_pairs),
                    fixture.executable_paths,
                    directory,
                )
        self.assertEqual((result.status, result.mathematical_verdict), ("invalid", "none"))
        self.assertEqual(result.reason_code, "PORTFOLIO_EXECUTION_INVALID")
        self.assertEqual(result.attempts, ())
        self.assertIsNone(result.selected_evidence_sha256)
        self.assertEqual(calls, 1)

    def test_unsupported_containment_and_insufficient_budget_fail_closed(self) -> None:
        from mathhead import isolated_worker as worker
        from mathhead.proof_search_portfolio import make_proof_search_portfolio_request, run_portfolio
        from tests.isolated_worker.test_isolated_worker import parent_budget

        self.require_isolation()
        fixture = self.fixture
        with mock.patch.object(worker.sys, "platform", "unsupported-test-platform"):
            with tempfile.TemporaryDirectory(dir=ROOT) as directory:
                unsupported = run_portfolio(
                    fixture.request,
                    fixture.plan_bytes,
                    fixture.parent,
                    (fixture.descriptor,),
                    (fixture.binding,),
                    tuple(raw for _, raw in fixture.input_pairs),
                    fixture.executable_paths,
                    directory,
                )
        self.assertEqual((unsupported.status, unsupported.attempts[0].outcome), ("unsupported", "unsupported"))
        self.assertEqual(unsupported.attempts[0].checker_status, "not_started")

        limits = {
            name: getattr(fixture.strategy.resource_request.requested, name)
            for name in (
                "wall_time_us", "cpu_time_us", "memory_bytes", "solver_calls",
                "generated_objects", "proof_bytes", "evidence_bytes", "output_bytes",
                "diagnostic_bytes", "nesting_depth",
            )
        }
        empty_parent = parent_budget(limits, scale=0)
        request = make_proof_search_portfolio_request(
            planning_result=fixture.plan_bytes,
            parent_budget=empty_parent,
            descriptors=(fixture.descriptor,),
            bindings=(fixture.binding,),
            artifacts=fixture.input_pairs,
        )
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            exhausted = run_portfolio(
                request,
                fixture.plan_bytes,
                empty_parent,
                (fixture.descriptor,),
                (fixture.binding,),
                tuple(raw for _, raw in fixture.input_pairs),
                fixture.executable_paths,
                directory,
            )
        self.assertEqual((exhausted.status, exhausted.attempts[0].outcome), ("exhausted", "exhausted"))
        self.assertEqual(exhausted.attempts[0].producer_reason_code, "BUDGET_INSUFFICIENT")
        self.assertEqual(exhausted.attempts[0].parent_budget_before_sha256, exhausted.attempts[0].parent_budget_after_sha256)

    def test_preobserved_cancellation_stops_without_checker_or_retry(self) -> None:
        event = Event()
        event.set()
        result = self.execute(cancel_event=event)
        self.assertEqual((result.status, result.mathematical_verdict), ("cancelled", "inconclusive"))
        self.assertEqual(len(result.attempts), 1)
        self.assertEqual((result.attempts[0].producer_status, result.attempts[0].checker_status), ("cancelled", "not_started"))

    def test_semantic_projection_is_stable_across_fresh_processes(self) -> None:
        from mathhead.proof_search_portfolio import proof_search_portfolio_semantic_bytes

        first = self.execute()
        second = self.execute()
        self.assertEqual(proof_search_portfolio_semantic_bytes(first), proof_search_portfolio_semantic_bytes(second))
        self.assertEqual(first.attempts[0].producer_worker_result_sha256, second.attempts[0].producer_worker_result_sha256)
        self.assertEqual(first.attempts[0].checker_worker_result_sha256, second.attempts[0].checker_worker_result_sha256)

    def test_swapped_executable_or_artifact_identity_is_rejected_prelaunch(self) -> None:
        from mathhead import proof_search_portfolio as portfolio

        fixture = self.fixture
        wrong_paths = (("0" * 64, str(fixture.executable)),)
        with mock.patch.object(portfolio, "supervise_worker") as supervisor:
            executable_result = portfolio.run_portfolio(
                fixture.request,
                fixture.plan_bytes,
                fixture.parent,
                (fixture.descriptor,),
                (fixture.binding,),
                tuple(raw for _, raw in fixture.input_pairs),
                wrong_paths,
                str(ROOT),
            )
            mutated = list(raw for _, raw in fixture.input_pairs)
            mutated[0] += b"x"
            artifact_result = portfolio.run_portfolio(
                fixture.request,
                fixture.plan_bytes,
                fixture.parent,
                (fixture.descriptor,),
                (fixture.binding,),
                tuple(mutated),
                fixture.executable_paths,
                str(ROOT),
            )
        supervisor.assert_not_called()
        self.assertEqual(executable_result.status, "invalid")
        self.assertEqual(artifact_result.status, "invalid")

    def test_manifest_closure_rejects_duplicate_surplus_stale_and_cross_plan_inputs(self) -> None:
        from mathhead import proof_search_portfolio as portfolio
        from tests.proof_search_portfolio.fixtures import (
            FallbackPortfolioFixture,
            canonical,
            self_hash,
        )

        fixture = self.fixture
        artifacts = tuple(raw for _, raw in fixture.input_pairs)
        malformed_request = json.loads(fixture.request)
        malformed_request["artifact_bindings"][0]["role"] = "portfolio_evidence"
        self_hash(malformed_request, "request_sha256")
        cases = (
            (
                "duplicate descriptor",
                fixture.request,
                fixture.plan_bytes,
                fixture.parent,
                (fixture.descriptor, fixture.descriptor),
                (fixture.binding,),
                artifacts,
                fixture.executable_paths,
            ),
            (
                "surplus binding",
                fixture.request,
                fixture.plan_bytes,
                fixture.parent,
                (fixture.descriptor,),
                (fixture.binding, fixture.binding),
                artifacts,
                fixture.executable_paths,
            ),
            (
                "surplus artifact",
                fixture.request,
                fixture.plan_bytes,
                fixture.parent,
                (fixture.descriptor,),
                (fixture.binding,),
                (*artifacts, b"surplus"),
                fixture.executable_paths,
            ),
            (
                "duplicate executable path",
                fixture.request,
                fixture.plan_bytes,
                fixture.parent,
                (fixture.descriptor,),
                (fixture.binding,),
                artifacts,
                (*fixture.executable_paths, *fixture.executable_paths),
            ),
            (
                "stale plan",
                fixture.request,
                fixture.plan_bytes[:-1],
                fixture.parent,
                (fixture.descriptor,),
                (fixture.binding,),
                artifacts,
                fixture.executable_paths,
            ),
            (
                "stale parent",
                fixture.request,
                fixture.plan_bytes,
                fixture.parent[:-1],
                (fixture.descriptor,),
                (fixture.binding,),
                artifacts,
                fixture.executable_paths,
            ),
            (
                "reserved evidence role",
                canonical(malformed_request),
                fixture.plan_bytes,
                fixture.parent,
                (fixture.descriptor,),
                (fixture.binding,),
                artifacts,
                fixture.executable_paths,
            ),
        )
        multi = FallbackPortfolioFixture()
        multi_case = (
            multi.request,
            multi.plan_bytes,
            multi.parent,
            multi.descriptors,
            tuple(reversed(multi.bindings)),
            tuple(raw for _, raw in multi.input_pairs),
            multi.executable_paths,
        )
        with mock.patch.object(portfolio, "supervise_worker") as supervisor:
            for label, request, plan, parent, descriptors, bindings, bound_artifacts, paths in cases:
                with self.subTest(label=label):
                    result = portfolio.run_portfolio(
                        request,
                        plan,
                        parent,
                        descriptors,
                        bindings,
                        bound_artifacts,
                        paths,
                        str(ROOT),
                    )
                    self.assertEqual((result.status, result.reason_code), ("invalid", "PORTFOLIO_INPUT_INVALID"))
            cross_plan = portfolio.run_portfolio(*multi_case, str(ROOT))
        supervisor.assert_not_called()
        self.assertEqual((cross_plan.status, cross_plan.reason_code), ("invalid", "PORTFOLIO_INPUT_INVALID"))


if __name__ == "__main__":
    unittest.main()
