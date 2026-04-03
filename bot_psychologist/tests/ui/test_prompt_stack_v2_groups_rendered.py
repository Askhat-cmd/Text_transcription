from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SERVICE_PATH = REPO_ROOT / "bot_psychologist/web_ui/src/services/adminConfig.service.ts"
EDITOR_PATH = REPO_ROOT / "bot_psychologist/web_ui/src/components/admin/PromptEditorPanel.tsx"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def test_prompt_ui_uses_stack_v2_api_surface() -> None:
    text = _read(SERVICE_PATH)
    assert "/prompts/stack-v2" in text
    assert "/prompts/stack-v2/${name}" in text
    assert "/prompts/stack-v2/${name}/reset" in text


def test_prompt_editor_supports_runtime_sections_and_readonly_badge() -> None:
    text = _read(EDITOR_PATH)
    assert "read-only runtime section" in text
    assert "RO" in text
