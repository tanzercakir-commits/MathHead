"""
mathhead.core.proof — İspat üretimi (v3).

`entailment` "geçerli" der ama *neden* söylemez. Bu modül iki şey ekler:

  1) **Minimal çekirdek (used_premises):** sonucun gerçekten dayandığı öncül alt
     kümesi (Z3 unsat core). Gereksiz öncülleri ayıklar — %100 sağlam.
  2) **Doğal tümdengelim (natural deduction) türetimi:** önerme + yüklem +
     evrensel örnekleme parçası için İLERİ ZİNCİRLEME ile adım adım ispat.
     Kurallar: ∧-ayıklama, modus ponens (implies), iff-ayıklama, evrensel
     örnekleme (forall). Klasik silogizmi adım adım gösterir.

DÜRÜSTLÜK: Türetici bu parçayla sınırlıdır (aritmetik, `or`/`not`-ağırlıklı ya da
varoluşsal çıkarımlar için türetim kurulamaz). Kuramazsa `unknown` DEĞİL — Z3'ün
sağlam kararı korunur ve "türetim kurulamadı (Z3 doğruladı)" denir. Türetici
SAĞLAMdır (yalnızca geçerli kurallar) — yani ürettiği her adım doğrudur.
"""
from __future__ import annotations

import ast
import copy
import time
from dataclasses import dataclass, field
from typing import Any

import z3

from mathhead.core.logic import DEFAULT_SEED, DEFAULT_TIMEOUT_MS, check_entailment
from mathhead.core.translate import ParseError, parse, translate_all
from mathhead.guardrails import GuardrailError, solver_config, validate_input

_RESERVED = {"implies", "iff", "xor", "forall", "exists"}
_MAX_ROUNDS = 200


@dataclass
class ProofResult:
    status: str                                  # valid|invalid|unknown|error
    reason_code: str
    explanation: str
    used_premises: list[int] | None = None       # minimal çekirdek (öncül indeksleri)
    proof_steps: list[dict[str, Any]] | None = None  # adım adım türetim
    witness: dict[str, Any] | None = None        # invalid ise karşıörnek
    meta: dict[str, Any] = field(default_factory=dict)


def _meta(t0: float, seed: int, timeout_ms: int) -> dict[str, Any]:
    return {
        "engine": "z3+nd",
        "z3_version": z3.get_version_string(),
        "elapsed_ms": round((time.perf_counter() - t0) * 1000, 3),
        "seed": seed,
        "timeout_ms": timeout_ms,
    }


def _key(node: ast.AST) -> str:
    return ast.unparse(node)


class _Subst(ast.NodeTransformer):
    """Serbest `var`'ı `repl_id` adıyla değiştirir; iç içe aynı adı bağlayan
    nicelik belirtecine girmez (yakalama önleme)."""

    def __init__(self, var: str, repl_id: str):
        self.var = var
        self.repl_id = repl_id

    def visit_Call(self, node: ast.Call) -> ast.AST:
        if (isinstance(node.func, ast.Name) and node.func.id in ("forall", "exists")
                and node.args and isinstance(node.args[0], ast.Name)
                and node.args[0].id == self.var):
            return node  # var yeniden bağlandı
        return self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> ast.AST:
        if node.id == self.var:
            return ast.Name(id=self.repl_id, ctx=ast.Load())
        return node


def _substitute(body: ast.AST, var: str, repl_id: str) -> ast.AST:
    new = _Subst(var, repl_id).visit(copy.deepcopy(body))
    return ast.fix_missing_locations(new)


def _bound_vars(nodes: list[ast.AST]) -> set[str]:
    bv: set[str] = set()
    for node in nodes:
        for n in ast.walk(node):
            if (isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                    and n.func.id in ("forall", "exists") and n.args
                    and isinstance(n.args[0], ast.Name)):
                bv.add(n.args[0].id)
    return bv


def _individuals(nodes: list[ast.AST]) -> set[str]:
    """Yüklem argümanı olarak geçen serbest bireyler (evrensel örnekleme için)."""
    bound = _bound_vars(nodes)
    inds: set[str] = set()
    for node in nodes:
        for n in ast.walk(node):
            if (isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                    and n.func.id not in _RESERVED):
                for arg in n.args:
                    if isinstance(arg, ast.Name) and arg.id not in bound:
                        inds.add(arg.id)
    return inds


def _forward_chain(premise_nodes: list[ast.AST], goal: ast.AST) -> list[dict] | None:
    """İleri zincirleme ND türetimi. Başarırsa adım listesi, yoksa None döner."""
    known: dict[str, dict] = {}   # key -> {node, rule, refs, order}
    order = [0]

    def add(node: ast.AST, rule: str, refs: list[str]) -> bool:
        k = _key(node)
        if k not in known:
            known[k] = {"node": node, "rule": rule, "refs": refs, "order": order[0]}
            order[0] += 1
            return True
        return False

    for p in premise_nodes:
        add(p, "öncül", [])
    individuals = sorted(_individuals(premise_nodes + [goal]))
    goal_key = _key(goal)

    rounds = 0
    changed = True
    while changed and goal_key not in known and rounds < _MAX_ROUNDS:
        changed = False
        rounds += 1
        for k, fact in list(known.items()):
            node = fact["node"]
            if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.And):
                for v in node.values:
                    changed |= add(v, "∧-ayıklama", [k])
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                fid, args = node.func.id, node.args
                if fid == "implies" and len(args) == 2 and _key(args[0]) in known:
                    changed |= add(args[1], "modus ponens", [k, _key(args[0])])
                elif fid == "iff" and len(args) == 2:
                    if _key(args[0]) in known:
                        changed |= add(args[1], "iff-ayıklama", [k, _key(args[0])])
                    if _key(args[1]) in known:
                        changed |= add(args[0], "iff-ayıklama", [k, _key(args[1])])
                elif fid == "forall" and len(args) == 2 and isinstance(args[0], ast.Name):
                    var, bod = args[0].id, args[1]
                    for t in individuals:
                        changed |= add(_substitute(bod, var, t), f"evrensel örnekleme (x:={t})", [k])

    if goal_key not in known:
        return None

    # Hedefe ulaşan adımların geçmişini topla, türetim sırasına diz, numaralandır.
    needed: set[str] = set()
    stack = [goal_key]
    while stack:
        k = stack.pop()
        if k in needed:
            continue
        needed.add(k)
        stack.extend(known[k]["refs"])
    ordered = sorted(needed, key=lambda k: known[k]["order"])
    num = {k: i + 1 for i, k in enumerate(ordered)}
    steps = []
    for k in ordered:
        f = known[k]
        steps.append({
            "step": num[k],
            "formula": _key(f["node"]),
            "rule": f["rule"],
            "refs": [num[r] for r in f["refs"]],
        })
    return steps


def _minimal_core(premises: list[str], conclusion: str, timeout_ms: int, seed: int) -> list[int] | None:
    """Sonucun dayandığı minimal öncül alt kümesi (Z3 unsat core)."""
    z3_list, _ = translate_all([*premises, conclusion])
    *prem_z, concl_z = z3_list
    solver = solver_config(timeout_ms, seed)
    trackers: dict[str, int] = {}
    for i, pz in enumerate(prem_z):
        lit = z3.Bool(f"__p_{i}")
        trackers[str(lit)] = i
        solver.assert_and_track(pz, lit)
    solver.add(z3.Not(concl_z))
    if solver.check() == z3.unsat:
        return sorted(trackers[str(c)] for c in solver.unsat_core() if str(c) in trackers)
    return None


def prove_entailment(
    premises: list[str],
    conclusion: str,
    *,
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
    seed: int = DEFAULT_SEED,
) -> ProofResult:
    """`premises ⊨ conclusion` mı — ve neden? Verdict (Z3) + minimal çekirdek +
    (kurulabiliyorsa) adım adım doğal tümdengelim türetimi."""
    t0 = time.perf_counter()
    verdict = check_entailment(premises, conclusion, timeout_ms=timeout_ms, seed=seed)

    if verdict.status == "invalid":
        return ProofResult("invalid", "COUNTEREXAMPLE_FOUND",
                           "Geçersiz: öncülleri sağlayıp sonucu çürüten bir karşıörnek var.",
                           witness=verdict.witness, meta=_meta(t0, seed, timeout_ms))
    if verdict.status != "valid":
        return ProofResult(verdict.status, verdict.reason_code, verdict.explanation,
                           meta=_meta(t0, seed, timeout_ms))

    # Geçerli: çekirdek + türetim.
    try:
        core = _minimal_core(premises, conclusion, timeout_ms, seed)
    except (ParseError, GuardrailError):
        core = None
    try:
        prem_nodes = [parse(p).body for p in premises]
        goal_node = parse(conclusion).body
        steps = _forward_chain(prem_nodes, goal_node)
    except Exception:  # noqa: BLE001 - türetim best-effort; verdict yine sağlam
        steps = None

    if steps is not None:
        explanation = f"Geçerli. {len(steps)} adımlık doğal tümdengelim türetimi kuruldu."
    else:
        explanation = ("Geçerli (Z3 doğruladı). Bu parça için adım adım türetim "
                       "kurulamadı — minimal çekirdek yine de sonucun dayanağını gösterir.")
    return ProofResult("valid", "ENTAILED", explanation,
                       used_premises=core, proof_steps=steps, meta=_meta(t0, seed, timeout_ms))
