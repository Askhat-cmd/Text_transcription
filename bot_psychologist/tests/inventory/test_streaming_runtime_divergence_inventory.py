from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
API_ROUTES = REPO_ROOT / "bot_psychologist/api/routes.py"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def test_streaming_entrypoint_exists() -> None:
    text = _read_text(API_ROUTES)
    assert "ask_adaptive_question_stream" in text
    assert "/questions/adaptive-stream" in text


def test_streaming_runtime_legacy_markers_are_sanitized() -> None:
    text = _read_text(API_ROUTES)
    # Active runtime should not contain legacy streaming classifier split.
    assert "_classify_parallel(" not in text
    assert "sd_classifier" not in text

    # Active runtime keeps explicit sanitization of legacy trace fields.
    assert "trace.pop(\"sd_classification\", None)" in text
    assert "trace.pop(\"sd_detail\", None)" in text
    assert "user_level_adapter_applied" in text
