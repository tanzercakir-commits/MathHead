"""
mathhead.core.proof — İspat üretimi (v3.2).

`entailment` "geçerli" der ama *neden* söylemez. Bu modül ekler:

  1) **Minimal çekirdek (used_premises):** sonucun dayandığı öncül alt kümesi
     (Z3 unsat core). %100 sağlam.
  2) **Doğal tümdengelim türetimi (natural deduction):** iki strateji —
     * DOĞRUDAN ileri zincirleme. Kurallar: ∧-ayıklama, modus ponens/tollens,
       ayrık tasım, iff-ayıklama, çift olumsuzlama, De Morgan, **evrensel
       örnekleme (∀-eleme)**, **varoluşsal eleme (∃-eleme, tanık sabiti)**,
       **varoluşsal içe alma (∃-giriş)**.
     * ÇELİŞKİDEN İSPAT (RAA): doğrudan bulunamazsa ¬sonuç varsayılıp çelişki
       aranır → "durum ayrımı" gibi dolaylı ispatlar.

DÜRÜSTLÜK: Türetici klasik FOL'un önemli bir parçasını kapsar ama tümünü değil
(aritmetik türetim ve bazı içiçe nicelik desenleri yok). Kuramazsa `unknown`
DEĞİL — Z3'ün sağlam kararı korunur. Türetici SAĞLAMdır (yalnızca geçerli
kurallar); ayrıca her sonuç önce Z3 ile doğrulanır.
"""
from __future__ import annotations

import ast
import copy
import time
from dataclasses import dataclass, field
from typing import Any, Callable

import z3

from mathhead.core.logic import DEFAULT_SEED, DEFAULT_TIMEOUT_MS, check_entailment
from mathhead.core.translate import ParseError, parse, translate_all
from mathhead.guardrails import GuardrailError, solver_config

_RESERVED = {"implies", "iff", "xor", "forall", "exists"}
_MAX_ROUNDS = 200


@dataclass
class ProofResult:
    status: str
    reason_code: str
    explanation: str
    used_premises: list[int] | None = None
    proof_steps: list[dict[str, Any]] | None = None
    witness: dict[str, Any] | None = None
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


def _mk_not(node: ast.AST) -> ast.AST:
    return ast.fix_missing_locations(ast.UnaryOp(op=ast.Not(), operand=copy.deepcopy(node)))


def _neg_key(node: ast.AST) -> str:
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return _key(node.operand)
    return _key(_mk_not(node))


# --------------------------- ikame (substitution) ------------------------- #
class _Subst(ast.NodeTransformer):
    def __init__(self, var: str, repl_id: str):
        self.var = var
        self.repl_id = repl_id

    def visit_Call(self, node: ast.Call) -> ast.AST:
        if (isinstance(node.func, ast.Name) and node.func.id in ("forall", "exists")
                and node.args and isinstance(node.args[0], ast.Name)
                and node.args[0].id == self.var):
            return node
        return self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> ast.AST:
        if node.id == self.var:
            return ast.Name(id=self.repl_id, ctx=ast.Load())
        return node


def _substitute(body: ast.AST, var: str, repl_id: str) -> ast.AST:
    return ast.fix_missing_locations(_Subst(var, repl_id).visit(copy.deepcopy(body)))


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


def _all_names(nodes: list[ast.AST]) -> set[str]:
    s: set[str] = set()
    for node in nodes:
        for n in ast.walk(node):
            if isinstance(n, ast.Name):
                s.add(n.id)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
                s.add(n.func.id)
    return s


class _Ctx:
    """Türetim bağlamı: bireyler (∀-eleme için, ∃-eleme ile büyür) + taze tanık
    üreticisi + bir kez elenmiş ∃'ler."""

    def __init__(self, individuals: set[str], taken: set[str]):
        self.individuals = set(individuals)
        self.taken = set(taken) | set(individuals)
        self.eliminated: set[str] = set()
        self._wcount = 0

    def fresh(self) -> str:
        while True:
            self._wcount += 1
            w = f"_w{self._wcount}"
            if w not in self.taken:
                self.taken.add(w)
                self.individuals.add(w)
                return w


# ------------------------- ileri zincirleme çekirdek ---------------------- #
def _apply_rules(node: ast.AST, known: dict, ctx: _Ctx, add: Callable) -> bool:
    changed = False
    if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.And):
        for v in node.values:
            changed |= add(v, "∧-ayıklama", [_key(node)])
    elif isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or) and len(node.values) == 2:
        a, b = node.values
        if _neg_key(a) in known:
            changed |= add(b, "ayrık tasım", [_key(node), _neg_key(a)])
        if _neg_key(b) in known:
            changed |= add(a, "ayrık tasım", [_key(node), _neg_key(b)])
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        inner = node.operand
        if isinstance(inner, ast.UnaryOp) and isinstance(inner.op, ast.Not):
            changed |= add(inner.operand, "çift olumsuzlama", [_key(node)])
        if isinstance(inner, ast.BoolOp) and isinstance(inner.op, ast.Or):
            for v in inner.values:
                changed |= add(_mk_not(v), "De Morgan", [_key(node)])
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        fid, args = node.func.id, node.args
        if fid == "implies" and len(args) == 2:
            if _key(args[0]) in known:
                changed |= add(args[1], "modus ponens", [_key(node), _key(args[0])])
            if _neg_key(args[1]) in known:
                changed |= add(_mk_not(args[0]), "modus tollens", [_key(node), _neg_key(args[1])])
        elif fid == "iff" and len(args) == 2:
            if _key(args[0]) in known:
                changed |= add(args[1], "iff-ayıklama", [_key(node), _key(args[0])])
            if _key(args[1]) in known:
                changed |= add(args[0], "iff-ayıklama", [_key(node), _key(args[1])])
        elif fid == "forall" and len(args) == 2 and isinstance(args[0], ast.Name):
            var, bod = args[0].id, args[1]
            for t in sorted(ctx.individuals):
                changed |= add(_substitute(bod, var, t), f"evrensel örnekleme (x:={t})", [_key(node)])
        elif fid == "exists" and len(args) == 2 and isinstance(args[0], ast.Name):
            ek = _key(node)
            if ek not in ctx.eliminated:
                ctx.eliminated.add(ek)
                witness = ctx.fresh()
                changed |= add(_substitute(args[1], args[0].id, witness),
                               f"varoluşsal eleme (tanık {witness})", [ek])
    return changed


def _find_contradiction(known: dict) -> tuple[str, str] | None:
    for k, fact in known.items():
        nk = _neg_key(fact["node"])
        if nk in known:
            return (k, nk)
    return None


def _saturate(initial: list[tuple], ctx: _Ctx, stop: Callable):
    known: dict[str, dict] = {}
    order = [0]

    def add(node: ast.AST, rule: str, refs: list[str]) -> bool:
        k = _key(node)
        if k not in known:
            known[k] = {"node": node, "rule": rule, "refs": refs, "order": order[0]}
            order[0] += 1
            return True
        return False

    for node, rule, refs in initial:
        add(node, rule, refs)

    result = stop(known)
    rounds = 0
    changed = True
    while result is None and changed and rounds < _MAX_ROUNDS:
        changed = False
        rounds += 1
        for k in list(known.keys()):
            changed |= _apply_rules(known[k]["node"], known, ctx, add)
        result = stop(known)
    return known, result


def _closure(known: dict, roots: list[str]) -> set[str]:
    needed: set[str] = set()
    stack = list(roots)
    while stack:
        k = stack.pop()
        if k in needed or k not in known:
            continue
        needed.add(k)
        stack.extend(known[k]["refs"])
    return needed


def _order_steps(known: dict, needed: set[str]) -> tuple[list[dict], dict[str, int]]:
    ordered = sorted(needed, key=lambda k: known[k]["order"])
    num = {k: i + 1 for i, k in enumerate(ordered)}
    steps = [{
        "step": num[k],
        "formula": _key(known[k]["node"]),
        "rule": known[k]["rule"],
        "refs": [num[r] for r in known[k]["refs"] if r in num],
    } for k in ordered]
    return steps, num


def _new_ctx(premise_nodes: list[ast.AST], goal: ast.AST) -> _Ctx:
    nodes = premise_nodes + [goal]
    return _Ctx(_individuals(nodes), _all_names(nodes))


def _direct_proof(premise_nodes: list[ast.AST], goal: ast.AST) -> list[dict] | None:
    ctx = _new_ctx(premise_nodes, goal)
    initial = [(p, "öncül", []) for p in premise_nodes]
    goal_key = _key(goal)

    def stop(known):
        if goal_key in known:
            return ("direct", goal_key, None)
        if (isinstance(goal, ast.Call) and isinstance(goal.func, ast.Name)
                and goal.func.id == "exists" and len(goal.args) == 2
                and isinstance(goal.args[0], ast.Name)):
            var, psi = goal.args[0].id, goal.args[1]
            for t in sorted(ctx.individuals):
                inst = _key(_substitute(psi, var, t))
                if inst in known:
                    return ("exists_intro", inst, t)
        return None

    known, result = _saturate(initial, ctx, stop)
    if result is None:
        return None
    kind, hit, witness = result
    if kind == "direct":
        return _order_steps(known, _closure(known, [goal_key]))[0]
    steps, num = _order_steps(known, _closure(known, [hit]))
    steps.append({
        "step": len(steps) + 1,
        "formula": goal_key,
        "rule": f"varoluşsal içe alma (tanık {witness})",
        "refs": [num[hit]],
    })
    return steps


def _raa_proof(premise_nodes: list[ast.AST], goal: ast.AST) -> list[dict] | None:
    ctx = _new_ctx(premise_nodes, goal)
    initial = [(p, "öncül", []) for p in premise_nodes]
    initial.append((_mk_not(goal), "varsayım (çelişki için)", []))
    known, result = _saturate(initial, ctx, _find_contradiction)
    if result is None:
        return None
    kpos, kneg = result
    steps, num = _order_steps(known, _closure(known, [kpos, kneg]))
    steps.append({
        "step": len(steps) + 1,
        "formula": _key(goal),
        "rule": "çelişkiden ispat (RAA)",
        "refs": [num[kpos], num[kneg]],
    })
    return steps


def _minimal_core(premises: list[str], conclusion: str, timeout_ms: int, seed: int) -> list[int] | None:
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
    """`premises ⊨ conclusion` mı — ve neden? Z3 verdict + minimal çekirdek +
    (kurulabiliyorsa) doğrudan ya da çelişkiden (RAA) adım adım türetim."""
    t0 = time.perf_counter()
    verdict = check_entailment(premises, conclusion, timeout_ms=timeout_ms, seed=seed)

    if verdict.status == "invalid":
        return ProofResult("invalid", "COUNTEREXAMPLE_FOUND",
                           "Geçersiz: öncülleri sağlayıp sonucu çürüten bir karşıörnek var.",
                           witness=verdict.witness, meta=_meta(t0, seed, timeout_ms))
    if verdict.status != "valid":
        return ProofResult(verdict.status, verdict.reason_code, verdict.explanation,
                           meta=_meta(t0, seed, timeout_ms))

    try:
        core = _minimal_core(premises, conclusion, timeout_ms, seed)
    except (ParseError, GuardrailError):
        core = None

    steps, method = None, ""
    try:
        prem_nodes = [parse(p).body for p in premises]
        goal_node = parse(conclusion).body
        steps = _direct_proof(prem_nodes, goal_node)
        if steps is not None:
            method = "doğrudan"
        else:
            steps = _raa_proof(prem_nodes, goal_node)
            method = "çelişkiden (RAA)" if steps is not None else ""
    except Exception:  # noqa: BLE001 - türetim best-effort; verdict yine sağlam
        steps = None

    if steps is not None:
        explanation = f"Geçerli. {len(steps)} adımlık {method} doğal tümdengelim türetimi kuruldu."
    else:
        explanation = ("Geçerli (Z3 doğruladı). Bu parça için adım adım türetim "
                       "kurulamadı — minimal çekirdek yine de sonucun dayanağını gösterir.")
    return ProofResult("valid", "ENTAILED", explanation,
                       used_premises=core, proof_steps=steps, meta=_meta(t0, seed, timeout_ms))
