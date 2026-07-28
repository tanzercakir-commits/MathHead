# Changelog

Tüm önemli değişiklikler burada tutulur. Sürümleme [SemVer](https://semver.org/lang/tr/).

## [Yayınlanmamış]

### Eklendi

- **İspat üretimi (`prove`):** entailment için *neden* — minimal öncül çekirdeği
  (unsat core) + adım adım **doğal tümdengelim**: modus ponens/tollens, ayrık
  tasım, ∧-ayıklama, iff, çift olumsuzlama, De Morgan, evrensel örnekleme,
  **varoluşsal eleme/giriş (∃)**; ve **çelişkiden ispat (RAA)** ile durum ayrımı
  (proof by cases). Silogizm, ∃-çıkarımı ve proof-by-cases adım adım. MCP aracı
  `prove` (12 araç) + `mathhead prove` CLI.
- **Model numaralandırma (`enumerate_models`):** bir formülü sağlayan tüm/çoklu
  farklı modeli (all-SAT, bloklama-cümlesi) döndürür; `exhaustive` bayrağıyla
  "tümü mü, sınır mı" dürüstçe belirtilir. MCP aracı (13 araç) + `mathhead
  enumerate` CLI.

## [0.1.0] — 2026-07-28

İlk yayınlanabilir sürüm. AI'ın **MCP** üzerinden kullanabileceği, first-order
logic temelli, **deterministik** matematik akıl yürütme, hesap ve indirgeme motoru.

### Eklendi

- **Mantık çekirdeği (Z3):** `entailment` / `consistency` / `find_model`;
  önermeler mantığı + doğrusal aritmetik + nicelik belirteçleri (`∀`/`∃`) + Real
  sayılar + yorumsuz yüklemler (`Man(x)`) → klasik silogizm çalışır.
- **Hesap katmanı (SymPy):** `simplify` / `solve` / `differentiate` / `integrate`.
- **Track B (SAT indirgeme):** güvercin yuvası, Boolean Pythagorean, van der
  Waerden (W(2,3..5) yeniden üretildi), Schur (S(2..3) yeniden üretildi).
  Ayrıntı: `docs/track-b-results.md`.
- **Arayüzler:** MCP sunucusu (**11 araç**) + `mathhead` komut satırı aracı (`--json`).
- Determinizm (sabit tohum + zaman aşımı), guardrail'ler, `unknown`/`error`
  birinci sınıf çıktı (dürüstlük). **66 otomatik test**, CI (GitHub Actions).

### Prensipler

Bağlam kaybı, fazla varsayım ve non-determinizme karşı: açık prensipler
(`PRINCIPLES.md`), karar günlüğü (`DECISIONS.md`, 13 ADR), ilerleme günlüğü
(`Progress.md`) ve net protokol (`docs/mcp-api.md`).
