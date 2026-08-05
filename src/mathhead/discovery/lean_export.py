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

from dataclasses import dataclass

_HEADER = '''/-
  MathHead kernel theorems — Lean 4 export (v2C2/M6 cross-seal).

  TO VERIFY (external step, NOT yet run):
    lake new mathhead_check math && cd mathhead_check
    -- put this file in MathheadCheck/, add to imports, then:
    lake build          -- success = Lean's kernel re-checked every theorem below

  Correspondence: MathHead's RESIDUE rule (finite residue exhaustion) is Lean's `decide` over the
  FINITE type `ZMod m`; the bridge lemma transports it to all of ℤ. Tactic glue may need adjustment
  across mathlib versions; `decide` over `ZMod m` is the version-stable mathematical core.
  Status of every theorem here: export_written_pending_external_check.
-/
import Mathlib.Data.ZMod.Basic
import Mathlib.Tactic

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


def export_divides(name: str, m: int, poly: tuple) -> str:
    """Lean theorem for `m | p(n) ∀ n : ℤ` via decide-over-ZMod — mirrors the RESIDUE proof exactly."""
    p = _lean_poly(poly)
    return (
        f"-- MathHead kernel: Divides({m}, {poly}) — RESIDUE exhaustion ≡ decide over ZMod {m}\n"
        f"theorem {name} : ∀ n : ℤ, ({m} : ℤ) ∣ ({p}) := by\n"
        f"  intro n\n"
        f"  have key : ∀ x : ZMod {m}, ({_lean_poly(poly, 'x').replace('ℤ', f'ZMod {m}')}) = 0 := by decide\n"
        f"  have h : ((({p}) : ℤ) : ZMod {m}) = 0 := by push_cast; simpa using key ((n : ZMod {m}))\n"
        f"  exact (ZMod.intCast_zmod_eq_zero_iff_dvd _ {m}).mp h\n")


def export_identity(name: str, lhs: str, rhs: str) -> str:
    """Lean theorem for a polynomial identity — the kernel's PolyIdentity ≡ `ring`."""
    return (f"-- MathHead kernel: PolyIdentity — exact coefficient equality ≡ ring\n"
            f"theorem {name} : ∀ n : ℤ, ({lhs} : ℤ) = ({rhs}) := by intro n; ring\n")


@dataclass
class LeanExport:
    path: str
    theorems: int
    status: str = "export_written_pending_external_check"
    note: str = ("Lean+mathlib cannot run in this container; a human/CI must `lake build`. "
                 "No theorem is claimed Lean-verified until that succeeds.")


def export_kernel_theorems(path: str = "docs/discovery/lean/MathheadKernel.lean") -> LeanExport:
    """Export the kernel's proved Divides facts + representative identities to one Lean file."""
    from pathlib import Path

    from .arithmetic import run_arithmetic_discovery
    from .kernel import poly_from_sympy
    blocks = [_HEADER]
    count = 0
    for f in run_arithmetic_discovery():
        if f.verdict != "proved":
            continue
        count += 1
        safe = f.expression.replace("**", "_pow_").replace("*", "_mul_").replace(" ", "") \
                           .replace("+", "_plus_").replace("-", "_minus_").replace("(", "").replace(")", "")
        blocks.append(export_divides(f"mathhead_divides_{count}_{safe[:40]}",
                                     f.modulus, poly_from_sympy(f.expression)))
    for lhs, rhs in (("n^2 - 1", "(n - 1) * (n + 1)"), ("n^3 - n", "n * (n - 1) * (n + 1)")):
        count += 1
        blocks.append(export_identity(f"mathhead_identity_{count}", lhs, rhs))
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(blocks), encoding="utf-8")
    return LeanExport(str(out), count)
