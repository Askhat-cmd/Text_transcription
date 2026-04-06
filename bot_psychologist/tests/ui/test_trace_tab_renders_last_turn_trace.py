from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
ADMIN_PANEL_PATH = REPO_ROOT / "bot_psychologist/web_ui/src/components/admin/AdminPanel.tsx"


def _read_admin_panel() -> str:
    return ADMIN_PANEL_PATH.read_text(encoding="utf-8", errors="ignore")


def test_trace_tab_renders_last_turn_trace_blocks() -> None:
    text = _read_admin_panel()
    assert "Turn header" in text
    assert "Diagnostics snapshot" in text
    assert "Routing decision" in text
    assert "Retrieval pipeline" in text
    assert "Prompt stack summary" in text
    assert "Output validation" in text
    assert "Memory / summary update" in text
    assert "Flags / degraded / anomalies" in text

