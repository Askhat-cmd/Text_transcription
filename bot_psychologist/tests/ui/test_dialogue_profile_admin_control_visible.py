from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
ADMIN_PANEL_PATH = REPO_ROOT / "bot_psychologist/web_ui/src/components/admin/AdminPanel.tsx"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def test_runtime_tab_shows_dialogue_profile_control_block() -> None:
    text = _read(ADMIN_PANEL_PATH)
    assert "Dialogue Profile" in text
    assert "mvp_free_dialogue" in text
    assert "dialogue_profile?.warning" in text
    assert "effective.writer_autonomy" in text
    assert "effective.planner_authority" in text
