from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
ADMIN_PANEL_PATH = REPO_ROOT / "bot_psychologist/web_ui/src/components/admin/AdminPanel.tsx"


def _read_admin_panel() -> str:
    return ADMIN_PANEL_PATH.read_text(encoding="utf-8", errors="ignore")


def test_legacy_routing_tab_component_not_used_in_primary_surface() -> None:
    text = _read_admin_panel()
    assert "import { RoutingTab }" not in text
    assert "<RoutingTab" not in text


def test_primary_routing_panel_is_neo_only() -> None:
    text = _read_admin_panel()
    assert "DEPRECATED_ROUTING_KEYS" not in text
    assert "SD_CLASSIFIER_ENABLED" not in text
    assert "SD_CLASSIFIER_CONFIDENCE_THRESHOLD" not in text
    assert "PROMPT_SD_OVERRIDES_BASE" not in text
