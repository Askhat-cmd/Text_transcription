from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
ADMIN_PANEL_PATH = REPO_ROOT / "bot_psychologist/web_ui/src/components/admin/AdminPanel.tsx"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def test_compatibility_button_deemphasized() -> None:
    text = _read(ADMIN_PANEL_PATH)
    assert "Advanced" in text
    assert "Show Compatibility tab" in text
    assert "Hide Compatibility tab" in text
    assert "Показать Compatibility" not in text
