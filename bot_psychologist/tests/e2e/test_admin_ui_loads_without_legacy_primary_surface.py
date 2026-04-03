from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
ADMIN_PANEL_PATH = REPO_ROOT / "bot_psychologist/web_ui/src/components/admin/AdminPanel.tsx"


def test_admin_primary_surface_does_not_expose_legacy_tabs() -> None:
    text = ADMIN_PANEL_PATH.read_text(encoding="utf-8", errors="ignore")
    assert "key: 'storage'" not in text
    assert "key: 'history'" not in text
    assert "import { RoutingTab }" not in text
