from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

try:
    from jsonschema import Draft202012Validator
except ModuleNotFoundError:  # Dependency-minimal governed status profile.
    Draft202012Validator = None  # type: ignore[assignment,misc]


ROOT = Path(__file__).resolve().parents[2]

ARTIFACTS = {
    "docs/contracts/schemas/proof-obligation-v1.schema.json": "55ff62bac3515763773645577c0ba163adbdda726a277a98945002ea82103db4",
    "docs/contracts/schemas/proof-obligation-local-context-v1.schema.json": "7ace8271f6ab2839b109208fd0b9686f9a6d3ac1c75c7df60e6febb37a7bd3e5",
    "docs/contracts/schemas/proof-obligation-graph-v1.schema.json": "7244ad195f7a55732babda563b7b6d7d7b9b56f37d41874fe137f8b2e1349da3",
    "docs/contracts/schemas/proof-obligation-rules-v1.schema.json": "4e9dd834724e85b630b57a1fc9b2d92919e85952d202ec0713a812afacc3f739",
    "docs/contracts/schemas/proof-strategy-catalogue-v1.schema.json": "77a9f1de86d6bedc10c2b181c614dee987bea36937ce696be4aa232694d2333e",
    "docs/contracts/schemas/proof-obligation-result-v1.schema.json": "449f6bb90edf609532410f6df133cb92e7cae925f0b57d1c527b7e5d453cb9ce",
    "docs/obligations/proof-obligation-rules-v1.json": "d59c480c6ee19471051632407deb611d8df6be4987cf23154d56aa4d3326a524",
    "docs/obligations/proof-strategy-catalogue-v1.json": "28b815267fb5a2637d4a673218d1720c9ddcab0ea3f6bf3a8f6d05a3125fa1c8",
}


class ProofObligationArtifactTests(unittest.TestCase):
    def test_frozen_schema_and_catalogue_bytes_are_exact(self) -> None:
        for relative, expected in ARTIFACTS.items():
            payload = (ROOT / relative).read_bytes()
            self.assertEqual(hashlib.sha256(payload).hexdigest(), expected, relative)
            self.assertEqual(json.loads(payload), json.loads(payload.decode("utf-8")))

    def test_catalogues_match_their_closed_schemas(self) -> None:
        pairs = (
            (
                "docs/contracts/schemas/proof-obligation-rules-v1.schema.json",
                "docs/obligations/proof-obligation-rules-v1.json",
            ),
            (
                "docs/contracts/schemas/proof-strategy-catalogue-v1.schema.json",
                "docs/obligations/proof-strategy-catalogue-v1.json",
            ),
        )
        for schema_path, value_path in pairs:
            schema = json.loads((ROOT / schema_path).read_bytes())
            value = json.loads((ROOT / value_path).read_bytes())
            self.assertEqual(
                schema["$schema"],
                "https://json-schema.org/draft/2020-12/schema",
            )
            self.assertEqual(schema["type"], "object")
            self.assertIs(schema["additionalProperties"], False)
            self.assertEqual(value["schema"], schema["properties"]["schema"]["const"])
            if Draft202012Validator is not None:
                Draft202012Validator.check_schema(schema)
                Draft202012Validator(schema).validate(value)

    def test_rule_and_strategy_identities_are_unique_and_non_authoritative(self) -> None:
        rules = json.loads(
            (ROOT / "docs/obligations/proof-obligation-rules-v1.json").read_bytes()
        )
        strategies = json.loads(
            (ROOT / "docs/obligations/proof-strategy-catalogue-v1.json").read_bytes()
        )
        rule_ids = [item["rule_id"] for item in rules["rules"]]
        strategy_ids = [item["strategy_id"] for item in strategies["strategies"]]
        match_ids = [item["match_rule_id"] for item in strategies["strategies"]]
        self.assertEqual(len(rule_ids), len(set(rule_ids)))
        self.assertEqual(len(strategy_ids), len(set(strategy_ids)))
        self.assertEqual(len(match_ids), len(set(match_ids)))
        self.assertIs(rules["mathematical_authority"], False)
        self.assertIs(strategies["mathematical_authority"], False)
        self.assertIs(strategies["guarantees_success"], False)


if __name__ == "__main__":
    unittest.main()
