from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_PATH = (
    REPO_ROOT
    / "bot_psychologist/tests/fixtures/admin_operational_surface_inventory_v1041_phase0.json"
)


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8-sig"))


def test_prompt_runtime_usage_metadata_gap_fixture_shape() -> None:
    payload = _load_fixture()
    api = payload.get("api_operational_gaps", {})
    assert isinstance(api.get("missing_endpoints"), list)
    assert isinstance(api.get("missing_prompt_usage_fields"), list)
    assert api["missing_endpoints"], "missing_endpoints must not be empty"
    assert api["missing_prompt_usage_fields"], "missing_prompt_usage_fields must not be empty"


def test_prompt_runtime_usage_metadata_gap_has_known_targets() -> None:
    payload = _load_fixture()
    missing_endpoints = set(payload["api_operational_gaps"]["missing_endpoints"])
    missing_fields = set(payload["api_operational_gaps"]["missing_prompt_usage_fields"])
    assert "/prompts/stack-v2/usage" in missing_endpoints
    assert "read_only_reason" in missing_fields
    assert "derived_from" in missing_fields


def test_prompt_runtime_usage_baseline_file_exists() -> None:
    payload = _load_fixture()
    path = REPO_ROOT / payload["api_operational_gaps"]["file"]
    assert path.exists(), f"Missing admin API file in inventory: {path}"
