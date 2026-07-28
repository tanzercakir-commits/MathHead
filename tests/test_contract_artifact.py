"""
Machine-readable MCP contract (ROADMAP L2) — docs/mcp-contract.json.

The artifact must match regeneration (code = docs), it must realize the "stable core +
experimental extended" model, and EVERY tool's result must carry a valid `certainty`
(epistemic strength) + `stability` in `meta`.
"""
import json
import subprocess
import sys
from pathlib import Path

from mathhead.router import route

_ROOT = Path(__file__).resolve().parent.parent
_CONTRACT = _ROOT / "docs" / "mcp-contract.json"
_TASK = {"model": "find_model", "enumerate_models": "enumerate", "max_satisfy": "maxsat"}


def test_contract_artifact_is_up_to_date():
    r = subprocess.run([sys.executable, str(_ROOT / "scripts" / "gen_contract.py"), "--check"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_contract_realizes_stable_core_experimental_extended():
    c = json.loads(_CONTRACT.read_text(encoding="utf-8"))
    tiers = {t["stability"] for t in c["tools"].values()}
    assert {"stable", "experimental"} <= tiers                 # both tiers are present
    # the verification differentiators are the stable core
    for name in ("verify_equality", "verify_solution", "cross_check", "check_certificate",
                 "prove_unsat", "check_unsat_proof", "entailment"):
        assert c["tools"][name]["stability"] == "stable", name
    assert c["output_envelope"]["required"] == ["status", "reason_code", "explanation", "meta"]
    assert "certainty" in c["output_envelope"]["meta_keys"]


def test_modal_certainty_is_honestly_bounded():
    r = route("check_modal", {"formula": "implies(box(p), p)", "system": "T", "max_worlds": 4})
    assert r.meta["certainty"] == "bounded_check"              # not a bare "valid"
    assert r.meta["stability"] == "provisional"


def test_independent_certificate_labeling():
    for task, payload in (("prove_unsat", {"clauses": [[1], [-1]]}),
                          ("check_certificate", {"certificate": {"kind": "subset_sum",
                                                                 "numbers": [3, 4, 2], "target": 9,
                                                                 "indices": [0, 1, 2]}})):
        assert route(task, payload).meta["certainty"] == "independent_certificate"


def test_every_tool_result_has_valid_certainty_and_stability():
    c = json.loads(_CONTRACT.read_text(encoding="utf-8"))
    levels, tiers = set(c["certainty_levels"]), set(c["stability_tiers"])
    from tests.test_mcp_layer import ARGS
    for name, payload in ARGS.items():
        r = route(_TASK.get(name, name), payload)
        assert r.meta.get("certainty") in levels, f"{name}: {r.meta.get('certainty')!r}"
        assert r.meta.get("stability") in tiers, f"{name}: {r.meta.get('stability')!r}"
