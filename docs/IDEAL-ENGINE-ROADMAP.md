# İdeal Matematik Motoru — Tam Yol Haritası (tepeden ormana)  ·  [PLAN — DONMUŞ]

> **Bu, üç takip dosyasından PLAN'dır.** Aşama LİSTESİ donmuştur — hiçbir aşama silinmez/eklenmez
> (CI `test_trackers` tam 103 aşama / 21 track olduğunu doğrular). Yalnızca her aşama satırına, o iş
> bitince ✅/🟢 tamamlanma işareti EKLENİR (bu planı değiştirmez, sadece ilerlemeyi kaydeder). Canlı
> özet TODO.md'de, anlatı PROGRESS.md'de.


> **Bu dosyanın işi:** "İdeal matematik motoru" belgesindeki HER özelliği, MathHead'in
> bugün durduğu yerden (yargıç/doğrulama omurgası, Track A–L) o vizyona kadar, aşama aşama,
> eksiksiz dökmek. Amaç: sonradan "şu da vardı, bu da vardı" dememek. Önceki MathHead
> roadmap mantığıyla aynı: her aşama TEK bir iş yapar, öncekinin üstüne biner, test-kapılıdır.

## Sözlük (etiketler)

```
♻️  MathHead'de zaten var / tabanı kurulu → yeniden kullan
🟢  Standart mühendislik (nasıl yapılacağı biliniyor)
🟡  Zor / entegrasyon-ağırlıklı (bilinir ama emek ister)
🔴  Araştırma sınırı (garantili çözümü YOK — dürüst uyarı)
```

## Orman — 22 track, 4 küme

```
KÜME 1 — GÜVEN / YARGIÇ omurgası      (MathHead'in evi; kurulu, sağlamlaştırılacak)
   M  Güvenilir çekirdek & proof kernel        (§1)
   Q  Karşı-örnek-önce refütasyon               (§6)   ♻️ kısmen
   R  Sertifikalar & epistemik durum            (§11,§14) ♻️ büyük ölçüde

KÜME 2 — MADDE & DENEY                 (motorun üstünde çalıştığı nesneler)
   N  Tipli nesne modeli & üretim
   O  Özellik & invariant değerlendirme
   U  Temsil dönüştürücü & arama                (§2)
   AA Program sentezi / çalıştırılabilir matematik (§10)

KÜME 3 — KEŞİF / YARATICI kalp         (belgenin heyecanı; çoğu YENİ)
   P  Konjektür üretimi                         (§4)
   T  Ara-lema keşfi                            (§8)
   S  İspat arama portföyü & orkestrasyon        (§7)
   W  İlginçlik & seçim                          (§5)
   Z  Yeni kavram & tanım üretimi                (§9)  🔴 sınır
   AB Aksiyom & bağımsızlık analizi              (§15) 🔴 sınır

KÜME 4 — BİLGİ, ARAYÜZ, ÜRÜNLEŞME     (glue + hafıza + insan + ölçek)
   V  Doğal dilden güvenli formelleştirme        (§3)
   X  Bilgi grafiği & etki analizi               (§12)
   Y  Başarısızlık hafızası & negatif bilgi       (§13)
   AC Araştırma direktörü & tam döngü             (mimari)
   AD İnsan ortak-çalışma arayüzü                 (§16) ♻️ kısmen
   AE Alan örneklemesi: sonlu kombinatorik + graf (v0.1)
   AF Değerlendirme, benchmark & provenance
   AG Altyapı: ölçek, determinizm, güvenlik, CI, docs ♻️ kısmen
```

---

## Tam aşama listesi

### KÜME 1 — GÜVEN / YARGIÇ omurgası

**Track M — Güvenilir çekirdek & proof kernel (§1)**
```
M0 ♻️🟡 MathHead yargıç yüzeyini (envelope + determinizm + provenance/meta) kernel arayüzü olarak sabitle  🟢 PİNLENDİ: Verdict zarfı (status/certainty/reason_code/detail/source_status/engine) alan-alan test-kilidli + judge determinizmi pinli (test_discovery_statement_parse.test_m0); kernel provenance (hash+aksiyom) zaten M4/M5'te mühürlü; ADR-D0071
M1   🟡 Minimal proof-term dili tasarla (LCF-stili / bağımlı tip) — "yalnızca izin verilen kurallar"  🟢 İLK KERNEL: proof-term ADT (RESIDUE yaprağı + CRT kompozisyon) modüler-polinom parçası için; Theorem forge-korumalı (yalnız kernel _mint eder); ADR-D0022  🟢 GENİŞLETİLDİ: ikinci yargı SumIdentity (SumInduction kuralı, rasyonel polinom aritmetiği); tek kernel iki alanı da kapsar, yargılar karışmaz; ADR-D0024
M2   🟡 Kernel: tip kontrolü + kural kontrolü + nihai terim teoremi gerçekten kuruyor mu?  🟢 kernel.check terimi yorumlar, her kural yan-koşulunu doğrular (residue taraması; CRT eşit-polinom+ikili-aitlik-asal), yanlış iddiayı/forge'u/uyumsuz-polinomu reddeder; prover AYRIK & güvenilmez; ADR-D0022 + GÜVEN TABANI KÜÇÜLDÜ: RESIDUE artık PRİMİTİF değil — çarpan teoreminden türetiliyor (congruence.derive_residue: her r için p(x)−p(r)=(x−r)q(x) kernel PolyIdentity ile doğrulanır); residue-exhaustion bir AKSİYOM değil TEOREM; bağımsız checker kernel'siz yeniden doğrular; ADR-D0040 + SUMINDUCTION DA TÜRETİLDİ: tümevarım ADIMI artık açık — g(n)=g(n−1)+f(n) kernel'in KENDİ PolyIdentity kuralıyla doğrulanır (sum_derivation.derive_sum_identity), taban n=1 değerlendirmesi; SumInduction bir primitif değil PolyIdentity üzerine TEOREM; kernel SumInduction kuralıyla birebir tutarlı (Σi, Σi², Σi³); ADR-D0043 + M-TABANI TAMAMLANDI: "elementer tamsayı bölünebilirliği" el-sallaması artık AÇIK — m|a∧m|b⇒m|a+b ve m|a⇒m|a·k lemmaları konstrüktif tanık (bölüm) + tüm aralıkta tükenmeli kontrol (4624 kontrol, 0 hata); ℤ halka aksiyomlarına dayanır, altında başka bir şey yok (divisibility.py); ADR-D0049
M3   🟡 Bağımsız İKİNCİ checker (farklı dil/ekip) — kernel'i çapraz doğrula  🟢 İLK BAĞIMSIZ CHECKER: modüler-polinom ispatlarını dik/stdlib kalıntı yöntemiyle yeniden doğrular, yanlışı/bozuk-CRT'yi reddeder (ADR-D0016)
M4   🟢 Deterministik proof replay + proof-artifact hash + kernel sürümleme  ✅ (provenance.proof_hash: kanonik+versiyonlu içerik hash'i, sıra-bağımsız; replay: kernel'i yeniden çalıştır; ArithmeticFinding.proof_hash + raporda [hash]; ADR-D0023)
M5   🟢 Kullanılan aksiyomların tam listesi + bağımlı-teorem grafiği (provenance)  🟢 AKSİYOM LİSTESİ: provenance.axioms_used her teoremin dayandığı RESIDUE(m)/CRT kurallarını verir; raporda kernel-aksiyom manifestosu; bağımlı-teorem grafiği (proof_tree, T3) mevcut; ADR-D0023
M6   🟡 Lean/harici ispat asistanına köprü: ispatı dışa aktar + Lean çekirdeğiyle çapraz-mühürle  🟢 EXPORT KATMANI KURULDU (v2C2 = lean_export.py): 9 teorem Lean 4 kaynağı olarak yazıldı, decide-over-ZMod korespondansı belgelendi; harici lake build ÇALIŞTIRILMADI — çapraz-mühür beklemede, dürüstçe
M7   🟢 Zengin durum çıktısı (STATUS/FOUNDATION/DEPENDENCIES/KERNEL/PROOF_HASH/INDEPENDENT_CHECKER)
```

**Track Q — Karşı-örnek-önce (§6)**
```
Q0 ♻️🟢 Küçük sonlu tam tarama (MathHead bounded + N üreticileri)  ✅ (refute: counterexample-first bounded scan; survivor = no_counterexample_within_bound)
Q1 ♻️🟢 SAT/SMT + constraint programming saldırısı (MathHead frontier'i genişlet)  🟢 GENİŞLETİLDİ: ramsey_sat (v2C1) SAT cephesini Ramsey-tipi problemlere taşıdı — R(3,3)=6/R(3,4)=9 bracketlendi, tanıklar bağımsız doğrulı; çapraz-bağ ADR-D0067
Q2   🟢 Rastgele + adversarial + evrimsel karşı-örnek arama  ✅ (v2 enstrümanlarıyla TESLİM EDİLDİ: adaptive_search — tohumlu SA bağlı-graf + ağaç uzayları, tamsayı-sertifikalı verdictler; frankl.hunt_frankl — küme-aile uzayında jeneratör-evrimi; çapraz-referans ADR-D0064/65)
Q3   🟡 Model checking + interval arithmetic + sembolik test yolları  🟢 INTERVAL-ARİTMETİK DİLİMİ (interval_check.py): mpmath.iv directed-rounding ile A–H çift-yıldız slack'inin SERTİFİKALI kapaması; üç-değerli dürüst verdict (violation/no-violation/undecided — D(12,12) eşitliği dürüstçe undecided, kapama [0,0]); tamsayı-Sylvester'a TAM BAĞIMSIZ ikinci kesin yol, 7/7 çapraz-uyum testli; ADR-D0070
Q4   🟡 Minimal karşı-örnek indirgeme (delta-debugging)  ✅ (minimal: en küçük n, sonra en az kenar; ör. T≤E → K6−e)
Q5   🔴 Başarısızlık mekanizması çıkarımı ("invariant iki çevrim bir tepe paylaşınca bozuluyor")
Q6   🔴 Onarılmış konjektür önerisi (ek varsayımla ifade geçerli mi?)
```

**Track R — Sertifikalar & epistemik durum (§11, §14)**
```
R0 ♻️🟢 Bağımsız sertifika kontrolcüleri (MathHead: subset-sum, boyama, DRAT/DRUP, çarpanlama...)  ✅ (MathHead; + discovery.judge köprüsü kuruldu)
R1   🟡 Yeni sertifika türleri: LP dual, Gröbner basis kontrolü, coverage manifesto, canonical-labeling, interval izi  🟢 İLK DİLİM: grafik alanı için KONSTRÜKTİF sertifikalar — χ≤Δ+1 (greedy boyama tanığı), χ≤n (kimlik boyama), ω≤χ (maksimum klik, MathHead ile çift-doğrulanmış: K_ω, (ω−1)-boyanamaz→unsat); bağımsız checker sahteleri reddeder; DÜRÜST etiket `constructive_bounded` (tanıklı ama evrensel ∀G ispat DEĞİL — o M1/M2 kernel gerektirir); ADR-D0021
R2   🟢 Kernel sertifikayı yeniden-hesaplamadan kontrol edebilsin (certificate-check API)  ✅ (TESLİM EDİLMİŞTİ, çapraz-bağ: graph_proofs.check_certificate tanığı yeniden-türetmeden doğrular; provenance.replay ispat artefaktını yeniden-hesapsız tekrar-kontrol eder; spectral_cert/ramsey_sat tanıkları da kendi bağımsız checker'larını taşır)
R3 ♻️🟢 Epistemik durum sözlüğü (MathHead certainty/stability → §14: UNFORMALIZED..INDEPENDENTLY_VERIFIED..LIKELY_INDEPENDENT)  ✅ (Verdict, MathHead certainty taşıyor; empirical→proved/refuted; ADR-D0006)
R4   🟢 "Çözemedim; yalnızca şu sınıra kadar karşı-örnek yok" — bounded-honesty her çıktının sözleşmesi  ✅ (Q0 no_counterexample_within_bound + judge not_applicable)
```

### KÜME 2 — MADDE & DENEY

**Track N — Tipli nesne modeli & üretim**
```
N0 🟢 Tipli matematiksel nesne DSL'i (graph, matrix, integer-seq, finite-model, poly, combinatorial obj...)  ✅ (Graph; mathhead.discovery.objects) + ÜÇÜNCÜ ALAN: Permutation (S_n, A000142; inv/desc/fix/cycle; ADR-D0032) + DÖRDÜNCÜ ALAN: Partition (p(n) A000041; Euler distinct=odd A000009 + conjugation; ADR-D0037) + BEŞİNCİ ALAN: SetPartition (Bell A000110, Stirling2 A008277) + ALTINCI ALAN: Composition (2^(n−1) A011782, CUT-POINT bijeksiyonuyla konstrüktif ispat; C(n−1,k−1) k-parça; ADR-D0047); mimari alan-bağımsız ALTI kez kanıtlandı — rapor/merdiven/açıklamalar/scorecard sıfır değişiklikle absorbe etti
N1 🟢 Kanonik nesne üreticisi — küçük/orta boy nesneleri sistematik üret  ✅ (brute n≤7 honest-bound; OEIS A000088 ile doğrulı; nauty/orderly = opt)
N2 🟡 İzomorfizm eleme (canonical labeling, nauty-benzeri) — tekrarları at  ✅ (derece-arıtılmış permütasyon-min; C6≠2C3 ayırıyor; ADR-D0002)
N3 🟢 Nesne serileştirme + içerik-hash + tekrar-üretilebilir sıralama (determinizm)  ✅ (serialize.py: 5 nesne tipini kapsayan tek kanonikleştirici; content_hash, reproducible_sort, deduplicate; stdlib-only, deterministik)
N4 🟢 Parametrik aileler + kısıtlı örnekleyiciler (stratified sampling)  ✅ (families.py: K_n/C_n/P_n/star/wheel/K_{a,b} her boyutta + stratified_sample; invariantlar bilinen kapalı formlarla çapraz-doğrulanır [oracle])
N5 🟡 Rastgele + adversarial + ekstrem/dejeneratif nesne üreticileri  ✅ (adversarial_objects: degenerate + K_n/K_n−e + seed'li rastgele stress_set; tüm invariantlar 0 çökme ile geçer; determinizm seed'li)
N6 🟢 Nesne deposu + invariant'a göre indeksleme/sorgu  ✅ (object_store.ObjectStore: content-hash dedup + invariant ters-indeks; query(χ=3, num_triangles=0)→C5; N3+O1 üzerine)
```

**Track O — Özellik & invariant değerlendirme**
```
O0 🟢 Özellik değerlendirici (nesnede P doğru mu? deterministik, cache'li)  ✅ (invariants.evaluate + registry)
O1 🟢 Yerleşik invariant kütüphanesi (derece dizisi, kromatik/çevrim/bağlılık...)  ✅ (edges/degseq/triangles/components... + SPEKTRAL: Σλ²=2E, Σλ³=6·üçgen; graf→MathHead köprüsü; ADR-D0009 + FRONTIER-1: kromatik sayı χ backtracking ile, MathHead graph_coloring ile bağımsız doğrulanır [sat@χ, unsat@χ−1]; ω≤χ≤Δ+1 madenciliği, χ≤Δ çürütüldü; ADR-D0018 + FRONTIER-2: is_hamiltonian backtracking ile, MathHead hamiltonian_path[cycle] ile doğrulanır [n≤5'te 0 uyuşmazlık]; Dirac teoremi veriden yeniden keşfedildi, connected⟹Hamiltonian çürütüldü [P₃]; ADR-D0019)
O2 🟡 Otomatik invariant çıkarımı — milyonlarca örnekte değişmeyeni bul  ✅ (null-space lineer yasa madenciliği; Handshake Lemma'yı veriden buldu; empirical; ADR-D0004) + NON-LINEAR GENİŞLETME: derece-2 polinom özellik haritası (çarpımlar/kareler) üzerinde aynı tam null-space; K_n'de 2·num_edges = n²−n'i yeniden keşfeder; indirgenebilir (alt-yasa × invariant, ör. Handshake×derece) yasaları eler; zengin örneklemde yalnız Handshake-karesi kalır (dürüst: yeni evrensel yok); empirical, derece-2 sınırlı; nonlinear_relations.py; ADR-D0050
O3 🟢 Özellik/invariant ↔ nesne matrisi (feature table) — konjektür & sınıflandırma zemini  ✅ (invariant_vector + relations feature matrix)
O4 ♻️🟢 Numerik + sembolik + exact değerlendirme yolları + tutarlılık çapraz-kontrolü (cross_check)  ✅ (cross_check.py: |E| 4 yolla [sayım/Handshake/trace(A²)/MathHead Σλ²], #üçgen 3 yolla; n≤5 tüm graflar + adversarial stress_set tutarlı, 0 uyuşmazlık)
```

**Track U — Temsil dönüştürücü & arama (§2)**
```
U0 🟢 Temsiller arası köprüler: algebra ↔ graph ↔ SAT ↔ matrix ↔ poly-ideal ↔ program ↔ optimization  🟢 representations.py: DOĞRULANMIŞ temsil-dönüşümü kütüğü — graph↔komşuluk-matrisi + kompozisyon↔kesim-altkümesi (round-trip: decode∘encode=kimlik, tüm örnekte), graph→derece-dizisi (Handshake Σderece=2|E| korunur), bölünebilirlik→kalıntı-tablosu (KARAR: tablo sıfır ⟺ kernel m|p(n) ispatlar, verdictler uyuşur); dönüşümlerin SADIK olduğunu doğrular (O4 değer-tutarlılığını tamamlar); ADR-D0051
U1 🟡 Sayı-teorisi zinciri: Diophantine → modular → lattice → SAT/SMT → finite residue → alg. geometri  🟢 nt_chain.py: bir bölünebilirlik iddiasını zincirin KARAR VERİLEBİLİR segmentinde yürütür — Diophantine → modular p(n)≡0 (mod m) → sonlu-kalıntı tablosu → karar; ∀ için tablo (hepsi-sıfır) kernel RESIDUE ile çapraz-doğrulanır, ∃ için (bir-sıfır) dürüst ayrımı yüzeye çıkarır (5|n³−n ∀ YANLIŞ ama ∃ DOĞRU, n=5); AÇIK defter: yürünen linkler vs yürünmeyenler (lattice/SAT-SMT/cebirsel-geometri) kaydedilir — zincirin kapsamadığı kısmı gizlemez; U0 köprüsü üzerine; ADR-D0054
U2 🔴 Representation SEARCH: hangi temsil problemi kolaylaştırır? (otonom seçim — açık problem)
U3 ♻️🟢 Dönüşüm anlam-koruyor mu doğrulaması (cross_check)
```

**Track AA — Program sentezi / çalıştırılabilir matematik (§10)**
```
AA0 🟢 Aday program üreteci (DSL) + otomatik değerlendirici (FunSearch iskeleti)  ✅ (program_search: ifade-ağacı DSL'i {+,−,×,güvenli //, sabitler} + TAM-eşleşme değerlendirici (float yok); overflow/sıfır-bölme korumalı; ADR-D0069)
AA1 🟢 Evrimsel arama: iyi programları mutasyona uğrat + seç  ✅ (tohumlu mutasyon-only elitist evrim + deterministik restart'lar; kareleri ve üçgensel sayıları YENİDEN KEŞFEDER — ((n+1)+n·n)//2 zarif floor-form; bulamayınca dürüstçe not_found_within_budget; ADR-D0069)
AA2 🟢 Programın davranışından konjektür çıkar  ✅ (kazanan program = kapalı-form konjektürü, program_found_empirical; kısmi-toplam hedeflerinde kapalı form KERNEL'e verilir — SumInduction ispatı + proof hash → kernel_verified; evrim ve kernel BAĞIMSIZ yollardan aynı forma varır, AA→M döngüsü kapandı; ADR-D0069)
AA3 🟡 Dört seviye: DISCOVERED_HEURISTIC → EMPIRICALLY_VALIDATED → FORMALLY_SPECIFIED → FORMALLY_PROVED  🟢 epistemic_ladder: tüm certainty sözlüğünü 4 basamağa indirger, her bulguyu sınıflar (L2=23,L3=7,L4=17); muhafazakâr eşleme (L4 yalnız kernel/bağımsız doğrulanmış); raporda solidity dağılımı; ADR-D0031
AA4 🟡 Bulunan algoritmayı ispata bağla (Track S/M köprüsü)  🟢 algorithm_proof.py: keşfedilen ALGORİTMAYI onu doğrulayan İSPATA bağlar — residue-exhaustion/CRT → KERNEL Teoremi (kernel_verified, evrensel ∀n, hash+aksiyom); greedy-coloring/max-clique → KONSTRÜKTİF sertifika (constructive_bounded, örnekte tanıklı, ∀G değil); İKİ modalitenin GÜÇ farkı hakkında dürüst — sertifikayı asla kernel_verified etiketlemez, ispat tutmazsa verified=False (sahte ispat yok); yeniden ispatlamaz, LİNKLER (S/AA → M köprüsü); ADR-D0048
```

### KÜME 3 — KEŞİF / YARATICI kalp

**Track P — Konjektür üretimi (§4)**
```
P0 🟢 Deneysel örüntü madenciliği: eşitlik/eşitsizlik/monotonluk/periyodiklik/asimptotik/yasak-yapı  ✅ (alt-sınıf yasaları + eşitsizlik sınırları; ağaç teoremlerini veriden buldu; ADR-D0005) + GENİŞLETME (oran & monotonluk): pattern_mining.py — SABİT oranlar (Handshake'i oran biçiminde yeniden bulur: sum_degrees/num_edges = 2; payda 0 ise atlar; ≥1 yönü) + sıralı ailede MONOTON eğilimler (K_n'de num_edges/sum_degrees/num_triangles kesin artan); tam (Fraction), empirical; ADR-D0053
P1 🟢 Teorem mutasyonu: varsayım zayıflat / sonuç güçlendir / sabit iyileştir / boyut artır / genelle  ✅ (mutate.py: survivor'ı GÜÇLENDİR [en büyük çarpan/toplamsal boşluk: num_edges≤sum_degrees ⇒ 2·num_edges≤sum_degrees = Handshake], refuted'ı ONAR [num_triangles≤num_edges+5]; her mutasyon counterexample-first yeniden test edilir) + systematic P0: feature_conjectures tüm ikili invariant eşitsizliklerini üretir
P2 🟡 Tersine mühendislik: ilginç sonucu bul → onu açıklayan daha genel ilkeyi ara  🟢 generalize.py: SPESİFİK bulguyu (6|n³−n, 3 ardışık tamsayı) PARAMETRE üzerinde genel yasaya kaldırır ("her k için k ardışık tamsayının çarpımı k! ile bölünür"), k=1..K örneklerini kernel ile doğrular (her biri n'de evrensel, RESIDUE(k!)); ∀k iddiası DÜRÜST işaretlenir (per-k kernel_verified, sınırsız k = atıflı yapısal argüman C(n,k)∈ℤ); ardışık-çarpım yapısı yoksa üretmeyi REDDEDER (n⁵−n); ADR-D0044
P3 🟡 Analoji motoru: bir alandaki yapıyı diğerine taşı (graph-cut ↔ submodular...)  🟢 analogy.find_analogies: aynı ispat TEKNİĞİ (çift-sayma, konstrüktif bijeksiyon, rekürrans) ≥2 alanda tekrar ederse analoji olarak raporlar; bijeksiyon: permütasyon↔bölüntü, rekürrans: permütasyon↔küme-bölüntü; DÜRÜST: ortak ispat ŞEKLİ iddiası (metin eşleme), derin denklik değil; ADR-D0041
P4 🟡 Ramanujan-tarzı bağıntı/sabit arama (sayısal ilişki → sembolik aday)  ✅ (sum-identity: kısmi toplamdan kapalı form fit + tümevarımla ispat; Σi², Σi³ …; non-poly reddedilir; ADR-D0010)
P5 🟢 Konjektür normalize + tekilleştir + dedup  🟢 conjecture_normalize.py: birden çok madenciden gelen konjektürleri TEK kanonik lineer-form anahtarına indirger (primitif + işaret-sabitli) → tekrarlar birleşir; Handshake hem lineer yasa hem oran olarak bulunur → TEK konjektür, corroboration=2 (bağımsız kaynak sayısı); oran A/B=p/q → qA−pB=0 ilişkisine çevrilir; provenance korunur; DÜRÜST: yalnız tam lineer normal-form eşitliğiyle dedup, asla aşırı-birleştirmez, çarpım-terimli non-linear çakışmaz; ADR-D0055
P6 🟡 (LLM-periferi) doğal-dil sezgisinden aday konjektür — yargıç zorunlu (kalite açık)
```

**Track T — Ara-lema keşfi (§8)**
```
T0 🟡 Hedef ↔ mevcut bilgi arası "boşluk" ölçümü  🟢 gap.py: bir hedef için KANITLANMIŞ zemine BFS mesafesi + çözülmemiş bağımlılıklar → [0,1] boşluk skoru; açık hedefleri "ele en yakın" (en küçük boşluk) sıralar; impact'in dolanıklık görüşünü TAMAMLAR (mesafe ≠ merkezilik); kanıt-çıpası yoksa dürüstçe boşluk=1.0 (aritmetik-dışı hedeflerin gerçek sınırını yüzeye çıkarır); ADR-D0045
T1 🔴 Eksik kavram/lemma tahmini (bottleneck: "F, μ invariant'ını koruyor mu?")
T2 🟢 Aday lemma sıralama (önem/olabilirlik)  🟢 lemma_ranking.py: açık hedefleri ÖNEM × OLABİLİRLİK ile sıralar — impact'in dolanıklığı (önem = related_to derecesi, normalize) ile gap'in kanıta-yakınlığını (olabilirlik = 1−gap_score) tek şeffaf önceliğe kaynaştırır (ağırlıklı toplam, denetlenebilir, ÖĞRENİLMİŞ DEĞİL); next_lemma = direktörün sıradaki hedefi; yalnız DİKKATİ sıralar, doğruluğu değil; ADR-D0052
T3 🟢 Proof dependency graph üretimi (lemma → ana hedef bağlantısı)  ✅ (proof_tree: CRT ispatı → prime-power lemmaları; residue → tam-vaka yaprağı; render_tree; ADR-D0015) + SUM-IDENTITY genişletme: sum_proof_tree — Σf(i)=g(n) ispatını TABAN (g(1)=f(1) değerlendirme) + ADIM (g(n)=g(n−1)+f(n) kernel PolyIdentity) lemmalarına ayırır (sum_derivation üzerine); modüler ağaçla aynı dürüst dilim; ADR-D0058
```

**Track S — İspat arama portföyü & orkestrasyon (§7)**
```
S0 🟢 Strateji kayıt defteri (forward/backward, best-first, MCTS, resolution, superposition, rewriting, induction, case-split, symmetry, QE, Gröbner, ILP, exhaustive...)  🟢 İLK STRATEJİ: modül-çarpanlama + CRT (tek tümevarımın çözemediğini ispatlar; direct→fallback mini-portföy; ADR-D0011)
S1 🟡 Problem sınıflandırıcı (discrete/finite-large/symmetry/existential/polynomial) → portföy seçici  🟢 İLK PORTFÖY: induction → factoring+CRT → residue-exhaustion (tam karar); kazanan yöntem kaydediliyor; ADR-D0014
S2 🟡 Paralel portföy yürütücü + kaynak/bütçe yöneticisi  🟢 portfolio.py: modüler ispat portföyünü (direct-residue vs CRT-prime-powers) PAYLAŞILAN adım-bütçesi altında ucuzdan-pahalıya yürütür; kazanan = ispatlayan en düşük-maliyetli strateji (yarışta ilk biten); tam maliyet defteri (hangi başlatıldı/atlandı, harcanan); DÜRÜST durum solved/unsolved/exhausted — bütçe yetmezse "exhausted" der, asla sahte ispat üretmez; idealize-paralel deterministik model (OS thread/duvar-saati yok, tekrarüretilebilirlik önce); ADR-D0046
S3 🟢 Başarısız stratejilerin kaydı (Track Y'ye besleme)  🟢 strategy_log.py: S2 portföyünün ÇÖZEMEDİĞİ koşularını failure_memory'ye (Track Y) besler — exhausted→timeout, unsolved→dead_end (idempotent, fingerprint ile dedup); solved kaydedilmez; strateji-başı TANI (launched/skipped/wins sayıları) darboğazı yüzeye çıkarır (en çok "karşılanamaz" diye atlanan strateji = direct-residue, pahalı tam-m taraması); S→Y döngüsü kapandı, sessiz tekrar yok; ADR-D0056
S4 🔴 (RL/öğrenilmiş) ispat rehberliği — arama uzayı patlamasına karşı
```

**Track W — İlginçlik & seçim (§5)**
```
W0 🟢 Trivial filtreler (x=x, "n=73421 ise n²≥n") — çöp teoremleri ele  ✅ (novelty: alt-sınıfa-özgü mü yoksa kısıtlanmış-evrensel mi; handshake-restriction eleniyor; ADR-D0012) + GENİŞLETME yeni örüntülere: trivial_filter.py — SABİT invariant üzerinde monoton "eğilim" sahtedir (num_components≡1 → non_decreasing atılır); iki tarafı da sabit olan oran tesadüfidir (atılır); gerçek ilişki (Handshake) korunur; tam, örnek-temelli, yalnız ELER; ADR-D0057
W1 🟡 İlginçlik bileşenleri: novelty/generality/surprise/usefulness/compression/connectivity − triviality  🟢 interestingness.score: her bileşen adlandırılmış deterministik proxy + belgelenmiş ağırlıklar → [0,1] skor + bileşen dökümü; raporda MOST INTERESTING; DÜRÜST: öğrenilmiş değil (W3 açık); ADR-D0026
W2 🟡 Novelty = literatür/bilgi-grafiğiyle eşdeğerlik kontrolü (Track X'e bağlı)  🟢 known_results yapılandırılmış+atıflı katalog (21 sonuç, 5 alan); attributed_findings her bulguyu bilinen teorem+atıfla eşler; scorecard 0-novel denetlenebilir; gerçek korpus katalogu GENİŞLETİR, hükmü değiştirmez; ADR-D0042
W3 🔴 Öğrenilmiş ilginçlik modeli + insan geri-bildirim döngüsü (tam otomatik DEĞİL — belge de kabul ediyor)
```

**Track Z — Yeni kavram & tanım üretimi (§9) — TAMAMEN 🔴**
```
Z0 🔴 Ortak-değişmezlik madenciliği: birlikte sabit kalan özelliklerden aday yeni invariant
Z1 🔴 Yeni norm/uzaklık/eşdeğerlik/karmaşıklık-ölçüsü/dönüşüm/sınıflandırma önerisi
Z2 🔴 Önerilen kavramın rolü: açıklanamayan aileyi sınıflandırıyor mu? (fayda testi)
Z3 🔴 Kavramın dile yerleşmesi: tanım tutarlı mı + üretken mi (yeni teorem doğuruyor mu?)
        (Belgenin hem "en önemli fark" hem "en zor" dediği yer — kimsede araştırma-derinliğinde çözümü yok.)
```

**Track AB — Aksiyom & bağımsızlık analizi (§15)**
```
AB0 🟢 Kullanılan aksiyomları izle (Track M provenance'tan)
AB1 ✅ Daha zayıf aksiyomla ispat ara (choice'suz, vb.) — axiom_minimize.py: direct-RESIDUE vs CRT, en az aksiyomlu ispatı seçer (6|n³−n ⇒ RESIDUE(6) tek başına)
AB2 🔴 Model oluşturma / forcing (sonlu analog: T+P ve T+¬P modelleri)
AB3 🔴 Bağımsızlık ihtimali değerlendirmesi ("ispat bulamadım" ≠ "ispat imkânsız")
```

### KÜME 4 — BİLGİ, ARAYÜZ, ÜRÜNLEŞME

**Track V — Doğal dilden güvenli formelleştirme (§3)**
```
V0 ♻️🟢 Tanı-ya-da-reddet tabanı (MathHead interpret_natural)
V1   🟡 Bileşen ayrıştırma: tanım/niceleyici/önkoşul/örtük-varsayım/notasyon/hedef/temel  🟢 DETERMİNİSTİK DİLİM (statement_parse.py): motorun kendi ifade dizgeleri → niceleyici/alan-kısıtı/boyut-önkoşulu/ilişki/invariantlar (X2 eşanlam tablosuyla çözülür); LLM YOK, tahmin YOK — tanınmayan parça `unrecognized` olarak GÖRÜNÜR kalır; conjecture_db girişleriyle uyum testli; ADR-D0071
V2   🟡 Aday formalizasyonlar A/B/C + aralarındaki farkı gösterme ("A süreklilik, C yalnızca ölçülebilirlik varsayar")
V3   🟢 Formalizasyon testleri: bilinen örnek/karşı-örnek/sınır durumu ifadeyi doğru mu çürütüyor/doğruluyor?
V4   🟡 (LLM-periferi) makale/jargon → aday formal — yargıç + testler zorunlu
```

**Track X — Bilgi grafiği & etki analizi (§12)**
```
X0 🟡 Semantik şema: teorem/tanım/lemma/karşı-örnek/açık-problem + ilişkiler (generalizes, equivalent-under, invalidates)  🟢 knowledge_graph: tipli düğümler (theorem/law/conjecture/counterexample/axiom) + ilişkiler; from_report YALNIZ kesin kenarları kurar (depends_on kernel aksiyomlarından, refuted_by tanıktan, related_to ortak invariant); generalizes/equivalent_to şemada REZERVE ama tahmin edilmez (yargılı geçiş X3'e); Mermaid export; ADR-D0027
X1 🟡 İçe aktarım: OEIS, teorem kitaplıkları, makale meta — lisans/hukuk dahil  🟢 KISMİ: known_results kataloğu (OEIS A000041/A000009/A000088/A000110/A000142/A008277/A008292 + adlandırılmış teoremler) atıf temeli; tam korpus ingest açık; ADR-D0042
X2 🟢 Notasyon eşanlamlıları + teknik ↔ problem-yapısı eşlemesi
X3 🟡 Otomatik etki analizi: yeni sonuç hangi açık problemi çözer / sınırı iyileştirir / varsayımı kaldırır  🟢 impact.py: bilgi grafiği üzerinde KESİN yapısal analiz — load-bearing aksiyomlar (RESIDUE(m=2) 6 ispat taşır), hub'lar, açık-cephe (en dolanık çözülmemiş konjektürler); raporda özet; DÜRÜST: kendi bilgisi içinde etki (literatür ingest X1/W2 açık); ADR-D0028
```

**Track Y — Başarısızlık hafızası & negatif bilgi (§13)**
```
Y0 🟢 Denenen dönüşüm/kapanan-dal/timeout/işe-yaramaz-lemma/çürütülen-konjektür kaydı  ✅ (failure_memory: AttemptRecord + KINDS; raporda "negative knowledge" özeti; ADR-D0025)
Y1 🟡 Kanonikleştirme (aynı çıkmaz iki kez denenmesin — attempt fingerprint)  ✅ (fingerprint: whitespace-normalize + kind-aware içerik hash'i; record idempotent; seen(); ADR-D0025)
Y2 🟢 "Yeniden kullanılabilir ders" çıkarımı (family F için n yerine yapısal derinlikte tümevarım)  🟢 lessons(): çürütülen konjektürleri onları öldüren TANIK'a göre kümeler (en geniş refuter önce); yapısal-derinlik dersi gelecek tür; ADR-D0025
```

**Track AC — Araştırma direktörü & tam döngü (mimari)**
```
AC0 🟡 Hedef ayrıştırma + strateji seçimi (üst orkestratör)  🟢 director.ResearchDirector: her döngü sonrası impact (açık cephe) + merdiveni okuyup sıradaki hedefi seçer (en dolanık açık konjektürü çöz, yoksa sınırı genişlet); kural-tabanlı dürüst AC0; sadece DİKKAT'i seçer, DOĞRULUĞU değil; ADR-D0034
AC1 🟡 16-adımlı döngüyü bağla (formalize→örnek→sınır→invariant→konjektür→karşı-örnek→sırala→lema→ispat→sertifika→kernel→bağımsız→literatür→rapor)  🟢 İLK KAPALI DÖNGÜ (aritmetik alan): üret→önce-çürüt→İSPATLA uçtan uca (arithmetic.py; ADR-D0007)
AC2 🟢 Başarısızlıkta bile değerli çıktı (progress report: neyi çürüttük, neyi N'e kadar doğruladık, hangi lema açık)  ✅ (report.run_report: PROVED/REFUTED/DISCOVERED/OPEN + FRONTIER [χ/Hamilton değerleri solver_verified; frontier yasaları OPEN/REFUTED'a katıldı, taksonomi saf]; deterministik; ADR-D0008/D0020)
AC3 🟡 Döngüler-arası durum + uzun-soluklu araştırma oturumu  🟢 ResearchDirector döngüler-arası durum tutar: paylaşılan FailureMemory (parmak-izi dedup, çıkmazlar tekrar yürünmez), seen-set (yeni bulgular azalır: 51→3→0), döngü-başı merdiven anlık görüntüleri; run_session kendi önerisini takip eder; ADR-D0034
```

**Track AD — İnsan ortak-çalışma arayüzü (§16)**
```
AD0 ♻️🟢 Kontrol yüzeyi (MathHead MCP/profil tabanı): aksiyom yasakla, teknik önceliklendir, lemaya odaklan, ispat-stili seç
AD1   🟢 Kontrol-edilebilir karar gerekçesi (neden spektral yöntem? — CoT dökümü DEĞİL, denetlenebilir gerekçe)
AD2   🟢 İnsan-okunur ispat + araştırma raporu üretimi
AD3   🟡 Uzman-döngüde ilginçlik/onay geri bildirimi (Track W'ye besleme)
```

**Track AE — Alan örneklemesi: sonlu kombinatorik + graf (v0.1)**
```
AE0 🟢 v0.1 kapsamını sabitle (sonlu kombinatorik + grafik teorisi)  ✅ (kapsam sabitlendi VE yaşandı: 7 nesne alanının tamamı sonlu kombinatorik içinde — graf/aritmetik/permütasyon/bölüntü/küme-bölüntü/kompozisyon/küme-ailesi; kapsam dışına tek sapma yok)
AE1 🟢 Bu alanda N/O/P/Q/R'yi somut örnekle (grafik nesneleri, kromatik/spektral invariant'lar, sınır konjektürleri)
AE2 🟡 İLK HEDEF: bilinen bir sonuçtan literatürde OLMAYAN, doğru, ilginç ≥1 yeni lemma üret  🟢 DÜRÜST AV KURULDU ve ÇALIŞTIRILDI (candidate_hunt.py): geniş ağ (6 aile + tüm-graf örneklemi, tüm madenciler) → her bulgu kataloğa atıflandı → 40 bulgu, 36 atıflı, 4 "katalogda-yok" aday — DÖRDÜ DE ders-kitabı aile formülü çıktı (C_n: V=E; P_n/yıldız: V=E+1; tekerlek: 2V=E+2). SONUÇ: hedefin kendisi AÇIK; katalogda-yok ≠ literatürde-yeni birebir kanıtlandı; gerçek yenilik v2 programına (dış-onaylı kanallar: OEIS/karşı-örnek/Lean) devredildi; ADR-D0059
AE3 🟢 v0.1 çıktı sözleşmesi + provenance + Lean export  🟢 (rapor sözleşmesi + provenance uzun süredir tam; LEAN EXPORT artık VAR — lean_export.py 9 teorem, dış lake build beklemede; çapraz-referans v2C2/ADR-D0068)
```

**Track AF — Değerlendirme, benchmark & provenance**
```
AF0 ♻️🟢 Catch-rate + tool-selection tabanını genişlet (MathHead)
AF1   🟡 Keşif-oranı metriği: birim başına yeni/doğru/ilginç lemma; novelty-vs-literatür  🟢 evaluation.Scorecard: doğruluk (17/45 verified) + KNOWN sonuçlara atıf (%100 bilinen matematiğe eşlenir) + DÜRÜST novelty: 0 novel-to-literature (motor bilineni yeniden keşfediyor, keşif DEĞİL); raporda HONEST SCORECARD; tam novelty korpus ingest gerektirir (X1/W2, yapılmadı); ADR-D0035
AF2   🟢 Regresyon çitleri + deterministik replay (her keşif tekrar-üretilebilir)
AF3   🟡 İnsan değerlendirme paneli (ilginçlik ground-truth'u)
```

**Track AG — Altyapı: ölçek, determinizm, güvenlik, CI, docs**
```
AG0 ♻️🟢 Determinizm/seed/replay + provenance/hash (MathHead disiplinini genele taşı)
AG1   🟡 Dağıtık/paralel arama + iş kuyruğu + önbellek + artımlı hesap
AG2 ♻️🟢 Kaynak fençleri + güvenlik/threat-model (güvenilmez girdi, compute bütçesi)
AG3 ♻️🟢 CI matris/release + paketleme + sürümleme (kernel/DSL/contract)
AG4 ♻️🟢 Dokümantasyon + ADR disiplini + kod=docs
AG5   🟡 Gözlemlenebilirlik/metrikler + maliyet takibi
```

---

## v0.1'e giden kritik yol (en kısa omurga)

Belgenin kendi "nasıl başlardım"ıyla birebir. İlk gerçek keşif için 🔴 sınır işlerinin
HİÇBİRİNE gerek yok:

```
N (nesne+üretim) → O (invariant) → P0/P1 (konjektür) → Q0/Q1 (karşı-örnek) → R (durum+sertifika) → AE (grafik alanı)
        └── hepsi MathHead yargıç omurgası üzerinde (M0/R0/Q0/Q1/AF0/AG0 ♻️)
İLK HEDEF (AE2): "ünlü problemi çöz" DEĞİL → literatürde olmayan, doğru, ilginç ≥1 yeni lemma.
```

## Dürüst büyüklük okuması

```
Toplam: 22 track, ~103 aşama.
  ♻️ MathHead'den gelen/taban  : ~15 aşama  (bedavaya yakın — omurga kurulu)
  🟢 standart mühendislik       : ~55 aşama  (nasıl yapılacağı belli)
  🟡 zor/entegrasyon            : ~35 aşama  (emek ister, bilinir)
  🔴 araştırma sınırı           : ~13 aşama  (garantili çözümü YOK)
```

- **Tam ideal motor** = çok-yıllık, çok-kişilik bir araştırma programı. 🔴'lerin çoğu (Z tümü,
  U2, AB2/3, S4, W3, Q5/6, T1) bugün kimsenin tam çözemediği açık problemler. Bunları "bitiririz"
  diye söz vermek dürüstlük olmaz.
- **Ama v0.1** (yukarıdaki kritik yol) neredeyse tamamen 🟢/🟡 ve büyük kısmı MathHead üstünde.
  Yani ilk gerçek keşfe ulaşmak için sınırı çözmen GEREKMİYOR. Yola önce oradan çıkılır.
- 🔴'ler yolu tıkamaz; motorun "asistan"dan "kâşif"e terfi ettiği yerlerdir. Oraya vardığımızda
  zaten çok şey öğrenmiş oluruz — belki de asıl kıymet o öğrenmede.

---

## v2 EKİ — GERÇEK KEŞİF PROGRAMI (2026-07-30, kullanıcı onayıyla eklendi)

> Orijinal 103-aşamalık liste DONMUŞ ve yukarıda değişmeden durur (guard: 103 aşama / 21 track).
> Bu ek, dış-onaylı gerçek keşif hedefine giden kademeli programdır (ayrı guard: 16 v2 aşaması).
> **Dürüstlük çıpası:** yenilik yalnız DIŞ kanalla iddia edilir — OEIS hakem kabulü, kendini-doğrulayan
> karşı-örnek tanığı, Lean çekirdek onayı. Motor asla kendi kendine "yeni" demez (AE2 dersi: 40 bulgu →
> 4 "katalogda-yok" aday → dördü de ders-kitabı formülü. Katalogda-yok ≠ literatürde-yeni).
> Stratejik teşhis: gerçek keşif küçük nesnelerin yasalarında değil, ÜSTEL SAMANLIKLARDA yaşar
> (belirli tanık / formül / yapı — emsal: Wagner 2021 karşı-örnekleri, FunSearch cap-set, BBP/PSLQ,
> Heule SAT, Graffiti, Ramanujan Machine).

**Kademe 1 — dış-onaylı ilk keşif şansı (bu makinede yapılabilir)**
```
v2A0 🟢 OEIS erişim katmanı: sorgu-bazlı eşleştirici (API/yerel döküm; lisans + atıf) — oeis_radar.LOCAL_CORPUS: kod-tabanında pinli + su-götürmez klasik prefix'ler; ≥5-terim örtüşme koşulu (çöp eşleşemez); runtime dış sorgu YOK (oeis.org robots.txt otomasyonu engelliyor — saygı gösteriyoruz, aşmıyoruz): eşleşmeyen = pending_external_lookup, İNSAN-halkalı çözüm; ADR-D0061
v2A1 ✅ Doğal aile → sayma dizisi üreticisi (6 alandan sistematik dizi çıkarımı) — extract_natural_sequences: 11 dizi MOTORUN KENDİ üreticilerinden hesaplanır (asla hardcode değil): 6 alan toplamı + rafine aileler (bağlantılı graflar A001349, derangement A000166, involusyon A000085, üçgensiz, χ=3); 9'u OEIS pinine birebir oturdu; ADR-D0061
v2A2 🟢 OEIS radarı: eşleşmeyen doğal dizi tespiti → insan-onaylı gönderim dosyası (kabul = dış-onaylı keşif) — radar(): matched(9, A-numaralı) / pending(2: üçgensiz 1,1,2,3,7,14,38; χ=3 0,0,0,1,3,16,84) ayrımı; protokol AÇIK: dış OEIS sorgusu → yoksa insan-onaylı gönderim → hakem kabulü = keşif, öncesi hiçbir şey; pending asla keşif diye sunulmaz; ADR-D0061
v2A3 ✅ PSLQ sabit-formül avı (mpmath.pslq): iki-hassasiyet protokolü, gürültü reddi, numerical_conjecture statüsü — pslq_hunt.py: 60 hanede keşif → 220 hanede sıfırdan yeniden-doğrulama (ikinci kapıda ölmeyen kalır); kalibrasyon: 6ζ(2)=π², 90ζ(4)=π⁴, √2→x²−2, φ→x²−x−1 yeniden-keşfedildi (residual~10⁻²²⁰); e-π, γ-ln2, gürültü-sabiti, π-cebirsel DÜRÜSTÇE None; statü asla proved değil; ADR-D0060
v2A4 ✅ nauty/geng ölçek entegrasyonu (n~20-30) + hızlı invariant yolu — nauty_scale.py (nauty 2.8.8): tam sayım n=10'a dek (12M sınıf, A000088 birebir devam), nesne-enumerasyonu n≈9 (274k); KÖR GÜVEN YOK — geng çıktısı saf-Python üreticiyle SINIF-SINIF çapraz-doğrulandı (n≤5 kanonik-anahtar kümeleri eşit, n=6 sayı eşit) + üçgensiz sayımlar motorun bağımsız hesabıyla üçüncü yoldan birebir; graph6 decoder round-trip; -c/-t/-b filtreli sınıflar radar'ın bekleyen prefix'lerini 10 terime uzattı (üçgensiz ...107,410,1897); hard_cap sessiz kesme yerine REDDEDER; ADR-D0062
v2A5 🟡 Zengin invariant kütüphanesi (independence, domination, girth, diameter, matching, energy, spectral radius)
```

**Kademe 2 — karşı-örnek avcısı (en kısa yol → yayınlanabilir sonuç)**
```
v2B0 ✅ Açık-konjektür veritabanı (küratörlü ingest; kaynak + durum + sınanabilir form) — conjecture_db.py: her giriş 4 savunmalı (verbatim ifade + alan kısıtı; dürüst statü refuted_in_literature/open; KÜÇÜK-n FORMALİZASYON ZIRHI — literatürün 'tutuyor' dediği aralıkta tükenmeli doğrulama, ihlal = BİZİM ifademiz yanlış demek; kesin certify — verdictte float yasak); 3 giriş: A–H spektral-eşleşme (transkripsiyon-kaydı: insan kaynak-kontrolü arXiv:2104.14516'da), χ≤Δ, conn⟹Ham; ADR-D0064
v2B1 ✅ Adaptif arama çekirdeği (tavlama/evrimsel; deterministik tohumlu) — adaptive_search.py: tohumlu SA bağlı-graf uzayında (kenar-toggle, bağlılık korunur) + AĞAÇ-uzayı rewire varyantı (döngü-kenarı değişimi); ağaç-ν lineer kesin DP (300 rastgele ağaçta genel kesin ν ile birebir); float skor YÖNLENDİRİR, tamsayı sertifika KARAR VERİR; float_candidate_uncertified / not_found_within_budget dürüst statüler; ADR-D0064
v2B2 ✅ Kalibrasyon: bilinen-çürütülmüş konjektürlerin tanıklarını YENİDEN bul (Wagner seti) — BAŞARILDI: transkribe A–H ifadesi n=18'den itibaren SERTİFİKALI tanıklarla çürütüldü (en küçük: D(7,8)+orta-köşe n=18; n=19 dengeli D(8,8)+orta = Wagner'ın RL tanığının TARİF EDİLEN ŞEKLİ 'merkezleri yolla birleşik iki dengeli yıldız'); her verdict saf-TAMSAYI sertifika (Bareiss-Sylvester λ₁<p/q + tamsayı kare testi, floatsız); İKİ eşitlik ailesi motor-sertifikalı: yıldızlar + D(12,12) n=26 (λ₁=4 TAM); smoke kademesi (χ≤Δ→K4, conn⟹Ham→ağaç) anında; YENİDEN-KEŞİF olarak etiketli, dış iddia öncesi insan kaynak-kontrolü şart; ADR-D0064
v2B3 🟡 Canlı av: açık konjektürlerde tanık araması (tanık kendini doğrular — dürüstlük içkin)
```

**Kademe 3 — konjektür servisi + cephe**
```
v2C0 ✅ Keskinlik-tespitli konjektür servisi (Graffiti-tarzı; W0 novelty filtreli; insanlara yayın) — conjecture_service.py: zengin kütük (α,γ,ν,girth,diam,radius) + klasikler üzerinde A≤B / A≤B+c / A≤2B formları, tüm bağlı graflarda counterexample-first (142 graf, 330 aday → 74 survivor); KESKİNLİK sıralaması (eşitliğe ulaşan graf sayısı + en küçük eşitlik tanığı): ω≤χ 138-keskin (mükemmel graflar), diameter≤2·radius, Ore γ≤α, γ≤ν; baskılanan offset-formlar düşürülür; her madde empirical + 'bilinen-sonuç, insanlara saldırı listesi' kaydı; ADR-D0066
v2C1 ✅ SAT cephesi: Ramsey-tipi sonlu problem kodlayıcıları (pysat üstüne; DRAT ispat-log hedefi) — ramsey_sat.py: K_n 2-boyama CNF (kırmızı K_s yok + mavi K_t yok); R(3,3)=6, R(3,4)=9, R(3,5)=14 ve R(4,4)=18 MOTOR TARAFINDAN BRACKETLENDİ — DÖRT klasik küçük Ramsey sayısının tamamı; R(3,5)>13 ve R(4,4)>17 bağımsız-doğrulı tanıklarla, UNSAT tarafları TÜRETİLMİŞ derece-lemmalarıyla (kırmızı-derece≤t−1 öz-yeterli; mavi/kırmızı-derece≤8 = MOTORUN KENDİ R(3,4)=9 bracket'ine atıfla — kendi sonucunu lemma olarak kullanan zincir, solver_verified_with_derived_lemmas etiketiyle dürüst); DÜRÜSTLÜK KATMANLARI AYRI: SAT tanığı KABA KUVVETLE bağımsız yeniden-doğrulanır (independently_verified_witness; solver yalan söylerse verdict REDDEDİLİR), UNSAT solver_verified kalır (kernel-seviye UNSAT için DRAT loglama = kayıtlı sonraki adım, iddia edilmedi); flip aralık dışındaysa değer İDDİA EDİLMEZ; ADR-D0067
v2C2 🟢 Lean 4 / mathlib köprüsü: kernel ispat exportu + "bilinen mi?" kâhini (M6'yı kapsar) — lean_export.py: kernel'in 7 Divides teoremi + kimlikler Lean 4'e çevrildi (docs/discovery/lean/MathheadKernel.lean, 9 teorem); TEORİK KÖPRÜ TAM: RESIDUE kuralımız ≡ Lean'ın ZMod m üzerinde decide'ı (sonlu tip, Lean çekirdeği aynı taramayı yapar) + ZMod.intCast_zmod_eq_zero_iff_dvd ile ∀n:ℤ'ye taşınır; PolyIdentity ≡ ring; DÜRÜST: export_written_pending_external_check — Lean+mathlib konteynerde derlenemez, lake build = insan/CI adımı, o koşana dek hiçbir teorem Lean-verified SAYILMAZ (✅ değil 🟢 bu yüzden); ADR-D0068
```

**Kademe 4 — Alpha Centauri (🔴 araştırma ufku; fizik yasası yasaklamıyor, yol haritası bilinmiyor)**
```
v2D0 🔴 Program-uzayı yapı arayıcı (FunSearch-tarzı; büyük hesap ister)
v2D1 🔴 Otoformalizasyon döngüsü (kaynak → tanım/konjektür → saldırı → geri-besleme)
v2D2 🔴 Yeni tanım üretimi (Track Z'nin v2 hali; matematiksel ZEVK problemi — kimse çözmedi)
```

---

## v3 EKİ — ÜRÜN PROGRAMI (2026-07-30, kullanıcı hedefi: "matematikçilerin kullanmak isteyeceği ürün")

> DONE kriteri (ölçülebilir): repo'yu bulan bir matematikçi 10 dakika içinde — kurar (`pip install`),
> 3 gerçek kontrol koşar (tanıklı bir refütasyon + bir kernel ispatı + bir Ramsey bracket), dürüstlük
> sözleşmesini okur ve atıf verir. Hepsi CI'da çalışan örnek-testlerle KANITLI. Konumlandırma:
> **"Konjektürünü getir — çürüteyim, ispatlayayım, ya da tam olarak nereye kadar dayandığını söyleyeyim."**
> Pazar farkı: hiçbir araç verdict başına EPİSTEMİK KADEME vermiyor; bizim dürüstlük sözleşmemiz ürünün ruhu.

```
v3P0 ✅ Ürün çekirdeği: check() tek-kapı API — ifade → yapı sınıflandırma → enstrüman → dürüst verdict zarfı — product.py: modüler (kernel ispat / kesin kalıntı-tanığıyla refütasyon), toplam-kimliği (SumInduction / en-küçük-n tanığı), graf-sınırı (counterexample-first, bağlı graflar; en-küçük tanık ör. T≤E → n=6, 16>14; survivor dürüstçe OPEN); tanınmayan girdi 'unsupported' + enstrüman önerisi — ASLA tahmin yok; 7 quickstart-testi CI'da; ADR-D0072
v3P1 ✅ CLI: mathhead-discover check/bracket/hunt/report komutları — discovery/cli.py + pyproject entry-point; her verdict epistemik kademesiyle basılır, lemmalar verdict üstünde listelenir, --json makine-okur çıktı; 5 CLI testi CI'da; v1 CLI yüzeyine (donmuş MCP router) SIFIR dokunuş; ADR-D0073
v3P2 ✅ README ürün-sınıfı yeniden yazım (30-saniye değer önermesi + 3 canlı örnek + kademe tablosu) — hero: 'Konjektürünü getir…' + 3 gerçek konsol örneği (kernel ispat, n=6 tanıklı refütasyon, R(3,5)=14 bracket) + 7-katmanlı dürüstlük-kademe tablosu + 'bugün yapabildikleri' (her iddia CI-testli); mevcut MCP-core içeriği korunarak altta; ADR-D0073
v3P3 ✅ Docs sitesi (mkdocs-material): quickstart + 5 işlenmiş örnek + API referans + DÜRÜSTLÜK SÖZLEŞMESİ sayfası — mkdocs.yml + docs/manual/{index,quickstart,honesty,examples,api}.md; sözleşme sayfası 10-katman kademe tablosu + '0 novel-to-literature' gerçeğini AÇIKÇA yazar; mkdocs build yerelde doğrulandı; ADR-D0074
v3P4 ✅ Örnek galerisi = çalıştırılabilir testler (docs çürüyemez; CI koşar) — tests/test_docs_examples.py: quickstart üçlüsü CLI'dan BİREBİR belgedeki çıktıyla koşar, örnek 1-3 doğrulanır, honesty sayfasının motorun yaydığı HER kademeyi listelediği test edilir; ADR-D0074
v3P5 ✅ Sitabilite: CITATION.cff + whitepaper taslağı (yöntem + dürüst değerlendirme bölümü) — CITATION.cff (v1.1.0, yazar, abstract) + docs/manual/whitepaper.md (kernel/enstrümanlar/sonuçlar/SINIRLILIKLAR AÇIKÇA: 'her şey yeniden-keşif; yenilik iddia edilmiyor'); nav'a eklendi; ADR-D0075
v3P6 ✅ Sürüm cilası: CHANGELOG + semver v1.1.0 + pip extras denetimi — 1.0.1→1.1.0 (yalnız EK yüzeyler, semver minor); CHANGELOG 1.1.0 bölümü ürün-özeti + Honesty alt-başlığıyla; DÜRÜSTLÜK YAKALAMASI: paket PyPI'DA YOK — README/quickstart git-install'a çevrildi (yalan talimat düzeltildi), PyPI yayını kullanıcının release adımı; ADR-D0075
v3P7 🟢 GitHub Pages docs deploy CI + repo vitrini (badges, topics) — .github/workflows/docs.yml (mkdocs gh-deploy, main push'ta); İLK deploy repo ayarında Pages'in gh-pages branch'e açılmasını ister (insan adımı, kayıtlı); ADR-D0075
v3P8 ✅ Topluluk yüzeyi: issue şablonları + CONTRIBUTING + "conjecture wanted" şablonu — conjecture_wanted.md (ifade formları + dürüst-atıf alanı), bug_report.md ('kademe kanıtı abartıyorsa = en yüksek-öncelik bug sınıfı'), CONTRIBUTING.md (dürüstlük kuralları = katkı kuralları); ADR-D0075
```

---

## v4 EKİ — MAKSİMUM FONKSİYONELLİK SPRİNTİ (2026-08-05, kullanıcı: "release'i boşver; hedef maksimum fonksiyonellik; sonuna kadar git")

> TASARIM İLKESİ (v1'den alınan ders): "sonuna kadar gitmek" bir irade ayarı değil, PLAN TASARIMIDIR.
> v1'in 103/103 kapanamamasının nedeni 12 🔴 açık-araştırma fazıdır (dürüstçe bitirilemez). Bu v4 planı
> BİLEREK yalnızca konteyner-içi TAMAMLANABİLİR fazlardan oluşur: her fazın ölçülebilir DONE ölçütü var,
> son faz bir FİNAL DENETİMdir (rakip-plan disiplini). Bu plana "sonuna kadar" gidilir ve gidilecektir.
>
> ÇALIŞMA DİSİPLİNİ — İKİLİ AJAN DÖNGÜSÜ (kullanıcı talebi): her faz iki ayrı ajanla koşar:
>   Ajan-2 IMPLEMENTER (uygular, test yazar) → Ajan-1 MENTOR/TESTER/EVALUATOR (düşmanca dener: kırmaya
>   çalışır, kademe-abartısı arar, DONE ölçütünü kanıta karşı denetler) → FAIL ise bulgular implementer'a
>   geri döner (döngü) → PASS ise orkestratör tam suite + commit + tracker günceller.
>   Protokol: docs/discovery/AGENT-PROTOCOL.md

```
v4F0 ⬜ RUP/DRAT UNSAT sertifikası → Ramsey: UNSAT verdiktleri çözücü-sözüne değil BAĞIMSIZ kontrol edilen çürütme-ispatına dayansın — J2'nin DRUP/RUP altyapısı ramsey_sat'a bağlanır; DONE: R(3,3)≤6 ve R(3,4)≤9 UNSAT'ları motor-içi bağımsız RUP kontrolünden geçer, yeni dürüstlük kademesi verdikte görünür; lemmalı koşularda ispatın GÜÇLENDİRİLMİŞ formüle ait olduğu dürüstçe etiketlenir; testler CI'da
v4F1 ⬜ check() kapsama dalgası 1 (aynı domainlerde derinlik): polinom kongrüansları p(n) ≡ q(n) (mod m), graf-sınırında >= yönü ve invA == invB eşitlik iddiaları, karşılaştırmalı toplam-eşitsizlikleri; DONE: en az 3 yeni ifade formu proved/refuted/open yollarıyla tek kapıdan geçer, quickstart+docs örnekleri güncellenir, testler CI'da
v4F2 ⬜ check() kapsama dalgası 2 (yeni domainler tek kapıya): permütasyon ve partisyon iddiaları ("all perms of n: inv <= n(n-1)/2" tarzı sınırlar, sayım kimlikleri) mevcut domain motorlarına yönlendirilir; DONE: en az 2 yeni domain check()'ten tanık/ispatla erişilir, unsupported-mesajları yeni kapsamı bilir, testler CI'da
v4F3 ⬜ Sertleştirme süpürmesi A: dokunulmuş-kısmi fazların ilk yarısı (M/Q/R/S/N/O kümeleri) tam ✅'a — her biri için eksik listesi çıkarılır, kapatılır, kanıt testi eklenir; DONE: hedef listedeki her faz ya ✅ ya da kapanamama nedeni tek cümleyle roadmap'e işlenmiş
v4F4 ⬜ Sertleştirme süpürmesi B: ikinci yarı (P/T/U/W/X/AA/AC kümeleri) aynı disiplinle; DONE: aynı ölçüt
v4F5 ⬜ Ölçek koşuları: geng n=8 bağlı-graf invariant süpürmesi konjektür servisine; R(3,6)=18 denemesi (türetilmiş derece-lemmaları: kırmızı≤5, mavi≤R(3,5)−1=13 — motorun KENDİ bracket'i, öz-referanslı zincir büyür); Frankl büyük bütçe; DONE: her koşu dürüst kademeyle kayıtlı, zaman-aşımı asla sonuç gibi yazılmaz
v4F6 ⬜ Bilgi-grafı derinliği: X0 generalizes/specializes kenarları P2 genellemesinden beslenir + kalan derinlik kalemleri (T3 ispat-ağacı boşlukları); DONE: kenarlar sorgulanabilir + testli
v4F7 ⬜ FİNAL DENETİM (rakip-plan disiplini): evaluator-ajan v4F0..F6'nın HER DONE ölçütünü kanıta karşı denetler; kapanamayan varsa dürüstçe listelenir; v1.2.0 sürüm + CHANGELOG; DONE: denetim raporu docs'ta, tam suite yeşil, tracker'lar senkron
```
