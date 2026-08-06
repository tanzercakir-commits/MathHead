# v4 Sprint FİNAL DENETİM Raporu (v4F7)

- **Tarih:** 2026-08-06
- **Denetçi:** Ajan-1 (final auditor — MENTOR/TESTER/EVALUATOR, ikili-ajan protokolü:
  `docs/discovery/AGENT-PROTOCOL.md`)
- **Denetlenen:** v4F0..v4F6 (roadmap "v4 EKİ" bölümü, `docs/IDEAL-ENGINE-ROADMAP.md` 356–378)
- **Repo durumu:** HEAD `5e599d0`, çalışma ağacı temiz
- **Yöntem:** her fazın DONE ölçütü maddelere ayrıldı; her madde BAĞIMSIZ kanıtla işaretlendi
  (testler yeniden koşuldu, kritik iddialar motor-dışı spot-check ve düşmanca saldırıyla doğrulandı).
  Bu rapor yalnız bulunan kanıtı yazar; bulunamayan kanıt "bulunamadı" olarak işaretlenir.

---

## v4F0 — RUP/DRAT UNSAT sertifikası → Ramsey — **CLOSED**

| DONE maddesi | Durum | Kanıt (bu denetimde üretildi) |
|---|---|---|
| `rup_check.py` saf-Python, çözücü importsuz | ✓ | Dosyanın tüm import'ları: `__future__`, `dataclasses` — pysat/z3 yok (grep ile doğrulandı) |
| `ramsey_decide(certify_unsat=True)` → `independently_verified_unsat_proof` | ✓ | Spot-check: `ramsey_decide(6,3,3)` → `certainty='independently_verified_unsat_proof'`, `unsat_proof_checked=True`, 29 lemma RUP-kontrollü, 0.021 s |
| Lemmalı koşuda kademe adı `..._of_strengthened_formula` | ✓ | Spot-check: `ramsey_decide(14,3,5,strengthen=True)` ve `(18,4,4,strengthen=True)` → `independently_verified_unsat_proof_of_strengthened_formula`, her ikisi <0.1 s |
| Kontrol geçmezse kademe YÜKSELMEZ (geri-düşüş + not, testli) | ✓ | `test_failed_check_falls_back_honestly_never_upgrading` (monkeypatch'li) — koşuldu, geçti |
| Zaman iddiaları: R(3,3)@6 ~0.01s, R(3,4)@9 ~5.4s | ✓ | Yeniden ölçüldü: 0.021 s ve 4.38 s (aynı mertebe) |
| Negatif testler: sahte/kesik ispat → refuted; bütçe → budget_exceeded | ✓ | `test_tampered_proof_is_rejected`, `test_truncated_proof_is_rejected`, `test_proof_for_the_wrong_formula_is_rejected`, `test_exhausted_budget_is_neither_verified_nor_refuted` — hepsi geçti (25/25, `test_discovery_rup_check.py` + `test_discovery_ramsey_sat.py`) |
| J2 çapraz-doğrulama + diferansiyel fuzz | ✓ | `test_cross_checked_by_the_j2_drat_checker`, `test_differential_agreement_with_the_j2_checker_on_random_cnfs` — geçti |
| honesty.md + README + CLI güncel | ✓ | honesty.md satır 21–22 iki yeni kademe; README satır 23/43; CLI `prove-unsat` + `check-unsat-proof` alt-komutları (`src/mathhead/cli.py` 226–231) |
| Fuzzer'ın 3. gerçek bug'ı düzeltildi, 7 landmine kalıcı | ✓ | `tests/test_fuzz.py` LANDMINES listesi tam 7 dizgi (`implies(0,0)` dahil); `test_landmine_strings_are_all_clean_errors_or_results` geçti (4/4) |
| İkili-ajan gate izi | ✓ | PROGRESS 2026-08-05 v4F0 girişi: evaluator 2×PASS, 400-CNF düşmanca fuzz 0 sahte "verified" |

## v4F1 — check() kapsama dalgası 1 — **CLOSED**

| DONE maddesi | Durum | Kanıt |
|---|---|---|
| En az 3 yeni ifade formu tek kapıdan | ✓ | Kongrüans + graf >=/== + sum-eşitsizliği: üçü de `check()` üzerinden (37/37 test, `test_discovery_product_v4f1.py` + `test_discovery_congruence.py`) |
| Kongrüans proved/refuted yolları | ✓ | Spot-check: `n^2+n ≡ 0 (mod 2)` → proved/`kernel_verified` (proof_hash `0b5a07c36f79d3bf`, m\|(p−q) indirgemesi notta); `n^2+1 ≡ 0 (mod 3)` → refuted/`exact_integer_certificate`, kendi-doğrular kalıntı tanığı `{n:0, lhs_mod_m:1, rhs_mod_m:0}` |
| Graf >= aynası + == eşitlik; sonlu tarama ASLA proved demez | ✓ | `test_graph_equality_handshake_is_open_never_proved` (sum_degrees==2\|E\| bile open kalır) — pin testi geçti |
| Sum-eşitsizliği kernel+z3 zinciri, proved=solver_verified (en zayıf halka) | ✓ | Spot-check: `sum_(i=1..n) i <= n^2` → proved/`solver_verified`, notta "closed form kernel_verified; inequality step z3"; `>= n^2` → refuted/`exact_integer_certificate`, tanık {n:2, 3<4} |
| z3 reel modeli yalnız İPUCU; tamsayıysa exact yeniden-doğrulama, değilse open | ✓ | `test_sum_z3_integer_hint_is_upgraded_only_after_exact_reverification` (n=201, doğrudan exact toplama) + `test_sum_non_integer_real_counterexample_stays_open` — geçti |
| 3 eski unsound davranış kapandı | ✓ | Spot-check: `2 \| n/2`, `0 \| n`, `6 \| x^3-x` üçü de artık `unsupported` (sahte proved / çökme yok) |
| Büyük-m reddi (10^6) | ✓ | `test_huge_modulus_is_an_honest_refusal_not_a_hang` — geçti |
| quickstart+docs örnekleri güncel | ✓ | `docs/manual/quickstart.md` satır 29/34/41 yeni formların örnekleri; `test_docs_examples.py` 13/13 geçti |
| İkili-ajan gate izi | ✓ | PROGRESS v4F1 girişi: evaluator PASS + davranış-değişikliği yaması açıkça ONAYLI |

## v4F2 — check() kapsama dalgası 2 (perm/partisyon/kompozisyon) — **CLOSED**

| DONE maddesi | Durum | Kanıt |
|---|---|---|
| Permütasyon sınırları S_n≤7, one-line tanık, exact refütasyon | ✓ | Spot-check: `all perms of n: descents <= fixed_points` → refuted/`exact_integer_certificate`, tanık `{n:2, perm:[1,0], descents:1, fixed_points:0}`; n-tavanı testi `test_perm_max_n_shrinks_and_the_factorial_wall_is_honest` geçti |
| Sonlu tarama ASLA proved demez | ✓ | `test_perm_true_bound_is_open_never_proved` — geçti |
| Partisyon kimlikleri n≤20, Glaisher HER çağrıda CANLI yeniden-doğrulanır (bayrak okuma yok) | ✓ | Kod: `product.py` 600–606 `certify_euler_bijection` çağrısı route içinde; DENETÇİ SALDIRISI: `certify_euler_bijection` bozuk sahteyle monkeypatch'lendi → Glaisher notu ve enstrümanı KAYBOLDU, verdict dürüstçe open kaldı — canlı doğrulama teyitli |
| Kademe dürüstçe `no_counterexample_within_bound` + "universal step not machine-checked" notu | ✓ | Spot-check çıktısı notu birebir taşıyor; `test_partition_euler_identity_open_with_glaisher_note_and_exact_tier` geçti |
| Kompozisyon kimlikleri n≤12, cut-point bijeksiyonu in-route | ✓ | Spot-check: `compositions(n) == 2^(n-1)` → open/`no_counterexample_within_bound` + cut-point notu |
| Dev-sabit guard'ı (4000 basamak, 3 katman) | ✓ | v4f2 test dosyasında 4000-digit testleri (satır 222–239) — 59/59 geçti (v4f2+perm+partition+composition dosyaları) |
| pi-RHS dürüst red, num_cycles alias | ✓ | `test_..._pi` (refuting-with-pi reddi) + `test_perm_num_cycles_alias_is_accepted_and_documented` — geçti |
| İkili-ajan gate izi | ✓ | PROGRESS v4F2 girişi: evaluator PASS, tanıklar motor-dışı yeniden hesaplandı, monkeypatch saldırısı kayıtlı |

## v4F3 — Sertleştirme süpürmesi A (M/Q/R/S/N/O) — **CLOSED**

| DONE maddesi | Durum | Kanıt |
|---|---|---|
| Hedef listedeki her faz ya ✅ ya tek-cümle neden roadmap'te | ✓ | 14 aday satırı roadmap'te v4F3 anotasyonlu (M0,M1,M2,M3,M5,M6,M7,Q1,Q3,R1,S0,S1,S2,S3; N/O zaten tamdı): 8 kapanış + 6 tek-cümle neden (M3 dil/ekip-kanadı Lean ister, M6 Lean toolchain konteynerde derlenemez, Q1/Q3/R1/S1 ayrı-enstrüman) — satır satır grep ile doğrulandı |
| 8 kapanış kanıt-testli | ✓ | `test_discovery_hardening_v4f3.py` 9 test (M0/M1/M2/M3-kapsam/M5/M7/S0/S2/S3) — 9/9 geçti |
| Done-sayacı faz-çıpalı | ✓ | `scripts/gen_status.py` satır 48: prose/header/v2+ satırındaki ✅ ASLA sayılmaz; `test_trackers.py` 6/6 geçti |
| kernel.check KernelError'a totalleştirildi, portföy negatif-bütçe reddi | ✓ | v4f3 test dosyası + tam suite içinde geçti; roadmap M2/S2 satırlarında kayıtlı |
| İkili-ajan gate izi | ✓ | PROGRESS v4F3 girişi: evaluator kendi forge/yan-koşul/bütçe saldırılarıyla (subclass forgery, TOCTOU, CRT nesting — hiçbiri mint edemedi) PASS |

## v4F4 — Sertleştirme süpürmesi B (P/T/U/W/X/AA/AC) — **CLOSED**

| DONE maddesi | Durum | Kanıt |
|---|---|---|
| 20 aday = 11 kapanış + 9 dürüst neden | ✓ | Roadmap'te 20 satır v4F4 anotasyonlu (grep ile sayıldı): kapanışlar P5/T0/T2/U0/U3/W1/X2/AA3/AA4/AC0/AC3, nedenler P2/P3/P6/U1/W2/X0/X1/X3/AC1 — 11+9=20 birebir |
| 11 kapanış kanıt-testli | ✓ | `test_discovery_hardening_v4f4.py` tam 11 test, adları kapanışlarla 1:1 eşleşiyor — 11/11 geçti |
| AA4 certainty='unproven' düzeltmesi | ✓ | `test_aa4_algorithm_proof_bridge_never_inflates_modality` geçti |
| X0 bilerek v4F6'ya ertelendi | ✓ | Roadmap X0 satırı hem v4F4 erteleme notunu hem v4F6 kapanış notunu taşıyor — tutarlı |
| İkili-ajan gate izi (6/6 mutasyon) | ✓ | PROGRESS v4F4 girişi: evaluator 6/6 mutasyon bataryası (kaynak geçici bozuldu, her mutasyon yeni testlerce yakalandı — testler kodu pinliyor, aritmetiği değil), kozmetik-test avı temiz, PASS |

## v4F5 — Ölçek koşuları — **CLOSED**

| DONE maddesi | Durum | Kanıt |
|---|---|---|
| Her koşu dürüst kademeyle SCALE-RUNS.md'de kayıtlı | ✓ | 3 koşu da kayıtlı: geng n=8 (`empirical` + kesin tanıklar), R(3,6) (2a `independently_verified_witness`, 2b KADEME YOK), Frankl (`not_found_within_budget`) |
| geng n=8 sayı tutarlılığı | ✓ | 853 (n=7) + 11 117 (n=8) A001349 ile birebir; 74 = 60 hayatta + 14 refüte; 60+2 dirilen = 62 survivor; toplam 12 112 = Σ bağlı graf (2≤n≤8) — hepsi aritmetik olarak doğrulandı |
| 14 refütasyon tanığı makine-okunur | ✓ | 14/14 graph6+kenar-listesiyle kayıtta; DENETÇİ SPOT-CHECK: `G?bDKk` kenar listesinden γ ve diam motor-dışı yeniden hesaplandı → γ=4 > diam=3, refütasyon teyitli |
| R(3,6)>17 tanıklı | ✓ | Koşu 2a: n=17 SAT 0.1 s, kaba-kuvvet bağımsız doğrulama, `independently_verified_witness` |
| Zaman-aşımı ASLA sonuç gibi yazılmadı (R(3,6) sızıntı grep'i) | ✓ | Repo-geneli grep `R(3,6)(=\|<=\|≤)18`: yalnız SCALE-RUNS başlığı ("denemesi"), açık NEGATİF kayıt ("bracket'e EKLENMEDİ"), ve PROGRESS'in sızıntı-kontrolü notu; `src/` içinde sıfır iddia; `_OWN_BRACKETS` tablosunda (3,6) girdisi YOK |
| Mavi≤13 lemması _OWN_BRACKETS'tan türetiliyor | ✓ | `ramsey_sat.py` 44–48 tablo {(3,3):6,(3,4):9,(3,5):14} + 97–101 türetme; `test_r36_degree_lemmas_derive_the_right_bounds` + çıpa regresyonu geçti |
| Frankl dürüst duvarlar; m=5 exhaustive reddi + guard_sampled "proves NOTHING" | ✓ | SCALE-RUNS Koşu 3 kaydı + `test_exhaustive_guard_refuses_m5_*` / `test_sampled_guard_is_deterministic_*` geçti (`test_discovery_frankl.py`, 26/26 F5 test bloku) |
| ruff==0.15.11 pinlendi | ✓ | `pyproject.toml` satır 41 + `constraints.txt` satır 10; aktif `ruff --version` = 0.15.11 |
| İkili-ajan gate izi | ✓ | PROGRESS v4F5 girişi: geng sayıları bağımsız, 5/5 tanık motor-dışı, t=6 lemma-sağlamlık hükmü SAĞLAM, PASS |

## v4F6 — Bilgi-grafı derinliği — **CLOSED**

| DONE maddesi | Durum | Kanıt |
|---|---|---|
| generalizes/specializes kenarları P2'den doğar (from_report otomatik) | ✓ | Spot-check: `from_report(run_report(max_n=5))` → tam 5 generalizes + 5 specializes kenarı, tek P2 yasa düğümü |
| Kenarlar SORGULANABİLİR + testli (DONE'un çekirdeği) | ✓ | Spot-check: `generalizations_of` / `specializations_of` iki yönde tutarlı; `test_generalization_edges_are_queryable_in_both_directions` dahil 36/36 test geçti (kg+proof_tree+impact dosyaları) |
| Yasa düğümü attr'ları dürüst (instance=kernel_verified, universal=structural_argument) | ✓ | Spot-check çıktısı birebir: `{'instance_status':'kernel_verified','universal_status':'structural_argument'}`; ∀k hiçbir yerde makine-ispatı diye yazılmıyor |
| Epistemik kelepçe: şişik kademeli yasa ValueError | ✓ | `test_inflated_universal_status_is_clamped_with_a_loud_error` — geçti |
| n⁵−n / n⁷−n dürüst kenarsız | ✓ | `test_p2_decline_yields_no_edge_honestly` — geçti |
| generalization_impact graftan hesaplanır | ✓ | Spot-check çıktısı: "all instances keep their own kernel proofs (independent depends_on support); only the common explanation is lost", 5/5 bağımsız-ispatlı örnek |
| T3 PROOF_TREE_COVERAGE totalliği + tree_or_reason | ✓ | Spot-check: `tree_or_reason('solver_verified')` dürüst gerekçe döndürür; bilinmeyen kademe (`made_up_tier`) → LOUD KeyError; canlı-denetim testi `test_discovery_proof_tree.py` geçti |
| Sum-identity kademe-DEFLASYONU düzeltmesi (→ formal_proof) | ✓ | Spot-check: raporun proved bulguları {formal_proof:8, kernel_identity:6, exhaustive_residue_proof:3} — `sum_(i=1..n) i = n(n+1)/2` vb. artık `formal_proof`; solver_verified sızıntısı yok; honesty.md satır 18 kademeyi tanımlıyor |
| İkili-ajan gate izi | ✓ | PROGRESS v4F6 girişi: sahte-genelleme sabotajı kelepçeye takıldı, kernel sabotajında 0 kenar, PASS |

---

## GENEL KAPILAR

| Kapı | Sonuç |
|---|---|
| Tam suite (`pytest tests/ -q`) | **1969 passed, 0 failed** (129 s) — beklenen 1969 ile birebir |
| ruff (pinli 0.15.11) | `All checks passed!` — aktif binary 0.15.11 (pin `pyproject.toml`+`constraints.txt`); NOT: ortamda ayrıca bir pip-görünür ruff 0.16.0 var, kapı bilinçli olarak 0.15.11'de (0.16 lint borcu bilinen sınır) |
| `python scripts/gen_status.py --check` | `tracker check OK: 103 phases · 21 tracks · v2 16 · v3 9 · v4 8 · sample fresh` (rc=0); `V4_PHASES_EXPECTED=8` guard'ı yerinde, `test_trackers.py` 6/6 |
| git log (7 faz commit'i) | ✓ 7/7: `e1b22b6` (F0), `e8355ff` (F1), `c7959ae` (F2), `c24ebd5` (F3), `8596101` (F4), `76c2c1b` (F5), `5e599d0` (F6) + plan commit'i `da655f2` |

## DÜRÜSTLÜK TARAMASI (sprint-düzeyi)

1. **Kademe-abartısı avı — TEMİZ.** v4'ün yeni kademe adları honesty.md tablosuyla birebir:
   `independently_verified_unsat_proof` (satır 21), `..._of_strengthened_formula` (satır 22),
   `formal_proof` (satır 18, F6 deflasyon düzeltmesiyle güncel). `test_docs_examples.py` 13/13 geçti.
   Denetçinin kendi saldırıları da abartı bulamadı: Glaisher sabotajında not kayboldu (canlı doğrulama,
   bayrak değil); bilinmeyen kademe `tree_or_reason`'da sessizce geçmiyor (KeyError); sonlu taramalar
   hiçbir yerde proved üretmiyor (pin testleri koşuldu).
   Küçük not (v4 kusuru DEĞİL): `structural_argument` kademesi honesty.md tablosunda yok — ama v4
   öncesinden geliyor (commit `4e60c86`), tablo check()/bulgu kademelerine odaklı; kayda geçirildi.
2. **Zaman-aşımı → sonuç sızıntısı — SIFIR.** R(3,6) n=18 iki 600 s zaman-aşımı yalnız
   `undecided_within_budget` olarak SCALE-RUNS'ta; repo-geneli grep'te hiçbir "R(3,6)≤18 / =18" iddiası
   yok (başlıktaki "denemesi" ve "EKLENMEDİ" negatifi hariç); `_OWN_BRACKETS`'ta (3,6) girdisi yok.
   Frankl 17/17 av `not_found_within_budget`; guard_sampled kapsam alanı "proves NOTHING" diyor (testli).
3. **İkili-ajan gate izi — 7/7 fazda mevcut.** PROGRESS'in her v4F0..F6 girişi evaluator PASS'ini
   somut saldırı içeriğiyle kaydediyor (F0: 2×PASS + 400-CNF fuzz; F1: PASS + yama ONAYı; F2:
   monkeypatch saldırısı; F3: forge/TOCTOU/CRT; F4: 6/6 mutasyon; F5: bağımsız yeniden-hesap + lemma
   hükmü; F6: sabotaj çifti). Gate'in ürettiği GERÇEK bulgular da kayıtlı (F4 AA4 unproven düzeltmesi,
   F6 deflasyon düzeltmesi) — gate kozmetik değil, iş üretmiş.
4. **Sayı tutarlılığı.** Suite büyümesi faz faz monoton ve kayıtlarla tutarlı:
   1849 → 1885 → 1922 → 1932 → 1943 → 1951 → 1969; bu denetimde 1969 yeniden üretildi.

## SONUÇ

**v4 sprint: 7/7 faz CLOSED** (v4F0..v4F6 — denetlenen tüm DONE maddeleri bağımsız kanıtlı).
v4F7'nin kendisi bu raporla kapanma yolunda; v4F7 DONE'unun kalan iki kalemi
(v1.2.0 sürüm + CHANGELOG) bu denetimin ARDINDAN orkestratörün adımıdır — henüz yapılmadı
(`__version__` hâlâ 1.1.0, CHANGELOG `[Unreleased]` boş; dürüstçe kayda geçirildi).

**Kalan bilinen sınırlar (dürüst liste — hiçbiri v4 DONE ölçütlerini ihlal etmez):**

- **R(3,6)=18 kanıtlanmadı:** motorun bildiği yalnız R(3,6)>17 (tanıklı); n=18 UNSAT iki 600 s
  segmentte `undecided_within_budget`. Simetri-kırma klozları bilinçli olarak DENENMEDİ (ayrı
  dürüstlük-etiket tasarımı ister — gelecek faz adayı).
- **ruff-0.16 lint borcu:** kapı 0.15.11'e pinli (bilinçli, `pyproject.toml` notu); 0.16'ya geçiş
  ayrı, kasıtlı bir iş.
- **Lean çapraz-mühür (M6, M3'ün dil/ekip kanadı):** Lean+mathlib toolchain konteynerde derlenemiyor;
  `lake build` insan/CI adımı.
- **İnsan release adımları:** PyPI publish, GitHub Pages etkinleştirme, opsiyonel Zenodo DOI
  (PROGRESS/TODO'da kayıtlı).
- **v1 103/103 kapanamaz:** 12 faz 🔴 açık araştırma; done-sayacı 52/103 (faz-çıpalı).
- **Evrensel adımlar makine-ispatsız (tasarım gereği dürüst):** partisyon/kompozisyon bijeksiyonları
  ve graf taramaları `no_counterexample_within_bound`'da kalır; P2 yasasının ∀k adımı
  `structural_argument`.
- **P6 (LLM-periferi) konteynerde denenemez; W2/X1/X3/AC1 korpus-bağımlı; Q1/Q3/R1/S1
  ayrı-enstrüman** — tek-cümle nedenleri roadmap satırlarında.
- **Frankl:** karşı-örnek yok (beklenen); m=5 exhaustive 2^32 nedeniyle reddedilir, örnekleme hiçbir
  şey ispatlamaz (etiketli).
