# MathHead

![CI](https://github.com/tanzercakir-commits/MathHead/actions/workflows/ci.yml/badge.svg)

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
git clone https://github.com/tanzercakir-commits/MathHead && cd MathHead
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

mathhead-server        # MCP sunucusunu stdio ile başlat
pytest -q              # testler → 17/17 yeşil
```

## Kullanım (v1)

Python'dan:

```python
from mathhead.core import check_entailment, check_consistency, find_model

check_entailment(["p", "implies(p, q)"], "q")   # -> status="valid"
check_entailment(["x > 0"], "x > 5")             # -> "invalid", witness={"x": 1}
check_consistency(["p", "not(p)"])               # -> "unsat" + unsat core
find_model(["x > 2", "x < 5"])                    # -> "sat", witness={"x": 3}

from mathhead.compute import solve, differentiate, integrate   # v2 (SymPy)
solve("x**2 == 4", "x")                           # -> ["-2", "2"]
differentiate("x**3 + 2*x", "x")                  # -> "3*x**2 + 2"
integrate("2*x", "x")                             # -> "x**2"
```

MCP istemcisine (ör. Claude Code) bağlamak:

```bash
claude mcp add mathhead -- mathhead-server
```

Girdi dili (gramer) ve araç sözleşmesi: `docs/mcp-api.md`.

Terminalden (CLI):

```bash
mathhead entail -p "p" -p "implies(p, q)" -c "q"          # -> valid
mathhead entail -p "forall(x, implies(Man(x), Mortal(x)))" \
                -p "Man(socrates)" -c "Mortal(socrates)"  # silogizm -> valid
mathhead solve "x**2 == 4" x                              # -> ['-2', '2']
mathhead pigeonhole 4                                     # -> unsat (ispat)
mathhead --json consistent "x > 2" "x < 5"                # ham JSON
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

Apache-2.0 — bkz. `LICENSE`.
