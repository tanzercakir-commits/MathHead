# İkili Ajan Protokolü (v4 çalışma disiplini)

> Kullanıcı talebi (2026-08-05): "1. ajan mentor, tester, evaluator — 2. ajan implementer.
> Böyle bir ortam hazırlarsan otokontrol mekanizması daha iyi işler."
> Bu dosya o ortamın SÖZLEŞMESİDİR. Tracker değildir (üç tracker: PLAN/TODO/PROGRESS).

## Roller

**Ajan-2 — IMPLEMENTER**
- Girdi: faz tanımı + DONE ölçütü (roadmap'ten, birebir) + varsa önceki tur bulguları.
- İş: kodu yazar, testleri yazar, KENDİ testlerini koşar, kısa değişiklik raporu döndürür
  (dosyalar, test sayısı, dürüstlük-kademe kararları).
- Yasak: DONE ölçütünü kendisi "geçti" ilan edemez; kademe (epistemic tier) YÜKSELTEMEZ —
  yalnızca gerekçeli önerir.

**Ajan-1 — MENTOR / TESTER / EVALUATOR**
- Girdi: implementer'ın raporu + diff + DONE ölçütü.
- İş: DÜŞMANCA değerlendirir — üç şapka sırayla:
  1. TESTER: kırmaya çalışır (uç girdiler, yalan iddialar besler, tanıkları bağımsız doğrular).
  2. EVALUATOR: DONE ölçütünün her maddesini KANITA karşı işaretler (test çıktısı, dosya, hash).
  3. MENTOR: kademe-abartısı arar (en yüksek-öncelik bug sınıfı, bkz. CONTRIBUTING) ve
     bir sonraki tur için somut iyileştirme önerir.
- Çıktı: `PASS` ya da `FAIL + numaralı bulgu listesi` (her bulgu: nasıl yeniden üretilir).

## Döngü (gate)

```
faz tanımı ──▶ Ajan-2 IMPLEMENTER ──rapor+diff──▶ Ajan-1 EVALUATOR
                      ▲                                │
                      └──── FAIL: numaralı bulgular ◀──┤
                                                       │ PASS
                                                       ▼
                    orkestratör: TAM suite + ruff + tracker check
                                → commit + push → TODO/PROGRESS güncelle
```

Kurallar:
- Evaluator PASS demeden commit YOK. Orkestratör evaluator'ı override edemez
  (tek istisna: evaluator'ın kendi bulgusu yanlış-pozitifse, gerekçe PROGRESS'e yazılır).
- En fazla 3 tur FAIL → faz "blocked" işaretlenir, neden roadmap'e dürüstçe işlenir; sessizce
  ölçüt gevşetilmez.
- İki ajan aynı oturum-bağlamını PAYLAŞMAZ (bağımsızlık = değerlendirmenin değeri);
  yalnızca rapor/bulgu metni taşınır.
- Dürüstlük sözleşmesi (docs/manual/honesty.md) her iki ajan için de bağlayıcıdır.
