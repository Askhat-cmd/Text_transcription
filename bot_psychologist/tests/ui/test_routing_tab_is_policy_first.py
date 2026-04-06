from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
ADMIN_PANEL_PATH = REPO_ROOT / "bot_psychologist/web_ui/src/components/admin/AdminPanel.tsx"


def _read_admin_panel() -> str:
    return ADMIN_PANEL_PATH.read_text(encoding="utf-8", errors="ignore")


def test_routing_tab_is_policy_first() -> None:
    text = _read_admin_panel()
    assert "Current Routing Policy" in text
    assert "False-Inform Protection" in text
    assert "Curiosity Decoupling" in text
    assert "Practice Trigger Rules" in text
    assert "Safety Override Priority" in text

