from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
ADMIN_PANEL_PATH = REPO_ROOT / "bot_psychologist/web_ui/src/components/admin/AdminPanel.tsx"


def _read() -> str:
    return ADMIN_PANEL_PATH.read_text(encoding="utf-8", errors="ignore")


def test_diagnostics_panel_mentions_v1_contract_fields() -> None:
    text = _read()
    assert "Diagnostics v1" in text
    assert "nervous_system_state" in text
    assert "request_function" in text
    assert "informational narrowing" in text
