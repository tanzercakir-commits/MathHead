# MathHead — Gelişim Notları (development notes)

Bu dosya iş günlüğü (→ `Progress.md`), yapılacaklar (→ `Todo.md`) ya da karar
kaydı (→ `DECISIONS.md`) değildir. Burası projenin **yönünü** besleyen fikir /
gözlem defteri — acelesi olmayan, olgunlaşacak notlar.

---

## 2026-07-28 — "Kodlama değil, matematik/fizik öğrenin" ne demek? (yön notu)

Teknoloji liderlerinin (ör. Jensen Huang) kastettiği "matematik" mekanik **hesap**
değil (onu AI zaten yapıyor). Üç katman:

1. **AI'ı çalıştıran matematik:** lineer cebir (tensör/matris), olasılık &
   istatistik (belirsizlik/çıkarım), çok değişkenli kalkülüs & optimizasyon
   (gradyan/eğitim), bilgi kuramı (entropi).
2. **Titiz düşünmenin matematiği — kalıcı insan üstünlüğü:** matematiksel mantık &
   ispat, ayrık matematik / kombinatorik / graf, soyutlama & cebirsel yapı.
3. **En derin okuma, bir düşünme biçimi:** gerçekliği ilk ilkelerden modelleme
   (fizik), dağınık bir problemi **kesin bir matematiksel ifadeye** çevirme, ve
   "hesaplıyor" değil "**neden doğru**" (ispat / doğrulama) rigoru.

**MathHead için anlamı (kritik):** MathHead tam da 2. ve 3. katmanda yaşıyor —
*hesap* değil, **doğrulanabilir akıl yürütme + modelleme**. AI kodu yazınca
darboğaz yukarı kayıyor: "nasıl yazarım"dan → "problem tam olarak ne, çıkarımım
doğru mu, cevabı nasıl doğrularım"a. MathHead'in tezi (AI'a deterministik,
sağlam, **ispat-üreten** bir motor vermek) bu kaymanın tam ortasında.

**Yön teyidi:** `prove` (adım adım ispat), FOL (yüklem/nicelik), `enumerate`,
Track B indirgemeleri (problem → kesin ifade) — *hesaptan çok mantık / ispat /
modelleme* eksenine yaslanmak doğru bahis. Yani şu ana kadarki yön bu tezle
uyumlu; ileride de ağırlığı buraya vermek mantıklı.

**Dürüst denge:** "kodlamayı hiç öğrenmeyin" bir abartı; asıl devalüe olan şey
*sözdizimi emeği* olarak kodlama. Sistemleri anlama + AI'ı yönetip **doğrulama**
hâlâ çok değerli — ki bu da yine rigor / matematik demek.
