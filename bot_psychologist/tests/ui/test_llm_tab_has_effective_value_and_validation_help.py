from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
ADMIN_PANEL_PATH = REPO_ROOT / "bot_psychologist/web_ui/src/components/admin/AdminPanel.tsx"
GROUP_PANEL_PATH = REPO_ROOT / "bot_psychologist/web_ui/src/components/admin/ConfigGroupPanel.tsx"


def test_llm_tab_has_effective_value_and_validation_help() -> None:
    admin_text = ADMIN_PANEL_PATH.read_text(encoding="utf-8", errors="ignore")
    group_text = GROUP_PANEL_PATH.read_text(encoding="utf-8", errors="ignore")
    assert "key: 'llm'" in admin_text
    assert "[{param.min}" in group_text
    assert "param.max" in group_text
