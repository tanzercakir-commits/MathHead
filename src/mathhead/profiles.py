"""
mathhead.profiles — Capability packs + tool triage (ROADMAP L3).

168 tools is a large surface for an LLM to choose from (the external review's #3): it
hurts tool-selection accuracy and inflates context. This module:

  * groups every tool into a **capability pack** (core / logic / symbolic / numerical /
    frontier / observability);
  * lets a server expose only the packs a user wants via `MATHHEAD_PROFILE`
    (default `core` — the verification differentiator ~20 tools; `full` = everything);
  * adds three always-present **triage tools** — `list_capabilities`, `describe_tool`,
    `recommend_tool` — so an AI can discover what exists and pick the right tool (and
    learn how to enable more) even from a small default profile.

The full catalog is snapshotted at import (before any profile filtering), so the triage
tools always describe every tool, including ones the current profile has hidden.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any

from mathhead.certainty import _FRONTIER, _NUMERICAL, certainty_of, stability_of

# MCP tool name -> router task name (a few differ)
_TASK = {"model": "find_model", "enumerate_models": "enumerate", "max_satisfy": "maxsat"}

# tools that are ALWAYS exposed, whatever the profile (discovery must never be hidden)
ALWAYS = {"list_capabilities", "describe_tool", "recommend_tool"}

PACKS: dict[str, str] = {
    "core": "The verification differentiator — verify_*, cross_check, certificates, "
            "entailment/consistency/model. The stable core.",
    "logic": "Logic & proof depth — optimize/maxsat, induction, SMT theories, quantifier "
             "elimination, modal logic, inequalities, CNF solving.",
    "symbolic": "Symbolic computation (CAS) — algebra, calculus, linear algebra, number "
                "theory, combinatorics, transforms, statistics.",
    "numerical": "Numerical methods — root finding, quadrature, RK4, precision, numeric checks.",
    "frontier": "Frontier SAT reductions — N-queens, Sudoku, Ramsey, graph coloring, TSP, …",
    "observability": "Introspection/admin — metrics, resource limits, cache, and this triage.",
}


def pack_of(mcp_name: str) -> str:
    """The capability pack a tool belongs to (by stability tier + category)."""
    if mcp_name in ALWAYS:
        return "observability"
    task = _TASK.get(mcp_name, mcp_name)
    tier = stability_of(task)
    if tier == "stable":
        return "core"
    if tier == "provisional":
        return "logic"
    if tier == "internal":
        return "observability"
    if mcp_name in _NUMERICAL:
        return "numerical"
    if mcp_name in _FRONTIER:
        return "frontier"
    return "symbolic"


# --------------------------------------------------------------------------- #
# Catalog (full, snapshotted before profile filtering)
# --------------------------------------------------------------------------- #
_CATALOG: dict[str, dict[str, Any]] = {}


def _ensure_catalog() -> None:
    """Populate the catalog if empty — importing the MCP server (whose module-end snapshots
    the FULL tool set, before any profile filtering). A no-op once populated; safe from any
    caller (router/CLI/tests) regardless of import order, with no import cycle (lazy)."""
    if not _CATALOG:
        import mathhead.server.mcp_server  # noqa: F401


def snapshot_catalog(mcp: Any) -> None:
    """Record every currently-registered tool (name/description/pack/stability/schema)."""
    _CATALOG.clear()
    for name, tool in mcp._tool_manager._tools.items():
        first = (tool.description or "").strip().splitlines()
        _CATALOG[name] = {
            "description": first[0].strip() if first else "",
            "pack": pack_of(name),
            "stability": "internal" if name in ALWAYS else stability_of(_TASK.get(name, name)),
            "input_schema": getattr(tool, "parameters", {}) or {},
        }


def select_packs(profile: str | None) -> set[str]:
    """Parse a `MATHHEAD_PROFILE` value into a set of pack names (unset → the curated `core`)."""
    p = (profile or "core").strip().lower()
    if p in ("full", "all", "*"):
        return set(PACKS)
    chosen = {x.strip().lower() for x in p.split(",") if x.strip()}
    valid = chosen & set(PACKS)
    return valid or {"core"}


def apply_profile(mcp: Any, packs: set[str]) -> list[str]:
    """Remove tools whose pack is not selected (triage tools are always kept).
    Returns the list of kept tool names. Call ONLY at server startup."""
    kept = []
    for name in list(mcp._tool_manager._tools.keys()):
        if name in ALWAYS or pack_of(name) in packs:
            kept.append(name)
        else:
            mcp._tool_manager.remove_tool(name)
    return sorted(kept)


# --------------------------------------------------------------------------- #
# Triage tools
# --------------------------------------------------------------------------- #
@dataclass
class CapabilitiesResult:
    status: str
    reason_code: str
    explanation: str
    packs: dict[str, Any] = field(default_factory=dict)
    total_tools: int = 0
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolInfoResult:
    status: str
    reason_code: str
    explanation: str
    tool: dict[str, Any] | None = None
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class RecommendResult:
    status: str
    reason_code: str
    explanation: str
    recommendations: list[dict[str, Any]] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)


def _meta(t0: float) -> dict[str, Any]:
    return {"engine": "profiles", "elapsed_ms": round((time.perf_counter() - t0) * 1000, 3)}


def list_capabilities() -> CapabilitiesResult:
    """The capability packs, each with its tool count and a sample — how to navigate 168 tools."""
    t0 = time.perf_counter()
    _ensure_catalog()
    by_pack: dict[str, list[str]] = {}
    for name, info in sorted(_CATALOG.items()):
        by_pack.setdefault(info["pack"], []).append(name)
    packs = {
        pack: {"description": desc, "tool_count": len(by_pack.get(pack, [])),
               "sample": by_pack.get(pack, [])[:6]}
        for pack, desc in PACKS.items()
    }
    return CapabilitiesResult(
        "ok", "CAPABILITIES",
        "Tools are grouped into capability packs. The default server profile exposes the `core` "
        "pack (verification); set MATHHEAD_PROFILE=full (or e.g. core,symbolic) to expose more. "
        "Use describe_tool / recommend_tool to pick a tool.",
        packs, len(_CATALOG), _meta(t0))


def describe_tool(name: str) -> ToolInfoResult:
    """Full metadata for one tool (description, input schema, pack, stability) — even if the
    current profile has it hidden, so an AI knows what to enable."""
    t0 = time.perf_counter()
    _ensure_catalog()
    info = _CATALOG.get(name)
    if info is None:
        return ToolInfoResult("error", "UNKNOWN_TOOL",
                              f"no tool named {name!r}; try recommend_tool or list_capabilities.",
                              meta=_meta(t0))
    return ToolInfoResult("ok", "TOOL_INFO", f"{name}: {info['description']}",
                          {"name": name, **info}, _meta(t0))


def recommend_tool(query: str, limit: int = 5) -> RecommendResult:
    """Given a natural-language task, suggest the best-matching tools (name + why + how to enable).
    A keyword-overlap heuristic over tool names and descriptions — a navigation aid, not a solver."""
    t0 = time.perf_counter()
    _ensure_catalog()
    if not isinstance(query, str) or not query.strip():
        return RecommendResult("error", "GUARDRAIL_VIOLATION", "query must be a non-empty string",
                               meta=_meta(t0))
    tokens = [w for w in re.split(r"[^a-z0-9]+", query.lower()) if len(w) > 2]
    scored = []
    for name, info in _CATALOG.items():
        hay = (name + " " + info["description"]).lower()
        score = sum(1 for w in set(tokens) if w in hay)
        if name.lower() in query.lower():
            score += 3
        if score:
            scored.append((score, name, info))
    scored.sort(key=lambda s: (-s[0], s[1]))
    recs = [{"tool": n, "pack": i["pack"], "stability": i["stability"],
             "description": i["description"], "score": sc} for sc, n, i in scored[:max(1, limit)]]
    if not recs:
        return RecommendResult("unknown", "NO_MATCH",
                               "No tool matched; call list_capabilities to browse the packs.",
                               meta=_meta(t0))
    return RecommendResult("ok", "RECOMMENDATIONS",
                           f"{len(recs)} candidate tool(s) for {query!r} (best first).",
                           recs, _meta(t0))


# certainty/stability annotation reads these result types' meta too — reuse certainty_of via meta.
_ = certainty_of  # (kept for symmetry; annotation happens in the router)
