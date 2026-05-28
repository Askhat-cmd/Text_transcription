from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
ADMIN_PANEL_PATH = REPO_ROOT / "bot_psychologist/web_ui/src/components/admin/AdminPanel.tsx"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def test_runtime_tab_shows_response_planner_effective_card() -> None:
    text = _read(ADMIN_PANEL_PATH)
    assert "Response Planner" in text
    assert "live_acceptance_requires_api_trace" in text
