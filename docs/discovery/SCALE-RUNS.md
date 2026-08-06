# Ölçek Koşuları — Sonuç Kayıtları (v4F5)

> Bu dosya bir TRACKER DEĞİLDİR (üç tracker: PLAN/TODO/PROGRESS) — DECISIONS.md gibi bir KAYIT
> dosyasıdır: her ölçek koşusu tarih + komut/parametre + süre + sonuç + DÜRÜST KADEME ile buraya
> işlenir. İki demir kural: (1) zaman aşımı ASLA sonuç gibi yazılmaz — `undecided_within_budget`
> olarak, süresiyle birlikte kaydedilir; (2) uzun koşular test DEĞİLDİR — hızlı test paketi yalnız
> MEKANİZMAYI pinler (deterministik küçük-n davranışı), sonuçlar yalnız burada yaşar.

---

## Koşu 1 — geng n=8 bağlı-graf invariant süpürmesi → konjektür servisi

- **Tarih:** 2026-08-05 · **Ortam:** nauty geng (`nauty-geng`), Python 3, tek çekirdek
- **Komut/parametreler:** `scale_sweep(n_small=6, n_max=8)` ve `run_service(n_max=8)`
  (`mathhead.discovery.conjecture_service`; geng `-c`, 11 invariant: α, γ, ν, girth, diam, radius,
  |E|, Δ, δ, χ, ω; formlar A≤B, A≤B+1, A≤2B — 330 aday)
- **Süre:** `scale_sweep(6,8)` **15.8 s** · `run_service(8)` **15.9 s** (11 970 yeni graf: n=7'de
  853 + n=8'de 11 117 — geng sayımıyla birebir; toplam örnek 12 112 bağlı graf, 2 ≤ n ≤ 8)
- **Sonuç:** v2C0'ın n≤6 üzerindeki **74 survivor'ından 60'ı n=8'de hayatta, 14'ü refüte** (her
  biri tanık graflı, deterministik ilk-tanık). Tam n≤8 feed'i: 330 aday → **62 survivor**
  (60 hayatta-kalan + 2 "dirilen" ofset formu: `domination_number <= diameter + 1` ve
  `domination_number <= max_degree + 1` — n≤6'da sıkı formları yaşadığı için bastırılmışlardı
  [dominated-duplicate kuralı], sıkı formlar n≤8'de ölünce ofsetler yüzeye çıktı; 60+2=62
  tutarlılığı ve alive ⊆ survivors(8) / refuted ∩ survivors(8) = ∅ değişmezleri koşuda doğrulandı).
- **KADEME:** survivors = `empirical` (yalnız n ≤ 8 bağlı örneklem üzerinde; teorem DEĞİL, v2C0
  caveat'i aynen geçerli: çoğu bilinen sonuçtur, feed insanların saldırması için bir listedir).
  Refütasyonlar = kesin tamsayı tanıklı (tanık graf + iki değer kayıtta; iki örnek bağımsız
  yeniden hesaplandı).
- **Refütasyon tanıkları — 14'ün TAMAMI, makine-okunur** (deterministik yeniden-koşuyla üretildi,
  2026-08-06; her graph6 dizgisi motorun kendi `decode_graph6`'sıyla round-trip doğrulandı; alanlar:
  `statement | n | lhs_value | rhs_value | graph6 | kenar listesi`; graph6 alfabesi ters-tırnak
  içerebildiği için blok çitli metindir, tablo değil):

  ```text
  domination_number <= diameter          | 8 | 4 | 3 | G?bDKk | 0-4 0-5 0-6 0-7 1-5 2-6 3-7 5-6 5-7 6-7
  matching_number <= clique_number + 1   | 8 | 4 | 2 | G?`@F_ | 0-4 0-7 1-5 1-7 2-6 2-7 3-7
  domination_number <= max_degree        | 7 | 3 | 2 | FCQb?  | 0-3 0-5 1-4 1-6 2-5 2-6
  matching_number <= chromatic_number + 1| 8 | 4 | 2 | G?`@F_ | 0-4 0-7 1-5 1-7 2-6 2-7 3-7
  independence_number <= max_degree + 1  | 7 | 5 | 3 | F?Bco  | 0-5 0-6 1-5 2-5 3-6 4-6
  domination_number <= radius + 1        | 8 | 4 | 2 | G?`@F_ | 0-4 0-7 1-5 1-7 2-6 2-7 3-7
  matching_number <= max_degree + 1      | 8 | 4 | 2 | G?`ad? | 0-4 0-7 1-5 1-6 2-5 2-7 3-6
  min_degree <= chromatic_number + 1     | 8 | 4 | 2 | G?~vf_ | 0-4 0-5 0-6 0-7 1-4 1-5 1-6 1-7 2-4 2-5 2-6 2-7 3-4 3-5 3-6 3-7
  min_degree <= clique_number + 1        | 8 | 4 | 2 | G?~vf_ | 0-4 0-5 0-6 0-7 1-4 1-5 1-6 1-7 2-4 2-5 2-6 2-7 3-4 3-5 3-6 3-7
  radius <= chromatic_number + 1         | 8 | 4 | 2 | G?`ad? | 0-4 0-7 1-5 1-6 2-5 2-7 3-6
  radius <= clique_number + 1            | 8 | 4 | 2 | G?`ad? | 0-4 0-7 1-5 1-6 2-5 2-7 3-6
  radius <= max_degree + 1               | 8 | 4 | 2 | G?`ad? | 0-4 0-7 1-5 1-6 2-5 2-7 3-6
  domination_number <= chromatic_number + 1 | 8 | 4 | 2 | G?`@F_ | 0-4 0-7 1-5 1-7 2-6 2-7 3-7
  domination_number <= clique_number + 1 | 8 | 4 | 2 | G?`@F_ | 0-4 0-7 1-5 1-7 2-6 2-7 3-7
  ```

  Tanık çeşitliliği dürüstçe: 14 ölüm yalnız 6 farklı grafa dayanıyor — `` G?`@F_ `` (n=8 örümcek
  ağacı, 5 ölüm), `` G?`ad? `` (n=8 ağaç, 4 ölüm), `G?~vf_` (K₄,₄, 2 ölüm), `G?bDKk` (n=8, 1),
  `FCQb?` ve `F?Bco` (n=7 ağaçlar, 1'er). İki tanık (γ=4>diam=3 ve ν=4>ω+1) bağımsız yeniden
  hesapla ayrıca doğrulandı.
- **Not (örüntü, dürüst etiketle):** n≤8'de en keskin survivor'lar `clique_number <=
  chromatic_number` (11 576/12 112 eşitlik), `radius <= diameter`, `diameter <= 2*radius`,
  `domination_number <= independence_number`, `domination_number <= matching_number` —
  **hepsi `empirical`** ve **known-result caveat**: bunlar klasik teoremlerdir (ω ≤ χ; r ≤ d ≤ 2r;
  γ ≤ α; izole-köşesiz graflarda γ ≤ ν), n=8 taraması yenilik değil SAĞLAMLIK sinyalidir.
  Ölümlerin deseni de bilinen yönde: +1-ofsetli küçük-n artefaktları (14 ölümün 11'i A≤B+1
  formu) büyük yıldız/örümcek ağaçlarında kırıldı.
- **Test pinleri (hızlı, mekanizma):** n≤6 survivor sayısı 74'e pinli
  (`test_small_n_survivor_count_is_pinned`); sweep determinizmi + yalnız-düşürür sözleşmesi +
  tanıkların yeniden hesaplanması + survivor-filtre tutarlılığı küçük n'de
  (`test_scale_sweep_*`, `tests/test_discovery_conjecture_service.py`).

---

## Koşu 2 — R(3,6) = 18 denemesi (türetilmiş derece-lemmaları; öz-referanslı zincir)

- **Tarih:** 2026-08-05 · **Çözücü:** Glucose3 (pysat), `ramsey_decide` (v2C1 + v4F0 RUP yolu)
- **Kod değişikliği:** `_degree_lemmas` s=3, t=6'ya genişletildi — kırmızı-derece ≤ 5 (mevcut
  s=3 kuralı t−1'i veriyor) + **mavi-derece ≤ R(3,5)−1 = 13** (t=6 dalı). R(3,5)=14 motorun
  KENDİ bracket'idir (bu modül: 13'te bağımsız-doğrulanmış tanık, 14'te çürütme —
  `test_r35_and_r44_bracketed_with_engine_derived_lemmas`); öz-referanslı lemma zinciri büyüdü:
  R(3,4) → R(3,5)'i besledi, R(3,5) şimdi R(3,6)'yı besliyor (v2C1 deseni). Mini kapanışta
  (2026-08-06) mavi sınır sabit sözlükten çıkarıldı: `_OWN_BRACKETS` tablosu (yalnız motorun
  kendi bracketleri: R(3,3)=6, R(3,4)=9, R(3,5)=14) + `R(3,t−1)−1` formülü — t=4 dalı bedava
  geldi (mavi ≤ 5 = R(3,3)−1, lemma metni zinciri söylüyor), s=t=4 dalı da aynı tablodan türüyor;
  R(3,3)/R(3,4) verdictleri değişmedi (testli).

### 2a — SAT tarafı: n=17 tanık araması
- **Komut:** `ramsey_decide(17, 3, 6, strengthen=True)` · bütçe 300 s (tek segment)
- **Süre:** **0.1 s** (bütçenin çok altında)
- **Sonuç:** **SAT — R(3,6) > 17.** 41 kırmızı kenarlı tanık boyama bulundu ve kaba kuvvetle
  (çözücüsüz: her 3-altküme kırmızı-K₃, her 6-altküme mavi-K₆ taraması) bağımsız doğrulandı.
  Tanığın tam kenar listesi koşu çıktısında; ilk kenarlar:
  `(0,7),(0,8),(0,13),(0,14),(0,15),(1,3),(1,5),(1,8),…` (41 kenar, K₁₇).
- **KADEME:** `independently_verified_witness` — motorun en yüksek SAT kademesi, hak edilmiş.

### 2b — UNSAT tarafı: n=18
- **Komut (segment 1):** `ramsey_decide(18, 3, 6, strengthen=True, certify_unsat=True)` ·
  bütçe 600 s → **ZAMAN AŞIMI (SIGTERM, 600 s)**
- **Komut (segment 2):** `ramsey_decide(18, 3, 6, strengthen=True, certify_unsat=False)`
  (yalnız çözüm, DRUP kaydı kapalı) · bütçe 600 s → **ZAMAN AŞIMI (SIGTERM, 600 s)**
- **Sonuç:** **`undecided_within_budget`** — n=18 için NE SAT NE UNSAT iddiası vardır. Zaman
  aşımı sonuç değildir ve burada sonuç olarak YAZILMAMIŞTIR. Glucose3, türetilmiş iki derece
  lemmasıyla (kırmızı ≤ 5, mavi ≤ 13) güçlendirilmiş formülü 600 saniyelik iki ayrı segmentte
  de bitiremedi; RUP sertifika aşamasına hiç ulaşılamadı (certify sonucu yok — kaydedilecek bir
  `certify_unsat` çıktısı üretilmedi, bu satır o yokluğun dürüst kaydıdır).
- **KADEME:** yok (verdict yok). R(3,6)=18 motorun bracket'ine EKLENMEDİ; motorun R(3,6)
  bilgisi bugün yalnız "R(3,6) > 17" (2a, tanıklı) + literatür bilgisidir (kullanılmadı).
- **Not:** karşılaştırma için R(4,4) n=18 aynı makinede < 1 s'de UNSAT oluyor (mevcut test);
  (3,6) örneğinin mavi-K₆ kloz sayısı (C(18,6)=18 564) ve kırılması güç simetrisi bariyer.
  Simetri-kırma klozları DENENMEDİ — bunlar türetilmiş (implied) lemma DEĞİLDİR, model-koruma
  yerine yalnız SAT-eşdeğerlik verir; eklenmesi ayrı bir dürüstlük-etiket tasarımı ister
  (gelecek faz adayı, kademe tasarımıyla birlikte).
  **Güncelleme (2026-08-06):** o tasarım yapıldı ve n=18 çözüldü — bkz. Koşu 4 (bu kayıt
  değiştirilmedi; 2b'nin `undecided_within_budget` sonucu MONOLİTİK formül için hâlâ doğrudur).
- **Test pinleri (hızlı):** lemma metinleri + kloz-sayısı formülü (n başına iki seqcounter
  atmost bloğu) `test_r36_degree_lemmas_derive_the_right_bounds`; R(3,3)/R(3,4) çıpa
  regresyonu strengthen=True ile `test_r36_branch_leaves_small_anchors_untouched`
  (`tests/test_discovery_ramsey_sat.py`). Uzun n=17/18 koşuları test paketinde DEĞİL.

---

## Koşu 3 — Frankl büyük bütçe (v2B3 avının ~10×'i) + m=5 örneklemeli guard

- **Tarih:** 2026-08-05 · **Araç:** `hunt_frankl` (seeded SA, üreteç-uzayında; kesin tamsayı
  sertifikalayıcı kapıda), `guard_sampled` (yeni, v4F5)
- **Komut/parametreler:** 17 av portföyü — m=7 × 10 seed × 12 000 adım (cap 2000);
  m=8 × 5 seed × 8 000 adım (cap 3000); m=9 × 2 seed × 4 000 adım (cap 3000).
  Referans bütçe: v2B3 tek av m=7/4 000 adım (~3.2 s) → bu koşu toplam adım×seed olarak ~10×+.
- **Süre:** toplam **247.8 s** (m=7: ~10 s/av, m=8: ~22 s/av, m=9: 31.9 s + 4.2 s)
- **Sonuç:** **17/17 av `not_found_within_budget`** — karşı-örnek YOK (beklenen dürüst sonuç;
  bir tanık 45+ yıllık açık konjektürü çürütürdü). En iyi skorlar: m=7 ve m=8'in TÜM
  seed'lerinde `best_score = 1` (aile boyu 127 / 255), m=9'da 8 ve 11 (cap=3000 tam kuvvet
  kümesine [511 küme] izin vermiyor).
- **KADEME:** `not_found_within_budget` (aynen); skor kayıtları `exact_integer` (skor =
  max_x 2·freq(x) − |F|; ≤ −1 olsaydı kesin sertifika kapısı çalışırdı — hiç olmadı).
- **Örüntü (dürüst empirical + known-result caveat):** SA her m=7/m=8 seed'inde delinmiş kuvvet
  kümesine (2^m − 1 küme, boş küme atılmış) yakınsıyor; orada her eleman tam 2^(m−1) kümede →
  skor = 2·2^(m−1) − (2^m − 1) = **+1**, konjektüre en yakın "duvar". Bu BİLİNEN bir sınır
  davranışıdır (kuvvet-kümesi ailelerinde eşitlik-yakını doyma), yenilik iddiası değildir;
  kaydedilen şey enerjinin nereye çöktüğüdür.
- **m=5 hakkında dürüst not:** m=5 exhaustive **DENENMEDİ** — evren m=5'te 2^5 = 32 altküme, aday
  aile sayısı 2^(2^5) = 2^32 ≈ 4.29 milyar (m=4'ün 65 536'sından patlama); `guard_exhaustive(5)`
  bu yüzden `ValueError` ile REDDEDER (testli). Yerine `guard_sampled(5)`: sınırlı rastgele örnekleme +
  üreteç-evrimi (yürüyüşün yarısı önceki üreteçlerin mutasyonu), her örnek kesin
  sertifikalayıcıdan geçer. Büyük koşu: **20 000 örnek (17 633 farklı birleşim-kapalı aile),
  0.6 s, 0 ihlal**, en büyük aile 27 küme. `coverage` alanı aynen: örnekleme HİÇBİR ŞEY
  İSPATLAMAZ, yalnız formalizasyonu destekler.
- **Test pinleri (hızlı):** `guard_exhaustive(5)` reddi + örneklemeli guard'ın dürüst etiketi ve
  determinizmi (`test_exhaustive_guard_refuses_m5_*`, `test_sampled_guard_is_deterministic_*`,
  `tests/test_discovery_frankl.py`). 248 saniyelik portföy test paketinde DEĞİL.

---

## Koşu 4 — R(3,6) = 18: maks-kırmızı-derece SİMETRİ case-split'i n=18'i çözdü

- **Tarih:** 2026-08-06 · **Çözücüler:** Cadical195 (sonuç koşusu; RUP YOK — aşağıda),
  Glucose3 (probe'lar + hızlı-test çıpaları) · **Kod:** `ramsey_decide_case_split(n, s, t,
  budget_per_case_s, certify, strengthen, fix_neighbourhood, second_level, solver_name)` —
  yeni `CaseSplitVerdict`/`RamseyCase` (case başına D/d1/sonuç/süre/RUP-durumu kayıtlı).
- **Tasarım (simetri, implied DEĞİL — Koşu 2b'nin istediği ayrı dürüstlük-etiketi):** case'ler
  D = maks kırmızı-derece üzerinden (s=3'te D ∈ {0..t−1}: kırmızı-derece ≤ t−1 taban formülün
  kendisinin sonucu); `fix_neighbourhood`: N_red(0) = {1..D} birim klozları; `second_level`
  (s=3 + fix_neighbourhood şartlı): d1 = kırmızı-derece(1) ∈ {1..D} alt-case'leri,
  N_red(1) = {0} ∪ {D+1..D+d1−1} birim klozları. Kapsama argümanı ÜÇ yeniden-adlandırma adımı
  (maks-dereceli köşe → 0; N_red(0) → {1..D}; N_red(1)\{0} → {D+1..D+d1−1}), her adım K_n
  otomorfizmi — taban klozları, per-köşe lemma ailesi ve önceki adımların kısıtları korunur.
  HERHANGİ case SAT ⟹ taban SAT (case modeli taban modelidir — SAT yönü simetri istemez);
  TÜM case'ler UNSAT ⟹ taban UNSAT ⟹ R(s,t) ≤ n. Argüman docstring + verdict notunda YAZILI
  PROSE'dur, makine-kontrollü DEĞİLDİR — kademe adları bunu taşır (aşağıda). Lex-leader tam
  kırma İDDİA EDİLMEZ; yalnız tatmin-edilebilirlik korunumu.

### 4a — Probe'lar (dürüst ara kayıt: Glucose3 yetmedi, tasarım derinleşti)
- Glucose3 weak split (kardinalite eşitliği), 30 s/case: D=0..3 UNSAT ~0.02 s (mavi-derece ≤ 13
  lemması kırmızı-derece ≥ 4'ü zorluyor); **D=4 ve D=5 TIMEOUT** → `undecided_within_budget`.
- Glucose3 + fix_neighbourhood, 120 s/case: **D=4, D=5 yine TIMEOUT**.
- second_level probe'ları (tek-case script, dış `timeout 250`): Glucose3 (4,4) UNSAT **3.7 s**
  ama (5,4)/(5,5) 250 s'de bitmedi; Cadical195 (4,4) **1.1 s**, (5,4) **76.3 s**,
  (5,5) **169.0 s** — hepsi UNSAT. Ayrıca kayıt: pysat Cadical195 `interrupt()` koşan aramayı
  DURDURAMIYOR (1 s'lik timer'a rağmen çözüm 30 s+ koştu, dıştan öldürüldü) — bu yüzden motorda
  cadical bütçesi fork'lu child-process kill ile uygulanır.

### 4b — SONUÇ KOŞUSU: iki-seviye case-split, Cadical195, 240 s/case
- **Komut:** `ramsey_decide_case_split(18, 3, 6, budget_per_case_s=240, certify=False,
  strengthen=True, fix_neighbourhood=True, second_level=True, solver_name="cadical195")`
- **Süre:** toplam **239.0 s** — 16 case'in **HEPSİ UNSAT**, hiçbiri bütçeye çarpmadı:

  ```text
  (D=0,–): 0.06s   (D=1,1): 0.04s   (D=2,1): 0.04s   (D=2,2): 0.06s
  (D=3,1): 0.04s   (D=3,2): 0.04s   (D=3,3): 0.04s
  (D=4,1): 0.04s   (D=4,2): 0.04s   (D=4,3): 0.04s   (D=4,4): 1.25s
  (D=5,1): 0.04s   (D=5,2): 0.04s   (D=5,3): 0.04s   (D=5,4): 70.12s  (D=5,5): 167.01s
  ```

  (Lemmalar her case formülünde: kırmızı-derece ≤ 5 + mavi-derece ≤ 13 = R(3,5)−1 — motorun
  kendi bracket'i; D<4 ve d1<4 case'lerinin anında ölmesi bu iki sınırın kesişmesindendir.)
- **Sonuç:** **R(3,6) ≤ 18.** Koşu 2a'nın n=17 bağımsız-doğrulanmış tanığıyla birlikte:
  **R(3,6) = 18 — motorun KENDİ bracket'i** (`_OWN_BRACKETS`e işlendi; zincir:
  R(3,3)/R(3,4) → R(3,5) → R(3,6), t=7'nin mavi lemması artık hazır).
- **KADEME:** `solver_verified_unsat_by_symmetry_case_split` — sınırları aynen: (1) kapsama
  argümanı yazılıdır, makine-kontrollü değildir; (2) Cadical UNSAT'ları çözücünün sözüdür — RUP
  yok: Cadical DRAT-ailesi çıktı verir ve `rup_check`'in belgeli sağlamlık argümanı RUP-only
  (trap marker), bu yüzden motor `certify=True` + cadical'ı `ValueError` ile REDDEDER (sessiz
  düşürme yok); (3) RUP'lu kademe (`..._with_rup_checked_cases`) motorda vardır ve R(3,4)@9
  çıpasında KAZANILIR (testli: 4 case'in 4'ü RUP-doğrulamalı) ama R(3,6)@18'de
  KAZANILMAMIŞTIR — proof verebilen Glucose3, (5,4)/(5,5) case'lerini bütçede bitiremedi.
  Bracket tablosundaki (3,6) girişi bu zayıf halkayı üstünde taşır; R(3,6)'yı ileride
  alıntılayacak her lemma o kaydı miras alır.
- **Test pinleri (hızlı, mekanizma):** RUP'lu kademe R(3,4)@9 (`test_case_split_r34_unsat_
  earns_the_rup_checked_cases_tier`), SAT tanık yolu R(3,3)@5, second-level çıpaları + case
  listesi, timeout→`undecided_within_budget` (n=18, 0.05 s bütçe — kısmî UNSAT asla sonuç
  değil), guard `ValueError`ları, bracket girişinin SAT bacağı (n=17, ~0.1 s) ve t=7 zincir
  lemma metni (`tests/test_discovery_ramsey_sat.py`). 239 s'lik koşu test paketinde DEĞİL.
- **Mini kapanış (2026-08-06, evaluator PASS sonrası):** (1) dejenere alt-case'ler (d1 > n−D)
  üretimden atlanır ve D-aralığı n−1'e kırpılır (`_case_split_ids` — her yayımlanan kısıt metni
  her rejimde harfiyen doğru; n=18 listesi değişmedi: 16 case, test-pinli); (2) her `RamseyCase`
  kendi kısıt metnini taşır (`constraint` alanı), verdict'teki `case_constraint` artık şemadır;
  (3) kloz-üreticide iç guard (d1 ⟹ fix_neighbourhood, `ValueError`); (4) kapsama ZİNCİRİ küçük
  n'de TÜKETİCİ makine-kontrollü — (3,3) n≤5 + (3,4) n≤4'ün 87 taban modelinin HEPSİ üç-adım
  yeniden-adlandırmayla geçerli (D,d1) case'ine iner, tüm kısıtlar korunur
  (`test_case_split_covering_chain_is_machine_checked_by_exhaustion_at_small_n`). Bu KÜÇÜK-n
  KALIP kontrolüdür: n=18'in kapsaması hâlâ yazılı argümandır, kademe DEĞİŞMEDİ.

## Koşu 5 — R(3,7) SAT sondası @ n=22 (2026-08-06)

Komut: `ramsey_decide(22, 3, 7, strengthen=True)` (Glucose3; türetilmiş lemmalar: kırmızı≤6 taban-türevi,
mavi≤17 = R(3,6)−1 — motorun KENDİ yeni bracket'inden, öz-referanslı zincir 5. halkasını denedi).
Sonuç: **SAT, 0.8 s** — 64 kırmızı kenarlı boyama, kaba-kuvvet bağımsız doğrulamadan geçti
(kademe `independently_verified_witness`) ⟹ **R(3,7) > 22**.
DÜRÜST SINIR: üst taraf (UNSAT @ n=23) DENENMEDİ — R(3,6)@18'in (5,5) case'i 167 s idi; n=23 case-split'i
kestirilebilir biçimde çok daha ağır, ayrı bütçelenmiş bir saldırı ister (kayıtlı sonraki adım).
R(3,7) motorda BRACKET DEĞİL (tek taraf); _OWN_BRACKETS'a GİRMEDİ.
