"""
Track B tohumu — problem → SAT indirgeme.

En değerli test: motorun ÜRETTİĞİ çözümü bağımsız doğrulamak (boyama gerçekten
tek renkli üçlü içermiyor mu) ve bir imkânsızlığı ispatladığını görmek.
"""
from mathhead.frontier import (
    arithmetic_progressions,
    boolean_pythagorean_coloring,
    graph_coloring,
    pigeonhole,
    pythagorean_triples,
    schur_number_coloring,
    subset_sum,
    van_der_waerden_coloring,
)


def test_pythagorean_triples_enumeration():
    assert (3, 4, 5) in pythagorean_triples(5)
    assert (6, 8, 10) in pythagorean_triples(10)
    assert pythagorean_triples(4) == []  # 5'ten küçük üçlü yok


def test_small_set_is_colorable():
    r = boolean_pythagorean_coloring(20)
    assert r.status == "sat"
    assert r.reason_code == "COLORING_FOUND"


def test_produced_coloring_has_no_monochromatic_triple():
    # Motorun döndürdüğü boyamayı BAĞIMSIZ doğrula (çözüm gerçekten geçerli mi).
    r = boolean_pythagorean_coloring(30)
    assert r.status == "sat"
    coloring = r.witness["coloring"]
    for a, b, c in pythagorean_triples(30):
        assert len({coloring[a], coloring[b], coloring[c]}) == 2  # tek renkli DEĞİL


def test_pigeonhole_is_proven_impossible():
    r = pigeonhole(4)  # 5 güvercin, 4 kutu
    assert r.status == "unsat"
    assert r.reason_code == "PROVEN_IMPOSSIBLE"


def test_guardrail_rejects_out_of_range():
    assert boolean_pythagorean_coloring(10**6).status == "error"
    assert pigeonhole(999).status == "error"


# --------------------- van der Waerden (W(colors,k)) ---------------------- #
def test_arithmetic_progressions_enumeration():
    assert (1, 2, 3) in arithmetic_progressions(3, 3)
    assert arithmetic_progressions(2, 3) == []  # 3-AP için >=3 eleman gerekir


def test_vdw_w23_boundary():
    # W(2,3) = 9: n=8 boyanabilir, n=9 imkânsız (bilinen değeri yeniden üretir)
    assert van_der_waerden_coloring(8, 3).status == "sat"
    assert van_der_waerden_coloring(9, 3).status == "unsat"


def test_vdw_w24_is_proven_unsat():
    # W(2,4) = 35: {1..35} 2-renkle 4-AP'siz boyanamaz (gerçek imkânsızlık ispatı)
    assert van_der_waerden_coloring(35, 4).status == "unsat"


def test_vdw_produced_coloring_is_valid():
    r = van_der_waerden_coloring(34, 4)  # n=34 < W(2,4)=35 -> boyanabilir
    assert r.status == "sat"
    coloring = r.witness["coloring"]
    for ap in arithmetic_progressions(34, 4):
        assert len({coloring[i] for i in ap}) == 2  # üçlü/dizi tek renkli DEĞİL


def test_vdw_guardrail():
    assert van_der_waerden_coloring(10, 1).status == "error"       # k<2
    assert van_der_waerden_coloring(10**6, 3).status == "error"    # n çok büyük


# --------------------------- Schur sayıları S(r) -------------------------- #
def test_schur_s2_boundary():
    # S(2) = 4: {1..4} 2 sum-free renge bölünür; {1..5} bölünmez
    assert schur_number_coloring(4, 2).status == "sat"
    assert schur_number_coloring(5, 2).status == "unsat"


def test_schur_s3_boundary():
    # S(3) = 13: {1..13} 3 sum-free renge bölünür; {1..14} bölünmez (imkânsızlık ispatı)
    assert schur_number_coloring(13, 3).status == "sat"
    assert schur_number_coloring(14, 3).status == "unsat"


def test_schur_produced_coloring_is_sum_free():
    # Motorun döndürdüğü bölmeyi BAĞIMSIZ doğrula: hiçbir renk sınıfında x+y=z yok
    r = schur_number_coloring(13, 3)
    assert r.status == "sat"
    col = r.witness["coloring"]
    for x in range(1, 14):
        for y in range(x, 14):
            z = x + y
            if z <= 13:
                assert not (col[x] == col[y] == col[z])


def test_schur_guardrail():
    assert schur_number_coloring(10, 1).status == "error"      # colors<2
    assert schur_number_coloring(9999, 3).status == "error"    # n çok büyük


def test_symmetry_break_preserves_result():
    # Simetri kırma bir OPTİMİZASYON; sat/unsat sonucunu DEĞİŞTİRMEMELİ.
    assert schur_number_coloring(13, 3, symmetry_break=True).status == "sat"
    assert schur_number_coloring(14, 3, symmetry_break=True).status == "unsat"
    assert van_der_waerden_coloring(35, 4, symmetry_break=True).status == "unsat"


# --------- Aşama 10: yeni indirgemeler + doğrulanabilir sertifika ---------- #
def test_graph_coloring_triangle_3colorable():
    # Üçgen (K3) 3 renge boyanabilir; tanık BAĞIMSIZ doğrulanmış olmalı
    r = graph_coloring([[1, 2], [2, 3], [1, 3]], 3)
    assert r.status == "sat"
    assert r.reason_code == "COLORING_FOUND"
    assert r.meta.get("verified") is True
    # sertifikayı testin kendisi de bağımsız kontrol etsin
    col = r.witness["coloring"]
    assert all(col[u] != col[v] for u, v in ([1, 2], [2, 3], [1, 3]))


def test_graph_coloring_triangle_not_2colorable():
    # K3 iki renge BOYANAMAZ (tek sayılı döngü)
    r = graph_coloring([[1, 2], [2, 3], [1, 3]], 2)
    assert r.status == "unsat"
    assert r.reason_code == "NO_COLORING"


def test_graph_coloring_k4_needs_4():
    # K4 üç renge boyanamaz (kromatik sayı 4)
    assert graph_coloring([[1, 2], [1, 3], [1, 4], [2, 3], [2, 4], [3, 4]], 3).status == "unsat"


def test_graph_coloring_bad_edge_rejected():
    assert graph_coloring([[1, 2, 3]], 2).status == "error"


def test_subset_sum_found_and_verified():
    r = subset_sum([3, 34, 4, 12, 5, 2], 9)
    assert r.status == "sat"
    assert r.meta.get("verified") is True
    assert sum(r.witness["subset"]) == 9      # sertifikayı bağımsız doğrula


def test_subset_sum_none():
    # 1,2,4 ile 8'e ulaşılamaz (max 7)
    assert subset_sum([1, 2, 4], 8).status == "unsat"


def test_subset_sum_empty_rejected():
    assert subset_sum([], 5).status == "error"


def test_trackB_determinism():
    for _ in range(3):
        assert graph_coloring([[1, 2], [2, 3], [1, 3]], 2).status == "unsat"
        assert subset_sum([3, 4, 2], 9).status == "sat"
