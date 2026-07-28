"""
mathhead.server.mcp_server
==========================

MathHead'in MCP (Model Context Protocol) arayüzü. AI istemcisi (ör. Claude)
motorun yeteneklerine SADECE buradaki araçlar (tools) üzerinden erişir. Bu
katman "net protokol & API tanımı" prensibinin uygulama noktasıdır.

SDK: `mcp` (FastMCP), Python 3.10+. Kurulum: `pip install "mcp[cli]"`.
Çalıştırma (yerel): `mathhead-server`  ya da  `python -m mathhead.server.mcp_server`

Akış: server -> router -> (guardrails + core/Z3). Araç imzaları ve dönüş şekli
docs/mcp-api.md ile birebir aynıdır (ADR-0004: erken donduruldu).
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Any

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:  # guardrail: bağımlılık yoksa net mesaj
    raise SystemExit(
        "MCP SDK bulunamadı. Kurulum: pip install 'mcp[cli]'  (bkz. pyproject.toml)"
    ) from exc

from mathhead.router import route

mcp = FastMCP("MathHead")


@mcp.tool()
def entailment(premises: list[str], conclusion: str) -> dict[str, Any]:
    """Öncüller sonucu MANTIKSAL OLARAK gerektirir mi? (premises ⊨ conclusion)

    Dönüş: ReasoningResult sözlüğü. status ∈ {valid, invalid, unknown, error}.
    invalid ise `witness` bir karşıörnek (counterexample) içerir.
    İfade grameri için: docs/mcp-api.md.
    """
    return asdict(route("entailment", {"premises": premises, "conclusion": conclusion}))


@mcp.tool()
def consistency(statements: list[str]) -> dict[str, Any]:
    """Bu ifadeler AYNI ANDA doğru olabilir mi? (tutarlılık / satisfiability)

    Dönüş: status ∈ {sat, unsat, unknown, error}. sat ise `witness` örnek bir
    atama (model); unsat ise çelişen alt küme (unsat core) döner.
    """
    return asdict(route("consistency", {"statements": statements}))


@mcp.tool()
def model(statements: list[str]) -> dict[str, Any]:
    """İfadeleri sağlayan SOMUT bir örnek (değişken ataması) döndürür.

    Dönüş: status ∈ {sat, unsat, unknown, error}. sat ise `witness` = model.
    """
    return asdict(route("find_model", {"statements": statements}))


@mcp.tool()
def prove(premises: list[str], conclusion: str) -> dict[str, Any]:
    """Öncüller sonucu gerektiriyorsa NEDEN gösterir — minimal çekirdek + adım adım türetim.

    valid: `used_premises` (gerekli öncüller) + `proof_steps` (önerme/yüklem/evrensel
    parçası için kurulur; kurulamazsa Z3 kararı korunur). invalid: `witness` karşıörnek.
    """
    return asdict(route("prove", {"premises": premises, "conclusion": conclusion}))


@mcp.tool()
def equivalent(a: str, b: str) -> dict[str, Any]:
    """İki ifade mantıksal olarak DENK mi? (her atamada aynı doğruluk değeri)

    status ∈ {equivalent, not_equivalent, unknown, error}. not_equivalent ise
    `witness` = ikisinin farklı doğruluk değeri aldığı bir atama.
    """
    return asdict(route("equivalent", {"a": a, "b": b}))


@mcp.tool()
def classify(formula: str) -> dict[str, Any]:
    """Bir formülü sınıflandır: totoloji / çelişki / olumsal (contingent).

    status ∈ {tautology, contradiction, contingent, unknown, error}. contingent
    ise `witness` = onu doğru-kılan ve yanlış-kılan birer atama.
    """
    return asdict(route("classify", {"formula": formula}))


@mcp.tool()
def enumerate_models(statements: list[str], limit: int = 10) -> dict[str, Any]:
    """İfadeleri sağlayan FARKLI modelleri (en fazla `limit`) numaralandırır.

    Dönüş: `models` (liste), `count`, `exhaustive` (True = tüm modeller bulundu;
    False = sınıra ulaşıldı, sonsuz alanda daha fazlası olabilir).
    """
    return asdict(route("enumerate", {"statements": statements, "limit": limit}))


@mcp.tool()
def optimize(constraints: list[str], objective: str, sense: str = "max") -> dict[str, Any]:
    """Kısıtları sağlayıp sayısal `objective`'i en büyük/küçük (`sense`) yapan çözümü bul.

    Dönüş: status ∈ {optimal, unbounded, unsat, unknown, error}; optimal ise
    `objective_value` + `witness` (optimumu sağlayan atama). (Z3 Optimize çekirdeği.)
    """
    return asdict(route("optimize", {"constraints": constraints, "objective": objective, "sense": sense}))


@mcp.tool()
def max_satisfy(hard: list[str], soft: list[str], weights: list[int] | None = None) -> dict[str, Any]:
    """Zorunlu (`hard`) kısıtları sağlayıp EN ÇOK (ağırlıklı) `soft` kısıtı sağla (MaxSAT).

    Aşırı-kısıtlı/çelişen isteklerde "hepsi değil, en iyisi". Dönüş: `status`;
    optimal ise `satisfied`/`unsatisfied` (soft indeksleri), `satisfied_weight` /
    `total_weight`, `witness`. `hard` sağlanamazsa `unsat`.
    """
    return asdict(route("maxsat", {"hard": hard, "soft": soft, "weights": weights}))


# ----------------- Eşitsizlik ispatı & nonlineer (Z3 NRA) ----------------- #
@mcp.tool()
def prove_inequality(goal: str, assumptions: list[str] | None = None) -> dict[str, Any]:
    """`goal` eşitsizliği TÜM gerçel değerler için (varsayımlar altında) geçerli mi?

    Z3 NRA (nonlinear real): valid → her yerde doğru; invalid → `witness` karşıörnek;
    unknown → karar verilemedi (dürüst). Ör: `"x**2 + y**2 >= 2*x*y"` → valid.
    """
    return asdict(route("prove_inequality", {"goal": goal, "assumptions": assumptions}))


@mcp.tool()
def prove_nonnegative(expression: str, assumptions: list[str] | None = None) -> dict[str, Any]:
    """`expression ≥ 0` her gerçel değer için (varsayımlar altında) geçerli mi?

    Kareler-toplamı benzeri negatif-olmama iddiaları (ör. `x**2 - 2*x + 1`).
    """
    return asdict(route("prove_nonnegative", {"expression": expression, "assumptions": assumptions}))


@mcp.tool()
def find_real_solution(constraints: list[str]) -> dict[str, Any]:
    """Doğrusal-olmayan kısıt kümesini GERÇEL sayılarda sağlayan bir nokta bulur.

    sat → `witness` somut çözüm; unsat → gerçel çözüm yok; unknown → karar yok.
    Ör: `["x**2 + y**2 == 1", "x == y"]` → sat.
    """
    return asdict(route("find_real_solution", {"constraints": constraints}))


# --------------------------- Hesap (SymPy) -------------------------------- #
@mcp.tool()
def simplify(expression: str) -> dict[str, Any]:
    """Bir cebirsel ifadeyi sadeleştirir (ör. 'sin(x)**2 + cos(x)**2' -> '1')."""
    return asdict(route("simplify", {"expression": expression}))


@mcp.tool()
def solve(equation: str, symbol: str) -> dict[str, Any]:
    """Bir denklemi bir değişken için çözer (ör. 'x**2 == 4', symbol='x')."""
    return asdict(route("solve", {"equation": equation, "symbol": symbol}))


@mcp.tool()
def differentiate(expression: str, symbol: str, order: int = 1) -> dict[str, Any]:
    """İfadenin `symbol`'e göre `order`. mertebeden türevini alır."""
    return asdict(route("differentiate", {"expression": expression, "symbol": symbol, "order": order}))


@mcp.tool()
def integrate(expression: str, symbol: str) -> dict[str, Any]:
    """İfadenin `symbol`'e göre belirsiz integralini alır (+C)."""
    return asdict(route("integrate", {"expression": expression, "symbol": symbol}))


@mcp.tool()
def limit(expression: str, symbol: str, point: str = "0", direction: str = "both") -> dict[str, Any]:
    """`symbol` → `point` iken ifadenin limiti. direction: both | + | - (tek yön).

    `point` sonsuz olabilir ("oo" / "-oo"). Ör: 'sin(x)/x', x→0 = 1; '1/x', x→oo = 0.
    """
    return asdict(route("limit", {"expression": expression, "symbol": symbol,
                                  "point": point, "direction": direction}))


@mcp.tool()
def series(expression: str, symbol: str, point: str = "0", order: int = 6) -> dict[str, Any]:
    """İfadenin `symbol`=`point` etrafında `order`. mertebeden Taylor/seri açılımı.

    Ör: 'exp(x)', x=0, order=5 → 'x**4/24 + x**3/6 + x**2/2 + x + 1'.
    """
    return asdict(route("series", {"expression": expression, "symbol": symbol,
                                   "point": point, "order": order}))


@mcp.tool()
def solve_system(equations: list[str], symbols: list[str]) -> dict[str, Any]:
    """Bir denklem SİSTEMİNİ birden çok değişken için çözer.

    Dönüş: `result` = çözüm sözlükleri listesi. Boş liste = çözüm yok; birden çok
    sözlük = birden çok çözüm; serbest değişken parametrik olarak görünür (dürüst).
    """
    return asdict(route("solve_system", {"equations": equations, "symbols": symbols}))


# -------------------------- Lineer cebir (matris) ------------------------- #
@mcp.tool()
def determinant(matrix: list[list[str]]) -> dict[str, Any]:
    """Kare bir matrisin determinantı. Hücreler sayısal veya sembolik olabilir.

    Ör: [["1","2"],["3","4"]] → "-2"; [["a","b"],["c","d"]] → "a*d - b*c".
    """
    return asdict(route("determinant", {"matrix": matrix}))


@mcp.tool()
def matrix_inverse(matrix: list[list[str]]) -> dict[str, Any]:
    """Kare bir matrisin tersi (A⁻¹). Tekil (singular, det=0) ise DÜRÜSTÇE hata.

    Dönüş: `result` = ters matris (satır listeleri). Tersinir değilse status=error.
    """
    return asdict(route("matrix_inverse", {"matrix": matrix}))


@mcp.tool()
def eigenvalues(matrix: list[list[str]]) -> dict[str, Any]:
    """Kare bir matrisin özdeğerleri (eigenvalue) + cebirsel katlılık (multiplicity).

    Dönüş: `result` = [{"value": ..., "multiplicity": n}, ...]. Karmaşık/irrasyonel
    değerler tam formda döner (ör. "I", "sqrt(2)"); değer str'e göre sıralı.
    """
    return asdict(route("eigenvalues", {"matrix": matrix}))


@mcp.tool()
def matrix_rank(matrix: list[list[str]]) -> dict[str, Any]:
    """Bir matrisin rankı (doğrusal bağımsız satır/sütun sayısı). Kare olması şart değil."""
    return asdict(route("matrix_rank", {"matrix": matrix}))


@mcp.tool()
def matrix_multiply(a: list[list[str]], b: list[list[str]]) -> dict[str, Any]:
    """İki matrisin çarpımı A·B. İç boyutlar (A sütun = B satır) uyumsuzsa dürüst hata."""
    return asdict(route("matrix_multiply", {"a": a, "b": b}))


@mcp.tool()
def matrix_solve(matrix: list[list[str]], rhs: list[str]) -> dict[str, Any]:
    """`A x = b` doğrusal sistemini matris formunda çözer.

    Dönüş: `result` = çözüm sözlükleri (`x0,x1,...`). Boş = çözüm yok (tutarsız);
    serbest değişken parametrik görünür (dürüst).
    """
    return asdict(route("matrix_solve", {"matrix": matrix, "rhs": rhs}))


@mcp.tool()
def eigenvectors(matrix: list[list[str]]) -> dict[str, Any]:
    """Özdeğer + cebirsel katlılık + özvektör(ler). Özdeğere göre sıralı (determinizm)."""
    return asdict(route("eigenvectors", {"matrix": matrix}))


@mcp.tool()
def rref(matrix: list[list[str]]) -> dict[str, Any]:
    """İndirgenmiş satır eşelon form (RREF) + pivot sütun indeksleri."""
    return asdict(route("rref", {"matrix": matrix}))


@mcp.tool()
def nullspace(matrix: list[list[str]]) -> dict[str, Any]:
    """Boş uzayın (null space / çekirdek) bir tabanı. Boş liste = yalnız sıfır (trivial)."""
    return asdict(route("nullspace", {"matrix": matrix}))


@mcp.tool()
def lu_decomposition(matrix: list[list[str]]) -> dict[str, Any]:
    """LU ayrıştırma: A = P·L·U. Dönüş: `L`, `U` matrisleri + `perm` (satır takasları)."""
    return asdict(route("lu_decomposition", {"matrix": matrix}))


# ---------------------------- Sayı teorisi -------------------------------- #
@mcp.tool()
def gcd(a: str, b: str) -> dict[str, Any]:
    """İki tam sayının en büyük ortak böleni (GCD)."""
    return asdict(route("gcd", {"a": a, "b": b}))


@mcp.tool()
def lcm(a: str, b: str) -> dict[str, Any]:
    """İki tam sayının en küçük ortak katı (LCM)."""
    return asdict(route("lcm", {"a": a, "b": b}))


@mcp.tool()
def is_prime(n: str) -> dict[str, Any]:
    """`n` asal mı? (deterministik asallık testi). Dönüş: `result` = true/false."""
    return asdict(route("is_prime", {"n": n}))


@mcp.tool()
def factorize(n: str) -> dict[str, Any]:
    """`n`'i asal çarpanlarına ayırır. Dönüş: `[{"prime":p,"exponent":e}, ...]` (artan)."""
    return asdict(route("factorize", {"n": n}))


@mcp.tool()
def modular_inverse(a: str, m: str) -> dict[str, Any]:
    """`a`'nın `m` modülünde çarpımsal tersi. Yoksa (gcd(a,m)≠1) dürüst hata."""
    return asdict(route("modular_inverse", {"a": a, "m": m}))


@mcp.tool()
def chinese_remainder(moduli: list[str], residues: list[str]) -> dict[str, Any]:
    """Çin Kalan Teoremi (CRT): x ≡ residues[i] (mod moduli[i]). Bağdaşmazsa dürüst hata.

    Dönüş: `result` = {"x": ..., "modulus": ...} (en küçük negatif-olmayan çözüm).
    """
    return asdict(route("chinese_remainder", {"moduli": moduli, "residues": residues}))


@mcp.tool()
def linear_diophantine(a: str, b: str, c: str) -> dict[str, Any]:
    """`a·x + b·y = c` denklemini TAM SAYILARDA çözer (parametre `t_0`).

    Boş liste = tam sayı çözüm yok (gcd(a,b) ∤ c) — dürüst.
    """
    return asdict(route("linear_diophantine", {"a": a, "b": b, "c": c}))


# ------------------------ Kombinatorik & ayrık ---------------------------- #
@mcp.tool()
def permutations(n: str, k: str) -> dict[str, Any]:
    """P(n,k) — `n` nesneden `k`'lı sıralı seçim sayısı (k>n ise 0)."""
    return asdict(route("permutations", {"n": n, "k": k}))


@mcp.tool()
def combinations(n: str, k: str) -> dict[str, Any]:
    """C(n,k) — `n` nesneden `k`'lı sırasız seçim sayısı (binom katsayısı)."""
    return asdict(route("combinations", {"n": n, "k": k}))


@mcp.tool()
def factorial(n: str) -> dict[str, Any]:
    """n! — ilk `n` pozitif tam sayının çarpımı (0! = 1)."""
    return asdict(route("factorial", {"n": n}))


@mcp.tool()
def partition_count(n: str) -> dict[str, Any]:
    """p(n) — `n`'i pozitif tam sayı toplamı olarak yazma yollarının sayısı."""
    return asdict(route("partition_count", {"n": n}))


@mcp.tool()
def solve_recurrence(recurrence: str, func: str = "y", var: str = "n",
                     initial: dict[str, str] | None = None) -> dict[str, Any]:
    """Doğrusal özyineleme bağıntısını KAPALI FORMA çözer.

    Ör: `recurrence="y(n) = y(n-1) + y(n-2)"`, `initial={"0":"0","1":"1"}` →
    Fibonacci kapalı formu. Kapalı form yoksa (ör. doğrusal olmayan) dürüst hata.
    """
    return asdict(route("solve_recurrence", {"recurrence": recurrence, "func": func,
                                             "var": var, "initial": initial}))


# --------------------- Çok değişkenli analiz ------------------------------ #
@mcp.tool()
def gradient(expression: str, variables: list[str]) -> dict[str, Any]:
    """∇f — `expression`'ın her değişkene göre kısmi türevleri (liste)."""
    return asdict(route("gradient", {"expression": expression, "variables": variables}))


@mcp.tool()
def jacobian(expressions: list[str], variables: list[str]) -> dict[str, Any]:
    """Jacobian matrisi — vektör-değerli fonksiyonun kısmi türev matrisi."""
    return asdict(route("jacobian", {"expressions": expressions, "variables": variables}))


@mcp.tool()
def hessian(expression: str, variables: list[str]) -> dict[str, Any]:
    """Hessian matrisi — skaler fonksiyonun ikinci kısmi türev matrisi (simetrik)."""
    return asdict(route("hessian", {"expression": expression, "variables": variables}))


@mcp.tool()
def definite_integral(expression: str, symbol: str, lower: str, upper: str) -> dict[str, Any]:
    """Belirli integral ∫ₐᵇ f dx. Sınırlar sonsuz olabilir ("oo"/"-oo")."""
    return asdict(route("definite_integral", {"expression": expression, "symbol": symbol,
                                              "lower": lower, "upper": upper}))


@mcp.tool()
def summation(expression: str, index: str, lower: str, upper: str) -> dict[str, Any]:
    """Toplam Σ — `index`=lower..upper için `expression` toplamı (kapalı form olabilir).

    Ör: `"i", "i", "1", "n"` → `n**2/2 + n/2`.
    """
    return asdict(route("summation", {"expression": expression, "index": index,
                                      "lower": lower, "upper": upper}))


@mcp.tool()
def product(expression: str, index: str, lower: str, upper: str) -> dict[str, Any]:
    """Çarpım Π — `index`=lower..upper için `expression` çarpımı."""
    return asdict(route("product", {"expression": expression, "index": index,
                                    "lower": lower, "upper": upper}))


@mcp.tool()
def solve_ode(equation: str, func: str = "y", var: str = "x") -> dict[str, Any]:
    """Sıradan diferansiyel denklemi (ODE) çözer. Türev: `y'`, `y''` (üs işareti).

    Ör: `"y' = y"` → `Eq(y(x), C1*exp(x))`. Çözülemezse dürüst hata.
    """
    return asdict(route("solve_ode", {"equation": equation, "func": func, "var": var}))


# --------------------- Olasılık & istatistik ------------------------------ #
@mcp.tool()
def mean(data: list[str]) -> dict[str, Any]:
    """Bir sayı listesinin aritmetik ortalaması (tam/rasyonel)."""
    return asdict(route("mean", {"data": data}))


@mcp.tool()
def variance(data: list[str], sample: bool = False) -> dict[str, Any]:
    """Varyans. sample=True → örneklem (n-1); aksi halde yığın (n)."""
    return asdict(route("variance", {"data": data, "sample": sample}))


@mcp.tool()
def standard_deviation(data: list[str], sample: bool = False) -> dict[str, Any]:
    """Standart sapma = √varyans (sample seçeneği variance ile aynı)."""
    return asdict(route("standard_deviation", {"data": data, "sample": sample}))


@mcp.tool()
def median(data: list[str]) -> dict[str, Any]:
    """Ortanca. Çift sayıda gözlemde ortadaki ikinin ortalaması."""
    return asdict(route("median", {"data": data}))


@mcp.tool()
def distribution(name: str, params: list[str], at: str | None = None) -> dict[str, Any]:
    """Adlandırılmış dağılımın E[X]/Var/std (sembolik/tam) özellikleri.

    `at` verilirse `P(X ≤ at)` (cdf) + yoğunluk/pmf eklenir. Desteklenen:
    normal(mu,sigma), binomial(n,p), poisson(lambda), exponential(rate),
    uniform(a,b), bernoulli(p), geometric(p).
    """
    return asdict(route("distribution", {"name": name, "params": params, "at": at}))


# ------------------- Frontier / Track B (SAT indirgeme) ------------------- #
@mcp.tool()
def pythagorean_coloring(n: int) -> dict[str, Any]:
    """{1..n}'i 2 renge, tek renkli Pythagoras üçlüsü olmadan boyamayı dener.

    Track B gösterimi: sat -> boyama bulundu; unsat -> imkânsızlık ispatı.
    (2016'da n=7825'i çözen ~200 TB'lık ispatın aynı kodlaması; küçük ölçek.)
    """
    return asdict(route("pythagorean_coloring", {"n": n}))


@mcp.tool()
def pigeonhole(n: int) -> dict[str, Any]:
    """`n+1` güvercinin `n` kutuya sığamayacağını ispatlar (güvercin yuvası ilkesi)."""
    return asdict(route("pigeonhole", {"n": n}))


@mcp.tool()
def van_der_waerden(n: int, k: int, colors: int = 2) -> dict[str, Any]:
    """{1..n}'i `colors` renge, tek renkli k-terimli aritmetik dizi olmadan boyamayı dener.

    van der Waerden sayısı W(colors,k) hesabının çekirdeği: `unsat` -> n ≥ W (ispat).
    Bilinen W değerleri bu yöntemle hesaplandı; büyük/açık değerler `unknown` döner.
    """
    return asdict(route("van_der_waerden", {"n": n, "k": k, "colors": colors}))


@mcp.tool()
def schur_number(n: int, colors: int) -> dict[str, Any]:
    """{1..n}'i `colors` sum-free renge bölmeyi dener (Schur sayısı S(colors) çekirdeği).

    `unsat` -> n > S(colors) (ispat). Bilinen: S(2)=4, S(3)=13, S(4)=44, S(5)=160;
    S(6) açık.
    """
    return asdict(route("schur_number", {"n": n, "colors": colors}))


@mcp.tool()
def graph_coloring(edges: list[list[int]], colors: int, n: int | None = None) -> dict[str, Any]:
    """Grafı `colors` renge boyar (komşular farklı). NP-tam graph k-coloring.

    `sat` → boyama (BAĞIMSIZ doğrulanmış, `meta.verified`); `unsat` → kromatik
    sayı > colors. Köşeler 1-indeksli; kenarlar `[[u,v],...]`.
    """
    return asdict(route("graph_coloring", {"edges": edges, "colors": colors, "n": n}))


@mcp.tool()
def subset_sum(numbers: list[int], target: int) -> dict[str, Any]:
    """`numbers`'ın bir alt kümesi `target`'a toplanır mı? (NP-tam subset-sum).

    `sat` → toplayan alt küme (BAĞIMSIZ doğrulanmış sertifika); `unsat` → yok.
    """
    return asdict(route("subset_sum", {"numbers": numbers, "target": target}))


def main() -> None:
    """Sunucuyu stdio üzerinden başlatır (yerel MCP istemcileri için)."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
