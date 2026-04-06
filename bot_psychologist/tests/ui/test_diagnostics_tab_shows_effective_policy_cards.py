from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
ADMIN_PANEL_PATH = REPO_ROOT / "bot_psychologist/web_ui/src/components/admin/AdminPanel.tsx"


def _read_admin_panel() -> str:
    return ADMIN_PANEL_PATH.read_text(encoding="utf-8", errors="ignore")


def test_diagnostics_tab_shows_effective_policy_cards() -> None:
    text = _read_admin_panel()
    assert "Active Diagnostics Contract" in text
    assert "Current Behavior Policies" in text
    assert "Inform/Mixed/User Correction" in text

