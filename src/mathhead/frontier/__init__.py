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


def arithmetic_progressions(n: int, k: int) -> list[tuple[int, ...]]:
    """{1..n} içindeki tüm k-terimli aritmetik dizileri döndürür."""
    aps: list[tuple[int, ...]] = []
    for a in range(1, n + 1):
        max_d = (n - a) // (k - 1) if k > 1 else 0
        for d in range(1, max_d + 1):
            aps.append(tuple(a + i * d for i in range(k)))
    return aps


def van_der_waerden_coloring(
    n: int, k: int, colors: int = 2, *, timeout_ms: int = 20_000, seed: int = 42
) -> ReasoningResult:
    """{1..n}, `colors` renge, **tek renkli k-terimli aritmetik dizi olmadan** boyanabilir mi?

    Bu, van der Waerden sayısı W(colors, k)'nın SAT ile hesaplanmasının çekirdeğidir:
    W(r,k) = boyamanın imkânsız hale geldiği en küçük n. `sat` -> boyama var (n < W);
    `unsat` -> imkânsız (n ≥ W, ispat); `unknown` -> ölçek çözücüyü aştı.

    DÜRÜSTLÜK: Bilinen W değerleri bu YÖNTEMLE hesaplandı (aynı kod). Büyük/açık
    değerler (ör. W(2,7)) devasa hesap ister; motor orada dürüstçe `unknown` döner.
    """
    t0 = time.perf_counter()
    if not all(isinstance(x, int) for x in (n, k, colors)):
        return ReasoningResult("error", "GUARDRAIL_VIOLATION", "n, k, colors tam sayı olmalı",
                               None, _meta(t0, seed, timeout_ms))
    if k < 2 or colors < 2 or colors > 6 or n < 1 or n > 5000:
        return ReasoningResult("error", "GUARDRAIL_VIOLATION",
                               "k≥2, colors 2..6, 1≤n≤5000 olmalı",
                               None, _meta(t0, seed, timeout_ms))

    aps = arithmetic_progressions(n, k)
    solver = solver_config(timeout_ms, seed)
    if colors == 2:
        c = {i: z3.Bool(f"c_{i}") for i in range(1, n + 1)}
        for ap in aps:
            solver.add(z3.Or(*[z3.Not(c[i]) for i in ap]))  # hepsi renk-A değil
            solver.add(z3.Or(*[c[i] for i in ap]))          # hepsi renk-B değil
    else:
        c = {i: z3.Int(f"c_{i}") for i in range(1, n + 1)}
        for i in range(1, n + 1):
            solver.add(c[i] >= 0, c[i] < colors)
        for ap in aps:
            solver.add(z3.Or(*[c[ap[j]] != c[ap[j + 1]] for j in range(len(ap) - 1)]))

    extra = {"n": n, "k": k, "colors": colors, "arithmetic_progressions": len(aps)}
    result = solver.check()
    if result == z3.sat:
        model = solver.model()
        if colors == 2:
            coloring = {i: ("A" if z3.is_true(model.eval(c[i], model_completion=True)) else "B")
                        for i in range(1, n + 1)}
        else:
            coloring = {i: model.eval(c[i], model_completion=True).as_long()
                        for i in range(1, n + 1)}
        witness = {"coloring": coloring} if n <= 60 else {"note": f"{n} sayı boyandı (özet gizlendi)"}
        return ReasoningResult(
            "sat", "COLORING_FOUND",
            f"{{1..{n}}}, {colors} renge tek renkli {k}-terimli aritmetik dizi olmadan "
            f"boyanabilir → W({colors},{k}) > {n}.",
            witness, _meta(t0, seed, timeout_ms, extra),
        )
    if result == z3.unsat:
        return ReasoningResult(
            "unsat", "NO_COLORING",
            f"{{1..{n}}} böyle boyanAMAZ — tek renkli {k}-terimli aritmetik dizi kaçınılmaz "
            f"→ W({colors},{k}) ≤ {n} (imkânsızlık ispatlandı).",
            {"note": "imkânsızlık ispatı"}, _meta(t0, seed, timeout_ms, extra),
        )
    return _unknown(solver, t0, seed, timeout_ms, extra)


def schur_number_coloring(
    n: int, colors: int, *, timeout_ms: int = 20_000, seed: int = 42
) -> ReasoningResult:
    """{1..n}, `colors` renge, hiçbir renk sınıfında `x + y = z` (aynı renk) olmadan
    boyanabilir mi? (yani her renk sınıfı **sum-free** mi; x=y'ye izin verilir).

    Schur sayısı S(r) = böyle boyanabilen en büyük n. `n ≤ S(r)` -> `sat`;
    `n = S(r)+1` -> `unsat` (ispat). Bilinen: S(2)=4, S(3)=13, S(4)=44, S(5)=160.
    **S(6) AÇIK.** Bilinen değerler bu yöntemle hesaplandı; büyük ölçek devasadır.
    """
    t0 = time.perf_counter()
    if not all(isinstance(x, int) for x in (n, colors)):
        return ReasoningResult("error", "GUARDRAIL_VIOLATION", "n, colors tam sayı olmalı",
                               None, _meta(t0, seed, timeout_ms))
    if colors < 2 or colors > 6 or n < 1 or n > 500:
        return ReasoningResult("error", "GUARDRAIL_VIOLATION",
                               "colors 2..6, 1≤n≤500 olmalı", None, _meta(t0, seed, timeout_ms))

    solver = solver_config(timeout_ms, seed)
    triples = 0
    if colors == 2:
        c = {i: z3.Bool(f"c_{i}") for i in range(1, n + 1)}
        for x in range(1, n + 1):
            for y in range(x, n + 1):
                z = x + y
                if z > n:
                    break
                solver.add(z3.Or(z3.Not(c[x]), z3.Not(c[y]), z3.Not(c[z])))
                solver.add(z3.Or(c[x], c[y], c[z]))
                triples += 1
    else:
        c = {i: z3.Int(f"c_{i}") for i in range(1, n + 1)}
        for i in range(1, n + 1):
            solver.add(c[i] >= 0, c[i] < colors)
        for x in range(1, n + 1):
            for y in range(x, n + 1):
                z = x + y
                if z > n:
                    break
                solver.add(z3.Or(c[x] != c[y], c[y] != c[z]))
                triples += 1

    extra = {"n": n, "colors": colors, "sum_triples": triples}
    result = solver.check()
    if result == z3.sat:
        model = solver.model()
        if colors == 2:
            coloring = {i: (0 if z3.is_true(model.eval(c[i], model_completion=True)) else 1)
                        for i in range(1, n + 1)}
        else:
            coloring = {i: model.eval(c[i], model_completion=True).as_long()
                        for i in range(1, n + 1)}
        witness = {"coloring": coloring} if n <= 60 else {"note": f"{n} sayı bölündü (özet)"}
        return ReasoningResult(
            "sat", "COLORING_FOUND",
            f"{{1..{n}}}, {colors} sum-free renge bölünebilir → S({colors}) ≥ {n}.",
            witness, _meta(t0, seed, timeout_ms, extra),
        )
    if result == z3.unsat:
        return ReasoningResult(
            "unsat", "NO_COLORING",
            f"{{1..{n}}}, {colors} sum-free renge bölünEMEZ → S({colors}) < {n} "
            f"(imkânsızlık ispatlandı).",
            {"note": "imkânsızlık ispatı"}, _meta(t0, seed, timeout_ms, extra),
        )
    return _unknown(solver, t0, seed, timeout_ms, extra)
