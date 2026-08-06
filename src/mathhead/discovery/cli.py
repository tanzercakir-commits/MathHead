"""
mathhead-discover — the discovery engine's command line (v3P1).

    mathhead-discover check "6 | n^3 - n"
    mathhead-discover check "num_triangles <= num_edges" --max-n 6
    mathhead-discover bracket 3 5 --lo 13 --hi 14 --strengthen
    mathhead-discover hunt frankl --universe 8 --steps 3000
    mathhead-discover report --max-n 5

Every verdict prints its EPISTEMIC TIER — the product's honesty contract on the command line.

Exit codes for `check`: 0 = the engine answered (proved / refuted / open); 3 = `unsupported`
(an honest refusal — non-zero so scripts cannot mistake a refusal for an answer); argparse
usage errors exit 2 as usual. The stdout envelope is identical in every case.

`--stats` (AG5) additionally prints a local JSON metrics block (durations, verdict distribution,
solver-call counts) to STDERR — stdout keeps its documented contract, and nothing leaves the
machine (no external telemetry). The counters live on a PRIVATE Collector for the one
invocation (printed in a try/finally epilogue, so even an exception cannot leak state or skip
the block), never on the library-level default collector.
"""
from __future__ import annotations

import argparse
import json
import sys

_UNSUPPORTED_EXIT = 3     # honest refusal ≠ answer: scripts must be able to tell them apart


def _print_check(r, as_json: bool) -> int:
    code = _UNSUPPORTED_EXIT if r.verdict == "unsupported" else 0
    if as_json:
        print(json.dumps(r.__dict__, default=str, indent=2))
        return code
    print(f"VERDICT: {r.verdict}   [{r.tier}]")
    print(f"  statement : {r.statement}")
    if r.witness:
        print(f"  witness   : {r.witness}")
    if r.checked_up_to:
        print(f"  checked   : {r.checked_up_to}")
    if r.proof_hash:
        print(f"  proof     : kernel hash {r.proof_hash}")
    if r.notes:
        print(f"  note      : {r.notes}")
    if getattr(r, "readings", ()):
        # v1 readings feature: the SAME text under its 3 candidate quantifier readings, each with
        # its own honest verdict. Appended AFTER the classic envelope — every line above and the
        # exit-code contract are byte-identical to the pre-readings CLI.
        print("  readings  : the same text under 3 candidate quantifier readings —")
        for e in r.readings:
            print(f"    [{e['label']}] {e['verdict']:<10} [{e['tier']}]  {e['assumption_delta']}")
    return code


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="mathhead-discover",
                                 description="Bring your conjecture — it gets refuted (with a witness), "
                                             "proved (with a kernel proof), or you learn exactly how far "
                                             "it survived. Every verdict carries its epistemic tier.")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--stats", action="store_true",
                    help="print a local JSON metrics block (durations, verdict distribution, "
                         "solver calls) to stderr — no external telemetry")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("check", help="check a statement (modular / congruence / sums / graph / "
                                     "permutations / partitions / compositions)")
    p.add_argument("statement")
    p.add_argument("--max-n", type=int, default=7,
                   help="scan bound (connected graphs; permutation scans cap honestly at 7)")

    p = sub.add_parser("bracket", help="bracket a Ramsey number R(s,t) by SAT")
    p.add_argument("s", type=int)
    p.add_argument("t", type=int)
    p.add_argument("--lo", type=int, required=True)
    p.add_argument("--hi", type=int, required=True)
    p.add_argument("--strengthen", action="store_true",
                   help="add derived degree lemmas (verdict tier says so honestly)")

    p = sub.add_parser("hunt", help="adversarial counterexample hunt")
    p.add_argument("target", choices=["frankl"])
    p.add_argument("--universe", type=int, default=7)
    p.add_argument("--steps", type=int, default=2000)
    p.add_argument("--seed", type=int, default=0)

    p = sub.add_parser("report", help="the full deterministic discovery report (markdown)")
    p.add_argument("--max-n", type=int, default=5)

    args = ap.parse_args(argv)
    # AG5: a PRIVATE Collector per invocation (enabled only under --stats). Not the module-level
    # default — a CLI run can never reset or pollute a library user's counters. The epilogue sits
    # in try/finally, so "never sticky" holds on the exception path too (the local collector dies
    # with this call either way, and the stats block is still emitted for the work done so far).
    from .instrumentation import Collector
    stats = Collector(enabled=args.stats)
    try:
        return _dispatch(args, stats)
    finally:
        if args.stats:
            print(stats.dump_json(), file=sys.stderr)   # stderr: stdout contract unchanged


def _dispatch(args, ins) -> int:
    """Route one parsed invocation; `ins` is the invocation's PRIVATE metrics Collector
    (disabled ⇒ pure passthrough)."""
    if args.cmd == "check":
        from .product import check
        r = ins.observe("check", check, args.statement, max_n=args.max_n,
                        _outcome=lambda r: r.verdict,
                        # the sum-inequality proof attempt is the one z3 route on this surface
                        _solver_calls=lambda r: int(
                            "core.inequality.prove_inequality" in r.instruments))
        return _print_check(r, args.json)

    if args.cmd == "bracket":
        from .ramsey_sat import ramsey_decide
        verdicts = [ins.observe("bracket", ramsey_decide, n, args.s, args.t,
                                strengthen=args.strengthen,
                                _outcome=lambda v: "SAT" if v.satisfiable else "UNSAT",
                                _solver_calls=lambda _v: 1)   # one SAT-solver call per instance
                    for n in range(args.lo, args.hi + 1)]
        value = None
        for prev, cur in zip(verdicts, verdicts[1:]):
            if prev.satisfiable and not cur.satisfiable:
                value = cur.n
        if args.json:
            print(json.dumps({"value": value,
                              "verdicts": [v.__dict__ for v in verdicts]}, default=str, indent=2))
            return 0
        for v in verdicts:
            print(f"n={v.n}: {'SAT' if v.satisfiable else 'UNSAT'}  [{v.certainty}]  → {v.meaning}")
            for lem in v.lemmas_used:
                print(f"        lemma: {lem}")
        print(f"R({args.s},{args.t}) = {value}" if value is not None
              else "flip not inside the range — no value claimed (honest)")
        return 0

    if args.cmd == "hunt":
        from .frankl import hunt_frankl
        h = ins.observe("hunt", hunt_frankl, m=args.universe, seed=args.seed, steps=args.steps,
                        _outcome=lambda h: h.status)
        if args.json:
            print(json.dumps(h.__dict__, default=str, indent=2))
            return 0
        print(f"target=frankl universe={h.universe} seed={h.seed} steps={h.steps}")
        print(f"STATUS: {h.status}  best_score={h.best_score}  (score <= -1 would be a witness; "
              f"+1 is one above the equality wall)")
        return 0

    if args.cmd == "report":
        from .report import render, run_report
        print(ins.observe("report", lambda: render(run_report(max_n=args.max_n)),
                          _outcome=lambda _t: "rendered"))
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
