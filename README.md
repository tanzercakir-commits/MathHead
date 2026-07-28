# MathHead

AI'ın (ör. Claude) **MCP** üzerinden çağırabileceği, first-order logic temelli,
**deterministik** bir matematik akıl yürütme ve ispat motoru.

> **Fikir:** LLM'ler katı mantık/ispatta güvenilmez (non-deterministik, varsayıma
> açık). MathHead bu işi gerçek bir motora (SMT çözücü **Z3** + sembolik hesap
> **SymPy**) devrederek "uydurma" payını düşürür.

## Durum

**v0 — iskelet & tasarım.** Yapı, sözleşmeler ve tasarım dosyaları hazır; çekirdek
gövdeleri v1'de doldurulacak. Yol için `Todo.md`, hedef için `Plan.md`.

## Hızlı başlangıç

```bash
git clone <repo> && cd mathhead
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

mathhead-server        # MCP sunucusunu stdio ile başlat
pytest -q              # testler (v0: smoke geçer, logic spec xfail)
```

## Yapı

```
mathhead/
├── README.md            · bu dosya
├── Plan.md              · hedef mimari + yol haritası (değişmeye dirençli)
├── Todo.md              · şu anki işler + öncelikler (sık değişir)
├── Progress.md          · ne yaptık / ne zaman (append-only günlük)
├── PRINCIPLES.md        · değişmez proje kuralları (çit felsefesi)
├── DECISIONS.md         · karar günlüğü (ADR) — kararlar kaybolmasın
├── pyproject.toml       · bağımlılıklar (z3-solver, sympy, mcp[cli])
├── docs/
│   ├── architecture.md  · katman şeması (Mermaid) + istek yaşam döngüsü
│   ├── mcp-api.md        · net MCP protokol & araç tanımları + gramer
│   └── glossary.md       · terimler (FOL, SMT, CAS, entailment...)
├── src/mathhead/
│   ├── core/            · mantık çekirdeği (Z3) — logic.py, translate.py  [v1]
│   ├── compute/         · sembolik hesap (SymPy)                          [v2+]
│   ├── router/          · yönlendirme
│   ├── guardrails/      · çit: doğrulama, timeout, determinizm
│   └── server/          · MCP sunucusu (FastMCP, 3 araç)
└── tests/               · smoke (geçer) + logic spec (best/worst, xfail)
```

## Nereden okumaya başlamalı?

`Plan.md` (büyük resim) → `docs/architecture.md` (katmanlar) →
`docs/mcp-api.md` (sözleşme) → `Todo.md` (sıradaki iş).

## Lisans

MIT.
