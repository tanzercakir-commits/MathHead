"""
mathhead.frontier — Track B tohumu.

**Fikir (Plan.md §2, Track B):** Zor/açık problemleri **sağlanabilirlik
(satisfiability)** sorusuna indirgeyip Z3 ile çözmek. SMT/SAT çözücüleri bu
yöntemle onlarca yıllık açık problemleri fiilen çözdü (Boolean Pythagorean
Triples 2016, Keller 7. boyut 2020, Schur 5 2017).

**DÜRÜSTLÜK sınırı:** Buradaki küçük örnekler o ünlü sonuçların *kendisi*
değildir — **aynı indirgeme yöntemidir**. Boolean Pythagorean'ın n=7825 sınırı
~200 TB ispat gerektirdi; biz küçük n'i anında çözüyoruz. *Yöntem aynı, ölçek
farklı.* Bu modülün amacı yöntemi somut ve çalışır göstermek.

Bu katman, kullanıcı girdi dilini DEĞİL, problemin **programatik kodlamasını**
kullanır (kodlama mantığı burada, güvenle). Çıktı yine ortak `ReasoningResult`.
"""
from __future__ import annotations

import math
import time
from typing import Any

import z3

from mathhead.core.logic import ReasoningResult
from mathhead.guardrails import solver_config


def _meta(t0: float, seed: int, timeout_ms: int, extra: dict | None = None) -> dict[str, Any]:
    meta = {
        "engine": "z3",
        "z3_version": z3.get_version_string(),
        "elapsed_ms": round((time.perf_counter() - t0) * 1000, 3),
        "seed": seed,
        "timeout_ms": timeout_ms,
    }
    if extra:
        meta.update(extra)
    return meta


def _unknown(solver: z3.Solver, t0: float, seed: int, timeout_ms: int, extra: dict) -> ReasoningResult:
    reason = solver.reason_unknown()
    code = "SOLVER_TIMEOUT" if reason == "timeout" else "SOLVER_UNKNOWN"
    return ReasoningResult(
        "unknown", code,
        f"Çözücü bu ölçekte karar veremedi ({reason}). Yöntem doğru; ölçek büyük.",
        None, _meta(t0, seed, timeout_ms, extra),
    )


def pythagorean_triples(n: int) -> list[tuple[int, int, int]]:
    """{1..n} içindeki tüm Pythagoras üçlülerini (a² + b² = c², a≤b) döndürür."""
    triples = []
    for a in range(1, n + 1):
        for b in range(a, n + 1):
            s = a * a + b * b
            c = math.isqrt(s)
            if c * c == s and c <= n:
                triples.append((a, b, c))
    return triples


def boolean_pythagorean_coloring(n: int, *, timeout_ms: int = 10_000, seed: int = 42) -> ReasoningResult:
    """{1..n} sayıları 2 renge, **tek renkli Pythagoras üçlüsü olmadan** boyanabilir mi?

    İndirgeme: her i için Boolean `c_i` (True=kırmızı). Her (a,b,c) üçlüsü için
    "hepsi kırmızı değil" ve "hepsi mavi değil" kısıtı. SAT -> boyama var;
    UNSAT -> imkânsız (ispat).

    (Bu, 2016'da n=7825'in boyanamadığını kanıtlayan ~200 TB'lık ispatın *aynı*
    kodlamasıdır; biz küçük n'i çözüyoruz.)
    """
    t0 = time.perf_counter()
    if not isinstance(n, int) or n < 1 or n > 3000:
        return ReasoningResult(
            "error", "GUARDRAIL_VIOLATION", "n, 1..3000 arası tam sayı olmalı",
            None, _meta(t0, seed, timeout_ms),
        )
    triples = pythagorean_triples(n)
    color = {i: z3.Bool(f"c_{i}") for i in range(1, n + 1)}
    solver = solver_config(timeout_ms, seed)
    for a, b, c in triples:
        solver.add(z3.Or(z3.Not(color[a]), z3.Not(color[b]), z3.Not(color[c])))  # hepsi kırmızı değil
        solver.add(z3.Or(color[a], color[b], color[c]))                          # hepsi mavi değil

    extra = {"n": n, "pythagorean_triples": len(triples)}
    result = solver.check()
    if result == z3.sat:
        model = solver.model()
        reds = [i for i in range(1, n + 1) if z3.is_true(model.eval(color[i], model_completion=True))]
        if n <= 60:
            coloring = {i: ("kırmızı" if i in set(reds) else "mavi") for i in range(1, n + 1)}
            witness: dict[str, Any] = {"coloring": coloring}
        else:
            witness = {"kirmizi_sayisi": len(reds), "mavi_sayisi": n - len(reds),
                       "not": "boyama çok uzun; özetlendi"}
        return ReasoningResult(
            "sat", "COLORING_FOUND",
            f"{{1..{n}}} iki renge, tek renkli Pythagoras üçlüsü olmadan boyanabilir "
            f"({len(triples)} üçlü kısıtı sağlandı).",
            witness, _meta(t0, seed, timeout_ms, extra),
        )
    if result == z3.unsat:
        return ReasoningResult(
            "unsat", "NO_COLORING",
            f"{{1..{n}}} böyle boyanAMAZ — tek renkli bir Pythagoras üçlüsü kaçınılmaz "
            f"(imkânsızlık ispatlandı).",
            {"note": "bu bir imkânsızlık ispatıdır"}, _meta(t0, seed, timeout_ms, extra),
        )
    return _unknown(solver, t0, seed, timeout_ms, extra)


def pigeonhole(n: int, *, timeout_ms: int = 10_000, seed: int = 42) -> ReasoningResult:
    """`n+1` güvercin `n` kutuya, çakışmadan yerleştirilebilir mi? (güvercin yuvası)

    Beklenen: **unsat** — yani motor güvercin yuvası ilkesini *ispatlar*. Klasik
    bir teoremi indirgemeyle kanıtlamanın örneği. (Not: PHP, CDCL için üstel
    zordur; büyük n zaman aşımına uğrayabilir — bu dürüstçe `unknown` döner.)
    """
    t0 = time.perf_counter()
    if not isinstance(n, int) or n < 1 or n > 10:
        return ReasoningResult(
            "error", "GUARDRAIL_VIOLATION",
            "n, 1..10 arası tam sayı olmalı (PHP çözücü için üstel zordur)",
            None, _meta(t0, seed, timeout_ms),
        )
    pigeons, holes = n + 1, n
    p = [[z3.Bool(f"p_{i}_{j}") for j in range(holes)] for i in range(pigeons)]
    solver = solver_config(timeout_ms, seed)
    for i in range(pigeons):                        # her güvercin en az bir kutuda
        solver.add(z3.Or(*p[i]))
    for j in range(holes):                          # hiçbir kutuda iki güvercin yok
        for i1 in range(pigeons):
            for i2 in range(i1 + 1, pigeons):
                solver.add(z3.Or(z3.Not(p[i1][j]), z3.Not(p[i2][j])))

    extra = {"guvercin": pigeons, "kutu": holes}
    result = solver.check()
    if result == z3.unsat:
        return ReasoningResult(
            "unsat", "PROVEN_IMPOSSIBLE",
            f"{pigeons} güvercin {holes} kutuya çakışmadan yerleştirilEMEZ — "
            f"güvercin yuvası ilkesi ispatlandı.",
            {"note": "imkânsızlık ispatı (teorem)"}, _meta(t0, seed, timeout_ms, extra),
        )
    if result == z3.sat:
        return ReasoningResult(
            "sat", "UNEXPECTED_SAT",
            "Beklenmedik: yerleşim bulundu (ilke gereği olmamalıydı).",
            None, _meta(t0, seed, timeout_ms, extra),
        )
    return _unknown(solver, t0, seed, timeout_ms, extra)
