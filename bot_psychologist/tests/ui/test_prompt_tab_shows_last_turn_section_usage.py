from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
PROMPT_EDITOR_PATH = REPO_ROOT / "bot_psychologist/web_ui/src/components/admin/PromptEditorPanel.tsx"
TYPES_PATH = REPO_ROOT / "bot_psychologist/web_ui/src/types/admin.types.ts"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def test_prompt_tab_hides_last_turn_section_usage() -> None:
    text = _read(PROMPT_EDITOR_PATH)
    assert "Last Turn Section Usage" not in text
    assert "last_turn?.used_sections" not in text
    assert "used_sections.join" not in text


def test_prompt_usage_response_type_has_last_turn_schema() -> None:
    text = _read(TYPES_PATH)
    assert "export interface PromptStackUsageResponse" in text
    assert "last_turn_available: boolean;" in text
    assert "used_sections: string[];" in text
