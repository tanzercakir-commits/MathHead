from __future__ import annotations

import copy
import dataclasses
import hashlib
import importlib.util
from itertools import combinations, product
import json
from pathlib import Path
import pickle
import sys
import unittest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from mathhead.kernel import sat  # noqa: E402
from mathhead.kernel.sat import (  # noqa: E402
    SATReplayResult,
    SATReplayStats,
    SATReplayValidationError,
    canonical_cnf_bytes,
    canonical_drup_bytes,
    canonical_sat_assignment_bytes,
    check_sat_certificate,
    parse_sat_replay_result,
    sat_replay_result_sha256,
    sat_replay_result_to_bytes,
    validate_sat_replay_result,
)


def _drup(cnf: bytes, records: str = "") -> bytes:
    return (
        f"p mathhead-drup 1 {hashlib.sha256(cnf).hexdigest()}\n" + records
    ).encode("ascii")


def _drat(cnf: bytes) -> bytes:
    return f"p mathhead-drat 1 {hashlib.sha256(cnf).hexdigest()}\n".encode("ascii")


class SATReplayTests(unittest.TestCase):
    def test_sat_assignment_verifies_and_false_assignment_is_refuted(self) -> None:
        cnf = canonical_cnf_bytes([[1, 2], [-1, 2]])
        verified = check_sat_certificate(cnf, canonical_sat_assignment_bytes(cnf, [1, 2]))
        refuted = check_sat_certificate(cnf, canonical_sat_assignment_bytes(cnf, [1, -2]))
        self.assertEqual((verified.verdict, verified.reason_code), ("verified", "SAT_VERIFIED"))
        self.assertEqual(verified.authority, "checker_attestation")
        self.assertEqual((refuted.verdict, refuted.reason_code), ("refuted", "CLAIM_REFUTED"))
        self.assertEqual(refuted.authority, "none")

    def test_sat_assignment_must_be_complete_exact_and_ordered(self) -> None:
        cnf = canonical_cnf_bytes([[1, 2]])
        digest = hashlib.sha256(cnf).hexdigest()
        cases = (
            f"p mathhead-sat-assignment 1 {digest}\nv 1 0\n",
            f"p mathhead-sat-assignment 1 {digest}\nv 2 1 0\n",
            f"p mathhead-sat-assignment 1 {digest}\nv 1 -1 0\n",
            f"p mathhead-sat-assignment 1 {digest}\nv 1 2 0\nv 1 2 0\n",
        )
        for certificate in cases:
            result = check_sat_certificate(cnf, certificate.encode("ascii"))
            self.assertEqual(result.verdict, "invalid")
            self.assertEqual(result.authority, "none")

    def test_direct_conflict_and_explicit_empty_clause_verify_unsat(self) -> None:
        direct = canonical_cnf_bytes([[1], [-1]])
        direct_result = check_sat_certificate(direct, canonical_drup_bytes(direct, []))
        self.assertEqual(direct_result.reason_code, "UNSAT_VERIFIED")
        nontrivial = canonical_cnf_bytes([[1, 2], [1, -2], [-1, 2], [-1, -2]])
        proof = canonical_drup_bytes(nontrivial, [("a", (1,)), ("a", (-1,)), ("a", ())])
        replay = check_sat_certificate(nontrivial, proof)
        self.assertEqual((replay.verdict, replay.reason_code), ("verified", "UNSAT_VERIFIED"))
        self.assertIn("empty clause", replay.diagnostic)

    def test_bogus_and_truncated_drup_never_gain_authority(self) -> None:
        cnf = canonical_cnf_bytes([[1, 2], [1, -2], [-1, 2], [-1, -2]])
        satisfiable = canonical_cnf_bytes([[1, 2]])
        bogus = check_sat_certificate(
            satisfiable, canonical_drup_bytes(satisfiable, [("a", (1,))])
        )
        truncated = check_sat_certificate(cnf, canonical_drup_bytes(cnf, []))
        for result in (bogus, truncated):
            self.assertEqual(result.verdict, "refuted")
            self.assertEqual(result.authority, "none")

    def test_deletion_and_include_deleted_fallback_are_sound(self) -> None:
        cnf = canonical_cnf_bytes([[1], [-1]])
        certificate = canonical_drup_bytes(
            cnf,
            [("d", (1,)), ("a", ())],
        )
        result = check_sat_certificate(cnf, certificate)
        self.assertEqual(result.verdict, "verified")
        self.assertEqual(result.stats.deletions, 1)
        self.assertIn("retained deleted clauses from proof addition 1", result.diagnostic)

    def test_repeated_and_nonexistent_deletions_do_not_mint_a_proof_step(self) -> None:
        cnf = canonical_cnf_bytes([[1, 2]])
        certificate = canonical_drup_bytes(
            cnf,
            [("d", (1, 2)), ("d", (1, 2)), ("d", (-1,)), ("a", (1,))],
        )
        result = check_sat_certificate(cnf, certificate)
        self.assertEqual(result.verdict, "refuted")
        self.assertEqual(result.stats.deletions, 3)
        self.assertEqual(result.authority, "none")

    def test_drat_rat_and_unknown_formats_are_explicitly_unsupported(self) -> None:
        cnf = canonical_cnf_bytes([[1]])
        drat = check_sat_certificate(cnf, _drat(cnf))
        unknown = check_sat_certificate(cnf, b"p something 1 deadbeef\n")
        self.assertEqual((drat.verdict, drat.reason_code, drat.certificate_format),
                         ("unsupported", "FORMAT_UNSUPPORTED", "drat-v1"))
        self.assertEqual((unknown.verdict, unknown.reason_code),
                         ("unsupported", "FORMAT_UNSUPPORTED"))
        self.assertEqual(drat.authority, unknown.authority, "none")

    def test_wrong_formula_identity_is_invalid(self) -> None:
        first = canonical_cnf_bytes([[1]])
        second = canonical_cnf_bytes([[-1]])
        result = check_sat_certificate(second, canonical_drup_bytes(first, []))
        self.assertEqual((result.verdict, result.reason_code), ("invalid", "CERTIFICATE_INVALID"))
        self.assertEqual(result.authority, "none")

    def test_canonical_cnf_rejects_every_grammar_ambiguity(self) -> None:
        valid = canonical_cnf_bytes([[1], [-1, 2]])
        mutations = (
            valid.replace(b"\n", b"\r\n", 1),
            valid[:-1],
            valid.replace(b" 1 ", b" 01 ", 1),
            valid.replace(b"-1 2 0", b"2 -1 0"),
            valid.replace(b"-1 2 0\n1 0", b"1 0\n-1 2 0"),
            valid + b"1 0\n",
            b"p mathhead-cnf 1 1 1\n1  0\n",
            b"p mathhead-cnf 1 1 1\n-1 1 0\n",
            b"p mathhead-cnf 1 1 2\n1 0\n1 0\n",
            b"p mathhead-cnf 1 1 1\nc comment\n",
            b"p mathhead-cnf 1 1 1\n\xff 0\n",
        )
        for mutation in mutations:
            result = check_sat_certificate(mutation, b"p unknown 1 0\n")
            self.assertEqual((result.verdict, result.reason_code), ("invalid", "CNF_INVALID"), mutation)
            self.assertEqual(result.authority, "none")

    def test_certificate_grammar_is_closed_and_trailing_data_is_checked(self) -> None:
        cnf = canonical_cnf_bytes([[1], [-1]])
        digest = hashlib.sha256(cnf).hexdigest()
        mutations = (
            f"p mathhead-drup 1 {digest}\na  0\n",
            f"p mathhead-drup 1 {digest}\na 0",
            f"p mathhead-drup 1 {digest}\na 0\nc ignored\n",
            f"p mathhead-drup 1 {digest}\na -0 0\n",
            f"p mathhead-drup 1 {digest}\na 1 1 0\n",
            f"p mathhead-drup 1 {digest}\na -1 1 0\n",
            f"p mathhead-drup 1 {digest}\nx 0\n",
        )
        for mutation in mutations:
            result = check_sat_certificate(cnf, mutation.encode("ascii"))
            self.assertEqual((result.verdict, result.reason_code),
                             ("invalid", "CERTIFICATE_INVALID"), mutation)

    def test_wrong_input_types_are_total_and_non_authoritative(self) -> None:
        values = (("x", b"y"), (b"x", "y"), (bytearray(b"x"), b"y"), (None, None))
        for cnf, certificate in values:
            result = check_sat_certificate(cnf, certificate)  # type: ignore[arg-type]
            self.assertEqual((result.verdict, result.reason_code),
                             ("invalid", "INPUT_TYPE_INVALID"))
            self.assertEqual(result.authority, "none")

    def test_legacy_normalizers_reject_bool_float_zero_and_oversized_literals(self) -> None:
        invalid = ([True], [1.0], [0], [sat.MAX_VARIABLES + 1])
        for clause in invalid:
            with self.assertRaises(ValueError):
                canonical_cnf_bytes([clause])

    def test_huge_record_and_huge_decimal_exhaust_before_integer_conversion(self) -> None:
        huge_line = b"p mathhead-cnf 1 1 1\n" + b"1" * (sat.MAX_RECORD_BYTES + 1) + b" 0\n"
        huge_decimal = b"p mathhead-cnf 1 99999999 0\n"
        for cnf in (huge_line, huge_decimal):
            result = check_sat_certificate(cnf, b"p unknown 1 0\n")
            self.assertEqual((result.verdict, result.reason_code),
                             ("exhausted", "BUDGET_EXHAUSTED"))
            self.assertEqual(result.authority, "none")

    def test_normalization_is_unique_and_drops_only_cnf_tautologies(self) -> None:
        first = canonical_cnf_bytes([[2, -1, 2], [1, -1, 3], [-2], [2, -1]])
        second = canonical_cnf_bytes([[-1, 2], [-2], [2, -1]])
        self.assertEqual(first, second)
        self.assertEqual(first, b"p mathhead-cnf 1 2 2\n-2 0\n-1 2 0\n")
        with self.assertRaisesRegex(ValueError, "tautological"):
            canonical_drup_bytes(first, [("a", (1, -1))])

    def test_result_round_trip_digest_and_closed_schema(self) -> None:
        cnf = canonical_cnf_bytes([[1], [-1]])
        certificate = canonical_drup_bytes(cnf, [])
        result = check_sat_certificate(cnf, certificate)
        data = sat_replay_result_to_bytes(result)
        self.assertEqual(parse_sat_replay_result(data, cnf, certificate), result)
        envelope = json.loads(data)
        self.assertEqual(envelope["result_sha256"], sat_replay_result_sha256(result))
        self.assertEqual(envelope["result"]["checker"]["contract_sha256"],
                         sat.SAT_REPLAY_CONTRACT_SHA256)

    def test_closed_schema_accepts_every_outcome(self) -> None:
        try:
            from jsonschema import Draft202012Validator
        except ImportError:
            Draft202012Validator = None  # type: ignore[assignment,misc]
        schema = json.loads(
            (ROOT / "docs/contracts/schemas/sat-replay-result-v1.schema.json").read_text(
                encoding="utf-8"
            )
        )
        validator = Draft202012Validator(schema) if Draft202012Validator is not None else None
        cnf = canonical_cnf_bytes([[1, 2]])
        refuted = check_sat_certificate(cnf, canonical_drup_bytes(cnf, [("a", (1,))]))
        invalid = check_sat_certificate(b"not canonical\n", b"not a certificate\n")
        unsupported = check_sat_certificate(cnf, b"p unknown 7 value\n")
        huge_cnf = (
            b"p mathhead-cnf 1 1 1\n" + b"1" * (sat.MAX_RECORD_BYTES + 1) + b" 0\n"
        )
        exhausted = check_sat_certificate(huge_cnf, b"p unknown 7 value\n")
        for result in (refuted, invalid, unsupported, exhausted):
            envelope = json.loads(sat_replay_result_to_bytes(result))
            if validator is not None:
                validator.validate(envelope)
            else:
                self.assertFalse(schema["additionalProperties"])
                self.assertEqual(set(envelope), set(schema["required"]))
                self.assertEqual(set(envelope["result"]), set(schema["properties"]["result"]["required"]))

    def test_result_tampering_duplicate_keys_and_noncanonical_bytes_fail(self) -> None:
        cnf = canonical_cnf_bytes([[1], [-1]])
        certificate = canonical_drup_bytes(cnf, [])
        result = check_sat_certificate(cnf, certificate)
        data = sat_replay_result_to_bytes(result)
        tampered = data.replace(b'"authority":"checker_attestation"', b'"authority":"none"')
        duplicate = data.replace(b'{"result":', b'{"result":null,"result":', 1)
        noncanonical = data.replace(b'"result":{', b'"result": {', 1)
        for candidate in (tampered, duplicate, noncanonical):
            with self.assertRaises(SATReplayValidationError):
                parse_sat_replay_result(candidate, cnf, certificate)

    def test_result_values_are_closed_immutable_and_recomputed(self) -> None:
        for cls in (SATReplayResult, SATReplayStats):
            with self.assertRaises(PermissionError):
                cls()  # type: ignore[call-arg]
            with self.assertRaises(TypeError):
                type(f"Forged{cls.__name__}", (cls,), {})
        cnf = canonical_cnf_bytes([[1], [-1]])
        result = check_sat_certificate(cnf, canonical_drup_bytes(cnf, []))
        with self.assertRaises(PermissionError):
            dataclasses.replace(result, authority="none")
        with self.assertRaises(TypeError):
            pickle.dumps(result)
        self.assertIs(copy.copy(result), result)
        self.assertIs(copy.deepcopy(result), result)
        object.__setattr__(result, "authority", "none")
        with self.assertRaises(SATReplayValidationError):
            validate_sat_replay_result(result)

    def test_budget_exhaustion_is_distinct_from_refutation(self) -> None:
        cnf = canonical_cnf_bytes([[1, 2], [-1, 2]])
        certificate = canonical_sat_assignment_bytes(cnf, [1, 2])
        original = sat.MAX_VISITS
        try:
            sat.MAX_VISITS = 1
            result = check_sat_certificate(cnf, certificate)
        finally:
            sat.MAX_VISITS = original
        self.assertEqual((result.verdict, result.reason_code), ("exhausted", "BUDGET_EXHAUSTED"))
        self.assertEqual(result.authority, "none")

    def test_deterministic_replay_has_exactly_equal_result_and_bytes(self) -> None:
        cnf = canonical_cnf_bytes([[1, 2], [1, -2], [-1, 2], [-1, -2]])
        certificate = canonical_drup_bytes(cnf, [("a", (1,)), ("a", (-1,))])
        first = check_sat_certificate(cnf, certificate)
        second = check_sat_certificate(cnf, certificate)
        self.assertEqual(first, second)
        self.assertEqual(sat_replay_result_to_bytes(first), sat_replay_result_to_bytes(second))

    def test_exhaustive_two_variable_sat_assignments_match_truth_tables(self) -> None:
        clauses = [
            (-2,), (-1,), (1,), (2,),
            (-1, -2), (-1, 2), (1, -2), (1, 2),
        ]
        for width in range(4):
            for chosen in combinations(clauses, width):
                cnf = canonical_cnf_bytes(chosen)
                variables = max((abs(literal) for clause in chosen for literal in clause), default=0)
                assignments = tuple(product((False, True), repeat=variables))
                for values in assignments:
                    signed = [index if value else -index for index, value in enumerate(values, 1)]
                    result = check_sat_certificate(cnf, canonical_sat_assignment_bytes(cnf, signed))
                    expected = all(
                        any(values[abs(literal) - 1] == (literal > 0) for literal in clause)
                        for clause in chosen
                    )
                    self.assertEqual(result.ok, expected, (chosen, values, result))

    def test_legacy_entry_points_are_only_translators_to_the_same_result(self) -> None:
        from mathhead.drat import check_unsat_proof

        name = "_mathhead_rup_adapter_test"
        spec = importlib.util.spec_from_file_location(
            name, ROOT / "src/mathhead/discovery/rup_check.py"
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader if spec is not None else None)
        module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
        sys.modules[name] = module
        try:
            spec.loader.exec_module(module)  # type: ignore[union-attr]
        finally:
            sys.modules.pop(name, None)
        check_drup_proof = module.check_drup_proof

        clauses = [[1, 2], [1, -2], [-1, 2], [-1, -2]]
        proof = [[1], [-1], []]
        cnf = canonical_cnf_bytes(clauses)
        core = check_sat_certificate(
            cnf, canonical_drup_bytes(cnf, [("a", clause) for clause in proof])
        )
        first = check_unsat_proof(clauses, proof)
        second = check_drup_proof(clauses, [("a", tuple(clause)) for clause in proof])
        self.assertTrue(core.ok)
        self.assertEqual((first.status, first.verified), ("verified", True))
        self.assertTrue(second.ok)
        fallback = check_drup_proof([[1], [-1]], [("d", (1,)), ("a", ())])
        self.assertEqual(fallback.deletions_ignored_from, 1)


if __name__ == "__main__":
    unittest.main()
