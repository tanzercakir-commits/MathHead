# MathHead — Mimari

Katmanlı hibrit. Her katmanın **tek** sorumluluğu var; dış dünya motora yalnızca
MCP katmanından dokunur. Kararların gerekçesi `../DECISIONS.md`'de.

## Katman şeması

```mermaid
flowchart TD
    AI["AI / Claude<br/>(MCP istemcisi)"] -->|araç çağrısı| S["server/<br/>MCP arayüzü · tek sözleşme"]
    S --> G["guardrails/ · ÇİT<br/>girdi doğrulama · timeout · seed"]
    G --> R["router/<br/>yönlendirme"]
    R -->|mantık| C["core/ · Z3 (SMT)<br/>entailment · consistency · model"]
    R -->|hesap · v2+| K["compute/ · SymPy (CAS)"]
    C --> RES["ReasoningResult"]
    K --> RES
    RES --> S
    S --> AI
```

## Katman sorumlulukları

| Katman | Yapar | YAPMAZ (sınırı) | Dosya |
|---|---|---|---|
| `server/` | MCP araçlarını yayınlar, çıktıyı sözlüğe çevirir | İş mantığı içermez | `server/mcp_server.py` |
| `guardrails/` | Girdiyi doğrular, çözücüyü sınırlar/deterministik yapar | Matematik çözmez | `guardrails/__init__.py` |
| `router/` | Görevi doğru çözücü + ilkele yönlendirir (kurallı) | "Sezgiyle" seçmez | `router/__init__.py` |
| `core/` | Z3 ile entailment / consistency / model | Girdi ayrıştırmasını *tek başına* yapmaz (translate) | `core/logic.py`, `core/translate.py` |
| `compute/` | (v2+) SymPy ile solve/simplify/kalkülüs | v1'de boş (rezerve) | `compute/__init__.py` |

## İstek yaşam döngüsü (request lifecycle)

```mermaid
sequenceDiagram
    participant AI as AI (Claude)
    participant MCP as server (MCP)
    participant GR as guardrails
    participant RT as router
    participant Z3 as core / Z3
    AI->>MCP: entailment(premises, conclusion)
    MCP->>GR: validate_input()
    alt girdi geçersiz / çit ihlali
        GR-->>AI: status=error (net gerekçe, tahmin YOK)
    else geçerli
        GR->>RT: route("entailment", payload)
        RT->>Z3: (⋀ premises) ∧ ¬conclusion  UNSAT?
        Z3-->>RT: unsat=valid · sat=karşıörnek · unknown
        RT-->>MCP: ReasoningResult
        MCP-->>AI: {status, witness, explanation, meta}
    end
```

## Determinizm nasıl garanti edilir?

- **Sabit tohum (seed)** + **tek iş parçacığı**: Z3 yapılandırması `solver_config()`
  ile sabitlenir → aynı girdi, aynı arama yolu, aynı çıktı.
- **Zaman aşımı (timeout)**: worst-case sınırı; süre dolarsa `unknown` (hata değil).
- **İzlenebilir `meta`**: her yanıt hangi çözücü/sürüm/seed/süre ile üretildiğini
  taşır → sonuç *yeniden üretilebilir*.

> Bu üç mekanizma, senin **3. duvarına** (non-determinizm) mimari cevaptır:
> non-determinizmi yok saymıyoruz, çitle sınırlıyoruz.
