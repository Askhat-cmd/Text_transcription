from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
ADMIN_PANEL_PATH = REPO_ROOT / "bot_psychologist/web_ui/src/components/admin/AdminPanel.tsx"


def _read_admin_panel() -> str:
    return ADMIN_PANEL_PATH.read_text(encoding="utf-8", errors="ignore")


def test_diagnostics_tab_policy_surface_has_no_last_snapshot() -> None:
    text = _read_admin_panel()
    assert "Current Behavior Policies" in text
    assert "Last Diagnostics Snapshot" not in text
    assert "informational_mode_hint" not in text
    assert "mixed_query_snapshot" not in text
