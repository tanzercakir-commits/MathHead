"""
Track B seed — problem → SAT reduction.

Most valuable test: independently verifying the solution PRODUCED by the engine
(does the coloring really contain no monochromatic triple) and seeing that it
proves an impossibility.
"""
from mathhead.frontier import (
    arithmetic_progressions,
    boolean_pythagorean_coloring,
    graph_coloring,
    pigeonhole,
    pythagorean_triples,
    schur_number_coloring,
    subset_sum,
    van_der_waerden_coloring,
)


def test_pythagorean_triples_enumeration():
    assert (3, 4, 5) in pythagorean_triples(5)
    assert (6, 8, 10) in pythagorean_triples(10)
    assert pythagorean_triples(4) == []  # no triple below 5


def test_small_set_is_colorable():
    r = boolean_pythagorean_coloring(20)
    assert r.status == "sat"
    assert r.reason_code == "COLORING_FOUND"


def test_produced_coloring_has_no_monochromatic_triple():
    # INDEPENDENTLY verify the coloring the engine returned (is the solution really valid).
    r = boolean_pythagorean_coloring(30)
    assert r.status == "sat"
    coloring = r.witness["coloring"]
    for a, b, c in pythagorean_triples(30):
        assert len({coloring[a], coloring[b], coloring[c]}) == 2  # NOT monochromatic


def test_pigeonhole_is_proven_impossible():
    r = pigeonhole(4)  # 5 pigeons, 4 boxes
    assert r.status == "unsat"
    assert r.reason_code == "PROVEN_IMPOSSIBLE"


def test_guardrail_rejects_out_of_range():
    assert boolean_pythagorean_coloring(10**6).status == "error"
    assert pigeonhole(999).status == "error"


# --------------------- van der Waerden (W(colors,k)) ---------------------- #
def test_arithmetic_progressions_enumeration():
    assert (1, 2, 3) in arithmetic_progressions(3, 3)
    assert arithmetic_progressions(2, 3) == []  # a 3-AP needs >=3 elements


def test_vdw_w23_boundary():
    # W(2,3) = 9: n=8 colorable, n=9 impossible (reproduces the known value)
    assert van_der_waerden_coloring(8, 3).status == "sat"
    assert van_der_waerden_coloring(9, 3).status == "unsat"


def test_vdw_w24_is_proven_unsat():
    # W(2,4) = 35: {1..35} cannot be 2-colored without a 4-AP (real impossibility proof)
    assert van_der_waerden_coloring(35, 4).status == "unsat"


def test_vdw_produced_coloring_is_valid():
    r = van_der_waerden_coloring(34, 4)  # n=34 < W(2,4)=35 -> colorable
    assert r.status == "sat"
    coloring = r.witness["coloring"]
    for ap in arithmetic_progressions(34, 4):
        assert len({coloring[i] for i in ap}) == 2  # triple/sequence NOT monochromatic


def test_vdw_guardrail():
    assert van_der_waerden_coloring(10, 1).status == "error"       # k<2
    assert van_der_waerden_coloring(10**6, 3).status == "error"    # n too large


# --------------------------- Schur numbers S(r) -------------------------- #
def test_schur_s2_boundary():
    # S(2) = 4: {1..4} splits into 2 sum-free colors; {1..5} does not
    assert schur_number_coloring(4, 2).status == "sat"
    assert schur_number_coloring(5, 2).status == "unsat"


def test_schur_s3_boundary():
    # S(3) = 13: {1..13} splits into 3 sum-free colors; {1..14} does not (impossibility proof)
    assert schur_number_coloring(13, 3).status == "sat"
    assert schur_number_coloring(14, 3).status == "unsat"


def test_schur_produced_coloring_is_sum_free():
    # INDEPENDENTLY verify the partition the engine returned: no color class has x+y=z
    r = schur_number_coloring(13, 3)
    assert r.status == "sat"
    col = r.witness["coloring"]
    for x in range(1, 14):
        for y in range(x, 14):
            z = x + y
            if z <= 13:
                assert not (col[x] == col[y] == col[z])


def test_schur_guardrail():
    assert schur_number_coloring(10, 1).status == "error"      # colors<2
    assert schur_number_coloring(9999, 3).status == "error"    # n too large


def test_symmetry_break_preserves_result():
    # Symmetry breaking is an OPTIMIZATION; must NOT change the sat/unsat result.
    assert schur_number_coloring(13, 3, symmetry_break=True).status == "sat"
    assert schur_number_coloring(14, 3, symmetry_break=True).status == "unsat"
    assert van_der_waerden_coloring(35, 4, symmetry_break=True).status == "unsat"


# --------- Phase 10: new reductions + verifiable certificate ---------- #
def test_graph_coloring_triangle_3colorable():
    # Triangle (K3) is 3-colorable; the witness must be INDEPENDENTLY verified
    r = graph_coloring([[1, 2], [2, 3], [1, 3]], 3)
    assert r.status == "sat"
    assert r.reason_code == "COLORING_FOUND"
    assert r.meta.get("verified") is True
    # let the test itself also independently check the certificate
    col = r.witness["coloring"]
    assert all(col[u] != col[v] for u, v in ([1, 2], [2, 3], [1, 3]))


def test_graph_coloring_triangle_not_2colorable():
    # K3 CANNOT be 2-colored (odd cycle)
    r = graph_coloring([[1, 2], [2, 3], [1, 3]], 2)
    assert r.status == "unsat"
    assert r.reason_code == "NO_COLORING"


def test_graph_coloring_k4_needs_4():
    # K4 cannot be 3-colored (chromatic number 4)
    assert graph_coloring([[1, 2], [1, 3], [1, 4], [2, 3], [2, 4], [3, 4]], 3).status == "unsat"


def test_graph_coloring_bad_edge_rejected():
    assert graph_coloring([[1, 2, 3]], 2).status == "error"


def test_subset_sum_found_and_verified():
    r = subset_sum([3, 34, 4, 12, 5, 2], 9)
    assert r.status == "sat"
    assert r.meta.get("verified") is True
    assert sum(r.witness["subset"]) == 9      # independently verify the certificate


def test_subset_sum_none():
    # 8 is unreachable with 1,2,4 (max 7)
    assert subset_sum([1, 2, 4], 8).status == "unsat"


def test_subset_sum_empty_rejected():
    assert subset_sum([], 5).status == "error"


def test_trackB_determinism():
    for _ in range(3):
        assert graph_coloring([[1, 2], [2, 3], [1, 3]], 2).status == "unsat"
        assert subset_sum([3, 4, 2], 9).status == "sat"
