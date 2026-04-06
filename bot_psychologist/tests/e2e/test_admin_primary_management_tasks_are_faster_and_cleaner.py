from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
ADMIN_PANEL_PATH = REPO_ROOT / "bot_psychologist/web_ui/src/components/admin/AdminPanel.tsx"


def test_admin_primary_management_tasks_are_faster_and_cleaner() -> None:
    text = ADMIN_PANEL_PATH.read_text(encoding="utf-8", errors="ignore")
    assert "Deep message-level diagnostics are available in developer trace inside chat." in text
    assert "key: 'trace'" not in text
    assert "Effective Runtime Truth" in text
