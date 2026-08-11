# MH-ADR-0002: Package ownership and dependency direction

**Status:** Accepted  
**Accepted:** 2026-08-11  
**Decision topic:** package-ownership

## Context

The legacy package mixes public adapters, parsing, solvers, checkers,
orchestration, and discovery. Reconstruction needs one owner for each semantic
concept and an import direction that keeps producers out of the trust base.

## Decision

The target ownership model is:

| Owner | Owns | May depend on | Must not depend on |
|---|---|---|---|
| `mathhead.contracts` | versioned IR, context, budget, result, evidence and plugin protocols | Python standard library and declared schema utilities | solvers, adapters, legacy modules, laboratory code |
| `mathhead.kernel` | immutable proof terms and dependency-minimal certificate checkers | `contracts`, standard-library primitives | Z3, SymPy, MCP/HTTP, planners, producers, laboratory code |
| `mathhead.theories` | typed theory plugins, bounded producers, explanations and plugin-local evidence | `contracts`, approved backends, shared producer utilities | interfaces, laboratory policy, kernel internals |
| `mathhead.engine` | analysis, obligations, capability registry, deterministic planning, budgets, sessions, replay and safe caching | public `contracts`, `kernel`, and theory-plugin protocols | interface-specific serialization, laboratory internals |
| `mathhead.interfaces` | Python API, CLI, MCP and HTTP adapters | public engine and contract APIs | solver-specific logic or unique mathematical semantics |
| `mathhead.lab` | conjectures, campaigns, ranking, novelty evidence and experiment manifests | public contracts and engine submission APIs | kernel internals or authority to construct supported verdicts |

Dependency flow is inward from interfaces and lab toward contracts/engine, and
from engine toward public kernel/plugin boundaries. The kernel is never allowed
to import a producer. External solvers produce artifacts; they do not decide
the epistemic tier.

Legacy `core`, `compute`, `router`, `server`, and `discovery` packages are
transitional sources, not the target ownership model. During migration an
anti-corruption adapter may call them, but new cross-layer imports must follow
the target direction and adapters must be visibly transitional.

## Consequences

Contract tests can run without importing legacy solvers. Kernel tests can run
without optional backends. Each theory slice declares capabilities and costs
instead of adding top-level tool-specific routing branches. Public adapters
share one semantic engine.

## Rejected alternatives

- One package per external solver, because backends do not own semantics.
- A shared `utils` package for cross-layer concepts, because it erases
  ownership and encourages cycles.
- Letting interfaces call theory modules directly, because adapters would
  develop divergent behavior.
