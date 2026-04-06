from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
ADMIN_PANEL_PATH = REPO_ROOT / "bot_psychologist/web_ui/src/components/admin/AdminPanel.tsx"
ADMIN_ROUTES_PATH = REPO_ROOT / "bot_psychologist/api/admin_routes.py"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def test_runtime_tab_keeps_schema_version_fields_visible() -> None:
    text = _read(ADMIN_PANEL_PATH)
    assert "schema_version:" in text
    assert "admin_schema_version:" in text
    assert "prompt_stack_version:" in text


def test_admin_backend_versions_updated_to_105_family() -> None:
    text = _read(ADMIN_ROUTES_PATH)
    assert 'ADMIN_SCHEMA_VERSION = "10.5"' in text
    assert 'ADMIN_EFFECTIVE_SCHEMA_VERSION = "10.5.1"' in text
    assert 'ADMIN_SCHEMA_VERSION = "10.4"' not in text
    assert 'ADMIN_EFFECTIVE_SCHEMA_VERSION = "10.4.1"' not in text

