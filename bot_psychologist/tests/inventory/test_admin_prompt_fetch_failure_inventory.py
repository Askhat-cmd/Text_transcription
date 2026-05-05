from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_PATH = REPO_ROOT / "bot_psychologist/tests/fixtures/admin_surface_inventory_v104_phase0.json"


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8-sig"))


def test_admin_prompt_fetch_inventory_is_archived_fixture() -> None:
    payload = _load_fixture()
    assert payload.get("schema_version") == "10.4-phase0"
    assert payload.get("status") == "archived"
    assert payload.get("archived_after_prd") == "PRD-037"
    assert payload.get("superseded_by") == "admin_runtime_contract_tests"
    assert payload.get("do_not_use_as_current_failure_contract") is True


def test_admin_prompt_fetch_broken_flow_record_is_preserved_as_archive() -> None:
    payload = _load_fixture()
    broken = payload.get("ui_surface", {}).get("broken_flows", [])
    assert isinstance(broken, list) and broken

    flow = next((item for item in broken if item.get("name") == "prompt_fetch_error_non_actionable"), None)
    assert flow is not None, "Archived phase0 artifact must keep prompt_fetch_error_non_actionable entry"

    files = flow.get("files")
    missing_markers = flow.get("missing_markers")
    assert isinstance(files, list) and files
    assert isinstance(missing_markers, list) and missing_markers
