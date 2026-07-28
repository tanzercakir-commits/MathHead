# MathHead

![CI](https://github.com/tanzercakir-commits/MathHead/actions/workflows/ci.yml/badge.svg)

AI'ın (ör. Claude) **MCP** üzerinden çağırabileceği, first-order logic temelli,
**deterministik** bir matematik akıl yürütme ve ispat motoru.

> **Fikir:** LLM'ler katı mantık/ispatta güvenilmez (non-deterministik, varsayıma
> açık). MathHead bu işi gerçek bir motora (SMT çözücü **Z3** + sembolik hesap
> **SymPy**) devrederek "uydurma" payını düşürür.

## Durum

**Çalışır motor.** Mantık çekirdeği (Z3) + hesap/kalkülüs/lineer cebir/sayı
teorisi/kombinatorik/olasılık (SymPy) + Track B (SAT indirgeme) + **doğrulama
katmanı** (AI muhakemesini denetler): **60+ MCP aracı**, CLI ve kapsamlı test
paketi. Aşamalı yol haritası `ROADMAP.md`'de; sıradaki iş `Todo.md`'de.

## Hızlı başlangıç

PyPI'ye yüklendiğinde: `pip install mathhead` (bkz. `RELEASING.md`). Şimdilik kaynaktan:

```bash
git clone https://github.com/tanzercakir-commits/MathHead && cd MathHead
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

mathhead-server        # MCP sunucusunu stdio ile başlat
pytest -q              # tüm testler yeşil
```

## Kullanım (v1)

Python'dan:

```python
from mathhead.core import check_entailment, check_consistency, find_model

check_entailment(["p", "implies(p, q)"], "q")   # -> status="valid"
check_entailment(["x > 0"], "x > 5")             # -> "invalid", witness={"x": 1}
check_consistency(["p", "not(p)"])               # -> "unsat" + unsat core
find_model(["x > 2", "x < 5"])                    # -> "sat", witness={"x": 3}

from mathhead.core.inequality import prove_inequality   # v2+ (Z3 NRA, nonlineer)
prove_inequality("x**2 + y**2 >= 2*x*y")          # -> "valid"  (AM-GM, ispat)
prove_inequality("x**2 >= x")                     # -> "invalid", witness={"x": 0.5}

from mathhead.core.verify import verify_equality, verify_solution  # DOĞRULAMA (AI denetçisi)
verify_equality("(x**2-1)/(x-1)", "x+1")          # -> valid, AMA domain uyarısı (x=1 tanımsız!)
verify_solution("x**2==4", "x", ["2"])            # -> invalid: EKSİK (-2 kaçtı)
verify_solution("x**2==4", "x", ["2","-2"])       # -> valid: doğru + tam

from mathhead.core.crosscheck import cross_check  # ÇAPRAZ DENETİM (Z3 ⋈ SymPy)
cross_check("(x+1)**2", "x**2 + 2*x + 1")         # -> CONSENSUS_EQUAL (iki motor anlaşıyor)
cross_check("(x**2-1)/(x-1)", "x+1")              # -> ENGINES_DISAGREE (domain tuzağı bayrağı!)

from mathhead.core.verify import verify_derivative, verify_integral, verify_limit  # AI iddia denetimi
verify_derivative("x**3", "x", "3*x**2")          # -> valid (türev doğru)
verify_integral("2*x", "x", "x**2 + 5")           # -> valid (+C sabit farkı hoşgörülür)
verify_limit("sin(x)/x", "x", "0", "1")           # -> valid (limit doğru)

from mathhead.core.nl import interpret            # DOĞAL DİL → formal (tanı-ya-da-reddet)
interpret("x**3 ifadesinin x e göre türevi")      # -> UNDERSTOOD + "ne anladım" (onayla-sonra-güven)
interpret("anlamsız cümle")                       # -> UNRECOGNIZED (TAHMİN YOK)

from mathhead.certificate import check_certificate  # BAĞIMSIZ checker (z3/sympy YOK)
check_certificate({"kind":"subset_sum","numbers":[3,4,2],"target":9,"indices":[0,1,2]})  # verified
check_certificate({"kind":"solution","expression":"x**2 - 4","symbol":"x","value":"3"})  # refuted

from mathhead.compute import solve, differentiate, integrate   # v2 (SymPy)
solve("x**2 == 4", "x")                           # -> ["-2", "2"]
differentiate("x**3 + 2*x", "x")                  # -> "3*x**2 + 2"
integrate("2*x", "x")                             # -> "x**2"

from mathhead.compute import limit, series, solve_system       # v2+ (kalkülüs)
limit("sin(x)/x", "x", "0")                       # -> "1"
limit("1/x", "x", "oo")                           # -> "0"
series("exp(x)", "x", "0", 5)                     # -> "x**4/24 + x**3/6 + x**2/2 + x + 1"
solve_system(["x + y == 10", "x - y == 2"], ["x", "y"])   # -> [{"x": "6", "y": "4"}]

from mathhead.compute import determinant, matrix_inverse, eigenvalues   # v2+ (lineer cebir)
determinant([["a", "b"], ["c", "d"]])             # -> "a*d - b*c" (sembolik)
matrix_inverse([["1", "2"], ["3", "4"]])          # -> [["-2","1"],["3/2","-1/2"]]
matrix_inverse([["1", "2"], ["2", "4"]])          # -> error: tersinir değil (dürüst)
eigenvalues([["2", "0"], ["0", "3"]])             # -> [{"value":"2",...},{"value":"3",...}]

from mathhead.compute import matrix_multiply, matrix_solve, nullspace   # v2+ (lineer cebir II)
matrix_multiply([["1","2"],["3","4"]], [["5","6"],["7","8"]])  # -> [["19","22"],["43","50"]]
matrix_solve([["1","1"],["1","-1"]], ["10","2"]) # -> [{"x0":"6","x1":"4"}]  (Ax=b)
matrix_solve([["1","1"],["1","1"]], ["1","2"])   # -> []  (tutarsız → çözüm yok, dürüst)
nullspace([["1","2"],["2","4"]])                  # -> [["-2","1"]]  (boş uzay tabanı)

from mathhead.compute import gcd, factorize, modular_inverse, chinese_remainder  # v2+ (sayı teorisi)
gcd(48, 36)                                       # -> 12
factorize(360)                                    # -> 2^3 · 3^2 · 5
modular_inverse(3, 11)                            # -> 4  (3·4 ≡ 1 mod 11)
modular_inverse(4, 8)                             # -> error: ters yok (gcd≠1, dürüst)
chinese_remainder([3,5,7], [2,3,2])               # -> {"x": 23, "modulus": 105}

from mathhead.compute import combinations, factorial, solve_recurrence  # v2+ (kombinatorik)
combinations(49, 6)                               # -> 13983816  (loto)
factorial(10)                                     # -> 3628800
solve_recurrence("y(n) = y(n-1) + y(n-2)",        # -> Fibonacci kapalı formu (Binet)
                 "y", "n", {"0": "0", "1": "1"})

from mathhead.compute import gradient, summation, solve_ode  # v2+ (çok değişkenli analiz)
gradient("x**2*y + sin(y)", ["x", "y"])           # -> ["2*x*y", "x**2 + cos(y)"]
summation("i", "i", "1", "n")                     # -> "n**2/2 + n/2"  (kapalı form)
solve_ode("y'' + y = 0")                          # -> Eq(y(x), C1*sin(x) + C2*cos(x))

from mathhead.compute import mean, distribution   # v2+ (olasılık & istatistik)
mean(["2", "4", "4", "5", "5"])                   # -> "4"
distribution("binomial", ["10", "1/2"], at="3")   # -> {mean:5, variance:5/2, cdf_at:11/64, ...}
distribution("normal", ["mu", "sigma"])           # -> {mean:"mu", variance:"sigma**2", ...}
```

MCP istemcisine (ör. Claude Code) bağlamak:

```bash
claude mcp add mathhead -- mathhead-server
```

Girdi dili (gramer) ve araç sözleşmesi: `docs/mcp-api.md`.

Terminalden (CLI):

```bash
mathhead entail -p "p" -p "implies(p, q)" -c "q"          # -> valid
mathhead entail -p "forall(x, implies(Man(x), Mortal(x)))" \
                -p "Man(socrates)" -c "Mortal(socrates)"  # silogizm -> valid
mathhead prove -p "forall(x, implies(Man(x), Mortal(x)))" \
               -p "Man(socrates)" -c "Mortal(socrates)"   # + adım adım ispat
mathhead solve "x**2 == 4" x                              # -> ['-2', '2']
mathhead limit "sin(x)/x" x --point 0                     # -> 1
mathhead solve-system --eq "x + y == 10" --eq "x - y == 2" \
                      --sym x --sym y                     # -> [{'x':'6','y':'4'}]
mathhead det "1,2;3,4"                                    # -> -2
mathhead eigenvals "2,0;0,3"                              # -> özdeğerler + katlılık
mathhead pigeonhole 4                                     # -> unsat (ispat)
mathhead graph-coloring --edge 1,2 --edge 2,3 --edge 1,3 --colors 3   # -> sat (doğrulanmış)
mathhead subset-sum 3 34 4 12 5 2 --target 9              # -> sat: {3,4,2}
mathhead --json consistent "x > 2" "x < 5"                # ham JSON
```

## Yapı

```
mathhead/
├── README.md            · bu dosya
├── Plan.md              · hedef mimari + yol haritası (değişmeye dirençli)
├── Todo.md              · şu anki işler + öncelikler (sık değişir)
├── Progress.md          · ne yaptık / ne zaman (append-only günlük)
├── PRINCIPLES.md        · değişmez proje kuralları (çit felsefesi)
├── DECISIONS.md         · karar günlüğü (ADR) — kararlar kaybolmasın
├── pyproject.toml       · bağımlılıklar (z3-solver, sympy, mcp[cli])
├── docs/
│   ├── architecture.md  · katman şeması (Mermaid) + istek yaşam döngüsü
│   ├── mcp-api.md        · net MCP protokol & araç tanımları + gramer
│   ├── api-reference.md  · TÜM araçların otomatik referansı (kod=doküman)
│   ├── error-taxonomy.md · tüm status/reason_code kanonik listesi
│   └── glossary.md       · terimler (FOL, SMT, CAS, entailment...)
├── src/mathhead/
│   ├── core/            · mantık (Z3) + doğrulama (verify/crosscheck/inequality)
│   ├── certificate.py  · BAĞIMSIZ sertifika checker (yalnız stdlib, z3/sympy YOK)
│   ├── compute/         · sembolik hesap (SymPy)                          [v2+]
│   ├── router/          · yönlendirme
│   ├── guardrails/      · çit: doğrulama, timeout, determinizm
│   └── server/          · MCP sunucusu (FastMCP, 70 araç)
├── scripts/             · benchmark.py + gen_api_reference.py
├── benchmarks/          · LLM-tuzak seti + harness (%100 yakalama, Track C4)
└── tests/               · kapsamlı test paketi + fixtures/golden.json (regresyon çiti)
```

## Nereden okumaya başlamalı?

`Plan.md` (büyük resim) → `docs/architecture.md` (katmanlar) →
`docs/mcp-api.md` (sözleşme) → `Todo.md` (sıradaki iş).

## Lisans

Apache-2.0 — bkz. `LICENSE`.
