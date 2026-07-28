# MathHead — Progress / ChangeLog

> **Bu dosyanın işi:** NE yaptık, NE ZAMAN, NEDEN — ekleme-only (append-only)
> günlük. En yeni en üstte. Küçük tasarım kararlarının *gerekçesi* `DECISIONS.md`'ye,
> yapılan işin *özeti* buraya.

---

## 2026-07-28 — v2 · hesap katmanı (SymPy) (aynı oturum)

**Yapıldı**

- `compute/`: ast-whitelist → SymPy çevirici (`sympify`/`eval` YOK — güvenlik).
- 4 işlem: `simplify`, `solve`, `differentiate`, `integrate` + `ComputeResult`.
- `router` compute görevlerini yönlendiriyor; MCP'ye 4 yeni araç (toplam **7**).
- Testler: hesap + güvenlik (`__import__` / bilinmeyen fonksiyon reddi) →
  **37/37 yeşil**.
- Yeni karar: ADR-0011.

**Karar:** Hesap, mantıktan ayrı katman; girdi yine beyaz-liste. SymPy kapalı
formda çözemezse dürüstçe değerlendirilmemiş sonuç. Dış sözleşme (mevcut araçlar)
DEĞİŞMEDİ.

**Sıradaki:** Track B tohumu (kombinatoryal problemi SAT'a indirgeme) / T9.

## 2026-07-28 — v1.1 · nicelik belirteçleri + Real (aynı oturum)

**Yapıldı**

- `translate` iki geçişe ayrıldı (infer/sort + build); kapsam (scope) yönetimi.
- `forall(x, …)` / `exists(x, …)`: bağlı sabit mangling → değişken yakalama yok.
- Real sayı desteği: ondalık sabit varsa numeric domain = Real (yoksa Int).
- `logic` artık `translate_all` kullanıyor (paylaşımlı bağlam + doğru domain).
- Real model değeri okunur (`3/2` → `1.5`).
- Testler: quantifier + Real + capture + **soundness** (∀∃'de asla yanlış cevap;
  gerekirse `unknown`) → **25/25 yeşil**.
- Yeni karar: ADR-0010.

**Karar:** Nicelik belirteçleri karar-verilebilirliği zayıflatır; `unknown`
birinci sınıf, **soundness** korunur. Dış sözleşme (ReasoningResult, MCP) DEĞİŞMEDİ.

**Sıradaki:** T9 (explanation zenginleştir) / v2 (SymPy compute).

## 2026-07-28 — v1 · çekirdek çalışır (aynı oturum)

**Yapıldı**

- `guardrails`: `validate_input` (boyut/derinlik/sözdizimi) + `solver_config`
  (sabit seed + timeout → determinizm).
- `core/translate`: Python `ast` tabanlı, beyaz-listeli parser → Z3; sort
  çıkarımı (Bool/Int); doğrusallık çiti (var*var reddi); zincirli karşılaştırma.
- `core/logic`: `check_entailment` (¬sonuç UNSAT + karşıörnek), `check_consistency`
  (sat/unsat + **unsat core**), `find_model`. İzlenebilir `meta`.
- `router.route` 3 ilkeli bağlar; `mcp_server` → router → core.
- Testler: best/worst + **determinizm (×50)** + guardrail → **17/17 yeşil**.
- Canlı MCP: 3 araç kayıtlı (`entailment`/`consistency`/`model`), JSON çıktı temiz.
- Yeni karar: ADR-0009 (ast-tabanlı parser + karar-verilebilir v1 parçası).

**Karar:** v1 dili bilinçle **karar verilebilir** (Presburger + önermeler);
Real/∀∃/nonlinear v1.1+'a ertelendi. Dış sözleşme (ReasoningResult, MCP imzaları)
DEĞİŞMEDİ.

**Doğrulandı:** `pytest` 17/17; z3 5.0.0; uçtan uca route → Z3 → JSON.

**Sıradaki:** T9 (explanation zenginleştir) / v1.1 (Real + nicelik belirteçleri).

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
