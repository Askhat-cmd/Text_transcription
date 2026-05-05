from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_PATH = REPO_ROOT / "bot_psychologist/tests/fixtures/runtime_legacy_touchpoints_v102.json"


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8-sig"))


def test_archived_runtime_legacy_touchpoints_fixture_metadata() -> None:
    payload = _load_fixture()
    assert payload.get("schema_version") == "10.2-phase0"
    assert payload.get("status") == "archived"
    assert payload.get("archived_after_prd") == "PRD-037"
    assert payload.get("superseded_by") == "multiagent_runtime_invariants_v1"
    assert payload.get("do_not_use_as_runtime_contract") is True


def test_archived_runtime_legacy_touchpoints_fixture_shape() -> None:
    payload = _load_fixture()

    entrypoints = payload.get("entrypoints")
    touchpoints = payload.get("legacy_touchpoints")
    metadata_fields = payload.get("legacy_metadata_fields")

    assert isinstance(entrypoints, list) and entrypoints
    for entrypoint in entrypoints:
        assert isinstance(entrypoint.get("name"), str) and entrypoint["name"]
        assert isinstance(entrypoint.get("file"), str) and entrypoint["file"]
        assert isinstance(entrypoint.get("symbol"), str) and entrypoint["symbol"]

    assert isinstance(touchpoints, dict) and touchpoints
    for touchpoint_name, spec in touchpoints.items():
        assert isinstance(touchpoint_name, str) and touchpoint_name
        assert isinstance(spec, dict)
        assert isinstance(spec.get("file"), str) and spec["file"]
        patterns = spec.get("patterns")
        assert isinstance(patterns, list) and patterns

    assert isinstance(metadata_fields, list) and metadata_fields
