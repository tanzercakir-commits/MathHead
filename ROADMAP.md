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

[ ] Aşama 5 · [S] Sağlamlaştırma-2
    └─ hata taksonomisi birleştirme (reason_code tutarlılığı) +
       golden senaryolar (`tests/fixtures/*.json`) + benchmark iskeleti

[ ] Aşama 6 · Çok değişkenli analiz (multivariable)
    └─ gradyan, Jacobian, Hessian, belirli integral, seri toplam/çarpım,
       temel ODE (diferansiyel denklem) çözümü
       ↳ dürüst duvar: her ODE kapalı-form çözülemez → değerlendirilmemiş döner

[ ] Aşama 7 · Olasılık & istatistik
    └─ dağılımlar (sembolik), beklenen değer/varyans, temel çıkarım

[ ] Aşama 8 · [S] Sağlamlaştırma-3
    └─ kapsam (coverage) raporu + benchmark regresyon çiti +
       dokümantasyon konsolidasyonu (üretilmiş API referansı)

[ ] Aşama 9 · Eşitsizlik ispatı & nonlineer
    └─ Z3 nonlinear real (NRA) + kareler toplamı (SOS) ile eşitsizlik kanıtı
       ↳ dürüst duvar: NRA yarı-karar verilebilir → unknown birinci sınıf

[ ] Aşama 10 · Track B genişletme + sertifika
    └─ yeni indirgeme(ler) + doğrulanabilir UNSAT sertifikası (DRAT/LRAT)
       → "dürüst ispat": sonucu bağımsız denetleyici doğrulayabilsin

[ ] Aşama 11 · [S] Büyük sağlamlaştırma (sürüm hazırlığı)
    └─ uçtan uca CANLI MCP entegrasyon testi + tüm araçların sözleşme
       denetimi + sürüm dondurma (release candidate / RC)
```

## B. Ürünleştirme (akşam sende — ayrı track)

```
[ ] PyPI yayını  ·  GitHub release  ·  örnek/tutorial defterleri
    (motordan bağımsız; kullanıcı yapar — ajan motora yüklenir)
```

---

## Nerede kaldık?

En güncel durum daima `Progress.md`'nin en üstünde. Yeni oturum önce onu ve bu
dosyayı okur, sonra hedef aşamaya kadar sürer.
