from __future__ import annotations

import copy
import hashlib
import json
from typing import Any, Callable

from mathhead.canonical_normalization import (
    canonical_normalization_result_bytes,
    canonical_obligation_bytes,
    normalize_canonical_obligations,
)
from mathhead.domain_assumptions import (
    domain_assumption_result_bytes,
    normalize_domain_assumptions,
)
from mathhead.problem_intake import intake_problem, problem_intake_result_bytes
from mathhead.problem_readings import analyze_problem_readings, reading_analysis_result_bytes
from mathhead.problem_sessions import (
    make_problem_session_command,
    make_session_artifact_link,
    make_session_obligation,
    transition_problem_session,
)
from mathhead.proof_obligations import (
    decompose_proof_obligations,
    proof_obligation_result_bytes,
)
from tools.validate_problem_ir_contract import minimal_problem_ir
from tools.validate_theory_plugin_contract import (
    descriptor_basis_sha256,
    minimal_theory_plugin,
)


def canonical(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("ascii")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class RouteFixture:
    def __init__(self) -> None:
        problem = minimal_problem_ir()
        for registry in (
            "source_documents", "source_spans", "domains", "variables",
            "expressions", "relations", "statements", "definitions",
            "assumptions", "goals", "readings",
        ):
            problem[registry].sort(key=lambda item: item["id"])
        intake = intake_problem({"schema": "mathhead.problem-intake.v1", "problem": problem})
        readings = analyze_problem_readings(problem_intake_result_bytes(intake))
        domains = normalize_domain_assumptions(reading_analysis_result_bytes(readings))
        proof = decompose_proof_obligations(domain_assumption_result_bytes(domains))
        normalization = normalize_canonical_obligations(proof_obligation_result_bytes(proof))
        if normalization.status != "normalized":
            raise AssertionError(normalization)
        candidate = normalization.candidates[0]
        obligation = candidate.obligations[1]
        normalization_bytes = canonical_normalization_result_bytes(normalization)
        obligation_bytes = canonical_obligation_bytes(obligation)
        context_bytes = canonical(
            {"context_id": "context_capability", "schema": "mathhead.theory-context.v1"}
        )
        context_sha256 = sha(context_bytes)
        payloads = {
            sha(context_bytes): context_bytes,
            sha(normalization_bytes): normalization_bytes,
        }
        context_link = make_session_artifact_link(
            context_bytes,
            role="context",
            media_type="application/json",
            artifact_schema="mathhead.theory-context.v1",
            context_sha256=context_sha256,
        )
        analysis_link = make_session_artifact_link(
            normalization_bytes,
            role="problem_analysis",
            media_type="application/json",
            artifact_schema="mathhead.canonical-normalization-result.v1",
            context_sha256=context_sha256,
            reading_id=candidate.reading_id,
        )
        create = make_problem_session_command(
            command_id="create_capability_session",
            kind="create_session",
            session_id="session_capability",
            context_sha256=context_sha256,
            analysis_artifact_sha256s=(sha(normalization_bytes),),
            introduced_artifacts=tuple(
                sorted((context_link, analysis_link), key=lambda item: item.sha256)
            ),
        )
        first = transition_problem_session(
            create,
            (),
            tuple(payloads[digest] for digest in sorted(payloads)),
        )
        obligation_link = make_session_artifact_link(
            obligation_bytes,
            role="obligation",
            media_type="application/json",
            artifact_schema="mathhead.canonical-obligation.v1",
            context_sha256=context_sha256,
            reading_id=candidate.reading_id,
        )
        payloads[sha(obligation_bytes)] = obligation_bytes
        record = make_session_obligation(
            record_id="obligation_capability",
            generation=0,
            obligation_id=obligation.source_obligation_id,
            obligation_sha256=sha(obligation_bytes),
            context_sha256=context_sha256,
            reading_id=candidate.reading_id,
            state="open",
        )
        put = make_problem_session_command(
            command_id="put_capability_obligation",
            kind="put_obligation",
            session_id="session_capability",
            expected_head_sha256=first.head_sha256,
            introduced_artifacts=(obligation_link,),
            record=record,
        )
        result = transition_problem_session(
            put,
            first.events,
            tuple(payloads[digest] for digest in sorted(payloads)),
        )
        if result.status != "updated" or result.revision_value is None:
            raise AssertionError(result)
        revision = result.revision_value
        self.result = result
        self.fragment = None
        self.payloads = payloads
        self.artifacts = (*result.events, *(payloads[digest] for digest in revision.artifact_sha256s))
        self.request_fields: dict[str, object] = {
            "session_id": result.session_id,
            "session_head_sha256": result.head_sha256,
            "session_context_sha256": context_sha256,
            "event_sha256s": revision.event_sha256s,
            "session_artifact_sha256s": revision.artifact_sha256s,
            "normalization_result_sha256": sha(normalization_bytes),
            "reading_id": candidate.reading_id,
            "session_obligation_record_id": "obligation_capability",
            "obligation_artifact_sha256": sha(obligation_bytes),
            "obligation_semantic_sha256": obligation.semantic_sha256,
            "local_context_semantic_sha256": obligation.local_context_semantic_sha256,
            "capability_kind": "decision",
            "operation": "solve",
            "replay_mode": "deterministic",
            "evidence_format": {
                "format_id": "org.mathhead.proof",
                "major": 1,
                "minor": 0,
                "required_features": [],
            },
        }


def plugin_bytes(
    fragment: object,
    *,
    suffix: str = "alpha",
    base_cost: int = 10,
    priority: int = 100,
    mutation: Callable[[dict[str, Any]], None] | None = None,
) -> bytes:
    value = copy.deepcopy(minimal_theory_plugin())
    if suffix != "alpha":
        namespace_suffix = suffix.replace("_", "-")
        value["plugin_id"] = f"org.mathhead.fixture-{namespace_suffix}"
        value["display_name"] = f"Fixture {suffix}"
        value["implementation"]["package"] = f"fixture_{suffix}"
        value["implementation"]["entry_point"] = f"fixture_{suffix}.plugin:Plugin"
        value["components"]["producer"]["component_id"] = f"producer_{suffix}"
        value["components"]["checker"]["component_id"] = f"checker_{suffix}"
        value["capabilities"][0]["capability_id"] = f"capability_{suffix}"
        for operation in value["operations"]:
            operation["component_id"] = (
                f"checker_{suffix}" if operation["operation"] == "check" else f"producer_{suffix}"
            )
    capability = value["capabilities"][0]
    capability["priority"] = priority
    capability["cost_model"]["base"] = base_cost
    capability["fragment"].update(
        domains=list(fragment.domains),
        quantifiers=list(fragment.quantifiers),
        expression_kinds=list(fragment.expression_kinds),
        relation_kinds=list(fragment.relation_kinds),
        maximum_polynomial_degree=fragment.polynomial_degree,
        maximum_quantifier_depth=fragment.quantifier_depth,
        maximum_variables=fragment.variables,
        required_theory_features=list(fragment.theory_features),
    )
    if mutation is not None:
        mutation(value)
    value["replay"]["descriptor_basis_sha256"] = descriptor_basis_sha256(value)
    return canonical(value)
