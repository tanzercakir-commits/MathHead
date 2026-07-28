# MathHead

![CI](https://github.com/tanzercakir-commits/MathHead/actions/workflows/ci.yml/badge.svg)

AI'ın (ör. Claude) **MCP** üzerinden çağırabileceği, first-order logic temelli,
**deterministik** bir matematik akıl yürütme ve ispat motoru.

> **Fikir:** LLM'ler katı mantık/ispatta güvenilmez (non-deterministik, varsayıma
> açık). MathHead bu işi gerçek bir motora (SMT çözücü **Z3** + sembolik hesap
> **SymPy**) devrederek "uydurma" payını düşürür.

## Durum

**Çalışır motor.** Mantık çekirdeği (Z3) + hesap/kalkülüs/lineer cebir/sayı
teorisi/kombinatorik (SymPy) + Track B (SAT indirgeme): **49 MCP aracı**, CLI ve
242+ otomatik test. Aşamalı yol haritası `ROADMAP.md`'de; sıradaki iş `Todo.md`'de.

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
│   ├── error-taxonomy.md · tüm status/reason_code kanonik listesi
│   └── glossary.md       · terimler (FOL, SMT, CAS, entailment...)
├── src/mathhead/
│   ├── core/            · mantık çekirdeği (Z3) — logic.py, translate.py  [v1]
│   ├── compute/         · sembolik hesap (SymPy)                          [v2+]
│   ├── router/          · yönlendirme
│   ├── guardrails/      · çit: doğrulama, timeout, determinizm
│   └── server/          · MCP sunucusu (FastMCP, 49 araç)
├── scripts/             · benchmark.py (performans taban çizgisi)
└── tests/               · 242 test + fixtures/golden.json (regresyon çiti)
```

## Nereden okumaya başlamalı?

`Plan.md` (büyük resim) → `docs/architecture.md` (katmanlar) →
`docs/mcp-api.md` (sözleşme) → `Todo.md` (sıradaki iş).

## Lisans

Apache-2.0 — bkz. `LICENSE`.
