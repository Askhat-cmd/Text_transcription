from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
ADMIN_PANEL_PATH = REPO_ROOT / "bot_psychologist/web_ui/src/components/admin/AdminPanel.tsx"


def _read_admin_panel() -> str:
    return ADMIN_PANEL_PATH.read_text(encoding="utf-8", errors="ignore")


def test_sd_and_user_level_prompts_not_exposed_as_primary_tabs() -> None:
    text = _read_admin_panel()
    assert "Спиральная динамика" not in text
    assert "Уровень пользователя" not in text
    assert "Mode: Informational (curious)" not in text


def test_compatibility_tab_exists_for_legacy_controls() -> None:
    text = _read_admin_panel()
    assert "key: 'compatibility'" in text
    assert "Compatibility" in text
