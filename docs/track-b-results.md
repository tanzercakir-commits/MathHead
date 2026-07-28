# Track B — Sonuç Kaydı (honest results log)

Bu dosya, MathHead'in `frontier/` katmanının SAT-indirgemeyle **fiilen kurduğu /
ispatladığı** sonuçları kaydeder. Amaç dürüstlük: **yeniden üretilen bilinen
değerler** (doğrulama) ile **açık / erişilemez** olanları net ayırmak. Sahte
zafer yok.

> **Yöntem:** problemi 2-renk (veya r-renk) *sağlanabilirliğine* (satisfiability)
> indir, Z3 ile çöz. Bu, ilgili araştırma değerlerini hesaplayan yöntemin
> **aynısıdır** — tek fark ölçek.

## Güvercin yuvası (pigeonhole)

`n+1` güvercin, `n` kutu → **unsat** (teoremin ispatı), her `n` için. ✓
Klasik bir teoremi indirgemeyle kanıtlamanın örneği.

## Boolean Pythagorean üçlüleri

`{1..n}` 2-boyama, tek renkli Pythagoras üçlüsü (a²+b²=c²) olmadan.

- Küçük `n`: `sat` (boyama bulunur ve **bağımsız doğrulanır**). ✓
- Bilinen açık-problem sonucu: `n=7825`'te imkânsız (Heule ve ark., 2016,
  ~200 TB ispat) — bu ölçek bu ortamın **çok** ötesinde.

## van der Waerden sayıları W(2, k)  ·  *bu oturumda hesaplandı*

`{1..n}`'i 2 renge, tek renkli `k`-terimli aritmetik dizi olmadan boyayabilir
miyiz? `W(2,k)` = boyamanın imkânsızlaştığı en küçük `n`.

| Sayı | Bilinen değer | Motorun sonucu | Süre |
|---|---|---|---|
| W(2,3) | 9 | n=8 `sat`, **n=9 `unsat`** ✓ | ~6 ms |
| W(2,4) | 35 | n=34 `sat`, **n=35 `unsat`** ✓ | ~40 ms |
| W(2,5) | 178 | n=177 `sat`, **n=178 `unsat`** ✓ | ~61 sn |

Her `unsat` **gerçek bir imkânsızlık ispatıdır**: `{1..W}` kümesi 2 renge, tek
renkli `k`-terimli aritmetik dizi olmadan boyanamaz. Bu değerler literatürdeki
araştırma sonuçlarıyla birebir uyuşur — yani motor onları **aynı yöntemle
yeniden üretti** (W(2,5)=178 ilk kez 1978'de belirlenmiştir).

## Dürüst sınır (compute wall)

- Bu ortamda pratik sınır **~W(2,5)** (n≈178, ~1 dk).
- **W(2,6) = 1132**: *bilinen* ama devasa (özel SAT çözücüler / kümeler gerekti)
  — bu konteynerde erişilemez.
- **W(2,7)**: exact değeri **AÇIK** (bilinen alt sınır ≥ 3703). Motorun yöntemi
  doğru ama bu ölçek erişilemez → dürüstçe `unknown`.

## Sonuç

MathHead açık bir problemi **çözmedi** — çözülenler süper-hesap gerektirdi. Ama
araştırma düzeyi değerleri (W(2,3..5)) aynı yöntemle **doğrulanabilir biçimde
yeniden üretti** ve duvarın tam olarak nerede başladığını şeffafça gösterdi.
Track B'nin tezi budur: *yöntem gerçek; ölçek arttıkça hesap sınırı devreye
girer.* Ölçeği büyütmek (daha güçlü çözücü, paralellik, küme) mühendislik işidir
— yöntem değişmez.
