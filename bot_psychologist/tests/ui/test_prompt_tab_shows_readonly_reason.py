from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
PROMPT_EDITOR_PATH = REPO_ROOT / "bot_psychologist/web_ui/src/components/admin/PromptEditorPanel.tsx"
ADMIN_ROUTES_PATH = REPO_ROOT / "bot_psychologist/api/admin_routes.py"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def test_prompt_tab_shows_readonly_reason_metadata() -> None:
    text = _read(PROMPT_EDITOR_PATH)
    assert "read_only_reason" in text
    assert "editable_section" in text


def test_prompt_usage_backend_has_runtime_readonly_reason() -> None:
    text = _read(ADMIN_ROUTES_PATH)
    assert "runtime_derived_section_not_editable_via_admin" in text
    assert "derived_from" in text
    assert "usage_markers" in text
