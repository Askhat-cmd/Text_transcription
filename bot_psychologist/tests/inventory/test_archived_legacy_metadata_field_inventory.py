from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_PATH = REPO_ROOT / "bot_psychologist/tests/fixtures/runtime_legacy_touchpoints_v102.json"


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8-sig"))


def test_archived_legacy_metadata_fields_fixture_is_documented() -> None:
    payload = _load_fixture()
    assert payload.get("status") == "archived"
    assert payload.get("do_not_use_as_runtime_contract") is True
    assert payload.get("superseded_by") == "multiagent_runtime_invariants_v1"


def test_archived_legacy_metadata_fields_are_preserved_as_audit_artifact() -> None:
    payload = _load_fixture()
    fields = payload.get("legacy_metadata_fields", [])
    assert isinstance(fields, list) and fields
    assert all(isinstance(field, str) and field for field in fields)
