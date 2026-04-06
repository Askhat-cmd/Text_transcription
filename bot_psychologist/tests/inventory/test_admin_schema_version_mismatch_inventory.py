from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_PATH = REPO_ROOT / "bot_psychologist/tests/fixtures/admin_backend_boundary_v1051_phase0.json"


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8-sig"))


def test_admin_schema_version_mismatch_inventory_shape() -> None:
    payload = _load_fixture()
    inventory = payload.get("residual_boundary_inventory", {})
    markers = inventory.get("schema_markers_before_alignment", {})
    assert isinstance(markers, dict)
    assert "admin_schema_version" in markers
    assert "admin_effective_schema_version" in markers


def test_admin_schema_version_mismatch_inventory_values() -> None:
    markers = _load_fixture()["residual_boundary_inventory"]["schema_markers_before_alignment"]
    assert markers["admin_schema_version"] == "10.4"
    assert markers["admin_effective_schema_version"] == "10.4.1"
