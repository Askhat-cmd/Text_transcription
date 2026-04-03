from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
HOOK_PATH = REPO_ROOT / "bot_psychologist/web_ui/src/hooks/useAdminConfig.ts"
EDITOR_PATH = REPO_ROOT / "bot_psychologist/web_ui/src/components/admin/PromptEditorPanel.tsx"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def test_prompt_fetch_error_has_retry_callback_in_hook() -> None:
    text = _read(HOOK_PATH)
    assert "promptError" in text
    assert "retryPromptDetailLoad" in text
    assert "Не удалось загрузить секцию prompt stack v2" in text


def test_prompt_fetch_error_is_actionable_in_ui() -> None:
    text = _read(EDITOR_PATH)
    assert "Повторить" in text
    assert "onRetryLoad" in text
