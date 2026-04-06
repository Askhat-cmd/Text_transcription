from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
ADMIN_PANEL_PATH = REPO_ROOT / "bot_psychologist/web_ui/src/components/admin/AdminPanel.tsx"


def _read_admin_panel() -> str:
    return ADMIN_PANEL_PATH.read_text(encoding="utf-8", errors="ignore")


def test_runtime_tab_keeps_effective_truth_without_trace_forensics() -> None:
    text = _read_admin_panel()
    assert "Schema / Versions" in text
    assert "Grouped Feature Flags" in text
    assert "Raw Feature Flags" in text
    assert "Turn header" not in text
    assert "Recent traces list" not in text
