"""Pure, non-authoritative Lean 4 export boundary for MH-036."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import hashlib
import json
from typing import Any, NoReturn

from mathhead.kernel.checkers import (
    CheckerResult,
    DividesStatement,
    PolynomialIdentityStatement,
    SumIdentityStatement,
    checker_result_to_bytes,
    parse_checker_result,
    validate_checker_result,
)
from mathhead.kernel.proof_terms import (
    ProofTerm,
    parse_proof_term,
    proof_term_to_bytes,
    validate_proof_term,
)


LEAN_VERIFICATION_CONTRACT_ID = "MH-C-LEAN-VERIFICATION-001"
LEAN_VERIFICATION_CONTRACT_SHA256 = (
    "b5c8bd2b3f93698d404042e7785d6dc503968481de13a77aee71769079a4b60a"
)
LEAN_REQUEST_SCHEMA = "mathhead.lean-verification-request.v1"
LEAN_TOOLCHAIN = "leanprover/lean4:v4.33.0"
LEAN_COMMIT = "d8b18978322de05a8f3dba51ef03cf5461676c17"
MATHLIB_COMMIT = "db584cd6d46c92f209a44c0f1c829460d327499d"
LEAN_RELEASE_ASSET_SHA256 = (
    "4b3fb03c29a1e0a253fb1d11f9bae3725f19a0dc6fc09b3ea16d2c9df3349e2c"
)
LAKE_EXECUTABLE_SHA256 = (
    "60330ab6f07dce20f3fa9ebb08e8b984ea9549eac172afeb15d9d2227060e2b3"
)
LEAN_EXECUTABLE_SHA256 = (
    "e8baaa71855a616dc351028f3ad2200051b0671f423a1696a100e809302d5550"
)
LEAN_PLATFORM = "x86_64-unknown-linux-gnu"

MAX_REQUEST_BYTES = 4_194_304
MAX_ARTIFACT_BYTES = 67_108_864
MAX_SOURCE_BYTES = 4_194_304
MAX_OUTPUT_BYTES = 1_048_576
MAX_INTEGER_BITS = 4_096
MAX_TOTAL_SECONDS = 600

LEAN_TOOLCHAIN_BYTES = b"leanprover/lean4:v4.33.0\n"
ACQUISITION_LAKEFILE_BYTES = b'''name = "mathhead_lean"
version = "1.0.0"
defaultTargets = ["MathHead"]

[[require]]
name = "mathlib"
git = "https://github.com/leanprover-community/mathlib4.git"
rev = "db584cd6d46c92f209a44c0f1c829460d327499d"

[[lean_lib]]
name = "MathHead"
'''
LAKEFILE_BYTES = b'''name = "mathhead_lean"
version = "1.0.0"
defaultTargets = ["MathHead"]

[[require]]
name = "mathlib"
path = ".lake/packages/mathlib"

[[require]]
name = "plausible"
path = ".lake/packages/plausible"

[[require]]
name = "LeanSearchClient"
path = ".lake/packages/LeanSearchClient"

[[require]]
name = "importGraph"
path = ".lake/packages/importGraph"

[[require]]
name = "proofwidgets"
path = ".lake/packages/proofwidgets"

[[require]]
name = "aesop"
path = ".lake/packages/aesop"

[[require]]
name = "Qq"
path = ".lake/packages/Qq"

[[require]]
name = "batteries"
path = ".lake/packages/batteries"

[[require]]
name = "Cli"
path = ".lake/packages/Cli"

[[lean_lib]]
name = "MathHead"
'''
ACQUISITION_MANIFEST_BYTES = b'''{"version": "1.2.0",
 "packagesDir": ".lake/packages",
 "packages":
 [{"url": "https://github.com/leanprover-community/mathlib4.git",
   "type": "git",
   "subDir": null,
   "scope": "",
   "rev": "db584cd6d46c92f209a44c0f1c829460d327499d",
   "name": "mathlib",
   "manifestFile": "lake-manifest.json",
   "inputRev": "db584cd6d46c92f209a44c0f1c829460d327499d",
   "inherited": false,
   "configFile": "lakefile.lean"},
  {"url": "https://github.com/leanprover-community/plausible",
   "type": "git",
   "subDir": null,
   "scope": "leanprover-community",
   "rev": "b7eb3304aeae834b12dda98993a37f6a41f6f0bb",
   "name": "plausible",
   "manifestFile": "lake-manifest.json",
   "inputRev": "main",
   "inherited": true,
   "configFile": "lakefile.toml"},
  {"url": "https://github.com/leanprover-community/LeanSearchClient",
   "type": "git",
   "subDir": null,
   "scope": "leanprover-community",
   "rev": "5f4d51b81cbd3f6b32b156bfad9056621a040404",
   "name": "LeanSearchClient",
   "manifestFile": "lake-manifest.json",
   "inputRev": "main",
   "inherited": true,
   "configFile": "lakefile.toml"},
  {"url": "https://github.com/leanprover-community/import-graph",
   "type": "git",
   "subDir": null,
   "scope": "leanprover-community",
   "rev": "16f02aa7642864af59f1ff0e384a015994db9118",
   "name": "importGraph",
   "manifestFile": "lake-manifest.json",
   "inputRev": "main",
   "inherited": true,
   "configFile": "lakefile.toml"},
  {"url": "https://github.com/leanprover-community/ProofWidgets4",
   "type": "git",
   "subDir": null,
   "scope": "leanprover-community",
   "rev": "4be2e3d5087eeb272cf5a8853b8f9dd025ef5957",
   "name": "proofwidgets",
   "manifestFile": "lake-manifest.json",
   "inputRev": "main",
   "inherited": true,
   "configFile": "lakefile.lean"},
  {"url": "https://github.com/leanprover-community/aesop",
   "type": "git",
   "subDir": null,
   "scope": "leanprover-community",
   "rev": "3448c0bcc5ce01b2d1546e483ec3620e32df3d0e",
   "name": "aesop",
   "manifestFile": "lake-manifest.json",
   "inputRev": "master",
   "inherited": true,
   "configFile": "lakefile.toml"},
  {"url": "https://github.com/leanprover-community/quote4",
   "type": "git",
   "subDir": null,
   "scope": "leanprover-community",
   "rev": "92c15be17b7caf78c2ad767ec40f89052d908d81",
   "name": "Qq",
   "manifestFile": "lake-manifest.json",
   "inputRev": "master",
   "inherited": true,
   "configFile": "lakefile.toml"},
  {"url": "https://github.com/leanprover-community/batteries",
   "type": "git",
   "subDir": null,
   "scope": "leanprover-community",
   "rev": "4488d40d070b9700d4d5a6aa342f0d40c31b2a2d",
   "name": "batteries",
   "manifestFile": "lake-manifest.json",
   "inputRev": "main",
   "inherited": true,
   "configFile": "lakefile.toml"},
  {"url": "https://github.com/leanprover/lean4-cli",
   "type": "git",
   "subDir": null,
   "scope": "leanprover",
   "rev": "6130a47896ce867c6a4a55373441e59e565bad0f",
   "name": "Cli",
   "manifestFile": "lake-manifest.json",
   "inputRev": "v4.33.0",
   "inherited": true,
   "configFile": "lakefile.toml"}],
 "name": "mathhead_lean",
 "lakeDir": ".lake",
 "fixedToolchain": false}
'''
LAKE_MANIFEST_BYTES = b'''{"version": "1.2.0",
 "packagesDir": ".lake/packages",
 "packages":
 [{"type": "path",
   "scope": "",
   "name": "Cli",
   "manifestFile": "lake-manifest.json",
   "inherited": false,
   "dir": ".lake/packages/Cli",
   "configFile": "lakefile.toml"},
  {"type": "path",
   "scope": "",
   "name": "batteries",
   "manifestFile": "lake-manifest.json",
   "inherited": false,
   "dir": ".lake/packages/batteries",
   "configFile": "lakefile.toml"},
  {"type": "path",
   "scope": "",
   "name": "Qq",
   "manifestFile": "lake-manifest.json",
   "inherited": false,
   "dir": ".lake/packages/Qq",
   "configFile": "lakefile.toml"},
  {"type": "path",
   "scope": "",
   "name": "aesop",
   "manifestFile": "lake-manifest.json",
   "inherited": false,
   "dir": ".lake/packages/aesop",
   "configFile": "lakefile.toml"},
  {"type": "path",
   "scope": "",
   "name": "proofwidgets",
   "manifestFile": "lake-manifest.json",
   "inherited": false,
   "dir": ".lake/packages/proofwidgets",
   "configFile": "lakefile.lean"},
  {"type": "path",
   "scope": "",
   "name": "importGraph",
   "manifestFile": "lake-manifest.json",
   "inherited": false,
   "dir": ".lake/packages/importGraph",
   "configFile": "lakefile.toml"},
  {"type": "path",
   "scope": "",
   "name": "LeanSearchClient",
   "manifestFile": "lake-manifest.json",
   "inherited": false,
   "dir": ".lake/packages/LeanSearchClient",
   "configFile": "lakefile.toml"},
  {"type": "path",
   "scope": "",
   "name": "plausible",
   "manifestFile": "lake-manifest.json",
   "inherited": false,
   "dir": ".lake/packages/plausible",
   "configFile": "lakefile.toml"},
  {"type": "path",
   "scope": "",
   "name": "mathlib",
   "manifestFile": "lake-manifest.json",
   "inherited": false,
   "dir": ".lake/packages/mathlib",
   "configFile": "lakefile.lean"}],
 "name": "mathhead_lean",
 "lakeDir": ".lake",
 "fixedToolchain": false}
'''
TOOLCHAIN_LOCK_BYTES = (
    b'{"acquisition_lakefile_sha256":"97f36d32f161a82a15fe2aab1d63b1140d09921b6a2b0af60f0a290f4171ff20",'
    b'"acquisition_manifest_sha256":"eb779c50df3a22f76fe654ce809a10b65cdb3c9aaf1d23d36a1252ef24c0bf80",'
    b'"contract_id":"MH-C-LEAN-VERIFICATION-001",'
    b'"contract_sha256":"b5c8bd2b3f93698d404042e7785d6dc503968481de13a77aee71769079a4b60a",'
    b'"dependency_commits":{"Cli":"6130a47896ce867c6a4a55373441e59e565bad0f",'
    b'"LeanSearchClient":"5f4d51b81cbd3f6b32b156bfad9056621a040404",'
    b'"Qq":"92c15be17b7caf78c2ad767ec40f89052d908d81",'
    b'"aesop":"3448c0bcc5ce01b2d1546e483ec3620e32df3d0e",'
    b'"batteries":"4488d40d070b9700d4d5a6aa342f0d40c31b2a2d",'
    b'"importGraph":"16f02aa7642864af59f1ff0e384a015994db9118",'
    b'"mathlib":"db584cd6d46c92f209a44c0f1c829460d327499d",'
    b'"plausible":"b7eb3304aeae834b12dda98993a37f6a41f6f0bb",'
    b'"proofwidgets":"4be2e3d5087eeb272cf5a8853b8f9dd025ef5957"},'
    b'"lake_executable_sha256":"60330ab6f07dce20f3fa9ebb08e8b984ea9549eac172afeb15d9d2227060e2b3",'
    b'"lake_manifest_sha256":"77661e08c2d9b9f26b890865eb347fb51f6f79442f27c57c261443a51368eb6f",'
    b'"lean_commit":"d8b18978322de05a8f3dba51ef03cf5461676c17",'
    b'"lean_executable_sha256":"e8baaa71855a616dc351028f3ad2200051b0671f423a1696a100e809302d5550",'
    b'"lean_release_asset":"lean-4.33.0-linux.tar.zst",'
    b'"lean_release_asset_bytes":574882764,'
    b'"lean_release_asset_sha256":"4b3fb03c29a1e0a253fb1d11f9bae3725f19a0dc6fc09b3ea16d2c9df3349e2c",'
    b'"lean_toolchain":"leanprover/lean4:v4.33.0",'
    b'"mathlib_commit":"db584cd6d46c92f209a44c0f1c829460d327499d",'
    b'"platform":"x86_64-unknown-linux-gnu",'
    b'"schema":"mathhead.lean-toolchain-lock.v1"}\n'
)

_ROLE_MEDIA = {
    "checker_result": "application/json",
    "generated_source": "application/vnd.mathhead.lean+text",
    "lake_manifest": "application/json",
    "lakefile": "application/toml",
    "proof_term": "application/json",
    "toolchain_lock": "application/json",
    "toolchain_selector": "text/plain",
}
_ROLES = tuple(sorted(_ROLE_MEDIA))
_COMMAND = (
    "lake",
    "env",
    "lean",
    "-o",
    ".lake/build/lib/lean/MathHead/Generated.olean",
    "MathHead/Generated.lean",
)
_FORBIDDEN_SOURCE_WORDS = (
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
)


class LeanVerificationValidationError(ValueError):
    """Classified failure at the Lean export or result boundary."""

    def __init__(self, kind: str, detail: str) -> None:
        self.kind = kind
        self.detail = detail
        super().__init__(f"{kind}: {detail}")


class _LeanValue:
    __slots__ = ()

    def __reduce__(self) -> NoReturn:
        raise TypeError("Lean verification values cannot be pickled")

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del protocol
        raise TypeError("Lean verification values cannot be pickled")

    def __copy__(self) -> _LeanValue:
        return self

    def __deepcopy__(self, memo: dict[int, Any]) -> _LeanValue:
        del memo
        return self


@dataclass(frozen=True, slots=True, init=False)
class LeanExport(_LeanValue):
    request: bytes
    artifacts: tuple[bytes, ...]
    request_sha256: str
    project_sha256: str
    proof_term_sha256: str
    checker_result_sha256: str
    statement_sha256: str
    source_sha256: str
    theorem_name: str
    statement_kind: str
    status: str
    authority: str

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PermissionError("use build_lean_export() or parse_lean_export()")

    def __init_subclass__(cls, **kwargs: object) -> NoReturn:
        del cls, kwargs
        raise TypeError("LeanExport is final")


def _fail(kind: str, detail: str) -> NoReturn:
    raise LeanVerificationValidationError(kind, detail)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_json(value: object) -> bytes:
    try:
        encoded = json.dumps(
            value,
            ensure_ascii=True,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("ascii")
    except (TypeError, ValueError, OverflowError) as exc:
        _fail("canonical", f"canonical JSON encoding failed: {type(exc).__name__}")
    return encoded + b"\n"


def _fraction_object(value: Fraction) -> dict[str, int]:
    return {"denominator": value.denominator, "numerator": value.numerator}


def _statement_object(statement: object) -> dict[str, object]:
    if type(statement) is DividesStatement:
        return {
            "kind": "divides",
            "modulus": statement.modulus,
            "polynomial": list(statement.polynomial),
        }
    if type(statement) is PolynomialIdentityStatement:
        return {
            "kind": "polynomial_identity",
            "lhs": [_fraction_object(value) for value in statement.lhs],
            "rhs": [_fraction_object(value) for value in statement.rhs],
        }
    if type(statement) is SumIdentityStatement:
        return {
            "closed_form": [_fraction_object(value) for value in statement.closed_form],
            "kind": "sum_identity",
            "summand": [_fraction_object(value) for value in statement.summand],
        }
    _fail("source", f"unsupported checker statement: {type(statement).__name__}")


def _integer_polynomial(coefficients: tuple[int, ...], variable: str, type_name: str) -> str:
    terms: list[str] = []
    for degree, coefficient in enumerate(coefficients):
        if coefficient.bit_length() > MAX_INTEGER_BITS:
            _fail("budget", "polynomial coefficient exceeds the integer budget")
        power = "1" if degree == 0 else variable if degree == 1 else f"({variable} ^ {degree})"
        terms.append(f"(({coefficient} : {type_name}) * {power})")
    return "(" + " + ".join(terms) + ")"


def _rational(value: Fraction) -> str:
    if (
        value.numerator.bit_length() > MAX_INTEGER_BITS
        or value.denominator.bit_length() > MAX_INTEGER_BITS
    ):
        _fail("budget", "rational coefficient exceeds the integer budget")
    return f"(({value.numerator} : \u211a) / ({value.denominator} : \u211a))"


def _rational_polynomial(coefficients: tuple[Fraction, ...], variable: str) -> str:
    terms: list[str] = []
    for degree, coefficient in enumerate(coefficients):
        power = "1" if degree == 0 else variable if degree == 1 else f"({variable} ^ {degree})"
        terms.append(f"({_rational(coefficient)} * {power})")
    return "(" + " + ".join(terms) + ")"


def _source_for_statement(statement: object, theorem_name: str) -> bytes:
    lines = [
        "import Mathlib",
        "",
        "set_option autoImplicit false",
        "set_option maxHeartbeats 1000000",
        "set_option maxRecDepth 100000",
        "",
        "namespace MathHead.Generated",
        "",
    ]
    if type(statement) is DividesStatement:
        integer = _integer_polynomial(statement.polynomial, "n", "\u2124")
        modular = _integer_polynomial(
            statement.polynomial, "x", f"ZMod {statement.modulus}"
        )
        lines.extend(
            [
                f"theorem {theorem_name} : \u2200 n : \u2124, "
                f"({statement.modulus} : \u2124) \u2223 {integer} := by",
                "  intro n",
                f"  have key : \u2200 x : ZMod {statement.modulus}, {modular} = 0 := by decide",
                f"  have reduced : (({integer} : \u2124) : ZMod {statement.modulus}) = 0 := by",
                "    push_cast",
                f"    simpa using key (n : ZMod {statement.modulus})",
                "  exact (ZMod.intCast_zmod_eq_zero_iff_dvd _ "
                f"{statement.modulus}).mp reduced",
            ]
        )
    elif type(statement) is PolynomialIdentityStatement:
        lhs = _rational_polynomial(statement.lhs, "n")
        rhs = _rational_polynomial(statement.rhs, "n")
        lines.extend(
            [
                f"theorem {theorem_name} : \u2200 n : \u211a, {lhs} = {rhs} := by",
                "  intro n",
                "  ring",
            ]
        )
    elif type(statement) is SumIdentityStatement:
        summand = _rational_polynomial(statement.summand, "((k + 1 : \u2115) : \u211a)")
        closed = _rational_polynomial(statement.closed_form, "(n : \u211a)")
        lines.extend(
            [
                f"theorem {theorem_name} : \u2200 n : \u2115,",
                f"    (\u2211 k \u2208 Finset.range n, {summand}) = {closed} := by",
                "  intro n",
                "  induction n with",
                "  | zero => norm_num",
                "  | succ n ih =>",
                "      rw [Finset.sum_range_succ, ih]",
                "      push_cast",
                "      ring",
            ]
        )
    else:
        _fail("source", f"unsupported checker statement: {type(statement).__name__}")
    lines.extend(["", "end MathHead.Generated", ""])
    source = "\n".join(lines).encode("utf-8")
    if len(source) > MAX_SOURCE_BYTES:
        _fail("budget", f"generated source exceeds {MAX_SOURCE_BYTES} bytes")
    lowered = source.decode("utf-8").lower()
    for word in _FORBIDDEN_SOURCE_WORDS:
        if word in lowered:
            _fail("source", f"generated source contains forbidden token: {word}")
    return source


def _artifact_record(role: str, data: bytes) -> dict[str, object]:
    if not data or len(data) > MAX_ARTIFACT_BYTES:
        _fail("budget", f"{role} artifact length is outside the contract")
    return {
        "bytes": len(data),
        "media_type": _ROLE_MEDIA[role],
        "role": role,
        "sha256": _sha256(data),
    }


def _new_export(fields: dict[str, object]) -> LeanExport:
    value = object.__new__(LeanExport)
    for name, field in fields.items():
        object.__setattr__(value, name, field)
    return value


def build_lean_export(term: ProofTerm, checker_result: CheckerResult) -> LeanExport:
    """Build one canonical written-only export from a fresh verified checker result."""
    try:
        validate_proof_term(term)
        validate_checker_result(checker_result)
    except (TypeError, ValueError, AttributeError, RecursionError) as exc:
        _fail("result", f"proof or checker validation failed: {type(exc).__name__}")
    if (
        checker_result.verdict != "verified"
        or checker_result.authority != "checker_attestation"
        or checker_result.proof_term != term
        or checker_result.statement is None
    ):
        _fail("result", "only a matching verified checker attestation may be exported")

    proof_bytes = proof_term_to_bytes(term)
    checker_bytes = checker_result_to_bytes(checker_result)
    statement_object = _statement_object(checker_result.statement)
    statement_bytes = _canonical_json(statement_object)
    proof_digest = _sha256(proof_bytes)
    checker_digest = _sha256(checker_bytes)
    statement_digest = _sha256(statement_bytes)
    name_basis = f"{proof_digest}:{statement_digest}".encode("ascii")
    theorem_name = "mathhead_" + _sha256(name_basis)[:16]
    source = _source_for_statement(checker_result.statement, theorem_name)

    by_role = {
        "checker_result": checker_bytes,
        "generated_source": source,
        "lake_manifest": LAKE_MANIFEST_BYTES,
        "lakefile": LAKEFILE_BYTES,
        "proof_term": proof_bytes,
        "toolchain_lock": TOOLCHAIN_LOCK_BYTES,
        "toolchain_selector": LEAN_TOOLCHAIN_BYTES,
    }
    records = [_artifact_record(role, by_role[role]) for role in _ROLES]
    project_records = [
        record
        for record in records
        if record["role"]
        in {
            "generated_source",
            "lake_manifest",
            "lakefile",
            "toolchain_lock",
            "toolchain_selector",
        }
    ]
    project_digest = _sha256(
        _canonical_json(
            {"artifacts": project_records, "schema": "mathhead.lean-project.v1"}
        )
    )
    request_object = {
        "artifacts": records,
        "checker_result_sha256": checker_digest,
        "command": list(_COMMAND),
        "contract_id": LEAN_VERIFICATION_CONTRACT_ID,
        "environment_policy": "mathhead.lean-hermetic.v1",
        "limits": {
            "artifact_bytes": MAX_ARTIFACT_BYTES,
            "diagnostic_codepoints": 512,
            "integer_bits": MAX_INTEGER_BITS,
            "output_bytes": MAX_OUTPUT_BYTES,
            "source_bytes": MAX_SOURCE_BYTES,
            "theorems": 1,
            "total_seconds": MAX_TOTAL_SECONDS,
        },
        "project_sha256": project_digest,
        "proof_term_sha256": proof_digest,
        "schema": LEAN_REQUEST_SCHEMA,
        "source_sha256": _sha256(source),
        "statement_kind": statement_object["kind"],
        "statement_sha256": statement_digest,
        "theorem_name": theorem_name,
        "toolchain": {
            "lean_commit": LEAN_COMMIT,
            "lean_release_asset_sha256": LEAN_RELEASE_ASSET_SHA256,
            "lean_toolchain": LEAN_TOOLCHAIN,
            "mathlib_commit": MATHLIB_COMMIT,
            "platform": LEAN_PLATFORM,
        },
    }
    request = _canonical_json(request_object)
    if len(request) > MAX_REQUEST_BYTES:
        _fail("budget", f"Lean request exceeds {MAX_REQUEST_BYTES} bytes")
    artifacts = tuple(by_role[role] for role in _ROLES)
    return _new_export(
        {
            "artifacts": artifacts,
            "authority": "none",
            "checker_result_sha256": checker_digest,
            "project_sha256": project_digest,
            "proof_term_sha256": proof_digest,
            "request": request,
            "request_sha256": _sha256(request),
            "source_sha256": _sha256(source),
            "statement_kind": str(statement_object["kind"]),
            "statement_sha256": statement_digest,
            "status": "export_written",
            "theorem_name": theorem_name,
        }
    )


class _DuplicateKey(ValueError):
    pass


def _pairs_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKey(key)
        result[key] = value
    return result


def _reject_number(value: str) -> NoReturn:
    del value
    raise ValueError("floating-point JSON numbers are forbidden")


def parse_lean_export(request: bytes, artifacts: tuple[bytes, ...]) -> LeanExport:
    """Rebuild one export from exact bytes instead of trusting stored fields."""
    if type(request) is not bytes or type(artifacts) is not tuple:
        _fail("type", "Lean request and artifact tuple must use exact runtime types")
    if len(request) > MAX_REQUEST_BYTES or len(artifacts) != len(_ROLES):
        _fail("budget", "Lean request or artifact count exceeds the contract")
    if any(type(item) is not bytes for item in artifacts):
        _fail("type", "every Lean artifact must be exact bytes")
    try:
        decoded = request.decode("utf-8", errors="strict")
        raw = json.loads(
            decoded,
            object_pairs_hook=_pairs_object,
            parse_float=_reject_number,
            parse_constant=_reject_number,
        )
    except UnicodeDecodeError as exc:
        _fail("encoding", f"invalid UTF-8 at byte {exc.start}")
    except _DuplicateKey as exc:
        _fail("duplicate", f"duplicate JSON key: {exc.args[0]}")
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        _fail("json", f"invalid Lean request JSON: {type(exc).__name__}")
    except RecursionError:
        _fail("budget", "Lean request nesting exceeds the parser budget")
    if type(raw) is not dict or request != _canonical_json(raw):
        _fail("canonical", "Lean request bytes are not canonical")
    records = raw.get("artifacts")
    if type(records) is not list or len(records) != len(_ROLES):
        _fail("schema", "Lean request artifact records differ")
    for index, (role, data) in enumerate(zip(_ROLES, artifacts, strict=True)):
        if records[index] != _artifact_record(role, data):
            _fail("identity", f"Lean artifact record differs for role {role}")
    proof = parse_proof_term(artifacts[_ROLES.index("proof_term")])
    checker = parse_checker_result(artifacts[_ROLES.index("checker_result")])
    rebuilt = build_lean_export(proof, checker)
    if rebuilt.request != request or rebuilt.artifacts != artifacts:
        _fail("result", "Lean export differs from complete independent reconstruction")
    return rebuilt


def validate_lean_export(value: object) -> None:
    """Validate an in-memory export without trusting constructor history."""
    if type(value) is not LeanExport:
        _fail("result", f"unknown Lean export type: {type(value).__name__}")
    try:
        rebuilt = parse_lean_export(value.request, value.artifacts)
    except AttributeError:
        _fail("result", "Lean export has missing fields")
    if value != rebuilt:
        _fail("result", "Lean export fields differ from reconstruction")


__all__ = [
    "ACQUISITION_LAKEFILE_BYTES",
    "ACQUISITION_MANIFEST_BYTES",
    "LAKEFILE_BYTES",
    "LAKE_MANIFEST_BYTES",
    "LAKE_EXECUTABLE_SHA256",
    "LEAN_COMMIT",
    "LEAN_EXECUTABLE_SHA256",
    "LEAN_PLATFORM",
    "LEAN_RELEASE_ASSET_SHA256",
    "LEAN_REQUEST_SCHEMA",
    "LEAN_TOOLCHAIN",
    "LEAN_TOOLCHAIN_BYTES",
    "LEAN_VERIFICATION_CONTRACT_ID",
    "LEAN_VERIFICATION_CONTRACT_SHA256",
    "LeanExport",
    "LeanVerificationValidationError",
    "MATHLIB_COMMIT",
    "MAX_ARTIFACT_BYTES",
    "MAX_OUTPUT_BYTES",
    "MAX_REQUEST_BYTES",
    "MAX_SOURCE_BYTES",
    "MAX_TOTAL_SECONDS",
    "TOOLCHAIN_LOCK_BYTES",
    "build_lean_export",
    "parse_lean_export",
    "validate_lean_export",
]
