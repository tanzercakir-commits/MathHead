"""
MathHead command-line interface (CLI).

Purpose: make the engine usable straight from the terminal, without MCP/Python
(a productization step). All commands go to the same `router` and hence the
same kernel — the CLI is a thin shell.

Examples:
    mathhead entail -p "p" -p "implies(p, q)" -c "q"
    mathhead entail -p "forall(x, implies(Man(x), Mortal(x)))" -p "Man(socrates)" -c "Mortal(socrates)"
    mathhead consistent "x > 2" "x < 5" "p"
    mathhead model "x > 2" "x < 5"
    mathhead simplify "sin(x)**2 + cos(x)**2"
    mathhead solve "x**2 == 4" x
    mathhead diff "x**3 + 2*x" x --order 2
    mathhead integrate "2*x" x
    mathhead limit "sin(x)/x" x --point 0
    mathhead limit "1/x" x --point oo
    mathhead series "exp(x)" x --order 5
    mathhead solve-system --eq "x + y == 10" --eq "x - y == 2" --sym x --sym y
    mathhead det "1,2;3,4"
    mathhead inverse "1,2;3,4"
    mathhead eigenvals "2,0;0,3"
    mathhead pigeonhole 4
    mathhead pythagorean 30

`--json` yields raw JSON output. Exit code: 0 = result, 1 = error, 2 = unknown.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from typing import Any

from mathhead import __version__
from mathhead.router import route


def _emit(result: Any, as_json: bool) -> int:
    data = asdict(result)
    status = data.get("status")
    if as_json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(f"status        : {status}")
        if data.get("reason_code"):
            print(f"reason        : {data['reason_code']}")
        if data.get("explanation"):
            print(f"explanation   : {data['explanation']}")
        if data.get("witness") is not None:
            print(f"witness       : {data['witness']}")
        if data.get("details") is not None:
            print(f"details       : {data['details']}")
        if "verified" in data:
            exact = "exact" if data.get("exact") else "numeric"
            print(f"verified      : {data['verified']} ({exact})")
        if data.get("interpretation") is not None:
            print(f"interpretation: {data['interpretation']}")
        if data.get("result") is not None:
            print(f"result        : {data['result']}")
        if data.get("used_premises") is not None:
            print(f"core          : {data['used_premises']}  (required premise indices)")
        if data.get("proof_steps"):
            print("proof:")
            for s in data["proof_steps"]:
                ref = " " + str(s["refs"]) if s["refs"] else ""
                print(f"  {s['step']}. {s['formula']}  [{s['rule']}{ref}]")
        if "count" in data and "models" in data:
            ex = "all" if data.get("exhaustive") else "partial (there may be more)"
            print(f"models        : {data['count']} ({ex})")
            for i, mdl in enumerate(data["models"], 1):
                print(f"  #{i}: {mdl}")
        if "objective_value" in data and "sense" in data:
            print(f"objective[{data['sense']}] : {data.get('objective_value')}")
        if "satisfied_weight" in data and "total_weight" in data:
            print(f"maxsat        : {data['satisfied_weight']}/{data['total_weight']} weight "
                  f"(satisfied soft: {data.get('satisfied')})")
    if status in ("error", "refuted"):
        return 1
    if status == "unknown":
        return 2
    return 0


def _matrix(s: str) -> list[list[str]]:
    """MATLAB-style matrix string -> list[list[str]]. Rows with ';', cells with ','.

    E.g. "1,2;3,4" -> [["1","2"],["3","4"]]. Cells may be symbolic too ("a,b;c,d").
    """
    return [[cell.strip() for cell in row.split(",")] for row in s.split(";")]


def _node(s: str) -> object:
    """Graph node from CLI text: int when it looks numeric, else the string as-is."""
    try:
        return int(s)
    except ValueError:
        return s


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mathhead",
        description="MathHead — first-order-logic-based, deterministic mathematics engine.",
    )
    parser.add_argument("--version", action="version", version=f"mathhead {__version__}")
    parser.add_argument("--json", action="store_true", help="emit raw JSON output")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("entail", help="do the premises entail the conclusion (⊨)")
    p.add_argument("-p", "--premise", action="append", default=[], metavar="EXPRESSION")
    p.add_argument("-c", "--conclusion", required=True, metavar="EXPRESSION")

    p = sub.add_parser("consistent", help="can the statements all be true at once")
    p.add_argument("statements", nargs="+", metavar="EXPRESSION")

    p = sub.add_parser("model", help="find a model satisfying the statements")
    p.add_argument("statements", nargs="+", metavar="EXPRESSION")

    p = sub.add_parser("prove", help="entailment + step-by-step proof / minimal core")
    p.add_argument("-p", "--premise", action="append", default=[], metavar="EXPRESSION")
    p.add_argument("-c", "--conclusion", required=True, metavar="EXPRESSION")

    p = sub.add_parser("equiv", help="are two expressions logically equivalent")
    p.add_argument("a", metavar="A")
    p.add_argument("b", metavar="B")

    p = sub.add_parser("classify", help="tautology / contradiction / contingent")
    p.add_argument("formula", metavar="EXPRESSION")

    p = sub.add_parser("enumerate", help="enumerate all/multiple models")
    p.add_argument("statements", nargs="+", metavar="EXPRESSION")
    p.add_argument("--limit", type=int, default=10)

    p = sub.add_parser("optimize", help="optimize an objective under constraints (max/min)")
    p.add_argument("objective", metavar="OBJECTIVE")
    p.add_argument("constraints", nargs="*", metavar="CONSTRAINT")
    p.add_argument("--min", action="store_true", help="min (default: max)")

    p = sub.add_parser("maxsat", help="hard constraints + satisfy as many soft as possible (MaxSAT)")
    p.add_argument("--hard", action="append", default=[], metavar="CONSTRAINT")
    p.add_argument("--soft", action="append", default=[], metavar="CONSTRAINT")

    p = sub.add_parser("prove-inequality", help="prove an inequality (Z3 NRA, nonlinear)")
    p.add_argument("goal", metavar="INEQUALITY", help="e.g. 'x**2 + y**2 >= 2*x*y'")
    p.add_argument("--assume", action="append", default=[], metavar="ASSUMPTION")

    p = sub.add_parser("prove-nonnegative", help="is the expression ≥ 0 (for every real)")
    p.add_argument("expression", metavar="EXPRESSION")
    p.add_argument("--assume", action="append", default=[], metavar="ASSUMPTION")

    p = sub.add_parser("real-solve", help="find a real solution to nonlinear constraints")
    p.add_argument("constraints", nargs="+", metavar="CONSTRAINT")

    p = sub.add_parser("verify-eq", help="are two expressions equivalent (incl. domain trap)")
    p.add_argument("left", metavar="LEFT"); p.add_argument("right", metavar="RIGHT")

    p = sub.add_parser("verify-solution", help="are the solutions correct + complete")
    p.add_argument("equation", metavar="EQUATION"); p.add_argument("symbol", metavar="VARIABLE")
    p.add_argument("--claim", action="append", default=[], required=True, metavar="VALUE",
                   help="claimed solution, repeatable (for a negative use --claim=-2)")

    p = sub.add_parser("verify-steps", help="find the first error in a chain of steps")
    p.add_argument("steps", nargs="+", metavar="STEP")

    p = sub.add_parser("check-derivation", help="check each step's cited operation in a derivation")
    p.add_argument("steps", nargs="+", metavar="STEP", help="steps (equations or expressions), in order")
    p.add_argument("--ops", required=True, metavar="JSON",
                   help='operations JSON, len = steps-1, e.g. \'[{"op":"subtract","value":"3"}]\'')

    p = sub.add_parser("cross-check", help="cross-verify a claim with Z3 + SymPy")
    p.add_argument("left", metavar="LEFT"); p.add_argument("right", metavar="RIGHT")

    p = sub.add_parser("check-certificate", help="verify a certificate independently (stdlib)")
    p.add_argument("certificate", metavar="JSON", help="certificate JSON (e.g. '{\"kind\":\"subset_sum\",...}')")

    p = sub.add_parser("verify-derivative", help="check a derivative claim")
    p.add_argument("expression", metavar="EXPRESSION"); p.add_argument("symbol", metavar="VARIABLE")
    p.add_argument("claimed", metavar="CLAIM"); p.add_argument("--order", type=int, default=1)

    p = sub.add_parser("verify-integral", help="check an integral claim (+C tolerated)")
    p.add_argument("expression", metavar="EXPRESSION"); p.add_argument("symbol", metavar="VARIABLE")
    p.add_argument("claimed", metavar="CLAIM")

    p = sub.add_parser("verify-limit", help="check a limit claim")
    p.add_argument("expression", metavar="EXPRESSION"); p.add_argument("symbol", metavar="VARIABLE")
    p.add_argument("--point", default="0"); p.add_argument("--claimed", required=True)

    p = sub.add_parser("verify-series", help="check a Taylor series claim")
    p.add_argument("expression", metavar="EXPRESSION"); p.add_argument("symbol", metavar="VARIABLE")
    p.add_argument("--point", default="0"); p.add_argument("--order", type=int, default=6)
    p.add_argument("--claimed", required=True)

    p = sub.add_parser("verify-matrix", help="check a matrix identity ('1,2;3,4')")
    p.add_argument("left", metavar="LEFT"); p.add_argument("right", metavar="RIGHT")

    p = sub.add_parser("interpret", help="turn natural language into a formal task (recognize-or-reject)")
    p.add_argument("text", metavar="TEXT", help="e.g. 'derivative of x**3 with respect to x'")

    p = sub.add_parser("simplify", help="simplify an expression")
    p.add_argument("expression", metavar="EXPRESSION")

    p = sub.add_parser("solve", help="solve an equation for a variable")
    p.add_argument("equation", metavar="EQUATION")
    p.add_argument("symbol", metavar="VARIABLE")

    p = sub.add_parser("diff", help="take a derivative")
    p.add_argument("expression", metavar="EXPRESSION")
    p.add_argument("symbol", metavar="VARIABLE")
    p.add_argument("--order", type=int, default=1)

    p = sub.add_parser("integrate", help="take an indefinite integral")
    p.add_argument("expression", metavar="EXPRESSION")
    p.add_argument("symbol", metavar="VARIABLE")

    p = sub.add_parser("limit", help="take a limit (point may be 'oo'/'-oo')")
    p.add_argument("expression", metavar="EXPRESSION")
    p.add_argument("symbol", metavar="VARIABLE")
    p.add_argument("--point", default="0", help="the point approached (default 0; 'oo'/'-oo' valid)")
    p.add_argument("--dir", dest="direction", default="both", choices=["both", "+", "-"],
                   help="'+' or '-' for one-sided (default both). For '-': --dir=-")

    p = sub.add_parser("series", help="Taylor/series expansion")
    p.add_argument("expression", metavar="EXPRESSION")
    p.add_argument("symbol", metavar="VARIABLE")
    p.add_argument("--point", default="0", help="expansion point (default 0)")
    p.add_argument("--order", type=int, default=6, help="order (default 6)")

    p = sub.add_parser("solve-system", help="solve a system of equations (multiple --eq/--sym)")
    p.add_argument("--eq", action="append", default=[], metavar="EQUATION", help="an equation (repeatable)")
    p.add_argument("--sym", action="append", default=[], metavar="VARIABLE", help="a variable (repeatable)")

    p = sub.add_parser("det", help="determinant (matrix: '1,2;3,4')")
    p.add_argument("matrix", metavar="MATRIX", help="rows with ';', cells with ','")

    p = sub.add_parser("inverse", help="matrix inverse A⁻¹ (honest error if singular)")
    p.add_argument("matrix", metavar="MATRIX", help="rows with ';', cells with ','")

    p = sub.add_parser("eigenvals", help="eigenvalues + multiplicity")
    p.add_argument("matrix", metavar="MATRIX", help="rows with ';', cells with ','")

    p = sub.add_parser("rank", help="matrix rank (need not be square)")
    p.add_argument("matrix", metavar="MATRIX", help="rows with ';', cells with ','")

    p = sub.add_parser("matmul", help="matrix product A·B")
    p.add_argument("a", metavar="A", help="rows with ';', cells with ','")
    p.add_argument("b", metavar="B", help="rows with ';', cells with ','")

    p = sub.add_parser("matsolve", help="Ax=b linear system (matrix form)")
    p.add_argument("matrix", metavar="A", help="coefficient matrix")
    p.add_argument("--b", required=True, metavar="B", help="right-hand-side vector, with ',' (e.g. '10,2')")

    p = sub.add_parser("eigenvectors", help="eigenvalue + eigenvector")
    p.add_argument("matrix", metavar="MATRIX", help="rows with ';', cells with ','")

    p = sub.add_parser("rref", help="reduced row echelon form + pivots")
    p.add_argument("matrix", metavar="MATRIX", help="rows with ';', cells with ','")

    p = sub.add_parser("nullspace", help="null space (kernel) basis")
    p.add_argument("matrix", metavar="MATRIX", help="rows with ';', cells with ','")

    p = sub.add_parser("lu", help="LU decomposition (A = P·L·U)")
    p.add_argument("matrix", metavar="MATRIX", help="rows with ';', cells with ','")

    p = sub.add_parser("gcd", help="greatest common divisor")
    p.add_argument("a"); p.add_argument("b")

    p = sub.add_parser("lcm", help="least common multiple")
    p.add_argument("a"); p.add_argument("b")

    p = sub.add_parser("isprime", help="primality test")
    p.add_argument("n")

    p = sub.add_parser("factorize", help="factorize into primes")
    p.add_argument("n")

    p = sub.add_parser("modinv", help="modular inverse a^-1 (mod m)")
    p.add_argument("a"); p.add_argument("m")

    p = sub.add_parser("crt", help="Chinese Remainder Theorem (comma-separated lists)")
    p.add_argument("--moduli", required=True, metavar="M", help="e.g. '3,5,7'")
    p.add_argument("--residues", required=True, metavar="R", help="e.g. '2,3,2'")

    p = sub.add_parser("diophantine", help="a·x + b·y = c (integer solution)")
    p.add_argument("a"); p.add_argument("b"); p.add_argument("c")

    p = sub.add_parser("perm", help="permutation P(n,k)")
    p.add_argument("n"); p.add_argument("k")

    p = sub.add_parser("comb", help="combination C(n,k)")
    p.add_argument("n"); p.add_argument("k")

    p = sub.add_parser("factorial", help="factorial n!")
    p.add_argument("n")

    p = sub.add_parser("partitions", help="integer partition count p(n)")
    p.add_argument("n")

    p = sub.add_parser("recurrence", help="closed-form solution of a recurrence")
    p.add_argument("recurrence", metavar="RELATION", help="e.g. 'y(n) = y(n-1) + y(n-2)'")
    p.add_argument("--func", default="y"); p.add_argument("--var", default="n")
    p.add_argument("--init", action="append", default=[], metavar="K=V",
                   help="initial condition, repeatable (e.g. --init 0=0 --init 1=1)")

    p = sub.add_parser("gradient", help="gradient ∇f (--vars comma-separated)")
    p.add_argument("expression", metavar="EXPRESSION")
    p.add_argument("--vars", required=True, metavar="X,Y", help="variables, with ','")

    p = sub.add_parser("jacobian", help="Jacobian matrix (multiple --f, --vars)")
    p.add_argument("--f", action="append", default=[], required=True, metavar="EXPRESSION")
    p.add_argument("--vars", required=True, metavar="X,Y")

    p = sub.add_parser("hessian", help="Hessian matrix (--vars comma-separated)")
    p.add_argument("expression", metavar="EXPRESSION")
    p.add_argument("--vars", required=True, metavar="X,Y")

    p = sub.add_parser("divergence", help="divergence ∇·F (--field per component, --vars)")
    p.add_argument("--field", action="append", default=[], required=True, metavar="COMPONENT")
    p.add_argument("--vars", required=True, metavar="X,Y,Z")

    p = sub.add_parser("curl", help="curl ∇×F of a 3-D field (3× --field, --vars x,y,z)")
    p.add_argument("--field", action="append", default=[], required=True, metavar="COMPONENT")
    p.add_argument("--vars", required=True, metavar="X,Y,Z")

    p = sub.add_parser("laplacian", help="Laplacian ∇²f (--vars comma-separated)")
    p.add_argument("expression", metavar="EXPRESSION")
    p.add_argument("--vars", required=True, metavar="X,Y,Z")

    p = sub.add_parser("dir-deriv", help="directional derivative ∇f·û (--vars, --dir)")
    p.add_argument("expression", metavar="EXPRESSION")
    p.add_argument("--vars", required=True, metavar="X,Y")
    p.add_argument("--dir", required=True, metavar="DX,DY", help="direction (normalized), with ','")

    p = sub.add_parser("line-integral", help="∫_C F·dr along a parametrized curve")
    p.add_argument("--field", action="append", default=[], required=True, metavar="COMPONENT")
    p.add_argument("--vars", required=True, metavar="X,Y")
    p.add_argument("--r", action="append", default=[], required=True, metavar="PARAM_EXPR",
                   help="parametrization component (per variable), in order")
    p.add_argument("--param", default="t", metavar="T")
    p.add_argument("--lower", required=True, metavar="LOWER")
    p.add_argument("--upper", required=True, metavar="UPPER")

    p = sub.add_parser("laplace", help="Laplace transform ℒ{f(t)}(s)")
    p.add_argument("expression", metavar="EXPRESSION")
    p.add_argument("--t", default="t", metavar="T", help="time variable")
    p.add_argument("--s", default="s", metavar="S", help="frequency variable")

    p = sub.add_parser("inv-laplace", help="inverse Laplace ℒ⁻¹{F(s)}(t)")
    p.add_argument("expression", metavar="EXPRESSION")
    p.add_argument("--s", default="s", metavar="S")
    p.add_argument("--t", default="t", metavar="T")

    p = sub.add_parser("fourier", help="Fourier transform ℱ{f(x)}(k)")
    p.add_argument("expression", metavar="EXPRESSION")
    p.add_argument("--x", default="x", metavar="X")
    p.add_argument("--k", default="k", metavar="K")

    p = sub.add_parser("inv-fourier", help="inverse Fourier ℱ⁻¹{F(k)}(x)")
    p.add_argument("expression", metavar="EXPRESSION")
    p.add_argument("--k", default="k", metavar="K")
    p.add_argument("--x", default="x", metavar="X")

    p = sub.add_parser("z-transform", help="Z-transform Z{x[n]}(z)")
    p.add_argument("expression", metavar="EXPRESSION")
    p.add_argument("--n", default="n", metavar="N")
    p.add_argument("--z", default="z", metavar="Z")

    p = sub.add_parser("defint", help="definite integral ∫[a,b] f dx")
    p.add_argument("expression", metavar="EXPRESSION"); p.add_argument("symbol", metavar="VARIABLE")
    p.add_argument("lower", metavar="LOWER"); p.add_argument("upper", metavar="UPPER")

    p = sub.add_parser("sum", help="summation Σ (index lower upper)")
    p.add_argument("expression", metavar="EXPRESSION"); p.add_argument("index", metavar="INDEX")
    p.add_argument("lower", metavar="LOWER"); p.add_argument("upper", metavar="UPPER")

    p = sub.add_parser("product", help="product Π (index lower upper)")
    p.add_argument("expression", metavar="EXPRESSION"); p.add_argument("index", metavar="INDEX")
    p.add_argument("lower", metavar="LOWER"); p.add_argument("upper", metavar="UPPER")

    p = sub.add_parser("ode", help="differential equation (derivative y', y'')")
    p.add_argument("equation", metavar="EQUATION", help="e.g. \"y'' + y = 0\"")
    p.add_argument("--func", default="y"); p.add_argument("--var", default="x")

    p = sub.add_parser("ode-system", help="system of ODEs (multiple --eq, --func, --var)")
    p.add_argument("--eq", action="append", default=[], required=True, metavar="EQUATION")
    p.add_argument("--func", action="append", default=[], required=True, metavar="FUNC")
    p.add_argument("--var", default="x")

    p = sub.add_parser("ode-ivp", help="ODE with initial/boundary conditions (IVP/BVP)")
    p.add_argument("equation", metavar="EQUATION", help="e.g. \"y'' + y = 0\"")
    p.add_argument("--cond", action="append", default=[], required=True, metavar="COND",
                   help="condition, e.g. \"y(0)=0\" or \"y'(0)=1\" (repeatable)")
    p.add_argument("--func", default="y")
    p.add_argument("--var", default="x")

    p = sub.add_parser("classify-ode", help="classify an ODE (solution methods)")
    p.add_argument("equation", metavar="EQUATION")
    p.add_argument("--func", default="y")
    p.add_argument("--var", default="x")

    p = sub.add_parser("pde", help="first-order linear PDE (partials via D(u,x))")
    p.add_argument("equation", metavar="EQUATION", help="e.g. \"D(u,x) + D(u,y) = 0\"")
    p.add_argument("--vars", required=True, metavar="X,Y", help="variables, with ','")
    p.add_argument("--func", default="u")

    p = sub.add_parser("residue", help="residue Res(f, z0) at a pole (complex ok, e.g. I)")
    p.add_argument("expression", metavar="EXPRESSION")
    p.add_argument("symbol", metavar="VARIABLE")
    p.add_argument("point", metavar="POINT", help="pole, e.g. 0 or I")

    p = sub.add_parser("contour", help="∮ f dz via residue theorem (--pole per enclosed pole)")
    p.add_argument("expression", metavar="EXPRESSION")
    p.add_argument("symbol", metavar="VARIABLE")
    p.add_argument("--pole", action="append", default=[], required=True, metavar="POLE")

    p = sub.add_parser("laurent", help="Laurent series (includes negative powers)")
    p.add_argument("expression", metavar="EXPRESSION")
    p.add_argument("symbol", metavar="VARIABLE")
    p.add_argument("--point", default="0", metavar="POINT")
    p.add_argument("--order", type=int, default=6)

    p = sub.add_parser("complex-parts", help="split into real + imaginary parts")
    p.add_argument("expression", metavar="EXPRESSION")

    p = sub.add_parser("perm-order", help="order of a permutation (array form '1,2,0')")
    p.add_argument("perm", metavar="PERM", help="array form, comma-separated, e.g. 1,2,0")

    p = sub.add_parser("perm-parity", help="parity of a permutation (even/odd)")
    p.add_argument("perm", metavar="PERM")

    p = sub.add_parser("perm-compose", help="compose permutations (multiple --perm)")
    p.add_argument("--perm", action="append", default=[], required=True, metavar="PERM")

    p = sub.add_parser("group-order", help="order of a named group (+ abelian)")
    p.add_argument("name", metavar="NAME", help="symmetric|alternating|cyclic|dihedral")
    p.add_argument("degree", type=int, metavar="DEGREE")

    p = sub.add_parser("gen-group", help="group order from generators (multiple --gen)")
    p.add_argument("--gen", action="append", default=[], required=True, metavar="PERM")

    p = sub.add_parser("singular-values", help="singular values of a matrix ('1,2;3,4')")
    p.add_argument("matrix", metavar="MATRIX")

    p = sub.add_parser("qr", help="QR decomposition (A = Q·R)")
    p.add_argument("matrix", metavar="MATRIX")

    p = sub.add_parser("cholesky", help="Cholesky (symmetric positive-definite)")
    p.add_argument("matrix", metavar="MATRIX")

    p = sub.add_parser("gram-schmidt", help="Gram-Schmidt (multiple --vec 'a,b,c')")
    p.add_argument("--vec", action="append", default=[], required=True, metavar="VECTOR")
    p.add_argument("--no-normalize", action="store_true", help="orthogonal but not normalized")

    p = sub.add_parser("pinv", help="Moore-Penrose pseudo-inverse")
    p.add_argument("matrix", metavar="MATRIX")

    p = sub.add_parser("matrix-exp", help="matrix exponential e^A")
    p.add_argument("matrix", metavar="MATRIX")

    p = sub.add_parser("jordan", help="Jordan canonical form")
    p.add_argument("matrix", metavar="MATRIX")

    p = sub.add_parser("charpoly", help="characteristic polynomial det(A - λI)")
    p.add_argument("matrix", metavar="MATRIX")
    p.add_argument("--symbol", default="lambda")

    p = sub.add_parser("least-squares", help="least-squares solution A x ≈ b")
    p.add_argument("matrix", metavar="MATRIX")
    p.add_argument("rhs", nargs="+", metavar="B")

    p = sub.add_parser("shortest-path", help="shortest path (edges as JSON)")
    p.add_argument("--edges", required=True, metavar="JSON", help="e.g. '[[0,1,4],[0,2,1]]'")
    p.add_argument("--source", required=True)
    p.add_argument("--target", required=True)
    p.add_argument("--directed", action="store_true")
    p.add_argument("--weighted", action="store_true")

    p = sub.add_parser("components", help="connected components (edges as JSON)")
    p.add_argument("--edges", required=True, metavar="JSON")
    p.add_argument("--nodes", metavar="JSON", help="optional node-list JSON (isolated vertices)")

    p = sub.add_parser("mst", help="minimum spanning tree (edges [u,v,w] as JSON)")
    p.add_argument("--edges", required=True, metavar="JSON")

    p = sub.add_parser("max-flow", help="max flow (directed [u,v,cap] as JSON)")
    p.add_argument("--edges", required=True, metavar="JSON")
    p.add_argument("--source", required=True)
    p.add_argument("--sink", required=True)

    p = sub.add_parser("matching", help="max bipartite matching (edges + left partition JSON)")
    p.add_argument("--edges", required=True, metavar="JSON")
    p.add_argument("--left", required=True, metavar="JSON")

    p = sub.add_parser("isomorphic", help="graph isomorphism (two edge lists JSON)")
    p.add_argument("--edges1", required=True, metavar="JSON")
    p.add_argument("--edges2", required=True, metavar="JSON")

    p = sub.add_parser("totient", help="Euler's totient φ(n)")
    p.add_argument("n", type=int)

    p = sub.add_parser("mobius", help="Möbius μ(n)")
    p.add_argument("n", type=int)

    p = sub.add_parser("cfrac", help="continued fraction of p/q")
    p.add_argument("numerator", type=int)
    p.add_argument("denominator", type=int, nargs="?", default=1)

    p = sub.add_parser("cfrac-sqrt", help="periodic continued fraction of √n")
    p.add_argument("n", type=int)

    p = sub.add_parser("quad-residue", help="is a a quadratic residue mod n")
    p.add_argument("a", type=int)
    p.add_argument("n", type=int)

    p = sub.add_parser("primitive-root", help="smallest primitive root mod n")
    p.add_argument("n", type=int)

    p = sub.add_parser("pell", help="fundamental Pell solution x²-n·y²=1")
    p.add_argument("n", type=int)

    p = sub.add_parser("catalan", help="n-th Catalan number")
    p.add_argument("n", type=int)

    p = sub.add_parser("bell", help="n-th Bell number")
    p.add_argument("n", type=int)

    p = sub.add_parser("stirling", help="Stirling number (--kind first|second)")
    p.add_argument("n", type=int)
    p.add_argument("k", type=int)
    p.add_argument("--kind", default="second", choices=["first", "second"])

    p = sub.add_parser("derangements", help="derangement count !n")
    p.add_argument("n", type=int)

    p = sub.add_parser("gf-coeff", help="coefficient of x^n in a generating function")
    p.add_argument("expression", metavar="EXPRESSION")
    p.add_argument("symbol", metavar="VARIABLE")
    p.add_argument("n", type=int)

    p = sub.add_parser("necklaces", help="distinct necklaces (n beads, colors) under rotation")
    p.add_argument("n", type=int)
    p.add_argument("colors", type=int)

    p = sub.add_parser("bayes", help="Bayes posterior from prior, likelihood, false-alarm")
    p.add_argument("prior")
    p.add_argument("likelihood")
    p.add_argument("false_alarm")

    p = sub.add_parser("covariance", help="covariance of two datasets (--sample for n-1)")
    p.add_argument("--x", nargs="+", required=True, metavar="NUMBER")
    p.add_argument("--y", nargs="+", required=True, metavar="NUMBER")
    p.add_argument("--sample", action="store_true")

    p = sub.add_parser("correlation", help="Pearson correlation of two datasets")
    p.add_argument("--x", nargs="+", required=True, metavar="NUMBER")
    p.add_argument("--y", nargs="+", required=True, metavar="NUMBER")

    p = sub.add_parser("markov-stationary", help="stationary distribution ('1/2,1/2;1/4,3/4')")
    p.add_argument("matrix", metavar="MATRIX")

    p = sub.add_parser("markov-step", help="distribution after k steps")
    p.add_argument("matrix", metavar="MATRIX")
    p.add_argument("--init", nargs="+", required=True, metavar="NUMBER")
    p.add_argument("--steps", type=int, required=True)

    p = sub.add_parser("marginal", help="marginal from a joint table (--axis row|col)")
    p.add_argument("joint", metavar="MATRIX")
    p.add_argument("--axis", default="row", choices=["row", "col"])

    p = sub.add_parser("t-test", help="t-test (one-sample vs --mu, or two-sample via --sample2)")
    p.add_argument("--sample1", nargs="+", required=True, metavar="NUMBER")
    p.add_argument("--sample2", nargs="+", metavar="NUMBER")
    p.add_argument("--mu", type=float, default=0)

    p = sub.add_parser("z-test", help="one-sample z-test (known sigma)")
    p.add_argument("--sample", nargs="+", required=True, metavar="NUMBER")
    p.add_argument("--mu", type=float, required=True)
    p.add_argument("--sigma", type=float, required=True)

    p = sub.add_parser("chi2-test", help="chi-square goodness-of-fit")
    p.add_argument("--observed", nargs="+", required=True, metavar="NUMBER")
    p.add_argument("--expected", nargs="+", required=True, metavar="NUMBER")

    p = sub.add_parser("anova", help="one-way ANOVA (--group 'a,b,c' repeatable)")
    p.add_argument("--group", action="append", default=[], required=True, metavar="GROUP")

    p = sub.add_parser("conf-interval", help="confidence interval for the mean")
    p.add_argument("data", nargs="+", metavar="NUMBER")
    p.add_argument("--confidence", type=float, default=0.95)

    p = sub.add_parser("regression", help="linear regression (--x, --y)")
    p.add_argument("--x", nargs="+", required=True, metavar="NUMBER")
    p.add_argument("--y", nargs="+", required=True, metavar="NUMBER")

    p = sub.add_parser("critical-points", help="unconstrained critical points (--vars)")
    p.add_argument("expression", metavar="EXPRESSION")
    p.add_argument("--vars", required=True, metavar="X,Y")

    p = sub.add_parser("lagrange", help="Lagrange multipliers (--constraint repeatable, --vars)")
    p.add_argument("objective", metavar="OBJECTIVE")
    p.add_argument("--constraint", action="append", default=[], required=True, metavar="G")
    p.add_argument("--vars", required=True, metavar="X,Y")

    p = sub.add_parser("convexity", help="check convexity of a function (--vars)")
    p.add_argument("expression", metavar="EXPRESSION")
    p.add_argument("--vars", required=True, metavar="X,Y")

    p = sub.add_parser("newton", help="Newton root-finding from x0")
    p.add_argument("expression", metavar="EXPRESSION")
    p.add_argument("symbol", metavar="VARIABLE")
    p.add_argument("x0", type=float)

    p = sub.add_parser("bisection", help="bisection root in [a,b] (needs a sign change)")
    p.add_argument("expression", metavar="EXPRESSION")
    p.add_argument("symbol", metavar="VARIABLE")
    p.add_argument("a", type=float)
    p.add_argument("b", type=float)

    p = sub.add_parser("secant", help="secant root from x0, x1")
    p.add_argument("expression", metavar="EXPRESSION")
    p.add_argument("symbol", metavar="VARIABLE")
    p.add_argument("x0", type=float)
    p.add_argument("x1", type=float)

    p = sub.add_parser("num-integrate", help="numerical integral (--method simpson|trapezoid)")
    p.add_argument("expression", metavar="EXPRESSION")
    p.add_argument("symbol", metavar="VARIABLE")
    p.add_argument("lower", type=float)
    p.add_argument("upper", type=float)
    p.add_argument("--method", default="simpson", choices=["simpson", "trapezoid"])
    p.add_argument("--intervals", type=int, default=100)

    p = sub.add_parser("interpolate", help="Lagrange interpolation (--points JSON, --at)")
    p.add_argument("--points", required=True, metavar="JSON", help="e.g. '[[0,1],[1,3],[2,7]]'")
    p.add_argument("--at", type=float)

    p = sub.add_parser("mean", help="arithmetic mean")
    p.add_argument("data", nargs="+", metavar="NUMBER")

    p = sub.add_parser("variance", help="variance (--sample: sample)")
    p.add_argument("data", nargs="+", metavar="NUMBER")
    p.add_argument("--sample", action="store_true")

    p = sub.add_parser("std", help="standard deviation (--sample: sample)")
    p.add_argument("data", nargs="+", metavar="NUMBER")
    p.add_argument("--sample", action="store_true")

    p = sub.add_parser("median", help="median")
    p.add_argument("data", nargs="+", metavar="NUMBER")

    p = sub.add_parser("distribution", help="distribution properties (E/Var/std [+cdf])")
    p.add_argument("name", metavar="NAME", help="normal|binomial|poisson|exponential|uniform|bernoulli|geometric")
    p.add_argument("--params", required=True, metavar="P", help="parameters with ',' (e.g. '0,1')")
    p.add_argument("--at", metavar="K", help="point for P(X<=K) + density")

    p = sub.add_parser("pigeonhole", help="prove the pigeonhole principle")
    p.add_argument("n", type=int)

    p = sub.add_parser("pythagorean", help="{1..n} Pythagorean coloring (Track B)")
    p.add_argument("n", type=int)

    p = sub.add_parser("vdw", help="van der Waerden coloring W(colors,k) (Track B)")
    p.add_argument("n", type=int)
    p.add_argument("k", type=int)
    p.add_argument("--colors", type=int, default=2)

    p = sub.add_parser("schur", help="Schur number S(colors) coloring (Track B)")
    p.add_argument("n", type=int)
    p.add_argument("colors", type=int)

    p = sub.add_parser("graph-coloring", help="graph k-coloring (Track B, verified)")
    p.add_argument("--edge", action="append", default=[], required=True, metavar="U,V",
                   help="an edge, repeatable (e.g. --edge 1,2)")
    p.add_argument("--colors", type=int, required=True)
    p.add_argument("--n", type=int, default=None, help="number of vertices (default: largest vertex)")

    p = sub.add_parser("subset-sum", help="subset sum (Track B, verified)")
    p.add_argument("numbers", nargs="+", type=int, metavar="NUMBER")
    p.add_argument("--target", type=int, required=True)

    return parser


_DISPATCH = {
    "entail": lambda a: ("entailment", {"premises": a.premise, "conclusion": a.conclusion}),
    "consistent": lambda a: ("consistency", {"statements": a.statements}),
    "model": lambda a: ("find_model", {"statements": a.statements}),
    "prove": lambda a: ("prove", {"premises": a.premise, "conclusion": a.conclusion}),
    "equiv": lambda a: ("equivalent", {"a": a.a, "b": a.b}),
    "classify": lambda a: ("classify", {"formula": a.formula}),
    "enumerate": lambda a: ("enumerate", {"statements": a.statements, "limit": a.limit}),
    "optimize": lambda a: ("optimize", {"constraints": a.constraints, "objective": a.objective,
                                        "sense": "min" if a.min else "max"}),
    "maxsat": lambda a: ("maxsat", {"hard": a.hard, "soft": a.soft}),
    "prove-inequality": lambda a: ("prove_inequality", {"goal": a.goal, "assumptions": a.assume}),
    "prove-nonnegative": lambda a: ("prove_nonnegative", {"expression": a.expression, "assumptions": a.assume}),
    "real-solve": lambda a: ("find_real_solution", {"constraints": a.constraints}),
    "verify-eq": lambda a: ("verify_equality", {"left": a.left, "right": a.right}),
    "verify-solution": lambda a: ("verify_solution", {"equation": a.equation,
                                                      "symbol": a.symbol, "claimed": a.claim}),
    "verify-steps": lambda a: ("verify_steps", {"steps": a.steps}),
    "check-derivation": lambda a: ("verify_derivation",
                                   {"steps": a.steps, "operations": json.loads(a.ops)}),
    "cross-check": lambda a: ("cross_check", {"left": a.left, "right": a.right}),
    "check-certificate": lambda a: ("check_certificate", {"certificate": json.loads(a.certificate)}),
    "verify-derivative": lambda a: ("verify_derivative", {"expression": a.expression,
                                    "symbol": a.symbol, "claimed": a.claimed, "order": a.order}),
    "verify-integral": lambda a: ("verify_integral", {"expression": a.expression,
                                  "symbol": a.symbol, "claimed": a.claimed}),
    "verify-limit": lambda a: ("verify_limit", {"expression": a.expression, "symbol": a.symbol,
                               "point": a.point, "claimed": a.claimed}),
    "verify-series": lambda a: ("verify_series", {"expression": a.expression, "symbol": a.symbol,
                                "point": a.point, "order": a.order, "claimed": a.claimed}),
    "verify-matrix": lambda a: ("verify_matrix_identity", {"left": _matrix(a.left),
                                "right": _matrix(a.right)}),
    "interpret": lambda a: ("interpret_natural", {"text": a.text}),
    "simplify": lambda a: ("simplify", {"expression": a.expression}),
    "solve": lambda a: ("solve", {"equation": a.equation, "symbol": a.symbol}),
    "diff": lambda a: ("differentiate", {"expression": a.expression, "symbol": a.symbol, "order": a.order}),
    "integrate": lambda a: ("integrate", {"expression": a.expression, "symbol": a.symbol}),
    "limit": lambda a: ("limit", {"expression": a.expression, "symbol": a.symbol,
                                  "point": a.point, "direction": a.direction}),
    "series": lambda a: ("series", {"expression": a.expression, "symbol": a.symbol,
                                    "point": a.point, "order": a.order}),
    "solve-system": lambda a: ("solve_system", {"equations": a.eq, "symbols": a.sym}),
    "det": lambda a: ("determinant", {"matrix": _matrix(a.matrix)}),
    "inverse": lambda a: ("matrix_inverse", {"matrix": _matrix(a.matrix)}),
    "eigenvals": lambda a: ("eigenvalues", {"matrix": _matrix(a.matrix)}),
    "rank": lambda a: ("matrix_rank", {"matrix": _matrix(a.matrix)}),
    "matmul": lambda a: ("matrix_multiply", {"a": _matrix(a.a), "b": _matrix(a.b)}),
    "matsolve": lambda a: ("matrix_solve", {"matrix": _matrix(a.matrix),
                                            "rhs": [c.strip() for c in a.b.split(",")]}),
    "eigenvectors": lambda a: ("eigenvectors", {"matrix": _matrix(a.matrix)}),
    "rref": lambda a: ("rref", {"matrix": _matrix(a.matrix)}),
    "nullspace": lambda a: ("nullspace", {"matrix": _matrix(a.matrix)}),
    "lu": lambda a: ("lu_decomposition", {"matrix": _matrix(a.matrix)}),
    "gcd": lambda a: ("gcd", {"a": a.a, "b": a.b}),
    "lcm": lambda a: ("lcm", {"a": a.a, "b": a.b}),
    "isprime": lambda a: ("is_prime", {"n": a.n}),
    "factorize": lambda a: ("factorize", {"n": a.n}),
    "modinv": lambda a: ("modular_inverse", {"a": a.a, "m": a.m}),
    "crt": lambda a: ("chinese_remainder", {"moduli": [c.strip() for c in a.moduli.split(",")],
                                            "residues": [c.strip() for c in a.residues.split(",")]}),
    "diophantine": lambda a: ("linear_diophantine", {"a": a.a, "b": a.b, "c": a.c}),
    "perm": lambda a: ("permutations", {"n": a.n, "k": a.k}),
    "comb": lambda a: ("combinations", {"n": a.n, "k": a.k}),
    "factorial": lambda a: ("factorial", {"n": a.n}),
    "partitions": lambda a: ("partition_count", {"n": a.n}),
    "recurrence": lambda a: ("solve_recurrence", {
        "recurrence": a.recurrence, "func": a.func, "var": a.var,
        "initial": dict(kv.split("=", 1) for kv in a.init),
    }),
    "gradient": lambda a: ("gradient", {"expression": a.expression,
                                        "variables": [v.strip() for v in a.vars.split(",")]}),
    "jacobian": lambda a: ("jacobian", {"expressions": a.f,
                                        "variables": [v.strip() for v in a.vars.split(",")]}),
    "hessian": lambda a: ("hessian", {"expression": a.expression,
                                      "variables": [v.strip() for v in a.vars.split(",")]}),
    "divergence": lambda a: ("divergence", {"field": a.field,
                                            "variables": [v.strip() for v in a.vars.split(",")]}),
    "curl": lambda a: ("curl", {"field": a.field,
                                "variables": [v.strip() for v in a.vars.split(",")]}),
    "laplacian": lambda a: ("laplacian", {"expression": a.expression,
                                          "variables": [v.strip() for v in a.vars.split(",")]}),
    "dir-deriv": lambda a: ("directional_derivative",
                            {"expression": a.expression,
                             "variables": [v.strip() for v in a.vars.split(",")],
                             "direction": [d.strip() for d in a.dir.split(",")]}),
    "line-integral": lambda a: ("line_integral",
                                {"field": a.field,
                                 "variables": [v.strip() for v in a.vars.split(",")],
                                 "parametrization": a.r, "param": a.param,
                                 "lower": a.lower, "upper": a.upper}),
    "laplace": lambda a: ("laplace_transform",
                          {"expression": a.expression, "t_var": a.t, "s_var": a.s}),
    "inv-laplace": lambda a: ("inverse_laplace_transform",
                              {"expression": a.expression, "s_var": a.s, "t_var": a.t}),
    "fourier": lambda a: ("fourier_transform",
                          {"expression": a.expression, "x_var": a.x, "k_var": a.k}),
    "inv-fourier": lambda a: ("inverse_fourier_transform",
                              {"expression": a.expression, "k_var": a.k, "x_var": a.x}),
    "z-transform": lambda a: ("z_transform",
                              {"expression": a.expression, "n_var": a.n, "z_var": a.z}),
    "defint": lambda a: ("definite_integral", {"expression": a.expression, "symbol": a.symbol,
                                               "lower": a.lower, "upper": a.upper}),
    "sum": lambda a: ("summation", {"expression": a.expression, "index": a.index,
                                    "lower": a.lower, "upper": a.upper}),
    "product": lambda a: ("product", {"expression": a.expression, "index": a.index,
                                      "lower": a.lower, "upper": a.upper}),
    "ode": lambda a: ("solve_ode", {"equation": a.equation, "func": a.func, "var": a.var}),
    "ode-system": lambda a: ("solve_ode_system",
                             {"equations": a.eq, "functions": a.func, "var": a.var}),
    "ode-ivp": lambda a: ("solve_ode_ivp",
                          {"equation": a.equation, "conditions": a.cond,
                           "func": a.func, "var": a.var}),
    "classify-ode": lambda a: ("classify_ode",
                               {"equation": a.equation, "func": a.func, "var": a.var}),
    "pde": lambda a: ("solve_pde",
                      {"equation": a.equation, "func": a.func,
                       "variables": [v.strip() for v in a.vars.split(",")]}),
    "residue": lambda a: ("residue",
                          {"expression": a.expression, "symbol": a.symbol, "point": a.point}),
    "contour": lambda a: ("contour_integral",
                          {"expression": a.expression, "symbol": a.symbol, "poles": a.pole}),
    "laurent": lambda a: ("laurent_series",
                          {"expression": a.expression, "symbol": a.symbol,
                           "point": a.point, "order": a.order}),
    "complex-parts": lambda a: ("complex_parts", {"expression": a.expression}),
    "perm-order": lambda a: ("permutation_order", {"permutation": a.perm.split(",")}),
    "perm-parity": lambda a: ("permutation_parity", {"permutation": a.perm.split(",")}),
    "perm-compose": lambda a: ("permutation_compose",
                               {"permutations": [p.split(",") for p in a.perm]}),
    "group-order": lambda a: ("group_order", {"name": a.name, "degree": a.degree}),
    "gen-group": lambda a: ("generated_group",
                            {"generators": [g.split(",") for g in a.gen]}),
    "singular-values": lambda a: ("singular_values", {"matrix": _matrix(a.matrix)}),
    "qr": lambda a: ("qr_decomposition", {"matrix": _matrix(a.matrix)}),
    "cholesky": lambda a: ("cholesky_decomposition", {"matrix": _matrix(a.matrix)}),
    "gram-schmidt": lambda a: ("gram_schmidt",
                               {"vectors": [v.split(",") for v in a.vec],
                                "normalize": not a.no_normalize}),
    "pinv": lambda a: ("pseudoinverse", {"matrix": _matrix(a.matrix)}),
    "matrix-exp": lambda a: ("matrix_exponential", {"matrix": _matrix(a.matrix)}),
    "jordan": lambda a: ("jordan_form", {"matrix": _matrix(a.matrix)}),
    "charpoly": lambda a: ("characteristic_polynomial",
                           {"matrix": _matrix(a.matrix), "symbol": a.symbol}),
    "least-squares": lambda a: ("least_squares",
                                {"matrix": _matrix(a.matrix), "rhs": a.rhs}),
    "shortest-path": lambda a: ("shortest_path",
                                {"edges": json.loads(a.edges), "source": _node(a.source),
                                 "target": _node(a.target), "directed": a.directed,
                                 "weighted": a.weighted}),
    "components": lambda a: ("connected_components",
                             {"edges": json.loads(a.edges),
                              "nodes": json.loads(a.nodes) if a.nodes else None}),
    "mst": lambda a: ("minimum_spanning_tree", {"edges": json.loads(a.edges)}),
    "max-flow": lambda a: ("max_flow",
                           {"edges": json.loads(a.edges), "source": _node(a.source),
                            "sink": _node(a.sink)}),
    "matching": lambda a: ("maximum_matching",
                           {"edges": json.loads(a.edges), "left": json.loads(a.left)}),
    "isomorphic": lambda a: ("is_isomorphic",
                             {"edges1": json.loads(a.edges1), "edges2": json.loads(a.edges2)}),
    "totient": lambda a: ("euler_totient", {"n": a.n}),
    "mobius": lambda a: ("mobius", {"n": a.n}),
    "cfrac": lambda a: ("continued_fraction",
                        {"numerator": a.numerator, "denominator": a.denominator}),
    "cfrac-sqrt": lambda a: ("continued_fraction_sqrt", {"n": a.n}),
    "quad-residue": lambda a: ("quadratic_residue", {"a": a.a, "n": a.n}),
    "primitive-root": lambda a: ("primitive_root", {"n": a.n}),
    "pell": lambda a: ("pell_solution", {"n": a.n}),
    "catalan": lambda a: ("catalan_number", {"n": a.n}),
    "bell": lambda a: ("bell_number", {"n": a.n}),
    "stirling": lambda a: ("stirling_number", {"n": a.n, "k": a.k, "kind": a.kind}),
    "derangements": lambda a: ("derangements", {"n": a.n}),
    "gf-coeff": lambda a: ("generating_function_coefficient",
                           {"expression": a.expression, "symbol": a.symbol, "n": a.n}),
    "necklaces": lambda a: ("necklace_count", {"n": a.n, "colors": a.colors}),
    "bayes": lambda a: ("bayes_theorem",
                        {"prior": a.prior, "likelihood": a.likelihood, "false_alarm": a.false_alarm}),
    "covariance": lambda a: ("covariance", {"x": a.x, "y": a.y, "sample": a.sample}),
    "correlation": lambda a: ("correlation", {"x": a.x, "y": a.y}),
    "markov-stationary": lambda a: ("markov_stationary", {"matrix": _matrix(a.matrix)}),
    "markov-step": lambda a: ("markov_step",
                              {"matrix": _matrix(a.matrix), "initial": a.init, "steps": a.steps}),
    "marginal": lambda a: ("joint_marginal", {"joint": _matrix(a.joint), "axis": a.axis}),
    "t-test": lambda a: ("t_test", {"sample1": a.sample1, "sample2": a.sample2, "mu": a.mu}),
    "z-test": lambda a: ("z_test", {"sample": a.sample, "mu": a.mu, "sigma": a.sigma}),
    "chi2-test": lambda a: ("chi_square_test", {"observed": a.observed, "expected": a.expected}),
    "anova": lambda a: ("anova_oneway", {"groups": [g.split(",") for g in a.group]}),
    "conf-interval": lambda a: ("confidence_interval",
                                {"data": a.data, "confidence": a.confidence}),
    "regression": lambda a: ("linear_regression", {"x": a.x, "y": a.y}),
    "critical-points": lambda a: ("critical_points",
                                  {"expression": a.expression,
                                   "variables": [v.strip() for v in a.vars.split(",")]}),
    "lagrange": lambda a: ("lagrange_multipliers",
                           {"objective": a.objective, "constraints": a.constraint,
                            "variables": [v.strip() for v in a.vars.split(",")]}),
    "convexity": lambda a: ("check_convexity",
                            {"expression": a.expression,
                             "variables": [v.strip() for v in a.vars.split(",")]}),
    "newton": lambda a: ("find_root_newton",
                         {"expression": a.expression, "symbol": a.symbol, "x0": a.x0}),
    "bisection": lambda a: ("find_root_bisection",
                            {"expression": a.expression, "symbol": a.symbol, "a": a.a, "b": a.b}),
    "secant": lambda a: ("find_root_secant",
                         {"expression": a.expression, "symbol": a.symbol, "x0": a.x0, "x1": a.x1}),
    "num-integrate": lambda a: ("numerical_integrate",
                                {"expression": a.expression, "symbol": a.symbol, "lower": a.lower,
                                 "upper": a.upper, "method": a.method, "intervals": a.intervals}),
    "interpolate": lambda a: ("interpolate",
                              {"points": json.loads(a.points), "at": a.at}),
    "mean": lambda a: ("mean", {"data": a.data}),
    "variance": lambda a: ("variance", {"data": a.data, "sample": a.sample}),
    "std": lambda a: ("standard_deviation", {"data": a.data, "sample": a.sample}),
    "median": lambda a: ("median", {"data": a.data}),
    "distribution": lambda a: ("distribution", {"name": a.name,
                                                "params": [p.strip() for p in a.params.split(",")],
                                                "at": a.at}),
    "pigeonhole": lambda a: ("pigeonhole", {"n": a.n}),
    "pythagorean": lambda a: ("pythagorean_coloring", {"n": a.n}),
    "vdw": lambda a: ("van_der_waerden", {"n": a.n, "k": a.k, "colors": a.colors}),
    "schur": lambda a: ("schur_number", {"n": a.n, "colors": a.colors}),
    "graph-coloring": lambda a: ("graph_coloring", {
        "edges": [[int(x) for x in e.split(",")] for e in a.edge],
        "colors": a.colors, "n": a.n,
    }),
    "subset-sum": lambda a: ("subset_sum", {"numbers": a.numbers, "target": a.target}),
}


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    task, payload = _DISPATCH[args.cmd](args)
    return _emit(route(task, payload), args.json)


if __name__ == "__main__":
    sys.exit(main())
