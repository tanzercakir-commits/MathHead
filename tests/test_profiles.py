"""
Capability packs + tool triage (ROADMAP L3).

Tools are grouped into packs; a server exposes a profile (default `core`), and three
always-present triage tools let an AI navigate the surface. The apply_profile filter is
tested as pure logic (it must not mutate the shared registry mid-suite).
"""
from mathhead.profiles import ALWAYS, PACKS, pack_of, select_packs
from mathhead.router import route


# ------------------------------ pack mapping ------------------------------- #
def test_pack_of_representative_tools():
    assert pack_of("verify_equality") == "core"          # the verification differentiator
    assert pack_of("cross_check") == "core"
    assert pack_of("check_modal") == "logic"
    assert pack_of("simplify") == "symbolic"
    assert pack_of("find_root_newton") == "numerical"
    assert pack_of("n_queens") == "frontier"
    assert pack_of("engine_metrics") == "observability"
    assert pack_of("list_capabilities") == "observability"


def test_select_packs():
    assert select_packs("core") == {"core"}
    assert select_packs(None) == {"core"}                # unset → curated default
    assert select_packs("full") == set(PACKS)
    assert select_packs("all") == set(PACKS)
    assert select_packs("core,frontier") == {"core", "frontier"}
    assert select_packs("nonsense") == {"core"}          # unknown → core, never empty


def test_core_profile_hides_compute_keeps_verification_and_triage():
    packs = select_packs("core")
    assert pack_of("verify_equality") in packs           # kept in the default profile
    assert pack_of("prove_unsat") in packs
    assert pack_of("simplify") not in packs              # a compute tool is hidden by default
    assert "list_capabilities" in ALWAYS                 # triage always exposed → discovery works


# ------------------------------ triage tools ------------------------------- #
def test_list_capabilities():
    r = route("list_capabilities", {})
    assert r.status == "ok" and r.total_tools >= 168
    assert r.packs["core"]["tool_count"] >= 15           # the verification core
    assert set(PACKS) <= set(r.packs)


def test_describe_tool():
    r = route("describe_tool", {"name": "cross_check"})
    assert r.status == "ok" and r.tool["pack"] == "core" and r.tool["stability"] == "stable"
    assert route("describe_tool", {"name": "no_such_tool"}).status == "error"


def test_recommend_tool_finds_the_right_verifier():
    r = route("recommend_tool", {"query": "verify that a derivative claim is correct"})
    assert r.status == "ok"
    names = [x["tool"] for x in r.recommendations]
    assert "verify_derivative" in names                  # the on-target tool is surfaced


def test_recommend_tool_guardrail():
    assert route("recommend_tool", {"query": ""}).status == "error"


def test_triage_results_are_annotated():
    # even navigation tools flow through the certainty/stability annotation
    r = route("list_capabilities", {})
    assert r.meta["stability"] == "internal" and r.meta["certainty"] == "not_applicable"
