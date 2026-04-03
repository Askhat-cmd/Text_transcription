from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
ADMIN_PANEL_PATH = REPO_ROOT / "bot_psychologist/web_ui/src/components/admin/AdminPanel.tsx"


def _read() -> str:
    return ADMIN_PANEL_PATH.read_text(encoding="utf-8", errors="ignore")


def test_memory_panel_mentions_summary_snapshot_model() -> None:
    text = _read()
    assert "Memory Model v1.1" in text
    assert "Summary enabled" in text
    assert "Snapshot schema v1.1" in text
    assert "staleness/fallback policy" in text
