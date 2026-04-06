from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
ADMIN_PANEL_PATH = REPO_ROOT / "bot_psychologist/web_ui/src/components/admin/AdminPanel.tsx"
HOOK_PATH = REPO_ROOT / "bot_psychologist/web_ui/src/hooks/useAdminConfig.ts"


def test_admin_save_feedback_and_validation_states() -> None:
    admin_text = ADMIN_PANEL_PATH.read_text(encoding="utf-8", errors="ignore")
    hook_text = HOOK_PATH.read_text(encoding="utf-8", errors="ignore")
    assert "successMessage" in admin_text
    assert "setError" in hook_text
    assert "setSuccessMessage" in hook_text
