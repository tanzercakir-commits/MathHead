# MathHead — Todo

> **Bu dosyanın işi:** ŞU AN yapılacaklar ve öncelikler. Sürekli değişir.
> Hedef mimari `Plan.md`'de sabit durur; oraya bakınca "nereye gidiyoruz"
> her zaman elinin altında olur.
>
> İşaretler: `[ ]` açık · `[~]` devam ediyor · `[x]` bitti

---

## Aktif hedef: **v1 — Akıl Yürütme Denetçisi**

### P0 — Zemin (çekirdek çalışsın)

- [ ] **T1** `guardrails`: `validate_input` + `solver_config` (sabit tohum + zaman aşımı + tek iş parçacığı) — `src/mathhead/guardrails/__init__.py`
- [ ] **T2** `translate`: gramer + `parse` + `to_z3` (önerme mantığı + doğrusal aritmetik) — `src/mathhead/core/translate.py`
- [ ] **T3** `logic.check_entailment`: "negasyonun UNSAT'lığı" yöntemi + karşıörnek — `src/mathhead/core/logic.py`
- [ ] **T4** `logic.check_consistency`: SAT + `unsat core`
- [ ] **T5** `logic.find_model`: okunur model çıktısı

### P1 — Uçtan uca bağla

- [ ] **T6** `router.route`: 3 ilkeli bağla (v1 tek çözücü: Z3)
- [ ] **T7** `tests`: `test_logic` içindeki `xfail` işaretini kaldır, best/worst senaryoları yeşile al; **determinizm testi** ekle (aynı girdi ×100 → aynı çıktı)
- [ ] **T8** `server`: gerçek MCP istemcisiyle (Claude) uçtan uca en az 3 soru denemesi

### P2 — Cila

- [ ] **T9** `explanation` alanını zenginleştir (neden valid/invalid — insan-okur gerekçe)
- [ ] **T10** golden senaryolar (`tests/fixtures/`) + `README` hızlı başlangıç kes-yapıştır

---

## Backlog (v1 sonrası — olgunlaşınca Plan yol haritasına taşınır)

- ∀/∃ nicelik belirteçleri ve daha zengin FOL parçası (v1.1)
- `compute/` SymPy katmanı: `solve`, `simplify`, türev/integral (v2)
- İspat üretimi + AI ispatını doğrulama (v3)

---

## Bu oturumda biten (v0)

- [x] Repo iskeleti + import edilebilir stub'lar
- [x] Dönüş sözleşmesi (`ReasoningResult`) donduruldu
- [x] `Plan` / `Todo` / `Progress` / `PRINCIPLES` / `DECISIONS` + `docs/`
