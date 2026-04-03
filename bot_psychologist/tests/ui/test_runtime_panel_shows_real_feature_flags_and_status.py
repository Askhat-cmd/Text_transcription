from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
ADMIN_PANEL_PATH = REPO_ROOT / "bot_psychologist/web_ui/src/components/admin/AdminPanel.tsx"
ROUTES_PATH = REPO_ROOT / "bot_psychologist/api/admin_routes.py"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def test_runtime_panel_contains_status_and_feature_flags_sections() -> None:
    text = _read(ADMIN_PANEL_PATH)
    assert "Статус системы" in text
    assert "DEGRADED_MODE" in text
    assert "Feature Flags" in text


def test_admin_status_endpoint_includes_feature_flags() -> None:
    text = _read(ROUTES_PATH)
    assert "\"feature_flags\": status_payload[\"feature_flags\"]" in text
