from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
ADMIN_PANEL_PATH = REPO_ROOT / "bot_psychologist/web_ui/src/components/admin/AdminPanel.tsx"


def test_retrieval_tab_explains_caps_and_pipeline() -> None:
    text = ADMIN_PANEL_PATH.read_text(encoding="utf-8", errors="ignore")
    assert "Retrieval Pipeline (Neo)" in text
    assert "Final cap (high)" in text
    assert "Stage order: initial retrieval" in text
