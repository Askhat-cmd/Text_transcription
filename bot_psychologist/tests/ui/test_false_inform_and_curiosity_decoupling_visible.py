from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
ADMIN_PANEL_PATH = REPO_ROOT / "bot_psychologist/web_ui/src/components/admin/AdminPanel.tsx"


def _read_admin_panel() -> str:
    return ADMIN_PANEL_PATH.read_text(encoding="utf-8", errors="ignore")


def test_false_inform_and_curiosity_decoupling_visible() -> None:
    text = _read_admin_panel()
    assert "false-inform protection" in text
    assert "curiosity decoupling" in text
    assert "curious` больше не принуждает informational override" in text

