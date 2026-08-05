"""Discovery v2C2/M6 — Lean 4 export for external cross-sealing (pending external check)."""
from mathhead.discovery.lean_export import (
    _lean_poly,
    export_divides,
    export_identity,
    export_kernel_theorems,
)


def test_poly_rendering():
    assert _lean_poly((0, -1, 0, 1)) == "(-n) + n^3"
    assert _lean_poly((0, 2, 3, 1)) == "(2) * n + (3) * n^2 + n^3"


def test_divides_export_mirrors_the_residue_rule():
    src = export_divides("t1", 6, (0, -1, 0, 1))
    assert "∀ n : ℤ, (6 : ℤ) ∣" in src
    assert "∀ x : ZMod 6" in src and "by decide" in src       # residue exhaustion ≡ decide over ZMod m
    assert "ZMod.intCast_zmod_eq_zero_iff_dvd" in src         # the transport bridge to all of ℤ


def test_identity_export_uses_ring():
    src = export_identity("t2", "n^2 - 1", "(n - 1) * (n + 1)")
    assert src.strip().endswith("by intro n; ring")


def test_export_writes_file_with_honest_status(tmp_path):
    r = export_kernel_theorems(str(tmp_path / "K.lean"))
    text = (tmp_path / "K.lean").read_text()
    assert r.theorems >= 9 and r.status == "export_written_pending_external_check"
    assert "NOT yet run" in text and "lake build" in text      # the external step, stated in the file
    assert sum(1 for ln in text.splitlines() if ln.startswith("theorem ")) == r.theorems
    assert "Lean-verified" not in r.status                     # never claimed verified here


def test_export_is_deterministic(tmp_path):
    export_kernel_theorems(str(tmp_path / "a.lean"))
    export_kernel_theorems(str(tmp_path / "b.lean"))
    assert (tmp_path / "a.lean").read_text() == (tmp_path / "b.lean").read_text()
