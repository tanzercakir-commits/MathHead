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
    if status == "error":
        return 1
    if status == "unknown":
        return 2
    return 0


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
    "simplify": lambda a: ("simplify", {"expression": a.expression}),
    "solve": lambda a: ("solve", {"equation": a.equation, "symbol": a.symbol}),
    "diff": lambda a: ("differentiate", {"expression": a.expression, "symbol": a.symbol, "order": a.order}),
    "integrate": lambda a: ("integrate", {"expression": a.expression, "symbol": a.symbol}),
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
