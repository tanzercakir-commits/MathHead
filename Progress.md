# MathHead — Progress / ChangeLog

> **Bu dosyanın işi:** NE yaptık, NE ZAMAN, NEDEN — ekleme-only (append-only)
> günlük. En yeni en üstte. Küçük tasarım kararlarının *gerekçesi* `DECISIONS.md`'ye,
> yapılan işin *özeti* buraya.

---

## 2026-07-28 — v0.1 · vizyon düzeltmesi (aynı oturum)

**Değişti**

- Hedef iki hatta ayrıldı: **Track A** (doğrulanabilir çekirdek, yakın vade) +
  **Track B** (zor/açık problemlere saldırı, Kuzey Yıldızı, v3+). Proje sahibinin
  geri bildirimi: açık problem çözümü de birinci sınıf hedef olmalı.
- `Plan.md` §2 yeniden yazıldı (SMT/SAT'ın açık problem çözme siciliyle:
  Boolean Pythagorean Triples 2016, Keller 7. boyut 2020, Schur 5 2017).
- Yeni karar: `DECISIONS.md` ADR-0008.

**Karar:** Track B kapsamı = satisfiability'e indirgenebilen problemler + ispat
doğrulama. v1 kapsamı DEĞİŞMEDİ (hâlâ Track A / Akıl Yürütme Denetçisi).

## 2026-07-28 — v0 · iskelet & tasarım (bu oturum)

**Kuruldu**

- Proje iskeleti: `src/mathhead/{core, compute, router, guardrails, server}` + `tests/` + `docs/`
- Dönüş sözleşmesi `ReasoningResult` donduruldu: `status / reason_code / explanation / witness / meta`
- MCP sunucu iskeleti (FastMCP, 3 araç: `entailment` / `consistency` / `model`) — stub
- Guardrail sabitleri + imzaları: `validate_input`, `solver_config`
- Tasarım dosyaları: `Plan.md`, `Todo.md`, `Progress.md`, `PRINCIPLES.md`, `DECISIONS.md`
- `docs/`: `architecture.md`, `mcp-api.md`, `glossary.md`
- Testler: `test_smoke` (geçer) + `test_logic` (spec, şimdilik `xfail`)

**Mimari kararlar** (özet — detay `DECISIONS.md`)

- ADR-0001: Sıfırdan FOL motoru yerine kanıtlanmış çözücü orkestrasyonu
- ADR-0002: Mantık çekirdeği = **Z3** (SMT); hesap = **SymPy** (CAS)
- ADR-0003: Dil = **Python**; MCP SDK = **FastMCP** (`mcp[cli]`)
- ADR-0004: Dış API/sözleşme **erken dondurulur**

**Doğrulandı**

- Çekirdek harici bağımlılık olmadan temiz import ediliyor; `ReasoningResult`
  sözleşmesi ve `is_conclusive()` beklendiği gibi çalışıyor.

**Sıradaki adım:** `Todo` → T1 (guardrails) → T2 (translate) → T3 (entailment).

---

<!-- Yeni girdiler bu satırın ÜSTÜNE eklenecek. Şablon:
## YYYY-AA-GG — vX · başlık
**Yapıldı** …  **Karar** …  **Doğrulandı** …  **Sıradaki** …
-->
