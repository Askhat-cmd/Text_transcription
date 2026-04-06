from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_PATH = REPO_ROOT / "bot_psychologist/tests/fixtures/admin_boundary_inventory_v105_phase0.json"


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8-sig"))


def test_admin_boundary_inventory_fixture_shape_v105() -> None:
    payload = _load_fixture()
    assert payload.get("schema_version") == "10.5-phase0"
    boundary = payload.get("boundary_inventory", {})
    assert isinstance(boundary.get("sections"), list)
    assert boundary["sections"], "boundary sections must not be empty"


def test_admin_boundary_inventory_has_management_and_debug_sets() -> None:
    payload = _load_fixture()["boundary_inventory"]
    management = payload.get("admin_management_surfaces", [])
    debug = payload.get("message_level_debug_surfaces", [])

    assert isinstance(management, list) and management
    assert isinstance(debug, list) and debug
    assert "runtime" in management
    assert "trace_debug_tab" in debug


def test_admin_boundary_inventory_files_exist() -> None:
    payload = _load_fixture()["boundary_inventory"]
    for section in payload.get("sections", []):
      path = REPO_ROOT / section["file"]
      assert path.exists(), f"Missing inventory file: {section['file']}"
