"""
Hardening — algebra & discrete (ROADMAP E6 [S]) — property-based theorems +
determinism + fuzz across Track E (groups, linear algebra III, graphs, number
theory II, combinatorics II).

The properties ARE the classic theorems: Lagrange, Euler-φ multiplicativity,
Σ_{d|n} φ(d) = n, Bell = Σ Stirling₂, the Catalan–binomial identity, and the
multiplicativity of permutation sign.
"""
import math

import hypothesis.strategies as st
import sympy
from hypothesis import assume, given, settings

from mathhead.compute import (
    bell_number,
    catalan_number,
    euler_totient,
    generated_group,
    mobius,
    necklace_count,
    permutation_compose,
    permutation_parity,
    pell_solution,
    qr_decomposition,
    stirling_number,
)

_CFG = settings(max_examples=40, deadline=None)


# ------------------------- number-theory theorems ------------------------- #
@_CFG
@given(st.integers(2, 60), st.integers(2, 60))
def test_euler_phi_is_multiplicative(m, n):
    # φ(m·n) = φ(m)·φ(n) whenever gcd(m, n) = 1
    assume(math.gcd(m, n) == 1)
    assert euler_totient(m * n).result == euler_totient(m).result * euler_totient(n).result


@_CFG
@given(st.integers(1, 150))
def test_phi_divisor_sum_equals_n(n):
    # Σ_{d | n} φ(d) = n
    total = sum(euler_totient(d).result for d in range(1, n + 1) if n % d == 0)
    assert total == n


@_CFG
@given(st.integers(1, 150))
def test_mobius_divisor_sum_is_indicator(n):
    # Σ_{d | n} μ(d) = 1 if n == 1 else 0
    total = sum(mobius(d).result for d in range(1, n + 1) if n % d == 0)
    assert total == (1 if n == 1 else 0)


@_CFG
@given(st.integers(2, 40))
def test_pell_solution_satisfies_equation(n):
    # if a fundamental solution exists, it really satisfies x² − n·y² = 1
    assume(not sympy.sqrt(n).is_integer)
    r = pell_solution(n)
    x, y = r.result["x"], r.result["y"]
    assert x * x - n * y * y == 1


# ------------------------- combinatorics theorems ------------------------- #
@_CFG
@given(st.integers(0, 10))
def test_bell_is_sum_of_stirling_second(n):
    # Bₙ = Σ_{k=0}^{n} S(n, k)  (second kind)
    assert bell_number(n).result == sum(stirling_number(n, k).result for k in range(n + 1))


@_CFG
@given(st.integers(0, 15))
def test_catalan_binomial_identity(n):
    # Cₙ = C(2n, n) / (n+1)  — cross-checked against stdlib math.comb (independent of SymPy)
    assert catalan_number(n).result == math.comb(2 * n, n) // (n + 1)


@_CFG
@given(st.integers(1, 8), st.integers(1, 4))
def test_necklace_count_is_a_positive_integer(n, colors):
    # Burnside always yields a whole number of necklaces
    r = necklace_count(n, colors)
    assert r.status == "ok" and isinstance(r.result, int) and r.result >= 1


# ---------------------------- group theorems ------------------------------ #
@_CFG
@given(st.integers(2, 6).flatmap(
    lambda m: st.tuples(st.permutations(list(range(m))), st.permutations(list(range(m))))))
def test_permutation_sign_is_multiplicative(pq):
    # sign(σ∘τ) = sign(σ)·sign(τ)  ⟺  parity adds mod 2
    p, q = [list(x) for x in pq]
    pp, qp = permutation_parity(p).result, permutation_parity(q).result
    comp = permutation_compose([p, q]).result["array_form"]
    expected = "even" if (pp == qp) else "odd"
    assert permutation_parity(comp).result == expected


@_CFG
@given(st.integers(3, 5).flatmap(
    lambda m: st.tuples(st.just(m),
                        st.lists(st.permutations(list(range(m))), min_size=1, max_size=2))))
def test_lagrange_generated_group_divides_factorial(data):
    # |generated subgroup of Sₘ| divides |Sₘ| = m!  (Lagrange's theorem)
    m, gens = data
    r = generated_group([list(g) for g in gens])
    assert r.status == "ok"
    assert math.factorial(m) % r.result["order"] == 0


# ------------------------ linear-algebra identity ------------------------- #
@_CFG
@given(st.lists(st.lists(st.integers(-4, 4), min_size=2, max_size=2), min_size=2, max_size=2))
def test_qr_reconstructs_matrix(m):
    A = sympy.Matrix(m)
    assume(A.rank() == 2)                       # QR needs full column rank
    r = qr_decomposition([[str(c) for c in row] for row in m])
    assert r.status == "ok"
    Q = sympy.Matrix([[sympy.sympify(c) for c in row] for row in r.result["Q"]])
    R = sympy.Matrix([[sympy.sympify(c) for c in row] for row in r.result["R"]])
    assert sympy.simplify(Q * R - A) == sympy.zeros(2, 2)


# ---------------------------- fuzz / determinism -------------------------- #
@_CFG
@given(st.integers(-50, 200))
def test_number_tools_never_crash(n):
    for fn in (euler_totient, mobius, catalan_number, bell_number):
        assert fn(n).status in {"ok", "error"}


def test_algebra_hardening_determinism():
    for _ in range(5):
        assert euler_totient(36).result == 12
        assert bell_number(6).result == 203
        assert generated_group([[1, 2, 0], [1, 0, 2]]).result["order"] == 6
