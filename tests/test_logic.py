"""
v1 DAVRANIŞ SPESİFİKASYONU — best-case / worst-case senaryolar.

Bu dosya aynı zamanda yaşayan bir spec'tir: her test, motorun v1'de vermesi
gereken bilinen-doğru sonucu kodlar. Gövdeler henüz yazılmadığı için testler
şu an `xfail` (beklenen başarısızlık). Çekirdek doldurulunca `xpass` olur;
bu, "testleri aktif et" hatırlatıcısıdır (Todo.md > T7).

Kaynak: proje prensibi "iyi tasarlanmış otomatik testler (best/worst case)".
"""
import pytest

from mathhead.core import check_consistency, check_entailment, find_model

pytestmark = pytest.mark.xfail(
    reason="v1 çekirdeği henüz yazılmadı (Todo T3-T5)", strict=False
)


# --------------------------- BEST CASE ---------------------------
# Bilinen, tartışmasız doğru sonuçlar. Motor bunları KESİN vermeli.

def test_modus_ponens_is_valid():
    # p, (p -> q)  ⊨  q
    r = check_entailment(premises=["p", "implies(p, q)"], conclusion="q")
    assert r.status == "valid"
    assert r.reason_code == "ENTAILED"


def test_non_entailment_returns_counterexample():
    # p  ⊭  q   (karşıörnek: p=true, q=false)
    r = check_entailment(premises=["p"], conclusion="q")
    assert r.status == "invalid"
    assert r.witness is not None  # somut karşıörnek dönmeli


def test_contradiction_is_unsat():
    # { p, ¬p } tutarsız
    r = check_consistency(["p", "not(p)"])
    assert r.status == "unsat"


def test_linear_arithmetic_model():
    # x > 2 ∧ x < 5  -> sat (Int teorisi), ör. x = 3
    r = find_model(["x > 2", "x < 5"])
    assert r.status == "sat"
    assert r.witness is not None


# --------------------------- WORST CASE --------------------------
# Sınır durumlar: motor ASLA uydurmamalı; 'unknown'/'error' birinci sınıf.

def test_unknown_is_reported_honestly():
    # Zor/karar-verilemez girdide sonuç 'unknown' olabilir; motor bunu
    # gizleyip sahte bir 'valid/sat' UYDURMAMALI (dürüstlük prensibi).
    r = check_consistency(["forall_x(exists_y(p(x, y)))"])
    assert r.status in ("sat", "unsat", "unknown")
    assert r.is_conclusive() or r.status == "unknown"
