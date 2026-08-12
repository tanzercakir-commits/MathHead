# Syntax-neutral problem intake v1

MH-040 introduces the first target-architecture problem-analysis boundary under
accepted contract `MH-C-PROBLEM-INTAKE-001` at SHA-256
`855375a8fb788ff65728d860c16f0ccfa32fe9d058b3fe93534ef11f147794dc`.
The implementation is `mathhead.problem_intake`; the normative input and result
schemas are `docs/contracts/schemas/problem-intake-v1.schema.json` and
`problem-intake-result-v1.schema.json`.

## Boundary and authority

`intake_problem(specification: dict[str, object]) -> ProblemIntakeResult`
accepts one exact built-in Python dictionary with exactly `schema` and
`problem`. Nested containers may be exact `dict`, `list`, or `tuple`; leaves
may be exact `None`, `bool`, `int`, or `str`. Tuples become arrays and strings
become NFC after NUL rejection. Subclasses, custom mappings or sequences,
bytes, floats, decimals, fractions, dataclasses, iterators, AST nodes, SymPy
objects, and solver objects fail closed.

An accepted result establishes only that the explicit declaration is one valid,
canonical ProblemIR representation. `mathematical_authority` is always false.
Intake does not prove, refute, solve, simplify, evaluate, infer a domain or
assumption, select an ambiguous reading, create evidence, or call a checker.

Natural-language, Markdown, LaTeX, MathML, Python-expression, SymPy, CLI, MCP,
file, network, and discovery inputs are deliberately outside this boundary.
Existing text and interface parsers remain non-authoritative adapters; callers
must make every mathematical choice explicit before invoking intake.

## Minimal structured use

The following complete value declares the proposition “for every integer `x`,
`x = x`.” Registry order is normalized by stable ID, while semantic orders such
as binders, operands, definition parameters, and reading goals are preserved.

```python
from mathhead.problem_intake import (
    canonical_problem_ir_bytes,
    intake_problem,
    problem_intake_result_sha256,
)

problem = {
    "schema": "mathhead.problem-ir.v1",
    "source_documents": [],
    "source_spans": [],
    "domains": [
        {"id": "domain_integer", "kind": "builtin", "name": "integer", "span_ids": []}
    ],
    "variables": [
        {
            "id": "variable_x",
            "name": "x",
            "domain_id": "domain_integer",
            "role": "bound",
            "span_ids": [],
        }
    ],
    "expressions": [
        {
            "id": "expression_x",
            "kind": "variable",
            "domain_id": "domain_integer",
            "variable_id": "variable_x",
            "span_ids": [],
        }
    ],
    "relations": [
        {
            "id": "relation_reflexive",
            "kind": "equal",
            "operand_expr_ids": ["expression_x", "expression_x"],
            "span_ids": [],
        }
    ],
    "statements": [
        {
            "id": "statement_body",
            "kind": "relation",
            "relation_id": "relation_reflexive",
            "span_ids": [],
        },
        {
            "id": "statement_forall",
            "kind": "quantified",
            "quantifier": "forall",
            "variable_ids": ["variable_x"],
            "body_statement_id": "statement_body",
            "span_ids": [],
        },
    ],
    "definitions": [],
    "assumptions": [],
    "goals": [
        {
            "id": "goal_reflexive",
            "statement_id": "statement_forall",
            "mode": "prove",
            "span_ids": [],
        }
    ],
    "readings": [
        {
            "id": "reading_only",
            "label": "For every integer x, x equals itself.",
            "definition_ids": [],
            "assumption_ids": [],
            "goal_ids": ["goal_reflexive"],
            "difference_from": None,
            "differences": [],
            "span_ids": [],
        }
    ],
    "ambiguity": {
        "status": "unambiguous",
        "candidate_reading_ids": ["reading_only"],
        "selected_reading_id": "reading_only",
        "required_choice": None,
    },
    "extensions": {},
}

result = intake_problem({"schema": "mathhead.problem-intake.v1", "problem": problem})
assert result.status == "accepted"
problem_ir_bytes = canonical_problem_ir_bytes(result)
result_identity = problem_intake_result_sha256(result)
```

## Result and failure algebra

The result status is exactly `accepted`, `invalid`, or `exhausted`. Accepted
results contain canonical ProblemIR bytes and their full SHA-256; diagnostics
are empty. Failed results contain one bounded diagnostic and no ProblemIR bytes
or identity. Stable reason codes are `ACCEPTED`, `BUDGET_EXHAUSTED`,
`INVALID_CANONICAL_VALUE`, `INVALID_PROBLEM`, `INVALID_REFERENCE`,
`INVALID_SCHEMA`, `INVALID_SEMANTICS`, and `INVALID_TYPE`.

`problem_intake_result_bytes` produces closed canonical result JSON;
`parse_problem_intake_result` and `validate_problem_intake_result` recompute all
bindings, canonical form, ProblemIR semantics, and digests before consumption.
Direct result construction, subclassing, and pickle reconstruction are blocked.

The fixed ceilings include 64 MiB input and output, 4,000,000 JSON nodes,
8,000,000 validation steps, depth 512, 100,000 combined entities and items per
array, 1,048,576 code points per string, 16,777,216 aggregate string code
points, 4,096 digits per numeric-literal component, and exact integers no
larger than `2**53 - 1` in magnitude. Exhaustion never exposes a partial
ProblemIR or digest.

## Validation

```bash
python -m unittest discover -s tests/problem_intake -v
python tools/validate_problem_intake.py
python tools/contract_artifacts.py verify \
  --contract MH-C-PROBLEM-INTAKE-001 --require-bound
python tools/validate_trust_base.py
```

The independent validator feeds every tagged ProblemIR variant and all eight
foundation scenarios through the production boundary, then validates the bytes
again with the independent ProblemIR validator. Cross-platform and clean-wheel
checks run in the governed CI profiles.
