"""
mathhead.discovery.rup_check — independent DRUP/RUP proof checking for SAT-frontier UNSATs (v4F0).

This is the J2 idea (`mathhead.drat`: an UNSAT is not the solver's word, it is a re-checked DRUP
proof) carried to the discovery engine's SAT frontier. `mathhead.drat.rup_check` is the same
algorithm in its smallest honest form; this module is an adaptation of it that solver-emitted
Ramsey proofs actually need in practice:

  * **deletion (`d`) lines are supported** — solver DRUP output interleaves clause deletions with
    lemmas. Deleting a clause only *weakens* the formula, so a lemma that is RUP w.r.t. the
    weakened formula is still a consequence of the original — honouring deletions is sound and
    makes checking faster. Solvers' deletion info is sometimes over-eager (a deleted clause is
    still needed by a later lemma); because *ignoring* deletions is ALSO sound for RUP (unit
    propagation is monotone in the clause set, and every ignored deletion leaves behind an
    already-entailed clause), the checker falls back to include-deleted propagation from the
    first such failure onward — soundness is never traded, only speed. NOTE: that fallback is
    sound for RUP-only proofs (Glucose3's DRUP output) and would NOT be for DRAT's RAT steps —
    see `check_drup_proof`'s docstring for the full argument and the migration trap marker;
  * **occurrence-list BCP over a flat assignment array** — per-lemma reverse unit propagation
    driven by occurrence lists and a propagation trail instead of repeated full-formula scans,
    so multi-thousand-lemma proofs (R(3,4) ≤ 9 is ~9k lemmas) check in tens of seconds;
  * **a visit budget** — pure Python is slow; exceeding the budget is an honest
    `budget_exceeded`, never a fake `verified` and never a fake `refuted`.

Independence, the entire point: this module is pure Python and imports NO solver — not pysat,
not z3. The checker would reject a fabricated proof from anyone, including our own solver call.

The RUP rule, exactly: a lemma clause L is RUP w.r.t. formula F iff assuming the negation of
every literal of L and running unit propagation over F derives a conflict (hence F ⊨ L). A DRUP
proof is a sequence of add/delete steps whose added lemmas are each RUP w.r.t. the formula
accumulated so far, ending in the empty clause ⊥ (or leaving a formula that unit-propagates to
conflict on its own).
"""
from __future__ import annotations

from dataclasses import dataclass

_DEFAULT_VISIT_BUDGET = 500_000_000     # clause visits; R(3,4)<=9 needs well under half of this


@dataclass
class RupCheckResult:
    status: str                          # "verified" | "refuted" | "budget_exceeded" | "error"
    message: str
    lemmas_checked: int = 0
    deletions_applied: int = 0
    visits: int = 0                      # clause visits performed (the budget's unit)
    deletions_ignored_from: int | None = None   # lemma index from which deletions were ignored

    @property
    def ok(self) -> bool:
        return self.status == "verified"


def parse_drup(lines: list[str]) -> list[tuple[str, tuple[int, ...]]]:
    """Parse solver DRUP output lines ("1 -2 0", "d 3 4 0", "0") into (op, literals) steps.

    op is "a" (add lemma) or "d" (delete clause). The trailing 0 terminator is optional.
    Comment lines ("c ...") and blank lines are skipped. Raises ValueError on garbage —
    a malformed proof is rejected loudly, never partially trusted.
    """
    steps: list[tuple[str, tuple[int, ...]]] = []
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("c"):
            continue
        op = "a"
        if line == "d" or line.startswith("d "):
            op, line = "d", line[1:].strip()
        try:
            nums = [int(tok) for tok in line.split()]
        except ValueError as exc:
            raise ValueError(f"unparseable DRUP line: {raw!r}") from exc
        if nums and nums[-1] == 0:
            nums = nums[:-1]
        if any(x == 0 for x in nums):
            raise ValueError(f"literal 0 inside a DRUP clause: {raw!r}")
        steps.append((op, tuple(nums)))
    return steps


_UNSET, _TRUE, _FALSE = 0, 1, 2


class _Formula:
    """The accumulating clause set: two-watched-literal BCP, deletion flags, a reset trail.

    The watch invariant is the textbook one — a clause is revisited only when one of its two
    watched literals becomes false — which is what makes ~9k-lemma proofs checkable in pure
    Python. Watch positions persist across lemma checks (every check starts from the empty
    assignment, where any watch pair is valid)."""

    def __init__(self, clauses: list) -> None:
        self.clauses: list[tuple[int, ...]] = []
        self.deleted: list[bool] = []
        self.watchlist: dict[int, list[int]] = {}            # literal -> clauses watching it
        self.watched: list[list[int] | None] = []            # idx -> its two watched literals
        self.by_key: dict[frozenset, list[int]] = {}         # for deletion matching
        self.unit_idxs: list[int] = []                       # indices of unit clauses
        self.has_empty = False
        self.assign = bytearray(1)                           # var -> _UNSET/_TRUE/_FALSE
        for cl in clauses:
            self.add(cl)

    def add(self, lits) -> None:
        idx = len(self.clauses)
        t = tuple(dict.fromkeys(lits))                       # dedupe, keep order
        self.clauses.append(t)
        self.deleted.append(False)
        self.by_key.setdefault(frozenset(t), []).append(idx)
        if len(t) >= 2:
            w = [t[0], t[1]]
            self.watched.append(w)
            self.watchlist.setdefault(t[0], []).append(idx)
            self.watchlist.setdefault(t[1], []).append(idx)
        else:
            self.watched.append(None)
            if len(t) == 1:
                self.unit_idxs.append(idx)
            else:
                self.has_empty = True
        self.ensure_capacity(max((abs(x) for x in t), default=0))

    def ensure_capacity(self, top: int) -> None:
        """Grow the assignment array to hold variable `top` (a proof lemma may mention a
        variable the input formula never does — it must be assignable, not a crash)."""
        if top >= len(self.assign):
            self.assign.extend(bytearray(top + 1 - len(self.assign)))

    def delete(self, lits) -> bool:
        """Mark one active clause equal (as a literal set) to `lits` deleted; False if none."""
        stack = self.by_key.get(frozenset(lits), [])
        while stack:
            idx = stack.pop()
            if not self.deleted[idx]:
                self.deleted[idx] = True
                return True
        return False

    def propagates_to_conflict(self, assumed, include_deleted: bool, budget: list[int]) -> bool:
        """True iff unit propagation from `assumed` (+ the formula's unit clauses) conflicts.

        `budget` is a one-cell counter of remaining clause visits; TimeoutError when spent
        (the caller reports budget_exceeded honestly — neither verified nor refuted).
        """
        clauses, deleted, assign = self.clauses, self.deleted, self.assign
        watchlist, watched = self.watchlist, self.watched
        trail: list[int] = []

        def set_lit(lit: int) -> bool:
            var = lit if lit > 0 else -lit
            val = _TRUE if lit > 0 else _FALSE
            cur = assign[var]
            if cur == _UNSET:
                assign[var] = val
                trail.append(lit)
                return True
            return cur == val

        remaining = budget[0]
        try:
            for lit in assumed:
                if not set_lit(lit):
                    return True
            for idx in self.unit_idxs:
                if (include_deleted or not deleted[idx]) and not set_lit(clauses[idx][0]):
                    return True
            head = 0
            while head < len(trail):
                false_lit = -trail[head]                     # this literal just became false
                head += 1
                wl = watchlist.get(false_lit)
                if not wl:
                    continue
                i = 0
                while i < len(wl):
                    idx = wl[i]
                    if deleted[idx] and not include_deleted:
                        i += 1
                        continue
                    remaining -= 1
                    if remaining < 0:
                        raise TimeoutError
                    w = watched[idx]
                    other = w[0] if w[1] == false_lit else w[1]
                    ov = assign[other if other > 0 else -other]
                    if ov != _UNSET and (ov == _TRUE) == (other > 0):
                        i += 1                               # clause satisfied by the other watch
                        continue
                    replacement = 0
                    for x in clauses[idx]:
                        if x == other or x == false_lit:
                            continue
                        v = assign[x if x > 0 else -x]
                        if v == _UNSET or (v == _TRUE) == (x > 0):
                            replacement = x
                            break
                    if replacement:
                        w[0 if w[0] == false_lit else 1] = replacement
                        wl[i] = wl[-1]                       # swap-pop out of this watch list
                        wl.pop()
                        watchlist.setdefault(replacement, []).append(idx)
                        continue                             # wl[i] is now a different clause
                    if ov == _UNSET:                         # unit: the other watch is forced
                        if not set_lit(other):
                            return True
                        i += 1
                        continue
                    return True                              # both watches false, no way out
            return False
        finally:
            budget[0] = remaining
            for lit in trail:                                # reset for the next lemma check
                assign[lit if lit > 0 else -lit] = _UNSET


def check_drup_proof(clauses: list[list[int]],
                     steps: list[tuple[str, tuple[int, ...]]],
                     visit_budget: int = _DEFAULT_VISIT_BUDGET) -> RupCheckResult:
    """Independently verify a parsed DRUP proof (`parse_drup`) refutes `clauses`.

    Every added lemma must be RUP w.r.t. the formula accumulated so far (original clauses plus
    earlier lemmas, minus deletions — falling back to ignore-deletions, which is equally sound,
    if the solver's deletion info proves over-eager). The proof succeeds when the empty clause
    is derived, or when the final formula unit-propagates to a conflict on its own. Anything
    else is `refuted`. Pure Python, no solver — that is the independence guarantee.

    Two documented soundness boundaries:

      * **Ignoring deletions is sound for RUP, and ONLY for RUP.** Unit propagation is monotone
        in the clause set, and every clause a `d`-line would remove is either an input clause or
        an already-RUP-verified lemma — i.e. entailed by the input — so keeping it can only help
        derive entailed conclusions. This argument breaks for DRAT's RAT steps, whose
        justification is *relative* to the exact current clause set (a RAT lemma need not be
        entailed, and extra clauses can invalidate the RAT property or its models). This checker
        therefore assumes RUP-only proofs — true for Glucose3's DRUP output, which this engine
        uses. TRAP MARKER for a future Cadical/DRAT migration: a proof with genuine RAT steps
        must NOT be routed through the ignore-deletions fallback (it would honestly come out
        `refuted` here, never falsely `verified`, but a real DRAT checker is the fix).
      * **A proof truncated just before the empty clause still verifies** — the final-formula
        conflict rule: if the input F plus the RUP-verified lemmas unit-propagates to a conflict
        from the empty assignment, then F ∪ lemmas is UNSAT; since every lemma is entailed by F,
        F itself is UNSAT. Sound, and exactly `mathhead.drat.rup_check`'s closing rule.

    Malformed input (`None`, non-lists) is an `error` result, never an exception.
    """
    if not isinstance(clauses, (list, tuple)) or not isinstance(steps, (list, tuple)):
        return RupCheckResult("error", "clauses and steps must be lists (got "
                                       f"{type(clauses).__name__}, {type(steps).__name__})")
    formula = _Formula(clauses)
    budget = [visit_budget]
    lemmas_checked = 0
    deletions = 0
    ignore_from: int | None = None
    if formula.has_empty:
        return RupCheckResult("verified", "the input formula already contains the empty clause",
                              0, 0, 0)

    def _result(status: str, message: str) -> RupCheckResult:
        return RupCheckResult(status, message, lemmas_checked, deletions,
                              visit_budget - budget[0], ignore_from)

    try:
        for op, lits in steps:
            if op == "d":
                deletions += formula.delete(lits)
                continue
            formula.ensure_capacity(max((abs(x) for x in lits), default=0))
            neg = [-lit for lit in frozenset(lits)]
            ok = formula.propagates_to_conflict(neg, ignore_from is not None, budget)
            if not ok and ignore_from is None:
                # The solver deleted a clause a later lemma still needs. Ignoring deletions is
                # just as sound (extra clauses only help propagation), so switch — permanently,
                # and say so on the result.
                ok = formula.propagates_to_conflict(neg, True, budget)
                if ok:
                    ignore_from = lemmas_checked + 1
            if not ok:
                return _result("refuted",
                               f"proof step {lemmas_checked + 1} {sorted(lits, key=abs)} is not "
                               f"RUP w.r.t. the accumulated formula")
            lemmas_checked += 1
            formula.add(lits)
            if not lits:
                return _result("verified",
                               f"the empty clause was derived by reverse unit propagation "
                               f"({lemmas_checked} lemmas checked, {deletions} deletions applied)")
        if formula.propagates_to_conflict([], ignore_from is not None, budget) or \
                (ignore_from is None and formula.propagates_to_conflict([], True, budget)):
            return _result("verified",
                           f"the final formula unit-propagates to a conflict "
                           f"({lemmas_checked} lemmas checked, {deletions} deletions applied)")
    except TimeoutError:
        return _result("budget_exceeded",
                       f"RUP checking exceeded the visit budget ({visit_budget}) after "
                       f"{lemmas_checked} lemmas — no verdict on the proof "
                       f"(honest: neither verified nor refuted)")
    return _result("refuted", "the proof ends without deriving the empty clause")


def check_drup_lines(clauses: list[list[int]], lines: list[str],
                     visit_budget: int = _DEFAULT_VISIT_BUDGET) -> RupCheckResult:
    """`check_drup_proof` over raw solver output lines (pysat `Solver.get_proof()` format).

    Malformed input — `None`, a non-iterable, non-string lines, unparseable literals — is an
    `error` result, never an exception and never a partial verdict.
    """
    if not isinstance(clauses, (list, tuple)):
        return RupCheckResult("error", f"clauses must be a list of clauses, got {type(clauses).__name__}")
    if not isinstance(lines, (list, tuple)) or any(not isinstance(x, str) for x in lines):
        return RupCheckResult("error",
                              f"proof lines must be a list of strings, got "
                              f"{type(lines).__name__ if not isinstance(lines, (list, tuple)) else 'non-string entries'}")
    try:
        steps = parse_drup(lines)
    except ValueError as exc:
        return RupCheckResult("error", str(exc))
    return check_drup_proof(clauses, steps, visit_budget=visit_budget)
