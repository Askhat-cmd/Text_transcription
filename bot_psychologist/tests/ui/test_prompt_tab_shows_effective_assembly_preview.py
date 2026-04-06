from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
PROMPT_EDITOR_PATH = REPO_ROOT / "bot_psychologist/web_ui/src/components/admin/PromptEditorPanel.tsx"
ADMIN_PANEL_PATH = REPO_ROOT / "bot_psychologist/web_ui/src/components/admin/AdminPanel.tsx"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def test_prompt_tab_shows_effective_assembly_preview() -> None:
    text = _read(PROMPT_EDITOR_PATH)
    assert "Effective Assembly Preview" in text
    assert "Section Metadata" in text
    assert "used in last turn" in text


def test_prompt_tab_passes_prompt_usage_payload_to_editor() -> None:
    text = _read(ADMIN_PANEL_PATH)
    assert "promptUsageData" in text
    assert "loadPromptUsage" in text
    assert "promptUsage={promptUsageData}" in text
