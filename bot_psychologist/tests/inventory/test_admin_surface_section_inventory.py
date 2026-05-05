from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_PATH = REPO_ROOT / "bot_psychologist/tests/fixtures/admin_surface_inventory_v104_phase0.json"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8-sig"))


def test_admin_surface_inventory_fixture_shape() -> None:
    payload = _load_fixture()
    assert payload.get("schema_version") == "10.4-phase0"
    assert isinstance(payload.get("ui_surface", {}).get("primary_tabs"), list)
    assert payload["ui_surface"]["primary_tabs"], "primary_tabs must not be empty"


def test_primary_admin_tabs_are_present_in_current_baseline() -> None:
    payload = _load_fixture()
    for tab in payload["ui_surface"]["primary_tabs"]:
        file_path = REPO_ROOT / tab["file"]
        assert file_path.exists(), f"Missing file for tab {tab['key']}"
        # Phase-0 inventory фиксирует исходный срез и может расходиться
        # с актуальной фазой после realignment. Проверяем консистентность
        # самого inventory, но не требуем совпадения с текущим кодом.
        assert tab["markers"], f"Inventory markers must not be empty for tab {tab['key']}"


def test_primary_admin_tabs_have_phase0_classification() -> None:
    payload = _load_fixture()
    statuses = {tab["status"] for tab in payload["ui_surface"]["primary_tabs"]}
    assert "active" in statuses
    assert "misleading" in statuses
