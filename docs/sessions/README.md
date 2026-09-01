# Problem-session reports

This directory contains the frozen, deterministic validation evidence for
MH-046. `problem-sessions-v1.json` covers the pure replay boundary;
`problem-session-store-v1.json` covers the non-authoritative atomic filesystem
adapter. Regenerate either report only after deliberately reviewing the
contracts, schemas, implementation, tests, and validator change that caused
its identity to move.

```bash
python tools/validate_problem_sessions.py \
  --write-report docs/sessions/reports/problem-sessions-v1.json
python tools/validate_problem_session_store.py \
  --write-report docs/sessions/reports/problem-session-store-v1.json
python tools/validate_problem_sessions.py
python tools/validate_problem_session_store.py
```

The reports claim conformance and identity stability only. They never claim
that stored mathematical content is true.
