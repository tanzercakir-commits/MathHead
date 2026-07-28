"""
MathHead
========

A DETERMINISTIC, first-order-logic-based mathematical reasoning and proof
engine that an AI (e.g. Claude) can invoke over MCP.

Core idea: LLMs are unreliable at logic/proof (non-deterministic, prone to
unwarranted assumptions). MathHead delegates that work to a real,
deterministic engine (the SMT solver Z3 + symbolic computation via SymPy),
reducing the room for "making things up".

Layers (see docs/architecture.md):
    server/     -> MCP interface (the single contract with the outside world)
    router/     -> routes the incoming problem to the right solver
    core/       -> logic kernel (Z3 wrapper)         [v1 focus]
    compute/    -> symbolic computation (SymPy)      [v2+]
    guardrails/ -> the fence: input validation, timeouts, determinism settings
"""

__version__ = "1.0.1"
