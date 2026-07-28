# MathHead — Plan

> **Bu dosyanın işi:** Projenin *hedef mimarisini* ve *yol haritasını* korumak.
> Değişmeye dirençlidir; sık güncellenmez. Anlık işler `Todo.md`'de, ne yaptığımız
> `Progress.md`'de, kararların gerekçesi `DECISIONS.md`'dedir.
> (Plan ≠ Todo ayrımı senin çalışma prensiplerinden geliyor.)

---

## 0. Tek cümlede

AI'ın matematiksel **akıl yürütme ve ispatını**, kendi kafasından
(non-deterministik, varsayıma açık) yapmak yerine, **MCP** üzerinden
**deterministik** bir motora (SMT çözücü **Z3** + sembolik hesap **SymPy**)
devrettiği bir sistem.

---

## 1. Neden var? (çözdüğü gerçek problem)

LLM'ler dil işinde güçlü ama katı mantık/ispatta güvenilmez: geçersiz çıkarım
adımı atar, sayı/cebir hatası yapar, "emin" görünüp yanılır. Senin AI ile
çarptığın 3 duvar bunun kök nedeni. MathHead matematiği **gerçek bir motora
offload** ederek bu üç duvara birden mimari cevap verir:

| Duvar | MathHead'in cevabı |
|---|---|
| **#1 Bağlam kaybı** | `Plan/Todo/Progress/DECISIONS` disiplini + her yanıtta izlenebilir `meta` (hangi çözücü, hangi sürüm, ne kadar sürdü). Kararlar `DECISIONS.md`'de kaybolmaz. |
| **#2 Fazla varsayım** | Motor yalnızca **açık gramerin** izin verdiği girdiyi kabul eder; belirsizi *reddeder*, tahmin etmez. "Sessiz varsayım yok" kuralı. |
| **#3 Non-determinizm** | Çekirdek deterministik (sabit tohum + zaman aşımı + tek iş parçacığı). **Aynı girdi → aynı çıktı.** AI'ın oynak kısmı motorun dışında kalır. |

---

## 2. Hedef — iki hat (Track A + Track B)

Senin isteğin net: motor hem güvenilir olsun **hem de** "şu an çözülemeyen ya da
çözülmesine en çok ihtiyaç duyulan" zor problemlere gerçekten saldırsın. Bunu tek
hedefe sıkıştırmıyoruz; **iki paralel hat** olarak kuruyoruz:

**Track A — Sağlam temel (yakın vade, v1–v2).**
AI'ın matematiğini *deterministik ve doğrulanabilir* kılmak. LLM'lerin bugün
yapamadığı şey tam olarak bu; bu hat güvenin kaynağı.

**Track B — Kuzey Yıldızı: gerçekten zor/açık problemlere saldırı (v3+).**
Ve burada dürüst olmak "yapamayız" demek *değil* — tam tersi. SMT/SAT
çözücülerinin **onlarca yıllık açık problemleri fiilen çözdüğü** bir sicil var:

- **Boolean Pythagorean Triples** (2016) — uzun süre açık kalan soru, SAT
  çözücüyle çözüldü (Heule ve ark.); ~200 TB'lık makine-üretimi ispat.
- **Keller sanısı, 7. boyut** (2020, CMU) — ~90 yıllık geometri problemi, SAT ile
  kapatıldı.
- **Schur sayısı 5** (2017) — yine SAT çözücüyle belirlendi (~2 PB ispat).
- **Collatz sanısı** gibi dev problemlere bile SAT / yeniden-yazma ile *aktif
  saldırı* denemeleri sürüyor.

MathHead'in Z3 çekirdeği tam da bu soydan geliyor. Track B'nin hedef sınıfı:
**büyük sonlu/kombinatoryal "sağlanabilirlik" (satisfiability) problemine
indirgenebilen** açık sorular — artı, insan/AI ispatlarını *formal doğrulama*
(Lean / AlphaProof tarzı frontier). Kritik nokta: bir çözücünün "çözdüm" demesi,
ancak **bağımsız doğrulanabilir bir sertifika/ispat** üretirse değerlidir; bu
yüzden Track B, Track A'nın (doğrulanabilir çekirdek) *üstüne* kurulur —
**önce güven, sonra fetih.**

---

## 3. Kapsam sözleşmesi: Vizyon geniş, v1 dar

Senin iki tercihin ("ileriye dönük/iddialı" **ve** "v1 dar & sağlam") çelişmiyor;
tam da senin `Plan ≠ Todo` prensibinle çözülüyor:

```
Plan.md  ─▶ BÜYÜK vizyon (frontier): AI için doğrulanabilir ispat motoru
Todo.md  ─▶ KÜÇÜK dilim (v1): tek, uçtan uca çalışan "Akıl Yürütme Denetçisi"
```

v1'i kasıtlı olarak **dikey bir dilim** (vertical slice) tutuyoruz: dar konu,
ama MCP'den çekirdeğe kadar *uçtan uca çalışan ve iyi test edilmiş*. Sağlam zemin
kurulunca genişlemek ucuz; zemin çürükken genişlemek pahalı.

---

## 4. Mimari — katmanlı hibrit

Tek bir "FOL motoru" yazmıyoruz. Her katmanın tek bir sorumluluğu var; dış dünya
motora **yalnızca** MCP katmanından dokunur.

```
                ┌──────────────────────────────────────────────┐
   AI / Claude ─┤  server/   MCP arayüzü (tek sözleşme/protokol) │
                └───────────────┬──────────────────────────────┘
                                │  net API (docs/mcp-api.md)
                ┌───────────────▼──────────────┐
                │  guardrails/  ÇİT             │  ← girdi doğrulama, zaman aşımı,
                │  (her istek buradan geçer)    │     determinizm ayarı
                └───────────────┬──────────────┘
                ┌───────────────▼──────────────┐
                │  router/   yönlendirme        │  ← hangi çözücü + hangi ilkel?
                └──────┬────────────────┬───────┘
          ┌────────────▼───┐     ┌──────▼─────────────┐
          │ core/  (Z3)    │     │ compute/ (SymPy)   │
          │ MANTIK [v1]    │     │ HESAP    [v2+]     │
          │ entailment,    │     │ solve, simplify,   │
          │ consistency,   │     │ türev/integral     │
          │ find_model     │     │                    │
          └────────────────┘     └────────────────────┘
```

Katman sorumlulukları detayı: `docs/architecture.md`. Neden Z3 + SymPy seçildi:
`DECISIONS.md` ADR-0001/0002.

---

## 5. v1 dilimi — "Akıl Yürütme Denetçisi" (Reasoning Checker)

AI bir çıkarım/iddia üretir; MathHead onu **deterministik** denetler. Üç ilkel:

1. **`entailment(premises, conclusion)`** — Öncüller sonucu mantıksal gerektirir mi?
   Yöntem: `(⋀ premises) ∧ ¬conclusion` **UNSAT** ise geçerli; **SAT** ise
   *karşıörnek* döner.
2. **`consistency(statements)`** — Bu ifadeler aynı anda doğru olabilir mi?
   `SAT` → model, `UNSAT` → çelişen alt küme (unsat core).
3. **`model(statements)`** — İfadeleri sağlayan somut bir örnek atama.

**v1 girdi parçası (fragment):** önermeler mantığı (and/or/not/implies/iff) +
doğrusal aritmetik (Int/Real üzerinde `+ - * < <= = >= >`). Nicelik belirteçleri
(∀/∃) v1.1 hedefi. Gramerin tamamı: `docs/mcp-api.md`.

**Ortak çıktı sözleşmesi:** her ilkel `ReasoningResult` döner —
`status ∈ {valid, invalid, sat, unsat, unknown, error}`, `witness` (model/
karşıörnek), `explanation`, `reason_code`, `meta`. `unknown` ve `error` **birinci
sınıf**tır; motor asla sonucu uydurmaz.

---

## 6. Yol haritası

```
v0  İSKELET (bu oturum) ....... yapı, sözleşmeler, tasarım dosyaları, stub'lar
v1  Akıl Yürütme Denetçisi .... 3 ilkel çalışır; önerme + doğrusal aritmetik;
                                 uçtan uca MCP; best/worst testler yeşil
v1.1 Nicelik belirteçleri ..... ∀/∃ ve daha zengin FOL parçası
v2  Hesap katmanı (SymPy) ..... solve/simplify/türev/integral; router genişler
v3  Track B başlar ........... ispat üretimi/doğrulama; açık problemi
                                 satisfiability'e indirgeyip çözücüyle çözme
                                 [TOHUM EKLENDİ: frontier/ — Pythagorean + PHP]
v4+ "Motor ailesi" ............ aynı iskelet üzerine Fizik/Kimya motorları
```

Not: Fizik/Kimya motorları senin uzun vadeli fikrin. İskeleti (guardrails +
router + MCP sözleşmesi) *motor-bağımsız* tasarlıyoruz ki v4'te tekrar
yazılmasın. Ama v1 kapsamına **dahil değil**.

---

## 7. Guardrail'ler (senin 4 koruyucu maddenin karşılığı)

1. **Otomatik testler (best/worst case)** → `tests/` : bilinen-doğru senaryolar
   spec olarak kodlandı; `unknown`/timeout dürüstlüğü de test ediliyor.
2. **Mimari güvenlik (çit)** → `guardrails/` : girdi boy/derinlik sınırı,
   bilinmeyen sembol reddi, çözücü zaman aşımı, deterministik yapılandırma.
3. **Açık proje prensipleri** → `PRINCIPLES.md`.
4. **Net protokol / API** → `docs/mcp-api.md` (+ `server/mcp_server.py` birebir
   aynı imzalar). API **erken donduruldu**; çekirdek değişse de dış sözleşme sabit.

---

## 8. Başarı ölçütü — "v1 bitti" tanımı

- [ ] Üç ilkel gerçek Z3 ile çalışıyor.
- [ ] `tests/test_logic.py` içindeki best/worst senaryolar **yeşil** (xfail kalkar).
- [ ] Malformed girdi net reddediliyor (sessiz varsayım yok).
- [ ] Aynı girdi 100 kez → 100 kez aynı çıktı (determinizm kanıtı).
- [ ] Bir MCP istemcisinden (ör. Claude) uçtan uca en az 3 gerçek soru çözülüyor.
- [ ] Her karar `DECISIONS.md`'ye, her adım `Progress.md`'ye işlendi.

---

## 9. Riskler & dürüst sınırlar

- **Undecidability:** Genel FOL yarı-karar verilebilir (semi-decidable); zengin
  parçalarda motor `unknown` dönebilir. Bunu *gizlemiyoruz*, raporluyoruz.
- **Girdi dili gerginliği:** Gramer ne kadar dar → o kadar güvenli ama az yetenek;
  ne kadar geniş → o kadar güçlü ama riskli. v1 bilinçli olarak dar başlar.
- **"Matematik fizik/kimyadan kolay mı?"** Dürüst cevap: *kapsama bağlı.*
  Doğrulama/mantık (v1) tractable; açık teorem ispatı (v3+) zor cephedir. Kolaylık
  varsayımına yaslanmıyoruz, dar dilimle riski düşürüyoruz.
- **Determinizm sınırı:** Z3 çoğu sorguda kararlı; yine de sürüm/zaman aşımı
  kaynaklı sapmaları `meta` ile şeffaf kaydediyoruz.
- **Track B'nin sınırı (dürüst):** Ünlü sanıları (Riemann vb.) *sihirle* çözmeyi
  vaat etmiyoruz. Gerçekçi cephe: sonlu/kombinatoryal satisfiability'e
  indirgenebilen problemler + ispat doğrulama/formalleştirme. Track B, Track A
  olgunlaşmadan başlamaz ve her "çözüm" bağımsız doğrulanabilir sertifika ister.
