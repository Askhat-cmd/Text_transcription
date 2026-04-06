from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
ADMIN_PANEL_PATH = REPO_ROOT / "bot_psychologist/web_ui/src/components/admin/AdminPanel.tsx"


def test_compatibility_hidden_under_advanced_controls() -> None:
    text = ADMIN_PANEL_PATH.read_text(encoding="utf-8", errors="ignore")
    assert "<details className=\"relative\">" in text
    assert "Advanced" in text
    assert "Show Compatibility tab" in text
