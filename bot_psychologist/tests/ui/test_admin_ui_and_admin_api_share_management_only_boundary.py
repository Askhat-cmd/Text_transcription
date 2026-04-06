from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
ADMIN_PANEL_PATH = REPO_ROOT / "bot_psychologist/web_ui/src/components/admin/AdminPanel.tsx"
ADMIN_SERVICE_PATH = REPO_ROOT / "bot_psychologist/web_ui/src/services/adminConfig.service.ts"
ADMIN_ROUTES_PATH = REPO_ROOT / "bot_psychologist/api/admin_routes.py"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def test_admin_ui_and_admin_api_share_management_only_boundary() -> None:
    panel_text = _read(ADMIN_PANEL_PATH)
    service_text = _read(ADMIN_SERVICE_PATH)
    routes_text = _read(ADMIN_ROUTES_PATH)

    assert "Trace" not in panel_text.split("const TABS", 1)[1].split("];", 1)[0]
    assert "/trace/last" not in service_text
    assert "/trace/recent" not in service_text
    assert "/prompts/stack-v2/usage" not in service_text

    assert "def _build_trace_turn_payload" not in routes_text
    assert "def _build_prompt_stack_usage_payload" not in routes_text

