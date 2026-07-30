"""
Tracker integrity — CI-enforced automation of the three tracking files.

Guards, on every push (CI runs pytest):
  * the PLAN never silently shrinks (103 phases across 21 tracks),
  * the three tracking files exist with their role headers,
  * SAMPLE-REPORT.md stays in sync with the live engine (code = docs).

If this fails, run:  python scripts/gen_status.py
"""
import importlib.util
from pathlib import Path

_ROOT = Path(__file__).parent.parent
_spec = importlib.util.spec_from_file_location("gen_status", _ROOT / "scripts" / "gen_status.py")
gen_status = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen_status)


def test_plan_is_intact_never_silently_shrinks():
    phases, tracks, _done = gen_status.roadmap_counts()
    assert phases == gen_status.PHASES_EXPECTED == 103     # the full to-do list, preserved
    assert tracks == gen_status.TRACKS_EXPECTED == 21


def test_v2_extension_is_guarded_and_cannot_leak_into_v1():
    # the v2 Real Discovery Program (user-approved) has its own pinned count, and its lowercase
    # phase IDs (v2A0…) can never inflate the original 103
    assert gen_status.v2_count() == gen_status.V2_PHASES_EXPECTED == 16
    phases, _, _ = gen_status.roadmap_counts()
    assert phases == 103                                   # unchanged AFTER the v2 append


def test_three_tracking_files_exist_with_role_headers():
    assert "PLAN — DONMUŞ" in gen_status.ROADMAP.read_text(encoding="utf-8")
    assert "# Discovery Engine — TODO" in gen_status.TODO.read_text(encoding="utf-8")
    assert "CHANGELOG" in gen_status.PROGRESS.read_text(encoding="utf-8")


def test_sample_report_is_in_sync_with_the_engine():
    # code = docs: the committed sample must match a fresh render (regen with gen_status.py)
    assert gen_status.SAMPLE.read_text(encoding="utf-8") == gen_status.sample_report_text()


def test_check_passes_end_to_end():
    assert gen_status.check() == 0
