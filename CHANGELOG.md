# Changelog

Tüm önemli değişiklikler burada tutulur. Sürümleme [SemVer](https://semver.org/lang/tr/).

## [Yayınlanmamış]

### Eklendi

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
