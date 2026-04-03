from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
EDITOR_PATH = REPO_ROOT / "bot_psychologist/web_ui/src/components/admin/PromptEditorPanel.tsx"
TYPES_PATH = REPO_ROOT / "bot_psychologist/web_ui/src/types/admin.types.ts"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def test_prompt_editor_has_preview_and_diff_controls() -> None:
    text = _read(EDITOR_PATH)
    assert "Показать оригинал" in text
    assert "Скрыть оригинал" in text
    assert "default_text" in text


def test_prompt_types_expose_versioning_fields() -> None:
    text = _read(TYPES_PATH)
    assert "version?: string;" in text
    assert "updated_at?: string | null;" in text
    assert "stack_version?: string;" in text
