# Security Policy

MathHead is a **deterministic math-verification engine** an AI calls over MCP. Its whole
purpose is trust, so its security model is part of the product, not an afterthought. This file
says what MathHead defends against, what it deliberately does **not**, and how to report a
problem.

## Reporting a vulnerability

Please report privately — do **not** open a public issue for a security bug.

- Use GitHub's **"Report a vulnerability"** (Security → Advisories) on
  `tanzercakir-commits/MathHead`, which opens a private advisory thread.
- Include: what you observed, a minimal reproduction (the exact tool call / expression), and
  the impact you think it has.

We aim to acknowledge a report within a few days, agree on severity, and fix confirmed issues
on `main` before any public disclosure. There is no bounty program; credit is given in the
advisory unless you prefer otherwise.

## Supported versions

| Version | Supported |
|---|---|
| latest `main` / latest `1.0.x` | ✅ security fixes land here |
| older `0.x` pre-release tags | ❌ |

MathHead is not yet published to PyPI; "supported" means the current source tree.

## The security model (what is defended, by design)

The threat model is documented in full in [`docs/threat-model.md`](docs/threat-model.md); the
short version:

- **No arbitrary code execution from expression strings.** The computation layer never uses
  `sympify`, `eval`, or `exec`. Every expression is parsed with Python's `ast` module and then
  walked through a strict **allowlist** (`mathhead/compute/__init__.py::_to_sympy`): only
  arithmetic (`+ - * / **`), unary sign, calls to a fixed set of math functions
  (`sin`, `cos`, `exp`, `log`, `sqrt`, …), named symbols/constants, and integer/float literals
  are accepted. Any other AST node — attribute access (`x.__class__`), an un-listed call
  (`__import__(...)`), a lambda, a subscript — is rejected with a clean `PARSE_ERROR`. Safety is
  by construction (allowlist), not by blocklisting known-bad strings.
- **Hard input fences, no silent truncation.** The guardrail layer
  (`mathhead/guardrails`) rejects oversized input up front: at most **256** statements, **4000**
  characters per expression, **AST depth 64**. Violations raise a clear `GUARDRAIL_VIOLATION`;
  input is never quietly cut down or "fixed".
- **Bounded, deterministic solving.** Z3-backed tools run with a fixed random seed (**42**) and
  a **5000 ms** solver timeout; on the wall they return an honest `SOLVER_TIMEOUT` / `unknown`,
  never a guess. All active fences are introspectable at runtime via the `resource_limits` tool.
- **No ambient authority in tool execution.** Answering a tool call does not read or write the
  filesystem, open network connections, or spawn subprocesses. The engine is pure computation
  over its inputs.
- **Protocol integrity.** The MCP server speaks JSON-RPC over stdio; diagnostic messages
  (e.g. the startup profile line) go to **stderr**, so nothing pollutes the stdout protocol
  stream.

## Honest limits (what is NOT defended)

Stating these plainly is itself part of the security posture:

- **No hard CPU / wall-clock cap on SymPy or pure-Python compute.** The 5000 ms timeout is a
  **Z3** parameter. Symbolic-computation and numeric tools are bounded only by the input-size
  fences and per-tool numeric caps — a pathological but *well-formed, in-size* input can still
  cost significant CPU/time. If you expose MathHead to untrusted input at scale, run it under
  OS-level limits (a container, `ulimit`, or cgroups). See the threat model for detail.
- **No hard memory cap.** A legitimately huge result (a large series expansion, a big factorial)
  can allocate substantial memory. Same mitigation: OS-level limits.
- **It is a library/subprocess, not a sandbox.** MathHead runs with the privileges of the
  process that launches it. It does not attempt to sandbox itself; that is the host's job.
- **Optional external binaries.** DRAT proof checking (`drat-trim`) and high-performance SAT
  (CaDiCaL/Kissat) invoke external tools **only** if you install them and call those specific
  paths; they are outside the default install and outside this in-process model.

## Scope

In scope: anything that lets a crafted MCP argument or expression **execute code, escape the
allowlist, read/write files, open a network connection, or crash the server process**, and any
case where the engine returns a **confidently wrong verdict** as if it were sound (a soundness
bug is a trust bug). Out of scope: resource exhaustion from well-formed in-size input (a known,
documented limit — mitigate with OS-level controls), and issues in Z3/SymPy themselves (report
upstream; we will pin around a known-bad release).
