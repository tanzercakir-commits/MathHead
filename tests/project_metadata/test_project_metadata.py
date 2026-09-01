"""Contract tests for generated project facts and published-example ownership."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
EXPECTED_SHA256 = "701a5f99a41f3f2226859fac98c5a8050915d88fb83111a53e5172a2b2760aad"


def _load_tool(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_accepted_contract_is_exact_reviewed_proposal():
    accepted = ROOT / "docs/contracts/MH-C-PROJECT-FACTS-001.json"
    proposed = ROOT / "docs/contracts/proposed/MH-C-PROJECT-FACTS-001.json"
    assert hashlib.sha256(accepted.read_bytes()).hexdigest() == EXPECTED_SHA256
    assert accepted.read_bytes() == proposed.read_bytes()


def test_current_manifest_and_source_directives_validate():
    validator = _load_tool("validate_project_metadata_current", "tools/validate_project_metadata.py")
    validator.validate_examples()


def test_unknown_manifest_field_fails_closed(tmp_path):
    validator = _load_tool("validate_project_metadata_unknown", "tools/validate_project_metadata.py")
    original = (ROOT / "docs/examples.toml").read_text(encoding="utf-8")
    path = tmp_path / "examples.toml"
    path.write_text(original.replace("schema = 1", "schema = 1\nunknown = true", 1), encoding="utf-8")
    with pytest.raises(validator.ProjectMetadataError, match="top-level fields"):
        validator.validate_examples(manifest_path=path)


def test_unclassified_source_fence_fails_closed(tmp_path):
    validator = _load_tool("validate_project_metadata_fence", "tools/validate_project_metadata.py")
    (tmp_path / "docs").mkdir()
    (tmp_path / "tools").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "README.md").write_text("# Bad\n\n```python\nprint('x')\n```\n", encoding="utf-8")
    (tmp_path / "tools/dev_profiles.json").write_text(
        json.dumps({"profiles": {"docs": {}}}), encoding="utf-8"
    )
    (tmp_path / "docs/examples.toml").write_text(
        "schema = 1\n"
        'contract_id = "MH-C-PROJECT-FACTS-001"\n'
        'sources = ["README.md"]\n'
        "[[examples]]\n"
        'id = "bad"\nsource = "README.md"\nlanguage = "python"\n'
        'mode = "executable"\nprofile = "docs"\nvalidators = ["tests/test_bad.py::test_bad"]\n',
        encoding="utf-8",
    )
    (tmp_path / "tests/test_bad.py").write_text("def test_bad():\n    pass\n", encoding="utf-8")
    with pytest.raises(validator.ProjectMetadataError, match="unclassified fence"):
        validator.validate_examples(root=tmp_path)


def test_generated_artifacts_are_canonical_and_current():
    facts_tool = _load_tool("project_facts_contract", "tools/project_facts.py")
    facts = json.loads((ROOT / "docs/project-facts.json").read_text(encoding="utf-8"))
    assert (ROOT / "docs/project-facts.json").read_text(encoding="utf-8") == \
        facts_tool._json_text(facts)
    assert facts["contract"] == {
        "id": facts_tool.CONTRACT_ID,
        "sha256": facts_tool.CONTRACT_SHA256,
    }
    assert facts["package"]["version"] == __import__("mathhead").__version__


def test_update_surface_is_limited_to_declared_outputs():
    facts_tool = _load_tool("project_facts_outputs", "tools/project_facts.py")
    assert {facts_tool.FACTS_PATH, facts_tool.README_PATH} == {
        Path("docs/project-facts.json"),
        Path("README.md"),
    }
    source = (ROOT / "tools/project_facts.py").read_text(encoding="utf-8")
    assert "docs/PLAN.md" not in source
    assert "docs/TODO.md" not in source
    assert "docs/PROGRESS.md" not in source


def test_timeout_has_a_distinct_nonzero_exit(monkeypatch, capsys):
    facts_tool = _load_tool("project_facts_timeout", "tools/project_facts.py")

    def timed_out():
        raise facts_tool.ProjectFactsTimeout("test-budget")

    monkeypatch.setattr(facts_tool, "build_facts", timed_out)
    assert facts_tool.main(["--check"]) == 4
    assert "TIMED_OUT: test-budget" in capsys.readouterr().err
