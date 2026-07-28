"""
Sağlamlaştırma-2 (ROADMAP Aşama 5) — durum & hata taksonomisi denetimi.

Her araç yalnızca `docs/error-taxonomy.md`'de belgelenen `status` ve
`reason_code` değerlerini döndürmeli. Bu test taksonomiyi ZORLAR: yeni/belgesiz
bir kod sızarsa kırılır (doküman + test birlikte güncellenmeli).
"""
from dataclasses import asdict

from mathhead.router import route

# --- Kanonik kümeler (docs/error-taxonomy.md ile birebir) ----------------- #
ALLOWED_STATUS = frozenset({
    "unknown", "error",
    "valid", "invalid",
    "sat", "unsat",
    "tautology", "contradiction", "contingent",
    "equivalent", "not_equivalent",
    "optimal", "unbounded",
    "ok",
})

ALLOWED_REASON = frozenset({
    "OK", "ENTAILED", "CONSISTENT", "MODEL_FOUND", "MODELS_FOUND", "ALL_MODELS_FOUND",
    "TAUTOLOGY", "CONTRADICTION", "CONTINGENT", "EQUIVALENT", "NOT_EQUIVALENT",
    "OPTIMAL", "UNBOUNDED", "OPEN_BOUND", "COLORING_FOUND",
    "COUNTEREXAMPLE_FOUND", "NO_MODEL", "PROVEN_IMPOSSIBLE", "NO_COLORING",
    "INFEASIBLE", "HARD_INFEASIBLE", "PARSE_ERROR", "COMPUTE_FAILED",
    "GUARDRAIL_VIOLATION", "SOLVER_TIMEOUT", "SOLVER_UNKNOWN", "UNEXPECTED_SAT",
})

_ERROR_STATUS = {"error"}

# --- Temsili çağrılar: her araç ailesi + başarı/hata yolları -------------- #
CALLS = [
    ("entailment", {"premises": ["p", "implies(p,q)"], "conclusion": "q"}),
    ("entailment", {"premises": ["p"], "conclusion": "q"}),
    ("consistency", {"statements": ["p", "not(p)"]}),
    ("consistency", {"statements": ["x>2", "x<5"]}),
    ("find_model", {"statements": ["x>2"]}),
    ("prove", {"premises": ["p", "implies(p,q)"], "conclusion": "q"}),
    ("equivalent", {"a": "p", "b": "p"}),
    ("equivalent", {"a": "p", "b": "q"}),
    ("classify", {"formula": "p or not(p)"}),
    ("classify", {"formula": "p and not(p)"}),
    ("classify", {"formula": "p"}),
    ("enumerate", {"statements": ["p or q"]}),
    ("optimize", {"constraints": ["x>=0", "x<=10"], "objective": "x", "sense": "max"}),
    ("optimize", {"constraints": ["x>=0"], "objective": "x", "sense": "max"}),
    ("maxsat", {"hard": ["p"], "soft": ["not(p)"], "weights": None}),
    # compute — başarı + hata
    ("simplify", {"expression": "x+x"}),
    ("simplify", {"expression": "foo(x)"}),
    ("solve", {"equation": "x**2==4", "symbol": "x"}),
    ("differentiate", {"expression": "x**3", "symbol": "x", "order": 1}),
    ("integrate", {"expression": "2*x", "symbol": "x"}),
    ("limit", {"expression": "sin(x)/x", "symbol": "x", "point": "0"}),
    ("series", {"expression": "exp(x)", "symbol": "x", "point": "0", "order": 5}),
    ("solve_system", {"equations": ["x+y==10", "x-y==2"], "symbols": ["x", "y"]}),
    ("determinant", {"matrix": [["1", "2"], ["3", "4"]]}),
    ("matrix_inverse", {"matrix": [["1", "2"], ["2", "4"]]}),   # tekil -> COMPUTE_FAILED
    ("eigenvalues", {"matrix": [["2", "0"], ["0", "3"]]}),
    ("matrix_multiply", {"a": [["1", "2"]], "b": [["1", "2"]]}),  # boyut -> PARSE_ERROR
    ("matrix_solve", {"matrix": [["1", "1"], ["1", "-1"]], "rhs": ["10", "2"]}),
    ("rref", {"matrix": [["1", "2"], ["2", "4"]]}),
    ("nullspace", {"matrix": [["1", "2"], ["2", "4"]]}),
    ("gcd", {"a": "48", "b": "36"}),
    ("gcd", {"a": "x", "b": "2"}),                               # sembol -> PARSE_ERROR
    ("modular_inverse", {"a": "4", "m": "8"}),                   # ters yok -> COMPUTE_FAILED
    ("factorize", {"n": "360"}),
    ("chinese_remainder", {"moduli": ["3", "5", "7"], "residues": ["2", "3", "2"]}),
    ("linear_diophantine", {"a": "3", "b": "6", "c": "9"}),
    ("permutations", {"n": "10", "k": "3"}),
    ("combinations", {"n": "10", "k": "3"}),
    ("factorial", {"n": "6"}),
    ("partition_count", {"n": "10"}),
    ("solve_recurrence", {"recurrence": "y(n)=2*y(n-1)", "func": "y", "var": "n",
                          "initial": {"0": "1"}}),
    ("solve_recurrence", {"recurrence": "y(n)=y(n-1)**2", "func": "y", "var": "n",
                          "initial": {"0": "2"}}),               # nonlin -> COMPUTE_FAILED
    ("pigeonhole", {"n": 4}),
    ("pythagorean_coloring", {"n": 10}),
]


def _results():
    return [(task, asdict(route(task, pl))) for task, pl in CALLS]


def test_all_status_in_taxonomy():
    for task, r in _results():
        assert r["status"] in ALLOWED_STATUS, f"{task}: belgesiz status {r['status']!r}"


def test_all_reason_codes_in_taxonomy():
    for task, r in _results():
        rc = r.get("reason_code")
        assert rc in ALLOWED_REASON, f"{task}: belgesiz reason_code {rc!r}"


def test_error_status_has_no_fabricated_result():
    # Dürüstlük değişmezi: error -> uydurma 'result' yok (None ya da boş).
    for task, r in _results():
        if r["status"] in _ERROR_STATUS and "result" in r:
            assert r["result"] in (None, [], {}, ""), \
                f"{task}: error olmasına rağmen result dolu ({r['result']!r})"


def test_sweep_covers_success_and_error():
    # Tarama hem başarı hem hata yolunu gerçekten görmeli (test anlamlı kalsın).
    statuses = {r["status"] for _, r in _results()}
    assert "error" in statuses
    assert statuses & {"ok", "valid", "sat", "optimal"}
