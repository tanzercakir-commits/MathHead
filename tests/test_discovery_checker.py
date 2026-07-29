"""Discovery — an INDEPENDENT proof checker: re-verify proofs, reject anything it can't confirm."""
from mathhead.discovery import run_arithmetic_discovery
from mathhead.discovery.checker import check_proof, independently_verify
from mathhead.discovery.proof_tree import ProofNode, proof_tree


def _fn(expr):
    return {"n**3 - n": lambda n: n**3 - n, "n**5 - n": lambda n: n**5 - n}[expr]


def _tree(expr):
    return proof_tree({f.expression: f for f in run_arithmetic_discovery(check_upto=40)}[expr])


def test_independently_confirms_a_crt_proof_and_its_reasoning():
    ok, detail = check_proof(_tree("n**3 - n"), _fn("n**3 - n"))
    assert ok
    assert detail["coprime"] and detail["product_ok"]      # CRT structure checks out (2·3 = 6)


def test_independently_confirms_a_residue_proof():
    ok, detail = check_proof(_tree("n**5 - n"), _fn("n**5 - n"))
    assert ok and detail["residues_checked"] == 30


def test_checker_rejects_a_false_claim():
    # a fabricated proof node claiming n²+1 ≡ 0 mod 4 (false) is REJECTED by the checker
    bogus = ProofNode("(n**2 + 1) % 4 == 0", "residue-exhaustion", "exhaustive_residue_proof")
    ok, _ = check_proof(bogus, lambda n: n**2 + 1)
    assert not ok


def test_checker_rejects_broken_crt_reasoning():
    # children claim mod 2 & mod 3 (product 6) but the goal claims mod 12 -> product mismatch
    kids = [ProofNode("(n**3 - n) % 2 == 0", "induction", "formal_proof"),
            ProofNode("(n**3 - n) % 3 == 0", "induction", "formal_proof")]
    fake = ProofNode("(n**3 - n) % 12 == 0", "CRT", "formal_proof", kids)
    ok, detail = check_proof(fake, lambda n: n**3 - n)
    assert not ok and not detail["product_ok"]             # 2·3 ≠ 12: reasoning rejected


def test_independently_verify_is_complete():
    assert independently_verify(lambda n: n**5 - n, 30)
    assert not independently_verify(lambda n: n**2 + 1, 4)
