from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
ADMIN_PANEL_PATH = REPO_ROOT / "bot_psychologist/web_ui/src/components/admin/AdminPanel.tsx"


def _read_admin_panel() -> str:
    return ADMIN_PANEL_PATH.read_text(encoding="utf-8", errors="ignore")


def test_runtime_surface_has_no_turn_trace_payload_rendering() -> None:
    text = _read_admin_panel()
    assert "tracePayload.diagnostics ?? {}" not in text
    assert "tracePayload.retrieval ?? {}" not in text
    assert "tracePayload.validation ?? {}" not in text
    assert "tracePayload.memory ?? {}" not in text
