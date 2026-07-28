"""
Propositional modal logic (ROADMAP H4) — check_modal.

Bounded Kripke model checking across the normal systems K/T/D/B/S4/S5. The classic
correspondence theorems are the acceptance test: an axiom is valid exactly in the
systems whose frame condition it characterizes. A countermodel is definitive;
a positive result is honest bounded model checking.
"""
from mathhead.core.modal import check_modal
from mathhead.router import route

# Classic axioms and the frame property each characterizes.
K_AX = "implies(box(implies(p,q)), implies(box(p), box(q)))"   # valid in every normal system
T_AX = "implies(box(p), p)"                                    # reflexive  (T, S4, S5)
FOUR_AX = "implies(box(p), box(box(p)))"                       # transitive (S4, S5)
FIVE_AX = "implies(dia(p), box(dia(p)))"                       # euclidean  (S5)


def _status(formula, system):
    return check_modal(formula, system).status


# ------------------------- correspondence theorems ------------------------- #
def test_k_axiom_valid_everywhere():
    for system in ("K", "T", "S4", "S5"):
        assert _status(K_AX, system) == "valid"


def test_t_axiom_characterizes_reflexivity():
    assert _status(T_AX, "K") == "invalid"      # not valid without reflexivity
    for system in ("T", "S4", "S5"):
        assert _status(T_AX, system) == "valid"


def test_four_axiom_characterizes_transitivity():
    assert _status(FOUR_AX, "K") == "invalid"
    assert _status(FOUR_AX, "T") == "invalid"   # reflexive but not transitive
    assert _status(FOUR_AX, "S4") == "valid"
    assert _status(FOUR_AX, "S5") == "valid"


def test_five_axiom_only_in_s5():
    assert _status(FIVE_AX, "K") == "invalid"
    assert _status(FIVE_AX, "S4") == "invalid"  # transitive but not symmetric
    assert _status(FIVE_AX, "S5") == "valid"


def test_d_axiom_serial():
    # □p → ◇p holds on serial frames; T (reflexive ⇒ serial) satisfies it, K does not
    assert _status("implies(box(p), dia(p))", "K") == "invalid"
    assert _status("implies(box(p), dia(p))", "T") == "valid"


# ------------------------------- countermodel ------------------------------ #
def test_countermodel_is_reported():
    r = check_modal(T_AX, "K")
    assert r.status == "invalid" and r.reason_code == "COUNTERMODEL_FOUND"
    w = r.witness
    assert "false_at_world" in w and "accessibility" in w and "valuation" in w
    assert w["false_at_world"] in w["worlds"]


def test_valid_result_is_marked_bounded():
    r = check_modal(K_AX, "K")
    assert r.status == "valid" and r.reason_code == "VALID_BOUNDED"
    assert r.meta["bounded"] is True and r.meta["max_worlds"] == 6


# ------------------------------ guardrails --------------------------------- #
def test_bad_system_rejected():
    r = check_modal("p", "Q9")
    assert r.status == "error" and r.reason_code == "GUARDRAIL_VIOLATION"


def test_bad_world_count_rejected():
    assert check_modal("p", "K", 99).status == "error"


def test_unsupported_operator_rejected():
    r = check_modal("nec(p)", "K")
    assert r.status == "error" and r.reason_code == "PARSE_ERROR"


# --------------------------- routing / determinism ------------------------- #
def test_router_wiring():
    r = route("check_modal", {"formula": T_AX, "system": "T", "max_worlds": 6})
    assert r.status == "valid"


def test_determinism_of_verdict():
    # ADR-0019: verdicts are stable (a countermodel witness is an example that may vary).
    assert [check_modal(FOUR_AX, "S4").status for _ in range(5)] == ["valid"] * 5
    assert [check_modal(FOUR_AX, "T").status for _ in range(5)] == ["invalid"] * 5
