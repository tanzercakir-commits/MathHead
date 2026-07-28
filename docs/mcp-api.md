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

## Girdi grameri (v1 parçası)

v1 yalnızca aşağıdaki parçayı (fragment) kabul eder; gerisi `error` ile
reddedilir (whitelist — ADR-0007).

```
expr        := iff
iff         := implies ( "iff" implies )*
implies     := disj ( "implies" disj )*
disj        := conj ( "or" conj )*
conj        := neg ( "and" neg )*
neg         := "not" neg | atom
atom        := bool_var | comparison | "(" expr ")"
comparison  := term ( "<" | "<=" | "=" | ">=" | ">" ) term
term        := factor ( ("+" | "-") factor )*
factor      := coeff "*" var | var | number        ; DOĞRUSAL: var*var YASAK
var         := IDENT        ; sayısal değişken (Int/Real teorisi)
bool_var    := IDENT        ; Boolean değişken
number      := INTEGER | REAL
```

Fonksiyon/yordam çağrısı gösterimi de kabul edilir: `implies(p, q)`, `not(p)`,
`and(p, q)` — sunucu için daha kolay. İki gösterim de aynı AST'ye çevrilir.

> **Açık tasarım kararı (T2'de kesinleşir):** bir `IDENT`'in Boolean mı sayısal mı
> olduğu, kullanım bağlamından çıkarılır (karşılaştırmada geçen → sayısal; atom
> olarak geçen → Boolean). Belirsizlik varsa motor **reddeder** (sessiz varsayım
> yok — PRINCIPLES #2).

**Nicelik belirteçleri (∀/∃):** v1'de **yok**, v1.1 hedefi (Plan yol haritası).

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
