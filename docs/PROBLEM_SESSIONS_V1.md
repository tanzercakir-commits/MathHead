# Persistent problem sessions v1

MH-046 adds a replayable boundary for retaining the exact state of one
mathematical problem across processes. It does not plan, solve, verify, merge
branches, or grant mathematical authority. The pure transition boundary is
governed by accepted contract `MH-C-PROBLEM-SESSION-001`; its filesystem
adapter is separately governed by `MH-C-PROBLEM-SESSION-STORE-001`.

## Boundary split

`mathhead.problem_sessions.transition_problem_session` is the dependency-small
core. It receives one optional canonical command, the complete ordered event
history, and the complete sorted artifact byte inventory. It parses and
recomputes every identity before returning one immutable
`ProblemSessionResult`. It imports no filesystem, process, network, clock,
random, solver, or checker owner.

`mathhead.problem_session_store.persist_problem_session` is an effect-only
adapter. It writes validated bytes beneath one explicit absolute root, commits
one sealed `HEAD` atomically, then reloads all referenced objects and asks the
core to replay them. `load_problem_session` always performs the same fresh
replay. `recover_problem_session_store` is an explicit operator action which
removes only abandoned writer/head temporaries and reopens the last committed
head.

Neither layer changes the epistemic tier carried by an artifact. A stored
certificate or checker result remains exactly the evidence it was before it
entered the session; a digest is identity, not proof.

## Revision model

A new session binds one TheoryContext identity and the complete initial
problem-analysis artifact set. Each accepted command appends exactly one
canonical event with:

- the exact parent event identity and monotonic revision number;
- the complete command and newly admitted artifact links;
- deterministic invalidations with explicit causes;
- the digest of the complete current view.

Definitions retain their ProblemIR, TheoryContext, declaration, payload, and
dependency identities. Lemmas retain their statement, producer,
checker/certificate or explicit absence, replay provenance, reading, context,
dependencies, and retained tier. Attempts retain strategy, inputs,
observations, diagnostics, resource outcome, produced artifacts, and attempted
obligations, including failed, cancelled, timed-out, and exhausted outcomes.
Obligation records retain their canonical obligation, reading, context,
dependencies, lifecycle state, and separately admitted evidence links.

Replacing or retiring a record moves that exact generation and every
transitively dependent current record into immutable stale history. Replacing
the TheoryContext invalidates every context-bound current record. A stale
record never becomes current because a name or digest reappears: revival needs
a new generation supplied by a new accepted command with all current
dependencies and evidence. Cross-session references, cross-reading references,
cycles, missing dependencies, trust escalation, and self-attested discharged
obligations fail closed.

The closed outcomes are `updated`, `unchanged`, `conflict`, `invalid`, and
`exhausted`. Only `updated` contains a new child revision. `unchanged` is
reserved for an exact idempotent retry or replay. Every refusal contains no new
head, revision, artifacts, or authority.

## Store layout and commit rule

The adapter derives every path itself:

```text
STORE/
  objects/<sha256[0:2]>/<sha256[2:]>
  sessions/<sha256(session_id)[0:2]>/<remaining>/HEAD
```

Objects are canonical or exact input bytes named by their SHA-256 content and
sealed read-only after installation. Existing objects are accepted only when
their bytes, file type, ownership, link count, mode, and digest still match.
The adapter rejects relative roots, filesystem roots, traversal, links,
reparse points, hardlinks, writable committed files, collisions, and mutated
reads. The pure logical head and the byte-object digest are deliberately
distinct identities.

One writer lock serializes a session. A command names the exact expected
logical head; an outdated writer receives `conflict` without changing `HEAD`.
An exact retry returns `unchanged`. A successful commit writes and fsyncs all
immutable objects, writes and fsyncs a same-directory temporary head, performs
one atomic replacement, fsyncs the directory, and then freshly replays the
committed bytes. Orphan objects are never interpreted as committed state.

## Minimal use

Construct artifacts, typed records, and commands with the public `make_*`
functions in `mathhead.problem_sessions`. The first call must be a
`create_session` command:

```python
from pathlib import Path

from mathhead.problem_session_store import load_problem_session, persist_problem_session
from mathhead.problem_sessions import make_problem_session_command

command = make_problem_session_command(
    command_id="create_problem_001",
    kind="create_session",
    session_id="problem_001",
    context_sha256=context_link.sha256,
    analysis_artifact_sha256s=(analysis_link.sha256,),
    introduced_artifacts=(context_link, analysis_link),
)
created = persist_problem_session(
    Path("/absolute/private/mathhead-store"),
    command,
    (context_bytes, analysis_bytes),
)
reopened = load_problem_session(
    Path("/absolute/private/mathhead-store"), "problem_001"
)
assert reopened.revision_value == created.revision_value
```

Callers must sort artifact links and byte inventories by their declared digest
where the contract requires canonical set order. They must preserve the exact
returned head for the next command's `expected_head_sha256`.

## Validation

The frozen core report independently recomputes command, record,
invalidation, event, view, revision, and artifact identities over a reference
history. The store report independently inspects canonical head bytes,
content-addressed paths, sealed file metadata, idempotency, stale-writer
conflict, recovery, and reopen equality.

```bash
python -m unittest discover -s tests/problem_sessions -v
python tools/validate_problem_sessions.py
python tools/validate_problem_session_store.py
python tools/contract_artifacts.py verify \
  --contract MH-C-PROBLEM-SESSION-001 --require-bound
python tools/contract_artifacts.py verify \
  --contract MH-C-PROBLEM-SESSION-STORE-001 --require-bound
```

The frozen reports are
`docs/sessions/reports/problem-sessions-v1.json` and
`docs/sessions/reports/problem-session-store-v1.json`. Garbage collection,
remote synchronization, multi-host consensus, divergent-history merge,
encryption, strategy execution, and collaboration UI remain outside MH-046.
