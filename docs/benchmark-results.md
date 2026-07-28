# MathHead — LLM-Tuzak Benchmark Sonuçları

> **Ne ölçer:** MathHead'in, LLM'lerin sık DÜŞTÜĞÜ klasik matematik hata
> desenlerini doğru **adjuke etme** (yakalama) oranını. Kaynak veri:
> `benchmarks/llm_traps.json`; harness: `benchmarks/run.py`; regresyon çiti:
> `tests/test_benchmark_traps.py`.
>
> **DÜRÜST çerçeve (önemli):** Bu bir **yeniden-üretilebilir gösterimdir** — MathHead
> her tuzağa doğru düzeltici verdict'i veriyor mu? Bu bir **canlı LLM A/B testi
> DEĞİLDİR.** Gerçek bir modelin bu tuzaklara ham hâlde ne kadar düştüğünü ölçmek
> (raw-LLM vs MathHead-destekli doğruluk) kullanıcının gerçek modelle koşacağı iştir.
> Buradaki iddia mütevazı ve dürüst: *MathHead bu hata sınıflarını güvenilir yakalar.*

## Sonuç

**Yakalama oranı: 14/14 = %100** (tüm kategoriler).

Kritik: "doğru_pozitif" kontrolü de geçer — MathHead DOĞRU bir özdeşliği
(`sin²+cos² = 1`) yanlışlıkla işaretlemez. Yani yalnız hatayı yakalamıyor,
doğruyu da bozmuyoruz (yanlış-pozitif yok).

## Tuzak kategorileri (LLM'in düştüğü → MathHead'in yakaladığı)

| Kategori | LLM hatası | MathHead verdict | Araç |
|---|---|---|---|
| eksik_çözüm | `x²=4 → {2}` (−2 kaçar) | `SOLUTION_INCOMPLETE` | `verify_solution` |
| yanlış_çözüm | `x²=4 → {2,3}` | `SOLUTION_INCORRECT` | `verify_solution` |
| yanlış_özdeşlik | `(x+1)² = x²+1` | `CONSENSUS_NOT_EQUAL` | `cross_check` |
| domain_tuzağı | `(x²−1)/(x−1) = x+1` | `EQUAL_ON_COMMON_DOMAIN` / `ENGINES_DISAGREE` | `verify_equality` / `cross_check` |
| yanlış_eşitsizlik | `x² ≥ x` (∀x) | `invalid` + karşıörnek `x=0.5` | `prove_inequality` |
| kök_dalı | `√(x²) = x` | `NOT_EQUAL` (`x=−1`) | `verify_equality` |
| hatalı_adım | `2(x+3) = 2x+3` | `STEP_INVALID` | `verify_steps` |
| asallık | `91 asaldır` | `result: false` | `is_prime` |
| aritmetik | `2¹⁰ = 1000` | `NOT_EQUAL` (1024) | `verify_equality` |
| modüler | `4⁻¹ mod 8` uydurma | `COMPUTE_FAILED` | `modular_inverse` |
| tam_sayı_çözüm | `2x+4y=5` tam sayı | `[]` (çözüm yok) | `linear_diophantine` |

## Yeniden üretme

```bash
python benchmarks/run.py            # tabloyu ve oranı yazdırır
pytest tests/test_benchmark_traps.py -q   # regresyon çiti (her tuzak yakalanmalı)
```

Yeni tuzak eklemek: `benchmarks/llm_traps.json`'a bir giriş ekle (task + payload +
beklenen düzeltici verdict). Çit otomatik kapsar.
