from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
HOOK_PATH = REPO_ROOT / "bot_psychologist/web_ui/src/hooks/useAdminConfig.ts"
EDITOR_PATH = REPO_ROOT / "bot_psychologist/web_ui/src/components/admin/PromptEditorPanel.tsx"


def test_prompt_fetch_retry_flow_markers_present() -> None:
    hook_text = HOOK_PATH.read_text(encoding="utf-8", errors="ignore")
    panel_text = EDITOR_PATH.read_text(encoding="utf-8", errors="ignore")
    assert "retryPromptDetailLoad" in hook_text
    assert "setPromptError" in hook_text
    assert "onRetryLoad" in panel_text
    assert "Повторить" in panel_text
