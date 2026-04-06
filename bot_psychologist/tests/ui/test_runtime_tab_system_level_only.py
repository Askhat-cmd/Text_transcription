from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
ADMIN_PANEL_PATH = REPO_ROOT / "bot_psychologist/web_ui/src/components/admin/AdminPanel.tsx"
ADMIN_ROUTES_PATH = REPO_ROOT / "bot_psychologist/api/admin_routes.py"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def test_runtime_tab_system_level_only() -> None:
    text = _read(ADMIN_PANEL_PATH)
    assert "Effective Runtime Truth" in text
    assert "developer trace supported:" in text
    assert "developer trace enabled:" in text
    assert "last session id" not in text
    assert "last turn #" not in text


def test_runtime_effective_payload_no_turn_identity_fields() -> None:
    text = _read(ADMIN_ROUTES_PATH)
    function_body = text.split("def _build_runtime_effective_payload", 1)[1].split("def ", 1)[0]
    assert "last_trace" not in function_body
    assert '"developer_trace_supported": True' in function_body
    assert '"developer_trace_enabled": True' in function_body
    assert '"last_turn_number"' not in function_body
    assert '"session_id"' not in function_body
