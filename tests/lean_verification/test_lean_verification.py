from __future__ import annotations

import ast
import copy
import dataclasses
from fractions import Fraction
import inspect
import json
import os
from pathlib import Path
import pickle
import sys
from tempfile import TemporaryDirectory
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from mathhead.kernel.checkers import (  # noqa: E402
    check_proof_term,
    parse_checker_result,
)
from mathhead.kernel.proof_terms import (  # noqa: E402
    CRTTerm,
    crt,
    parse_proof_term,
    polynomial_identity,
    residue,
    sum_induction,
)
from mathhead.proof_assistant.export import (  # noqa: E402
    ACQUISITION_LAKEFILE_BYTES,
    ACQUISITION_MANIFEST_BYTES,
    LAKEFILE_BYTES,
    LAKE_EXECUTABLE_SHA256,
    LAKE_MANIFEST_BYTES,
    LEAN_EXECUTABLE_SHA256,
    LEAN_TOOLCHAIN_BYTES,
    LEAN_VERIFICATION_CONTRACT_SHA256,
    LeanExport,
    LeanVerificationValidationError,
    MAX_OUTPUT_BYTES,
    TOOLCHAIN_LOCK_BYTES,
    build_lean_export,
    parse_lean_export,
    validate_lean_export,
)
from mathhead.proof_assistant.lean import (  # noqa: E402
    LeanVerificationResult,
    _process_environment,
    _real_directory,
    _regular_file_bytes,
    _run,
    export_written_result,
    lean_verification_result_sha256,
    lean_verification_result_to_bytes,
    parse_lean_verification_result,
    prepare_lean_project,
    validate_lean_verification_result,
    verify_with_lean,
)
from mathhead.proof_assistant.provenance import replay_lean_provenance  # noqa: E402


def _canonical(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=True,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("ascii")


class LeanVerificationTests(unittest.TestCase):
    def setUp(self) -> None:
        polynomial = (0, -1, 0, 1)
        self.terms = (
            residue(6, polynomial),
            crt((residue(2, polynomial), residue(3, polynomial))),
            sum_induction((0, 1), (0, Fraction(1, 2), Fraction(1, 2))),
            polynomial_identity(polynomial, polynomial),
        )
        self.exports = tuple(
            build_lean_export(term, check_proof_term(term)) for term in self.terms
        )

    @staticmethod
    def _write_fixed_project(root: Path) -> None:
        for relative, data in (
            ("lakefile.toml", LAKEFILE_BYTES),
            ("lake-manifest.json", LAKE_MANIFEST_BYTES),
            ("lean-toolchain", LEAN_TOOLCHAIN_BYTES),
            ("mathhead-lean-lock.json", TOOLCHAIN_LOCK_BYTES),
        ):
            (root / relative).write_bytes(data)

    def test_all_four_rules_export_one_canonical_theorem(self) -> None:
        self.assertEqual(
            [item.statement_kind for item in self.exports],
            ["divides", "divides", "sum_identity", "polynomial_identity"],
        )
        for item in self.exports:
            self.assertEqual(item.status, "export_written")
            self.assertEqual(item.authority, "none")
            self.assertEqual(item, parse_lean_export(item.request, item.artifacts))
            source = item.artifacts[1].decode("utf-8")
            self.assertEqual(source.count("theorem "), 1)
            self.assertIn(f"theorem {item.theorem_name}", source)
            self.assertTrue(source.endswith("end MathHead.Generated\n"))

    def test_export_is_deterministic_and_binds_every_artifact(self) -> None:
        for term, first in zip(self.terms, self.exports, strict=True):
            second = build_lean_export(term, check_proof_term(term))
            self.assertEqual(first, second)
            request = json.loads(first.request)
            self.assertEqual(
                [record["role"] for record in request["artifacts"]],
                sorted(record["role"] for record in request["artifacts"]),
            )
            for record, artifact in zip(
                request["artifacts"], first.artifacts, strict=True
            ):
                self.assertEqual(record["bytes"], len(artifact))
                self.assertEqual(len(record["sha256"]), 64)

    def test_generated_source_has_no_trust_widening_escape(self) -> None:
        forbidden = {
            "admit",
            "axiom",
            "extern",
            "implemented_by",
            "native_decide",
            "opaque",
            "partial",
            "run_tac",
            "sorry",
            "unsafe",
        }
        for item in self.exports:
            source = item.artifacts[1].decode("utf-8").lower()
            self.assertFalse(forbidden & set(source.replace("(", " ").split()))
            self.assertEqual(source.count("import mathlib"), 1)
            self.assertNotIn("mathhead.discovery", source)

    def test_false_exhausted_unknown_and_mismatched_results_do_not_export(self) -> None:
        false_term = residue(2, (1,))
        with self.assertRaisesRegex(LeanVerificationValidationError, "verified"):
            build_lean_export(false_term, check_proof_term(false_term))
        valid = self.terms[0]
        with self.assertRaises(LeanVerificationValidationError):
            build_lean_export(valid, check_proof_term(self.terms[-1]))
        forged = object.__new__(CRTTerm)
        object.__setattr__(forged, "parts", (forged,))
        with self.assertRaises(LeanVerificationValidationError):
            build_lean_export(forged, check_proof_term(forged))

    def test_request_tampering_and_noncanonical_bytes_fail_closed(self) -> None:
        item = self.exports[0]
        mutations = []
        for key, value in (
            ("source_sha256", "0" * 64),
            ("project_sha256", "0" * 64),
            ("theorem_name", "mathhead_0000000000000000"),
        ):
            request = json.loads(item.request)
            request[key] = value
            mutations.append(_canonical(request))
        request = json.loads(item.request)
        request["toolchain"]["mathlib_commit"] = "0" * 40
        mutations.append(_canonical(request))
        for mutated in mutations:
            with self.assertRaises(LeanVerificationValidationError):
                parse_lean_export(mutated, item.artifacts)
        with self.assertRaisesRegex(LeanVerificationValidationError, "canonical"):
            parse_lean_export(item.request[:-1], item.artifacts)
        duplicate = item.request.replace(
            b'{"artifacts":', b'{"artifacts":[],"artifacts":', 1
        )
        with self.assertRaisesRegex(LeanVerificationValidationError, "duplicate"):
            parse_lean_export(duplicate, item.artifacts)

    def test_artifact_substitution_missing_extra_and_wrong_types_fail(self) -> None:
        item = self.exports[0]
        mutated = list(item.artifacts)
        mutated[1] += b"\n"
        for artifacts in (
            tuple(mutated),
            item.artifacts[:-1],
            item.artifacts + (b"extra",),
            list(item.artifacts),
        ):
            with self.assertRaises(LeanVerificationValidationError):
                parse_lean_export(item.request, artifacts)  # type: ignore[arg-type]

    def test_export_values_are_closed_immutable_and_recomputed(self) -> None:
        item = self.exports[0]
        with self.assertRaises(PermissionError):
            LeanExport()  # type: ignore[call-arg]
        with self.assertRaises(TypeError):
            type("ForgedLeanExport", (LeanExport,), {})
        with self.assertRaises(PermissionError):
            dataclasses.replace(item, authority="external_proof_assistant")
        with self.assertRaises(TypeError):
            pickle.dumps(item)
        self.assertIs(copy.copy(item), item)
        self.assertIs(copy.deepcopy(item), item)
        object.__setattr__(item, "authority", "external_proof_assistant")
        with self.assertRaises(LeanVerificationValidationError):
            validate_lean_export(item)

    def test_export_written_result_round_trips_as_historical_evidence(self) -> None:
        pending = export_written_result(self.exports[0])
        encoded = lean_verification_result_to_bytes(pending)
        parsed = parse_lean_verification_result(encoded)
        self.assertEqual(parsed, pending)
        self.assertEqual(pending.authority, "none")
        self.assertEqual(pending.verdict, "unsupported")
        self.assertEqual(len(lean_verification_result_sha256(pending)), 64)
        validate_lean_verification_result(parsed)

    def test_result_values_are_closed_immutable_and_revalidated(self) -> None:
        result = export_written_result(self.exports[0])
        with self.assertRaises(PermissionError):
            LeanVerificationResult()  # type: ignore[call-arg]
        with self.assertRaises(TypeError):
            type("ForgedLeanVerificationResult", (LeanVerificationResult,), {})
        with self.assertRaises(PermissionError):
            dataclasses.replace(result, authority="external_proof_assistant")
        with self.assertRaises(TypeError):
            pickle.dumps(result)
        self.assertIs(copy.copy(result), result)
        self.assertIs(copy.deepcopy(result), result)
        object.__setattr__(result, "authority", "external_proof_assistant")
        with self.assertRaises(LeanVerificationValidationError):
            validate_lean_verification_result(result)

    def test_process_adapter_bounds_retained_output_before_classification(self) -> None:
        with TemporaryDirectory() as directory:
            observation = _run(
                [
                    sys.executable,
                    "-c",
                    (
                        "import sys; "
                        f"sys.stdout.buffer.write(b'x' * {MAX_OUTPUT_BYTES + 65536}); "
                        "sys.stdout.buffer.flush()"
                    ),
                ],
                Path(directory),
                dict(os.environ),
                30,
            )
        self.assertTrue(observation.output_exhausted)
        self.assertFalse(observation.timed_out)
        self.assertEqual(len(observation.stdout), MAX_OUTPUT_BYTES)
        self.assertEqual(observation.stderr, b"")

    def test_result_bytes_reject_forgery_duplicates_and_noncanonical_forms(self) -> None:
        pending = export_written_result(self.exports[0])
        encoded = lean_verification_result_to_bytes(pending)
        value = json.loads(encoded)
        value["authority"] = "external_proof_assistant"
        with self.assertRaises(LeanVerificationValidationError):
            parse_lean_verification_result(_canonical(value))
        value = json.loads(encoded)
        value["extra"] = True
        with self.assertRaises(LeanVerificationValidationError):
            parse_lean_verification_result(_canonical(value))
        duplicate = encoded.replace(
            b'{"authority":', b'{"authority":"none","authority":', 1
        )
        with self.assertRaisesRegex(LeanVerificationValidationError, "duplicate"):
            parse_lean_verification_result(duplicate)
        with self.assertRaisesRegex(LeanVerificationValidationError, "canonical"):
            parse_lean_verification_result(encoded[:-1])

    def test_runner_rejects_malformed_request_before_project_or_process(self) -> None:
        with TemporaryDirectory() as directory:
            result = verify_with_lean(b"{}\n", (), str(Path(directory).resolve()))
        self.assertEqual(
            (result.status, result.reason_code, result.authority),
            ("check_failed", "REQUEST_INVALID", "none"),
        )

    def test_substituted_toolchain_cannot_mint_external_authority(self) -> None:
        item = self.exports[0]
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for relative, data in (
                ("lakefile.toml", LAKEFILE_BYTES),
                ("lake-manifest.json", LAKE_MANIFEST_BYTES),
                ("lean-toolchain", LEAN_TOOLCHAIN_BYTES),
                ("mathhead-lean-lock.json", TOOLCHAIN_LOCK_BYTES),
            ):
                (root / relative).write_bytes(data)
            prepare_lean_project(item, str(root.resolve()))
            toolchain = root / ".toolchain" / "bin"
            toolchain.mkdir(parents=True)
            for name in ("lake", "lean"):
                path = toolchain / name
                path.write_bytes(b"not the pinned executable")
                path.chmod(0o555)
            result = verify_with_lean(
                item.request, item.artifacts, str(root.resolve())
            )
        self.assertEqual(result.status, "check_unavailable")
        self.assertEqual(result.authority, "none")
        self.assertNotEqual(LAKE_EXECUTABLE_SHA256, LEAN_EXECUTABLE_SHA256)

    @unittest.skipIf(not hasattr(Path, "symlink_to"), "symlinks unavailable")
    def test_symlinked_generated_source_is_rejected(self) -> None:
        item = self.exports[0]
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for relative, data in (
                ("lakefile.toml", LAKEFILE_BYTES),
                ("lake-manifest.json", LAKE_MANIFEST_BYTES),
                ("lean-toolchain", LEAN_TOOLCHAIN_BYTES),
                ("mathhead-lean-lock.json", TOOLCHAIN_LOCK_BYTES),
            ):
                (root / relative).write_bytes(data)
            (root / "MathHead").mkdir()
            target = root / "source-target"
            target.write_bytes(item.artifacts[1])
            try:
                (root / "MathHead" / "Generated.lean").symlink_to(target)
            except OSError:
                self.skipTest("symlink creation is not permitted")
            result = verify_with_lean(
                item.request, item.artifacts, str(root.resolve())
            )
        self.assertEqual(result.status, "check_unavailable")
        self.assertEqual(result.authority, "none")

    @unittest.skipIf(not hasattr(Path, "symlink_to"), "symlinks unavailable")
    def test_symlinked_source_parent_cannot_escape_the_project(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_fixed_project(root)
            outside = root / "outside"
            outside.mkdir()
            try:
                (root / "MathHead").symlink_to(outside, target_is_directory=True)
            except OSError:
                self.skipTest("symlink creation is not permitted")
            with self.assertRaisesRegex(LeanVerificationValidationError, "link"):
                prepare_lean_project(self.exports[0], str(root.resolve()))
            self.assertEqual(list(outside.iterdir()), [])

    @unittest.skipUnless(hasattr(os, "link"), "hard links unavailable")
    def test_hardlinked_project_bytes_are_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_fixed_project(root)
            try:
                os.link(root / "mathhead-lean-lock.json", root / "second-lock-link")
            except OSError:
                self.skipTest("hard-link creation is not permitted")
            with self.assertRaisesRegex(LeanVerificationValidationError, "regular file"):
                prepare_lean_project(self.exports[0], str(root.resolve()))

    def test_stale_compiled_artifact_is_removed_before_execution(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_fixed_project(root)
            output = root / ".lake/build/lib/lean/MathHead/Generated.olean"
            output.parent.mkdir(parents=True)
            output.write_bytes(b"corrupt stale olean")
            prepare_lean_project(self.exports[0], str(root.resolve()))
            self.assertFalse(output.exists())

    @unittest.skipIf(not hasattr(Path, "symlink_to"), "symlinks unavailable")
    def test_hermetic_home_must_be_empty_real_and_root_owned(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            toolchain = _real_directory(
                root, Path(".toolchain/bin"), "test toolchain", create=True
            )
            outside = root / "outside-home"
            outside.mkdir()
            try:
                (root / ".hermetic-home").symlink_to(outside, target_is_directory=True)
            except OSError:
                self.skipTest("symlink creation is not permitted")
            with self.assertRaisesRegex(LeanVerificationValidationError, "link"):
                _process_environment(root, toolchain)

    def test_regular_file_reader_rejects_oversize_before_retaining_bytes(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "oversize"
            path.write_bytes(b"x" * 11)
            with self.assertRaisesRegex(LeanVerificationValidationError, "length"):
                _regular_file_bytes(path, None, "oversize fixture", max_bytes=10)

    def test_committed_project_bytes_and_toolchain_digests_are_exact(self) -> None:
        self.assertEqual(
            (ROOT / "lean/acquisition-lakefile.toml").read_bytes(),
            ACQUISITION_LAKEFILE_BYTES,
        )
        self.assertEqual(
            (ROOT / "lean/acquisition-lake-manifest.json").read_bytes(),
            ACQUISITION_MANIFEST_BYTES,
        )
        self.assertEqual((ROOT / "lean/lean-toolchain").read_bytes(), LEAN_TOOLCHAIN_BYTES)
        self.assertEqual((ROOT / "lean/lakefile.toml").read_bytes(), LAKEFILE_BYTES)
        self.assertEqual(
            (ROOT / "lean/lake-manifest.json").read_bytes(), LAKE_MANIFEST_BYTES
        )
        self.assertEqual(
            (ROOT / "lean/mathhead-lean-lock.json").read_bytes(), TOOLCHAIN_LOCK_BYTES
        )
        lock = json.loads(TOOLCHAIN_LOCK_BYTES)
        self.assertEqual(lock["contract_sha256"], LEAN_VERIFICATION_CONTRACT_SHA256)
        self.assertEqual(lock["lake_executable_sha256"], LAKE_EXECUTABLE_SHA256)
        self.assertEqual(lock["lean_executable_sha256"], LEAN_EXECUTABLE_SHA256)

    def test_request_and_result_schemas_are_closed_and_accept_outputs(self) -> None:
        try:
            import jsonschema
        except ImportError:
            return
        request_schema = json.loads(
            (ROOT / "docs/contracts/schemas/lean-verification-request-v1.schema.json").read_text()
        )
        result_schema = json.loads(
            (ROOT / "docs/contracts/schemas/lean-verification-result-v1.schema.json").read_text()
        )
        for schema in (request_schema, result_schema):
            self.assertFalse(schema["additionalProperties"])
            jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.Draft202012Validator(request_schema).validate(
            json.loads(self.exports[0].request)
        )
        pending = export_written_result(self.exports[0])
        jsonschema.Draft202012Validator(result_schema).validate(
            json.loads(lean_verification_result_to_bytes(pending))
        )

    def test_provenance_dispatch_requires_fresh_matching_bundle(self) -> None:
        sys.path.insert(0, str(ROOT / "tests/provenance_replay"))
        from test_provenance_replay import _bundle

        manifest, objects = _bundle()
        records = json.loads(manifest)["objects"]
        by_role = {
            record["role"]: data
            for record, data in zip(records, objects, strict=True)
        }
        term = parse_proof_term(by_role["proof_term"])
        checker = parse_checker_result(by_role["checker_result"])
        matching = build_lean_export(term, checker)
        self.assertEqual(
            list(inspect.signature(replay_lean_provenance).parameters),
            ["manifest", "objects", "request", "artifacts", "project_root"],
        )
        with TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            mismatched = replay_lean_provenance(
                manifest,
                objects,
                self.exports[0].request,
                self.exports[0].artifacts,
                str(root),
            )
            self.assertEqual((mismatched.status, mismatched.authority), ("check_failed", "none"))
            self.assertEqual(list(root.iterdir()), [])
            unavailable = replay_lean_provenance(
                manifest,
                objects,
                matching.request,
                matching.artifacts,
                str(root),
            )
            self.assertEqual((unavailable.status, unavailable.authority), ("check_unavailable", "none"))
            invalid = replay_lean_provenance(
                manifest[:-1],
                objects,
                matching.request,
                matching.artifacts,
                str(root),
            )
            self.assertEqual((invalid.status, invalid.authority), ("check_failed", "none"))

    def test_pure_exporter_has_no_effect_or_producer_imports(self) -> None:
        tree = ast.parse(
            (ROOT / "src/mathhead/proof_assistant/export.py").read_text(encoding="utf-8")
        )
        roots = {
            alias.name.split(".", 1)[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        roots.update(
            node.module.split(".", 1)[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        )
        self.assertLessEqual(
            roots,
            {
                "__future__",
                "dataclasses",
                "fractions",
                "hashlib",
                "json",
                "mathhead",
                "typing",
            },
        )
        self.assertFalse(
            roots
            & {
                "importlib",
                "mcp",
                "os",
                "pathlib",
                "pysat",
                "random",
                "subprocess",
                "sympy",
                "time",
                "z3",
            }
        )


if __name__ == "__main__":
    unittest.main()
