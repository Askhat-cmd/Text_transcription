from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
ADMIN_PANEL_PATH = REPO_ROOT / "bot_psychologist/web_ui/src/components/admin/AdminPanel.tsx"


def _read_admin_panel() -> str:
    return ADMIN_PANEL_PATH.read_text(encoding="utf-8", errors="ignore")


def test_primary_admin_tabs_match_neo_runtime_ia() -> None:
    text = _read_admin_panel()
    expected_tabs = [
        "key: 'llm'",
        "key: 'retrieval'",
        "key: 'diagnostics'",
        "key: 'routing'",
        "key: 'memory'",
        "key: 'prompts'",
        "key: 'runtime'",
        "key: 'compatibility'",
    ]
    for marker in expected_tabs:
        assert marker in text, f"Missing neo primary tab marker: {marker}"

    assert "key: 'history'" not in text
    assert "key: 'storage'" not in text
