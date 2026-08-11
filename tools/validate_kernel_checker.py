"""Validate the accepted MH-032 dependency-minimal checker boundary."""

from __future__ import annotations

import ast
from fractions import Fraction
import hashlib
import inspect
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "src"
PACKAGE_ROOT = SOURCE_ROOT / "mathhead"
CONTRACT = ROOT / "docs/contracts/MH-C-KERNEL-CHECKER-001.json"
PROPOSAL = ROOT / "docs/contracts/proposed/MH-C-KERNEL-CHECKER-001.json"
SCHEMA = ROOT / "docs/contracts/schemas/kernel-checker-result-v1.schema.json"
TRUST_INVENTORY = ROOT / "docs/trust/trust-base-v1.json"

CONTRACT_ID = "MH-C-KERNEL-CHECKER-001"
CONTRACT_SHA256 = "78293c5a2e8845377e8bd704398c7a0058afcea74017dffbc2a18daac97ecff7"
SCHEMA_SHA256 = "0718099abb10ff08501909b59faa92a1d4579c9047ef29576b16b1ed8a1892e4"
ALLOWED_ROOTS = {
    "__future__",
    "dataclasses",
    "fractions",
    "hashlib",
    "json",
    "math",
    "typing",
}
DENIED_ROOTS = {
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


class KernelCheckerContractError(ValueError):
    pass


def _fail(detail: str) -> None:
    raise KernelCheckerContractError(detail)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        _fail(f"cannot load {path.relative_to(ROOT)}: {type(exc).__name__}")
    if type(value) is not dict:
        _fail(f"{path.relative_to(ROOT)} must contain an object")
    return value


def _module_name(path: Path) -> str:
    relative = path.relative_to(SOURCE_ROOT).with_suffix("")
    parts = list(relative.parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _module_path(module: str) -> Path | None:
    if module != "mathhead" and not module.startswith("mathhead."):
        return None
    relative = Path(*module.split("."))
    file_path = SOURCE_ROOT / relative.with_suffix(".py")
    if file_path.is_file():
        return file_path
    init_path = SOURCE_ROOT / relative / "__init__.py"
    if init_path.is_file():
        return init_path
    _fail(f"unresolved internal checker import: {module}")


def _package_initializers(path: Path) -> set[Path]:
    result: set[Path] = set()
    parent = path.parent
    while parent == PACKAGE_ROOT or PACKAGE_ROOT in parent.parents:
        init_path = parent / "__init__.py"
        if init_path.is_file():
            result.add(init_path)
        if parent == PACKAGE_ROOT:
            break
        parent = parent.parent
    return result


def _resolve_from(path: Path, node: ast.ImportFrom) -> str | None:
    if node.level == 0:
        return node.module
    module = _module_name(path)
    package_parts = module.split(".") if path.name == "__init__.py" else module.split(".")[:-1]
    remove = node.level - 1
    if remove > len(package_parts):
        _fail(f"relative import escapes package in {path.relative_to(ROOT)}")
    base = package_parts[: len(package_parts) - remove]
    if node.module:
        base.extend(node.module.split("."))
    return ".".join(base)


def _source_closure(entry: Path) -> tuple[set[Path], set[str]]:
    pending = [entry]
    closure: set[Path] = set()
    roots: set[str] = set()
    while pending:
        path = pending.pop()
        if path in closure:
            continue
        closure.add(path)
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, UnicodeError, SyntaxError) as exc:
            _fail(f"cannot parse {path.relative_to(ROOT)}: {type(exc).__name__}")
        for node in ast.walk(tree):
            module: str | None = None
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported = _module_path(alias.name)
                    if imported is None:
                        roots.add(alias.name.split(".", 1)[0])
                    else:
                        pending.extend(_package_initializers(imported))
                        pending.append(imported)
                continue
            if isinstance(node, ast.ImportFrom):
                module = _resolve_from(path, node)
            if not module:
                continue
            imported = _module_path(module)
            if imported is None:
                roots.add(module.split(".", 1)[0])
            else:
                pending.extend(_package_initializers(imported))
                pending.append(imported)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in {"__import__", "eval", "exec", "open"}:
                    _fail(f"dynamic or effect call {node.func.id} in {path.relative_to(ROOT)}")
    return closure, roots


def _verify_artifacts() -> None:
    if not CONTRACT.is_file() or not PROPOSAL.is_file() or not SCHEMA.is_file():
        _fail("checker contract, proposal, or schema is missing")
    if CONTRACT.read_bytes() != PROPOSAL.read_bytes():
        _fail("accepted checker contract differs from its proposal")
    if _sha256(CONTRACT) != CONTRACT_SHA256:
        _fail("accepted checker contract hash differs")
    if _sha256(SCHEMA) != SCHEMA_SHA256:
        _fail("checker-result schema hash differs")
    contract = _load(CONTRACT)
    if contract.get("contract_id") != CONTRACT_ID:
        _fail("checker contract ID differs")
    if contract.get("target") != "mathhead.kernel.checkers:check_proof_term":
        _fail("checker contract target differs")
    if contract.get("signature") != "check_proof_term(term: object) -> CheckerResult":
        _fail("checker contract signature differs")
    if SCHEMA_SHA256 not in contract.get("requires", [])[-1]:
        _fail("checker contract does not bind the exact result schema")
    schema = _load(SCHEMA)
    if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        _fail("checker-result schema is not Draft 2020-12")
    if schema.get("additionalProperties") is not False:
        _fail("checker-result schema root is open")


def _verify_closure() -> tuple[int, int]:
    entry = PACKAGE_ROOT / "kernel/checkers.py"
    if not entry.is_file():
        _fail("checker implementation is missing")
    closure, roots = _source_closure(entry)
    trust = _load(TRUST_INVENTORY).get("kernel_target")
    if type(trust) is not dict or trust.get("task_id") != "MH-032":
        _fail("MH-030 kernel target is missing")
    source_budget = trust.get("source_budget")
    if type(source_budget) is not dict:
        _fail("MH-030 kernel source budget is missing")
    if len(closure) > source_budget.get("max_transitive_internal_modules", -1):
        _fail(f"checker closure exceeds internal-module budget: {len(closure)}")
    if len(roots) > source_budget.get("max_stdlib_roots", -1):
        _fail(f"checker closure exceeds stdlib-root budget: {len(roots)}")
    if not roots <= ALLOWED_ROOTS:
        _fail(f"checker closure imports undeclared roots: {sorted(roots - ALLOWED_ROOTS)}")
    if roots & DENIED_ROOTS:
        _fail(f"checker closure imports denied roots: {sorted(roots & DENIED_ROOTS)}")
    relative = {str(path.relative_to(ROOT)).replace("\\", "/") for path in closure}
    if any("discovery" in path or "certificate.py" in path for path in relative):
        _fail("checker closure contains a legacy producer or checker")
    return len(closure), len(roots)


def _verify_runtime() -> int:
    sys.path.insert(0, str(SOURCE_ROOT))
    from mathhead.kernel.checkers import (
        KERNEL_CHECKER_CONTRACT_ID,
        KERNEL_CHECKER_CONTRACT_SHA256,
        check_proof_term,
        checker_result_to_bytes,
        parse_checker_result,
    )
    from mathhead.kernel.proof_terms import (
        crt,
        polynomial_identity,
        residue,
        sum_induction,
    )

    if KERNEL_CHECKER_CONTRACT_ID != CONTRACT_ID:
        _fail("checker source contract ID differs")
    if KERNEL_CHECKER_CONTRACT_SHA256 != CONTRACT_SHA256:
        _fail("checker source contract SHA-256 differs")
    signature = inspect.signature(check_proof_term)
    if list(signature.parameters) != ["term"]:
        _fail("checker target parameter list differs")
    if str(signature.parameters["term"].annotation) not in {"object", "'object'"}:
        _fail("checker target parameter annotation differs")
    if str(signature.return_annotation) not in {"CheckerResult", "'CheckerResult'"}:
        _fail("checker target return annotation differs")

    polynomial = (0, -1, 0, 1)
    cases = (
        residue(2, polynomial),
        crt((residue(2, polynomial), residue(3, polynomial))),
        sum_induction((0, 1), (0, Fraction(1, 2), Fraction(1, 2))),
        polynomial_identity(polynomial, polynomial),
    )
    for term in cases:
        first = check_proof_term(term)
        second = check_proof_term(term)
        if first != second or first.verdict != "verified":
            _fail("checker positive decision is not deterministic and verified")
        encoded = checker_result_to_bytes(first)
        if parse_checker_result(encoded) != first:
            _fail("checker canonical replay differs")
        envelope = json.loads(encoded)
        result_bytes = (
            json.dumps(
                envelope["result"],
                ensure_ascii=True,
                allow_nan=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        ).encode("utf-8")
        if hashlib.sha256(result_bytes).hexdigest() != envelope["result_sha256"]:
            _fail("checker result identity differs")
    false = check_proof_term(residue(2, (1,)))
    if false.authority != "none" or false.statement is not None or false.verdict != "invalid":
        _fail("false residue acquired checker authority")
    unknown = check_proof_term(object())
    if unknown.reason_code != "UNSUPPORTED_TERM" or unknown.authority != "none":
        _fail("unsupported object acquired checker authority")
    return len(cases)


def _verify_legacy_adapter() -> int:
    source = PACKAGE_ROOT / "legacy_kernel_adapter.py"
    if not source.is_file():
        _fail("legacy proof-term adapter is missing")
    try:
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
    except (OSError, UnicodeError, SyntaxError) as exc:
        _fail(f"cannot parse legacy proof-term adapter: {type(exc).__name__}")
    imported = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    if "mathhead.kernel.checkers" in imported:
        _fail("non-authoritative legacy adapter imports checker authority")

    from mathhead.kernel.checkers import check_proof_term
    from mathhead.legacy_kernel_adapter import LegacyProofAdapterError, adapt_legacy_proof_term

    def legacy_type(name: str) -> type:
        return type(name, (), {"__module__": "mathhead.discovery.kernel"})

    CRT = legacy_type("CRT")
    Identity = legacy_type("Identity")
    Residue = legacy_type("Residue")
    SumInduction = legacy_type("SumInduction")
    Theorem = legacy_type("Theorem")
    polynomial = (0, -1, 0, 1)
    cases = (
        Residue(),
        CRT(),
        SumInduction(),
        Identity(),
    )
    cases[0].modulus, cases[0].poly = 2, polynomial
    left, right = Residue(), Residue()
    left.modulus, left.poly = 2, polynomial
    right.modulus, right.poly = 3, polynomial
    cases[1].parts = (left, right)
    cases[2].f_poly = (0, 1)
    cases[2].g_poly = (0, Fraction(1, 2), Fraction(1, 2))
    cases[3].lhs, cases[3].rhs = polynomial, polynomial
    for legacy in cases:
        candidate = adapt_legacy_proof_term(legacy)
        if hasattr(candidate, "authority"):
            _fail("legacy adapter output carries authority")
        if check_proof_term(candidate).verdict != "verified":
            _fail("valid migrated legacy proof does not replay")
    forged = object.__new__(Theorem)
    object.__setattr__(forged, "kind", "Divides")
    object.__setattr__(forged, "payload", (2, polynomial))
    try:
        adapt_legacy_proof_term(forged)
    except LegacyProofAdapterError as exc:
        if exc.kind != "authority":
            _fail("legacy theorem rejection has unstable classification")
    else:
        _fail("legacy theorem crossed migration boundary")
    return len(cases)


def main() -> int:
    try:
        _verify_artifacts()
        closure_count, root_count = _verify_closure()
        case_count = _verify_runtime()
        legacy_count = _verify_legacy_adapter()
    except KernelCheckerContractError as exc:
        print(f"kernel-checker: FAIL: {exc}", file=sys.stderr)
        return 1
    print(
        "kernel-checker: PASS "
        f"(closure={closure_count}, roots={root_count}, cases={case_count}, "
        f"legacy={legacy_count}, "
        f"checker={CONTRACT_SHA256[:12]})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
