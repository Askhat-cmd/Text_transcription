from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
API_ROUTE_FILES = [
    REPO_ROOT / "bot_psychologist/api/routes/chat.py",
    REPO_ROOT / "bot_psychologist/api/routes/common.py",
]


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def test_streaming_entrypoint_exists() -> None:
    text = _read_text(API_ROUTE_FILES[0])
    assert "ask_adaptive_question_stream" in text
    assert "/questions/adaptive-stream" in text


def test_streaming_runtime_legacy_markers_are_sanitized() -> None:
    text = "\n".join(_read_text(path) for path in API_ROUTE_FILES)
    # Active runtime should not contain legacy streaming classifier split.
    assert "_classify_parallel(" not in text
    assert "sd_classifier" not in text

    # Active runtime uses explicit multiagent builders + compat debug view.
    assert "_build_multiagent_trace_storage_payload(" in text
    assert "_build_debug_trace_compat_payload(" in text
    assert "\"sd_classification\"" in text
    assert "\"sd_detail\"" in text
    assert "user_level_adapter_applied" in text
