#!/usr/bin/env python3
"""Validate the accepted MH-C-GRAPH-BUDGET-001 binding fail-closed."""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
import hashlib
import inspect
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

EXPECTED_CONTRACT_SHA256 = \
    "3af2573324b7c485b8b3612cacde764e36bad341ce9ab4f83ebd819b39e7d794"
FROZEN_BASELINE_SHA256 = \
    "b93f71ce676380574235ca422e8a23a8f4871ee45b2973195575ea397cefe19a"
FROZEN_OBSERVATIONS_SHA256 = \
    "69c90d4e71a9955c4211b5939be75bdde19a2d05457b1d272d900b74b11aa903"


class GraphBudgetValidationError(RuntimeError):
    """Raised when the accepted resource boundary or its binding drifts."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _function(tree: ast.Module, name: str) -> ast.FunctionDef:
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise GraphBudgetValidationError(f"missing function: {name}")


def _assignment_int(tree: ast.Module, name: str) -> int:
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == name for target in node.targets):
            value = ast.literal_eval(node.value)
            if isinstance(value, int) and not isinstance(value, bool):
                return value
    raise GraphBudgetValidationError(f"missing integer assignment: {name}")


def _load_planner(tree: ast.Module) -> dict[str, object]:
    names = {
        "GRAPH_BUDGET_CONTRACT_ID",
        "GRAPH_BUDGET_CONTRACT_SHA256",
        "GraphSearchPlan",
        "graph_search_plan",
    }
    body: list[ast.stmt] = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id in names for target in node.targets):
            body.append(node)
        elif isinstance(node, (ast.ClassDef, ast.FunctionDef)) and node.name in names:
            body.append(node)
    namespace: dict[str, object] = {"dataclass": dataclass, "field": field}
    exec(compile(ast.fix_missing_locations(ast.Module(body=body, type_ignores=[])),
                 "product-planner", "exec"), namespace)
    return namespace


def validate() -> None:
    accepted = ROOT / "docs/contracts/MH-C-GRAPH-BUDGET-001.json"
    proposed = ROOT / "docs/contracts/proposed/MH-C-GRAPH-BUDGET-001.json"
    for path in (accepted, proposed):
        if _sha256(path) != EXPECTED_CONTRACT_SHA256:
            raise GraphBudgetValidationError(f"contract hash drift: {path.relative_to(ROOT)}")
    if accepted.read_bytes() != proposed.read_bytes():
        raise GraphBudgetValidationError("accepted contract differs from reviewed proposal")
    if _sha256(ROOT / "docs/reconstruction/legacy-baseline-v1.json") != FROZEN_BASELINE_SHA256:
        raise GraphBudgetValidationError("immutable baseline artifact drift")
    if _sha256(ROOT / "docs/reconstruction/legacy-observations-v1.json") != \
            FROZEN_OBSERVATIONS_SHA256:
        raise GraphBudgetValidationError("immutable observation artifact drift")

    product_path = SRC / "mathhead/discovery/product.py"
    formalize_path = SRC / "mathhead/discovery/formalize.py"
    cli_path = SRC / "mathhead/discovery/cli.py"
    product_tree = ast.parse(product_path.read_text(encoding="utf-8"))
    formalize_tree = ast.parse(formalize_path.read_text(encoding="utf-8"))
    cli_tree = ast.parse(cli_path.read_text(encoding="utf-8"))
    planner = _load_planner(product_tree)

    if planner["GRAPH_BUDGET_CONTRACT_ID"] != "MH-C-GRAPH-BUDGET-001" or \
            planner["GRAPH_BUDGET_CONTRACT_SHA256"] != EXPECTED_CONTRACT_SHA256:
        raise GraphBudgetValidationError("implementation contract metadata drift")
    graph_search_plan = planner["graph_search_plan"]
    signature = inspect.signature(graph_search_plan)
    if list(signature.parameters) != ["max_n", "fast_backend_available"]:
        raise GraphBudgetValidationError(f"graph_search_plan signature drift: {signature}")
    if signature.parameters["fast_backend_available"].kind is not \
            inspect.Parameter.KEYWORD_ONLY:
        raise GraphBudgetValidationError("fast_backend_available must be keyword-only")
    check_node = _function(product_tree, "check")
    if len(check_node.args.args) != 2 or check_node.args.args[1].arg != "max_n" or \
            len(check_node.args.defaults) != 1 or ast.literal_eval(check_node.args.defaults[0]) != 6:
        raise GraphBudgetValidationError("public check default must be max_n=6")
    if _assignment_int(formalize_tree, "_MAX_ORDER") != 8:
        raise GraphBudgetValidationError("formalization fast wall must be order 8")

    cli_defaults: list[tuple[int, object]] = []
    for node in ast.walk(cli_tree):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        if not isinstance(node.args[0], ast.Constant) or node.args[0].value != "--max-n":
            continue
        for keyword in node.keywords:
            if keyword.arg == "default":
                cli_defaults.append((node.lineno, ast.literal_eval(keyword.value)))
    if not cli_defaults or min(cli_defaults)[1] != 6:
        raise GraphBudgetValidationError("discovery CLI default must be max_n=6")

    pure = graph_search_plan(6, fast_backend_available=False)
    fast = graph_search_plan(8, fast_backend_available=True)
    pure_refusal = graph_search_plan(7, fast_backend_available=False)
    fast_refusal = graph_search_plan(9, fast_backend_available=True)
    if (pure.backend, pure.safe_max_n, pure.max_objects, pure.supported) != \
            ("pure_python", 6, 2_000, True):
        raise GraphBudgetValidationError("pure plan drift")
    if (fast.backend, fast.safe_max_n, fast.max_objects, fast.supported) != \
            ("nauty", 8, 20_000, True):
        raise GraphBudgetValidationError("fast plan drift")
    if (pure_refusal.supported, pure_refusal.reason) != (False, "fast-backend-required"):
        raise GraphBudgetValidationError("pure order-seven refusal drift")
    if (fast_refusal.supported, fast_refusal.reason) != \
            (False, "fast-order-limit-exceeded"):
        raise GraphBudgetValidationError("fast order-nine refusal drift")

    for tree, name in ((product_tree, "_graph_bound_verdict"),
                       (formalize_tree, "evaluate_candidate")):
        node = _function(tree, name)
        if any(isinstance(child, (ast.ListComp, ast.SetComp, ast.DictComp))
               for child in ast.walk(node)):
            raise GraphBudgetValidationError(f"cross-order materialization returned: {name}")
    verdict_node = _function(product_tree, "_graph_bound_verdict")
    calls = {
        child.func.id: child.lineno
        for child in ast.walk(verdict_node)
        if isinstance(child, ast.Call) and isinstance(child.func, ast.Name)
        and child.func.id in {"graph_search_plan", "_iter_planned_graphs"}
    }
    if set(calls) != {"graph_search_plan", "_iter_planned_graphs"} or \
            calls["graph_search_plan"] >= calls["_iter_planned_graphs"]:
        raise GraphBudgetValidationError("enumeration is not guarded by the accepted plan")


def main() -> int:
    try:
        validate()
    except (GraphBudgetValidationError, OSError, SyntaxError) as exc:
        print(f"graph-budget: FAIL: {exc}", file=sys.stderr)
        return 1
    print("graph-budget: PASS (pure<=6/2000, nauty<=8/20000, defaults=6)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
