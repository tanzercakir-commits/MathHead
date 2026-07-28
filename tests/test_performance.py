"""
Performance (ROADMAP K1) — incremental solving (entail_batch) + deterministic
memoization (cache).

Correctness first: the incremental batch must give the SAME verdict as calling
check_entailment individually (only the shared context is reused). Memoization must
be transparent (a cache hit returns the identical, deterministic result).
"""
from mathhead.cache import cache_stats, cache_stats_result, memoize, reset_cache
from mathhead.compute import is_prime, simplify
from mathhead.core.logic import check_entailment, entail_batch
from mathhead.router import route


# ------------------------- incremental entailment -------------------------- #
_PREMISES = ["forall(x, implies(Man(x), Mortal(x)))", "Man(socrates)"]
_CONCLUSIONS = ["Mortal(socrates)", "Man(plato)"]


def test_entail_batch_matches_individual_checks():
    batch = entail_batch(_PREMISES, _CONCLUSIONS)
    assert batch.status == "ok" and len(batch.results) == 2
    for r in batch.results:
        individual = check_entailment(_PREMISES, _CONCLUSIONS[r["index"]])
        assert r["status"] == individual.status


def test_entail_batch_propositional():
    r = entail_batch(["p", "implies(p, q)"], ["q", "p", "r"])
    verdicts = [x["status"] for x in r.results]
    assert verdicts == ["valid", "valid", "invalid"]
    assert "witness" in r.results[2]  # the invalid one carries a counterexample


def test_entail_batch_determinism():
    a = entail_batch(_PREMISES, _CONCLUSIONS)
    b = entail_batch(_PREMISES, _CONCLUSIONS)
    assert [x["status"] for x in a.results] == [x["status"] for x in b.results]


def test_entail_batch_guardrail():
    assert entail_batch(["p"], []).status == "error"          # empty conclusions
    assert entail_batch(["p ++"], ["q"]).status == "error"    # parse/guardrail error


def test_entail_batch_router_wiring():
    r = route("entail_batch", {"premises": ["p", "implies(p, q)"], "conclusions": ["q"]})
    assert r.status == "ok" and r.results[0]["status"] == "valid"


# ----------------------------- memoization --------------------------------- #
def test_memoized_hit_returns_identical_result():
    reset_cache()
    r1 = is_prime(1_000_003)
    r2 = is_prime(1_000_003)
    assert r1 is r2                       # a cache hit returns the IDENTICAL object
    stats = cache_stats()
    assert stats["hits"] >= 1 and stats["misses"] >= 1


def test_memoization_does_not_change_results():
    reset_cache()
    a = simplify("sin(x)**2 + cos(x)**2")
    b = simplify("sin(x)**2 + cos(x)**2")
    assert a.result == b.result == "1"    # correctness unaffected by caching


def test_memoize_skips_unhashable_arguments():
    calls = {"n": 0}

    @memoize
    def f(x):
        calls["n"] += 1
        return x

    f([1, 2])                             # unhashable → not cached
    f([1, 2])
    assert calls["n"] == 2                # both calls actually ran (no false cache hit)


def test_cache_stats_tool():
    reset_cache()
    is_prime(7919)
    is_prime(7919)
    r = cache_stats_result()
    assert r.status == "ok" and r.reason_code == "CACHE_STATS"
    assert r.stats["hits"] >= 1
    # via the router too
    assert route("cache_stats", {}).status == "ok"
