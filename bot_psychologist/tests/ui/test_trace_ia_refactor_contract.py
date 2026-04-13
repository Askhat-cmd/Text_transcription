from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
INLINE_TRACE_PATH = REPO_ROOT / "bot_psychologist/web_ui/src/components/chat/InlineDebugTrace.tsx"
LLM_CANVAS_PATH = REPO_ROOT / "bot_psychologist/web_ui/src/components/debug/LLMPayloadPanel.tsx"
SESSION_PANEL_PATH = REPO_ROOT / "bot_psychologist/web_ui/src/components/debug/SessionTracePanel.tsx"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def test_inline_trace_has_simple_deep_and_problems_controls() -> None:
    text = _read(INLINE_TRACE_PATH)
    assert "Simple" in text
    assert "Deep" in text
    assert "Problems only" in text
    assert "Export trace JSON (compact)" in text
    assert "Export trace JSON (full)" in text


def test_inline_trace_no_long_prompt_previews_in_llm_calls() -> None:
    text = _read(INLINE_TRACE_PATH)
    assert "System prompt (preview)" not in text
    assert "User prompt (preview)" not in text
    assert "Response (preview)" not in text
    assert "LLM Calls" in text


def test_session_widgets_moved_to_dedicated_panel() -> None:
    inline_text = _read(INLINE_TRACE_PATH)
    panel_text = _read(SESSION_PANEL_PATH)

    assert "SessionDashboard" not in inline_text
    assert "TraceHistory" not in inline_text
    assert "ConfigSnapshot" not in inline_text
    assert "Session Totals" in panel_text
    assert "Session Dashboard" in panel_text
    assert "Trace History" in panel_text
    assert "Config Snapshot" in panel_text


def test_llm_canvas_uses_utf8_strings_and_copy_actions() -> None:
    text = _read(LLM_CANVAS_PATH)
    assert "Полотно LLM" in text
    assert "Копировать все" in text
    assert "Копировать call" in text
    assert "Копировать section" in text
