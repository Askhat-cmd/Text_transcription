from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
ADMIN_PANEL_PATH = REPO_ROOT / "bot_psychologist/web_ui/src/components/admin/AdminPanel.tsx"


def _read_admin_panel() -> str:
    return ADMIN_PANEL_PATH.read_text(encoding="utf-8", errors="ignore")


def test_trace_tab_renders_recent_traces_list() -> None:
    text = _read_admin_panel()
    assert "Recent traces list" in text
    assert "No recent traces available." in text

