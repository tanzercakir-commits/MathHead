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

## Girdi grameri (v1)

Girdi **Python ifade sözdizimi** ile yazılır; motorun ayrıştırıcısı (`ast`
tabanlı, beyaz-listeli — ADR-0009) yalnızca aşağıdakine izin verir, gerisini net
reddeder. Ayrıştırmayı Python yaptığı için **operatör önceliği ve parantez**
beklendiği gibi çalışır.

| Kategori | İzin verilenler | Not |
|---|---|---|
| Boolean bağlaç | `and`, `or`, `not` | Python anahtar sözcükleri |
| Boolean fonksiyon | `implies(a, b)`, `iff(a, b)`, `xor(a, b)` | her biri tam 2 argüman |
| Karşılaştırma | `<`, `<=`, `==`, `!=`, `>=`, `>` | zincir destekli: `1 < x < 5` |
| Aritmetik | `+`, `-`, `*` | **doğrusal**: `değişken*değişken` yasak |
| Değişken | `Bool` veya `Int` | sort **bağlamdan** çıkarılır (aşağıda) |
| Sabit | tam sayı, `True`, `False` | Real yok (v1.1) |

**Sort çıkarımı (tür):** bir ismin Boolean mı Int mi olduğu kullanımından
belirlenir — karşılaştırma/aritmetik içinde geçen → `Int`; bağlaç/fonksiyon
içinde ya da yalın atom → `Bool`. Bir isim **aynı problemde** hem Bool hem Int
kullanılırsa motor `error` (`PARSE_ERROR`) döner — sessiz varsayım yok
(PRINCIPLES #2).

**v1'de YOK (bilerek):** Real sayılar, `∀`/`∃` nicelik belirteçleri, doğrusal
olmayan çarpım. Bunlar v1.1+ hedefi (Plan yol haritası). Neden dar? Bu parça
**karar verilebilir** (decidable: önermeler + doğrusal tam sayı / Presburger),
yani motor neredeyse her zaman kesin `valid/invalid/sat/unsat` verir.

Örnek geçerli ifadeler: `p`, `not(p)`, `implies(p, q)`, `p and (q or not(r))`,
`x > 2`, `1 < x < 5`, `2*x + 3 <= y`, `iff(p, q)`.

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
