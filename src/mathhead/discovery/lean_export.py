"""
mathhead.discovery.lean_export — export kernel theorems to Lean 4 for external cross-sealing (v2C2/M6).

The deepest trust upgrade available to the kernel: have an INDEPENDENT proof kernel (Lean 4's, with
mathlib) re-check our theorems. The mathematical correspondence is exact and beautiful:

    our RESIDUE rule  (exhaust residues 0..m−1 ⟹ m | p(n) ∀n)
        ≡  Lean's `decide` over `ZMod m`  (a FINITE type — Lean's kernel performs the same finite
           exhaustion, then `ZMod.intCast_zmod_eq_zero_iff_dvd` transports it to ∀ n : ℤ)
    our CRT composition — not even needed on the Lean side: `decide` over `ZMod m` handles composite m
        directly (the finite check at m subsumes the prime-power split)
    our PolyIdentity rule (exact coefficient equality)  ≡  Lean's `ring`

HONEST STATUS — the whole point: this module WRITES the Lean file; it cannot COMPILE it here (Lean +
mathlib is a multi-GB toolchain). Every export is stamped `export_written_pending_external_check`, and
the file header says exactly what a human/CI must run. Tactic glue (mathlib lemma names drift across
versions) may need touch-up at compile time; the invariant core — `decide` over `ZMod m` — is stable.
We NEVER report a theorem as Lean-verified until that external run happens.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass

from mathhead.kernel.checkers import check_proof_term
from mathhead.kernel.proof_terms import polynomial_identity, residue
from mathhead.parsing import parse_expression
from mathhead.proof_assistant.export import build_lean_export

_HEADER = '''/-
  MathHead legacy combined Lean export — non-authoritative compatibility view.

  TO VERIFY (external step, NOT yet run):
    Use mathhead.proof_assistant to create one canonical content-addressed
    request per theorem, then run the pinned MH-C-LEAN-VERIFICATION-001 job.
    `lake build` on this combined convenience file is not an authority source.

  Each theorem block below is derived by the canonical exporter from a freshly
  checked proof term. This file deliberately omits request and provenance bytes.
  Status of every theorem here: export_written_pending_external_check.
-/
import Mathlib

set_option autoImplicit false
set_option maxHeartbeats 1000000
set_option maxRecDepth 100000

namespace MathHead.LegacyExport

'''


def _lean_poly(coeffs: tuple, var: str = "n") -> str:
    """Integer coefficient tuple (low→high) → a Lean expression like `n^3 - n`."""
    terms = []
    for k, c in enumerate(coeffs):
        c = int(c)
        if c == 0:
            continue
        if k == 0:
            terms.append(f"({c} : ℤ)")
        else:
            mono = var if k == 1 else f"{var}^{k}"
            terms.append(mono if c == 1 else f"(-{mono})" if c == -1 else f"({c}) * {mono}")
    return " + ".join(terms) if terms else "(0 : ℤ)"


def _legacy_name(name: str) -> str:
    """Accept one inert ASCII compatibility identifier, never source text."""
    if (
        type(name) is not str
        or not 0 < len(name) <= 128
        or not name.isascii()
        or not (name[0].isalpha() or name[0] == "_")
        or any(not (character.isalnum() or character == "_") for character in name)
        or name in {"axiom", "def", "end", "namespace", "opaque", "partial", "theorem", "unsafe"}
    ):
        raise ValueError("legacy theorem name is not one inert ASCII identifier")
    return name


def export_divides(name: str, m: int, poly: tuple) -> str:
    """Compatibility text derived from one canonical written-only export."""
    name = _legacy_name(name)
    term = residue(int(m), tuple(int(value) for value in poly))
    exported = build_lean_export(term, check_proof_term(term))
    return _theorem_block(exported).replace(exported.theorem_name, name, 1)


def _legacy_polynomial(expression: str) -> tuple[int, ...]:
    """Parse the tiny historical integer-polynomial expression surface."""
    if type(expression) is not str or len(expression) > 4096:
        raise ValueError("legacy polynomial expression is invalid")
    tree = parse_expression(expression.replace("^", "**"))

    def add(left: tuple[int, ...], right: tuple[int, ...], sign: int = 1) -> tuple[int, ...]:
        size = max(len(left), len(right))
        values = [0] * size
        for index in range(size):
            values[index] = (
                (left[index] if index < len(left) else 0)
                + sign * (right[index] if index < len(right) else 0)
            )
        while len(values) > 1 and values[-1] == 0:
            values.pop()
        return tuple(values)

    def multiply(left: tuple[int, ...], right: tuple[int, ...]) -> tuple[int, ...]:
        if len(left) + len(right) > 66:
            raise ValueError("legacy polynomial degree exceeds the adapter budget")
        values = [0] * (len(left) + len(right) - 1)
        for i, a in enumerate(left):
            for j, b in enumerate(right):
                values[i + j] += a * b
        return tuple(values)

    def visit(node: ast.AST) -> tuple[int, ...]:
        if isinstance(node, ast.Name) and node.id == "n":
            return (0, 1)
        if isinstance(node, ast.Constant) and type(node.value) is int:
            return (node.value,)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return tuple(-value for value in visit(node.operand))
        if isinstance(node, ast.BinOp):
            if isinstance(node.op, ast.Add):
                return add(visit(node.left), visit(node.right))
            if isinstance(node.op, ast.Sub):
                return add(visit(node.left), visit(node.right), -1)
            if isinstance(node.op, ast.Mult):
                return multiply(visit(node.left), visit(node.right))
            if (
                isinstance(node.op, ast.Pow)
                and isinstance(node.right, ast.Constant)
                and type(node.right.value) is int
                and 0 <= node.right.value <= 32
            ):
                base = visit(node.left)
                result = (1,)
                for _ in range(node.right.value):
                    result = multiply(result, base)
                return result
        raise ValueError("legacy polynomial expression uses unsupported syntax")

    return visit(tree.body)


def export_identity(name: str, lhs: str, rhs: str) -> str:
    """Preserve legacy text only after the canonical checker accepts the identity."""
    name = _legacy_name(name)
    left = _legacy_polynomial(lhs)
    right = _legacy_polynomial(rhs)
    term = polynomial_identity(left, right)
    build_lean_export(term, check_proof_term(term))
    return (
        "-- Non-authoritative compatibility rendering of a checked identity\n"
        f"theorem {name} : ∀ n : ℤ, ({_lean_poly(left)}) = "
        f"({_lean_poly(right)}) := by intro n; ring\n"
    )


def _theorem_block(export: object) -> str:
    source = export.artifacts[1].decode("utf-8")
    start = source.index("theorem ")
    end = source.index("\n\nend MathHead.Generated")
    return source[start:end] + "\n"


@dataclass
class LeanExport:
    path: str
    theorems: int
    status: str = "export_written_pending_external_check"
    note: str = ("Lean+mathlib cannot run in this container; a human/CI must `lake build`. "
                 "No theorem is claimed Lean-verified until that succeeds.")


def export_kernel_theorems(path: str = "docs/discovery/lean/MathheadKernel.lean") -> LeanExport:
    """Write a compatibility view; canonical per-theorem requests remain separate."""
    from pathlib import Path

    from .arithmetic import run_arithmetic_discovery
    from .kernel import poly_from_sympy
    blocks = [_HEADER]
    count = 0
    for f in run_arithmetic_discovery():
        if f.verdict != "proved":
            continue
        count += 1
        term = residue(f.modulus, poly_from_sympy(f.expression))
        blocks.append(_theorem_block(build_lean_export(term, check_proof_term(term))))
    for coefficients in ((-1, 0, 1), (0, -1, 0, 1)):
        count += 1
        term = polynomial_identity(coefficients, coefficients)
        blocks.append(_theorem_block(build_lean_export(term, check_proof_term(term))))
    blocks.append("\nend MathHead.LegacyExport\n")
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(blocks), encoding="utf-8")
    return LeanExport(str(out), count)
