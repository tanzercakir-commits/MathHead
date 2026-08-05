/-
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


-- MathHead kernel: Divides(2, (0, 1, 1)) — RESIDUE exhaustion ≡ decide over ZMod 2
theorem mathhead_divides_1_n_mul_n_plus_1 : ∀ n : ℤ, (2 : ℤ) ∣ (n + n^2) := by
  intro n
  have key : ∀ x : ZMod 2, (x + x^2) = 0 := by decide
  have h : (((n + n^2) : ℤ) : ZMod 2) = 0 := by push_cast; simpa using key ((n : ZMod 2))
  exact (ZMod.intCast_zmod_eq_zero_iff_dvd _ 2).mp h

-- MathHead kernel: Divides(6, (0, 2, 3, 1)) — RESIDUE exhaustion ≡ decide over ZMod 6
theorem mathhead_divides_2_n_mul_n_plus_1_mul_n_plus_2 : ∀ n : ℤ, (6 : ℤ) ∣ ((2) * n + (3) * n^2 + n^3) := by
  intro n
  have key : ∀ x : ZMod 6, ((2) * x + (3) * x^2 + x^3) = 0 := by decide
  have h : ((((2) * n + (3) * n^2 + n^3) : ℤ) : ZMod 6) = 0 := by push_cast; simpa using key ((n : ZMod 6))
  exact (ZMod.intCast_zmod_eq_zero_iff_dvd _ 6).mp h

-- MathHead kernel: Divides(24, (0, 6, 11, 6, 1)) — RESIDUE exhaustion ≡ decide over ZMod 24
theorem mathhead_divides_3_n_mul_n_plus_1_mul_n_plus_2_mul_n_plus_3 : ∀ n : ℤ, (24 : ℤ) ∣ ((6) * n + (11) * n^2 + (6) * n^3 + n^4) := by
  intro n
  have key : ∀ x : ZMod 24, ((6) * x + (11) * x^2 + (6) * x^3 + x^4) = 0 := by decide
  have h : ((((6) * n + (11) * n^2 + (6) * n^3 + n^4) : ℤ) : ZMod 24) = 0 := by push_cast; simpa using key ((n : ZMod 24))
  exact (ZMod.intCast_zmod_eq_zero_iff_dvd _ 24).mp h

-- MathHead kernel: Divides(2, (0, -1, 1)) — RESIDUE exhaustion ≡ decide over ZMod 2
theorem mathhead_divides_4_n_pow_2_minus_n : ∀ n : ℤ, (2 : ℤ) ∣ ((-n) + n^2) := by
  intro n
  have key : ∀ x : ZMod 2, ((-x) + x^2) = 0 := by decide
  have h : ((((-n) + n^2) : ℤ) : ZMod 2) = 0 := by push_cast; simpa using key ((n : ZMod 2))
  exact (ZMod.intCast_zmod_eq_zero_iff_dvd _ 2).mp h

-- MathHead kernel: Divides(6, (0, -1, 0, 1)) — RESIDUE exhaustion ≡ decide over ZMod 6
theorem mathhead_divides_5_n_pow_3_minus_n : ∀ n : ℤ, (6 : ℤ) ∣ ((-n) + n^3) := by
  intro n
  have key : ∀ x : ZMod 6, ((-x) + x^3) = 0 := by decide
  have h : ((((-n) + n^3) : ℤ) : ZMod 6) = 0 := by push_cast; simpa using key ((n : ZMod 6))
  exact (ZMod.intCast_zmod_eq_zero_iff_dvd _ 6).mp h

-- MathHead kernel: Divides(30, (0, -1, 0, 0, 0, 1)) — RESIDUE exhaustion ≡ decide over ZMod 30
theorem mathhead_divides_6_n_pow_5_minus_n : ∀ n : ℤ, (30 : ℤ) ∣ ((-n) + n^5) := by
  intro n
  have key : ∀ x : ZMod 30, ((-x) + x^5) = 0 := by decide
  have h : ((((-n) + n^5) : ℤ) : ZMod 30) = 0 := by push_cast; simpa using key ((n : ZMod 30))
  exact (ZMod.intCast_zmod_eq_zero_iff_dvd _ 30).mp h

-- MathHead kernel: Divides(42, (0, -1, 0, 0, 0, 0, 0, 1)) — RESIDUE exhaustion ≡ decide over ZMod 42
theorem mathhead_divides_7_n_pow_7_minus_n : ∀ n : ℤ, (42 : ℤ) ∣ ((-n) + n^7) := by
  intro n
  have key : ∀ x : ZMod 42, ((-x) + x^7) = 0 := by decide
  have h : ((((-n) + n^7) : ℤ) : ZMod 42) = 0 := by push_cast; simpa using key ((n : ZMod 42))
  exact (ZMod.intCast_zmod_eq_zero_iff_dvd _ 42).mp h

-- MathHead kernel: PolyIdentity — exact coefficient equality ≡ ring
theorem mathhead_identity_8 : ∀ n : ℤ, (n^2 - 1 : ℤ) = ((n - 1) * (n + 1)) := by intro n; ring

-- MathHead kernel: PolyIdentity — exact coefficient equality ≡ ring
theorem mathhead_identity_9 : ∀ n : ℤ, (n^3 - n : ℤ) = (n * (n - 1) * (n + 1)) := by intro n; ring
