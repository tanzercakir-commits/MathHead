"""Discovery AA4 — connect a discovered algorithm to the proof that certifies it (S/M bridge)."""
import pytest

from mathhead.discovery.algorithm_proof import (
    bridge_modular_algorithm,
    link_algorithm_to_proof,
)
from mathhead.discovery.kernel import poly_from_sympy
from mathhead.discovery.objects import Graph

_N3 = poly_from_sympy("n**3 - n")
_C4 = Graph(4, [(0, 1), (1, 2), (2, 3), (0, 3)])
_K3 = Graph(3, [(0, 1), (1, 2), (0, 2)])


def test_modular_algorithm_links_to_a_universal_kernel_proof():
    ap = link_algorithm_to_proof("modular", m=6, poly=_N3)
    assert ap.modality == "kernel" and ap.certainty == "kernel_verified" and ap.verified
    assert ap.evidence["proof_hash"] and "RESIDUE(m=2)" in ap.evidence["axioms"]


def test_false_modular_claim_yields_no_proof_not_a_fake_one():
    ap = bridge_modular_algorithm(5, _N3)                 # 5 ∤ n³−n
    assert not ap.verified and "proof_hash" not in ap.evidence
    assert ap.certainty == "kernel_verified"             # the modality is still kernel; it just didn't check


def test_greedy_coloring_links_to_a_bounded_certificate_not_a_kernel_proof():
    ap = link_algorithm_to_proof("coloring", g=_C4)
    assert ap.modality == "certificate" and ap.certainty == "constructive_bounded" and ap.verified
    assert ap.certainty != "kernel_verified"             # honest: witnessed, NOT a universal ∀G proof
    assert ap.evidence["colors_used"] == 2


def test_max_clique_links_to_a_bounded_certificate():
    ap = link_algorithm_to_proof("clique", g=_K3)
    assert ap.modality == "certificate" and ap.certainty == "constructive_bounded"
    assert ap.evidence["omega"] == 3


def test_the_two_modalities_have_honestly_different_strengths():
    kernel = link_algorithm_to_proof("modular", m=6, poly=_N3)
    cert = link_algorithm_to_proof("coloring", g=_C4)
    # a kernel link is universal; a certificate link is only witnessed — never conflated
    assert kernel.certainty == "kernel_verified" and cert.certainty == "constructive_bounded"
    assert kernel.modality != cert.modality


def test_unknown_algorithm_kind_is_rejected():
    with pytest.raises(ValueError, match="unknown algorithm kind"):
        link_algorithm_to_proof("teleport", g=_C4)


def test_bridge_is_deterministic():
    assert bridge_modular_algorithm(6, _N3) == bridge_modular_algorithm(6, _N3)
