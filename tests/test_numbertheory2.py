"""
Number theory II (ROADMAP E4) — euler_totient / mobius / continued_fraction /
continued_fraction_sqrt / quadratic_residue / primitive_root / pell_solution.

Best-case (known values) + honesty (no primitive root / perfect-square Pell) +
worst-case (bad input) + determinism.
"""
from mathhead.compute import (
    continued_fraction,
    continued_fraction_sqrt,
    euler_totient,
    mobius,
    pell_solution,
    primitive_root,
    quadratic_residue,
)


# ---------------------------- euler_totient ------------------------------- #
def test_totient_composite():
    assert euler_totient(12).result == 4


def test_totient_prime():
    # φ(p) = p − 1
    assert euler_totient(13).result == 12


def test_totient_nonpositive_rejected():
    assert euler_totient(0).status == "error"


# ------------------------------- mobius ----------------------------------- #
def test_mobius_squarefree_odd_primes():
    assert mobius(30).result == -1        # 2·3·5 → (−1)³ = −1


def test_mobius_square_factor_is_zero():
    assert mobius(12).result == 0         # 2²·3 → 0


# --------------------------- continued_fraction --------------------------- #
def test_continued_fraction_rational():
    assert continued_fraction(415, 93).result == [4, 2, 6, 7]


def test_continued_fraction_zero_denominator_rejected():
    assert continued_fraction(1, 0).status == "error"


def test_continued_fraction_sqrt_periodic():
    r = continued_fraction_sqrt(23)
    assert r.result == {"a0": 4, "period": [1, 3, 1, 8]}


def test_continued_fraction_sqrt_perfect_square():
    r = continued_fraction_sqrt(16)
    assert r.result == {"a0": 4, "period": []}


# ---------------------------- quadratic_residue --------------------------- #
def test_quadratic_residue_true():
    r = quadratic_residue(2, 7)
    assert r.result["is_residue"] is True
    assert r.result["jacobi_symbol"] == 1


def test_quadratic_residue_false():
    r = quadratic_residue(3, 7)
    assert r.result["is_residue"] is False
    assert r.result["jacobi_symbol"] == -1


# ----------------------------- primitive_root ----------------------------- #
def test_primitive_root_prime():
    assert primitive_root(7).result == 3


def test_primitive_root_none_exists():
    # 8 has no primitive root
    r = primitive_root(8)
    assert r.status == "ok"
    assert r.result is None                # honest: none, not fabricated


# ------------------------------ pell_solution ----------------------------- #
def test_pell_fundamental_solution():
    assert pell_solution(2).result == {"x": 3, "y": 2}


def test_pell_larger():
    # the famous n=13 case
    assert pell_solution(13).result == {"x": 649, "y": 180}


def test_pell_perfect_square_is_trivial():
    r = pell_solution(9)
    assert r.status == "ok"
    assert r.result is None                # no non-trivial solution (honest)


# ------------------------------ determinism ------------------------------- #
def test_numbertheory2_determinism():
    for _ in range(5):
        assert euler_totient(12).result == 4
        assert continued_fraction_sqrt(23).result == {"a0": 4, "period": [1, 3, 1, 8]}
        assert pell_solution(13).result == {"x": 649, "y": 180}
