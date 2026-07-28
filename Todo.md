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
