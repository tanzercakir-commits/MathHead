# MathHead — Todo

> **Bu dosyanın işi:** ŞU AN yapılacaklar ve öncelikler. Sürekli değişir.
> Hedef mimari `Plan.md`'de sabit durur.
>
> İşaretler: `[ ]` açık · `[~]` devam ediyor · `[x]` bitti

---

## Aktif hedef: **v1 — Akıl Yürütme Denetçisi** → ÇEKİRDEK TAMAM ✅

### P0 — Zemin (çekirdek)

- [x] **T1** `guardrails`: `validate_input` + `solver_config` (sabit tohum + timeout)
- [x] **T2** `translate`: Python `ast` → Z3, sort çıkarımı, doğrusallık çiti
- [x] **T3** `check_entailment` (¬sonuç UNSAT + karşıörnek)
- [x] **T4** `check_consistency` (sat/unsat + `unsat core`)
- [x] **T5** `find_model`

### P1 — Uçtan uca

- [x] **T6** `router.route` (3 ilkel) + `server → router`
- [x] **T7** testler: best/worst + **determinizm (×50)** + guardrail → **17/17 yeşil**
- [~] **T8** gerçek MCP istemcisi (Claude): araçlar in-process doğrulandı; canlı
  `stdio` bağlantısı senin tarafında (`claude mcp add ...`) — README'de tarif var

### P2 — Cila / sıradaki

- [ ] **T9** `explanation`'ı zenginleştir (invalid'de karşıörneği cümleye göm)
- [ ] **T10** golden senaryolar (`tests/fixtures/*.json`)
- [x] **T11** v1.1: Real sayılar + `∀`/`∃` nicelik belirteçleri ✅
- [x] **T12** v2: `compute/` (SymPy) — solve / simplify / türev-integral ✅
- [x] **T13** v2+: kalkülüs & sistemler — limit / series / solve_system ✅
- [x] **T14** v2+: lineer cebir (matris) — determinant / eigenvalue / inverse / rank ✅
- [x] **T15** v2+: lineer cebir II — matmul / Ax=b / eigenvector / rref / nullspace / LU ✅
      (ROADMAP Aşama 1 · 161 test · 30 araç)
- [x] **T16** ROADMAP Aşama 2 [S]: determinizm + property (det/Ax=b/simplify) + fuzz ✅ (169 test)
- [ ] **T17** ROADMAP Aşama 3: sayı teorisi (gcd/lcm, asal, factorize, modüler ters/CRT, Diophantine)

---

## Bu oturumda biten

- [x] v0: iskelet + tasarım dosyaları
- [x] v1 çekirdeği **çalışır** (gerçek Z3): 3 ilkel, unsat core, karşıörnek, meta
- [x] MCP uçtan uca (3 araç kayıtlı, JSON temiz), 17/17 test yeşil
- [x] Repo GitHub'da; CI (Actions) kurulu
- [x] **v1.1**: nicelik belirteçleri (∀/∃) + Real → 25/25 test yeşil
- [x] **v2**: hesap katmanı (SymPy) — solve/simplify/türev/integral → 37/37 test yeşil
- [x] **Track B tohumu**: problem→SAT indirgeme (Pythagorean + pigeonhole) → 42/42 yeşil
- [x] **v1.2**: yüklemler + bireyler (klasik silogizm çalışır) → 51/51 yeşil
- [x] **CLI**: `mathhead` terminal aracı (11 komut + --json)
- [x] **v3 ispat üretimi** (adım adım ND: MP/MT/DS/∀/∃/RAA) + **model numaralandırma** → 84/84
- [x] **optimizasyon** (Z3 Optimize / MaxSMT): kısıt altında amacı en iyile → 90/90
- [x] **MaxSAT** (yumuşak/ağırlıklı kısıtlar): en çok soft kısıtı sağla → 96/96
- [x] **sağlamlaştırma**: property-based test (hypothesis) + determinizm kesinleştirildi → 103/103
- [x] **denklik & sınıflandırma** (equivalent / classify): totoloji/çelişki/olumsal → 110/110
- [x] **kalkülüs & sistemler** (limit / series / solve_system): tek yön + sonsuz nokta,
  Taylor, çok değişkenli sistem (doğrusal+değil, dürüst boş çözüm) → **128/128**, MCP **20 araç**
- [x] **lineer cebir (matris)** (determinant / inverse / eigenvalues / rank): sembolik hücre,
  tekil matris dürüst hata, karmaşık özdeğer + katlılık → **146/146**, MCP **24 araç**
- [x] **Track B / van der Waerden**: W(2,3..5) bilinen değerleri yeniden üretildi (dürüst) → 61/61
- [x] **Track B / Schur**: S(2)=4, S(3)=13 yeniden üretildi; S(4)≥44 (dürüst duvar) → 65/65
- [x] **v3 / ispat üretimi**: minimal çekirdek + doğal tümdengelim (silogizm adım adım) → 72/72
