from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
PROMPT_EDITOR_PATH = REPO_ROOT / "bot_psychologist/web_ui/src/components/admin/PromptEditorPanel.tsx"
ADMIN_PANEL_PATH = REPO_ROOT / "bot_psychologist/web_ui/src/components/admin/AdminPanel.tsx"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def test_prompt_tab_keeps_section_metadata_and_no_turn_usage_surface() -> None:
    text = _read(PROMPT_EDITOR_PATH)
    assert "Section Metadata" in text
    assert "Effective Assembly Preview" not in text
    assert "used in last turn" not in text


def test_prompt_tab_does_not_depend_on_prompt_usage_payload() -> None:
    text = _read(ADMIN_PANEL_PATH)
    assert "promptUsageData" not in text
    assert "loadPromptUsage" not in text
    assert "promptUsage={promptUsageData}" not in text
