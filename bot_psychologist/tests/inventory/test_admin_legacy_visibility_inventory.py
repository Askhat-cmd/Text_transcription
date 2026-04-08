from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_PATH = REPO_ROOT / "bot_psychologist/tests/fixtures/admin_surface_inventory_v104_phase0.json"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_legacy_controls_inventory_shape() -> None:
    payload = _load_fixture()
    legacy_controls = payload.get("ui_surface", {}).get("legacy_primary_controls", [])
    assert isinstance(legacy_controls, list)
    assert legacy_controls, "legacy_primary_controls must not be empty for phase-0 baseline"


def test_legacy_controls_are_still_visible_in_phase0_baseline() -> None:
    """Phase0 inventory is historical; verify references stay resolvable."""
    payload = _load_fixture()
    for item in payload["ui_surface"]["legacy_primary_controls"]:
        file_path = REPO_ROOT / item["file"]
        assert file_path.exists(), f"Missing file: {item['file']}"
        markers = item.get("markers", [])
        assert isinstance(markers, list)
        assert markers, f"Inventory item must keep non-empty markers list: {item['name']}"


def test_phase0_has_deprecated_or_misleading_legacy_classifications() -> None:
    payload = _load_fixture()
    classes = {item["classification"] for item in payload["ui_surface"]["legacy_primary_controls"]}
    assert "misleading" in classes or "deprecated_visible" in classes
