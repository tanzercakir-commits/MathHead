"""Fresh external Lean dispatch from an exact MH-035 provenance bundle."""

from __future__ import annotations

import json

from mathhead.kernel.checkers import KERNEL_CHECKER_ID
from mathhead.kernel.provenance import replay_provenance_bundle
from mathhead.proof_assistant.export import (
    LeanVerificationValidationError,
    parse_lean_export,
)
from mathhead.proof_assistant.lean import (
    LeanVerificationResult,
    _rejected_export_result,
    prepare_lean_project,
    verify_with_lean,
)


def replay_lean_provenance(
    manifest: bytes,
    objects: tuple[bytes, ...],
    request: bytes,
    artifacts: tuple[bytes, ...],
    project_root: str,
) -> LeanVerificationResult:
    """Replay a complete provenance graph, then freshly invoke pinned Lean.

    Stored Lean result bytes are deliberately not an input.  The proof term and
    checker result inside the canonical Lean request must be byte-identical to
    their content-addressed MH-035 objects before any project write or process.
    """
    try:
        export = parse_lean_export(request, artifacts)
    except (LeanVerificationValidationError, TypeError, ValueError, RecursionError):
        return verify_with_lean(request, artifacts, project_root)

    provenance = replay_provenance_bundle(manifest, objects)
    if (
        provenance.verdict != "verified"
        or provenance.authority != "checker_attestation"
        or provenance.checker_id != KERNEL_CHECKER_ID
        or not provenance.bundle_complete
        or provenance.manifest is None
        or provenance.objects is None
    ):
        return _rejected_export_result(
            export,
            "content-addressed provenance did not freshly replay with checker authority",
        )

    try:
        provenance_manifest = json.loads(provenance.manifest.decode("ascii"))
        provenance_by_role = {
            record["role"]: data
            for record, data in zip(
                provenance_manifest["objects"], provenance.objects, strict=True
            )
        }
        request_manifest = json.loads(export.request.decode("ascii"))
        request_by_role = {
            record["role"]: data
            for record, data in zip(
                request_manifest["artifacts"], export.artifacts, strict=True
            )
        }
    except (UnicodeError, ValueError, KeyError, TypeError, RecursionError):
        return _rejected_export_result(
            export, "content-addressed provenance role mapping is invalid"
        )
    if (
        provenance_by_role.get("proof_term") != request_by_role.get("proof_term")
        or provenance_by_role.get("checker_result")
        != request_by_role.get("checker_result")
        or provenance.replayed_result_sha256 != export.checker_result_sha256
    ):
        return _rejected_export_result(
            export,
            "Lean request does not match the freshly replayed provenance proof and result",
        )

    try:
        prepare_lean_project(export, project_root)
    except (LeanVerificationValidationError, OSError, ValueError):
        return verify_with_lean(request, artifacts, project_root)
    return verify_with_lean(request, artifacts, project_root)


__all__ = ["replay_lean_provenance"]
