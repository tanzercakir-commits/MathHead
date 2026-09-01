"""Versioned external proof-assistant boundaries."""

from mathhead.proof_assistant.export import (
    LeanExport,
    LeanVerificationValidationError,
    build_lean_export,
    parse_lean_export,
)
from mathhead.proof_assistant.lean import (
    LeanVerificationResult,
    execution_artifacts,
    export_written_result,
    lean_verification_result_sha256,
    lean_verification_result_to_bytes,
    parse_lean_verification_result,
    prepare_lean_project,
    validate_lean_verification_result,
    verify_with_lean,
)
from mathhead.proof_assistant.provenance import replay_lean_provenance

__all__ = [
    "LeanExport",
    "LeanVerificationResult",
    "LeanVerificationValidationError",
    "build_lean_export",
    "execution_artifacts",
    "export_written_result",
    "lean_verification_result_sha256",
    "lean_verification_result_to_bytes",
    "parse_lean_export",
    "parse_lean_verification_result",
    "prepare_lean_project",
    "replay_lean_provenance",
    "validate_lean_verification_result",
    "verify_with_lean",
]
