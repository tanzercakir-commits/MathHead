# MathHead — Yol Haritası (Aşamalı)

> **Bu dosyanın işi:** İlerlemenin AŞAMA AŞAMA planı. Kullanıcı "şu aşamaya kadar
> devam et" der; ajan o aşamaya kadar sırayla, otonom ilerler.
> Güncel ince görevler `Todo.md`'de; ne yapıldığı `Progress.md`'de; hedef mimari
> `Plan.md`'de. Bu dosya = **sıra + kilometre taşları** görünümü.

---

## Çalışma protokolü (mod)

- Kullanıcı bir **hedef aşama** söyler: ör. *"Aşama 5'e kadar devam et."*
- Ajan **1'den hedefe** kadar sırayla ilerler; her aşamayı bağımsız bitirir.
- **Her aşama için DONE kriteri (değişmez):**
  1. Tüm testler yeşil (`pytest` — sağlama kapısı / test-gated)
  2. `commit` + `push` (aşama başına ayrı commit → yarıda durulursa durum temiz)
  3. Docs güncel (`mcp-api.md` / `README` / `CHANGELOG`)
  4. `Progress.md` + `Todo.md` işlendi; varsa **dürüst duvar** yazıldı
- Hedefte **durur**, toplu özet verir. Yarıda geri-dönülmez bir karar çıkarsa
  (ör. dış sözleşme kırılması) durup sorar. Aksi halde durmaz.
- Aşamalar **yeniden sıralanabilir / atlanabilir** — bu bir sözleşme değil, plan.

Durum işareti: `[ ]` bekliyor · `[~]` sürüyor · `[x]` bitti · `[S]` = sağlamlaştırma

---

## A. Motor geliştirme (mühendislik — ajanda)

```
[x] Aşama 0 · MEVCUT ÇEKİRDEK  (bitti — 146 test, 24 MCP aracı)
    ├─ Mantık (Z3):  entailment/consistency/model/prove/equivalent/
    │                classify/enumerate/optimize/maxsat
    ├─ Hesap (SymPy): simplify/solve/diff/integrate · limit/series/
    │                solve_system · det/inverse/eigenvalues/rank
    └─ Track B (SAT indirgeme): pigeonhole/pythagorean/vdW/Schur

[x] Aşama 1 · Lineer cebiri tamamla  (bitti — 161 test, 30 araç)
    └─ matris çarpımı, Ax=b (matris formu), özvektör (eigenvector),
       rref/boş uzay (nullspace), LU ayrıştırma
       ↳ dürüst duvar: tekil/tutarsız sistemleri açıkça raporla ✅

[x] Aşama 2 · [S] Sağlamlaştırma-1  (bitti — 169 test)
    └─ `compute` determinizm denetimi + property test (hypothesis: det çarpımsal/
       transpoz, Ax=b roundtrip, simplify idempotent) + parser fuzz ✅

[x] Aşama 3 · Sayı teorisi (number theory)  (bitti — 187 test, 37 araç)
    └─ gcd/lcm, asal test (isprime), çarpanlara ayırma (factorint),
       modüler ters + CRT (Çin kalan teoremi), doğrusal Diophantine ✅
       ↳ dürüst: ters yok / CRT bağdaşmaz → hata; Diophantine çözümsüz → boş

[x] Aşama 4 · Kombinatorik & ayrık  (bitti — 205 test, 42 araç)
    └─ permütasyon/kombinasyon, binom, bölüntü (partition),
       yineleme bağıntısı (recurrence) kapalı-form çözümü ✅ (Fibonacci→Binet)

[x] Aşama 5 · [S] Sağlamlaştırma-2  (bitti — 242 test)
    └─ hata taksonomisi (docs/error-taxonomy.md + test_taxonomy) +
       golden senaryolar (fixtures/golden.json, 32) + benchmark iskeleti ✅

[x] Aşama 6 · Çok değişkenli analiz (multivariable)  (bitti — 258 test, 49 araç)
    └─ gradyan, Jacobian, Hessian, belirli integral, seri toplam/çarpım,
       temel ODE (diferansiyel denklem) çözümü ✅
       ↳ dürüst: çözülemeyen ODE → COMPUTE_FAILED (uydurma yok)

[x] Aşama 7 · Olasılık & istatistik  (bitti — 273 test, 54 araç)
    └─ betimsel (mean/var/std/median) + 7 adlandırılmış dağılım (E/Var/std +
       cdf/pmf, sembolik) ✅

[x] Aşama 8 · [S] Sağlamlaştırma-3  (bitti — 330 test, kapsam %87)
    └─ coverage (pytest-cov + MCP katman testi %85→%87) + benchmark çiti +
       otomatik API referansı (docs/api-reference.md, kod=doküman) ✅

[x] Aşama 9 · Eşitsizlik ispatı & nonlineer  (bitti — 345 test, 57 araç)
    └─ Z3 nonlinear real (NRA/nlsat) ile eşitsizlik kanıtı (AM-GM, kareler-
       tamamlama) + gerçel çözüm bulma. core/inequality.py ✅
       ↳ dürüst duvar: NRA yarı-karar verilebilir → unknown birinci sınıf ✅
       ↳ not: SOS-sertifikası yerine CAD-temelli Z3 kararı (daha güçlü/tam)

[x] Aşama 10 · Track B genişletme + sertifika  (bitti — 357 test, 59 araç)
    └─ yeni indirgemeler: graph_coloring, subset_sum ✅
       → olumlu sertifika: sat tanığı BAĞIMSIZ doğrulanır (meta.verified) ✅
       ↳ dürüst asimetri: unsat DRAT/LRAT = duvar (DIMACS hattı gerekir), belgelendi

[x] Aşama 11 · [S] Büyük sağlamlaştırma (sürüm hazırlığı)  (bitti — 417 test, v0.2.0)
    └─ CANLI MCP entegrasyon testi (subprocess+stdio+JSON-RPC) + tüm araçların
       sözleşme denetimi (59) + sürüm dondurma 0.1.0→0.2.0 (RC) ✅
```

**🎉 Aşama 1–11 TAMAM.** Motor: 24→59 MCP aracı, 146→417 test, kapsam %87.
Ürünleştirme (B) kullanıcıda.

## B. Ürünleştirme (akşam sende — ayrı track)

```
[ ] PyPI yayını  ·  GitHub release  ·  örnek/tutorial defterleri
    (motordan bağımsız; kullanıcı yapar — ajan motora yüklenir)
```

## C. Öne geçiren yön — DOĞRULAMA KATMANI (AI muhakeme denetçisi)

> **Tez:** Ham hesapta değil, **güven**de öne geçeriz. AI non-deterministik ve
> uydurur; MathHead deterministik denetler ve bağımsız doğrulanabilir kanıt verir.
> Ürünü "başka bir CAS"tan **"AI muhakemesinin yargıcı"**na çevirir.

```
[x] C1 · Çekirdek doğrulayıcı (öner-ve-denetle)  (bitti — 438 test, 62 araç)
    └─ verify_equality (denklik + DOMAIN tuzağı), verify_solution (doğruluk +
       TAMLIK), verify_steps (adım zincirinde ilk hatayı bul) ✅
       ↳ dürüst duvar: domain ayrışması + tamlık 'unknown' açıkça raporlanır ✅
[x] C2 · Bağımsız sertifika — Z3/SymPy'siz stdlib checker (mathhead/certificate.py)  ✅
    ↳ bağımsızlık alt-süreçle KANITLI; tam aritmetik (Fraction); verified/refuted
[x] C3 · Çapraz denetim — Z3 ⋈ SymPy mutabakatı (iki bağımsız tanık)  (bitti — 447 test, 63 araç)
    ↳ domain tuzağı → ENGINES_DISAGREE; + determinizm düzeltmesi (ADR-0020)
[x] C4 · Benchmark — LLM-tuzak seti (14) + %100 yakalama + regresyon çiti  ✅
    ↳ benchmarks/ + docs/benchmark-results.md; dürüst: gösterim, canlı A/B değil
```

**🎉 TRACK C TAMAM.** Doğrulama katmanı: doğrulayıcı + bağımsız sertifika +
çapraz denetim + benchmark. MathHead = AI muhakemesinin bağımsız yargıcı.

---

# ÖNERİLEN — TÜM MOTOR GELİŞTİRMELERİ (D–K, onay bekliyor)

> Kullanıcı onayıyla aktifleşir; sırasını kullanıcı belirler. Ürünleştirme (PyPI/
> release) hariç — o kullanıcıda. Zorluk: 🟢 hızlı (SymPy/Z3 hazır) · 🟡 orta ·
> 🔴 zor/frontier. **[S]** = arada sağlamlaştırma.

## D. Analiz & Dönüşümler
```
[ ] D1 🟢 Vektör kalkülüs — divergence/curl/Laplacian, çizgi & yüzey integrali,
          Green/Stokes/Gauss teoremleri
[ ] D2 🟢 İntegral dönüşümleri — Laplace & ters, Fourier & ters, Z-dönüşümü
[ ] D3 🟡 Diferansiyel denklemler II — ODE sistemleri, yüksek mertebe, sınır değer;
          temel PDE (ısı/dalga, ayrık değişkenler)   ↳ 🔴 PDE genel çözüm sınırlı
[ ] D4 🟡 Karmaşık analiz — rezidü, kontur integrali, Laurent serisi, karmaşık değerlendirme
[ ] D5 [S] Sağlamlaştırma — analiz özdeşlik property'leri (∇×∇f=0, ∇·(∇×F)=0) + sayısal kontrol
```

## E. Cebir & Ayrık Yapılar
```
[ ] E1 🟡 Soyut cebir — permütasyon grupları (mertebe/altgrup/üreteç/Cayley), halka/cisim temel
[ ] E2 🟢 Lineer cebir III — SVD, QR, Cholesky, Gram-Schmidt, en küçük kareler,
          pseudo-inverse, matris üsteli (exp), Jordan formu, karakteristik/minimal polinom
[ ] E3 🟡 Graf teorisi — en kısa yol, bağlantılılık, eşleme (matching), max-flow/min-cut,
          MST, izomorfizm
[ ] E4 🟡 Sayı teorisi II — sürekli kesirler, karesel kalıntı, ilkel kök, Pell, Euler φ / Möbius
[ ] E5 🟡 Kombinatorik II — üreteç fonksiyonları, içerme-dışlama, Catalan/Bell/Stirling, Polya
[ ] E6 [S] Sağlamlaştırma
```

## F. Olasılık, İstatistik & Optimizasyon
```
[ ] F1 🟡 Olasılık II — koşullu & Bayes, ortak/marjinal dağılım, kovaryans, Markov zinciri
[ ] F2 🟡 Çıkarımsal istatistik — hipotez testi (z/t/χ²/ANOVA), güven aralığı, p-değeri, regresyon
[ ] F3 🟡 Optimizasyon II — doğrusal programlama (simpleks), tamsayı programlama,
          Lagrange çarpanları, KKT/konveks
[ ] F4 [S] Sağlamlaştırma
```

## G. Sayısal Yöntemler
```
[ ] G1 🟢 Kök & sayısal analiz — Newton/bisection/secant, quadrature (Simpson/Gauss), interpolasyon
[ ] G2 🟡 Sayısal lineer cebir & ODE — sayısal eigenvalue/çözüm, koşul sayısı, Runge-Kutta (RK4)
[ ] G3 🟡 Kesinlik köprüsü — arbitrary precision (mpmath), sembolik↔sayısal çapraz doğrulama, hata sınırı
[ ] G4 [S] Sağlamlaştırma
```

## H. Mantık & İspat Derinliği
```
[ ] H1 🔴 Tümevarım ispatları — matematiksel tümevarım (temel+adım; Z3 native yapamaz, özel işleme)
[ ] H2 🟡 SMT teorileri — diziler (arrays), bit-vektörler, dizeler (strings), yorumsuz fonksiyonlar
[ ] H3 🟡 İspat üretimi II — daha çok teori için adım adım türetim; quantifier elimination
[ ] H4 🔴 Modal/temporal mantık — K/S4/LTL temel (opsiyonel/frontier, dikkatli kapsam)
[ ] H5 [S] Sağlamlaştırma
```

## I. Doğrulama Katmanı II (Track C devamı — ÖNE GEÇİREN)
```
[ ] I1 🟢 Yeni iddia türleri — verify_limit / verify_derivative / verify_integral /
          verify_series / verify_matrix_identity
[ ] I2 🔴 Doğal dil → formal (NL→formal) + GERİ-çeviri doğrulaması (round-trip; "2. duvar"a doğrudan)
[ ] I3 🟡 Tam türetim ispat denetimi — çok adımlı çözümde her adımın gerekçesini denetle (kural bazlı)
[ ] I4 🟡 Sertifika genişletme (C2 devamı) — matris / sayı teorisi / olasılık sertifikaları (stdlib)
[ ] I5 [S] Sağlamlaştırma
```

## J. Frontier — Track B genişletme
```
[ ] J1 🟡 Yeni indirgemeler — Ramsey (küçük), Latin kareler, Sudoku, N-vezir, Hamilton, TSP (karar)
[ ] J2 🔴 Doğrulanabilir UNSAT sertifikası (DRAT/LRAT) — Aşama 10 duvarı; DIMACS + drat-trim
[ ] J3 🟡 Yüksek-performans çözücü — CaDiCaL/Kissat entegrasyonu (ölçek), paralel çözme
[ ] J4 [S] Sağlamlaştırma
```

## K. Bütünsel Performans & Sağlamlaştırma (enine kesen, sonda)
```
[ ] K1 🟡 Performans — önbellek (memoization), artımlı çözme (Z3 push/pop), paralel, timeout profili
[ ] K2 🟢 Kapsam & fuzzing — tüm ayrıştırıcı fuzz'ı, gramer formal spec, coverage %95
[ ] K3 🟡 Gözlemlenebilirlik — yapılandırılmış metrik/log, kaynak limitleri, perf regresyon çiti
[ ] K4 🟢 Sürüm 1.0 dondurma — tam sözleşme denetimi, API stabilitesi, sürüm notları
```

**Ölçek (dürüst):** ~37 aşama. Çok oturumluk iş; parça parça onaylanabilir.
**Önerilen sıra (değer-öncelikli):** I (öne geçiren) → D → E → F → G → H → J → K;
ama sıra tamamen sende. Onay/başka sıra/kapsam daraltma — hepsi olur.

---

## Nerede kaldık?

En güncel durum daima `Progress.md`'nin en üstünde. Yeni oturum önce onu ve bu
dosyayı okur, sonra hedef aşamaya kadar sürer.
