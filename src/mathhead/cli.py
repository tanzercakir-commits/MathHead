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
        if data.get("details") is not None:
            print(f"ayrıntı  : {data['details']}")
        if "verified" in data:
            exact = "tam" if data.get("exact") else "sayısal"
            print(f"doğrulama: {data['verified']} ({exact})")
        if data.get("interpretation") is not None:
            print(f"yorum    : {data['interpretation']}")
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
    if status in ("error", "refuted"):
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

    p = sub.add_parser("prove-inequality", help="eşitsizliği ispatla (Z3 NRA, nonlineer)")
    p.add_argument("goal", metavar="EŞİTSİZLİK", help="ör. 'x**2 + y**2 >= 2*x*y'")
    p.add_argument("--assume", action="append", default=[], metavar="VARSAYIM")

    p = sub.add_parser("prove-nonnegative", help="ifade ≥ 0 mı (her gerçel için)")
    p.add_argument("expression", metavar="İFADE")
    p.add_argument("--assume", action="append", default=[], metavar="VARSAYIM")

    p = sub.add_parser("real-solve", help="nonlineer kısıtlara gerçel çözüm bul")
    p.add_argument("constraints", nargs="+", metavar="KISIT")

    p = sub.add_parser("verify-eq", help="iki ifade denk mi (domain tuzağı dahil)")
    p.add_argument("left", metavar="SOL"); p.add_argument("right", metavar="SAĞ")

    p = sub.add_parser("verify-solution", help="çözümler doğru + tam mı")
    p.add_argument("equation", metavar="DENKLEM"); p.add_argument("symbol", metavar="DEĞİŞKEN")
    p.add_argument("--claim", action="append", default=[], required=True, metavar="DEĞER",
                   help="iddia edilen çözüm, tekrarlanabilir (negatif için --claim=-2)")

    p = sub.add_parser("verify-steps", help="adım zincirinde ilk hatayı bul")
    p.add_argument("steps", nargs="+", metavar="ADIM")

    p = sub.add_parser("cross-check", help="iddiayı Z3 + SymPy ile çapraz doğrula")
    p.add_argument("left", metavar="SOL"); p.add_argument("right", metavar="SAĞ")

    p = sub.add_parser("check-certificate", help="sertifikayı bağımsız (stdlib) doğrula")
    p.add_argument("certificate", metavar="JSON", help="sertifika JSON'u (ör. '{\"kind\":\"subset_sum\",...}')")

    p = sub.add_parser("verify-derivative", help="türev iddiasını denetle")
    p.add_argument("expression", metavar="İFADE"); p.add_argument("symbol", metavar="DEĞİŞKEN")
    p.add_argument("claimed", metavar="İDDİA"); p.add_argument("--order", type=int, default=1)

    p = sub.add_parser("verify-integral", help="integral iddiasını denetle (+C hoşgörülür)")
    p.add_argument("expression", metavar="İFADE"); p.add_argument("symbol", metavar="DEĞİŞKEN")
    p.add_argument("claimed", metavar="İDDİA")

    p = sub.add_parser("verify-limit", help="limit iddiasını denetle")
    p.add_argument("expression", metavar="İFADE"); p.add_argument("symbol", metavar="DEĞİŞKEN")
    p.add_argument("--point", default="0"); p.add_argument("--claimed", required=True)

    p = sub.add_parser("verify-series", help="Taylor serisi iddiasını denetle")
    p.add_argument("expression", metavar="İFADE"); p.add_argument("symbol", metavar="DEĞİŞKEN")
    p.add_argument("--point", default="0"); p.add_argument("--order", type=int, default=6)
    p.add_argument("--claimed", required=True)

    p = sub.add_parser("verify-matrix", help="matris özdeşliği denetle ('1,2;3,4')")
    p.add_argument("left", metavar="SOL"); p.add_argument("right", metavar="SAĞ")

    p = sub.add_parser("interpret", help="doğal dili formal göreve çevir (tanı-ya-da-reddet)")
    p.add_argument("text", metavar="METİN", help="ör. 'x**3 ifadesinin x e göre türevi'")

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

    p = sub.add_parser("perm", help="permütasyon P(n,k)")
    p.add_argument("n"); p.add_argument("k")

    p = sub.add_parser("comb", help="kombinasyon C(n,k)")
    p.add_argument("n"); p.add_argument("k")

    p = sub.add_parser("factorial", help="faktöriyel n!")
    p.add_argument("n")

    p = sub.add_parser("partitions", help="tam sayı bölüntü sayısı p(n)")
    p.add_argument("n")

    p = sub.add_parser("recurrence", help="özyineleme kapalı-form çözümü")
    p.add_argument("recurrence", metavar="BAĞINTI", help="ör. 'y(n) = y(n-1) + y(n-2)'")
    p.add_argument("--func", default="y"); p.add_argument("--var", default="n")
    p.add_argument("--init", action="append", default=[], metavar="K=V",
                   help="başlangıç koşulu, tekrarlanabilir (ör. --init 0=0 --init 1=1)")

    p = sub.add_parser("gradient", help="gradyan ∇f (--vars virgüllü)")
    p.add_argument("expression", metavar="İFADE")
    p.add_argument("--vars", required=True, metavar="X,Y", help="değişkenler, ',' ile")

    p = sub.add_parser("jacobian", help="Jacobian matrisi (çoklu --f, --vars)")
    p.add_argument("--f", action="append", default=[], required=True, metavar="İFADE")
    p.add_argument("--vars", required=True, metavar="X,Y")

    p = sub.add_parser("hessian", help="Hessian matrisi (--vars virgüllü)")
    p.add_argument("expression", metavar="İFADE")
    p.add_argument("--vars", required=True, metavar="X,Y")

    p = sub.add_parser("defint", help="belirli integral ∫[a,b] f dx")
    p.add_argument("expression", metavar="İFADE"); p.add_argument("symbol", metavar="DEĞİŞKEN")
    p.add_argument("lower", metavar="ALT"); p.add_argument("upper", metavar="ÜST")

    p = sub.add_parser("sum", help="toplam Σ (index alt üst)")
    p.add_argument("expression", metavar="İFADE"); p.add_argument("index", metavar="İNDİS")
    p.add_argument("lower", metavar="ALT"); p.add_argument("upper", metavar="ÜST")

    p = sub.add_parser("product", help="çarpım Π (index alt üst)")
    p.add_argument("expression", metavar="İFADE"); p.add_argument("index", metavar="İNDİS")
    p.add_argument("lower", metavar="ALT"); p.add_argument("upper", metavar="ÜST")

    p = sub.add_parser("ode", help="diferansiyel denklem (türev y', y'')")
    p.add_argument("equation", metavar="DENKLEM", help="ör. \"y'' + y = 0\"")
    p.add_argument("--func", default="y"); p.add_argument("--var", default="x")

    p = sub.add_parser("mean", help="aritmetik ortalama")
    p.add_argument("data", nargs="+", metavar="SAYI")

    p = sub.add_parser("variance", help="varyans (--sample: örneklem)")
    p.add_argument("data", nargs="+", metavar="SAYI")
    p.add_argument("--sample", action="store_true")

    p = sub.add_parser("std", help="standart sapma (--sample: örneklem)")
    p.add_argument("data", nargs="+", metavar="SAYI")
    p.add_argument("--sample", action="store_true")

    p = sub.add_parser("median", help="ortanca")
    p.add_argument("data", nargs="+", metavar="SAYI")

    p = sub.add_parser("distribution", help="dağılım özellikleri (E/Var/std [+cdf])")
    p.add_argument("name", metavar="AD", help="normal|binomial|poisson|exponential|uniform|bernoulli|geometric")
    p.add_argument("--params", required=True, metavar="P", help="parametreler ',' ile (ör. '0,1')")
    p.add_argument("--at", metavar="K", help="P(X<=K) + yoğunluk için nokta")

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

    p = sub.add_parser("graph-coloring", help="graf k-boyama (Track B, doğrulanmış)")
    p.add_argument("--edge", action="append", default=[], required=True, metavar="U,V",
                   help="bir kenar, tekrarlanabilir (ör. --edge 1,2)")
    p.add_argument("--colors", type=int, required=True)
    p.add_argument("--n", type=int, default=None, help="köşe sayısı (varsayılan: en büyük köşe)")

    p = sub.add_parser("subset-sum", help="alt küme toplamı (Track B, doğrulanmış)")
    p.add_argument("numbers", nargs="+", type=int, metavar="SAYI")
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
    "defint": lambda a: ("definite_integral", {"expression": a.expression, "symbol": a.symbol,
                                               "lower": a.lower, "upper": a.upper}),
    "sum": lambda a: ("summation", {"expression": a.expression, "index": a.index,
                                    "lower": a.lower, "upper": a.upper}),
    "product": lambda a: ("product", {"expression": a.expression, "index": a.index,
                                      "lower": a.lower, "upper": a.upper}),
    "ode": lambda a: ("solve_ode", {"equation": a.equation, "func": a.func, "var": a.var}),
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
