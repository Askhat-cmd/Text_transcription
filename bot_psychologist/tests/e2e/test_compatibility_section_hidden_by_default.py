from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
ADMIN_PANEL_PATH = REPO_ROOT / "bot_psychologist/web_ui/src/components/admin/AdminPanel.tsx"


def test_compatibility_section_hidden_by_default_markers() -> None:
    text = ADMIN_PANEL_PATH.read_text(encoding="utf-8", errors="ignore")
    assert "const [showCompatibility, setShowCompatibility] = useState(false);" in text
    assert "TABS.filter((tab) => tab.key !== 'compatibility')" in text
    assert "Показать Compatibility" in text
