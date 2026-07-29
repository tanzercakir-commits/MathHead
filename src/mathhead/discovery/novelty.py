"""
mathhead.discovery.novelty — a first 'interestingness' filter (roadmap W0/W1).

A subclass law is only INTERESTING if it is specific to that subclass — not a universal law
merely restricted to it. `trees: 2*num_edges = sum_degrees` is just the Handshake Lemma seen on
trees (it holds on EVERY graph), so it is no discovery about trees; `trees: num_edges =
num_vertices - 1` fails off the subclass, so it genuinely characterizes trees.

Rule: a subclass law is subclass-specific iff its claim FAILS on at least one object in the full
sample. This drops restricted-universals and keeps the real subclass facts — a small but real step
against the "a machine can emit a million true-but-trivial statements" problem.
"""
from __future__ import annotations

from .conjectures import subclass_laws


def is_subclass_specific(conjecture, sample) -> bool:
    """True iff the law's claim FAILS somewhere in the full sample (so it is not a universal law
    merely restricted to the subclass)."""
    return any(not conjecture.claim(g) for g in sample)


def novel_subclass_laws(objects, scope, label) -> list:
    """The subclass laws that genuinely characterize the subclass (restricted-universals dropped)."""
    return [c for c in subclass_laws(objects, scope, label) if is_subclass_specific(c, objects)]
