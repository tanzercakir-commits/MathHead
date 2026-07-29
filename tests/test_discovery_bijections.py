"""Discovery — CONSTRUCTIVE bijections proving the partition equidistributions (Euler, conjugation)."""
from mathhead.discovery.bijections import (
    certify_conjugation_bijection,
    certify_euler_bijection,
    certify_partition_bijections,
    glaisher_distinct_to_odd,
    glaisher_odd_to_distinct,
)
from mathhead.discovery.partitions import (
    generate_partitions,
    into_distinct_parts,
    into_odd_parts,
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
