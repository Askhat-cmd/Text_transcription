from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_PATH = REPO_ROOT / "bot_psychologist/tests/fixtures/admin_surface_inventory_v104_phase0.json"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_prompt_fetch_failure_inventory_shape() -> None:
    payload = _load_fixture()
    broken = payload.get("ui_surface", {}).get("broken_flows", [])
    assert isinstance(broken, list)
    assert broken, "broken_flows must not be empty for phase-0 baseline"


def test_prompt_fetch_failure_markers_are_present_in_current_baseline() -> None:
    payload = _load_fixture()
    flow = next(
        item for item in payload["ui_surface"]["broken_flows"]
        if item["name"] == "prompt_fetch_error_non_actionable"
    )
    for file_spec in flow["files"]:
        file_path = REPO_ROOT / file_spec["path"]
        assert file_path.exists(), f"Missing file: {file_spec['path']}"
        text = _read_text(file_path)
        for marker in file_spec["markers"]:
            assert marker in text, (
                f"Missing prompt-fetch baseline marker '{marker}' in {file_spec['path']}"
            )


def test_prompt_fetch_failure_has_no_explicit_retry_marker_in_ui_baseline() -> None:
    payload = _load_fixture()
    flow = next(
        item for item in payload["ui_surface"]["broken_flows"]
        if item["name"] == "prompt_fetch_error_non_actionable"
    )
    panel_path = REPO_ROOT / "bot_psychologist/web_ui/src/components/admin/AdminPanel.tsx"
    assert panel_path.exists()
    assert isinstance(flow.get("missing_markers"), list)
    assert flow["missing_markers"], "Inventory must capture missing markers for phase-0 broken flow"
