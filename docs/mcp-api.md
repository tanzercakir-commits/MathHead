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

---

## Girdi grameri (v1.1)

Girdi **Python ifade sözdizimi** ile yazılır; motorun ayrıştırıcısı (`ast`
tabanlı, beyaz-listeli — ADR-0009/0010) yalnızca aşağıdakine izin verir, gerisini
net reddeder. Ayrıştırmayı Python yaptığı için **operatör önceliği ve parantez**
beklendiği gibi çalışır.

| Kategori | İzin verilenler | Not |
|---|---|---|
| Boolean bağlaç | `and`, `or`, `not` | Python anahtar sözcükleri |
| Boolean fonksiyon | `implies(a, b)`, `iff(a, b)`, `xor(a, b)` | her biri tam 2 argüman |
| Nicelik belirteci | `forall(x, gövde)`, `exists(x, gövde)` | `x` bağlı değişken |
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

**Hâlâ YOK:** doğrusal olmayan çarpım, fonksiyon/yüklem sembolleri (`P(x)`),
küme/dizi teorileri. **Dürüst uyarı:** nicelik belirteçleri FOL'u yarı-karar
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
