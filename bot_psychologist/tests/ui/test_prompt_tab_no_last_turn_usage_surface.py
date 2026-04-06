from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
PROMPT_EDITOR_PATH = REPO_ROOT / "bot_psychologist/web_ui/src/components/admin/PromptEditorPanel.tsx"


def test_prompt_tab_no_last_turn_usage_surface() -> None:
    text = PROMPT_EDITOR_PATH.read_text(encoding="utf-8", errors="ignore")
    assert "Section Metadata" in text
    assert "Last Turn Section Usage" not in text
    assert "used in last turn" not in text
