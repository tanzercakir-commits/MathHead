# MathHead — Glossary

Terms that appear in the project, kept brief. Goal: a new session (or a new
person/AI) gets into context quickly (against wall #1).

- **FOL (First-Order Logic):** Logic with objects, predicates, and `∀/∃`
  quantifiers. More expressive than propositional logic.

- **Propositional logic:** Only true/false variables and `and/or/not/implies/iff`.
  The quantifier-free subset of FOL. A core piece of v1.

- **SMT (Satisfiability Modulo Theories):** A decision problem that adds
  *theories* (arithmetic, equality, arrays...) on top of SAT. **Z3** is an SMT
  solver. This is the technical name for our "FOL + built-in theories" phrasing.

- **CAS (Computer Algebra System):** Symbolic computation (simplification,
  equation solving, derivative/integral). **SymPy** is a CAS. In MathHead, the
  *compute* layer (v2+).

- **entailment (logical consequence, `⊨`):** The conclusion being *necessarily*
  true when the premises are true. Check method: is `(premises) ∧ ¬conclusion`
  **UNSAT**?

- **satisfiability (sat):** Is there at least one assignment that makes a formula
  true? If so **SAT**, otherwise **UNSAT**.

- **model:** A concrete variable assignment that makes a formula true (e.g.
  `x = 3`). The witness of SAT.

- **counterexample:** A concrete assignment that *refutes* a claim. When
  entailment is invalid, the engine returns this.

- **unsat core:** The *smallest* culprit subset that makes a set contradictory.
  Shows why it is inconsistent.

- **decidability:** Is there an algorithm that *always* terminates and answers a
  problem? Propositional logic is decidable; general FOL is **semi**-decidable
  → the engine sometimes returns `unknown`.

- **guardrail:** A hard limit the engine cannot cross (size, time, symbols). The
  counterpart of the user's "must not step outside the guardrail" requirement.

- **determinism:** Same input → same output. Ensured by a fixed seed + timeout +
  single thread.

- **MCP (Model Context Protocol):** The protocol through which AI clients (e.g.
  Claude) connect to external tools in a standard way. MathHead is published
  through it.

- **ADR (Architecture Decision Record):** A short record that stores an
  architectural decision with its rationale. Kept in `DECISIONS.md`.

- **vertical slice:** A narrow feature that *works* end to end (from interface to
  core). Our v1 strategy.
