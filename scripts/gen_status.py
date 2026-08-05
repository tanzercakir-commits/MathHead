#!/usr/bin/env python3
"""
MathHead discovery — tracker status generator + integrity guard.

Keeps the THREE tracking files honest AUTOMATICALLY, so bookkeeping isn't a manual chore:
  * PLAN   docs/IDEAL-ENGINE-ROADMAP.md    — frozen; this script only GUARDS it (phase/track counts
                                             must not silently shrink).
  * TODO   docs/discovery/TODO.md          — refreshes the "_Last updated_" stats line in place.
  * SAMPLE docs/discovery/SAMPLE-REPORT.md — regenerated from the live engine (code = docs).

Usage:
    python scripts/gen_status.py           # refresh TODO stats + SAMPLE-REPORT.md
    python scripts/gen_status.py --check    # CI: verify plan integrity + sample freshness (exit 0/1)

`tests/test_trackers.py` runs the --check invariants inside pytest, so CI fails the build if the plan
shrinks or the sample report goes stale — the automation the trackers rely on.
"""
from __future__ import annotations

import argparse
import glob
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
ROADMAP = ROOT / "docs" / "IDEAL-ENGINE-ROADMAP.md"
TODO = ROOT / "docs" / "discovery" / "TODO.md"
SAMPLE = ROOT / "docs" / "discovery" / "SAMPLE-REPORT.md"
PROGRESS = ROOT / "docs" / "discovery" / "PROGRESS.md"
DISCO = ROOT / "src" / "mathhead" / "discovery"
TESTS = ROOT / "tests"

# The frozen plan's invariants — guarded so the 103-phase list can never be silently lost.
PHASES_EXPECTED = 103
TRACKS_EXPECTED = 21
# The v2 extension (Real Discovery Program, user-approved 2026-07-30) — guarded the same way.
# v2 phase IDs are lowercase-prefixed (v2A0…) so they can NEVER inflate the original 103 count.
V2_PHASES_EXPECTED = 16
# The v3 PRODUCT programme (user goal 2026-07-30: "a product mathematicians will want to use").
V3_PHASES_EXPECTED = 9
# The v4 MAX-FUNCTIONALITY sprint (user goal 2026-08-05: fully completable plan + final audit).
V4_PHASES_EXPECTED = 8


def roadmap_counts() -> tuple:
    t = ROADMAP.read_text(encoding="utf-8")
    phases = len(re.findall(r"(?m)^[A-Z]{1,2}[0-9]+", t))
    tracks = len(re.findall(r"(?m)^\*\*Track", t))
    done = t.count("✅")
    return phases, tracks, done


def v2_count() -> int:
    return len(re.findall(r"(?m)^v2[A-D][0-9]+", ROADMAP.read_text(encoding="utf-8")))


def v3_count() -> int:
    return len(re.findall(r"(?m)^v3P[0-9]+", ROADMAP.read_text(encoding="utf-8")))


def v4_count() -> int:
    return len(re.findall(r"(?m)^v4F[0-9]+", ROADMAP.read_text(encoding="utf-8")))


def module_count() -> int:
    return len([p for p in glob.glob(str(DISCO / "*.py")) if "__" not in Path(p).name])


def discovery_test_count() -> int:
    n = 0
    for f in glob.glob(str(TESTS / "test_discovery_*.py")):
        n += len(re.findall(r"(?m)^def test_", Path(f).read_text(encoding="utf-8")))
    return n


def sample_report_text() -> str:
    from mathhead.discovery import render, run_report
    return render(run_report(max_n=6)) + "\n"


def _stats_line() -> str:
    import datetime
    phases, tracks, done = roadmap_counts()
    today = datetime.date.today().isoformat()
    return (f"_Last updated: {today} · {module_count()} modules · {discovery_test_count()} "
            f"discovery tests · {done} phases ✅ full, of {phases} v1 + {v2_count()} v2 "
            f"(across {tracks} tracks)._")


def refresh() -> None:
    SAMPLE.write_text(sample_report_text(), encoding="utf-8")
    todo = TODO.read_text(encoding="utf-8")
    # the stats block runs from "_Last updated:" to its closing "_" (may span lines)
    todo, n = re.subn(r"_Last updated:.*?_", _stats_line(), todo, count=1, flags=re.S)
    if n != 1:
        raise SystemExit("could not find the '_Last updated: … _' stats block in TODO.md")
    TODO.write_text(todo, encoding="utf-8")
    print("refreshed:", SAMPLE.name, "+ TODO stats line")


def check() -> int:
    problems = []
    phases, tracks, _ = roadmap_counts()
    if phases != PHASES_EXPECTED:
        problems.append(f"PLAN shrunk/grew: {phases} phases (expected {PHASES_EXPECTED})")
    if tracks != TRACKS_EXPECTED:
        problems.append(f"PLAN tracks changed: {tracks} (expected {TRACKS_EXPECTED})")
    if v2_count() != V2_PHASES_EXPECTED:
        problems.append(f"v2 extension changed: {v2_count()} phases (expected {V2_PHASES_EXPECTED})")
    if v3_count() != V3_PHASES_EXPECTED:
        problems.append(f"v3 extension changed: {v3_count()} phases (expected {V3_PHASES_EXPECTED})")
    if v4_count() != V4_PHASES_EXPECTED:
        problems.append(f"v4 extension changed: {v4_count()} phases (expected {V4_PHASES_EXPECTED})")
    for f in (ROADMAP, TODO, PROGRESS, SAMPLE):
        if not f.exists():
            problems.append(f"missing tracking file: {f.name}")
    if SAMPLE.exists() and SAMPLE.read_text(encoding="utf-8") != sample_report_text():
        problems.append("SAMPLE-REPORT.md is stale — run: python scripts/gen_status.py")
    if problems:
        print("TRACKER CHECK FAILED:", *(f"\n  - {p}" for p in problems), file=sys.stderr)
        return 1
    print("tracker check OK:",
          f"{phases} phases · {tracks} tracks · v2 {v2_count()} · v3 {v3_count()} · v4 {v4_count()} "
          "· sample fresh")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="verify integrity (CI); do not write")
    args = ap.parse_args()
    sys.exit(check() if args.check else (refresh() or 0))
