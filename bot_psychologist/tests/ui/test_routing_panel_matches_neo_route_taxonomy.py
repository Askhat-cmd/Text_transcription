from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
ADMIN_PANEL_PATH = REPO_ROOT / "bot_psychologist/web_ui/src/components/admin/AdminPanel.tsx"


def _read() -> str:
    return ADMIN_PANEL_PATH.read_text(encoding="utf-8", errors="ignore")


def test_routing_panel_has_neo_route_taxonomy() -> None:
    text = _read()
    assert "Neo Route Taxonomy" in text
    for route in ("safe_override", "regulate", "reflect", "practice", "inform", "contact_hold"):
        assert route in text
