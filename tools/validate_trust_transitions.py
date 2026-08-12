#!/usr/bin/env python3
"""Generate and validate the MH-037 trust-transition catalogue and G3 report.

The production auditor is deliberately pure and non-authoritative.  This
repository tool owns filesystem inventory, real checker red-team probes, the
static effect audit, and deterministic report generation.
"""

from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Any, Mapping, NoReturn, Sequence

try:
    from jsonschema import Draft202012Validator
    from jsonschema.exceptions import SchemaError, ValidationError
except ImportError:  # Dependency-minimal status profile.
    Draft202012Validator = None  # type: ignore[assignment,misc]
    SchemaError = ValidationError = Exception  # type: ignore[assignment,misc]


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from mathhead.kernel.checkers import (  # noqa: E402
    check_proof_term,
    checker_result_to_bytes,
)
from mathhead.kernel.proof_terms import (  # noqa: E402
    proof_term_to_bytes,
    residue,
)
from mathhead.kernel.provenance import (  # noqa: E402
    canonical_provenance_manifest_bytes,
    checker_configuration_bytes,
    provenance_replay_result_to_bytes,
    replay_provenance_bundle,
)
from mathhead.kernel.sat import (  # noqa: E402
    canonical_cnf_bytes,
    canonical_drup_bytes,
    canonical_sat_assignment_bytes,
    check_sat_certificate,
    sat_replay_result_to_bytes,
)
from mathhead.kernel.trust_transitions import (  # noqa: E402
    CATALOGUE_SHA256,
    CONTRACT_ID,
    CONTRACT_SHA256,
    EFFECT_SURFACES,
    audit_trust_transition,
    transition_audit_result_to_bytes,
    trust_transition_attempt_to_bytes,
    trust_transition_issuer_key,
    validate_trust_transition_catalogue,
)
from mathhead.proof_assistant.export import build_lean_export  # noqa: E402
from mathhead.proof_assistant.lean import (  # noqa: E402
    export_written_result,
    lean_verification_result_to_bytes,
    verify_with_lean,
)


CATALOGUE_PATH = Path("docs/trust/trust-transition-catalogue-v1.json")
REPORT_PATH = Path("docs/trust/reports/trust-transition-g3-v1.json")
TRUST_INVENTORY_PATH = Path("docs/trust/trust-base-v1.json")
CONTRACT_PATH = Path("docs/contracts/MH-C-TRUST-TRANSITION-001.json")
SCHEMA_PATHS = (
    Path("docs/contracts/schemas/trust-transition-attempt-v1.schema.json"),
    Path("docs/contracts/schemas/trust-transition-audit-result-v1.schema.json"),
    Path("docs/contracts/schemas/trust-transition-catalogue-v1.schema.json"),
    Path("docs/contracts/schemas/trust-transition-report-v1.schema.json"),
)
SCHEMA_SHA256 = {
    SCHEMA_PATHS[0]: "570ff6ed9905b9b3c39b45f51693e3f2b157d3f9ce93a12ce7a4cc3a8e4ca29a",
    SCHEMA_PATHS[1]: "8b8b48110d7a2c429b18eec52427e9878bd7c8dde05fb8c9b29dac1a061b89bf",
    SCHEMA_PATHS[2]: "205dfc544f130203ef092dbda050c763b93cbd92b9d2d4606fe95516843f2e1e",
    SCHEMA_PATHS[3]: "e043d8f6c3425f9806512ced28daaa3a66da080388c0e6a37e6f649eaf74d2f3",
}
CONTRACTS = {
    "MH-C-KERNEL-CHECKER-002": "1baf3b44734369fdb298609ad0230062686697a7198401d6fc53f161c70a678e",
    "MH-C-LEAN-VERIFICATION-001": "b5c8bd2b3f93698d404042e7785d6dc503968481de13a77aee71769079a4b60a",
    "MH-C-PROOF-TERM-001": "20c501b77e370c4258523a291e83b15a99ed6308e002d9a54d0abc3bb18199ac",
    "MH-C-PROVENANCE-REPLAY-001": "31a664252096b47a10dfe14d999a5fe7bf278612fdebd003c3982123a0bcdb67",
    "MH-C-SAT-REPLAY-001": "0bf4edbba9285070ef525ae584124ae4fab2762ce83a42f2434c18c8db6f2b50",
    "MH-C-TRUST-BASE-001": "2d2c23da4d3b167c5220c7548602f11403af7634031c438a8f61ac8e3e191456",
    CONTRACT_ID: CONTRACT_SHA256,
}
REPORT_SCHEMA = "mathhead.trust-transition-report.v1"
ZERO_SHA256 = "0" * 64
STRONG_TIERS = {"checker_attestation", "external_proof_assistant"}
ISSUER_SITES = (
    (
        "mathhead.kernel.checkers.check_proof_term",
        Path("src/mathhead/kernel/checkers.py"),
        "check_proof_term",
        "checker_attestation",
    ),
    (
        "mathhead.kernel.provenance.replay_provenance_bundle",
        Path("src/mathhead/kernel/provenance.py"),
        "replay_provenance_bundle",
        "checker_attestation",
    ),
    (
        "mathhead.kernel.sat.check_sat_certificate",
        Path("src/mathhead/kernel/sat.py"),
        "check_sat_certificate",
        "checker_attestation",
    ),
    (
        "mathhead.proof_assistant.lean.verify_with_lean",
        Path("src/mathhead/proof_assistant/lean.py"),
        "verify_with_lean",
        "external_proof_assistant",
    ),
    (
        "mathhead.proof_assistant.provenance.replay_lean_provenance",
        Path("src/mathhead/proof_assistant/provenance.py"),
        "replay_lean_provenance",
        "external_proof_assistant",
    ),
)
AUTHORITY_LITERAL_COUNTS = {
    "src/mathhead/capability_registry.py": {
        "checker_attestation": 1,
        "producer_report": 1,
    },
    "src/mathhead/kernel/checkers.py": {"checker_attestation": 2},
    "src/mathhead/kernel/provenance.py": {"checker_attestation": 2},
    "src/mathhead/kernel/sat.py": {"checker_attestation": 1},
    "src/mathhead/kernel/trust_transitions.py": {
        "checker_attestation": 1,
        "external_proof_assistant": 1,
        "producer_report": 1,
        "solver_verdict": 1,
    },
    "src/mathhead/problem_sessions.py": {
        "checker_attestation": 2,
        "external_proof_assistant": 2,
        "producer_report": 1,
        "solver_verdict": 1,
    },
    "src/mathhead/proof_assistant/export.py": {"checker_attestation": 1},
    "src/mathhead/proof_assistant/lean.py": {"external_proof_assistant": 2},
    "src/mathhead/proof_assistant/provenance.py": {"checker_attestation": 1},
}
FORBIDDEN_EFFECT_CALLS = {
    "check_proof_term",
    "check_sat_certificate",
    "replay_lean_provenance",
    "replay_provenance_bundle",
    "verify_with_lean",
}
CLASSIFIED_EFFECT_ADAPTER_CALLS = {
    ("runtime.clock", "src/mathhead/drat.py", "check_sat_certificate"),
}


class TrustTransitionReportError(RuntimeError):
    """A deterministic catalogue, mutation, source, or report check failed."""


def _fail(detail: str) -> NoReturn:
    raise TrustTransitionReportError(detail)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


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
    ).encode("utf-8")


def _load_canonical(path: Path) -> tuple[dict[str, Any], bytes]:
    raw = (ROOT / path).read_bytes()
    try:
        value = json.loads(raw)
    except (UnicodeError, json.JSONDecodeError) as exc:
        _fail(f"{path}: invalid JSON: {exc}")
    if type(value) is not dict or _canonical(value) != raw:
        _fail(f"{path}: JSON is not one canonical object")
    return value, raw


def _load_json(path: Path) -> tuple[dict[str, Any], bytes]:
    raw = (ROOT / path).read_bytes()
    try:
        value = json.loads(raw)
    except (UnicodeError, json.JSONDecodeError) as exc:
        _fail(f"{path}: invalid JSON: {exc}")
    if type(value) is not dict:
        _fail(f"{path}: JSON root is not an object")
    return value, raw


def _safe_output_path(path: Path) -> Path:
    candidate = path if path.is_absolute() else ROOT / path
    candidate = candidate.absolute()
    root = ROOT.resolve()
    try:
        lexical_parent = candidate.parent.relative_to(ROOT)
    except ValueError:
        _fail(f"{path}: output parent escapes the repository")
    if ".." in lexical_parent.parts:
        _fail(f"{path}: output parent contains traversal")
    current = ROOT
    for part in lexical_parent.parts:
        current /= part
        if current.is_symlink():
            _fail(f"{path}: output parent contains a symbolic link")
    candidate.parent.mkdir(parents=True, exist_ok=True)
    try:
        candidate.parent.resolve().relative_to(root)
    except (OSError, ValueError):
        _fail(f"{path}: resolved output parent escapes the repository")
    if candidate.exists() or candidate.is_symlink():
        if candidate.is_symlink() or not candidate.is_file():
            _fail(f"{path}: output target is not a regular file")
        try:
            links = candidate.stat(follow_symlinks=False).st_nlink
        except OSError as exc:
            _fail(f"{path}: cannot inspect output target: {exc}")
        if links != 1:
            _fail(f"{path}: output target has {links} hard links")
    return candidate


def _write_atomic(path: Path, data: bytes) -> None:
    target = _safe_output_path(path)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=target.parent, prefix=f".{target.name}.", delete=False
        ) as handle:
            temporary = Path(handle.name)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
        temporary = None
    finally:
        if temporary is not None:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass


def _contract_ref(contract_id: str) -> dict[str, str]:
    return {"contract_id": contract_id, "sha256": CONTRACTS[contract_id]}


def _contract_role(contract_id: str) -> str:
    return "contract_" + contract_id.removeprefix("MH-C-").lower().replace("-", "_")


def _artifact(
    role: str,
    data: bytes,
    *,
    media_type: str = "application/json",
    schema: str = "mathhead.bound-artifact.v1",
) -> dict[str, object]:
    return {
        "bytes": len(data),
        "media_type": media_type,
        "role": role,
        "schema": schema,
        "sha256": _sha(data),
    }


def _configuration(component_id: str, transition_id: str) -> bytes:
    return _canonical(
        {
            "component_id": component_id,
            "schema": "mathhead.trust-transition-issuer-configuration.v1",
            "transition_id": transition_id,
        }
    )


def _source_set(surface: Mapping[str, Any]) -> bytes:
    sources = []
    for relative in surface["source_paths"]:
        data = (ROOT / relative).read_bytes()
        sources.append({"path": relative, "sha256": _sha(data)})
    return _canonical(
        {
            "schema": "mathhead.trust-transition-source-set.v1",
            "sources": sources,
            "surface_id": surface["surface_id"],
        }
    )


def _foundation_values() -> dict[str, bytes]:
    schemas = {
        "certificate": "mathhead.certificate.v1",
        "engine_result": "mathhead.engine-result.v1",
        "evidence": "mathhead.evidence.v1",
        "problem_ir": "mathhead.problem-ir.v1",
        "resource_budget": "mathhead.resource-budget.v1",
        "theory_context": "mathhead.theory-context.v1",
        "theory_plugin": "mathhead.theory-plugin.v1",
    }
    values = {role: _canonical({"schema": schema}) for role, schema in schemas.items()}
    values["theory_plugin"] = _canonical(
        {
            "plugin_id": "org.mathhead.trust-transition-control",
            "plugin_version": "1.0.0",
            "schema": "mathhead.theory-plugin.v1",
        }
    )
    return values


def _provenance_dependencies(role: str, roles: set[str]) -> list[str]:
    foundation = ["problem_ir", "resource_budget", "theory_context", "theory_plugin"]
    inputs = [name for name in ("proof_term", "cnf", "sat_certificate") if name in roles]
    if role in {"problem_ir", "resource_budget", "theory_plugin", "checker_contract"}:
        return []
    if role == "theory_context":
        return ["problem_ir"]
    if role in {"proof_term", "cnf"}:
        return ["problem_ir", "theory_context"]
    if role == "sat_certificate":
        return ["cnf"]
    if role == "evidence":
        return foundation
    if role == "certificate":
        return [*foundation, "evidence", *inputs]
    if role == "engine_result":
        return [*foundation, "evidence", "certificate"]
    if role == "checker_implementation":
        return ["checker_contract"]
    if role == "checker_configuration":
        return ["checker_contract", "checker_implementation"]
    if role == "checker_result":
        return sorted(roles - {"checker_result"})
    raise AssertionError(role)


def build_provenance_control(
    checker_id: str = "mathhead.kernel.checker.v2",
) -> tuple[bytes, tuple[bytes, ...]]:
    """Build a small complete bundle used by positive and adversarial controls."""

    checker = {
        "mathhead.kernel.checker.v2": {
            "contract_id": "MH-C-KERNEL-CHECKER-002",
            "implementation": Path("src/mathhead/kernel/checkers.py"),
            "result_schema": "mathhead.kernel-checker-result.v2",
        },
        "mathhead.kernel.sat-replay.v1": {
            "contract_id": "MH-C-SAT-REPLAY-001",
            "implementation": Path("src/mathhead/kernel/sat.py"),
            "result_schema": "mathhead.sat-replay-result.v1",
        },
    }[checker_id]
    values = _foundation_values()
    contract_id = checker["contract_id"]
    contract_sha = CONTRACTS[contract_id]
    values["checker_contract"] = (ROOT / f"docs/contracts/{contract_id}.json").read_bytes()
    values["checker_implementation"] = (ROOT / checker["implementation"]).read_bytes()
    values["checker_configuration"] = checker_configuration_bytes(checker_id)
    if checker_id == "mathhead.kernel.checker.v2":
        term = residue(2, (0, -1, 0, 1))
        values["proof_term"] = proof_term_to_bytes(term)
        values["checker_result"] = checker_result_to_bytes(check_proof_term(term))
    else:
        cnf = canonical_cnf_bytes(((1,),))
        certificate = canonical_sat_assignment_bytes(cnf, (1,))
        values["cnf"] = cnf
        values["sat_certificate"] = certificate
        values["checker_result"] = sat_replay_result_to_bytes(
            check_sat_certificate(cnf, certificate)
        )
    foundation_contracts = {
        "certificate": (
            "MH-C-CERTIFICATE-001",
            "0a21aca8058fb5fc9900decb6dcd14e179c7a5171f7653ea965b5d34edd59740",
        ),
        "engine_result": (
            "MH-C-ENGINE-RESULT-001",
            "6c57ba36c78a2e15b27d3e464342b890f71b2d298f6395c7f4b0cd5aa5a09370",
        ),
        "evidence": (
            "MH-C-EVIDENCE-001",
            "c68c20ca599cfdd7aabe9b85f2817c6c3f1a121289334136ff048768ee20c3b3",
        ),
        "problem_ir": (
            "MH-C-PROBLEM-IR-002",
            "6d657195869a5746c5a41492c334b32ee5edd2ca84eb7facfade44f53334c286",
        ),
        "resource_budget": (
            "MH-C-RESOURCE-BUDGET-001",
            "eef46d8e6d37ada50fb9af1ab6a1db5665070896f83c5d9155fc6ee2777f5045",
        ),
        "theory_context": (
            "MH-C-THEORY-CONTEXT-001",
            "d2cb0e61c33327a6c2d5887872278179b5e11e42b6358b1661b60386e60e888d",
        ),
        "theory_plugin": (
            "MH-C-THEORY-PLUGIN-001",
            "2226973b172a3b2ce489aae3baae7820c3b7b57ab76cff089927f68a2759a8e8",
        ),
    }
    roles = set(values)
    records = []
    for role in sorted(roles):
        data = values[role]
        schema: str | None = "mathhead.bound-artifact.v1"
        media = "application/json"
        if role in foundation_contracts:
            role_contract, role_contract_sha = foundation_contracts[role]
            schema = json.loads(data)["schema"]
        elif role == "checker_contract":
            role_contract, role_contract_sha = contract_id, contract_sha
            schema = "mathhead.function-contract.v1"
        elif role == "checker_implementation":
            role_contract, role_contract_sha = contract_id, contract_sha
            schema, media = None, "text/x-python"
        elif role == "checker_configuration":
            role_contract, role_contract_sha = contract_id, contract_sha
            schema = "mathhead.checker-configuration.v1"
        elif role == "checker_result":
            role_contract, role_contract_sha = contract_id, contract_sha
            schema = checker["result_schema"]
        elif role == "proof_term":
            role_contract = "MH-C-PROOF-TERM-001"
            role_contract_sha = CONTRACTS[role_contract]
            schema = "mathhead.proof-term.v1"
        elif role == "cnf":
            role_contract, role_contract_sha = contract_id, contract_sha
            schema, media = "mathhead.cnf.v1", "application/octet-stream"
        else:
            role_contract, role_contract_sha = contract_id, contract_sha
            schema, media = "mathhead.sat-certificate.v1", "application/octet-stream"
        records.append(
            {
                "byte_count": len(data),
                "contract_id": role_contract,
                "contract_sha256": role_contract_sha,
                "depends_on_sha256": sorted(
                    _sha(values[name]) for name in _provenance_dependencies(role, roles)
                ),
                "media_type": media,
                "role": role,
                "schema": schema,
                "sha256": _sha(data),
            }
        )
    manifest = canonical_provenance_manifest_bytes(
        {
            "objects": records,
            "plugin": {
                "plugin_id": "org.mathhead.trust-transition-control",
                "plugin_version": "1.0.0",
            },
            "replay": {
                "checker_configuration_sha256": _sha(values["checker_configuration"]),
                "checker_contract_id": contract_id,
                "checker_contract_sha256": contract_sha,
                "checker_id": checker_id,
                "checker_implementation_sha256": _sha(values["checker_implementation"]),
                "recorded_result_sha256": _sha(values["checker_result"]),
            },
            "schema": "mathhead.provenance-manifest.v1",
        }
    )
    return manifest, tuple(values[record["role"]] for record in records)


def _transition_blueprints() -> list[dict[str, Any]]:
    return [
        {
            "id": "transition.checker.lean.issue",
            "source": "checker_attestation",
            "target": "external_proof_assistant",
            "operation": "issue",
            "component": "mathhead.proof-assistant.lean",
            "entry": "mathhead.proof_assistant.lean.verify_with_lean",
            "role": "proof_assistant",
            "contract": "MH-C-LEAN-VERIFICATION-001",
            "contracts": ["MH-C-LEAN-VERIFICATION-001", "MH-C-PROVENANCE-REPLAY-001"],
            "implementation": Path("src/mathhead/proof_assistant/lean.py"),
            "fresh": True,
            "independent": True,
            "requires_fresh": True,
            "requires_independent": True,
            "status": "verified",
        },
        {
            "id": "transition.checker.provenance-proof.preserve",
            "source": "checker_attestation",
            "target": "checker_attestation",
            "operation": "preserve",
            "component": "mathhead.kernel.provenance-proof",
            "entry": "mathhead.kernel.provenance.replay_provenance_bundle",
            "role": "checker",
            "contract": "MH-C-PROVENANCE-REPLAY-001",
            "contracts": ["MH-C-KERNEL-CHECKER-002", "MH-C-PROVENANCE-REPLAY-001"],
            "implementation": Path("src/mathhead/kernel/provenance.py"),
            "fresh": True,
            "independent": True,
            "requires_fresh": True,
            "requires_independent": True,
            "status": "verified",
        },
        {
            "id": "transition.checker.provenance-sat.preserve",
            "source": "checker_attestation",
            "target": "checker_attestation",
            "operation": "preserve",
            "component": "mathhead.kernel.provenance-sat",
            "entry": "mathhead.kernel.provenance.replay_provenance_bundle",
            "role": "checker",
            "contract": "MH-C-PROVENANCE-REPLAY-001",
            "contracts": ["MH-C-PROVENANCE-REPLAY-001", "MH-C-SAT-REPLAY-001"],
            "implementation": Path("src/mathhead/kernel/provenance.py"),
            "fresh": True,
            "independent": True,
            "requires_fresh": True,
            "requires_independent": True,
            "status": "verified",
        },
        {
            "id": "transition.external.lean-provenance.preserve",
            "source": "external_proof_assistant",
            "target": "external_proof_assistant",
            "operation": "preserve",
            "component": "mathhead.proof-assistant.lean-provenance",
            "entry": "mathhead.proof_assistant.provenance.replay_lean_provenance",
            "role": "proof_assistant",
            "contract": "MH-C-LEAN-VERIFICATION-001",
            "contracts": ["MH-C-LEAN-VERIFICATION-001", "MH-C-PROVENANCE-REPLAY-001"],
            "implementation": Path("src/mathhead/proof_assistant/provenance.py"),
            "fresh": True,
            "independent": True,
            "requires_fresh": True,
            "requires_independent": True,
            "status": "verified",
        },
        {
            "id": "transition.none.approximate.issue",
            "source": "none",
            "target": "producer_report",
            "operation": "issue",
            "component": "mathhead.producer.approximate",
            "entry": "mathhead.producer.approximate.report",
            "role": "producer",
            "contract": "MH-C-TRUST-BASE-001",
            "contracts": ["MH-C-TRUST-BASE-001"],
            "surface": "arithmetic.approximate",
            "fresh": False,
            "independent": False,
            "requires_fresh": False,
            "requires_independent": False,
            "status": "completed",
        },
        {
            "id": "transition.none.nauty.issue",
            "source": "none",
            "target": "producer_report",
            "operation": "issue",
            "component": "mathhead.producer.nauty",
            "entry": "mathhead.producer.nauty.report",
            "role": "producer",
            "contract": "MH-C-TRUST-BASE-001",
            "contracts": ["MH-C-TRUST-BASE-001"],
            "surface": "process.external-nauty",
            "fresh": False,
            "independent": False,
            "requires_fresh": False,
            "requires_independent": False,
            "status": "completed",
        },
        {
            "id": "transition.none.proof-checker.issue",
            "source": "none",
            "target": "checker_attestation",
            "operation": "issue",
            "component": "mathhead.kernel.proof-checker",
            "entry": "mathhead.kernel.checkers.check_proof_term",
            "role": "checker",
            "contract": "MH-C-KERNEL-CHECKER-002",
            "contracts": ["MH-C-KERNEL-CHECKER-002", "MH-C-PROOF-TERM-001"],
            "implementation": Path("src/mathhead/kernel/checkers.py"),
            "fresh": True,
            "independent": True,
            "requires_fresh": False,
            "requires_independent": True,
            "status": "verified",
        },
        {
            "id": "transition.none.sat-checker.issue",
            "source": "none",
            "target": "checker_attestation",
            "operation": "issue",
            "component": "mathhead.kernel.sat-checker",
            "entry": "mathhead.kernel.sat.check_sat_certificate",
            "role": "checker",
            "contract": "MH-C-SAT-REPLAY-001",
            "contracts": ["MH-C-SAT-REPLAY-001"],
            "implementation": Path("src/mathhead/kernel/sat.py"),
            "fresh": True,
            "independent": True,
            "requires_fresh": False,
            "requires_independent": True,
            "status": "verified",
        },
        {
            "id": "transition.none.sympy.issue",
            "source": "none",
            "target": "producer_report",
            "operation": "issue",
            "component": "mathhead.producer.sympy",
            "entry": "mathhead.producer.sympy.report",
            "role": "producer",
            "contract": "MH-C-TRUST-BASE-001",
            "contracts": ["MH-C-TRUST-BASE-001"],
            "surface": "solver.sympy",
            "fresh": False,
            "independent": False,
            "requires_fresh": False,
            "requires_independent": False,
            "status": "completed",
        },
        {
            "id": "transition.none.z3.issue",
            "source": "none",
            "target": "producer_report",
            "operation": "issue",
            "component": "mathhead.producer.z3",
            "entry": "mathhead.producer.z3.report",
            "role": "producer",
            "contract": "MH-C-TRUST-BASE-001",
            "contracts": ["MH-C-TRUST-BASE-001"],
            "surface": "solver.z3",
            "fresh": False,
            "independent": False,
            "requires_fresh": False,
            "requires_independent": False,
            "status": "completed",
        },
        {
            "id": "transition.producer.sat-checker.issue",
            "source": "producer_report",
            "target": "checker_attestation",
            "operation": "issue",
            "component": "mathhead.kernel.sat-checker",
            "entry": "mathhead.kernel.sat.check_sat_certificate",
            "role": "checker",
            "contract": "MH-C-SAT-REPLAY-001",
            "contracts": ["MH-C-SAT-REPLAY-001"],
            "implementation": Path("src/mathhead/kernel/sat.py"),
            "fresh": True,
            "independent": True,
            "requires_fresh": False,
            "requires_independent": True,
            "status": "verified",
        },
    ]


def _surface_inventory() -> dict[str, dict[str, Any]]:
    value, _raw = _load_canonical(TRUST_INVENTORY_PATH)
    return {item["surface_id"]: item for item in value["surfaces"]}


def build_positive_control(
    blueprint: Mapping[str, Any],
    surfaces: Mapping[str, Mapping[str, Any]] | None = None,
) -> tuple[dict[str, Any], bytes, tuple[bytes, ...], dict[str, Any]]:
    """Build one exact policy attempt plus its transition catalogue record."""

    if surfaces is None:
        surfaces = _surface_inventory()
    transition_id = blueprint["id"]
    component_id = blueprint["component"]
    config = _configuration(component_id, transition_id)
    if "surface" in blueprint:
        implementation = _source_set(surfaces[blueprint["surface"]])
        implementation_media = "application/json"
        implementation_schema = "mathhead.trust-transition-source-set.v1"
        subject = _canonical(
            {
                "authority": "producer_report",
                "schema": "mathhead.producer-control.v1",
                "status": "completed",
                "surface_id": blueprint["surface"],
            }
        )
        subject_schema = "mathhead.producer-control.v1"
    else:
        implementation = (ROOT / blueprint["implementation"]).read_bytes()
        implementation_media = "text/x-python"
        implementation_schema = "mathhead.python-source.v1"
        if transition_id == "transition.none.proof-checker.issue":
            term = residue(2, (0, -1, 0, 1))
            subject = checker_result_to_bytes(check_proof_term(term))
            subject_schema = "mathhead.kernel-checker-result.v2"
        elif transition_id in {
            "transition.none.sat-checker.issue",
            "transition.producer.sat-checker.issue",
        }:
            cnf = canonical_cnf_bytes(((1,),))
            certificate = canonical_sat_assignment_bytes(cnf, (1,))
            subject = sat_replay_result_to_bytes(check_sat_certificate(cnf, certificate))
            subject_schema = "mathhead.sat-replay-result.v1"
        elif transition_id.startswith("transition.checker.provenance-"):
            checker_id = (
                "mathhead.kernel.checker.v2"
                if "proof" in transition_id
                else "mathhead.kernel.sat-replay.v1"
            )
            manifest, objects = build_provenance_control(checker_id)
            subject = provenance_replay_result_to_bytes(
                replay_provenance_bundle(manifest, objects)
            )
            subject_schema = "mathhead.provenance-replay-result.v1"
        else:
            term = residue(2, (0, -1, 0, 1))
            export = build_lean_export(term, check_proof_term(term))
            written = export_written_result(export)
            subject = lean_verification_result_to_bytes(written)
            subject_schema = "mathhead.lean-verification-result.v1"
    issuer = {
        "component_id": component_id,
        "configuration_sha256": _sha(config),
        "contract_id": blueprint["contract"],
        "contract_sha256": CONTRACTS[blueprint["contract"]],
        "entry_point": blueprint["entry"],
        "fresh": blueprint["fresh"],
        "implementation_sha256": _sha(implementation),
        "independent": blueprint["independent"],
        "role": blueprint["role"],
    }
    artifact_values: dict[str, tuple[bytes, str, str]] = {
        "issuer_configuration": (
            config,
            "application/json",
            "mathhead.trust-transition-issuer-configuration.v1",
        ),
        "issuer_implementation": (
            implementation,
            implementation_media,
            implementation_schema,
        ),
        "subject": (subject, "application/json", subject_schema),
    }
    for contract_id in blueprint["contracts"]:
        artifact_values[_contract_role(contract_id)] = (
            (ROOT / f"docs/contracts/{contract_id}.json").read_bytes(),
            "application/json",
            "mathhead.function-contract.v1",
        )
    bindings = [
        _artifact(role, data, media_type=media, schema=schema)
        for role, (data, media, schema) in sorted(artifact_values.items())
    ]
    subject_record = next(item for item in bindings if item["role"] == "subject")
    attempt = {
        "bindings": bindings,
        "budget_complete": True,
        "claimed_authority": blueprint["target"],
        "evidence_complete": True,
        "issuer": issuer,
        "operation": blueprint["operation"],
        "schema": "mathhead.trust-transition-attempt.v1",
        "source_tier": blueprint["source"],
        "status": blueprint["status"],
        "subject": subject_record,
        "target_tier": blueprint["target"],
        "transition_id": transition_id,
    }
    artifacts = tuple(artifact_values[item["role"]][0] for item in bindings)
    allowed_issuers = [trust_transition_issuer_key(issuer)]
    if blueprint["requires_fresh"]:
        stale = {**issuer, "fresh": False}
        allowed_issuers.append(trust_transition_issuer_key(stale))
    if blueprint["requires_independent"]:
        aliased = {**issuer, "independent": False}
        allowed_issuers.append(trust_transition_issuer_key(aliased))
    record = {
        "allowed_issuers": sorted(set(allowed_issuers)),
        "allowed_statuses": [blueprint["status"]],
        "mutation_ids": [],
        "on_failure_tier": "none",
        "operation": blueprint["operation"],
        "positive_control_ids": ["control." + transition_id.removeprefix("transition.")],
        "required_binding_roles": [item["role"] for item in bindings],
        "required_contracts": [
            _contract_ref(contract_id) for contract_id in sorted(blueprint["contracts"])
        ],
        "requires_fresh": blueprint["requires_fresh"],
        "requires_independent": blueprint["requires_independent"],
        "source_tier": blueprint["source"],
        "target_tier": blueprint["target"],
        "transition_id": transition_id,
    }
    return attempt, trust_transition_attempt_to_bytes(attempt), artifacts, record


def _mutation_specs() -> list[dict[str, str]]:
    """Return the finite normative attack catalogue."""

    rows = [
        ("artifact.byte-flip", "artifact", "transition.none.proof-checker.issue", "downgraded", "ARTIFACT_MISMATCH", "Flip supplied subject bytes without repairing the binding."),
        ("artifact.duplicate-payload", "artifact", "transition.none.z3.issue", "downgraded", "ARTIFACT_MISMATCH", "Duplicate one supplied payload in the exact artifact tuple."),
        ("artifact.extra", "artifact", "transition.none.approximate.issue", "downgraded", "ARTIFACT_MISMATCH", "Append an undeclared artifact to the exact inventory."),
        ("artifact.hash-reference", "artifact", "transition.none.sympy.issue", "downgraded", "ARTIFACT_MISMATCH", "Alter a binding digest while retaining the original bytes."),
        ("artifact.length-reference", "artifact", "transition.none.nauty.issue", "downgraded", "ARTIFACT_MISMATCH", "Alter a binding length while retaining the original bytes."),
        ("artifact.omit", "artifact", "transition.none.sat-checker.issue", "downgraded", "ARTIFACT_MISMATCH", "Omit one exact bound artifact."),
        ("authority.claim", "authority", "transition.external.lean-provenance.preserve", "downgraded", "TIER_CLAIM_MISMATCH", "Claim a tier different from the catalogued target."),
        ("authority.operation", "authority", "transition.none.sympy.issue", "downgraded", "TRANSITION_FORBIDDEN", "Relabel issue as preservation."),
        ("authority.source-tier", "authority", "transition.none.approximate.issue", "downgraded", "TRANSITION_FORBIDDEN", "Substitute the source authority tier."),
        ("authority.target-tier", "authority", "transition.none.nauty.issue", "downgraded", "TRANSITION_FORBIDDEN", "Substitute the target authority tier."),
        ("budget.incomplete", "budget", "transition.none.sat-checker.issue", "downgraded", "BUDGET_INCOMPLETE", "Mark resource accounting incomplete."),
        ("canonical.catalogue-whitespace", "canonical", "transition.checker.provenance-sat.preserve", "rejected", "CATALOGUE_INVALID", "Add noncanonical whitespace to catalogue bytes."),
        ("canonical.unknown-field", "canonical", "transition.checker.lean.issue", "rejected", "MALFORMED_ATTEMPT", "Add an unknown attempt field."),
        ("canonical.whitespace", "canonical", "transition.checker.provenance-sat.preserve", "rejected", "MALFORMED_ATTEMPT", "Render the attempt with noncanonical whitespace."),
        ("freshness.stale", "freshness", "transition.checker.lean.issue", "downgraded", "FRESHNESS_REQUIRED", "Replay an allowlisted issuer identity without freshness."),
        ("identity.component", "identity", "transition.none.proof-checker.issue", "downgraded", "ISSUER_FORBIDDEN", "Substitute the issuer component identity."),
        ("identity.configuration", "identity", "transition.checker.provenance-sat.preserve", "downgraded", "ISSUER_FORBIDDEN", "Substitute the issuer configuration identity."),
        ("identity.contract", "identity", "transition.checker.lean.issue", "downgraded", "ISSUER_FORBIDDEN", "Substitute the accepted issuer contract identity."),
        ("identity.entry-point", "identity", "transition.none.sat-checker.issue", "downgraded", "ISSUER_FORBIDDEN", "Substitute the issuer entry point."),
        ("identity.implementation", "identity", "transition.checker.provenance-proof.preserve", "downgraded", "ISSUER_FORBIDDEN", "Substitute the issuer implementation identity."),
        ("independence.aliased", "independence", "transition.none.proof-checker.issue", "downgraded", "INDEPENDENCE_REQUIRED", "Alias an allowlisted checker identity to its producer."),
        ("provenance.missing-contract", "provenance", "transition.external.lean-provenance.preserve", "downgraded", "ARTIFACT_MISMATCH", "Remove one required accepted-contract artifact."),
        ("status.disagreement", "status", "transition.none.z3.issue", "downgraded", "STATUS_FORBIDDEN", "Force explicit backend disagreement instead of completion."),
        ("status.invalid", "status", "transition.none.proof-checker.issue", "downgraded", "STATUS_FORBIDDEN", "Relabel the checker outcome invalid."),
        ("structure.unknown-transition", "structure", "transition.checker.provenance-proof.preserve", "rejected", "TRANSITION_UNKNOWN", "Request a schema-valid transition absent from the catalogue."),
        ("semantic.lean-request-substitution", "semantic", "transition.checker.lean.issue", "rejected", "REQUEST_INVALID", "Repair JSON form after substituting the Lean theorem request."),
        ("semantic.lean-stored-result", "semantic", "transition.external.lean-provenance.preserve", "rejected", "EXPORT_WRITTEN", "Treat a stored written export as fresh external authority."),
        ("semantic.proof-counterexample", "semantic", "transition.none.proof-checker.issue", "rejected", "RESIDUE_COUNTEREXAMPLE", "Replace the proof subject with a false residue claim."),
        ("semantic.proof-forged-object", "semantic", "transition.none.proof-checker.issue", "rejected", "TERM_INVALID", "Forge hidden proof-term state through object allocation."),
        ("semantic.sat-certificate-truncation", "semantic", "transition.producer.sat-checker.issue", "rejected", "CLAIM_REFUTED", "Truncate the RUP certificate while keeping canonical framing."),
        ("semantic.sat-false-assignment", "semantic", "transition.none.sat-checker.issue", "rejected", "CLAIM_REFUTED", "Substitute a complete but false SAT assignment."),
        ("semantic.sat-trailing-data", "semantic", "transition.producer.sat-checker.issue", "rejected", "CERTIFICATE_INVALID", "Append trailing data to a SAT certificate."),
        ("provenance.corrupted-object", "provenance", "transition.checker.provenance-proof.preserve", "rejected", "OBJECT_MISMATCH", "Corrupt one stored object without repairing its manifest."),
        ("provenance.repaired-implementation", "provenance", "transition.checker.provenance-sat.preserve", "rejected", "CHECKER_IDENTITY_MISMATCH", "Swap checker source and repair every outer digest reference."),
    ]
    effect_transition = {
        "arithmetic.approximate": "transition.none.approximate.issue",
        "process.external-nauty": "transition.none.nauty.issue",
        "solver.sympy": "transition.none.sympy.issue",
        "solver.z3": "transition.none.z3.issue",
    }
    for surface_id in EFFECT_SURFACES:
        transition_id = effect_transition.get(
            surface_id, "transition.none.proof-checker.issue"
        )
        rows.append(
            (
                "effect." + surface_id,
                "effect",
                transition_id,
                "rejected",
                "EFFECT_AUTHORITY_FORBIDDEN",
                f"Attempt to promote the {surface_id} effect surface into authority.",
            )
        )
    return [
        {
            "description": description,
            "expected_decision": decision,
            "expected_reason": reason,
            "expected_tier": "none",
            "mutation_class": mutation_class,
            "mutation_id": mutation_id,
            "transition_ids": [transition_id],
        }
        for mutation_id, mutation_class, transition_id, decision, reason, description in rows
    ]


def build_catalogue() -> tuple[bytes, dict[str, tuple[dict[str, Any], bytes, tuple[bytes, ...]]]]:
    surfaces = _surface_inventory()
    controls: dict[str, tuple[dict[str, Any], bytes, tuple[bytes, ...]]] = {}
    transitions = []
    for blueprint in sorted(_transition_blueprints(), key=lambda item: item["id"]):
        attempt, attempt_bytes, artifacts, record = build_positive_control(
            blueprint, surfaces
        )
        controls[blueprint["id"]] = (attempt, attempt_bytes, artifacts)
        transitions.append(record)
    mutations = sorted(_mutation_specs(), key=lambda item: item["mutation_id"])
    by_transition: dict[str, list[str]] = {item["transition_id"]: [] for item in transitions}
    for mutation in mutations:
        for transition_id in mutation["transition_ids"]:
            by_transition[transition_id].append(mutation["mutation_id"])
    for transition in transitions:
        transition["mutation_ids"] = sorted(by_transition[transition["transition_id"]])
        if not transition["mutation_ids"]:
            _fail(f"{transition['transition_id']}: has no normative mutation")
    effects = []
    for surface_id in EFFECT_SURFACES:
        maximum = (
            "producer_report"
            if surface_id in {
                "arithmetic.approximate",
                "process.external-nauty",
                "solver.sympy",
                "solver.z3",
            }
            else "none"
        )
        role = "producer" if maximum == "producer_report" else (
            "transport" if surface_id.startswith("transport.") else "effect_boundary"
        )
        effects.append(
            {
                "authority_issuer": False,
                "maximum_tier": maximum,
                "mutation_ids": ["effect." + surface_id],
                "role": role,
                "surface_id": surface_id,
            }
        )
    catalogue = {
        "contract": _contract_ref(CONTRACT_ID),
        "effects": effects,
        "mutations": mutations,
        "schema": "mathhead.trust-transition-catalogue.v1",
        "tiers": [
            "none",
            "producer_report",
            "solver_verdict",
            "checker_attestation",
            "external_proof_assistant",
        ],
        "transitions": transitions,
    }
    raw = _canonical(catalogue)
    if _sha(raw) != CATALOGUE_SHA256:
        _fail("normative catalogue hash differs from the production binding")
    validate_trust_transition_catalogue(raw)
    return raw, controls


def _replace_bound_artifact(
    attempt: dict[str, Any],
    artifacts: tuple[bytes, ...],
    role: str,
    replacement: bytes,
) -> tuple[dict[str, Any], tuple[bytes, ...]]:
    changed = copy.deepcopy(attempt)
    index = next(
        index for index, item in enumerate(changed["bindings"]) if item["role"] == role
    )
    changed["bindings"][index]["bytes"] = len(replacement)
    changed["bindings"][index]["sha256"] = _sha(replacement)
    if changed["subject"]["role"] == role:
        changed["subject"] = changed["bindings"][index]
    values = list(artifacts)
    values[index] = replacement
    return changed, tuple(values)


def _mutate_policy(
    mutation_id: str,
    attempt: dict[str, Any],
    attempt_bytes: bytes,
    artifacts: tuple[bytes, ...],
    catalogue: bytes,
) -> tuple[bytes, tuple[bytes, ...], bytes]:
    value = copy.deepcopy(attempt)
    changed_artifacts = artifacts
    changed_catalogue = catalogue
    if mutation_id == "artifact.byte-flip":
        values = list(artifacts)
        values[-1] = values[-1][:-1] + bytes([values[-1][-1] ^ 1])
        changed_artifacts = tuple(values)
    elif mutation_id == "artifact.duplicate-payload":
        changed_artifacts = (*artifacts, artifacts[0])
    elif mutation_id == "artifact.extra":
        changed_artifacts = (*artifacts, b"undeclared")
    elif mutation_id == "artifact.hash-reference":
        value["bindings"][0]["sha256"] = ZERO_SHA256
    elif mutation_id == "artifact.length-reference":
        value["bindings"][0]["bytes"] += 1
    elif mutation_id == "artifact.omit":
        changed_artifacts = artifacts[:-1]
    elif mutation_id == "authority.claim":
        value["claimed_authority"] = "checker_attestation"
    elif mutation_id == "authority.operation":
        value["operation"] = "preserve"
    elif mutation_id == "authority.source-tier":
        value["source_tier"] = "producer_report"
    elif mutation_id == "authority.target-tier":
        value["target_tier"] = "checker_attestation"
    elif mutation_id == "budget.incomplete":
        value["budget_complete"] = False
    elif mutation_id == "canonical.catalogue-whitespace":
        changed_catalogue = b" " + catalogue
    elif mutation_id == "canonical.unknown-field":
        value["unknown"] = None
    elif mutation_id == "freshness.stale":
        value["issuer"]["fresh"] = False
    elif mutation_id == "identity.component":
        value["issuer"]["component_id"] = "mathhead.attacker"
    elif mutation_id == "identity.configuration":
        value["issuer"]["configuration_sha256"] = ZERO_SHA256
    elif mutation_id == "identity.contract":
        value["issuer"]["contract_id"] = "MH-C-TRUST-BASE-001"
        value["issuer"]["contract_sha256"] = CONTRACTS["MH-C-TRUST-BASE-001"]
    elif mutation_id == "identity.entry-point":
        value["issuer"]["entry_point"] = "mathhead.attacker.issue"
    elif mutation_id == "identity.implementation":
        value["issuer"]["implementation_sha256"] = ZERO_SHA256
    elif mutation_id == "independence.aliased":
        value["issuer"]["independent"] = False
    elif mutation_id == "provenance.missing-contract":
        index = next(
            index
            for index, item in enumerate(value["bindings"])
            if item["role"].startswith("contract_")
        )
        del value["bindings"][index]
        changed_artifacts = artifacts[:index] + artifacts[index + 1 :]
    elif mutation_id == "status.disagreement":
        value["status"] = "disagreement"
    elif mutation_id == "status.invalid":
        value["status"] = "invalid"
    elif mutation_id == "structure.unknown-transition":
        value["transition_id"] = "transition.unknown.attack"
    if mutation_id == "canonical.whitespace":
        return b" " + attempt_bytes, changed_artifacts, changed_catalogue
    if mutation_id == "canonical.unknown-field":
        return _canonical(value), changed_artifacts, changed_catalogue
    return trust_transition_attempt_to_bytes(value), changed_artifacts, changed_catalogue


def _policy_mutation_result(
    mutation: Mapping[str, Any],
    controls: Mapping[str, tuple[dict[str, Any], bytes, tuple[bytes, ...]]],
    catalogue: bytes,
) -> tuple[str, str, str, bytes]:
    transition_id = mutation["transition_ids"][0]
    attempt, attempt_bytes, artifacts = controls[transition_id]
    mutated_attempt, mutated_artifacts, mutated_catalogue = _mutate_policy(
        mutation["mutation_id"], attempt, attempt_bytes, artifacts, catalogue
    )
    result = audit_trust_transition(mutated_attempt, mutated_artifacts, mutated_catalogue)
    return result.decision, result.effective_tier, result.reason, transition_audit_result_to_bytes(result)


def _replace_provenance_object(
    manifest: bytes,
    objects: tuple[bytes, ...],
    role: str,
    replacement: bytes,
) -> tuple[bytes, tuple[bytes, ...]]:
    value = json.loads(manifest)
    index = next(
        index for index, record in enumerate(value["objects"]) if record["role"] == role
    )
    previous = value["objects"][index]["sha256"]
    current = _sha(replacement)
    value["objects"][index]["sha256"] = current
    value["objects"][index]["byte_count"] = len(replacement)
    for record in value["objects"]:
        record["depends_on_sha256"] = sorted(
            current if dependency == previous else dependency
            for dependency in record["depends_on_sha256"]
        )
    replay_field = {
        "checker_configuration": "checker_configuration_sha256",
        "checker_contract": "checker_contract_sha256",
        "checker_implementation": "checker_implementation_sha256",
        "checker_result": "recorded_result_sha256",
    }.get(role)
    if replay_field is not None:
        value["replay"][replay_field] = current
    changed = list(objects)
    changed[index] = replacement
    return _canonical(value), tuple(changed)


def _semantic_mutation_result(mutation_id: str) -> tuple[str, str, str, bytes]:
    authority = "none"
    if mutation_id == "semantic.proof-counterexample":
        result = check_proof_term(residue(4, (1, 0, 1)))
        reason, authority = result.reason_code, result.authority
        raw = checker_result_to_bytes(result)
    elif mutation_id == "semantic.proof-forged-object":
        term = object.__new__(type(residue(2, (0,))))
        object.__setattr__(term, "modulus", True)
        object.__setattr__(term, "polynomial", (0,))
        result = check_proof_term(term)
        reason, authority = result.reason_code, result.authority
        raw = checker_result_to_bytes(result)
    elif mutation_id == "semantic.sat-false-assignment":
        cnf = canonical_cnf_bytes(((1,),))
        result = check_sat_certificate(cnf, canonical_sat_assignment_bytes(cnf, (-1,)))
        reason, authority = result.reason_code, result.authority
        raw = sat_replay_result_to_bytes(result)
    elif mutation_id == "semantic.sat-certificate-truncation":
        cnf = canonical_cnf_bytes(((1, 2), (1, -2), (-1, 2), (-1, -2)))
        result = check_sat_certificate(cnf, canonical_drup_bytes(cnf, ()))
        reason, authority = result.reason_code, result.authority
        raw = sat_replay_result_to_bytes(result)
    elif mutation_id == "semantic.sat-trailing-data":
        cnf = canonical_cnf_bytes(((1,),))
        certificate = canonical_sat_assignment_bytes(cnf, (1,)) + b"c trailing\n"
        result = check_sat_certificate(cnf, certificate)
        reason, authority = result.reason_code, result.authority
        raw = sat_replay_result_to_bytes(result)
    elif mutation_id == "provenance.corrupted-object":
        manifest, objects = build_provenance_control()
        changed = list(objects)
        changed[0] = changed[0][:-1] + bytes([changed[0][-1] ^ 1])
        result = replay_provenance_bundle(manifest, tuple(changed))
        reason, authority = result.reason_code, result.authority
        raw = provenance_replay_result_to_bytes(result)
    elif mutation_id == "provenance.repaired-implementation":
        manifest, objects = build_provenance_control("mathhead.kernel.sat-replay.v1")
        changed_manifest, changed_objects = _replace_provenance_object(
            manifest, objects, "checker_implementation", b"# attacker checker\n"
        )
        result = replay_provenance_bundle(changed_manifest, changed_objects)
        reason, authority = result.reason_code, result.authority
        raw = provenance_replay_result_to_bytes(result)
    elif mutation_id == "semantic.lean-stored-result":
        term = residue(2, (0, -1, 0, 1))
        export = build_lean_export(term, check_proof_term(term))
        result = export_written_result(export)
        reason, authority = result.reason_code, result.authority
        raw = lean_verification_result_to_bytes(result)
    elif mutation_id == "semantic.lean-request-substitution":
        term = residue(2, (0, -1, 0, 1))
        export = build_lean_export(term, check_proof_term(term))
        request = json.loads(export.request)
        request["theorem_name"] = "MathHead.Generated.attacker"
        result = verify_with_lean(_canonical(request), export.artifacts, str(ROOT))
        reason, authority = result.reason_code, result.authority
        raw = lean_verification_result_to_bytes(result)
    else:
        raise AssertionError(mutation_id)
    if authority != "none":
        _fail(f"{mutation_id}: semantic attack retained {authority}")
    return "rejected", "none", reason, raw


def _authority_literals() -> dict[str, dict[str, int]]:
    actual: dict[str, dict[str, int]] = {}
    for path in sorted((ROOT / "src/mathhead").rglob("*.py")):
        relative = path.relative_to(ROOT).as_posix()
        tree = ast.parse(path.read_bytes(), filename=relative)
        counts: dict[str, int] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and node.value in {
                "producer_report",
                "solver_verdict",
                *STRONG_TIERS,
            }:
                counts[node.value] = counts.get(node.value, 0) + 1
        if counts:
            actual[relative] = counts
    return actual


def _issuer_site_report() -> list[dict[str, object]]:
    if _authority_literals() != AUTHORITY_LITERAL_COUNTS:
        _fail("static authority-tier literal inventory drift")
    report = []
    for entry_point, relative, symbol, tier in ISSUER_SITES:
        tree = ast.parse((ROOT / relative).read_bytes(), filename=relative.as_posix())
        matches = [
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == symbol
        ]
        if len(matches) != 1:
            _fail(f"{relative}:{symbol}: issuer entry point missing or duplicated")
        report.append(
            {
                "entry_point": entry_point,
                "line": matches[0].lineno,
                "path": relative.as_posix(),
                "tier": tier,
            }
        )
    return sorted(report, key=lambda item: item["entry_point"])


def _effect_results(catalogue: Mapping[str, Any]) -> list[dict[str, object]]:
    inventory = _surface_inventory()
    catalogue_effects = {item["surface_id"]: item for item in catalogue["effects"]}
    if set(catalogue_effects) != set(EFFECT_SURFACES):
        _fail("effect catalogue does not exactly match the MH-037 surface set")
    results = []
    for surface_id in EFFECT_SURFACES:
        surface = inventory[surface_id]
        expected_maximum = surface["target_authority"]
        if surface_id == "arithmetic.approximate":
            expected_maximum = "producer_report"
        if expected_maximum == "solver_verdict":
            expected_maximum = "producer_report"
        record = catalogue_effects[surface_id]
        violations = []
        if record["authority_issuer"] is not False:
            violations.append("EFFECT_MARKED_ISSUER")
        if record["maximum_tier"] != expected_maximum:
            violations.append("EFFECT_MAXIMUM_DRIFT")
        authority_sites = 0
        for relative in surface["source_paths"]:
            tree = ast.parse((ROOT / relative).read_bytes(), filename=relative)
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and node.value in STRONG_TIERS:
                    authority_sites += 1
                if isinstance(node, ast.Call):
                    name = None
                    if isinstance(node.func, ast.Name):
                        name = node.func.id
                    elif isinstance(node.func, ast.Attribute):
                        name = node.func.attr
                    classified = (surface_id, relative, name)
                    if (
                        name in FORBIDDEN_EFFECT_CALLS
                        and classified not in CLASSIFIED_EFFECT_ADAPTER_CALLS
                    ):
                        authority_sites += 1
        if authority_sites:
            violations.append("EFFECT_AUTHORITY_ROUTE")
        results.append(
            {
                "authority_sites": authority_sites,
                "surface_id": surface_id,
                "violations": sorted(set(violations)),
            }
        )
    return results


def _effect_mutation_result(
    mutation_id: str, surface_results: Sequence[Mapping[str, Any]]
) -> tuple[str, str, str, bytes]:
    surface_id = mutation_id.removeprefix("effect.")
    result = next(item for item in surface_results if item["surface_id"] == surface_id)
    killed = result["authority_sites"] == 0 and not result["violations"]
    raw = _canonical(
        {
            "attack": "effect-to-authority",
            "killed": killed,
            "schema": "mathhead.trust-transition-effect-probe.v1",
            "surface_id": surface_id,
        }
    )
    return (
        "rejected" if killed else "downgraded",
        "none",
        "EFFECT_AUTHORITY_FORBIDDEN" if killed else "EFFECT_AUTHORITY_ROUTE",
        raw,
    )


def _source_snapshot() -> str:
    paths = [
        *sorted(Path("src/mathhead").glob("**/*.py")),
        Path("tools/validate_trust_transitions.py"),
        CONTRACT_PATH,
        *SCHEMA_PATHS,
        TRUST_INVENTORY_PATH,
    ]
    test_root = ROOT / "tests/trust_transitions"
    if test_root.is_dir():
        paths.extend(
            path.relative_to(ROOT) for path in sorted(test_root.glob("**/*.py"))
        )
    framed = bytearray()
    for relative in sorted(set(paths), key=lambda item: item.as_posix()):
        data = (ROOT / relative).read_bytes()
        name = relative.as_posix().encode("utf-8")
        framed.extend(len(name).to_bytes(4, "big"))
        framed.extend(name)
        framed.extend(len(data).to_bytes(8, "big"))
        framed.extend(data)
    return _sha(bytes(framed))


def _validate_schemas() -> None:
    for path, expected in SCHEMA_SHA256.items():
        value, raw = _load_json(path)
        if _sha(raw) != expected:
            _fail(f"{path}: accepted schema hash drift")
        if value.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
            _fail(f"{path}: Draft 2020-12 identity drift")
        if Draft202012Validator is not None:
            try:
                Draft202012Validator.check_schema(value)
            except SchemaError as exc:
                _fail(f"{path}: schema meta-validation failed: {exc}")
    if _sha((ROOT / CONTRACT_PATH).read_bytes()) != CONTRACT_SHA256:
        _fail("accepted trust-transition contract hash drift")


def _validate_report_schema(report: dict[str, Any]) -> None:
    schema, _raw = _load_json(SCHEMA_PATHS[3])
    if Draft202012Validator is not None:
        try:
            Draft202012Validator(schema).validate(report)
        except ValidationError as exc:
            _fail(f"G3 report schema validation failed: {exc.message}")
    required = set(schema["required"])
    if set(report) != required:
        _fail("G3 report root fields differ from the closed schema")


def build_report(catalogue_raw: bytes) -> bytes:
    catalogue = json.loads(catalogue_raw)
    generated_catalogue, controls = build_catalogue()
    if generated_catalogue != catalogue_raw:
        _fail("catalogue bytes are stale")
    transition_results = []
    for transition_id in sorted(controls):
        _attempt, attempt_raw, artifacts = controls[transition_id]
        result = audit_trust_transition(attempt_raw, artifacts, catalogue_raw)
        result_raw = transition_audit_result_to_bytes(result)
        if (
            result.decision != "allowed"
            or result.mathematical_authority is not False
            or result.transition_id != transition_id
        ):
            _fail(f"{transition_id}: positive control did not pass closed policy")
        transition_results.append(
            {
                "attempt_sha256": _sha(attempt_raw),
                "decision": result.decision,
                "effective_tier": result.effective_tier,
                "result_sha256": _sha(result_raw),
                "transition_id": transition_id,
            }
        )
    surface_results = _effect_results(catalogue)
    semantic_ids = {
        "provenance.corrupted-object",
        "provenance.repaired-implementation",
        "semantic.lean-request-substitution",
        "semantic.lean-stored-result",
        "semantic.proof-counterexample",
        "semantic.proof-forged-object",
        "semantic.sat-certificate-truncation",
        "semantic.sat-false-assignment",
        "semantic.sat-trailing-data",
    }
    mutation_results = []
    for mutation in catalogue["mutations"]:
        mutation_id = mutation["mutation_id"]
        if mutation_id.startswith("effect."):
            decision, tier, reason, raw = _effect_mutation_result(
                mutation_id, surface_results
            )
        elif mutation_id in semantic_ids:
            decision, tier, reason, raw = _semantic_mutation_result(mutation_id)
        else:
            decision, tier, reason, raw = _policy_mutation_result(
                mutation, controls, catalogue_raw
            )
        killed = (
            decision == mutation["expected_decision"]
            and tier == mutation["expected_tier"]
            and reason == mutation["expected_reason"]
        )
        mutation_results.append(
            {
                "decision": decision,
                "effective_tier": tier,
                "mutation_id": mutation_id,
                "outcome": "killed" if killed else "survived",
                "reason": reason,
                "result_sha256": _sha(raw),
                "transition_id": mutation["transition_ids"][0],
            }
        )
    issuer_sites = _issuer_site_report()
    survived = sum(item["outcome"] == "survived" for item in mutation_results)
    violations = sum(bool(item["violations"]) for item in surface_results)
    report = {
        "catalogue_sha256": _sha(catalogue_raw),
        "contract_id": CONTRACT_ID,
        "contract_sha256": CONTRACT_SHA256,
        "g3_passed": survived == 0 and violations == 0,
        "generated_by": {
            "path": "tools/validate_trust_transitions.py",
            "sha256": _sha((ROOT / "tools/validate_trust_transitions.py").read_bytes()),
        },
        "issuer_sites": issuer_sites,
        "mutation_results": mutation_results,
        "schema": REPORT_SCHEMA,
        "source_snapshot_sha256": _source_snapshot(),
        "surface_results": surface_results,
        "totals": {
            "issuer_sites": len(issuer_sites),
            "mutants": len(mutation_results),
            "mutants_killed": len(mutation_results) - survived,
            "mutants_survived": survived,
            "positive_controls": len(transition_results),
            "surfaces": len(surface_results),
            "transitions": len(catalogue["transitions"]),
        },
        "transition_results": transition_results,
    }
    _validate_report_schema(report)
    if not report["g3_passed"]:
        survivors = [
            item["mutation_id"] for item in mutation_results if item["outcome"] == "survived"
        ]
        _fail(f"G3 failed: survivors={survivors}, surface_violations={violations}")
    return _canonical(report)


def validate_repository(
    *,
    write_catalogue: Path | None = None,
    write_report: Path | None = None,
) -> dict[str, int]:
    _validate_schemas()
    expected_catalogue, _controls = build_catalogue()
    catalogue_target = ROOT / CATALOGUE_PATH
    if write_catalogue is not None:
        catalogue_target = _safe_output_path(write_catalogue)
        _write_atomic(catalogue_target, expected_catalogue)
    elif not catalogue_target.is_file() or catalogue_target.read_bytes() != expected_catalogue:
        _fail(f"{CATALOGUE_PATH}: deterministic catalogue drift")
    expected_report = build_report(expected_catalogue)
    report_target = ROOT / REPORT_PATH
    if write_report is not None:
        report_target = _safe_output_path(write_report)
        _write_atomic(report_target, expected_report)
    elif not report_target.is_file() or report_target.read_bytes() != expected_report:
        _fail(f"{REPORT_PATH}: deterministic report drift")
    report = json.loads(expected_report)
    return report["totals"]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-catalogue", type=Path)
    parser.add_argument("--write-report", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        totals = validate_repository(
            write_catalogue=args.write_catalogue,
            write_report=args.write_report,
        )
    except (OSError, TrustTransitionReportError, ValueError) as exc:
        print(f"trust-transitions: FAIL: {exc}", file=sys.stderr)
        return 1
    print(
        "trust-transitions: PASS "
        f"(transitions={totals['transitions']}, controls={totals['positive_controls']}, "
        f"mutants={totals['mutants']}, killed={totals['mutants_killed']}, "
        f"surfaces={totals['surfaces']}, issuers={totals['issuer_sites']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
