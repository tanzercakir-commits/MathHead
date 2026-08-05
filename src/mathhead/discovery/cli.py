"""
mathhead-discover — the discovery engine's command line (v3P1).

    mathhead-discover check "6 | n^3 - n"
    mathhead-discover check "num_triangles <= num_edges" --max-n 6
    mathhead-discover bracket 3 5 --lo 13 --hi 14 --strengthen
    mathhead-discover hunt frankl --universe 8 --steps 3000
    mathhead-discover report --max-n 5

Every verdict prints its EPISTEMIC TIER — the product's honesty contract on the command line.
"""
from __future__ import annotations

import argparse
import json
import sys


def _print_check(r, as_json: bool) -> int:
    if as_json:
        print(json.dumps(r.__dict__, default=str, indent=2))
        return 0
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
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="mathhead-discover",
                                 description="Bring your conjecture — it gets refuted (with a witness), "
                                             "proved (with a kernel proof), or you learn exactly how far "
                                             "it survived. Every verdict carries its epistemic tier.")
    ap.add_argument("--json", action="store_true")
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

    if args.cmd == "check":
        from .product import check
        return _print_check(check(args.statement, max_n=args.max_n), args.json)

    if args.cmd == "bracket":
        from .ramsey_sat import ramsey_decide
        verdicts = [ramsey_decide(n, args.s, args.t, strengthen=args.strengthen)
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
        h = hunt_frankl(m=args.universe, seed=args.seed, steps=args.steps)
        if args.json:
            print(json.dumps(h.__dict__, default=str, indent=2))
            return 0
        print(f"target=frankl universe={h.universe} seed={h.seed} steps={h.steps}")
        print(f"STATUS: {h.status}  best_score={h.best_score}  (score <= -1 would be a witness; "
              f"+1 is one above the equality wall)")
        return 0

    if args.cmd == "report":
        from .report import render, run_report
        print(render(run_report(max_n=args.max_n)))
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
