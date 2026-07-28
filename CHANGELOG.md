# Changelog

Tüm önemli değişiklikler burada tutulur. Sürümleme [SemVer](https://semver.org/lang/tr/).

## [Yayınlanmamış]

### Eklendi

- **Doğal dil → formal (`interpret_natural`):** ROADMAP I2 — "2. duvar"a (fazla
  varsayım) panzehir. Kurallı, bilingual (TR+EN), **TANI-YA-DA-REDDET**: tanınmayan/
  belirsiz girdide tahmin etmez (`UNRECOGNIZED`/`AMBIGUOUS`). Anladığında
  **round-trip restatement** ile ne anlaşıldığını NL geri-ifade eder (onayla-sonra-
  güven). Tanınan: türev/integral/limit/çözme/çarpanlara ayırma/asallık/EBOB/denklik.
  Yeni `core/nl.py`. MCP (**70 araç**) + CLI (`interpret`) + 18 test. 3 yeni reason_code.
- **Doğrulama katmanı II — kalkülüs & matris iddiaları (`verify_derivative`,
  `verify_integral`, `verify_limit`, `verify_series`, `verify_matrix_identity`):**
  ROADMAP I1. AI'ın türev/integral/limit/Taylor-seri/matris-özdeşliği iddialarını
  bağımsız denetler (iddia ≟ hesaplanan doğru). `verify_integral` türev-alıp-
  karşılaştır yöntemiyle **+C sabit farkını** dürüstçe hoş görür; yanlışta
  `details.correct` doğru değeri verir. MCP (**69 araç**) + CLI + 20 test.
- **LLM-tuzak benchmark (Track C4):** `benchmarks/llm_traps.json` (14 klasik LLM
  hata deseni: eksik/yanlış çözüm, yanlış özdeşlik, domain tuzağı, yanlış
  eşitsizlik, kök dalı, hatalı adım, asallık, aritmetik, modüler, Diophantine) +
  `benchmarks/run.py` harness + `tests/test_benchmark_traps.py` regresyon çiti +
  `docs/benchmark-results.md`. **Yakalama oranı %100** (doğru-pozitif kontrolü
  dahil — doğruyu yanlış işaretlemez). Dürüst çerçeve: yeniden-üretilebilir
  gösterim, canlı LLM A/B değil.
- **Bağımsız sertifika denetleyicisi (`check_certificate`):** ROADMAP Track C2.
  Bir sonucu, onu ÜRETEN motordan (Z3/SymPy) **BAĞIMSIZ**, yalnız Python stdlib
  (`ast`+`fractions`, mümkünse tam aritmetik) ile yeniden doğrular →
  `verified`/`refuted`. Yeni `mathhead/certificate.py` **z3/sympy'yi fiilen import
  etmez** (alt-süreç testiyle kanıtlı — "bize güvenme, checker'ı çalıştır"). Türler:
  `subset_sum`, `graph_coloring`, `solution`, `not_equal`, `inequality_counterexample`.
  MCP (**64 araç**) + CLI (`check-certificate`) + 13 test. Yeni statü:
  `verified`/`refuted` (taksonomiye işlendi).
- **Çapraz denetim — Z3 ⋈ SymPy (`cross_check`):** ROADMAP Track C3. Bir denklik
  iddiasını **iki bağımsız motorla** doğrular; mutabakat şart. `CONSENSUS_EQUAL/
  _NOT_EQUAL` (yüksek güven), `ENGINES_DISAGREE` (çelişki → domain/ince konu
  bayrağı — ör. `(x²-1)/(x-1)` vs `x+1`), `SINGLE_ENGINE` (yalnız biri, ör.
  transandantalde SymPy). MCP (**63 araç**) + CLI (`cross-check`) + 7 test.
- **Doğrulama katmanı — AI muhakeme denetçisi (`verify_equality`,
  `verify_solution`, `verify_steps`):** ROADMAP Track C1 — "öne geçiren yön".
  MathHead'i "başka bir CAS"tan **AI iddialarının bağımsız yargıcı**na çevirir.
  `verify_equality` denkliği **ve tanım-kümesi ayrışmasını** (domain tuzağı,
  `(x²-1)/(x-1)` vs `x+1` → x=1 uyarısı) yakalar; `verify_solution` doğruluk **ve
  TAMLIĞI** denetler (eksik/yanlış kök); `verify_steps` adım zincirinde ilk hatayı
  bulur. Yeni modül `core/verify.py` + `VerifyResult`. MCP (**62 araç**) + CLI
  (`verify-eq/verify-solution/verify-steps`) + 15 test. 10 yeni reason_code
  (taksonomiye işlendi).

## [0.2.0] — 2026-07-28

Motorun büyük genişlemesi: **24 → 59 MCP aracı**, **146 → 357 test**, kapsam
**%87**. Aşamalı yol haritasının (`ROADMAP.md`) 1–11 aşamaları tamamlandı —
lineer cebir, sayı teorisi, kombinatorik, çok değişkenli analiz, olasılık &
istatistik, eşitsizlik ispatı (Z3 NRA) ve genişletilmiş Track B; arada üç
sağlamlaştırma turu (property/fuzz, taksonomi/golden, coverage/API-ref).

### Eklendi

- **Track B genişleme + doğrulanabilir sertifika (`graph_coloring`, `subset_sum`):**
  Aşama 10. İki yeni NP-tam indirgeme (graf k-boyama, alt küme toplamı). **Olumlu
  sertifika:** `sat` tanığı Z3'ten **bağımsız**, saf Python'da yeniden denetlenir
  → `meta.verified=true` (kodlama hatası olsa da yakalanır). **Dürüst asimetri:**
  `unsat` için bağımsız DRAT/LRAT sertifikası bir DUVAR olarak açıkça belgelenir
  (`docs/track-b-results.md`). MCP (**59 araç**) + CLI (`graph-coloring/subset-sum`).
- **Eşitsizlik ispatı & nonlineer (`prove_inequality`, `prove_nonnegative`,
  `find_real_solution`):** Aşama 9. Z3 doğrusal-olmayan gerçel aritmetik (NRA /
  nlsat) ile polinom eşitsizliklerini **ispatlar** (ret-ile-ispat: `¬P` UNSAT mı)
  ya da karşıörnek verir; nonlineer kısıtlara gerçel çözüm bulur. AM-GM
  (`x²+y²≥2xy`), kareler-tamamlama vb. ispatlanır. **Dürüstlük:** `unknown`
  birinci sınıf; nonpolinom üs / non-bool hedef reddedilir. Yeni modül
  `core/inequality.py` (nonlineer Z3 çevirici). MCP (**57 araç**) + CLI
  (`prove-inequality/prove-nonnegative/real-solve`). +15 test.
- **Olasılık & istatistik (`mean`, `variance`, `standard_deviation`, `median`,
  `distribution`):** Aşama 7. Betimsel istatistik (tam/rasyonel) + `sympy.stats`
  ile 7 adlandırılmış dağılım (`normal/binomial/poisson/exponential/uniform/
  bernoulli/geometric`): E[X]/Var/std (sembolik/tam) + `P(X≤k)`/yoğunluk. MCP
  (**54 araç**) + CLI (`mean/variance/std/median/distribution`). +15 test.
- **Çok değişkenli analiz (`gradient`, `jacobian`, `hessian`, `definite_integral`,
  `summation`, `product`, `solve_ode`):** Aşama 6. Gradyan/Jacobian/Hessian,
  belirli integral (sonsuz sınır dahil), toplam/çarpım (Σ/Π, kapalı form:
  `Σi = n²/2+n/2`) ve **ODE çözümü** (`dsolve`; `y'`/`y''` ya da `D(y,k)`
  notasyonu, güvenli ayrıştırıcı). Çözülemeyen ODE'de dürüst hata. MCP
  (**49 araç**) + CLI (`gradient/jacobian/hessian/defint/sum/product/ode`). +16 test.
- **Kombinatorik & ayrık (`permutations`, `combinations`, `factorial`,
  `partition_count`, `solve_recurrence`):** Aşama 4. Permütasyon/kombinasyon,
  faktöriyel, tam sayı bölüntü sayısı ve **doğrusal özyineleme kapalı-form
  çözümü** (`rsolve` — Fibonacci → Binet). `solve_recurrence` özyinelemeyi güvenli
  bir mini-ayrıştırıcıyla okur (`=`/`==`, whitelist dışı ad reddedilir); doğrusal
  olmayan bağıntıda dürüst hata. MCP (**42 araç**) + CLI (`perm/comb/factorial/
  partitions/recurrence`). +18 test.
- **Sayı teorisi (`gcd`, `lcm`, `is_prime`, `factorize`, `modular_inverse`,
  `chinese_remainder`, `linear_diophantine`):** Aşama 3. Tam sayılarda GCD/LCM,
  deterministik asallık, asal çarpanlara ayırma, modüler ters, Çin Kalan Teoremi
  (CRT), doğrusal Diophantine. **Dürüstlük:** modüler ters yoksa / CRT bağdaşmazsa
  hata; Diophantine tam sayı çözüm yoksa boş liste. MCP (**37 araç**) + CLI
  (`gcd/lcm/isprime/factorize/modinv/crt/diophantine`). +18 test.
- **Lineer cebir II (`matrix_multiply`, `matrix_solve`, `eigenvectors`, `rref`,
  `nullspace`, `lu_decomposition`):** Aşama 1 — lineer cebir tamamlandı. `Ax=b`
  matris formunda (tutarsız → boş, sonsuz → parametrik, dürüst); matris çarpımı
  (boyut denetimli); özvektör; RREF + pivotlar; boş uzay (kernel) tabanı; LU
  ayrıştırma. MCP (**30 araç**) + CLI (`matmul/matsolve/eigenvectors/rref/
  nullspace/lu`). +15 test (`tests/test_linalg.py`).
- **Lineer cebir / matris (`determinant`, `matrix_inverse`, `eigenvalues`,
  `matrix_rank`):** SymPy `Matrix` üstünde. Girdi `list[list[str]]` (hücreler
  sembolik olabilir → `det[[a,b],[c,d]] = a*d - b*c`). **Dürüstlük:** tekil
  (singular) matriste ters uydurulmaz, `COMPUTE_FAILED`; özdeğerler karmaşık/
  irrasyonel değerleri tam formda + cebirsel katlılıkla verir (sıralı →
  deterministik). MCP araçları (**24 araç**) + `mathhead det/inverse/eigenvals/
  rank` CLI (`"1,2;3,4"` dizgisi). +18 test (`tests/test_matrix.py`).
- **Kalkülüs & sistemler (`limit`, `series`, `solve_system`):** hesap katmanı
  (SymPy) genişledi. `limit` — sonlu/sonsuz nokta + tek yön (`+`/`-`);
  `series` — bir nokta etrafında Taylor açılımı (`order`. mertebe); `solve_system`
  — çok değişkenli denklem sistemi (doğrusal + doğrusal olmayan). **Dürüstlük:**
  `solve_system` boş liste döndürerek "çözüm yok"u gizlemez, serbest değişkeni
  parametrik gösterir. MCP araçları (**20 araç**) + `mathhead limit/series/
  solve-system` CLI. +18 test (`tests/test_calculus.py`).
- **İspat üretimi (`prove`):** entailment için *neden* — minimal öncül çekirdeği
  (unsat core) + adım adım **doğal tümdengelim**: modus ponens/tollens, ayrık
  tasım, ∧-ayıklama, iff, çift olumsuzlama, De Morgan, evrensel örnekleme,
  **varoluşsal eleme/giriş (∃)**; ve **çelişkiden ispat (RAA)** ile durum ayrımı
  (proof by cases). Silogizm, ∃-çıkarımı ve proof-by-cases adım adım. MCP aracı
  `prove` (12 araç) + `mathhead prove` CLI.
- **Model numaralandırma (`enumerate_models`):** bir formülü sağlayan tüm/çoklu
  farklı modeli (all-SAT, bloklama-cümlesi) döndürür; `exhaustive` bayrağıyla
  "tümü mü, sınır mı" dürüstçe belirtilir. MCP aracı (13 araç) + `mathhead
  enumerate` CLI.
- **Optimizasyon (`optimize`):** kısıtlar altında sayısal bir amacı en büyük/
  küçük yapan çözümü bulur (Z3 Optimize / MaxSMT). `unbounded` / `unsat` /
  açık-sınır dürüstçe raporlanır. MCP aracı (14 araç) + `mathhead optimize` CLI.
- **MaxSAT (`max_satisfy`):** zorunlu (hard) kısıtları sağlayıp en çok (ağırlıklı)
  yumuşak (soft) kısıtı sağlar — aşırı-kısıtlı / çelişen isteklerin çözümü. MCP
  aracı (15 araç) + `mathhead maxsat` CLI.
- **Denklik & sınıflandırma (`equivalent`, `classify`):** iki ifade mantıksal
  denk mi (A ≡ B); bir formül totoloji / çelişki / olumsal mı. MCP (17 araç) +
  `mathhead equiv` / `mathhead classify` CLI.

### Değişti / sağlamlaştırma

- **Determinizm düzeltmesi (ADR-0020):** denklik kararı SymPy `.equals()`'ten
  arındırıldı — o içsel rastgele örnekleme yapıyordu (`sqrt(x²)` vs `x` çağrılar
  arası değişiyordu). Ortak deterministik yardımcı `verify._equal_verdict`
  (simplify + sabit-nokta karşıörnek); `verify_equality`/`verify_steps`/
  `cross_check` paylaşır. Verdict artık kararlı **ve** daha güçlü (karşıörnekli).
- **Sağlamlaştırma-3 (ROADMAP Aşama 8):** (1) **Kapsam (coverage)** — `pytest-cov`
  + `[tool.coverage]`; MCP katman testi (`tests/test_mcp_layer.py`, 54 aracı uçtan
  uca çağırır + kayıtla senkron tutar) → kapsam %85→**%87** (mcp_server %67→%97).
  (2) **Otomatik API referansı** — `scripts/gen_api_reference.py` MCP'ye kayıtlı
  araçlardan `docs/api-reference.md` üretir; `tests/test_api_reference.py` güncel
  kalmasını zorlar. (3) **Benchmark regresyon çiti** — katastrofik yavaşlama için
  cömert (10 sn) üst sınır testi.
- **Sağlamlaştırma-2 (ROADMAP Aşama 5):** (1) **Hata taksonomisi** birleştirildi
  → `docs/error-taxonomy.md` (tüm `status`/`reason_code` kanonik listesi) +
  `tests/test_taxonomy.py` bunu zorlar (belgesiz kod sızarsa kırılır). (2) **Golden
  fixtures** → `tests/fixtures/golden.json` (32 bilinen girdi→çıktı) +
  `tests/test_golden.py` (regresyon çiti). (3) **Benchmark iskeleti** →
  `scripts/benchmark.py` (taban çizgisi; süre eşiği yok) + duman testi.
- **Sağlamlaştırma-1 (ROADMAP Aşama 2) — hesap katmanı property testleri:**
  `tests/test_compute_properties.py`. Matematiksel değişmezler çapraz kontrol:
  `det(A·B)=det(A)·det(B)`, `det(Aᵀ)=det(A)`, `Ax=b` roundtrip (b=Ax → x geri),
  `simplify` idempotent. **Parser fuzz** (güvenlik): rastgele/kötücül metin ve
  düzensiz matrislerde çökme yok, yalnız `ok|error`. Determinizm denetimi
  (det/rank/özdeğer/simplify) 3 tohumda kararlı.
- **Property-based testler (`hypothesis`):** rastgele formüllerde değişmezler
  (çökme yok, araçlar tutarlı, türetici sağlam). Test bir zayıflık yakaladı →
  **determinizm garantisi kesinleştirildi**: *verdict* deterministik, *tanık* bir
  geçerli örnek (birden çok çözümde değişebilir) — ADR-0019.

## [0.1.0] — 2026-07-28

İlk yayınlanabilir sürüm. AI'ın **MCP** üzerinden kullanabileceği, first-order
logic temelli, **deterministik** matematik akıl yürütme, hesap ve indirgeme motoru.

### Eklendi

- **Mantık çekirdeği (Z3):** `entailment` / `consistency` / `find_model`;
  önermeler mantığı + doğrusal aritmetik + nicelik belirteçleri (`∀`/`∃`) + Real
  sayılar + yorumsuz yüklemler (`Man(x)`) → klasik silogizm çalışır.
- **Hesap katmanı (SymPy):** `simplify` / `solve` / `differentiate` / `integrate`.
- **Track B (SAT indirgeme):** güvercin yuvası, Boolean Pythagorean, van der
  Waerden (W(2,3..5) yeniden üretildi), Schur (S(2..3) yeniden üretildi).
  Ayrıntı: `docs/track-b-results.md`.
- **Arayüzler:** MCP sunucusu (**11 araç**) + `mathhead` komut satırı aracı (`--json`).
- Determinizm (sabit tohum + zaman aşımı), guardrail'ler, `unknown`/`error`
  birinci sınıf çıktı (dürüstlük). **66 otomatik test**, CI (GitHub Actions).

### Prensipler

Bağlam kaybı, fazla varsayım ve non-determinizme karşı: açık prensipler
(`PRINCIPLES.md`), karar günlüğü (`DECISIONS.md`, 13 ADR), ilerleme günlüğü
(`Progress.md`) ve net protokol (`docs/mcp-api.md`).
