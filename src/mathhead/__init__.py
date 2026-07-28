"""
MathHead
========

AI'ın (ör. Claude) MCP üzerinden çağırabileceği, first-order logic temelli,
DETERMINISTIK bir matematik akıl yürütme ve ispat motoru.

Temel fikir: LLM'ler mantık/ispatta güvenilmez (non-deterministik, varsayıma
açık). MathHead bu işi gerçek, deterministik bir motora (SMT çözücü Z3 +
sembolik hesap SymPy) devrederek "uydurma" payını düşürür.

Katmanlar (bkz. docs/architecture.md):
    server/     -> MCP arayüzü (dış dünya ile tek sözleşme)
    router/     -> gelen problemi doğru çözücüye yönlendirir
    core/       -> mantık çekirdeği (Z3 sarmalayıcı) [v1 odağı]
    compute/    -> sembolik hesap (SymPy)            [v2+]
    guardrails/ -> çit: girdi doğrulama, zaman aşımı, determinizm ayarları
"""

__version__ = "0.0.1"
