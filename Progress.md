# MathHead — Progress / ChangeLog

> **Bu dosyanın işi:** NE yaptık, NE ZAMAN, NEDEN — ekleme-only (append-only)
> günlük. En yeni en üstte. Küçük tasarım kararlarının *gerekçesi* `DECISIONS.md`'ye,
> yapılan işin *özeti* buraya.

---

## 2026-07-28 — Aşama 4 · kombinatorik & ayrık (perm/comb/factorial/partition/recurrence)

**Yapıldı**

- 5 yeni işlem: `permutations`, `combinations`, `factorial`, `partition_count`,
  `solve_recurrence` (doğrusal özyineleme kapalı-form, `rsolve`).
- `solve_recurrence` için güvenli mini-ayrıştırıcı: `func(...)` çağrıları + `var`
  + aritmetik; `=`→`==` normalizasyonu; whitelist dışı ad/çağrı reddedilir.
- Uçtan uca: router (5) + MCP (**42 araç**) + CLI (`perm/comb/factorial/
  partitions/recurrence`) + `tests/test_combinatorics.py` (18) → **205/205 yeşil**.

**Doğrulandı (dürüst duvarlar ampirik)**

- `P(10,3)=720`, `C(10,3)=120`, `10!`, `p(10)=42`, `p(100)=190569292`.
- **Fibonacci** `y(n)=y(n-1)+y(n-2)` → Binet kapalı formu; `Fib(10)=55` ikame ile
  doğrulandı. `y(n)=2y(n-1)` → `2**n`.
- Dürüstlük: doğrusal olmayan `y(n)=y(n-1)**2` → kapalı form yok (COMPUTE_FAILED);
  `k>n` → 0; kötücül/tanımsız ad → reddedilir.

**Not (bug→fix):** `ast.parse(mode="eval")` `=` kabul etmiyordu (atama). Tek `=`,
`==`'e normalize edildi → Compare işleyicisi devraldı. Ampirik yakalandı.

**Sıradaki:** Aşama 5 [S] — hata taksonomisi + golden fixtures + benchmark iskeleti.

## 2026-07-28 — Aşama 3 · sayı teorisi (gcd/lcm/asal/factorize/modinv/CRT/Diophantine)

**Yapıldı**

- 7 yeni işlem: `gcd`, `lcm`, `is_prime`, `factorize`, `modular_inverse`,
  `chinese_remainder` (CRT), `linear_diophantine`. Girdi güvenli tam sayı
  (`_parse_int`: ast-whitelist + tam sayı denetimi; "2**10" serbest, sembol yok).
- Uçtan uca: router (7 görev) + MCP (**37 araç**) + CLI (`gcd/lcm/isprime/
  factorize/modinv/crt/diophantine`) + `tests/test_numbertheory.py` (18) →
  **187/187 yeşil**. Docs güncel.

**Doğrulandı (dürüst duvarlar ampirik)**

- `factorize(360)=2³·3²·5`; `is_prime(91)=False` (7·13); `CRT([3,5,7],[2,3,2])→23
  (mod 105)`; `Diophantine 3x+6y=9 → (3-2t₀, t₀)`.
- Dürüstlük: `modular_inverse(4,8)` → ters yok (gcd≠1); CRT `[4,6],[1,2]` →
  bağdaşmaz; `Diophantine 2x+4y=5` → boş liste (gcd(2,4)∤5); `factorize(1)=[]`.

**Sıradaki:** Aşama 4 — kombinatorik & ayrık (permütasyon/kombinasyon, binom,
partition, recurrence).

## 2026-07-28 — Aşama 2 [S] · sağlamlaştırma-1 (property + determinizm + fuzz)

**Yapıldı**

- `tests/test_compute_properties.py` (8 property testi): hesap katmanı için
  matematiksel değişmezler + parser fuzz + determinizm denetimi.
- Değişmezler: `det(A·B)=det(A)·det(B)`, `det(Aᵀ)=det(A)`, `Ax=b` roundtrip,
  `simplify` idempotent. Fuzz: rastgele/kötücül metin & düzensiz matris → çökme
  yok, yalnız `ok|error`. → **169/169 yeşil**, 3 hypothesis tohumunda kararlı.

**Doğrulandı**

- Güvenlik değişmezi property testiyle de doğrulandı: beyaz-liste dışı hiçbir
  girdi kod çalıştırmıyor / exception sızdırmıyor.
- Yeni araç/CLI yok (bilinçli — bu bir sağlamlaştırma aşaması). API yüzeyi sabit.

**Sıradaki:** Aşama 3 — sayı teorisi (gcd/lcm, asal, factorize, modüler ters/CRT,
Diophantine).

## 2026-07-28 — Aşama 1 · lineer cebiri tamamla (matmul/Ax=b/eigvec/rref/nullspace/LU)

**Yapıldı**

- 6 yeni işlem: `matrix_multiply`, `matrix_solve` (Ax=b matris formu),
  `eigenvectors`, `rref` (+pivotlar), `nullspace`, `lu_decomposition`.
- Uçtan uca: router (6 görev) + MCP (**30 araç**) + CLI (`matmul`/`matsolve`/
  `eigenvectors`/`rref`/`nullspace`/`lu`) + `tests/test_linalg.py` (15) →
  **161/161 yeşil**. Docs güncel.

**Doğrulandı (dürüst duvarlar ampirik)**

- `Ax=b`: benzersiz `{x0:6,x1:4}`; **tutarsız → boş liste** (uydurma yok);
  **sonsuz → parametrik** `{x0: "3 - x1", x1: "x1"}` + açıklamada "parametrik".
- matmul boyut uyumsuz (`A.cols≠B.rows`) → hata; nullspace tam-rank → trivial
  (boş); LU → L alt/U üst üçgen. Özvektörler özdeğere göre sıralı (determinizm).

**Sıradaki:** Aşama 2 [S] — determinizm denetimi + property test genişletme +
parser fuzz. (Hedef: Aşama 11'e kadar otonom.)

## 2026-07-28 — lineer cebir / matris (det / inverse / eigenvalues / rank)

**Yapıldı**

- Hesap katmanına matris çekirdeği: `determinant`, `matrix_inverse`,
  `eigenvalues` (+ cebirsel katlılık), `matrix_rank`. Girdi `list[list[str]]`,
  her hücre ast-whitelist ile süzülür → sembolik hücre serbest.
- Uçtan uca: `router` (4 yeni görev) + MCP (**24 araç — dört yeni**) + CLI
  (`det`/`inverse`/`eigenvals`/`rank`, MATLAB-tarzı `"1,2;3,4"` dizgisi) +
  `tests/test_matrix.py` (18 test) → **146/146 yeşil**. Docs güncel.

**Doğrulandı (dürüst duvarlar ampirik)**

- `det[[a,b],[c,d]] = a*d - b*c` (sembolik çalışıyor); `inv[[1,2],[3,4]] =
  [[-2,1],[3/2,-1/2]]`; döndürme matrisinin özdeğerleri `±i` (karmaşık, tam form);
  kusurlu (defective) matriste tek özdeğer **katlılık 2** (gizlenmez).
- **Dürüstlük:** tekil matris (`[[1,2],[2,4]]`, det=0) → ters uydurulmaz,
  `COMPUTE_FAILED` + "tersinir değil" mesajı. Kare-değil determinant → reddedilir.
- Güvenlik değişmezi korundu: hücrede `__import__` → reddedilir.
- Determinizm: özdeğerler `value`'ya göre sıralı → çağrılar arası kararlı (ADR-0019).

**Sıradaki (gelecek oturum):** matris çarpımı + `Ax=b` (lineer sistem matris
formu) + özvektör (eigenvector); ya da ispat/mantık tarafını derinleştirme.
(Ürün/PyPI akşam kullanıcıda.)

## 2026-07-28 — kalkülüs & sistemler (limit / series / solve_system)

**Yapıldı**

- Hesap katmanı (SymPy) genişledi: `limit` (sonlu/sonsuz nokta + tek yön `+`/`-`),
  `series` (bir nokta etrafında `order`. mertebe Taylor açılımı, `removeO`),
  `solve_system` (çok değişkenli sistem; doğrusal + doğrusal olmayan).
- Uçtan uca bağlandı: `router` (3 yeni görev) + MCP (**20 araç — üç yeni**) +
  CLI (`limit`, `series`, `solve-system`) + `tests/test_calculus.py` (18 test)
  → **128/128 yeşil**. Docs: `mcp-api.md`, `README.md`, `CHANGELOG.md` güncel.

**Doğrulandı (dürüst duvarlar ampirik)**

- `lim x→0 sin(x)/x = 1`, `lim x→∞ 1/x = 0`, `lim n→∞ (1+1/n)^n = e` (bilinen
  sabit yeniden üretildi); `exp(x)` 5. mertebe Taylor doğru.
- `solve_system` **dürüst**: çelişen sistem → boş liste (uydurma yok); doğrusal
  olmayan (çember ∩ doğru) → iki çözüm; serbest değişken → parametrik.
- Güvenlik değişmezi korundu: beyaz-liste dışı çağrı (`__import__`) reddedilir.

**Sıradaki (gelecek oturum):** lineer cebir (matris) — determinant, özdeğer,
tersini alma. (Ürün/PyPI akşam kullanıcıda.)

## 2026-07-28 — mantıksal denklik & sınıflandırma

**Yapıldı**

- `logic.equivalent` (A ≡ B; `a XOR b` UNSAT ise denk) + `logic.classify`
  (totoloji / çelişki / olumsal). Router + MCP (**17. araç — iki yeni**) + CLI
  (`equiv`, `classify`) + testler → **110/110 yeşil**.
- `not_equivalent`'ta farklılaşma tanığı; `contingent`'te doğru + yanlış tanık.

**Sıradaki (gelecek oturumlar):** performans; daha çok property; (ürün akşam sende).

## 2026-07-28 — sağlamlaştırma: property-based test (hypothesis)

**Yapıldı**

- `tests/test_properties.py`: `hypothesis` ile rastgele formüllerde değişmezler —
  hiç çökmeme, `A⊨B ⟺ {A,¬B} tutarsız`, öz-gerektirme, `enumerate ⟺ consistency`,
  türetici sağlamlığı. `hypothesis` dev bağımlılığı eklendi.
- **Property testi GERÇEK bir zayıflık yakaladı:** tanık (model) çağrılar arası
  değişebiliyordu (birden çok geçerli model). Determinizm iddiası kesinleştirildi:
  **verdict garantidir, tanık bir örnektir** (ADR-0019); don't-care'ler kanonik
  varsayılana sabitlendi. `PRINCIPLES` / `Plan` güncellendi.
- **103/103 yeşil** (7 property testi dahil).

**Sıradaki (gelecek oturumlar):** mantıksal denklik/sınıflandırma; performans.

## 2026-07-28 — MaxSAT (yumuşak/ağırlıklı kısıtlar)

**Yapıldı**

- `logic.max_satisfy` + `MaxSatResult`: zorunlu (hard) kısıtları sağlayıp EN ÇOK
  (ağırlıklı) yumuşak (soft) kısıtı sağla (`z3.Optimize.add_soft`). Router + MCP
  (**15. araç**) + CLI (`mathhead maxsat`) + testler → **96/96 yeşil**.
- Ağırlıklı seçim doğrulandı (ağır kısıt tercih edilir); `hard` sağlanamazsa unsat.
- Yeni karar: ADR-0018.

**Sıradaki (gelecek oturumlar):** mantıksal denklik/sınıflandırma; performans;
(ürün/yayın akşam, sende).

## 2026-07-28 — optimizasyon (Z3 Optimize / MaxSMT)

**Yapıldı**

- `logic.optimize` + `OptimizeResult` + `translate.translate_objective`: kısıtlar
  altında sayısal amacı max/min (`z3.Optimize`). Router + MCP (**14. araç**) + CLI
  (`mathhead optimize`) + testler → **90/90 yeşil**.
- Dürüst kenar durumlar: `unbounded` (sınırsız), `unsat` (infeasible), açık-sınır
  (ε — supremum/infimum tam ulaşılamaz).
- Yeni karar: ADR-0017.

**Sıradaki (gelecek oturumlar):** mantıksal denklik/sınıflandırma; performans;
(ürün/yayın akşam, sende).

## 2026-07-28 — model numaralandırma (all-SAT)

**Yapıldı**

- `logic.enumerate_models` + `ModelSet`: bir formülü sağlayan FARKLI modelleri
  (bloklama-cümlesiyle) say. `exhaustive` bayrağı dürüst: tümü mü, sınır mı.
- Router + MCP (**13. araç**) + CLI (`mathhead enumerate`) + testler → **84/84**.

**Dürüstlük:** Sonsuz alanda (sınırsız Int/Real) `exhaustive=False` — "daha
fazlası olabilir" açıkça belirtilir.

**Sıradaki (gelecek oturumlar):** mantıksal denklik/sınıflandırma; performans;
(ürün/yayın akşam, sende).

## 2026-07-28 — v3.2 · ispat üreticisine ∃ (varoluşsal) akıl yürütme

**Yapıldı**

- `core/proof.py`: **∃-eleme** (taze tanık sabiti; `∀`-eleme onu da kullanır) +
  **∃-giriş** (hedef `∃x.ψ`, `ψ[t]` türetildiyse). Bağlam/witness yönetimi.
- `∃x P(x), ∀x(P→Q) ⊨ ∃x Q(x)` gibi çıkarımlar adım adım. Testler + regresyon
  → **78/78 yeşil**.
- Yeni karar: ADR-0016. Klasik FOL doğal tümdengelim parçası büyük ölçüde tamam.

**Dürüstlük:** Aritmetik türetim ve bazı karışık nicelik desenleri hâlâ yok →
Z3 kararı korunur (adımsız).

**Sıradaki (gelecek oturumlar):** ispatı LaTeX/metin dışa verme; performans;
(yayın akşam, sende).

## 2026-07-28 — v3.1 · ispat üreticisi genişletildi (RAA + MT/DS)

**Yapıldı**

- `core/proof.py` kural kümesi: modus tollens, ayrık tasım, çift olumsuzlama,
  De Morgan; + ikinci strateji **çelişkiden ispat (RAA)** → durum ayrımı (proof
  by cases) gibi dolaylı ispatlar adım adım çıkıyor.
- Testler (MT / DS / RAA / De Morgan) + regresyon → **76/76 yeşil**.
- Yeni karar: ADR-0015.

**Dürüstlük:** Varoluşsal (∃) eleme ve aritmetik türetim hâlâ yok → Z3 kararı
korunur (adımsız).

**Sıradaki (gelecek oturumlar):** ∃-eleme; GitHub release + PyPI (akşam, sende).

## 2026-07-28 — v3 · ispat üretimi (adım adım) (aynı oturum)

**Yapıldı**

- `core/proof.py`: entailment + NEDEN. (1) minimal öncül çekirdeği (unsat core),
  (2) ileri zincirleme **doğal tümdengelim** türetimi (modus ponens, ∧-ayıklama,
  iff, evrensel örnekleme). Klasik silogizm adım adım.
- Yeni MCP aracı `prove` (**12. araç**) + CLI `mathhead prove` + testler → **72/72**.
- Yeni karar: ADR-0014.

**Dürüstlük:** Türetici önerme + yüklem + evrensel parçasıyla sınırlı; aritmetik /
`or`-`not` / varoluşsal için türetim kurulamaz → Z3 kararı korunur, adımsız
("türetim yok" denir).

**Sıradaki (gelecek oturumlar):** türeticiyi genişletme (or-elim, varoluşsal);
GitHub release; PyPI (senin evden).

## 2026-07-28 — Optimizasyon denemesi · simetri kırma (dürüst: karışık sonuç)

**Yapıldı**

- `frontier`'a renk-simetri kırma eklendi (opsiyonel `symmetry_break`; doğruluk
  teste kilitli). Ölçüm: küçük/UNSAT'ta hızlandırdı; **SAT'ta yavaşlattı**
  (S(4)=44: 35s → 48s); W(2,5) 2-renkte değişmedi (faktör 2).
- **Dürüst sonuç:** naif simetri kırma duvarı (S(4)=45, W(2,6)) AŞMADI →
  varsayılan **kapalı**. Gerçek duvar araştırma-düzeyi SAT teknikleri ister.
  Detay: `docs/track-b-results.md`.

**Sıradaki (gelecek oturumlar):** ürünleşme (PyPI); farklı hızlandırma teknikleri.

## 2026-07-28 — Track B · Schur sayıları (bilinen değerler yeniden üretildi)

**Yapıldı**

- `frontier.schur_number_coloring`: {1..n} r-renk sum-free bölme. Router + MCP
  (**11. araç**) + CLI (`mathhead schur n r`) + testler → **65/65 yeşil**.
- Dürüst saldırı: S(2)=4, S(3)=13 **tam** yeniden üretildi (n=5, n=14 imkânsızlık
  ispatları); S(4) için S(4) ≥ 44 doğrulandı (n=44 sat, ~25 sn), üst sınır (n=45)
  duvara takıldı. Detay: `docs/track-b-results.md`.

**Dürüst sonuç:** S(5)=160 ve açık S(6) bu ortamda erişilemez. Sahte zafer yok.

**Sıradaki (gelecek oturumlar):** PyPI paketi; ölçek/çözücü; v3 ispat üretimi.

## 2026-07-28 — Track B · van der Waerden (bilinen değerler yeniden üretildi)

**Yapıldı**

- `frontier.van_der_waerden_coloring`: {1..n} r-renk, tek renkli k-terimli
  aritmetik dizi olmadan boyama. Router + MCP (**10. araç**) + CLI
  (`mathhead vdw n k`) + testler → **61/61 yeşil**.
- **Açık-problem sınıfına dürüst saldırı** (kullanıcı isteği): motor W(2,3)=9,
  W(2,4)=35, **W(2,5)=178** değerlerini AYNI SAT yöntemiyle **yeniden üretti**
  (her biri gerçek imkânsızlık ispatı; W(2,5) ~61 sn). Detay + dürüst
  compute-wall: `docs/track-b-results.md`.

**Dürüst sonuç:** Açık bir problem ÇÖZÜLMEDİ (W(2,6)=1132 ve açık W(2,7) bu
ortamın ötesinde). Ama araştırma değerleri doğrulanabilir biçimde üretildi ve
duvarın yeri şeffafça gösterildi. Sahte zafer yok.

**Sıradaki (gelecek oturumlar):** PyPI paketi; ölçek/çözücü iyileştirme; v3 ispat üretimi.

## 2026-07-28 — CLI · terminal arayüzü (aynı oturum)

**Yapıldı**

- `mathhead` CLI (argparse): entail / consistent / model / simplify / solve /
  diff / integrate / pigeonhole / pythagorean; `--json`; anlamlı çıkış kodları
  (0 sonuç, 1 hata, 2 unknown). Aynı `router`'a bağlı ince kabuk.
- `pyproject` script girişi (`mathhead`); README + CI rozeti. → **56/56 yeşil**.

**Sıradaki (gelecek oturumlar):** PyPI paketi, fonksiyon terimleri, v3 ispat üretimi.

## 2026-07-28 — v1.2 · yüklemler + bireyler (aynı oturum)

**Yapıldı**

- `translate`: üçüncü sort `U` (birey) + yorumsuz yüklemler (`Man(x)`, `Loves(a,b)`).
- Klasik silogizm çalışır: `∀x.(Man(x)→Mortal(x))`, `Man(socrates)` ⊨ `Mortal(socrates)`.
- Ad çakışması / arite / argüman-sort denetimleri (net reddeder). Yeni MCP aracı
  YOK (dil zenginleşti; mevcut 3 mantık aracı kapsıyor).
- Testler: silogizm + ilişkisel + çelişki + guardrail → **51/51 yeşil**.
- Yeni karar: ADR-0013.

**Karar:** v1.2'de yüklem argümanları yalnızca birey; fonksiyon terimleri (`f(x)`)
sonraki sürüme. Yüklem+quantifier undecidability'i artırır; `unknown` mümkün,
soundness korunur.

**Sıradaki (gelecek oturumlar — acele yok):** yorumsuz fonksiyon terimleri;
v3 ispat üretimi; Track B derinleştirme (graph coloring/Schur); ürünleştirme
(PyPI paketi, CLI, README rozetleri, kullanım kılavuzu).

## 2026-07-28 — v2.1 · Track B tohumu (aynı oturum)

**Yapıldı**

- `frontier/`: problemi SAT'a indirgeme demoları — Boolean Pythagorean
  renklendirme + güvercin yuvası (pigeonhole) imkânsızlık ispatı.
- 2 MCP aracı (toplam **9**). Testler: üretilen boyamanın **bağımsız doğrulaması**
  (tek renkli üçlü yok) + PHP ispatı → **42/42 yeşil**.
- Yeni karar: ADR-0012.

**Karar:** Track B "yöntem"i çalışır (indirgeme → Z3). Dürüstlük: küçük ölçek;
ünlü sonuçların kendisi değil, aynı yöntem. Dış sözleşme DEĞİŞMEDİ.

**Sıradaki:** ölçek/CDCL sınırları, daha çok indirgeme (graph coloring, Schur),
veya v1.2 (yüklem sembolleri).

## 2026-07-28 — v2 · hesap katmanı (SymPy) (aynı oturum)

**Yapıldı**

- `compute/`: ast-whitelist → SymPy çevirici (`sympify`/`eval` YOK — güvenlik).
- 4 işlem: `simplify`, `solve`, `differentiate`, `integrate` + `ComputeResult`.
- `router` compute görevlerini yönlendiriyor; MCP'ye 4 yeni araç (toplam **7**).
- Testler: hesap + güvenlik (`__import__` / bilinmeyen fonksiyon reddi) →
  **37/37 yeşil**.
- Yeni karar: ADR-0011.

**Karar:** Hesap, mantıktan ayrı katman; girdi yine beyaz-liste. SymPy kapalı
formda çözemezse dürüstçe değerlendirilmemiş sonuç. Dış sözleşme (mevcut araçlar)
DEĞİŞMEDİ.

**Sıradaki:** Track B tohumu (kombinatoryal problemi SAT'a indirgeme) / T9.

## 2026-07-28 — v1.1 · nicelik belirteçleri + Real (aynı oturum)

**Yapıldı**

- `translate` iki geçişe ayrıldı (infer/sort + build); kapsam (scope) yönetimi.
- `forall(x, …)` / `exists(x, …)`: bağlı sabit mangling → değişken yakalama yok.
- Real sayı desteği: ondalık sabit varsa numeric domain = Real (yoksa Int).
- `logic` artık `translate_all` kullanıyor (paylaşımlı bağlam + doğru domain).
- Real model değeri okunur (`3/2` → `1.5`).
- Testler: quantifier + Real + capture + **soundness** (∀∃'de asla yanlış cevap;
  gerekirse `unknown`) → **25/25 yeşil**.
- Yeni karar: ADR-0010.

**Karar:** Nicelik belirteçleri karar-verilebilirliği zayıflatır; `unknown`
birinci sınıf, **soundness** korunur. Dış sözleşme (ReasoningResult, MCP) DEĞİŞMEDİ.

**Sıradaki:** T9 (explanation zenginleştir) / v2 (SymPy compute).

## 2026-07-28 — v1 · çekirdek çalışır (aynı oturum)

**Yapıldı**

- `guardrails`: `validate_input` (boyut/derinlik/sözdizimi) + `solver_config`
  (sabit seed + timeout → determinizm).
- `core/translate`: Python `ast` tabanlı, beyaz-listeli parser → Z3; sort
  çıkarımı (Bool/Int); doğrusallık çiti (var*var reddi); zincirli karşılaştırma.
- `core/logic`: `check_entailment` (¬sonuç UNSAT + karşıörnek), `check_consistency`
  (sat/unsat + **unsat core**), `find_model`. İzlenebilir `meta`.
- `router.route` 3 ilkeli bağlar; `mcp_server` → router → core.
- Testler: best/worst + **determinizm (×50)** + guardrail → **17/17 yeşil**.
- Canlı MCP: 3 araç kayıtlı (`entailment`/`consistency`/`model`), JSON çıktı temiz.
- Yeni karar: ADR-0009 (ast-tabanlı parser + karar-verilebilir v1 parçası).

**Karar:** v1 dili bilinçle **karar verilebilir** (Presburger + önermeler);
Real/∀∃/nonlinear v1.1+'a ertelendi. Dış sözleşme (ReasoningResult, MCP imzaları)
DEĞİŞMEDİ.

**Doğrulandı:** `pytest` 17/17; z3 5.0.0; uçtan uca route → Z3 → JSON.

**Sıradaki:** T9 (explanation zenginleştir) / v1.1 (Real + nicelik belirteçleri).

## 2026-07-28 — v0.1 · vizyon düzeltmesi (aynı oturum)

**Değişti**

- Hedef iki hatta ayrıldı: **Track A** (doğrulanabilir çekirdek, yakın vade) +
  **Track B** (zor/açık problemlere saldırı, Kuzey Yıldızı, v3+). Proje sahibinin
  geri bildirimi: açık problem çözümü de birinci sınıf hedef olmalı.
- `Plan.md` §2 yeniden yazıldı (SMT/SAT'ın açık problem çözme siciliyle:
  Boolean Pythagorean Triples 2016, Keller 7. boyut 2020, Schur 5 2017).
- Yeni karar: `DECISIONS.md` ADR-0008.

**Karar:** Track B kapsamı = satisfiability'e indirgenebilen problemler + ispat
doğrulama. v1 kapsamı DEĞİŞMEDİ (hâlâ Track A / Akıl Yürütme Denetçisi).

## 2026-07-28 — v0 · iskelet & tasarım (bu oturum)

**Kuruldu**

- Proje iskeleti: `src/mathhead/{core, compute, router, guardrails, server}` + `tests/` + `docs/`
- Dönüş sözleşmesi `ReasoningResult` donduruldu: `status / reason_code / explanation / witness / meta`
- MCP sunucu iskeleti (FastMCP, 3 araç: `entailment` / `consistency` / `model`) — stub
- Guardrail sabitleri + imzaları: `validate_input`, `solver_config`
- Tasarım dosyaları: `Plan.md`, `Todo.md`, `Progress.md`, `PRINCIPLES.md`, `DECISIONS.md`
- `docs/`: `architecture.md`, `mcp-api.md`, `glossary.md`
- Testler: `test_smoke` (geçer) + `test_logic` (spec, şimdilik `xfail`)

**Mimari kararlar** (özet — detay `DECISIONS.md`)

- ADR-0001: Sıfırdan FOL motoru yerine kanıtlanmış çözücü orkestrasyonu
- ADR-0002: Mantık çekirdeği = **Z3** (SMT); hesap = **SymPy** (CAS)
- ADR-0003: Dil = **Python**; MCP SDK = **FastMCP** (`mcp[cli]`)
- ADR-0004: Dış API/sözleşme **erken dondurulur**

**Doğrulandı**

- Çekirdek harici bağımlılık olmadan temiz import ediliyor; `ReasoningResult`
  sözleşmesi ve `is_conclusive()` beklendiği gibi çalışıyor.

**Sıradaki adım:** `Todo` → T1 (guardrails) → T2 (translate) → T3 (entailment).

---

<!-- Yeni girdiler bu satırın ÜSTÜNE eklenecek. Şablon:
## YYYY-AA-GG — vX · başlık
**Yapıldı** …  **Karar** …  **Doğrulandı** …  **Sıradaki** …
-->
