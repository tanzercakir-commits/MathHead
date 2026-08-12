from __future__ import annotations

from dataclasses import FrozenInstanceError
import copy
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import pickle
import signal
import sys
import tempfile
from threading import Event
import time
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
for entry in (SRC, ROOT):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from mathhead.deterministic_planner import plan_strategies, planning_result_bytes  # noqa: E402
import mathhead.isolated_worker as worker_module  # noqa: E402
from mathhead.isolated_worker import (  # noqa: E402
    ISOLATED_WORKER_CONTRACT_SHA256,
    SCHEMA_SHA256S,
    IsolatedWorkerRequest,
    IsolatedWorkerResult,
    IsolatedWorkerValidationError,
    isolated_worker_budget_bytes,
    isolated_worker_result_bytes,
    make_isolated_worker_request,
    parse_isolated_worker_request,
    parse_isolated_worker_result,
    supervise_worker,
    validate_isolated_worker_result,
    worker_artifact_bytes,
)
from tests.capability_registry.fixtures import plugin_bytes  # noqa: E402
from tests.deterministic_planner.fixtures import PlannerFixture, canonical, self_hash  # noqa: E402
from tools import validate_resource_budget_contract as budget_validator  # noqa: E402


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def process_descriptor(fixture: PlannerFixture) -> bytes:
    def mutate(value: dict[str, object]) -> None:
        value["effects"][3].update(  # type: ignore[index]
            mode="declared",
            policy_id="org.mathhead.process-policy",
            reason="isolated worker fixture",
        )
        value["operations"][1]["effect_kinds"] = ["process"]  # type: ignore[index]
        value["lifecycle"].update(  # type: ignore[union-attr]
            isolation="subprocess_required",
            shutdown_timeout_us=30_000_000,
        )

    return plugin_bytes(
        fixture.fragment,
        suffix="isolated_worker",
        # A POSIX child inherits the long-lived pytest process's peak RSS before
        # exec, and wait4 reports that peak as part of the child observation.
        # Keep the fixture above the supported matrix's supervisor footprint so
        # a bounded successful producer is not mislabeled as a memory overrun.
        base_cost=1_000_000,
        mutation=mutate,
    )


def parent_budget(limits: dict[str, int], *, scale: int = 2) -> bytes:
    value = {
        "schema": "mathhead.resource-budget.v1",
        "budget_id": "budget_isolated_parent",
        "lineage": {"kind": "root"},
        "policy": {
            "wall_clock": "monotonic_elapsed_us",
            "deadline": "relative_to_start",
            "cpu_accounting": "exclusive_budget_scope_us",
            "memory_accounting": "inclusive_active_process_tree_bytes",
            "integer_rounding": "ceil",
            "reservation": "conservative_all_dimensions",
        },
        "limits": {name: amount * scale for name, amount in limits.items()},
        "events": [],
        "outcome": {"status": "open"},
        "extensions": {},
    }
    return canonical(value)


class IsolatedWorkerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        fixture = PlannerFixture()
        descriptor = process_descriptor(fixture)
        inputs = fixture.planning_inputs(
            (descriptor,),
            availability_changes={"allowed_effects": ("process",)},
        )
        plan = plan_strategies(*inputs)
        if plan.status != "planned":
            raise AssertionError(plan)
        cls.plan = plan
        cls.plan_bytes = planning_result_bytes(plan)
        cls.strategy = plan.strategies[0]
        cls.limits = {
            name: getattr(cls.strategy.resource_request.requested, name)
            for name in worker_module.RESOURCE_DIMENSIONS
        }
        cls.parent = parent_budget(cls.limits)
        cls.executable = Path(sys.executable).resolve(strict=True)
        cls.executable_bytes = cls.executable.read_bytes()
        cls.schema, _ = budget_validator.load_json(
            ROOT / "docs/contracts/schemas/resource-budget-v1.schema.json"
        )

    def request(
        self,
        arguments: tuple[str, ...],
        *,
        parent: bytes | None = None,
        artifacts: tuple[tuple[str, bytes], ...] = (),
        executable: bytes | None = None,
        strategy_sha256: str | None = None,
        family: str = "python_enumeration",
        identity_suffix: str = "",
    ) -> bytes:
        return make_isolated_worker_request(
            planning_result=self.plan_bytes,
            strategy_sha256=strategy_sha256 or self.strategy.strategy_sha256,
            descriptor_sha256=self.strategy.descriptor_sha256,
            family=family,
            executable=self.executable_bytes if executable is None else executable,
            arguments=arguments,
            artifacts=artifacts,
            parent_budget=self.parent if parent is None else parent,
            lease_id=f"lease_isolated_worker{identity_suffix}",
            child_budget_id=f"budget_isolated_child{identity_suffix}",
            resource_limits=self.limits,
        )

    def adapter_limits(self, **updates: int):
        limits = dict(self.limits)
        limits.update(updates)
        raw = make_isolated_worker_request(
            planning_result=self.plan_bytes,
            strategy_sha256=self.strategy.strategy_sha256,
            descriptor_sha256=self.strategy.descriptor_sha256,
            family="python_enumeration",
            executable=self.executable_bytes,
            arguments=("-I", "-S", "-c", "pass"),
            artifacts=(),
            parent_budget=self.parent,
            lease_id="lease_adapter",
            child_budget_id="budget_adapter_child",
            resource_limits=limits,
        )
        return parse_isolated_worker_request(raw).resource_limits

    def execute(self, arguments: tuple[str, ...], **kwargs: object):
        if not worker_module.isolation_capability().supported:
            self.skipTest("host cannot enforce the complete isolated-worker capability")
        parent = kwargs.pop("parent", self.parent)
        payloads = kwargs.pop("payloads", ())
        request = self.request(arguments, parent=parent, artifacts=tuple((f"input_{index}", payload) for index, payload in enumerate(payloads)), **kwargs)
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            return supervise_worker(
                request,
                self.plan_bytes,
                parent,
                payloads,
                str(self.executable),
                directory,
            )

    def test_accepted_contract_and_schemas_are_exact(self) -> None:
        accepted = ROOT / "docs/contracts/MH-C-ISOLATED-WORKER-001.json"
        proposal = ROOT / "docs/contracts/proposed/MH-C-ISOLATED-WORKER-001.json"
        self.assertEqual(accepted.read_bytes(), proposal.read_bytes())
        self.assertEqual(sha(accepted.read_bytes()), ISOLATED_WORKER_CONTRACT_SHA256)
        self.assertEqual(len(SCHEMA_SHA256S), 6)
        for schema, expected in SCHEMA_SHA256S.items():
            name = schema.removeprefix("mathhead.").replace(".", "-") + ".schema.json"
            raw = (ROOT / "docs/contracts/schemas" / name).read_bytes()
            self.assertEqual(sha(raw), expected, name)
            self.assertFalse(json.loads(raw)["additionalProperties"])

    def test_request_is_closed_canonical_and_content_addressed(self) -> None:
        raw = self.request(("-I", "-S", "-c", "print('ok')"), artifacts=(("context", b"abc"),))
        value = parse_isolated_worker_request(raw)
        self.assertEqual(value.strategy_sha256, self.strategy.strategy_sha256)
        self.assertEqual(value.artifact_bindings[0].sha256, sha(b"abc"))
        self.assertFalse(value.mathematical_authority)
        self.assertEqual(parse_isolated_worker_request(raw), value)
        with self.assertRaises(IsolatedWorkerValidationError):
            parse_isolated_worker_request(raw.rstrip(b"\n"))
        duplicate = raw.replace(b'{"arguments"', b'{"schema":"duplicate","arguments"', 1)
        with self.assertRaises(IsolatedWorkerValidationError):
            parse_isolated_worker_request(duplicate)

    def test_success_is_bounded_reconciled_and_non_authoritative(self) -> None:
        result = self.execute(("-I", "-S", "-c", "import sys;sys.stdout.buffer.write(b'ok')"))
        self.assertEqual((result.status, result.reason_code), ("completed", "COMPLETED"), result.diagnostics)
        self.assertTrue(result.tree_terminated)
        self.assertTrue(result.lease_reconciled)
        self.assertFalse(result.mathematical_authority)
        self.assertEqual(worker_artifact_bytes(result.artifacts[0]), b"ok")
        child = isolated_worker_budget_bytes(result, "child")
        parent = isolated_worker_budget_bytes(result, "parent")
        child_value = json.loads(child)
        parent_value = json.loads(parent)
        budget_validator.validate_resource_budget(child_value, self.schema)
        budget_validator.validate_resource_budget(parent_value, self.schema)
        self.assertEqual(parent_value["events"][-1]["lease_id"], "lease_isolated_worker")
        validate_isolated_worker_result(result)
        raw = isolated_worker_result_bytes(result)
        rebuilt = parse_isolated_worker_result(
            raw,
            tuple(worker_artifact_bytes(item) for item in result.artifacts),
            child,
            parent,
        )
        self.assertEqual(rebuilt, result)

    def test_same_producer_bytes_have_same_semantic_identity(self) -> None:
        first = self.execute(("-I", "-S", "-c", "print('stable', end='')"))
        second = self.execute(("-I", "-S", "-c", "print('stable', end='')"))
        self.assertEqual(first.status, "completed")
        self.assertEqual(second.status, "completed")
        self.assertEqual(first.semantic_sha256, second.semantic_sha256)
        self.assertEqual(worker_artifact_bytes(first.artifacts[0]), b"stable")

    def test_nonzero_exit_is_failed_not_evidence(self) -> None:
        result = self.execute(("-I", "-S", "-c", "raise SystemExit(7)"))
        self.assertEqual((result.status, result.reason_code), ("failed", "EXIT_FAILED"))
        self.assertTrue(result.tree_terminated)
        self.assertTrue(result.lease_reconciled)
        self.assertFalse(result.mathematical_authority)

    def test_output_overrun_is_exhausted_and_explicit(self) -> None:
        amount = self.limits["output_bytes"] + 1
        result = self.execute(("-I", "-S", "-c", f"import sys;sys.stdout.buffer.write(b'x'*{amount})"))
        self.assertEqual((result.status, result.reason_code), ("exhausted", "OUTPUT_EXHAUSTED"))
        self.assertGreater(result.artifacts[0].omitted_bytes, 0)
        child = json.loads(isolated_worker_budget_bytes(result, "child"))
        self.assertEqual(child["outcome"]["status"], "exhausted")
        budget_validator.validate_resource_budget(child, self.schema)

    def test_preobserved_cancellation_terminates_and_reconciles(self) -> None:
        event = Event()
        event.set()
        request = self.request(("-I", "-S", "-c", "import time;time.sleep(30)"))
        if not worker_module.isolation_capability().supported:
            self.skipTest("host cannot enforce the complete isolated-worker capability")
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            result = supervise_worker(request, self.plan_bytes, self.parent, (), str(self.executable), directory, event)
        self.assertEqual((result.status, result.reason_code), ("cancelled", "CANCELLED"))
        self.assertTrue(result.tree_terminated)
        self.assertTrue(result.lease_reconciled)
        child = json.loads(isolated_worker_budget_bytes(result, "child"))
        self.assertEqual(child["outcome"]["status"], "cancelled")
        budget_validator.validate_resource_budget(child, self.schema)

    @unittest.skipUnless(sys.platform.startswith("linux"), "Linux hard-limit adapter")
    def test_posix_adapter_enforces_hard_wall_cpu_and_memory_limits(self) -> None:
        capability = worker_module.isolation_capability()
        self.assertTrue(capability.supported)
        command_prefix = [str(self.executable), "-I", "-S", "-c"]
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory)
            environment = worker_module._environment(root)
            wall = worker_module._run_posix(
                [*command_prefix, "import time;time.sleep(30)"],
                root,
                environment,
                self.adapter_limits(
                    wall_time_us=100_000,
                    cpu_time_us=5_000_000,
                    memory_bytes=268_435_456,
                    output_bytes=4_096,
                    diagnostic_bytes=4_096,
                ),
                None,
            )
            self.assertEqual(wall.reason, "WALL_TIME_EXHAUSTED")
            self.assertTrue(wall.tree_terminated)

        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory)
            environment = worker_module._environment(root)
            cpu = worker_module._run_posix(
                [*command_prefix, "while True: pass"],
                root,
                environment,
                self.adapter_limits(
                    wall_time_us=5_000_000,
                    cpu_time_us=1_000_000,
                    memory_bytes=268_435_456,
                    output_bytes=4_096,
                    diagnostic_bytes=4_096,
                ),
                None,
            )
            self.assertEqual(cpu.reason, "CPU_TIME_EXHAUSTED")
            self.assertTrue(cpu.tree_terminated)

        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory)
            environment = worker_module._environment(root)
            memory = worker_module._run_posix(
                [*command_prefix, "import os,signal;\ntry: bytearray(268435456)\nexcept MemoryError: os.kill(os.getpid(),signal.SIGSEGV)"],
                root,
                environment,
                self.adapter_limits(
                    wall_time_us=5_000_000,
                    cpu_time_us=5_000_000,
                    memory_bytes=67_108_864,
                    output_bytes=4_096,
                    diagnostic_bytes=4_096,
                ),
                None,
            )
            self.assertEqual(memory.reason, "MEMORY_EXHAUSTED")
            self.assertTrue(memory.tree_terminated)

    def test_direct_argv_does_not_interpret_shell_metacharacters(self) -> None:
        marker = "$(printf injected);`printf injected`;*;&&"
        result = self.execute(("-I", "-S", "-c", "import sys;print(sys.argv[1],end='')", marker))
        self.assertEqual(result.status, "completed")
        self.assertEqual(worker_artifact_bytes(result.artifacts[0]).decode("ascii"), marker)

    def test_all_declared_producer_families_use_the_same_isolated_boundary(self) -> None:
        for family in ("sympy", "python_enumeration", "smt", "external_process"):
            with self.subTest(family=family):
                result = self.execute(
                    ("-I", "-S", "-c", "import sys;print(sys.argv[1],end='')", family),
                    family=family,
                    identity_suffix=f"_{family}",
                )
                self.assertEqual((result.status, result.reason_code), ("completed", "COMPLETED"))
                self.assertEqual(worker_artifact_bytes(result.artifacts[0]).decode("ascii"), family)
                self.assertEqual(result.usage.solver_calls, min(1, self.limits["solver_calls"]))

    def test_hostile_ambient_environment_is_not_inherited(self) -> None:
        key = "MATHHEAD_UNTRUSTED_SECRET"
        code = f"import os;print(os.environ.get('{key}','absent'),end='')"
        with mock.patch.dict(os.environ, {key: "must-not-leak"}):
            result = self.execute(("-I", "-S", "-c", code))
        self.assertEqual(result.status, "completed")
        self.assertEqual(worker_artifact_bytes(result.artifacts[0]), b"absent")

    def test_diagnostic_overrun_signal_and_forced_cleanup_are_explicit(self) -> None:
        amount = self.limits["diagnostic_bytes"] + 1
        diagnostic = self.execute(("-I", "-S", "-c", f"import sys;sys.stderr.buffer.write(b'x'*{amount})"))
        self.assertEqual((diagnostic.status, diagnostic.reason_code), ("exhausted", "DIAGNOSTIC_EXHAUSTED"))
        self.assertGreater(diagnostic.artifacts[-1].omitted_bytes, 0)

        if os.name == "posix":
            signalled = self.execute(("-I", "-S", "-c", "import os,signal;os.kill(os.getpid(),signal.SIGTERM)"))
            self.assertEqual((signalled.status, signalled.reason_code), ("failed", "EXIT_FAILED"))
            self.assertEqual(signalled.usage.termination_signal, signal.SIGTERM)

            amount = self.limits["output_bytes"] + 1
            ignored = self.execute(("-I", "-S", "-c", f"import signal,sys,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);sys.stdout.buffer.write(b'x'*{amount});sys.stdout.flush();time.sleep(30)"))
            self.assertEqual((ignored.status, ignored.reason_code), ("exhausted", "OUTPUT_EXHAUSTED"))
            self.assertTrue(ignored.tree_terminated)

    def test_concurrent_supervisors_have_independent_containment(self) -> None:
        def run(index: int):
            return self.execute(
                ("-I", "-S", "-c", "import sys;print(sys.argv[1],end='')", str(index)),
                identity_suffix=f"_{index}",
            )

        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(run, range(4)))
        self.assertEqual([result.status for result in results], ["completed"] * 4)
        self.assertEqual([worker_artifact_bytes(result.artifacts[0]) for result in results], [b"0", b"1", b"2", b"3"])

    def test_cleanup_failure_cannot_become_success(self) -> None:
        if not worker_module.isolation_capability().supported:
            self.skipTest("host cannot enforce the complete isolated-worker capability")
        request = self.request(("-I", "-S", "-c", "print('ok',end='')"))
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            with mock.patch.object(worker_module.shutil, "rmtree", side_effect=OSError("cleanup denied")):
                result = supervise_worker(request, self.plan_bytes, self.parent, (), str(self.executable), directory)
        self.assertEqual((result.status, result.reason_code), ("failed", "SUPERVISOR_FAILED"))
        self.assertFalse(result.tree_terminated)
        self.assertTrue(result.lease_reconciled)

    @unittest.skipUnless(os.name == "posix" and Path("/proc").is_dir(), "Linux process-tree observation")
    def test_grandchild_is_dead_before_return(self) -> None:
        code = "import subprocess,sys,time;p=subprocess.Popen([sys.executable,'-I','-S','-c','import time;time.sleep(30)']);print(p.pid,flush=True)"
        result = self.execute(("-I", "-S", "-c", code))
        self.assertEqual(result.status, "completed", result.diagnostics)
        child_pid = int(worker_artifact_bytes(result.artifacts[0]).strip())
        deadline = time.monotonic() + 2
        child_path = Path(f"/proc/{child_pid}")
        while child_path.exists() and time.monotonic() < deadline:
            try:
                if (child_path / "stat").read_text(encoding="ascii").split()[2] == "Z":
                    break
            except (OSError, IndexError):
                break
            time.sleep(0.01)
        if child_path.exists():
            self.assertEqual((child_path / "stat").read_text(encoding="ascii").split()[2], "Z")

    def test_invalid_plan_artifact_budget_and_executable_fail_before_authority(self) -> None:
        request = self.request(("-I", "-S", "-c", "print('never')"), artifacts=(("context", b"abc"),))
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            wrong_artifact = supervise_worker(request, self.plan_bytes, self.parent, (b"xyz",), str(self.executable), directory)
            wrong_plan = supervise_worker(request, self.plan_bytes[:-1], self.parent, (b"abc",), str(self.executable), directory)
        self.assertEqual(wrong_artifact.status, "invalid")
        self.assertEqual(wrong_plan.status, "invalid")

        insufficient = parent_budget(self.limits, scale=0)
        refused = self.execute(("-I", "-S", "-c", "print('never')"), parent=insufficient)
        self.assertEqual((refused.status, refused.reason_code), ("refused", "BUDGET_INSUFFICIENT"))

        request_bad_executable = self.request(("-I", "-S", "-c", "print('never')"), executable=b"wrong")
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            invalid_executable = supervise_worker(request_bad_executable, self.plan_bytes, self.parent, (), str(self.executable), directory)
        self.assertEqual((invalid_executable.status, invalid_executable.reason_code), ("invalid", "EXECUTABLE_INVALID"))

    def test_repaired_invalid_parent_budget_semantics_fail_before_launch(self) -> None:
        malformed_values: list[dict[str, object]] = []

        bad_lineage = json.loads(self.parent)
        bad_lineage["lineage"] = {
            "kind": "child",
            "parent_budget_id": "budget_upstream",
            "parent_lease_id": "lease_upstream",
            "allocation_sha256": "0" * 64,
        }
        malformed_values.append(bad_lineage)

        bad_extension = json.loads(self.parent)
        bad_extension["extensions"] = {"not_namespaced": {}}
        malformed_values.append(bad_extension)

        bad_truncation = json.loads(self.parent)
        bad_truncation["events"] = [{
            "event_id": "truncate_event",
            "sequence": 0,
            "kind": "truncate",
            "truncation_id": "truncation_one",
            "dimension": "output_bytes",
            "subject_id": "worker_output",
            "strategy": "prefix",
            "original": 2,
            "retained": 1,
            "omitted": 1,
            "retained_sha256": sha(b"x"),
            "extensions": {},
        }]
        malformed_values.append(bad_truncation)

        bad_observation = json.loads(self.parent)
        bad_observation["events"] = [{
            "event_id": "sample_overrun",
            "sequence": 0,
            "kind": "sample",
            "observation": {
                "wall_time_us": bad_observation["limits"]["wall_time_us"] + 1,
                "memory_peak_bytes": 0,
                "memory_retained_bytes": 0,
                "nesting_current": 0,
                "nesting_peak": 0,
            },
            "extensions": {},
        }]
        malformed_values.append(bad_observation)

        for malformed in malformed_values:
            parent = canonical(malformed)
            request = self.request(("-I", "-S", "-c", "print('never')"), parent=parent)
            with self.subTest(parent=malformed), tempfile.TemporaryDirectory(dir=ROOT) as directory:
                result = supervise_worker(request, self.plan_bytes, parent, (), str(self.executable), directory)
            self.assertEqual((result.status, result.reason_code), ("invalid", "REQUEST_INVALID"))

    def test_repaired_result_cannot_bind_invalid_budget_bytes(self) -> None:
        result = self.execute(("-I", "-S", "-c", "print('ok',end='')"))
        child = json.loads(isolated_worker_budget_bytes(result, "child"))
        child["lineage"]["allocation_sha256"] = "0" * 64
        child_raw = canonical(child)
        parent = json.loads(isolated_worker_budget_bytes(result, "parent"))
        parent["events"][-1]["child_budget_sha256"] = sha(child_raw)
        parent_raw = canonical(parent)
        forged = json.loads(isolated_worker_result_bytes(result))
        forged["child_budget_sha256"] = sha(child_raw)
        forged["parent_budget_sha256"] = sha(parent_raw)
        self_hash(forged, "result_sha256")
        with self.assertRaises(IsolatedWorkerValidationError):
            parse_isolated_worker_result(
                canonical(forged),
                tuple(worker_artifact_bytes(item) for item in result.artifacts),
                child_raw,
                parent_raw,
            )

    def test_repaired_request_and_result_forgery_fail_closed(self) -> None:
        raw = json.loads(self.request(("-I", "-S", "-c", "print('ok')")))
        raw["resource_limits"]["output_bytes"] += 1
        self_hash(raw, "request_sha256")
        repaired = canonical(raw)
        parse_isolated_worker_request(repaired)
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            rejected = supervise_worker(repaired, self.plan_bytes, self.parent, (), str(self.executable), directory)
        self.assertEqual((rejected.status, rejected.reason_code), ("invalid", "STRATEGY_MISMATCH"))

        result = self.execute(("-I", "-S", "-c", "print('ok',end='')"))
        forged = json.loads(isolated_worker_result_bytes(result))
        forged["mathematical_authority"] = True
        forged["semantic_sha256"] = sha(canonical(worker_module._semantic_preimage(forged)))
        self_hash(forged, "result_sha256")
        with self.assertRaises(IsolatedWorkerValidationError):
            parse_isolated_worker_result(
                canonical(forged),
                tuple(worker_artifact_bytes(item) for item in result.artifacts),
                isolated_worker_budget_bytes(result, "child"),
                isolated_worker_budget_bytes(result, "parent"),
            )

        forged = json.loads(isolated_worker_result_bytes(result))
        forged["reason_code"] = "EXIT_FAILED"
        forged["diagnostics"] = [{
            "schema": "mathhead.worker-diagnostic.v1",
            "code": "EXIT_FAILED",
            "message": "forged status pair",
            "diagnostic_sha256": None,
            "mathematical_authority": False,
        }]
        self_hash(forged["diagnostics"][0], "diagnostic_sha256")
        forged["semantic_sha256"] = sha(canonical(worker_module._semantic_preimage(forged)))
        self_hash(forged, "result_sha256")
        with self.assertRaises(IsolatedWorkerValidationError):
            parse_isolated_worker_result(
                canonical(forged),
                tuple(worker_artifact_bytes(item) for item in result.artifacts),
                isolated_worker_budget_bytes(result, "child"),
                isolated_worker_budget_bytes(result, "parent"),
            )

    def test_values_are_immutable_final_and_not_pickle_authority(self) -> None:
        request = parse_isolated_worker_request(self.request(("-I", "-S", "-c", "print('ok')")))
        with self.assertRaises(FrozenInstanceError):
            request.family = "smt"  # type: ignore[misc]
        with self.assertRaises(TypeError):
            type("Forged", (IsolatedWorkerResult,), {})
        with self.assertRaises(TypeError):
            pickle.dumps(request)
        with self.assertRaises(PermissionError):
            IsolatedWorkerRequest()  # type: ignore[call-arg]
        with self.assertRaises(TypeError):
            copy.copy(request)

    def test_fatal_controls_propagate_after_cleanup_path(self) -> None:
        if not worker_module.isolation_capability().supported:
            self.skipTest("host cannot enforce the complete isolated-worker capability")
        request = self.request(("-I", "-S", "-c", "print('ok')"))
        for fatal in (MemoryError(), KeyboardInterrupt(), SystemExit()):
            with self.subTest(kind=type(fatal).__name__), tempfile.TemporaryDirectory(dir=ROOT) as directory:
                patcher = mock.patch.object(worker_module, "_run_posix" if os.name == "posix" else "_run_windows", side_effect=fatal)
                with patcher:
                    with self.assertRaises(type(fatal)):
                        supervise_worker(request, self.plan_bytes, self.parent, (), str(self.executable), directory)

    @unittest.skipUnless(sys.platform == "darwin", "Darwin capability outcome")
    def test_darwin_address_space_limit_is_explicitly_unsupported(self) -> None:
        capability = worker_module.isolation_capability()
        self.assertEqual(capability.platform, "darwin")
        self.assertFalse(capability.supported)
        self.assertEqual(capability.reason_code, "PRIMITIVE_UNAVAILABLE")
        self.assertEqual(capability.containment, "none")
        request = self.request(("-I", "-S", "-c", "print('never')"))
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            result = supervise_worker(
                request,
                self.plan_bytes,
                self.parent,
                (),
                str(self.executable),
                directory,
            )
        self.assertEqual((result.status, result.reason_code), ("unsupported", "ISOLATION_UNSUPPORTED"))
        # Capability refusal precedes executable/cwd authority, budget
        # reservation, and process creation, so neither post-launch claim is
        # made for this honest closed outcome.
        self.assertFalse(result.lease_reconciled)
        self.assertFalse(result.tree_terminated)


if __name__ == "__main__":
    unittest.main()
