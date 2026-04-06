from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
ADMIN_PANEL_PATH = REPO_ROOT / "bot_psychologist/web_ui/src/components/admin/AdminPanel.tsx"


def test_routing_tab_policy_first_and_no_forensic_trace() -> None:
    text = ADMIN_PANEL_PATH.read_text(encoding="utf-8", errors="ignore")
    assert "Current Routing Policy" in text
    assert "Advanced Routing Controls" in text
    assert "last routing decision reason" not in text
