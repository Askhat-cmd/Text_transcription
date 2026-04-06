from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
ADMIN_PANEL_PATH = REPO_ROOT / "bot_psychologist/web_ui/src/components/admin/AdminPanel.tsx"
ADMIN_ROUTES_PATH = REPO_ROOT / "bot_psychologist/api/admin_routes.py"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def test_diagnostics_tab_policy_only_no_last_snapshot() -> None:
    text = _read(ADMIN_PANEL_PATH)
    assert "Current Behavior Policies" in text
    assert "Last Diagnostics Snapshot" not in text


def test_diagnostics_effective_payload_uses_system_level_contract() -> None:
    text = _read(ADMIN_ROUTES_PATH)
    assert '"contract_version": "diagnostics-v1"' in text
    assert '"interaction_mode_policy": "system-level"' in text
    assert '"last_snapshot": {}' in text
