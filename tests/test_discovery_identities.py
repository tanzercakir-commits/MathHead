"""Discovery — factorization identities, kernel-verified, EXPLAINING the modular divisibilities."""
from mathhead.discovery.identities import (
    discover_factorization,
    run_identity_discovery,
)


def _by_expr():
    return {f.expression: f for f in run_identity_discovery()}


def test_factorizations_are_kernel_verified():
    for f in run_identity_discovery():
        assert f.kernel_verified and f.axioms == ("POLY_IDENTITY",)
        assert len(f.proof_hash) == 16


def test_consecutive_run_explains_divisibility():
    f = _by_expr()
    # n³−n = n(n−1)(n+1): three consecutive integers ⇒ divisible by 3! = 6 (explains 6 | n³−n)
    assert f["n**3 - n"].consecutive_run == 3
    assert f["n**3 - n"].divisibility_explained == 6
    # n²−n = n(n−1): two consecutive ⇒ divisible by 2
    assert f["n**2 - n"].consecutive_run == 2
    assert f["n**2 - n"].divisibility_explained == 2


def test_non_consecutive_factorizations_explain_nothing():
    f = _by_expr()
    # n²−1 = (n−1)(n+1): offsets −1, +1 are NOT consecutive (gap 2)
    assert f["n**2 - 1"].consecutive_run == 0
    assert f["n**2 - 4"].consecutive_run == 0


def test_factored_form_matches_expansion():
    import sympy
    for f in run_identity_discovery():
        assert sympy.expand(sympy.sympify(f.factored)) == sympy.expand(sympy.sympify(f.expression))


def test_discovery_is_deterministic():
    a = [(f.expression, f.factored, f.divisibility_explained) for f in run_identity_discovery()]
    b = [(f.expression, f.factored, f.divisibility_explained) for f in run_identity_discovery()]
    assert a == b


def test_single_factorization_helper():
    f = discover_factorization("n**3 - n")
    assert f.factored.replace(" ", "") in ("n*(n-1)*(n+1)", "(n-1)*n*(n+1)")
    assert f.kernel_verified and f.divisibility_explained == 6
