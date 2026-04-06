from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
ADMIN_PANEL_PATH = REPO_ROOT / "bot_psychologist/web_ui/src/components/admin/AdminPanel.tsx"


def _read_admin_panel() -> str:
    return ADMIN_PANEL_PATH.read_text(encoding="utf-8", errors="ignore")


def test_diagnostics_tab_present_in_primary_ia() -> None:
    text = _read_admin_panel()
    assert "key: 'diagnostics'" in text
    assert "Diagnostics v1" in text


def test_trace_tab_removed_from_primary_ia() -> None:
    text = _read_admin_panel()
    assert "key: 'trace'" not in text
    assert "Trace / Debug" not in text
