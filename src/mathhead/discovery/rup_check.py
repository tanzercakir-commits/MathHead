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
    `budget_exceeded`, never a fake `verified` and never a fake `refuted`;
  * **a BACKWARD checker** (`check_drup_backward`, drat-trim's marking idea) — the forward
    checker RUP-checks every lemma; the backward checker first replays the whole proof without
    checking anything, finds the final conflict, and then walks the proof from the END to the
    start RUP-checking ONLY the lemmas marked as participating in that conflict's derivation
    (each successful RUP check conflict-analyses its unit-propagation cone and marks the
    antecedent clauses used). Unmarked lemmas are never checked — on real solver proofs that is
    the vast majority of the work skipped, which is what makes multi-million-lemma proofs
    checkable in pure Python at all. Soundness of skipping: `verified` claims only that ⊥ is
    derivable from the input by the RUP chain over the MARKED clauses — every clause any
    check's conflict cone used is itself marked (and hence checked when the walk reaches it),
    so by induction over add order every marked lemma is entailed by the input, and so is ⊥.
    Two further drat-trim ideas keep the per-check cost sub-linear in the formula size:
    **core-first propagation** (each check first unit-propagates over the already-marked core
    only — conflicts overwhelmingly live there, and a core conflict costs visits proportional
    to the small core, not the huge formula; the full propagation runs only when the core pass
    finds nothing, and its conflict then grows the core) and **deletion-blind checking** (`d`
    lines are parsed and counted but deliberately NOT applied: ignoring deletions is sound for
    RUP — unit propagation is monotone in the clause set and every deleted clause is an input
    clause or an earlier lemma — and solver deletion info is over-eager at scale, measured at
    54% of checks needing a deletions-ignored retry on a 1.7M-lemma Glucose42 proof, so
    honouring deletions would DOUBLE most propagations to reach the same sound verdict).

Independence, the entire point: this module is pure Python and imports NO solver — not pysat,
not z3. The checker would reject a fabricated proof from anyone, including our own solver call.

The RUP rule, exactly: a lemma clause L is RUP w.r.t. formula F iff assuming the negation of
every literal of L and running unit propagation over F derives a conflict (hence F ⊨ L). A DRUP
proof is a sequence of add/delete steps whose added lemmas are each RUP w.r.t. the formula
accumulated so far, ending in the empty clause ⊥ (or leaving a formula that unit-propagates to
conflict on its own).

DRAT-family proofs (`proof_format="drat"` on the backward checker): solvers like CaDiCaL and
Lingeling emit DRAT, whose steps may be RAT (Resolution Asymmetric Tautology) rather than RUP.
A RAT lemma need not be ENTAILED by the formula — its justification is relative to the exact
current clause set — so this RUP-only checker cannot validate it, and a RUP failure on such a
lemma is NOT evidence the proof is wrong. The backward checker therefore reports a marked
lemma's RUP failure under `proof_format="drat"` as `not_rup_checkable` — a distinct honest
status, deliberately separate from `refuted` (under `proof_format="drup"`, the default, solvers
document RUP-only output and a failure IS `refuted`). `verified` is claimed, in either format,
only when every marked lemma passed its RUP check and ⊥ was derived — and that claim is sound
even for DRAT input, because the verification rests solely on the RUP chain over the marked
clauses (any RAT steps end up unmarked or fail honestly; they are never assumed correct).
"""
from __future__ import annotations

from dataclasses import dataclass

_DEFAULT_VISIT_BUDGET = 500_000_000     # clause visits; R(3,4)<=9 needs well under half of this


@dataclass
class RupCheckResult:
    status: str                          # "verified" | "refuted" | "budget_exceeded" | "error"
    #                                      | "not_rup_checkable" (backward checker, DRAT input:
    #                                      a marked lemma failed RUP but may be a RAT step —
    #                                      honestly UNDECIDED, never claimed refuted)
    message: str
    lemmas_checked: int = 0              # forward: every lemma; backward: only MARKED lemmas
    deletions_applied: int = 0           # forward: deletions honoured; backward: `d` lines seen
    #                                      (parsed, counted, deliberately NOT applied — the
    #                                      deletion-blind mode documented on check_drup_backward)
    visits: int = 0                      # clause visits performed (the budget's unit)
    deletions_ignored_from: int | None = None   # lemma index from which deletions were ignored
    total_lemmas: int = 0                # backward checker: add steps seen (0 on forward paths)

    @property
    def checked_lemmas(self) -> int:
        """Alias of `lemmas_checked` — the backward checker's natural name for it (the count of
        MARKED lemmas actually RUP-checked, against `total_lemmas` add steps in the proof)."""
        return self.lemmas_checked

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


class _BackwardChecker:
    """The clause database of `check_drup_backward`: two-watched-literal BCP with REASON
    tracking (for conflict-cone marking), a retirement flag per clause, and a SECOND watch
    index over the marked CORE (drat-trim's core-first propagation).

    Retirement: when the backward walk passes a clause's own add step the clause is retired —
    from then on it lies in the proof's FUTURE and must never take part in a check (that would
    be circular); a retired clause found in any watch list is purged on sight. `d` lines are
    NOT applied at all (deletion-blind mode — sound for RUP, argued in the module docstring),
    so retirement is the only state a clause has.

    Both watch indexes share each clause's single `watched` pair, so entries can go STALE (the
    pair moved while the entry stayed); every scan validates the entry against the pair and
    purges mismatches lazily. Watch positions persist across checks — every check starts from
    the empty assignment, where any watch pair is valid (same argument as `_Formula`)."""

    def __init__(self) -> None:
        self.clause_lits: list[tuple[int, ...]] = []
        self.retired = bytearray()
        self.marked = bytearray()                            # in the ⊥-derivation cone
        self.watched: list[list[int] | None] = []
        self.watchlist: dict[int, list[int]] = {}            # full index: every 2+-lit clause
        self.core_watchlist: dict[int, list[int]] = {}       # core index: marked clauses only
        self.unit_idxs: list[int] = []
        self.core_unit_idxs: list[int] = []
        self.has_empty = False
        self.assign = bytearray(1)
        self.reason: list[int] = [0]                         # var -> clause idx + 1 (0 = none)
        self.trail: list[int] = []

    def ensure_capacity(self, top: int) -> None:
        if top >= len(self.assign):
            grow = top + 1 - len(self.assign)
            self.assign.extend(bytearray(grow))
            self.reason.extend([0] * grow)

    def add(self, lits) -> int:
        idx = len(self.clause_lits)
        t = tuple(dict.fromkeys(lits))
        self.clause_lits.append(t)
        self.retired.append(0)
        self.marked.append(0)
        if len(t) >= 2:
            self.watched.append([t[0], t[1]])
            self.watchlist.setdefault(t[0], []).append(idx)
            self.watchlist.setdefault(t[1], []).append(idx)
        else:
            self.watched.append(None)
            if len(t) == 1:
                self.unit_idxs.append(idx)
            else:
                self.has_empty = True
        self.ensure_capacity(max((abs(x) for x in t), default=0))
        return idx

    def _propagate(self, assumed, core_only: bool, budget: list[int]):
        """Unit-propagate from `assumed` + active unit clauses, over the core index alone
        (`core_only=True` — cheap, may miss conflicts, never invents one) or the full index.
        Returns the conflict — a clause index, or "assumption" for an assumed-literal clash
        (tautological lemma), or None. Trail/assignment/reasons are LEFT IN PLACE for conflict
        analysis; the caller must `reset()`. TimeoutError when the visit budget is spent."""
        clauses, retired, assign = self.clause_lits, self.retired, self.assign
        reason, watched = self.reason, self.watched
        watchlist = self.core_watchlist if core_only else self.watchlist
        unit_idxs = self.core_unit_idxs if core_only else self.unit_idxs
        trail = self.trail

        def set_lit(lit: int, why: int) -> bool:
            var = lit if lit > 0 else -lit
            val = _TRUE if lit > 0 else _FALSE
            cur = assign[var]
            if cur == _UNSET:
                assign[var] = val
                reason[var] = why
                trail.append(lit)
                return True
            return cur == val

        remaining = budget[0]
        try:
            for lit in assumed:
                if not set_lit(lit, 0):
                    return "assumption"
            i = 0
            while i < len(unit_idxs):
                idx = unit_idxs[i]
                if retired[idx]:                             # future clause: purge on sight
                    unit_idxs[i] = unit_idxs[-1]
                    unit_idxs.pop()
                    continue
                if not set_lit(clauses[idx][0], idx + 1):
                    return idx
                i += 1
            head = 0
            while head < len(trail):
                false_lit = -trail[head]
                head += 1
                wl = watchlist.get(false_lit)
                if not wl:
                    continue
                i = 0
                while i < len(wl):
                    idx = wl[i]
                    w = watched[idx]
                    if retired[idx] or w is None or (w[0] != false_lit and w[1] != false_lit):
                        wl[i] = wl[-1]                       # retired or stale: purge on sight
                        wl.pop()
                        continue
                    remaining -= 1
                    if remaining < 0:
                        raise TimeoutError
                    other = w[0] if w[1] == false_lit else w[1]
                    ov = assign[other if other > 0 else -other]
                    if ov != _UNSET and (ov == _TRUE) == (other > 0):
                        i += 1                               # satisfied by the other watch
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
                        wl[i] = wl[-1]
                        wl.pop()
                        self.watchlist.setdefault(replacement, []).append(idx)
                        if self.marked[idx]:                 # keep the clause findable in BOTH
                            self.core_watchlist.setdefault(replacement, []).append(idx)
                        continue
                    if ov == _UNSET:                         # unit: the other watch is forced
                        if not set_lit(other, idx + 1):
                            return idx
                        i += 1
                        continue
                    return idx                               # both watches false
            return None
        finally:
            budget[0] = remaining

    def reset(self) -> None:
        assign, reason = self.assign, self.reason
        for lit in self.trail:
            var = lit if lit > 0 else -lit
            assign[var] = _UNSET
            reason[var] = 0
        self.trail.clear()

    def _mark(self, idx: int) -> None:
        """Mark a clause into the core: it will be RUP-checked when the walk reaches it, and
        from now on core-first propagation may use it (registered in the core watch index)."""
        self.marked[idx] = 1
        t = self.clause_lits[idx]
        if len(t) >= 2:
            w = self.watched[idx]
            self.core_watchlist.setdefault(w[0], []).append(idx)
            self.core_watchlist.setdefault(w[1], []).append(idx)
        elif len(t) == 1:
            self.core_unit_idxs.append(idx)

    def mark_core(self, conflict_idx: int) -> None:
        """Conflict analysis: mark the conflict clause and, transitively, the reason clause of
        every variable in its unit-propagation cone. Every clause a check USED becomes marked —
        the backward walk will RUP-check exactly those."""
        clauses, reason, marked = self.clause_lits, self.reason, self.marked
        if not marked[conflict_idx]:
            self._mark(conflict_idx)
        seen = bytearray(len(self.assign))
        stack = []
        for x in clauses[conflict_idx]:
            v = x if x > 0 else -x
            seen[v] = 1
            stack.append(v)
        while stack:
            r = reason[stack.pop()] - 1
            if r >= 0:
                if not marked[r]:
                    self._mark(r)
                for x in clauses[r]:
                    v = x if x > 0 else -x
                    if not seen[v]:
                        seen[v] = 1
                        stack.append(v)

    def check_marked_rup(self, lits, budget: list[int]) -> bool:
        """RUP-check one clause against the currently-active clause set, core first: propagate
        the negated literals over the marked core alone — the conflict overwhelmingly lives
        there, and then the cost is proportional to the small core; fall back to the full
        index only when the core pass finds nothing. On success the conflict cone is marked."""
        neg = [-lit for lit in frozenset(lits)]
        conflict = self._propagate(neg, True, budget)
        if conflict is None:
            self.reset()
            conflict = self._propagate(neg, False, budget)
            if conflict is None:
                self.reset()
                return False
        if conflict != "assumption":
            self.mark_core(conflict)
        self.reset()
        return True


def check_drup_backward(clauses: list[list[int]], lines, *,
                        visit_budget: int = _DEFAULT_VISIT_BUDGET,
                        proof_format: str = "drup") -> RupCheckResult:
    """BACKWARD-check a DRUP/DRAT-format proof (drat-trim's marking idea, pure Python).

    Two passes. FORWARD: every add step is appended to the clause database UNCHECKED (watch
    setup only) and every `d` step is applied, stopping at the first empty clause. The final
    conflict — ⊥'s reverse unit propagation, or the accumulated formula conflicting on its own
    (`check_drup_proof`'s closing rule) — is found and its conflict cone MARKED. BACKWARD: the
    proof is walked end-to-start; an add step first retires its clause (a clause in the proof's
    future must never justify an earlier lemma — that would be circular), then, ONLY if the
    clause is marked, RUP-checks it against the formula as it stood at that point (a `d` step
    read backwards is an addition, so deletions are honoured exactly); each successful check
    marks its own conflict cone. Lemmas never marked are never checked — that skipped work is
    the entire speed-up, and skipping is sound: `verified` asserts exactly that ⊥ follows from
    the input by the RUP chain over marked clauses, and every clause any check used is marked.

    Deletion-blind, by measurement: `d` lines are parsed and counted but NOT applied, in both
    directions of the walk. Ignoring deletions is sound for RUP (the module docstring's
    monotonicity argument — every deleted clause is an input clause or an earlier lemma), and
    solver deletion info is over-eager at scale: on a 1.7M-lemma Glucose42 proof 54% of the
    first 1642 deletion-honouring checks failed and needed the deletions-ignored retry, i.e.
    honouring deletions DOUBLED most propagations only to land on the same sound verdict.
    (This differs from drat-trim, which honours deletions; for RUP-only conclusions the two
    are equally sound, and the result records the `d` count it skipped on
    `deletions_applied`.)

    Speed: per check the negated lemma is first propagated over the marked CORE only
    (drat-trim's core-first idea) — conflicts overwhelmingly live in the core, so a check
    usually costs visits proportional to the small core rather than the whole formula; the
    full-index propagation runs only when the core pass finds nothing, and its conflict then
    grows the core.

    `proof_format` decides what a marked lemma's RUP FAILURE means, honestly:

      * "drup" (default — Glucose3/Glucose42, documented RUP-only output): the proof is
        invalid → `refuted`;
      * "drat" (CaDiCaL/Lingeling families): the lemma may be a genuine RAT step, which this
        RUP-only checker cannot validate and does NOT treat as evidence of invalidity →
        `not_rup_checkable` (neither verified nor refuted; the module docstring carries the
        full RAT argument). `verified` under "drat" is still sound — it never leans on any
        unverified RAT step (see the docstring).

    Result fields: `lemmas_checked` = marked lemmas actually RUP-checked (the empty-clause
    step, when present, is counted — its RUP check IS the root-conflict check; the closing
    final-formula conflict of a ⊥-less proof is not an add step and adds no count),
    `total_lemmas` = add steps seen, `deletions_applied` = `d` lines
    recognized (and deliberately skipped). `lines` may be any iterable of strings (a list, or
    a lazily-read file — multi-hundred-MB proofs need not be held in memory as a list).
    Malformed input is an `error` result, never an exception; the visit budget makes an
    exhausted check an honest `budget_exceeded`, never a fake verdict either way."""
    if proof_format not in ("drup", "drat"):
        return RupCheckResult("error",
                              f"proof_format must be 'drup' or 'drat', got {proof_format!r}")
    if not isinstance(clauses, (list, tuple)):
        return RupCheckResult("error",
                              f"clauses must be a list of clauses, got {type(clauses).__name__}")
    if lines is None or isinstance(lines, (str, bytes)):
        return RupCheckResult("error",
                              "proof lines must be an iterable of strings, got "
                              f"{type(lines).__name__}")
    chk = _BackwardChecker()
    for cl in clauses:
        if not isinstance(cl, (list, tuple)):
            return RupCheckResult("error",
                                  f"every clause must be a list of ints, got {type(cl).__name__}")
        chk.add(cl)
    n_input = len(chk.clause_lits)
    if chk.has_empty:
        return RupCheckResult("verified", "the input formula already contains the empty clause")

    # ---- forward pass: replay the proof unchecked (adds only, deletion-blind), stop at ⊥ ----
    steps: list[int] = []            # clause idx per add step, in proof order
    total_lemmas = 0
    deletions = 0
    saw_empty = False
    for raw in lines:
        if not isinstance(raw, str):
            return RupCheckResult("error",
                                  f"proof lines must be strings, got {type(raw).__name__}")
        line = raw.strip()
        if not line or line.startswith("c"):
            continue
        is_delete = False
        if line == "d" or line.startswith("d "):
            is_delete, line = True, line[1:].strip()
        try:
            nums = [int(tok) for tok in line.split()]
        except ValueError:
            return RupCheckResult("error", f"unparseable DRUP line: {raw!r}",
                                  total_lemmas=total_lemmas)
        if nums and nums[-1] == 0:
            nums.pop()
        if any(x == 0 for x in nums):
            return RupCheckResult("error", f"literal 0 inside a DRUP clause: {raw!r}",
                                  total_lemmas=total_lemmas)
        if is_delete:
            deletions += 1                                   # recognized, deliberately skipped
        else:
            total_lemmas += 1
            if not nums:
                saw_empty = True                             # ⊥: the proof's root — stop here
                break
            steps.append(chk.add(nums))

    budget = [visit_budget]
    checked = 0

    def _result(status: str, message: str) -> RupCheckResult:
        return RupCheckResult(status, message, checked, deletions, visit_budget - budget[0],
                              None, total_lemmas)

    try:
        # ---- the root conflict: ⊥'s RUP check / the closing final-formula conflict ----
        conflict = chk._propagate([], False, budget)
        if conflict is None:
            chk.reset()
            return _result("refuted",
                           f"the empty clause (add step {total_lemmas}) is not RUP w.r.t. the "
                           f"accumulated formula" if saw_empty else
                           "the proof ends without deriving the empty clause (and the final "
                           "formula does not unit-propagate to a conflict)")
        chk.mark_core(conflict)
        chk.reset()
        if saw_empty:
            checked += 1                                     # ⊥ itself was just RUP-checked

        # ---- backward walk: retire each add; RUP-check it ONLY if marked ----
        retired, marked, clause_lits = chk.retired, chk.marked, chk.clause_lits
        for enc in reversed(steps):
            retired[enc] = 1                                 # now in the proof's future
            if not marked[enc]:
                continue
            ok = chk.check_marked_rup(clause_lits[enc], budget)
            checked += 1
            if not ok:
                lemma_no = enc - n_input + 1
                cl_text = sorted(clause_lits[enc], key=abs)
                if proof_format == "drup":
                    return _result("refuted",
                                   f"marked proof step {lemma_no} {cl_text} is not RUP w.r.t. "
                                   f"the formula at its position (input + every earlier lemma; "
                                   f"deletion-blind, which only ADDS clauses and can only make "
                                   f"RUP easier)")
                return _result("not_rup_checkable",
                               f"marked proof step {lemma_no} {cl_text} is not RUP at its "
                               f"position; under proof_format='drat' it may be a genuine RAT "
                               f"step, which this RUP-only checker cannot validate — honestly "
                               f"UNDECIDED, not refuted ({checked} of {total_lemmas} lemmas "
                               f"were RUP-checked before this)")
    except TimeoutError:
        return _result("budget_exceeded",
                       f"backward RUP checking exceeded the visit budget ({visit_budget}) "
                       f"after {checked} checked lemmas (of {total_lemmas} total) — no verdict "
                       f"on the proof (honest: neither verified nor refuted)")
    root = ("the empty clause was derived" if saw_empty
            else "the final formula unit-propagates to a conflict")
    return _result("verified",
                   f"{root}; backward check RUP-verified all {checked} marked lemmas "
                   f"(of {total_lemmas} in the proof; {deletions} d lines parsed and "
                   f"deliberately skipped — deletion-blind mode, sound for RUP)")


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
