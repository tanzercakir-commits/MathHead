from __future__ import annotations

from dataclasses import dataclass
import importlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from mathhead import output  # noqa: E402


EXPECTED_HASH = "b47e07c259a8357000d57cde4238b61ea11a872113d713165515dc86a54cf210"


class EncodedStream:
    def __init__(self, encoding: str) -> None:
        self.encoding = encoding
        self.buffer = bytearray()
        self.flushes = 0

    def write(self, text: str) -> int:
        payload = text.encode(self.encoding)
        self.buffer.extend(payload)
        return len(text)

    def flush(self) -> None:
        self.flushes += 1

    def text(self) -> str:
        return bytes(self.buffer).decode(self.encoding)


class BrokenStream:
    encoding = "ascii"

    def write(self, _text: str) -> int:
        raise BrokenPipeError("closed consumer")


@dataclass
class EmitResult:
    status: str = "ok"
    explanation: str = "Türkçe → sonuç"


class CommandEncodingContractTests(unittest.TestCase):
    def test_contract_binding_and_signature(self) -> None:
        self.assertEqual(output.ENCODING_CONTRACT_ID, "MH-C-ENCODING-001")
        self.assertEqual(output.ENCODING_CONTRACT_SHA256, EXPECTED_HASH)
        self.assertEqual(list(importlib.import_module("inspect").signature(
            output.safe_text).parameters), ["text", "encoding"])

    def test_exact_text_is_preserved_when_encodable(self) -> None:
        for encoding in (None, "ascii", "utf-8", "utf_16", "utf-32"):
            with self.subTest(encoding=encoding):
                self.assertEqual(output.safe_text("plain text", encoding), "plain text")
        self.assertEqual(output.safe_text("Türkçe", "cp1254"), "Türkçe")

    def test_only_unencodable_code_points_are_reversibly_escaped(self) -> None:
        text = "Türkçe → π 😀"
        escaped = output.safe_text(text, "cp1254")
        self.assertTrue(escaped.startswith("Türkçe "))
        self.assertIn("\\u2192", escaped)
        self.assertIn("\\u03c0", escaped)
        self.assertIn("\\U0001f600", escaped)
        self.assertEqual(output.safe_text(escaped, "cp1254"), escaped)
        escaped.encode("cp1254")

    def test_constrained_codecs_are_deterministic(self) -> None:
        self.assertEqual(output.safe_text("é—", "ascii"), "\\xe9\\u2014")
        self.assertEqual(output.safe_text("é—", "cp1252"), "é—")
        self.assertEqual(output.safe_text("Türkçe−", "cp1254"), "Türkçe\\u2212")

    def test_invalid_types_and_unknown_codec_fail_visible(self) -> None:
        for bad in (b"text", 1, None):
            with self.subTest(text=bad), self.assertRaises(TypeError):
                output.safe_text(bad, "ascii")
        for bad in (1, b"ascii"):
            with self.subTest(encoding=bad), self.assertRaises(TypeError):
                output.safe_text("text", bad)
        with self.assertRaises(LookupError):
            output.safe_text("text", "not-a-real-codec")

    def test_safe_print_preserves_redirected_unicode_and_flush(self) -> None:
        stream = io.StringIO()
        output.safe_print("Türkçe", "→", file=stream, flush=True)
        self.assertEqual(stream.getvalue(), "Türkçe →\n")

        constrained = EncodedStream("cp1254")
        output.safe_print("Türkçe", "→", file=constrained, flush=True)
        self.assertEqual(constrained.text(), "Türkçe \\u2192\n")
        self.assertEqual(constrained.flushes, 1)

    def test_non_encoding_io_failures_are_not_hidden(self) -> None:
        with self.assertRaises(BrokenPipeError):
            output.safe_print("text", file=BrokenStream())

    def test_main_cli_json_is_ascii_safe_and_data_preserving(self) -> None:
        main_cli = importlib.import_module("mathhead.cli")
        stream = EncodedStream("ascii")
        with mock.patch.object(sys, "stdout", stream):
            code = main_cli._emit(EmitResult(), as_json=True)
        self.assertEqual(code, 0)
        raw = stream.text()
        raw.encode("ascii")
        self.assertEqual(json.loads(raw)["explanation"], "Türkçe → sonuç")

    def test_main_cli_human_output_preserves_turkish_and_escapes_arrow(self) -> None:
        main_cli = importlib.import_module("mathhead.cli")
        stream = EncodedStream("cp1254")
        with mock.patch.object(sys, "stdout", stream):
            code = main_cli._emit(EmitResult(), as_json=False)
        self.assertEqual(code, 0)
        self.assertIn("Türkçe \\u2192 sonuç", stream.text())

    def test_discovery_json_is_ascii_safe_and_human_output_is_bounded(self) -> None:
        discovery_cli = importlib.import_module("mathhead.discovery.cli")
        product = importlib.import_module("mathhead.discovery.product")
        result = product.CheckResult(
            "Türkçe →", "unknown", "unsupported", "none", notes="dürüst − sonuç"
        )
        stream = EncodedStream("ascii")
        with mock.patch.object(sys, "stdout", stream):
            self.assertEqual(discovery_cli._print_check(result, as_json=True), 3)
        raw = stream.text()
        raw.encode("ascii")
        self.assertEqual(json.loads(raw)["statement"], "Türkçe →")

        human = EncodedStream("cp1254")
        with mock.patch.object(sys, "stdout", human):
            self.assertEqual(discovery_cli._print_check(result, as_json=False), 3)
        self.assertIn("Türkçe \\u2192", human.text())
        self.assertIn("dürüst \\u2212 sonuç", human.text())

    def test_mcp_startup_diagnostic_is_stderr_only_and_encoding_safe(self) -> None:
        server = importlib.import_module("mathhead.server.mcp_server")
        stderr = EncodedStream("cp1252")
        stdout = EncodedStream("ascii")
        with mock.patch.object(server._profiles, "select_packs", return_value={"core"}), \
                mock.patch.object(server._profiles, "apply_profile", return_value=[1, 2]), \
                mock.patch.object(server.mcp, "run") as run_mock, \
                mock.patch.object(sys, "stderr", stderr), \
                mock.patch.object(sys, "stdout", stdout):
            server.main()
        run_mock.assert_called_once_with(transport="stdio")
        self.assertEqual(stdout.text(), "")
        self.assertIn("\\u2192 2 tools exposed", stderr.text())

    def test_ascii_subprocess_does_not_crash_on_unicode_discovery_output(self) -> None:
        env = dict(os.environ)
        env.update({"PYTHONIOENCODING": "ascii", "LC_ALL": "C"})
        result = subprocess.run(
            [sys.executable, "-m", "mathhead.discovery.cli", "check", "6 | n^3 - n"],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            encoding="ascii",
            timeout=30,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("UnicodeEncodeError", result.stderr)
        self.assertIn("\\u", result.stdout)


if __name__ == "__main__":
    unittest.main()
