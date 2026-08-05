# Contributing

Dev setup: `pip install -e ".[dev,solvers]"` (+ `apt install nauty`), then `pytest -q` (1800+ tests)
and `ruff check .` must both be green. `python scripts/gen_status.py --check` guards the plan files.

**The honesty rules are the contribution rules:**
1. Any new verdict path MUST carry an epistemic tier, and the tier must not overstate the evidence.
2. Witnesses must be self-verifying (exact arithmetic or independent re-checking) and tested.
3. If your feature can fail or run out of budget, it reports that honestly — no silent truncation.
4. Docs claims must be executable (add them to `tests/test_docs_examples.py`).
