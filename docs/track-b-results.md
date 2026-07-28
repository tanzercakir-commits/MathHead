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

## Schur sayıları S(r)  ·  *bu oturumda hesaplandı*

`{1..n}`, `r` renge, hiçbir renk sınıfında `x + y = z` olmadan (her sınıf
**sum-free**) bölünebilir mi? `S(r)` = bölünebilen en büyük `n`.

| Sayı | Bilinen değer | Motorun sonucu | Süre |
|---|---|---|---|
| S(2) | 4 | n=4 `sat`, **n=5 `unsat`** ✓ | ~5 ms |
| S(3) | 13 | n=13 `sat`, **n=14 `unsat`** ✓ | ~0.3 sn |
| S(4) | 44 | n=44 **`sat`** → S(4) ≥ 44 doğrulandı | ~25 sn |

S(2) ve S(3) **tam** yeniden üretildi (her iki yön = değerin kesin ispatı). S(4)
için alt sınır (S(4) ≥ 44) doğrulandı; üst sınır (n=45 `unsat`) bu ortamda ~1.5
dk'da tamamlanmadı → duvar. **S(5)=160** bilinen ama devasa (Heule 2017, ~2 PB
ispat). **S(6) hâlâ AÇIK.**

## Optimizasyon denemesi: simetri kırma (symmetry breaking)

Duvarı ileri itmek için renk-permütasyon simetrisini kıran kısıtlar denendi
(2-renk: 1. eleman sabit; r-renk: lex-leader). `sat`/`unsat` **değişmez**
(doğruluk korunur — teste kilitli). Ama etkisi **karışık** çıktı:

| Vaka | Simetrisiz | Simetrili | Sonuç |
|---|---|---|---|
| S(3) n=14 (unsat) | ~0.23 sn | ~0.0 sn | hızlandı |
| W(2,5) n=178 (unsat, 2-renk) | ~61 sn | ~65 sn | değişmedi (faktör 2) |
| S(4) n=44 (sat, 4-renk) | ~35 sn | ~48 sn | **yavaşladı** (ek yük) |

**Dürüst sonuç:** Naif renk-simetri kırma sihirli değnek değil — küçük/UNSAT
vakalarında yardımcı, ama SAT vakalarında eklediği kısıt yük getirip zarar
verebilir. Bu yüzden varsayılan **kapalı** (opsiyonel `symmetry_break` flag'i
olarak kaldı, doğruluğu testle güvence altında). Gerçek duvarı (S(4)=45, W(2,6))
aşmak araştırma düzeyi SAT teknikleri (streamlining, özel çözücüler, paralellik)
ister — bu, *yöntemin* değil *ölçeğin/mühendisliğin* işidir.

## Dürüst sınır (compute wall)

- Bu ortamda pratik sınır **~W(2,5)** (n≈178, ~1 dk).
- **W(2,6) = 1132**: *bilinen* ama devasa (özel SAT çözücüler / kümeler gerekti)
  — bu konteynerde erişilemez.
- **W(2,7)**: exact değeri **AÇIK** (bilinen alt sınır ≥ 3703). Motorun yöntemi
  doğru ama bu ölçek erişilemez → dürüstçe `unknown`.

## Sonuç

MathHead açık bir problemi **çözmedi** — çözülenler süper-hesap gerektirdi. Ama
araştırma düzeyi değerleri (W(2,3..5) ve Schur S(2..3), S(4)≥44) aynı yöntemle
**doğrulanabilir biçimde yeniden üretti** ve duvarın tam olarak nerede
başladığını şeffafça gösterdi.
Track B'nin tezi budur: *yöntem gerçek; ölçek arttıkça hesap sınırı devreye
girer.* Ölçeği büyütmek (daha güçlü çözücü, paralellik, küme) mühendislik işidir
— yöntem değişmez.

## Aşama 10 — yeni indirgemeler + doğrulanabilir sertifika

**Yeni indirgemeler (NP-tam):**

- `graph_coloring(edges, colors)` — graf k-boyama. K3 → 3 renk sat, 2 renk unsat
  (tek döngü); K4 → 3 renk unsat (kromatik sayı 4). Bağımsız doğrulandı.
- `subset_sum(numbers, target)` — alt küme toplamı. `[3,34,4,12,5,2]→9` sat
  (`{3,4,2}`); `→100` unsat.

**Doğrulanabilir sertifika (dürüst durum):**

- **Olumlu (`sat`):** tanık bir sertifikadır ve Z3'ten BAĞIMSIZ, saf Python'da
  yeniden denetlenir → `meta.verified=true`. Bu, olumlu kanıtı çözücüden bağımsız
  ve polinom-zamanda doğrulanabilir kılar (kodlama/çeviri hatasını yakalar).
- **Olumsuz (`unsat`) — DUVAR:** bağımsız-denetlenebilir bir **DRAT/LRAT**
  sertifikası, DIMACS düzeyinde bir CDCL SAT çözücü + `drat-trim` tarzı denetleyici
  hattı gerektirir. Z3'ün iç ispat nesnesi kendi biçimindedir (DRAT değil). Bunu
  kurmak bu turun kapsamı dışında; **dürüstçe** `unsat` sonucunu veriyor ve notta
  DRAT sertifikasının henüz üretilmediğini belirtiyoruz. Gelecek iş.
