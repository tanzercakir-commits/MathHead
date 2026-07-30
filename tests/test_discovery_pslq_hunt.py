"""Discovery v2A3 — PSLQ constant-formula hunt with the two-precision honesty protocol."""
from mathhead.discovery.pslq_hunt import find_algebraic, find_relation, hunt_constants


def test_rediscovers_zeta2_equals_pi_squared_over_six():
    nc = find_relation(("zeta2", "pi^2"))
    assert nc is not None and nc.kind == "integer_relation"
    a, b = nc.coefficients
    assert (abs(a), abs(b)) == (6, 1) and a * b < 0            # 6·ζ(2) = π², up to overall sign
    assert nc.residual_exponent <= -180                        # collapsed to the 220-digit floor


def test_rediscovers_zeta4_equals_pi_fourth_over_ninety():
    nc = find_relation(("zeta4", "pi^4"))
    assert nc is not None and sorted(map(abs, nc.coefficients)) == [1, 90]


def test_rediscovers_sqrt2_and_phi_minimal_polynomials():
    s = find_algebraic("sqrt2", 2)
    assert s is not None and sorted(map(abs, s.coefficients)) == [0, 1, 2]      # x² − 2
    p = find_algebraic("phi", 2)
    assert p is not None and sorted(map(abs, p.coefficients)) == [1, 1, 1]      # x² − x − 1


def test_unrelated_constants_yield_none_not_a_forced_relation():
    assert find_relation(("e", "pi")) is None                  # no known low-height relation
    assert find_relation(("gamma", "ln2")) is None
    assert find_relation(("noise", "pi")) is None              # the noise control
    assert find_algebraic("pi", 4) is None                     # transcendental — honestly out of reach


def test_status_is_always_numerical_conjecture_never_proved():
    r = hunt_constants()
    assert r["found"] and all(nc.status == "numerical_conjecture" for nc in r["found"])
    assert all("proved" not in nc.status for nc in r["found"])


def test_two_precision_protocol_is_recorded():
    nc = find_relation(("zeta2", "pi^2"))
    assert nc.discovered_at_dps == 60 and nc.verified_at_dps == 220
    assert nc.verified_at_dps > 3 * nc.discovered_at_dps       # the second gate is far stricter


def test_the_none_list_is_a_result_not_an_error():
    r = hunt_constants()
    assert "relation('e', 'pi')" in r["none"] and "algebraic(pi)" in r["none"]


def test_hunt_is_deterministic():
    a = hunt_constants()
    b = hunt_constants()
    assert [nc.statement for nc in a["found"]] == [nc.statement for nc in b["found"]]
    assert a["none"] == b["none"]
