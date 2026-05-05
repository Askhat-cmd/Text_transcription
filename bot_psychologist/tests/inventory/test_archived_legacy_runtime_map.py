from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_PATH = REPO_ROOT / "bot_psychologist/tests/fixtures/legacy_runtime_map.json"


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8-sig"))


def test_archived_legacy_runtime_map_fixture_metadata() -> None:
    payload = _load_fixture()
    assert payload.get("schema_version") == "1.0"
    assert payload.get("status") == "archived"
    assert payload.get("archived_after_prd") == "PRD-036"
    assert payload.get("superseded_by") == "multiagent_runtime_invariants_v1"
    assert payload.get("do_not_use_as_runtime_contract") is True


def test_archived_legacy_runtime_map_fixture_shape() -> None:
    payload = _load_fixture()
    entrypoints = payload.get("entrypoints")
    dependencies = payload.get("legacy_runtime_dependencies")

    assert isinstance(entrypoints, list) and entrypoints
    assert isinstance(dependencies, dict) and dependencies

    for entrypoint in entrypoints:
        assert isinstance(entrypoint.get("name"), str) and entrypoint["name"]
        assert isinstance(entrypoint.get("file"), str) and entrypoint["file"]
        assert isinstance(entrypoint.get("symbol"), str) and entrypoint["symbol"]

    for dep_name, files in dependencies.items():
        assert isinstance(dep_name, str) and dep_name
        assert isinstance(files, list) and files
        assert all(isinstance(path, str) and path for path in files)
