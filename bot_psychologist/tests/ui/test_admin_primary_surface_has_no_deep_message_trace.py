from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
ADMIN_PANEL_PATH = REPO_ROOT / "bot_psychologist/web_ui/src/components/admin/AdminPanel.tsx"
PROMPT_EDITOR_PATH = REPO_ROOT / "bot_psychologist/web_ui/src/components/admin/PromptEditorPanel.tsx"


def test_admin_primary_surface_has_no_deep_message_trace() -> None:
    panel = ADMIN_PANEL_PATH.read_text(encoding="utf-8", errors="ignore")
    prompt = PROMPT_EDITOR_PATH.read_text(encoding="utf-8", errors="ignore")

    assert "Recent traces list" not in panel
    assert "Turn header" not in panel
    assert "Diagnostics snapshot" not in panel
    assert "Last Turn Section Usage" not in prompt
    assert "Effective Assembly Preview" not in prompt
