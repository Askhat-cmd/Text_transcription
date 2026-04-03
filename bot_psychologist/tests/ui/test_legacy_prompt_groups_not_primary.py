from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SERVICE_PATH = REPO_ROOT / "bot_psychologist/web_ui/src/services/adminConfig.service.ts"
PANEL_PATH = REPO_ROOT / "bot_psychologist/web_ui/src/components/admin/AdminPanel.tsx"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def test_legacy_prompt_endpoint_not_used_as_primary_prompt_surface() -> None:
    text = _read(SERVICE_PATH)
    assert "getPrompts: () =>\n    request<PromptMeta[]>('GET', '/prompts/stack-v2')" in text
    assert "request<PromptMeta[]>('GET', '/prompts')," not in text


def test_legacy_prompt_groups_not_referenced_in_primary_admin_panel() -> None:
    text = _read(PANEL_PATH)
    assert "Mode: Informational (curious)" not in text
    assert "Спиральная динамика" not in text
