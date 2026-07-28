# MathHead — Karar Günlüğü (ADR)

> **Bu dosyanın işi:** Projenin yönünü belirleyen kararları *gerekçesiyle* saklamak.
> Senin çalışma prensiplerindeki **1. duvara** (bağlam kaybı — "devir teslim
> belgesine hiç girmeyen düzinelerce küçük tasarım kararı") doğrudan panzehir.
> Küçük görünen bir karar bile buraya yazılır; böylece 6 ay sonra "neden böyle
> yapmıştık?" sorusunun cevabı kaybolmaz.
>
> **Format (ADR = Architecture Decision Record):** her karar; Durum, Bağlam,
> Karar, Sonuçlar. Kararlar *değiştirilmez*; fikir değişirse yeni ADR açıp eskisini
> "yerini alan" (superseded) diye işaretleriz.

---

## ADR-0001 — Sıfırdan FOL motoru yerine kanıtlanmış çözücü orkestrasyonu

- **Durum:** Kabul edildi · 2026-07-28
- **Bağlam:** "First-order logic temelli" motor iki yolla kurulabilir: (a) resolution/
  unification çekirdeğini sıfırdan yazmak, (b) olgun bir çözücüyü sarmalamak.
- **Karar:** (b). Sıfırdan yazmak öğretici ama yavaş, hataya açık ve bakım yükü
  ağır; olgun çözücüler on yılların mühendisliğini taşıyor.
- **Sonuçlar:** Hız ve güvenilirlik kazanılır; "motorun içini birebir biz yazdık"
  öğrenme değeri feda edilir. Çözücü bir bağımlılık olur (sürüm yönetimi gerekir).

## ADR-0002 — Mantık çekirdeği = Z3 (SMT), hesap = SymPy (CAS)

- **Durum:** Kabul edildi · 2026-07-28
- **Bağlam:** İki farklı iş var — *akıl yürütme/ispat* (bir ifade geçerli mi) ve
  *hesap* (integral/denklem çöz). Tek araç ikisini de iyi yapmıyor.
- **Karar:** Akıl yürütme için **Z3** (FOL + teoriler, deterministik, güçlü).
  Sembolik hesap için **SymPy**. İkisi ayrı katman, router ile bağlanır.
- **Sonuçlar:** Her iş doğru araca gider. İki bağımlılık + bir yönlendirme katmanı
  maliyeti doğar; buna karşılık her alanda "en iyi araç" kullanılır. v1 yalnızca
  Z3'ü hayata geçirir; SymPy v2'ye ertelenir.

## ADR-0003 — Dil = Python, MCP SDK = FastMCP

- **Durum:** Kabul edildi · 2026-07-28
- **Bağlam:** Motor MCP üzerinden AI'a açılacak. Ekosistem uyumu önemli.
- **Karar:** **Python** — çünkü resmi MCP SDK (`mcp[cli]`, FastMCP), `z3-solver`
  ve `sympy` birinci sınıf Python desteğine sahip. Sunucu FastMCP `@mcp.tool()`
  desenini kullanır, `stdio` taşımasıyla yerel çalışır.
- **Sonuçlar:** En düşük sürtünme, en olgun kütüphane zinciri. Python'un çalışma
  zamanı hızı bir maliyet; ama darboğaz çözücü (C++ Z3), Python değil.

## ADR-0004 — Dış API/sözleşme erken dondurulur

- **Durum:** Kabul edildi · 2026-07-28
- **Bağlam:** Non-determinizm ve bağlam kaybı, en çok *sözleşme kayması* olarak
  zarar veriyor (bir oturumda imza değişiyor, sonraki oturum uyumsuz kalıyor).
- **Karar:** `ReasoningResult` çıktı şekli ve MCP araç imzaları v0'da dondurulur.
  Çekirdek gövdesi sonra doldurulur ama *dış yüzey* değişmez. Değişmesi gerekirse
  yeni ADR şarttır.
- **Sonuçlar:** İskelet ile MVP arasında kararlılık; testler ve istemciler erken
  yazılabilir. Esneklik bir miktar azalır — bilinçli takas.

## ADR-0005 — v1 kapsamı = "Akıl Yürütme Denetçisi" (dar dikey dilim)

- **Durum:** Kabul edildi · 2026-07-28
- **Bağlam:** Vizyon geniş (ileriye dönük, en çok ihtiyaç duyulan alan) ama v1'in
  "dar & sağlam" olması istendi.
- **Karar:** v1 = üç ilkel (`entailment`, `consistency`, `model`) + önerme mantığı
  ve doğrusal aritmetik parçası. Nicelik belirteçleri, hesap ve ispat üretimi
  sonraki sürümlere.
- **Sonuçlar:** Uçtan uca çalışan sağlam bir zemin; frontier vizyon `Plan.md`'de
  korunur, bugünkü iş küçük tutulur.

## ADR-0006 — `unknown` / `error` birinci sınıf çıktıdır

- **Durum:** Kabul edildi · 2026-07-28
- **Bağlam:** FOL yarı-karar verilebilir; çözücü kimi girdide karar veremez.
- **Karar:** Motor "bilmiyorum"u açıkça `unknown` olarak döner; guardrail ihlali
  `error` olur. Sonuç asla uydurulmaz.
- **Sonuçlar:** İstemci (AI) belirsizliği görebilir ve buna göre davranır; motor
  güvenilir kalır. "Her zaman bir cevap" beklentisinden vazgeçilir — kasıtlı.

## ADR-0007 — Girdi grameri kısıtlıdır (whitelist)

- **Durum:** Kabul edildi · 2026-07-28
- **Bağlam:** Serbest metin girdisi hem enjeksiyon hem "fazla varsayım" riski.
- **Karar:** Motor yalnızca açıkça tanımlı gramerin (bkz. `docs/mcp-api.md`) izin
  verdiği ifadeleri kabul eder; gerisini `error` ile reddeder.
- **Sonuçlar:** Güvenli ve öngörülebilir yüzey; başlangıçta ifade gücü sınırlı.
  Gramer, ihtiyaç kanıtlandıkça ADR ile genişletilir.

## ADR-0008 — Frontier problem çözümü (Track B) birinci sınıf Kuzey Yıldızı'dır

- **Durum:** Kabul edildi · 2026-07-28
- **Bağlam:** İlk taslak "açık matematik çözmeyi hedeflemiyoruz" diyordu; proje
  sahibi bunu hedeflemek *istediğini* net söyledi. SMT/SAT çözücülerinin açık
  problemleri fiilen çözdüğü sicil de var (Boolean Pythagorean Triples 2016,
  Keller 7. boyut 2020, Schur 5 2017).
- **Karar:** "Zor/açık problemlere saldırı" birinci sınıf hedeftir (Track B);
  kapsamı dürüstçe sınırlıdır: sonlu/kombinatoryal satisfiability'e indirgenebilen
  sorular + ispat doğrulama/formalleştirme. Track B, doğrulanabilir çekirdek
  (Track A) üstüne kurulur ve v3+'ta başlar. v1 hâlâ Track A'dır.
- **Sonuçlar:** İddia yükselir ama sahte vaat yok; "çözdüm" ancak bağımsız
  doğrulanabilir sertifika ile geçerli. Sertifika üretimi/arama ileride yeni ADR
  ile mimariye eklenecek.

## ADR-0009 — Girdi ayrıştırma: elle parser yerine Python `ast` + beyaz liste

- **Durum:** Kabul edildi · 2026-07-28
- **Bağlam:** v1 bir girdi diline ihtiyaç duydu. Elle lexer/grammar yazmak zaman
  alır ve hata/saldırı yüzeyi geniştir.
- **Karar:** Girdiyi Python ifade sözdizimiyle al, `ast.parse(mode="eval")` ile
  ayrıştır, düğümleri **beyaz liste** ile süz. İzinli: `and/or/not`,
  `implies/iff/xor`, `+ - *` (doğrusal), karşılaştırmalar, `Int`/`Bool`. Sort
  bağlamdan çıkarılır; çelişki → `PARSE_ERROR`.
- **Sonuçlar:** Olgun ayrıştırıcı; öncelik/parantez bedava; saldırı yüzeyi
  beyaz listeyle dar. Bedeli: dil "Python'umsu" (`==`, `!=`; implies/iff fonksiyon
  biçiminde). v1 parçası **karar verilebilir** seçildi (Presburger + önermeler)
  → çoğunlukla kesin sonuç, az "unknown".

## ADR-0010 — Nicelik belirteçleri (∀/∃) + Real; iki geçişli çevirmen

- **Durum:** Kabul edildi · 2026-07-28
- **Bağlam:** v1.1, FOL'u gerçekten "first-order" yapmak için `∀`/`∃` ve Real
  istedi. Nicelik belirteci bağlı değişken tanıtır; sortu gövdeden belli olur
  (inşadan önce) ve serbest değişkenle çakışmamalı (variable capture).
- **Karar:** Çevirmen iki geçişe ayrıldı — (1) infer: kapsamlı (scoped) sort
  çıkarımı, (2) build: Z3 inşası. Bağlı sabitlere benzersiz iç ad (mangling) →
  capture yok. Sayısal alan: problemde ondalık varsa Real, yoksa Int.
- **Sonuçlar:** Gerçek FOL ifade gücü. Bedeli: karar-verilebilirlik zayıflar,
  bazı formüllerde `unknown` mümkün (dürüstçe raporlanır; **soundness** korunur —
  motor asla yanlış cevap üretmez). Int/Real karışımı ve yüklem sembolleri
  sonraki sürümlere.

## ADR-0011 — Hesap katmanı: SymPy + ast-whitelist (mantıktan ayrı)

- **Durum:** Kabul edildi · 2026-07-28
- **Bağlam:** v2, "problem çözme" için sembolik hesap (çöz/sadeleştir/türev/
  integral) istedi. Bu, mantık/ispat (Z3) ile aynı iş değil.
- **Karar:** Ayrı `compute/` katmanı, **SymPy** ile. Girdi yine Python `ast` +
  beyaz liste ile süzülür (`sympify`/`eval` güvensizliği KULLANILMAZ). Ayrı
  `ComputeResult` sözleşmesi. Router aynı; yalnızca yeni görev adları eklendi.
- **Sonuçlar:** Her iş doğru araca gider (mantık→Z3, hesap→SymPy). Güvenlik
  beyaz-listeyle korunur (ör. `__import__` reddedilir). SymPy kapalı formda
  çözemezse dürüstçe değerlendirilmemiş sonuç döner.

---

<!-- Yeni karar şablonu:
## ADR-XXXX — başlık
- **Durum:** Öneri | Kabul | Yerini aldı (ADR-YYYY) · YYYY-AA-GG
- **Bağlam:** …
- **Karar:** …
- **Sonuçlar:** …
-->
