#!/usr/bin/env python3
"""Validate MH-C-DISCOVERY-PORTFOLIO-002 without runtime dependencies."""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/mathhead/discovery/arithmetic.py"
EXPECTED_CONTRACT_SHA256 = \
    "247534720fe49f89a9961196701cc12a954f5e95e12bd7b8b8c5a07318b3bf7b"
SUPERSEDED_CONTRACT_SHA256 = \
    "aa0fbda6f0ba42c8f154ffc21a6a35eb7386f53e47be40326e5d49e3bc5be223"
EXPECTED_SAMPLE_SHA256 = \
    "fe96722948f40d6f6b0ba21ac9792d0556d4e9ab20093d1c8d65b10970cd93e9"
FROZEN_BASELINE_SHA256 = \
    "b93f71ce676380574235ca422e8a23a8f4871ee45b2973195575ea397cefe19a"
FROZEN_OBSERVATIONS_SHA256 = \
    "69c90d4e71a9955c4211b5939be75bdde19a2d05457b1d272d900b74b11aa903"


class DiscoveryPortfolioValidationError(RuntimeError):
    """Raised when deterministic proof selection or its evidence drifts."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _assignment(tree: ast.Module, name: str) -> ast.AST:
    matches = [
        node.value for node in tree.body
        if isinstance(node, (ast.Assign, ast.AnnAssign))
        and ((isinstance(node, ast.Assign)
              and any(isinstance(target, ast.Name) and target.id == name
                      for target in node.targets))
             or (isinstance(node, ast.AnnAssign)
                 and isinstance(node.target, ast.Name) and node.target.id == name))
    ]
    if len(matches) != 1:
        raise DiscoveryPortfolioValidationError(f"assignment drift: {name}")
    return matches[0]


def _validate_contracts() -> None:
    current = ROOT / "docs/contracts/MH-C-DISCOVERY-PORTFOLIO-002.json"
    proposal = ROOT / "docs/contracts/proposed/MH-C-DISCOVERY-PORTFOLIO-002.json"
    prior = ROOT / "docs/contracts/MH-C-DISCOVERY-PORTFOLIO-001.json"
    prior_proposal = ROOT / "docs/contracts/proposed/MH-C-DISCOVERY-PORTFOLIO-001.json"
    for path in (current, proposal):
        if _sha256(path) != EXPECTED_CONTRACT_SHA256:
            raise DiscoveryPortfolioValidationError(
                f"current contract hash drift: {path.relative_to(ROOT)}"
            )
    for path in (prior, prior_proposal):
        if _sha256(path) != SUPERSEDED_CONTRACT_SHA256:
            raise DiscoveryPortfolioValidationError(
                f"superseded contract hash drift: {path.relative_to(ROOT)}"
            )
    if current.read_bytes() != proposal.read_bytes():
        raise DiscoveryPortfolioValidationError("accepted contract differs from reviewed proposal")
    if prior.read_bytes() != prior_proposal.read_bytes():
        raise DiscoveryPortfolioValidationError("superseded contract evidence differs")
    expected_files = {
        ROOT / "docs/discovery/SAMPLE-REPORT.md": EXPECTED_SAMPLE_SHA256,
        ROOT / "docs/reconstruction/legacy-baseline-v1.json": FROZEN_BASELINE_SHA256,
        ROOT / "docs/reconstruction/legacy-observations-v1.json": FROZEN_OBSERVATIONS_SHA256,
    }
    for path, expected in expected_files.items():
        if _sha256(path) != expected:
            raise DiscoveryPortfolioValidationError(
                f"differential evidence drift: {path.relative_to(ROOT)}"
            )


def _validate_source() -> None:
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"), filename=str(SOURCE))
    contract_id = _assignment(tree, "DISCOVERY_PORTFOLIO_CONTRACT_ID")
    contract_hash = _assignment(tree, "DISCOVERY_PORTFOLIO_CONTRACT_SHA256")
    degree_limit = _assignment(tree, "_MAX_INDUCTION_FIRST_DEGREE")
    if not isinstance(contract_id, ast.Constant) or \
            contract_id.value != "MH-C-DISCOVERY-PORTFOLIO-002":
        raise DiscoveryPortfolioValidationError("implementation contract ID drift")
    if not isinstance(contract_hash, ast.Constant) or \
            contract_hash.value != EXPECTED_CONTRACT_SHA256:
        raise DiscoveryPortfolioValidationError("implementation contract hash drift")
    if not isinstance(degree_limit, ast.Constant) or degree_limit.value != 3:
        raise DiscoveryPortfolioValidationError("induction-first degree boundary drift")

    functions = [
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "discover_and_prove"
    ]
    if len(functions) != 1:
        raise DiscoveryPortfolioValidationError("discover_and_prove definition drift")
    fn = functions[0]
    if [arg.arg for arg in fn.args.args] != [
        "expr", "fn", "check_upto", "judge_timeout_ms"
    ] or len(fn.args.defaults) != 2:
        raise DiscoveryPortfolioValidationError("discover_and_prove signature drift")

    calls = [
        (node.func.id, node.lineno)
        for node in ast.walk(fn)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        and node.func.id in {
            "poly_from_sympy", "prove_modular_divisibility", "prove_by_residues"
        }
    ]
    names = [name for name, _line in calls]
    if names.count("poly_from_sympy") < 2 or \
            names.count("prove_modular_divisibility") != 1 or \
            names.count("prove_by_residues") != 2:
        raise DiscoveryPortfolioValidationError("portfolio call structure drift")
    selection_line = min(line for name, line in calls if name == "poly_from_sympy")
    solver_line = next(line for name, line in calls if name == "prove_modular_divisibility")
    if selection_line >= solver_line:
        raise DiscoveryPortfolioValidationError("strategy is not selected before solver work")
    source_segment = ast.get_source_segment(SOURCE.read_text(encoding="utf-8"), fn) or ""
    required = (
        "degree > _MAX_INDUCTION_FIRST_DEGREE",
        'v, method = prove_by_residues(fn, m), "residue-exhaustion"',
        '"modulus-factoring" if len(v.detail.get("prime_powers", [m])) > 1',
    )
    if any(fragment not in source_segment for fragment in required):
        raise DiscoveryPortfolioValidationError("deterministic selection source drift")


def validate() -> None:
    _validate_contracts()
    _validate_source()


def main() -> int:
    try:
        validate()
    except (DiscoveryPortfolioValidationError, OSError, SyntaxError) as exc:
        print(f"discovery-portfolio: FAIL: {exc}", file=sys.stderr)
        return 1
    print("discovery-portfolio: PASS (degree<=3 induction/CRT; degree>=4 residues)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
