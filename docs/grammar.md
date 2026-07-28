# MathHead — Input Grammars (formal spec)

> **This file's job:** the formal-ish specification of every input grammar the engine
> accepts (ROADMAP K2). Each layer parses with Python `ast` and filters through a
> **whitelist** — anything outside the grammar is a clean `PARSE_ERROR` /
> `GUARDRAIL_VIOLATION`, never a silent guess (PRINCIPLES 2, "no silent assumptions").
> The `tests/test_fuzz.py` fuzzers assert these parsers never crash on malformed input.

Notation: EBNF-ish. `|` alternation, `*` zero-or-more, `?` optional, lowercase = rule,
`"x"` = literal. All layers share the guardrail fence (`guardrails/validate_input`):
≤ 256 statements, ≤ 4000 chars each, AST depth ≤ 64.

---

## 1. Logic kernel (`core/translate.py`) — Z3

Used by: `entailment`, `consistency`, `model`, `prove`, `equivalent`, `classify`,
`enumerate_models`, `optimize`, `max_satisfy`, `entail_batch`, and (as the formula
grammar) `eliminate_quantifiers`.

```
formula   := bool_expr
bool_expr := bool_expr ("and" | "or") bool_expr
           | "not" bool_expr
           | "implies" "(" bool_expr "," bool_expr ")"
           | "iff" "(" bool_expr "," bool_expr ")"
           | "xor" "(" bool_expr "," bool_expr ")"
           | "forall" "(" name "," bool_expr ")"
           | "exists" "(" name "," bool_expr ")"
           | predicate | comparison | name | bool_const
predicate := Name "(" name ("," name)* ")"          # uninterpreted, args are individuals
comparison:= num_expr (("<"|"<="|"=="|"!="|">="|">") num_expr)+   # chained
num_expr  := num_expr ("+"|"-"|"*") num_expr | "-" num_expr | name | number
```

Sorts (inferred, conflict → error): `bool`, numeric (`Int`, or `Real` if any decimal
appears), `ind` (individual / sort `U`). **Linearity fence:** `variable * variable`
is rejected. Quantifiers + predicates make FOL semi-decidable → Z3 may return
`unknown` (honest).

---

## 2. Compute layer (`compute/__init__.py`) — SymPy

Used by: `simplify`, `solve`, `differentiate`, `integrate`, `limit`, `series`, and the
whole CAS surface (calculus, linear algebra, number theory, combinatorics, transforms,
statistics, numerics). Nonlinear and `**` ARE allowed here (unlike the logic kernel).

```
expr := expr ("+"|"-"|"*"|"/"|"**") expr | "-" expr | func "(" expr ("," expr)* ")"
      | name | number | const
func := "sin"|"cos"|"tan"|"asin"|"acos"|"atan"|"sinh"|"cosh"|"tanh"
      | "exp"|"log"|"sqrt"|"Abs"
const:= "pi" | "E" | "I"                              # π, e, imaginary unit (ADR-0021)
```

Matrices are `"a,b;c,d"` (CLI) or `[[...],[...]]` (list). Unsafe paths (`eval`,
`sympify`) are never used. An unevaluated result (e.g. an `Integral(...)` SymPy cannot
close) is reported honestly, not hidden.

---

## 3. Induction (`core/induction.py`) — single-variable nonlinear integer

Used by: `prove_by_induction`. One integer variable; nonlinear arithmetic allowed.

```
claim := bool
bool  := bool ("and"|"or") bool | "not" bool | "implies" "(" bool "," bool ")"
       | int_expr cmp int_expr (cmp int_expr)*
int_expr := int_expr ("+"|"-"|"*"|"%"|"//") int_expr | int_expr "**" nat_const
          | "-" int_expr | var | int_const
cmp   := "<"|"<="|"=="|"!="|">="|">"
```

`var` is the single induction variable; any OTHER free name is rejected. `**` exponent
must be a constant integer in `0..12`. Constants are integers only (induction is over ℤ).

---

## 4. SMT theories (`core/smt.py`) — Z3 decision theories

Shared shape `check_<theory>(assumptions, goal=None)`. Common wrapper:
`and`/`or`/`not`, `implies(a,b)`, `iff(a,b)` (each `implies`/`iff` needs exactly 2 args).

```
# Bit-vectors (check_bitvector, width-bit)
bv_atom := bv cmp bv                     # cmp unsigned unless signed=True
bv      := bv ("&"|"|"|"^"|"<<"|">>"|"+"|"-"|"*") bv | "~" bv | "-" bv | name | int

# Uninterpreted functions + equality (check_uninterpreted, EUF)
euf_atom := term ("=="|"!=") term | Pred "(" term ("," term)* ")"
term     := name | Func "(" term ("," term)* ")"       # over one abstract sort U

# Arrays (check_arrays; a name first used as select/store arg 1 is an array)
arr_atom := scalar cmp scalar | array "==" array
scalar   := "select" "(" array "," scalar ")" | scalar ("+"|"-"|"*") scalar | name | number
array    := "store" "(" array "," scalar "," scalar ")" | name

# Strings / sequences (check_strings)
str_atom := s ("=="|"!=") s | int cmp int
          | ("contains"|"prefixof"|"suffixof") "(" s "," s ")"
s        := s "+" s | "concat" "(" s ("," s)+ ")" | "at" "(" s "," int ")" | name | "text"
int      := "length" "(" s ")" | integer | int ("+"|"-"|"*") int
```

`goal` given → entailment (`valid`/`invalid` + witness); `goal=None` → consistency
(`sat`/`unsat`). A sort clash or unexpected symbol → clean `PARSE_ERROR`.

---

## 5. Modal logic (`core/modal.py`)

Used by: `check_modal(formula, system, max_worlds)`. Systems: `K T D B S4 S5`.

```
mformula := mformula ("and"|"or") mformula | "not" mformula
          | "implies" "(" mformula "," mformula ")" | "iff" "(" mformula "," mformula ")"
          | "box" "(" mformula ")" | "dia" "(" mformula ")" | atom
```

`box` = □ (necessity), `dia` = ◇ (possibility); `atom` is a propositional name. Bounded
Kripke model checking over `max_worlds` (1..12).

---

## 6. CNF layer (`drat.py`, `hpsolver.py`)

Used by: `prove_unsat`, `check_unsat_proof`, `solve_cnf`. DIMACS-style.

```
cnf    := clause+
clause := literal*                        # [] is the empty clause (a contradiction)
literal:= nonzero_integer                 # n = variable n true, -n = false
proof  := clause*                         # a DRUP proof (lemmas, ending in the empty clause)
```

`0` is not a valid literal (a clean error). `prove_unsat` is bounded to 20 variables;
`check_unsat_proof` scales further (checking is polynomial).
