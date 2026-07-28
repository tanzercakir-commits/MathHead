# MathHead — Durum & Hata Taksonomisi

> **Bu dosyanın işi:** Motorun döndürebileceği TÜM `status` ve `reason_code`
> değerlerinin kanonik listesi. Yeni bir kod eklenirse burası **ve**
> `tests/test_taxonomy.py` birlikte güncellenir (test bu listeyi zorlar).
>
> İlke (PRINCIPLES): başarısızlık birinci sınıf çıktıdır — `unknown`/`error`
> gizlenmez. Her sonuç `status` (ne olduğu) + `reason_code` (neden) taşır.

---

## `status` — ne oldu?

```
Ortak
  unknown            · çözücü karar veremedi (timeout / yarı-karar-verilebilir)
  error              · girdi/gramer hatası ya da hesap başarısız

Mantık — entailment / prove
  valid              · öncüller sonucu gerektirir (⊨)
  invalid            · gerektirmez (karşıörnek var)

Mantık — consistency / find_model / enumerate / Track B
  sat                · sağlanabilir (model/boyama var)
  unsat              · sağlanamaz (çelişki / imkânsızlık ispatı)

Sınıflandırma — classify
  tautology | contradiction | contingent

Denklik — equivalent
  equivalent | not_equivalent

Optimizasyon — optimize / maxsat
  optimal            · en iyi çözüm bulundu
  unbounded          · amaç sınırsız (optimize)

Hesap — compute (SymPy)
  ok                 · hesap başarılı
```

## `reason_code` — neden?

```
BAŞARI (status: ok/valid/sat/optimal/...)
  OK                     · hesap tamam (compute)
  ENTAILED               · ⊨ doğrulandı
  CONSISTENT             · birlikte sağlanabilir
  MODEL_FOUND            · somut model bulundu
  MODELS_FOUND           · çoklu model (sınır)  ·  ALL_MODELS_FOUND · tümü
  TAUTOLOGY / CONTRADICTION / CONTINGENT       · classify sonucu
  EQUIVALENT / NOT_EQUIVALENT                  · denklik sonucu
  OPTIMAL                · optimum bulundu  ·  UNBOUNDED · sınırsız  ·  OPEN_BOUND · açık sınır
  COLORING_FOUND         · Track B: boyama bulundu (sat)

BAŞARISIZLIK / KARŞITLIK (status: invalid/unsat/error/unknown)
  COUNTEREXAMPLE_FOUND   · karşıörnek (invalid)
  CONTRADICTION          · çelişki (unsat)
  NO_MODEL               · model yok
  PROVEN_IMPOSSIBLE      · Track B: imkânsızlık ispatı (unsat)  ·  NO_COLORING
  INFEASIBLE             · kısıtlar sağlanamaz (optimize)  ·  HARD_INFEASIBLE (maxsat)
  PARSE_ERROR            · girdi grameri/beyaz-liste ihlali (compute)
  COMPUTE_FAILED         · hesap kapalı-formda başarısız (compute; ör. tekil matris)
  GUARDRAIL_VIOLATION    · çit ihlali (mantık girdisi: sözdizimi/uzunluk/sembol)
  SOLVER_TIMEOUT         · zaman aşımı  ·  SOLVER_UNKNOWN · çözücü 'unknown'
  UNEXPECTED_SAT         · beklenmeyen sat (iç tutarlılık kontrolü)

DOĞRULAMA KATMANI (Track C — AI muhakeme denetçisi)
  EQUAL                  · ifadeler denk (valid)
  EQUAL_ON_COMMON_DOMAIN · ortak tanım kümesinde denk, tanım kümeleri ayrışıyor (valid + uyarı)
  NOT_EQUAL              · denk değil, karşıörnek var (invalid)
  SOLUTION_VERIFIED      · çözümler doğru + TAM (valid)
  SOLUTION_INCORRECT     · en az bir iddia edilen değer çözüm değil (invalid)
  SOLUTION_INCOMPLETE    · değerler doğru ama eksik (kaçan çözüm) (invalid)
  COMPLETENESS_UNKNOWN   · değerler tutar ama tümü doğrulanamadı (unknown)
  STEPS_VALID            · adım zincirinin tüm geçişleri denk (valid)
  STEP_INVALID           · ilk hatalı geçiş bulundu (invalid)
  UNDECIDED              · denklik/geçiş kararlaştırılamadı (unknown)

ÇAPRAZ DENETİM (Track C3 — Z3 ⋈ SymPy)
  CONSENSUS_EQUAL        · iki motor da 'denk' (valid, yüksek güven)
  CONSENSUS_NOT_EQUAL    · iki motor da 'denk değil' (invalid)
  ENGINES_DISAGREE       · motorlar çelişiyor — ince konu/domain bayrağı (unknown)
  SINGLE_ENGINE          · yalnız bir motor karar verdi (valid/invalid, düşük güven)
  CROSS_UNDECIDED        · hiçbir motor karar veremedi (unknown)
```

**Değişmez (test_taxonomy):** her araç çağrısı yalnız yukarıdaki `status` ve
`reason_code` kümelerinden değer döndürür; `error` durumunda uydurma sonuç
üretilmez. Yeni kod = bu doküman + test birlikte güncellenir.
