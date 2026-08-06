# MathHead — Threat Model

> Companion to [`../SECURITY.md`](../SECURITY.md). This document is grounded in the actual code
> (`mathhead/compute/__init__.py`, `mathhead/guardrails/__init__.py`,
> `mathhead/server/mcp_server.py`, `mathhead/observability.py`) — where it names a limit, that
> limit is enforced and introspectable via the `resource_limits` tool.

## 1. What we are protecting

MathHead's core asset is **trust in a verdict**. Two things must hold:

1. **Soundness** — a `valid` / `verified` / `unsat` answer must be correct. A confidently wrong
   verdict is the worst possible failure for a verification engine, so soundness bugs are
   treated as security bugs.
2. **Integrity of the host** — answering a tool call must not let a crafted input execute code,
   touch the filesystem, open the network, or crash the server.

Availability (not hanging, not exhausting memory) is a goal too, but a *weaker* one, and the
honest limits below say exactly how far it is guaranteed.

## 2. Trust boundaries

```
   ┌─────────────┐   MCP tool call (JSON-RPC/stdio)   ┌──────────────────────────────┐
   │  AI client  │ ─────────────────────────────────▶ │  mathhead MCP server         │
   │ (host/LLM)  │   args: strings, lists, dicts       │  (this process)              │
   └─────────────┘ ◀───────────────────────────────── └──────────────┬───────────────┘
        UNTRUSTED        result dict (frozen envelope)                │
        INPUT                                                         ▼
                                                    ┌────────────────────────────────┐
                                                    │ guardrails  (size/depth fence)  │  ← boundary 1
                                                    ├────────────────────────────────┤
                                                    │ router → core (Z3) / compute    │
                                                    │           (SymPy, AST allowlist)│  ← boundary 2
                                                    └────────────────────────────────┘
```

- **Boundary 1 — the guardrail fence.** Every request crosses `validate_input` (count/length/
  depth) before any engine sees it. Reject-clean, never truncate.
- **Boundary 2 — the parse allowlist.** Every expression string crosses a whitelisting AST
  walker before it becomes a Z3 or SymPy object. Nothing is `eval`'d.

The AI client and everything it forwards (which may originate from an end user, a web page, or
another model) is treated as **fully untrusted**.

## 3. Attack surface

The only inputs are MCP tool arguments: expression strings, lists of statements, matrices
(lists of lists of strings), and a few scalars/enums. There is no auth surface (the transport is
a local stdio subprocess owned by the host), no persisted state beyond an in-memory
memoization cache and metrics ring, and no config file parsing at request time.

## 4. Threats and mitigations

| # | Threat | Vector | Mitigation (in code) | Residual |
|---|---|---|---|---|
| T1 | **Arbitrary code execution** | expression string like `__import__('os').system(...)`, `x.__class__.__bases__`, `lambda: ...` | `compute/_to_sympy` is an **allowlist** AST walker: only `BinOp(+ - * / **)`, unary sign, `Call` to the fixed `_FUNCS` set, `Name`, and int/float `Constant`. Every other node → `ComputeError`/`PARSE_ERROR`. No `sympify`/`eval`/`exec`. | None known — safety is by construction, not blocklist. Covered by fuzz + explicit rejection tests. |
| T2 | **Resource exhaustion via input size** | 10⁶ statements, a megabyte-long expression, deeply nested parens | Guardrail caps: `MAX_STATEMENTS=256`, `MAX_EXPRESSION_CHARS=4000`, `MAX_AST_DEPTH=64`. Clean `GUARDRAIL_VIOLATION`. | Bounds *size*, not *cost* — see T3. |
| T3 | **Resource exhaustion via cost** | a well-formed, in-size input that is expensive to compute (SymPy) | Z3 tools: hard `timeout=5000ms` + honest `SOLVER_TIMEOUT`. Per-tool numeric caps (`modal_max_worlds=12`, `prove_unsat_max_vars=20`, …). | **SymPy/pure-Python tools have no hard wall-clock/CPU/memory cap** (§5). Mitigate with OS-level limits. Documented, not silently assumed. |
| T4 | **Unsound verdict** (trust bug) | an input where the engine answers `valid`/`verified` but the claim is false | Independent cross-checking (`cross_check` = Z3 ⋈ SymPy), stdlib-only re-checkers (`check_certificate`, DRAT/DRUP), domain-aware equality, completeness checks; determinism (fixed seed). Large regression + fuzz + property suites. | Bugs still possible; reported as security-class. `unknown` is always allowed instead of a guess. |
| T5 | **Protocol stream corruption** | anything the server writes to stdout besides JSON-RPC | All diagnostics (startup profile line) go to **stderr** (`print(..., file=sys.stderr)`); results are returned through the SDK, not printed. | A no-stdout-leak e2e test pins this. |
| T6 | **Filesystem / network / process abuse** | a tool call that tries to make the engine read a file, call out, or spawn | Tool execution is pure compute; no such calls exist on the request path. Optional external binaries (`drat-trim`, CaDiCaL) are opt-in installs on explicit tool paths only. | Host must still sandbox if the threat is untrusted-at-scale (§5). |
| T7 | **Non-determinism / info leak via witness** | relying on a counterexample being stable | ADR-0019: the **verdict** is deterministic; a witness is *an* example and may vary. `meta.certainty` states the epistemic strength of each answer. | By design — callers must not treat a specific witness as canonical. |
| T8 | **`sympify` on the discovery surface** | a crafted statement passed to `mathhead.discovery.product.check()` or the `mathhead-discover` CLI | Unlike the core compute path (AST allowlist, boundary 2), the DISCOVERY layer parses statement fragments with `sympy.sympify` after its own regex routing — a deliberate, documented boundary. `check()` is an **operator/CLI surface** for the human running the engine, not an MCP tool: no MCP tool routes untrusted client input into `sympify`. Discovery-side fences still apply (route-wide 4000-digit constant refusal, modulus cap 10⁶, honest generation walls). | Treat discovery-surface input as trusted-operator input; do **not** pipe untrusted text into `check()`/`mathhead-discover` without OS-level sandboxing. Stated here rather than pretended away. |

## 5. The timeout / cost model, stated honestly

This is the most important honest limitation, so it gets its own section.

**Z3-backed tools are time-bounded.** The guardrail `solver_config` sets a Z3 `timeout` (default
**5000 ms**, reported by `resource_limits`). If Z3 hits it, the tool returns
`status="unknown"`, `reason_code="SOLVER_TIMEOUT"` — a wall, never a fabricated verdict. This
covers entailment/consistency/model, inequalities, induction, the SMT theories, modal logic,
QE, optimization, and the frontier reductions.

**SymPy and pure-Python tools are NOT wall-clock-bounded the same way.** There is no signal/
alarm-based timer around a SymPy call. Their protection is *upstream* (the input-size fences of
T2) and *per-tool* (numeric caps), not a timer. Consequences to be honest about:

- A well-formed, in-size expression can still make SymPy run long (e.g. a hard symbolic integral)
  or allocate a lot of memory (e.g. a very large series/expansion/factorial). The size fences
  make this hard to weaponize, but they do not make it impossible.
- Therefore, **for untrusted input at scale, wrap the process in OS-level limits** — a container
  with CPU/memory limits, `ulimit -t/-v`, or cgroups. MathHead bounds *what it parses* and *how
  long Z3 runs*; it does not bound *total* CPU/memory of an arbitrary SymPy computation.

Adding a hard cross-platform wall-clock timeout to the SymPy path (which needs care: `SIGALRM`
is POSIX-only and doesn't interrupt C extensions cleanly) is tracked as future work; until it
exists, this document does not pretend it is there.

## 6. Non-goals

MathHead is not a multi-tenant sandbox, not a secrets store, and not a network service. It runs
with the privileges of its launcher and expects the host to provide process isolation. It makes
no cryptographic claims. These are deliberate scope choices, not oversights.
