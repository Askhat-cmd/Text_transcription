from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
ADMIN_PANEL_PATH = REPO_ROOT / "bot_psychologist/web_ui/src/components/admin/AdminPanel.tsx"


def _read() -> str:
    return ADMIN_PANEL_PATH.read_text(encoding="utf-8", errors="ignore")


def test_retrieval_panel_mentions_real_pipeline_stages() -> None:
    text = _read()
    assert "Retrieval Pipeline (Neo)" in text
    assert "initial retrieval → rerank → confidence cap → final blocks to LLM" in text
    assert "Initial top-k" in text
    assert "Rerank enabled" in text
