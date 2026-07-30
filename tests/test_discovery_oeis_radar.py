"""Discovery v2A0/A1/A2 — natural-family sequence extraction + the OEIS radar."""
from mathhead.discovery.oeis_radar import (
    LOCAL_CORPUS,
    NaturalSequence,
    extract_natural_sequences,
    match,
    radar,
)


def test_engine_computed_sequences_match_their_pinned_oeis_prefixes():
    rep = radar()
    matched = {anum for _seq, anum in rep.matched}
    # every classic the engine generates lands on its OEIS pin — computed, not hardcoded
    for anum in ("A000088", "A001349", "A000142", "A000166", "A000085",
                 "A000041", "A000009", "A000110", "A011782"):
        assert anum in matched


def test_derangements_and_involutions_are_computed_correctly():
    seqs = {s.name: s.terms for s in extract_natural_sequences()}
    assert seqs["derangements"][:7] == (1, 0, 1, 2, 9, 44, 265)
    assert seqs["involutions"][:7] == (1, 1, 2, 4, 10, 26, 76)


def test_refined_families_surface_as_pending_external_lookup():
    rep = radar()
    pending = {s.name for s in rep.pending}
    assert pending == {"triangle_free_graphs", "chromatic_3_graphs"}   # not in the local corpus
    assert "referee acceptance" in rep.protocol                        # the honest path is spelled out


def test_pending_is_never_presented_as_a_discovery():
    rep = radar()
    assert "never" in rep.protocol.lower() or "nothing more" in rep.protocol
    # and matched+pending partition the extraction exactly
    assert len(rep.matched) + len(rep.pending) == len(extract_natural_sequences())


def test_short_sequences_cannot_match_the_corpus():
    stub = NaturalSequence("stub", "test", "too short to attribute", 0, (1, 1, 2))
    assert match(stub) is None                                         # < _MIN_OVERLAP terms


def test_corpus_prefixes_are_internally_consistent():
    for anum, (_name, prefix) in LOCAL_CORPUS.items():
        assert len(prefix) >= 5 and anum.startswith("A")


def test_radar_is_deterministic():
    a, b = radar(), radar()
    assert [(s.name, s.terms) for s, _ in a.matched] == [(s.name, s.terms) for s, _ in b.matched]
    assert [s.terms for s in a.pending] == [s.terms for s in b.pending]
