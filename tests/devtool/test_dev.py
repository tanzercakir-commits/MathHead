from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

from tools import dev


ROOT = Path(__file__).resolve().parents[2]


class DevDispatcherTests(unittest.TestCase):
    def test_repository_manifest_is_strict_and_bound(self) -> None:
        manifest = dev._load_manifest(ROOT)
        self.assertEqual(tuple(manifest["profiles"]), dev.PROFILE_NAMES)
        self.assertEqual(manifest["contract_id"], dev.CONTRACT_ID)
        self.assertEqual(manifest["contract_sha256"], dev.CONTRACT_SHA256)

    def test_profile_dependency_boundaries_are_explicit(self) -> None:
        profiles = dev._load_manifest(ROOT)["profiles"]
        self.assertEqual(profiles["status"]["install"], [])
        self.assertEqual(profiles["runtime"]["install"], ["."])
        self.assertEqual(profiles["core"]["install"], [".[dev]"])
        self.assertNotIn("solvers", " ".join(profiles["core"]["install"]))
        self.assertEqual(profiles["solver"]["install"], [".[dev,solvers]"])
        self.assertEqual(profiles["solver"]["platforms"], ["linux"])
        self.assertEqual(profiles["docs"]["install"], [".[docs]"])
        self.assertEqual(profiles["release"]["install"], [".[release]"])

    def test_describe_never_claims_passed(self) -> None:
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            code = dev.main(["describe", "--profile", "status", "--json"])
        payload = json.loads(stdout.getvalue())
        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "not_run")
        self.assertNotEqual(payload["status"], "passed")

    def test_unsupported_platform_is_an_explicit_nonzero_result(self) -> None:
        stdout = io.StringIO()
        with mock.patch.object(dev, "_platform_name", return_value="plan9"):
            with redirect_stdout(stdout):
                code = dev.main(["check", "--profile", "core", "--json"])
        payload = json.loads(stdout.getvalue())
        self.assertEqual(code, dev.RESULT_EXIT_CODES["unsupported"])
        self.assertEqual(payload["status"], "unsupported")
        self.assertEqual(payload["commands"], [])

    def test_missing_command_is_fail_closed(self) -> None:
        result, stdout, stderr = dev._run_command(
            "missing",
            ["mathhead-command-that-does-not-exist"],
            root=ROOT,
            timeout_seconds=1,
        )
        self.assertEqual((result.status, result.exit_code), ("missing", None))
        self.assertEqual(stdout, "")
        self.assertTrue(stderr)

    def test_failed_command_is_fail_closed(self) -> None:
        result, _stdout, _stderr = dev._run_command(
            "failed",
            [sys.executable, "-c", "raise SystemExit(7)"],
            root=ROOT,
            timeout_seconds=5,
        )
        self.assertEqual((result.status, result.exit_code), ("failed", 7))

    def test_timed_out_command_is_terminated(self) -> None:
        result, _stdout, _stderr = dev._run_command(
            "slow",
            [sys.executable, "-c", "import time; time.sleep(5)"],
            root=ROOT,
            timeout_seconds=0.05,
        )
        self.assertEqual((result.status, result.exit_code), ("timed_out", None))
        self.assertLess(result.elapsed_seconds, 3)

    def test_subprocess_output_is_utf8(self) -> None:
        result, stdout, stderr = dev._run_command(
            "utf8",
            [sys.executable, "-c", "print('çözüm–kanıt')"],
            root=ROOT,
            timeout_seconds=5,
        )
        self.assertEqual(result.status, "passed")
        self.assertEqual(stdout.strip(), "çözüm–kanıt")
        self.assertEqual(stderr, "")

    def test_status_bootstrap_never_invokes_pip(self) -> None:
        stdout = io.StringIO()
        with mock.patch.object(
            dev, "_profile_support", return_value=(True, "supported")
        ):
            with mock.patch.object(dev, "_run_command") as run:
                with redirect_stdout(stdout):
                    code = dev.main(
                        ["bootstrap", "--profile", "status", "--current", "--json"]
                    )
        self.assertEqual(code, 0)
        self.assertFalse(run.called)
        self.assertEqual(json.loads(stdout.getvalue())["reason"], "stdlib-profile-no-install")

    def test_bootstrap_uses_editable_repository_install(self) -> None:
        passed = dev.CommandResult("bootstrap", "passed", 0, "0" * 64, 0.0)
        stdout = io.StringIO()
        with mock.patch.object(
            dev, "_run_command", return_value=(passed, "", "")
        ) as run:
            with redirect_stdout(stdout):
                code = dev.main(
                    ["bootstrap", "--profile", "core", "--current", "--json"]
                )
        self.assertEqual(code, 0)
        profile_argv = run.call_args_list[1].args[1]
        self.assertIn("--editable", profile_argv)
        self.assertEqual(profile_argv[-1], ".[dev]")

    def test_unknown_profile_command_hides_traceback(self) -> None:
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            code = dev.main(
                ["run", "--profile", "core", "--command", "absent-command"]
            )
        self.assertEqual(code, dev.RESULT_EXIT_CODES["failed"])
        self.assertIn("unknown-profile-command", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_bootstrap_target_is_unambiguous(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            target = Path(temp_name) / "env"
            parser = dev._parser()
            with self.assertRaises(SystemExit):
                parser.parse_args(
                    [
                        "bootstrap", "--profile", "runtime", "--current", "--venv",
                        str(target),
                    ]
                )

    def test_required_command_failure_prevents_green_summary(self) -> None:
        results = [
            dev.CommandResult("first", "passed", 0, "0" * 64, 0.0),
            dev.CommandResult("second", "failed", 1, "1" * 64, 0.0),
        ]
        self.assertEqual(dev._overall_status(results), "failed")

    def test_runtime_smoke_refuses_artifact_export(self) -> None:
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            code = dev.main(
                [
                    "clean-smoke", "--profile", "runtime", "--artifact-dir",
                    "dist",
                ]
            )
        self.assertEqual(code, dev.RESULT_EXIT_CODES["failed"])
        self.assertIn("artifact-export-requires-release-profile", stderr.getvalue())

    def test_release_export_is_repository_bounded_and_complete(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            source = root / "source"
            source.mkdir()
            (source / "package.whl").write_bytes(b"wheel")
            (source / "package.tar.gz").write_bytes(b"sdist")
            result = dev._export_release_artifacts(
                root=root,
                source=source,
                requested=Path("dist"),
                elapsed_seconds=1.25,
            )
            self.assertEqual(result.status, "passed")
            self.assertEqual(
                sorted(path.name for path in root.joinpath("dist").iterdir()),
                ["package.tar.gz", "package.whl"],
            )
            with self.assertRaisesRegex(
                dev.DevEnvironmentError, "artifact-directory-outside-repository"
            ):
                dev._export_release_artifacts(
                    root=root,
                    source=source,
                    requested=root.parent / "outside",
                    elapsed_seconds=0,
                )


if __name__ == "__main__":
    unittest.main()
