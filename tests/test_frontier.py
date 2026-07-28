"""
Track B tohumu — problem → SAT indirgeme.

En değerli test: motorun ÜRETTİĞİ çözümü bağımsız doğrulamak (boyama gerçekten
tek renkli üçlü içermiyor mu) ve bir imkânsızlığı ispatladığını görmek.
"""
from mathhead.frontier import (
    boolean_pythagorean_coloring,
    pigeonhole,
    pythagorean_triples,
)


def test_pythagorean_triples_enumeration():
    assert (3, 4, 5) in pythagorean_triples(5)
    assert (6, 8, 10) in pythagorean_triples(10)
    assert pythagorean_triples(4) == []  # 5'ten küçük üçlü yok


def test_small_set_is_colorable():
    r = boolean_pythagorean_coloring(20)
    assert r.status == "sat"
    assert r.reason_code == "COLORING_FOUND"


def test_produced_coloring_has_no_monochromatic_triple():
    # Motorun döndürdüğü boyamayı BAĞIMSIZ doğrula (çözüm gerçekten geçerli mi).
    r = boolean_pythagorean_coloring(30)
    assert r.status == "sat"
    coloring = r.witness["coloring"]
    for a, b, c in pythagorean_triples(30):
        assert len({coloring[a], coloring[b], coloring[c]}) == 2  # tek renkli DEĞİL


def test_pigeonhole_is_proven_impossible():
    r = pigeonhole(4)  # 5 güvercin, 4 kutu
    assert r.status == "unsat"
    assert r.reason_code == "PROVEN_IMPOSSIBLE"


def test_guardrail_rejects_out_of_range():
    assert boolean_pythagorean_coloring(10**6).status == "error"
    assert pigeonhole(999).status == "error"
