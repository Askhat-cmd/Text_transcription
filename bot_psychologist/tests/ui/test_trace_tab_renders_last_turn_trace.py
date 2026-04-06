from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
ADMIN_PANEL_PATH = REPO_ROOT / "bot_psychologist/web_ui/src/components/admin/AdminPanel.tsx"


def _read_admin_panel() -> str:
    return ADMIN_PANEL_PATH.read_text(encoding="utf-8", errors="ignore")


def test_admin_surface_no_longer_renders_trace_forensics_blocks() -> None:
    text = _read_admin_panel()
    assert "Turn header" not in text
    assert "Diagnostics snapshot" not in text
    assert "Routing decision" not in text
    assert "Retrieval pipeline" not in text
    assert "Prompt stack summary" not in text
    assert "Output validation" not in text
    assert "Memory / summary update" not in text
    assert "Flags / degraded / anomalies" not in text
