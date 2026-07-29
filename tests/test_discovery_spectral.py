"""Discovery — spectral invariants + the graph domain's first bridge to MathHead."""
from mathhead.discovery import (
    discover_spectral_laws,
    generate_graphs,
    num_distinct_eigenvalues,
    spectrum,
    spectrum_confirms_moments,
)
from mathhead.discovery.invariants import spectral_moment_2, spectral_moment_3


def _complete(n: int):
    return generate_graphs(n)[-1]      # the last iso-class on n vertices is K_n (most edges)


def test_mathhead_spectrum_is_correct():
    # K4 adjacency spectrum: 3 (once) and -1 (three times)
    spec = {str(v): m for v, m in spectrum(_complete(4))}
    assert spec == {"3": 1, "-1": 3}


def test_discovers_spectral_identities_from_data():
    laws = {law.expression for law in discover_spectral_laws(
        [g for n in range(6) for g in generate_graphs(n)])}
    assert "2*num_edges = spectral_moment_2" in laws        # Σλ² = 2|E|
    assert "6*num_triangles = spectral_moment_3" in laws     # Σλ³ = 6·#triangles


def test_mathhead_independently_confirms_the_moments():
    # MathHead's actual eigenvalues reproduce the (matmul) moments — three ways agree.
    for n in range(6):
        for g in generate_graphs(n):
            assert spectrum_confirms_moments(g)


def test_moments_equal_the_known_structural_quantities():
    for n in range(6):
        for g in generate_graphs(n):
            from mathhead.discovery.invariants import num_edges, num_triangles
            assert spectral_moment_2(g) == 2 * num_edges(g)
            assert spectral_moment_3(g) == 6 * num_triangles(g)


def test_num_distinct_eigenvalues():
    assert num_distinct_eigenvalues(_complete(3)) == 2      # K_n has 2 distinct: (n-1) and -1
    assert num_distinct_eigenvalues(_complete(4)) == 2
