"""
v1 closure sweep D — PROOF tests for the AF / AG closure candidates.

Each test is the evidence behind a roadmap ✅: AF0 catch-rate + tool-selection base extended to
the discovery surface, AF1 the discovery-rate metric (deterministic per-unit counts, novelty
honestly 0), AF2 regression fences + deterministic replay, AG0 seed discipline across the
evolve / hunt / sample surfaces + the product door, AG1 the in-container parallel-search +
disk-cache slice (parallel == serial by construction, the cache can never change an answer),
AG2 the resource-fence inventory + the threat-model's discovery-sympify line (T8), AG3 CI
matrix / release / packaging pins, AG4 docs build + gallery coverage derived from the docs +
ADR archive integrity, AG5 the in-container instrumentation slice (opt-in metrics that never
change a result; CLI --stats to stderr). (AF3 stays open with a one-line honest reason in the
roadmap — no test pretends otherwise.)
"""
import json
import re
import shlex
import shutil
import subprocess
import sys
import tomllib
from importlib import util as importlib_util
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent


# --- AF0: catch-rate + tool-selection base, EXTENDED to the discovery surface ------------------

def _poly_expr(coeffs) -> str:
    """Kernel poly tuple (low→high) as an expression string for the product door."""
    terms = [f"({c})*n**{k}" for k, c in enumerate(coeffs) if c]
    return " + ".join(terms) or "0"


def test_af0_catch_rate_and_tool_selection_extend_to_the_discovery_surface():
    # the MathHead base: the systematic adversarial battery — 600+ false claims, ZERO breaches,
    # and the positive controls prove the verifier is not just rejecting everything
    from mathhead.discovery.adversarial import _false_divides_cases, robustness_report
    rr = robustness_report(600)
    assert rr.attempts >= 600 and rr.positive_controls == 3
    assert rr.breaches == [] and rr.positive_failures == [] and rr.sound
    assert (rr.attempts - len(rr.breaches)) / rr.attempts == 1.0        # the catch rate itself

    # the EXTENSION: the same false claims (plus one known-false claim per additional product
    # surface) fed through the check() gate — nothing may come back 'proved'
    from mathhead.discovery.product import check
    battery = [(f"{m} | {_poly_expr(poly)}", "modular_divisibility")
               for i, (m, poly) in enumerate(_false_divides_cases()) if i < 120]
    battery += [
        ("n^2 ≡ n (mod 3)", "polynomial_congruence"),
        ("sum_(i=1..n) i = n^2", "sum_identity"),
        ("num_vertices <= num_edges", "graph_inequality"),
        ("all perms of n: descents <= fixed_points", "permutation_inequality"),
        ("partitions(n, odd) == partitions(n, all)", "partition_count_identity"),
        ("compositions(n) == n", "composition_count_identity"),
    ]
    results = [check(stmt) for stmt, _ in battery]
    assert [r.statement for r in results if r.verdict == "proved"] == []    # zero breaches
    assert all(r.verdict == "refuted" and r.structure == want
               for (_s, want), r in zip(battery, results))
    # the measurement is deterministic: a re-run of a slice reproduces the verdicts exactly
    assert [check(s) for s, _ in battery[:10]] == results[:10]

    # tool-selection base (♻️ MathHead): the benchmark runs live and its honest floors hold …
    sys.path.insert(0, str(_ROOT / "benchmarks"))
    import run_tool_selection as ts
    summary = ts.summarize(ts.run())
    assert summary["cases"] >= 15                               # a substantial case set
    assert summary["top3_rate"] >= 0.85 and summary["top1_rate"] >= 0.70
    # … and the discovery side selects the strongest instrument first (X2 map)
    from mathhead.discovery.technique_map import suggest_techniques
    assert suggest_techniques("6 | n^3 - n")[0][1] == "kernel.prove_divides"


# --- AF1: the discovery-rate metric — deterministic per-unit counts, novelty honestly 0 --------

def test_af1_discovery_rate_metric_is_deterministic_and_novelty_is_honestly_zero():
    from mathhead.discovery.evaluation import attribute, evaluate, render_scorecard
    from mathhead.discovery.report import run_report

    rep = run_report(max_n=4)
    card = evaluate(rep)
    items = list(rep.proved) + list(rep.empirical_laws) + list(rep.open_bounded)
    assert card.total == len(items) > 0                       # per-unit: exactly the graded corpus

    # verified / attributed counts re-derived by TEST-LOCAL predicates (not evaluation's own)
    def _is_verified(it):
        return bool(it.get("kernel_verified") or it.get("independently_verified")
                    or it.get("certainty") in {"formal_proof", "exhaustive_residue_proof",
                                               "kernel_identity", "solver_verified"})
    assert card.verified == sum(1 for it in items if _is_verified(it)) > 0
    assert card.attributed_known == sum(
        1 for it in items if attribute(it["statement"]) is not None) > 0

    # deterministic: a completely fresh pipeline run grades identically
    assert evaluate(run_report(max_n=4)) == card

    # novelty is HONESTLY zero: no field and no rendering claims a novel result
    text = render_scorecard(card)
    assert "novel-to-literature: 0 established" in text
    assert "pending a corpus check" in text
    assert card.novel_candidates == card.unattributed         # candidates, never claims
    assert "not built" in card.notes and "not novelty claims" in card.notes

    # the report carries the same card — meta.scorecard mirrors the live grading, novelty pinned 0
    assert rep.meta["scorecard"] == {
        "total": card.total, "verified": card.verified,
        "attributed_known": card.attributed_known, "novel_established": 0,
        "unattributed": len(card.unattributed)}


# --- AF2: regression fences + deterministic replay ---------------------------------------------

def test_af2_regression_fences_and_deterministic_replay():
    from mathhead.discovery.report import render, run_report

    # two END-TO-END pipeline runs render byte-identically (every discovery reproducible)
    assert render(run_report(max_n=4)) == render(run_report(max_n=4))

    # the committed SAMPLE-REPORT.md IS the live engine output — a regression fence living in
    # the repo (also enforced by gen_status --check; re-proved here directly, byte for byte)
    sample = (_ROOT / "docs" / "discovery" / "SAMPLE-REPORT.md").read_text(encoding="utf-8")
    assert sample == render(run_report(max_n=6)) + "\n"

    # kernel replay: re-running the kernel mints the SAME theorem with the SAME hash, and the
    # product door reproduces that hash from the statement alone
    from mathhead.discovery.kernel import prove_divides
    from mathhead.discovery.product import check
    from mathhead.discovery.provenance import proof_hash, replay
    thm, term = prove_divides(30, (0, -1, 0, 0, 0, 1))
    _thm2, term2 = prove_divides(30, (0, -1, 0, 0, 0, 1))
    assert replay(term) == thm and proof_hash(term) == proof_hash(term2)
    assert check("6 | n^3 - n").proof_hash == proof_hash(prove_divides(6, (0, -1, 0, 1))[1])

    # a seeded discovery hunt replays field-by-field
    from mathhead.discovery.frankl import hunt_frankl
    assert hunt_frankl(m=5, seed=7, steps=250) == hunt_frankl(m=5, seed=7, steps=250)


# --- AG0: seed discipline across evolve / hunt / sample + the product door ---------------------

def test_ag0_seed_discipline_spans_evolve_hunt_sample_and_the_product_door(capsys):
    # EVOLVE — the seeded SA hunter replays exactly, and its provenance rides the outcome
    from mathhead.discovery.adaptive_search import hunt
    from mathhead.discovery.conjecture_db import CHI_LE_DELTA
    h1 = hunt(CHI_LE_DELTA, n=7, seed=3, steps=200)
    assert h1 == hunt(CHI_LE_DELTA, n=7, seed=3, steps=200)
    assert (h1.n, h1.seed) == (7, 3)

    # HUNT — the live Frankl hunt replays, and the CLI carries the seed to the user verbatim
    from mathhead.discovery.cli import main
    from mathhead.discovery.frankl import hunt_frankl
    f1 = hunt_frankl(m=6, seed=1, steps=200)
    assert f1 == hunt_frankl(m=6, seed=1, steps=200) and f1.seed == 1
    outs = []
    for _ in range(2):
        assert main(["--json", "hunt", "frankl", "--universe", "6",
                     "--steps", "200", "--seed", "4"]) == 0
        outs.append(capsys.readouterr().out)
    assert outs[0] == outs[1] and json.loads(outs[0])["seed"] == 4

    # SAMPLE — the m>=5 sampled guard replays, and stays honest about what a sample is NOT
    from mathhead.discovery.frankl import guard_sampled
    g1 = guard_sampled(5, samples=300, seed=2)
    assert g1 == guard_sampled(5, samples=300, seed=2)
    assert g1.violations == 0 and "proves NOTHING" in g1.coverage

    # PRODUCT DOOR — the whole envelope (hash included) is call-stable
    from mathhead.discovery.product import check
    a, b = check("n^5 ≡ n (mod 30)"), check("n^5 ≡ n (mod 30)")
    assert a == b and a.proof_hash != "" and a.proof_hash == b.proof_hash


# --- AG1: parallel search == serial search; the cache can never change an answer ---------------

def test_ag1_parallel_sweep_equals_serial_and_the_disk_cache_never_changes_an_answer(tmp_path):
    from itertools import combinations

    from mathhead.discovery.parallel_search import SCOPE_NOTE, DiskCache, sweep_graph_bound

    # the worker count CANNOT change the answer: workers=3 == workers=1, field for field
    serial = sweep_graph_bound("num_triangles <= num_edges", 6, workers=1)
    parallel = sweep_graph_bound("num_triangles <= num_edges", 6, workers=3)
    assert parallel == serial
    assert (serial.verdict, serial.tier) == ("refuted", "exact_integer_certificate")
    # the merged witness is the smallest-order violation — re-verified RAW, no engine call
    edges = {tuple(e) for e in serial.witness["edges"]}
    tri = sum(1 for x, y, z in combinations(range(serial.witness["n"]), 3)
              if {(x, y), (y, z), (x, z)} <= edges)
    assert tri == serial.witness["num_triangles"] > serial.witness["num_edges"] == len(edges)
    # the ledger pins the classes scanned: connected graphs per order (OEIS A001349 prefix),
    # the violating order stopping AT its first witness
    assert serial.checked_per_order == ((2, 1), (3, 2), (4, 6), (5, 21), (6, 111))
    # cross-instrument agreement with the product door (independent scan, same verdict)
    from mathhead.discovery.product import check
    assert check("num_triangles <= num_edges", max_n=6).verdict == "refuted"

    # a TRUE bound stays open identically at any worker count; the honest scope note rides along
    open_serial = sweep_graph_bound("num_vertices <= num_edges + 1", 5, workers=1)
    assert open_serial == sweep_graph_bound("num_vertices <= num_edges + 1", 5, workers=2)
    assert (open_serial.verdict, open_serial.witness) == ("open", None)
    assert open_serial.checked_per_order == ((2, 1), (3, 2), (4, 6), (5, 21))
    assert "OUT of scope" in SCOPE_NOTE and open_serial.scope_note == SCOPE_NOTE

    # refusal, never guessing: unparseable statements, unknown invariants, AND a max_n beyond
    # the generation wall are all refused up front — before any worker is launched
    with pytest.raises(ValueError):
        sweep_graph_bound("the weather tomorrow", 5)
    with pytest.raises(ValueError):
        sweep_graph_bound("frobnitz <= num_edges", 5)
    with pytest.raises(ValueError, match="refused up front"):
        sweep_graph_bound("num_vertices <= num_edges", 8)

    # DISK CACHE: a second run is all-hits with the SAME answer
    cache = DiskCache(tmp_path / "c")
    first = sweep_graph_bound("num_vertices <= num_edges + 1", 5, workers=2, cache=cache)
    assert (cache.misses, cache.hits) == (4, 0)
    second = sweep_graph_bound("num_vertices <= num_edges + 1", 5, workers=1, cache=cache)
    assert (cache.misses, cache.hits) == (4, 4)
    assert first == second == open_serial
    # a corrupted entry is a MISS and gets recomputed — never trusted
    victim = sorted((tmp_path / "c").glob("*.json"))[0]
    victim.write_text("{ this is not json", encoding="utf-8")
    assert sweep_graph_bound("num_vertices <= num_edges + 1", 5, cache=cache) == open_serial
    assert cache.misses == 5                                   # exactly the corrupted entry
    # schema bump = invalidation by key: a new-schema cache sees NONE of the old entries
    v2 = DiskCache(tmp_path / "c", schema="v2-test")
    assert sweep_graph_bound("num_vertices <= num_edges + 1", 5, cache=v2) == open_serial
    assert (v2.hits, v2.misses) == (0, 4)
    # explicit invalidation empties the store
    assert cache.invalidate() == 8                             # 4 old-schema + 4 new-schema
    assert list((tmp_path / "c").glob("*.json")) == []


def test_ag1_parallel_ramsey_decisions_merge_deterministically():
    pytest.importorskip("pysat.solvers", reason="pysat not installed")
    from mathhead.discovery.parallel_search import sweep_ramsey
    par = sweep_ramsey(3, 3, 5, 6, workers=2)
    assert par == sweep_ramsey(3, 3, 5, 6, workers=1)
    assert par.ramsey_value == 6
    assert [(v["n"], v["satisfiable"], v["certainty"]) for v in par.verdicts] == [
        (5, True, "independently_verified_witness"),
        (6, False, "independently_verified_unsat_proof")]
    # the merge applies the SAME bracket rule as the serial instrument
    from mathhead.discovery.ramsey_sat import bracket_ramsey
    assert bracket_ramsey(3, 3, 5, 6)["ramsey_value"] == par.ramsey_value
    # deliberately NO witness in the merged record — a witness is AN example (ADR-0019 / T7)
    assert all(set(v) == {"n", "satisfiable", "meaning", "certainty"} for v in par.verdicts)


# --- AG2: resource-fence inventory + the threat model covers the discovery surface -------------

def test_ag2_resource_fence_inventory_and_threat_model_cover_the_discovery_surface():
    from mathhead.router import route

    # 1) the MCP guardrail fence triggers, and every advertised fence is introspectable
    r = route("entailment", {"premises": ["p"] * 5000, "conclusion": "p"})
    assert (r.status, r.reason_code) == ("error", "GUARDRAIL_VIOLATION")
    from mathhead.observability import limits
    lim = limits()
    assert route("resource_limits", {}).limits == lim
    assert all(isinstance(v, int) and v > 0 for v in lim.values())

    # 2) the z3 defaults pinned to the documented security posture (seed 42, 5000 ms)
    from mathhead.core.logic import DEFAULT_SEED, DEFAULT_TIMEOUT_MS
    assert (DEFAULT_SEED, DEFAULT_TIMEOUT_MS) == (42, 5000)

    # 3) the discovery generation walls REFUSE — never a silent truncation
    from mathhead.discovery.frankl import guard_exhaustive, union_closure
    from mathhead.discovery.generate import generate_graphs
    from mathhead.discovery.permutations import generate_permutations
    with pytest.raises(ValueError):
        generate_graphs(8)                                     # 2^(n choose 2) wall
    with pytest.raises(ValueError):
        generate_permutations(8)                               # n! wall
    with pytest.raises(ValueError):
        guard_exhaustive(5)                                    # 2^(2^m) wall
    assert union_closure([1, 2, 4], cap=2) is None             # cap: explicit refusal
    from mathhead.discovery.nauty_scale import geng_available, geng_graphs
    if geng_available():                                       # the geng hard cap refuses too
        with pytest.raises(ValueError):
            geng_graphs(8, hard_cap=100)

    # 4) product-door fences refuse up front (modulus cap, 4000-digit constant guard)
    from mathhead.discovery.product import check
    assert check("1000001 | n").verdict == "unsupported"
    assert check("0 | n").verdict == "unsupported"
    monster = "2 | " + "9" * 4001
    assert (check(monster).verdict, check(monster).structure) == \
        ("unsupported", "oversized_constant")

    # 5) the threat model now WRITES DOWN the discovery-sympify boundary (T8) — and the line
    #    matches the actual code: product.py does use sympify; the MCP path stays allowlisted
    tm = (_ROOT / "docs" / "threat-model.md").read_text(encoding="utf-8")
    assert "| T8 |" in tm and "`sympify` on the discovery surface" in tm
    assert "operator/CLI surface" in tm and "OS-level sandboxing" in tm
    import inspect

    from mathhead.discovery import product
    assert "sympify" in inspect.getsource(product)             # the documented boundary is real
    evil = route("simplify", {"expression": "__import__('os').system('id')"})
    assert evil.status == "error"                              # boundary 2 still holds


# --- AG3: CI matrix / release / packaging pinned -----------------------------------------------

def test_ag3_ci_matrix_release_and_packaging_are_pinned(capsys):
    ci = (_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    for job in ("trackers:", "test:", "test-solvers:", "reproducible:", "build:"):
        assert f"\n  {job}" in ci, f"CI job missing: {job}"
    assert "os: [ubuntu-latest, macos-latest, windows-latest]" in ci     # 3-OS matrix
    assert 'python: ["3.10", "3.11", "3.12"]' in ci                      # 3-Python matrix
    assert "ruff check ." in ci and "--cov=mathhead" in ci               # lint + coverage gate
    assert "python -m build" in ci and "twine check dist/*" in ci        # wheel build validated
    assert 'pip install -e ".[dev]"' in ci and 'pip install -e ".[dev,solvers]"' in ci
    assert "-c constraints.txt" in ci                                    # reproducible install
    assert "gen_status.py --check" in ci                                 # tracker integrity job

    rel = (_ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    assert 'tags: [ "v*" ]' in rel and "pypa/gh-action-pypi-publish" in rel
    assert "id-token: write" in rel and "twine check dist/*" in rel      # trusted publishing
    docs = (_ROOT / ".github" / "workflows" / "docs.yml").read_text(encoding="utf-8")
    assert "mkdocs gh-deploy" in docs and "mkdocs-material" in docs

    # packaging: every declared console script resolves to a real callable, versions cohere
    import importlib

    import mathhead
    proj = tomllib.loads((_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    scripts = proj["project"]["scripts"]
    assert set(scripts) == {"mathhead", "mathhead-server", "mathhead-discover"}
    for target in scripts.values():
        mod, attr = target.split(":")
        assert callable(getattr(importlib.import_module(mod), attr)), target
    assert proj["project"]["version"] == mathhead.__version__
    assert proj["project"]["requires-python"] == ">=3.10"                # matches the matrix floor
    assert proj["build-system"]["build-backend"] == "hatchling.build"

    # the in-process equivalent of the wheel-smoke the build job runs on every push
    from mathhead import cli as core_cli
    assert core_cli.main(["entail", "-p", "p", "-p", "implies(p, q)", "-c", "q"]) == 0
    assert "valid" in capsys.readouterr().out


# --- AG4: docs build + gallery coverage FROM the docs + ADR archive integrity ------------------

def test_ag4_docs_build_gallery_coverage_and_adr_integrity(tmp_path, capsys):
    manual = _ROOT / "docs" / "manual"

    # mkdocs nav ↔ files, BOTH directions (no dead nav entry, no orphan page)
    mk = (_ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    nav_files = re.findall(r"(?m)^\s+-\s+[^:]+:\s+(\S+\.md)\s*$", mk)
    assert len(nav_files) == 6 and "docs_dir: docs/manual" in mk
    for f in nav_files:
        assert (manual / f).exists(), f"nav points at a missing page: {f}"
    for page in manual.glob("*.md"):
        assert page.name in nav_files, f"orphan page not in nav: {page.name}"
    # the CI docs pipeline deploys exactly this config
    docs_yml = (_ROOT / ".github" / "workflows" / "docs.yml").read_text(encoding="utf-8")
    assert "mkdocs gh-deploy --force" in docs_yml
    # a LIVE strict build whenever the toolchain is present (it is not a [dev] dependency —
    # the nav/file/gallery pins above run everywhere regardless)
    if shutil.which("mkdocs") and importlib_util.find_spec("material") is not None:
        proc = subprocess.run(["mkdocs", "build", "--strict", "-q", "-d",
                               str(tmp_path / "site")],
                              cwd=_ROOT, capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr
        assert (tmp_path / "site" / "index.html").exists()

    # gallery coverage derived FROM the docs themselves: every documented `check` command in the
    # manual is extracted and executed VERBATIM (code = docs, inventory included)
    from mathhead.discovery.cli import main
    cmds = []
    for page in ("quickstart.md", "examples.md"):
        for line in (manual / page).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("$ mathhead-discover check"):
                cmds.append(shlex.split(line[len("$ mathhead-discover "):]))
    assert len(cmds) >= 15                                     # the gallery is substantial
    for argv in cmds:
        # exit 0 is now VERDICT-tied: the CLI exits 3 on an `unsupported` refusal, so a
        # documented command drifting out of the supported surface FAILS this fence
        assert main(argv) == 0, f"documented command failed (or became unsupported): {argv}"
        out = capsys.readouterr().out
        assert "VERDICT: unsupported" not in out, f"documented command unsupported: {argv}"

    # ADR archive integrity: the frozen discovery archive is complete and untampered, and the
    # main decision log is unique + monotone
    disc = (_ROOT / "docs" / "discovery" / "DECISIONS.md").read_text(encoding="utf-8")
    dn = [int(x) for x in re.findall(r"(?m)^## ADR-D(\d{4})", disc)]
    assert dn == list(range(1, 43))                            # ADR-D0001..D0042, no gap, no dup
    assert "[FROZEN ARCHIVE]" in disc and disc.count("**Status:**") >= 42
    main_log = (_ROOT / "DECISIONS.md").read_text(encoding="utf-8")
    mn = [int(x) for x in re.findall(r"(?m)^## ADR-(\d{4})", main_log)]
    assert mn == sorted(mn) and len(mn) == len(set(mn)) and len(mn) >= 35


# --- AG5: the in-container instrumentation slice ------------------------------------------------

def test_ag5_instrumentation_collects_metrics_without_changing_results(tmp_path):
    from mathhead.discovery import instrumentation as ins
    from mathhead.discovery.product import check

    ins.reset()
    ins.disable()
    # OFF by default: observe is a pure passthrough — zero state, untouched result
    r_off = ins.observe("check", check, "6 | n^3 - n",
                        _outcome=lambda r: r.verdict)
    assert ins.snapshot()["total_calls"] == 0

    ins.enable()
    r_on = ins.observe("check", check, "6 | n^3 - n", _outcome=lambda r: r.verdict)
    assert r_on == r_off == check("6 | n^3 - n")               # results NEVER change
    ins.observe("check", check, "5 | n^3 - n", _outcome=lambda r: r.verdict)
    snap = ins.snapshot()
    assert snap["total_calls"] == 2
    op = snap["ops"]["check"]
    assert op["calls"] == 2 and op["outcomes"] == {"proved": 1, "refuted": 1}
    assert op["total_ms"] >= op["max_ms"] >= 0 and op["solver_calls"] == 0
    assert "no external telemetry" in snap["note"]             # the privacy boundary rides along

    # the JSON dump is the snapshot, and goes only to a LOCAL file
    out = tmp_path / "stats.json"
    text = ins.dump_json(str(out))
    assert json.loads(text) == json.loads(out.read_text(encoding="utf-8")) == snap

    ins.reset()
    assert ins.snapshot()["total_calls"] == 0
    ins.disable()


def test_ag5_cli_stats_flag_reports_to_stderr_and_keeps_the_stdout_contract(capsys):
    from mathhead.discovery import instrumentation as ins
    from mathhead.discovery.cli import main

    # a LIBRARY user's default collector — enabled, carrying data — must survive a CLI run
    ins.reset()
    ins.enable()
    ins.record("library_op", "ok", 1.0)

    # without --stats: stderr silent, stdout exactly as documented
    assert main(["check", "6 | n^3 - n"]) == 0
    plain = capsys.readouterr()
    assert "VERDICT: proved" in plain.out and plain.err == ""

    # with --stats: stdout UNCHANGED, stderr carries the JSON metrics block
    assert main(["--stats", "check", "6 | n^3 - n"]) == 0
    got = capsys.readouterr()
    assert got.out == plain.out
    stats = json.loads(got.err)
    assert stats["ops"]["check"]["calls"] == 1
    assert stats["ops"]["check"]["outcomes"] == {"proved": 1}
    assert stats["ops"]["check"]["solver_calls"] == 0
    assert "no external telemetry" in stats["note"]
    # ISOLATION both ways: the CLI's private collector never saw the library op …
    assert "library_op" not in stats["ops"]
    # … and the CLI neither reset, nor disabled, nor polluted the library default collector
    assert ins.enabled()
    assert ins.snapshot()["ops"]["library_op"]["calls"] == 1
    assert "check" not in ins.snapshot()["ops"]
    ins.disable()
    ins.reset()

    # the z3-using route counts its solver call honestly
    assert main(["--stats", "check", "sum_(i=1..n) i <= n^2"]) == 0
    st2 = json.loads(capsys.readouterr().err)
    assert st2["ops"]["check"]["solver_calls"] == 1

    # the hunt op reports its status distribution (and uses no solver)
    assert main(["--stats", "hunt", "frankl", "--universe", "5", "--steps", "100"]) == 0
    st3 = json.loads(capsys.readouterr().err)
    assert st3["ops"]["hunt"]["calls"] == 1 and st3["ops"]["hunt"]["solver_calls"] == 0
    assert st3["ops"]["hunt"]["outcomes"] == {"not_found_within_budget": 1}


def test_ag5_cli_stats_epilogue_survives_exceptions_and_never_leaks(capsys, monkeypatch):
    from mathhead.discovery import instrumentation as ins
    from mathhead.discovery import product
    from mathhead.discovery.cli import main

    ins.reset()
    ins.disable()

    def boom(statement, max_n=7):
        raise RuntimeError("engine exploded mid-call")
    monkeypatch.setattr(product, "check", boom)

    # --stats + an exception: the epilogue STILL prints (try/finally), and nothing sticks —
    # the invocation's collector is private and dies with the call
    with pytest.raises(RuntimeError, match="mid-call"):
        main(["--stats", "check", "6 | n^3 - n"])
    stats = json.loads(capsys.readouterr().err)
    assert stats["total_calls"] == 0 and stats["enabled"] is True    # died before any record
    assert not ins.enabled() and ins.snapshot()["total_calls"] == 0  # library default untouched

    # without --stats + an exception: no epilogue, and still no leakage anywhere
    with pytest.raises(RuntimeError):
        main(["check", "6 | n^3 - n"])
    assert capsys.readouterr().err == ""
    assert not ins.enabled() and ins.snapshot()["total_calls"] == 0

    # two Collectors are genuinely isolated objects (resetting one cannot touch the other)
    a, b = ins.Collector(enabled=True), ins.Collector(enabled=True)
    a.record("op", "ok", 1.0)
    b.reset()
    assert a.snapshot()["total_calls"] == 1 and b.snapshot()["total_calls"] == 0


def test_cli_check_unsupported_exits_nonzero_with_the_envelope_unchanged(capsys):
    from mathhead.discovery.cli import main

    # an honest refusal is a DISTINCT exit code (3) — a script can never mistake it for an answer
    assert main(["check", "the weather tomorrow"]) == 3
    out = capsys.readouterr().out
    assert "VERDICT: unsupported   [none]" in out               # the stdout envelope is unchanged
    assert main(["--json", "check", "the weather tomorrow"]) == 3
    assert json.loads(capsys.readouterr().out)["verdict"] == "unsupported"
    # answered verdicts keep exit 0 — refuted/open are ANSWERS, not refusals
    assert main(["check", "5 | n^3 - n"]) == 0
    assert main(["check", "clique_number <= chromatic_number", "--max-n", "4"]) == 0
    capsys.readouterr()
