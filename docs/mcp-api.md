# MathHead — MCP API & Protokol

> Motorun dış dünya ile **tek sözleşmesi**. Bu dosya ve `server/mcp_server.py`
> birebir aynı olmalıdır; imzalar **erken donduruldu** (DECISIONS ADR-0004).
> Senin "net protokol / API tanımı" maddenin karşılığı.

## Taşıma (transport)

- SDK: `mcp[cli]` (FastMCP), Python 3.10+
- Yerel çalıştırma: `mathhead-server` veya `python -m mathhead.server.mcp_server`
- Taşıma: `stdio` (yerel MCP istemcileri için)

---

## Araçlar (tools)

### 1) `entailment(premises: list[str], conclusion: str) -> ReasoningResult`

Öncüller sonucu mantıksal olarak gerektirir mi? (`premises ⊨ conclusion`)

- `valid` → gerektirir (`reason_code=ENTAILED`)
- `invalid` → gerektirmez; `witness` bir **karşıörnek** (`COUNTEREXAMPLE_FOUND`)
- `unknown` → çözücü karar veremedi (`SOLVER_TIMEOUT` / `SOLVER_UNKNOWN`)

### 2) `consistency(statements: list[str]) -> ReasoningResult`

İfadeler aynı anda doğru olabilir mi? (tutarlılık / satisfiability)

- `sat` → tutarlı; `witness` = örnek atama (model)
- `unsat` → çelişkili; `witness` = çelişen alt küme (**unsat core**)
- `unknown` → karar verilemedi

### 3) `model(statements: list[str]) -> ReasoningResult`

İfadeleri sağlayan **somut** bir örnek (değişken ataması) döndürür.
`sat` → `witness` = model; `unsat` → model yok; `unknown` → belirsiz.

### 4) `prove(premises: list[str], conclusion: str) -> ProofResult`

Entailment + **neden**. `valid` ise: `used_premises` (sonucun dayandığı minimal
öncül alt kümesi) + `proof_steps` (önerme/yüklem/evrensel parçası için adım adım
doğal tümdengelim; kurulamazsa Z3 kararı korunur, adımsız). `invalid` ise
`witness` = karşıörnek. İki strateji: DOĞRUDAN ileri zincirleme; olmazsa
ÇELİŞKİDEN (RAA). Adım biçimi: `{step, formula, rule, refs}` — kurallar:
`modus ponens`, `modus tollens`, `ayrık tasım`, `∧-ayıklama`, `iff-ayıklama`,
`çift olumsuzlama`, `De Morgan`, `evrensel örnekleme`, `varoluşsal eleme`,
`varoluşsal içe alma`, `çelişkiden ispat (RAA)`.

### 5) `enumerate_models(statements: list[str], limit: int = 10) -> ModelSet`

İfadeleri sağlayan **farklı** modelleri (en fazla `limit`) numaralandırır
(all-SAT; bloklama-cümlesi yöntemi). Dönüş: `models` (liste), `count`,
`exhaustive` — `True` = tümü bulundu (unsat'a ulaşıldı); `False` = sınıra
ulaşıldı, sonsuz alanda (sınırsız Int/Real) daha fazlası olabilir.

### 6) `optimize(constraints: list[str], objective: str, sense = "max") -> OptimizeResult`

Kısıtları sağlayıp sayısal `objective`'i en büyük/küçük (`sense`: `max`/`min`)
yapan çözümü bulur (Z3 Optimize — *optimization modulo theories*). Dönüş:
`status` ∈ {`optimal`, `unbounded`, `unsat`, `unknown`, `error`},
`objective_value`, `witness` (optimumu sağlayan atama), `sense`. Sınırsız
(`unbounded`), uygun-çözüm-yok (`unsat`) ve açık-sınır (supremum/infimum, ε ile
tam ulaşılamaz) durumları dürüstçe raporlanır.

### 7) `max_satisfy(hard: list[str], soft: list[str], weights=None) -> MaxSatResult`

Zorunlu (`hard`) kısıtları sağlayıp EN ÇOK (ağırlıklı) `soft` kısıtı sağlar
(MaxSAT). Aşırı-kısıtlı / çelişen isteklerde "hepsi değil, en iyisi". Dönüş:
`status`; optimal ise `satisfied` / `unsatisfied` (soft indeksleri),
`satisfied_weight` / `total_weight`, `witness`. `hard` sağlanamazsa `unsat`.

### 8) `equivalent(a: str, b: str) -> ReasoningResult`

İki ifade mantıksal olarak DENK mi (her atamada aynı doğruluk değeri)? `status` ∈
{`equivalent`, `not_equivalent`, `unknown`, `error`}; `not_equivalent` ise
`witness` = ikisinin farklılaştığı bir atama.

### 9) `classify(formula: str) -> ReasoningResult`

Bir formülü sınıflandırır: `status` ∈ {`tautology` (her zaman doğru),
`contradiction` (her zaman yanlış), `contingent` (bazen doğru bazen yanlış),
`unknown`, `error`}. `contingent` ise `witness` = doğru-kılan + yanlış-kılan atama.

---

## Girdi grameri (v1.2)

Girdi **Python ifade sözdizimi** ile yazılır; motorun ayrıştırıcısı (`ast`
tabanlı, beyaz-listeli — ADR-0009/0010) yalnızca aşağıdakine izin verir, gerisini
net reddeder. Ayrıştırmayı Python yaptığı için **operatör önceliği ve parantez**
beklendiği gibi çalışır.

| Kategori | İzin verilenler | Not |
|---|---|---|
| Boolean bağlaç | `and`, `or`, `not` | Python anahtar sözcükleri |
| Boolean fonksiyon | `implies(a, b)`, `iff(a, b)`, `xor(a, b)` | her biri tam 2 argüman |
| Nicelik belirteci | `forall(x, gövde)`, `exists(x, gövde)` | `x` bağlı değişken |
| Yüklem / ilişki | `Man(x)`, `Loves(a, b)` | yorumsuz; argümanlar **birey** |
| Karşılaştırma | `<`, `<=`, `==`, `!=`, `>=`, `>` | zincir destekli: `1 < x < 5` |
| Aritmetik | `+`, `-`, `*` | **doğrusal**: `değişken*değişken` yasak |
| Değişken | `Bool` veya sayısal | sort **bağlamdan** çıkarılır (aşağıda) |
| Sabit | tam sayı, ondalık, `True`, `False` | ondalık → Real |

**Sort çıkarımı (tür):** bir ismin Boolean mı Int mi olduğu kullanımından
belirlenir — karşılaştırma/aritmetik içinde geçen → `Int`; bağlaç/fonksiyon
içinde ya da yalın atom → `Bool`. Bir isim **aynı problemde** hem Bool hem Int
kullanılırsa motor `error` (`PARSE_ERROR`) döner — sessiz varsayım yok
(PRINCIPLES #2).

**Sayısal alan (Int vs Real):** problemde herhangi bir **ondalık** sabit (ör.
`2.0`) varsa tüm sayısal değişkenler **Real**, yoksa **Int** (v1.1 sadeleştirmesi;
aynı problemde karışım yok). Anlamı değiştirir: `exists(x, 1 < x and x < 2)`
Int'te **unsat**; `1.0 < x and x < 2.0` ile Real'de **sat**.

**Hâlâ YOK:** yorumsuz fonksiyon terimleri (`f(x)` — birey döndüren), yüklem-içi
aritmetik, doğrusal olmayan çarpım, küme/dizi teorileri. (Yüklemler `P(x)` ve
birey sabitleri v1.2'de **eklendi** — klasik silogizm çalışır.) **Dürüst uyarı:** nicelik belirteçleri FOL'u yarı-karar
verilebilir yapar; Z3 bazı formüllerde (ör. iç içe `∀∃`) `unknown` dönebilir —
gizlenmez, birinci sınıf raporlanır (soundness: motor asla yanlış cevap üretmez).

Örnek geçerli ifadeler: `p`, `implies(p, q)`, `p and (q or not(r))`, `1 < x < 5`,
`2*x + 3 <= y`, `forall(x, implies(x > 2, x > 1))`, `exists(x, 1.0 < x and x < 2.0)`.

---

## Çıktı sözleşmesi — `ReasoningResult`

| Alan | Tip | Anlamı |
|---|---|---|
| `status` | str | `valid` \| `invalid` \| `sat` \| `unsat` \| `unknown` \| `error` |
| `reason_code` | str | makine-okur kod (aşağıdaki tablo) |
| `explanation` | str | insan-okur açıklama |
| `witness` | dict \| null | model (sat) / karşıörnek (invalid) / unsat core |
| `meta` | dict | `engine`, `z3_version`, `elapsed_ms`, `seed`, `timeout_ms` |

### `reason_code` değerleri

| Kod | Ne zaman |
|---|---|
| `ENTAILED` | entailment geçerli |
| `COUNTEREXAMPLE_FOUND` | entailment geçersiz, karşıörnek var |
| `CONSISTENT` | ifadeler tutarlı (sat) |
| `CONTRADICTION` | ifadeler çelişkili (unsat) |
| `MODEL_FOUND` | find_model: model bulundu (sat) |
| `NO_MODEL` | find_model: model yok (unsat) |
| `SOLVER_TIMEOUT` | zaman aşımı → unknown |
| `SOLVER_UNKNOWN` | çözücü karar veremedi → unknown |
| `PARSE_ERROR` | gramer ihlali → error |
| `GUARDRAIL_VIOLATION` | boyut/derinlik/sembol sınırı → error |

---

## Örnek (AI → MathHead)

**İstek**

```json
{ "tool": "entailment",
  "premises": ["p", "implies(p, q)"],
  "conclusion": "q" }
```

**Yanıt**

```json
{ "status": "valid",
  "reason_code": "ENTAILED",
  "explanation": "q, öncüllerden modus ponens ile çıkar.",
  "witness": null,
  "meta": { "engine": "z3", "z3_version": "4.13.x", "elapsed_ms": 3, "seed": 42 } }
```

**Karşıörnek örneği** — `entailment(["x > 0"], "x > 5")`

```json
{ "status": "invalid",
  "reason_code": "COUNTEREXAMPLE_FOUND",
  "explanation": "x = 1 öncülü sağlar ama sonucu sağlamaz.",
  "witness": { "x": 1 },
  "meta": { "engine": "z3", "elapsed_ms": 2, "seed": 42 } }
```

---

## Hesap araçları (v2 — SymPy)

Mantık araçlarından ayrı; sembolik **hesap** (ispat değil). Girdi yine
ast-whitelist ile süzülür (`sympify`/`eval` yok). Burada `*`, `/`, `**` (üs) ve
doğrusal olmayan ifadeler **serbesttir**.

| Araç | İmza | Örnek |
|---|---|---|
| `simplify` | `simplify(expression)` | `sin(x)**2 + cos(x)**2` → `1` |
| `solve` | `solve(equation, symbol)` | `x**2 == 4`, `x` → `["-2","2"]` |
| `differentiate` | `differentiate(expression, symbol, order=1)` | `x**3+2*x`, `x` → `3*x**2 + 2` |
| `integrate` | `integrate(expression, symbol)` | `2*x`, `x` → `x**2` (+C) |
| `limit` | `limit(expression, symbol, point="0", direction="both")` | `sin(x)/x`, `x`, `0` → `1` |
| `series` | `series(expression, symbol, point="0", order=6)` | `exp(x)`, `x`, `0`, `5` → `x**4/24 + x**3/6 + x**2/2 + x + 1` |
| `solve_system` | `solve_system(equations: list[str], symbols: list[str])` | `["x+y==10","x-y==2"]`, `["x","y"]` → `[{"x":"6","y":"4"}]` |

**İzinli:** `+ - * / **`, tekli `-`, semboller, sayı (tam/ondalık), fonksiyonlar
`sin cos tan asin acos atan sinh cosh tanh exp log sqrt Abs`. `solve` girdisi
`a == b` (Eq) veya `=0` varsayımıyla düz ifade olabilir.

**Kalkülüs & sistemler:** `limit` noktası sonsuz olabilir (`point="oo"` / `"-oo"`)
ve `direction` tek yön için `"+"`/`"-"` alır. `series` `point` etrafında `order`.
mertebeden Taylor açılımı döndürür (`removeO`). `solve_system` **çözüm sözlükleri
listesi** döner: boş liste = çözüm yok (dürüst), birden çok sözlük = birden çok
çözüm (doğrusal olmayan sistemler dahil), serbest değişken parametrik görünür.

### Lineer cebir (matris)

Girdi **`list[list[str]]`** (satır listeleri); her hücre yine ast-whitelist ile
süzülür, sembolik olabilir. CLI'da MATLAB-tarzı dizgi: `"1,2;3,4"`.

| Araç | İmza | Örnek |
|---|---|---|
| `determinant` | `determinant(matrix)` | `[["1","2"],["3","4"]]` → `"-2"`; `[["a","b"],["c","d"]]` → `"a*d - b*c"` |
| `matrix_inverse` | `matrix_inverse(matrix)` | `[["1","2"],["3","4"]]` → `[["-2","1"],["3/2","-1/2"]]` |
| `eigenvalues` | `eigenvalues(matrix)` | `[["2","0"],["0","3"]]` → `[{"value":"2","multiplicity":1},{"value":"3","multiplicity":1}]` |
| `matrix_rank` | `matrix_rank(matrix)` | `[["1","2"],["2","4"]]` → `1` |
| `matrix_multiply` | `matrix_multiply(a, b)` | `[[1,2],[3,4]]·[[5,6],[7,8]]` → `[["19","22"],["43","50"]]` |
| `matrix_solve` | `matrix_solve(matrix, rhs)` | `A=[[1,1],[1,-1]]`, `b=["10","2"]` → `[{"x0":"6","x1":"4"}]` |
| `eigenvectors` | `eigenvectors(matrix)` | `[["2","0"],["0","3"]]` → `[{"eigenvalue":"2","multiplicity":1,"vectors":[["1","0"]]}, ...]` |
| `rref` | `rref(matrix)` | → `{"rref": [...], "pivots": [0,1]}` |
| `nullspace` | `nullspace(matrix)` | `[["1","2"],["2","4"]]` → `[["-2","1"]]` |
| `lu_decomposition` | `lu_decomposition(matrix)` | → `{"L":[...], "U":[...], "perm":[...]}` |

`determinant`/`matrix_inverse`/`eigenvalues`/`eigenvectors`/`lu_decomposition`
**kare** matris ister (değilse `PARSE_ERROR`). **Dürüstlük:** tekil (singular,
det=0) matriste `matrix_inverse` uydurmaz, `COMPUTE_FAILED` döner; `eigenvalues`/
`eigenvectors` karmaşık/irrasyonel değerleri tam formda (`"I"`, `"sqrt(2)"`) ve
cebirsel katlılığı açıkça verir, `value`/`eigenvalue`'ya göre sıralı (determinizm
— ADR-0019). `matrix_multiply` iç boyut uyumsuzsa (`A.cols ≠ B.rows`) hata verir.
`matrix_solve` (`Ax=b`) **çözüm sözlükleri listesi** döner: boş = çözüm yok
(tutarsız), serbest değişken parametrik (`"3 - x1"`). `matrix_rank`/`rref`/
`nullspace` kare olmayan matriste de çalışır; `nullspace` boş liste = trivial
(yalnız sıfır).

### Sayı teorisi (number theory)

Tam sayılar üzerinde. Girdi ast-whitelist ile süzülür (`"2**10"` serbest); sonuç
tam sayı değilse `PARSE_ERROR`.

| Araç | İmza | Örnek |
|---|---|---|
| `gcd` | `gcd(a, b)` | `48, 36` → `12` |
| `lcm` | `lcm(a, b)` | `4, 6` → `12` |
| `is_prime` | `is_prime(n)` | `97` → `true`; `91` → `false` |
| `factorize` | `factorize(n)` | `360` → `[{"prime":2,"exponent":3},{"prime":3,"exponent":2},{"prime":5,"exponent":1}]` |
| `modular_inverse` | `modular_inverse(a, m)` | `3, 11` → `4` |
| `chinese_remainder` | `chinese_remainder(moduli, residues)` | `[3,5,7],[2,3,2]` → `{"x":23,"modulus":105}` |
| `linear_diophantine` | `linear_diophantine(a, b, c)` | `3,6,9` → `[{"x":"3 - 2*t_0","y":"t_0"}]` |

**Dürüstlük:** `modular_inverse` ters yoksa (gcd(a,m)≠1) uydurmaz, `COMPUTE_FAILED`;
`chinese_remainder` moduller bağdaşmazsa hata; `linear_diophantine` tam sayı çözüm
yoksa (gcd(a,b) ∤ c) **boş liste** döner; `factorize(1)` = `[]` (asal çarpan yok).
Diophantine çözümü parametriktir (parametre `t_0`).

### Kombinatorik & ayrık (combinatorics)

| Araç | İmza | Örnek |
|---|---|---|
| `permutations` | `permutations(n, k)` | `10, 3` → `720` (k>n → `0`) |
| `combinations` | `combinations(n, k)` | `10, 3` → `120` |
| `factorial` | `factorial(n)` | `6` → `720` |
| `partition_count` | `partition_count(n)` | `10` → `42` |
| `solve_recurrence` | `solve_recurrence(recurrence, func="y", var="n", initial={})` | `"y(n)=y(n-1)+y(n-2)"`, `{"0":"0","1":"1"}` → Fibonacci kapalı formu |

`solve_recurrence` özyinelemeyi ayrı bir güvenli ayrıştırıcıyla okur (`func`
çağrıları + `var` + aritmetik; `=` ya da `==` kabul edilir; whitelist dışı ad/çağrı
reddedilir). **Dürüstlük:** doğrusal olmayan / kapalı formu olmayan bağıntıda
uydurmaz, `COMPUTE_FAILED` döner. `permutations`/`combinations` `k>n` için `0`
(kombinatorik olarak doğru); negatif girdi reddedilir.

### Çok değişkenli analiz (multivariable calculus)

| Araç | İmza | Örnek |
|---|---|---|
| `gradient` | `gradient(expression, variables)` | `x**2*y+sin(y)`, `["x","y"]` → `["2*x*y","x**2 + cos(y)"]` |
| `jacobian` | `jacobian(expressions, variables)` | `["x*y","x+y"]`, `["x","y"]` → `[["y","x"],["1","1"]]` |
| `hessian` | `hessian(expression, variables)` | → simetrik 2. türev matrisi |
| `definite_integral` | `definite_integral(expression, symbol, lower, upper)` | `x**2`, `x`, `0`, `3` → `9`; sınır `oo` olabilir |
| `summation` | `summation(expression, index, lower, upper)` | `i`, `i`, `1`, `n` → `n**2/2 + n/2` (kapalı form) |
| `product` | `product(expression, index, lower, upper)` | `i`, `i`, `1`, `5` → `120` |
| `solve_ode` | `solve_ode(equation, func="y", var="x")` | `"y'' + y = 0"` → `Eq(y(x), C1*sin(x) + C2*cos(x))` |

`solve_ode` türevi `y'`, `y''` (üs işareti) ya da `D(y, k)` biçiminde okur; ayrı
bir güvenli ayrıştırıcı kullanır (`=`/`==`, whitelist dışı ad reddedilir).
**Dürüstlük:** çözülemeyen ODE'de uydurmaz, `COMPUTE_FAILED`. `definite_integral`/
`summation` sınırları sonsuz (`oo`) ve `summation` üst sınırı sembolik (`n`) olabilir.

### Olasılık & istatistik (probability & statistics)

| Araç | İmza | Örnek |
|---|---|---|
| `mean` | `mean(data)` | `[2,4,4,4,5,5,7,9]` → `5` |
| `variance` | `variance(data, sample=False)` | yığın → `4`; `sample=True` → `32/7` |
| `standard_deviation` | `standard_deviation(data, sample=False)` | → `2` |
| `median` | `median(data)` | çift n → ortadaki ikinin ortalaması (`9/2`) |
| `distribution` | `distribution(name, params, at=None)` | `binomial`,`["10","1/2"]`,`"3"` → `{mean:5, variance:5/2, cdf_at:11/64, density_at:15/128}` |

Betimsel istatistik **tam/rasyonel** sonuç verir (sembolik veri reddedilir).
`distribution` `sympy.stats` üstünde **sembolik/tam**: `E[X]`, `Var`, `std`; `at`
verilirse `P(X ≤ at)` (cdf) + yoğunluk/pmf. Desteklenen: `normal(mu,sigma)`,
`binomial(n,p)`, `poisson(lambda)`, `exponential(rate)`, `uniform(a,b)`,
`bernoulli(p)`, `geometric(p)`. Bilinmeyen dağılım / yanlış parametre sayısı
reddedilir (dürüst).

**Çıktı — `ComputeResult`:** `status` (`ok`|`error`), `operation`, `result`
(metin veya kök listesi), `explanation`, `reason_code` (`OK`|`PARSE_ERROR`|
`COMPUTE_FAILED`), `meta` (`engine=sympy`, `sympy_version`, `elapsed_ms`).

**Dürüstlük:** SymPy kapalı formda çözemezse (ör. `∫ exp(x**2) dx`) sonucu
gizlemez; değerlendirilmemiş/özel-fonksiyonlu tam ifadeyi (`erfi(...)` gibi)
döner.

---

## Eşitsizlik ispatı & nonlineer (Z3 NRA)

Polinom eşitsizliklerini Z3'ün doğrusal-olmayan gerçel aritmetik (nonlinear real
arithmetic, NRA / nlsat) karar yordamıyla **ispatlar** ya da karşıörnek verir.
Yöntem: `∀x. P(x)` → `¬P(x)` UNSAT mı (ret-ile-ispat). Girdi burada **nonlineer**
serbest: `Real` değişkenler, `+ - * / **` (üs = negatif-olmayan tam sayı),
`< <= > >= == !=`, `and`/`or`/`not(...)`/`implies`/`iff`.

| Araç | İmza | Örnek |
|---|---|---|
| `prove_inequality` | `prove_inequality(goal, assumptions=None)` | `x**2 + y**2 >= 2*x*y` → `valid` |
| `prove_nonnegative` | `prove_nonnegative(expression, assumptions=None)` | `x**2 - 2*x + 1` → `valid` |
| `find_real_solution` | `find_real_solution(constraints)` | `["x**2+y**2==1","x==y"]` → `sat` |

Dönüş `ReasoningResult`: `prove_*` → `valid` (her yerde doğru) / `invalid`
(`witness` karşıörnek) / `unknown`. `find_real_solution` → `sat` (`witness` somut
nokta) / `unsat` / `unknown`. **Dürüstlük:** NRA teoride karar-verilebilir ama Z3
zor örnekte `unknown`/timeout dönebilir — birinci sınıf raporlanır; hedef
karşılaştırma değilse ya da üs değişkense (nonpolinom) `GUARDRAIL_VIOLATION`.

---

## Doğrulama katmanı (AI muhakeme denetçisi) — öne geçiren yön

MathHead'i "başka bir CAS"tan **AI muhakemesinin yargıcı**na çeviren katman.
AI bir İDDİA sunar; MathHead bağımsız denetler ve karşıörnek/uyarı verir.

| Araç | İmza | Örnek |
|---|---|---|
| `verify_equality` | `verify_equality(left, right)` | `(x**2-1)/(x-1)` vs `x+1` → `EQUAL_ON_COMMON_DOMAIN` (x=1 uyarısı) |
| `verify_solution` | `verify_solution(equation, symbol, claimed)` | `x**2==4`, `x`, `["2"]` → `SOLUTION_INCOMPLETE` (-2 kaçtı) |
| `verify_steps` | `verify_steps(steps)` | `["(x+1)**2","x**2+1"]` → `STEP_INVALID` (1. geçiş) |

**Neden öne geçirir (naif kontrolün kaçırdıkları):**

- `verify_equality` yalnız denkliği değil, **tanım kümesi ayrışmasını** da yakalar:
  `(x²-1)/(x-1)` ile `x+1` sembolik denk görünür ama `x=1`'de tanımsız →
  `EQUAL_ON_COMMON_DOMAIN` + `details.domain_caveat`. invalid'de somut karşıörnek.
- `verify_solution` değerleri ikame ile denetler **ve TAMLIĞI** kontrol eder —
  eksik kök (`SOLUTION_INCOMPLETE` + `details.missing`) veya yanlış kök
  (`SOLUTION_INCORRECT` + `details.wrong_values`). Tamlık kapalı-formda
  doğrulanamazsa `COMPLETENESS_UNKNOWN` (dürüst).
- `verify_steps` bir çözümü adım adım "not verir": ilk kırılan geçişi
  (`details.first_bad_step`, 1-tabanlı) + karşıörnek verir.

Dönüş `VerifyResult`: `status` (valid|invalid|unknown|error) + `reason_code` +
`explanation` + `details` (karşıörnek/eksik/ilk-hatalı-adım) + `meta`.

---

## Track B araçları (frontier — SAT indirgeme)

Zor problemleri **sağlanabilirliğe indirgeyip** çözer / imkânsızlığı ispatlar.
Girdi programatik (sayı `n`); çıktı ortak `ReasoningResult`.

| Araç | İmza | Sonuç |
|---|---|---|
| `pythagorean_coloring` | `pythagorean_coloring(n)` | `sat` (boyama) / `unsat` (imkânsız) |
| `pigeonhole` | `pigeonhole(n)` | `unsat` = güvercin yuvası ilkesi ispatı |
| `van_der_waerden` | `van_der_waerden(n, k, colors=2)` | `unsat` = n ≥ W(colors,k) (ispat) |
| `schur_number` | `schur_number(n, colors)` | `unsat` = n > S(colors) (ispat) |
| `graph_coloring` | `graph_coloring(edges, colors, n=None)` | `sat` (boyama, doğrulanmış) / `unsat` (kromatik sayı > colors) |
| `subset_sum` | `subset_sum(numbers, target)` | `sat` (alt küme, doğrulanmış) / `unsat` (yok) |

Motorun fiilen ispatladığı/yeniden ürettiği sonuçlar (dürüst kayıt, bilinen vs
açık ayrımı): `docs/track-b-results.md`.

**Dürüstlük:** Küçük örnekler ünlü sonuçların *kendisi* değil, **aynı yöntemdir**
(Boolean Pythagorean n=7825 sınırı ~200 TB ispat; burada küçük n anında çözülür).
Büyük ölçek `unknown`/`error` döner — gizlenmez.

**Doğrulanabilir sertifika:** `graph_coloring`/`subset_sum` `sat` döndüğünde tanık
(witness) BİR SERTİFİKADIR ve Z3'ten **bağımsız** olarak saf Python'da yeniden
denetlenir → `meta.verified: true` (kodlama hatası olsa bile yakalanır). **Dürüst
asimetri:** `unsat` için bağımsız-denetlenebilir **DRAT/LRAT** sertifikası üretmek
DIMACS düzeyinde bir SAT hattı ister — bu bir **duvar** olarak açıkça belgelenir
(çıktı `unsat`'ı verir ve notta belirtir); ayrıntı `docs/track-b-results.md`.
