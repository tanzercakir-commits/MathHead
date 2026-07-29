"""Discovery — CONSTRUCTIVE bijections proving the partition equidistributions (Euler, conjugation)."""
from mathhead.discovery.bijections import (
    certify_conjugation_bijection,
    certify_euler_bijection,
    certify_mahonian_bijection,
    certify_partition_bijections,
    foata,
    glaisher_distinct_to_odd,
    glaisher_odd_to_distinct,
)
from mathhead.discovery.partitions import (
    generate_partitions,
    into_distinct_parts,
    into_odd_parts,
)
from mathhead.discovery.permutations import (
    generate_permutations,
    inversions,
    major_index,
)


def test_glaisher_maps_odd_to_distinct_preserving_sum():
    for p in generate_partitions(9):
        if into_odd_parts(p):
            d = glaisher_odd_to_distinct(p)
            assert into_distinct_parts(d) and d.total == p.total


def test_glaisher_inverse_round_trips():
    for p in generate_partitions(10):
        if into_odd_parts(p):
            assert glaisher_distinct_to_odd(glaisher_odd_to_distinct(p)).parts == p.parts


def test_glaisher_known_values():
    from mathhead.discovery.partitions import Partition
    assert glaisher_odd_to_distinct(Partition((3, 3))).parts == (6,)           # 3 twice → 6
    assert glaisher_odd_to_distinct(Partition((1, 1, 1, 1, 1, 1))).parts == (4, 2)  # 1×6 → 4+2


def test_euler_bijection_certificate_verifies():
    c = certify_euler_bijection(18)
    assert c.verified and c.certainty == "constructive_bijection"
    assert "Glaisher" in c.detail


def test_conjugation_bijection_certificate_verifies():
    c = certify_conjugation_bijection(18)
    assert c.verified and c.certainty == "constructive_bijection"


def test_all_partition_bijections_certified():
    certs = certify_partition_bijections(12)
    assert len(certs) == 2 and all(c.verified for c in certs)
    # honest: a bounded constructive bijection, not a universal proof
    assert all(c.certainty == "constructive_bijection" for c in certs)


def test_foata_preserves_the_statistic_and_is_a_bijection():
    for n in range(1, 8):
        perms = generate_permutations(n)
        images = [foata(p).perm for p in perms]
        assert len(set(images)) == len(perms)                # bijection of S_n
        assert all(inversions(foata(p)) == major_index(p) for p in perms)   # inv(Φ)=maj


def test_mahonian_bijection_certificate_verifies():
    c = certify_mahonian_bijection(7)
    assert c.verified and c.certainty == "constructive_bijection"
    assert "Foata" in c.detail
