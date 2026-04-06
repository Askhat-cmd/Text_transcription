from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
ADMIN_PANEL_PATH = REPO_ROOT / "bot_psychologist/web_ui/src/components/admin/AdminPanel.tsx"


def test_admin_tabs_focus_on_management_surfaces() -> None:
    text = ADMIN_PANEL_PATH.read_text(encoding="utf-8", errors="ignore")
    for tab_key in ("llm", "retrieval", "diagnostics", "routing", "memory", "prompts", "runtime"):
        assert f"key: '{tab_key}'" in text
    assert "key: 'trace'" not in text
