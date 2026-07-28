"""
MathHead komut satırı arayüzü (CLI).

Amaç: motoru MCP/Python olmadan, doğrudan terminalden kullanılabilir kılmak
(ürünleşme adımı). Tüm komutlar aynı `router`'a ve dolayısıyla aynı çekirdeğe
gider — CLI ince bir kabuktur.

Örnekler:
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

`--json` ile ham JSON çıktı alınır. Çıkış kodu: 0 = sonuç, 1 = hata, 2 = unknown.
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
        print(f"status   : {status}")
        if data.get("reason_code"):
            print(f"reason   : {data['reason_code']}")
        if data.get("explanation"):
            print(f"açıklama : {data['explanation']}")
        if data.get("witness") is not None:
            print(f"tanık    : {data['witness']}")
        if data.get("result") is not None:
            print(f"sonuç    : {data['result']}")
        if data.get("used_premises") is not None:
            print(f"çekirdek : {data['used_premises']}  (gerekli öncül indeksleri)")
        if data.get("proof_steps"):
            print("ispat:")
            for s in data["proof_steps"]:
                ref = " " + str(s["refs"]) if s["refs"] else ""
                print(f"  {s['step']}. {s['formula']}  [{s['rule']}{ref}]")
        if "count" in data and "models" in data:
            ex = "tümü" if data.get("exhaustive") else "kısmi (daha olabilir)"
            print(f"modeller : {data['count']} ({ex})")
            for i, mdl in enumerate(data["models"], 1):
                print(f"  #{i}: {mdl}")
        if "objective_value" in data and "sense" in data:
            print(f"amaç[{data['sense']}] : {data.get('objective_value')}")
        if "satisfied_weight" in data and "total_weight" in data:
            print(f"maxsat   : {data['satisfied_weight']}/{data['total_weight']} ağırlık "
                  f"(sağlanan soft: {data.get('satisfied')})")
    if status == "error":
        return 1
    if status == "unknown":
        return 2
    return 0


def _matrix(s: str) -> list[list[str]]:
    """MATLAB-tarzı matris dizgisi -> list[list[str]]. Satır ';', hücre ',' ile.

    Ör: "1,2;3,4" -> [["1","2"],["3","4"]]. Hücreler sembolik de olabilir ("a,b;c,d").
    """
    return [[cell.strip() for cell in row.split(",")] for row in s.split(";")]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mathhead",
        description="MathHead — first-order logic temelli, deterministik matematik motoru.",
    )
    parser.add_argument("--version", action="version", version=f"mathhead {__version__}")
    parser.add_argument("--json", action="store_true", help="ham JSON çıktı ver")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("entail", help="öncüller sonucu gerektirir mi (⊨)")
    p.add_argument("-p", "--premise", action="append", default=[], metavar="İFADE")
    p.add_argument("-c", "--conclusion", required=True, metavar="İFADE")

    p = sub.add_parser("consistent", help="ifadeler aynı anda doğru olabilir mi")
    p.add_argument("statements", nargs="+", metavar="İFADE")

    p = sub.add_parser("model", help="ifadeleri sağlayan bir model bul")
    p.add_argument("statements", nargs="+", metavar="İFADE")

    p = sub.add_parser("prove", help="entailment + adım adım ispat / minimal çekirdek")
    p.add_argument("-p", "--premise", action="append", default=[], metavar="İFADE")
    p.add_argument("-c", "--conclusion", required=True, metavar="İFADE")

    p = sub.add_parser("equiv", help="iki ifade mantıksal olarak denk mi")
    p.add_argument("a", metavar="A")
    p.add_argument("b", metavar="B")

    p = sub.add_parser("classify", help="totoloji / çelişki / olumsal")
    p.add_argument("formula", metavar="İFADE")

    p = sub.add_parser("enumerate", help="tüm/çoklu modelleri numaralandır")
    p.add_argument("statements", nargs="+", metavar="İFADE")
    p.add_argument("--limit", type=int, default=10)

    p = sub.add_parser("optimize", help="kısıtlar altında bir amacı en iyile (max/min)")
    p.add_argument("objective", metavar="AMAÇ")
    p.add_argument("constraints", nargs="*", metavar="KISIT")
    p.add_argument("--min", action="store_true", help="min (varsayılan: max)")

    p = sub.add_parser("maxsat", help="hard kısıtlar + en çok soft kısıtı sağla (MaxSAT)")
    p.add_argument("--hard", action="append", default=[], metavar="KISIT")
    p.add_argument("--soft", action="append", default=[], metavar="KISIT")

    p = sub.add_parser("simplify", help="ifadeyi sadeleştir")
    p.add_argument("expression", metavar="İFADE")

    p = sub.add_parser("solve", help="denklemi bir değişken için çöz")
    p.add_argument("equation", metavar="DENKLEM")
    p.add_argument("symbol", metavar="DEĞİŞKEN")

    p = sub.add_parser("diff", help="türev al")
    p.add_argument("expression", metavar="İFADE")
    p.add_argument("symbol", metavar="DEĞİŞKEN")
    p.add_argument("--order", type=int, default=1)

    p = sub.add_parser("integrate", help="belirsiz integral al")
    p.add_argument("expression", metavar="İFADE")
    p.add_argument("symbol", metavar="DEĞİŞKEN")

    p = sub.add_parser("limit", help="limit al (nokta 'oo'/'-oo' olabilir)")
    p.add_argument("expression", metavar="İFADE")
    p.add_argument("symbol", metavar="DEĞİŞKEN")
    p.add_argument("--point", default="0", help="yaklaşılan nokta (varsayılan 0; 'oo'/'-oo' geçerli)")
    p.add_argument("--dir", dest="direction", default="both", choices=["both", "+", "-"],
                   help="tek yön için '+' veya '-' (varsayılan both). '-' için: --dir=-")

    p = sub.add_parser("series", help="Taylor/seri açılımı")
    p.add_argument("expression", metavar="İFADE")
    p.add_argument("symbol", metavar="DEĞİŞKEN")
    p.add_argument("--point", default="0", help="açılım noktası (varsayılan 0)")
    p.add_argument("--order", type=int, default=6, help="mertebe (varsayılan 6)")

    p = sub.add_parser("solve-system", help="denklem sistemini çöz (çoklu --eq/--sym)")
    p.add_argument("--eq", action="append", default=[], metavar="DENKLEM", help="bir denklem (tekrarlanabilir)")
    p.add_argument("--sym", action="append", default=[], metavar="DEĞİŞKEN", help="bir değişken (tekrarlanabilir)")

    p = sub.add_parser("det", help="determinant (matris: '1,2;3,4')")
    p.add_argument("matrix", metavar="MATRİS", help="satır ';', hücre ',' ile")

    p = sub.add_parser("inverse", help="matris tersi A⁻¹ (tekilse dürüst hata)")
    p.add_argument("matrix", metavar="MATRİS", help="satır ';', hücre ',' ile")

    p = sub.add_parser("eigenvals", help="özdeğerler + katlılık")
    p.add_argument("matrix", metavar="MATRİS", help="satır ';', hücre ',' ile")

    p = sub.add_parser("rank", help="matris rankı (kare olması şart değil)")
    p.add_argument("matrix", metavar="MATRİS", help="satır ';', hücre ',' ile")

    p = sub.add_parser("matmul", help="matris çarpımı A·B")
    p.add_argument("a", metavar="A", help="satır ';', hücre ',' ile")
    p.add_argument("b", metavar="B", help="satır ';', hücre ',' ile")

    p = sub.add_parser("matsolve", help="Ax=b doğrusal sistemi (matris formu)")
    p.add_argument("matrix", metavar="A", help="katsayı matrisi")
    p.add_argument("--b", required=True, metavar="B", help="sağ taraf vektörü, ',' ile (ör. '10,2')")

    p = sub.add_parser("eigenvectors", help="özdeğer + özvektör")
    p.add_argument("matrix", metavar="MATRİS", help="satır ';', hücre ',' ile")

    p = sub.add_parser("rref", help="indirgenmiş satır eşelon form + pivotlar")
    p.add_argument("matrix", metavar="MATRİS", help="satır ';', hücre ',' ile")

    p = sub.add_parser("nullspace", help="boş uzay (çekirdek) tabanı")
    p.add_argument("matrix", metavar="MATRİS", help="satır ';', hücre ',' ile")

    p = sub.add_parser("lu", help="LU ayrıştırma (A = P·L·U)")
    p.add_argument("matrix", metavar="MATRİS", help="satır ';', hücre ',' ile")

    p = sub.add_parser("gcd", help="en büyük ortak bölen")
    p.add_argument("a"); p.add_argument("b")

    p = sub.add_parser("lcm", help="en küçük ortak kat")
    p.add_argument("a"); p.add_argument("b")

    p = sub.add_parser("isprime", help="asallık testi")
    p.add_argument("n")

    p = sub.add_parser("factorize", help="asal çarpanlara ayır")
    p.add_argument("n")

    p = sub.add_parser("modinv", help="modüler ters a^-1 (mod m)")
    p.add_argument("a"); p.add_argument("m")

    p = sub.add_parser("crt", help="Çin Kalan Teoremi (virgüllü listeler)")
    p.add_argument("--moduli", required=True, metavar="M", help="ör. '3,5,7'")
    p.add_argument("--residues", required=True, metavar="R", help="ör. '2,3,2'")

    p = sub.add_parser("diophantine", help="a·x + b·y = c (tam sayı çözüm)")
    p.add_argument("a"); p.add_argument("b"); p.add_argument("c")

    p = sub.add_parser("pigeonhole", help="güvercin yuvası ilkesini ispatla")
    p.add_argument("n", type=int)

    p = sub.add_parser("pythagorean", help="{1..n} Pythagoras-boyaması (Track B)")
    p.add_argument("n", type=int)

    p = sub.add_parser("vdw", help="van der Waerden boyaması W(colors,k) (Track B)")
    p.add_argument("n", type=int)
    p.add_argument("k", type=int)
    p.add_argument("--colors", type=int, default=2)

    p = sub.add_parser("schur", help="Schur sayısı S(colors) boyaması (Track B)")
    p.add_argument("n", type=int)
    p.add_argument("colors", type=int)

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
    "pigeonhole": lambda a: ("pigeonhole", {"n": a.n}),
    "pythagorean": lambda a: ("pythagorean_coloring", {"n": a.n}),
    "vdw": lambda a: ("van_der_waerden", {"n": a.n, "k": a.k, "colors": a.colors}),
    "schur": lambda a: ("schur_number", {"n": a.n, "colors": a.colors}),
}


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    task, payload = _DISPATCH[args.cmd](args)
    return _emit(route(task, payload), args.json)


if __name__ == "__main__":
    sys.exit(main())
