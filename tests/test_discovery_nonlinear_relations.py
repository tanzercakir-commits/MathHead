"""Discovery O2 (richer) — non-linear (degree-2) relation discovery."""
from mathhead.discovery.families import complete
from mathhead.discovery.generate import generate_graphs
from mathhead.discovery.invariants import evaluate
from mathhead.discovery.nonlinear_relations import (
    _is_product,
    discover_polynomial_laws,
)

_KN = [complete(n) for n in range(2, 9)]           # K_2 .. K_8
_ALL = [g for n in range(1, 6) for g in generate_graphs(n)]


def _feature_value(feature: str, obj) -> int:
    """Evaluate a feature name ('a', 'a*b', 'a^2') on an object."""
    if "^2" in feature:
        v = evaluate(obj, feature.replace("^2", ""))
        return v * v
    out = 1
    for nm in feature.split("*"):
        out *= evaluate(obj, nm)
    return out


def _law_holds_exactly(law, objs) -> bool:
    return all(sum(c * _feature_value(f, o) for f, c in law.coeffs.items()) + law.const == 0
               for o in objs)


def test_rediscovers_the_quadratic_edge_law_on_complete_graphs():
    laws = discover_polynomial_laws(_KN)
    # 2*num_edges = num_vertices^2 - num_vertices  (i.e. C(n,2) edges), rendered with the square term
    assert any("num_vertices^2" in law.expression and "num_edges" in law.expression for law in laws)


def test_every_returned_law_is_nonlinear_and_holds_exactly():
    laws = discover_polynomial_laws(_KN)
    assert laws
    for law in laws:
        assert any(_is_product(f) for f in law.coeffs)      # genuinely degree-2
        assert law.status == "empirical"                     # honest: sample-true conjecture
        assert _law_holds_exactly(law, _KN)                  # exact over the sample


def test_reducible_handshake_times_invariant_laws_are_filtered_out():
    # over the rich all-graphs sample the only degree-2 laws are consequences of Handshake; the
    # (Handshake × invariant) reducibles must be dropped, leaving no common-invariant-factor law
    laws = discover_polynomial_laws(_ALL)
    for law in laws:
        assert _law_holds_exactly(law, _ALL)
        common = set.intersection(*[set(f.replace("^2", "").split("*")) for f in law.coeffs])
        assert not common                                    # no single invariant divides every term


def test_constant_invariants_are_excluded_from_features():
    # num_components is constant (1) on complete graphs → must not appear in any mined law
    laws = discover_polynomial_laws(_KN)
    assert all("num_components" not in f for law in laws for f in law.coeffs)


def test_empty_sample_returns_no_laws():
    assert discover_polynomial_laws([]) == []


def test_discovery_is_deterministic():
    a = discover_polynomial_laws(_KN)
    b = discover_polynomial_laws(_KN)
    assert [law.expression for law in a] == [law.expression for law in b]
