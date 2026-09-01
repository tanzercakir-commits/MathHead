from __future__ import annotations

import ast
import copy
import dataclasses
import hashlib
import json
import os
from pathlib import Path
import pickle
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import mathhead.problem_sessions as sessions  # noqa: E402
import mathhead.problem_session_store as session_store  # noqa: E402
from mathhead.problem_session_store import (  # noqa: E402
    PROBLEM_SESSION_STORE_CONTRACT_SHA256,
    ProblemSessionStoreError,
    load_problem_session,
    persist_problem_session,
    recover_problem_session_store,
)
from mathhead.problem_sessions import (  # noqa: E402
    PROBLEM_SESSION_CONTRACT_SHA256,
    ProblemSessionResult,
    ProblemSessionValidationError,
    SessionDefinition,
    make_problem_session_command,
    make_session_artifact_link,
    make_session_attempt,
    make_session_definition,
    make_session_lemma,
    make_session_obligation,
    parse_problem_session_result,
    problem_session_result_to_bytes,
    transition_problem_session,
    validate_problem_session_result,
)

SCHEMA_HASHES = {
    "problem-session-artifact-link-v1.schema.json": "562faa38159bc98c4a1fb37c107afc20b933244b7f1cd3257b63c80f849a4133",
    "problem-session-attempt-v1.schema.json": "e14f6d0a9d1711bca56bfd195430eb081a58a5718c8c987bc7823df5beeeeb4b",
    "problem-session-command-v1.schema.json": "f395dfd35e14d88b5fd8a8b92613b1fcc355f8d72332483425774e2a8feceac1",
    "problem-session-definition-v1.schema.json": "d00d200ce97494b08ed7fc1b6b7d32f805f4a6c8ec4bd20d942fa426d586bb46",
    "problem-session-event-v1.schema.json": "983be63a2ee1096b8e9f550f0c3d3a1fe49fdaab64565927b6fd66e4b2247582",
    "problem-session-invalidation-v1.schema.json": "fd8dccac3d9437dafdba236d7d40619779661bd32eebbc204da8b08500b6700b",
    "problem-session-lemma-v1.schema.json": "79a446b77cb45f80eded2af13fda66daccc7445bf817161b2eaa6ab1debd6095",
    "problem-session-obligation-state-v1.schema.json": "150c0dfb2649fceb7057cd607e17bf8910ba13ffd97c7a1449995d30847c742e",
    "problem-session-result-v1.schema.json": "4d06b76fb9cca2e646c0a7b95a49d6926b83bf70b54246a40417d9667ba9cd53",
    "problem-session-revision-v1.schema.json": "02b89fd663f6506a6d993900635acb5ac0cd2c283b2f9d0994378e2d35882311",
    "problem-session-store-head-v1.schema.json": "a5bed15dda9e8c229687f1a89ba1ca9770e17d72314d16b5de63417472f3f683",
}


def canonical(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode()


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def self_hash(value: dict[str, object], field: str) -> None:
    value[field] = None
    value[field] = sha(canonical(value))


class Fixture:
    def __init__(self, session_id: str = "session_alpha") -> None:
        self.session_id = session_id
        self.payloads: dict[str, bytes] = {}
        self.events: tuple[bytes, ...] = ()
        self.result: ProblemSessionResult | None = None
        context = canonical({"context_id": "ctx_alpha", "schema": "mathhead.theory-context.v1"})
        analysis = canonical(
            {"schema": "mathhead.unsupported-explanation-result.v1", "status": "explained"}
        )
        self.context_sha = sha(context)
        self.analysis_sha = sha(analysis)
        context_link = self.add(
            context,
            role="context",
            artifact_schema="mathhead.theory-context.v1",
            context_sha256=self.context_sha,
        )
        analysis_link = self.add(
            analysis,
            role="problem_analysis",
            artifact_schema="mathhead.unsupported-explanation-result.v1",
            context_sha256=self.context_sha,
        )
        command = make_problem_session_command(
            command_id="create_session_000",
            kind="create_session",
            session_id=session_id,
            context_sha256=self.context_sha,
            analysis_artifact_sha256s=(self.analysis_sha,),
            introduced_artifacts=tuple(sorted((context_link, analysis_link), key=lambda item: item.sha256)),
        )
        result = self.apply(command)
        if result.status != "updated":
            raise AssertionError(result)

    @property
    def artifacts(self) -> tuple[bytes, ...]:
        return tuple(self.payloads[key] for key in sorted(self.payloads))

    def add(
        self,
        data: bytes,
        *,
        role: str,
        artifact_schema: str | None,
        context_sha256: str | None = None,
        reading_id: str | None = None,
        retained_tier: str = "none",
        depends_on_sha256s: tuple[str, ...] = (),
        media_type: str = "application/json",
    ):
        self.payloads[sha(data)] = data
        return make_session_artifact_link(
            data,
            role=role,
            media_type=media_type,
            artifact_schema=artifact_schema,
            context_sha256=context_sha256,
            reading_id=reading_id,
            retained_tier=retained_tier,
            depends_on_sha256s=depends_on_sha256s,
        )

    def apply(self, command: bytes) -> ProblemSessionResult:
        result = transition_problem_session(command, self.events, self.artifacts)
        if result.status == "updated":
            assert result.events is not None
            self.events = result.events
            self.result = result
        return result

    def add_definition(
        self,
        record_id: str = "definition_alpha",
        generation: int = 0,
        dependencies: tuple[str, ...] = (),
        command_id: str | None = None,
    ) -> ProblemSessionResult:
        payload = canonical(
            {"definition_id": record_id, "generation": generation, "schema": "mathhead.definition-payload.v1"}
        )
        link = self.add(
            payload,
            role="definition_payload",
            artifact_schema="mathhead.definition-payload.v1",
            context_sha256=self.context_sha,
        )
        record = make_session_definition(
            record_id=record_id,
            generation=generation,
            definition_id=record_id,
            primary_artifact_sha256=sha(payload),
            problem_ir_sha256=self.analysis_sha,
            theory_context_sha256=self.context_sha,
            declaration_sha256=sha(canonical({"declaration": record_id, "generation": generation})),
            depends_on_record_sha256s=dependencies,
        )
        return self.apply(
            make_problem_session_command(
                command_id=command_id or f"put_{record_id}_{generation}",
                kind="put_definition",
                session_id=self.session_id,
                expected_head_sha256=self.result.head_sha256 if self.result else None,
                introduced_artifacts=(link,),
                record=record,
            )
        )

    def add_obligation(
        self,
        *,
        record_id: str = "obligation_alpha",
        generation: int = 0,
        state: str = "open",
        evidence: tuple[str, ...] = (),
        dependencies: tuple[str, ...] = (),
    ) -> ProblemSessionResult:
        payload = canonical(
            {"obligation_id": record_id, "schema": "mathhead.canonical-obligation.v1"}
        )
        links = []
        if sha(payload) not in self.payloads:
            links.append(
                self.add(
                    payload,
                    role="obligation",
                    artifact_schema="mathhead.canonical-obligation.v1",
                    context_sha256=self.context_sha,
                    reading_id="reading_alpha",
                )
            )
        record = make_session_obligation(
            record_id=record_id,
            generation=generation,
            obligation_id=record_id,
            obligation_sha256=sha(payload),
            context_sha256=self.context_sha,
            reading_id="reading_alpha",
            state=state,
            evidence_sha256s=evidence,
            depends_on_record_sha256s=dependencies,
        )
        return self.apply(
            make_problem_session_command(
                command_id=f"put_{record_id}_{generation}_{state}",
                kind="put_obligation",
                session_id=self.session_id,
                expected_head_sha256=self.result.head_sha256 if self.result else None,
                introduced_artifacts=tuple(links),
                record=record,
            )
        )


class ProblemSessionTests(unittest.TestCase):
    def test_contract_schema_and_source_bindings_are_exact(self) -> None:
        self.assertEqual(
            sha((ROOT / "docs/contracts/MH-C-PROBLEM-SESSION-001.json").read_bytes()),
            PROBLEM_SESSION_CONTRACT_SHA256,
        )
        self.assertEqual(
            sha((ROOT / "docs/contracts/MH-C-PROBLEM-SESSION-STORE-001.json").read_bytes()),
            PROBLEM_SESSION_STORE_CONTRACT_SHA256,
        )
        for name, expected in SCHEMA_HASHES.items():
            self.assertEqual(
                sha((ROOT / "docs/contracts/schemas" / name).read_bytes()), expected, name
            )

    def test_root_replay_and_result_round_trip_are_exact(self) -> None:
        fixture = Fixture()
        result = fixture.result
        assert result is not None and result.events is not None
        self.assertEqual((result.status, result.revision, result.event_count), ("updated", 0, 1))
        replayed = transition_problem_session(None, result.events, result.artifacts)
        self.assertEqual(replayed.status, "unchanged")
        self.assertEqual(replayed.revision_value, result.revision_value)
        encoded = problem_session_result_to_bytes(result)
        self.assertEqual(parse_problem_session_result(encoded, result.events, result.artifacts), result)
        self.assertFalse(result.mathematical_authority)

    def test_all_record_kinds_and_failed_attempts_survive_replay(self) -> None:
        fixture = Fixture()
        definition = fixture.add_definition()
        definition_sha = definition.revision_value.definitions[0].record_sha256  # type: ignore[union-attr]
        statement = canonical({"lemma": "alpha", "schema": "mathhead.lemma-statement.v1"})
        lemma_link = fixture.add(
            statement,
            role="lemma_statement",
            artifact_schema="mathhead.lemma-statement.v1",
            context_sha256=fixture.context_sha,
            reading_id="reading_alpha",
            retained_tier="unchecked",
        )
        lemma = make_session_lemma(
            record_id="lemma_alpha",
            generation=0,
            lemma_id="lemma_alpha",
            statement_sha256=sha(statement),
            primary_artifact_sha256=sha(statement),
            context_sha256=fixture.context_sha,
            reading_id="reading_alpha",
            depends_on_record_sha256s=(definition_sha,),
        )
        lemma_result = fixture.apply(
            make_problem_session_command(
                command_id="put_lemma_000",
                kind="put_lemma",
                session_id=fixture.session_id,
                expected_head_sha256=fixture.result.head_sha256,  # type: ignore[union-attr]
                introduced_artifacts=(lemma_link,),
                record=lemma,
            )
        )
        obligation = fixture.add_obligation(dependencies=(lemma.record_sha256,))
        obligation_sha = obligation.revision_value.obligations[0].record_sha256  # type: ignore[union-attr]
        observation = b"bounded failure observation\n"
        observation_link = fixture.add(
            observation,
            role="attempt_observation",
            media_type="text/plain",
            artifact_schema=None,
            context_sha256=fixture.context_sha,
            reading_id="reading_alpha",
        )
        attempt = make_session_attempt(
            record_id="attempt_alpha",
            generation=0,
            attempt_id="attempt_alpha",
            strategy_id="strategy.alpha",
            outcome="failed",
            context_sha256=fixture.context_sha,
            reading_id="reading_alpha",
            obligation_record_sha256s=(obligation_sha,),
            observation_artifact_sha256s=(sha(observation),),
            diagnostic_codes=("NO_CERTIFICATE",),
            depends_on_record_sha256s=(obligation_sha,),
        )
        attempted = fixture.apply(
            make_problem_session_command(
                command_id="put_attempt_000",
                kind="put_attempt",
                session_id=fixture.session_id,
                expected_head_sha256=fixture.result.head_sha256,  # type: ignore[union-attr]
                introduced_artifacts=(observation_link,),
                record=attempt,
            )
        )
        self.assertEqual(attempted.status, "updated")
        revision = attempted.revision_value
        assert revision is not None
        self.assertEqual((len(revision.definitions), len(revision.lemmas)), (1, 1))
        self.assertEqual((len(revision.obligations), len(revision.attempts)), (1, 1))
        self.assertEqual(revision.attempts[0].outcome, "failed")
        replayed = transition_problem_session(None, attempted.events, attempted.artifacts)
        self.assertEqual(replayed.revision_value, revision)
        self.assertEqual(lemma_result.status, "updated")

    def test_every_attempt_outcome_is_retained_without_execution(self) -> None:
        for outcome in ("succeeded", "failed", "cancelled", "timed_out", "exhausted"):
            with self.subTest(outcome=outcome):
                fixture = Fixture(session_id=f"session_{outcome}")
                obligation = fixture.add_obligation()
                obligation_record = obligation.revision_value.obligations[0]  # type: ignore[union-attr]
                attempt = make_session_attempt(
                    record_id=f"attempt_{outcome}",
                    generation=0,
                    attempt_id=f"attempt_{outcome}",
                    strategy_id="strategy.bounded",
                    outcome=outcome,
                    context_sha256=fixture.context_sha,
                    reading_id="reading_alpha",
                    obligation_record_sha256s=(obligation_record.record_sha256,),
                    diagnostic_codes=(f"OUTCOME_{outcome.upper()}",),
                    depends_on_record_sha256s=(obligation_record.record_sha256,),
                )
                result = fixture.apply(
                    make_problem_session_command(
                        command_id=f"put_attempt_{outcome}",
                        kind="put_attempt",
                        session_id=fixture.session_id,
                        expected_head_sha256=fixture.result.head_sha256,  # type: ignore[union-attr]
                        record=attempt,
                    )
                )
                self.assertEqual(result.status, "updated")
                self.assertEqual(result.revision_value.attempts[0].outcome, outcome)  # type: ignore[union-attr]
                replay = transition_problem_session(None, result.events, result.artifacts)
                self.assertEqual(replay.revision_value, result.revision_value)

    def test_complete_obligation_lifecycle_preserves_stale_generations(self) -> None:
        fixture = Fixture()
        opened = fixture.add_obligation(state="open")
        self.assertEqual(opened.revision_value.obligations[0].state, "open")  # type: ignore[union-attr]
        blocked = fixture.add_obligation(generation=1, state="blocked")
        self.assertEqual(blocked.revision_value.obligations[0].state, "blocked")  # type: ignore[union-attr]

        evidence = canonical({"schema": "mathhead.checker-result.v1", "status": "verified"})
        evidence_link = fixture.add(
            evidence,
            role="evidence",
            artifact_schema="mathhead.checker-result.v1",
            context_sha256=fixture.context_sha,
            reading_id="reading_alpha",
            retained_tier="checker_attestation",
        )
        obligation_payload = canonical(
            {"obligation_id": "obligation_alpha", "schema": "mathhead.canonical-obligation.v1"}
        )
        discharged_record = make_session_obligation(
            record_id="obligation_alpha",
            generation=2,
            obligation_id="obligation_alpha",
            obligation_sha256=sha(obligation_payload),
            context_sha256=fixture.context_sha,
            reading_id="reading_alpha",
            state="discharged",
            evidence_sha256s=(sha(evidence),),
        )
        discharged = fixture.apply(
            make_problem_session_command(
                command_id="put_obligation_alpha_2_discharged",
                kind="put_obligation",
                session_id=fixture.session_id,
                expected_head_sha256=fixture.result.head_sha256,  # type: ignore[union-attr]
                introduced_artifacts=(evidence_link,),
                record=discharged_record,
            )
        )
        self.assertEqual(discharged.revision_value.obligations[0].state, "discharged")  # type: ignore[union-attr]
        reopened = fixture.add_obligation(generation=3, state="reopened")
        superseded = fixture.add_obligation(generation=4, state="superseded")
        revision = superseded.revision_value
        assert revision is not None
        self.assertEqual(reopened.status, "updated")
        self.assertEqual(revision.obligations[0].state, "superseded")
        self.assertEqual(len(revision.stale_record_sha256s), 4)
        self.assertIn(sha(evidence), revision.artifact_sha256s)
        self.assertEqual(
            transition_problem_session(None, superseded.events, superseded.artifacts).revision_value,
            revision,
        )

    def test_replacement_invalidates_transitive_dependents_but_keeps_history(self) -> None:
        fixture = Fixture()
        first = fixture.add_definition()
        first_sha = first.revision_value.definitions[0].record_sha256  # type: ignore[union-attr]
        fixture.add_obligation(record_id="obligation_dep", dependencies=(first_sha,))
        replaced = fixture.add_definition(generation=1)
        revision = replaced.revision_value
        assert revision is not None
        self.assertEqual(len(revision.definitions), 1)
        self.assertEqual(revision.definitions[0].generation, 1)
        self.assertEqual(revision.obligations, ())
        self.assertEqual(len(revision.stale_record_sha256s), 2)
        self.assertEqual(len(revision.invalidation_sha256s), 2)
        history = b"".join(replaced.events or ())
        self.assertIn(first_sha.encode(), history)

    def test_context_revision_invalidates_every_context_bound_record(self) -> None:
        fixture = Fixture()
        fixture.add_definition()
        fixture.add_obligation()
        old_head = fixture.result.head_sha256  # type: ignore[union-attr]
        new_context = canonical({"context_id": "ctx_beta", "schema": "mathhead.theory-context.v1"})
        new_analysis = canonical({"schema": "mathhead.canonical-normalization-result.v1", "status": "normalized"})
        new_context_sha = sha(new_context)
        context_link = fixture.add(
            new_context,
            role="context",
            artifact_schema="mathhead.theory-context.v1",
            context_sha256=new_context_sha,
        )
        analysis_link = fixture.add(
            new_analysis,
            role="problem_analysis",
            artifact_schema="mathhead.canonical-normalization-result.v1",
            context_sha256=new_context_sha,
        )
        command = make_problem_session_command(
            command_id="replace_context_001",
            kind="replace_context",
            session_id=fixture.session_id,
            expected_head_sha256=old_head,
            context_sha256=new_context_sha,
            analysis_artifact_sha256s=(sha(new_analysis),),
            introduced_artifacts=tuple(sorted((context_link, analysis_link), key=lambda item: item.sha256)),
        )
        result = fixture.apply(command)
        revision = result.revision_value
        assert revision is not None
        self.assertEqual(revision.context_sha256, new_context_sha)
        self.assertEqual((revision.definitions, revision.obligations), ((), ()))
        self.assertEqual(len(revision.stale_record_sha256s), 2)
        self.assertTrue(all(item in b"".join(result.events or ()) for item in (b"context_revised",)))

    def test_retirement_invalidates_dependents_and_cannot_be_repeated(self) -> None:
        fixture = Fixture()
        definition = fixture.add_definition()
        definition_sha = definition.revision_value.definitions[0].record_sha256  # type: ignore[union-attr]
        fixture.add_obligation(record_id="obligation_dep", dependencies=(definition_sha,))
        command = make_problem_session_command(
            command_id="retire_definition_001",
            kind="retire_record",
            session_id=fixture.session_id,
            expected_head_sha256=fixture.result.head_sha256,  # type: ignore[union-attr]
            target_record_kind="definition",
            target_record_id="definition_alpha",
            reason_code="USER_RETIRED",
        )
        retired = fixture.apply(command)
        revision = retired.revision_value
        assert revision is not None
        self.assertEqual(revision.definitions, ())
        self.assertIn(definition_sha, revision.retired_record_sha256s)
        again = transition_problem_session(
            make_problem_session_command(
                command_id="retire_definition_002",
                kind="retire_record",
                session_id=fixture.session_id,
                expected_head_sha256=retired.head_sha256,
                target_record_kind="definition",
                target_record_id="definition_alpha",
                reason_code="USER_RETIRED",
            ),
            retired.events,
            retired.artifacts,
        )
        self.assertEqual((again.status, again.reason_code), ("conflict", "RECORD_NOT_CURRENT"))

    def test_idempotency_stale_heads_and_command_id_reuse_fail_closed(self) -> None:
        fixture = Fixture()
        first = fixture.add_definition()
        command = first.events[-1]  # event bytes, intentionally not a command
        invalid = transition_problem_session(command, first.events, first.artifacts)
        self.assertEqual(invalid.status, "invalid")
        event_value = json.loads(first.events[-1])
        exact_command = canonical(event_value["command"])
        retry = transition_problem_session(exact_command, first.events, first.artifacts)
        self.assertEqual((retry.status, retry.reason_code), ("unchanged", "IDEMPOTENT_RETRY"))
        stale_record = make_session_definition(
            record_id="definition_beta",
            generation=0,
            definition_id="definition_beta",
            primary_artifact_sha256=first.revision_value.definitions[0].primary_artifact_sha256,  # type: ignore[union-attr]
            problem_ir_sha256=fixture.analysis_sha,
            theory_context_sha256=fixture.context_sha,
            declaration_sha256="2" * 64,
        )
        stale = make_problem_session_command(
            command_id="stale_command",
            kind="put_definition",
            session_id=fixture.session_id,
            expected_head_sha256=first.events[0] and json.loads(first.events[0])["event_sha256"],
            record=stale_record,
        )
        self.assertEqual(
            transition_problem_session(stale, first.events, first.artifacts).status, "conflict"
        )

    def test_missing_surplus_reordered_and_corrupt_inputs_fail_closed(self) -> None:
        fixture = Fixture()
        result = fixture.result
        assert result is not None and result.events is not None and result.artifacts is not None
        self.assertEqual(transition_problem_session(None, result.events, result.artifacts[:-1]).status, "invalid")
        surplus = canonical({"schema": "mathhead.surplus.v1"})
        extra = tuple(item for _, item in sorted((sha(item), item) for item in (*result.artifacts, surplus)))
        self.assertEqual(transition_problem_session(None, result.events, extra).status, "invalid")
        self.assertEqual(transition_problem_session(None, result.events, tuple(reversed(result.artifacts))).status, "invalid")
        damaged = result.events[0][:-2] + b"x\n"
        self.assertEqual(transition_problem_session(None, (damaged,), result.artifacts).status, "invalid")

    def test_repaired_parent_event_and_result_forgery_are_rejected(self) -> None:
        fixture = Fixture()
        result = fixture.add_definition()
        events = list(result.events or ())
        value = json.loads(events[1])
        value["parent_event_sha256"] = "0" * 64
        self_hash(value, "event_sha256")
        events[1] = canonical(value)
        self.assertEqual(
            transition_problem_session(None, tuple(events), result.artifacts).status, "invalid"
        )
        encoded = json.loads(problem_session_result_to_bytes(result))
        encoded["head_sha256"] = "0" * 64
        self_hash(encoded, "result_sha256")
        with self.assertRaises(ProblemSessionValidationError):
            parse_problem_session_result(canonical(encoded), result.events, result.artifacts)

    def test_generation_cross_reading_and_stale_dependency_guards(self) -> None:
        fixture = Fixture()
        definition = fixture.add_definition()
        definition_record = definition.revision_value.definitions[0]  # type: ignore[union-attr]
        wrong_generation = make_session_definition(
            record_id="definition_alpha",
            generation=3,
            definition_id="definition_alpha",
            primary_artifact_sha256=definition_record.primary_artifact_sha256,
            problem_ir_sha256=fixture.analysis_sha,
            theory_context_sha256=fixture.context_sha,
            declaration_sha256="3" * 64,
        )
        command = make_problem_session_command(
            command_id="wrong_generation",
            kind="put_definition",
            session_id=fixture.session_id,
            expected_head_sha256=definition.head_sha256,
            record=wrong_generation,
        )
        self.assertEqual(transition_problem_session(command, definition.events, definition.artifacts).status, "conflict")
        statement = canonical({"schema": "mathhead.lemma-statement.v1"})
        link = fixture.add(
            statement,
            role="lemma_statement",
            artifact_schema="mathhead.lemma-statement.v1",
            context_sha256=fixture.context_sha,
            reading_id="reading_beta",
        )
        other_reading = make_session_lemma(
            record_id="lemma_beta",
            generation=0,
            lemma_id="lemma_beta",
            statement_sha256=sha(statement),
            primary_artifact_sha256=sha(statement),
            context_sha256=fixture.context_sha,
            reading_id="reading_beta",
            depends_on_record_sha256s=(definition_record.record_sha256,),
        )
        cross = make_problem_session_command(
            command_id="cross_reading",
            kind="put_lemma",
            session_id=fixture.session_id,
            expected_head_sha256=definition.head_sha256,
            introduced_artifacts=(link,),
            record=other_reading,
        )
        # Definitions are shared (null reading), so this dependency is permitted.
        self.assertEqual(fixture.apply(cross).status, "updated")

    def test_lemma_tier_and_obligation_evidence_rules_are_closed(self) -> None:
        with self.assertRaises(ProblemSessionValidationError):
            make_session_lemma(
                record_id="lemma_bad",
                generation=0,
                lemma_id="lemma_bad",
                statement_sha256="1" * 64,
                primary_artifact_sha256="1" * 64,
                context_sha256="2" * 64,
                retained_tier="checker_attestation",
            )
        with self.assertRaises(ProblemSessionValidationError):
            make_session_obligation(
                record_id="obligation_bad",
                generation=0,
                obligation_id="obligation_bad",
                obligation_sha256="1" * 64,
                context_sha256="2" * 64,
                reading_id="reading_alpha",
                state="discharged",
            )

    def test_values_are_closed_immutable_copy_safe_and_not_pickle_authority(self) -> None:
        fixture = Fixture()
        result = fixture.result
        assert result is not None
        with self.assertRaises(PermissionError):
            ProblemSessionResult()  # type: ignore[call-arg]
        with self.assertRaises(dataclasses.FrozenInstanceError):
            result.status = "updated"  # type: ignore[misc]
        with self.assertRaises(TypeError):
            pickle.dumps(result)
        self.assertIs(copy.copy(result), result)
        self.assertIs(copy.deepcopy(result), result)
        with self.assertRaises(TypeError):
            class Forged(SessionDefinition):
                pass
        forged = object.__new__(ProblemSessionResult)
        for item in dataclasses.fields(ProblemSessionResult):
            object.__setattr__(forged, item.name, getattr(result, item.name))
        object.__setattr__(forged, "head_sha256", "0" * 64)
        with self.assertRaises(ProblemSessionValidationError):
            validate_problem_session_result(forged)

    def test_budget_and_fatal_control_exceptions_never_return_partial_state(self) -> None:
        fixture = Fixture()
        with mock.patch.object(sessions, "MAX_EVENTS", 0):
            exhausted = transition_problem_session(None, fixture.events, fixture.artifacts)
        self.assertEqual(exhausted.status, "exhausted")
        self.assertIsNone(exhausted.head_sha256)
        with mock.patch.object(sessions, "_artifact_map", side_effect=MemoryError("fatal")):
            with self.assertRaises(MemoryError):
                transition_problem_session(None, fixture.events, fixture.artifacts)

    def test_cross_process_hash_seed_determinism(self) -> None:
        script = r'''
import hashlib,json
from mathhead.problem_sessions import make_problem_session_command,make_session_artifact_link,transition_problem_session
c=lambda v:(json.dumps(v,sort_keys=True,separators=(",",":"))+"\n").encode()
s=lambda b:hashlib.sha256(b).hexdigest()
ctx=c({"schema":"mathhead.theory-context.v1"}); ana=c({"schema":"mathhead.problem-intake-result.v1"})
ch,ah=s(ctx),s(ana)
links=tuple(sorted((make_session_artifact_link(ctx,role="context",artifact_schema="mathhead.theory-context.v1",context_sha256=ch),make_session_artifact_link(ana,role="problem_analysis",artifact_schema="mathhead.problem-intake-result.v1",context_sha256=ch)),key=lambda x:x.sha256))
cmd=make_problem_session_command(command_id="create_1",kind="create_session",session_id="session_1",context_sha256=ch,analysis_artifact_sha256s=(ah,),introduced_artifacts=links)
arts=tuple(v for _,v in sorted((s(v),v) for v in (ctx,ana)))
r=transition_problem_session(cmd,(),arts)
print(r.head_sha256,r.view_sha256,r.result_sha256)
'''
        outputs = []
        for seed in ("1", "77"):
            env = dict(os.environ)
            env["PYTHONHASHSEED"] = seed
            env["PYTHONPATH"] = str(SRC)
            outputs.append(
                subprocess.run(
                    [sys.executable, "-c", script],
                    cwd=ROOT,
                    env=env,
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout
            )
        self.assertEqual(outputs[0], outputs[1])

    def test_store_is_atomic_replayable_and_idempotent(self) -> None:
        fixture = Fixture()
        create_event = json.loads(fixture.events[0])
        command = canonical(create_event["command"])
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve() / "store"
            stored = persist_problem_session(root, command, fixture.artifacts)
            self.assertEqual(stored.status, "updated")
            loaded = load_problem_session(root, fixture.session_id)
            self.assertEqual(loaded.status, "unchanged")
            self.assertEqual(loaded.revision_value, stored.revision_value)
            head = root / "sessions" / sha(fixture.session_id.encode())[:2] / sha(fixture.session_id.encode())[2:] / "HEAD"
            before = head.read_bytes()
            retry = persist_problem_session(root, command, ())
            self.assertEqual(retry.reason_code, "IDEMPOTENT_RETRY")
            self.assertEqual(head.read_bytes(), before)
            self.assertEqual(head.stat().st_mode & 0o777, 0o444)

    def test_store_rejects_stale_writer_corruption_links_and_unsafe_roots(self) -> None:
        fixture = Fixture()
        command = canonical(json.loads(fixture.events[0])["command"])
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary).resolve()
            root = base / "store"
            stored = persist_problem_session(root, command, fixture.artifacts)
            definition_payload = canonical({"schema": "mathhead.definition-payload.v1", "v": 1})
            link = make_session_artifact_link(
                definition_payload,
                role="definition_payload",
                artifact_schema="mathhead.definition-payload.v1",
                context_sha256=fixture.context_sha,
            )
            record = make_session_definition(
                record_id="definition_stale",
                generation=0,
                definition_id="definition_stale",
                primary_artifact_sha256=sha(definition_payload),
                problem_ir_sha256=fixture.analysis_sha,
                theory_context_sha256=fixture.context_sha,
                declaration_sha256="9" * 64,
            )
            stale = make_problem_session_command(
                command_id="stale_store_writer",
                kind="put_definition",
                session_id=fixture.session_id,
                expected_head_sha256="0" * 64,
                introduced_artifacts=(link,),
                record=record,
            )
            conflict = persist_problem_session(root, stale, (definition_payload,))
            self.assertEqual(conflict.status, "conflict")
            self.assertEqual(load_problem_session(root, fixture.session_id).head_sha256, stored.head_sha256)
            object_path = root / "objects" / fixture.context_sha[:2] / fixture.context_sha[2:]
            duplicate = root / "duplicate"
            os.link(object_path, duplicate)
            with self.assertRaises(ProblemSessionStoreError):
                load_problem_session(root, fixture.session_id)
            os.chmod(duplicate, 0o600)
            try:
                duplicate.unlink()
            finally:
                os.chmod(object_path, 0o444)
            link_root = base / "link"
            link_root.symlink_to(root, target_is_directory=True)
            with self.assertRaises(ProblemSessionStoreError):
                load_problem_session(link_root, fixture.session_id)
            ancestor = base / "ancestor"
            ancestor.symlink_to(root, target_is_directory=True)
            with self.assertRaises(ProblemSessionStoreError):
                load_problem_session(ancestor / "nested", fixture.session_id)

    def test_store_recovery_removes_only_uncommitted_adapter_state(self) -> None:
        fixture = Fixture()
        command = canonical(json.loads(fixture.events[0])["command"])
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve() / "store"
            stored = persist_problem_session(root, command, fixture.artifacts)
            key = sha(fixture.session_id.encode())
            session_dir = root / "sessions" / key[:2] / key[2:]
            (session_dir / ".writer-lock").write_bytes(b"abandoned\n")
            (session_dir / ".mathhead-head-orphan").write_bytes(b"partial\n")
            with self.assertRaises(ProblemSessionStoreError):
                persist_problem_session(root, command, ())
            recovered = recover_problem_session_store(root, fixture.session_id)
            self.assertEqual(recovered.head_sha256, stored.head_sha256)
            self.assertFalse((session_dir / ".writer-lock").exists())
            self.assertFalse((session_dir / ".mathhead-head-orphan").exists())

    def test_store_interruption_before_head_replace_preserves_prior_commit(self) -> None:
        fixture = Fixture()
        create = canonical(json.loads(fixture.events[0])["command"])
        create_artifacts = fixture.artifacts
        definition = fixture.add_definition()
        update = canonical(json.loads(definition.events[-1])["command"])  # type: ignore[index]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve() / "store"
            initial = persist_problem_session(root, create, create_artifacts)
            key = sha(fixture.session_id.encode())
            session_dir = root / "sessions" / key[:2] / key[2:]
            prior_head = (session_dir / "HEAD").read_bytes()
            with mock.patch.object(
                session_store.os, "replace", side_effect=OSError("injected before HEAD")
            ):
                with self.assertRaises(ProblemSessionStoreError):
                    persist_problem_session(root, update, fixture.artifacts)
            self.assertEqual((session_dir / "HEAD").read_bytes(), prior_head)
            self.assertEqual(load_problem_session(root, fixture.session_id).head_sha256, initial.head_sha256)
            self.assertFalse((session_dir / ".writer-lock").exists())
            self.assertFalse(any(path.name.startswith(".mathhead-head-") for path in session_dir.iterdir()))

    def test_store_replaces_a_sealed_head_through_the_windows_path(self) -> None:
        fixture = Fixture()
        create = canonical(json.loads(fixture.events[0])["command"])
        create_artifacts = fixture.artifacts
        definition = fixture.add_definition()
        update = canonical(json.loads(definition.events[-1])["command"])  # type: ignore[index]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve() / "store"
            initial = persist_problem_session(root, create, create_artifacts)
            with mock.patch.object(session_store, "_WINDOWS", True):
                updated = persist_problem_session(root, update, fixture.artifacts)
            self.assertEqual(initial.revision, 0)
            self.assertEqual(updated.revision, 1)
            key = sha(fixture.session_id.encode())
            head = root / "sessions" / key[:2] / key[2:] / "HEAD"
            self.assertEqual(head.stat().st_mode & 0o777, 0o444)
            self.assertEqual(
                load_problem_session(root, fixture.session_id).head_sha256,
                updated.head_sha256,
            )

    def test_pure_import_closure_has_no_effect_or_optional_roots(self) -> None:
        tree = ast.parse((ROOT / "src/mathhead/problem_sessions.py").read_text())
        imports = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        imports.update(
            node.module.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        )
        self.assertTrue(imports.isdisjoint({"os", "pathlib", "subprocess", "socket", "time", "random", "sympy", "z3"}))
        self.assertNotIn("mathhead", imports)


if __name__ == "__main__":
    unittest.main()
