"""Discovery Track Y — negative knowledge: fingerprinting dead ends, skipping repeats, lessons."""
import pytest

from mathhead.discovery.failure_memory import (
    FailureMemory,
    fingerprint,
    populate_from_refutations,
)


def test_fingerprint_is_canonical_and_kind_aware():
    assert fingerprint("dead_end", "a <= b") == fingerprint("dead_end", "a   <=   b")  # whitespace
    assert fingerprint("dead_end", "a <= b") != fingerprint("timeout", "a <= b")       # kind matters
    with pytest.raises(ValueError):
        fingerprint("nonsense_kind", "x")


def test_record_is_idempotent_and_seen_detects_repeats():
    m = FailureMemory()
    assert not m.seen("refuted_conjecture", "chromatic_number <= max_degree")
    m.record("refuted_conjecture", "chromatic_number <= max_degree", {"counterexample": {"n": 1}})
    m.record("refuted_conjecture", "chromatic_number <= max_degree", {"counterexample": {"n": 1}})
    assert m.seen("refuted_conjecture", "chromatic_number <= max_degree")
    assert len(m.records("refuted_conjecture")) == 1        # idempotent — one record, not two


def test_summary_counts_by_kind():
    m = FailureMemory()
    m.record("refuted_conjecture", "s1")
    m.record("timeout", "s2")
    m.record("timeout", "s3")
    assert m.summary() == {"refuted_conjecture": 1, "timeout": 2}


def test_lessons_cluster_by_witness():
    m = FailureMemory()
    # three conjectures all killed by the same witness (the single vertex), one by another
    for s in ("chromatic_number <= max_degree", "A <= B", "C <= D"):
        m.record("refuted_conjecture", s, {"counterexample": {"n": 1, "edges": []}})
    m.record("refuted_conjecture", "E <= F", {"counterexample": {"n": 3, "edges": [[0, 1], [1, 2]]}})
    lessons = m.lessons()
    assert lessons[0]["refutes"] == 3                       # the broad witness leads
    assert "chromatic_number <= max_degree" in lessons[0]["statements"]
    assert lessons[1]["refutes"] == 1


def test_populate_from_refutations_learns_only_new_dead_ends():
    m = FailureMemory()
    results = [
        ("law A", {"status": "refuted", "counterexample": {"n": 1}}),
        ("law B", {"status": "no_counterexample_within_bound"}),   # a survivor — not a dead end
        ("law A", {"status": "refuted", "counterexample": {"n": 1}}),  # repeat of A
    ]
    learned = populate_from_refutations(m, results)
    assert learned == 1                                     # only 'law A', once
    assert m.seen("refuted_conjecture", "law A")
    assert not m.seen("refuted_conjecture", "law B")


def test_populate_accepts_dataclass_like_results():
    class _Res:
        def __init__(self, status, detail):
            self.status = status
            self.detail = detail
    m = FailureMemory()
    learned = populate_from_refutations(m, [("law C", _Res("refuted", {"n": 5}))])
    assert learned == 1 and m.seen("refuted_conjecture", "law C")


def test_memory_is_deterministic():
    def build():
        m = FailureMemory()
        for s in ("z", "a", "m"):
            m.record("refuted_conjecture", s, {"counterexample": {"w": s}})
        return [le["witness"] for le in m.lessons()]
    assert build() == build()
