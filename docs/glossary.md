# MathHead — Sözlük (Glossary)

Projede geçen terimler, kısa ve Türkçe. Amaç: yeni bir oturum (ya da yeni bir
kişi/AI) bağlama hızlı girsin (duvar #1'e karşı).

- **FOL (First-Order Logic / Birinci Dereceden Mantık):** Nesneler, yüklemler
  (predicate) ve `∀/∃` nicelik belirteçleri içeren mantık. Önermeler mantığından
  daha ifadeli.

- **Önermeler mantığı (propositional logic):** Yalnızca doğru/yanlış değişkenler
  ve `and/or/not/implies/iff`. FOL'un nicelik belirteci olmayan alt kümesi. v1'in
  çekirdek parçası.

- **SMT (Satisfiability Modulo Theories):** SAT'ın üstüne *teoriler* (aritmetik,
  eşitlik, diziler...) ekleyen karar problemi. **Z3** bir SMT çözücüsüdür. Bizim
  "FOL + hazır teoriler" cümlemizin teknik adı budur.

- **CAS (Computer Algebra System / Bilgisayar Cebir Sistemi):** Sembolik
  hesaplama (sadeleştirme, denklem çözme, türev/integral). **SymPy** bir CAS'tır.
  MathHead'de *hesap* katmanı (v2+).

- **entailment (mantıksal gerektirme, `⊨`):** Öncüller doğruyken sonucun *zorunlu*
  doğru olması. Kontrol yöntemi: `(öncüller) ∧ ¬sonuç` **UNSAT** mı?

- **satisfiability (sat / tatmin edilebilirlik):** Bir formülü doğru yapan en az
  bir atama var mı? Varsa **SAT**, yoksa **UNSAT**.

- **model:** Bir formülü doğru kılan somut değişken ataması (ör. `x = 3`). SAT'ın
  tanığı (witness).

- **karşıörnek (counterexample):** Bir iddiayı *çürüten* somut atama. entailment
  geçersizse motor bunu döndürür.

- **unsat core:** Bir kümeyi çelişkili yapan *en küçük* suçlu alt küme. Neden
  tutarsız olduğunu gösterir.

- **decidability (karar verilebilirlik):** Bir problemi *her zaman* sonlandırıp
  yanıtlayan algoritma var mı? Önermeler mantığı karar verilebilir; genel FOL
  **yarı**-karar verilebilir (semi-decidable) → motor bazen `unknown` döner.

- **guardrail (çit):** Motorun aşamayacağı sert sınır (boyut, süre, sembol).
  Kullanıcının "çitin dışına çıkmamalı" maddesinin karşılığı.

- **determinizm:** Aynı girdi → aynı çıktı. Sabit tohum + zaman aşımı + tek iş
  parçacığı ile sağlanır.

- **MCP (Model Context Protocol):** AI istemcilerinin (ör. Claude) dış araçlara
  standart biçimde bağlandığı protokol. MathHead buradan yayınlanır.

- **ADR (Architecture Decision Record):** Bir mimari kararı gerekçesiyle saklayan
  kısa kayıt. `DECISIONS.md`'de tutulur.

- **vertical slice (dikey dilim):** Uçtan uca (arayüzden çekirdeğe) *çalışan* dar
  bir özellik. v1 stratejimiz.
