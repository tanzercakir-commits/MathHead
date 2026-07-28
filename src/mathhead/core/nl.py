"""
mathhead.core.nl — Natural language → formal (ROADMAP I2). A direct antidote to
"wall #2" (excessive assumptions).

**Design principle — RECOGNIZE-OR-REFUSE:** MathHead is NOT a full natural-language
parser (that job belongs to the LLM; and it is exactly there that the "assumption"
error is born). Only a **rule-based, transparent, bounded** subset is recognized
here; on unrecognized/ambiguous input it **does not guess** — it refuses honestly.

**Round-trip (back-translation) verification — the star feature:** input NL → a
formal task is produced, then formal → NL **restatement** (`restatement`) is
returned. This lets the caller (AI/human) SEE "what did MathHead understand?" and
confirm it BEFORE trusting it. A misreading is caught before it turns into a silent
assumption.

Mixed TR + EN input is supported (the user writes in Turkish). Recognized
operations: derivative, integral, limit, solve, factorization, primality, GCD,
equivalence.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any

__all__ = ["NLResult", "interpret"]


@dataclass
class NLResult:
    status: str                       # ok | unknown | error
    reason_code: str                  # UNDERSTOOD | AMBIGUOUS | UNRECOGNIZED | PARSE_ERROR
    explanation: str
    interpretation: dict[str, Any] | None = None   # {task, payload, restatement}
    meta: dict[str, Any] = field(default_factory=dict)


def _meta(t0: float) -> dict[str, Any]:
    return {"engine": "nl-rules", "elapsed_ms": round((time.perf_counter() - t0) * 1000, 3)}


# Word → symbol (deterministic, bounded). Order matters (longer patterns first).
_PHRASES: list[tuple[str, str]] = [
    (r"\bkarekök(?:ü)?\s+", "sqrt "), (r"\bsquare\s+root\s+of\s+", "sqrt "),
    (r"\bküpü?\b", "**3"), (r"\bcubed\b", "**3"),
    (r"\bkaresi?\b", "**2"), (r"\bsquared\b", "**2"),
    (r"\bçarpı\b", "*"), (r"\btimes\b", "*"), (r"\bmultiplied\s+by\b", "*"),
    (r"\bbölü\b", "/"), (r"\bdivided\s+by\b", "/"), (r"\bover\b", "/"),
    (r"\bartı\b", "+"), (r"\bplus\b", "+"),
    (r"\beksi\b", "-"), (r"\bminus\b", "-"),
    (r"\büzeri\b", "**"), (r"\bto\s+the\s+power\s+of\b", "**"),
]


def _normalize(expr: str) -> str:
    """Converts word-operators to symbols + wraps `sqrt X` → `sqrt(X)`. Bounded, transparent."""
    s = expr.strip().strip(".?!").strip()
    for pat, rep in _PHRASES:
        s = re.sub(pat, rep, s, flags=re.IGNORECASE)
    # 'sqrt X' → 'sqrt(X)' (single term)
    s = re.sub(r"\bsqrt\s+([A-Za-z0-9_]+)", r"sqrt(\1)", s)
    return re.sub(r"\s+", " ", s).strip()


def _point(word: str) -> str:
    w = word.strip().strip(".?!").lower()
    if w in ("sonsuz", "sonsuza", "infinity", "infinite", "inf", "oo", "+oo", "+sonsuz"):
        return "oo"
    if w in ("eksi sonsuz", "eksi sonsuza", "-oo", "-infinity", "-sonsuz", "negatif sonsuz"):
        return "-oo"
    return _normalize(word)


# (task, restatement builder) — each pattern returns a matcher.
def _restate(task: str, p: dict[str, Any]) -> str:
    if task == "differentiate":
        o = f" (order {p['order']})" if p.get("order", 1) != 1 else ""
        return f"the derivative of '{p['expression']}' with respect to '{p['symbol']}'{o}"
    if task == "integrate":
        return f"the integral of '{p['expression']}' with respect to '{p['symbol']}'"
    if task == "limit":
        return f"the limit of '{p['expression']}' as '{p['symbol']}' → {p['point']}"
    if task == "solve":
        return f"the solution of '{p['equation']}' for '{p['symbol']}'"
    if task == "factorize":
        return f"the prime factorization of {p['n']}"
    if task == "gcd":
        return f"the greatest common divisor (GCD) of {p['a']} and {p['b']}"
    if task == "is_prime":
        return f"whether {p['n']} is prime"
    if task == "verify_equality":
        return f"whether '{p['left']}' and '{p['right']}' are equivalent"
    return f"{task}({p})"


# Regex patterns: (pattern, task, payload builder from groups).
# NOTE: Turkish keywords in these patterns (türev, ifadesinin, göre, asal mı, ile,
# en büyük ortak bölen, ...) are INPUT-matching data — kept to preserve the
# bilingual TR+EN feature. Do not translate them.
_PATTERNS: list[tuple[str, str, Any]] = [
    (r"(?:(\d+)\.?\s*(?:mertebeden|order)\s+)?(?:türev(?:i)?|derivative)\s+(?:of\s+)?(.+?)\s+"
     r"(?:with\s+respect\s+to|göre|için)\s+([A-Za-z]\w*)",
     "differentiate", lambda m: {"expression": _normalize(m.group(2)), "symbol": m.group(3),
                                 "order": int(m.group(1)) if m.group(1) else 1}),
    (r"(.+?)\s+ifadesinin\s+([A-Za-z]\w*)(?:['\s]*[eay]+)?\s*göre\s+türev",
     "differentiate", lambda m: {"expression": _normalize(m.group(1)), "symbol": m.group(2),
                                 "order": 1}),
    (r"(?:integral(?:i)?)\s+(?:of\s+)?(.+?)\s+(?:with\s+respect\s+to|göre|için)\s+([A-Za-z]\w*)",
     "integrate", lambda m: {"expression": _normalize(m.group(1)), "symbol": m.group(2)}),
    (r"(.+?)\s+ifadesinin\s+([A-Za-z]\w*)(?:['\s]*[eay]+)?\s*göre\s+integral",
     "integrate", lambda m: {"expression": _normalize(m.group(1)), "symbol": m.group(2)}),
    (r"(?:limit(?:i)?)\s+(?:of\s+)?(.+?)\s+(?:as\s+)?([A-Za-z]\w*)\s+"
     r"(?:approaches|goes\s+to|tends\s+to|→|->)\s+(.+)",
     "limit", lambda m: {"expression": _normalize(m.group(1)), "symbol": m.group(2),
                         "point": _point(m.group(3))}),
    (r"(.+?)\s+ifadesinin\s+([A-Za-z]\w*)\s*(?:→|->|,)\s*(.+?)\s+limit",
     "limit", lambda m: {"expression": _normalize(m.group(1)), "symbol": m.group(2),
                         "point": _point(m.group(3))}),
    (r"(?:solve|çöz)\s+(.+?)\s+(?:for|için)\s+([A-Za-z]\w*)",
     "solve", lambda m: {"equation": _normalize(m.group(1)), "symbol": m.group(2)}),
    (r"(.+?)\s+denklemini\s+([A-Za-z]\w*)\s+için\s+çöz",
     "solve", lambda m: {"equation": _normalize(m.group(1)), "symbol": m.group(2)}),
    (r"(?:factor(?:ize)?|çarpanlar(?:ın)?a\s+ayır)\s+(\d+)",
     "factorize", lambda m: {"n": m.group(1)}),
    (r"(\d+)\s+(?:sayısını\s+)?çarpanlar",
     "factorize", lambda m: {"n": m.group(1)}),
    (r"(?:gcd|ebob|greatest\s+common\s+divisor|en\s+büyük\s+ortak\s+bölen)\s+"
     r"(?:of\s+)?(\d+)\s+(?:and|ile|,)\s+(\d+)",
     "gcd", lambda m: {"a": m.group(1), "b": m.group(2)}),
    (r"(\d+)\s+ile\s+(\d+)\s*(?:'?\w+)?\s+(?:en\s+büyük\s+ortak\s+böl(?:en|eni)?|ebob)",
     "gcd", lambda m: {"a": m.group(1), "b": m.group(2)}),
    (r"(?:is\s+)?(\d+)\s+(?:asal\s+mı|prime|bir\s+asal|asal)",
     "is_prime", lambda m: {"n": m.group(1)}),
    (r"(.+?)\s+(?:ile\s+)?(.+?)\s+(?:denk\s+mi|eşit\s+mi|equal\s+to|equals)",
     "verify_equality", lambda m: {"left": _normalize(m.group(1)), "right": _normalize(m.group(2))}),
]


def interpret(text: str) -> NLResult:
    """Translates a natural-language math statement into a formal task (recognize-or-refuse).

    ok + UNDERSTOOD → `interpretation` {task, payload, restatement}; `restatement`
    restates what MathHead understood in NL (CONFIRM-then-trust).
    unknown + AMBIGUOUS → multiple interpretations. error + UNRECOGNIZED → not
    recognized (NO guessing).
    """
    t0 = time.perf_counter()
    if not isinstance(text, str) or not text.strip():
        return NLResult("error", "PARSE_ERROR", "empty input.", None, _meta(t0))
    raw = text.strip()
    matches = []
    for pat, task, build in _PATTERNS:
        m = re.search(pat, raw, flags=re.IGNORECASE)
        if m:
            try:
                payload = build(m)
            except (ValueError, IndexError):
                continue
            matches.append((task, payload))

    if not matches:
        return NLResult("error", "UNRECOGNIZED",
                        "not recognized — no guessing. Supported: derivative/integral/limit/"
                        "solve/factorization/primality/GCD/equivalence. A formal grammar may "
                        "also be used (see docs/mcp-api.md).", None, _meta(t0))
    # If matches map to different TASKS, it is ambiguous (honest)
    distinct = {t for t, _ in matches}
    if len(distinct) > 1:
        opts = [{"task": t, "payload": p, "restatement": _restate(t, p)} for t, p in matches]
        return NLResult("unknown", "AMBIGUOUS",
                        "multiple interpretations are possible — please clarify or write it "
                        "formally.",
                        {"candidates": opts}, _meta(t0))
    task, payload = matches[0]
    restatement = _restate(task, payload)
    return NLResult("ok", "UNDERSTOOD",
                    f"Understood: {restatement}. (Confirm this BEFORE trusting it.)",
                    {"task": task, "payload": payload, "restatement": restatement}, _meta(t0))
