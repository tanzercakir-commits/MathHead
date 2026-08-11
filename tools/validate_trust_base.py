#!/usr/bin/env python3
"""Validate and report the MH-030 trusted-computing-base inventory."""

from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any, NoReturn, Sequence
import unicodedata

try:
    from jsonschema import Draft202012Validator
    from jsonschema.exceptions import SchemaError, ValidationError
except ImportError:  # Dependency-minimal status profile.
    Draft202012Validator = None  # type: ignore[assignment,misc]
    SchemaError = ValidationError = Exception  # type: ignore[assignment,misc]


ROOT = Path(__file__).resolve().parents[1]
INVENTORY_PATH = Path("docs/trust/trust-base-v1.json")
SCHEMA_PATH = Path("docs/trust/trust-base-v1.schema.json")
REPORT_PATH = Path("docs/trust/reports/trust-base-v1.json")
FOUNDATION_PATH = Path("docs/fixtures/foundation-v1/manifest.json")
CONFORMANCE_PATH = Path("docs/contracts/reports/foundation-conformance-v1.json")
TRUST_BASE_CONTRACT_PATH = Path("docs/contracts/MH-C-TRUST-BASE-001.json")
TRUST_BASE_CONTRACT_ID = "MH-C-TRUST-BASE-001"
TRUST_BASE_CONTRACT_SHA256 = "2d2c23da4d3b167c5220c7548602f11403af7634031c438a8f61ac8e3e191456"
TRUST_BASE_SCHEMA_SHA256 = "99c3024ffc5f2de636d2a61ed9c01a9396aa51c1f54b09fe14e6dde7d6816f3d"
FOUNDATION_BUNDLE_SHA256 = "4132b29b69600f8ff48477515853f66bb748c7337735c00db8e634987f70ddca"
ZERO_SHA256 = "0" * 64
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
ID_RE = re.compile(r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$")
TARGET_RE = re.compile(
    r"^(?P<module>[a-z_][a-z0-9_]*(?:\.[a-z_][a-z0-9_]*)*):"
    r"(?P<symbol>[A-Za-z_][A-Za-z0-9_]*)$"
)
TASK_RE = re.compile(r"^MH-[0-9]{3}$")
ROOT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
INVENTORY_FIELDS = {
    "schema",
    "contract",
    "foundation",
    "scope",
    "authority_tiers",
    "roles",
    "entry_points",
    "import_roots",
    "surfaces",
    "kernel_target",
    "migration_order",
    "inventory_sha256",
}
AUTHORITY_ORDER = (
    "none",
    "producer_report",
    "solver_verdict",
    "checker_attestation",
    "external_proof_assistant",
)
THIRD_PARTY_ROOTS = {"mcp", "mpmath", "pysat", "sympy", "z3"}
EFFECT_ROOTS = {
    "importlib",
    "mcp",
    "multiprocessing",
    "os",
    "pathlib",
    "random",
    "shutil",
    "subprocess",
    "sys",
    "threading",
    "time",
}
KERNEL_DENY_REQUIRED = {
    "importlib",
    "mcp",
    "mpmath",
    "multiprocessing",
    "os",
    "pathlib",
    "pysat",
    "random",
    "shutil",
    "subprocess",
    "sympy",
    "sys",
    "time",
    "z3",
}
FUTURE_STDLIB_ROOTS = {"enum", "unicodedata"}
NON_AUTHORITY_ROLES = {
    "approximate_arithmetic",
    "canonicalizer",
    "effect_boundary",
    "exact_arithmetic",
    "identity_primitive",
    "orchestrator",
    "parser",
    "runtime",
    "transport",
}
REPORT_CHECKS = (
    "canonical-inventory",
    "closed-schema",
    "contract-and-foundation-bindings",
    "complete-source-graph",
    "exact-import-root-inventory",
    "entry-point-closures",
    "dynamic-and-effect-boundaries",
    "surface-reference-closure",
    "authority-separation",
    "migration-closure",
    "minimal-kernel-target",
    "stable-report-identity",
)


@dataclass(frozen=True)
class TrustBaseValidationError(RuntimeError):
    """A classified fail-closed trust-base validation error."""

    kind: str
    path: str
    detail: str

    def __str__(self) -> str:
        return f"{self.path}: {self.detail}"


def _fail(kind: str, path: str, detail: str) -> NoReturn:
    raise TrustBaseValidationError(kind, path, detail)


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical_bytes(value: Any) -> bytes:
    try:
        rendered = json.dumps(
            value,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        _fail("schema", "$", f"value is not canonical JSON: {exc}")
    return (rendered + "\n").encode("utf-8")


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            _fail("schema", "$", f"duplicate JSON key: {key}")
        value[key] = item
    return value


def _load_json(
    path: Path, *, canonical: bool, max_bytes: int = 4_194_304
) -> tuple[dict[str, Any], bytes]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        _fail("path", str(path), f"cannot read JSON: {exc}")
    if len(raw) > max_bytes:
        _fail("budget", str(path), f"JSON exceeds {max_bytes} bytes")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs)
    except TrustBaseValidationError:
        raise
    except (UnicodeError, json.JSONDecodeError) as exc:
        _fail("schema", str(path), f"invalid JSON: {exc}")
    if not isinstance(value, dict):
        _fail("schema", str(path), "JSON root must be an object")
    if canonical and raw != canonical_bytes(value):
        _fail("schema", str(path), "JSON bytes are not canonical")
    return value, raw


def _safe_path(root: Path, relative: str) -> Path:
    candidate = Path(relative)
    if candidate.is_absolute() or not candidate.parts or ".." in candidate.parts:
        _fail("path", relative, "path must be safe and repository-relative")
    current = root.resolve()
    for part in candidate.parts:
        try:
            names = {entry.name for entry in current.iterdir()}
        except OSError as exc:
            _fail("path", relative, f"cannot inspect path: {exc}")
        if part not in names:
            aliases = sorted(name for name in names if name.casefold() == part.casefold())
            suffix = f"; found {aliases[0]}" if aliases else ""
            _fail("path", relative, f"exact path is missing{suffix}")
        current /= part
    try:
        current.resolve().relative_to(root.resolve())
    except ValueError:
        _fail("path", relative, "path resolves outside repository")
    if not current.is_file():
        _fail("path", relative, "path is not a regular file")
    return current


def _fields(value: Any, expected: set[str], path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail("schema", path, "must be an object")
    if set(value) != expected:
        _fail(
            "schema",
            path,
            f"fields differ: missing={sorted(expected - set(value))}, "
            f"unknown={sorted(set(value) - expected)}",
        )
    return value


def _string(value: Any, path: str, *, pattern: re.Pattern[str] | None = None) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        _fail("schema", path, "must be a nonempty trimmed string")
    if unicodedata.normalize("NFC", value) != value or "\x00" in value:
        _fail("schema", path, "must be NFC and contain no NUL")
    if pattern is not None and pattern.fullmatch(value) is None:
        _fail("schema", path, f"invalid value: {value!r}")
    return value


def _strings(value: Any, path: str, *, allow_empty: bool = True) -> list[str]:
    if not isinstance(value, list) or (not allow_empty and not value):
        _fail("schema", path, "must be a list" + ("" if allow_empty else " with entries"))
    result = [_string(item, f"{path}[{index}]") for index, item in enumerate(value)]
    if result != sorted(set(result)):
        _fail("schema", path, "must be lexically sorted and unique")
    return result


def _id(value: Any, path: str) -> str:
    return _string(value, path, pattern=ID_RE)


def _hash(value: Any, path: str) -> str:
    return _string(value, path, pattern=SHA256_RE)


def _json_budget(
    value: Any, path: str = "$", *, depth: int = 0, seen: list[int] | None = None
) -> None:
    if seen is None:
        seen = [0]
    seen[0] += 1
    if seen[0] > 200_000 or depth > 128:
        _fail("budget", path, "canonical JSON node or depth budget exceeded")
    if isinstance(value, float):
        _fail("schema", path, "floats are forbidden")
    if isinstance(value, str):
        _string(value, path)
    elif isinstance(value, dict):
        for key, item in value.items():
            _string(key, f"{path}.<key>")
            _json_budget(item, f"{path}.{key}", depth=depth + 1, seen=seen)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _json_budget(item, f"{path}[{index}]", depth=depth + 1, seen=seen)
    elif value is not None and not isinstance(value, (bool, int)):
        _fail("schema", path, f"unsupported canonical type: {type(value).__name__}")


def _check_schema(schema: dict[str, Any]) -> None:
    if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        _fail("schema", str(SCHEMA_PATH), "Draft 2020-12 identity drift")
    if schema.get("type") != "object" or schema.get("additionalProperties") is not False:
        _fail("schema", str(SCHEMA_PATH), "root schema must be a closed object")

    def walk(node: Any, path: str) -> None:
        if isinstance(node, dict):
            if node.get("type") == "object" and node.get("additionalProperties") is not False:
                _fail("schema", path, "object schema is not closed")
            for key, item in node.items():
                walk(item, f"{path}.{key}")
        elif isinstance(node, list):
            for index, item in enumerate(node):
                walk(item, f"{path}[{index}]")

    walk(schema, "$schema")
    if Draft202012Validator is not None:
        try:
            Draft202012Validator.check_schema(schema)
        except SchemaError as exc:
            _fail("schema", str(SCHEMA_PATH), f"standard meta-validation failed: {exc}")


def _validate_inventory_shape(value: dict[str, Any], schema: dict[str, Any]) -> None:
    _fields(value, INVENTORY_FIELDS, "$")
    if value["schema"] != "mathhead.trust-base-inventory.v1":
        _fail("schema", "$.schema", "inventory schema identity drift")
    _json_budget(value)
    if Draft202012Validator is not None:
        try:
            Draft202012Validator(schema).validate(value)
        except ValidationError as exc:
            where = ".".join(str(item) for item in exc.absolute_path)
            _fail("schema", f"$.{where}" if where else "$", exc.message)


def _validate_bindings(root: Path, value: dict[str, Any], inventory_raw: bytes) -> None:
    contract = _fields(
        value["contract"],
        {"contract_id", "sha256", "path", "schema_sha256"},
        "$.contract",
    )
    expected_contract = {
        "contract_id": TRUST_BASE_CONTRACT_ID,
        "sha256": TRUST_BASE_CONTRACT_SHA256,
        "path": TRUST_BASE_CONTRACT_PATH.as_posix(),
        "schema_sha256": TRUST_BASE_SCHEMA_SHA256,
    }
    if contract != expected_contract:
        _fail("contract", "$.contract", "accepted contract or schema binding drift")
    if _sha(_safe_path(root, contract["path"]).read_bytes()) != TRUST_BASE_CONTRACT_SHA256:
        _fail("contract", contract["path"], "accepted contract bytes drift")
    if _sha(_safe_path(root, SCHEMA_PATH.as_posix()).read_bytes()) != TRUST_BASE_SCHEMA_SHA256:
        _fail("contract", str(SCHEMA_PATH), "schema bytes drift")
    foundation = _fields(
        value["foundation"],
        {"bundle_sha256", "manifest_path", "manifest_sha256"},
        "$.foundation",
    )
    if foundation["bundle_sha256"] != FOUNDATION_BUNDLE_SHA256:
        _fail("foundation", "$.foundation.bundle_sha256", "bundle identity drift")
    manifest_path = _safe_path(
        root, _string(foundation["manifest_path"], "$.foundation.manifest_path")
    )
    manifest, manifest_raw = _load_json(manifest_path, canonical=True)
    if _sha(manifest_raw) != _hash(foundation["manifest_sha256"], "$.foundation.manifest_sha256"):
        _fail("foundation", str(manifest_path), "manifest byte identity drift")
    if manifest.get("bundle_sha256") != FOUNDATION_BUNDLE_SHA256:
        _fail("foundation", str(manifest_path), "manifest bundle identity drift")
    basis = dict(value)
    basis["inventory_sha256"] = ZERO_SHA256
    expected_identity = _sha(canonical_bytes(basis))
    if _hash(value["inventory_sha256"], "$.inventory_sha256") != expected_identity:
        _fail("identity", "$.inventory_sha256", "inventory basis identity drift")
    if inventory_raw != canonical_bytes(value):
        _fail("schema", str(INVENTORY_PATH), "inventory bytes are not canonical")


def _validate_authority_and_roles(
    value: dict[str, Any],
) -> tuple[dict[str, dict[str, Any]], set[str]]:
    tiers = value["authority_tiers"]
    if not isinstance(tiers, list) or [
        item.get("tier_id") for item in tiers if isinstance(item, dict)
    ] != list(AUTHORITY_ORDER):
        _fail("authority", "$.authority_tiers", "authority tier order or inventory drift")
    for index, item in enumerate(tiers):
        row = _fields(
            item,
            {"tier_id", "mathematical_authority", "meaning", "requirements"},
            f"$.authority_tiers[{index}]",
        )
        if not isinstance(row["mathematical_authority"], bool):
            _fail("schema", f"$.authority_tiers[{index}].mathematical_authority", "must be boolean")
        expected = row["tier_id"] in {
            "solver_verdict",
            "checker_attestation",
            "external_proof_assistant",
        }
        if row["mathematical_authority"] is not expected:
            _fail(
                "authority",
                f"$.authority_tiers[{index}]",
                "mathematical authority classification drift",
            )
        _string(row["meaning"], f"$.authority_tiers[{index}].meaning")
        _strings(row["requirements"], f"$.authority_tiers[{index}].requirements", allow_empty=False)
    roles = value["roles"]
    if not isinstance(roles, list) or not roles:
        _fail("schema", "$.roles", "roles must be a nonempty list")
    role_map: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(roles):
        row = _fields(item, {"role_id", "may_grant_authority", "meaning"}, f"$.roles[{index}]")
        role_id = _id(row["role_id"], f"$.roles[{index}].role_id")
        if role_id in role_map:
            _fail("authority", "$.roles", f"duplicate role: {role_id}")
        if not isinstance(row["may_grant_authority"], bool):
            _fail("schema", f"$.roles[{index}].may_grant_authority", "must be boolean")
        if role_id in NON_AUTHORITY_ROLES and row["may_grant_authority"]:
            _fail("authority", f"$.roles[{index}]", "non-authority role grants authority")
        _string(row["meaning"], f"$.roles[{index}].meaning")
        role_map[role_id] = row
    if list(role_map) != sorted(role_map):
        _fail("schema", "$.roles", "roles must be sorted by role_id")
    return role_map, set(AUTHORITY_ORDER)


def _validate_surfaces(
    root: Path,
    value: dict[str, Any],
    roles: dict[str, dict[str, Any]],
    authorities: set[str],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    surfaces = value["surfaces"]
    if not isinstance(surfaces, list) or not surfaces:
        _fail("schema", "$.surfaces", "surfaces must be a nonempty list")
    surface_map: dict[str, dict[str, Any]] = {}
    trusted_bytes: dict[str, str] = {}
    fields = {
        "surface_id",
        "category",
        "owner",
        "role_id",
        "current_authority",
        "target_authority",
        "state",
        "required",
        "source_paths",
        "import_roots",
        "trusted_primitives",
        "trusted_bytes",
        "attack_modes",
        "failure_modes",
        "controls",
        "migration",
    }
    for index, item in enumerate(surfaces):
        path = f"$.surfaces[{index}]"
        row = _fields(item, fields, path)
        surface_id = _id(row["surface_id"], f"{path}.surface_id")
        if surface_id in surface_map:
            _fail("surface", path, f"duplicate surface: {surface_id}")
        role = _id(row["role_id"], f"{path}.role_id")
        if role not in roles:
            _fail("surface", f"{path}.role_id", f"unknown role: {role}")
        current = _string(row["current_authority"], f"{path}.current_authority")
        target = _string(row["target_authority"], f"{path}.target_authority")
        if current not in authorities or target not in authorities:
            _fail("authority", path, "unknown authority tier")
        if (current != "none" or target != "none") and not roles[role]["may_grant_authority"]:
            _fail("authority", path, "non-authority role carries an authority tier")
        if role == "checker" and current not in {"none", "checker_attestation"}:
            _fail("authority", path, "checker role authority drift")
        if role == "proof_assistant" and target != "external_proof_assistant":
            _fail("authority", path, "proof-assistant target authority drift")
        if role == "producer" and current not in {"producer_report", "solver_verdict"}:
            _fail("authority", path, "producer authority drift")
        if not isinstance(row["required"], bool):
            _fail("schema", f"{path}.required", "must be boolean")
        state = _string(row["state"], f"{path}.state")
        if state == "future" and current != "none":
            _fail("authority", path, "future surface claims current authority")
        source_paths = _strings(row["source_paths"], f"{path}.source_paths")
        for source_path in source_paths:
            if not source_path.startswith("src/mathhead/") or not source_path.endswith(".py"):
                _fail("surface", path, f"invalid source path: {source_path}")
            _safe_path(root, source_path)
        _strings(row["import_roots"], f"{path}.import_roots")
        _strings(row["trusted_primitives"], f"{path}.trusted_primitives")
        for name in ("attack_modes", "failure_modes", "controls"):
            _strings(row[name], f"{path}.{name}", allow_empty=False)
        bytes_rows = row["trusted_bytes"]
        if not isinstance(bytes_rows, list):
            _fail("schema", f"{path}.trusted_bytes", "must be a list")
        seen_paths: list[str] = []
        for byte_index, binding in enumerate(bytes_rows):
            byte_path = f"{path}.trusted_bytes[{byte_index}]"
            bound = _fields(binding, {"path", "sha256", "reason"}, byte_path)
            relative = _string(bound["path"], f"{byte_path}.path")
            digest = _hash(bound["sha256"], f"{byte_path}.sha256")
            _string(bound["reason"], f"{byte_path}.reason")
            if _sha(_safe_path(root, relative).read_bytes()) != digest:
                _fail("primitive", relative, "trusted byte identity drift")
            if relative in trusted_bytes and trusted_bytes[relative] != digest:
                _fail("primitive", relative, "conflicting trusted byte identities")
            trusted_bytes[relative] = digest
            seen_paths.append(relative)
        if seen_paths != sorted(set(seen_paths)):
            _fail("schema", f"{path}.trusted_bytes", "must be sorted and unique by path")
        migration = _fields(
            row["migration"],
            {"task_id", "action", "target_owner", "target_state"},
            f"{path}.migration",
        )
        task = _string(migration["task_id"], f"{path}.migration.task_id", pattern=TASK_RE)
        if task < "MH-030" or task > "MH-037":
            _fail("migration", path, "surface migration must be owned by MH-030 through MH-037")
        _string(migration["action"], f"{path}.migration.action")
        _string(migration["target_owner"], f"{path}.migration.target_owner")
        _string(migration["target_state"], f"{path}.migration.target_state")
        owner = _string(row["owner"], f"{path}.owner")
        if ":" in owner:
            _target(root, owner)
        surface_map[surface_id] = row
    if list(surface_map) != sorted(surface_map):
        _fail("schema", "$.surfaces", "surfaces must be sorted by surface_id")
    required_bytes = {
        TRUST_BASE_CONTRACT_PATH.as_posix(),
        "docs/contracts/PYTHON_CONTRACT_FIRST_WORKFLOW_V1.md",
        CONFORMANCE_PATH.as_posix(),
        FOUNDATION_PATH.as_posix(),
    }
    if not required_bytes.issubset(trusted_bytes):
        _fail("primitive", "$.surfaces", "required governing byte bindings are incomplete")
    return surface_map, {path: {"sha256": digest} for path, digest in trusted_bytes.items()}


def _target(root: Path, target: str) -> tuple[str, str]:
    match = TARGET_RE.fullmatch(target)
    if match is None:
        _fail("entry-point", target, "invalid Python target")
    module = match.group("module")
    symbol = match.group("symbol")
    module_paths = _module_paths(root)
    if module not in module_paths:
        _fail("entry-point", target, "target module is missing")
    try:
        tree = ast.parse(module_paths[module].read_text(encoding="utf-8"), filename=target)
    except (OSError, UnicodeError, SyntaxError) as exc:
        _fail("source", target, f"cannot parse target: {exc}")
    matches = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        and node.name == symbol
    ]
    if len(matches) != 1:
        _fail("entry-point", target, f"target symbol count is {len(matches)}")
    return module, symbol


def _module_paths(root: Path) -> dict[str, Path]:
    source_root = root / "src/mathhead"
    try:
        paths = sorted(source_root.rglob("*.py"))
    except OSError as exc:
        _fail("source", str(source_root), f"cannot enumerate sources: {exc}")
    if not paths or len(paths) > 1000:
        _fail("budget", str(source_root), f"source file count is {len(paths)}")
    result: dict[str, Path] = {}
    total_bytes = 0
    for path in paths:
        try:
            resolved = path.resolve()
            resolved.relative_to(source_root.resolve())
            size = path.stat().st_size
        except (OSError, ValueError) as exc:
            _fail("source", str(path), f"unsafe source path: {exc}")
        total_bytes += size
        relative = path.relative_to(root / "src").as_posix()
        module = relative[:-3].replace("/", ".")
        if module.endswith(".__init__"):
            module = module[:-9]
        if module in result:
            _fail("source", relative, f"duplicate module identity: {module}")
        result[module] = path
    if total_bytes > 67_108_864:
        _fail("budget", str(source_root), "source byte budget exceeded")
    return result


def _resolve_imports(
    module: str,
    path: Path,
    tree: ast.AST,
    module_names: set[str],
) -> tuple[list[str], list[dict[str, Any]]]:
    imports: set[str] = set()
    package = module if path.name == "__init__.py" else module.rpartition(".")[0]
    dynamic: set[tuple[str, tuple[str, ...]]] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                parts = package.split(".") if package else []
                keep = len(parts) - node.level + 1
                if keep < 1:
                    _fail("import", module, "relative import escapes mathhead package")
                base = ".".join(parts[:keep])
                imported = ".".join(item for item in (base, node.module or "") if item)
            else:
                imported = node.module or ""
            if imported:
                imports.add(imported)
            for alias in node.names:
                candidate = ".".join(item for item in (imported, alias.name) if item)
                if candidate in module_names:
                    imports.add(candidate)
        elif isinstance(node, ast.Call):
            call = None
            if isinstance(node.func, ast.Name) and node.func.id in {"import_module", "__import__"}:
                call = node.func.id
            elif (
                isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "importlib"
                and node.func.attr == "import_module"
            ):
                call = "importlib.import_module"
            if call is not None:
                literals = tuple(
                    arg.value
                    for arg in node.args
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str)
                )
                dynamic.add((call, literals))
    return sorted(imports), [
        {"call": call, "literal_arguments": list(arguments)} for call, arguments in sorted(dynamic)
    ]


def _source_graph(root: Path) -> dict[str, Any]:
    paths = _module_paths(root)
    names = set(paths)
    modules: list[dict[str, Any]] = []
    internal_graph: dict[str, list[str]] = {}
    dynamic_calls: list[dict[str, Any]] = []
    root_users: dict[str, set[str]] = {}
    edge_count = 0
    for module, path in sorted(paths.items()):
        relative = path.relative_to(root).as_posix()
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=relative)
        except (OSError, UnicodeError, SyntaxError) as exc:
            _fail("source", relative, f"cannot parse source: {exc}")
        imports, dynamic = _resolve_imports(module, path, tree, names)
        internal: set[str] = set()
        roots: set[str] = set()
        for imported in imports:
            if imported == "mathhead" or imported.startswith("mathhead."):
                if imported not in names:
                    _fail("import", relative, f"unresolved internal import: {imported}")
                if imported != module:
                    internal.add(imported)
            else:
                root_name = imported.split(".", 1)[0]
                if ROOT_RE.fullmatch(root_name) is None:
                    _fail("import", relative, f"invalid import root: {root_name}")
                roots.add(root_name)
                root_users.setdefault(root_name, set()).add(relative)
        internal_graph[module] = sorted(internal)
        edge_count += len(internal) + len(roots)
        modules.append(
            {
                "module": module,
                "path": relative,
                "internal_imports": sorted(internal),
                "import_roots": sorted(roots),
            }
        )
        for call in dynamic:
            dynamic_calls.append({"module": module, "path": relative, **call})
    return {
        "files": [item["path"] for item in modules],
        "module_count": len(modules),
        "edge_count": edge_count,
        "modules": modules,
        "internal_graph": internal_graph,
        "root_users": {key: sorted(users) for key, users in sorted(root_users.items())},
        "dynamic_imports": sorted(
            dynamic_calls,
            key=lambda item: (item["module"], item["call"], item["literal_arguments"]),
        ),
    }


def _cycles(graph: dict[str, list[str]]) -> list[list[str]]:
    index = 0
    indices: dict[str, int] = {}
    low: dict[str, int] = {}
    stack: list[str] = []
    on_stack: set[str] = set()
    result: list[list[str]] = []

    def visit(node: str) -> None:
        nonlocal index
        indices[node] = low[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)
        for child in graph[node]:
            if child not in indices:
                visit(child)
                low[node] = min(low[node], low[child])
            elif child in on_stack:
                low[node] = min(low[node], indices[child])
        if low[node] == indices[node]:
            component: list[str] = []
            while True:
                child = stack.pop()
                on_stack.remove(child)
                component.append(child)
                if child == node:
                    break
            if len(component) > 1:
                result.append(sorted(component))

    for node in sorted(graph):
        if node not in indices:
            visit(node)
    return sorted(result)


def _console_scripts(root: Path) -> dict[str, str]:
    try:
        lines = (root / "pyproject.toml").read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        _fail("entry-point", "pyproject.toml", f"cannot read project scripts: {exc}")
    active = False
    scripts: dict[str, str] = {}
    pattern = re.compile(r'^([a-z][a-z0-9-]*)\s*=\s*"([^"\n]+)"\s*$')
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("["):
            active = stripped == "[project.scripts]"
            continue
        if active and stripped and not stripped.startswith("#"):
            match = pattern.fullmatch(stripped)
            if match is None:
                _fail(
                    "entry-point", "pyproject.toml", f"unsupported script declaration: {stripped}"
                )
            scripts[match.group(1)] = match.group(2)
    return dict(sorted(scripts.items()))


def _entry_points(
    root: Path,
    value: dict[str, Any],
    surfaces: dict[str, dict[str, Any]],
    graph: dict[str, Any],
) -> list[dict[str, Any]]:
    entries = value["entry_points"]
    if not isinstance(entries, list) or not entries:
        _fail("schema", "$.entry_points", "entry points must be a nonempty list")
    seen: dict[str, dict[str, Any]] = {}
    console: dict[str, str] = {}
    reports: list[dict[str, Any]] = []
    module_records = {item["module"]: item for item in graph["modules"]}
    for index, item in enumerate(entries):
        path = f"$.entry_points[{index}]"
        row = _fields(item, {"entry_id", "kind", "target", "surface_ids"}, path)
        entry_id = _id(row["entry_id"], f"{path}.entry_id")
        if entry_id in seen:
            _fail("entry-point", path, f"duplicate entry point: {entry_id}")
        kind = _string(row["kind"], f"{path}.kind")
        target = _string(row["target"], f"{path}.target", pattern=TARGET_RE)
        module, _symbol = _target(root, target)
        surface_ids = _strings(row["surface_ids"], f"{path}.surface_ids", allow_empty=False)
        unknown = sorted(set(surface_ids) - set(surfaces))
        if unknown:
            _fail("surface", path, f"unknown surface references: {unknown}")
        if kind == "console_script":
            name = entry_id.removeprefix("console.")
            console[name] = target
        closure: set[str] = set()
        pending = [module]
        while pending:
            current = pending.pop()
            if current in closure:
                continue
            closure.add(current)
            pending.extend(graph["internal_graph"][current])
        roots = sorted(
            {
                root_name
                for current in closure
                for root_name in module_records[current]["import_roots"]
            }
        )
        reports.append(
            {
                "entry_id": entry_id,
                "kind": kind,
                "target": target,
                "internal_closure": sorted(closure),
                "import_roots": roots,
                "surface_ids": surface_ids,
            }
        )
        seen[entry_id] = row
    if list(seen) != sorted(seen):
        _fail("schema", "$.entry_points", "entry points must be sorted by entry_id")
    if console != _console_scripts(root):
        _fail("entry-point", "$.entry_points", "console scripts do not match pyproject.toml")
    return reports


def _import_inventory(
    value: dict[str, Any],
    surfaces: dict[str, dict[str, Any]],
    graph: dict[str, Any],
) -> list[dict[str, Any]]:
    rows = value["import_roots"]
    if not isinstance(rows, list) or not rows:
        _fail("schema", "$.import_roots", "import roots must be a nonempty list")
    mapping: dict[str, dict[str, Any]] = {}
    reports: list[dict[str, Any]] = []
    for index, item in enumerate(rows):
        path = f"$.import_roots[{index}]"
        row = _fields(item, {"root", "kind", "surface_id", "policy", "reason"}, path)
        root_name = _string(row["root"], f"{path}.root", pattern=ROOT_RE)
        if root_name in mapping:
            _fail("import", path, f"duplicate import root: {root_name}")
        kind = _string(row["kind"], f"{path}.kind")
        expected_kind = (
            "third_party"
            if root_name in THIRD_PARTY_ROOTS
            else "language"
            if root_name == "__future__"
            else "stdlib"
        )
        if kind != expected_kind:
            _fail("import", path, f"root kind must be {expected_kind}")
        surface_id = _id(row["surface_id"], f"{path}.surface_id")
        if surface_id not in surfaces:
            _fail("surface", path, f"unknown import owner: {surface_id}")
        if root_name not in surfaces[surface_id]["import_roots"]:
            _fail("surface", path, "owning surface does not declare this import root")
        _string(row["policy"], f"{path}.policy")
        _string(row["reason"], f"{path}.reason")
        mapping[root_name] = row
        reports.append({**row, "source_paths": graph["root_users"].get(root_name, [])})
    if list(mapping) != sorted(mapping):
        _fail("schema", "$.import_roots", "import roots must be sorted")
    actual = set(graph["root_users"])
    if set(mapping) != actual:
        _fail(
            "import",
            "$.import_roots",
            f"root inventory drift: missing={sorted(actual - set(mapping))}, stale={sorted(set(mapping) - actual)}",
        )
    for surface_id, surface in surfaces.items():
        for root_name in surface["import_roots"]:
            if root_name not in mapping or mapping[root_name]["surface_id"] != surface_id:
                _fail("surface", surface_id, f"import root ownership drift: {root_name}")
    return reports


def _validate_migrations(value: dict[str, Any], surfaces: dict[str, dict[str, Any]]) -> None:
    rows = value["migration_order"]
    expected = [f"MH-03{number}" for number in range(1, 8)]
    if (
        not isinstance(rows, list)
        or [item.get("task_id") for item in rows if isinstance(item, dict)] != expected
    ):
        _fail("migration", "$.migration_order", "must contain MH-031 through MH-037 in order")
    closed: dict[str, str] = {}
    completed = {"MH-030"}
    for index, item in enumerate(rows):
        path = f"$.migration_order[{index}]"
        row = _fields(item, {"task_id", "depends_on", "closes"}, path)
        task = _string(row["task_id"], f"{path}.task_id", pattern=TASK_RE)
        dependencies = _strings(row["depends_on"], f"{path}.depends_on")
        if not dependencies or not set(dependencies).issubset(completed):
            _fail("migration", path, "dependency is missing, forward, or cyclic")
        closes = _strings(row["closes"], f"{path}.closes", allow_empty=False)
        for surface_id in closes:
            if surface_id not in surfaces:
                _fail("migration", path, f"unknown surface: {surface_id}")
            if surface_id in closed:
                _fail("migration", path, f"surface already closed by {closed[surface_id]}")
            if surfaces[surface_id]["migration"]["task_id"] != task:
                _fail("migration", path, f"surface migration owner drift: {surface_id}")
            closed[surface_id] = task
        completed.add(task)
    if set(closed) != set(surfaces):
        _fail(
            "migration",
            "$.migration_order",
            f"uncovered surfaces: {sorted(set(surfaces) - set(closed))}",
        )


def _validate_kernel_target(value: dict[str, Any], import_rows: list[dict[str, Any]]) -> None:
    target = _fields(
        value["kernel_target"],
        {
            "owner",
            "task_id",
            "authority",
            "source_budget",
            "allow_import_roots",
            "deny_import_roots",
            "allowed_primitives",
            "forbidden_capabilities",
            "replay_requirement",
        },
        "$.kernel_target",
    )
    if (target["owner"], target["task_id"], target["authority"]) != (
        "mathhead.kernel",
        "MH-032",
        "checker_attestation",
    ):
        _fail("primitive", "$.kernel_target", "target owner, task, or authority drift")
    allowed = set(
        _strings(
            target["allow_import_roots"], "$.kernel_target.allow_import_roots", allow_empty=False
        )
    )
    denied = set(
        _strings(
            target["deny_import_roots"], "$.kernel_target.deny_import_roots", allow_empty=False
        )
    )
    if allowed & denied:
        _fail("primitive", "$.kernel_target", "allowlist and denylist overlap")
    if not KERNEL_DENY_REQUIRED.issubset(denied):
        _fail("primitive", "$.kernel_target.deny_import_roots", "mandatory exclusion is missing")
    root_kinds = {row["root"]: row["kind"] for row in import_rows}
    if any(
        (root_name not in root_kinds and root_name not in FUTURE_STDLIB_ROOTS)
        or root_kinds.get(root_name) == "third_party"
        for root_name in allowed
    ):
        _fail(
            "primitive",
            "$.kernel_target.allow_import_roots",
            "allowlist contains unknown or third-party root",
        )
    _strings(target["allowed_primitives"], "$.kernel_target.allowed_primitives", allow_empty=False)
    forbidden = set(
        _strings(
            target["forbidden_capabilities"],
            "$.kernel_target.forbidden_capabilities",
            allow_empty=False,
        )
    )
    required_forbidden = {
        "cas",
        "clock",
        "dynamic_import",
        "environment",
        "filesystem",
        "floating_point",
        "network",
        "process",
        "randomness",
        "solver",
        "transport",
    }
    if not required_forbidden.issubset(forbidden):
        _fail(
            "primitive",
            "$.kernel_target.forbidden_capabilities",
            "forbidden capability closure is incomplete",
        )
    _string(target["replay_requirement"], "$.kernel_target.replay_requirement")
    budget = _fields(
        target["source_budget"],
        {
            "max_modules",
            "max_transitive_internal_modules",
            "max_stdlib_roots",
            "max_third_party_roots",
            "max_dynamic_imports",
            "max_effect_roots",
        },
        "$.kernel_target.source_budget",
    )
    for key, limit in budget.items():
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 0:
            _fail("budget", f"$.kernel_target.source_budget.{key}", "must be a nonnegative integer")
    for key in ("max_third_party_roots", "max_dynamic_imports", "max_effect_roots"):
        if budget[key] != 0:
            _fail("budget", f"$.kernel_target.source_budget.{key}", "must be zero")


def _report_identity(report: dict[str, Any]) -> str:
    basis = dict(report)
    basis["report_sha256"] = ZERO_SHA256
    return _sha(canonical_bytes(basis))


def validate_trust_base(root: Path, *, check_report: Path | None = None) -> dict[str, Any]:
    """Validate inventory and static repository trust graph without importing product code."""
    root = root.resolve()
    inventory_path = _safe_path(root, INVENTORY_PATH.as_posix())
    schema_path = _safe_path(root, SCHEMA_PATH.as_posix())
    schema, _schema_raw = _load_json(schema_path, canonical=False)
    _check_schema(schema)
    inventory, inventory_raw = _load_json(inventory_path, canonical=True)
    _validate_inventory_shape(inventory, schema)
    _validate_bindings(root, inventory, inventory_raw)
    roles, authorities = _validate_authority_and_roles(inventory)
    surfaces, trusted_bytes = _validate_surfaces(root, inventory, roles, authorities)
    graph = _source_graph(root)
    import_rows = _import_inventory(inventory, surfaces, graph)
    entry_rows = _entry_points(root, inventory, surfaces, graph)
    _validate_migrations(inventory, surfaces)
    _validate_kernel_target(inventory, import_rows)
    effect_rows = [row for row in import_rows if row["root"] in EFFECT_ROOTS]
    dynamic_paths = {item["path"] for item in graph["dynamic_imports"]}
    declared_dynamic = set(surfaces["process.dynamic-import"]["source_paths"])
    if dynamic_paths != declared_dynamic:
        _fail("effect", "process.dynamic-import", "dynamic import source inventory drift")
    authority_owners = sorted(
        {
            surface["owner"]
            for surface in surfaces.values()
            if surface["current_authority"] != "none"
        }
    )
    report: dict[str, Any] = {
        "schema": "mathhead.trust-base-report.v1",
        "contract": {
            "contract_id": TRUST_BASE_CONTRACT_ID,
            "sha256": TRUST_BASE_CONTRACT_SHA256,
        },
        "inventory": {
            "path": INVENTORY_PATH.as_posix(),
            "sha256": _sha(inventory_raw),
            "identity_sha256": inventory["inventory_sha256"],
            "schema_path": SCHEMA_PATH.as_posix(),
            "schema_sha256": TRUST_BASE_SCHEMA_SHA256,
        },
        "foundation": inventory["foundation"],
        "source": {
            "root": "src/mathhead",
            "file_count": len(graph["files"]),
            "module_count": graph["module_count"],
            "edge_count": graph["edge_count"],
            "files": graph["files"],
            "modules": graph["modules"],
            "cycles": _cycles(graph["internal_graph"]),
        },
        "import_roots": import_rows,
        "entry_points": entry_rows,
        "dynamic_imports": graph["dynamic_imports"],
        "effect_boundaries": effect_rows,
        "authority_owners": authority_owners,
        "surface_summary": {
            "count": len(surfaces),
            "ids": sorted(surfaces),
            "trusted_bytes": [
                {"path": path, "sha256": binding["sha256"]}
                for path, binding in sorted(trusted_bytes.items())
            ],
        },
        "kernel_target": inventory["kernel_target"],
        "migration_order": inventory["migration_order"],
        "checks": [{"id": check, "status": "passed"} for check in REPORT_CHECKS],
        "report_sha256": ZERO_SHA256,
    }
    report["report_sha256"] = _report_identity(report)
    if check_report is not None:
        try:
            relative = check_report.resolve().relative_to(root).as_posix()
        except ValueError:
            _fail("path", str(check_report), "report path escapes repository")
        current = _safe_path(root, relative)
        try:
            raw = current.read_bytes()
        except OSError as exc:
            _fail("report", relative, f"cannot read report: {exc}")
        if raw != canonical_bytes(report):
            _fail("report", relative, "deterministic report drift")
    return report


def _write_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=path.parent, prefix=f".{path.name}.", delete=False
        ) as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
            temporary = Path(handle.name)
        os.replace(temporary, path)
    except OSError as exc:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        _fail("report", str(path), f"atomic report write failed: {exc}")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    output = parser.add_mutually_exclusive_group()
    output.add_argument("--write-report", type=Path)
    output.add_argument("--check-report", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = args.root.resolve()
    check_path = args.check_report
    if check_path is None and args.write_report is None:
        check_path = root / REPORT_PATH
    elif check_path is not None and not check_path.is_absolute():
        check_path = root / check_path
    try:
        report = validate_trust_base(root, check_report=check_path)
        if args.write_report is not None:
            target = (
                args.write_report if args.write_report.is_absolute() else root / args.write_report
            )
            try:
                target.resolve().relative_to(root)
            except ValueError:
                _fail("path", str(target), "write-report path escapes repository")
            _write_atomic(target, canonical_bytes(report))
            print(f"trust-base: report updated: {target}")
        print(
            "trust-base: PASS "
            f"(modules={report['source']['module_count']}, "
            f"roots={len(report['import_roots'])}, "
            f"surfaces={report['surface_summary']['count']}, "
            f"report={report['report_sha256'][:12]})"
        )
        return 0
    except TrustBaseValidationError as exc:
        print(f"trust-base: {exc.kind}: {exc}", file=os.sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
