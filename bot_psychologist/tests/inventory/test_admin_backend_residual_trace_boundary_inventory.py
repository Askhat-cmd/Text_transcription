from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_PATH = REPO_ROOT / "bot_psychologist/tests/fixtures/admin_backend_boundary_v1051_phase0.json"


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8-sig"))


def test_admin_backend_residual_trace_boundary_inventory_shape() -> None:
    payload = _load_fixture()
    assert payload.get("schema_version") == "10.5.1-phase0"
    inventory = payload.get("residual_boundary_inventory", {})
    assert isinstance(inventory.get("trace_related_admin_endpoints"), list)
    assert isinstance(inventory.get("trace_related_backend_builders"), list)
    assert inventory.get("trace_related_admin_endpoints"), "trace endpoint inventory must not be empty"
    assert inventory.get("trace_related_backend_builders"), "trace builder inventory must not be empty"


def test_admin_backend_residual_trace_boundary_contains_expected_markers() -> None:
    inventory = _load_fixture()["residual_boundary_inventory"]
    assert "/api/admin/trace/last" in inventory["trace_related_admin_endpoints"]
    assert "/api/admin/trace/recent" in inventory["trace_related_admin_endpoints"]
    assert "_build_trace_turn_payload" in inventory["trace_related_backend_builders"]
