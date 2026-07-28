# MathHead — Progress / ChangeLog

> **Bu dosyanın işi:** NE yaptık, NE ZAMAN, NEDEN — ekleme-only (append-only)
> günlük. En yeni en üstte. Küçük tasarım kararlarının *gerekçesi* `DECISIONS.md`'ye,
> yapılan işin *özeti* buraya.

---

## 2026-07-28 — v3.2 · ispat üreticisine ∃ (varoluşsal) akıl yürütme

**Yapıldı**

- `core/proof.py`: **∃-eleme** (taze tanık sabiti; `∀`-eleme onu da kullanır) +
  **∃-giriş** (hedef `∃x.ψ`, `ψ[t]` türetildiyse). Bağlam/witness yönetimi.
- `∃x P(x), ∀x(P→Q) ⊨ ∃x Q(x)` gibi çıkarımlar adım adım. Testler + regresyon
  → **78/78 yeşil**.
- Yeni karar: ADR-0016. Klasik FOL doğal tümdengelim parçası büyük ölçüde tamam.

**Dürüstlük:** Aritmetik türetim ve bazı karışık nicelik desenleri hâlâ yok →
Z3 kararı korunur (adımsız).

**Sıradaki (gelecek oturumlar):** ispatı LaTeX/metin dışa verme; performans;
(yayın akşam, sende).

## 2026-07-28 — v3.1 · ispat üreticisi genişletildi (RAA + MT/DS)

**Yapıldı**

- `core/proof.py` kural kümesi: modus tollens, ayrık tasım, çift olumsuzlama,
  De Morgan; + ikinci strateji **çelişkiden ispat (RAA)** → durum ayrımı (proof
  by cases) gibi dolaylı ispatlar adım adım çıkıyor.
- Testler (MT / DS / RAA / De Morgan) + regresyon → **76/76 yeşil**.
- Yeni karar: ADR-0015.

**Dürüstlük:** Varoluşsal (∃) eleme ve aritmetik türetim hâlâ yok → Z3 kararı
korunur (adımsız).

**Sıradaki (gelecek oturumlar):** ∃-eleme; GitHub release + PyPI (akşam, sende).

## 2026-07-28 — v3 · ispat üretimi (adım adım) (aynı oturum)

**Yapıldı**

- `core/proof.py`: entailment + NEDEN. (1) minimal öncül çekirdeği (unsat core),
  (2) ileri zincirleme **doğal tümdengelim** türetimi (modus ponens, ∧-ayıklama,
  iff, evrensel örnekleme). Klasik silogizm adım adım.
- Yeni MCP aracı `prove` (**12. araç**) + CLI `mathhead prove` + testler → **72/72**.
- Yeni karar: ADR-0014.

**Dürüstlük:** Türetici önerme + yüklem + evrensel parçasıyla sınırlı; aritmetik /
`or`-`not` / varoluşsal için türetim kurulamaz → Z3 kararı korunur, adımsız
("türetim yok" denir).

**Sıradaki (gelecek oturumlar):** türeticiyi genişletme (or-elim, varoluşsal);
GitHub release; PyPI (senin evden).

## 2026-07-28 — Optimizasyon denemesi · simetri kırma (dürüst: karışık sonuç)

**Yapıldı**

- `frontier`'a renk-simetri kırma eklendi (opsiyonel `symmetry_break`; doğruluk
  teste kilitli). Ölçüm: küçük/UNSAT'ta hızlandırdı; **SAT'ta yavaşlattı**
  (S(4)=44: 35s → 48s); W(2,5) 2-renkte değişmedi (faktör 2).
- **Dürüst sonuç:** naif simetri kırma duvarı (S(4)=45, W(2,6)) AŞMADI →
  varsayılan **kapalı**. Gerçek duvar araştırma-düzeyi SAT teknikleri ister.
  Detay: `docs/track-b-results.md`.

**Sıradaki (gelecek oturumlar):** ürünleşme (PyPI); farklı hızlandırma teknikleri.

## 2026-07-28 — Track B · Schur sayıları (bilinen değerler yeniden üretildi)

**Yapıldı**

- `frontier.schur_number_coloring`: {1..n} r-renk sum-free bölme. Router + MCP
  (**11. araç**) + CLI (`mathhead schur n r`) + testler → **65/65 yeşil**.
- Dürüst saldırı: S(2)=4, S(3)=13 **tam** yeniden üretildi (n=5, n=14 imkânsızlık
  ispatları); S(4) için S(4) ≥ 44 doğrulandı (n=44 sat, ~25 sn), üst sınır (n=45)
  duvara takıldı. Detay: `docs/track-b-results.md`.

**Dürüst sonuç:** S(5)=160 ve açık S(6) bu ortamda erişilemez. Sahte zafer yok.

**Sıradaki (gelecek oturumlar):** PyPI paketi; ölçek/çözücü; v3 ispat üretimi.

## 2026-07-28 — Track B · van der Waerden (bilinen değerler yeniden üretildi)

**Yapıldı**

- `frontier.van_der_waerden_coloring`: {1..n} r-renk, tek renkli k-terimli
  aritmetik dizi olmadan boyama. Router + MCP (**10. araç**) + CLI
  (`mathhead vdw n k`) + testler → **61/61 yeşil**.
- **Açık-problem sınıfına dürüst saldırı** (kullanıcı isteği): motor W(2,3)=9,
  W(2,4)=35, **W(2,5)=178** değerlerini AYNI SAT yöntemiyle **yeniden üretti**
  (her biri gerçek imkânsızlık ispatı; W(2,5) ~61 sn). Detay + dürüst
  compute-wall: `docs/track-b-results.md`.

**Dürüst sonuç:** Açık bir problem ÇÖZÜLMEDİ (W(2,6)=1132 ve açık W(2,7) bu
ortamın ötesinde). Ama araştırma değerleri doğrulanabilir biçimde üretildi ve
duvarın yeri şeffafça gösterildi. Sahte zafer yok.

**Sıradaki (gelecek oturumlar):** PyPI paketi; ölçek/çözücü iyileştirme; v3 ispat üretimi.

## 2026-07-28 — CLI · terminal arayüzü (aynı oturum)

**Yapıldı**

- `mathhead` CLI (argparse): entail / consistent / model / simplify / solve /
  diff / integrate / pigeonhole / pythagorean; `--json`; anlamlı çıkış kodları
  (0 sonuç, 1 hata, 2 unknown). Aynı `router`'a bağlı ince kabuk.
- `pyproject` script girişi (`mathhead`); README + CI rozeti. → **56/56 yeşil**.

**Sıradaki (gelecek oturumlar):** PyPI paketi, fonksiyon terimleri, v3 ispat üretimi.

## 2026-07-28 — v1.2 · yüklemler + bireyler (aynı oturum)

**Yapıldı**

- `translate`: üçüncü sort `U` (birey) + yorumsuz yüklemler (`Man(x)`, `Loves(a,b)`).
- Klasik silogizm çalışır: `∀x.(Man(x)→Mortal(x))`, `Man(socrates)` ⊨ `Mortal(socrates)`.
- Ad çakışması / arite / argüman-sort denetimleri (net reddeder). Yeni MCP aracı
  YOK (dil zenginleşti; mevcut 3 mantık aracı kapsıyor).
- Testler: silogizm + ilişkisel + çelişki + guardrail → **51/51 yeşil**.
- Yeni karar: ADR-0013.

**Karar:** v1.2'de yüklem argümanları yalnızca birey; fonksiyon terimleri (`f(x)`)
sonraki sürüme. Yüklem+quantifier undecidability'i artırır; `unknown` mümkün,
soundness korunur.

**Sıradaki (gelecek oturumlar — acele yok):** yorumsuz fonksiyon terimleri;
v3 ispat üretimi; Track B derinleştirme (graph coloring/Schur); ürünleştirme
(PyPI paketi, CLI, README rozetleri, kullanım kılavuzu).

## 2026-07-28 — v2.1 · Track B tohumu (aynı oturum)

**Yapıldı**

- `frontier/`: problemi SAT'a indirgeme demoları — Boolean Pythagorean
  renklendirme + güvercin yuvası (pigeonhole) imkânsızlık ispatı.
- 2 MCP aracı (toplam **9**). Testler: üretilen boyamanın **bağımsız doğrulaması**
  (tek renkli üçlü yok) + PHP ispatı → **42/42 yeşil**.
- Yeni karar: ADR-0012.

**Karar:** Track B "yöntem"i çalışır (indirgeme → Z3). Dürüstlük: küçük ölçek;
ünlü sonuçların kendisi değil, aynı yöntem. Dış sözleşme DEĞİŞMEDİ.

**Sıradaki:** ölçek/CDCL sınırları, daha çok indirgeme (graph coloring, Schur),
veya v1.2 (yüklem sembolleri).

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
