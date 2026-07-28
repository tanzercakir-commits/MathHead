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

**İzinli:** `+ - * / **`, tekli `-`, semboller, sayı (tam/ondalık), fonksiyonlar
`sin cos tan asin acos atan sinh cosh tanh exp log sqrt Abs`. `solve` girdisi
`a == b` (Eq) veya `=0` varsayımıyla düz ifade olabilir.

**Çıktı — `ComputeResult`:** `status` (`ok`|`error`), `operation`, `result`
(metin veya kök listesi), `explanation`, `reason_code` (`OK`|`PARSE_ERROR`|
`COMPUTE_FAILED`), `meta` (`engine=sympy`, `sympy_version`, `elapsed_ms`).

**Dürüstlük:** SymPy kapalı formda çözemezse (ör. `∫ exp(x**2) dx`) sonucu
gizlemez; değerlendirilmemiş/özel-fonksiyonlu tam ifadeyi (`erfi(...)` gibi)
döner.

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

Motorun fiilen ispatladığı/yeniden ürettiği sonuçlar (dürüst kayıt, bilinen vs
açık ayrımı): `docs/track-b-results.md`.

**Dürüstlük:** Küçük örnekler ünlü sonuçların *kendisi* değil, **aynı yöntemdir**
(Boolean Pythagorean n=7825 sınırı ~200 TB ispat; burada küçük n anında çözülür).
Büyük ölçek `unknown`/`error` döner — gizlenmez.
