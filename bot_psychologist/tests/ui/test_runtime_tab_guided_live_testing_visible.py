from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
ADMIN_PANEL_PATH = REPO_ROOT / "bot_psychologist/web_ui/src/components/admin/AdminPanel.tsx"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def test_runtime_tab_shows_guided_live_testing_card() -> None:
    text = _read(ADMIN_PANEL_PATH)
    assert "Guided Live Testing" in text
    assert "raw_dialogue_saved_by_default" in text
